/**
 * Dashboard — list all A/B tests with status badges.
 * Main landing page when merchant opens the app.
 */
import type { LoaderFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { useLoaderData, useNavigate } from "@remix-run/react";
import {
  Page,
  Layout,
  Card,
  CalloutCard,
  EmptyState,
  IndexTable,
  Badge,
  Banner,
  Text,
  Button,
  BlockStack,
  InlineStack,
  Box,
  Filters,
  ProgressBar,
} from "@shopify/polaris";
import { useState, useCallback } from "react";

import { authenticate } from "~/shopify.server";
import { getIntegrationByShop, listTests, provisionIntegration } from "~/lib/opal-api.server";
import type { ABTest } from "~/lib/opal-api.server";
import { getEntitlements } from "~/lib/entitlements.server";
import type { Entitlements } from "~/lib/entitlements.server";
import { OpalLogo } from "~/components/OpalLogo";

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const { session, billing } = await authenticate.admin(request);
  const shopDomain = session.shop;

  // Auto-provision integration if it doesn't exist
  let integration = await getIntegrationByShop(shopDomain);
  if (!integration) {
    try {
      integration = await provisionIntegration(shopDomain);
    } catch {
      return json({
        tests: [] as ABTest[],
        hasIntegration: false,
        shopDomain,
        entitlements: null as Entitlements | null,
      });
    }
  }

  const [tests, entitlements] = await Promise.all([
    listTests(integration.id),
    getEntitlements(billing, integration.id),
  ]);

  // Redirect first-time users to the welcome wizard
  if (tests.length === 0) {
    const url = new URL(request.url);
    // Avoid redirect loop — only redirect if not coming from welcome
    if (!url.searchParams.has("from_welcome")) {
      const { redirect } = await import("@remix-run/node");
      return redirect("/app/welcome");
    }
  }

  return json({ tests, hasIntegration: true, shopDomain, entitlements });
};

const STATUS_BADGE_MAP: Record<string, { tone: "success" | "info" | "attention" | "critical" | undefined; label: string }> = {
  created: { tone: "info", label: "Draft" },
  running: { tone: "success", label: "Running" },
  concluded: { tone: undefined, label: "Concluded" },
  canceled: { tone: "critical", label: "Canceled" },
};

export default function Dashboard() {
  const { tests, hasIntegration, shopDomain, entitlements } = useLoaderData<typeof loader>();
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState("");

  const handleFilterChange = useCallback((value: string) => {
    setStatusFilter(value);
  }, []);

  const handleFilterClear = useCallback(() => {
    setStatusFilter("");
  }, []);

  if (!hasIntegration) {
    return (
      <Page title="Opal A/B">
        <Layout>
          <Layout.Section>
            <Card>
              <EmptyState
                heading="Connect your store to Opal"
                image="https://cdn.shopify.com/s/files/1/0262/4071/2726/files/emptystate-files.png"
              >
                <p>
                  Your store ({shopDomain}) is not yet connected to Opal.
                  Please connect your Shopify store from the{" "}
                  <a href="https://opaloptics.com" target="_blank" rel="noopener noreferrer">
                    Opal dashboard
                  </a>{" "}
                  first.
                </p>
              </EmptyState>
            </Card>
          </Layout.Section>
        </Layout>
      </Page>
    );
  }

  const filteredTests = statusFilter
    ? tests.filter((t) => t.status === statusFilter)
    : tests;

  const canCreate = entitlements?.canCreateTest !== false;

  if (tests.length === 0) {
    return (
      <Page
        title="A/B Image Tests"
        primaryAction={{
          content: "Create test",
          onAction: () => navigate("/app/tests/new"),
        }}
      >
        <Layout>
          <Layout.Section>
            <Card>
              <EmptyState
                heading="Run your first A/B image test"
                action={{
                  content: "Create your first test",
                  onAction: () => navigate("/app/tests/new"),
                }}
                image=""
              >
                <BlockStack gap="200">
                  <div style={{ display: "flex", justifyContent: "center", padding: "0.5rem 0" }}>
                    <OpalLogo size={56} />
                  </div>
                  <p>
                    Find out which product images drive more sales. Pick two images,
                    and Opal automatically tracks which one converts better — no code needed.
                  </p>
                </BlockStack>
              </EmptyState>
            </Card>
          </Layout.Section>
        </Layout>
      </Page>
    );
  }

  const resourceName = { singular: "test", plural: "tests" };

  const rowMarkup = filteredTests.map((test, index) => {
    const badge = STATUS_BADGE_MAP[test.status] || { tone: undefined, label: test.status };
    const startedDate = test.started_at
      ? new Date(test.started_at).toLocaleDateString()
      : "—";

    return (
      <IndexTable.Row
        id={test.id}
        key={test.id}
        position={index}
        onClick={() => navigate(`/app/tests/${test.id}`)}
      >
        <IndexTable.Cell>
          <Text variant="bodyMd" fontWeight="bold" as="span">
            {test.product_title || `Product ${test.product_id}`}
          </Text>
        </IndexTable.Cell>
        <IndexTable.Cell>
          <Badge tone={badge.tone}>{badge.label}</Badge>
        </IndexTable.Cell>
        <IndexTable.Cell>{startedDate}</IndexTable.Cell>
        <IndexTable.Cell>
          <Text as="span" variant="bodyMd">
            {test.active_variant === "a" ? test.variant_a_label : test.variant_b_label}
          </Text>
        </IndexTable.Cell>
        <IndexTable.Cell>
          {test.winner ? (
            <Badge tone="success">
              {`Winner: ${test.winner === "a" ? test.variant_a_label : test.variant_b_label}`}
            </Badge>
          ) : (
            "—"
          )}
        </IndexTable.Cell>
      </IndexTable.Row>
    );
  });

  return (
    <Page
      title="A/B Image Tests"
      primaryAction={{
        content: canCreate ? "Create test" : "Upgrade to create more",
        onAction: () => navigate(canCreate ? "/app/tests/new" : "/app/billing"),
      }}
    >
      <Layout>
        {/* Upgrade banner when at test limit */}
        {entitlements && !canCreate && (
          <Layout.Section>
            <Banner
              tone="warning"
              action={{ content: "Upgrade", url: "/app/billing" }}
            >
              {entitlements.createTestBlockReason}
            </Banner>
          </Layout.Section>
        )}
        {/* Plan badge */}
        {entitlements && entitlements.tier === "free" && tests.length > 0 && canCreate && (
          <Layout.Section>
            <Banner
              tone="info"
              action={{ content: "See plans", url: "/app/billing" }}
            >
              You're on the Free plan ({entitlements.runningTestCount}/{entitlements.maxConcurrentTests} test used).
              Upgrade for more tests and auto-conclude.
            </Banner>
          </Layout.Section>
        )}
        {/* Monthly view usage warnings (free tier only) */}
        {entitlements && entitlements.tier === "free" && entitlements.monthlyViewLimit !== null && (() => {
          const pct = Math.round((entitlements.monthlyViews / entitlements.monthlyViewLimit) * 100);
          if (pct >= 100) {
            return (
              <Layout.Section>
                <Banner
                  tone="critical"
                  action={{ content: "Start free trial", url: "/app/billing" }}
                >
                  <BlockStack gap="100">
                    <Text as="p" variant="bodySm">
                      Monthly visitor limit reached ({entitlements.monthlyViews.toLocaleString()}/{entitlements.monthlyViewLimit.toLocaleString()}).
                      Tracking is paused for all tests. Upgrade for unlimited visitors.
                    </Text>
                    <ProgressBar progress={100} tone="critical" size="small" />
                  </BlockStack>
                </Banner>
              </Layout.Section>
            );
          }
          if (pct >= 90) {
            return (
              <Layout.Section>
                <Banner
                  tone="critical"
                  action={{ content: "Start free trial", url: "/app/billing" }}
                >
                  <BlockStack gap="100">
                    <Text as="p" variant="bodySm">
                      {entitlements.monthlyViews.toLocaleString()} of {entitlements.monthlyViewLimit.toLocaleString()} monthly visitors used ({pct}%).
                      Tracking will pause when the limit is reached.
                    </Text>
                    <ProgressBar progress={pct} tone="critical" size="small" />
                  </BlockStack>
                </Banner>
              </Layout.Section>
            );
          }
          if (pct >= 75) {
            return (
              <Layout.Section>
                <Banner
                  tone="warning"
                  action={{ content: "See plans", url: "/app/billing" }}
                >
                  <BlockStack gap="100">
                    <Text as="p" variant="bodySm">
                      {entitlements.monthlyViews.toLocaleString()} of {entitlements.monthlyViewLimit.toLocaleString()} monthly visitors used ({pct}%).
                    </Text>
                    <ProgressBar progress={pct} tone="highlight" size="small" />
                  </BlockStack>
                </Banner>
              </Layout.Section>
            );
          }
          return null;
        })()}
        <Layout.Section>
          <Card padding="0">
            <Box padding="400">
              <Filters
                queryValue=""
                filters={[
                  {
                    key: "status",
                    label: "Status",
                    filter: (
                      <BlockStack gap="200">
                        {["running", "created", "concluded", "canceled"].map((s) => (
                          <Button
                            key={s}
                            variant={statusFilter === s ? "primary" : "plain"}
                            onClick={() => handleFilterChange(s)}
                            size="slim"
                          >
                            {STATUS_BADGE_MAP[s]?.label || s}
                          </Button>
                        ))}
                      </BlockStack>
                    ),
                    shortcut: true,
                  },
                ]}
                onQueryChange={() => {}}
                onQueryClear={() => {}}
                onClearAll={handleFilterClear}
              />
            </Box>
            <IndexTable
              resourceName={resourceName}
              itemCount={filteredTests.length}
              headings={[
                { title: "Product" },
                { title: "Status" },
                { title: "Started" },
                { title: "Active variant" },
                { title: "Winner" },
              ]}
              selectable={false}
            >
              {rowMarkup}
            </IndexTable>
          </Card>
        </Layout.Section>

        {/* Cross-sell: Opal Image Studio */}
        <Layout.Section>
          <CalloutCard
            title="Need better product images?"
            illustration="https://cdn.shopify.com/s/files/1/0262/4071/2726/files/emptystate-files.png"
            primaryAction={{
              content: "Try Opal Image Studio",
              url: "https://opaloptics.com",
              external: true,
            }}
          >
            <p>
              Generate studio-quality product photos with AI. Remove backgrounds,
              create professional scenes, and upscale — directly from your catalog.
            </p>
          </CalloutCard>
        </Layout.Section>
      </Layout>
    </Page>
  );
}
