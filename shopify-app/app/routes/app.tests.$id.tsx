/**
 * Test Detail — live metrics, significance gauge, swap/conclude controls.
 *
 * Shows side-by-side variant comparison with:
 * - Views, ATC, conversions, revenue per variant
 * - Conversion rate + lift percentage
 * - Statistical significance progress bar
 * - Action buttons: Swap, Conclude, Cancel
 * - Free tier limit warnings (views & duration)
 */
import type { ActionFunctionArgs, LoaderFunctionArgs } from "@remix-run/node";
import { json, redirect } from "@remix-run/node";
import {
  useActionData,
  useLoaderData,
  useNavigation,
  useSubmit,
  useRevalidator,
  useNavigate,
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
import { OpalLogo } from "~/components/OpalLogo";
import {
  getTest,
  getIntegrationByShop,
  startTest,
  swapVariant,
  concludeTest,
  cancelTest,
} from "~/lib/opal-api.server";
import type { ABTest, VariantMetrics, Significance } from "~/lib/opal-api.server";
import { getEntitlements } from "~/lib/entitlements.server";
import type { Entitlements } from "~/lib/entitlements.server";
import { SignificanceGauge } from "~/components/SignificanceGauge";
import { VariantCard } from "~/components/VariantCard";

export const loader = async ({ params, request }: LoaderFunctionArgs) => {
  const { session, billing } = await authenticate.admin(request);
  const testId = params.id!;

  try {
    const integration = await getIntegrationByShop(session.shop);
    const [test, entitlements] = await Promise.all([
      getTest(testId),
      getEntitlements(billing, integration?.id || null),
    ]);
    return json({ test, entitlements });
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
      case "start":
        await startTest(testId);
        return json({ success: "Test started. Variant A is now live on your storefront." });

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
        return redirect("/app");

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
  const { test, entitlements } = useLoaderData<typeof loader>();
  const actionData = useActionData<typeof action>();
  const navigation = useNavigation();
  const submit = useSubmit();
  const navigate = useNavigate();
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
  const isDraft = test.status === "created";
  const isRunning = test.status === "running";
  const isConcluded = test.status === "concluded";

  const daysSinceStart = test.started_at
    ? Math.ceil((Date.now() - new Date(test.started_at).getTime()) / 86_400_000)
    : 0;

  // ── Free tier limit calculations ──────────────────────────────────
  const isFree = entitlements.tier === "free";
  const maxDays = entitlements.maxTestDays;
  const viewLimit = entitlements.monthlyViewLimit;
  const viewsUsed = entitlements.monthlyViews;

  const viewPercent = viewLimit ? Math.round((viewsUsed / viewLimit) * 100) : 0;
  const dayPercent = maxDays && daysSinceStart > 0 ? Math.round((daysSinceStart / maxDays) * 100) : 0;

  const viewLimitReached = isFree && viewLimit !== null && viewsUsed >= viewLimit;
  const dayLimitReached = isFree && maxDays !== null && daysSinceStart >= maxDays;
  const trackingPaused = viewLimitReached || dayLimitReached;

  const viewWarning75 = isFree && !viewLimitReached && viewPercent >= 75 && viewPercent < 90;
  const viewWarning90 = isFree && !viewLimitReached && viewPercent >= 90;
  const dayWarning75 = isFree && !dayLimitReached && dayPercent >= 75 && dayPercent < 90;
  const dayWarning90 = isFree && !dayLimitReached && dayPercent >= 90;

  const handleStart = useCallback(() => {
    const formData = new FormData();
    formData.set("intent", "start");
    submit(formData, { method: "post" });
  }, [submit]);

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
      title={<InlineStack gap="200" blockAlign="center"><OpalLogo size={24} /> {test.product_title || `Product ${test.product_id}`}</InlineStack> as any}
      titleMetadata={<Badge tone={badge.tone}>{badge.label}</Badge>}
      subtitle={
        test.started_at
          ? `Started ${new Date(test.started_at).toLocaleDateString()} \u00B7 Day ${daysSinceStart}`
          : "Not started"
      }
      backAction={{ onAction: () => navigate("/app") }}
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

        {/* Tracking paused — limit reached */}
        {isRunning && trackingPaused && (
          <Layout.Section>
            <Banner
              tone="warning"
              title="Tracking paused — free plan limit reached"
              action={{ content: "Start free trial", onAction: () => navigate("/app/billing") }}
            >
              <BlockStack gap="200">
                <Text as="p" variant="bodySm">
                  {viewLimitReached && dayLimitReached
                    ? `You've used all ${viewLimit?.toLocaleString()} monthly visitors and exceeded the ${maxDays}-day test duration.`
                    : viewLimitReached
                      ? `You've used all ${viewLimit?.toLocaleString()} monthly visitors included in your free plan.`
                      : `Your test has exceeded the ${maxDays}-day duration limit on the free plan.`}
                  {" "}New metrics are no longer being collected. Your existing results are still available below.
                </Text>
                <Text as="p" variant="bodySm">
                  Upgrade to Pro or Unlimited for unlimited visitors and test duration.
                </Text>
              </BlockStack>
            </Banner>
          </Layout.Section>
        )}

        {/* View limit warnings (75% / 90%) */}
        {isRunning && viewWarning90 && (
          <Layout.Section>
            <Banner
              tone="critical"
              action={{ content: "Start free trial", onAction: () => navigate("/app/billing") }}
            >
              <BlockStack gap="100">
                <Text as="p" variant="bodySm">
                  You've used {viewsUsed.toLocaleString()} of {viewLimit?.toLocaleString()} monthly visitors ({viewPercent}%).
                  Tracking will pause when the limit is reached.
                </Text>
                <ProgressBar progress={Math.min(viewPercent, 100)} tone="critical" size="small" />
              </BlockStack>
            </Banner>
          </Layout.Section>
        )}
        {isRunning && viewWarning75 && (
          <Layout.Section>
            <Banner
              tone="warning"
              action={{ content: "See plans", onAction: () => navigate("/app/billing") }}
            >
              <BlockStack gap="100">
                <Text as="p" variant="bodySm">
                  You've used {viewsUsed.toLocaleString()} of {viewLimit?.toLocaleString()} monthly visitors ({viewPercent}%).
                </Text>
                <ProgressBar progress={viewPercent} tone="highlight" size="small" />
              </BlockStack>
            </Banner>
          </Layout.Section>
        )}

        {/* Day limit warnings (75% / 90%) */}
        {isRunning && dayWarning90 && (
          <Layout.Section>
            <Banner
              tone="critical"
              action={{ content: "Start free trial", onAction: () => navigate("/app/billing") }}
            >
              <Text as="p" variant="bodySm">
                Day {daysSinceStart} of {maxDays} — your test is about to reach the free plan duration limit.
                Tracking will pause after day {maxDays}. Upgrade for unlimited test duration.
              </Text>
            </Banner>
          </Layout.Section>
        )}
        {isRunning && dayWarning75 && (
          <Layout.Section>
            <Banner
              tone="warning"
              action={{ content: "See plans", onAction: () => navigate("/app/billing") }}
            >
              <Text as="p" variant="bodySm">
                Day {daysSinceStart} of {maxDays} — you're approaching the free plan duration limit.
              </Text>
            </Banner>
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

        {/* Actions — Draft */}
        {isDraft && (
          <Layout.Section>
            <Card>
              <BlockStack gap="300">
                <Text variant="bodySm" as="p" tone="subdued">
                  Starting the test will push Variant A to your storefront and
                  begin tracking views, add-to-carts, and conversions.
                </Text>
                <InlineStack align="end" gap="300">
                  <Button
                    onClick={() => setShowCancelModal(true)}
                    tone="critical"
                    disabled={isActing}
                  >
                    Delete test
                  </Button>
                  <Button
                    variant="primary"
                    onClick={handleStart}
                    loading={isActing}
                    disabled={isActing}
                  >
                    Start test
                  </Button>
                </InlineStack>
              </BlockStack>
            </Card>
          </Layout.Section>
        )}

        {/* Actions — Running */}
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

        {/* Tips — shown while running, before significance */}
        {isRunning && !significance?.confident && (
          <Layout.Section>
            <Card>
              <BlockStack gap="300">
                <Text variant="headingSm" as="h3">Tips for better results</Text>
                <Divider />
                <BlockStack gap="200">
                  <Text variant="bodySm" as="p" tone="subdued">
                    <strong>Be patient.</strong> Let your test run until statistical significance
                    is reached — usually 200+ views per variant. Ending early may lead to wrong conclusions.
                  </Text>
                  <Text variant="bodySm" as="p" tone="subdued">
                    <strong>Use the swap button.</strong> Periodically swapping variants helps account
                    for time-of-day and day-of-week patterns in your traffic.
                  </Text>
                  <Text variant="bodySm" as="p" tone="subdued">
                    <strong>Test meaningful differences.</strong> The best A/B tests compare images
                    that are meaningfully different — e.g. lifestyle vs. white background, or different angles.
                  </Text>
                </BlockStack>
              </BlockStack>
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
                    {trackingPaused
                      ? "Paused (limit reached)"
                      : test.tracking_mode === "pixel" ? "Automatic (pixel)" : "Manual"}
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
