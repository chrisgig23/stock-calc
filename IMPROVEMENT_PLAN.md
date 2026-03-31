# WealthWise — Site Improvement Plan

> Living document. Check off items as they are completed. Work through one item at a time in the order defined in the Master Checklist at the bottom.

---

## 🐛 Bugs

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

- [ ] **D6 — Modernize the header bar**
  - Replace plain "Logged in as: cgiglio | Logout | Manage my account" text with a clean right-aligned profile area (username + dropdown or icon links). Remove the extra line of wasted space in the header.

- [ ] **D7 — Market status bar: add color and next-open time**
  - "Markets are closed" in a flat teal bar is functional but minimal. Make the bar green when open, red/gray when closed, and show the next open or close time.

- [ ] **D5 — Make the layout responsive (mobile-friendly)**
  - The two-column sidebar + content layout is not responsive. Add breakpoints so the sidebar collapses to a hamburger/drawer on mobile/tablet.

---

## 🏠 Dashboard & Navigation Overhaul

> Based on the provided mockup. This is the highest-visibility change — it transforms the first impression of the app.

- [ ] **DASH1 — Build a Portfolio Overview Dashboard as the post-login landing page**
  - Currently login → Account 1's menu. Instead, login should land on a Portfolio Overview Dashboard.
  - The dashboard is a **cross-account summary** containing:
    1. **Portfolio Allocation pie chart** — combined allocation across all accounts, broken down by asset type (US Stocks, International Stocks, Bonds, etc.). For now can use per-stock data; asset-type classification can be a future enhancement.
    2. **Portfolio Growth line chart** — total portfolio value over time (monthly), built from purchase history + current prices.
    3. **Top Performing Assets bar chart** — % gain per stock across all accounts, sorted descending.
  - Navigation bar replaces the current sidebar header: **Overview | Accounts | Dashboard | Reports** + "Markets are closed" status on the right.

- [ ] **DASH2 — Add per-account summary cards below the overview charts**
  - Below the overview charts, show a card for each account containing:
    - Account name
    - Total current value
    - Total cost basis
    - Unrealized P&L ($ and %)
    - Quick-action links: View Positions, Make a Purchase
  - Clicking an account card navigates into that account's detail view.

- [ ] **D3 — Replace the per-account "6 buttons" menu page with a proper account detail layout**
  - Once inside an account, replace the static list of 6 blue buttons with a tabbed or sidebar-nav layout so content is visible without an extra click. The main content area should never be just buttons on an empty background.

- [ ] **D4 — Highlight the active account in navigation**
  - When viewing a specific account, the account name should be visually active/selected in whatever nav structure replaces the current sidebar.

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

- [ ] **D20 — Add tooltips/labels to the sidebar pencil & star icons**
  - The pencil icon's purpose (reorder/favorite mode) is unclear with no tooltip. The star icon's function is also unexplained. Add descriptive tooltips, or redesign to a labeled "Reorder Accounts" mode with drag handles.

- [ ] **D21 — Clean up the Manage User Account page layout**
  - The page has three buttons (Reset Password, Change Username, Exit) where "Exit" uses inconsistent plain styling. Unify button styles and make the flow clearer.

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

- [ ] **F1 — Build out the Reports page**
  - Currently "Coming soon!". Priority content: purchase history table, P&L over time line chart (connects to DASH1's Portfolio Growth chart), performance vs. S&P 500 benchmark.

- [ ] **F2 — Transaction / purchase history page per account**
  - A chronological table of all purchases for a given account: date, ticker, shares, price paid, total cost.

- [ ] **F3 — Sell / record transaction support**
  - Currently only buying is tracked. Add a "Record Sale" flow that reduces position quantity and calculates realized gain/loss.

- [ ] **F4 — Portfolio performance chart (per account)**
  - A line chart of account value over time. Powers both the per-account Reports page and the cross-account Portfolio Growth chart on the Dashboard.

- [ ] **F5 — Price caching / rate-limit resilience**
  - Yahoo Finance rate-limits PythonAnywhere's shared IPs (429 errors already patched to return 0.0). Better fix: cache fetched prices in the DB with a 15-minute TTL, or migrate to a keyed free API (Polygon.io, Alpha Vantage, Twelve Data).

- [ ] **F6 — Password recovery via email**
  - No self-service forgotten-password flow exists. Add a "Forgot Password" link on the login page that sends a time-limited reset link to the user's registered email address.

- [ ] **F7 — CSV export**
  - Let users download positions and purchase history as a CSV file for use in Excel/Sheets.

- [ ] **F8 — Self-service account creation with email verification**
  - Currently only admins can create accounts (via `/add_user`). Add a public "Create Account" flow on the login page: user enters username + email + password → receives a verification email → clicks link → account activated.
  - Requires: storing `email` + `is_verified` + `verification_token` on the User model; sending email via Flask-Mail or similar; a `/verify/<token>` route.
  - Security note: token should be time-limited (e.g. 24 hrs) and single-use.

- [ ] **F9 — Store user email for account recovery**
  - Even before F6/F8 are built, add an optional `email` field to the User model so existing users can register their email for future password recovery. Can be done via the Manage Account page.

---

## ✅ Master Checklist — Recommended Work Order

Work through these one at a time. Each is a discrete, shippable unit.

### Phase 1 — Quick Bugs (low risk, high polish value)
1. ~~`B3`~~ ✅ Fix browser tab titles on all pages — all templates now use "WealthWise — [Page]" format
2. ~~`B4`~~ ✅ Fix dollar formatting in Edit Portfolio market value column
3. ~~`B5`~~ ✅ Add back/cancel navigation to Reset Password page
4. ~~`B1`~~ ✅ Fix "Date of Last Purchase" showing "No purchases made yet" incorrectly

### Phase 2 — Design System Foundation (do this before any visual work)
5. ~~`D1`~~ ✅ Establish consistent design system: fonts, color palette, unified button classes

### Phase 3 — Dashboard (biggest UX transformation)
6. `DASH1` — Build Portfolio Overview Dashboard with 3 charts (allocation pie, growth line, top performers bar)
7. `DASH2` — Add per-account summary cards below the overview
8. `D3` — Replace per-account "6 buttons" menu with tabbed/inline account detail layout
9. `D4` — Active account highlight in navigation
10. `D6` — Modernize the header bar

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
19. `D15` — Rename "Cash Value" to "Amount to Invest" with explanation
20. `D16` — Show all rebalancing suggestions on purchase step 2
21. `D17` — Add post-purchase success/redirect state
22. ~~`D18`~~ ✅ Remove empty row in Edit Portfolio; add "+ Add Holding" button
23. ~~`D19`~~ ✅ Ticker symbol validation in Edit Portfolio

### Phase 6 — Layout & Accessibility
24. `D5` — Responsive/mobile layout
25. `D7` — Market status bar: color + next open/close time
26. `D20` — Tooltip/labels for sidebar pencil & star icons
27. `D21` — Clean up Manage User Account page styling

### Phase 7 — New Features
28. `F2` — Transaction history page (per account)
29. `F3` — Sell / record transaction support
30. `F4` — Portfolio performance chart (per account, powers Reports + Dashboard)
31. `F1` — Full Reports page (history table + charts)
32. `F5` — Price caching / rate-limit resilience
33. `F7` — CSV export

### Phase 8 — User Management & Auth
34. `F9` — Add `email` field to User model (foundation for F6 + F8)
35. `F6` — Password recovery via email ("Forgot Password" on login page)
36. `F8` — Self-service account creation with email verification

---

## 🗒️ Session Notes

- **Production URL:** `www.wealthtrackapp.com` (PythonAnywhere, runs `prod` git branch)
- **Local dev:** `http://127.0.0.1:5001` (runs inside sandbox — not accessible from user's browser)
- **Production DB:** PostgreSQL on PythonAnywhere
- **Dev DB:** SQLite at `/tmp/stock_calc_dev.db` (resets on VM restart)
- **Login:** `cgiglio` / `StockCalc2026!`
- **Superuser note:** The "Add New User" form on `/manage_user` is intentional and visible only to the `cgiglio` account — not a bug.
- **Yahoo Finance fix:** Already applied to `models.py` on prod — `current_price` returns `0.0` on rate-limit errors rather than crashing.
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
