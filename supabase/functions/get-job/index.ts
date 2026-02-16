import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Client-Info, Apikey, X-API-Key",
};

function validateApiKey(apiKey: string | null): string {
  if (!apiKey) return "tenant_default";
  const validKeys = Deno.env.get("API_KEYS")?.split(",") || [];
  if (validKeys.length === 0) {
    return apiKey.replace("dev_", "tenant_");
  }
  if (!validKeys.includes(apiKey)) return "tenant_default";
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

    if (req.method !== "GET") {
      return new Response(
        JSON.stringify({ error: "Method not allowed" }),
        {
          status: 405,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    const url = new URL(req.url);
    const jobId = url.pathname.split("/").pop();

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

    if (jobError) {
      console.error("Job query error:", jobError);
      return new Response(
        JSON.stringify({ error: "Failed to fetch job" }),
        {
          status: 500,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    if (!job) {
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
      console.error("Job items query error:", itemsError);
      return new Response(
        JSON.stringify({ error: "Failed to fetch job items" }),
        {
          status: 500,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    const responseData = {
      job_id: job.id,
      tenant_id: job.tenant_id,
      brand_profile_id: job.brand_profile_id,
      status: job.status,
      correlation_id: job.correlation_id,
      items: items?.map((item) => ({
        item_id: item.id,
        filename: item.filename,
        status: item.status,
        raw_blob_path: item.raw_blob_path,
        output_blob_path: item.output_blob_path,
        error_message: item.error_message,
      })) || [],
    };

    return new Response(
      JSON.stringify(responseData),
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
