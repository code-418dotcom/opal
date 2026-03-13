/**
 * Entitlement checks — determines what a merchant can do based on their plan.
 *
 * Billing sources:
 * 1. Shopify subscription (Pro plan via Shopify billing API)
 * 2. Opal platform subscription (checked via Opal API integration metadata)
 * 3. Free tier (default — limited features)
 */
import { MONTHLY_PRO, ANNUAL_PRO, FREE_TIER_MAX_TESTS, FREE_TIER_MAX_DAYS } from "~/shopify.server";
import { listTests } from "~/lib/opal-api.server";

export type PlanTier = "free" | "pro";

export interface Entitlements {
  tier: PlanTier;
  /** Shopify subscription plan name, if any */
  shopifyPlan: string | null;
  /** Whether the merchant has an Opal platform subscription */
  opalSubscription: boolean;
  /** Max concurrent running tests allowed */
  maxConcurrentTests: number;
  /** Max test duration in days (null = unlimited) */
  maxTestDays: number | null;
  /** Whether auto-conclude is available */
  autoConcludes: boolean;
  /** Whether the merchant can create a new test right now */
  canCreateTest: boolean;
  /** Reason if canCreateTest is false */
  createTestBlockReason: string | null;
  /** Number of currently running tests */
  runningTestCount: number;
}

/**
 * Check a merchant's entitlements by examining Shopify billing and Opal integration.
 */
export async function getEntitlements(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  billing: any,
  integrationId: string | null,
): Promise<Entitlements> {
  // 1. Check Shopify billing
  let shopifyPlan: string | null = null;
  try {
    const { hasActivePayment, appSubscriptions } = await billing.check({
      plans: [MONTHLY_PRO, ANNUAL_PRO] as const,
      isTest: true, // Allow test charges during development
    });
    if (hasActivePayment && appSubscriptions.length > 0) {
      shopifyPlan = appSubscriptions[0].name;
    }
  } catch {
    // billing.check can fail if billing not configured — treat as no subscription
  }

  // 2. Check Opal platform subscription (via integration metadata)
  // TODO: Add endpoint to check if the integration's user has an active Opal subscription
  const opalSubscription = false;

  // 3. Determine tier
  const isPro = shopifyPlan !== null || opalSubscription;
  const tier: PlanTier = isPro ? "pro" : "free";

  // 4. Check running test count
  let runningTestCount = 0;
  if (integrationId) {
    try {
      const tests = await listTests(integrationId);
      runningTestCount = tests.filter((t) => t.status === "running").length;
    } catch {
      // If we can't fetch tests, assume 0
    }
  }

  // 5. Compute entitlements
  const maxConcurrentTests = isPro ? Infinity : FREE_TIER_MAX_TESTS;
  const maxTestDays = isPro ? null : FREE_TIER_MAX_DAYS;
  const autoConcludes = isPro;

  let canCreateTest = true;
  let createTestBlockReason: string | null = null;

  if (!isPro && runningTestCount >= FREE_TIER_MAX_TESTS) {
    canCreateTest = false;
    createTestBlockReason = `Free plan allows ${FREE_TIER_MAX_TESTS} concurrent test. Upgrade to Pro for unlimited tests.`;
  }

  return {
    tier,
    shopifyPlan,
    opalSubscription,
    maxConcurrentTests,
    maxTestDays,
    autoConcludes,
    canCreateTest,
    createTestBlockReason,
    runningTestCount,
  };
}
