"""
schwab_parser.py
----------------
Parsers for Charles Schwab CSV exports.

Supported formats
-----------------
1. Positions export  — "Accounts → Positions → Export" in Schwab web app
   Filename pattern: Personal-Positions-YYYY-MM-DD-HHMMSS.csv

2. Transactions export — "Accounts → History → Export" in Schwab web app
   Filename pattern: Personal_XXXNNN_Transactions_YYYYMMDD-HHMMSS.csv

Both parsers return plain Python dicts ready to be passed to SQLAlchemy
model constructors.
"""

import csv
import re
from datetime import datetime
from io import StringIO


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _parse_date(date_str: str):
    """
    Handle Schwab date formats:
      '03/25/2026'
      '03/16/2026 as of 03/15/2026'  → use the first date
    Returns a datetime.date object, or None on failure.
    """
    date_str = date_str.split(' as of ')[0].strip()
    for fmt in ('%m/%d/%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def _parse_money(val: str):
    """
    Strip currency symbols, commas, and parenthetical negatives.
    Returns float or None.
    """
    if not val:
        return None
    val = val.strip().strip('"')
    if val in ('--', '', 'N/A'):
        return None
    # Handle parenthetical negatives like (1,234.56)
    negative = val.startswith('(') and val.endswith(')')
    val = val.strip('()')
    val = val.replace('$', '').replace(',', '').strip()
    try:
        result = float(val)
        return -result if negative else result
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Action-type mapping  (Schwab raw → WealthWise canonical)
# ---------------------------------------------------------------------------

_ACTION_MAP = {
    'Buy':                   'buy',
    'Sell':                  'sell',
    'Cash Dividend':         'dividend',
    'Pr Yr Cash Div':        'dividend',
    'Qualified Dividend':    'dividend',
    'Non-Qualified Div':     'dividend',
    'Reinvest Dividend':     'reinvest_dividend',
    'Reinvest Shares':       'reinvest_shares',
    'MoneyLink Transfer':    'transfer_in',   # refined below by sign of amount
    'MoneyLink Deposit':     'transfer_in',
    'MoneyLink Withdrawal':  'transfer_out',
    'Wire Received':         'transfer_in',
    'Wire Sent':             'transfer_out',
    'Bank Interest':         'interest',
    'Short Term Cap Gain Reinvest': 'reinvest_dividend',
    'Long Term Cap Gain Reinvest':  'reinvest_dividend',
    'Service Fee':           'fee',
    'Margin Interest':       'fee',
    'Journal':               'other',
    'Misc Credits':          'other',
    'Misc Debits':           'other',
    'Stock Split':           'other',
    'Security Transfer':     'other',
}

_TRANSFER_ACTIONS = {'MoneyLink Transfer', 'MoneyLink Deposit', 'MoneyLink Withdrawal'}


# ---------------------------------------------------------------------------
# Transactions CSV parser
# ---------------------------------------------------------------------------

def parse_schwab_transactions(file_content: str) -> list[dict]:
    """
    Parse a Schwab transaction history CSV.

    Returns a list of dicts with keys:
        date, action_type, raw_action, ticker, description,
        quantity, price, fees, amount, import_source
    """
    reader = csv.DictReader(StringIO(file_content.strip()))
    results = []

    for row in reader:
        raw_action = row.get('Action', '').strip()
        date_str   = row.get('Date', '').strip()

        if not raw_action or not date_str:
            continue

        date = _parse_date(date_str)
        if date is None:
            continue

        amount = _parse_money(row.get('Amount', '')) or 0.0

        # Determine canonical action type
        action_type = _ACTION_MAP.get(raw_action, 'other')

        # Refine transfer direction from amount sign
        if raw_action in _TRANSFER_ACTIONS:
            action_type = 'transfer_in' if amount >= 0 else 'transfer_out'

        ticker      = row.get('Symbol', '').strip() or None
        description = row.get('Description', '').strip() or None
        quantity    = _parse_money(row.get('Quantity', ''))
        price       = _parse_money(row.get('Price', ''))
        fees        = _parse_money(row.get('Fees & Comm', ''))

        results.append({
            'date':         date,
            'action_type':  action_type,
            'raw_action':   raw_action,
            'ticker':       ticker.upper() if ticker else None,
            'description':  description,
            'quantity':     abs(quantity) if quantity is not None else None,
            'price':        abs(price)    if price    is not None else None,
            'fees':         abs(fees)     if fees     is not None else None,
            'amount':       amount,
            'import_source': 'schwab_transactions_csv',
        })

    return results


# ---------------------------------------------------------------------------
# Positions CSV parser
# ---------------------------------------------------------------------------

_SKIP_SYMBOLS = {'Cash & Cash Investments', 'Positions Total', 'Account Total', ''}

def parse_schwab_positions(file_content: str) -> list[dict]:
    """
    Parse a Schwab positions/holdings CSV export.

    The file has a non-standard header (account info on row 1, blank row 2),
    so we scan for the actual column header row that starts with "Symbol".

    Returns a list of dicts with keys:
        ticker, quantity, cost_basis, description, import_source
    """
    lines = file_content.splitlines()

    # Find the column-header row
    header_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip().strip('"')
        if stripped.startswith('Symbol'):
            header_idx = i
            break

    if header_idx is None:
        return []

    data_block = '\n'.join(lines[header_idx:])
    reader = csv.DictReader(StringIO(data_block))
    results = []

    for row in reader:
        symbol = row.get('Symbol', '').strip().strip('"')
        if not symbol or symbol in _SKIP_SYMBOLS:
            continue

        qty_str = row.get('Qty (Quantity)', '').strip().strip('"')
        if qty_str in ('--', ''):
            continue
        try:
            quantity = float(qty_str.replace(',', ''))
        except ValueError:
            continue

        # Cost basis column label varies slightly between exports
        cost_basis_raw = (
            row.get('Cost Basis', '')
            or row.get('Cost Basis Total', '')
            or row.get('Adj Cost Basis', '')
        )
        cost_basis  = _parse_money(cost_basis_raw)
        description = row.get('Description', '').strip().strip('"') or None

        results.append({
            'ticker':       symbol.upper(),
            'quantity':     quantity,
            'cost_basis':   cost_basis,
            'description':  description,
            'import_source': 'schwab_positions_csv',
        })

    return results
