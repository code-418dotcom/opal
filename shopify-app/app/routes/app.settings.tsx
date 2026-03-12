/**
 * Settings — pixel key display, auto-conclude config.
 */
import type { LoaderFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { useLoaderData } from "@remix-run/react";
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
} from "@shopify/polaris";
import { useCallback, useState } from "react";

import { authenticate } from "~/shopify.server";
import { getIntegrationByShop, ensurePixelKey } from "~/lib/opal-api.server";

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const { session } = await authenticate.admin(request);
  const shopDomain = session.shop;

  const integration = await getIntegrationByShop(shopDomain);
  if (!integration) {
    return json({
      hasIntegration: false,
      pixelKey: null,
      integrationId: null,
      shopDomain,
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

  return json({
    hasIntegration: true,
    pixelKey,
    integrationId: integration.id,
    shopDomain,
  });
};

export default function Settings() {
  const { hasIntegration, pixelKey, integrationId, shopDomain } =
    useLoaderData<typeof loader>();
  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    if (pixelKey) {
      navigator.clipboard.writeText(pixelKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [pixelKey]);

  if (!hasIntegration) {
    return (
      <Page title="Settings" backAction={{ url: "/app" }}>
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

  const opalApiUrl = typeof window !== "undefined"
    ? ""
    : (process.env.OPAL_API_URL || "https://dev.opaloptics.com");

  return (
    <Page title="Settings" backAction={{ url: "/app" }}>
      <Layout>
        {/* Pixel Configuration */}
        <Layout.Section>
          <Card>
            <BlockStack gap="400">
              <Text variant="headingMd" as="h2">
                Pixel tracking
              </Text>
              <Text variant="bodySm" as="p" tone="subdued">
                The Opal pixel automatically tracks product views, add-to-carts,
                and conversions on your storefront. These settings are used by
                the Web Pixel extension.
              </Text>
              <Divider />

              <BlockStack gap="300">
                <Text variant="headingSm" as="h3">API URL</Text>
                <TextField
                  label=""
                  labelHidden
                  value={opalApiUrl}
                  readOnly
                  autoComplete="off"
                  helpText="Enter this value in the Web Pixel extension settings in your theme editor."
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
                  <strong>1.</strong> Go to your Shopify Admin {"\u2192"} Online Store {"\u2192"} Themes {"\u2192"} Customize
                </Text>
                <Text variant="bodyMd" as="p">
                  <strong>2.</strong> Click App embeds in the left sidebar
                </Text>
                <Text variant="bodyMd" as="p">
                  <strong>3.</strong> Enable "Opal A/B Testing"
                </Text>
                <Text variant="bodyMd" as="p">
                  <strong>4.</strong> The Web Pixel settings (API URL and Pixel Key) are configured
                  in the pixel extension settings. Go to Settings {"\u2192"} Customer events to verify
                  the pixel is active.
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
