/**
 * Entitlement checks — determines what a merchant can do based on their plan.
 *
 * Billing sources:
 * 1. Shopify subscription (Pro / Unlimited plan via Shopify billing API)
 * 2. Opal platform subscription (checked via Opal API integration metadata)
 * 3. Free tier (default — limited features)
 */
import {
  MONTHLY_PRO, ANNUAL_PRO,
  MONTHLY_UNLIMITED, ANNUAL_UNLIMITED,
  FREE_TIER_MAX_TESTS, PRO_TIER_MAX_TESTS, FREE_TIER_MAX_DAYS,
  FREE_TIER_MAX_MONTHLY_VIEWS,
} from "~/shopify.server";
import { listTests, updateEventLimit, getViewUsage } from "~/lib/opal-api.server";

export type PlanTier = "free" | "pro" | "unlimited";

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
  /** Monthly view usage (free tier tracking) */
  monthlyViews: number;
  /** Monthly view limit (null = unlimited) */
  monthlyViewLimit: number | null;
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
      plans: [MONTHLY_PRO, ANNUAL_PRO, MONTHLY_UNLIMITED, ANNUAL_UNLIMITED] as const,
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
  const isUnlimited = shopifyPlan === MONTHLY_UNLIMITED || shopifyPlan === ANNUAL_UNLIMITED;
  const isPro = shopifyPlan === MONTHLY_PRO || shopifyPlan === ANNUAL_PRO;
  const tier: PlanTier = isUnlimited ? "unlimited" : isPro ? "pro" : opalSubscription ? "pro" : "free";

  // 4. Check running test count + view usage
  let runningTestCount = 0;
  let monthlyViews = 0;
  if (integrationId) {
    try {
      const [tests, viewUsage] = await Promise.all([
        listTests(integrationId),
        getViewUsage(integrationId),
      ]);
      runningTestCount = tests.filter((t) => t.status === "running").length;
      monthlyViews = viewUsage.monthly_views;
    } catch {
      // If we can't fetch, assume 0
    }
  }

  // 5. Compute entitlements
  const maxConcurrentTests = isUnlimited ? Infinity : isPro ? PRO_TIER_MAX_TESTS : FREE_TIER_MAX_TESTS;
  const maxTestDays = tier === "free" ? FREE_TIER_MAX_DAYS : null;
  const monthlyViewLimit = tier === "free" ? FREE_TIER_MAX_MONTHLY_VIEWS : null;
  const autoConcludes = tier !== "free";

  let canCreateTest = true;
  let createTestBlockReason: string | null = null;

  if (tier === "free" && runningTestCount >= FREE_TIER_MAX_TESTS) {
    canCreateTest = false;
    createTestBlockReason = `Free plan allows ${FREE_TIER_MAX_TESTS} concurrent test. Upgrade to Pro for up to ${PRO_TIER_MAX_TESTS} tests.`;
  } else if (tier === "pro" && runningTestCount >= PRO_TIER_MAX_TESTS) {
    canCreateTest = false;
    createTestBlockReason = `Pro plan allows ${PRO_TIER_MAX_TESTS} concurrent tests. Upgrade to Unlimited for unlimited tests.`;
  }

  // 6. Sync event limit to backend (fire-and-forget)
  if (integrationId) {
    const eventLimit = tier === "free" ? FREE_TIER_MAX_MONTHLY_VIEWS : null;
    updateEventLimit(integrationId, eventLimit).catch(() => {
      // Non-critical — don't block entitlement check
    });
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
    monthlyViews,
    monthlyViewLimit,
  };
}
