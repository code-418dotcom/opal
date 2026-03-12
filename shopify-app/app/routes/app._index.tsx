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
  EmptyState,
  IndexTable,
  Badge,
  Text,
  Button,
  BlockStack,
  InlineStack,
  Box,
  Filters,
} from "@shopify/polaris";
import { useState, useCallback } from "react";

import { authenticate } from "~/shopify.server";
import { getIntegrationByShop, listTests } from "~/lib/opal-api.server";
import type { ABTest } from "~/lib/opal-api.server";

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const { session } = await authenticate.admin(request);
  const shopDomain = session.shop;

  const integration = await getIntegrationByShop(shopDomain);
  if (!integration) {
    return json({ tests: [] as ABTest[], hasIntegration: false, shopDomain });
  }

  const tests = await listTests(integration.id);
  return json({ tests, hasIntegration: true, shopDomain });
};

const STATUS_BADGE_MAP: Record<string, { tone: "success" | "info" | "attention" | "critical" | undefined; label: string }> = {
  created: { tone: "info", label: "Draft" },
  running: { tone: "success", label: "Running" },
  concluded: { tone: undefined, label: "Concluded" },
  canceled: { tone: "critical", label: "Canceled" },
};

export default function Dashboard() {
  const { tests, hasIntegration, shopDomain } = useLoaderData<typeof loader>();
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
      <Page title="Opal A/B Image Testing">
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
                  content: "Create test",
                  onAction: () => navigate("/app/tests/new"),
                }}
                image="https://cdn.shopify.com/s/files/1/0262/4071/2726/files/emptystate-files.png"
              >
                <p>
                  Test different product images to find which ones drive more
                  sales. Opal automatically tracks views, add-to-carts, and
                  conversions.
                </p>
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
        content: "Create test",
        onAction: () => navigate("/app/tests/new"),
      }}
    >
      <Layout>
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
      </Layout>
    </Page>
  );
}
