/**
 * Shopify webhook handler — mandatory GDPR webhooks.
 * Shopify requires these for App Store approval.
 */
import type { ActionFunctionArgs } from "@remix-run/node";
import { authenticate } from "~/shopify.server";

export const action = async ({ request }: ActionFunctionArgs) => {
  const { topic, shop, payload } = await authenticate.webhook(request);

  switch (topic) {
    case "APP_UNINSTALLED":
      // Clean up: could notify Opal to deactivate integration
      console.log(`App uninstalled from ${shop}`);
      break;

    case "CUSTOMERS_DATA_REQUEST":
      // GDPR: customer data request
      console.log(`Customer data request from ${shop}`, payload);
      break;

    case "CUSTOMERS_REDACT":
      // GDPR: customer data deletion
      console.log(`Customer data redact from ${shop}`, payload);
      break;

    case "SHOP_REDACT":
      // GDPR: shop data deletion (48 hours after uninstall)
      console.log(`Shop redact for ${shop}`, payload);
      break;

    default:
      console.log(`Unhandled webhook topic: ${topic}`);
  }

  return new Response(null, { status: 200 });
};
