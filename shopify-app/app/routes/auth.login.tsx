/**
 * Login page — shown when the merchant needs to install/reinstall the app.
 */
import type { ActionFunctionArgs, LoaderFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { Form, useActionData, useLoaderData } from "@remix-run/react";

import { login } from "~/shopify.server";

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const errors = login(request);
  return json({ errors, polarisTranslations: {} });
};

export const action = async ({ request }: ActionFunctionArgs) => {
  const errors = login(request);
  return json({ errors });
};

export default function Auth() {
  const { errors } = useLoaderData<typeof loader>();
  const actionData = useActionData<typeof action>();

  return (
    <div style={{ display: "flex", justifyContent: "center", padding: "4rem" }}>
      <div style={{ maxWidth: "400px", width: "100%" }}>
        <h1 style={{ marginBottom: "1rem" }}>Opal A/B</h1>
        <Form method="post">
          <label htmlFor="shop" style={{ display: "block", marginBottom: "0.5rem" }}>
            Shop domain
          </label>
          <input
            type="text"
            name="shop"
            id="shop"
            placeholder="mystore.myshopify.com"
            style={{
              width: "100%",
              padding: "0.5rem",
              marginBottom: "1rem",
              border: "1px solid #ccc",
              borderRadius: "4px",
            }}
          />
          <button
            type="submit"
            style={{
              width: "100%",
              padding: "0.75rem",
              backgroundColor: "#008060",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
            }}
          >
            Log in
          </button>
        </Form>
      </div>
    </div>
  );
}
