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

function buildRawBlobPath(tenantId: string, jobId: string, itemId: string, filename: string): string {
  const tenant = sanitizePathComponent(tenantId);
  const job = sanitizePathComponent(jobId);
  const item = sanitizePathComponent(itemId);
  const safeFilename = sanitizeFilename(filename);
  return `${tenant}/jobs/${job}/items/${item}/raw/${safeFilename}`;
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

    const formData = await req.formData();
    const file = formData.get("file") as File;
    const jobId = formData.get("job_id") as string;
    const itemId = formData.get("item_id") as string;

    if (!file || !jobId || !itemId) {
      return new Response(
        JSON.stringify({ error: "file, job_id, and item_id are required" }),
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
      .select("id")
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

    const { data: item, error: itemError } = await supabase
      .from("job_items")
      .select("id, tenant_id, job_id, filename")
      .eq("id", itemId)
      .maybeSingle();

    if (itemError || !item || item.tenant_id !== tenantId || item.job_id !== jobId) {
      return new Response(
        JSON.stringify({ error: "Item not found" }),
        {
          status: 404,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    const rawPath = buildRawBlobPath(tenantId, jobId, itemId, file.name || item.filename);
    const fileBytes = await file.arrayBuffer();

    const { error: uploadError } = await supabase.storage
      .from("raw")
      .upload(rawPath, fileBytes, {
        contentType: file.type || "application/octet-stream",
        upsert: true,
      });

    if (uploadError) {
      console.error("Upload error:", uploadError);
      return new Response(
        JSON.stringify({ error: "Failed to upload file" }),
        {
          status: 500,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    const { error: updateError } = await supabase
      .from("job_items")
      .update({ raw_blob_path: rawPath, status: "uploaded" })
      .eq("id", itemId);

    if (updateError) {
      console.error("Update error:", updateError);
      return new Response(
        JSON.stringify({ error: "Failed to update item status" }),
        {
          status: 500,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    return new Response(
      JSON.stringify({ ok: true, raw_blob_path: rawPath }),
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
