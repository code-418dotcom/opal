/**
 * Shopify app configuration for embedded admin.
 * Handles OAuth, session management, and API client creation.
 */
import "@shopify/shopify-app-remix/adapters/node";
import {
  AppDistribution,
  BillingInterval,
  shopifyApp,
  LATEST_API_VERSION,
} from "@shopify/shopify-app-remix/server";

// ── Billing Plans ───────────────────────────────────────────────────
// Free tier: 1 concurrent test, manual conclude, 30-day max (no plan needed)
// Pro tier: 10 concurrent tests, auto-conclude, full analytics ($19/mo)
// Unlimited tier: unlimited tests, auto-conclude, full analytics ($29/mo)
export const MONTHLY_PRO = "Opal A/B Pro";
export const ANNUAL_PRO = "Opal A/B Pro Annual";
export const MONTHLY_UNLIMITED = "Opal A/B Unlimited";
export const ANNUAL_UNLIMITED = "Opal A/B Unlimited Annual";

export const FREE_TIER_MAX_TESTS = 1;
export const PRO_TIER_MAX_TESTS = 10;
export const FREE_TIER_MAX_DAYS = 30;
export const FREE_TIER_MAX_MONTHLY_VIEWS = 1000;
import { SQLiteSessionStorage } from "@shopify/shopify-app-session-storage-sqlite";

const shopify = shopifyApp({
  apiKey: process.env.SHOPIFY_API_KEY!,
  apiSecretKey: process.env.SHOPIFY_API_SECRET || "",
  apiVersion: LATEST_API_VERSION,
  scopes: process.env.SCOPES?.split(",") || [
    "read_products",
    "write_products",
    "read_pixels",
    "write_pixels",
    "read_customer_events",
    "read_metaobjects",
    "write_metaobjects",
  ],
  appUrl: process.env.SHOPIFY_APP_URL || process.env.HOST || "https://localhost",
  sessionStorage: new SQLiteSessionStorage("sessions.sqlite"),
  authPathPrefix: "/auth",
  distribution: AppDistribution.AppStore,
  billing: {
    [MONTHLY_PRO]: {
      lineItems: [
        {
          amount: 19,
          currencyCode: "USD",
          interval: BillingInterval.Every30Days,
        },
      ],
      trialDays: 7,
    },
    [ANNUAL_PRO]: {
      lineItems: [
        {
          amount: 190,
          currencyCode: "USD",
          interval: BillingInterval.Annual,
        },
      ],
      trialDays: 7,
    },
    [MONTHLY_UNLIMITED]: {
      lineItems: [
        {
          amount: 29,
          currencyCode: "USD",
          interval: BillingInterval.Every30Days,
        },
      ],
      trialDays: 7,
    },
    [ANNUAL_UNLIMITED]: {
      lineItems: [
        {
          amount: 290,
          currencyCode: "USD",
          interval: BillingInterval.Annual,
        },
      ],
      trialDays: 7,
    },
  },
  future: {
    unstable_newEmbeddedAuthStrategy: true,
  },
  ...(process.env.SHOP_CUSTOM_DOMAIN
    ? { customShopDomains: [process.env.SHOP_CUSTOM_DOMAIN] }
    : {}),
});

export default shopify;
export const apiVersion = LATEST_API_VERSION;
export const addDocumentResponseHeaders = shopify.addDocumentResponseHeaders;
export const authenticate = shopify.authenticate;
export const unauthenticated = shopify.unauthenticated;
export const login = shopify.login;
export const registerWebhooks = shopify.registerWebhooks;
export const sessionStorage = shopify.sessionStorage;
