<wizard-report>
# PostHog post-wizard report

The wizard has completed a deep integration of PostHog analytics into the Bargain Hunters Next.js web app. Here is a summary of every change made:

- **`instrumentation-client.ts`** (new) — Initialises PostHog client-side using the Next.js 15.3+ `instrumentation-client` pattern. Enables session replay, auto-capture, and error tracking via `capture_exceptions: true`. Proxies requests through `/ingest` to avoid ad-blockers.
- **`next.config.js`** — Added `/ingest/*` reverse-proxy rewrites pointing to the EU PostHog ingestion endpoint (`eu.i.posthog.com`), plus `skipTrailingSlashRedirect: true`.
- **`.env.local`** — `NEXT_PUBLIC_POSTHOG_PROJECT_TOKEN` and `NEXT_PUBLIC_POSTHOG_HOST` written (EU host).
- **`src/store/auth.tsx`** — Added `posthog.identify()` after login (with user ID, email, name, plan tier as person properties) and `posthog.reset()` on logout.
- **`src/app/login/page.tsx`** — Captures `user_logged_in` on successful submit; `captureException` on error.
- **`src/app/register/page.tsx`** — Captures `user_signed_up` + `posthog.identify()` on successful registration; `captureException` on error.
- **`src/app/(app)/profile/page.tsx`** — Captures `profile_updated` (with `updated_fields` list) and `user_logged_out`; `captureException` on profile save error.
- **`src/app/(app)/upgrade/page.tsx`** — Captures `upgrade_payment_initiated` (amount, payment method) on M-Pesa payment success; `captureException` on error.
- **`src/app/(app)/alerts/new/page.tsx`** — Captures `deal_alert_created` (target type, ID, name) on success; `captureException` on error.
- **`src/app/(app)/deals/page.tsx`** — Captures `deal_alert_created_from_deal_card` (deal ID, product info, price, discount) when subscribing from a deal card; `captureException` on error.
- **`src/app/(app)/subscriptions/page.tsx`** — Captures `alert_paused`, `alert_resumed`, and `alert_deleted` on the respective mutation successes.
- **`src/components/DealCard.tsx`** — Captures `deal_link_clicked` (deal ID, product, retailer, price, discount) on the View external link click.
- **`src/components/ShoppingList/index.tsx`** — Captures `shopping_list_created`, `shopping_list_deleted`, `shopping_list_optimised` (with mode and item count), and `shopping_list_shared` (with savings totals).

## Events

| Event | Description | File |
|---|---|---|
| `user_signed_up` | User successfully created a new account | `src/app/register/page.tsx` |
| `user_logged_in` | User successfully signed in | `src/app/login/page.tsx` |
| `user_logged_out` | User signed out | `src/app/(app)/profile/page.tsx` |
| `profile_updated` | User saved profile changes (email or DOB) | `src/app/(app)/profile/page.tsx` |
| `deal_alert_created` | Alert subscription created via the alerts page | `src/app/(app)/alerts/new/page.tsx` |
| `deal_alert_created_from_deal_card` | Alert created directly from a deal card | `src/app/(app)/deals/page.tsx` |
| `deal_link_clicked` | User clicked View link to retailer site | `src/components/DealCard.tsx` |
| `alert_paused` | User paused an active alert subscription | `src/app/(app)/subscriptions/page.tsx` |
| `alert_resumed` | User resumed a paused alert subscription | `src/app/(app)/subscriptions/page.tsx` |
| `alert_deleted` | User permanently removed an alert | `src/app/(app)/subscriptions/page.tsx` |
| `upgrade_payment_initiated` | M-Pesa payment submitted for Premium upgrade | `src/app/(app)/upgrade/page.tsx` |
| `shopping_list_created` | User created a new shopping list | `src/components/ShoppingList/index.tsx` |
| `shopping_list_deleted` | User deleted a shopping list | `src/components/ShoppingList/index.tsx` |
| `shopping_list_optimised` | User ran Find Best Deals optimisation | `src/components/ShoppingList/index.tsx` |
| `shopping_list_shared` | User copied the optimised plan to clipboard | `src/components/ShoppingList/index.tsx` |

## Next steps

We've built some insights and a dashboard for you to keep an eye on user behavior, based on the events we just instrumented:

- [Analytics basics (wizard) — Dashboard](https://eu.posthog.com/project/200019/dashboard/742393)
- [New signups over time](https://eu.posthog.com/project/200019/insights/3dGZ2J2h)
- [Deal alerts created over time](https://eu.posthog.com/project/200019/insights/tuqOWjGB)
- [Deal link clicks over time](https://eu.posthog.com/project/200019/insights/X4qZXo8A)
- [Shopping list optimisations & shares](https://eu.posthog.com/project/200019/insights/ckTPpxiA)
- [Signup → Alert → Premium upgrade funnel](https://eu.posthog.com/project/200019/insights/uUMSwF6R)

### Agent skill

We've left an agent skill folder in your project at `.claude/skills/integration-nextjs-app-router/`. You can use this context for further agent development when using Claude Code. This will help ensure the model provides the most up-to-date approaches for integrating PostHog.

</wizard-report>
