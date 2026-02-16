import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Client-Info, Apikey",
};

function newId(prefix: string): string {
  return `${prefix}_${crypto.randomUUID().replace(/-/g, "")}`;
}

function sanitizePathComponent(component: string): string {
  if (!component || component.includes("..") || !/^[a-zA-Z0-9_\-]+$/.test(component)) {
    throw new Error("Invalid path component");
  }
  return component;
}

function sanitizeFilename(filename: string): string {
  const name = filename.split("/").pop() || "";
  if (!name || name === "." || name === ".." || !/^[a-zA-Z0-9_\-\.]+$/.test(name)) {
    throw new Error("Invalid filename");
  }
  return name;
}

function buildOutputBlobPath(tenantId: string, jobId: string, itemId: string, filename: string): string {
  const tenant = sanitizePathComponent(tenantId);
  const job = sanitizePathComponent(jobId);
  const item = sanitizePathComponent(itemId);
  const safeFilename = sanitizeFilename(filename);
  return `${tenant}/jobs/${job}/items/${item}/outputs/${safeFilename}`;
}

async function processMessage(supabase: any, message: any): Promise<void> {
  const { tenant_id, job_id, item_id, correlation_id } = message.payload;

  console.log(`Processing: tenant=${tenant_id} job=${job_id} item=${item_id}`);

  const { data: item, error: itemError } = await supabase
    .from("job_items")
    .select("*")
    .eq("id", item_id)
    .maybeSingle();

  if (itemError || !item) {
    console.error("Item not found:", item_id);
    throw new Error("Item not found");
  }

  if (item.status === "processing" || item.status === "completed") {
    console.log(`Item already ${item.status}:`, item_id);
    return;
  }

  await supabase
    .from("job_items")
    .update({ status: "processing" })
    .eq("id", item_id);

  if (!item.raw_blob_path) {
    await supabase
      .from("job_items")
      .update({ status: "failed", error_message: "Missing raw_blob_path" })
      .eq("id", item_id);
    throw new Error("Missing raw_blob_path");
  }

  console.log("[1/3] Downloading input:", item_id);
  const { data: inputData, error: downloadError } = await supabase.storage
    .from("raw")
    .download(item.raw_blob_path);

  if (downloadError || !inputData) {
    console.error("Download error:", downloadError);
    await supabase
      .from("job_items")
      .update({ status: "failed", error_message: "Failed to download input file" })
      .eq("id", item_id);
    throw new Error("Failed to download input file");
  }

  const inputBytes = await inputData.arrayBuffer();

  console.log("[2/3] Processing image (pass-through mode):", item_id);
  const outputBytes = inputBytes;

  const itemOutId = newId("out");
  const outName = `${itemOutId}.png`;
  const outPath = buildOutputBlobPath(tenant_id, job_id, item_id, outName);

  console.log("[3/3] Uploading output:", outPath);
  const { error: uploadError } = await supabase.storage
    .from("outputs")
    .upload(outPath, outputBytes, {
      contentType: "image/png",
      upsert: true,
    });

  if (uploadError) {
    console.error("Upload error:", uploadError);
    await supabase
      .from("job_items")
      .update({ status: "failed", error_message: "Failed to upload output file" })
      .eq("id", item_id);
    throw new Error("Failed to upload output file");
  }

  await supabase
    .from("job_items")
    .update({ status: "completed", output_blob_path: outPath })
    .eq("id", item_id);

  console.log("Item completed:", item_id);
}

async function finalizeJobStatus(supabase: any, jobId: string): Promise<void> {
  const { data: items } = await supabase
    .from("job_items")
    .select("status")
    .eq("job_id", jobId);

  if (!items || items.length === 0) return;

  const statuses = items.map((i: any) => i.status);
  const completed = statuses.filter((s: string) => s === "completed").length;
  const failed = statuses.filter((s: string) => s === "failed").length;
  const processing = statuses.filter((s: string) => s === "processing").length;

  let newStatus = "processing";
  if (completed === items.length) {
    newStatus = "completed";
  } else if (failed === items.length) {
    newStatus = "failed";
  } else if (failed > 0 && completed + failed === items.length) {
    newStatus = "partial";
  }

  await supabase
    .from("jobs")
    .update({ status: newStatus })
    .eq("id", jobId);

  console.log(`Job ${jobId} status: ${newStatus}`);
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      status: 200,
      headers: corsHeaders,
    });
  }

  try {
    const supabase = createClient(
      Deno.env.get("SUPABASE_URL") ?? "",
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? ""
    );

    const maxMessages = 5;
    console.log(`Polling for up to ${maxMessages} messages...`);

    const { data: messages, error: messagesError } = await supabase
      .rpc("process_queue_messages", {
        p_queue_name: "jobs",
        p_max_count: maxMessages,
      });

    if (messagesError) {
      console.error("Failed to fetch messages:", messagesError);
      return new Response(
        JSON.stringify({ error: "Failed to fetch messages", processed: 0 }),
        {
          status: 500,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    const queueMessages = messages || [];
    console.log(`Received ${queueMessages.length} messages`);

    let processed = 0;
    let failed = 0;

    for (const msg of queueMessages) {
      try {
        await processMessage(supabase, msg);
        await finalizeJobStatus(supabase, msg.payload.job_id);

        await supabase
          .from("job_queue")
          .update({ status: "completed", processed_at: new Date().toISOString() })
          .eq("id", msg.id);

        processed++;
        console.log(`Message ${msg.id} completed`);
      } catch (error) {
        console.error(`Message ${msg.id} failed:`, error);

        const { data: queueItem } = await supabase
          .from("job_queue")
          .select("attempts, max_attempts")
          .eq("id", msg.id)
          .maybeSingle();

        if (queueItem && queueItem.attempts >= queueItem.max_attempts) {
          await supabase
            .from("job_queue")
            .update({
              status: "failed",
              error: String(error),
              processed_at: new Date().toISOString(),
            })
            .eq("id", msg.id);
          console.log(`Message ${msg.id} dead-lettered`);
        } else {
          await supabase
            .from("job_queue")
            .update({ status: "pending", error: String(error) })
            .eq("id", msg.id);
          console.log(`Message ${msg.id} returned to queue`);
        }

        failed++;
      }
    }

    return new Response(
      JSON.stringify({
        ok: true,
        processed,
        failed,
        total: queueMessages.length,
      }),
      {
        status: 200,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      }
    );
  } catch (error) {
    console.error("Worker error:", error);
    return new Response(
      JSON.stringify({ error: "Worker error", details: String(error) }),
      {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      }
    );
  }
});
