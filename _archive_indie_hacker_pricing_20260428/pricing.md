# Pricing

hermes-rubric is MIT-licensed. You can run it in production commercially, forever, without paying us.

The tiers below are for teams that want API access, managed scoring pipelines, or to bundle rubric scoring into a larger Hermes Labs audit engagement.

---

## Tiers

### Trivial — Free

- `pip install hermes-rubric`
- Full CLI + Python library
- All features: rubric synthesis, evidence collection, scoring, receipts
- All backends: claude-cli, ollama-local
- All calibration data + failure-mode taxonomy
- No limits, no telemetry, no account required

**When to use:** individual use, research, prototyping, CI pipelines, commercial use.

---

### Team — $99/month

- Everything in Free
- Hosted scoring API (no local LLM required — we run the inference)
- Team dashboard: score history, per-project rubric library, receipt archive
- Shared rubric library (import a teammate's rubric as a baseline)
- Priority email support

**When to use:** teams running scoring at scale, teams without local LLM infrastructure, teams that need a persistent audit trail they don't self-host.

**To sign up:** [Checkout →](#checkout)

---

### Enterprise — $500/month

- Everything in Team
- Custom rubric synthesis (we build the initial rubric for your domain, iterate with your team)
- SLA: 99.9% API uptime, <2h support response
- SSO + SCIM
- On-premise deployment option (run the scoring server inside your VPC)
- Integration into hermes-bundle evidence bundles (scoring results pinned in sealed audit deliverables)

**When to use:** compliance teams, audit firms, regulated-industry AI teams that need scoring results in EU AI Act evidence bundles.

**To sign up:** email [roli@hermes-labs.ai](mailto:roli@hermes-labs.ai)

---

## Checkout

!!! note "Team plan checkout coming soon"
    Stripe checkout will be wired here. For early access at $99/mo, email [roli@hermes-labs.ai](mailto:roli@hermes-labs.ai) and reference "Team Plan."

---

## hermes-bundle (enterprise audit deliverables)

If you need sealed, cryptographically verifiable EU AI Act evidence bundles — not just scoring — that's `hermes-bundle`, a separate proprietary product.

Pricing: $5K design-partner pilot → $25K-$40K annual. Contact [roli@hermes-labs.ai](mailto:roli@hermes-labs.ai).

---

## FAQ

**Can I use the free tier in production?**
Yes. MIT license, no restrictions on commercial use.

**Will Team plan features ever be paywalled in the free tier?**
No. Hermes Labs OSS philosophy: features don't migrate from free to paid. New paid features are additive (API, dashboard, managed inference).

**Can I self-host the scoring server?**
Enterprise tier includes the on-premise option. Team tier is hosted-only.
