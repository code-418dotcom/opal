/**
 * SignificanceGauge — progress bar showing statistical confidence level.
 * Visualizes how close the test is to reaching 95% confidence.
 */
import {
  Card,
  BlockStack,
  InlineStack,
  Text,
  ProgressBar,
  Banner,
} from "@shopify/polaris";
import type { Significance } from "~/lib/opal-api.server";

interface SignificanceGaugeProps {
  significance?: Significance;
}

export function SignificanceGauge({ significance }: SignificanceGaugeProps) {
  if (!significance) {
    return (
      <Card>
        <BlockStack gap="300">
          <Text variant="headingSm" as="h3">
            Statistical significance
          </Text>
          <Text variant="bodySm" as="p" tone="subdued">
            No data yet. Metrics will appear as storefront events are collected.
          </Text>
          <ProgressBar progress={0} size="small" />
        </BlockStack>
      </Card>
    );
  }

  // Convert p-value to a confidence percentage for the gauge
  // p=0.05 → 95% confidence, p=0.01 → 99%, p=1.0 → 0%
  const confidence = significance.p_value !== null
    ? Math.max(0, Math.min(100, (1 - significance.p_value) * 100))
    : 0;

  const progressTone = significance.confident ? "success" : "highlight";

  return (
    <Card>
      <BlockStack gap="400">
        <InlineStack align="space-between" blockAlign="center">
          <Text variant="headingSm" as="h3">
            Statistical significance
          </Text>
          <Text variant="bodyMd" as="span" fontWeight="semibold">
            {confidence.toFixed(1)}%
          </Text>
        </InlineStack>

        <ProgressBar
          progress={confidence}
          size="small"
          tone={progressTone}
        />

        <InlineStack align="space-between">
          <Text variant="bodySm" as="span" tone="subdued">
            0%
          </Text>
          <Text variant="bodySm" as="span" tone="subdued">
            95% threshold
          </Text>
          <Text variant="bodySm" as="span" tone="subdued">
            100%
          </Text>
        </InlineStack>

        {significance.confident ? (
          <Banner tone="success" title="Statistically significant">
            {significance.recommended_winner && (
              <Text as="p" variant="bodyMd">
                Recommended winner: Variant {significance.recommended_winner.toUpperCase()}
                {significance.lift_percent !== null &&
                  ` (+${significance.lift_percent}% conversion lift)`}
              </Text>
            )}
            <Text as="p" variant="bodySm" tone="subdued">
              p-value: {significance.p_value?.toFixed(4)}
            </Text>
          </Banner>
        ) : (
          <Text variant="bodySm" as="p" tone="subdued">
            {significance.message || "Not enough data to determine significance."}
            {significance.p_value !== null && ` (p=${significance.p_value.toFixed(4)})`}
          </Text>
        )}

        {/* Conversion rate comparison */}
        {(significance.conversion_rate_a > 0 || significance.conversion_rate_b > 0) && (
          <InlineStack gap="800">
            <BlockStack gap="100">
              <Text variant="bodySm" as="span" tone="subdued">Variant A rate</Text>
              <Text variant="bodyMd" as="span">{significance.conversion_rate_a}%</Text>
            </BlockStack>
            <BlockStack gap="100">
              <Text variant="bodySm" as="span" tone="subdued">Variant B rate</Text>
              <Text variant="bodyMd" as="span">{significance.conversion_rate_b}%</Text>
            </BlockStack>
          </InlineStack>
        )}
      </BlockStack>
    </Card>
  );
}
