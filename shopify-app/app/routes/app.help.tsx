/**
 * Help page — FAQ, getting started guide, and support links.
 */
import { useNavigate } from "@remix-run/react";
import {
  Page,
  Layout,
  Card,
  BlockStack,
  InlineStack,
  Text,
  Button,
  Divider,
  Badge,
  Box,
  Banner,
  List,
} from "@shopify/polaris";

import { OpalLogo } from "~/components/OpalLogo";

export default function Help() {
  const navigate = useNavigate();

  return (
    <Page title={<InlineStack gap="200" blockAlign="center"><OpalLogo size={24} /> Help & Support</InlineStack> as any} backAction={{ onAction: () => navigate("/app") }}>
      <Layout>
        {/* Quick start */}
        <Layout.Section>
          <Card>
            <BlockStack gap="400">
              <InlineStack gap="300" blockAlign="center">
                <OpalLogo size={32} />
                <Text variant="headingMd" as="h2">
                  How Opal A/B works
                </Text>
              </InlineStack>
              <Divider />
              <BlockStack gap="300">
                <BlockStack gap="050">
                  <InlineStack gap="200" blockAlign="center">
                    <Badge tone="info">1</Badge>
                    <Text variant="headingSm" as="h3">Configure the pixel</Text>
                  </InlineStack>
                  <Text variant="bodySm" as="p" tone="subdued">
                    Go to Settings and click "Configure Pixel." This installs a lightweight
                    tracking pixel on your storefront that captures product views, add-to-carts,
                    and conversions. It runs in Shopify's sandboxed environment and collects no
                    personal customer data.
                  </Text>
                </BlockStack>
                <BlockStack gap="050">
                  <InlineStack gap="200" blockAlign="center">
                    <Badge tone="info">2</Badge>
                    <Text variant="headingSm" as="h3">Create a test</Text>
                  </InlineStack>
                  <Text variant="bodySm" as="p" tone="subdued">
                    Pick a product and select two images to compare. For example, test a lifestyle
                    shot against a white-background image, or try different angles. Give each variant
                    a descriptive label.
                  </Text>
                </BlockStack>
                <BlockStack gap="050">
                  <InlineStack gap="200" blockAlign="center">
                    <Badge tone="info">3</Badge>
                    <Text variant="headingSm" as="h3">Start the test</Text>
                  </InlineStack>
                  <Text variant="bodySm" as="p" tone="subdued">
                    When you start, Variant A is pushed to your storefront as the primary product
                    image. The pixel begins tracking how it performs. Use the "Swap variant" button
                    to switch to Variant B periodically.
                  </Text>
                </BlockStack>
                <BlockStack gap="050">
                  <InlineStack gap="200" blockAlign="center">
                    <Badge tone="info">4</Badge>
                    <Text variant="headingSm" as="h3">Watch the results</Text>
                  </InlineStack>
                  <Text variant="bodySm" as="p" tone="subdued">
                    Opal tracks views, add-to-carts, conversions, and revenue for each variant.
                    The statistical significance gauge shows how confident you can be in the results.
                    Wait until it reaches 95% before making a decision.
                  </Text>
                </BlockStack>
                <BlockStack gap="050">
                  <InlineStack gap="200" blockAlign="center">
                    <Badge tone="info">5</Badge>
                    <Text variant="headingSm" as="h3">Pick the winner</Text>
                  </InlineStack>
                  <Text variant="bodySm" as="p" tone="subdued">
                    When significance is reached, conclude the test and pick the winning image.
                    It stays as your product's primary image on your storefront.
                    On Pro/Unlimited plans, tests can auto-conclude when a clear winner emerges.
                  </Text>
                </BlockStack>
              </BlockStack>
            </BlockStack>
          </Card>
        </Layout.Section>

        {/* FAQ */}
        <Layout.Section>
          <Card>
            <BlockStack gap="400">
              <Text variant="headingMd" as="h2">Frequently asked questions</Text>
              <Divider />

              <BlockStack gap="200">
                <Text variant="headingSm" as="h3">How does the pixel tracking work?</Text>
                <Text variant="bodySm" as="p" tone="subdued">
                  The Opal pixel runs inside Shopify's Web Pixel sandbox — a secure, isolated
                  environment that has no access to personal customer data. It captures three
                  event types: product page views, add-to-cart clicks, and checkout conversions
                  (with order revenue). Events are batched and sent to our server every 5 seconds.
                </Text>
              </BlockStack>

              <BlockStack gap="200">
                <Text variant="headingSm" as="h3">How many visitors do I need for a valid test?</Text>
                <Text variant="bodySm" as="p" tone="subdued">
                  As a rule of thumb, aim for at least 200 views per variant (400 total) before
                  making a decision. Products with lower conversion rates may need more traffic.
                  The significance gauge on the test detail page tells you exactly when you have
                  enough data.
                </Text>
              </BlockStack>

              <BlockStack gap="200">
                <Text variant="headingSm" as="h3">How long should I run a test?</Text>
                <Text variant="bodySm" as="p" tone="subdued">
                  Run until the statistical significance gauge reaches 95%. This typically takes
                  1-4 weeks depending on your product traffic. Avoid ending tests early — the
                  results may not be reliable. On paid plans, Opal can auto-conclude tests when
                  significance is reached.
                </Text>
              </BlockStack>

              <BlockStack gap="200">
                <Text variant="headingSm" as="h3">Should I swap variants during the test?</Text>
                <Text variant="bodySm" as="p" tone="subdued">
                  Yes! Swapping variants every few days helps account for time-based patterns
                  (weekday vs. weekend traffic, seasonal effects). The pixel tracks which variant
                  was active at the time of each event, so your data stays accurate.
                </Text>
              </BlockStack>

              <BlockStack gap="200">
                <Text variant="headingSm" as="h3">What does "statistical significance" mean?</Text>
                <Text variant="bodySm" as="p" tone="subdued">
                  Statistical significance means the difference in conversion rates between your
                  two variants is unlikely to be due to random chance. At 95% confidence, there's
                  only a 5% probability the result is a fluke. Opal uses a standard z-test to
                  calculate this.
                </Text>
              </BlockStack>

              <BlockStack gap="200">
                <Text variant="headingSm" as="h3">What images should I test?</Text>
                <Text variant="bodySm" as="p" tone="subdued">
                  Test images that are meaningfully different — lifestyle vs. plain background,
                  different angles, with vs. without packaging, or model vs. product-only shots.
                  Small differences (like slightly different crops) usually don't produce
                  significant results.
                </Text>
              </BlockStack>

              <BlockStack gap="200">
                <Text variant="headingSm" as="h3">Does the pixel slow down my store?</Text>
                <Text variant="bodySm" as="p" tone="subdued">
                  No. The pixel runs asynchronously in Shopify's sandboxed environment and has
                  zero impact on your storefront's load time. Events are batched and sent in
                  the background using keepalive requests.
                </Text>
              </BlockStack>

              <BlockStack gap="200">
                <Text variant="headingSm" as="h3">What happens to my data if I uninstall?</Text>
                <Text variant="bodySm" as="p" tone="subdued">
                  Your test data and results are preserved for 90 days after uninstalling.
                  You can request full data deletion by contacting support@opaloptics.com.
                  We comply with all Shopify and GDPR data deletion requirements.
                </Text>
              </BlockStack>
            </BlockStack>
          </Card>
        </Layout.Section>

        {/* Best practices */}
        <Layout.Section>
          <Card>
            <BlockStack gap="400">
              <Text variant="headingMd" as="h2">Best practices</Text>
              <Divider />
              <List type="bullet">
                <List.Item>
                  <strong>Test one thing at a time.</strong> Don't change your product title or price during an image test — you want to isolate the image's impact.
                </List.Item>
                <List.Item>
                  <strong>Start with your best sellers.</strong> High-traffic products reach significance faster and have the biggest revenue impact.
                </List.Item>
                <List.Item>
                  <strong>Swap variants regularly.</strong> Every 2-3 days is ideal for most stores. This controls for day-of-week effects.
                </List.Item>
                <List.Item>
                  <strong>Don't peek and decide early.</strong> Wait for 95% significance. Early results can be misleading — patience pays off.
                </List.Item>
                <List.Item>
                  <strong>Test continuously.</strong> After finding a winner, create a new test with a fresh challenger. There's always room to improve.
                </List.Item>
              </List>
            </BlockStack>
          </Card>
        </Layout.Section>

        {/* Contact */}
        <Layout.Section>
          <Card>
            <BlockStack gap="300">
              <Text variant="headingMd" as="h2">Contact support</Text>
              <Divider />
              <Text variant="bodyMd" as="p">
                Need help? We typically respond within 24 hours on business days.
              </Text>
              <BlockStack gap="200">
                <Text variant="bodySm" as="p">
                  <strong>Email:</strong>{" "}
                  <a href="mailto:support@opaloptics.com">support@opaloptics.com</a>
                </Text>
                <Text variant="bodySm" as="p">
                  <strong>Privacy & data requests:</strong>{" "}
                  <a href="mailto:privacy@opaloptics.com">privacy@opaloptics.com</a>
                </Text>
              </BlockStack>
              <Divider />
              <InlineStack gap="300">
                <Button url="https://opaloptics.com/support" external>
                  Visit support page
                </Button>
                <Button url="https://opaloptics.com/privacy" external variant="plain">
                  Privacy policy
                </Button>
                <Button url="https://opaloptics.com/terms" external variant="plain">
                  Terms of service
                </Button>
              </InlineStack>
            </BlockStack>
          </Card>
        </Layout.Section>

        {/* Cross-sell */}
        <Layout.Section>
          <Card>
            <InlineStack gap="400" blockAlign="center">
              <OpalLogo size={36} />
              <BlockStack gap="100">
                <Text variant="headingSm" as="h3">
                  Generate winning images with Opal
                </Text>
                <Text variant="bodySm" as="p" tone="subdued">
                  Use AI to create studio-quality product photos — remove backgrounds,
                  generate scenes, and upscale. Then A/B test them right here.
                </Text>
                <Box>
                  <Button url="https://opaloptics.com" external size="slim">
                    Try Opal Image Studio
                  </Button>
                </Box>
              </BlockStack>
            </InlineStack>
          </Card>
        </Layout.Section>
      </Layout>
    </Page>
  );
}
