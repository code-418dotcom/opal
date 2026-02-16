import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Client-Info, Apikey",
};

function validateApiKey(apiKey: string | null): string | null {
  if (!apiKey) return null;
  const validKeys = Deno.env.get("API_KEYS")?.split(",") || [];
  if (!validKeys.includes(apiKey)) return null;
  return apiKey.replace("dev_", "tenant_");
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      status: 200,
      headers: corsHeaders,
    });
  }

  try {
    const apiKey = req.headers.get("x-api-key");
    const tenantId = validateApiKey(apiKey);

    if (!tenantId) {
      return new Response(
        JSON.stringify({ error: "Invalid or missing API key" }),
        {
          status: 401,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    if (req.method !== "POST") {
      return new Response(
        JSON.stringify({ error: "Method not allowed" }),
        {
          status: 405,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    const url = new URL(req.url);
    const jobId = url.pathname.split("/").filter(Boolean).pop();

    if (!jobId) {
      return new Response(
        JSON.stringify({ error: "Job ID is required" }),
        {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    const supabase = createClient(
      Deno.env.get("SUPABASE_URL") ?? "",
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? ""
    );

    const { data: job, error: jobError } = await supabase
      .from("jobs")
      .select("*")
      .eq("id", jobId)
      .eq("tenant_id", tenantId)
      .maybeSingle();

    if (jobError || !job) {
      return new Response(
        JSON.stringify({ error: "Job not found" }),
        {
          status: 404,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    const { data: items, error: itemsError } = await supabase
      .from("job_items")
      .select("*")
      .eq("job_id", jobId);

    if (itemsError) {
      console.error("Items query error:", itemsError);
      return new Response(
        JSON.stringify({ error: "Failed to fetch job items" }),
        {
          status: 500,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    const queueMessages = [];
    for (const item of items || []) {
      if (item.status === "created" || item.status === "uploaded") {
        queueMessages.push({
          queue_name: "jobs",
          payload: {
            tenant_id: tenantId,
            job_id: jobId,
            item_id: item.id,
            correlation_id: job.correlation_id,
          },
          status: "pending",
          attempts: 0,
          max_attempts: 3,
        });
      }
    }

    if (queueMessages.length > 0) {
      const { error: queueError } = await supabase
        .from("job_queue")
        .insert(queueMessages);

      if (queueError) {
        console.error("Queue insert error:", queueError);
        return new Response(
          JSON.stringify({ error: "Failed to enqueue job items" }),
          {
            status: 500,
            headers: { ...corsHeaders, "Content-Type": "application/json" },
          }
        );
      }
    }

    const { error: updateError } = await supabase
      .from("jobs")
      .update({ status: "processing" })
      .eq("id", jobId);

    if (updateError) {
      console.error("Job update error:", updateError);
    }

    return new Response(
      JSON.stringify({ ok: true, enqueued: queueMessages.length }),
      {
        status: 200,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      }
    );
  } catch (error) {
    console.error("Error:", error);
    return new Response(
      JSON.stringify({ error: "Internal server error" }),
      {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      }
    );
  }
});
