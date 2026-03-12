/**
 * VariantCard — displays metrics for one variant (A or B).
 * Shows views, ATC, conversions, revenue, conversion rate, and lift vs. other variant.
 */
import {
  Card,
  BlockStack,
  InlineStack,
  Text,
  Badge,
  Divider,
} from "@shopify/polaris";
import type { VariantMetrics } from "~/lib/opal-api.server";

interface VariantCardProps {
  label: string;
  variant: "a" | "b";
  metrics: VariantMetrics;
  isActive: boolean;
  isWinner: boolean;
  otherMetrics: VariantMetrics;
}

function formatRevenue(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 0,
  }).format(cents / 100);
}

function conversionRate(metrics: VariantMetrics): number {
  if (metrics.views === 0) return 0;
  return (metrics.conversions / metrics.views) * 100;
}

function liftPercent(rate: number, otherRate: number): number | null {
  if (otherRate === 0) return null;
  return ((rate - otherRate) / otherRate) * 100;
}

export function VariantCard({
  label,
  variant,
  metrics,
  isActive,
  isWinner,
  otherMetrics,
}: VariantCardProps) {
  const rate = conversionRate(metrics);
  const otherRate = conversionRate(otherMetrics);
  const lift = liftPercent(rate, otherRate);

  return (
    <Card>
      <BlockStack gap="400">
        {/* Header */}
        <InlineStack align="space-between" blockAlign="center">
          <Text variant="headingMd" as="h3">
            {label}
          </Text>
          <InlineStack gap="200">
            {isActive && <Badge tone="info">Active</Badge>}
            {isWinner && <Badge tone="success">Winner</Badge>}
          </InlineStack>
        </InlineStack>

        <Divider />

        {/* Metrics grid */}
        <BlockStack gap="300">
          <MetricRow label="Views" value={metrics.views.toLocaleString()} />
          <MetricRow label="Add to carts" value={metrics.add_to_carts.toLocaleString()} />
          <MetricRow label="Conversions" value={metrics.conversions.toLocaleString()} />
          <MetricRow label="Revenue" value={formatRevenue(metrics.revenue_cents)} />
        </BlockStack>

        <Divider />

        {/* Conversion rate + lift */}
        <BlockStack gap="200">
          <InlineStack align="space-between">
            <Text variant="bodyMd" as="span" fontWeight="semibold">
              Conversion rate
            </Text>
            <Text variant="headingSm" as="span">
              {rate.toFixed(1)}%
            </Text>
          </InlineStack>
          {lift !== null && (
            <InlineStack align="end">
              <Text
                variant="bodySm"
                as="span"
                tone={lift > 0 ? "success" : lift < 0 ? "critical" : "subdued"}
              >
                {lift > 0 ? "+" : ""}
                {lift.toFixed(1)}% vs {variant === "a" ? "B" : "A"}
              </Text>
            </InlineStack>
          )}
        </BlockStack>
      </BlockStack>
    </Card>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <InlineStack align="space-between">
      <Text variant="bodyMd" as="span" tone="subdued">
        {label}
      </Text>
      <Text variant="bodyMd" as="span">
        {value}
      </Text>
    </InlineStack>
  );
}
