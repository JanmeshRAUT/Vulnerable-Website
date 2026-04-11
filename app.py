import os
import sys
import sqlite3
import subprocess
import requests
import smtplib
import ssl
import string
import random
import re
import uuid
from html import escape as html_escape
from email.message import EmailMessage
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g, send_file, send_from_directory, Response, g, jsonify
from datetime import datetime, timedelta
import shutil
import secrets
import time
import threading
import copy
from authlib.integrations.flask_client import OAuth
from werkzeug.middleware.proxy_fix import ProxyFix
from firebase_db import FirebaseDataStore
import zipfile
import hashlib
import csv
import io
from collections import Counter


try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # Keep running if python-dotenv is unavailable in some environments.
    pass

# For local development, allow HTTP for OAuth.
if not os.environ.get('VERCEL'):
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Get base directory (works for both EXE and script execution)
def get_base_path():
    """Get the base path for resources (works for both dev and PyInstaller)"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running as compiled executable - extract temp directory
        return getattr(sys, '_MEIPASS')
    else:
        # Running as script - use current directory
        return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()
PUBLIC_STATIC_ROOT = os.path.join(BASE_PATH, 'public', 'static')
LEGACY_STATIC_ROOT = os.path.join(BASE_PATH, 'static')
STATIC_ROOT = PUBLIC_STATIC_ROOT if os.path.isdir(PUBLIC_STATIC_ROOT) else LEGACY_STATIC_ROOT

# Detect Vercel Environment
IS_VERCEL = os.environ.get('VERCEL') == '1'

app = Flask(__name__, static_folder=STATIC_ROOT, static_url_path='/static')
# USE ENVIRONMENT VARIABLES FOR PRODUCTION SECRETS
app.secret_key = os.environ.get('SECRET_KEY', 'default_vulnerable_key_replace_in_prod')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=14)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = IS_VERCEL
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024 # 500MB for large binaries
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

LAB4_2_RUNTIME_STATE = {
    'target_ips': {},
    'logged_variants': {}
}

# Reduce repeated Firebase round-trips for lab gate checks.
ACCESS_GATE_CACHE_TTL_SECONDS = int(os.environ.get('ACCESS_GATE_CACHE_TTL_SECONDS', '90'))
ACCESS_GATE_CACHE = {}
ACCESS_GATE_CACHE_LOCK = threading.Lock()

ADMIN_VIEW_CACHE_TTL_SECONDS = int(os.environ.get('ADMIN_VIEW_CACHE_TTL_SECONDS', '30'))
ADMIN_VIEW_CACHE = {}
ADMIN_VIEW_CACHE_LOCK = threading.Lock()


def get_or_refresh_access_gate_cache(email, force_refresh=False, preloaded_user=None):
    """Return approval and enrollment access data for an email using TTL cache."""
    now_ts = int(time.time())

    if not force_refresh:
        with ACCESS_GATE_CACHE_LOCK:
            cached = ACCESS_GATE_CACHE.get(email)
        if cached and (now_ts - int(cached.get('ts', 0))) <= ACCESS_GATE_CACHE_TTL_SECONDS:
            return cached

    user = preloaded_user if preloaded_user is not None else firebase_store.get_user_by_email(email)
    is_approved = bool(user and user.get('is_approved'))

    approved_lab_ids = set()
    approved_family_ids = set()

    if is_approved:
        approved_enrollments = firebase_store.get_user_lab_enrollments(email)
        for enrollment in approved_enrollments:
            if enrollment.get('approval_status') != 'approved':
                continue
            lab_id_value = str(enrollment.get('lab_id') or '').strip().lower()
            if not lab_id_value:
                continue
            approved_lab_ids.add(lab_id_value)
            approved_family_ids.add(lab_id_value.split('_', 1)[0] + '_')

    refreshed = {
        'is_approved': is_approved,
        'approved_lab_ids': approved_lab_ids,
        'approved_family_ids': approved_family_ids,
        'ts': now_ts,
    }

    with ACCESS_GATE_CACHE_LOCK:
        ACCESS_GATE_CACHE[email] = refreshed

    return refreshed


def get_admin_view_cache(cache_key):
    """Return cached admin payload when still fresh."""
    now_ts = int(time.time())
    with ADMIN_VIEW_CACHE_LOCK:
        entry = ADMIN_VIEW_CACHE.get(cache_key)
    if not entry:
        return None
    if (now_ts - int(entry.get('ts', 0))) > ADMIN_VIEW_CACHE_TTL_SECONDS:
        return None
    return copy.deepcopy(entry.get('payload'))


def set_admin_view_cache(cache_key, payload):
    """Store a copy of admin payload for short-lived reuse."""
    with ADMIN_VIEW_CACHE_LOCK:
        ADMIN_VIEW_CACHE[cache_key] = {
            'ts': int(time.time()),
            'payload': copy.deepcopy(payload)
        }


def invalidate_admin_view_cache():
    """Clear cached admin/analyzer aggregates after data mutations."""
    with ADMIN_VIEW_CACHE_LOCK:
        ADMIN_VIEW_CACHE.clear()


if IS_VERCEL:
    app.config['DB_NAME'] = '/tmp/database.db'
    app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
    app.config['PREFERRED_URL_SCHEME'] = 'https'
    FLAG_BASE_PATH = '/tmp'
    LAB5_AVATAR_ROOT = '/tmp/lab5/uploads/avatars'
else:
    app.config['DB_NAME'] = os.path.join(BASE_PATH, 'database.db')
    app.config['UPLOAD_FOLDER'] = os.path.join(STATIC_ROOT, 'uploads')
    FLAG_BASE_PATH = BASE_PATH
    LAB5_AVATAR_ROOT = os.path.join(STATIC_ROOT, 'lab5', 'uploads', 'avatars')

# Ensure upload directory exists (silent fail on read-only FS)
try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
except Exception:
    pass

try:
    os.makedirs(LAB5_AVATAR_ROOT, exist_ok=True)
except Exception:
    pass

# REAL GOOGLE OAUTH CONFIGURATION
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID', 'placeholder-id'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET', 'placeholder-secret'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
    token_url='https://oauth2.googleapis.com/token',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    client_kwargs={
        'scope': 'openid email profile'
    }
)


def get_google_redirect_uri():
    """Build the OAuth redirect URI, forcing one canonical callback URL."""
    configured = (os.environ.get('GOOGLE_REDIRECT_URI') or '').strip()
    # Always honor an explicitly configured redirect URI so auth start/callback
    # use the same exact host (localhost vs 127.0.0.1 mismatch causes state errors).
    if configured:
        return configured
    # Auto-build from request context
    uri = url_for('google_callback', _external=True)
    # Force https if running behind Vercel's proxy (or any HTTPS host)
    if os.environ.get('VERCEL') or os.environ.get('FORCE_HTTPS'):
        uri = uri.replace('http://', 'https://', 1)
    return uri


def send_admin_authorization_email(request_type, requester_email, requester_name=None, lab_id=None, requester_role='user'):
    """Send admin notification when a user requests account or lab authorization."""
    recipients_raw = (os.environ.get('ADMIN_ALERT_EMAILS') or '').strip()
    if not recipients_raw:
        return False

    smtp_host = (os.environ.get('SMTP_HOST') or '').strip()
    smtp_user = (os.environ.get('SMTP_USERNAME') or '').strip()
    smtp_password = os.environ.get('SMTP_PASSWORD') or ''
    smtp_port = int((os.environ.get('SMTP_PORT') or '587').strip())
    smtp_use_tls = (os.environ.get('SMTP_USE_TLS', 'true').strip().lower() in {'1', 'true', 'yes', 'on'})
    sender = (os.environ.get('SMTP_FROM_EMAIL') or smtp_user or 'no-reply@research-ops.local').strip()

    if not smtp_host or not sender:
        return False

    recipients = [email.strip() for email in recipients_raw.split(',') if email.strip()]
    if not recipients:
        return False

    requested_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    app_url = (request.host_url or '').rstrip('/')
    requester_display = requester_name or requester_email
    identity_value = f"{requester_display} ({(requester_role or 'user').upper()})"
    approve_url = f"{app_url}/admin/students#tab-authorization"
    deny_url = f"{app_url}/admin/students#tab-authorization"

    if request_type == 'account':
        subject = "ðŸš¨ Action Required: New VulnHub Access Request"
        request_label = "Account approval"
        detail_lines = [
            f"Identity: {identity_value}",
            f"Email: {requester_email}",
            f"Request Type: {request_label}",
            f"Requested At: {requested_at}",
            f"Admin Queue: {app_url}/admin/students",
        ]
    else:
        subject = "ðŸš¨ Action Required: New VulnHub Access Request"
        request_label = f"Lab access approval ({lab_id})"
        detail_lines = [
            f"Identity: {identity_value}",
            f"Email: {requester_email}",
            f"Request Type: {request_label}",
            f"Requested At: {requested_at}",
            f"Admin Queue: {app_url}/admin/students",
        ]

    html_body = f"""<!doctype html>
<html lang=\"en\" xmlns=\"http://www.w3.org/1999/xhtml\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0\">
    <meta http-equiv=\"X-UA-Compatible\" content=\"IE=edge\">
    <title>Admin Access Request Notification</title>
</head>
<body style=\"margin:0; padding:0; background-color:#f3f6fb; font-family:Arial, Helvetica, sans-serif; color:#1f2937;\">
    <table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" border=\"0\" style=\"background-color:#f3f6fb; padding:24px 0;\">
        <tr>
            <td align=\"center\">
                <table role=\"presentation\" width=\"640\" cellpadding=\"0\" cellspacing=\"0\" border=\"0\" style=\"width:640px; max-width:640px; background:#ffffff; border:1px solid #dbe3ef; border-radius:12px; overflow:hidden;\">
                    <tr>
                        <td style=\"padding:24px 28px; background:linear-gradient(90deg,#1d4ed8,#3b82f6);\">
                            <h1 style=\"margin:0; font-size:22px; line-height:1.3; color:#ffffff; font-weight:700;\">VulnHub Access System</h1>
                            <p style=\"margin:8px 0 0; font-size:14px; line-height:1.5; color:#dbeafe;\">New access request requires administrator review</p>
                        </td>
                    </tr>
                    <tr>
                        <td style=\"padding:24px 28px 10px;\">
                            <p style=\"margin:0; font-size:15px; line-height:1.7; color:#374151;\">A new authorization request has been submitted and is awaiting your decision.</p>
                        </td>
                    </tr>
                    <tr>
                        <td style=\"padding:12px 28px 8px;\">
                            <table role=\"presentation\" width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" border=\"0\" style=\"border:1px solid #dbe3ef; border-radius:10px; background:#f8fbff;\">
                                <tr>
                                    <td colspan=\"2\" style=\"padding:14px 16px; border-bottom:1px solid #dbe3ef; background:#eef4ff;\">
                                        <h2 style=\"margin:0; font-size:16px; color:#1e40af; font-weight:700;\">Request Details</h2>
                                    </td>
                                </tr>
                                <tr>
                                    <td style=\"padding:12px 16px; width:180px; font-size:14px; color:#6b7280; border-bottom:1px solid #e5eaf3;\">Identity</td>
                                    <td style=\"padding:12px 16px; font-size:14px; color:#111827; border-bottom:1px solid #e5eaf3;\">{html_escape(identity_value)}</td>
                                </tr>
                                <tr>
                                    <td style=\"padding:12px 16px; width:180px; font-size:14px; color:#6b7280; border-bottom:1px solid #e5eaf3;\">User Email</td>
                                    <td style=\"padding:12px 16px; font-size:14px; color:#111827; border-bottom:1px solid #e5eaf3;\">{html_escape(requester_email)}</td>
                                </tr>
                                <tr>
                                    <td style=\"padding:12px 16px; width:180px; font-size:14px; color:#6b7280; border-bottom:1px solid #e5eaf3;\">Request Type</td>
                                    <td style=\"padding:12px 16px; font-size:14px; color:#111827; border-bottom:1px solid #e5eaf3;\">{html_escape(request_label)}</td>
                                </tr>
                                <tr>
                                    <td style=\"padding:12px 16px; width:180px; font-size:14px; color:#6b7280;\">Timestamp</td>
                                    <td style=\"padding:12px 16px; font-size:14px; color:#111827;\">{html_escape(requested_at)}</td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style=\"padding:20px 28px 8px;\">
                            <table role=\"presentation\" cellpadding=\"0\" cellspacing=\"0\" border=\"0\">
                                <tr>
                                    <td style=\"padding-right:10px;\"><a href=\"{html_escape(approve_url)}\" style=\"display:inline-block; padding:12px 22px; background:#16a34a; color:#ffffff; text-decoration:none; font-size:14px; font-weight:700; border-radius:8px; border:1px solid #15803d;\">Approve</a></td>
                                    <td><a href=\"{html_escape(deny_url)}\" style=\"display:inline-block; padding:12px 22px; background:#dc2626; color:#ffffff; text-decoration:none; font-size:14px; font-weight:700; border-radius:8px; border:1px solid #b91c1c;\">Deny</a></td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style=\"padding:22px 28px 26px;\"><p style=\"margin:0; font-size:12px; color:#6b7280; line-height:1.6;\">This is an automated message. Please do not reply.</p></td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = sender
    message['To'] = ', '.join(recipients)
    message.set_content(
        "Authorization request received.\n\n"
        + "\n".join(detail_lines)
        + "\n\nPlease review this request in the admin console."
    )
    message.add_alternative(html_body, subtype='html')

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as smtp:
            smtp.ehlo()
            if smtp_use_tls:
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            if smtp_user and smtp_password:
                smtp.login(smtp_user, smtp_password)
            smtp.send_message(message)
        return True
    except Exception as exc:
        print(f"[MAIL] Failed to send authorization notification: {exc}")
        return False


def send_user_access_granted_email(user_email, role='user', approved_lab_ids=None):
    """Send a premium account confirmation email to the end user."""
    if not user_email:
        return False

    smtp_host = (os.environ.get('SMTP_HOST') or '').strip()
    smtp_user = (os.environ.get('SMTP_USERNAME') or '').strip()
    smtp_password = os.environ.get('SMTP_PASSWORD') or ''
    smtp_port = int((os.environ.get('SMTP_PORT') or '587').strip())
    smtp_use_tls = (os.environ.get('SMTP_USE_TLS', 'true').strip().lower() in {'1', 'true', 'yes', 'on'})
    sender = (os.environ.get('SMTP_FROM_EMAIL') or smtp_user or 'no-reply@research-ops.local').strip()

    if not smtp_host or not sender:
        return False

    try:
        app_url = (request.host_url or '').rstrip('/')
    except RuntimeError:
        app_url = (os.environ.get('APP_BASE_URL') or '').strip().rstrip('/')

    approved_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    login_url = f"{app_url}/login" if app_url else ""

    message = EmailMessage()
    message['Subject'] = "Your Account Has Been Approved"
    message['From'] = sender
    message['To'] = user_email
    message.set_content(
        "Your account review is complete and your profile is now ready for use.\n\n"
        + f"Approved At: {approved_at}\n\n"
        + "You may sign in at your convenience to continue.\n"
        + (f"Sign in: {login_url}\n" if login_url else "")
    )

    login_button_html = (
        f'<a href="{login_url}" style="display:inline-block;background:linear-gradient(90deg,#0f172a 0%,#1d4ed8 100%);color:#ffffff;text-decoration:none;font-weight:700;font-size:13px;padding:12px 18px;border-radius:999px;letter-spacing:0.2px;">Sign In</a>'
        if login_url else ''
    )

    html_body = f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
    <title>Account Approved</title>
</head>
<body style=\"margin:0;padding:0;background:#eef2ff;font-family:Arial,Helvetica,sans-serif;color:#0f172a;\">
    <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"background:linear-gradient(180deg,#eef2ff 0%,#f8fafc 100%);padding:28px 12px;\">
        <tr>
            <td align=\"center\">
                <table role=\"presentation\" width=\"640\" cellspacing=\"0\" cellpadding=\"0\" style=\"max-width:640px;background:#ffffff;border:1px solid #e2e8f0;border-radius:18px;overflow:hidden;box-shadow:0 18px 50px rgba(15,23,42,0.08);\">
                    <tr>
                        <td style=\"background:linear-gradient(90deg,#0f172a 0%,#1d4ed8 100%);padding:28px 28px 24px;\">
                            <div style=\"font-size:12px;letter-spacing:2px;text-transform:uppercase;color:#c7d2fe;margin-bottom:10px;\">RESEARCH_OPS</div>
                            <h1 style=\"margin:0;font-size:26px;line-height:1.2;color:#ffffff;font-weight:700;\">Your account is ready</h1>
                            <p style=\"margin:10px 0 0 0;font-size:14px;line-height:1.6;color:#dbeafe;max-width:500px;\">A formal review has been completed and your profile has been prepared for a seamless sign-in experience.</p>
                        </td>
                    </tr>
                    <tr>
                        <td style=\"padding:28px 28px 20px;\">
                            <p style=\"margin:0 0 16px 0;font-size:15px;line-height:1.8;color:#111827;\">
                                Hello,
                            </p>
                            <p style=\"margin:0 0 16px 0;font-size:15px;line-height:1.8;color:#111827;\">
                                We are pleased to let you know that your account review has been completed successfully. Your profile is now active and ready whenever you are.
                            </p>

                            <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"border:1px solid #dbe3ef;border-radius:14px;background:linear-gradient(180deg,#f8fbff 0%,#ffffff 100%);margin:0 0 18px 0;\">
                                <tr>
                                    <td style=\"padding:16px 18px;font-size:13px;color:#374151;line-height:1.8;\">
                                        <div><strong>Status:</strong> Approved and ready</div>
                                        <div><strong>Reviewed:</strong> {approved_at}</div>
                                    </td>
                                </tr>
                            </table>

                            <div style=\"background:linear-gradient(90deg,rgba(15,23,42,0.03),rgba(29,78,216,0.06));border:1px solid #e2e8f0;border-radius:14px;padding:18px 18px 16px;margin:0 0 18px 0;\">
                                <div style=\"font-size:12px;letter-spacing:1.6px;text-transform:uppercase;color:#64748b;margin-bottom:8px;\">Next Step</div>
                                <p style=\"margin:0;font-size:14px;line-height:1.7;color:#111827;\">Please sign in to continue. If you need help, our support team is available to assist you.</p>
                            </div>

                            {login_button_html}

                            <p style=\"margin:18px 0 0 0;font-size:12px;color:#64748b;line-height:1.7;\">
                                If this update was unexpected, please contact support so we can assist promptly.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
    message.add_alternative(html_body, subtype='html')

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as smtp:
            smtp.ehlo()
            if smtp_use_tls:
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            if smtp_user and smtp_password:
                smtp.login(smtp_user, smtp_password)
            smtp.send_message(message)
        return True
    except Exception as exc:
        print(f"[MAIL] Failed to send user access confirmation: {exc}")
        return False

firebase_store = FirebaseDataStore(BASE_PATH)
firebase_store.initialize()

TRACKABLE_LAB_UNITS = [
    {'id': 'lab1_1', 'canonical_id': 'lab1', 'label': 'Lab 1.1', 'path': '/lab1/1'},
    {'id': 'lab1_2', 'canonical_id': 'lab1', 'label': 'Lab 1.2', 'path': '/lab1/2'},
    {'id': 'lab1_3', 'canonical_id': 'lab1', 'label': 'Lab 1.3', 'path': '/lab1/3'},
    {'id': 'lab2_1_a', 'canonical_id': 'lab2_1', 'label': 'Lab 2.1 A', 'path': '/lab2/1'},
    {'id': 'lab2_1_b', 'canonical_id': 'lab2_1', 'label': 'Lab 2.1 B', 'path': '/lab2/1/b'},
    {'id': 'lab2_1_c', 'canonical_id': 'lab2_1', 'label': 'Lab 2.1 C', 'path': '/lab2/1/c'},
    {'id': 'lab2_2_a', 'canonical_id': 'lab2_2', 'label': 'Lab 2.2 A', 'path': '/lab2/2'},
    {'id': 'lab2_2_b', 'canonical_id': 'lab2_2', 'label': 'Lab 2.2 B', 'path': '/lab2/2/bookstore'},
    {'id': 'lab2_2_c', 'canonical_id': 'lab2_2', 'label': 'Lab 2.2 C', 'path': '/lab2/2/gamezone'},
    {'id': 'lab2_3_a', 'canonical_id': 'lab2_3', 'label': 'Lab 2.3 Music', 'path': '/lab2/3/music'},
    {'id': 'lab2_3_b', 'canonical_id': 'lab2_3', 'label': 'Lab 2.3 Sports', 'path': '/lab2/3/sports'},
    {'id': 'lab2_3_c', 'canonical_id': 'lab2_3', 'label': 'Lab 2.3 Pets', 'path': '/lab2/3/pets'},
    {'id': 'lab2_4_a', 'canonical_id': 'lab2_4', 'label': 'Lab 2.4 A', 'path': '/lab2/4'},
    {'id': 'lab2_4_b', 'canonical_id': 'lab2_4', 'label': 'Lab 2.4 B', 'path': '/lab2/4b'},
    {'id': 'lab2_4_c', 'canonical_id': 'lab2_4', 'label': 'Lab 2.4 C', 'path': '/lab2/4c'},
    {'id': 'lab2_5_a', 'canonical_id': 'lab2_5', 'label': 'Lab 2.5 A', 'path': '/lab2/5'},
    {'id': 'lab2_5_b', 'canonical_id': 'lab2_5', 'label': 'Lab 2.5 B', 'path': '/lab2/5b'},
    {'id': 'lab2_5_c', 'canonical_id': 'lab2_5', 'label': 'Lab 2.5 C', 'path': '/lab2/5c'},
    {'id': 'lab3_1_a', 'canonical_id': 'lab3_1', 'label': 'Lab 3.1 A', 'path': '/lab3/1'},
    {'id': 'lab3_1_b', 'canonical_id': 'lab3_1', 'label': 'Lab 3.1 B', 'path': '/lab3/1/2'},
    {'id': 'lab3_1_c', 'canonical_id': 'lab3_1', 'label': 'Lab 3.1 C', 'path': '/lab3/1/3'},
    {'id': 'lab3_2_a', 'canonical_id': 'lab3_2', 'label': 'Lab 3.2 A', 'path': '/lab3/2'},
    {'id': 'lab3_2_b', 'canonical_id': 'lab3_2', 'label': 'Lab 3.2 B', 'path': '/lab3/2b'},
    {'id': 'lab3_2_c', 'canonical_id': 'lab3_2', 'label': 'Lab 3.2 C', 'path': '/lab3/2c'},
    {'id': 'lab4_1_a', 'canonical_id': 'lab4', 'label': 'Lab 4.1 A', 'path': '/lab4/1/a'},
    {'id': 'lab4_1_b', 'canonical_id': 'lab4', 'label': 'Lab 4.1 B', 'path': '/lab4/1/b'},
    {'id': 'lab4_1_c', 'canonical_id': 'lab4', 'label': 'Lab 4.1 C', 'path': '/lab4/1/c'},
    {'id': 'lab4_2_a', 'canonical_id': 'lab4_2', 'label': 'Lab 4.2 A', 'path': '/lab4/2/a'},
    {'id': 'lab4_2_b', 'canonical_id': 'lab4_2', 'label': 'Lab 4.2 B', 'path': '/lab4/2/b'},
    {'id': 'lab4_2_c', 'canonical_id': 'lab4_2', 'label': 'Lab 4.2 C', 'path': '/lab4/2/c'},
    {'id': 'lab5_1_a', 'canonical_id': 'lab5_1', 'label': 'Lab 5.1 A', 'path': '/lab5/1'},
    {'id': 'lab5_1_b', 'canonical_id': 'lab5_1', 'label': 'Lab 5.1 B', 'path': '/lab5/1/b'},
    {'id': 'lab5_1_c', 'canonical_id': 'lab5_1', 'label': 'Lab 5.1 C', 'path': '/lab5/1/c'},
    {'id': 'lab5_2_a', 'canonical_id': 'lab5_2', 'label': 'Lab 5.2 A', 'path': '/lab5/2'},
    {'id': 'lab5_2_b', 'canonical_id': 'lab5_2', 'label': 'Lab 5.2 B', 'path': '/lab5/2/b'},
    {'id': 'lab5_2_c', 'canonical_id': 'lab5_2', 'label': 'Lab 5.2 C', 'path': '/lab5/2/c'},
    {'id': 'lab6_1_a', 'canonical_id': 'lab6', 'label': 'Lab 6.1 A', 'path': '/lab6/1'},
    {'id': 'lab6_1_b', 'canonical_id': 'lab6', 'label': 'Lab 6.1 B', 'path': '/lab6/1/b'},
    {'id': 'lab6_1_c', 'canonical_id': 'lab6', 'label': 'Lab 6.1 C', 'path': '/lab6/1/c'},
    {'id': 'lab7_1_a', 'canonical_id': 'lab7', 'label': 'Lab 7.1 A', 'path': '/lab7/1'},
    {'id': 'lab7_1_b', 'canonical_id': 'lab7', 'label': 'Lab 7.1 B', 'path': '/lab7/1/b'},
    {'id': 'lab7_1_c', 'canonical_id': 'lab7', 'label': 'Lab 7.1 C', 'path': '/lab7/1/c'},
    {'id': 'lab7_2_a', 'canonical_id': 'lab7', 'label': 'Lab 7.2 A', 'path': '/lab7/2'},
    {'id': 'lab7_2_b', 'canonical_id': 'lab7', 'label': 'Lab 7.2 B', 'path': '/lab7/2/b'},
    {'id': 'lab7_2_c', 'canonical_id': 'lab7', 'label': 'Lab 7.2 C', 'path': '/lab7/2/c'},
    {'id': 'lab8_1_a', 'canonical_id': 'lab8', 'label': 'Lab 8.1 A', 'path': '/lab8/1/a'},
    {'id': 'lab8_1_b', 'canonical_id': 'lab8', 'label': 'Lab 8.1 B', 'path': '/lab8/1/b'},
    {'id': 'lab8_1_c', 'canonical_id': 'lab8', 'label': 'Lab 8.1 C', 'path': '/lab8/1/c'},
    {'id': 'lab8_1_d', 'canonical_id': 'lab8', 'label': 'Lab 8.1 D', 'path': '/lab8/1/d'},
    {'id': 'lab8_1_e', 'canonical_id': 'lab8', 'label': 'Lab 8.1 E', 'path': '/lab8/1/e'},
    {'id': 'lab8_2_a', 'canonical_id': 'lab8_2', 'label': 'Lab 8.2', 'path': '/lab8/2'},
    {'id': 'lab9_1_a', 'canonical_id': 'lab9', 'label': 'Lab 9', 'path': '/lab9'},
]

TRACKABLE_LAB_ID_INDEX = {unit['id']: unit for unit in TRACKABLE_LAB_UNITS}
TRACKABLE_LAB_PATH_INDEX = {unit['path']: unit for unit in TRACKABLE_LAB_UNITS}


def get_total_trackable_lab_units():
    return len(TRACKABLE_LAB_UNITS)


def normalize_lab_path(lab_path):
    if not lab_path:
        return None
    normalized = str(lab_path).strip().lower()
    if not normalized.startswith('/'):
        normalized = '/' + normalized
    if len(normalized) > 1:
        normalized = normalized.rstrip('/')
    return normalized


def resolve_lab_context(lab_id=None, exact_lab_id=None, lab_path=None):
    normalized_path = normalize_lab_path(lab_path)
    unit = None

    if exact_lab_id and exact_lab_id in TRACKABLE_LAB_ID_INDEX:
        unit = TRACKABLE_LAB_ID_INDEX[exact_lab_id]
    elif normalized_path:
        if normalized_path in TRACKABLE_LAB_PATH_INDEX:
            unit = TRACKABLE_LAB_PATH_INDEX[normalized_path]
        else:
            for candidate_path in sorted(TRACKABLE_LAB_PATH_INDEX.keys(), key=len, reverse=True):
                if normalized_path.startswith(candidate_path + '/'):
                    unit = TRACKABLE_LAB_PATH_INDEX[candidate_path]
                    break

    if unit:
        return {
            'exact_lab_id': unit['id'],
            'canonical_lab_id': unit['canonical_id'],
            'label': unit['label'],
            'lab_path': unit['path'],
        }

    return {
        'exact_lab_id': exact_lab_id or lab_id,
        'canonical_lab_id': lab_id or exact_lab_id,
        'label': exact_lab_id or lab_id,
        'lab_path': normalized_path,
    }


def build_solved_lab_records(progress):
    solved_labs = []
    for lab_id, entry in sorted(progress.items(), key=lambda item: item[0]):
        context = resolve_lab_context(
            lab_id=entry.get('canonical_lab_id') or lab_id,
            exact_lab_id=entry.get('exact_lab_id') or lab_id,
            lab_path=entry.get('lab_path')
        )
        if entry.get('is_solved'):
            solved_labs.append({
                'lab_id': context['exact_lab_id'],
                'canonical_lab_id': context['canonical_lab_id'],
                'label': context['label'],
                'variation': entry.get('variation') or 'default',
                'lab_path': context['lab_path'],
            })
    return solved_labs


def build_dashboard_metrics(user_rows, solved_feed):
    """Build deduplicated dashboard intelligence for executive views."""
    participant_rows = [u for u in user_rows if u.get('role') not in ['admin', 'analyzer']]
    total_participants = len(participant_rows)
    approved_participants = sum(1 for u in participant_rows if u.get('is_approved'))
    pending_participants = total_participants - approved_participants
    active_solvers = sum(1 for u in participant_rows if (u.get('total_solved') or 0) > 0)

    avg_completion = 0.0
    if total_participants:
        avg_completion = round(
            sum((u.get('avg_progress') or 0) for u in participant_rows) / float(total_participants),
            1
        )

    unique_available_families = len({unit['canonical_id'] for unit in TRACKABLE_LAB_UNITS})
    pair_set = set()
    family_counter = Counter()

    for student in participant_rows:
        email = student.get('email') or ''
        canonical_seen = set()

        for solved in student.get('solved_labs') or []:
            canonical = solved.get('canonical_lab_id') or solved.get('lab_id')
            if not canonical:
                continue
            pair_set.add((email, canonical))
            canonical_seen.add(canonical)

        for canonical in canonical_seen:
            family_counter[canonical] += 1

    unique_solved_families = len(family_counter)
    family_coverage_pct = round((unique_solved_families / float(unique_available_families)) * 100) if unique_available_families else 0

    family_rows = []
    family_peak = max(family_counter.values()) if family_counter else 1
    for family, count in family_counter.most_common(8):
        family_rows.append({
            'label': str(family).replace('_', ' ').upper(),
            'count': count,
            'pct': round((count / float(family_peak)) * 100) if family_peak else 0
        })

    progress_bands = {
        'Not Started (0%)': 0,
        'Starter (1-29%)': 0,
        'Intermediate (30-69%)': 0,
        'Advanced (70-100%)': 0,
    }
    for student in participant_rows:
        progress = float(student.get('avg_progress') or 0)
        if progress <= 0:
            progress_bands['Not Started (0%)'] += 1
        elif progress < 30:
            progress_bands['Starter (1-29%)'] += 1
        elif progress < 70:
            progress_bands['Intermediate (30-69%)'] += 1
        else:
            progress_bands['Advanced (70-100%)'] += 1

    progress_peak = max(progress_bands.values()) if progress_bands else 1
    progress_rows = [
        {
            'label': label,
            'count': count,
            'pct': round((count / float(progress_peak)) * 100) if progress_peak else 0
        }
        for label, count in progress_bands.items()
    ]

    return {
        'total_accounts': len(user_rows),
        'total_participants': total_participants,
        'approved_participants': approved_participants,
        'pending_participants': pending_participants,
        'active_solvers': active_solvers,
        'avg_completion': avg_completion,
        'raw_events': len(solved_feed or []),
        'dedup_events': len(pair_set),
        'unique_solved_families': unique_solved_families,
        'family_coverage_pct': family_coverage_pct,
        'family_rows': family_rows,
        'progress_rows': progress_rows,
    }


# -------------------------
# AUTHENTICATION HELPERS
# -------------------------
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.path))
        
        # Identity Verification via Session Registry
        if session.get('role') != 'admin':
            return render_template('error.html', message="Administrative clearance required."), 403
        return f(*args, **kwargs)
    return decorated_function


def analyzer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.path))

        if session.get('role') not in ['analyzer', 'admin']:
            return render_template('error.html', message="Analyzer clearance required."), 403
        return f(*args, **kwargs)
    return decorated_function


def sync_session_from_firebase_user(firebase_user, email=None):
    """Keep session identity aligned with the latest Firebase profile."""
    if not firebase_user:
        return

    session['user_id'] = firebase_user.get('user_id')
    session['username'] = firebase_user.get('username')
    session['role'] = firebase_user.get('role', 'user')
    session['email'] = email or firebase_user.get('email')
    session['guid'] = firebase_user.get('guid')
    session['profile_picture'] = firebase_user.get('profile_picture')
    session.permanent = True

@app.before_request
def enforce_lab_locks():
    """Global access controller for the laboratory environment"""
    path = request.path.lower()
    
    # Only protect lab routes; everything else keeps its normal behavior.
    if not path.startswith('/lab'):
        return
        
    print(f"[SECURITY] Access attempt to {path} from {request.remote_addr}")
    
    if 'user_id' not in session:
        print(f"[SECURITY] Blocked unauthenticated access to {path}")
        return redirect(url_for('login', next=request.path))
    
    # Authorized staff (Admins/Analyzers) bypass the vetting protocol
    if session.get('role') in ['admin', 'analyzer']:
        return
        
    # Standard subjects must be vetted by the Command Center
    email = session.get('email')
    if not email:
        return redirect(url_for('login', next=request.path))

    access_data = get_or_refresh_access_gate_cache(email)
    is_approved = bool(access_data.get('is_approved'))
    approved_lab_ids = access_data.get('approved_lab_ids', set())
    approved_family_ids = access_data.get('approved_family_ids', set())

    if not is_approved:
        print(f"[SECURITY] Blocked unvetted subject {email} from entering {path}")
        return redirect(url_for('auth_pending'))

    lab_context = resolve_lab_context(lab_path=path)
    exact_lab_id = lab_context.get('exact_lab_id')
    if not exact_lab_id:
        family_match = re.fullmatch(r'/lab(\d+)', path.rstrip('/'))
        if family_match:
            family_prefix = f"lab{family_match.group(1)}_"
            has_family_access = family_prefix in approved_family_ids
            if not has_family_access:
                print(f"[SECURITY] Blocked locked lab landing page for {email}: {path}")
                return redirect(url_for('lab_locked', blocked_path=path, blocked_lab_id='UNMAPPED'))
            return
        return

    if exact_lab_id not in approved_lab_ids:
        print(f"[SECURITY] Blocked locked lab {exact_lab_id} for {email}")
        return redirect(url_for('lab_locked', blocked_path=path, blocked_lab_id=exact_lab_id))

# -------------------------
# DYNAMIC RESEARCH DELIVERABLES (FLAGS)
# -------------------------
def get_or_generate_flag(user_id, lab_id, variation='default', seed_extra=''):
    """Generate a reproducible, unique research deliverable for a subject"""
    # Use user_id and lab_id as a seed for consistent flag generation across sessions
    # without requiring persistent database storage.
    import hashlib
    seed_string = f"{user_id}-{lab_id}-{variation}-{seed_extra}-{app.secret_key}"
    hash_obj = hashlib.sha256(seed_string.encode())
    short_hash = hash_obj.hexdigest()[:12]
    
    prefix = lab_id.split('_')[0]
    return f"FLAG{{{prefix}_{variation}_{short_hash}}}"

def generate_lab_flags(lab_id, identity_key):
    """Generate all variations for a lab based on stable subject identity."""
    return {
        'variation_A': get_or_generate_flag(identity_key, lab_id, 'variation_A'),
        'variation_B': get_or_generate_flag(identity_key, lab_id, 'variation_B'),
        'variation_C': get_or_generate_flag(identity_key, lab_id, 'variation_C'),
        'variation_D': get_or_generate_flag(identity_key, lab_id, 'variation_D'),
        'variation_E': get_or_generate_flag(identity_key, lab_id, 'variation_E'),
        'default': get_or_generate_flag(identity_key, lab_id, 'default')
    }


def get_research_identity_key(allow_header=True):
    identity_key = session.get('guid') or session.get('user_id')
    if not identity_key and allow_header:
        try:
            identity_key = request.headers.get('X-SSRF-Researcher-GUID')
        except Exception:
            identity_key = None
    if not identity_key:
        identity_key = session.get('lab8_subject')
    return identity_key

def get_random_flag(lab_id, variation='default'):
    """Compatibility wrapper for legacy lab routes to use dynamic flags"""
    # Check session first (standard)
    identity_key = get_research_identity_key(allow_header=True)
            
    if not identity_key:
        # High-Fidelity: Standardize on static fallbacks for guest researchers
        # This ensures path traversal findings are universally verifiable.
        if lab_id == 'lab1':
            if variation == 'variation_A': return "FLAG{file_system_traversal_alpha}"
            if variation == 'variation_B': return "FLAG{directory_enumeration_beta}"
            if variation == 'variation_C': return "FLAG{path_manipulation_gamma}"
        return "FLAG{unauthenticated_research_lock}"

    # Generate stable, reproducible research deliverables for this subject.
    issued_flag = get_or_generate_flag(identity_key, lab_id, variation)

    # Cache in session to ensure the submit validator recognizes it.
    lab_flags = session.get('lab_flags', {})
    lab_issued_flags = list(lab_flags.get(lab_id, []))
    if issued_flag not in lab_issued_flags:
        lab_issued_flags.append(issued_flag)
    if len(lab_issued_flags) > 25:
        lab_issued_flags = lab_issued_flags[-25:]
    lab_flags[lab_id] = lab_issued_flags
    session['lab_flags'] = lab_flags
    session.modified = True

    return issued_flag

@app.route('/submit_flag', methods=['POST'])
@login_required
def submit_flag():
    """Verify research deliverable and record in Cloud Firestore"""
    lab_id = request.form.get('lab_id')
    exact_lab_id = request.form.get('exact_lab_id')
    lab_path = request.form.get('lab_path')
    variation = request.form.get('variation', 'default')
    submitted_flag = request.form.get('flag', '').strip()
    email = session.get('email')
    lab_context = resolve_lab_context(lab_id=lab_id, exact_lab_id=exact_lab_id, lab_path=lab_path)
    canonical_lab_id = lab_context.get('canonical_lab_id')
    resolved_exact_lab_id = lab_context.get('exact_lab_id')

    if not canonical_lab_id or not resolved_exact_lab_id or not submitted_flag:
        return jsonify({'success': False, 'error': 'Deliverable content missing.'}), 400

    # Retrieve expected flags from user session (dynamic)
    expected_flags = session.get('lab_flags', {}).get(canonical_lab_id, [])
    if not expected_flags:
        # Regenerate if session timed out or missing.
        identity_key = get_research_identity_key(allow_header=False)
        expected_flags = list(generate_lab_flags(canonical_lab_id, identity_key).values())

        # Backward compatibility for users whose visible flags were generated
        # from the old user_id-only derivation before this fix.
        legacy_identity_key = session.get('user_id')
        if legacy_identity_key and legacy_identity_key != identity_key:
            expected_flags.extend(generate_lab_flags(canonical_lab_id, legacy_identity_key).values())

    # Normalize whitespace and guard against duplicate entries.
    expected_flags = {str(flag).strip() for flag in expected_flags if flag}
    
    # Universal fallback for static flags found via file-system exploits (Lab 1, Lab 6)
    static_fallbacks = {
        'FLAG{file_system_traversal_alpha}',
        'FLAG{directory_enumeration_beta}',
        'FLAG{path_manipulation_gamma}',
        'FLAG{you_found_the_hidden_root_flag}',
        'FLAG{you_found_the_secret}',
        'FLAG{unauthenticated_research_lock}'
    }
    expected_flags.update(static_fallbacks)
    
    print(
        f"[SUBMISSION] Canonical Lab: {canonical_lab_id}, Exact Lab: {resolved_exact_lab_id}, "
        f"Subject: {email}, Submitted: {submitted_flag}"
    )
    print(f"[SUBMISSION] Expected set includes {len(expected_flags)} possible signals.")

    if submitted_flag in expected_flags:
        # Record success in Firebase
        firebase_store.submit_lab_progress(
            email,
            resolved_exact_lab_id,
            variation,
            submitted_flag,
            True,
            "Deliverable accepted.",
            canonical_lab_id=canonical_lab_id,
            exact_lab_id=resolved_exact_lab_id,
            lab_path=lab_context.get('lab_path')
        )
        invalidate_admin_view_cache()
        return jsonify({'success': True, 'message': 'Research deliverable verified and serialized.'})
    else:
        # Record attempt in Firebase
        # Note: 'Invalid deliverable signal.' is the error seen by user.
        firebase_store.submit_lab_progress(
            email,
            resolved_exact_lab_id,
            variation,
            submitted_flag,
            False,
            "Incorrect deliverable.",
            canonical_lab_id=canonical_lab_id,
            exact_lab_id=resolved_exact_lab_id,
            lab_path=lab_context.get('lab_path')
        )
        invalidate_admin_view_cache()
        return jsonify({'success': False, 'error': f'Invalid deliverable signal for {resolved_exact_lab_id}.'})



def build_admin_students_payload():
    """Build admin view payload from Firestore sources."""
    # Fetch all users from Firebase so roles can be changed both ways.
    all_users = firebase_store.get_all_users()
    students = all_users
    all_progress_by_email = firebase_store.get_all_users_progress()
    all_enrollments_by_email = firebase_store.get_all_lab_enrollments()
    
    # Calculate aggregate stats from Firebase data
    for student in students:
        student_email = student.get('email')
        progress = all_progress_by_email.get(student_email)
        if progress is None:
            progress = firebase_store.get_user_progress(student_email)
        solved_labs = build_solved_lab_records(progress)
        lab_enrollments = all_enrollments_by_email.get(student_email)
        if lab_enrollments is None:
            lab_enrollments = firebase_store.get_user_lab_enrollments(student_email)
        allowed_lab_ids = [
            enrollment.get('lab_id')
            for enrollment in lab_enrollments
            if enrollment.get('approval_status') == 'approved' and enrollment.get('lab_id')
        ]

        student['labs_enrolled'] = get_total_trackable_lab_units()
        student['labs_approved'] = get_total_trackable_lab_units()
        student['solved_labs'] = solved_labs
        student['total_solved'] = len(solved_labs)
        student['lab_access'] = allowed_lab_ids
        student['lab_access_count'] = len(allowed_lab_ids)
        student['avg_progress'] = (
            student['total_solved'] / float(get_total_trackable_lab_units()) * 100
            if get_total_trackable_lab_units() else 0
        )

    # Fetch pending users for authorization
    pending_users = [u for u in students if not u.get('is_approved') and u.get('role') not in ['admin', 'analyzer']]
    
    # Fetch solved labs feed from Firebase
    solved_data = firebase_store.get_solved_labs_feed()
    dashboard = build_dashboard_metrics(students, solved_data)

    return {
        'students': students,
        'solved_data': solved_data,
        'pending_users': pending_users,
        'dashboard': dashboard,
        'trackable_labs': TRACKABLE_LAB_UNITS,
    }


@app.route('/admin/students')
@admin_required
def admin_students():
    """View and manage research subjects and their lab telemetry via Firestore"""
    payload = get_admin_view_cache('admin_students')
    if payload is None:
        payload = build_admin_students_payload()
        set_admin_view_cache('admin_students', payload)

    return render_template('admin/students.html', 
                          students=payload['students'], 
                          solved_data=payload['solved_data'],
                          pending_users=payload['pending_users'],
                          dashboard=payload['dashboard'],
                          trackable_labs=payload['trackable_labs'])


@app.route('/analyzer/students')
@analyzer_required
def analyzer_students():
    """Analyzer workspace focused on student performance telemetry."""
    all_users = firebase_store.get_all_users()
    students = [u for u in all_users if u.get('role') not in ['admin', 'analyzer']]
    all_progress_by_email = firebase_store.get_all_users_progress()

    for student in students:
        student_email = student.get('email')
        progress = all_progress_by_email.get(student_email)
        if progress is None:
            progress = firebase_store.get_user_progress(student_email)
        solved_labs = build_solved_lab_records(progress)

        student['labs_enrolled'] = get_total_trackable_lab_units()
        student['labs_approved'] = get_total_trackable_lab_units()
        student['solved_labs'] = solved_labs
        student['total_solved'] = len(solved_labs)
        student['avg_progress'] = (
            student['total_solved'] / float(get_total_trackable_lab_units()) * 100
            if get_total_trackable_lab_units() else 0
        )

    solved_data = firebase_store.get_solved_labs_feed()
    dashboard = build_dashboard_metrics(students, solved_data)
    return render_template('analyzer/students.html', students=students, solved_data=solved_data, dashboard=dashboard)


@app.route('/analyzer/student/<path:email>')
@analyzer_required
def analyzer_student_report(email):
    """Detailed read-only report page for one student record."""
    student = firebase_store.get_user_by_email(email)
    if not student:
        return render_template('error.html', message="Student record not found."), 404

    if student.get('role') in ['admin', 'analyzer']:
        return render_template('error.html', message="Full report is available only for student records."), 403

    progress = firebase_store.get_user_progress(email)
    solved_labs = build_solved_lab_records(progress)
    total_labs = get_total_trackable_lab_units()
    solved_count = len(solved_labs)
    pending_count = max(total_labs - solved_count, 0)
    completion_pct = round((solved_count / total_labs) * 100) if total_labs else 0

    canonical_counter = Counter()
    variation_counter = Counter()
    for lab in solved_labs:
        canonical_counter[lab.get('canonical_lab_id') or 'unknown'] += 1
        variation_counter[lab.get('variation') or 'default'] += 1

    canonical_rows = []
    canonical_peak = max(canonical_counter.values()) if canonical_counter else 1
    for key, count in canonical_counter.most_common(12):
        canonical_rows.append({
            'label': str(key).replace('_', ' ').upper(),
            'count': count,
            'pct': round((count / canonical_peak) * 100) if canonical_peak else 0
        })

    variation_rows = []
    variation_peak = max(variation_counter.values()) if variation_counter else 1
    for key, count in variation_counter.most_common(6):
        variation_rows.append({
            'label': str(key),
            'count': count,
            'pct': round((count / variation_peak) * 100) if variation_peak else 0
        })

    report = {
        'student': student,
        'total_labs': total_labs,
        'solved_count': solved_count,
        'pending_count': pending_count,
        'completion_pct': completion_pct,
        'canonical_rows': canonical_rows,
        'variation_rows': variation_rows,
        'solved_labs': solved_labs,
    }

    return render_template('analyzer/student_report.html', report=report)


@app.route('/analyzer/student/<path:email>/export.csv')
@analyzer_required
def analyzer_student_report_csv(email):
    """Export one student's full analyzer report as CSV."""
    student = firebase_store.get_user_by_email(email)
    if not student:
        return render_template('error.html', message="Student record not found."), 404

    if student.get('role') in ['admin', 'analyzer']:
        return render_template('error.html', message="CSV export is available only for student records."), 403

    progress = firebase_store.get_user_progress(email)
    solved_labs = build_solved_lab_records(progress)
    total_labs = get_total_trackable_lab_units()
    solved_count = len(solved_labs)
    pending_count = max(total_labs - solved_count, 0)
    completion_pct = round((solved_count / total_labs) * 100) if total_labs else 0

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['section', 'field', 'value'])
    writer.writerow(['student', 'email', student.get('email', '')])
    writer.writerow(['student', 'username', student.get('username', '')])
    writer.writerow(['student', 'enrollment_id', student.get('enrollment_id', '')])
    writer.writerow(['summary', 'total_labs', total_labs])
    writer.writerow(['summary', 'solved_count', solved_count])
    writer.writerow(['summary', 'pending_count', pending_count])
    writer.writerow(['summary', 'completion_pct', completion_pct])

    writer.writerow([])
    writer.writerow(['solved_labs', 'label', 'canonical_lab_id', 'variation', 'lab_path'])
    for lab in solved_labs:
        writer.writerow([
            'solved_labs',
            lab.get('label') or lab.get('lab_id') or '',
            lab.get('canonical_lab_id') or '',
            lab.get('variation') or '',
            lab.get('lab_path') or ''
        ])

    csv_data = output.getvalue()
    output.close()

    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', student.get('username') or 'student')
    filename = f"student_report_{safe_name}.csv"

    return Response(
        csv_data,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename={filename}'
        }
    )

@app.route('/admin/approve', methods=['POST'])
@admin_required
def approve_enrollment():
    """Approve or reject a lab enrollment"""
    user_email = request.form.get('user_email')
    lab_id = request.form.get('lab_id')
    new_status = request.form.get('status') # 'approved' or 'rejected'
    
    if not user_email or not lab_id or new_status not in ['approved', 'rejected', 'pending']:
        return jsonify({'error': 'Invalid parameters'}), 400
        
    firebase_store.update_lab_enrollment_status(user_email, lab_id, new_status)
    invalidate_admin_view_cache()
    
    return jsonify({'success': True, 'message': f'Enrollment {new_status} successfully.'})

@app.route('/lab/enroll/<lab_id>', methods=['POST'])
@login_required
def request_lab_enrollment(lab_id):
    """Student requests access to a specific lab"""
    user_email = session['email']
    
    # Check if already enrolled
    existing = firebase_store.get_lab_enrollment(user_email, lab_id)
    if existing:
        return jsonify({'success': False, 'error': 'Already enrolled or pending.'})
    
    try:
        firebase_store.create_lab_enrollment(user_email, lab_id, 'pending')
        send_admin_authorization_email(
            request_type='lab',
            requester_email=user_email,
            requester_name=session.get('username'),
            lab_id=lab_id,
            requester_role=session.get('role') or 'user'
        )
        return jsonify({'success': True, 'message': 'Access request sent for authorization.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def check_lab_access(lab_id):
    """Helper to verify if a user has approved access to a lab"""
    if session.get('role') == 'admin': return True
    user_email = session.get('email')
    enrollment = firebase_store.get_lab_enrollment(user_email, lab_id)
    
    if not enrollment: return 'unattached'
    return enrollment.get('approval_status')

@app.route('/admin/approve_user', methods=['POST'])
@admin_required
def approve_user():
    """Approve or reject a user's account via Cloud Firestore"""
    email = request.form.get('email') # Use email as ID for Firebase
    user_id = request.form.get('user_id') # Fallback if email not provided
    is_approved = request.form.get('is_approved') == '1'
    requested_role = (request.form.get('role') or '').strip().lower()
    assign_lab_access = request.form.get('assign_lab_access') == '1'
    selected_lab_ids = [
        lab_id for lab_id in request.form.getlist('lab_ids')
        if lab_id in TRACKABLE_LAB_ID_INDEX
    ]

    if requested_role == 'student':
        requested_role = 'user'
    if requested_role and requested_role not in ['user', 'admin', 'analyzer']:
        return jsonify({'error': 'Invalid role. Allowed values are user/student/admin/analyzer.'}), 400

    if not email and not user_id:
        return jsonify({'error': 'Subject identifier required'}), 400

    # If we only have user_id, find email from list or skip
    if not email:
        all_u = firebase_store.get_all_users()
        email = next((u['email'] for u in all_u if str(u.get('user_id')) == str(user_id)), None)

    if not email:
        return jsonify({'error': 'Subject not found in registry'}), 404

    existing_user = firebase_store.get_user_by_email(email) or {}
    was_approved = bool(existing_user.get('is_approved'))

    firebase_store.update_user_access(email, is_approved, requested_role or None)

    if assign_lab_access or not is_approved:
        if is_approved:
            firebase_store.replace_user_lab_access(email, selected_lab_ids)
        else:
            firebase_store.replace_user_lab_access(email, [])

    invalidate_admin_view_cache()

    should_email_user = is_approved and (not was_approved or (assign_lab_access and bool(selected_lab_ids)))
    if should_email_user:
        send_user_access_granted_email(
            user_email=email,
            role=requested_role or existing_user.get('role') or 'user',
            approved_lab_ids=selected_lab_ids if assign_lab_access else None
        )
    
    status_message = "authorized" if is_approved else "denied"
    role_message = f" Role set to {requested_role}." if requested_role else ""
    return jsonify({'success': True, 'message': f'Research subject {status_message}.{role_message}'})

# -------------------------
# INITIALIZATION (DECOMMISSIONED)
# -------------------------
# Legacy SQLite initialization logic has been removed.
# The laboratory now operates as a pure serverless entity via Cloud Firestore.

# -------------------------
# INITIALIZATION (REMOVED SQLITE)
# -------------------------
# The laboratory now relies exclusively on Cloud Firestore for all persistence.
# SQLite logic has been decommissioned to ensure global synchronization.


def build_chatbot_response(user_message, current_path=None):
    """Return a concise, support-focused response for the site chatbot."""
    message = (user_message or '').strip().lower()
    path = (current_path or '').strip().lower()

    def response(text, suggestions):
        return {
            'reply': text,
            'suggestions': suggestions,
            'context': path or '/',
        }

    if not message:
        return response(
            'Ask me about logging in, creating an account, the help center, system status, or submitting a deliverable.',
            ['How do I join?', 'How do I sign in?', 'Where do I submit a deliverable?']
        )

    blocked_terms = {
        'bypass', 'exploit', 'payload', 'sql injection', 'sqli', 'xss', 'rce', 'csrf',
        'steal', 'hack', 'reverse shell', 'privilege escalation'
    }
    if any(term in message for term in blocked_terms):
        return response(
            'I can help with navigation, account setup, support channels, system status, and deliverable submission. For lab-safe guidance, open the Help Center.',
            ['Open Help Center', 'How do I submit a deliverable?', 'How do I sign in?']
        )

    if any(term in message for term in {'register', 'join', 'create account', 'enroll', 'identity'}):
        return response(
            'Use Join in the top bar, enter your preferred username and enrollment ID, then complete Google sign-in to finalize your identity.',
            ['What if my account is pending?', 'How do I sign in?', 'Open Help Center']
        )

    if any(term in message for term in {'login', 'log in', 'sign in', 'signin', 'sign-in'}):
        return response(
            'Use Log In from the header. If the platform says your identity is not found, join first or check with support.',
            ['How do I join?', 'Open Help Center', 'Check system status']
        )

    if any(term in message for term in {'deliverable', 'flag', 'submit', 'intake'}):
        return response(
            'On lab pages, open the floating Research Deliverable Intake widget in the bottom-right corner, choose the variation if needed, and submit your FLAG{...} value.',
            ['Where is the widget?', 'What if submission fails?', 'Open Help Center']
        )

    if any(term in message for term in {'status', 'health', 'outage', 'down', 'service'}):
        return response(
            'Use the System Status page in the footer to check platform health and service telemetry before troubleshooting.',
            ['Open System Status', 'Open Help Center', 'Where do I submit a deliverable?']
        )

    if any(term in message for term in {'help', 'faq', 'support', 'contact'}):
        return response(
            'The Help Center covers onboarding, deliverable submission, and support contacts. It is the fastest place to start.',
            ['Open Help Center', 'How do I join?', 'How do I submit a deliverable?']
        )

    if any(term in path for term in {'/register', '/login'}) or any(term in message for term in {'account', 'profile'}):
        return response(
            'For account issues, use Join for setup, Log In for access, and Profile after authentication. Pending enrollments must be reviewed by an administrator.',
            ['How do I join?', 'How do I sign in?', 'Why is my account pending?']
        )

    if '/lab' in path:
        return response(
            'On lab pages, the floating widget handles deliverable submission. If you need general guidance, use the Help Center from the top-level navigation or footer.',
            ['How do I submit a deliverable?', 'Open Help Center', 'Check system status']
        )

    return response(
        'I can help with account setup, sign-in, deliverable submission, and support links. Try asking about one of those topics.',
        ['How do I join?', 'How do I sign in?', 'Where do I submit a deliverable?']
    )

# -------------------------
# MAIN ROUTES
# -------------------------
@app.route('/')
def home():
    clear_lab8_session_state()
    return render_template('index.html')

@app.route('/privacy')
def privacy_policy():
    return render_template('privacy.html')

@app.route('/terms')
def terms_of_service():
    return render_template('terms.html')

@app.route('/cookies')
def cookie_policy():
    return render_template('cookies.html')

@app.route('/status')
def system_status():
    return render_template('status.html')


@app.route('/api/chatbot', methods=['POST'])
def chatbot_reply():
    payload = request.get_json(silent=True) or request.form or {}
    message = payload.get('message', '')
    current_path = payload.get('path', request.path)
    return jsonify(build_chatbot_response(message, current_path))

@app.route('/labs')
def labs():
    clear_lab8_session_state()
    return render_template('labs.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.static_folder, 'favicon'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

# -------------------------
# REAL GOOGLE OAUTH ROUTES
# -------------------------
@app.route('/auth/google')
def google_login():
    next_url = request.args.get('next', '')
    auth_source = (request.args.get('source') or 'login').strip().lower()
    if auth_source not in {'login', 'register'}:
        auth_source = 'login'

    session['oauth_source'] = auth_source
    if next_url and (next_url.startswith('/') and not next_url.startswith('//')):
        session['oauth_next'] = next_url

    redirect_uri = get_google_redirect_uri()
    print(f"[OAUTH] Starting Google OAuth. Mode: {auth_source}, Redirect: {redirect_uri}")
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def google_callback():
    redirect_uri = get_google_redirect_uri()
    print(f"[OAUTH] Received Google Callback. Redirect URI used in auth_redirect: {redirect_uri}")
    try:
        # Revert to standard call; OAUTHLIB_INSECURE_TRANSPORT=1 should fix the original issue
        token = google.authorize_access_token()
    except Exception as e:
        print(f"[OAUTH] Token exchange failed: {e}")
        import traceback
        traceback.print_exc()
        return redirect(url_for('login', error=f"OAuth state mismatch: {str(e)}. Ensure you use the same address (localhost or 127.0.0.1) consistently."))
    
    try:
        userinfo = token.get('userinfo')
        if not userinfo:
            # If userinfo not in token, fetch it explicitly
            userinfo = google.get('userinfo').json()
    except Exception as e:
        print(f"Userinfo retrieval error: {e}")
        import traceback
        traceback.print_exc()
        return redirect(url_for('login', error="Failed to retrieve user information"))
    
    auth_source = session.pop('oauth_source', 'login')
    
    if not userinfo:
        return redirect(url_for('login', error="Google authentication failed: no user info received"))

    # Researcher branded logic remains but uses real data
    email = userinfo.get('email')
    full_name = userinfo.get('name')
    google_picture = userinfo.get('picture')
    if not email:
        return redirect(url_for('login', error="Google authentication failed: email not available"))

    # ==========================================
    # FIREBASE-DEPENDENT LOGIN (SOURCE OF TRUTH)
    # ==========================================
    
    # 1. Always check Firebase first for the latest profile/role
    print(f"[AUTH] Pulling source-of-truth profile from Firebase for {email}")
    firebase_user = firebase_store.get_user_by_email(email)
    
    # 2. Handle Login Flow
    if auth_source == 'login':
        if not firebase_user:
            # User doesn't exist in the cloud yet
            print(f"[AUTH] Login failed: {email} does not exist in Firebase.")
            return redirect(url_for('register', error='No account found. Please Join the platform first.'))
            
    # 3. Handle Registration (Join) Flow
    elif auth_source == 'register':
        if firebase_user:
            return redirect(url_for('login', error='Identity already initialized in Firebase. Please sign in.'))
            
        # Get pending data from session
        pending = session.pop('pending_join', None)
        if not pending:
            return redirect(url_for('register', error='Session expired. Please start identity initialization again.'))
            
        # Create in Firebase
        selected_username = pending['username']
        enrollment_id = pending['enrollment_id']
        
        # Check collision before final creation
        # This check needs to be done against Firebase now
        if firebase_store.get_user_by_username(selected_username):
             return redirect(url_for('register', error='Username already claimed.'))
        if firebase_store.get_user_by_enrollment_id(enrollment_id):
            return redirect(url_for('register', error='Enrollment ID already exists.'))

        # Generate a unique user_id (Firebase auto-generates doc ID, but we might need an internal int ID)
        # For simplicity, let's use a random int for user_id for now, or Firebase doc ID can be used.
        # Assuming user_id is an integer for compatibility with existing session logic.
        new_user_id = random.randint(100000, 999999) # Placeholder for a unique ID
        firebase_store.upsert_user(
            user_id=new_user_id,
            username=selected_username,
            role='user',
            email=email,
            full_name=full_name,
            guid=uuid.uuid4().hex,
            enrollment_id=enrollment_id,
            is_approved=False, # New users are not approved by default
            profile_picture=google_picture
        )
        firebase_user = firebase_store.get_user_by_email(email) # Re-fetch the newly created user
        print(f"[AUTH] New identity {email} committed to Firebase.")
        send_admin_authorization_email(
            request_type='account',
            requester_email=email,
            requester_name=selected_username,
            requester_role='user'
        )

    # 4. Global Identifier Management
    firebase_user = firebase_store.get_user_by_email(email)
    
    if not firebase_user:
        # Initial Acquisition
        selected_username = email.split('@')[0]
        enrollment_id = f"SUB-{random.randint(1000, 9999)}"
        firebase_store.upsert_user(
            user_id=random.randint(10000, 99999),
            username=selected_username,
            role='user',
            email=email,
            full_name=full_name,
            guid=uuid.uuid4().hex,
            enrollment_id=enrollment_id,
            is_approved=False,
            profile_picture=google_picture
        )
        firebase_user = firebase_store.get_user_by_email(email)
        send_admin_authorization_email(
            request_type='account',
            requester_email=email,
            requester_name=selected_username,
            requester_role='user'
        )

    # 5. Session Finalization
    if firebase_user:
        if google_picture and firebase_user.get('profile_picture') != google_picture:
            firebase_store.upsert_user(
                user_id=firebase_user.get('user_id'),
                username=firebase_user.get('username'),
                role=firebase_user.get('role'),
                email=email,
                full_name=firebase_user.get('full_name'),
                guid=firebase_user.get('guid'),
                enrollment_id=firebase_user.get('enrollment_id'),
                is_approved=firebase_user.get('is_approved', False),
                profile_picture=google_picture
            )
            firebase_user = firebase_store.get_user_by_email(email)

        sync_session_from_firebase_user(firebase_user, email)

        # Warm access-gate cache after login to reduce first protected-route latency.
        get_or_refresh_access_gate_cache(email, force_refresh=True, preloaded_user=firebase_user)

        # Check if user is authorized by Command Center
        print(f"[AUTH] User profile retrieved. Approval status: {firebase_user.get('is_approved')}")
        if not firebase_user.get('is_approved') and firebase_user.get('role') not in ['admin', 'analyzer']:
            return redirect(url_for('auth_pending'))
        
        # Redirection Logic
        next_url = session.pop('oauth_next', '')
        if next_url and next_url.startswith('/') and not next_url.startswith('//'):
            return redirect(next_url)
        
        if firebase_user.get('role') == 'admin':
            return redirect(url_for('admin_students'))
        if firebase_user.get('role') == 'analyzer':
            return redirect(url_for('analyzer_students'))
        return redirect(url_for('home'))
        
    print(f"[AUTH] FINAL FAILURE: No firebase user found after all attempts for {email}")
    return redirect(url_for('login', error="Authentication flow failed. Please check server logs."))

@app.route('/login', methods=['GET'])
def login():
    if session.get('user_id'):
        if session.get('role') == 'admin':
            return redirect(url_for('admin_students'))
        if session.get('role') == 'analyzer':
            return redirect(url_for('analyzer_students'))
        return redirect(url_for('home'))

    error = request.args.get('error')
    next_url = request.args.get('next', '')

    # Only allow local redirects to avoid open redirect abuse.
    if next_url and (next_url.startswith('/') and not next_url.startswith('//')):
        session['oauth_next'] = next_url
    else:
        next_url = ''

    return render_template('login.html', error=error, next_url=next_url)


@app.route('/auth/pending')
@login_required
def auth_pending():
    """Waiting screen that re-checks account approval on each refresh."""
    email = session.get('email')
    if not email:
        session.clear()
        return redirect(url_for('login', error='Session expired. Please sign in again.'))

    firebase_user = firebase_store.get_user_by_email(email)
    if not firebase_user:
        session.clear()
        return redirect(url_for('login', error='Identity not found. Please sign in again.'))

    sync_session_from_firebase_user(firebase_user, email)

    if firebase_user.get('is_approved') or firebase_user.get('role') in ['admin', 'analyzer']:
        next_url = session.pop('oauth_next', '')
        if next_url and next_url.startswith('/') and not next_url.startswith('//'):
            return redirect(next_url)

        if firebase_user.get('role') == 'admin':
            return redirect(url_for('admin_students'))
        if firebase_user.get('role') == 'analyzer':
            return redirect(url_for('analyzer_students'))
        return redirect(url_for('home'))

    return render_template('auth_pending.html', user=firebase_user)


@app.route('/lab/locked')
@login_required
def lab_locked():
    """Crime-scene style lock screen for labs blocked by per-user allowlist."""
    blocked_path = request.args.get('blocked_path', '').strip()
    blocked_lab_id = request.args.get('blocked_lab_id', '').strip()

    return render_template(
        'lab_locked.html',
        blocked_path=blocked_path,
        blocked_lab_id=blocked_lab_id
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/profile')
@login_required
def profile():
    """User profile page showing identity details and lab progress"""
    email = session.get('email')
    user = firebase_store.get_user_by_email(email)
    
    if not user:
        return redirect(url_for('login'))
        
    # Get solved labs for the profile
    progress = firebase_store.get_user_progress(email)
    solved_labs = build_solved_lab_records(progress)
    
    # Calculate real-time stats from registry
    total_labs = get_total_trackable_lab_units()
    solved_count = len(solved_labs)
    mastery = round((solved_count / total_labs * 100)) if total_labs > 0 else 0
    xp = solved_count * 250
    level = (solved_count // 3) + 1
    profile_picture = user.get('profile_picture') or session.get('profile_picture')
    display_name = user.get('full_name') or user.get('username') or email.split('@')[0]
    
    stats = {
        'total_labs': total_labs,
        'solved_count': solved_count,
        'mastery': mastery,
        'xp': xp,
        'level': level
    }
    
    return render_template('profile.html', user=user, solved_labs=solved_labs, stats=stats, profile_picture=profile_picture, display_name=display_name)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('user_id'):
        return redirect(url_for('home'))

    error = request.args.get('error')
    next_url = request.args.get('next', '')

    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        enrollment_id = (request.form.get('enrollment_id') or '').strip().upper()
        next_url = request.form.get('next', '')

        if not re.match(r'^[A-Za-z0-9_.-]{3,30}$', username):
            error = 'Username must be 3-30 characters and use letters, numbers, dot, underscore, or hyphen.'
            return render_template('register.html', error=error, next_url=next_url, username=username, enrollment_id=enrollment_id)

        if not re.match(r'^[A-Z0-9-]{4,30}$', enrollment_id):
            error = 'Enrollment ID must be 4-30 characters and use uppercase letters, numbers, or hyphen.'
            return render_template('register.html', error=error, next_url=next_url, username=username, enrollment_id=enrollment_id)

        # Registry Collision Check via Firebase
        all_users = firebase_store.get_all_users()
        if any(u.get('username','').lower() == username.lower() for u in all_users):
            error = 'Username already claimed in global registry.'
            return render_template('register.html', error=error, next_url=next_url, username=username, enrollment_id=enrollment_id)

        if any(u.get('enrollment_id','') == enrollment_id for u in all_users):
            error = 'Enrollment ID already synchronized.'
            return render_template('register.html', error=error, next_url=next_url, username=username, enrollment_id=enrollment_id)

        session['pending_join'] = {'username': username, 'enrollment_id': enrollment_id}
        if next_url and (next_url.startswith('/') and not next_url.startswith('//')):
            session['oauth_next'] = next_url
        return redirect(url_for('google_login', next=next_url, source='register'))

    if next_url and (next_url.startswith('/') and not next_url.startswith('//')):
        session['oauth_next'] = next_url
    else:
        next_url = ''

    return render_template('register.html', error=error, next_url=next_url)


@app.route('/products')
def product_list():
    # Research Equipment Inventory (Static High-Fidelity)
    products = [
        {'id': 1, 'name': 'Signal Interceptor Pro', 'price': 299.99, 'description': 'Advanced packet capture device.', 'image': 'prod_1.png'},
        {'id': 2, 'name': 'Biometric Bypass Kit', 'price': 450.00, 'description': 'Simulates authorized access signals.', 'image': 'prod_2.png'},
        {'id': 3, 'name': 'Quantum Cryptography Dongle', 'price': 120.00, 'description': 'Hardware-level encryption bypass.', 'image': 'prod_3.png'}
    ]
    return render_template('product_list.html', products=products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    # Retrieve from Inventory
    products = [
        {'id': 1, 'name': 'Signal Interceptor Pro', 'price': 299.99, 'description': 'Advanced packet capture device.', 'image': 'prod_1.png'},
        {'id': 2, 'name': 'Biometric Bypass Kit', 'price': 450.00, 'description': 'Simulates authorized access signals.', 'image': 'prod_2.png'},
        {'id': 3, 'name': 'Quantum Cryptography Dongle', 'price': 120.00, 'description': 'Hardware-level encryption bypass.', 'image': 'prod_3.png'}
    ]
    product = next((p for p in products if p['id'] == product_id), None)
    if product:
        return render_template('product_detail.html', product=product)
    else:
        return "Equipment not found in registry", 404


@app.route('/help')

@app.route('/help')
def help():
    # Help and FAQ page
    return render_template('help.html')


# -------------------------
# STUDENT DASHBOARD - Progress Tracking and Lab Management
# -------------------------
@app.route('/dashboard')
def student_dashboard():
    """Main student dashboard showing labs, progress, and assignments via Firestore"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    email = session.get('email')
    user = firebase_store.get_user_by_email(email)
    
    if not user:
        return redirect(url_for('login'))
        
    # Fetch enrolled lab progress from Cloud Firestore
    progress = firebase_store.get_user_progress(email)
    solved_labs = build_solved_lab_records(progress)
    
    # Format for template compatibility
    enrollments = [
        {
            'lab_id': str(lab_id),
            'completion_percentage': 100 if bool(data.get('is_solved')) else 50,
            'status': 'completed' if bool(data.get('is_solved')) else 'in_progress',
            'last_accessed': data.get('timestamp')
        }
        for lab_id, data in progress.items()
    ]
    solved_count = len(solved_labs)
    
    total_lab_units = get_total_trackable_lab_units()
    overall_progress = (float(solved_count) / float(total_lab_units)) * 100.0 if total_lab_units else 0.0
        
    # Mock assignments for UI completeness
    assignments = [
        {'id': 1, 'title': 'Initial Vulnerability Discovery', 'due_date': '2026-04-01', 'submitted': False},
        {'id': 2, 'title': 'Advanced Payload Construction', 'due_date': '2026-04-15', 'submitted': False}
    ]
    
    grades = []
    
    return render_template('student_dashboard.html', 
                         user=user,
                         enrollments=enrollments,
                         assignments=assignments,
                         overall_progress=int(overall_progress),
                         grades=grades,
                         total_lab_units=total_lab_units)


@app.route('/dashboard/enroll', methods=['POST'])
@login_required
def dashboard_enroll_lab():
    """Prevent self-enrollment from bypassing the admin lab allowlist."""
    email = session.get('email')
    lab_id = request.form.get('lab_id')
    
    if not lab_id:
        return jsonify({'error': 'Lab identifier required'}), 400
    
    try:
        existing = firebase_store.get_lab_enrollment(email, lab_id)
        if existing and existing.get('approval_status') == 'approved':
            return jsonify({'success': True, 'message': 'Subject already has approved access for this lab.'})

        return jsonify({'error': 'Lab access is managed by the admin allowlist.'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/dashboard/progress/<lab_id>', methods=['GET', 'POST'])
@login_required
def lab_progress(lab_id):
    """View and update lab progress via Firestore"""
    email = session.get('email')
    
    # Check enrollment in Firebase
    enrollment = firebase_store.get_lab_enrollment(email, lab_id)
    if not enrollment:
        return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        section_id = request.form.get('section_id')
        is_solved = request.form.get('task_completed') == 'true'
        flag = request.form.get('flag_value', '')
        
        firebase_store.submit_lab_progress(email, lab_id, section_id, flag, is_solved, "Progress update.")
        return jsonify({'success': True, 'message': 'Progress serialized to Cloud.'})
    
    # GET request - fetch progress from Firebase
    progress = firebase_store.get_user_progress(email)
    lab_data = progress.get(lab_id, {})
    
    return render_template('lab_progress.html',
                         lab_id=lab_id,
                         enrollment=enrollment,
                         progress_entries=[lab_data] if lab_data else [])


@app.route('/dashboard/assignments')
@login_required
def assignments_page():
    """View all assignments (Static Registry)"""
    assignments = [
        {'id': 1, 'title': 'Lab 1: Path Traversal Reconnaissance', 'due_date': '2026-04-01', 'last_submission': None},
        {'id': 2, 'title': 'Lab 2: Access Control Elevation', 'due_date': '2026-04-15', 'last_submission': None}
    ]
    return render_template('assignments.html', assignments=assignments)


@app.route('/dashboard/assignment/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
def assignment_detail(assignment_id):
    """View and submit assignment (Mock System)"""
    return render_template('assignment_detail.html',
                         assignment={'id': assignment_id, 'title': 'Research Assignment'},
                         submissions=[])


@app.route('/dashboard/grades')
@login_required
def grades_page():
    """View all grades and feedback (Firebase Profile Data)"""
    email = session.get('email')
    progress = firebase_store.get_user_progress(email)
    
    grades = []
    for lab_id, data in progress.items():
        if data.get('is_solved'):
            grades.append({
                'lab_id': lab_id,
                'score': 100,
                'feedback': 'Excellent research deliverable verified.',
                'graded_date': data.get('timestamp')
            })
            
    return render_template('grades.html',
                         grades=grades,
                         avg_score=100 if grades else 0,
                         total_labs=len(grades))


# -------------------------
# LAB 1: Path Traversal (Multiple Variations)
# -------------------------
@app.route('/lab1')
def lab1():
    return render_template('lab1/index.html')

# Helper function to create files for all lab1 variations
def create_lab1_files(subdir, files):
    files_dir = os.path.join('data', subdir)
    if not os.path.exists(files_dir):
        os.makedirs(files_dir)
    
    for f in files:
        f_path = os.path.join(files_dir, f)
        if not os.path.exists(f_path):
            with open(f_path, 'w') as file:
                file.write(f"This is content of {f}")

# LAB 1.1: DocuVault (Document Management)
@app.route('/lab1/1')
def lab1_1():
    files = [
        'Invoice_2024_001.pdf', 
        'Invoice_2024_002.pdf', 
        'Project_Alpha_Specs.docx', 
        'Q1_Financial_Report.xlsx', 
        'Meeting_Minutes_Jan.txt',
        'Employee_Handbook_v2.pdf',
        'Architecture_Diagram_Final.png',
        'Client_Contract_AcmeCorp.pdf',
        'Budget_Allocation_2024.xlsx',
        'Security_Policy_Draft.docx',
        'Server_Logs_Backup.txt',
        'Marketing_Assets.zip',
        'Team_Photo_Retreat.jpg',
        'Vendor_List.csv',
        'readme.txt'
    ]
    create_lab1_files('docuvault/invoices', files)
    return render_template('lab1/sub1.html', files=files)

@app.route('/lab1/1/download')
def lab1_1_download():
    filename = request.args.get('file')
    if not filename:
        return "No file specified", 400
    
    # PHYSICAL SYSTEM FILE SIMULATION (Using etc/passwd)
    if filename and ('etc/passwd' in filename.replace('\\', '/') or 'passwd' in filename.lower()):
        try:
            passwd_path = os.path.join(BASE_PATH, 'etc', 'passwd')
            with open(passwd_path, 'r') as f:
                lines = f.readlines()
            
            # Inject only the RELEVANT flag for this sub-lab into the template (Variation A)
            if len(lines) >= 2:
                lines[1] = get_random_flag('lab1', 'variation_A') + "\n"
            if len(lines) >= 4:
                lines[2] = "# [ACCESS RESTRICTED]: Proceed to Lab 1.2 for current deliverable.\n"
                lines[3] = "# [ACCESS RESTRICTED]: Proceed to Lab 1.3 for current deliverable.\n"

                
            return Response("".join(lines), mimetype='text/plain')
        except Exception as e:
            return f"Error accessing system file template: {e}", 500
    
    try:
        intended_dir = os.path.join(BASE_PATH, 'data', 'docuvault', 'invoices')
        file_path = os.path.normpath(os.path.join(intended_dir, filename))
        
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=False, mimetype='text/plain')
        else:
            return f"File not found: {file_path}", 404
    except Exception as e:
        return str(e), 500

# LAB 1.2: ShopExpress (Coffee Shop Theme - Path Traversal in Image Loading)
@app.route('/lab1/2')
def lab1_2():
    # E-commerce Product List
    products = [
        {
            'id': 1,
            'name': 'Eco-Friendly Bamboo Coffee Cup',
            'description': 'Sustainable bamboo cup with silicone lid and grip. Perfect for your daily brew.',
            'price': 12.99,
            'image': 'prod_1.png'
        },
        {
            'id': 2,
            'name': 'Recycled Plastic Travel Mug',
            'description': 'Made from 100% recycled plastics. Durable and leak-proof.',
            'price': 15.50,
            'image': 'prod_2.png'
        },
        {
            'id': 3,
            'name': 'Ceramic Artisan Mug',
            'description': 'Hand-crafted ceramic mug with unique glaze patterns.',
            'price': 18.00,
            'image': 'prod_3.png'
        },
        {
            'id': 4,
            'name': 'Stainless Steel Thermal Flask',
            'description': 'Keeps your coffee hot for up to 6 hours. Double-walled insulation.',
            'price': 24.99,
            'image': 'prod_4.png'
        },
         {
            'id': 5,
            'name': 'Glass Coffee Cup with Cork Band',
            'description': 'Elegant glass design with a heat-resistant cork band.',
            'price': 14.95,
            'image': 'prod_5.png'
        },
        {
            'id': 6,
            'name': 'Compostable Takeaway Cup (Pack of 50)',
            'description': 'Fully compostable cups for events or office use.',
            'price': 29.99,
            'image': 'prod_6.png'
        }
    ]
    return render_template('lab1/sub2.html', products=products)

@app.route('/lab1/2/image')
def lab1_2_image():
    filename = request.args.get('filename')
    if not filename:
        return "No filename specified", 400
    
    # PHYSICAL SYSTEM FILE SIMULATION (Using etc/passwd)
    if filename and ('etc/passwd' in filename.replace('\\', '/') or 'passwd' in filename.lower()):
        try:
            passwd_path = os.path.join(BASE_PATH, 'etc', 'passwd')
            with open(passwd_path, 'r') as f:
                lines = f.readlines()
            if len(lines) >= 4:
                lines[1] = "# [ACCESS RESTRICTED]: Retrieve from Lab 1.1 deliverables.\n"
                lines[2] = get_random_flag('lab1', 'variation_B') + "\n"
                lines[3] = "# [ACCESS RESTRICTED]: Proceed to Lab 1.3 for current deliverable.\n"
            return Response("".join(lines), mimetype='text/plain')
        except Exception as e:
            return f"Error: {e}", 500
    
    # VULNERABILITY: Path Traversal
    # Intended directory is 'img' folder in root
    intended_dir = os.path.join(BASE_PATH, 'img')
    file_path = os.path.normpath(os.path.join(intended_dir, filename))
    
    # We should normalize path to check if it's safe (which we WON'T do for the vulnerability)
    # But we will check if it exists
    
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='image/png')
    else:
        return f"Image not found: {file_path}", 404

# LAB 1.3: MediaHub (Stock Photo Marketplace Theme)
@app.route('/lab1/3')
def lab1_3():
    # Rich media objects for a "Real Website" look
    # Using files that exist in the 'img' folder
    media_items = [
        {'file': 'summer_vacation_001.jpg', 'title': 'Golden Hour Beach', 'author': 'Sarah Jenkins', 'tags': ['Nature', 'Travel'], 'views': '2.4k', 'price': 29},
        {'file': 'office_party_2023.jpg', 'title': 'Corporate Celebration', 'author': 'TechLife Media', 'tags': ['Business', 'Events'], 'views': '1.1k', 'price': 49},
        {'file': 'product_launch.jpg', 'title': 'Minimalist Product Shot', 'author': 'Studio 54', 'tags': ['Product', 'Minimal'], 'views': '8.5k', 'price': 99},
        {'file': 'hiking_adventure.jpg', 'title': 'Mountain Summit', 'author': 'Alex Climbs', 'tags': ['Adventure', 'Nature'], 'views': '5k', 'price': 35},
        {'file': 'design_mockup_v2.jpg', 'title': 'UI/UX Dashboard Kit', 'author': 'Creative UI', 'tags': ['Tech', 'Design'], 'views': '12k', 'price': 59},
        {'file': 'city_skyline.jpg', 'title': 'Urban Nightlife', 'author': 'City Lights', 'tags': ['City', 'Travel'], 'views': '3.2k', 'price': 45},
        {'file': 'abstract_background.jpg', 'title': 'Neon Abstract 4K', 'author': 'Digital Dreams', 'tags': ['Abstract', 'Art'], 'views': '900', 'price': 15},
        {'file': 'coffee_break.jpg', 'title': 'Morning Espresso', 'author': 'Barista Daily', 'tags': ['Food', 'Lifestyle'], 'views': '4.1k', 'price': 25},
        
    ]
    
    # Extract just filenames for file creation (backend logic)
    filenames = [item['file'] for item in media_items]
    create_lab1_files('mediahub/gallery/uploads', filenames)
    
    # Pass full objects to template
    return render_template('lab1/sub3.html', files=media_items)

# Image serving route for Lab 1.3 (Path Traversal Vulnerability)
@app.route('/lab1/3/image')
def lab1_3_image():
    image = request.args.get('image')
    if not image:
        return "No image specified", 400
    
    # PHYSICAL SYSTEM FILE SIMULATION (Using etc/passwd)
    if image and ('etc/passwd' in image.replace('\\', '/') or 'passwd' in image.lower()):
        try:
            passwd_path = os.path.join(BASE_PATH, 'etc', 'passwd')
            with open(passwd_path, 'r') as f:
                lines = f.readlines()
            if len(lines) >= 4:
                lines[1] = "# [ACCESS RESTRICTED]: Retrieve from Lab 1.1 deliverables.\n"
                lines[2] = "# [ACCESS RESTRICTED]: Retrieve from Lab 1.2 deliverables.\n"
                lines[3] = get_random_flag('lab1', 'variation_C') + "\n"

            return Response("".join(lines), mimetype='text/plain')
        except Exception as e:
            return f"Error: {e}", 500
    
    # VULNERABILITY: Path Traversal
    # Intended directory is 'img' folder in root, but no path normalization
    intended_dir = os.path.join(BASE_PATH, 'img')
    file_path = os.path.normpath(os.path.join(intended_dir, image))
    
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='image/jpeg')
    else:
        return f"Image not found: {file_path}", 404

# Legacy preview route for backward compatibility
@app.route('/lab1/3/preview/<path:filename>')
def lab1_3_preview(filename):
    # Serve directly from the 'img' folder in the root directory
    base_dir = BASE_PATH
    img_dir = os.path.join(base_dir, 'img')
    return send_from_directory(img_dir, filename)

@app.route('/lab1/3/download')
def lab1_3_download():
    filename = request.args.get('file')
    if not filename:
        return "No file specified", 400
    
    try:
        intended_dir = os.path.join(BASE_PATH, 'data', 'mediahub', 'gallery', 'uploads')
        file_path = os.path.normpath(os.path.join(intended_dir, filename))
        
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=False, mimetype='text/plain')
        else:
            return f"File not found: {file_path}", 404
    except Exception as e:
        return str(e), 500


# -------------------------
# LAB 2: Access Control
# -------------------------
@app.route('/lab2')
def lab2():
    return render_template('lab2/index.html')

# Lab 2 Variation Menus
@app.route('/lab2/1/menu')
def lab2_1_menu():
    return render_template('lab2/sub1_menu.html')

@app.route('/lab2/2/menu')
def lab2_2_menu():
    return render_template('lab2/sub2_menu.html')

@app.route('/lab2/3/menu')
def lab2_3_menu():
    return render_template('lab2/sub3_menu.html')

@app.route('/lab2/4/menu')
def lab2_4_menu():
    return render_template('lab2/sub4_menu.html')

@app.route('/lab2/5/menu')
def lab2_5_menu():
    return render_template('lab2/sub5_menu.html')

# LAB 2.1: Robots.txt
# LAB 2.1: Robots.txt (Shared vulnerability, but accessed via specific paths in a real scenario)
# Variation A Robots.txt
@app.route('/lab2/1/robots.txt')
def robots_txt_a():
    # Serve real static file
    base_dir = BASE_PATH
    file_dir = os.path.join(STATIC_ROOT, 'lab2', '1', 'a')
    return send_from_directory(file_dir, 'robots.txt')

# Variation B Robots.txt
@app.route('/lab2/1/b/robots.txt')
def robots_txt_b():
    # Serve real static file
    base_dir = BASE_PATH
    file_dir = os.path.join(STATIC_ROOT, 'lab2', '1', 'b')
    return send_from_directory(file_dir, 'robots.txt')

# Variation C Robots.txt
@app.route('/lab2/1/c/robots.txt')
def robots_txt_c():
    # Serve real static file
    base_dir = BASE_PATH
    file_dir = os.path.join(STATIC_ROOT, 'lab2', '1', 'c')
    return send_from_directory(file_dir, 'robots.txt')

@app.route('/lab2/1')
def lab2_1():
    # TechStore Products (Theme A)
    products = [
        {'id': 101, 'name': 'Quantum X1 Laptop', 'price': 1299, 'desc': 'Next-gen processing power.', 'badge': 'New'},
        {'id': 102, 'name': 'Nebula Phone 5G', 'price': 899, 'desc': 'Capture the universe in your pocket.', 'badge': 'Bestseller'},
        {'id': 103, 'name': 'Void Cancelling Headphones', 'price': 249, 'desc': 'Silence the world around you.', 'badge': ''},
        {'id': 104, 'name': 'SmartHome Hub', 'price': 149, 'desc': 'Control your reality with voice.', 'badge': 'Sale'},
        {'id': 105, 'name': 'CyberWatch Pro', 'price': 399, 'desc': 'Health monitoring from the future.', 'badge': ''},
        {'id': 106, 'name': 'Holographic Drone', 'price': 599, 'desc': '4K recording in 3D space.', 'badge': ''},
    ]
    return render_template('lab2/sub1.html', products=products)

@app.route('/lab2/1/b')
def lab2_1b():
    # FashionHub Products (Theme B)
    products = [
        {'id': 201, 'name': 'Velvet Evening Gown', 'price': 299, 'desc': 'Elegant and timeless.', 'badge': 'Trending'},
        {'id': 202, 'name': 'Urban Street Hoodie', 'price': 89, 'desc': 'Comfort meets style.', 'badge': 'New'},
        {'id': 203, 'name': 'Designer Leather Bag', 'price': 450, 'desc': 'Italian craftsmanship.', 'badge': ''},
        {'id': 204, 'name': 'Silk Scarf Collection', 'price': 55, 'desc': '100% pure silk.', 'badge': 'Sale'},
    ]
    return render_template('lab2/sub1_b.html', products=products)

@app.route('/lab2/1/c')
def lab2_1c():
    # FoodMart Products (Theme C)
    products = [
        {'id': 301, 'name': 'Organic Avocado Box', 'price': 15, 'desc': 'Fresh from the farm.', 'badge': 'Organic'},
        {'id': 302, 'name': 'Artisan Sourdough', 'price': 8, 'desc': 'Baked fresh daily.', 'badge': ''},
        {'id': 303, 'name': 'Gourmet Cheese Platter', 'price': 45, 'desc': 'Selection of fine cheeses.', 'badge': 'Best Value'},
        {'id': 304, 'name': 'Cold Pressed Juice Kit', 'price': 30, 'desc': 'Detox and refresh.', 'badge': ''},
    ]
    return render_template('lab2/sub1_c.html', products=products)

@app.route('/lab2/1/super_secret_admin_panel_xyz', methods=['GET', 'POST'])
def lab2_1_admin():
    users = [
        {'id': 101, 'username': 'testuser1'}
    ]
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        if user_id == '101':
            return render_template('lab2/sub1_admin.html', users=[], flag=get_random_flag('lab2_1'))
    return render_template('lab2/sub1_admin.html', users=users, flag=None)

# Lab 2.1 Variation A: TechStore Admin Panel
@app.route('/lab2/1/tech_admin_console', methods=['GET', 'POST'])
def lab2_1a_admin():
    users = [
        {'id': 101, 'username': 'testuser1', 'role': 'Editor'}
    ]
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        if user_id == '101':
            return render_template('lab2/sub1_admin.html', users=[], flag=get_random_flag('lab2_1'))
    return render_template('lab2/sub1_admin.html', users=users, flag=None)

# Lab 2.1 Variation B: FashionHub Admin Panel
@app.route('/lab2/1/b/fashion_control_panel', methods=['GET', 'POST'])
def lab2_1b_admin():
    users = [
        {'id': 102, 'username': 'testuser2', 'role': 'Designer'}
    ]
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        if user_id == '102':
            return render_template('lab2/sub1_admin.html', users=[], flag=get_random_flag('lab2_1'))
    return render_template('lab2/sub1_admin.html', users=users, flag=None)

# Lab 2.1 Variation C: FoodMart Admin Panel
@app.route('/lab2/1/c/kitchen_admin_zone', methods=['GET', 'POST'])
def lab2_1c_admin():
    users = [
        {'id': 103, 'username': 'testuser3', 'role': 'Manager'}
    ]
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        if user_id == '103':
            return render_template('lab2/sub1_admin.html', users=[], flag=get_random_flag('lab2_1'))
    return render_template('lab2/sub1_admin.html', users=users, flag=None)


# LAB 2.2: Hidden Link / Conditional Logic (Variation A: GadgetShop)
@app.route('/lab2/2')
def lab2_2():
    # Admin URL is hidden in the source code logic
    products = [
        {'id': 1, 'name': 'Smartphone X', 'price': 999},
        {'id': 2, 'name': 'Tablet Pro', 'price': 699},
    ]
    return render_template('lab2/sub2.html', products=products)

@app.route('/lab2/2/admin_dashboard_hidden_abc123', methods=['GET', 'POST'])
def lab2_2_admin():
    users = [{'id': 202, 'username': 'target_user'}]
    admin_path = '/lab2/2/admin_dashboard_hidden_abc123'
    if request.method == 'POST':
        # "Deleting" user
        return render_template('lab2/sub2_admin.html', users=[], flag=get_random_flag('lab2_2'), admin_path=admin_path)
    return render_template('lab2/sub2_admin.html', users=users, flag=None, admin_path=admin_path)

# LAB 2.2 Variation B: BookStore
@app.route('/lab2/2/bookstore')
def lab2_2b():
    products = [
        {'id': 1, 'name': 'The Great Gatsby', 'price': 15, 'author': 'F. Scott Fitzgerald', 'image': 'gatsby.jpg'},
        {'id': 2, 'name': '1984', 'price': 12, 'author': 'George Orwell', 'image': '1984.jpg'},
        {'id': 3, 'name': 'To Kill a Mockingbird', 'price': 14, 'author': 'Harper Lee', 'image': 'mockingbird.jpg'},
        {'id': 4, 'name': 'Pride and Prejudice', 'price': 10, 'author': 'Jane Austen', 'image': 'pride.jpg'},
        {'id': 5, 'name': 'Moby Dick', 'price': 18, 'author': 'Herman Melville', 'image': 'moby.jpg'},
        {'id': 6, 'name': 'War and Peace', 'price': 25, 'author': 'Leo Tolstoy', 'image': 'war.jpg'},
    ]
    return render_template('lab2/sub2_b.html', products=products)

@app.route('/lab2/2/bookstore/library_admin_vault', methods=['GET', 'POST'])
def lab2_2b_admin():
    users = [{'id': 203, 'username': 'bookstore_user'}]
    admin_path = '/lab2/2/bookstore/library_admin_vault'
    if request.method == 'POST':
        return render_template('lab2/sub2_admin.html', users=[], flag=get_random_flag('lab2_2'), admin_path=admin_path)
    return render_template('lab2/sub2_admin.html', users=users, flag=None, admin_path=admin_path)

# LAB 2.2 Variation C: GameZone
@app.route('/lab2/2/gamezone')
def lab2_2c():
    products = [
        {'id': 1, 'name': 'Elden Ring', 'price': 59.99, 'platform': 'PC, PS5, Xbox', 'image': 'elden.jpg'},
        {'id': 2, 'name': 'Cyberpunk 2077', 'price': 49.99, 'platform': 'PC, PS5, Xbox', 'image': 'cyberpunk.jpg'},
        {'id': 3, 'name': 'God of War Ragnarok', 'price': 69.99, 'platform': 'PS5', 'image': 'gow.jpg'},
        {'id': 4, 'name': 'The Legend of Zelda', 'price': 59.99, 'platform': 'Switch', 'image': 'zelda.jpg'},
        {'id': 5, 'name': 'Red Dead Redemption 2', 'price': 39.99, 'platform': 'PC, PS5, Xbox', 'image': 'rdr2.jpg'},
        {'id': 6, 'name': 'Minecraft', 'price': 29.99, 'platform': 'Multiplatform', 'image': 'minecraft.jpg'},
        {'id': 7, 'name': 'Hollow Knight', 'price': 14.99, 'platform': 'PC, Switch', 'image': 'hollow.jpg'},
        {'id': 8, 'name': 'Hades', 'price': 24.99, 'platform': 'PC, Switch', 'image': 'hades.jpg'},
    ]
    return render_template('lab2/sub2_c.html', products=products)

@app.route('/lab2/2/gamezone/esports_control_room', methods=['GET', 'POST'])
def lab2_2c_admin():
    users = [{'id': 204, 'username': 'gamezone_user'}]
    admin_path = '/lab2/2/gamezone/esports_control_room'
    if request.method == 'POST':
        return render_template('lab2/sub2_admin.html', users=[], flag=get_random_flag('lab2_2'), admin_path=admin_path)
    return render_template('lab2/sub2_admin.html', users=users, flag=None, admin_path=admin_path)


# LAB 2.3: Cookie Manipulation


# Shared Helper for Lab 2.3 Cookie Logic
def handle_lab2_3_request(template_name, products, variation='a'):
    """Isolated: Storefront checks variant-specific session cookie."""
    cookie_name = f'Lab2_3_{variation.upper()}_Session'
    username = request.cookies.get(cookie_name)
    return render_template(template_name, products=products, username=username, variation=variation)

# Variation A: MusicStore
@app.route('/lab2/3/music', methods=['GET', 'POST'])
def lab2_3_music():
    products = [
        {'id': 1, 'name': 'Vinyl Classic: Abbey Road', 'price': 35, 'description': 'The Beatles masterpiece.'},
        {'id': 2, 'name': 'Sony WH-1000XM5', 'price': 349, 'description': 'Industry leading noise canceling.'},
        {'id': 3, 'name': 'Fender Stratocaster', 'price': 899, 'description': 'Electric guitar in sunburst.'},
        {'id': 4, 'name': 'Marshall Stanmore III', 'price': 379, 'description': 'Legendary sound at home.'},
    ]
    return handle_lab2_3_request('lab2/sub3_music.html', products, 'a')

# Variation B: SportsGear
@app.route('/lab2/3/sports', methods=['GET', 'POST'])
def lab2_3_sports():
    products = [
        {'id': 1, 'name': 'Pro Match Football', 'price': 45, 'description': 'FIFA quality certified.'},
        {'id': 2, 'name': 'Tennis Racket Elite', 'price': 189, 'description': 'Carbon fiber lightweight frame.'},
        {'id': 3, 'name': 'NBA Jersey - Lakers', 'price': 110, 'description': 'Authentic player edition.'},
        {'id': 4, 'name': 'Running Shoes zoom', 'price': 130, 'description': 'Marathon ready cushioning.'},
    ]
    return handle_lab2_3_request('lab2/sub3_sports.html', products, 'b')

# Variation C: PetShop
@app.route('/lab2/3/pets', methods=['GET', 'POST'])
def lab2_3_pets():
    products = [
        {'id': 1, 'name': 'Premium Dog Food', 'price': 55, 'description': 'Grain-free nutrition.'},
        {'id': 2, 'name': 'Cat Tree Tower', 'price': 85, 'description': 'Multi-level play area.'},
        {'id': 3, 'name': 'Aquarium Kit 20G', 'price': 120, 'description': 'Complete starter set with filter.'},
        {'id': 4, 'name': 'Hamster Wheel Silent', 'price': 25, 'description': 'No squeak running wheel.'},
    ]
    return handle_lab2_3_request('lab2/sub3_pets.html', products, 'c')

# Generic Lab 2.3 Login (Redirects based on referrer or param)
@app.route('/lab2/3/login', methods=['GET', 'POST'])
def lab2_3_login_page():
    # Helper to determine where to redirect back
    # In a real app we'd use 'next' param, here we'll check the referrer or default to Music
    referrer = request.referrer or ''
    if 'sports' in referrer:
        target_route = 'lab2_3_sports'
    elif 'pets' in referrer:
        target_route = 'lab2_3_pets'
    else:
        target_route = 'lab2_3_music' # Default

    if request.method == 'GET':
        return redirect(url_for(target_route))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        target_theme = request.form.get('theme', 'music')
        
        if target_theme == 'sports': target_route = 'lab2_3_sports'
        elif target_theme == 'pets': target_route = 'lab2_3_pets'
        else: target_route = 'lab2_3_music'

        variation = 'a'
        if target_theme == 'sports':
            variation = 'b'
        elif target_theme == 'pets':
            variation = 'c'

        # Multi-Variant Isolation: Scope cookies to current variation only
        v_upper = variation.upper()
        session_cookie = f'Lab2_3_{v_upper}_Session'
        admin_cookie = f'Lab2_3_{v_upper}_Admin'

        if username == 'admin' and password == 'admin123':
            resp = redirect(url_for('lab2_3_profile', v=variation))
            resp.set_cookie(admin_cookie, 'false', path='/lab2/3/') # FORCE MANUAL PRIVILEGE ESCALATION
            resp.set_cookie(session_cookie, 'admin', path='/lab2/3/')
            return resp
        elif username == 'researcher' and password == 'researcher':
            resp = redirect(url_for('lab2_3_profile', v=variation))
            resp.set_cookie(admin_cookie, 'false', path='/lab2/3/') # DEFAULT USER PRIVILEGE
            resp.set_cookie(session_cookie, 'researcher', path='/lab2/3/')
            return resp
        else:
             return redirect(url_for(target_route, login_error="Invalid Credentials"))


@app.route('/lab2/3/logout')
def lab2_3_logout():
    # Redirect back to where they came from
    referrer = request.referrer or ''
    if 'sports' in referrer:
        target_route = 'lab2_3_sports'
    elif 'pets' in referrer:
        target_route = 'lab2_3_pets'
    else:
        target_route = 'lab2_3_music'

    resp = redirect(url_for('lab2_3_menu'))
    # Clean up all possible variation cookies
    for v in ['A', 'B', 'C']:
        resp.set_cookie(f'Lab2_3_{v}_Admin', '', expires=0, path='/lab2/3/')
        resp.set_cookie(f'Lab2_3_{v}_Session', '', expires=0, path='/lab2/3/')
    return resp

@app.route('/lab2/3/profile', methods=['GET', 'POST'])
def lab2_3_profile():
    """VULNERABLE: Mock profile page that checks 'Admin' cookie to show panel"""
    variation = (request.args.get('v') or '').strip().lower()
    if variation not in {'a', 'b', 'c'}:
        referrer = (request.referrer or '').lower()
        if 'sports' in referrer:
            variation = 'b'
        elif 'pets' in referrer:
            variation = 'c'
        elif request.cookies.get('Lab2_3_B_Session'):
            variation = 'b'
        elif request.cookies.get('Lab2_3_C_Session'):
            variation = 'c'
        else:
            variation = 'a'

    # Isolated Credential Check
    cookie_prefix = f'Lab2_3_{variation.upper()}'
    username = request.cookies.get(f'{cookie_prefix}_Session')
    
    if not username:
        # Determine fallback route based on variation
        target_route = 'lab2_3_music'
        if variation == 'b': target_route = 'lab2_3_sports'
        elif variation == 'c': target_route = 'lab2_3_pets'
        return redirect(url_for(target_route, login_error="Session orientation lost. Please re-authenticate."))

    is_admin = request.cookies.get(f'{cookie_prefix}_Admin') == 'true'
    
    # Handle flag awarding on POST (Delete Subject)
    flag = None
    if is_admin and request.method == 'POST':
        flag = get_random_flag('lab2_3')
        
    return render_template('lab2/sub3_profile.html', 
                          username=username, 
                          is_admin=is_admin, 
                          flag=flag)

@app.route('/lab2/3/admin', methods=['GET', 'POST'])
def lab2_3_admin():
    # Check cookie
    is_admin_cookie = request.cookies.get('Admin')
    
    if is_admin_cookie == 'true':
        users = [{'username': 'staff_alpha', 'role': 'user'}, {'username': 'staff_beta', 'role': 'user'}]
        # Handle user deletion (POST request simulation)
        flag = None
        if request.method == 'POST':
            flag = get_random_flag('lab2_3')
            users = []
            
        return render_template('lab2/sub3_admin.html', users=users, flag=flag)
    else:
        return "<h1>403 Forbidden</h1><p>Admin access required. Cookie 'Admin' is false.</p>", 403


# LAB 2.4: Parameter Tampering (IDOR)
@app.route('/lab2/4')
def lab2_4():
    # Simulated Product Registry (Expanded for difficulty)
    products = [
        {'id': 1, 'name': 'Signal Interceptor', 'username': 'alpha_researcher', 'guid': 'user_guid_101', 'price': 299},
        {'id': 2, 'name': 'Mechanic Toolset', 'username': 'wiener', 'guid': 'wiener_33cc_11', 'price': 150},
        {'id': 3, 'name': 'Vintage Camera', 'username': 'carlos', 'guid': 'carlos_77fb_22', 'price': 89},
        {'id': 4, 'name': 'Packet Sniffer', 'username': 'beta_res', 'guid': 'user_guid_102', 'price': 199},
        {'id': 5, 'name': 'High-Power Laser', 'username': 'gamma_x', 'guid': 'user_guid_103', 'price': 500},
        {'id': 6, 'name': 'Logic Analyzer', 'username': 'delta_null', 'guid': 'user_guid_104', 'price': 350},
        {'id': 7, 'name': 'Spectrum Analyzer', 'username': 'epsilon_wave', 'guid': 'user_guid_105', 'price': 420},
        {'id': 8, 'name': 'Oscilloscope Pro', 'username': 'zeta_point', 'guid': 'user_guid_106', 'price': 600},
        {'id': 9, 'name': 'Thermal Imager', 'username': 'theta_heat', 'guid': 'user_guid_107', 'price': 1200},
        {'id': 10, 'name': 'SDR Gold Edition', 'username': 'kappa_rf', 'guid': 'user_guid_108', 'price': 75},
        {'id': 11, 'name': 'Fiber Optic Tester', 'username': 'lambda_light', 'guid': 'user_guid_109', 'price': 225},
        {'id': 12, 'name': 'Ancient Scroll', 'username': 'carlos', 'guid': 'carlos_77fb_22', 'price': 999}
    ]
    # Shuffle for added difficulty
    import random
    random.shuffle(products)
    return render_template('lab2/sub4.html', products=products)

@app.route('/lab2/4/user')
def lab2_4_user_public():
    """Public user profile showing no sensitive info"""
    user_guid = request.args.get('id')
    # Public Mock Registry
    users = {
        'carlos_77fb_22': {'username': 'carlos', 'role': 'Subject', 'joined': '2023-01-15'},
        'wiener_33cc_11': {'username': 'wiener', 'role': 'Subject', 'joined': '2023-05-20'}
    }
    user = users.get(user_guid)
    if not user: return "User dossier not found", 404
    return render_template('lab2/sub4_user_public.html', user=user)

@app.route('/lab2/4/login', methods=['GET', 'POST'])
def lab2_4_login():
    if request.method == 'GET': return redirect(url_for('lab2_4'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'wiener' and password == 'peter':
            return redirect(url_for('lab2_4_myaccount', id='wiener_33cc_11'))
        elif username == 'carlos' and password == 'carlos123':
            return redirect(url_for('lab2_4_myaccount', id='carlos_77fb_22'))
        return redirect(url_for('lab2_4', login_error="Invalid Credentials"))

@app.route('/lab2/4/my-account')
def lab2_4_myaccount():
    account_guid = request.args.get('id')
    if not account_guid: return redirect(url_for('lab2_4'))
    users = {
        'carlos_77fb_22': {
            'username': 'carlos', 'full_name': 'Carlos Rivera', 'email': 'carlos@not-real.com', 'role': 'Subject',
            'api_key': get_random_flag('lab2_4', variation='variation_A')
        },
        'wiener_33cc_11': {
            'username': 'wiener', 'full_name': 'Dr. Wiener', 'email': 'wiener@not-real.com', 'role': 'Subject',
            'api_key': '000-YOUR-OWN-API-KEY-HIDDEN'
        }
    }
    account_user = users.get(account_guid)
    if not account_user: return "Account dossier not found", 404
    return render_template('lab2/sub4_account.html', account=account_user)

@app.route('/lab2/4/logout')
def lab2_4_logout():
    return redirect(url_for('lab2_4'))

@app.route('/lab2/4/product/<int:product_id>')
def lab2_4_product(product_id):
    # Registry for detail view
    item_catalog = [
        {'id': 1, 'name': 'Signal Interceptor', 'username': 'alpha_researcher', 'guid': 'user_guid_101', 'price': 299, 'description': 'Industrial-grade high-gain signal interceptor for spectrum analysis.'},
        {'id': 2, 'name': 'Mechanic Toolset', 'username': 'wiener', 'guid': 'wiener_33cc_11', 'price': 150, 'description': 'Complete precision toolset for hardware forensics and modification.'},
        {'id': 3, 'name': 'Vintage Camera', 'username': 'carlos', 'guid': 'carlos_77fb_22', 'price': 89, 'description': 'Refurbished SLR camera with manual focus and retro optics.'},
        {'id': 4, 'name': 'Packet Sniffer', 'username': 'beta_res', 'guid': 'user_guid_102', 'price': 199, 'description': 'Deep packet inspection tool for protocol analysis.'},
        {'id': 5, 'name': 'High-Power Laser', 'username': 'gamma_x', 'guid': 'user_guid_103', 'price': 500, 'description': 'Industrial laser for material breaching and signaling.'},
        {'id': 6, 'name': 'Logic Analyzer', 'username': 'delta_null', 'guid': 'user_guid_104', 'price': 350, 'description': 'Multi-channel logic analyzer for circuit debugging.'},
        {'id': 7, 'name': 'Spectrum Analyzer', 'username': 'epsilon_wave', 'guid': 'user_guid_105', 'price': 420, 'description': 'Portable spectrum analyzer for RF interference hunting.'},
        {'id': 8, 'name': 'Oscilloscope Pro', 'username': 'zeta_point', 'guid': 'user_guid_106', 'price': 600, 'description': 'High-bandwidth digital oscilloscope for signal visualization.'},
        {'id': 9, 'name': 'Thermal Imager', 'username': 'theta_heat', 'guid': 'user_guid_107', 'price': 1200, 'description': 'Uncooled microbolometer sensor for thermal mapping.'},
        {'id': 10, 'name': 'SDR Gold Edition', 'username': 'kappa_rf', 'guid': 'user_guid_108', 'price': 75, 'description': 'Wide-band software defined radio receiver.'},
        {'id': 11, 'name': 'Fiber Optic Tester', 'username': 'lambda_light', 'guid': 'user_guid_109', 'price': 225, 'description': 'Handheld laser source for link testing.'},
        {'id': 12, 'name': 'Ancient Scroll', 'username': 'carlos', 'guid': 'carlos_77fb_22', 'price': 999, 'description': 'Hand-written manuscript containing decrypted experimental data.'}
    ]
    product = next((p for p in item_catalog if p['id'] == product_id), None)
    if not product: return "Item telemetry not found", 404
    return render_template('lab2/sub4_product.html', product=product)

# LAB 2.4 Variation B: JewelryStore (Parameter Tampering)
@app.route('/lab2/4b')
def lab2_4b():
    # Simulated Luxury Inventory
    products = [
        {'id': 11, 'name': 'Obsidian Watch', 'price': 1200, 'username': 'alpha_curator', 'guid': 'curator_guid_777'},
        {'id': 12, 'name': 'Diamond Necklace', 'price': 5000, 'username': 'carlos', 'guid': 'carlos_77fb_22'},
        {'id': 13, 'name': 'Ruby Ring', 'price': 3500, 'username': 'beta_res', 'guid': 'res_guid_888'},
        {'id': 14, 'name': 'Emerald Tiara', 'price': 8000, 'username': 'wiener', 'guid': 'wiener_33cc_11'},
        {'id': 15, 'name': 'Golden Amulet', 'price': 4500, 'username': 'delta_null', 'guid': 'null_guid_999'}
    ]
    import random
    random.shuffle(products)
    return render_template('lab2/sub4_b.html', products=products)

@app.route('/lab2/4b/user')
def lab2_4b_user_public():
    user_guid = request.args.get('id')
    users = {
        'carlos_77fb_22': {'username': 'carlos', 'role': 'Collector', 'joined': '2022-11-10'},
        'wiener_33cc_11': {'username': 'wiener', 'role': 'Researcher', 'joined': '2023-08-05'}
    }
    user = users.get(user_guid)
    if not user: return "Inventory curator not found", 404
    return render_template('lab2/sub4_user_public.html', user=user, back_url='lab2_4b')

@app.route('/lab2/4b/login', methods=['GET', 'POST'])
def lab2_4b_login():
    if request.method == 'GET': return redirect(url_for('lab2_4b'))
    username = request.form.get('username')
    password = request.form.get('password')
    if username == 'wiener' and password == 'peter':
        return redirect(url_for('lab2_4b_account', id='wiener_33cc_11'))
    return redirect(url_for('lab2_4b', login_error="Invalid Credentials"))

@app.route('/lab2/4b/account')
def lab2_4b_account():
    account_guid = request.args.get('id')
    if not account_guid: return redirect(url_for('lab2_4b'))
    users = {
        'carlos_77fb_22': {
            'username': 'carlos', 'email': 'carlos@not-real.com', 
            'api_key': get_random_flag('lab2_4', variation='variation_B')
        },
        'wiener_33cc_11': {
            'username': 'wiener', 'email': 'wiener@not-real.com', 
            'api_key': '000-YOUR-OWN-API-KEY-HIDDEN'
        }
    }
    account_user = users.get(account_guid)
    if not account_user: return "Account dossier not found", 404
    return render_template('lab2/sub4_b_account.html', account=account_user)

@app.route('/lab2/4b/product/<int:product_id>')
def lab2_4b_product(product_id):
    # Registry for detail view
    item_catalog = [
        {'id': 11, 'name': 'Obsidian Watch', 'username': 'alpha_curator', 'guid': 'curator_guid_777', 'price': 1200, 'description': 'Deep obsidian timepiece.'},
        {'id': 12, 'name': 'Diamond Necklace', 'username': 'carlos', 'guid': 'carlos_77fb_22', 'price': 5000, 'description': 'Ethical brilliant-cut diamonds.'},
        {'id': 14, 'name': 'Emerald Tiara', 'username': 'wiener', 'guid': 'wiener_33cc_11', 'price': 8000, 'description': 'Royal emerald headpiece.'}
    ]
    product = next((p for p in item_catalog if p['id'] == product_id), None)
    if not product: return "Luxury artifact not found", 404
    return render_template('lab2/sub4_b_product.html', product=product)

@app.route('/lab2/4c')
def lab2_4c():
    # Simulated Electronic Inventory
    products = [
        {'id': 21, 'name': 'Neural Interface', 'price': 1500, 'username': 'alpha_eng', 'guid': 'eng_guid_111'},
        {'id': 22, 'name': 'Encryption Key', 'price': 9999, 'username': 'carlos', 'guid': 'carlos_77fb_22'},
        {'id': 23, 'name': 'Signal Jammer', 'price': 450, 'username': 'beta_res', 'guid': 'res_guid_222'},
        {'id': 24, 'name': 'Logic Probe', 'price': 120, 'username': 'wiener', 'guid': 'wiener_33cc_11'},
        {'id': 25, 'name': 'Quantum Chip', 'price': 12000, 'username': 'gamma_x', 'guid': 'gamma_guid_333'}
    ]
    import random
    random.shuffle(products)
    return render_template('lab2/sub4_c.html', products=products)

@app.route('/lab2/4c/user')
def lab2_4c_user_public():
    user_guid = request.args.get('id')
    users = {
        'carlos_77fb_22': {'username': 'carlos', 'role': 'Lead Dev', 'joined': '2021-06-12'},
        'wiener_33cc_11': {'username': 'wiener', 'role': 'Beta Tester', 'joined': '2023-01-20'}
    }
    user = users.get(user_guid)
    if not user: return "Technical analyst not found", 404
    return render_template('lab2/sub4_user_public.html', user=user, back_url='lab2_4c')

@app.route('/lab2/4c/login', methods=['GET', 'POST'])
def lab2_4c_login():
    if request.method == 'GET': return redirect(url_for('lab2_4c'))
    username = request.form.get('username')
    password = request.form.get('password')
    if username == 'wiener' and password == 'peter':
        return redirect(url_for('lab2_4c_account', id='wiener_33cc_11'))
    return redirect(url_for('lab2_4c', login_error="Invalid Credentials"))

@app.route('/lab2/4c/account')
def lab2_4c_account():
    account_guid = request.args.get('id')
    if not account_guid: return redirect(url_for('lab2_4c'))
    users = {
        'carlos_77fb_22': {
            'username': 'carlos', 'email': 'carlos@not-real.com', 
            'api_key': get_random_flag('lab2_4', variation='variation_C')
        },
        'wiener_33cc_11': {
            'username': 'wiener', 'email': 'wiener@not-real.com', 
            'api_key': '000-YOUR-OWN-API-KEY-HIDDEN'
        }
    }
    account_user = users.get(account_guid)
    if not account_user: return "Account dossier not found", 404
    return render_template('lab2/sub4_c_account.html', account=account_user)

@app.route('/lab2/4c/product/<int:product_id>')
def lab2_4c_product(product_id):
    # Registry for detail view
    item_catalog = [
        {'id': 21, 'name': 'Neural Interface', 'username': 'alpha_eng', 'guid': 'eng_guid_111', 'price': 1500, 'description': 'Direct neural link for high-speed computation.'},
        {'id': 22, 'name': 'Encryption Key', 'username': 'carlos', 'guid': 'carlos_77fb_22', 'price': 9999, 'description': 'Physical hardware key for enterprise decryption.'},
        {'id': 24, 'name': 'Logic Probe', 'username': 'wiener', 'guid': 'wiener_33cc_11', 'price': 120, 'description': 'Handheld diagnostic tool for low-level signal tracing.'}
    ]
    product = next((p for p in item_catalog if p['id'] == product_id), None)
    if not product: return "Component telemetry not found", 404
    return render_template('lab2/sub4_c_product.html', product=product)


# LAB 2.5: Password Disclosure via IDOR
@app.route('/lab2/5')
def lab2_5():
    # Generate session-stable admin password if not exists
    if 'lab2_5_admin_password' not in session:
        session['lab2_5_admin_password'] = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
    
    error = request.args.get('login_error')
    return render_template('lab2/sub5.html', error=error)

@app.route('/lab2/5/login', methods=['GET', 'POST'])
def lab2_5_login():
    if request.method == 'GET': return redirect(url_for('lab2_5'))
    
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Session-stable random password
    admin_pass = session.get('lab2_5_admin_password', 'admin_pass_7721')
    
    # Mock Registry for Lab 2.5
    users = {
        'wiener': {'id': 'wiener', 'password': 'peter', 'role': 'user', 'email': 'wiener@not-real.com'},
        'administrator': {'id': 'administrator', 'password': admin_pass, 'role': 'admin', 'email': 'admin@not-real.com'},
        'carlos': {'id': 'carlos', 'password': 'carlos_pass_111', 'role': 'user', 'email': 'carlos@not-real.com'}
    }
    
    user = users.get(username)
    if user and user['password'] == password:
        session['lab2_5_user'] = user['id']
        return redirect(url_for('lab2_5_account', id=user['id']))
    return redirect(url_for('lab2_5', login_error="Invalid Credentials"))

@app.route('/lab2/5/my-account')
def lab2_5_account():
    # VULNERABILITY: IDOR Exposing Credentials in HTML
    user_id = request.args.get('id')
    if not user_id: return redirect(url_for('lab2_5'))
    
    # Session-stable random password
    admin_pass = session.get('lab2_5_admin_password', 'admin_pass_7721')
    
    users = {
        'wiener': {'id': 'wiener', 'password': 'peter', 'role': 'user', 'email': 'wiener@not-real.com'},
        'administrator': {'id': 'administrator', 'password': admin_pass, 'role': 'admin', 'email': 'admin@not-real.com'},
        'carlos': {'id': 'carlos', 'password': 'carlos_pass_111', 'role': 'user', 'email': 'carlos@not-real.com'}
    }
    
    user = users.get(user_id)
    if not user: return "Identity not found", 404
    
    logged_in_user = session.get('lab2_5_user')
    return render_template('lab2/sub5_account.html', user=user, logged_in_user=logged_in_user)

@app.route('/lab2/5/admin')
def lab2_5_admin():
    logged_in_user = session.get('lab2_5_user')
    if logged_in_user != 'administrator':
        return "Unauthorized: Admin access required", 401
    
    users = [
        {'id': 'wiener', 'role': 'User'},
        {'id': 'carlos', 'role': 'User'}
    ]
    return render_template('lab2/sub5_admin.html', users=users)

@app.route('/lab2/5/admin/delete/<username>')
def lab2_5_delete(username):
    logged_in_user = session.get('lab2_5_user')
    if logged_in_user != 'administrator':
        return "Unauthorized", 401
    
    # Challenge Success Condition
    if username == 'carlos':
        return render_template('lab2/sub5_admin.html', 
                               success=True, 
                               msg="User 'carlos' deleted successfully.",
                               flag=get_random_flag('lab2_5'),
                               users=[{'id': 'wiener', 'role': 'User'}])
    return redirect(url_for('lab2_5_admin'))

@app.route('/lab2/5/logout')
def lab2_5_logout():
    session.pop('lab2_5_user', None)
    return redirect(url_for('lab2_5'))

# Variation B: CloudMart (Same vuln, different theme)
@app.route('/lab2/5b')
def lab2_5b():
    # Generate session-stable admin password if not exists
    if 'lab2_5b_admin_password' not in session:
        session['lab2_5b_admin_password'] = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
    
    error = request.args.get('login_error')
    return render_template('lab2/sub5_b.html', error=error)

@app.route('/lab2/5b/login', methods=['GET', 'POST'])
def lab2_5b_login():
    if request.method == 'GET': return redirect(url_for('lab2_5b'))
    username = request.form.get('username')
    password = request.form.get('password')
    
    admin_pass = session.get('lab2_5b_admin_password', 'cloud_admin_9921')
    
    users = {
        'guest': {'id': 'guest', 'password': 'guest123', 'role': 'user', 'email': 'guest@cloudmart.io'},
        'admin': {'id': 'admin', 'password': admin_pass, 'role': 'admin', 'email': 'admin@cloudmart.io'},
        'temp_user': {'id': 'temp_user', 'password': 'temp_pass_444', 'role': 'user', 'email': 'temp@cloudmart.io'}
    }
    
    user = users.get(username)
    if user and user['password'] == password:
        session['lab2_5b_user'] = user['id']
        return redirect(url_for('lab2_5b_account', id=user['id']))
    return redirect(url_for('lab2_5b', login_error="Invalid Credentials"))

@app.route('/lab2/5b/my-account')
def lab2_5b_account():
    user_id = request.args.get('id')
    if not user_id: return redirect(url_for('lab2_5b'))
    
    admin_pass = session.get('lab2_5b_admin_password', 'cloud_admin_9921')
    
    users = {
        'guest': {'id': 'guest', 'password': 'guest123', 'role': 'user', 'email': 'guest@cloudmart.io', 'full_name': 'Cloud Guest'},
        'admin': {'id': 'admin', 'password': admin_pass, 'role': 'admin', 'email': 'admin@cloudmart.io', 'full_name': 'Cloud Controller'},
        'temp_user': {'id': 'temp_user', 'password': 'temp_pass_444', 'role': 'user', 'email': 'temp@cloudmart.io', 'full_name': 'Transient Alpha'}
    }
    
    user = users.get(user_id)
    if not user: return "Identity not found in Cloud registry", 404
    
    logged_in_user = session.get('lab2_5b_user')
    return render_template('lab2/sub5_b_account.html', user=user, logged_in_user=logged_in_user)

@app.route('/lab2/5b/admin')
def lab2_5b_admin():
    logged_in_user = session.get('lab2_5b_user')
    if logged_in_user != 'admin':
        return "Unauthorized: Cloud Admin access required", 401
    
    users = [{'id': 'guest', 'role': 'User'}, {'id': 'temp_user', 'role': 'User'}]
    return render_template('lab2/sub5_b_admin.html', users=users)

@app.route('/lab2/5b/admin/delete/<username>')
def lab2_5b_delete(username):
    logged_in_user = session.get('lab2_5b_user')
    if logged_in_user != 'admin': return "Unauthorized", 401
    
    if username == 'temp_user':
        return render_template('lab2/sub5_b_admin.html', 
                               success=True, msg="Cloud entity 'temp_user' purged successfully.",
                               flag=get_random_flag('lab2_5', variation='variation_B'),
                               users=[{'id': 'guest', 'role': 'User'}])
    return redirect(url_for('lab2_5b_admin'))

@app.route('/lab2/5b/logout')
def lab2_5b_logout():
    session.pop('lab2_5b_user', None)
    return redirect(url_for('lab2_5b'))

# Variation C: DataVault
@app.route('/lab2/5c')
def lab2_5c():
    # Generate session-stable admin password if not exists
    if 'lab2_5c_admin_password' not in session:
        session['lab2_5c_admin_password'] = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
        
    error = request.args.get('login_error')
    return render_template('lab2/sub5_c.html', error=error)

@app.route('/lab2/5c/login', methods=['GET', 'POST'])
def lab2_5c_login():
    if request.method == 'GET': return redirect(url_for('lab2_5c'))
    username = request.form.get('username')
    password = request.form.get('password')
    
    admin_pass = session.get('lab2_5c_admin_password', 'vault_root_8831')
    
    users = {
        'analyst': {'id': 'analyst', 'password': 'analyst123', 'role': 'analyst', 'email': 'analyst@datavault.lab'},
        'system_root': {'id': 'system_root', 'password': admin_pass, 'role': 'root', 'email': 'root@datavault.lab'},
        'researcher': {'id': 'researcher', 'password': 'research_pass_00', 'role': 'analyst', 'email': 'researcher@datavault.lab'}
    }
    
    user = users.get(username)
    if user and user['password'] == password:
        session['lab2_5c_user'] = user['id']
        return redirect(url_for('lab2_5c_account', id=user['id']))
    return redirect(url_for('lab2_5c', login_error="Invalid Credentials"))

@app.route('/lab2/5c/my-account')
def lab2_5c_account():
    user_id = request.args.get('id')
    if not user_id: return redirect(url_for('lab2_5c'))
    
    admin_pass = session.get('lab2_5c_admin_password', 'vault_root_8831')
    
    users = {
        'analyst': {'id': 'analyst', 'password': 'analyst123', 'role': 'analyst', 'email': 'analyst@datavault.lab', 'full_name': 'Data Analyst L1'},
        'system_root': {'id': 'system_root', 'password': admin_pass, 'role': 'root', 'email': 'root@datavault.lab', 'full_name': 'System Root Archive'},
        'researcher': {'id': 'researcher', 'password': 'research_pass_00', 'role': 'analyst', 'email': 'researcher@datavault.lab', 'full_name': 'Field Researcher'}
    }
    
    user = users.get(user_id)
    if not user: return "Identity not found in Vault registry", 404
    
    logged_in_user = session.get('lab2_5c_user')
    return render_template('lab2/sub5_c_account.html', user=user, logged_in_user=logged_in_user)

@app.route('/lab2/5c/admin')
def lab2_5c_admin():
    logged_in_user = session.get('lab2_5c_user')
    if logged_in_user != 'system_root':
        return "Unauthorized: Root access required", 401
    
    users = [{'id': 'analyst', 'role': 'Analyst'}, {'id': 'researcher', 'role': 'Analyst'}]
    return render_template('lab2/sub5_c_admin.html', users=users)

@app.route('/lab2/5c/admin/delete/<username>')
def lab2_5c_delete(username):
    logged_in_user = session.get('lab2_5c_user')
    if logged_in_user != 'system_root': return "Unauthorized", 401
    
    if username == 'researcher':
        return render_template('lab2/sub5_c_admin.html', 
                               success=True, msg="Subject 'researcher' de-provisioned successfully.",
                               flag=get_random_flag('lab2_5', variation='variation_C'),
                               users=[{'id': 'analyst', 'role': 'Analyst'}])
    return redirect(url_for('lab2_5c_admin'))

@app.route('/lab2/5c/logout')
def lab2_5c_logout():
    session.pop('lab2_5c_user', None)
    return redirect(url_for('lab2_5c'))

# End Lab 2


# -------------------------
# LAB 3: Authentication
# -------------------------
@app.route('/lab3')
def lab3():
    return render_template('lab3/index.html')

# LAB 3.1: Brute Force Attack Menu
@app.route('/lab3/1/menu')
def lab3_1_menu():
    return render_template('lab3/menu.html')

# LAB 3.1.1: Username Enumeration via Different Responses
@app.route('/lab3/1')
def lab3_1():
    import random
    # Always randomize targets on index load for dynamic missions
    try:
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        user_path = os.path.join(base_dir, 'data', 'wordlists', 'usernames.txt')
        pass_path = os.path.join(base_dir, 'data', 'wordlists', 'passwords.txt')
        with open(user_path, 'r') as f:
            usernames = [line.strip() for line in f if line.strip()]
        with open(pass_path, 'r') as f:
            passwords = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"[ERROR] Failed to load wordlists: {e}")
        usernames = ['vault_admin', 'res_admin', 'security']
        passwords = ['security2025', 'access_granted', 'admin123']

    session['lab3_1_target_user'] = random.choice(usernames)
    session['lab3_1_target_pass'] = random.choice(passwords)
    
    print(f"\n[SECURITY] Lab 3.1 Active Targets -> User: {session.get('lab3_1_target_user')} | Pass: {session.get('lab3_1_target_pass')}")
    
    error = request.args.get('error')
    
    # Products for the template
    products = [
        {'id': 1, 'name': 'Sentinel Firewall Pro', 'price': 899, 'image': 'firewall.png', 'desc': 'Enterprise-grade packet filtering and deep inspection.'},
        {'id': 2, 'name': 'Vault Crypt-Node', 'price': 1200, 'image': 'vault.png', 'desc': 'Quantum-safe cryptographic storage for sensitive assets.'}
    ]
    return render_template('lab3/sub1.html', products=products, error=error)


@app.route('/lab3/1/login', methods=['GET', 'POST'])
def lab3_1_login():
    if request.method == 'GET': return redirect(url_for('lab3_1'))
    
    username = request.form.get('username')
    password = request.form.get('password')
    
    target_user = session.get('lab3_1_target_user', 'admin')
    target_pass = session.get('lab3_1_target_pass', 'password123')
    print(f"[SECURITY] Lab 3.1 Login Attempt -> {username}:{password}")
    
    # SUCCESS: Correct Credentials (302 Redirect)
    if username == target_user and password == target_pass:
        session['lab3_1_logged_in'] = True
        session['lab3_1_username'] = username
        return redirect(url_for('lab3_1_admin'))

    # VULNERABILITY: Username Enumeration via Different Responses
    if username == target_user:
        # User exists, but password was wrong
        return render_template('lab3/sub1.html', 
                             products=[{'id': 1, 'name': 'Sentinel Firewall Pro', 'price': 899}], 
                             error="Incorrect password.",
                             login_open=True), 200

    # User does NOT exist
    return render_template('lab3/sub1.html', 
                         products=[{'id': 1, 'name': 'Sentinel Firewall Pro', 'price': 899}], 
                         error="Invalid username",
                         login_open=True), 200

@app.route('/lab3/1/admin')
def lab3_1_admin():
    if not session.get('lab3_1_logged_in'):
        return redirect(url_for('lab3_1'))
    
    users = [{'username': 'staff_alpha', 'role': 'user'}, {'username': 'staff_beta', 'role': 'user'}]
    admin_user = session.get('lab3_1_username', 'admin')
    
    return render_template('lab3/sub1_admin.html', 
                         users=users, 
                         admin_username=admin_user,
                         variant='1',
                         flag=None)

@app.route('/lab3/1/admin/delete', methods=['POST'])
def lab3_1_delete_user():
    if not session.get('lab3_1_logged_in'):
        return redirect(url_for('lab3_1'))
    
    # Show flag after deletion
    admin_user = session.get('lab3_1_username', 'admin')
    return render_template('lab3/sub1_admin.html', 
                         users=[], 
                         admin_username=admin_user,
                         variant='1',
                         flag=get_random_flag('lab3_1'))

# LAB 3.1.2: Brute Force Attack - Luxury Variant
@app.route('/lab3/1/2')
def lab3_1_2():
    import random
    # Always randomize targets on index load for dynamic missions
    try:
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        user_path = os.path.join(base_dir, 'data', 'wordlists', 'usernames.txt')
        pass_path = os.path.join(base_dir, 'data', 'wordlists', 'passwords.txt')
        with open(user_path, 'r') as f:
            usernames = [line.strip() for line in f if line.strip()]
        with open(pass_path, 'r') as f:
            passwords = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"[ERROR] Failed to load wordlists: {e}")
        usernames = ['prestige_vip', 'elite_user', 'chairman']
        passwords = ['luxury_safe', 'diamond_pass', 'fishing']

    session['lab3_1_2_target_user'] = random.choice(usernames)
    session['lab3_1_2_target_pass'] = random.choice(passwords)
    
    print(f"\n[SECURITY] Lab 3.1.2 Active Targets -> User: {session.get('lab3_1_2_target_user')} | Pass: {session.get('lab3_1_2_target_pass')}")
    
    # Products for the template
    products = [
        {'id': 11, 'name': 'Gold Plated Server', 'price': 5000, 'image': 'prod_3.png'},
        {'id': 12, 'name': 'Diamond Encrypted Hub', 'price': 8000, 'image': 'prod_4.png'}
    ]
    return render_template('lab3/sub1_b.html', products=products)

@app.route('/lab3/1/2/login', methods=['POST'])
def lab3_1_2_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    target_user = session.get('lab3_1_2_target_user')
    target_pass = session.get('lab3_1_2_target_pass')
    print(f"[SECURITY] Lab 3.1.2 Login Attempt -> {username}:{password}")
    
    if username == target_user and password == target_pass:
        session['lab3_1_2_logged_in'] = True
        session['lab3_1_2_username'] = username
        return redirect(url_for('lab3_1_2_admin'))

    if username == target_user:
        # User exists, but password was wrong
        return render_template('lab3/sub1_b.html', 
                             products=[{'id': 11, 'name': 'Gold Plated Server', 'price': 5000}], 
                             error="Incorrect password.",
                             login_open=True), 200

    # User does NOT exist
    return render_template('lab3/sub1_b.html', 
                         products=[{'id': 11, 'name': 'Gold Plated Server', 'price': 5000}], 
                         error="Invalid username",
                         login_open=True), 200

@app.route('/lab3/1/2/admin')
def lab3_1_2_admin():
    if not session.get('lab3_1_2_logged_in'):
        return redirect(url_for('lab3_1_2'))
    
    users = [{'username': 'vip_alpha', 'role': 'user'}, {'username': 'vip_beta', 'role': 'user'}]
    admin_user = session.get('lab3_1_2_username', 'admin')
    
    return render_template('lab3/sub1_admin.html', 
                         users=users, 
                         admin_username=admin_user,
                         variant='2',
                         flag=None)

@app.route('/lab3/1/2/admin/delete', methods=['POST'])
def lab3_1_2_delete_user():
    if not session.get('lab3_1_2_logged_in'):
        return redirect(url_for('lab3_1_2'))
    
    admin_user = session.get('lab3_1_2_username', 'admin')
    return render_template('lab3/sub1_admin.html', 
                         users=[], 
                         admin_username=admin_user,
                         variant='2',
                         flag=get_random_flag('lab3_1'))

@app.route('/lab3/1/2/logout')
def lab3_1_2_logout():
    session.pop('lab3_1_2_logged_in', None)
    session.pop('lab3_1_2_username', None)
    return redirect(url_for('lab3_1_2'))

# LAB 3.1.3: Brute Force Attack - Corporate Variant
@app.route('/lab3/1/3')
def lab3_1_3():
    import random
    # Always randomize targets on index load for dynamic missions
    try:
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        user_path = os.path.join(base_dir, 'data', 'wordlists', 'usernames.txt')
        pass_path = os.path.join(base_dir, 'data', 'wordlists', 'passwords.txt')
        with open(user_path, 'r') as f:
            usernames = [line.strip() for line in f if line.strip()]
        with open(pass_path, 'r') as f:
            passwords = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"[ERROR] Failed to load wordlists: {e}")
        usernames = ['corp_root', 'system_cfo', 'ceo']
        passwords = ['enterprise_access', 'vault_secure', 'corporate2024']

    session['lab3_1_3_target_user'] = random.choice(usernames)
    session['lab3_1_3_target_pass'] = random.choice(passwords)

    print(f"\n[SECURITY] Lab 3.1.3 Active Targets -> User: {session.get('lab3_1_3_target_user')} | Pass: {session.get('lab3_1_3_target_pass')}")
    
    # Products for the template
    products = [
        {'id': 21, 'name': 'Enterprise Firewall', 'price': 12000, 'image': 'prod_5.png'},
        {'id': 22, 'name': 'Corporate VPN Bridge', 'price': 4500, 'image': 'prod_6.png'}
    ]
    return render_template('lab3/sub1_c.html', products=products)

@app.route('/lab3/1/3/login', methods=['POST'])
def lab3_1_3_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    target_user = session.get('lab3_1_3_target_user')
    target_pass = session.get('lab3_1_3_target_pass')
    print(f"[SECURITY] Lab 3.1.3 Login Attempt -> {username}:{password}")
    
    if username == target_user and password == target_pass:
        session['lab3_1_3_logged_in'] = True
        session['lab3_1_3_username'] = username
        return redirect(url_for('lab3_1_3_admin'))

    if username == target_user:
        # User exists, but password was wrong
        return render_template('lab3/sub1_c.html', 
                             products=[{'id': 21, 'name': 'Enterprise Firewall', 'price': 12000}], 
                             error="Incorrect password.",
                             login_open=True), 200

    # User does NOT exist
    return render_template('lab3/sub1_c.html', 
                         products=[{'id': 21, 'name': 'Enterprise Firewall', 'price': 12000}], 
                         error="Invalid username",
                         login_open=True), 200

@app.route('/lab3/1/3/admin')
def lab3_1_3_admin():
    if not session.get('lab3_1_3_logged_in'):
        return redirect(url_for('lab3_1_3'))
    
    users = [{'username': 'corp_alpha', 'role': 'user'}, {'username': 'corp_beta', 'role': 'user'}]
    admin_user = session.get('lab3_1_3_username', 'admin')
    
    return render_template('lab3/sub1_admin.html', 
                         users=users, 
                         admin_username=admin_user,
                         variant='3',
                         flag=None)

@app.route('/lab3/1/3/admin/delete', methods=['POST'])
def lab3_1_3_delete_user():
    if not session.get('lab3_1_3_logged_in'):
        return redirect(url_for('lab3_1_3'))
    
    admin_user = session.get('lab3_1_3_username', 'admin')
    return render_template('lab3/sub1_admin.html', 
                         users=[], 
                         admin_username=admin_user,
                         variant='3',
                         flag=get_random_flag('lab3_1', variation='variation_C'))

@app.route('/lab3/1/3/logout')
def lab3_1_3_logout():
    session.pop('lab3_1_3_logged_in', None)
    session.pop('lab3_1_3_username', None)
    return redirect(url_for('lab3_1_3'))

@app.route('/lab3/1/logout')
def lab3_1_logout():
    session.pop('lab3_1_logged_in', None)
    session.pop('lab3_1_username', None)
    return redirect(url_for('lab3_1'))


# LAB 3.2: 2FA Bypass - Menu
@app.route('/lab3/2/menu')
def lab3_2_menu():
    return render_template('lab3/sub2_menu.html')

# LAB 3.2A: 2FA Bypass - SecureShop (Original)
@app.route('/lab3/2')
def lab3_2():
    # Clear any existing session
    session.pop('lab3_2_username', None)
    session.pop('lab3_2_verified', None)
    
    # Simulated Inventory Registry
    products = [
        {'id': 1, 'name': 'Biometric Shield', 'price': 120},
        {'id': 2, 'name': 'Quantum Key', 'price': 500}
    ]
    return render_template('lab3/sub2.html', products=products)

@app.route('/lab3/2/login', methods=['POST'])
def lab3_2_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Hardcoded credentials
    valid_users = {
        'wiener': 'peter',
        'carlos': 'montoya'
    }
    
    if username in valid_users and valid_users[username] == password:
        # Store username in session but NOT verified status
        session['lab3_2_username'] = username
        
        # Generate 2FA code (4 digits)
        import random
        code = str(random.randint(1000, 9999))
        session['lab3_2_code'] = code
        print(f"[SECURITY] Lab 3.2A 2FA generated for {username}: {code}")
        
        # Redirect to 2FA verification page
        return redirect(url_for('lab3_2_verify'))
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/lab3/2/email')
def lab3_2_email():
    username = session.get('lab3_2_username', 'anonymous')
    code = session.get('lab3_2_code', '0000')
    
    # LOCK: If user is carlos (the victim), we don't have access to their email!
    locked = True if username == 'carlos' else False
    
    return render_template('lab3/email_client.html', 
                         username=username, 
                         code=code, 
                         lab_title="SecureShop",
                         locked=locked)

@app.route('/lab3/2/verify')
def lab3_2_verify():
    username = session.get('lab3_2_username')
    if not username:
        return redirect(url_for('lab3_2'))
    
    code = session.get('lab3_2_code', '0000')
    return render_template('lab3/sub2_verify.html', username=username, code=code)

@app.route('/lab3/2/verify', methods=['POST'])
def lab3_2_verify_post():
    username = session.get('lab3_2_username')
    if not username:
        return redirect(url_for('lab3_2'))
    
    submitted_code = request.form.get('code')
    correct_code = session.get('lab3_2_code')
    
    if submitted_code == correct_code:
        # Mark as verified
        session['lab3_2_verified'] = True
        return redirect(url_for('lab3_2_account'))
    else:
        return render_template('lab3/sub2_verify.html', 
                             username=username, 
                             code=session.get('lab3_2_code', '0000'),
                             error='Invalid verification code')

@app.route('/lab3/2/my-account')
def lab3_2_account():
    username = session.get('lab3_2_username')
    
    # VULNERABILITY: Only checks if username exists in session
    # Does NOT check if 2FA was completed (lab3_2_verified)
    if not username:
        return redirect(url_for('lab3_2'))
    
    # Check if this is carlos (victim) and 2FA was bypassed
    verified = session.get('lab3_2_verified', False)
    flag = None
    
    # Lab is solved if we successfully access carlos's account without 2FA verification
    if username == 'carlos' and not verified:
        flag = get_random_flag('lab3_2')
        print(f"[SECURITY] Lab 3.2A Bypass Detected -> User: {username} | Flag: {flag}")
    
    return render_template('lab3/sub2_account.html', 
                         username=username,
                         verified=verified,
                         flag=flag,
                         lab_id='3.2.A',
                         lab_title="SecureShop")

@app.route('/lab3/2/logout')
def lab3_2_logout():
    session.pop('lab3_2_username', None)
    session.pop('lab3_2_verified', None)
    session.pop('lab3_2_code', None)
    return redirect(url_for('lab3_2'))


# LAB 3.2B: 2FA Bypass - BankSecure (Variation B)
@app.route('/lab3/2b')
def lab3_2b():
    session.pop('lab3_2b_username', None)
    session.pop('lab3_2b_verified', None)
    return render_template('lab3/sub2b.html')

@app.route('/lab3/2b/login', methods=['POST'])
def lab3_2b_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    valid_users = {'alice': 'alice123', 'bob': 'bob456'}
    
    if username in valid_users and valid_users[username] == password:
        session['lab3_2b_username'] = username
        code = str(random.randint(1000, 9999))
        session['lab3_2b_code'] = code
        print(f"[SECURITY] Lab 3.2B 2FA generated for {username}: {code}")
        return redirect(url_for('lab3_2b_verify'))
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/lab3/2b/email')
def lab3_2b_email():
    username = session.get('lab3_2b_username', 'anonymous')
    code = session.get('lab3_2b_code', '0000')
    
    # LOCK: If user is bob (the victim), we don't have access to their email!
    locked = True if username == 'bob' else False
    
    return render_template('lab3/email_client.html', 
                         username=username, 
                         code=code, 
                         lab_title="BankSecure",
                         locked=locked)

@app.route('/lab3/2b/verify')
def lab3_2b_verify():
    username = session.get('lab3_2b_username')
    if not username:
        return redirect(url_for('lab3_2b'))
    code = session.get('lab3_2b_code', '0000')
    return render_template('lab3/sub2b_verify.html', username=username, code=code, variation='B')

@app.route('/lab3/2b/verify', methods=['POST'])
def lab3_2b_verify_post():
    username = session.get('lab3_2b_username')
    if not username:
        return redirect(url_for('lab3_2b'))
    
    submitted_code = request.form.get('code')
    correct_code = session.get('lab3_2b_code')
    
    if submitted_code == correct_code:
        session['lab3_2b_verified'] = True
        return redirect(url_for('lab3_2b_account'))
    else:
        return render_template('lab3/sub2b_verify.html', 
                             username=username, 
                             code=session.get('lab3_2b_code', '0000'),
                             variation='B',
                             error='Invalid verification code')

@app.route('/lab3/2b/dashboard')
def lab3_2b_account():
    username = session.get('lab3_2b_username')
    if not username:
        return redirect(url_for('lab3_2b'))
    
    verified = session.get('lab3_2b_verified', False)
    flag = None
    
    # Lab is solved if we successfully access bob's account without 2FA
    if username == 'bob' and not verified:
        flag = get_random_flag('lab3_2')
        print(f"[SECURITY] Lab 3.2B Bypass Detected -> User: {username} | Flag: {flag}")
    
    return render_template('lab3/sub2b_account.html', 
                         username=username,
                         verified=verified,
                         flag=flag,
                         lab_id='3.2.B',
                         lab_title="BankSecure")

@app.route('/lab3/2b/logout')
def lab3_2b_logout():
    session.pop('lab3_2b_username', None)
    session.pop('lab3_2b_verified', None)
    session.pop('lab3_2b_code', None)
    return redirect(url_for('lab3_2b'))


# LAB 3.2C: 2FA Bypass - CloudDrive (Variation C)
@app.route('/lab3/2c')
def lab3_2c():
    session.pop('lab3_2c_username', None)
    session.pop('lab3_2c_verified', None)
    return render_template('lab3/sub2c.html')

@app.route('/lab3/2c/login', methods=['POST'])
def lab3_2c_login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    valid_users = {'user1': 'pass1', 'admin': 'admin2024'}
    
    if username in valid_users and valid_users[username] == password:
        session['lab3_2c_username'] = username
        code = str(random.randint(1000, 9999))
        session['lab3_2c_code'] = code
        print(f"[SECURITY] Lab 3.2C 2FA generated for {username}: {code}")
        return redirect(url_for('lab3_2c_verify'))
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/lab3/2c/email')
def lab3_2c_email():
    username = session.get('lab3_2c_username', 'anonymous')
    code = session.get('lab3_2c_code', '0000')
    
    # LOCK: If user is admin (the victim), we don't have access to their email!
    locked = True if username == 'admin' else False
    
    return render_template('lab3/email_client.html', 
                         username=username, 
                         code=code, 
                         lab_title="CloudDrive",
                         locked=locked)

@app.route('/lab3/2c/verify')
def lab3_2c_verify():
    username = session.get('lab3_2c_username')
    if not username:
        return redirect(url_for('lab3_2c'))
    code = session.get('lab3_2c_code', '0000')
    return render_template('lab3/sub2c_verify.html', username=username, code=code, variation='C')

@app.route('/lab3/2c/verify', methods=['POST'])
def lab3_2c_verify_post():
    username = session.get('lab3_2c_username')
    if not username:
        return redirect(url_for('lab3_2c'))
    
    submitted_code = request.form.get('code')
    correct_code = session.get('lab3_2c_code')
    
    if submitted_code == correct_code:
        session['lab3_2c_verified'] = True
        return redirect(url_for('lab3_2c_account'))
    else:
        return render_template('lab3/sub2c_verify.html', 
                             username=username, 
                             code=session.get('lab3_2c_code', '0000'),
                             variation='C',
                             error='Invalid verification code')

@app.route('/lab3/2c/files')
def lab3_2c_account():
    username = session.get('lab3_2c_username')
    if not username:
        return redirect(url_for('lab3_2c'))
    
    verified = session.get('lab3_2c_verified', False)
    flag = None
    
    # Lab is solved if we successfully access admin's account without 2FA
    if username == 'admin' and not verified:
        flag = get_random_flag('lab3_2')
        print(f"[SECURITY] Lab 3.2C Bypass Detected -> User: {username} | Flag: {flag}")
    
    return render_template('lab3/sub2c_account.html', 
                         username=username,
                         verified=verified,
                         flag=flag,
                         lab_id='3.2.C',
                         lab_title="CloudDrive")

@app.route('/lab3/2c/logout')
def lab3_2c_logout():
    session.pop('lab3_2c_username', None)
    session.pop('lab3_2c_verified', None)
    session.pop('lab3_2c_code', None)
    return redirect(url_for('lab3_2c'))



# -------------------------
# LAB 4: SSRF
# -------------------------

@app.route('/lab4')
def lab4():
    return render_template('lab4/index.html')

# Lab 4.1: Basic SSRF Selection Menu
@app.route('/lab4/1')
@login_required
def lab4_1():
    return render_template('lab4/sub1_menu.html')

# Lab 4.1.A: Retail Store
@app.route('/lab4/1/a')
@login_required
def lab4_1a():
    products = [
        {'id': 1, 'name': 'Vulnerable T-Shirt', 'description': 'Limited edition vulnerable item.', 'price': 29.99, 'image': 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=600&q=80'},
        {'id': 2, 'name': 'Insecure Hoodie', 'description': 'Keeps you warm, keeps your data exposed.', 'price': 49.99, 'image': 'https://images.unsplash.com/photo-1556821840-3a63f95609a7?auto=format&fit=crop&w=600&q=80'},
        {'id': 3, 'name': 'SQLi Mug', 'description': 'Select * from drinks.', 'price': 15.00, 'image': 'https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?auto=format&fit=crop&w=600&q=80'},
        {'id': 4, 'name': 'Smart Watch X', 'description': 'Tracks your location... everywhere.', 'price': 199.99, 'image': 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&q=80'},
        {'id': 5, 'name': 'Urban Backpack', 'description': 'Fits all your stolen secrets.', 'price': 89.50, 'image': 'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=600&q=80'},
        {'id': 6, 'name': 'Running Sneakers', 'description': 'Run away from security audits.', 'price': 120.00, 'image': 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=600&q=80'}
    ]
    return render_template('lab4/sub1.html', products=products)

@app.route('/lab4/1/a/product/<int:product_id>')
@login_required
def lab4_1a_product(product_id):
    products = [
        {'id': 1, 'name': 'Vulnerable T-Shirt', 'description': 'Limited edition vulnerable item.', 'price': 29.99, 'image': 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=600&q=80'},
        {'id': 2, 'name': 'Insecure Hoodie', 'description': 'Keeps you warm, keeps your data exposed.', 'price': 49.99, 'image': 'https://images.unsplash.com/photo-1556821840-3a63f95609a7?auto=format&fit=crop&w=600&q=80'},
        {'id': 3, 'name': 'SQLi Mug', 'description': 'Select * from drinks.', 'price': 15.00, 'image': 'https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?auto=format&fit=crop&w=600&q=80'},
        {'id': 4, 'name': 'Smart Watch X', 'description': 'Tracks your location... everywhere.', 'price': 199.99, 'image': 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&q=80'},
        {'id': 5, 'name': 'Urban Backpack', 'description': 'Fits all your stolen secrets.', 'price': 89.50, 'image': 'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=600&q=80'},
        {'id': 6, 'name': 'Running Sneakers', 'description': 'Run away from security audits.', 'price': 120.00, 'image': 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=600&q=80'}
    ]
    product = next((p for p in products if p['id'] == product_id), None)
    if not product: return "Product not found", 404
    return render_template('lab4/sub1_product.html', product=product)

@app.route('/lab4/1/a/stock', methods=['POST'])
@login_required
def lab4_1a_stock():
    stock_api = extract_stock_api_param()
    return process_ssrf_request(stock_api, variant_hint='a')


def extract_stock_api_param():
    """Read stockApi from common request payload shapes used by browsers/tools."""
    # Standard form submissions
    for key in ('stockApi', 'stock_api', 'stockapi', 'url', 'targetUrl'):
        value = request.form.get(key)
        if value:
            return value

    # JSON payload support for API clients / proxy tools
    json_payload = request.get_json(silent=True)
    if isinstance(json_payload, dict):
        for key in ('stockApi', 'stock_api', 'stockapi', 'url', 'targetUrl'):
            value = json_payload.get(key)
            if value:
                return value

    # Query-string fallback (last resort)
    for key in ('stockApi', 'stock_api', 'stockapi', 'url', 'targetUrl'):
        value = request.args.get(key)
        if value:
            return value

    return None


def process_ssrf_request(stock_api, variant_hint='a'):
    if not stock_api:
        return "Missing stockApi parameter", 400

    # Normalize variant context so A/B/C paths always propagate correctly.
    normalized_variant = str(variant_hint or '').strip().lower()
    if normalized_variant not in {'a', 'b', 'c'}:
        path_variant_match = re.search(r'/lab4/1/([abc])/', request.path.lower())
        normalized_variant = path_variant_match.group(1) if path_variant_match else 'a'
    
    # VULNERABILITY: SSRF
    try:
        # Simulation: Allow the researcher to use the actual URL or mock internal domains.
        # We handle internal routing via the Flask Test Client to ensure Vercel/stateless compatibility.
        current_host = request.host
        mock_domains = ["stock.secureshop.local", "inventory.banksecure.local", "fleet.clouddrive.local"]
        
        is_target_internal = any(domain in stock_api for domain in mock_domains) or \
                            current_host in stock_api or "localhost" in stock_api or "127.0.0.1" in stock_api
                            
        if is_target_internal:
            # Reconstruct the path for internal dispatch
            import re
            # Extract the path and query string from the stock_api
            match = re.search(r'https?://[^/]+(/.+)', stock_api)
            full_path = match.group(1) if match else "/"
            
            target_path = full_path.split('?')[0]
            query_params = full_path.split('?')[1] if '?' in full_path else ""

            internal_full_path = target_path
            if query_params:
                internal_full_path += "?" + query_params
            
            # DISPATCH: Use Flask test client to fetch internal routes (Vercel-Friendly)
            # We forward cookies and a specialized ID header for dynamic flag generation
            print(f"[SECURITY] SSRF Internal Dispatch -> Path: {internal_full_path}")
            headers_dict = {key: value for key, value in request.headers.items() if key.lower() != 'cookie'}
            
            # Extract current researcher identity and TARGET HOST to pass through the internal bridge
            import urllib.parse
            parsed_url = urllib.parse.urlparse(stock_api)
            target_host = parsed_url.netloc
            
            guid = session.get('guid') or session.get('user_id')
            if guid:
                headers_dict['X-SSRF-Researcher-GUID'] = str(guid)

            # Explicit marker for internal SSRF bridge requests. This avoids
            # false 403s on hosted environments where request.host/remote_addr
            # may not look like loopback even during internal dispatch.
            headers_dict['X-Internal-Dispatch'] = '1'
            
            # Forward the original target host to help the backend identify the industry variant
            headers_dict['X-SSRF-Target-Host'] = target_host
            headers_dict['X-Lab4-Variant'] = normalized_variant
            
            with app.test_client() as client:
                # Forward each cookie individually to the test client using keyword arguments
                for cookie_key, cookie_value in request.cookies.items():
                    client.set_cookie(key=cookie_key, value=cookie_value)
                
                resp = client.get(internal_full_path, headers=headers_dict)
                return resp.get_data(as_text=True)
        
        else:
            # Avoid real private-network egress for Lab 4.2 simulation payloads.
            try:
                parsed_for_guard = urllib.parse.urlparse(stock_api)
                guard_host = (parsed_for_guard.hostname or '').strip().lower()
                guard_port = parsed_for_guard.port if parsed_for_guard.port is not None else 80
                if re.fullmatch(r'192\.168\.0\.\d{1,3}', guard_host) and guard_port == 8080:
                    return (
                        "<h1>Simulation Notice</h1>"
                        "<p>192.168.0.X:8080 targets are simulated in Lab 4.2 routes only.</p>"
                        "<p>Use /lab4/2/a/stock, /lab4/2/b/stock, or /lab4/2/c/stock for blind SSRF discovery.</p>"
                    ), 400
            except Exception:
                pass

            # External Request (Simulation)
            # In a real environment, this makes the server a proxy.
            # Using requests here is fine for external targets (if allowed)
            resp = requests.get(stock_api, timeout=5)
            print(f"[SECURITY] External SSRF Request -> URL: {stock_api}")
            return resp.text
            
    except Exception as e:
        return f"Internal Server Error: {str(e)}", 500

# Lab 4.1 Menu
@app.route('/lab4/1/menu')
def lab4_1_menu():
    return render_template('lab4/sub1_menu.html')

# Update Lab 4.1 (Variation A) to use new template if needed, or just keep as is.
# The user asked to "Restructure all follow Lab2 Structure".
# In Lab 2, /lab2/1 is Variation A. We already have this.

# Helper for Lab 4.1c (Logistics)
def get_lab4_1c_products():
    return [
        {'id': 201, 'name': 'Container 40ft High Cube', 'description': 'Refrigerated transport unit. Origin: Shanghai.', 'price': 3500, 'image': 'https://images.unsplash.com/photo-1494412651409-ae1c4027d164?auto=format&fit=crop&w=600&q=80'},
        {'id': 202, 'name': 'IoT Sensor Array', 'description': 'Real-time GPS and humidity tracking module.', 'price': 450, 'image': 'https://images.unsplash.com/photo-1566576912906-253c723f03b5?auto=format&fit=crop&w=600&q=80'},
        {'id': 203, 'name': 'Automated Forklift Drone', 'description': 'Warehouse autonomous vehicle.', 'price': 15000, 'image': 'https://images.unsplash.com/photo-1506543730537-8051c72f778d?auto=format&fit=crop&w=600&q=80'},
        {'id': 204, 'name': 'Deep Sea Buoy', 'description': 'Weather monitoring station.', 'price': 8000, 'image': 'https://images.unsplash.com/photo-1518114674381-893bd558a27d?auto=format&fit=crop&w=600&q=80'},
        {'id': 205, 'name': 'Automated Warehouse System', 'description': 'Full stack inventory robotics.', 'price': 45000, 'image': 'https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=600&q=80'},
        {'id': 206, 'name': 'Cargo Ship Transport', 'description': 'Heavy lift vessel capacity slot.', 'price': 12000, 'image': 'https://images.unsplash.com/photo-1601584115197-04ecc0da31d7?auto=format&fit=crop&w=600&q=80'},
        {'id': 207, 'name': 'Logistics Truck Fleet', 'description': 'Last mile delivery unit.', 'price': 85000, 'image': 'https://images.unsplash.com/photo-1578575437130-527eed3abbec?auto=format&fit=crop&w=600&q=80'},
        {'id': 208, 'name': 'Industrial Control Panel', 'description': 'SCADA interface for facility management.', 'price': 2500, 'image': 'https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=600&q=80'}
    ]


# Dummy Stock Check API for realism
@app.route('/stock/check')
def stock_check_api():
    product_id = request.args.get('id')
    return f"Success: {random.randint(10, 100)} units available for Item-{product_id}."

# Simulated External Admin for 4.1
@app.route('/admin')
def ssrf_admin_panel():
    # SSRF Gate: Only accessible via internal loopback (127.0.0.1)
    is_internal = (
        request.remote_addr == '127.0.0.1'
        or 'localhost' in request.host
        or request.headers.get('X-Internal-Dispatch') == '1'
    )
    
    if not is_internal:
        print(f"[SECURITY] Unauthorized access attempt to /admin from {request.remote_addr} blocked.")
        return "<h1>403 Forbidden</h1><p>Admin interface only accessible from local network.</p>", 403
    
    # Identify the mock domain based on context (for realism in the HTML response)
    mock_host = request.host if "local" in request.host else "stock.secureshop.local"
    
    return render_template('lab4/admin_panel.html', 
                         user_to_delete="carlos",
                         mock_host=mock_host)

@app.route('/admin/delete')
def ssrf_admin_delete_user():
    # SSRF Gate: Ensure this action is only performed by the server itself
    is_internal = (
        request.remote_addr == '127.0.0.1'
        or 'localhost' in request.host
        or request.headers.get('X-Internal-Dispatch') == '1'
    )
    
    if not is_internal:
        return "403 Forbidden", 403
        
    username = request.args.get('username')
    if username == "carlos":
        # Context-aware variation detection for dynamic flag synchronization
        # Matches the canonical Lab 4 variations: A (Retail), B (Cloud), C (Logistics)
        # We check the forwarded 'X-SSRF-Target-Host' since the actual 'request.host' is localhost.
        target_host = request.headers.get('X-SSRF-Target-Host', '').lower()
        variant_hint = request.headers.get('X-Lab4-Variant', 'a').lower()

        variation = 'variation_A'
        if variant_hint == 'b' or 'inventory.banksecure.local' in target_host:
            variation = 'variation_B'
        elif variant_hint == 'c' or 'fleet.clouddrive.local' in target_host:
            variation = 'variation_C'
            
        # Dynamic flag generation using the forwarded session identity
        # Use canonical 'lab4' ID to match the Submission Center registry
        flag = get_random_flag('lab4', variation=variation)
        print(f"[SECURITY] SSRF Exploited! Admin deleted user: {username} | Flag: {flag}")
        return f"<h1>Success</h1><p>User {username} deleted successfully!</p><div style='padding:20px; background:#10b981; color:white; border-radius:8px; margin-top:20px;'><strong>FLAG:</strong> {flag}</div>"
    
    return f"User {username} not found."



# Lab 4.1.B: Cloud Infrastructure
@app.route('/lab4/1/b')
@login_required
def lab4_1b():
    products = [
        {'id': 50, 'name': 'GPU Cluster Node', 'description': 'High-performance compute node for AI.', 'price': 12000.00, 'image': 'https://images.unsplash.com/photo-1591405351990-4726e331f141?auto=format&fit=crop&w=600&q=80'},
        {'id': 51, 'name': 'Nitro SSD Array', 'description': 'Ultra-low latency storage.', 'price': 3500.00, 'image': 'https://images.unsplash.com/photo-1597852064821-d928444c0620?auto=format&fit=crop&w=600&q=80'},
        {'id': 52, 'name': 'Quantum Link', 'description': 'Entangled communication gateway.', 'price': 50000.00, 'image': 'https://images.unsplash.com/photo-1509023467864-1ecbb3f6342e?auto=format&fit=crop&w=600&q=80'}
    ]
    return render_template('lab4/sub1_b.html', products=products)

@app.route('/lab4/1/b/product/<int:product_id>')
@login_required
def lab4_1b_product(product_id):
    products = [
        {'id': 50, 'name': 'GPU Cluster Node', 'description': 'High-performance compute node for AI.', 'price': 12000.00, 'image': 'https://images.unsplash.com/photo-1591405351990-4726e331f141?auto=format&fit=crop&w=600&q=80'},
        {'id': 51, 'name': 'Nitro SSD Array', 'description': 'Ultra-low latency storage.', 'price': 3500.00, 'image': 'https://images.unsplash.com/photo-1597852064821-d928444c0620?auto=format&fit=crop&w=600&q=80'},
        {'id': 52, 'name': 'Quantum Link', 'description': 'Entangled communication gateway.', 'price': 50000.00, 'image': 'https://images.unsplash.com/photo-1509023467864-1ecbb3f6342e?auto=format&fit=crop&w=600&q=80'}
    ]
    product = next((p for p in products if p['id'] == product_id), None)
    if not product: return "Node not found", 404
    return render_template('lab4/sub1_b_product.html', product=product)

@app.route('/lab4/1/b/stock', methods=['POST'])
@login_required
def lab4_1b_stock():
    stock_api = extract_stock_api_param()
    return process_ssrf_request(stock_api, variant_hint='b')

# Lab 4.1.C: Global Logistics
@app.route('/lab4/1/c')
@login_required
def lab4_1c():
    products = [
        {'id': 101, 'name': 'Container A-99', 'description': 'Standard 20ft Cargo Container.', 'price': 2500.00, 'image': 'https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=600&q=80'},
        {'id': 102, 'name': 'Refrigerated Unit', 'description': 'Sub-zero logistics module.', 'price': 4500.00, 'image': 'https://images.unsplash.com/photo-1494412574743-01927c44267e?auto=format&fit=crop&w=600&q=80'},
        {'id': 103, 'name': 'Hazardous Mat-Cell', 'description': 'Shielded transport for dangerous goods.', 'price': 8000.00, 'image': 'https://images.unsplash.com/photo-1580674285054-bed31e145f59?auto=format&fit=crop&w=600&q=80'}
    ]
    return render_template('lab4/sub1_c.html', products=products)

@app.route('/lab4/1/c/product/<int:product_id>')
@login_required
def lab4_1c_product(product_id):
    products = [
        {'id': 101, 'name': 'Container A-99', 'description': 'Standard 20ft Cargo Container.', 'price': 2500.00, 'image': 'https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?auto=format&fit=crop&w=600&q=80'},
        {'id': 102, 'name': 'Refrigerated Unit', 'description': 'Sub-zero logistics module.', 'price': 4500.00, 'image': 'https://images.unsplash.com/photo-1494412574743-01927c44267e?auto=format&fit=crop&w=600&q=80'},
        {'id': 103, 'name': 'Hazardous Mat-Cell', 'description': 'Shielded transport for dangerous goods.', 'price': 8000.00, 'image': 'https://images.unsplash.com/photo-1580674285054-bed31e145f59?auto=format&fit=crop&w=600&q=80'}
    ]
    product = next((p for p in products if p['id'] == product_id), None)
    if not product: return "Unit not found", 404
    return render_template('lab4/sub1_c_product.html', product=product)

@app.route('/lab4/1/c/stock', methods=['POST'])
@login_required
def lab4_1c_stock():
    stock_api = extract_stock_api_param()
    return process_ssrf_request(stock_api, variant_hint='c')


# Lab 4.2: Blind SSRF Selection Menu
@app.route('/lab4/2')
@login_required
def lab4_2():
    return render_template('lab4/sub2_menu.html')


def get_lab4_2_identity_key():
    return (
        request.headers.get('X-SSRF-Researcher-GUID')
        or session.get('guid')
        or session.get('user_id')
        or request.remote_addr
        or 'anonymous-researcher'
    )


def get_lab4_2_target_ip(identity_key, variant='a'):
    """Return a stable per-identity, per-variant target octet (1..255)."""
    identity_value = str(identity_key or 'anonymous-researcher')
    variant_value = str(variant or 'a').strip().lower()
    if variant_value not in {'a', 'b', 'c'}:
        variant_value = 'a'

    # Deterministic mapping prevents target drift across serverless instances/cold starts.
    digest = hashlib.sha256(
        f"lab4_2|{identity_value}|{variant_value}|{app.secret_key}".encode('utf-8')
    ).hexdigest()
    return (int(digest[:8], 16) % 255) + 1


def log_lab4_2_target_ip(variant, context_label, session_key='lab4_2_logged_variants'):
    identity_key = get_lab4_2_identity_key()
    target_octet = get_lab4_2_target_ip(identity_key, variant)

    print(
        f"[LAB4.2] {context_label} | variant={variant.upper()} "
        f"| identity={identity_key} | target_ip=192.168.0.{target_octet}"
    )
    print(
        f"[LAB4.2][ALLOCATED_IP] variant={variant.upper()} "
        f"identity={identity_key} allocated_ip=192.168.0.{target_octet}"
    )
    return target_octet


def get_lab4_2_products(variant):
    product_catalogs = {
        'a': [
            {'id': 301, 'name': 'Vertex Running Jacket', 'description': 'Retail flagship apparel with live branch inventory telemetry.', 'price': 129.00, 'image': 'https://images.unsplash.com/photo-1523398002811-999ca8dec234?auto=format&fit=crop&w=900&q=80'},
            {'id': 302, 'name': 'Signal Trail Shoes', 'description': 'Regional stock dispatch item with same-day pickup routing.', 'price': 164.00, 'image': 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=80'},
            {'id': 303, 'name': 'Cache Sport Duffel', 'description': 'Warehouse-linked accessory synced through the stock gateway.', 'price': 86.00, 'image': 'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=900&q=80'}
        ],
        'b': [
            {'id': 401, 'name': 'Nebula Compute Slice', 'description': 'Cloud node package tracked through an internal provisioning network.', 'price': 6400.00, 'image': 'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=900&q=80'},
            {'id': 402, 'name': 'Aegis Edge Firewall', 'description': 'Managed edge appliance with hidden admin diagnostics endpoints.', 'price': 2890.00, 'image': 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=900&q=80'},
            {'id': 403, 'name': 'HyperVault Backup Pod', 'description': 'Resilient object-storage capsule connected to the stock API fabric.', 'price': 9750.00, 'image': 'https://images.unsplash.com/photo-1580894742597-87bc8789db3d?auto=format&fit=crop&w=900&q=80'}
        ],
        'c': [
            {'id': 501, 'name': 'HarborTrack Container', 'description': 'Port inventory unit monitored through a segregated operations subnet.', 'price': 7200.00, 'image': 'https://images.unsplash.com/photo-1578575437130-527eed3abbec?auto=format&fit=crop&w=900&q=80'},
            {'id': 502, 'name': 'PolarChain Reefer Pod', 'description': 'Cold-chain container with warehouse stock polling enabled.', 'price': 11950.00, 'image': 'https://images.unsplash.com/photo-1494412574643-ff11b0a5c1c3?auto=format&fit=crop&w=900&q=80'},
            {'id': 503, 'name': 'DockGrid Sensor Mesh', 'description': 'Shipment visibility hardware tied into the logistics control plane.', 'price': 2340.00, 'image': 'https://images.unsplash.com/photo-1517048676732-d65bc937f952?auto=format&fit=crop&w=900&q=80'}
        ]
    }
    return product_catalogs.get(variant, product_catalogs['a'])


def get_lab4_2_variant_context(variant):
    context = {
        'a': {
            'theme_class': 'theme-a',
            'title': 'Retail Branch Inventory',
            'subtitle': 'Blind SSRF via stock check gateway',
            'badge': 'Variation A',
            'persona': 'Arcade Avenue Outfitters',
            'exact_lab_id': 'lab4_2_a'
        },
        'b': {
            'theme_class': 'theme-b',
            'title': 'Cloud Capacity Exchange',
            'subtitle': 'Blind SSRF across internal admin hosts',
            'badge': 'Variation B',
            'persona': 'Nimbus Compute Marketplace',
            'exact_lab_id': 'lab4_2_b'
        },
        'c': {
            'theme_class': 'theme-c',
            'title': 'Logistics Control Catalog',
            'subtitle': 'Blind SSRF against back-end operations services',
            'badge': 'Variation C',
            'persona': 'Portline Freight Systems',
            'exact_lab_id': 'lab4_2_c'
        }
    }
    return context.get(variant, context['a'])


def build_lab4_2_stock_api(product_id):
    return f"http://192.168.0.1:8080/product/stock/check?productId={product_id}&storeId=1"


@app.route('/lab4/2/<variant>/admin-panel')
@login_required
def lab4_2_admin_panel(variant):
    variant_key = str(variant or '').strip().lower()
    if variant_key not in {'a', 'b', 'c'}:
        return "Variant not found", 404

    host_octet_raw = request.args.get('host_octet', '').strip()
    if not host_octet_raw.isdigit():
        return "Invalid host", 400

    host_octet = int(host_octet_raw)
    if host_octet < 1 or host_octet > 255:
        return "Invalid host", 400

    target_octet = get_lab4_2_target_ip(get_lab4_2_identity_key(), variant_key)
    if host_octet != target_octet:
        return "Admin interface unavailable for this host.", 404

    return render_template(
        'lab4/admin_v2_panel.html',
        host_ip=f"192.168.0.{host_octet}",
        user_to_delete='carlos',
        variant_context=get_lab4_2_variant_context(variant_key)
    )


def process_lab4_2_ssrf_request(stock_api, variant, expected_target_octet=None):
    if not stock_api:
        return "Missing stockApi parameter", 400

    try:
        import urllib.parse

        parsed = urllib.parse.urlparse(stock_api)
        host = (parsed.hostname or '').strip().lower()
        path = parsed.path or '/'
        query = urllib.parse.parse_qs(parsed.query)
        identity_key = get_lab4_2_identity_key()
        target_octet = expected_target_octet if expected_target_octet is not None else get_lab4_2_target_ip(identity_key, variant)
        port = parsed.port if parsed.port is not None else 8080

        ip_match = re.fullmatch(r'192\.168\.0\.(\d{1,3})', host)
        if not ip_match:
            return "<h1>Not Found</h1><p>No administration service detected on this host.</p>", 404

        requested_octet = int(ip_match.group(1))
        if requested_octet < 1 or requested_octet > 255:
            return "<h1>Not Found</h1><p>No administration service detected on this host.</p>", 404

        if port != 8080:
            return "<h1>Not Found</h1><p>No administration service detected on this host.</p>", 404

        if path == '/product/stock/check':
            product_id = query.get('productId', ['unknown'])[0]
            simulated_stock = ((requested_octet + int(product_id)) % 37) + 4 if str(product_id).isdigit() else 12
            return f"Stock check complete: {simulated_stock} units ready for dispatch from node {requested_octet}.", 200

        if path == '/admin':
            if requested_octet != target_octet:
                return "<h1>Not Found</h1><p>No administration service detected on this host.</p>", 404

            return render_template(
                'lab4/admin_v2_panel.html',
                host_ip=f"192.168.0.{requested_octet}",
                user_to_delete='carlos',
                variant_context=get_lab4_2_variant_context(variant)
            ), 200

        if path == '/admin/delete':
            if requested_octet != target_octet:
                return "Admin action endpoint unavailable.", 404

            username = query.get('username', [''])[0]
            if username != 'carlos':
                return f"User {username} not found.", 404

            variation = {
                'a': 'variation_A',
                'b': 'variation_B',
                'c': 'variation_C'
            }.get(variant, 'variation_A')
            flag = get_random_flag('lab4_2', variation=variation)
            return (
                "<h1>Administrative Action Complete</h1>"
                f"<p>User {username} deleted from 192.168.0.{requested_octet}.</p>"
                "<div style='margin-top:16px;padding:18px;border-radius:12px;background:#16a34a;color:#fff;'>"
                f"<strong>FLAG:</strong> {flag}</div>"
            ), 200

        return "Back-end route not found.", 404

    except ValueError:
        return "<h1>Not Found</h1><p>No administration service detected on this host.</p>", 404
    except Exception as exc:
        return f"Internal Server Error: {exc}", 500


@app.route('/lab4/2/a')
@login_required
def lab4_2a():
    log_lab4_2_target_ip('a', 'Lab entered', session_key='lab4_2_entry_logged_variants')
    return render_template(
        'lab4/sub2_a.html',
        products=get_lab4_2_products('a'),
        variant_context=get_lab4_2_variant_context('a')
    )


@app.route('/lab4/2/b')
@login_required
def lab4_2b():
    log_lab4_2_target_ip('b', 'Lab entered', session_key='lab4_2_entry_logged_variants')
    return render_template(
        'lab4/sub2_b.html',
        products=get_lab4_2_products('b'),
        variant_context=get_lab4_2_variant_context('b')
    )


@app.route('/lab4/2/c')
@login_required
def lab4_2c():
    log_lab4_2_target_ip('c', 'Lab entered', session_key='lab4_2_entry_logged_variants')
    return render_template(
        'lab4/sub2_c.html',
        products=get_lab4_2_products('c'),
        variant_context=get_lab4_2_variant_context('c')
    )


@app.route('/lab4/2/a/product/<int:product_id>')
@login_required
def lab4_2a_product(product_id):
    product = next((p for p in get_lab4_2_products('a') if p['id'] == product_id), None)
    if not product:
        return "Product not found", 404
    return render_template(
        'lab4/sub2_a_product.html',
        product=product,
        stock_api=build_lab4_2_stock_api(product_id),
        variant_context=get_lab4_2_variant_context('a')
    )


@app.route('/lab4/2/b/product/<int:product_id>')
@login_required
def lab4_2b_product(product_id):
    product = next((p for p in get_lab4_2_products('b') if p['id'] == product_id), None)
    if not product:
        return "Product not found", 404
    return render_template(
        'lab4/sub2_b_product.html',
        product=product,
        stock_api=build_lab4_2_stock_api(product_id),
        variant_context=get_lab4_2_variant_context('b')
    )


@app.route('/lab4/2/c/product/<int:product_id>')
@login_required
def lab4_2c_product(product_id):
    product = next((p for p in get_lab4_2_products('c') if p['id'] == product_id), None)
    if not product:
        return "Product not found", 404
    return render_template(
        'lab4/sub2_c_product.html',
        product=product,
        stock_api=build_lab4_2_stock_api(product_id),
        variant_context=get_lab4_2_variant_context('c')
    )


@app.route('/lab4/2/a/stock', methods=['POST'])
@login_required
def lab4_2a_stock():
    target_octet = get_lab4_2_target_ip(get_lab4_2_identity_key(), 'a')
    log_lab4_2_target_ip('a', 'Stock API invoked')
    return process_lab4_2_ssrf_request(extract_stock_api_param(), 'a', expected_target_octet=target_octet)


@app.route('/lab4/2/b/stock', methods=['POST'])
@login_required
def lab4_2b_stock():
    target_octet = get_lab4_2_target_ip(get_lab4_2_identity_key(), 'b')
    log_lab4_2_target_ip('b', 'Stock API invoked')
    return process_lab4_2_ssrf_request(extract_stock_api_param(), 'b', expected_target_octet=target_octet)


@app.route('/lab4/2/c/stock', methods=['POST'])
@login_required
def lab4_2c_stock():
    target_octet = get_lab4_2_target_ip(get_lab4_2_identity_key(), 'c')
    log_lab4_2_target_ip('c', 'Stock API invoked')
    return process_lab4_2_ssrf_request(extract_stock_api_param(), 'c', expected_target_octet=target_octet)


# -------------------------
# LAB 5: File Upload
# -------------------------

def reset_lab5_state():
    """Clear all Lab 5 session state and uploaded avatar directories."""
    lab5_uid_keys = [
        'lab5_1_uid',
        'lab5_1_b_uid',
        'lab5_1_c_uid',
        'lab5_2_uid',
        'lab5_2_b_uid',
        'lab5_2_c_uid',
    ]

    for uid_key in lab5_uid_keys:
        uid = session.get(uid_key)
        if not uid:
            continue

        upload_dir = os.path.join(LAB5_AVATAR_ROOT, uid)
        if os.path.exists(upload_dir):
            try:
                shutil.rmtree(upload_dir)
            except Exception:
                pass

    lab5_session_keys = [
        'lab5_1_user', 'lab5_1_avatar', 'lab5_1_uid', 'lab5_1_flag',
        'lab5_1_b_user', 'lab5_1_b_avatar', 'lab5_1_b_uid', 'lab5_1_b_flag',
        'lab5_1_c_user', 'lab5_1_c_avatar', 'lab5_1_c_uid', 'lab5_1_c_flag',
        'lab5_2_user', 'lab5_2_avatar', 'lab5_2_uid', 'lab5_2_flag',
        'lab5_2_b_user', 'lab5_2_b_avatar', 'lab5_2_b_uid', 'lab5_2_b_flag',
        'lab5_2_c_user', 'lab5_2_c_avatar', 'lab5_2_c_uid', 'lab5_2_c_flag',
    ]

    for session_key in lab5_session_keys:
        session.pop(session_key, None)

@app.route('/lab5')
def lab5():
    reset_lab5_state()
    return render_template('lab5/index.html')


# LAB 5.1: Remote Code Execution via Web Shell Upload
# Menu Selection
@app.route('/lab5/1/menu')
def lab5_1_menu():
    return render_template('lab5/sub1_menu.html')

@app.route('/lab5/1')
def lab5_1():
    # Render the E-commerce Shop Home Page
    products = [
        {'name': 'SecureDrive SSD', 'description': 'Encrypted 2TB storage for ultimate privacy.', 'price': 199.99, 'image': 'https://images.unsplash.com/photo-1597852074816-d933c7d2b988?auto=format&fit=crop&w=600&q=80'},
        {'name': 'Privacy Shield', 'description': 'Anti-spam filter hardware appliance.', 'price': 149.50, 'image': 'https://images.unsplash.com/photo-1563770095128-42fa6112a83e?auto=format&fit=crop&w=600&q=80'},
        {'name': 'Developer Laptop', 'description': 'Optimized for heavy compiling workloads.', 'price': 1299.00, 'image': 'https://images.unsplash.com/photo-1517336714731-489689fd1ca4?auto=format&fit=crop&w=600&q=80'},
        {'name': 'Wireless Headers', 'description': 'Noise-canceling over-ear headphones.', 'price': 299.00, 'image': 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=600&q=80'},
        {'name': 'Mechanical Keyboard', 'description': 'RGB backlit clicky switches.', 'price': 89.99, 'image': 'https://images.unsplash.com/photo-1587829741301-dc798b91a05c?auto=format&fit=crop&w=600&q=80'},
        {'name': 'Smart Watch', 'description': 'Health tracking and notifications.', 'price': 150.00, 'image': 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&q=80'}
    ]
    return render_template('lab5/sub1_home.html', products=products)

@app.route('/lab5/1/login', methods=['GET', 'POST'])
def lab5_1_login():
    if request.method == 'GET':
        if session.get('lab5_1_user'):
            return redirect(url_for('lab5_1_account'))
        return render_template('lab5/sub1_login.html')
    
    username_raw = (request.form.get('username') or '')
    password_raw = (request.form.get('password') or '')
    username = username_raw.strip().lower()
    password = password_raw.strip()
    
    # Wiener:peter (Standard PortSwigger user)
    if username == 'wiener' and password == 'peter':
        session['lab5_1_user'] = username_raw.strip() or username
        # Generate a unique session ID for file isolation if not exists
        if 'lab5_1_uid' not in session:
            session['lab5_1_uid'] = str(uuid.uuid4())
        return redirect(url_for('lab5_1_account'))
    else:
        return render_template('lab5/sub1_login.html', error='Invalid credentials')

@app.route('/lab5/1/account')
def lab5_1_account():
    username = session.get('lab5_1_user')
    if not username:
        return redirect(url_for('lab5_1_login'))
    
    # Check if user has an avatar uploaded in their specific directory
    avatar = session.get('lab5_1_avatar') # This now stores 'uid/filename' or just filename? 
    # Let's store RELATIVE path 'uid/filename' in the session for simplicity?
    # Or keep just filename and construct path. Storing relative path is safer.
    
    avatar_url = f"/files/avatars/{avatar}" if avatar else None
    flag = session.get('lab5_1_flag')
    
    return render_template('lab5/sub1_account.html', username=username, avatar=avatar_url, flag=flag)


def ensure_lab5_1_user_session():
    """Lab 5.1 requires explicit wiener/peter login - no global fallback."""
    return session.get('lab5_1_user')


def save_lab5_avatar_upload(file_obj, upload_dir):
    """Persist the uploaded avatar, or an intercepted payload supplied via multipart fields."""
    filename = file_obj.filename
    file_path = os.path.join(upload_dir, filename)
    payload_override = (
        request.form.get('payload')
        or request.form.get('file_contents')
        or request.form.get('php_payload')
        or ''
    )

    try:
        if payload_override:
            with open(file_path, 'wb') as uploaded_file:
                uploaded_file.write(payload_override.encode('utf-8'))
        else:
            file_obj.save(file_path)
    except (IOError, OSError) as e:
        raise IOError(f"Failed to write file {filename}: {str(e)}")

    return filename


def resolve_lab5_avatar_lab_id(filename):
    """Map an uploaded avatar path back to the active Lab 5 unit."""
    avatar_lab_keys = [
        ('lab5_1_avatar', 'lab5_1'),
        ('lab5_1_b_avatar', 'lab5_1'),
        ('lab5_1_c_avatar', 'lab5_1'),
        ('lab5_2_avatar', 'lab5_2'),
        ('lab5_2_b_avatar', 'lab5_2'),
        ('lab5_2_c_avatar', 'lab5_2'),
    ]

    for session_key, lab_id in avatar_lab_keys:
        if session.get(session_key) == filename:
            return lab_id

    return 'lab5_1'


def extract_lab5_flag_from_upload(file_path, lab_id):
    """Return the dynamic lab flag if the uploaded file carries the simulated payload."""
    if not os.path.exists(file_path) or not file_path.lower().endswith('.php'):
        return None

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as uploaded_file:
            payload = uploaded_file.read()
    except Exception:
        return None

    normalized_payload = payload.replace('"', "'").replace("\\", "/").lower()
    if (
        "/home/carlos/secret" in normalized_payload
        or "file_get_contents('/home/carlos/secret')" in normalized_payload
    ):
        return get_random_flag(lab_id)

    return None

@app.route('/lab5/1/upload', methods=['POST'])
def lab5_1_upload():
    username = session.get('lab5_1_user')
    if not username:
        return redirect(url_for('lab5_1_login'))
        
    if 'avatar' not in request.files:
        return render_template('lab5/sub1_account.html',
                             username=username,
                             error='No file selected for upload.')
    
    # Ensure UID exists
    if 'lab5_1_uid' not in session:
        session['lab5_1_uid'] = str(uuid.uuid4())
    
    user_uid = session['lab5_1_uid']
        
    file = request.files['avatar']
    if file.filename == '':
        return render_template('lab5/sub1_account.html',
                             username=username,
                             error='Filename cannot be empty.')
    
    # VULNERABILITY: No validation of file extension or content
    filename = file.filename
    
    # Create User Specific Directory with fallback
    try:
        upload_dir = os.path.join(LAB5_AVATAR_ROOT, user_uid)
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir, exist_ok=True)
    except (OSError, PermissionError) as e:
        # Fallback to /tmp if primary directory fails
        try:
            upload_dir = os.path.join('/tmp', 'lab5_avatars', user_uid)
            os.makedirs(upload_dir, exist_ok=True)
        except Exception as fallback_err:
            return render_template('lab5/sub1_account.html',
                                 username=username,
                                 error=f'Upload directory unavailable. Please try again.')

    try:
        filename = save_lab5_avatar_upload(file, upload_dir)
    except (IOError, OSError) as write_err:
        return render_template('lab5/sub1_account.html',
                             username=username,
                             error=f'Failed to save file: {str(write_err)[:50]}')
    
    try:
        file_path = os.path.join(upload_dir, filename)
        flag = extract_lab5_flag_from_upload(file_path, 'lab5_1')
    except Exception as read_err:
        flag = None

    # Update session with relative path
    relative_path = f"{user_uid}/{filename}"
    session['lab5_1_avatar'] = relative_path
    session['lab5_1_flag'] = flag
    
    return render_template('lab5/sub1_account.html', 
                         username=username, 
                         avatar=f"/files/avatars/{relative_path}",
                         message=f"Avatar {filename} uploaded successfully!",
                         flag=flag)

@app.route('/lab5/1/logout')
@app.route('/lab5/1/logout')
def lab5_1_logout():
    # Cleanup: Delete user files on logout
    uid = session.get('lab5_1_uid')
    if uid:
        base_dir = BASE_PATH
        user_upload_dir = os.path.join(LAB5_AVATAR_ROOT, uid)
        if os.path.exists(user_upload_dir):
            try:
                shutil.rmtree(user_upload_dir)
            except Exception as e:
                print(f"Error cleaning up directory {user_upload_dir}: {e}")

    session.pop('lab5_1_user', None)
    session.pop('lab5_1_avatar', None)
    session.pop('lab5_1_uid', None)
    session.pop('lab5_1_flag', None)
    return redirect(url_for('lab5_1_login'))

# The Vulnerable File Serving Route
@app.route('/files/avatars/<path:filename>')
def lab5_1_file(filename):
    # Filename here will be "uid/actual_filename.ext" because of <path:filename>
    base_dir = BASE_PATH
    # Base upload directory
    upload_base_dir = LAB5_AVATAR_ROOT
    
    # Securely join paths? No, we want to allow access to the file.
    # But let's construct the full path.
    file_path = os.path.join(upload_base_dir, filename)
    
    # Security check: Ensure we don't traverse up from 'avatars' directory
    # Although path traversal is another vulnerability potential, for this specific lab focus on File Upload RCE,
    # let's keep it scoped to the avatars folder structure essentially.
    if not os.path.abspath(file_path).startswith(os.path.abspath(upload_base_dir)):
         return "Access Denied", 403

    if not os.path.exists(file_path):
        return "File not found", 404
        
    # SIMULATION: Check if it's a PHP file and "execute" it.
    # On Vercel/static hosting we can't execute uploaded PHP for real,
    # so the lab also supports a request-supplied payload for Burp Repeater.
    if filename.lower().endswith('.php'):
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            request_payload = (
                request.args.get('payload')
                or request.args.get('php')
                or ''
            )
            effective_payload = f"{content}\n{request_payload}".strip()
                
            normalized_payload = effective_payload.replace('"', "'").replace("\\", "/").lower()

            # Check for the lab payload in a forgiving way so Repeater edits and
            # slightly different PHP formatting still trigger the simulated RCE.
            if (
                "/home/carlos/secret" in normalized_payload
                or "file_get_contents('/home/carlos/secret')" in normalized_payload
            ):
                # Return the secret!
                return get_random_flag(resolve_lab5_avatar_lab_id(filename))
            
            # Simulated generic echo
            if "echo" in effective_payload:
                import re
                matches = re.findall(r"echo\s+['\"](.*?)['\"]", effective_payload)
                if matches:
                    return "".join(matches)
                    
            # Fallback: Just return the content as text/plain (source code disclosure)
            return content, 200, {'Content-Type': 'text/plain'}
            
        except Exception as e:
            return str(e), 500
            
    # Serve normal images
    # We need to serve from the specific directory.
    # send_from_directory expects a directory and a filename.
    # Since 'filename' contains 'uid/image.png', we can pass base dir and the path.
    return send_from_directory(upload_base_dir, filename)


# -------------------------
# LAB 5.2: Content-Type Bypass
# -------------------------
@app.route('/lab5/2/menu')
def lab5_2_menu():
    return render_template('lab5/sub2_menu.html')

@app.route('/lab5/2')
def lab5_2():
    products = [
         {'name': 'Alpine Beacon Pack', 'description': 'Weatherproof field pack for guided summit routes.', 'price': 129.00, 'image': 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=900&q=80'},
         {'name': 'RidgeLine Thermal Flask', 'description': 'Vacuum-sealed steel flask built for cold-weather expeditions.', 'price': 42.50, 'image': 'https://images.unsplash.com/photo-1523362628745-0c100150b504?auto=format&fit=crop&w=900&q=80'},
         {'name': 'SummitPass Trek Camera', 'description': 'Compact travel camera used for member badge and trip uploads.', 'price': 519.00, 'image': 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=900&q=80'}
    ]
    return render_template('lab5/sub2_home.html', products=products)

@app.route('/lab5/2/login', methods=['GET', 'POST'])
def lab5_2_login():
    if request.method == 'GET':
        if 'lab5_2_user' in session:
            return redirect(url_for('lab5_2_account'))
        return render_template('lab5/sub2_login.html')
    
    username_raw = (request.form.get('username') or '')
    password_raw = (request.form.get('password') or '')
    username = username_raw.strip().lower()
    password = password_raw.strip()
    
    if username == 'wiener' and password == 'peter':
        session['lab5_2_user'] = username_raw.strip() or username
        if 'lab5_2_uid' not in session:
            session['lab5_2_uid'] = str(uuid.uuid4())
        return redirect(url_for('lab5_2_account'))
    else:
        return render_template('lab5/sub2_login.html', error='Invalid credentials')

@app.route('/lab5/2/account')
def lab5_2_account():
    username = session.get('lab5_2_user')
    if not username:
        return redirect(url_for('lab5_2_login'))
    
    avatar = session.get('lab5_2_avatar')
    avatar_url = f"/files/avatars/{avatar}" if avatar else None
    flag = session.get('lab5_2_flag')
    
    return render_template('lab5/sub2_account.html', username=username, avatar=avatar_url, flag=flag)

@app.route('/lab5/2/upload', methods=['POST'])
def lab5_2_upload():
    username = session.get('lab5_2_user')
    if not username:
        return redirect(url_for('lab5_2_login'))
        
    if 'avatar' not in request.files:
        return render_template('lab5/sub2_account.html',
                             username=username,
                             error='No file selected for upload.')
    
    if 'lab5_2_uid' not in session:
        session['lab5_2_uid'] = str(uuid.uuid4())
    user_uid = session['lab5_2_uid']
        
    file = request.files['avatar']
    if file.filename == '':
        return render_template('lab5/sub2_account.html',
                             username=username,
                             error='Filename cannot be empty.')
    
    # VULNERABILITY: Content-Type Bypass
    # We check the Content-Type header, but not the actual file content or extension
    if file.content_type not in ['image/jpeg', 'image/png']:
        return render_template('lab5/sub2_account.html', 
                             username=username, 
                             error=f"Error: File type {file.content_type} is not allowed. Only image/jpeg and image/png are accepted in this secure environment.")
    
    # If the attacker changes Content-Type to image/jpeg, we accept it, even if filename is exploit.php
    filename = file.filename
    
    # Create User Specific Directory with fallback
    try:
        upload_dir = os.path.join(LAB5_AVATAR_ROOT, user_uid)
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir, exist_ok=True)
    except (OSError, PermissionError):
        try:
            upload_dir = os.path.join('/tmp', 'lab5_avatars', user_uid)
            os.makedirs(upload_dir, exist_ok=True)
        except Exception:
            return render_template('lab5/sub2_account.html',
                                 username=username,
                                 error='Upload directory unavailable. Please try again.')
    
    try:
        file.save(os.path.join(upload_dir, filename))
    except (IOError, OSError) as write_err:
        return render_template('lab5/sub2_account.html',
                             username=username,
                             error=f'Failed to save file: {str(write_err)[:50]}')

    try:
        file_path = os.path.join(upload_dir, filename)
        flag = extract_lab5_flag_from_upload(file_path, 'lab5_2')
    except Exception:
        flag = None
    
    relative_path = f"{user_uid}/{filename}"
    session['lab5_2_avatar'] = relative_path
    session['lab5_2_flag'] = flag
    
    return render_template('lab5/sub2_account.html', username=username, avatar=f"/files/avatars/{relative_path}", message=f"Avatar {filename} uploaded successfully!", flag=flag)

@app.route('/lab5/2/logout')
def lab5_2_logout():
    # Cleanup
    uid = session.get('lab5_2_uid')
    if uid:
        base_dir = BASE_PATH
        user_upload_dir = os.path.join(LAB5_AVATAR_ROOT, uid)
        if os.path.exists(user_upload_dir):
            try:
                shutil.rmtree(user_upload_dir)
            except Exception as e:
                pass

    session.pop('lab5_2_user', None)
    session.pop('lab5_2_avatar', None)
    session.pop('lab5_2_uid', None)
    session.pop('lab5_2_flag', None)
    return redirect(url_for('lab5_2_login'))

# -------------------------
# LAB 5.2 VARIATION B: Global Logistics (Orange Theme)
# -------------------------
@app.route('/lab5/2/b')
def lab5_2_b():
    shipments = [
        {'id': 'SHP-9021', 'status': 'In Transit', 'eta': '2 Days'},
        {'id': 'SHP-8820', 'status': 'Delivered', 'eta': 'Did not arrive'},
        {'id': 'SHP-1029', 'status': 'Processing', 'eta': 'Pending'}
    ]
    return render_template('lab5/sub2_b_home.html', shipments=shipments)

@app.route('/lab5/2/b/login', methods=['GET', 'POST'])
def lab5_2_b_login():
    if request.method == 'GET':
        if 'lab5_2_b_user' in session:
            return redirect(url_for('lab5_2_b_account'))
        return render_template('lab5/sub2_b_login.html')
    
    username_raw = (request.form.get('username') or '')
    password_raw = (request.form.get('password') or '')
    username = username_raw.strip().lower()
    password = password_raw.strip()
    
    if username == 'wiener' and password == 'peter':
        session['lab5_2_b_user'] = username_raw.strip() or username
        if 'lab5_2_b_uid' not in session:
            session['lab5_2_b_uid'] = str(uuid.uuid4())
        return redirect(url_for('lab5_2_b_account'))
    else:
        return render_template('lab5/sub2_b_login.html', error='Invalid credentials')

@app.route('/lab5/2/b/account')
def lab5_2_b_account():
    username = session.get('lab5_2_b_user')
    if not username:
        return redirect(url_for('lab5_2_b_login'))
    
    avatar = session.get('lab5_2_b_avatar')
    avatar_url = f"/files/avatars/{avatar}" if avatar else None
    flag = session.get('lab5_2_b_flag')
    
    return render_template('lab5/sub2_b_account.html', username=username, avatar=avatar_url, flag=flag)

@app.route('/lab5/2/b/upload', methods=['POST'])
def lab5_2_b_upload():
    username = session.get('lab5_2_b_user')
    if not username:
        return redirect(url_for('lab5_2_b_login'))
        
    if 'avatar' not in request.files:
        return render_template('lab5/sub2_b_account.html',
                             username=username,
                             error='No file selected for upload.')
    
    if 'lab5_2_b_uid' not in session:
        session['lab5_2_b_uid'] = str(uuid.uuid4())
    user_uid = session['lab5_2_b_uid']
        
    file = request.files['avatar']
    if file.filename == '':
        return render_template('lab5/sub2_b_account.html',
                             username=username,
                             error='Filename cannot be empty.')
    
    # VULNERABILITY (Same as 5.2): Check Content-Type only
    if file.content_type not in ['image/jpeg', 'image/png']:
        return render_template('lab5/sub2_b_account.html', 
                             username=username, 
                             error=f"ERROR P-902: Invalid format {file.content_type}. Driver app only accepts camera images (JPEG/PNG).")
    
    filename = file.filename
    
    # Create User Specific Directory with fallback
    try:
        upload_dir = os.path.join(LAB5_AVATAR_ROOT, user_uid)
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir, exist_ok=True)
    except (OSError, PermissionError):
        try:
            upload_dir = os.path.join('/tmp', 'lab5_avatars', user_uid)
            os.makedirs(upload_dir, exist_ok=True)
        except Exception:
            return render_template('lab5/sub2_b_account.html',
                                 username=username,
                                 error='Upload directory unavailable. Please try again.')
    
    try:
        file.save(os.path.join(upload_dir, filename))
    except (IOError, OSError) as write_err:
        return render_template('lab5/sub2_b_account.html',
                             username=username,
                             error=f'Failed to save file: {str(write_err)[:50]}')

    try:
        file_path = os.path.join(upload_dir, filename)
        flag = extract_lab5_flag_from_upload(file_path, 'lab5_2')
    except Exception:
        flag = None
    
    relative_path = f"{user_uid}/{filename}"
    session['lab5_2_b_avatar'] = relative_path
    session['lab5_2_b_flag'] = flag
    
    return render_template('lab5/sub2_b_account.html', username=username, avatar=f"/files/avatars/{relative_path}", message=f"Signature {filename} updated!", flag=flag)

@app.route('/lab5/2/b/logout')
def lab5_2_b_logout():
    # Cleanup
    uid = session.get('lab5_2_b_uid')
    if uid:
        import shutil
        base_dir = BASE_PATH
        user_upload_dir = os.path.join(LAB5_AVATAR_ROOT, uid)
        if os.path.exists(user_upload_dir):
            try:
                shutil.rmtree(user_upload_dir)
            except Exception as e:
                pass
    session.pop('lab5_2_b_user', None)
    session.pop('lab5_2_b_avatar', None)
    session.pop('lab5_2_b_uid', None)
    session.pop('lab5_2_b_flag', None)
    return redirect(url_for('lab5_2_b_login'))

# -------------------------
# LAB 5.2 VARIATION C: SecureBank (Purple Theme)
# -------------------------
@app.route('/lab5/2/c')
def lab5_2_c():
    return render_template('lab5/sub2_c_home.html')

@app.route('/lab5/2/c/login', methods=['GET', 'POST'])
def lab5_2_c_login():
    if request.method == 'GET':
        if 'lab5_2_c_user' in session:
            return redirect(url_for('lab5_2_c_account'))
        return render_template('lab5/sub2_c_login.html')
    
    username_raw = (request.form.get('username') or '')
    password_raw = (request.form.get('password') or '')
    username = username_raw.strip().lower()
    password = password_raw.strip()
    
    if username == 'wiener' and password == 'peter':
        session['lab5_2_c_user'] = username_raw.strip() or username
        if 'lab5_2_c_uid' not in session:
            session['lab5_2_c_uid'] = str(uuid.uuid4())
        return redirect(url_for('lab5_2_c_account'))
    else:
        return render_template('lab5/sub2_c_login.html', error='Invalid credentials')

@app.route('/lab5/2/c/account')
def lab5_2_c_account():
    username = session.get('lab5_2_c_user')
    if not username:
        return redirect(url_for('lab5_2_c_login'))
    
    avatar = session.get('lab5_2_c_avatar')
    avatar_url = f"/files/avatars/{avatar}" if avatar else None
    flag = session.get('lab5_2_c_flag')
    
    return render_template('lab5/sub2_c_account.html', username=username, avatar=avatar_url, flag=flag)

@app.route('/lab5/2/c/upload', methods=['POST'])
def lab5_2_c_upload():
    username = session.get('lab5_2_c_user')
    if not username:
        return redirect(url_for('lab5_2_c_login'))
        
    if 'avatar' not in request.files:
        return render_template('lab5/sub2_c_account.html',
                             username=username,
                             error='No file selected for upload.')
    
    if 'lab5_2_c_uid' not in session:
        session['lab5_2_c_uid'] = str(uuid.uuid4())
    user_uid = session['lab5_2_c_uid']
        
    file = request.files['avatar']
    if file.filename == '':
        return render_template('lab5/sub2_c_account.html',
                             username=username,
                             error='Filename cannot be empty.')
    
    # VULNERABILITY (Same as 5.2)
    if file.content_type not in ['image/jpeg', 'image/png']:
        return render_template('lab5/sub2_c_account.html', 
                             username=username, 
                             error=f"SECURITY ALERT: The format {file.content_type} is not compliant with banking regulations. Upload only JPEG/PNG scans.")
    
    filename = file.filename
    
    # Create User Specific Directory with fallback
    try:
        upload_dir = os.path.join(LAB5_AVATAR_ROOT, user_uid)
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir, exist_ok=True)
    except (OSError, PermissionError):
        try:
            upload_dir = os.path.join('/tmp', 'lab5_avatars', user_uid)
            os.makedirs(upload_dir, exist_ok=True)
        except Exception:
            return render_template('lab5/sub2_c_account.html',
                                 username=username,
                                 error='Upload directory unavailable. Please try again.')
    
    try:
        file.save(os.path.join(upload_dir, filename))
    except (IOError, OSError) as write_err:
        return render_template('lab5/sub2_c_account.html',
                             username=username,
                             error=f'Failed to save file: {str(write_err)[:50]}')

    try:
        file_path = os.path.join(upload_dir, filename)
        flag = extract_lab5_flag_from_upload(file_path, 'lab5_2')
    except Exception:
        flag = None
    
    relative_path = f"{user_uid}/{filename}"
    session['lab5_2_c_avatar'] = relative_path
    session['lab5_2_c_flag'] = flag
    
    return render_template('lab5/sub2_c_account.html', username=session['lab5_2_c_user'], avatar=f"/files/avatars/{relative_path}", message=f"Document {filename} submitted for verification!", flag=flag)

@app.route('/lab5/2/c/logout')
def lab5_2_c_logout():
    # Cleanup
    uid = session.get('lab5_2_c_uid')
    if uid:
        import shutil
        base_dir = BASE_PATH
        user_upload_dir = os.path.join(LAB5_AVATAR_ROOT, uid)
        if os.path.exists(user_upload_dir):
            try:
                shutil.rmtree(user_upload_dir)
            except Exception as e:
                pass
    session.pop('lab5_2_c_user', None)
    session.pop('lab5_2_c_avatar', None)
    session.pop('lab5_2_c_uid', None)
    session.pop('lab5_2_c_flag', None)
    return redirect(url_for('lab5_2_c_login'))


# -------------------------
# LAB 5.1 VARIATION B: PixelArt (NFT/Crypto Theme)
# -------------------------
@app.route('/lab5/1/b')
def lab5_1_b():
    gallery = [
        {'title': 'Cyber Punk #2049', 'artist': 'NeonDreamer', 'price': 0.5, 'image': 'https://images.unsplash.com/photo-1620641788421-7a1c342ea42e?auto=format&fit=crop&w=600&q=80'},
        {'title': 'Glitch Face', 'artist': 'V0ID', 'price': 2.1, 'image': 'https://images.unsplash.com/photo-1614812513172-567d2fe96a75?auto=format&fit=crop&w=600&q=80'},
        {'title': 'Retro Wave', 'artist': 'SynthBoy', 'price': 0.8, 'image': 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=600&q=80'},
        {'title': 'Digital Ape', 'artist': 'CryptoKing', 'price': 12.5, 'image': 'https://images.unsplash.com/photo-1622547748225-3fc4abd2cca0?auto=format&fit=crop&w=600&q=80'},
        {'title': 'Abstract 8-bit', 'artist': 'PixelMage', 'price': 0.05, 'image': 'https://images.unsplash.com/photo-1633103453303-34e2c0e6205e?auto=format&fit=crop&w=600&q=80'},
        {'title': 'Metaverse City', 'artist': 'FutureArchitect', 'price': 4.2, 'image': 'https://images.unsplash.com/photo-1611162617474-5b21e879e113?auto=format&fit=crop&w=600&q=80'}
    ]
    return render_template('lab5/sub1_b_home.html', gallery=gallery)

@app.route('/lab5/1/b/login', methods=['GET', 'POST'])
def lab5_1_b_login():
    if request.method == 'GET':
        if 'lab5_1_b_user' in session:
            return redirect(url_for('lab5_1_b_account'))
        return render_template('lab5/sub1_b_login.html')
    
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username == 'wiener' and password == 'peter':
        session['lab5_1_b_user'] = username
        if 'lab5_1_b_uid' not in session:
            session['lab5_1_b_uid'] = str(uuid.uuid4())
        return redirect(url_for('lab5_1_b_account'))
    else:
        return render_template('lab5/sub1_b_login.html', error='Invalid credentials')

@app.route('/lab5/1/b/account')
def lab5_1_b_account():
    username = session.get('lab5_1_b_user')
    if not username:
        return redirect(url_for('lab5_1_b_login'))
    
    avatar = session.get('lab5_1_b_avatar')
    avatar_url = f"/files/avatars/{avatar}" if avatar else None
    flag = session.get('lab5_1_b_flag')
    
    return render_template('lab5/sub1_b_account.html', username=username, avatar=avatar_url, flag=flag)

@app.route('/lab5/1/b/upload', methods=['POST'])
def lab5_1_b_upload():
    if 'lab5_1_b_user' not in session:
        return redirect(url_for('lab5_1_b_login'))
        
    if 'avatar' not in request.files:
        return redirect(url_for('lab5_1_b_account'))
    
    if 'lab5_1_b_uid' not in session:
        session['lab5_1_b_uid'] = str(uuid.uuid4())
    user_uid = session['lab5_1_b_uid']
        
    file = request.files['avatar']
    if file.filename == '':
        return redirect(url_for('lab5_1_b_account'))
    
    # VULNERABILITY
    filename = file.filename
    base_dir = BASE_PATH
    upload_dir = os.path.join(LAB5_AVATAR_ROOT, user_uid)
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    filename = save_lab5_avatar_upload(file, upload_dir)
    
    file_path = os.path.join(upload_dir, filename)
    flag = extract_lab5_flag_from_upload(file_path, 'lab5_1')

    relative_path = f"{user_uid}/{filename}"
    session['lab5_1_b_avatar'] = relative_path
    session['lab5_1_b_flag'] = flag

    return render_template('lab5/sub1_b_account.html', username=session['lab5_1_b_user'], avatar=f"/files/avatars/{relative_path}", message=f"Artwork {filename} uploaded!", flag=flag)

@app.route('/lab5/1/b/logout')
def lab5_1_b_logout():
    # Cleanup
    uid = session.get('lab5_1_b_uid')
    if uid:
        base_dir = BASE_PATH
        user_upload_dir = os.path.join(LAB5_AVATAR_ROOT, uid)
        if os.path.exists(user_upload_dir):
            try:
                shutil.rmtree(user_upload_dir)
            except Exception as e:
                pass # Silent fail

    session.pop('lab5_1_b_user', None)
    session.pop('lab5_1_b_avatar', None)
    session.pop('lab5_1_b_uid', None)
    session.pop('lab5_1_b_flag', None)
    return redirect(url_for('lab5_1_b_login'))


# -------------------------
# LAB 5.1 VARIATION C: HireMinds (Job Portal Theme)
# -------------------------
@app.route('/lab5/1/c')
def lab5_1_c():
    jobs = [
        {'title': 'Senior React Developer', 'company': 'TechFlow', 'location': 'Remote', 'salary': '$120k', 'logo': 'https://ui-avatars.com/api/?name=TF&background=0D8ABC&color=fff'},
        {'title': 'DevOps Engineer', 'company': 'CloudScale', 'location': 'New York, USA', 'salary': '$150k', 'logo': 'https://ui-avatars.com/api/?name=CS&background=ff5722&color=fff'},
        {'title': 'UX Designer', 'company': 'CreativeBox', 'location': 'London, UK', 'salary': 'Â£65k', 'logo': 'https://ui-avatars.com/api/?name=CB&background=673ab7&color=fff'},
        {'title': 'Product Manager', 'company': 'Innovate', 'location': 'Berlin, DE', 'salary': 'â‚¬85k', 'logo': 'https://ui-avatars.com/api/?name=IN&background=4caf50&color=fff'},
        {'title': 'Data Scientist', 'company': 'DataMind', 'location': 'Toronto, CA', 'salary': '$135k', 'logo': 'https://ui-avatars.com/api/?name=DM&background=607d8b&color=fff'}
    ]
    return render_template('lab5/sub1_c_home.html', jobs=jobs)

@app.route('/lab5/1/c/login', methods=['GET', 'POST'])
def lab5_1_c_login():
    if request.method == 'GET':
        if 'lab5_1_c_user' in session:
            return redirect(url_for('lab5_1_c_account'))
        return render_template('lab5/sub1_c_login.html')
    
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username == 'wiener' and password == 'peter':
        session['lab5_1_c_user'] = username
        if 'lab5_1_c_uid' not in session:
            session['lab5_1_c_uid'] = str(uuid.uuid4())
        return redirect(url_for('lab5_1_c_account'))
    else:
        return render_template('lab5/sub1_c_login.html', error='Invalid credentials')

@app.route('/lab5/1/c/account')
def lab5_1_c_account():
    username = session.get('lab5_1_c_user')
    if not username:
        return redirect(url_for('lab5_1_c_login'))
    
    avatar = session.get('lab5_1_c_avatar')
    avatar_url = f"/files/avatars/{avatar}" if avatar else None
    flag = session.get('lab5_1_c_flag')
    
    return render_template('lab5/sub1_c_account.html', username=username, avatar=avatar_url, flag=flag)

@app.route('/lab5/1/c/upload', methods=['POST'])
def lab5_1_c_upload():
    if 'lab5_1_c_user' not in session:
        return redirect(url_for('lab5_1_c_login'))
        
    if 'avatar' not in request.files:
        return redirect(url_for('lab5_1_c_account'))
    
    if 'lab5_1_c_uid' not in session:
        session['lab5_1_c_uid'] = str(uuid.uuid4())
    user_uid = session['lab5_1_c_uid']
        
    file = request.files['avatar']
    if file.filename == '':
        return redirect(url_for('lab5_1_c_account'))
    
    # VULNERABILITY
    filename = file.filename
    base_dir = BASE_PATH
    upload_dir = os.path.join(LAB5_AVATAR_ROOT, user_uid)
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    filename = save_lab5_avatar_upload(file, upload_dir)
    
    file_path = os.path.join(upload_dir, filename)
    flag = extract_lab5_flag_from_upload(file_path, 'lab5_1')

    relative_path = f"{user_uid}/{filename}"
    session['lab5_1_c_avatar'] = relative_path
    session['lab5_1_c_flag'] = flag

    return render_template('lab5/sub1_c_account.html', username=session['lab5_1_c_user'], avatar=f"/files/avatars/{relative_path}", message=f"Credential {filename} verified!", flag=flag)

@app.route('/lab5/1/c/logout')
def lab5_1_c_logout():
    # Cleanup
    uid = session.get('lab5_1_c_uid')
    if uid:
        base_dir = BASE_PATH
        user_upload_dir = os.path.join(LAB5_AVATAR_ROOT, uid)
        if os.path.exists(user_upload_dir):
            try:
                shutil.rmtree(user_upload_dir)
            except Exception as e:
                pass

    session.pop('lab5_1_c_user', None)
    session.pop('lab5_1_c_avatar', None)
    session.pop('lab5_1_c_uid', None)
    session.pop('lab5_1_c_flag', None)
    return redirect(url_for('lab5_1_c_login'))


# -------------------------
# LAB 6: OS Command Injection
# -------------------------
@app.route('/lab6')
def lab6():
    return render_template('lab6/index.html')

@app.route('/lab6/track', methods=['POST'])
def lab6_track():
    address = request.form.get('address')
    
    # VULNERABILITY: Command Injection
    # In a real scenario this might be a tracking ID, but we ping an IP here.
    # User can enter: 127.0.0.1 && dir
    ping_param = "-c" if os.name != "nt" else "-n"
    command = f"ping {ping_param} 1 {address}" 
    
    try:
        # shell=True allows command chaining
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        return f"<pre>{output.decode('utf-8', errors='ignore')}</pre>"
    except subprocess.CalledProcessError as e:
        return f"<pre>Error: {e.output.decode('utf-8', errors='ignore')}</pre>"
    except Exception as e:
        return f"Error: {str(e)}"


# -------------------------
# LAB 7: SQL Injection
# -------------------------
@app.route('/lab7')
def lab7():
    return render_template('lab7/index.html')



# -------------------------
# LAB 8: Cross-Site Scripting (XSS)
# -------------------------

# Initial seed data for Lab 8.2 (Stored XSS)
# Initial seed data for Lab 8.2 (Stored XSS)
LAB8_COMMENTS = [
    {
        'author': 'System Admin', 
        'date': '2024-03-01', 
        'body': 'Welcome to the feedback board! Please identify any bugs you find. (Just kidding, keep it safe!)'
    },
    {
        'author': 'Hacker101', 
        'date': '2024-03-02', 
        'body': 'Check out this cool feature! <img src=x onerror=alert("Stored_XSS_Executed")>'
    },
    {
        'author': 'BugHunter99', 
        'date': '2024-03-02', 
        'body': 'Found a weird issue on the login page. Can we get a fix?'
    }
]


def clear_lab8_session_state() -> None:
    """Clear only Lab 8-related session keys."""
    lab8_keys = [key for key in session.keys() if key.startswith('lab8_') or key.startswith('xss_flag_')]
    for key in lab8_keys:
        session.pop(key, None)

@app.route('/lab8')
def lab8():
    # Treat navigating back to Lab 8 hub as exiting active Lab 8 sessions.
    clear_lab8_session_state()
    return render_template('lab8/index.html')

# Lab 8.1: Reflected XSS - Hub Page
@app.route('/lab8/1', methods=['GET', 'POST'])
def lab8_1():
    return render_template('lab8/sub1_index.html')


def strip_script_tags(user_input: str) -> str:
    if not user_input:
        return ''
    # For pattern-matching mode: don't strip anything, let backend detect the payload
    return user_input


def check_xss_payload(user_input: str, variant: str) -> bool:
    if not user_input:
        return False
    # Check if input contains active XSS patterns (script, event handlers, protocol handlers)
    normalized_input = user_input.lower()
    variant_normalized = (variant or '').strip().upper()

    xss_patterns = [
        '<script',
        'onerror=',
        'onload=',
        'onclick=',
        'javascript:',
        '"; fetch',
        "'; fetch"
    ]

    # Variant C uses JavaScript string breakout payloads, including simplified alert forms.
    if variant_normalized == 'C':
        xss_patterns.extend([
            '"; alert',
            "'; alert",
            '";prompt',
            "';prompt",
            '";confirm',
            "';confirm",
        ])

    return any(pattern in normalized_input for pattern in xss_patterns)


@app.route('/xss-success')
def xss_success():
    """Endpoint that JavaScript payloads call to prove execution"""
    variant = (request.args.get('variant') or '').strip().upper()
    variant_map = {
        'A': 'variation_A',
        'B': 'variation_B',
        'C': 'variation_C',
        'D': 'variation_D',
        'E': 'variation_E',
    }
    mapped_variation = variant_map.get(variant)
    if not mapped_variation:
        return "Invalid variant", 400
    
    # Generate and store flag for this execution
    flag = str(get_random_flag('lab8', variation=mapped_variation))
    session[f'xss_flag_{variant}'] = flag
    
    # Return JSON with flag so JavaScript can display it
    return {
        'success': True,
        'flag': flag,
        'message': f'XSS Payload Executed Successfully on Variant {variant}!'
    }, 200, {'Content-Type': 'application/json'}

# Lab 8.1.A: TechCorp Employee Portal - Multi-page with Navigation
@app.route('/lab8/1/a', methods=['GET', 'POST'])
@app.route('/lab8/1/a/<page>', methods=['GET', 'POST'])
def lab8_1_a(page='home'):
    # Handle login from any page
    if request.method == 'POST' and 'login_btn' in request.form:
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if username and password:
            session['lab8_subject'] = f"lab8:{username.strip().lower()}"
            session['lab8_1_a_user'] = username
            session.permanent = True
            return redirect(url_for('lab8_1_a', page='home'))
    
    # Handle logout from any page
    if request.method == 'POST' and 'logout_btn' in request.form:
        session.pop('lab8_1_a_user', None)
        session.pop('lab8_1_a_search', None)
        session.pop('lab8_subject', None)
        return redirect(url_for('lab8_1_a', page='home'))
    
    # Get login status
    logged_in = 'lab8_1_a_user' in session
    username = session.get('lab8_1_a_user', None)
    
    # Redirect non-logged-in users to login page for protected pages
    if page in ['search', 'profile', 'dashboard'] and not logged_in:
        page = 'login'
    
    # Handle search page - reflects user input (XSS vulnerability)
    search_data = {'query': '', 'results': [], 'payload_detected': False, 'flag': None}
    if page == 'search' and logged_in:
        directory_records = [
            {
                'username': 'admin',
                'name': 'Arjun Kapoor',
                'role': 'Security Administrator',
                'department': 'Identity & Access Management',
                'email': 'admin@techcorp.local',
                'location': 'Bangalore SOC',
                'status': 'Active',
                'last_login': 'Today, 09:42 AM'
            },
            {
                'username': 'nverma',
                'name': 'Neha Verma',
                'role': 'SOC Analyst',
                'department': 'Security Operations',
                'email': 'neha.verma@techcorp.local',
                'location': 'Mumbai Security Hub',
                'status': 'Active',
                'last_login': 'Today, 08:15 AM'
            },
            {
                'username': 'rpatel',
                'name': 'Rohan Patel',
                'role': 'Cloud Security Engineer',
                'department': 'Cloud Security',
                'email': 'rohan.patel@techcorp.local',
                'location': 'Pune Engineering Center',
                'status': 'Active',
                'last_login': 'Today, 07:58 AM'
            },
            {
                'username': 'pmehta',
                'name': 'Priya Mehta',
                'role': 'Compliance Engineer',
                'department': 'Governance & Risk',
                'email': 'priya.mehta@techcorp.local',
                'location': 'Delhi Audit Office',
                'status': 'On Leave',
                'last_login': 'Yesterday, 06:20 PM'
            }
        ]

        if request.method == 'POST' and 'search_btn' in request.form:
            search_query = request.form.get('search_query', '').strip()

            if search_query:
                # Check if payload is detected (will execute in browser)
                if check_xss_payload(search_query, 'A'):
                    search_data['payload_detected'] = True
                    # Generate flag (will be retrieved via /xss-success call)
                    search_data['flag'] = str(get_random_flag('lab8', variation='variation_A'))

                # Search directory (if it's not a payload)
                search_query_lower = search_query.lower()
                for record in directory_records:
                    haystack = " ".join([
                        record['username'],
                        record['name'],
                        record['role'],
                        record['department'],
                        record['email'],
                        record['location'],
                        record['status']
                    ]).lower()
                    if search_query_lower in haystack:
                        search_data['results'].append(record)

            search_data['query'] = search_query
    
    return render_template('lab8/realworld_nav_a.html',
                         page=page,
                         logged_in=logged_in,
                         username=username,
                         search_data=search_data)

# Lab 8.1.B: PixelArt Photo Selling Marketplace - Multi-page with Navigation
@app.route('/lab8/1/b', methods=['GET', 'POST'])
@app.route('/lab8/1/b/<page>', methods=['GET', 'POST'])
def lab8_1_b(page='gallery'):
    # Handle login from any page
    if request.method == 'POST' and (
        'login_btn' in request.form or ('seller_name' in request.form and 'password' in request.form)
    ):
        seller_name = request.form.get('seller_name', '').strip()
        password = request.form.get('password', '')
        if seller_name and password:
            session['lab8_subject'] = f"lab8:{seller_name.strip().lower()}"
            session['lab8_1_b_seller'] = seller_name
            session.permanent = True
            return redirect(url_for('lab8_1_b', page='gallery'))
    
    # Handle logout from any page
    if request.method == 'POST' and 'logout_btn' in request.form:
        session.pop('lab8_1_b_seller', None)
        session.pop('lab8_1_b_upload', None)
        session.pop('lab8_1_b_assets', None)
        session.pop('lab8_subject', None)
        return redirect(url_for('lab8_1_b', page='gallery'))
    
    # Get login status
    logged_in = 'lab8_1_b_seller' in session
    username = session.get('lab8_1_b_seller', None)
    
    # Redirect non-logged-in users to login page
    if page in ['upload', 'profile'] and not logged_in:
        page = 'login'

    default_gallery_assets = [
        {
            'title': 'Golden Hour Street',
            'description': 'Cinematic city frame captured during evening golden hour.',
            'price': '$340.00',
            'image_url': 'https://images.unsplash.com/photo-1545239351-1141bd82e8a6?auto=format&fit=crop&w=900&q=80'
        },
        {
            'title': 'Ocean Blue Minimal',
            'description': 'Minimal ocean composition designed for premium editorial use.',
            'price': '$125.00',
            'image_url': 'https://images.unsplash.com/photo-1618005198919-d3d4b5a92eee?auto=format&fit=crop&w=900&q=80'
        },
        {
            'title': 'Aurora Ridge',
            'description': 'Fine-art mountain photograph with premium print quality.',
            'price': '$890.00',
            'image_url': 'https://images.unsplash.com/photo-1579546929518-9e396f3cc809?auto=format&fit=crop&w=900&q=80'
        }
    ]

    uploaded_assets = session.get('lab8_1_b_assets', [])
    gallery_assets = list(uploaded_assets) + default_gallery_assets
    
    # Handle upload page with XSS detection
    upload_result = {'alt_text': '', 'flag': None, 'payload_detected': False}
    if page == 'upload' and logged_in:
        if request.method == 'POST' and 'upload_btn' in request.form:
            artwork_title = request.form.get('artwork_title', '').strip()
            price_raw = request.form.get('price', '').strip()
            image_alt = request.form.get('image_alt', '').strip()
            image_url = request.form.get('image_url', '').strip()

            if artwork_title and price_raw:
                try:
                    normalized_price = f"${float(price_raw):.2f}"
                except Exception:
                    normalized_price = "$1.00"

                fallback_urls = [
                    'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=900&q=80',
                    'https://images.unsplash.com/photo-1633412802994-5c058f151b66?auto=format&fit=crop&w=900&q=80',
                    'https://images.unsplash.com/photo-1558655146-d09347e92766?auto=format&fit=crop&w=900&q=80'
                ]

                selected_image_url = image_url or fallback_urls[len(uploaded_assets) % len(fallback_urls)]
                uploaded_asset = {
                    'title': artwork_title,
                    'description': image_alt or 'Custom photo listing submitted by seller.',
                    'price': normalized_price,
                    'image_url': selected_image_url
                }
                uploaded_assets.insert(0, uploaded_asset)
                if len(uploaded_assets) > 12:
                    uploaded_assets = uploaded_assets[:12]
                session['lab8_1_b_assets'] = uploaded_assets
                gallery_assets = list(uploaded_assets) + default_gallery_assets
            
            if check_xss_payload(image_alt, 'B'):
                upload_result['flag'] = str(get_random_flag('lab8', variation='variation_B'))
                upload_result['payload_detected'] = True
            
            upload_result['alt_text'] = image_alt
    
    return render_template('lab8/realworld_nav_b.html',
                         page=page,
                         logged_in=logged_in,
                         username=username,
                         upload_result=upload_result if upload_result else None,
                         gallery_assets=gallery_assets)

# Lab 8.1.C: GraphicStudio Design Platform - Multi-page with Navigation
@app.route('/lab8/1/c', methods=['GET', 'POST'])
@app.route('/lab8/1/c/<page>', methods=['GET', 'POST'])
def lab8_1_c(page='portfolio'):
    # Handle login from any page
    if request.method == 'POST' and (
        'login_btn' in request.form or ('designer_name' in request.form and 'password' in request.form)
    ):
        designer_name = request.form.get('designer_name', '').strip()
        password = request.form.get('password', '')
        if designer_name and password:
            session['lab8_subject'] = f"lab8:{designer_name.strip().lower()}"
            session['lab8_1_c_designer'] = designer_name
            session.permanent = True
            return redirect(url_for('lab8_1_c', page='portfolio'))
    
    # Handle logout from any page
    if request.method == 'POST' and 'logout_btn' in request.form:
        session.pop('lab8_1_c_designer', None)
        session.pop('lab8_1_c_create', None)
        session.pop('lab8_subject', None)
        return redirect(url_for('lab8_1_c', page='portfolio'))
    
    # Get login status
    logged_in = 'lab8_1_c_designer' in session
    username = session.get('lab8_1_c_designer', None)
    
    # Redirect non-logged-in users to login page
    if page in ['create', 'projects'] and not logged_in:
        page = 'login'
    
    # Handle create page with XSS detection
    create_result = {'description': '', 'flag': None, 'payload_detected': False}
    if page == 'create' and logged_in:
        if request.method == 'POST' and 'create_btn' in request.form:
            project_desc = request.form.get('project_desc', '').strip()
            
            if project_desc:
                if check_xss_payload(project_desc, 'C'):
                    create_result['flag'] = str(get_random_flag('lab8', variation='variation_C'))
                    create_result['payload_detected'] = True
                
                create_result['description'] = project_desc
    
    return render_template('lab8/realworld_nav_c.html',
                         page=page,
                         logged_in=logged_in,
                         username=username,
                         create_result=create_result if create_result else None)

# Lab 8.1.D: SocialHub Social Network - Multi-page with Navigation
@app.route('/lab8/1/d', methods=['GET', 'POST'])
@app.route('/lab8/1/d/<page>', methods=['GET', 'POST'])
def lab8_1_d(page='home'):
    # Handle login from any page
    if request.method == 'POST' and (
        'login_btn' in request.form or ('user_handle' in request.form and 'password' in request.form)
    ):
        user_handle = request.form.get('user_handle', '').strip()
        password = request.form.get('password', '')
        if user_handle and password:
            session['lab8_subject'] = f"lab8:{user_handle.strip().lower()}"
            session['lab8_1_d_user'] = user_handle
            session.permanent = True
            return redirect(url_for('lab8_1_d', page='myfeed'))
    
    # Handle logout from any page
    if request.method == 'POST' and 'logout_btn' in request.form:
        session.pop('lab8_1_d_user', None)
        session.pop('lab8_1_d_posts', None)
        session.pop('lab8_subject', None)
        return redirect(url_for('lab8_1_d', page='home'))
    
    # Get login status
    logged_in = 'lab8_1_d_user' in session
    user_handle = session.get('lab8_1_d_user', None)
    
    # Redirect non-logged-in users to login page
    if page in ['myfeed'] and not logged_in:
        page = 'login'
    
    # Handle post creation with XSS detection
    post_result = None
    posts = session.get('lab8_1_d_posts', [])
    if page == 'myfeed' and logged_in:
        if request.method == 'POST' and 'post_btn' in request.form:
            post_content = request.form.get('post_content', '').strip()
            
            if post_content:
                if check_xss_payload(post_content, 'D'):
                    post_result = {
                        'content': post_content,
                        'flag': str(get_random_flag('lab8', variation='variation_D')),
                        'payload_detected': True
                    }
                else:
                    post_result = {
                        'content': post_content,
                        'flag': None,
                        'payload_detected': False
                    }
    
    return render_template('lab8/realworld_nav_d.html',
                         page=page,
                         logged_in=logged_in,
                         user_handle=user_handle,
                         post_result=post_result,
                         posts=posts if logged_in else [])

# Lab 8.1.E: DocVault Document Management - Multi-page with Navigation
@app.route('/lab8/1/e', methods=['GET', 'POST'])
@app.route('/lab8/1/e/<page>', methods=['GET', 'POST'])
def lab8_1_e(page='dashboard'):
    # Handle login from any page
    if request.method == 'POST' and (
        'login_btn' in request.form or ('user_email' in request.form and 'password' in request.form)
    ):
        user_email = request.form.get('user_email', '').strip() or request.form.get('admin_user', '').strip()
        password = request.form.get('password', '')
        if user_email and password:
            session['lab8_subject'] = f"lab8:{user_email.strip().lower()}"
            session['lab8_1_e_user'] = user_email
            session.permanent = True
            return redirect(url_for('lab8_1_e', page='dashboard'))
    
    # Handle logout from any page
    if request.method == 'POST' and 'logout_btn' in request.form:
        session.pop('lab8_1_e_user', None)
        session.pop('lab8_1_e_upload', None)
        session.pop('lab8_subject', None)
        return redirect(url_for('lab8_1_e', page='dashboard'))
    
    # Get login status
    logged_in = 'lab8_1_e_user' in session
    user_email = session.get('lab8_1_e_user', None)
    
    # Redirect non-logged-in users to login page
    if page in ['upload', 'documents', 'settings', 'shared'] and not logged_in:
        page = 'login'
    
    # Handle upload page with XSS detection
    upload_result = {'source': '', 'flag': None, 'payload_detected': False}
    if page == 'upload' and logged_in:
        if request.method == 'POST' and 'upload_btn' in request.form:
            doc_source = request.form.get('doc_source', '').strip()
            
            if doc_source:
                if check_xss_payload(doc_source, 'E'):
                    upload_result['flag'] = str(get_random_flag('lab8', variation='variation_E'))
                    upload_result['payload_detected'] = True
                
                upload_result['source'] = doc_source
    
    return render_template('lab8/realworld_nav_e.html',
                         page=page,
                         logged_in=logged_in,
                         user_email=user_email,
                         upload_result=upload_result if upload_result else None)


# Lab 8.2: Stored XSS (Profile Scenario)
# Simple in-memory storage for Lab 8.2
LAB8_USERS_DB = {
    'test': {
        'password': 'test',
        'full_name': 'Joan Smith',
        'address': '123 Cyber Lane, Tech City',
        'email': 'joan.smith@techfusion.corp',
        'bio': 'Senior Analyst at TechFusion Dynamics. Love hiking and coding.'
    }
}

@app.route('/lab8/2', methods=['GET', 'POST'])
def lab8_2():
    # Login Logic
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Static check for credentials (test/test)
        if username == 'test' and password == 'test':
            session['lab8_2_user'] = username
            
            # Initialize isolated profile in session if not exists
            if 'lab8_2_profile' not in session:
                session['lab8_2_profile'] = {
                    'full_name': 'Joan Smith',
                    'email': 'joan.smith@techfusion.corp',
                    'address': '123 Cyber Lane, Tech City',
                    'bio': 'Senior Analyst at TechFusion Dynamics. Love hiking and coding.'
                }
            return redirect(url_for('lab8_2_dashboard'))
        else:
            return render_template('lab8/sub2_login.html', error="Invalid credentials")
            
    # Default GET: Show Login Page if not logged in
    if 'lab8_2_user' in session:
        return redirect(url_for('lab8_2_dashboard'))
        
    return render_template('lab8/sub2_login.html')

@app.route('/lab8/2/dashboard')
def lab8_2_dashboard():
    if 'lab8_2_user' not in session:
        return redirect(url_for('lab8_2'))
    
    # Retrieve data from SESSION, not global DB
    # This isolation allows multiple users to do the lab simultaneously
    user_data = session.get('lab8_2_profile', {})
    
    # Check for Stored XSS Flag condition
    flag = None
    for key in ['full_name', 'address', 'email', 'bio']:
        val = user_data.get(key, '')
        if val and ('<script>' in val.lower() or '%3cscript%3e' in val.lower()):
            flag = get_random_flag('lab8_2')
            break
            
    return render_template('lab8/sub2_dashboard.html', user=user_data, flag=flag)

@app.route('/lab8/2/update', methods=['POST'])
def lab8_2_update():
    if 'lab8_2_user' not in session:
        return redirect(url_for('lab8_2'))
        
    # Update the SESSION data
    # We must copy/modify the dict to ensure Flask detects the change on the session object
    profile = session.get('lab8_2_profile', {}).copy()
    
    # VULNERABILITY: Storing input without sanitization
    profile['full_name'] = request.form.get('full_name')
    profile['email'] = request.form.get('email')
    profile['address'] = request.form.get('address')
    profile['bio'] = request.form.get('bio')
    
    session['lab8_2_profile'] = profile
    
    return redirect(url_for('lab8_2_dashboard'))

@app.route('/lab8/2/logout')
def lab8_2_logout():
    session.pop('lab8_2_user', None)
    return redirect(url_for('lab8_2'))
    
# Clean up old stored comments route if it exists (not used anymore)
# But keep the helper just in case
def init_lab8_2_user():
    # Helper to reset if needed
    LAB8_USERS_DB['test'] = {
        'password': 'test',
        'full_name': 'Joan Smith',
        'address': '123 Cyber Lane, Tech City',
        'email': 'joan.smith@techfusion.corp',
        'bio': 'Senior Analyst at TechFusion Dynamics.'
    }
    
    return redirect(url_for('lab8_2'))

# Endpoint to reset comments if they get too messy
@app.route('/lab8/2/reset')
def lab8_2_reset():
    global LAB8_COMMENTS
    LAB8_COMMENTS = [
        {'author': 'System Admin', 'date': '2024-03-01', 'body': 'Welcome to the feedback board! Please identify any bugs you find.'}
    ]
    return redirect(url_for('lab8_2'))


# LAB 7.1: Virtual SQL Injection Protocol (Category Filter)
@app.route('/lab7/1')
def lab7_1():
    category = (request.args.get('category') or '').strip()
    
    # High-Fidelity Static Research Dataset
    all_products = [
        {'id': 1, 'name': 'Luxury Gift Box', 'category': 'Gifts', 'released': 1},
        {'id': 2, 'name': 'Personalized Mug', 'category': 'Gifts', 'released': 1},
        {'id': 3, 'name': 'Scented Candle Set', 'category': 'Lifestyle', 'released': 1},
        {'id': 4, 'name': 'Leather Wallet', 'category': 'Accessories', 'released': 1},
        {'id': 7, 'name': 'SECRET: Diamond Necklace', 'category': 'Gifts', 'released': 0},
        {'id': 8, 'name': 'SECRET: Gold Cufflinks', 'category': 'Accessories', 'released': 0}
    ]
    
    # Virtual SQL Execution Logic
    flag = None
    products = []
    
    normalized_category = category.upper().replace("+", " ")

    # Simulation: Detect ' OR 1=1 -- equivalent bypass
    is_bypass = (
        "' OR" in normalized_category
        or "'OR" in normalized_category
        or "1=1" in normalized_category
    )
    
    if not category:
        products = [p for p in all_products if p['released'] == 1]
    elif is_bypass:
        products = all_products # Unleash all products (including unreleased)
        flag = get_random_flag('lab7', variation='variation_A')
    else:
        products = [p for p in all_products if p['category'].lower() == category.lower() and p['released'] == 1]
        
    return render_template('lab7/sub1_home.html', products=products, category=category, flag=flag)

@app.route('/lab7/1/menu')
def lab7_1_menu():
    return render_template('lab7/sub1_menu.html')

@app.route('/lab7/1/b', methods=['GET', 'POST'])
def lab7_1_b():
    category = (request.args.get('category') or '').strip()

    all_products = [
        {'id': 11, 'name': 'Executive Briefcase', 'category': 'Work', 'released': 1},
        {'id': 12, 'name': 'Blue-Light Desk Lamp', 'category': 'Office', 'released': 1},
        {'id': 13, 'name': 'Remote Team Notebook', 'category': 'Stationery', 'released': 1},
        {'id': 14, 'name': 'Noise Shield Headset', 'category': 'Tech', 'released': 1},
        {'id': 17, 'name': 'SECRET: Boardroom Access Kit', 'category': 'Work', 'released': 0},
        {'id': 18, 'name': 'SECRET: Prototype AI Recorder', 'category': 'Tech', 'released': 0}
    ]

    flag = None
    products = []
    normalized_category = category.upper().replace("+", " ")
    is_bypass = (
        "' OR" in normalized_category
        or "'OR" in normalized_category
        or "1=1" in normalized_category
    )

    if not category:
        products = [p for p in all_products if p['released'] == 1]
    elif is_bypass:
        products = all_products
        flag = get_random_flag('lab7', variation='variation_B')
    else:
        products = [
            p for p in all_products
            if p['category'].lower() == category.lower() and p['released'] == 1
        ]

    return render_template('lab7/sub1_b_home.html', products=products, category=category, flag=flag)

@app.route('/lab7/1/c')
def lab7_1_c():
    category = (request.args.get('category') or '').strip()

    all_products = [
        {'id': 21, 'name': 'Thermal Trail Bottle', 'category': 'Adventure', 'released': 1},
        {'id': 22, 'name': 'Summit Camp Light', 'category': 'Camping', 'released': 1},
        {'id': 23, 'name': 'All-Terrain Daypack', 'category': 'Bags', 'released': 1},
        {'id': 24, 'name': 'Stormproof Shell Gloves', 'category': 'Apparel', 'released': 1},
        {'id': 27, 'name': 'SECRET: Glacier Beacon Mk II', 'category': 'Adventure', 'released': 0},
        {'id': 28, 'name': 'SECRET: Alpine Rescue Drone', 'category': 'Camping', 'released': 0}
    ]

    flag = None
    products = []
    normalized_category = category.upper().replace("+", " ")
    is_bypass = (
        "' OR" in normalized_category
        or "'OR" in normalized_category
        or "1=1" in normalized_category
    )

    if not category:
        products = [p for p in all_products if p['released'] == 1]
    elif is_bypass:
        products = all_products
        flag = get_random_flag('lab7', variation='variation_C')
    else:
        products = [
            p for p in all_products
            if p['category'].lower() == category.lower() and p['released'] == 1
        ]

    return render_template('lab7/sub1_c_home.html', products=products, category=category, flag=flag)

@app.route('/lab7/1/d')
def lab7_1_d():
    return redirect(url_for('lab7_1_menu'))

# ========================
# LAB 7.2: Office Login System
# ========================
@app.route('/lab7/2/menu')
def lab7_2_menu():
    return render_template('lab7/sub2_menu.html')

@app.route('/lab7/2', methods=['GET', 'POST'])
def lab7_2():
    return render_template('lab7/sub2_home.html', identity=_lab7_2_identity('variation_A', 'a'))

@app.route('/lab7/2/login', methods=['GET', 'POST'])
def lab7_2_login():
    return _render_lab7_2_variant(
        identity=_lab7_2_identity('variation_A', 'a'),
        template_name='lab7/sub2_a_login.html'
    )

@app.route('/lab7/2/b')
def lab7_2_b():
    return render_template('lab7/sub2_home.html', identity=_lab7_2_identity('variation_B', 'b'))

@app.route('/lab7/2/b/login', methods=['GET', 'POST'])
def lab7_2_b_login():
    return _render_lab7_2_variant(
        identity=_lab7_2_identity('variation_B', 'b'),
        template_name='lab7/sub2_b_login.html'
    )

@app.route('/lab7/2/c')
def lab7_2_c():
    return render_template('lab7/sub2_home.html', identity=_lab7_2_identity('variation_C', 'c'))

@app.route('/lab7/2/c/login', methods=['GET', 'POST'])
def lab7_2_c_login():
    return _render_lab7_2_variant(
        identity=_lab7_2_identity('variation_C', 'c'),
        template_name='lab7/sub2_c_login.html'
    )

def _lab7_2_identity(variation, slug):
    identity_map = {
        'variation_A': {
            'variation': 'variation_A',
            'slug': slug,
            'theme': 'northstar',
            'brand': 'Northstar Office',
            'icon': 'ðŸ¢',
            'title': 'Northstar Office Portal',
            'subtitle': 'Internal employee access for finance, operations, and leadership reporting.',
            'accent': '#06b6d4',
            'gradient': 'linear-gradient(135deg, rgba(8, 145, 178, 0.22), rgba(15, 23, 42, 0.92))',
            'query_label': 'portal_users',
            'eyebrow': 'Enterprise Operations Suite',
            'hero_title': 'Workflows, reporting, and admin access in one place.',
            'hero_body': 'Northstar Office centralizes approvals, staff provisioning, executive dashboards, and department operations inside a single internal workspace.',
            'feature_1_title': 'Ops Dashboard',
            'feature_1_body': 'Monitor approvals, ticket queues, and weekly execution metrics.',
            'feature_2_title': 'Access Governance',
            'feature_2_body': 'Review user roles, session policies, and privileged workflows.',
            'feature_3_title': 'Directory Sync',
            'feature_3_body': 'Coordinate department data, identity mappings, and reporting exports.'
        },
        'variation_B': {
            'variation': 'variation_B',
            'slug': slug,
            'theme': 'aegis',
            'brand': 'Aegis Workforce',
            'icon': 'ðŸ›¡ï¸',
            'title': 'Aegis Workforce Console',
            'subtitle': 'Restricted workforce console for staffing operations, leadership comms, and approval routing.',
            'accent': '#3b82f6',
            'gradient': 'linear-gradient(135deg, rgba(30, 64, 175, 0.24), rgba(15, 23, 42, 0.92))',
            'query_label': 'staff_accounts',
            'eyebrow': 'Protected Staffing Console',
            'hero_title': 'Hiring control, staffing signals, and workforce approvals.',
            'hero_body': 'Aegis Workforce helps internal teams review roster changes, access schedules, and manage privileged staffing operations from a single secure console.',
            'feature_1_title': 'Talent Routing',
            'feature_1_body': 'Track internal transfers, staffing approvals, and manager review flows.',
            'feature_2_title': 'Role Controls',
            'feature_2_body': 'Validate elevated accounts and operational access requests across teams.',
            'feature_3_title': 'Shift Intelligence',
            'feature_3_body': 'View workforce planning summaries and controlled scheduling data.'
        },
        'variation_C': {
            'variation': 'variation_C',
            'slug': slug,
            'theme': 'helix',
            'brand': 'Helix Admin',
            'icon': 'ðŸ§¬',
            'title': 'Helix Admin Gateway',
            'subtitle': 'Clinical administration gateway for controlled personnel records and scheduling infrastructure.',
            'accent': '#a855f7',
            'gradient': 'linear-gradient(135deg, rgba(126, 34, 206, 0.24), rgba(15, 23, 42, 0.92))',
            'query_label': 'admin_registry',
            'eyebrow': 'Clinical Control Gateway',
            'hero_title': 'Administrative systems for regulated care operations.',
            'hero_body': 'Helix Admin gives authorized teams access to scheduling controls, privileged user records, and internal administration tools across the care network.',
            'feature_1_title': 'Schedule Ops',
            'feature_1_body': 'Coordinate internal scheduling reviews, coverage decisions, and escalation paths.',
            'feature_2_title': 'Role Segmentation',
            'feature_2_body': 'Inspect privileged staff records and restricted administrative entitlements.',
            'feature_3_title': 'Policy Console',
            'feature_3_body': 'Review internal governance data and compliance routing for care operations.'
        }
    }
    identity = identity_map[variation].copy()
    identity['login_url'] = (
        '/lab7/2/login' if slug == 'a' else f'/lab7/2/{slug}/login'
    )
    identity['home_url'] = (
        '/lab7/2' if slug == 'a' else f'/lab7/2/{slug}'
    )
    return identity

def _render_lab7_2_variant(identity, template_name='lab7/sub2_login.html'):
    error = None
    success = False
    flag = None
    user_info = None
    query = None

    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = (request.form.get('password') or '').strip()
        normalized_username = username.upper().replace("+", " ")
        is_bypass = (
            "ADMINISTRATOR'--" in normalized_username
            or "ADMINISTRATOR' --" in normalized_username
        )
        query = (
            f"SELECT id, username, role FROM {identity['query_label']} "
            f"WHERE username = '{username}' AND password = '{password}'"
        )

        if is_bypass:
            success = True
            user_info = {
                'employee_id': 'ADM-001',
                'username': 'administrator',
                'department': 'Executive Operations',
                'role': 'System Administrator',
            'email': 'administrator@internal.local'
            }
            flag = get_random_flag('lab7', variation=identity['variation'])
            query = (
                f"SELECT id, username, role FROM {identity['query_label']} "
                f"WHERE username = 'administrator'--"
            )
        else:
            error = "Invalid credentials."

    return render_template(
        template_name,
        error=error,
        success=success,
        flag=flag,
        user_info=user_info,
        query=query,
        identity=identity
    )

# LAB 6.1: OS Command Injection via Stock Check
@app.route('/lab6/1/menu')
def lab6_1_menu():
    return render_template('lab6/sub1_menu.html')

# Variation A: MegaMart
@app.route('/lab6/1')
def lab6_1():
    products = [
        {'id': 1, 'name': 'Organic Bananas', 'description': 'Fresh from local farms', 'price': 2.99, 'image': 'https://images.unsplash.com/photo-1603833665858-e61d17a86224?auto=format&fit=crop&w=600&q=80'},
        {'id': 2, 'name': 'Whole Grain Bread', 'description': 'Artisan baked daily', 'price': 4.50, 'image': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=600&q=80'},
        {'id': 3, 'name': 'Free Range Eggs', 'description': 'Dozen large eggs', 'price': 5.99, 'image': 'https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?auto=format&fit=crop&w=600&q=80'}
    ]
    return render_template('lab6/sub1_home.html', products=products)

@app.route('/lab6/1/check-stock', methods=['POST'])
def lab6_1_check_stock():
    product_id = request.form.get('productId', '')
    store_id = request.form.get('storeId', '')
    
    # VULNERABILITY: OS Command Injection
    # The storeId parameter is directly concatenated into a shell command
    # An attacker can inject commands like: 1|whoami or 1;ls or 1 && cat /etc/passwd
    try:
        command = f"echo Stock check for product {product_id} at store {store_id} && echo Units available: 42"
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True, timeout=5)
        output = result.strip()
        if 'whoami' in store_id.lower():
            output = f"{output}\n{get_random_flag('lab6', variation='variation_A')}"
        return output
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        return f"Error executing stock check: {str(e)}"

# Variation B: AutoParts Pro
@app.route('/lab6/1/b')
def lab6_1_b():
    products = [
        {'id': 101, 'name': 'Brake Pads Set', 'description': 'Ceramic compound', 'price': 89.99, 'image': 'https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?auto=format&fit=crop&w=600&q=80'},
        {'id': 102, 'name': 'Oil Filter', 'description': 'Premium filtration', 'price': 12.50, 'image': 'https://images.unsplash.com/photo-1625047509168-a7026f36de04?auto=format&fit=crop&w=600&q=80'},
        {'id': 103, 'name': 'Spark Plugs', 'description': 'Iridium tipped', 'price': 24.99, 'image': 'https://images.unsplash.com/photo-1619642751034-765dfdf7c58e?auto=format&fit=crop&w=600&q=80'}
    ]
    return render_template('lab6/sub1_b_home.html', products=products)

@app.route('/lab6/1/b/check-stock', methods=['POST'])
def lab6_1_b_check_stock():
    product_id = request.form.get('productId', '')
    location_id = request.form.get('locationId', '')
    
    # VULNERABILITY: Same OS Command Injection, different parameter name
    try:
        command = f"echo Warehouse query: SKU {product_id} at location {location_id} && echo Inventory count: 156"
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True, timeout=5)
        output = result.strip()
        if 'whoami' in location_id.lower():
            output = f"{output}\n{get_random_flag('lab6', variation='variation_B')}"
        return output
    except subprocess.TimeoutExpired:
        return "Error: Query timed out"
    except Exception as e:
        return f"System error: {str(e)}"

# Variation C: PharmaCare
@app.route('/lab6/1/c')
def lab6_1_c():
    products = [
        {'id': 201, 'name': 'Ibuprofen 200mg', 'description': 'Pain relief tablets', 'price': 8.99, 'image': 'https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=600&q=80'},
        {'id': 202, 'name': 'Vitamin D3', 'description': '5000 IU softgels', 'price': 15.99, 'image': 'https://images.unsplash.com/photo-1550572017-4a6e8c5c1f8c?auto=format&fit=crop&w=600&q=80'},
        {'id': 203, 'name': 'First Aid Kit', 'description': 'Complete emergency kit', 'price': 29.99, 'image': 'https://images.unsplash.com/photo-1603398938378-e54eab446dde?auto=format&fit=crop&w=600&q=80'}
    ]
    return render_template('lab6/sub1_c_home.html', products=products)

@app.route('/lab6/1/c/check-stock', methods=['POST'])
def lab6_1_c_check_stock():
    product_id = request.form.get('productId', '')
    branch_id = request.form.get('branchId', '')
    
    # VULNERABILITY: Same OS Command Injection, different parameter name
    try:
        command = f"echo Prescription verification: NDC {product_id} at branch {branch_id} && echo Stock level: 89 units"
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True, timeout=5)
        output = result.strip()
        if 'whoami' in branch_id.lower():
            output = f"{output}\n{get_random_flag('lab6', variation='variation_C')}"
        return output
    except subprocess.TimeoutExpired:
        return "Error: Verification timeout"
    except Exception as e:
        return f"Database error: {str(e)}"


# -------------------------
# LAB 9: Mobile Binary Analysis (Sentinel)
# -------------------------
@app.route('/lab9')
@login_required
def lab9():
    """Sentinel Mobile Analyzer - Entry Point"""
    return render_template('lab9/sub1.html')
@app.route('/lab9/analyze', methods=['POST'])
@login_required
def lab9_analyze():
    """High-Fidelity Static Binary Analyzer (Memory-Efficient Engine)"""
    if 'file' not in request.files:
        return jsonify({'error': 'No APK archive detected in request buffer.'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Null filename provided.'}), 400

    results = {
        'filename': file.filename,
        'package_name': 'Unknown.Package.Identity',
        'file_size': 0,
        'binary_hash': '',
        'findings': [],
        'archive_contents': [],
        'flags_found': []
    }

    try:
        # Save temp file for analysis
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"analyze_{uuid.uuid4().hex}.apk")
        file.save(temp_path)
        
        file_size = os.path.getsize(temp_path)
        results['file_size'] = file_size
        
        # Calculate Hash and Search for Package Name in stream
        sha256 = hashlib.sha256()
        pkg_pattern = re.compile(rb'[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+')
        found_packages = Counter()

        # Forensic Logic Signatures
        patterns = {
            'Deliverable Token (Flag)': re.compile(rb'FLAG\{[A-Za-z0-9_.-]+\}'),
            'Identity Access (AWS)': re.compile(rb'AKIA[0-9A-Z]{16}'),
            'Google/Maps Dev Key': re.compile(rb'AIza[0-9A-Za-z-_]{35}'),
            'Infrastructure Endpoint (IPv4)': re.compile(rb'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
            'Internal Research URL': re.compile(rb'https?://[a-zA-Z0-9.-]+\.sentinel-research\.io[^\s]*'),
            'Firebase DB Instance': re.compile(rb'[a-z0-9-]+\.firebaseio\.com')
        }

        # Optimized: Stream search in chunks to handle large binaries like Photoshop.apk
        with open(temp_path, 'rb') as f:
            chunk_size = 1024 * 1024 # 1MB chunks
            overlap = 2048 # To handle patterns crossing chunk boundaries
            buffer = b""
            
            while True:
                chunk = f.read(chunk_size)
                if not chunk: break
                
                sha256.update(chunk)
                search_data = buffer + chunk
                                       # Extract potential package names (heuristic)
                pkgs = pkg_pattern.findall(search_data)
                for p in pkgs:
                    p_str = p.decode('latin-1', errors='ignore')
                    if len(p_str) > 10 and '.' in p_str:
                        found_packages[p_str] += 1

                # Pattern recognition
                for label, pattern in patterns.items():
                    matches = pattern.findall(search_data)
                    for m in matches:
                        match_str = m.decode('latin-1', errors='ignore')
                        if 'Flag' in label:
                            if match_str not in results['flags_found']:
                                results['flags_found'].append(match_str)
                        
                        # Add as finding if not already present
                        cat = 'Sensitive Telemetry'
                        exists = next((item for item in results['findings'] if item['category'] == cat and label in item['detail']), None)
                        if not exists:
                            results['findings'].append({
                                'category': cat,
                                'level': 'Critical' if 'Flag' in label else 'High',
                                'detail': f"Detected {label} pattern in binary stream.",
                                'remediation': "Remove transitionary secrets and hardcoded credentials from the production binary.",
                                'risk_score': 9.5 if 'Flag' in label else 7.0
                            })
                
                buffer = chunk[-overlap:]
        
        results['binary_hash'] = sha256.hexdigest()
        
        # Determine Package Name from identified strings
        if found_packages:
            most_common = found_packages.most_common(5)
            # Heuristic: Find com.* or io.* if possible
            for p_str, count in most_common:
                if p_str.startswith('com.') or p_str.startswith('io.'):
                    results['package_name'] = p_str
                    break
        
        # 1. Forensic Archive Audit
        with zipfile.ZipFile(temp_path, 'r') as apk:
            namelist = apk.namelist()
            results['archive_contents'] = namelist[:30]
            
            dex_count = len([f for f in namelist if f.endswith('.dex')])
            so_count = len([f for f in namelist if f.endswith('.so')])
            
            if dex_count > 0:
                results['findings'].append({
                    'category': 'Architecture',
                    'level': 'Low',
                    'detail': f"Found {dex_count} Dalvik Executable (DEX) files. Standard Android bytecode detected.",
                    'remediation': "Ensure code is obfuscated to prevent easy reverse engineering.",
                    'risk_score': 1.0
                })
            
            if so_count > 0:
                results['findings'].append({
                    'category': 'Native Interface',
                    'level': 'Medium',
                    'detail': f"Application contains {so_count} native libraries (.so). Potential for memory corruption vulnerabilities.",
                    'remediation': "Verify native code for buffer overflows and ensure stack protections (ASLR/DEP) are active.",
                    'risk_score': 4.5
                })

        # Cleanup
        os.remove(temp_path)
        
    except Exception as e:
        print(f"[FORENSIC_FAILURE] Error during {file.filename} analysis: {str(e)}")
        if os.path.exists(temp_path): os.remove(temp_path)
        return jsonify({'error': f'Scanner Engine Failure: {str(e)}'}), 500

    return jsonify(results)

@app.route('/lab9/export', methods=['POST'])
@login_required
def lab9_export():
    """Export the forensic research telemetry as a structured report."""
    data = request.json
    if not data:
        return jsonify({'error': 'Null data buffer.'}), 400
        
    report = f"""# SENTINEL FORENSIC REPORT: {data.get('package_name', 'UNKNOWN_TARGET')}
    
## BINARY METADATA
- **FILENAME**: {data.get('filename', 'N/A')}
- **FILE_SIZE**: {data.get('file_size', 0)} bytes
- **SHA-256 CRYSTAL HASH**: {data.get('binary_hash', 'N/A')}
- **TIMESTAMP**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

## SECURITY FINDINGS (VULNERABILITY VECTORS)
"""
    for finding in data.get('findings', []):
        report += f"### [{finding['level'].upper()}] {finding['category']}\n- {finding['detail']}\n\n"
        
    report += "## EXTRACTED TELEMETRY (DELIVERABLES)\n"
    for flag in data.get('flags_found', []):
        report += f"- FOUND SECRET: {flag}\n"
        
    report += "\n-- END OF FORENSIC RESEARCH SESSION --\n"
    
    # Return as downloadable file
    import io
    memory_file = io.BytesIO(report.encode())
    return send_file(memory_file, download_name=f"SENTINEL_REPORT_{data.get('binary_hash', 'SCAN')[:8]}.txt", as_attachment=True, mimetype='text/plain')





@app.route('/lab9/sample')
@login_required
def lab9_sample():
    """Generate a research sample binary (JAR/APK structure) for analysis."""
    import io
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        zf.writestr('AndroidManifest.xml', 'BINARY_XML_MOCK_DATA')
        zf.writestr('classes.dex', 'DALVIK_EXECUTABLE_MOCK_DATA')
        zf.writestr('res/values/strings.xml', f'FLAG: {get_random_flag("lab9")}\nGOOGLE_API_KEY: AIza' + ''.join(random.choices(string.ascii_letters + string.digits, k=35)))
        zf.writestr('assets/secrets.conf', f'AWS_KEY=AKIA' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=16)) + '\nBACKUP_URL=https://backup.sentinel-research.io/v1/sync')
    
    memory_file.seek(0)
    return send_file(memory_file, download_name='sentinel-research-sample.apk', as_attachment=True)



if __name__ == '__main__':

    # Cloud-Native Initialization: Local DB sequence decommissioned
    app.run(debug=not IS_VERCEL, use_reloader=not IS_VERCEL, host='0.0.0.0', port=5000)


