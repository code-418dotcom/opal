/**
 * App layout — wraps all /app/* routes with Shopify AppProvider + Polaris.
 * Handles authentication check on every navigation.
 * Provides NavMenu for embedded app sidebar navigation.
 */
import type { LoaderFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { Link, Outlet, useLoaderData, useRouteError } from "@remix-run/react";
import { NavMenu } from "@shopify/app-bridge-react";
import { AppProvider } from "@shopify/shopify-app-remix/react";
import { AppProvider as PolarisAppProvider } from "@shopify/polaris";
import enTranslations from "@shopify/polaris/locales/en.json";

import { authenticate } from "~/shopify.server";

export const loader = async ({ request }: LoaderFunctionArgs) => {
  await authenticate.admin(request);
  return json({
    apiKey: process.env.SHOPIFY_API_KEY || "",
  });
};

export default function AppLayout() {
  const { apiKey } = useLoaderData<typeof loader>();

  return (
    <AppProvider isEmbeddedApp apiKey={apiKey}>
      <PolarisAppProvider i18n={enTranslations}>
        <NavMenu>
          <Link to="/app" rel="home">A/B Tests</Link>
          <Link to="/app/tests/new">Create Test</Link>
          <Link to="/app/settings">Settings</Link>
        </NavMenu>
        <Outlet />
      </PolarisAppProvider>
    </AppProvider>
  );
}

export function ErrorBoundary() {
  const error = useRouteError();
  return (
    <PolarisAppProvider i18n={enTranslations}>
      <div style={{ padding: "2rem" }}>
        <h1>Something went wrong</h1>
        <p>{error instanceof Error ? error.message : "Unknown error"}</p>
      </div>
    </PolarisAppProvider>
  );
}
