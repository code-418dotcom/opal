/**
 * Billing — plan selection and subscription management.
 */
import type { ActionFunctionArgs, LoaderFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { useActionData, useLoaderData, useNavigation, useNavigate, useSubmit } from "@remix-run/react";
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

import { authenticate, MONTHLY_PRO, ANNUAL_PRO, MONTHLY_UNLIMITED, ANNUAL_UNLIMITED } from "~/shopify.server";
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
      plans: [MONTHLY_PRO, ANNUAL_PRO, MONTHLY_UNLIMITED, ANNUAL_UNLIMITED],
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

  if (intent === "subscribe_monthly_pro") {
    await billing.request({
      plan: MONTHLY_PRO,
      isTest: true,
    });
    return json({ ok: true });
  }

  if (intent === "subscribe_annual_pro") {
    await billing.request({
      plan: ANNUAL_PRO,
      isTest: true,
    });
    return json({ ok: true });
  }

  if (intent === "subscribe_monthly_unlimited") {
    await billing.request({
      plan: MONTHLY_UNLIMITED,
      isTest: true,
    });
    return json({ ok: true });
  }

  if (intent === "subscribe_annual_unlimited") {
    await billing.request({
      plan: ANNUAL_UNLIMITED,
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
  "Up to 1,000 monthly visitors",
  "Automatic pixel tracking",
  "Basic metrics (views, ATC, conversions)",
  "30-day max test duration",
  "Manual conclude only",
];

const PRO_FEATURES = [
  "10 concurrent A/B tests",
  "Unlimited monthly visitors",
  "Automatic pixel tracking",
  "Full metrics + revenue tracking",
  "Unlimited test duration",
  "Auto-conclude with statistical significance",
  "7-day free trial",
];

const UNLIMITED_FEATURES = [
  "Unlimited concurrent A/B tests",
  "Unlimited monthly visitors",
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
  const navigate = useNavigate();
  const isSubmitting = navigation.state === "submitting";

  const handleSubscribe = useCallback(
    (intent: string) => {
      const formData = new FormData();
      formData.set("intent", intent);
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

  const tier = entitlements.tier;

  return (
    <Page title="Plans & Billing" backAction={{ onAction: () => navigate("/app") }}>
      <Layout>
        {/* Action feedback */}
        {actionData && "action" in actionData && actionData.action === "canceled" && (
          <Layout.Section>
            <Banner tone="info">
              Your subscription has been canceled. You've been downgraded to the Free plan. Your existing tests and data are preserved.
            </Banner>
          </Layout.Section>
        )}
        {actionData && "error" in actionData && (
          <Layout.Section>
            <Banner tone="critical">{actionData.error}</Banner>
          </Layout.Section>
        )}

        {/* Current plan status */}
        {tier !== "free" && currentSubscription && (
          <Layout.Section>
            <CalloutCard
              title={`You're on the ${tier === "unlimited" ? "Unlimited" : "Pro"} plan`}
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
          <InlineGrid columns={3} gap="400">
            {/* Free Plan */}
            <Card>
              <BlockStack gap="400">
                <InlineStack align="space-between" blockAlign="center">
                  <Text variant="headingMd" as="h2">Free</Text>
                  {tier === "free" && <Badge>Current plan</Badge>}
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
                    {tier === "free" ? "Current plan" : "Downgrade"}
                  </Button>
                </Box>
              </BlockStack>
            </Card>

            {/* Pro Plan */}
            <Card>
              <BlockStack gap="400">
                <InlineStack align="space-between" blockAlign="center">
                  <Text variant="headingMd" as="h2">Pro</Text>
                  {tier === "pro" && <Badge tone="success">Current plan</Badge>}
                </InlineStack>
                <BlockStack gap="200">
                  <InlineStack gap="200" blockAlign="baseline">
                    <Text variant="headingXl" as="p">$19</Text>
                    <Text variant="bodySm" as="span" tone="subdued">/month</Text>
                  </InlineStack>
                  <Text variant="bodySm" as="p" tone="subdued">
                    or $190/year (2 months free)
                  </Text>
                </BlockStack>
                <Divider />
                <List type="bullet">
                  {PRO_FEATURES.map((f) => (
                    <List.Item key={f}>{f}</List.Item>
                  ))}
                </List>
                {tier === "free" ? (
                  <BlockStack gap="200">
                    <Button
                      variant="primary"
                      onClick={() => handleSubscribe("subscribe_monthly_pro")}
                      loading={isSubmitting}
                      fullWidth
                    >
                      Start 7-day free trial
                    </Button>
                    <Button
                      onClick={() => handleSubscribe("subscribe_annual_pro")}
                      loading={isSubmitting}
                      fullWidth
                    >
                      Subscribe annually — 2 months free
                    </Button>
                  </BlockStack>
                ) : tier === "pro" ? (
                  <Box>
                    <Button disabled fullWidth>
                      Current plan
                    </Button>
                  </Box>
                ) : (
                  <Box>
                    <Button disabled fullWidth>
                      Downgrade
                    </Button>
                  </Box>
                )}
              </BlockStack>
            </Card>

            {/* Unlimited Plan */}
            <Card>
              <BlockStack gap="400">
                <InlineStack align="space-between" blockAlign="center">
                  <Text variant="headingMd" as="h2">Unlimited</Text>
                  {tier === "unlimited" ? (
                    <Badge tone="success">Current plan</Badge>
                  ) : (
                    <Badge tone="attention">Best value</Badge>
                  )}
                </InlineStack>
                <BlockStack gap="200">
                  <InlineStack gap="200" blockAlign="baseline">
                    <Text variant="headingXl" as="p">$29</Text>
                    <Text variant="bodySm" as="span" tone="subdued">/month</Text>
                  </InlineStack>
                  <Text variant="bodySm" as="p" tone="subdued">
                    or $290/year (2 months free)
                  </Text>
                </BlockStack>
                <Divider />
                <List type="bullet">
                  {UNLIMITED_FEATURES.map((f) => (
                    <List.Item key={f}>{f}</List.Item>
                  ))}
                </List>
                {tier === "unlimited" ? (
                  <Box>
                    <Button disabled fullWidth>
                      Current plan
                    </Button>
                  </Box>
                ) : (
                  <BlockStack gap="200">
                    <Button
                      variant="primary"
                      onClick={() => handleSubscribe("subscribe_monthly_unlimited")}
                      loading={isSubmitting}
                      fullWidth
                    >
                      Start 7-day free trial
                    </Button>
                    <Button
                      onClick={() => handleSubscribe("subscribe_annual_unlimited")}
                      loading={isSubmitting}
                      fullWidth
                    >
                      Subscribe annually — 2 months free
                    </Button>
                  </BlockStack>
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
                  After your 7-day trial, you'll be charged through your Shopify bill.
                  Cancel anytime before the trial ends to avoid charges — you'll be
                  automatically moved to the Free plan.
                </Text>
              </BlockStack>
              <BlockStack gap="200">
                <Text variant="headingSm" as="h3">What if I cancel my subscription?</Text>
                <Text variant="bodySm" as="p" tone="subdued">
                  You'll be downgraded to the Free plan automatically. The app stays installed
                  and all your existing tests and data are preserved. You can upgrade again anytime.
                </Text>
              </BlockStack>
              <BlockStack gap="200">
                <Text variant="headingSm" as="h3">Can I switch between plans?</Text>
                <Text variant="bodySm" as="p" tone="subdued">
                  Yes! Cancel your current plan and subscribe to a different one. You'll receive a prorated credit.
                </Text>
              </BlockStack>
              <BlockStack gap="200">
                <Text variant="headingSm" as="h3">What happens to my tests if I downgrade?</Text>
                <Text variant="bodySm" as="p" tone="subdued">
                  Your existing tests and data are preserved. You'll be limited to the concurrent test
                  limit and monthly visitor cap of the Free plan, and won't have access to auto-conclude.
                </Text>
              </BlockStack>
              <BlockStack gap="200">
                <Text variant="headingSm" as="h3">Why subscribe annually?</Text>
                <Text variant="bodySm" as="p" tone="subdued">
                  Annual plans give you 2 months free compared to monthly billing.
                  That's $190/year instead of $228 on Pro, or $290/year instead of $348 on Unlimited.
                </Text>
              </BlockStack>
            </BlockStack>
          </Card>
        </Layout.Section>
      </Layout>
    </Page>
  );
}
