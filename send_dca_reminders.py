#!/usr/bin/env python3
"""
send_dca_reminders.py — Daily job: send DCA reminder emails to opted-in users.

Schedule this on PythonAnywhere as a daily task at 09:30 ET (14:30 UTC):
    /home/chrisgig23/.virtualenvs/stockcalc-env/bin/python \
        /home/chrisgig23/stock-calc/send_dca_reminders.py

The script checks whether today is the first NYSE trading day on or after
each user's chosen reminder day, then sends any due reminder emails.
"""

import os
import sys
from datetime import date, datetime, timedelta

import pandas_market_calendars as mcal
import pytz

# ── Bootstrap Flask app context ───────────────────────────────────────────────
# Add the project root to the path so imports resolve correctly.
sys.path.insert(0, os.path.dirname(__file__))

# Point at the production database.
os.environ.setdefault('FLASK_ENV', 'production')

from flask_app import app, db
from flask_app.models import User
from flask_app.email_utils import send_dca_reminder_email


def _today_et():
    return datetime.now(pytz.timezone('America/New_York')).date()


def _next_market_open_date(anchor_date):
    """Return the first NYSE trading date on or after anchor_date."""
    nyse = mcal.get_calendar('NYSE')
    schedule = nyse.schedule(
        start_date=anchor_date.isoformat(),
        end_date=(anchor_date + timedelta(days=10)).isoformat(),
    )
    if schedule.empty:
        return None
    return schedule.index[0].date()


def _is_due_today(reminder_day, today):
    """True if today is the reminder day or the next market-open day after it."""
    anchor_date = date(today.year, today.month, reminder_day)
    next_open = _next_market_open_date(anchor_date)
    return next_open == today


def run():
    today = _today_et()
    print(f"[DCA reminders] Running for {today.isoformat()} (ET).")

    with app.app_context():
        users = User.query.filter_by(dca_reminder_enabled=True).filter(
            User.email != None,          # noqa: E711
            User.email_verified == True  # noqa: E712
        ).all()

        if not users:
            print("[DCA reminders] No reminders scheduled for today.")
            return

        due_users = [
            user for user in users
            if user.dca_reminder_day and _is_due_today(user.dca_reminder_day, today)
        ]

        if not due_users:
            print("[DCA reminders] No reminders due on the current market schedule.")
            return

        sent = 0
        failed = 0
        for user in due_users:
            ok = send_dca_reminder_email(user.email, user.username)
            if ok:
                sent += 1
                print(f"  ✓ Sent to {user.email} (user: {user.username})")
            else:
                failed += 1
                print(f"  ✗ Failed for {user.email} (user: {user.username})")

        print(f"[DCA reminders] Done — {sent} sent, {failed} failed.")


if __name__ == '__main__':
    run()
