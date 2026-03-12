/**
 * Create Test — select product, pick image variants, start test.
 *
 * Flow:
 * 1. Merchant picks a product via Shopify Resource Picker
 * 2. Product images are displayed
 * 3. Merchant selects variant A and variant B images
 * 4. Preview side-by-side
 * 5. Click "Start Test" → creates + starts test via Opal API
 */
import type { ActionFunctionArgs, LoaderFunctionArgs } from "@remix-run/node";
import { json, redirect } from "@remix-run/node";
import {
  useActionData,
  useLoaderData,
  useNavigation,
  useSubmit,
  Form,
} from "@remix-run/react";
import {
  Page,
  Layout,
  Card,
  Button,
  BlockStack,
  InlineStack,
  Text,
  Banner,
  TextField,
  Thumbnail,
  InlineGrid,
  Box,
  Divider,
} from "@shopify/polaris";
import { useCallback, useState } from "react";

import { authenticate } from "~/shopify.server";
import {
  getIntegrationByShop,
  createTest,
  startTest,
} from "~/lib/opal-api.server";

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const { session } = await authenticate.admin(request);
  const integration = await getIntegrationByShop(session.shop);

  if (!integration) {
    return redirect("/app");
  }

  return json({ integrationId: integration.id });
};

export const action = async ({ request }: ActionFunctionArgs) => {
  const { session } = await authenticate.admin(request);
  const formData = await request.formData();

  const integrationId = formData.get("integration_id") as string;
  const productId = formData.get("product_id") as string;
  const productTitle = formData.get("product_title") as string;
  const variantAJobItemId = formData.get("variant_a_job_item_id") as string;
  const variantBJobItemId = formData.get("variant_b_job_item_id") as string;
  const variantALabel = (formData.get("variant_a_label") as string) || "Variant A";
  const variantBLabel = (formData.get("variant_b_label") as string) || "Variant B";
  const originalImageId = formData.get("original_image_id") as string | null;
  const autoStart = formData.get("auto_start") === "true";

  if (!integrationId || !productId || !variantAJobItemId || !variantBJobItemId) {
    return json(
      { error: "Missing required fields. Select a product and both image variants." },
      { status: 400 },
    );
  }

  try {
    const test = await createTest({
      integration_id: integrationId,
      product_id: productId,
      product_title: productTitle,
      variant_a_job_item_id: variantAJobItemId,
      variant_b_job_item_id: variantBJobItemId,
      variant_a_label: variantALabel,
      variant_b_label: variantBLabel,
      original_image_id: originalImageId || undefined,
    });

    if (autoStart) {
      await startTest(test.id);
    }

    return redirect(`/app/tests/${test.id}`);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to create test";
    return json({ error: message }, { status: 500 });
  }
};

export default function CreateTest() {
  const { integrationId } = useLoaderData<typeof loader>();
  const actionData = useActionData<typeof action>();
  const navigation = useNavigation();
  const submit = useSubmit();

  const isSubmitting = navigation.state === "submitting";

  // Product selection state
  const [selectedProduct, setSelectedProduct] = useState<{
    id: string;
    title: string;
    images: Array<{ id: string; url: string; alt?: string }>;
  } | null>(null);

  // Variant selection
  const [variantAJobItemId, setVariantAJobItemId] = useState("");
  const [variantBJobItemId, setVariantBJobItemId] = useState("");
  const [variantALabel, setVariantALabel] = useState("Variant A");
  const [variantBLabel, setVariantBLabel] = useState("Variant B");

  const handleProductPicker = useCallback(async () => {
    // In a real Shopify embedded app, this uses the Resource Picker:
    // const selected = await shopify.resourcePicker({ type: "product" });
    // For now, we show a placeholder — the Resource Picker only works
    // when running inside Shopify Admin via `shopify app dev`.
    //
    // This will be connected when testing on a dev store.
  }, []);

  const handleSubmit = useCallback(() => {
    if (!selectedProduct) return;

    const formData = new FormData();
    formData.set("integration_id", integrationId);
    formData.set("product_id", selectedProduct.id);
    formData.set("product_title", selectedProduct.title);
    formData.set("variant_a_job_item_id", variantAJobItemId);
    formData.set("variant_b_job_item_id", variantBJobItemId);
    formData.set("variant_a_label", variantALabel);
    formData.set("variant_b_label", variantBLabel);
    formData.set("auto_start", "true");

    submit(formData, { method: "post" });
  }, [
    integrationId,
    selectedProduct,
    variantAJobItemId,
    variantBJobItemId,
    variantALabel,
    variantBLabel,
    submit,
  ]);

  return (
    <Page
      title="Create A/B Test"
      backAction={{ url: "/app" }}
    >
      <Layout>
        {actionData?.error && (
          <Layout.Section>
            <Banner tone="critical">{actionData.error}</Banner>
          </Layout.Section>
        )}

        {/* Step 1: Select Product */}
        <Layout.Section>
          <Card>
            <BlockStack gap="400">
              <Text variant="headingMd" as="h2">
                1. Select product
              </Text>
              {selectedProduct ? (
                <InlineStack gap="400" align="start" blockAlign="center">
                  {selectedProduct.images[0] && (
                    <Thumbnail
                      source={selectedProduct.images[0].url}
                      alt={selectedProduct.title}
                      size="large"
                    />
                  )}
                  <BlockStack gap="100">
                    <Text variant="bodyMd" fontWeight="bold" as="span">
                      {selectedProduct.title}
                    </Text>
                    <Text variant="bodySm" as="span" tone="subdued">
                      {selectedProduct.images.length} image(s)
                    </Text>
                    <Button onClick={handleProductPicker} size="slim">
                      Change product
                    </Button>
                  </BlockStack>
                </InlineStack>
              ) : (
                <Button onClick={handleProductPicker} variant="primary">
                  Select product
                </Button>
              )}
              <Text variant="bodySm" as="p" tone="subdued">
                Choose the product you want to test different images for.
                Images should already be processed in Opal.
              </Text>
            </BlockStack>
          </Card>
        </Layout.Section>

        {/* Step 2: Configure Variants */}
        <Layout.Section>
          <Card>
            <BlockStack gap="400">
              <Text variant="headingMd" as="h2">
                2. Configure variants
              </Text>
              <Text variant="bodySm" as="p" tone="subdued">
                Enter the Opal job item IDs for each image variant.
                These are the processed images from your Opal dashboard.
              </Text>
              <InlineGrid columns={2} gap="400">
                <BlockStack gap="300">
                  <TextField
                    label="Variant A label"
                    value={variantALabel}
                    onChange={setVariantALabel}
                    autoComplete="off"
                  />
                  <TextField
                    label="Variant A job item ID"
                    value={variantAJobItemId}
                    onChange={setVariantAJobItemId}
                    placeholder="ji_abc123..."
                    autoComplete="off"
                  />
                </BlockStack>
                <BlockStack gap="300">
                  <TextField
                    label="Variant B label"
                    value={variantBLabel}
                    onChange={setVariantBLabel}
                    autoComplete="off"
                  />
                  <TextField
                    label="Variant B job item ID"
                    value={variantBJobItemId}
                    onChange={setVariantBJobItemId}
                    placeholder="ji_def456..."
                    autoComplete="off"
                  />
                </BlockStack>
              </InlineGrid>
            </BlockStack>
          </Card>
        </Layout.Section>

        {/* Step 3: Preview & Start */}
        <Layout.Section>
          <Card>
            <BlockStack gap="400">
              <Text variant="headingMd" as="h2">
                3. Start test
              </Text>
              <Text variant="bodySm" as="p" tone="subdued">
                Starting the test will push Variant A to your storefront and
                begin tracking views, add-to-carts, and conversions
                automatically via the Opal pixel.
              </Text>
              <Divider />
              <InlineStack align="end" gap="300">
                <Button url="/app">Cancel</Button>
                <Button
                  variant="primary"
                  onClick={handleSubmit}
                  loading={isSubmitting}
                  disabled={!selectedProduct || !variantAJobItemId || !variantBJobItemId}
                >
                  Create &amp; start test
                </Button>
              </InlineStack>
            </BlockStack>
          </Card>
        </Layout.Section>
      </Layout>
    </Page>
  );
}
