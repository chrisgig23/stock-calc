#!/usr/bin/env python3
"""
send_dca_reminders.py — Daily job: send DCA reminder emails to opted-in users.

Schedule this on PythonAnywhere as a daily task at 09:30 ET (14:30 UTC):
    /home/chrisgig23/.virtualenvs/stockcalc-env/bin/python \
        /home/chrisgig23/stock-calc/send_dca_reminders.py

The script checks today's day-of-month and emails every user whose
dca_reminder_enabled=True and dca_reminder_day matches today.
"""

import os
import sys
from datetime import date

# ── Bootstrap Flask app context ───────────────────────────────────────────────
# Add the project root to the path so imports resolve correctly.
sys.path.insert(0, os.path.dirname(__file__))

# Point at the production database.
os.environ.setdefault('FLASK_ENV', 'production')

from flask_app import app, db
from flask_app.models import User
from flask_app.email_utils import send_dca_reminder_email


def run():
    today_day = date.today().day
    print(f"[DCA reminders] Running for day {today_day} of the month.")

    with app.app_context():
        users = User.query.filter_by(dca_reminder_enabled=True).filter(
            User.dca_reminder_day == today_day,
            User.email != None,          # noqa: E711
            User.email_verified == True  # noqa: E712
        ).all()

        if not users:
            print("[DCA reminders] No reminders scheduled for today.")
            return

        sent = 0
        failed = 0
        for user in users:
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
