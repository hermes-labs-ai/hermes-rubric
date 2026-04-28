# Stripe Checkout Setup

**For Roli to wire — requires Stripe account access. Claude cannot do this autonomously.**

---

## Stripe products to create

### Product 1: hermes-rubric Team Plan

| Field | Value |
|---|---|
| Product name | hermes-rubric Team Plan |
| Description | Hosted scoring API + team dashboard + shared rubric library. No local LLM required. |
| Pricing | $99.00 / month (recurring) |
| Currency | USD |
| Billing interval | Monthly |
| Product ID (set after creation) | prod_team_XXXX |
| Price ID (set after creation) | price_team_XXXX |

### Product 2: hermes-rubric Enterprise Plan

| Field | Value |
|---|---|
| Product name | hermes-rubric Enterprise Plan |
| Description | Team plan + custom rubric synthesis + SLA + SSO + on-premise deployment option. |
| Pricing | $500.00 / month (recurring) |
| Currency | USD |
| Billing interval | Monthly |
| Product ID (set after creation) | prod_enterprise_XXXX |
| Price ID (set after creation) | price_enterprise_XXXX |

---

## Where the Checkout button goes

In `docs/pricing.md`, replace the "Checkout coming soon" admonition block with:

```html
<a href="https://checkout.stripe.com/pay/YOUR_PAYMENT_LINK_HERE" class="md-button md-button--primary">
  Start Team Plan — $99/mo
</a>
```

MkDocs Material supports raw HTML blocks in markdown. The button will render inline.

Alternatively, use a Stripe Payment Link (simpler than full Checkout integration):
1. Stripe Dashboard → Products → hermes-rubric Team Plan → Create payment link
2. Copy the `https://buy.stripe.com/XXXX` URL
3. Drop it in the `<a href="...">` above

For Enterprise: replace with `mailto:rbosch@lpci.ai?subject=Enterprise%20Plan%20Inquiry` (no Checkout needed — direct email).

---

## Success-redirect URL pattern

For Payment Links, configure the confirmation page in Stripe Dashboard:
- **Success URL:** `https://hermes-labs-ai.github.io/hermes-rubric/pricing/?checkout=success`
- **Cancel URL:** `https://hermes-labs-ai.github.io/hermes-rubric/pricing/`

If self-hosting the docs site on a custom domain (e.g. `docs.hermes-labs.ai`), update accordingly.

---

## Post-purchase flow (manual until webhook is wired)

Until a webhook listener is built:
1. Stripe sends confirmation email to customer
2. You receive a Stripe email with customer details
3. Manually provision API key and add to team dashboard

When volume justifies it, wire a Stripe webhook to auto-provision:
- Event: `checkout.session.completed`
- Endpoint: `/api/stripe/webhook` (to be built)
- Action: create team account, issue API key, send welcome email

---

## Test mode first

Before going live:
1. Use Stripe test mode (toggle in Dashboard)
2. Test card: `4242 4242 4242 4242`, any future date, any CVC
3. Verify success redirect works
4. Switch to live mode when confirmed

---

**Estimated Roli time:** 20-30 min (create 2 products + payment links + update pricing.md)
