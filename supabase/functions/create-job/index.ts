import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Client-Info, Apikey, X-API-Key",
};

interface ItemIn {
  filename: string;
}

interface CreateJobRequest {
  brand_profile_id?: string;
  items: ItemIn[];
}

function newId(prefix: string): string {
  return `${prefix}_${crypto.randomUUID().replace(/-/g, "")}`;
}

function newCorrelationId(): string {
  return crypto.randomUUID().replace(/-/g, "");
}

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

    if (req.method !== "POST") {
      return new Response(
        JSON.stringify({ error: "Method not allowed" }),
        {
          status: 405,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    const body: CreateJobRequest = await req.json();

    if (!body.items || !Array.isArray(body.items) || body.items.length === 0) {
      return new Response(
        JSON.stringify({ error: "Items array is required and must not be empty" }),
        {
          status: 400,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    if (body.items.length > 100) {
      return new Response(
        JSON.stringify({ error: "Maximum 100 items per job" }),
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

    const jobId = newId("job");
    const correlationId = newCorrelationId();
    const brandProfileId = body.brand_profile_id || "default";

    const jobData = {
      id: jobId,
      tenant_id: tenantId,
      brand_profile_id: brandProfileId,
      status: "created",
      correlation_id: correlationId,
    };

    const { error: jobError } = await supabase
      .from("jobs")
      .insert(jobData);

    if (jobError) {
      console.error("Job creation error:", jobError);
      return new Response(
        JSON.stringify({ error: "Failed to create job" }),
        {
          status: 500,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    const itemsData = body.items.map((item) => {
      const itemId = newId("item");
      return {
        id: itemId,
        job_id: jobId,
        tenant_id: tenantId,
        filename: item.filename,
        status: "created",
      };
    });

    const { error: itemsError } = await supabase
      .from("job_items")
      .insert(itemsData);

    if (itemsError) {
      console.error("Job items creation error:", itemsError);
      return new Response(
        JSON.stringify({ error: "Failed to create job items" }),
        {
          status: 500,
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        }
      );
    }

    const responseData = {
      job_id: jobId,
      correlation_id: correlationId,
      items: itemsData.map((item) => ({
        item_id: item.id,
        filename: item.filename,
      })),
    };

    return new Response(
      JSON.stringify(responseData),
      {
        status: 201,
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
