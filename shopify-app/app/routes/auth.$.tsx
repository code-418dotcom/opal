/**
 * Shopify OAuth catch-all route.
 * Handles /auth/login, /auth/callback, etc.
 */
import type { LoaderFunctionArgs } from "@remix-run/node";
import { authenticate } from "~/shopify.server";

export const loader = async ({ request }: LoaderFunctionArgs) => {
  await authenticate.admin(request);
  // Auth will redirect as needed — this should not render.
  return null;
};
