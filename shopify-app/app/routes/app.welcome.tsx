/**
 * Welcome / onboarding wizard — shown on first visit (no tests, pixel not configured).
 * 3-step flow: Welcome → Configure pixel → Create first test
 */
import type { LoaderFunctionArgs, ActionFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { useLoaderData, useActionData, useNavigate, useNavigation, useSubmit } from "@remix-run/react";
import {
  Page,
  Layout,
  Card,
  BlockStack,
  InlineStack,
  Text,
  Button,
  Banner,
  Divider,
  Box,
  Badge,
  List,
} from "@shopify/polaris";
import { useState, useCallback, useEffect } from "react";

import { authenticate } from "~/shopify.server";
import { getIntegrationByShop, ensurePixelKey } from "~/lib/opal-api.server";
import { OpalLogo } from "~/components/OpalLogo";

const OPAL_API_URL = process.env.OPAL_API_URL || "https://dev.opaloptics.com";

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const { session, admin } = await authenticate.admin(request);
  const shopDomain = session.shop;

  const integration = await getIntegrationByShop(shopDomain);

  let pixelConfigured = false;
  let pixelKey: string | null = null;

  if (integration) {
    pixelKey = integration.pixel_key;
    if (!pixelKey) {
      try {
        pixelKey = await ensurePixelKey(integration.id);
      } catch {
        // ignore
      }
    }

    // Check if pixel is configured
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
          pixelConfigured = !!(s.opal_api_url && s.opal_pixel_key);
        } catch {
          // ignore
        }
      }
    } catch {
      // ignore
    }
  }

  return json({
    hasIntegration: !!integration,
    integrationId: integration?.id || null,
    pixelConfigured,
    pixelKey,
    shopDomain,
    opalApiUrl: OPAL_API_URL,
  });
};

export const action = async ({ request }: ActionFunctionArgs) => {
  const { session, admin } = await authenticate.admin(request);
  const shopDomain = session.shop;

  const integration = await getIntegrationByShop(shopDomain);
  if (!integration) {
    return json({ ok: false, error: "Store not connected." }, { status: 400 });
  }

  let pixelKey: string;
  try {
    pixelKey = await ensurePixelKey(integration.id);
  } catch (err) {
    return json({ ok: false, error: `Failed to get pixel key: ${err instanceof Error ? err.message : "Unknown"}` }, { status: 500 });
  }

  const pixelSettings = JSON.stringify({
    opal_api_url: OPAL_API_URL,
    opal_pixel_key: pixelKey,
  });

  // Try create, then update if already exists
  try {
    const createResponse = await admin.graphql(
      `#graphql
      mutation webPixelCreate($webPixel: WebPixelInput!) {
        webPixelCreate(webPixel: $webPixel) {
          userErrors { code field message }
          webPixel { id }
        }
      }`,
      { variables: { webPixel: { settings: pixelSettings } } },
    );
    const createBody = await createResponse.json();
    const createErrors = createBody.data?.webPixelCreate?.userErrors || [];

    if (createErrors.length === 0) {
      return json({ ok: true });
    }

    const alreadyExists = createErrors.some(
      (e: { code?: string; message: string }) =>
        e.message.toLowerCase().includes("already exists") || e.code === "WEB_PIXEL_ALREADY_EXISTS",
    );

    if (!alreadyExists) {
      return json({ ok: false, error: createErrors.map((e: { message: string }) => e.message).join(", ") }, { status: 400 });
    }

    // Update existing pixel
    const queryResponse = await admin.graphql(`#graphql query webPixel { webPixel { id } }`);
    const queryBody = await queryResponse.json();
    const pixelId = queryBody.data?.webPixel?.id;

    if (!pixelId) {
      return json({ ok: false, error: "Could not find existing pixel to update." }, { status: 500 });
    }

    const updateResponse = await admin.graphql(
      `#graphql
      mutation webPixelUpdate($id: ID!, $webPixel: WebPixelInput!) {
        webPixelUpdate(id: $id, webPixel: $webPixel) {
          userErrors { field message }
          webPixel { id }
        }
      }`,
      { variables: { id: pixelId, webPixel: { settings: pixelSettings } } },
    );
    const updateBody = await updateResponse.json();
    const updateErrors = updateBody.data?.webPixelUpdate?.userErrors || [];

    if (updateErrors.length > 0) {
      return json({ ok: false, error: updateErrors.map((e: { message: string }) => e.message).join(", ") }, { status: 400 });
    }

    return json({ ok: true });
  } catch (err) {
    return json({ ok: false, error: `Failed to configure pixel: ${err instanceof Error ? err.message : "Unknown"}` }, { status: 500 });
  }
};

export default function Welcome() {
  const { hasIntegration, pixelConfigured, pixelKey } = useLoaderData<typeof loader>();
  const actionData = useActionData<typeof action>();
  const navigate = useNavigate();
  const navigation = useNavigation();
  const submit = useSubmit();

  const [step, setStep] = useState(1);
  const isConfiguring = navigation.state === "submitting";

  // Auto-advance to step 3 after successful pixel config
  useEffect(() => {
    if (actionData?.ok && step === 2) {
      setStep(3);
    }
  }, [actionData, step]);

  const handleConfigurePixel = useCallback(() => {
    const formData = new FormData();
    formData.set("intent", "configure_pixel");
    submit(formData, { method: "post" });
  }, [submit]);

  const stepIndicator = (
    <InlineStack align="center" gap="200">
      {[1, 2, 3].map((s) => (
        <div
          key={s}
          style={{
            width: s === step ? "32px" : "8px",
            height: "8px",
            borderRadius: "4px",
            background: s === step ? "#7c6cf7" : s < step ? "#4dc9f6" : "#e2e8f0",
            transition: "all 0.3s",
          }}
        />
      ))}
    </InlineStack>
  );

  return (
    <Page>
      <Layout>
        <Layout.Section>
          <div style={{ maxWidth: "600px", margin: "0 auto" }}>
            <Card>
              <BlockStack gap="500">
                {/* Step indicator */}
                <Box>{stepIndicator}</Box>

                {/* Step 1: Welcome */}
                {step === 1 && (
                  <BlockStack gap="400">
                    <div style={{ textAlign: "center", padding: "1rem 0" }}>
                      <OpalLogo size={80} />
                    </div>
                    <Text variant="headingXl" as="h1" alignment="center">
                      Welcome to Opal A/B
                    </Text>
                    <Text variant="bodyMd" as="p" alignment="center" tone="subdued">
                      Find out which product images drive more sales with
                      automated A/B testing. No code required.
                    </Text>
                    <Divider />
                    <BlockStack gap="300">
                      <InlineStack gap="300" blockAlign="start">
                        <div style={{ width: "32px", height: "32px", borderRadius: "50%", background: "#ede9fe", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                          <span style={{ fontSize: "14px", fontWeight: 700, color: "#7c6cf7" }}>1</span>
                        </div>
                        <BlockStack gap="100">
                          <Text variant="headingSm" as="h3">Automatic pixel tracking</Text>
                          <Text variant="bodySm" as="p" tone="subdued">
                            Our pixel tracks product views, add-to-carts, and conversions
                            automatically on your storefront. No manual data entry.
                          </Text>
                        </BlockStack>
                      </InlineStack>

                      <InlineStack gap="300" blockAlign="start">
                        <div style={{ width: "32px", height: "32px", borderRadius: "50%", background: "#ede9fe", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                          <span style={{ fontSize: "14px", fontWeight: 700, color: "#7c6cf7" }}>2</span>
                        </div>
                        <BlockStack gap="100">
                          <Text variant="headingSm" as="h3">Statistical significance</Text>
                          <Text variant="bodySm" as="p" tone="subdued">
                            Opal calculates when your results are statistically significant,
                            so you can be confident in your winner.
                          </Text>
                        </BlockStack>
                      </InlineStack>

                      <InlineStack gap="300" blockAlign="start">
                        <div style={{ width: "32px", height: "32px", borderRadius: "50%", background: "#ede9fe", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                          <span style={{ fontSize: "14px", fontWeight: 700, color: "#7c6cf7" }}>3</span>
                        </div>
                        <BlockStack gap="100">
                          <Text variant="headingSm" as="h3">Pick the winner</Text>
                          <Text variant="bodySm" as="p" tone="subdued">
                            When the test is done, pick the winning image and it's
                            automatically pushed to your storefront.
                          </Text>
                        </BlockStack>
                      </InlineStack>
                    </BlockStack>
                    <Divider />
                    <InlineStack align="end">
                      <Button variant="primary" onClick={() => setStep(2)}>
                        Get started
                      </Button>
                    </InlineStack>
                  </BlockStack>
                )}

                {/* Step 2: Configure pixel */}
                {step === 2 && (
                  <BlockStack gap="400">
                    <Text variant="headingLg" as="h2" alignment="center">
                      Set up automatic tracking
                    </Text>
                    <Text variant="bodyMd" as="p" alignment="center" tone="subdued">
                      The Opal pixel runs in Shopify's sandboxed environment and
                      automatically tracks how your product images perform.
                      No personal customer data is collected.
                    </Text>

                    {/* Pixel config result */}
                    {actionData && !actionData.ok && (
                      <Banner tone="critical">
                        {"error" in actionData ? String(actionData.error) : "Failed to configure pixel."}
                      </Banner>
                    )}

                    {pixelConfigured ? (
                      <Banner tone="success">
                        Pixel is already configured. You're all set!
                      </Banner>
                    ) : !hasIntegration ? (
                      <Banner tone="warning">
                        Store integration is being set up. This usually takes a few seconds.
                        Go back and try again.
                      </Banner>
                    ) : (
                      <BlockStack gap="300">
                        <Text variant="bodySm" as="p" tone="subdued">
                          What the pixel tracks:
                        </Text>
                        <List type="bullet">
                          <List.Item>Product page views</List.Item>
                          <List.Item>Add-to-cart events</List.Item>
                          <List.Item>Checkout conversions with revenue</List.Item>
                        </List>
                      </BlockStack>
                    )}

                    <Divider />
                    <InlineStack align="space-between">
                      <Button onClick={() => setStep(3)} variant="plain">
                        Skip for now
                      </Button>
                      <InlineStack gap="200">
                        <Button onClick={() => setStep(1)}>Back</Button>
                        {pixelConfigured ? (
                          <Button variant="primary" onClick={() => setStep(3)}>
                            Continue
                          </Button>
                        ) : (
                          <Button
                            variant="primary"
                            onClick={handleConfigurePixel}
                            loading={isConfiguring}
                            disabled={!pixelKey}
                          >
                            Configure pixel
                          </Button>
                        )}
                      </InlineStack>
                    </InlineStack>
                  </BlockStack>
                )}

                {/* Step 3: Create first test */}
                {step === 3 && (
                  <BlockStack gap="400">
                    <div style={{ textAlign: "center", padding: "0.5rem 0" }}>
                      <OpalLogo size={48} />
                    </div>
                    <Text variant="headingLg" as="h2" alignment="center">
                      You're ready to go!
                    </Text>
                    <Text variant="bodyMd" as="p" alignment="center" tone="subdued">
                      Create your first A/B test to find out which product images
                      drive more sales.
                    </Text>
                    <Divider />
                    <BlockStack gap="200">
                      <Text variant="headingSm" as="h3">How it works:</Text>
                      <List type="number">
                        <List.Item>Pick a product from your store</List.Item>
                        <List.Item>Select two images to compare (A vs B)</List.Item>
                        <List.Item>Start the test — Opal pushes Variant A to your storefront</List.Item>
                        <List.Item>Watch the metrics roll in — views, add-to-carts, conversions</List.Item>
                        <List.Item>When significant, pick the winner</List.Item>
                      </List>
                    </BlockStack>

                    {actionData?.ok && (
                      <Banner tone="success">
                        Pixel configured successfully! Tracking is ready.
                      </Banner>
                    )}

                    <Divider />
                    <InlineStack align="space-between">
                      <Button onClick={() => navigate("/app")} variant="plain">
                        Go to dashboard
                      </Button>
                      <Button
                        variant="primary"
                        onClick={() => navigate("/app/tests/new")}
                      >
                        Create your first test
                      </Button>
                    </InlineStack>
                  </BlockStack>
                )}
              </BlockStack>
            </Card>

            {/* Opal platform cross-sell */}
            <div style={{ marginTop: "1rem" }}>
              <Card>
                <InlineStack gap="300" blockAlign="center">
                  <OpalLogo size={28} />
                  <BlockStack gap="050">
                    <Text variant="bodySm" as="p" fontWeight="semibold">
                      Need better product images?
                    </Text>
                    <Text variant="bodySm" as="p" tone="subdued">
                      Generate studio-quality photos with AI on{" "}
                      <a href="https://opaloptics.com" target="_blank" rel="noopener noreferrer">
                        opaloptics.com
                      </a>
                    </Text>
                  </BlockStack>
                </InlineStack>
              </Card>
            </div>
          </div>
        </Layout.Section>
      </Layout>
    </Page>
  );
}
