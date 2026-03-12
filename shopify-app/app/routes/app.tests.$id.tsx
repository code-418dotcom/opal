/**
 * Test Detail — live metrics, significance gauge, swap/conclude controls.
 *
 * Shows side-by-side variant comparison with:
 * - Views, ATC, conversions, revenue per variant
 * - Conversion rate + lift percentage
 * - Statistical significance progress bar
 * - Action buttons: Swap, Conclude, Cancel
 */
import type { ActionFunctionArgs, LoaderFunctionArgs } from "@remix-run/node";
import { json, redirect } from "@remix-run/node";
import {
  useActionData,
  useLoaderData,
  useNavigation,
  useSubmit,
  useRevalidator,
} from "@remix-run/react";
import {
  Page,
  Layout,
  Card,
  Badge,
  Text,
  BlockStack,
  InlineStack,
  InlineGrid,
  Button,
  Banner,
  Divider,
  ProgressBar,
  Box,
  Modal,
} from "@shopify/polaris";
import { useCallback, useEffect, useState } from "react";

import { authenticate } from "~/shopify.server";
import {
  getTest,
  swapVariant,
  concludeTest,
  cancelTest,
} from "~/lib/opal-api.server";
import type { ABTest, VariantMetrics, Significance } from "~/lib/opal-api.server";
import { SignificanceGauge } from "~/components/SignificanceGauge";
import { VariantCard } from "~/components/VariantCard";

export const loader = async ({ params, request }: LoaderFunctionArgs) => {
  await authenticate.admin(request);
  const testId = params.id!;

  try {
    const test = await getTest(testId);
    return json({ test });
  } catch {
    throw new Response("Test not found", { status: 404 });
  }
};

export const action = async ({ params, request }: ActionFunctionArgs) => {
  await authenticate.admin(request);
  const testId = params.id!;
  const formData = await request.formData();
  const intent = formData.get("intent") as string;

  try {
    switch (intent) {
      case "swap":
        await swapVariant(testId);
        return json({ success: "Variant swapped successfully." });

      case "conclude": {
        const winner = formData.get("winner") as "a" | "b";
        if (!winner) return json({ error: "Select a winner." }, { status: 400 });
        await concludeTest(testId, winner);
        return json({ success: `Test concluded. Winner: Variant ${winner.toUpperCase()}.` });
      }

      case "cancel":
        await cancelTest(testId);
        return json({ success: "Test canceled." });

      default:
        return json({ error: "Unknown action." }, { status: 400 });
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : "Action failed";
    return json({ error: message }, { status: 500 });
  }
};

const STATUS_BADGE: Record<string, { tone: "success" | "info" | "attention" | "critical" | undefined; label: string }> = {
  created: { tone: "info", label: "Draft" },
  running: { tone: "success", label: "Running" },
  concluded: { tone: undefined, label: "Concluded" },
  canceled: { tone: "critical", label: "Canceled" },
};

export default function TestDetail() {
  const { test } = useLoaderData<typeof loader>();
  const actionData = useActionData<typeof action>();
  const navigation = useNavigation();
  const submit = useSubmit();
  const revalidator = useRevalidator();

  const isActing = navigation.state === "submitting";
  const [showConcludeModal, setShowConcludeModal] = useState(false);
  const [showCancelModal, setShowCancelModal] = useState(false);

  // Auto-refresh metrics every 30s while test is running
  useEffect(() => {
    if (test.status !== "running") return;
    const interval = setInterval(() => {
      revalidator.revalidate();
    }, 30_000);
    return () => clearInterval(interval);
  }, [test.status, revalidator]);

  const metricsA: VariantMetrics = test.metrics?.a || {
    views: 0, clicks: 0, add_to_carts: 0, conversions: 0, revenue_cents: 0,
  };
  const metricsB: VariantMetrics = test.metrics?.b || {
    views: 0, clicks: 0, add_to_carts: 0, conversions: 0, revenue_cents: 0,
  };
  const significance: Significance | undefined = test.significance;

  const badge = STATUS_BADGE[test.status] || { tone: undefined, label: test.status };
  const isRunning = test.status === "running";
  const isConcluded = test.status === "concluded";

  const daysSinceStart = test.started_at
    ? Math.ceil((Date.now() - new Date(test.started_at).getTime()) / 86_400_000)
    : 0;

  const handleSwap = useCallback(() => {
    const formData = new FormData();
    formData.set("intent", "swap");
    submit(formData, { method: "post" });
  }, [submit]);

  const handleConclude = useCallback(
    (winner: "a" | "b") => {
      const formData = new FormData();
      formData.set("intent", "conclude");
      formData.set("winner", winner);
      submit(formData, { method: "post" });
      setShowConcludeModal(false);
    },
    [submit],
  );

  const handleCancel = useCallback(() => {
    const formData = new FormData();
    formData.set("intent", "cancel");
    submit(formData, { method: "post" });
    setShowCancelModal(false);
  }, [submit]);

  return (
    <Page
      title={test.product_title || `Product ${test.product_id}`}
      titleMetadata={<Badge tone={badge.tone}>{badge.label}</Badge>}
      subtitle={
        test.started_at
          ? `Started ${new Date(test.started_at).toLocaleDateString()} \u00B7 Day ${daysSinceStart}`
          : "Not started"
      }
      backAction={{ url: "/app" }}
    >
      <Layout>
        {/* Feedback banners */}
        {actionData && "success" in actionData && (
          <Layout.Section>
            <Banner tone="success">{actionData.success}</Banner>
          </Layout.Section>
        )}
        {actionData && "error" in actionData && (
          <Layout.Section>
            <Banner tone="critical">{actionData.error}</Banner>
          </Layout.Section>
        )}

        {/* Winner banner */}
        {isConcluded && test.winner && (
          <Layout.Section>
            <Banner tone="success" title="Test concluded">
              Winner: {test.winner === "a" ? test.variant_a_label : test.variant_b_label}
            </Banner>
          </Layout.Section>
        )}

        {/* Variant comparison */}
        <Layout.Section>
          <InlineGrid columns={2} gap="400">
            <VariantCard
              label={test.variant_a_label}
              variant="a"
              metrics={metricsA}
              isActive={test.active_variant === "a"}
              isWinner={test.winner === "a"}
              otherMetrics={metricsB}
            />
            <VariantCard
              label={test.variant_b_label}
              variant="b"
              metrics={metricsB}
              isActive={test.active_variant === "b"}
              isWinner={test.winner === "b"}
              otherMetrics={metricsA}
            />
          </InlineGrid>
        </Layout.Section>

        {/* Significance gauge */}
        <Layout.Section>
          <SignificanceGauge significance={significance} />
        </Layout.Section>

        {/* Actions */}
        {isRunning && (
          <Layout.Section>
            <Card>
              <InlineStack align="end" gap="300">
                <Button
                  onClick={() => setShowCancelModal(true)}
                  tone="critical"
                  disabled={isActing}
                >
                  Cancel test
                </Button>
                <Button onClick={handleSwap} loading={isActing} disabled={isActing}>
                  Swap variant
                </Button>
                <Button
                  variant="primary"
                  onClick={() => setShowConcludeModal(true)}
                  disabled={isActing}
                >
                  Conclude test
                </Button>
              </InlineStack>
            </Card>
          </Layout.Section>
        )}

        {/* Test info */}
        <Layout.Section>
          <Card>
            <BlockStack gap="200">
              <Text variant="headingSm" as="h3">Test details</Text>
              <Divider />
              <InlineStack gap="800">
                <BlockStack gap="100">
                  <Text variant="bodySm" as="span" tone="subdued">Product ID</Text>
                  <Text variant="bodyMd" as="span">{test.product_id}</Text>
                </BlockStack>
                <BlockStack gap="100">
                  <Text variant="bodySm" as="span" tone="subdued">Tracking</Text>
                  <Text variant="bodyMd" as="span">
                    {test.tracking_mode === "pixel" ? "Automatic (pixel)" : "Manual"}
                  </Text>
                </BlockStack>
                <BlockStack gap="100">
                  <Text variant="bodySm" as="span" tone="subdued">Active variant</Text>
                  <Text variant="bodyMd" as="span">
                    {test.active_variant === "a" ? test.variant_a_label : test.variant_b_label}
                  </Text>
                </BlockStack>
                <BlockStack gap="100">
                  <Text variant="bodySm" as="span" tone="subdued">Test ID</Text>
                  <Text variant="bodySm" as="span" tone="subdued">{test.id}</Text>
                </BlockStack>
              </InlineStack>
            </BlockStack>
          </Card>
        </Layout.Section>
      </Layout>

      {/* Conclude modal */}
      <Modal
        open={showConcludeModal}
        onClose={() => setShowConcludeModal(false)}
        title="Conclude test"
        primaryAction={{
          content: significance?.recommended_winner
            ? `Pick ${significance.recommended_winner === "a" ? test.variant_a_label : test.variant_b_label}`
            : "Pick Variant A",
          onAction: () => handleConclude(significance?.recommended_winner || "a"),
          loading: isActing,
        }}
        secondaryActions={[
          {
            content: "Cancel",
            onAction: () => setShowConcludeModal(false),
          },
        ]}
      >
        <Modal.Section>
          <BlockStack gap="300">
            <Text as="p">
              Concluding the test will set the winning variant as the permanent
              product image on your storefront.
            </Text>
            {significance?.confident ? (
              <Banner tone="success">
                Statistical significance reached. Recommended winner:{" "}
                <strong>
                  {significance.recommended_winner === "a"
                    ? test.variant_a_label
                    : test.variant_b_label}
                </strong>
                {significance.lift_percent !== null &&
                  ` (+${significance.lift_percent}% conversion lift)`}
              </Banner>
            ) : (
              <Banner tone="warning">
                Statistical significance has not been reached yet.
                Concluding now means the result may not be reliable.
              </Banner>
            )}
            <Divider />
            <InlineStack gap="300">
              <Button onClick={() => handleConclude("a")} disabled={isActing}>
                Pick {test.variant_a_label}
              </Button>
              <Button onClick={() => handleConclude("b")} disabled={isActing}>
                Pick {test.variant_b_label}
              </Button>
            </InlineStack>
          </BlockStack>
        </Modal.Section>
      </Modal>

      {/* Cancel modal */}
      <Modal
        open={showCancelModal}
        onClose={() => setShowCancelModal(false)}
        title="Cancel test?"
        primaryAction={{
          content: "Cancel test",
          destructive: true,
          onAction: handleCancel,
          loading: isActing,
        }}
        secondaryActions={[
          {
            content: "Keep running",
            onAction: () => setShowCancelModal(false),
          },
        ]}
      >
        <Modal.Section>
          <Text as="p">
            This will stop the test. The current product image will remain as-is.
            Collected metrics will be preserved.
          </Text>
        </Modal.Section>
      </Modal>
    </Page>
  );
}
