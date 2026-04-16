"""
email_utils.py — Resend-backed transactional email helpers.

Requires:
  - pip install resend
  - RESEND_API_KEY env var set
  - Sending domain (wealthtrackapp.com) verified in Resend dashboard
"""

import os
import html
try:
    import resend
except ModuleNotFoundError:
    resend = None

FROM_ADDRESS = "WealthTrack <noreply@wealthtrackapp.com>"


def _get_client():
    if resend is None:
        print("[email] resend package is not installed; email sending is disabled.")
        return False

    resend.api_key = os.getenv("RESEND_API_KEY", "")
    return True


def send_verification_email(to_email: str, code: str, username: str) -> bool:
    """Send a 6-digit email verification code to the user."""
    if not _get_client():
        return False
    try:
        params = {
            "from": FROM_ADDRESS,
            "to": [to_email],
            "subject": "Verify your email for WealthTrack",
            "text": (
                f"Hi {username},\n\n"
                f"Use this 6-digit code to verify {to_email} for your WealthTrack account:\n\n"
                f"{code}\n\n"
                "This code expires in 15 minutes.\n\n"
                "If the message landed in spam or junk, mark it as Not Spam and add "
                "noreply@wealthtrackapp.com to your contacts or safe senders list.\n\n"
                "If you didn't request this, you can safely ignore this email."
            ),
            "html": f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:40px 16px;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08);">

        <!-- Header -->
        <tr><td style="background:#1e1b4b;padding:28px 32px;">
          <span style="color:#a78bfa;font-size:1.3rem;font-weight:700;letter-spacing:-0.02em;">WealthTrack™</span>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:32px;">
          <h2 style="margin:0 0 12px;color:#111827;font-size:1.25rem;">Verify your email address</h2>
          <p style="color:#4b5563;margin:0 0 24px;line-height:1.6;">
            Hi {username},<br><br>
            Enter the code below to verify <strong>{to_email}</strong> as your login email for WealthTrack.
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
            WealthTrack · Your data stays yours. No ads, no sharing.
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
    if not _get_client():
        return False
    try:
        params = {
            "from": FROM_ADDRESS,
            "to": [to_email],
            "subject": "💰 Your monthly DCA reminder — WealthTrack",
            "text": (
                f"Hi {username},\n\n"
                "This is your scheduled reminder to make your monthly dollar cost averaging "
                "(DCA) purchase.\n\n"
                "Open WealthTrack: https://www.wealthtrackapp.com\n\n"
                "You're receiving this because you opted in to monthly DCA reminders. "
                "To turn this off, visit your WealthTrack settings."
            ),
            "html": f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:40px 16px;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08);">

        <!-- Header -->
        <tr><td style="background:#1e1b4b;padding:28px 32px;">
          <span style="color:#a78bfa;font-size:1.3rem;font-weight:700;letter-spacing:-0.02em;">WealthTrack™</span>
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
              Open WealthTrack →
            </a>
          </div>

          <p style="color:#6b7280;font-size:0.82rem;line-height:1.6;margin:0 0 8px;">
            After making your purchase, remember to log it in WealthTrack under <strong>Make a Purchase</strong>
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
            WealthTrack · Stay consistent. Stay invested.
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
    if not _get_client():
        return False
    try:
        params = {
            "from": FROM_ADDRESS,
            "to": [to_email],
            "subject": "Your WealthTrack password has been reset",
            "text": (
                f"Hi {username},\n\n"
                "An administrator has reset your WealthTrack password.\n\n"
                f"Temporary password: {temp_password}\n\n"
                "Use it to sign in, then choose a new password.\n\n"
                "If you didn't expect this email, please contact your account administrator "
                "immediately."
            ),
            "html": f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:40px 16px;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08);">
        <tr><td style="background:#1e1b4b;padding:28px 32px;">
          <span style="color:#a78bfa;font-size:1.3rem;font-weight:700;">WealthTrack™</span>
        </td></tr>
        <tr><td style="padding:32px;">
          <h2 style="margin:0 0 12px;color:#111827;font-size:1.25rem;">Password reset by administrator</h2>
          <p style="color:#4b5563;margin:0 0 20px;line-height:1.6;">
            Hi {username},<br><br>
            An administrator has reset your WealthTrack password. Use the temporary password below to sign in,
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
          <p style="color:#9ca3af;font-size:0.75rem;margin:0;">WealthTrack · Your data stays yours.</p>
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


def send_password_reset_email(to_email: str, username: str, reset_url: str) -> bool:
    """Send a self-service password reset link."""
    if not _get_client():
        return False
    try:
        params = {
            "from": FROM_ADDRESS,
            "to": [to_email],
            "subject": "Reset your WealthTrack password",
            "text": (
                f"Hi {username},\n\n"
                "We received a request to reset the password for your WealthTrack account.\n\n"
                f"Reset password: {reset_url}\n\n"
                "This link expires in 1 hour.\n\n"
                "If you didn't request this, you can safely ignore this email and your "
                "password will stay the same."
            ),
            "html": f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:40px 16px;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08);">
        <tr><td style="background:#1e1b4b;padding:28px 32px;">
          <span style="color:#a78bfa;font-size:1.3rem;font-weight:700;">WealthTrack™</span>
        </td></tr>
        <tr><td style="padding:32px;">
          <h2 style="margin:0 0 12px;color:#111827;font-size:1.25rem;">Reset your password</h2>
          <p style="color:#4b5563;margin:0 0 20px;line-height:1.6;">
            Hi {username},<br><br>
            We received a request to reset the password for your WealthTrack account.
            Use the button below to choose a new password. This link expires in <strong>1 hour</strong>.
          </p>
          <div style="margin:0 0 24px;">
            <a href="{reset_url}"
               style="display:inline-block;background:#6d28d9;color:#ffffff;text-decoration:none;padding:12px 24px;border-radius:8px;font-weight:700;font-size:0.95rem;">
              Reset password
            </a>
          </div>
          <p style="color:#6b7280;font-size:0.82rem;line-height:1.5;margin:0 0 12px;">
            If the button doesn't work, copy and paste this link into your browser:
          </p>
          <p style="margin:0 0 20px;word-break:break-all;font-size:0.82rem;line-height:1.6;">
            <a href="{reset_url}" style="color:#6d28d9;">{reset_url}</a>
          </p>
          <p style="color:#6b7280;font-size:0.82rem;line-height:1.5;margin:0;">
            If you didn't request this, you can safely ignore this email and your password will stay the same.
          </p>
        </td></tr>
        <tr><td style="background:#f9fafb;padding:20px 32px;border-top:1px solid #e5e7eb;">
          <p style="color:#9ca3af;font-size:0.75rem;margin:0;">WealthTrack · Your data stays yours.</p>
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
        print(f"[email] Failed to send password reset email to {to_email}: {e}")
        return False


def send_invite_approval_email(to_email: str, name: str, invite_code: str) -> bool:
    """Send the invite code to an approved requester."""
    if not _get_client():
        return False
    try:
        signup_url = "https://www.wealthtrackapp.com/signup"
        params = {
            "from": FROM_ADDRESS,
            "to": [to_email],
            "subject": "You're invited to WealthTrack 🎉",
            "text": (
                f"Hi {name},\n\n"
                "Great news — your request for access to WealthTrack has been approved!\n\n"
                f"Your invite code: {invite_code}\n\n"
                f"Use it to create your account here: {signup_url}\n\n"
                "Welcome aboard!\n\n"
                "— The WealthTrack Team"
            ),
            "html": f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:40px 16px;">
    <tr><td align="center">
      <table width="100%" style="max-width:480px;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08);">

        <!-- Header -->
        <tr><td style="background:#0f172a;padding:28px 32px;">
          <span style="color:#a78bfa;font-size:1.3rem;font-weight:700;letter-spacing:-0.02em;">WealthTrack™</span>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:32px;">
          <h2 style="margin:0 0 12px;color:#111827;font-size:1.25rem;">You're in! 🎉</h2>
          <p style="color:#4b5563;margin:0 0 24px;line-height:1.6;">
            Hi {html.escape(name)},<br><br>
            Your request for access to WealthTrack has been approved. Use the invite code below
            to create your account.
          </p>

          <!-- Invite code box -->
          <div style="background:#f5f3ff;border:2px solid #7c3aed;border-radius:10px;padding:24px 32px;text-align:center;margin:0 0 28px;">
            <p style="margin:0 0 8px;color:#4c1d95;font-size:0.8rem;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;">Your invite code</p>
            <code style="font-size:1.8rem;font-weight:800;letter-spacing:0.15em;color:#6d28d9;">{html.escape(invite_code)}</code>
          </div>

          <!-- CTA -->
          <div style="text-align:center;margin:0 0 28px;">
            <a href="{signup_url}"
               style="display:inline-block;background:#6d28d9;color:#ffffff;text-decoration:none;padding:13px 32px;border-radius:8px;font-weight:700;font-size:0.95rem;">
              Create your account →
            </a>
          </div>

          <p style="color:#6b7280;font-size:0.82rem;line-height:1.5;margin:0;">
            If you didn't request access to WealthTrack, you can safely ignore this email.
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#f9fafb;padding:20px 32px;border-top:1px solid #e5e7eb;">
          <p style="color:#9ca3af;font-size:0.75rem;margin:0;line-height:1.5;">
            WealthTrack · Your portfolio, finally organized.
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
        print(f"[email] Failed to send invite approval email to {to_email}: {e}")
        return False


def send_invite_denial_email(to_email: str, name: str) -> bool:
    """Send a cordial denial to a requester, with a contact option."""
    if not _get_client():
        return False
    try:
        contact_email = "support@wealthtrackapp.com"
        params = {
            "from": FROM_ADDRESS,
            "to": [to_email],
            "subject": "Your WealthTrack access request",
            "text": (
                f"Hi {name},\n\n"
                "Thank you for your interest in WealthTrack.\n\n"
                "Unfortunately we're not able to extend an invitation at this time — we're keeping access limited while the app is in early development.\n\n"
                "If you have questions or want to be considered again in the future, feel free to reach out at "
                f"{contact_email}.\n\n"
                "Thanks again for your interest!\n\n"
                "— The WealthTrack Team"
            ),
            "html": f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:40px 16px;">
    <tr><td align="center">
      <table width="100%" style="max-width:480px;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08);">

        <!-- Header -->
        <tr><td style="background:#0f172a;padding:28px 32px;">
          <span style="color:#a78bfa;font-size:1.3rem;font-weight:700;letter-spacing:-0.02em;">WealthTrack™</span>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:32px;">
          <h2 style="margin:0 0 12px;color:#111827;font-size:1.25rem;">Thanks for your interest</h2>
          <p style="color:#4b5563;margin:0 0 20px;line-height:1.6;">
            Hi {html.escape(name)},<br><br>
            Thank you for reaching out about WealthTrack. Unfortunately, we're not able to
            extend an invitation at this time — we're keeping access limited while the app
            is in early development.
          </p>
          <p style="color:#4b5563;margin:0 0 24px;line-height:1.6;">
            If you have questions or would like to be considered again in the future, feel
            free to get in touch:
          </p>

          <!-- Contact box -->
          <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:20px 24px;text-align:center;margin:0 0 28px;">
            <p style="margin:0 0 6px;color:#64748b;font-size:0.82rem;">Contact us at</p>
            <a href="mailto:{contact_email}"
               style="color:#6d28d9;font-weight:600;font-size:1rem;text-decoration:none;">{contact_email}</a>
          </div>

          <p style="color:#6b7280;font-size:0.82rem;line-height:1.5;margin:0;">
            We appreciate your interest and hope to welcome you in the future.
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#f9fafb;padding:20px 32px;border-top:1px solid #e5e7eb;">
          <p style="color:#9ca3af;font-size:0.75rem;margin:0;line-height:1.5;">
            WealthTrack · Your portfolio, finally organized.
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
        print(f"[email] Failed to send invite denial email to {to_email}: {e}")
        return False


def send_invite_request_notification(
    requester_name: str,
    requester_email: str,
    requester_note: str = '',
    approve_url: str = '',
    deny_url: str = '',
) -> bool:
    """
    Notify the site admin that someone has requested an invite code.
    Optionally embeds one-click Approve / Deny buttons if action URLs are provided.
    The admin's email address is read from the NOTIFY_EMAIL env var — never
    exposed in any template or client-side code.
    """
    admin_email = os.getenv("NOTIFY_EMAIL", "")
    if not admin_email:
        print("[email] NOTIFY_EMAIL not set — invite request notification skipped.")
        return False
    if not _get_client():
        return False

    note_row = (
        f'<tr>'
        f'<td style="padding:10px 14px;font-size:0.85rem;color:#6b7280;background:#f9fafb;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 0 6px;font-weight:600;">Note</td>'
        f'<td style="padding:10px 14px;font-size:0.85rem;color:#111827;background:#fff;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 6px 0;">{html.escape(requester_note)}</td>'
        f'</tr>'
        if requester_note else ''
    )

    action_buttons = ''
    if approve_url and deny_url:
        action_buttons = f"""
          <!-- Approve / Deny actions -->
          <table style="width:100%;border-collapse:collapse;margin-bottom:8px;">
            <tr>
              <td style="padding-right:8px;">
                <a href="{approve_url}"
                   style="display:block;background:#16a34a;color:#fff;text-decoration:none;padding:12px 0;border-radius:8px;font-weight:700;font-size:0.9rem;text-align:center;">
                  ✅ Approve — Send Invite Code
                </a>
              </td>
              <td style="padding-left:8px;">
                <a href="{deny_url}"
                   style="display:block;background:#dc2626;color:#fff;text-decoration:none;padding:12px 0;border-radius:8px;font-weight:700;font-size:0.9rem;text-align:center;">
                  ✗ Deny Request
                </a>
              </td>
            </tr>
          </table>
          <p style="color:#9ca3af;font-size:0.75rem;text-align:center;margin:0 0 24px;">
            These links are valid for 7 days and can only be used once per request.
          </p>
        """

    action_text = (
        f"\nApprove (sends invite code automatically):\n{approve_url}\n\n"
        f"Deny (sends cordial decline):\n{deny_url}\n"
        if approve_url and deny_url else
        "If you'd like to grant access, reply to their email with your current invite code."
    )

    try:
        params = {
            "from": FROM_ADDRESS,
            "to": [admin_email],
            "subject": "WealthTrack — New Invite Code Request",
            "text": (
                "Someone has requested access to WealthTrack.\n\n"
                f"Name: {requester_name}\n"
                f"Email: {requester_email}\n"
                f"Note: {requester_note or '(none)'}\n\n"
                + action_text
            ),
            "html": f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 16px;">
      <table width="100%" style="max-width:480px;background:#ffffff;border-radius:12px;border:1px solid #e5e7eb;">
        <tr><td style="background:#0f172a;padding:20px 32px;border-radius:12px 12px 0 0;">
          <span style="color:#a78bfa;font-size:1.3rem;font-weight:700;">WealthTrack™</span>
        </td></tr>
        <tr><td style="padding:32px;">
          <h2 style="margin:0 0 12px;color:#111827;font-size:1.15rem;">New invite code request</h2>
          <p style="color:#4b5563;margin:0 0 20px;line-height:1.6;">
            Someone has requested access to WealthTrack:
          </p>
          <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
            <tr>
              <td style="padding:10px 14px;font-size:0.85rem;color:#6b7280;background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px 0 0 0;font-weight:600;width:30%;">Name</td>
              <td style="padding:10px 14px;font-size:0.85rem;color:#111827;background:#fff;border:1px solid #e5e7eb;border-radius:0 6px 0 0;">{html.escape(requester_name)}</td>
            </tr>
            <tr>
              <td style="padding:10px 14px;font-size:0.85rem;color:#6b7280;background:#f9fafb;border:1px solid #e5e7eb;border-top:none;font-weight:600;">Email</td>
              <td style="padding:10px 14px;font-size:0.85rem;color:#111827;background:#fff;border:1px solid #e5e7eb;border-top:none;">
                <a href="mailto:{html.escape(requester_email)}" style="color:#6d28d9;">{html.escape(requester_email)}</a>
              </td>
            </tr>
            {note_row}
          </table>
          {action_buttons}
        </td></tr>
        <tr><td style="background:#f9fafb;padding:20px 32px;border-top:1px solid #e5e7eb;">
          <p style="color:#9ca3af;font-size:0.75rem;margin:0;">WealthTrack · Your data stays yours.</p>
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
        print(f"[email] Failed to send invite request notification: {e}")
        return False
