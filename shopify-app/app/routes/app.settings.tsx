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
import { getIntegrationByShop, ensurePixelKey } from "~/lib/opal-api.server";

const OPAL_API_URL = process.env.OPAL_API_URL || "https://dev.opaloptics.com";

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const { session, admin } = await authenticate.admin(request);
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

  return json({
    hasIntegration: true,
    pixelKey,
    integrationId: integration.id,
    shopDomain,
    opalApiUrl: OPAL_API_URL,
    pixelStatus,
  });
};

export const action = async ({ request }: ActionFunctionArgs) => {
  const { session, admin } = await authenticate.admin(request);
  const shopDomain = session.shop;
  const formData = await request.formData();
  const intent = formData.get("intent");

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
  const { hasIntegration, pixelKey, integrationId, shopDomain, opalApiUrl, pixelStatus } =
    useLoaderData<typeof loader>();
  const actionData = useActionData<typeof action>();
  const navigate = useNavigate();
  const navigation = useNavigation();
  const submit = useSubmit();

  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showBanner, setShowBanner] = useState(false);

  const isConfiguring = navigation.state === "submitting" &&
    navigation.formData?.get("intent") === "configure_pixel";

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

  if (!hasIntegration) {
    return (
      <Page title="Settings" backAction={{ onAction: () => navigate("/app") }}>
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
    <Page title="Settings" backAction={{ onAction: () => navigate("/app") }}>
      <Layout>
        {/* Action feedback banner */}
        {showBanner && actionData && (
          <Layout.Section>
            {actionData.ok ? (
              <Banner
                tone="success"
                onDismiss={() => setShowBanner(false)}
              >
                Pixel {"action" in actionData && actionData.action === "created" ? "created" : "updated"} successfully.
                Your storefront is now tracking A/B test events automatically.
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
