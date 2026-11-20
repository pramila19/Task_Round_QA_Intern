import email
import imaplib
import os
import re
import time

from dotenv import load_dotenv

load_dotenv()

# Subjects we try (case-insensitive "contains"). Add your real subject if different.
SUBJECTS = ["Signup Confirm OTP", "OTP", "verification", "verify", "code"]


def _connect():
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(os.getenv("GMAIL_USER"), os.getenv("GMAIL_APP_PASSWORD"))
    mail.select("inbox")
    return mail


def _unseen_ids(mail):
    ids = set()
    for subject in SUBJECTS:
        _, data = mail.search(None, f'(UNSEEN SUBJECT "{subject}")')
        ids.update(data[0].split())
    return sorted(ids, key=lambda x: int(x))


def clear_old_otps():
    """Mark old OTP emails as read so we never pick up a stale code.
    Call this BEFORE clicking Next on step 1."""
    mail = _connect()
    for msg_id in _unseen_ids(mail):
        mail.store(msg_id, "+FLAGS", "\\Seen")
    mail.logout()


def _body_text(msg):
    body = ""
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        if part.get_content_type() in ("text/plain", "text/html"):
            payload = part.get_payload(decode=True)
            if payload:
                body += payload.decode(errors="ignore")
    body = re.sub(r"(?is)<(style|script).*?>.*?</\1>", " ", body)
    body = re.sub(r"(?s)<[^>]+>", " ", body)
    return body


def get_otp_from_gmail(timeout=90, poll_interval=5):
    end_time = time.time() + timeout
    while time.time() < end_time:
        mail = _connect()
        ids = _unseen_ids(mail)
        for msg_id in reversed(ids):  # newest first
            _, msg_data = mail.fetch(msg_id, "(RFC822)")
            body = _body_text(email.message_from_bytes(msg_data[0][1]))
            for pattern in (r"\b(\d{6})\b", r"\b(\d{4,5})\b"):
                match = re.search(pattern, body)
                if match:
                    mail.logout()
                    return match.group(1)
        mail.logout()
        time.sleep(poll_interval)
    raise TimeoutError("OTP email not received within timeout")