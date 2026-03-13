/**
 * Billing — plan selection and subscription management.
 */
import type { ActionFunctionArgs, LoaderFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { useActionData, useLoaderData, useNavigation, useSubmit } from "@remix-run/react";
import {
  Page,
  Layout,
  Card,
  BlockStack,
  InlineStack,
  InlineGrid,
  Text,
  Button,
  Badge,
  Divider,
  List,
  Banner,
  Box,
  CalloutCard,
} from "@shopify/polaris";
import { useCallback } from "react";

import { authenticate, MONTHLY_PRO, ANNUAL_PRO } from "~/shopify.server";
import { getIntegrationByShop } from "~/lib/opal-api.server";
import { getEntitlements } from "~/lib/entitlements.server";

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const { session, billing } = await authenticate.admin(request);
  const integration = await getIntegrationByShop(session.shop);

  const entitlements = await getEntitlements(billing, integration?.id || null);

  // Get current subscription details if any
  let currentSubscription: { id: string; name: string; status: string } | null = null;
  try {
    const { appSubscriptions } = await (billing as any).check({
      plans: [MONTHLY_PRO, ANNUAL_PRO],
      isTest: true,
    });
    if (appSubscriptions.length > 0) {
      currentSubscription = appSubscriptions[0];
    }
  } catch {
    // ignore
  }

  return json({
    entitlements,
    currentSubscription,
    shopDomain: session.shop,
  });
};

export const action = async ({ request }: ActionFunctionArgs) => {
  const auth = await authenticate.admin(request);
  const billing = auth.billing as any;
  const formData = await request.formData();
  const intent = formData.get("intent") as string;

  if (intent === "subscribe_monthly") {
    await billing.request({
      plan: MONTHLY_PRO,
      isTest: true,
    });
    // billing.request redirects — this won't be reached
    return json({ ok: true });
  }

  if (intent === "subscribe_annual") {
    await billing.request({
      plan: ANNUAL_PRO,
      isTest: true,
    });
    return json({ ok: true });
  }

  if (intent === "cancel") {
    const subscriptionId = formData.get("subscription_id") as string;
    if (!subscriptionId) {
      return json({ error: "No subscription to cancel." }, { status: 400 });
    }
    await billing.cancel({
      subscriptionId,
      isTest: true,
      prorate: true,
    });
    return json({ ok: true, action: "canceled" });
  }

  return json({ error: "Unknown action" }, { status: 400 });
};

const FREE_FEATURES = [
  "1 concurrent A/B test",
  "Automatic pixel tracking",
  "Basic metrics (views, ATC, conversions)",
  "30-day max test duration",
  "Manual conclude only",
];

const PRO_FEATURES = [
  "Unlimited concurrent A/B tests",
  "Automatic pixel tracking",
  "Full metrics + revenue tracking",
  "Unlimited test duration",
  "Auto-conclude with statistical significance",
  "7-day free trial",
];

export default function Billing() {
  const { entitlements, currentSubscription } = useLoaderData<typeof loader>();
  const actionData = useActionData<typeof action>();
  const navigation = useNavigation();
  const submit = useSubmit();
  const isSubmitting = navigation.state === "submitting";

  const handleSubscribe = useCallback(
    (plan: "monthly" | "annual") => {
      const formData = new FormData();
      formData.set("intent", plan === "monthly" ? "subscribe_monthly" : "subscribe_annual");
      submit(formData, { method: "post" });
    },
    [submit],
  );

  const handleCancel = useCallback(() => {
    if (!currentSubscription) return;
    const formData = new FormData();
    formData.set("intent", "cancel");
    formData.set("subscription_id", currentSubscription.id);
    submit(formData, { method: "post" });
  }, [submit, currentSubscription]);

  const isPro = entitlements.tier === "pro";

  return (
    <Page title="Plans & Billing" backAction={{ url: "/app" }}>
      <Layout>
        {/* Action feedback */}
        {actionData && "action" in actionData && actionData.action === "canceled" && (
          <Layout.Section>
            <Banner tone="info">
              Your subscription has been canceled. You'll retain Pro features until the end of your billing period.
            </Banner>
          </Layout.Section>
        )}
        {actionData && "error" in actionData && (
          <Layout.Section>
            <Banner tone="critical">{actionData.error}</Banner>
          </Layout.Section>
        )}

        {/* Current plan status */}
        {isPro && currentSubscription && (
          <Layout.Section>
            <CalloutCard
              title="You're on the Pro plan"
              illustration="https://cdn.shopify.com/s/files/1/0262/4071/2726/files/emptystate-files.png"
              primaryAction={{
                content: "Cancel subscription",
                onAction: handleCancel,
              }}
            >
              <Text as="p">
                Plan: <strong>{currentSubscription.name}</strong>{" "}
                <Badge tone="success">Active</Badge>
              </Text>
            </CalloutCard>
          </Layout.Section>
        )}

        {/* Plan cards */}
        <Layout.Section>
          <InlineGrid columns={2} gap="400">
            {/* Free Plan */}
            <Card>
              <BlockStack gap="400">
                <InlineStack align="space-between" blockAlign="center">
                  <Text variant="headingMd" as="h2">Free</Text>
                  {!isPro && <Badge>Current plan</Badge>}
                </InlineStack>
                <BlockStack gap="200">
                  <Text variant="headingXl" as="p">$0</Text>
                  <Text variant="bodySm" as="p" tone="subdued">Forever free</Text>
                </BlockStack>
                <Divider />
                <List type="bullet">
                  {FREE_FEATURES.map((f) => (
                    <List.Item key={f}>{f}</List.Item>
                  ))}
                </List>
                <Box>
                  <Button disabled fullWidth>
                    {!isPro ? "Current plan" : "Downgrade"}
                  </Button>
                </Box>
              </BlockStack>
            </Card>

            {/* Pro Plan */}
            <Card>
              <BlockStack gap="400">
                <InlineStack align="space-between" blockAlign="center">
                  <Text variant="headingMd" as="h2">Pro</Text>
                  {isPro && <Badge tone="success">Current plan</Badge>}
                </InlineStack>
                <BlockStack gap="200">
                  <InlineStack gap="200" blockAlign="baseline">
                    <Text variant="headingXl" as="p">$19</Text>
                    <Text variant="bodySm" as="span" tone="subdued">/month</Text>
                  </InlineStack>
                  <Text variant="bodySm" as="p" tone="subdued">
                    or $190/year (save ~17%)
                  </Text>
                </BlockStack>
                <Divider />
                <List type="bullet">
                  {PRO_FEATURES.map((f) => (
                    <List.Item key={f}>{f}</List.Item>
                  ))}
                </List>
                {!isPro ? (
                  <BlockStack gap="200">
                    <Button
                      variant="primary"
                      onClick={() => handleSubscribe("monthly")}
                      loading={isSubmitting}
                      fullWidth
                    >
                      Start 7-day free trial
                    </Button>
                    <Button
                      onClick={() => handleSubscribe("annual")}
                      loading={isSubmitting}
                      fullWidth
                    >
                      Subscribe annually ($190/yr)
                    </Button>
                  </BlockStack>
                ) : (
                  <Box>
                    <Button disabled fullWidth>
                      Current plan
                    </Button>
                  </Box>
                )}
              </BlockStack>
            </Card>
          </InlineGrid>
        </Layout.Section>

        {/* FAQ */}
        <Layout.Section>
          <Card>
            <BlockStack gap="400">
              <Text variant="headingMd" as="h2">Frequently asked questions</Text>
              <Divider />
              <BlockStack gap="200">
                <Text variant="headingSm" as="h3">What happens when my free trial ends?</Text>
                <Text variant="bodySm" as="p" tone="subdued">
                  After your 7-day trial, you'll be charged $19/month (or $190/year) through your Shopify bill.
                  Cancel anytime before the trial ends to avoid charges.
                </Text>
              </BlockStack>
              <BlockStack gap="200">
                <Text variant="headingSm" as="h3">Can I switch between monthly and annual?</Text>
                <Text variant="bodySm" as="p" tone="subdued">
                  Yes! Cancel your current plan and subscribe to the other. You'll receive a prorated credit.
                </Text>
              </BlockStack>
              <BlockStack gap="200">
                <Text variant="headingSm" as="h3">What happens to my tests if I downgrade?</Text>
                <Text variant="bodySm" as="p" tone="subdued">
                  Your existing tests and data are preserved. You'll be limited to 1 concurrent test
                  and won't have access to auto-conclude on the free plan.
                </Text>
              </BlockStack>
            </BlockStack>
          </Card>
        </Layout.Section>
      </Layout>
    </Page>
  );
}
