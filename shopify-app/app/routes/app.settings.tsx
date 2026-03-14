/**
 * Settings — pixel key display, auto-configure pixel, auto-conclude config.
 */
import type { LoaderFunctionArgs, ActionFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { useLoaderData, useActionData, useNavigate, useNavigation, useSubmit } from "@remix-run/react";
import {
  Page,
  Layout,
  Card,
  BlockStack,
  Text,
  TextField,
  Banner,
  Divider,
  Box,
  InlineStack,
  Button,
  Badge,
} from "@shopify/polaris";
import { useCallback, useState, useEffect } from "react";

import { authenticate } from "~/shopify.server";
import { getIntegrationByShop, ensurePixelKey, getGAConfig, updateGAConfig } from "~/lib/opal-api.server";
import { getEntitlements } from "~/lib/entitlements.server";
import { OpalLogo } from "~/components/OpalLogo";

const OPAL_API_URL = process.env.OPAL_API_URL || "https://dev.opaloptics.com";

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const { session, admin, billing } = await authenticate.admin(request);
  const shopDomain = session.shop;

  const integration = await getIntegrationByShop(shopDomain);
  if (!integration) {
    return json({
      hasIntegration: false,
      pixelKey: null,
      integrationId: null,
      shopDomain,
      opalApiUrl: OPAL_API_URL,
      pixelStatus: "not_connected" as const,
      gaConfigured: false,
      gaMeasurementId: null as string | null,
      tier: "free" as const,
    });
  }

  // Ensure a pixel key exists
  let pixelKey = integration.pixel_key;
  if (!pixelKey) {
    try {
      pixelKey = await ensurePixelKey(integration.id);
    } catch {
      pixelKey = null;
    }
  }

  // Check if web pixel is already configured
  let pixelStatus: "not_configured" | "configured" | "unknown" = "unknown";
  try {
    const response = await admin.graphql(
      `#graphql
      query webPixel {
        webPixel {
          id
          settings
        }
      }`,
    );
    const body = await response.json();
    const pixel = body.data?.webPixel;

    if (pixel) {
      try {
        const s = JSON.parse(pixel.settings);
        pixelStatus = (s.opal_api_url && s.opal_pixel_key) ? "configured" : "not_configured";
      } catch {
        pixelStatus = "not_configured";
      }
    } else {
      pixelStatus = "not_configured";
    }
  } catch {
    pixelStatus = "unknown";
  }

  // Get GA4 config and entitlements
  let gaConfigured = false;
  let gaMeasurementId: string | null = null;
  let tier: "free" | "pro" | "unlimited" = "free";

  try {
    const [gaConfig, entitlements] = await Promise.all([
      getGAConfig(integration.id),
      getEntitlements(billing, integration.id),
    ]);
    gaConfigured = gaConfig.configured;
    gaMeasurementId = gaConfig.ga_measurement_id;
    tier = entitlements.tier;
  } catch {
    // Non-critical — defaults are fine
  }

  return json({
    hasIntegration: true,
    pixelKey,
    integrationId: integration.id,
    shopDomain,
    opalApiUrl: OPAL_API_URL,
    pixelStatus,
    gaConfigured,
    gaMeasurementId,
    tier,
  });
};

export const action = async ({ request }: ActionFunctionArgs) => {
  const { session, admin } = await authenticate.admin(request);
  const shopDomain = session.shop;
  const formData = await request.formData();
  const intent = formData.get("intent");

  if (intent === "save_ga_config") {
    const integration = await getIntegrationByShop(shopDomain);
    if (!integration) {
      return json({ ok: false, error: "Store not connected" }, { status: 400 });
    }
    const measurementId = formData.get("ga_measurement_id") as string | null;
    const apiSecret = formData.get("ga_api_secret") as string | null;
    try {
      const result = await updateGAConfig(integration.id, measurementId || null, apiSecret || null);
      return json({ ok: true, gaAction: result.configured ? "saved" : "cleared" });
    } catch (err) {
      return json({ ok: false, error: `Failed to save GA config: ${err instanceof Error ? err.message : "Unknown"}` }, { status: 500 });
    }
  }

  if (intent !== "configure_pixel") {
    return json({ ok: false, error: "Unknown action" }, { status: 400 });
  }

  // 1. Get integration and pixel key
  const integration = await getIntegrationByShop(shopDomain);
  if (!integration) {
    return json({ ok: false, error: "Store not connected to Opal. Connect from the Opal dashboard first." }, { status: 400 });
  }

  let pixelKey: string;
  try {
    pixelKey = await ensurePixelKey(integration.id);
  } catch (err) {
    return json({ ok: false, error: `Failed to get pixel key: ${err instanceof Error ? err.message : "Unknown error"}` }, { status: 500 });
  }

  // 2. Build the settings JSON
  const pixelSettings = JSON.stringify({
    opal_api_url: OPAL_API_URL,
    opal_pixel_key: pixelKey,
  });

  // 3. Try to create the web pixel first; if it already exists, update it
  try {
    const createResponse = await admin.graphql(
      `#graphql
      mutation webPixelCreate($webPixel: WebPixelInput!) {
        webPixelCreate(webPixel: $webPixel) {
          userErrors {
            code
            field
            message
          }
          webPixel {
            id
            settings
          }
        }
      }`,
      {
        variables: {
          webPixel: { settings: pixelSettings },
        },
      },
    );
    const createBody = await createResponse.json();
    const createErrors = createBody.data?.webPixelCreate?.userErrors || [];

    if (createErrors.length === 0) {
      return json({ ok: true, action: "created" });
    }

    // If pixel already exists, fetch its ID and update
    const alreadyExists = createErrors.some(
      (e: { code?: string; message: string }) =>
        e.message.toLowerCase().includes("already exists") ||
        e.code === "WEB_PIXEL_ALREADY_EXISTS",
    );

    if (!alreadyExists) {
      return json({
        ok: false,
        error: `Shopify error: ${createErrors.map((e: { message: string }) => e.message).join(", ")}`,
      }, { status: 400 });
    }

    // Fetch existing pixel ID
    const queryResponse = await admin.graphql(
      `#graphql
      query webPixel {
        webPixel {
          id
        }
      }`,
    );
    const queryBody = await queryResponse.json();
    const pixelId = queryBody.data?.webPixel?.id;

    if (!pixelId) {
      return json({
        ok: false,
        error: "Pixel already exists but could not retrieve its ID for update.",
      }, { status: 500 });
    }

    const updateResponse = await admin.graphql(
      `#graphql
      mutation webPixelUpdate($id: ID!, $webPixel: WebPixelInput!) {
        webPixelUpdate(id: $id, webPixel: $webPixel) {
          userErrors {
            field
            message
          }
          webPixel {
            id
            settings
          }
        }
      }`,
      {
        variables: {
          id: pixelId,
          webPixel: { settings: pixelSettings },
        },
      },
    );
    const updateBody = await updateResponse.json();
    const updateErrors = updateBody.data?.webPixelUpdate?.userErrors || [];

    if (updateErrors.length > 0) {
      return json({
        ok: false,
        error: `Shopify error: ${updateErrors.map((e: { message: string }) => e.message).join(", ")}`,
      }, { status: 400 });
    }

    return json({ ok: true, action: "updated" });
  } catch (err) {
    return json({
      ok: false,
      error: `Failed to configure pixel: ${err instanceof Error ? err.message : "Unknown error"}`,
    }, { status: 500 });
  }
};

export default function Settings() {
  const {
    hasIntegration, pixelKey, integrationId, shopDomain, opalApiUrl, pixelStatus,
    gaConfigured, gaMeasurementId, tier,
  } = useLoaderData<typeof loader>();
  const actionData = useActionData<typeof action>();
  const navigate = useNavigate();
  const navigation = useNavigation();
  const submit = useSubmit();

  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showBanner, setShowBanner] = useState(false);

  // GA config state
  const [gaMid, setGaMid] = useState(gaMeasurementId || "");
  const [gaSecret, setGaSecret] = useState("");

  const isConfiguring = navigation.state === "submitting" &&
    navigation.formData?.get("intent") === "configure_pixel";

  const isSavingGA = navigation.state === "submitting" &&
    navigation.formData?.get("intent") === "save_ga_config";

  // Show success/error banner after action completes
  useEffect(() => {
    if (actionData) {
      setShowBanner(true);
    }
  }, [actionData]);

  const handleCopy = useCallback(() => {
    if (pixelKey) {
      navigator.clipboard.writeText(pixelKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [pixelKey]);

  const handleConfigurePixel = useCallback(() => {
    const formData = new FormData();
    formData.set("intent", "configure_pixel");
    submit(formData, { method: "post" });
  }, [submit]);

  const handleSaveGA = useCallback(() => {
    const formData = new FormData();
    formData.set("intent", "save_ga_config");
    formData.set("ga_measurement_id", gaMid);
    formData.set("ga_api_secret", gaSecret);
    submit(formData, { method: "post" });
  }, [submit, gaMid, gaSecret]);

  const handleClearGA = useCallback(() => {
    const formData = new FormData();
    formData.set("intent", "save_ga_config");
    formData.set("ga_measurement_id", "");
    formData.set("ga_api_secret", "");
    submit(formData, { method: "post" });
    setGaMid("");
    setGaSecret("");
  }, [submit]);

  if (!hasIntegration) {
    return (
      <Page title={<InlineStack gap="200" blockAlign="center"><OpalLogo size={24} /> Settings</InlineStack> as any} backAction={{ onAction: () => navigate("/app") }}>
        <Layout>
          <Layout.Section>
            <Banner tone="warning">
              Your store ({shopDomain}) is not connected to Opal.
              Connect from the Opal dashboard first.
            </Banner>
          </Layout.Section>
        </Layout>
      </Page>
    );
  }

  const currentPixelStatus = actionData?.ok ? "configured" : pixelStatus;

  return (
    <Page title={<InlineStack gap="200" blockAlign="center"><OpalLogo size={24} /> Settings</InlineStack> as any} backAction={{ onAction: () => navigate("/app") }}>
      <Layout>
        {/* Action feedback banner */}
        {showBanner && actionData && (
          <Layout.Section>
            {actionData.ok ? (
              <Banner
                tone="success"
                onDismiss={() => setShowBanner(false)}
              >
                {"gaAction" in actionData
                  ? (actionData.gaAction === "saved"
                    ? "Google Analytics connected. Events will be relayed to your GA4 property."
                    : "Google Analytics disconnected.")
                  : `Pixel ${"action" in actionData && actionData.action === "created" ? "created" : "updated"} successfully. Your storefront is now tracking A/B test events automatically.`}
              </Banner>
            ) : (
              <Banner
                tone="critical"
                onDismiss={() => setShowBanner(false)}
              >
                {"error" in actionData ? actionData.error : "Failed to configure pixel."}
              </Banner>
            )}
          </Layout.Section>
        )}

        {/* Getting Started */}
        <Layout.Section>
          <Card>
            <BlockStack gap="400">
              <Text variant="headingMd" as="h2">
                Getting started
              </Text>
              <Text variant="bodySm" as="p" tone="subdued">
                Set up A/B image testing in 4 simple steps:
              </Text>
              <BlockStack gap="300">
                <InlineStack gap="300" blockAlign="start">
                  <Badge tone="info">1</Badge>
                  <BlockStack gap="050">
                    <Text variant="headingSm" as="h3">Configure pixel</Text>
                    <Text variant="bodySm" as="p" tone="subdued">
                      Click "Configure Pixel" below to enable automatic storefront tracking.
                    </Text>
                  </BlockStack>
                </InlineStack>
                <InlineStack gap="300" blockAlign="start">
                  <Badge tone="info">2</Badge>
                  <BlockStack gap="050">
                    <Text variant="headingSm" as="h3">Create a test</Text>
                    <Text variant="bodySm" as="p" tone="subdued">
                      Pick a product and select two images to compare (e.g. lifestyle vs. white background).
                    </Text>
                  </BlockStack>
                </InlineStack>
                <InlineStack gap="300" blockAlign="start">
                  <Badge tone="info">3</Badge>
                  <BlockStack gap="050">
                    <Text variant="headingSm" as="h3">Watch the results</Text>
                    <Text variant="bodySm" as="p" tone="subdued">
                      Opal tracks views, add-to-carts, and conversions for each variant automatically.
                    </Text>
                  </BlockStack>
                </InlineStack>
                <InlineStack gap="300" blockAlign="start">
                  <Badge tone="info">4</Badge>
                  <BlockStack gap="050">
                    <Text variant="headingSm" as="h3">Pick the winner</Text>
                    <Text variant="bodySm" as="p" tone="subdued">
                      Once results are statistically significant, conclude the test and the winning image is set permanently.
                    </Text>
                  </BlockStack>
                </InlineStack>
              </BlockStack>
              <Divider />
              <BlockStack gap="300">
                <Text variant="headingSm" as="h3">Common questions</Text>
                <BlockStack gap="200">
                  <Text variant="bodySm" as="p" fontWeight="semibold">How does tracking work?</Text>
                  <Text variant="bodySm" as="p" tone="subdued">
                    The Opal pixel runs in Shopify's sandboxed web pixel environment. It captures product views,
                    add-to-carts, and checkout conversions — no personal customer data is collected.
                  </Text>
                </BlockStack>
                <BlockStack gap="200">
                  <Text variant="bodySm" as="p" fontWeight="semibold">How many visitors do I need?</Text>
                  <Text variant="bodySm" as="p" tone="subdued">
                    A good A/B test typically needs 200+ views per variant to reach statistical significance.
                    For products with lower traffic, tests may need to run longer.
                  </Text>
                </BlockStack>
                <BlockStack gap="200">
                  <Text variant="bodySm" as="p" fontWeight="semibold">How long should I run a test?</Text>
                  <Text variant="bodySm" as="p" tone="subdued">
                    Run until Opal tells you the results are statistically significant. This usually takes
                    1-4 weeks depending on your traffic. Don't end tests early — you might pick the wrong winner.
                  </Text>
                </BlockStack>
              </BlockStack>
              <Divider />
              <Text variant="bodySm" as="p" tone="subdued">
                Need help?{" "}
                <a href="https://opaloptics.com/support" target="_blank" rel="noopener noreferrer">
                  Contact support
                </a>
              </Text>
            </BlockStack>
          </Card>
        </Layout.Section>

        {/* Pixel Configuration */}
        <Layout.Section>
          <Card>
            <BlockStack gap="400">
              <InlineStack align="space-between" blockAlign="center">
                <Text variant="headingMd" as="h2">
                  Pixel tracking
                </Text>
                <Badge tone={currentPixelStatus === "configured" ? "success" : "warning"}>
                  {currentPixelStatus === "configured" ? "Configured" : "Not configured"}
                </Badge>
              </InlineStack>
              <Text variant="bodySm" as="p" tone="subdued">
                The Opal pixel automatically tracks product views, add-to-carts,
                and conversions on your storefront. Configure the pixel below to
                enable automatic A/B test tracking.
              </Text>
              <Divider />

              {/* Auto-configure button */}
              <BlockStack gap="300">
                <Text variant="headingSm" as="h3">Auto-configure</Text>
                <Text variant="bodySm" as="p" tone="subdued">
                  Automatically set up the web pixel with the correct API URL and pixel key.
                  This creates or updates the pixel extension in your Shopify store.
                </Text>
                <Box>
                  <Button
                    variant="primary"
                    onClick={handleConfigurePixel}
                    loading={isConfiguring}
                    disabled={!pixelKey}
                  >
                    {currentPixelStatus === "configured" ? "Reconfigure Pixel" : "Configure Pixel"}
                  </Button>
                </Box>
              </BlockStack>

              <Divider />

              <BlockStack gap="300">
                <Text variant="headingSm" as="h3">API URL</Text>
                <TextField
                  label=""
                  labelHidden
                  value={opalApiUrl}
                  readOnly
                  autoComplete="off"
                  helpText="The Opal API endpoint used by the pixel for tracking events."
                />
              </BlockStack>

              <BlockStack gap="300">
                <Text variant="headingSm" as="h3">Pixel key</Text>
                {pixelKey ? (
                  <InlineStack gap="200" blockAlign="end">
                    <Box minWidth="300px">
                      <TextField
                        label=""
                        labelHidden
                        value={showKey ? pixelKey : "\u2022".repeat(32)}
                        readOnly
                        autoComplete="off"
                      />
                    </Box>
                    <Button onClick={() => setShowKey(!showKey)} size="slim">
                      {showKey ? "Hide" : "Show"}
                    </Button>
                    <Button onClick={handleCopy} size="slim">
                      {copied ? "Copied!" : "Copy"}
                    </Button>
                  </InlineStack>
                ) : (
                  <Banner tone="warning">
                    Pixel key not available. Create an A/B test to generate one.
                  </Banner>
                )}
                <Text variant="bodySm" as="p" tone="subdued">
                  This key authenticates the pixel's tracking events.
                  Keep it private — do not share it publicly.
                </Text>
              </BlockStack>
            </BlockStack>
          </Card>
        </Layout.Section>

        {/* Setup Instructions */}
        <Layout.Section>
          <Card>
            <BlockStack gap="400">
              <Text variant="headingMd" as="h2">
                Setup instructions
              </Text>
              <BlockStack gap="200">
                <Text variant="bodyMd" as="p">
                  <strong>1.</strong> Click "Configure Pixel" above to automatically set up the web pixel with your credentials.
                </Text>
                <Text variant="bodyMd" as="p">
                  <strong>2.</strong> Go to your Shopify Admin {"\u2192"} Settings {"\u2192"} Customer events to verify
                  the pixel is active.
                </Text>
                <Text variant="bodyMd" as="p">
                  <strong>3.</strong> Create an A/B test from the Tests page — the pixel will automatically
                  track views, add-to-carts, and conversions for tested products.
                </Text>
              </BlockStack>
            </BlockStack>
          </Card>
        </Layout.Section>

        {/* Google Analytics (Unlimited tier only) */}
        <Layout.Section>
          <Card>
            <BlockStack gap="400">
              <InlineStack align="space-between" blockAlign="center">
                <Text variant="headingMd" as="h2">
                  Google Analytics
                </Text>
                {tier === "unlimited" ? (
                  <Badge tone={gaConfigured || (actionData && "gaAction" in actionData && actionData.gaAction === "saved") ? "success" : "info"}>
                    {gaConfigured || (actionData && "gaAction" in actionData && actionData.gaAction === "saved") ? "Connected" : "Not connected"}
                  </Badge>
                ) : (
                  <Badge tone="warning">Unlimited plan</Badge>
                )}
              </InlineStack>

              {tier !== "unlimited" ? (
                <Banner tone="info">
                  Upgrade to the Unlimited plan to relay A/B test events to your Google Analytics 4 property.
                  This lets you analyze test performance alongside your other store analytics.
                </Banner>
              ) : (
                <BlockStack gap="300">
                  <Text variant="bodySm" as="p" tone="subdued">
                    Connect your GA4 property to automatically relay A/B test events
                    (product views, add-to-carts, conversions) to Google Analytics.
                    No personal customer data is sent.
                  </Text>
                  <Divider />
                  <TextField
                    label="Measurement ID"
                    value={gaMid}
                    onChange={setGaMid}
                    autoComplete="off"
                    placeholder="G-XXXXXXXXXX"
                    helpText="Find this in GA4 → Admin → Data Streams → your stream."
                  />
                  <TextField
                    label="API Secret"
                    value={gaSecret}
                    onChange={setGaSecret}
                    autoComplete="off"
                    type="password"
                    placeholder={gaConfigured ? "••••••••  (secret is set, enter new value to update)" : "Enter your Measurement Protocol API secret"}
                    helpText="Create one in GA4 → Admin → Data Streams → Measurement Protocol API secrets."
                  />
                  <InlineStack gap="200">
                    <Button
                      variant="primary"
                      onClick={handleSaveGA}
                      loading={isSavingGA}
                      disabled={!gaMid || (!gaSecret && !gaConfigured)}
                    >
                      {gaConfigured ? "Update" : "Connect"}
                    </Button>
                    {gaConfigured && (
                      <Button
                        tone="critical"
                        onClick={handleClearGA}
                        disabled={isSavingGA}
                      >
                        Disconnect
                      </Button>
                    )}
                  </InlineStack>
                </BlockStack>
              )}
            </BlockStack>
          </Card>
        </Layout.Section>

        {/* Integration Info */}
        <Layout.Section>
          <Card>
            <BlockStack gap="200">
              <Text variant="headingSm" as="h3">Integration details</Text>
              <Divider />
              <InlineStack gap="800">
                <BlockStack gap="100">
                  <Text variant="bodySm" as="span" tone="subdued">Shop</Text>
                  <Text variant="bodyMd" as="span">{shopDomain}</Text>
                </BlockStack>
                <BlockStack gap="100">
                  <Text variant="bodySm" as="span" tone="subdued">Integration ID</Text>
                  <Text variant="bodySm" as="span" tone="subdued">{integrationId}</Text>
                </BlockStack>
              </InlineStack>
            </BlockStack>
          </Card>
        </Layout.Section>
      </Layout>
    </Page>
  );
}
