/**
 * Login page — shown when the merchant needs to install/reinstall the app.
 * Branded with Opal logo and links to legal pages.
 */
import type { ActionFunctionArgs, LoaderFunctionArgs } from "@remix-run/node";
import { json } from "@remix-run/node";
import { Form, useActionData, useLoaderData } from "@remix-run/react";

import { login } from "~/shopify.server";
import { OpalLogo } from "~/components/OpalLogo";

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
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        background: "linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%)",
        padding: "2rem",
      }}
    >
      <div
        style={{
          maxWidth: "420px",
          width: "100%",
          background: "#fff",
          borderRadius: "16px",
          padding: "2.5rem",
          boxShadow: "0 20px 60px rgba(0, 0, 0, 0.3)",
        }}
      >
        {/* Logo + branding */}
        <div style={{ textAlign: "center", marginBottom: "2rem" }}>
          <OpalLogo size={64} />
          <h1
            style={{
              fontSize: "1.75rem",
              fontWeight: 700,
              color: "#1e293b",
              margin: "0.75rem 0 0.25rem",
              letterSpacing: "-0.02em",
            }}
          >
            Opal A/B
          </h1>
          <p style={{ color: "#64748b", fontSize: "0.875rem", margin: 0 }}>
            A/B image testing for Shopify
          </p>
        </div>

        <Form method="post">
          <label
            htmlFor="shop"
            style={{
              display: "block",
              marginBottom: "0.5rem",
              fontSize: "0.875rem",
              fontWeight: 500,
              color: "#374151",
            }}
          >
            Shop domain
          </label>
          <input
            type="text"
            name="shop"
            id="shop"
            placeholder="mystore.myshopify.com"
            style={{
              width: "100%",
              padding: "0.75rem 1rem",
              marginBottom: "1rem",
              border: "1px solid #d1d5db",
              borderRadius: "8px",
              fontSize: "0.9375rem",
              outline: "none",
              boxSizing: "border-box",
              transition: "border-color 0.15s",
            }}
          />
          <button
            type="submit"
            style={{
              width: "100%",
              padding: "0.75rem",
              background: "linear-gradient(135deg, #4dc9f6 0%, #7c6cf7 100%)",
              color: "white",
              border: "none",
              borderRadius: "8px",
              fontSize: "0.9375rem",
              fontWeight: 600,
              cursor: "pointer",
              transition: "opacity 0.15s",
            }}
          >
            Log in
          </button>
        </Form>
      </div>

      {/* Footer */}
      <div
        style={{
          marginTop: "2rem",
          textAlign: "center",
          fontSize: "0.75rem",
          color: "#94a3b8",
        }}
      >
        <p style={{ margin: "0 0 0.5rem" }}>by Aardvark Hosting</p>
        <div style={{ display: "flex", gap: "1rem", justifyContent: "center" }}>
          <a href="https://opaloptics.com/privacy" target="_blank" rel="noopener noreferrer" style={{ color: "#94a3b8" }}>
            Privacy
          </a>
          <a href="https://opaloptics.com/terms" target="_blank" rel="noopener noreferrer" style={{ color: "#94a3b8" }}>
            Terms
          </a>
          <a href="https://opaloptics.com/support" target="_blank" rel="noopener noreferrer" style={{ color: "#94a3b8" }}>
            Support
          </a>
        </div>
      </div>
    </div>
  );
}
