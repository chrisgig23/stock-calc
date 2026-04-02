"""
email_utils.py — Resend-backed transactional email helpers.

Requires:
  - pip install resend
  - RESEND_API_KEY env var set
  - Sending domain (wealthtrackapp.com) verified in Resend dashboard
"""

import os
import resend

FROM_ADDRESS = "WealthWise <noreply@wealthtrackapp.com>"


def _get_client():
    resend.api_key = os.getenv("RESEND_API_KEY", "")


def send_verification_email(to_email: str, code: str, username: str) -> bool:
    """Send a 6-digit email verification code to the user."""
    _get_client()
    try:
        params: resend.Emails.SendParams = {
            "from": FROM_ADDRESS,
            "to": [to_email],
            "subject": "Verify your email — WealthWise",
            "html": f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:40px 16px;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08);">

        <!-- Header -->
        <tr><td style="background:#1e1b4b;padding:28px 32px;">
          <span style="color:#a78bfa;font-size:1.3rem;font-weight:700;letter-spacing:-0.02em;">WealthWise™</span>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:32px;">
          <h2 style="margin:0 0 12px;color:#111827;font-size:1.25rem;">Verify your email address</h2>
          <p style="color:#4b5563;margin:0 0 24px;line-height:1.6;">
            Hi {username},<br><br>
            Enter the code below to verify <strong>{to_email}</strong> as your login email for WealthWise.
            This code expires in <strong>15 minutes</strong>.
          </p>

          <!-- Code box -->
          <div style="background:#f5f3ff;border:2px solid #7c3aed;border-radius:10px;padding:28px 32px;text-align:center;margin:0 0 28px;">
            <span style="font-size:2.8rem;font-weight:800;letter-spacing:0.35em;color:#6d28d9;font-variant-numeric:tabular-nums;">{code}</span>
          </div>

          <p style="color:#6b7280;font-size:0.82rem;line-height:1.5;margin:0;">
            If you didn't request this, you can safely ignore this email — your account is not affected.
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#f9fafb;padding:20px 32px;border-top:1px solid #e5e7eb;">
          <p style="color:#9ca3af;font-size:0.75rem;margin:0;line-height:1.5;">
            WealthWise · Your data stays yours. No ads, no sharing.
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
            """,
        }
        resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"[email] Failed to send verification email to {to_email}: {e}")
        return False


def send_dca_reminder_email(to_email: str, username: str) -> bool:
    """Send the monthly DCA purchase reminder email."""
    _get_client()
    try:
        params: resend.Emails.SendParams = {
            "from": FROM_ADDRESS,
            "to": [to_email],
            "subject": "💰 Your monthly DCA reminder — WealthWise",
            "html": f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:40px 16px;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08);">

        <!-- Header -->
        <tr><td style="background:#1e1b4b;padding:28px 32px;">
          <span style="color:#a78bfa;font-size:1.3rem;font-weight:700;letter-spacing:-0.02em;">WealthWise™</span>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:32px;">
          <h2 style="margin:0 0 12px;color:#111827;font-size:1.25rem;">Time to make your monthly purchase 💰</h2>
          <p style="color:#4b5563;margin:0 0 20px;line-height:1.6;">
            Hi {username},<br><br>
            This is your scheduled reminder to make your monthly dollar cost averaging (DCA) purchase.
            Consistent, regular investing is one of the most powerful habits you can build — today's a great day to keep it going.
          </p>

          <!-- CTA box -->
          <div style="background:#f5f3ff;border:2px solid #7c3aed;border-radius:10px;padding:22px 28px;text-align:center;margin:0 0 28px;">
            <p style="margin:0 0 16px;color:#4c1d95;font-size:0.95rem;font-weight:600;">
              Ready to invest?
            </p>
            <a href="https://www.wealthtrackapp.com"
               style="display:inline-block;background:#6d28d9;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:700;font-size:0.95rem;">
              Open WealthWise →
            </a>
          </div>

          <p style="color:#6b7280;font-size:0.82rem;line-height:1.6;margin:0 0 8px;">
            After making your purchase, remember to log it in WealthWise under <strong>Make a Purchase</strong>
            or import your updated transactions from your broker.
          </p>
          <p style="color:#9ca3af;font-size:0.78rem;line-height:1.5;margin:0;">
            You're receiving this because you opted in to monthly DCA reminders.
            To turn this off, visit <a href="https://www.wealthtrackapp.com/manage_user/{{}}" style="color:#6d28d9;">Settings</a> and uncheck the reminder option.
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#f9fafb;padding:20px 32px;border-top:1px solid #e5e7eb;">
          <p style="color:#9ca3af;font-size:0.75rem;margin:0;line-height:1.5;">
            WealthWise · Stay consistent. Stay invested.
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
            """,
        }
        resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"[email] Failed to send DCA reminder to {to_email}: {e}")
        return False


def send_password_reset_notification(to_email: str, username: str, temp_password: str) -> bool:
    """Notify a user that their password was reset by an admin."""
    _get_client()
    try:
        params: resend.Emails.SendParams = {
            "from": FROM_ADDRESS,
            "to": [to_email],
            "subject": "Your WealthWise password has been reset",
            "html": f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:40px 16px;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08);">
        <tr><td style="background:#1e1b4b;padding:28px 32px;">
          <span style="color:#a78bfa;font-size:1.3rem;font-weight:700;">WealthWise™</span>
        </td></tr>
        <tr><td style="padding:32px;">
          <h2 style="margin:0 0 12px;color:#111827;font-size:1.25rem;">Password reset by administrator</h2>
          <p style="color:#4b5563;margin:0 0 20px;line-height:1.6;">
            Hi {username},<br><br>
            An administrator has reset your WealthWise password. Use the temporary password below to sign in,
            then you'll be prompted to choose a new one.
          </p>
          <div style="background:#fef3c7;border:2px solid #f59e0b;border-radius:10px;padding:20px 24px;margin:0 0 24px;">
            <p style="margin:0 0 6px;color:#92400e;font-size:0.8rem;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">Temporary password</p>
            <code style="font-size:1.4rem;font-weight:700;color:#78350f;letter-spacing:0.05em;">{temp_password}</code>
          </div>
          <p style="color:#6b7280;font-size:0.82rem;line-height:1.5;margin:0;">
            If you didn't expect this email, please contact your account administrator immediately.
          </p>
        </td></tr>
        <tr><td style="background:#f9fafb;padding:20px 32px;border-top:1px solid #e5e7eb;">
          <p style="color:#9ca3af;font-size:0.75rem;margin:0;">WealthWise · Your data stays yours.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
            """,
        }
        resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"[email] Failed to send reset notification to {to_email}: {e}")
        return False
