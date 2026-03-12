# A/B Image Testing — Backlog

Items remaining after Opal-AB merge (2026-03-12).
Phases 1–5 are complete. See `docs/SHOPIFY_AB_TEST_APP_PLAN.md` for full context.

---

## Testing

- [ ] Write tests for pixel event ingestion + variant attribution
- [ ] Verify web pixel JS bundle < 10KB gzipped
- [ ] Test theme app extension in Dawn theme (Online Store 2.0)

## Integration Testing (Phase 6)

- [ ] Set up Shopify Partner account + dev store
- [ ] Install app on dev store
- [ ] Full E2E: create test → start → visit product → add to cart → checkout → verify metrics
- [ ] Test variant swap + event attribution timing
- [ ] Test edge cases (concurrent tests, deleted products, app uninstall)
- [ ] Load test pixel endpoint (100+ events/sec burst)

## Deployment & App Store (Phase 7)

- [ ] Deploy backend changes to Azure (Opal API)
- [ ] Deploy Shopify app (Cloudflare Workers or Vercel)
- [ ] `shopify app deploy` — push extensions to Shopify CDN
- [ ] Prepare app listing (name, description, screenshots, privacy policy)
- [ ] Submit for Shopify App Store review

## Future (v2)

- [ ] Pricing model — separate Shopify app charge vs Opal subscription tier? (D8: skipped for v1)
- [ ] Client-side image swap — faster but fragile across themes
- [ ] Multi-variant A/B/C/D support — current schema is A vs B only
- [ ] Auto-swap scheduling — e.g., 1 week per variant
- [ ] Audience segmentation — device type, geography
