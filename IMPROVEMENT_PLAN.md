# WealthTrack — Site Improvement Plan

> Living document. Check off items as they are completed. Work through one item at a time in the order defined in the Master Checklist at the bottom.

---

## 🐛 Bugs

- [x] **B7 — Global `form` rule capped all forms at 600px wide** ✅
  - The global `form { max-width: 600px; display: flex; flex-direction: column }` rule in `styles.css` was turning every `<form>` into a narrow card, breaking the purchase table, admin user table, and any other full-width form. Fixed by removing those properties from the bare `form` selector and moving card-form styling to a new `.form-card` class. `change_username.html` was the only page that needed `.form-card` added.

- [x] **B8 — Hardcoded `#fff` backgrounds broke dark mode on all pages** ✅
  - Every page-level `<style>` block used literal `background: #fff` on card elements. Since page-level styles have higher specificity than the `styles.css` dark mode block, dark mode never reached the cards. Fixed across 11 templates by replacing `#fff` / `#FFFFFF` with `var(--color-surface, #fff)`, which automatically resolves to `#1E293B` in dark mode via the existing CSS custom property.

- [x] **B9 — Table headers globally overridden by `.purchase-table th`, `.users-table thead th`, etc.** ✅
  - Global `th { background-color: var(--color-primary); color: white }` overrode page-level table header styles on the admin, purchase, allocation, and tax-loss harvesting tables. Fixed with `!important` on the page-level `th` rules for each affected table.

- [x] **B10 — Scroll bars appearing in sidebar and account tab bar** ✅
  - `.sidebar` and `.sidebar-section` used `overflow-y: auto`, causing a scrollbar to flash when content was even slightly taller than the viewport. `.acct-tabs` used `overflow-x: auto`, causing a scrollbar to appear in the tab header. Fixed with `scrollbar-width: none` + `webkit-scrollbar: display: none` on those elements. Also added a global thin scrollbar style in `styles.css` to make all other scroll areas use slim, unobtrusive scrollbars.

- [x] **B1 — "No purchases made yet" on Positions page is wrong** ✅
  - `view_positions` was missing the `last_purchase_date` query entirely — fixed by adding the same Purchase join query that `make_purchase` uses and passing it to the template.

- [x] **B3 — Browser tab title is "Flask App" on most pages** ✅
  - `/view_positions`, `/edit_portfolio`, `/reset_password` all render `<title>Flask App</title>`. Every page needs a descriptive, branded title (e.g., "WealthWise — Current Positions").

- [x] **B4 — Edit Portfolio market value column missing dollar sign and formatting** ✅
  - Applied `${{ "%.2f" | format(...) }}` to Current Price and `${{ "{:,.2f}".format(...) }}` to Market Value in `edit_portfolio.html`.

- [x] **B5 — Reset Password page has no back/exit navigation** ✅
  - Added `← Cancel` link back to `manage_user/<user_id>` below the form in `reset_password.html`.

- [x] **B6 — Adjust Allocations: validation that percentages sum to 100%** ✅
  - Live total bar + submit-time guard both block saving unless total is exactly 100%.

---

## 🎨 Design System & Global UI

- [x] **D1 — Establish a consistent design system** ✅
  - Inter font loaded via Google Fonts (was incorrectly loading Roboto).
  - CSS custom properties defined in `:root` for full color palette (primary, success, danger, warning, neutrals, teal, shadows).
  - Unified button classes added: `.btn-primary`, `.btn-success`, `.btn-danger`, `.btn-ghost`.
  - `.back-button` and `.refresh-button` restyled to match `.btn-ghost` (consistent across all pages without touching every template).
  - Raw `<button>` in change_username.html given `.btn-primary` class.

- [x] **D6 — Modernize the header bar** ✅
  - Refreshed the authenticated app shell: tightened top brand/header spacing, polished the market status pill, and replaced the plain footer identity text with a proper profile card + action buttons for Settings, Logout, and Admin.

- [x] **D7 — Market status bar: add color and next-open time** ✅
  - Market status pill is green when open, gray when closed. Next open/close time shown dynamically. CSS polished (removed full-width stretch).

- [x] **D5 — Make the layout responsive (mobile-friendly)** ✅
  - Hamburger drawer + overlay already implemented for ≤768px. Added: hide desktop collapse button on mobile, tablet intermediate breakpoint at 960px (narrower sidebar, tighter padding), responsive stat card stacking, account tab bar adjustments, settings row stacking on small screens.

---

## 🏠 Dashboard & Navigation Overhaul

> Based on the provided mockup. This is the highest-visibility change — it transforms the first impression of the app.

- [x] **DASH1 — Build a Portfolio Overview Dashboard as the post-login landing page** ✅
  - Login now lands on `/dashboard` — a cross-account summary with three charts:
    1. **Portfolio Allocation pie chart** — combined allocation across all accounts by ticker.
    2. **Portfolio Growth line chart** — total portfolio value over time, built from `PortfolioSnapshot` records. "Build Growth Chart" backfill button in empty state.
    3. **Top Performing Assets bar chart** — % gain per holding across all accounts, sorted descending.

- [x] **DASH2 — Add per-account summary cards below the overview charts** ✅
  - Account cards below the charts show: account name, total market value, cost basis, unrealized G/L ($ and %), and quick-action links (View Positions, Make a Purchase).

- [x] **D3 — Replace the per-account "6 buttons" menu page with a proper account detail layout** ✅
  - Account detail page (`/view_account/<id>`) now has summary stat cards (Market Value, Cost Basis, Unrealized G/L, Total Return, Holdings count) and four tabs: Positions (inline table), Recent Activity (last 10 transactions), Allocation (mini doughnut + delta table), and Actions (card grid). Inline rename via pencil icon.

- [x] **D4 — Highlight the active account in navigation** ✅
  - Sidebar account links now show a persistent active state when viewing any page scoped to that account, including the account overview, positions, allocation, purchase, import, and report flows.

---

## 📊 Positions Page (`/view_positions`)

- [x] **D8 — Add cost basis and gain/loss columns** ✅
  - Added: Avg Cost/Share, Unrealized G/L ($), Unrealized G/L (%) — powered by the new `Holding` model with `cost_basis`, `cost_basis_per_share`, `unrealized_gain`, and `unrealized_gain_pct` properties.

- [x] **D9 — Color-code gain/loss values** ✅
  - Green for positive, red for negative — applied across all gain/loss cells in the new positions table.

- [x] **D10 — Add a summary card at the top of the positions page** ✅
  - Summary cards row shows: Total Market Value, Total Cost Basis, Total Unrealized G/L (color-coded).

---

## 📐 Allocation Pages (`/view_allocation`, `/adjust_allocation`)

- [x] **D11 — Add a pie/donut chart to View Allocation** ✅
  - Chart.js donut chart showing current allocation by ticker, with colour-coded legend.

- [x] **D12 — Add color coding + delta column to View Allocation** ✅
  - "Difference" column shows current % − target %. Green if under target (needs buying), red if over target.

- [x] **D13 — Show current allocation alongside inputs in Adjust Allocations** ✅
  - Read-only "Current %" column added next to "Target %" input.

- [x] **D14 — Live-updating total % on Adjust Allocations** ✅
  - Live total bar updates on every keystroke: grey → green at 100%, red if over. Shows remaining or overage.

---

## 🛒 Make a Purchase (`/make_purchase`)

- [x] **D15 — Rename "Enter Current Cash Value" to "Amount to Invest"** ✅
  - Renamed to "Amount to Invest ($)" with description: "Enter the cash you want to deploy across your portfolio targets."

- [x] **D16 — Show all rebalancing suggestions, not just the top stock** ✅
  - `_get_suggested_purchases` now returns ALL included holdings (over-allocated ones get qty=0 and are greyed out). Template shows Symbol, Price, Shares Held, Current %, Target %, Gap, Buy Qty (editable), Est. Cost. Live cost bar tracks total vs budget.

- [x] **D17 — Add a post-purchase success state** ✅
  - Flash messages now use `with_categories=True` in base.html. Success (green), error (red), warning (yellow), info (blue) styled with left-border accent. "Purchase recorded successfully!" flashes on redirect to positions page.

---

## ✏️ Edit Portfolio (`/edit_portfolio`)

- [x] **D18 — Remove the persistent empty row; add a proper "+ Add Holding" button** ✅
  - Replaced the always-visible blank row with a "+ Add Holding" button that appends rows on click.

- [x] **D19 — Add ticker symbol validation** ✅
  - New tickers are validated against Yahoo Finance via `/validate_tickers` before saving. Invalid tickers show an alert and block submission.

---

## ⚙️ Account Management Polish

- [x] **D20 — Add tooltips/labels to the sidebar pencil & star icons** ✅
  - Old ambiguous icon approach replaced with a clearly labeled "Reorder" toggle button in the Accounts section header. Click to enter reorder mode — each account shows ↑↓ chevron buttons with descriptive `title` attributes. Account order is saved to localStorage and restored on page load (no migration required).

- [x] **D21 — Clean up the Manage User Account page layout** ✅
  - Unified button styles across the Settings page. Added a back breadcrumb at the top of the page. Removed the redundant "← Back to Accounts" button at the bottom. All action buttons now use consistent `.btn` classes.

---

## 🗄️ Database Schema Redesign (completed 2026-03-26)

The original `Stock` / `Purchase` / `Position` schema was replaced with a prod-grade financial data model. The database was wiped and rebuilt from scratch.

**Old models (dropped):** `Stock`, `Purchase`, `Position`

**New models:**

| Model | Purpose |
|---|---|
| `Holding` | Current share positions. Fields: `ticker`, `quantity`, `cost_basis` (total), `isincluded`, `last_updated`. Computed properties: `current_price` (live yfinance), `market_value`, `cost_basis_per_share`, `unrealized_gain`, `unrealized_gain_pct`. |
| `Transaction` | Complete financial event log: buy, sell, dividend, transfer, interest, fee, other. Fields: `date`, `action_type`, `raw_action`, `ticker`, `description`, `quantity`, `price`, `fees`, `amount`, `import_source`. |
| `PortfolioSnapshot` | One row per account per day — powers a future growth chart. Fields: `snapshot_date`, `total_market_value`, `total_cost_basis`, `cash_balance`, `dividend_income`. Unique constraint on `(account_id, snapshot_date)`. |

**Canonical `action_type` values:** `buy`, `sell`, `dividend`, `reinvest_dividend`, `reinvest_shares`, `transfer_in`, `transfer_out`, `interest`, `fee`, `other`

---

## 📥 Schwab CSV Import (completed 2026-03-26)

Two-step CSV import flow at `/import/<account_id>`:

**Step 1 — Positions CSV** (`Accounts → Positions → Export` in Schwab web app)
- Parses the non-standard Schwab positions format (account info header + blank line before column headers)
- Upserts `Holding` records: updates quantity + cost_basis for existing holdings, inserts new ones — never deletes
- Re-importable at any time to refresh data

**Step 2 — Transaction History CSV** (`Accounts → History → Export` in Schwab web app)
- Maps 20+ Schwab action strings to canonical `action_type` values
- Handles special date formats like `"03/16/2026 as of 03/15/2026"` (takes first date)
- Handles `$`-prefixed amounts, comma separators, parenthetical negatives `(1,234.56)`
- Deduplicates on `(account_id, date, action_type, ticker, amount)` — safe to re-import

**Files:**
- `flask_app/utils/schwab_parser.py` — `parse_schwab_positions()` and `parse_schwab_transactions()`
- `flask_app/routes/import_data.py` — `import_bp` blueprint with 3 routes
- `flask_app/templates/import.html` — two-section UI with numbered Schwab export instructions

**Roadmap:** Direct Schwab API integration (OAuth) — marked "Coming Soon" in the UI.

---

## 🚀 New Features

- [x] **F1 — Build out the Reports page** ✅
  - Full reports page: portfolio growth chart (market value vs cost basis over time), per-holding performance table (qty, price, MV, cost basis, avg cost/share, G/L, % return with inline bar), transaction summary (total invested, dividends, interest, fees, sell proceeds). Export buttons for positions and transactions CSV.

- [x] **F2 — Transaction / purchase history page per account** ✅
  - Paginated, filterable transaction history at `/view_transactions/<id>`. Filter by type and ticker. "Record Transaction" and "Export CSV" buttons in header.

- [x] **F3 — Sell / record transaction support** ✅
  - `/record_transaction/<id>` — manual entry form for any transaction type (buy, sell, dividend, transfer, interest, fee, other). Sells reduce holding quantity and adjust cost basis proportionally. Buys update or create holdings. Live sell preview shows estimated realized G/L. Auto-calculates amount from qty × price.

- [x] **F4 — Portfolio performance chart (per account)** ✅
  - Per-account growth chart is live on the Reports page — market value vs cost basis line chart powered by PortfolioSnapshot records.

- [x] **F5 — Price caching / rate-limit resilience** ✅
  - `flask_app/utils/price_cache.py` — module-level in-process cache with 15-min TTL. `Holding.current_price` and the dashboard both use `get_price()` / `get_prices()`. Eliminates repeated yfinance calls on a single page load and dramatically reduces 429 rate-limit risk.

- [x] **F6 — Password recovery via email** ✅
  - Added a self-service "Forgot your password?" flow on the sign-in page. Users can enter a verified email address to receive a signed, time-limited reset link. The request form uses a generic success message so it does not reveal whether an email exists in the system.

- [x] **F7 — CSV export** ✅
  - `/export/positions/<id>` — current holdings as CSV (ticker, shares, price, MV, cost basis, G/L, %). `/export/transactions/<id>` — full transaction log as CSV, respects type/ticker filters. Export buttons on Positions page, Transaction History page, and Reports page.

- [x] **F8 — Self-service account creation with email verification** ✅
  - `/signup` route: invite-code gated public registration (username, email, password, invite code). On success: sends 6-digit OTP verification email via Resend, redirects to `/verify-email`. Security gate in `__init__.py` holds unverified users at the verify page. `email` + `email_verified` on User model. Invite code managed from Admin panel or `INVITE_CODE` env var. "Request a Code" modal emails admin via `NOTIFY_EMAIL` env var.

- [x] **F9 — Store user email for account recovery** ✅
  - `email` and `email_verified` fields added to User model. Manage Account page (`/manage_user/<id>`) lets users set/change their email; changing it sends a 6-digit verification code via Resend. Used by F6 (password reset) and DCA reminders.

---

## ✅ Recent Product Positioning Updates (completed 2026-04-09)

- **Email verification deliverability UX**
  - Added a clear note on the verification screen telling users to check spam/junk and add `noreply@wealthtrackapp.com` to their safe senders or contacts list.
  - Added plain-text fallbacks for transactional emails to improve deliverability without changing the visual HTML design of the verification email.
  - Kept the branded email design intact while improving the behind-the-scenes trust signals and user guidance.

- **First-account onboarding refresh**
  - Rebuilt `/add_account` into an adaptive page that now behaves differently based on account count.
  - Users with **0 accounts** see a richer onboarding experience with clearer guidance, value explanation, and lightweight visuals showing what WealthTrack can do.
  - Users with **1+ accounts** see a lighter-weight "add another account" experience with practical tips instead of a full onboarding pitch.

- **Broader investor messaging**
  - Reworked product copy across onboarding, help content, and empty states so WealthTrack reads as a portfolio tracking tool for regular investors, not just a rebalancing tool.
  - Messaging now emphasizes account organization, holdings tracking, gain/loss visibility, transaction history, imports, and cross-account dashboard value.
  - Allocation features are now framed as optional rather than central to the product experience.

- **ETF / target-based tool clarification**
  - Clarified that the Allocation and Purchase Planner workflows are optional strategy tools intended for ETF, index-fund, model-portfolio, or other target-based investors.
  - Renamed or re-labeled user-facing copy around these tools so regular investors are less likely to confuse them with the app's core tracking workflows.
  - Added explicit explanatory text on the account page, allocation pages, purchase-planning page, dashboard links, and home page so users can immediately tell when a feature is target-allocation-specific.

- **Privacy & Security page**
  - Added a dedicated in-app Privacy & Security page with plain-language explanations of what WealthTrack stores, what is protected, what is not claimed, and how users should think about admin/operator access.
  - Added a subtle `Privacy & Security` link to the authenticated sidebar footer so the page is always accessible without making it feel like a loud marketing element.
  - Framed the product's privacy promises honestly: private from other users, protected with standard safeguards, but not currently a zero-knowledge system.

---

## 🔍 Competitive Research Summary (2026-04)

Research across Copilot, Empower, Monarch Money, YNAB, Sharesight, and Kubera identified the following consistent pain points and market gaps. Items marked *(new)* below are net-new features added to the roadmap as a result.

**Universal pain points across all competitors:**
- Unreliable bank/brokerage sync (Plaid outages, accounts unlinking) — WealthTrack's manual-entry model is a quiet advantage here
- Aggressive upselling / sales calls once net worth is visible (Empower especially)
- Investment tracking is an afterthought in budgeting apps (Copilot, YNAB, Monarch treat it as a balance aggregator)
- Transaction recategorization rules are hidden and uneditable by users

**Confirmed gaps that WealthTrack can own:**
- No mainstream app does tax-aware tracking cleanly for US DIY investors (cost basis, realized vs unrealized, short vs long-term, loss harvesting)
- Nobody surfaces meaningful multi-account performance comparison
- Almost no app offers forward-looking portfolio projections
- Allocation drift alerts exist nowhere in the market despite allocation tracking being common
- The "active self-directed investor with multiple brokerages" is underserved — too advanced for YNAB, too small for Empower, too expensive for Kubera ($249/yr)

---

## 🛡️ Admin Panel Improvements (completed 2026-04-16)

- [x] **ADM1 — One-click approve/deny buttons in invite code request emails** ✅
  - When a user submits the "Request a Code" form, the admin notification email now contains one green **Approve** button per active invite code (so the admin can choose which code to send), plus a single red **Deny** button. Clicking either opens a no-login-required result page that sends the appropriate follow-up email to the applicant. Implemented using `itsdangerous.URLSafeTimedSerializer` with a 7-day expiry (same pattern as password reset). Routes: `GET /invite/approve/<token>` and `GET /invite/deny/<token>` in `auth.py`.

- [x] **ADM2 — Multiple active invite codes with label, use count, and per-code delete** ✅
  - Replaced the single `SiteConfig` invite_code entry with a new `InviteCode` model (`invite_codes` table: `id`, `code`, `label`, `created_at`, `use_count`). The admin dashboard now shows a full invite codes table — code, label, number of sign-ups, creation date, and a "✕ Remove" button per row. New codes can be added with an optional label (e.g., "Beta v2"). Multiple codes can be active simultaneously; any valid code grants sign-up access.

- [x] **ADM3 — Track which invite code each user used at signup** ✅
  - `invite_code_used` column added to `User` model. Set on registration from the code submitted in the signup form. Displayed as a monospace chip in the admin user table. `InviteCode.record_use()` increments the use count when a code is successfully used.

- [x] **ADM4 — Dedicated `/admin/users` page accessible from the admin dashboard** ✅
  - User management moved off the admin dashboard and onto a standalone page at `/admin/users`. The dashboard now shows a clean "Manage Users →" card linking to it. The user management page includes: full-width sortable table (checkbox, user/ID, email + verified status, role badge, invite code chip, joined date, account count, inline action buttons), client-side search by username/email, filter by invite code, bulk delete with confirmation modal, and single-user delete modal. Action buttons (`Reset PW`, `Toggle Admin`, `Delete`) are inline using `display: contents` on their `<form>` elements to prevent block stacking.

- [x] **ADM5 — Bulk delete users by invite code** ✅
  - Checkboxes on each user row (except the current admin) allow selecting multiple users. A yellow bulk-action bar appears when any are checked, showing selected count with **Delete Selected** and **Cancel** buttons. Confirmation modal shows the exact count before submitting `POST /admin/users/bulk-delete`. The invite code filter lets admins quickly select all users from a specific batch for bulk removal.

---

## 📈 Phase 9 — Analytics & Reporting

- [ ] **A1 — Realized gain/loss tracking (FIFO)**
  - Store cost basis at time of sell in the Transaction record. Add `realized_gain` and `cost_basis_at_sale` columns to Transaction. Implement FIFO lot matching when recording sells. Dedicated realized G/L section on Reports page showing short-term vs long-term gains (held <1yr vs ≥1yr). Essential for tax reporting.

- [ ] **A2 — Dividend income dashboard**
  - Dedicated page (or Reports tab) showing: total dividends received by year/month, dividend income per holding, yield on cost per ticker, rolling 12-month income chart. Data is already in the Transaction model — just needs surfacing.

- [ ] **A3 — Benchmark comparison (SPY / custom index)**
  - Overlay portfolio growth chart against SPY (or user-selected benchmark). Use yfinance to pull historical benchmark prices from the account's first snapshot date. Show annualized return vs benchmark return. Add to Reports page.

- [ ] **A4 — Tax report export**
  - Generate a Form 8949–style CSV/PDF showing all realized gains/losses for a selected tax year, split by short-term and long-term. Depends on A1.

---

## 🎨 Phase 10 — UX & Polish

- [x] **U1 — Dark mode** ✅
  - Full dark theme toggled by a moon/sun button in the sidebar footer. Preference is persisted to the `dark_mode` boolean column on the `User` model (server-side), so it survives browser/device changes and eliminates flash-of-wrong-theme on load. CSS custom property token overrides applied to body via `body.dark-mode` class. Covered: sidebar, all stat/chart/account/summary cards, admin panel, purchase planner, help page, positions page, allocation pages, privacy page, manage user page, add account page, import page, and all table headers. Dark mode overrides live in `styles.css` dark mode block plus page-level `var(--color-surface)` fallbacks.

- [ ] **U2 — Onboarding flow for new users**
  - First-login walkthrough: welcome screen → create first account → import or add holdings manually → set allocations → done. Step-by-step wizard with progress indicator. Skippable. Triggered only on first login (track via a `has_onboarded` flag on User).

- [ ] **U3 — Cash balance tracking**
  - `cash_balance` already exists on PortfolioSnapshot but isn't shown anywhere. Add cash as a line item on the account detail page and positions page. Let users manually set/update their cash balance per account. Include cash in total portfolio value calculations and allocation charts.

- [x] **U4 — PWA / mobile installability** ✅
  - Web App Manifest at `/manifest.json` (name, icons, theme color, start_url, standalone display). Service worker at `/sw.js` with cache-first for static assets, network-first for pages, and an offline fallback screen. Apple PWA meta tags added to base.html. Icons generated at 180, 192, and 512px. App is now installable to iOS/Android home screen via Safari/Chrome "Add to Home Screen".

---

## 🔌 Phase 11 — Integrations & Data Import

- [ ] **I1 — Fidelity CSV importer**
  - Parse Fidelity's positions and transaction history CSV export format. Fidelity has no public OAuth API so CSV is the only path. Model after the existing Schwab CSV importer.

- [ ] **I2 — Vanguard CSV importer**
  - Parse Vanguard's export format. Similar approach to I1.

- [ ] **I3 — Generic CSV importer (column mapping UI)**
  - A flexible import flow where users map their brokerage's CSV columns to WealthTrack fields. Handles any brokerage not covered by dedicated parsers. Useful long-term catch-all.

- [ ] **I4 — Interactive Brokers (IBKR) integration**
  - IBKR has a well-documented public API (Client Portal API) accessible to individual account holders — no developer approval required. Higher-effort but covers a significant user base.

- [ ] **I5 — Alpaca integration**
  - Alpaca's API is developer-friendly and free to access. Good coverage for users who trade programmatically or use commission-free accounts.

---

## 💰 Phase 12 — Monetization

- [ ] **M1 — Subscription tiers (Stripe)**
  - Integrate Stripe for billing. Define free vs paid tiers (e.g. free: 1 account, paid: unlimited accounts + advanced analytics + CSV export). Add `subscription_status` and `stripe_customer_id` to User model. Webhook handler for subscription events.

- [ ] **M2 — Usage limits enforcement**
  - Gate features by subscription tier. Show upgrade prompts when free users hit limits. Graceful degradation (don't break existing data if subscription lapses).

- [ ] **M3 — Admin billing dashboard**
  - Show active subscribers, MRR, churn in the admin panel. Stripe dashboard covers most of this but a lightweight in-app view is useful.

---

## 🎯 Phase 13 — Competitive Differentiators

Features identified through competitive research (2026-04) that directly address gaps in the market. These are the items most likely to make WealthTrack feel meaningfully better than existing tools for the self-directed investor.

- [x] **C1 — "Positions at a loss" quick view (Tax-Loss Harvesting helper)** ✅
  - Panel on the Positions page showing only holdings currently below cost basis, sorted by largest loss first. Shows total harvestable loss, estimated tax savings at 15% and 20% capital gains rates, per-holding breakdown, and a "Record Sell" quick-action link for each. Includes wash-sale rule disclaimer. Only visible when at least one position is at a loss.

- [ ] **C2 — Realized gain/loss tax-year summary (depends on A1)**
  - A dedicated section on the Reports page (or standalone page) showing: total short-term gains, total long-term gains, total realized losses, and net taxable gain for a selected calendar year. Formatted to mirror what ends up on Schedule D. Currently no mainstream portfolio tracker does this simply for US investors — Sharesight does it well for AU/NZ/CA but feels clunky for US users. Depends on FIFO lot tracking in A1.

- [ ] **C3 — Allocation drift alerts**
  - Let users set a drift threshold per account (e.g., "alert me if any position moves more than 3% from its target allocation"). Send an in-app notification and/or email when the threshold is breached. The allocation model is already built — this is mostly a scheduled check + notification layer. No competitor does this for stock-level portfolios. Pairs naturally with the DCA email reminder system already in place.

- [ ] **C4 — Multi-account performance comparison**
  - A dashboard view that places all accounts side-by-side: total return %, unrealized G/L, cost basis, and market value for each. Lets users instantly see which account strategy is winning. Power-user retention feature — the kind of thing that makes people say "I can't leave, I'd lose all my history." Could live as a tab on the main dashboard.

- [ ] **C5 — Projected portfolio value chart**
  - A forward-looking chart showing estimated portfolio value at a user-defined future date, based on a configurable assumed annual return rate (default 7%). Show optimistic/base/conservative bands. No budgeting or portfolio app does this cleanly for stock portfolios. YNAB users specifically call out the absence of forward-looking projections as their biggest frustration with the category. Could live on the Reports page or Dashboard.

- [ ] **C6 — Shareable account snapshot (read-only link)**
  - Let users generate a time-limited, read-only shareable link to their portfolio summary (no transaction history, just current positions and performance). Useful for sharing with a financial advisor, spouse, or accountant. Monarch and Copilot have joint/shared modes but they require both parties to have accounts — a simple read-only link is far easier. Important: no login required for the recipient, and the link expires.

---

## ✅ Master Checklist — Recommended Work Order

Work through these one at a time. Each is a discrete, shippable unit.

### Phase 1 — Quick Bugs (low risk, high polish value)
1. ~~`B3`~~ ✅ Fix browser tab titles on all pages — all templates now use "WealthWise — [Page]" format
2. ~~`B4`~~ ✅ Fix dollar formatting in Edit Portfolio market value column
3. ~~`B5`~~ ✅ Add back/cancel navigation to Reset Password page
4. ~~`B1`~~ ✅ Fix "Date of Last Purchase" showing "No purchases made yet" incorrectly
5. ~~`B7`~~ ✅ Root-cause fix for global `form` max-width: 600px breaking all full-width table forms
6. ~~`B8`~~ ✅ Dark mode card backgrounds — all 11 templates converted from `#fff` to `var(--color-surface)`
7. ~~`B9`~~ ✅ Table header purple override fixed with `!important` on affected page-level `th` rules
8. ~~`B10`~~ ✅ Unwanted scroll bars in sidebar, tab bar, and table wrappers

### Phase 2 — Design System Foundation (do this before any visual work)
5. ~~`D1`~~ ✅ Establish consistent design system: fonts, color palette, unified button classes

### Phase 3 — Dashboard (biggest UX transformation)
6. ~~`DASH1`~~ ✅ Build Portfolio Overview Dashboard with 3 charts (allocation pie, growth line, top performers bar)
7. ~~`DASH2`~~ ✅ Add per-account summary cards below the overview
8. ~~`D3`~~ ✅ Replace per-account "6 buttons" menu with tabbed/inline account detail layout
9. ~~`D4`~~ ✅ Active account highlight in navigation
10. ~~`D6`~~ ✅ Modernize the header bar

### Phase 3.5 — Schema Redesign + Data Import (completed 2026-03-26)
- ~~Schema redesign~~ ✅ `Holding` / `Transaction` / `PortfolioSnapshot` replace old models
- ~~Schwab Positions CSV importer~~ ✅ Step 1 on Import Data page
- ~~Schwab Transactions CSV importer~~ ✅ Step 2 on Import Data page

### Phase 4 — Core Data Pages (highest day-to-day value)
11. ~~`D8`~~ ✅ Add cost basis + P&L columns to Positions page
12. ~~`D9`~~ ✅ Color-code gains/losses on Positions page
13. ~~`D10`~~ ✅ Add summary card to top of Positions page
14. ~~`D11`~~ ✅ Add donut chart to View Allocation
15. ~~`D12`~~ ✅ Add delta column + color coding to View Allocation
16. ~~`B6`~~ ✅ Add 100% validation to Adjust Allocations

### Phase 5 — Form & Flow Polish
17. ~~`D13`~~ ✅ Show current % alongside inputs in Adjust Allocations
18. ~~`D14`~~ ✅ Live-updating total % on Adjust Allocations
19. ~~`D15`~~ ✅ Rename "Cash Value" to "Amount to Invest" with explanation
20. ~~`D16`~~ ✅ Show all rebalancing suggestions on purchase step 2
21. ~~`D17`~~ ✅ Add post-purchase success/redirect state
22. ~~`D18`~~ ✅ Remove empty row in Edit Portfolio; add "+ Add Holding" button
23. ~~`D19`~~ ✅ Ticker symbol validation in Edit Portfolio

### Phase 6 — Layout & Accessibility
24. ~~`D5`~~ ✅ Responsive/mobile layout
25. ~~`D7`~~ ✅ Market status bar: color + next open/close time
26. ~~`D20`~~ ✅ Tooltip/labels for sidebar pencil & star icons → redesigned as labeled Reorder mode
27. ~~`D21`~~ ✅ Clean up Manage User Account page styling

### Phase 7 — New Features ✅
28. ~~`F2`~~ ✅ Transaction history page (per account)
29. ~~`F3`~~ ✅ Sell / record transaction support
30. ~~`F4`~~ ✅ Portfolio performance chart (per account, powers Reports + Dashboard)
31. ~~`F1`~~ ✅ Full Reports page (history table + charts)
32. ~~`F5`~~ ✅ Price caching / rate-limit resilience
33. ~~`F7`~~ ✅ CSV export

### Phase 8 — User Management & Auth
34. ~~`F9`~~ ✅ Add `email` field to User model (foundation for F6 + F8)
35. ~~`F6`~~ ✅ Password recovery via email ("Forgot Password" on login page)
36. ~~`F8`~~ ✅ Self-service account creation with email verification

### Phase 9 — Analytics & Reporting
37. `A1` — Realized G/L tracking with FIFO cost basis
38. `A2` — Dividend income dashboard
39. `A3` — Benchmark comparison (SPY / custom index)
40. `A4` — Tax report export (depends on A1)

### Phase 8.5 — Admin & Invite System (completed 2026-04-16)
- ~~`ADM1`~~ ✅ One-click approve/deny buttons in invite code request emails
- ~~`ADM2`~~ ✅ Multiple active invite codes with label, use count, and delete
- ~~`ADM3`~~ ✅ Track which invite code each user used at signup
- ~~`ADM4`~~ ✅ Dedicated `/admin/users` page linked from admin dashboard
- ~~`ADM5`~~ ✅ Bulk delete users by invite code

### Phase 10 — UX & Polish
41. ~~`U1`~~ ✅ Dark mode (server-persisted, sidebar toggle, full coverage across all pages)
42. `U2` — Onboarding flow for new users
43. `U3` — Cash balance tracking
44. ~~`U4`~~ ✅ PWA / mobile installability

### Phase 11 — Integrations & Data Import
45. `I1` — Fidelity CSV importer
46. `I2` — Vanguard CSV importer
47. `I3` — Generic CSV importer with column mapping UI
48. `I4` — Interactive Brokers (IBKR) API integration
49. `I5` — Alpaca API integration

### Phase 12 — Monetization
50. `M1` — Stripe subscription integration
51. `M2` — Usage limits enforcement by tier
52. `M3` — Admin billing dashboard

### Phase 13 — Competitive Differentiators
53. ~~`C1`~~ ✅ "Positions at a loss" quick view / tax-loss harvesting helper
54. `C2` — Realized gain/loss tax-year summary for Schedule D *(depends on A1)*
55. `C3` — Allocation drift alerts (threshold-based, email or in-app)
56. `C4` — Multi-account performance comparison view
57. `C5` — Projected portfolio value chart (forward-looking, configurable return rate)
58. `C6` — Shareable read-only account snapshot link

---

## 🗒️ Session Notes

- **Production URL:** `www.wealthtrackapp.com` (PythonAnywhere, runs `prod` git branch)
- **Local dev:** `http://127.0.0.1:5001` (runs inside sandbox — not accessible from user's browser)
- **Production DB:** PostgreSQL on PythonAnywhere
- **Dev DB:** SQLite at `/tmp/stock_calc_dev.db` (resets on VM restart)
- **Login:** `cgiglio` / `StockCalc2026!`
- **Superuser note:** The "Add New User" form on `/manage_user` is intentional and visible only to the `cgiglio` account — not a bug.
- **Yahoo Finance fix:** Already applied to `models.py` on prod — `current_price` returns `0.0` on rate-limit errors rather than crashing.
- **Static asset cache-busting:** Implemented via `asset_url()` helper in `flask_app/__init__.py`, which appends each static file's modified timestamp to CSS/logo/favicon URLs so browsers pick up deploy updates without a hard refresh.
- **Local email fallback:** `flask_app/email_utils.py` now fails gracefully when the `resend` package is not installed locally, so auth flows can still be tested without crashing the app.
- **DNS:** `www.wealthtrackapp.com` CNAME → `webapp-2769154.pythonanywhere.com` (Squarespace, propagated 2026-03-26). Bare domain `wealthtrackapp.com` forwards → `https://www.wealthtrackapp.com`.
- **PythonAnywhere API token:** `3116453ae30a968dfc5eb596939f9b742d4bf2a8`

---

## 🌿 Git Workflow

### Branch Structure
| Branch | Purpose |
|---|---|
| `prod` | Live site — only receives merges from `dev` when a feature is complete and tested |
| `dev` | Active development — all day-to-day work happens here |

### PythonAnywhere Setup
- Repo location: `/home/chrisgig23/stock-calc/`
- Always checked out on: `prod`
- To deploy an update: merge `dev` → `prod` on PythonAnywhere, then `touch` the WSGI file
- Static asset note: CSS/logo/favicon changes automatically cache-bust after deploy because templates use versioned asset URLs.

### Deploying (step-by-step)
```bash
cd /home/chrisgig23/stock-calc
git checkout prod
git merge dev
touch /var/www/www_wealthtrackapp_com_wsgi.py
```

### Local VS Code Workflow
1. Make sure local is on `dev` branch: `git checkout dev`
2. Pull latest: `git pull origin dev`
3. Make changes, commit, push: `git push origin dev`
4. When ready to go live: merge `dev` → `prod` on PythonAnywhere (steps above)

### ⚠️ GitHub Token
The stored `ghp_` token has expired. Generate a new one at:
**GitHub → Settings → Developer settings → Personal access tokens → Fine-grained**
Scopes needed: `Contents` (read/write) on the `stock-calc` repo.
Once you have it, run on PythonAnywhere:
```bash
cd /home/chrisgig23/stock-calc
git push origin dev prod main
```
(git will prompt for username = `chrisgig23`, password = new token)

### Cleaning Up Old Branches (local VS Code only)
```bash
git branch -d import_export
git branch -d portfolio-overview
git branch -d refactor-routes
git branch -d reports
git branch -d schwab_connect
git branch -d encryption
```
Keep: `main`, `dev`, `prod`, the two `backup_` branches.
