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

- [ ] **B6 — Adjust Allocations: no validation that percentages sum to 100%**
  - Users can submit any arbitrary numbers with no warning or block if total ≠ 100%.

---

## 🎨 Design System & Global UI

- [ ] **D1 — Establish a consistent design system**
  - Adopt a clean sans-serif font (e.g., Inter via Google Fonts).
  - Define a formal color palette: primary blue, success green, danger red, warning amber, neutral grays.
  - Create unified CSS button classes (`.btn-primary`, `.btn-secondary`, `.btn-danger`, `.btn-ghost`) and apply them everywhere. Currently "← Back to Account", "Exit", "Refresh Market Pricing" use raw browser `<button>` styling while other buttons are custom-styled — this inconsistency appears on every page.

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

- [ ] **D8 — Add cost basis and gain/loss columns**
  - Currently shows: Symbol, Quantity, Current Price, Market Value.
  - Add: Cost Basis (per share), Total Cost Basis, Unrealized P&L ($), Unrealized P&L (%).
  - This is the single most important missing data for a portfolio tracker.

- [ ] **D9 — Color-code gain/loss values**
  - Green text for positive P&L, red for negative. Standard in every financial app.

- [ ] **D10 — Add a summary card at the top of the positions page**
  - Show: Total Market Value, Total Cost Basis, Total Unrealized P&L ($), Total Unrealized P&L (%).

---

## 📐 Allocation Pages (`/view_allocation`, `/adjust_allocation`)

- [ ] **D11 — Add a pie/donut chart to View Allocation**
  - Visual allocation chart (current vs. target) alongside the table. Chart.js or a similar lightweight library.

- [ ] **D12 — Add color coding + delta column to View Allocation**
  - New "Difference" column: current % − target %. Red if overweight, green if underweight.

- [ ] **D13 — Show current allocation alongside inputs in Adjust Allocations**
  - Add a read-only "Current %" column next to "Desired %" so users have a reference point.

- [ ] **D14 — Live-updating total % on Adjust Allocations**
  - Show a running "Total: X%" that updates as the user types, turns green at exactly 100%.

---

## 🛒 Make a Purchase (`/make_purchase`)

- [ ] **D15 — Rename "Enter Current Cash Value" to "Amount to Invest"**
  - The current label is ambiguous. Rename to "Amount to Invest ($)" with a one-line explanation: "Enter the cash you want to deploy across your portfolio."

- [ ] **D16 — Show all rebalancing suggestions, not just the top stock**
  - Currently shows only the single most-underweight stock. Should show all stocks that need buying to rebalance toward targets, with editable quantities.

- [ ] **D17 — Add a post-purchase success state**
  - After "Confirm Purchases", show a clear confirmation message (flash banner or success page) then redirect to the positions page.

---

## ✏️ Edit Portfolio (`/edit_portfolio`)

- [ ] **D18 — Remove the persistent empty row; add a proper "+ Add Stock" button**
  - The blank row at the bottom of the table is confusing. Replace with a "+ Add Stock" button that appends a new empty row on click.

- [ ] **D19 — Add ticker symbol validation**
  - Free-text input with no validation. At minimum, validate on blur against a known list or the Yahoo Finance API. Ideally add a typeahead/autocomplete for stock symbols.

---

## ⚙️ Account Management Polish

- [ ] **D20 — Add tooltips/labels to the sidebar pencil & star icons**
  - The pencil icon's purpose (reorder/favorite mode) is unclear with no tooltip. The star icon's function is also unexplained. Add descriptive tooltips, or redesign to a labeled "Reorder Accounts" mode with drag handles.

- [ ] **D21 — Clean up the Manage User Account page layout**
  - The page has three buttons (Reset Password, Change Username, Exit) where "Exit" uses inconsistent plain styling. Unify button styles and make the flow clearer.

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
  - No self-service forgotten-password flow exists. Add a "Forgot Password" link on the login page that sends a reset email.

- [ ] **F7 — CSV export**
  - Let users download positions and purchase history as a CSV file for use in Excel/Sheets.

---

## ✅ Master Checklist — Recommended Work Order

Work through these one at a time. Each is a discrete, shippable unit.

### Phase 1 — Quick Bugs (low risk, high polish value)
1. ~~`B3`~~ ✅ Fix browser tab titles on all pages — all templates now use "WealthWise — [Page]" format
2. ~~`B4`~~ ✅ Fix dollar formatting in Edit Portfolio market value column
3. ~~`B5`~~ ✅ Add back/cancel navigation to Reset Password page
4. ~~`B1`~~ ✅ Fix "Date of Last Purchase" showing "No purchases made yet" incorrectly

### Phase 2 — Design System Foundation (do this before any visual work)
5. `D1` — Establish consistent design system: fonts, color palette, unified button classes

### Phase 3 — Dashboard (biggest UX transformation)
6. `DASH1` — Build Portfolio Overview Dashboard with 3 charts (allocation pie, growth line, top performers bar)
7. `DASH2` — Add per-account summary cards below the overview
8. `D3` — Replace per-account "6 buttons" menu with tabbed/inline account detail layout
9. `D4` — Active account highlight in navigation
10. `D6` — Modernize the header bar

### Phase 4 — Core Data Pages (highest day-to-day value)
11. `D8` — Add cost basis + P&L columns to Positions page
12. `D9` — Color-code gains/losses on Positions page
13. `D10` — Add summary card to top of Positions page
14. `D11` — Add donut chart to View Allocation
15. `D12` — Add delta column + color coding to View Allocation
16. `B6` — Add 100% validation to Adjust Allocations

### Phase 5 — Form & Flow Polish
17. `D13` — Show current % alongside inputs in Adjust Allocations
18. `D14` — Live-updating total % on Adjust Allocations
19. `D15` — Rename "Cash Value" to "Amount to Invest" with explanation
20. `D16` — Show all rebalancing suggestions on purchase step 2
21. `D17` — Add post-purchase success/redirect state
22. `D18` — Remove empty row in Edit Portfolio; add "+ Add Stock" button
23. `D19` — Ticker symbol validation in Edit Portfolio

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
34. `F6` — Password recovery via email

---

## 🗒️ Session Notes

- **Production URL:** `www.stock-calc.com` (PythonAnywhere, runs `production` git branch)
- **Local dev:** `http://127.0.0.1:5001` (runs inside sandbox — not accessible from user's browser)
- **Production DB:** PostgreSQL on PythonAnywhere
- **Dev DB:** SQLite at `/tmp/stock_calc_dev.db` (resets on VM restart)
- **Login:** `cgiglio` / `StockCalc2026!`
- **Superuser note:** The "Add New User" form on `/manage_user` is intentional and visible only to the `cgiglio` account — not a bug.
- **Yahoo Finance fix:** Already applied to `models.py` on production — `current_price` returns `0.0` on rate-limit errors rather than crashing.
- **DNS:** `stock-calc.com` bare domain now has ALIAS record → `webapp-2769154.pythonanywhere.com` (propagating).
- **PythonAnywhere API token:** `3116453ae30a968dfc5eb596939f9b742d4bf2a8`

---

## 🌿 Git Workflow

### Branch Structure
| Branch | Purpose |
|---|---|
| `production` | Live site — only receives merges from `dev` when a feature is complete and tested |
| `dev` | Active development — all day-to-day work happens here |
| `main` | Legacy default branch — kept for reference; treat `production` as source of truth |

### PythonAnywhere Setup
- Repo location: `/home/chrisgig23/stock-calc/`
- Always checked out on: `production`
- To deploy an update: merge `dev` → `production` on PythonAnywhere, then `touch` the WSGI file

### Deploying (step-by-step)
```bash
cd /home/chrisgig23/stock-calc
git checkout production
git merge dev
touch /var/www/www_stock-calc_com_wsgi.py
```

### Local VS Code Workflow
1. Make sure local is on `dev` branch: `git checkout dev`
2. Pull latest: `git pull origin dev`
3. Make changes, commit, push: `git push origin dev`
4. When ready to go live: merge `dev` → `production` on PythonAnywhere (steps above)

### ⚠️ GitHub Token
The stored `ghp_` token has expired. Generate a new one at:
**GitHub → Settings → Developer settings → Personal access tokens → Fine-grained**
Scopes needed: `Contents` (read/write) on the `stock-calc` repo.
Once you have it, run on PythonAnywhere:
```bash
cd /home/chrisgig23/stock-calc
git push origin dev production main
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
Keep: `main`, `dev`, `production`, the two `backup_` branches.
