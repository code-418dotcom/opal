/**
 * Create Test — select product, pick image variants, start test.
 *
 * Flow:
 * 1. Merchant picks a product via Shopify Resource Picker
 * 2. Product images are displayed as clickable grid
 * 3. Merchant clicks to select variant A (original) and variant B (challenger)
 * 4. Preview side-by-side
 * 5. Click "Start Test" → creates + starts test via Opal API
 */
import type { ActionFunctionArgs, LoaderFunctionArgs } from "@remix-run/node";
import { json, redirect } from "@remix-run/node";
import {
  useActionData,
  useFetcher,
  useLoaderData,
  useNavigation,
  useSubmit,
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
  DropZone,
} from "@shopify/polaris";
import { useAppBridge } from "@shopify/app-bridge-react";
import { useCallback, useState } from "react";

import { authenticate } from "~/shopify.server";
import {
  getIntegrationByShop,
  createTest,
  startTest,
} from "~/lib/opal-api.server";
import { getEntitlements } from "~/lib/entitlements.server";

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const { session, billing } = await authenticate.admin(request);
  const integration = await getIntegrationByShop(session.shop);

  if (!integration) {
    return redirect("/app");
  }

  const entitlements = await getEntitlements(billing, integration.id);
  if (!entitlements.canCreateTest) {
    return redirect("/app/billing");
  }

  return json({ integrationId: integration.id, autoConcludes: entitlements.autoConcludes });
};

export const action = async ({ request }: ActionFunctionArgs) => {
  const { session, admin } = await authenticate.admin(request);
  const formData = await request.formData();
  const intent = formData.get("intent") as string;

  // ── Fetch product images via Admin GraphQL ──
  if (intent === "fetch_images") {
    const productGid = formData.get("product_gid") as string;
    if (!productGid) {
      return json({ error: "Missing product ID" }, { status: 400 });
    }

    try {
      const response = await admin.graphql(
        `#graphql
        query productImages($id: ID!) {
          product(id: $id) {
            images(first: 50) {
              edges {
                node {
                  id
                  url
                  altText
                  width
                  height
                }
              }
            }
          }
        }`,
        { variables: { id: productGid } },
      );
      const body = await response.json();
      const images = (body.data?.product?.images?.edges || []).map(
        (edge: { node: { id: string; url: string; altText?: string } }) => ({
          id: edge.node.id,
          url: edge.node.url,
          alt: edge.node.altText || "",
        }),
      );
      return json({ images });
    } catch (err) {
      return json({ error: "Failed to fetch product images" }, { status: 500 });
    }
  }

  // ── Create test ──
  const integrationId = formData.get("integration_id") as string;
  const productId = formData.get("product_id") as string;
  const productTitle = formData.get("product_title") as string;
  const variantAImageUrl = formData.get("variant_a_image_url") as string | null;
  const variantBImageUrl = formData.get("variant_b_image_url") as string | null;
  const variantALabel = (formData.get("variant_a_label") as string) || "Original";
  const variantBLabel = (formData.get("variant_b_label") as string) || "Challenger";
  const originalImageId = formData.get("original_image_id") as string | null;
  const autoStart = formData.get("auto_start") === "true";

  if (!integrationId || !productId || !variantAImageUrl || !variantBImageUrl) {
    return json(
      { error: "Select a product and both image variants." },
      { status: 400 },
    );
  }

  try {
    const test = await createTest({
      integration_id: integrationId,
      product_id: productId,
      product_title: productTitle,
      variant_a_image_url: variantAImageUrl,
      variant_b_image_url: variantBImageUrl,
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

interface ProductImage {
  id: string;
  url: string;
  alt?: string;
}

export default function CreateTest() {
  const { integrationId, autoConcludes } = useLoaderData<typeof loader>();
  const actionData = useActionData<typeof action>();
  const navigation = useNavigation();
  const submit = useSubmit();

  const isSubmitting = navigation.state === "submitting";

  // Product selection state
  const [selectedProduct, setSelectedProduct] = useState<{
    id: string;
    gid: string;
    title: string;
    thumbnail: string;
  } | null>(null);

  // Images fetched via Admin API (not from Resource Picker)
  const imageFetcher = useFetcher<{ images?: ProductImage[]; error?: string }>();
  const productImages: ProductImage[] = imageFetcher.data?.images || [];
  const isLoadingImages = imageFetcher.state === "submitting" || imageFetcher.state === "loading";

  // Variant selection — stores the image URL
  const [variantA, setVariantA] = useState<ProductImage | null>(null);
  const [variantB, setVariantB] = useState<ProductImage | null>(null);
  const [variantALabel, setVariantALabel] = useState("Original");
  const [variantBLabel, setVariantBLabel] = useState("Challenger");

  // Which slot is being selected ("a" or "b")
  const [selectingFor, setSelectingFor] = useState<"a" | "b" | null>(null);

  const shopify = useAppBridge();

  const handleProductPicker = useCallback(async () => {
    try {
      const selected = await shopify.resourcePicker({
        type: "product",
        multiple: false,
        action: "select",
      });

      if (selected && selected.length > 0) {
        const product = selected[0];
        const productGid = product.id; // "gid://shopify/Product/123"
        const numericId = productGid.split("/").pop() || productGid;
        const firstImage = product.images?.[0];

        setSelectedProduct({
          id: numericId,
          gid: productGid,
          title: product.title,
          thumbnail: firstImage?.originalSrc || "",
        });

        // Reset variant selections when product changes
        setVariantA(null);
        setVariantB(null);
        setSelectingFor(null);

        // Fetch all images via Admin API
        const fd = new FormData();
        fd.set("intent", "fetch_images");
        fd.set("product_gid", productGid);
        imageFetcher.submit(fd, { method: "post" });
      }
    } catch {
      // User dismissed the picker
    }
  }, [shopify, imageFetcher]);

  const handleImageClick = useCallback(
    (img: ProductImage) => {
      if (selectingFor === "a") {
        setVariantA(img);
        // Auto-advance to selecting B if not set
        if (!variantB) setSelectingFor("b");
        else setSelectingFor(null);
      } else if (selectingFor === "b") {
        setVariantB(img);
        setSelectingFor(null);
      }
    },
    [selectingFor, variantB],
  );

  const handleSubmit = useCallback(() => {
    if (!selectedProduct || !variantA || !variantB) return;

    const formData = new FormData();
    formData.set("integration_id", integrationId);
    formData.set("product_id", selectedProduct.id);
    formData.set("product_title", selectedProduct.title);
    formData.set("variant_a_image_url", variantA.url);
    formData.set("variant_b_image_url", variantB.url);
    formData.set("variant_a_label", variantALabel);
    formData.set("variant_b_label", variantBLabel);
    if (variantA.id) {
      // Extract numeric ID from gid format
      const numericImageId = variantA.id.split("/").pop() || variantA.id;
      formData.set("original_image_id", numericImageId);
    }
    formData.set("auto_start", "true");

    submit(formData, { method: "post" });
  }, [
    integrationId,
    selectedProduct,
    variantA,
    variantB,
    variantALabel,
    variantBLabel,
    submit,
  ]);

  const canStart = selectedProduct && variantA && variantB && variantA.url !== variantB.url;

  return (
    <Page title="Create A/B Test" backAction={{ url: "/app" }}>
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
                  {selectedProduct.thumbnail && (
                    <Thumbnail
                      source={selectedProduct.thumbnail}
                      alt={selectedProduct.title}
                      size="large"
                    />
                  )}
                  <BlockStack gap="100">
                    <Text variant="bodyMd" fontWeight="bold" as="span">
                      {selectedProduct.title}
                    </Text>
                    <Text variant="bodySm" as="span" tone="subdued">
                      {isLoadingImages ? "Loading images..." : `${productImages.length} image(s) available`}
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
            </BlockStack>
          </Card>
        </Layout.Section>

        {/* Step 2: Pick images */}
        {selectedProduct && (
          <Layout.Section>
            <Card>
              <BlockStack gap="400">
                <Text variant="headingMd" as="h2">
                  2. Choose images to test
                </Text>
                <Text variant="bodySm" as="p" tone="subdued">
                  Click an image to assign it as a variant. Select two different
                  images to compare.
                </Text>

                {/* Selection buttons */}
                <InlineStack gap="300">
                  <Button
                    variant={selectingFor === "a" ? "primary" : "plain"}
                    onClick={() => setSelectingFor("a")}
                    size="slim"
                  >
                    {variantA ? `Change ${variantALabel}` : `Select ${variantALabel}`}
                  </Button>
                  <Button
                    variant={selectingFor === "b" ? "primary" : "plain"}
                    onClick={() => setSelectingFor("b")}
                    size="slim"
                  >
                    {variantB ? `Change ${variantBLabel}` : `Select ${variantBLabel}`}
                  </Button>
                </InlineStack>

                {/* Instruction */}
                {selectingFor && (
                  <Banner tone="info">
                    Click an image below to set it as <strong>{selectingFor === "a" ? variantALabel : variantBLabel}</strong>
                  </Banner>
                )}

                {/* Image grid */}
                {isLoadingImages ? (
                  <Text as="p" tone="subdued">Loading product images...</Text>
                ) : productImages.length > 0 ? (
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))",
                      gap: "12px",
                    }}
                  >
                    {productImages.map((img) => {
                      const isA = variantA?.url === img.url;
                      const isB = variantB?.url === img.url;
                      const isSelected = isA || isB;
                      const borderColor = isA
                        ? "#2563eb"
                        : isB
                          ? "#d97706"
                          : selectingFor
                            ? "#ccc"
                            : "transparent";

                      return (
                        <div
                          key={img.id || img.url}
                          onClick={() => selectingFor && handleImageClick(img)}
                          style={{
                            border: `3px solid ${borderColor}`,
                            borderRadius: "8px",
                            overflow: "hidden",
                            cursor: selectingFor ? "pointer" : "default",
                            position: "relative",
                            opacity: selectingFor && !isSelected ? 0.85 : 1,
                            transition: "all 0.15s",
                          }}
                        >
                          <img
                            src={img.url}
                            alt={img.alt || "Product image"}
                            style={{
                              width: "100%",
                              aspectRatio: "1",
                              objectFit: "cover",
                              display: "block",
                            }}
                          />
                          {isSelected && (
                            <div
                              style={{
                                position: "absolute",
                                bottom: 0,
                                left: 0,
                                right: 0,
                                background: isA
                                  ? "rgba(37, 99, 235, 0.9)"
                                  : "rgba(217, 119, 6, 0.9)",
                                color: "white",
                                padding: "4px 8px",
                                fontSize: "11px",
                                fontWeight: 600,
                                textAlign: "center",
                              }}
                            >
                              {isA ? variantALabel : variantBLabel}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <Banner tone="warning">
                    This product has no images. Add images in your Shopify admin first.
                  </Banner>
                )}

                {/* Variant labels */}
                {(variantA || variantB) && (
                  <>
                    <Divider />
                    <InlineGrid columns={2} gap="400">
                      <TextField
                        label="Variant A label"
                        value={variantALabel}
                        onChange={setVariantALabel}
                        autoComplete="off"
                      />
                      <TextField
                        label="Variant B label"
                        value={variantBLabel}
                        onChange={setVariantBLabel}
                        autoComplete="off"
                      />
                    </InlineGrid>
                  </>
                )}
              </BlockStack>
            </Card>
          </Layout.Section>
        )}

        {/* Step 3: Preview & Start */}
        {variantA && variantB && (
          <Layout.Section>
            <Card>
              <BlockStack gap="400">
                <Text variant="headingMd" as="h2">
                  3. Preview & start
                </Text>
                <InlineGrid columns={2} gap="400">
                  <BlockStack gap="200">
                    <Text variant="headingSm" as="h3" alignment="center">
                      {variantALabel}
                    </Text>
                    <div style={{ border: "2px solid #2563eb", borderRadius: "8px", overflow: "hidden" }}>
                      <img
                        src={variantA.url}
                        alt={variantALabel}
                        style={{ width: "100%", display: "block" }}
                      />
                    </div>
                  </BlockStack>
                  <BlockStack gap="200">
                    <Text variant="headingSm" as="h3" alignment="center">
                      {variantBLabel}
                    </Text>
                    <div style={{ border: "2px solid #d97706", borderRadius: "8px", overflow: "hidden" }}>
                      <img
                        src={variantB.url}
                        alt={variantBLabel}
                        style={{ width: "100%", display: "block" }}
                      />
                    </div>
                  </BlockStack>
                </InlineGrid>

                {variantA.url === variantB.url && (
                  <Banner tone="warning">
                    Both variants use the same image. Select two different images to run a meaningful test.
                  </Banner>
                )}

                <Text variant="bodySm" as="p" tone="subdued">
                  Starting the test will push {variantALabel} to your storefront and
                  begin tracking views, add-to-carts, and conversions
                  automatically via the Opal pixel.
                  {autoConcludes
                    ? " The test will auto-conclude when statistical significance is reached."
                    : ""}
                </Text>
                <Divider />
                <InlineStack align="end" gap="300">
                  <Button url="/app">Cancel</Button>
                  <Button
                    variant="primary"
                    onClick={handleSubmit}
                    loading={isSubmitting}
                    disabled={!canStart}
                  >
                    Create & start test
                  </Button>
                </InlineStack>
              </BlockStack>
            </Card>
          </Layout.Section>
        )}
      </Layout>
    </Page>
  );
}
