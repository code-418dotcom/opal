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
    const itemId = url.searchParams.get("item_id");
    const bucket = url.searchParams.get("bucket") || "outputs";

    if (!itemId) {
      return new Response(
        JSON.stringify({ error: "item_id parameter is required" }),
        {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    if (!["raw", "outputs", "exports"].includes(bucket)) {
      return new Response(
        JSON.stringify({ error: "Invalid bucket. Must be raw, outputs, or exports" }),
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

    const { data: item, error: itemError } = await supabase
      .from("job_items")
      .select("id, tenant_id, raw_blob_path, output_blob_path")
      .eq("id", itemId)
      .maybeSingle();

    if (itemError || !item || item.tenant_id !== tenantId) {
      return new Response(
        JSON.stringify({ error: "Item not found" }),
        {
          status: 404,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    const blobPath = bucket === "raw" ? item.raw_blob_path : item.output_blob_path;

    if (!blobPath) {
      return new Response(
        JSON.stringify({ error: "File not found for this item" }),
        {
          status: 404,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    const { data: signedData, error: signedError } = await supabase.storage
      .from(bucket)
      .createSignedUrl(blobPath, 3600);

    if (signedError || !signedData) {
      console.error("Signed URL error:", signedError);
      return new Response(
        JSON.stringify({ error: "Failed to generate download URL" }),
        {
          status: 500,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    return new Response(
      JSON.stringify({
        download_url: signedData.signedUrl,
        expires_in: 3600,
        blob_path: blobPath,
      }),
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
