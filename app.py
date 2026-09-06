"""
app.py — TourConnect (SINGLE-FILE EDITION)
===========================================
Everything the project needs — database access, AI video verification,
Indic language + voice support, Firebase Analytics, the in-browser
camera/microphone recorder widgets, AND the Streamlit UI itself — lives
in this one file. Nothing else to import, no other .py modules required.

Originally this app was split across app.py / db.py / groq_verify.py /
sarvam_ai.py / firebase_analytics.py / video_recorder.py / voice_recorder.py
(plus two small HTML components). This file merges all of that together:
each former module is kept as its own clearly-labeled section below, in
the same order data flows through the app, so it's still easy to find
anything. The two tiny HTML/JS recorder widgets are embedded as string
constants and are auto-written to a hidden `_tourconnect_components`
folder next to this script the first time it runs — you never have to
create or manage that folder yourself.

--------------------------------------------------------------------------
SETUP — everything you need to edit is in the CONFIGURATION block below:
  1. MySQL connection details        (DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME)
     — set to a cloud MySQL (Aiven) by default. No local MySQL server needed.
  2. Groq API key                    (GROQ_API_KEY)        — https://console.groq.com/keys
  3. Sarvam AI API key               (SARVAM_API_KEY)      — https://dashboard.sarvam.ai
  4. Firebase Analytics (optional)   (FIREBASE_ENABLED / FIREBASE_CONFIG)

Run schema.sql once against your cloud MySQL server before starting the
app — it creates every table this file reads/writes. Then:
    pip install -r requirements.txt
    streamlit run app.py

Logging in:
  - Admin: username `admin`, password `admin123` (seeded by schema.sql —
    change it immediately via "Add New Admin" and delete the seed row).
  - Business: register via 🏢 Business Portal → "New Business Application",
    then log in once an admin approves it under 👨‍💼 Admin Panel.
  - Tourist: no password — just a name + email in 🌱 Go Green & Earn (or
    when redeeming a hotel voucher from the Tourist Portal).

⚠️ Since the DB password / Groq key / Sarvam key live directly in this
file as plain text, don't commit it to a public repo with real values
filled in — blank them out first if you ever do.
--------------------------------------------------------------------------
"""

import os
import io
import json
import uuid
import base64
import hashlib

import requests
import mysql.connector
import streamlit as st
import streamlit.components.v1 as components

try:
    from dotenv import load_dotenv
    load_dotenv()  # reads a .env file next to this script, if one exists
except ImportError:
    pass  # python-dotenv not installed — CONFIGURATION defaults below still work

try:
    import cv2
except ImportError:
    cv2 = None  # Go Green AI video verification will report itself as unavailable

try:
    from groq import Groq
except ImportError:
    Groq = None  # Go Green AI video verification will report itself as unavailable


# ==========================================================================
# CONFIGURATION — edit these values with your own details, then save.
#
# Every value below can be overridden by a ".env" file placed next to this
# script (DB_HOST=..., DB_PORT=..., DB_USER=..., DB_PASSWORD=..., DB_NAME=...).
# That's the recommended way to set real credentials (especially for a
# cloud database like Aiven/PlanetScale) so they're never hardcoded into
# source you might commit or share. If no .env is present, or a given
# variable isn't in it, the hardcoded fallback value below is used instead
# — handy for quick local testing.
# ==========================================================================

# ---- MySQL — cloud database (Aiven), no local MySQL involved ----
# Set here directly, or override via a ".env" file next to this script
# (DB_HOST=..., DB_PORT=..., DB_USER=..., DB_PASSWORD=..., DB_NAME=...).
DB_HOST = os.getenv("DB_HOST", "mysql-30c07ed9-snu-7345.j.aivencloud.com")
DB_PORT = int(os.getenv("DB_PORT", "24500"))
DB_USER = os.getenv("DB_USER", "avnadmin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "AVNS_Y3d77V11wyE9Ix0KGXi")
DB_NAME = os.getenv("DB_NAME", "Travel_connect")
DB_SSL_DISABLED = False  # Aiven requires SSL — always on, no local/no-SSL mode

# ---- Groq vision AI for Go Green video verification (formerly groq_verify.py) ----
GROQ_API_KEY = "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"                      # https://console.groq.com/keys
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
MAX_FRAMES = 5                                          # keep at/under the model's per-request image limit
AUTO_APPROVE_CONFIDENCE = 0.75                          # "Genuine" verdict at/above this auto-approves

# ---- Sarvam AI Indic language + voice support (formerly sarvam_ai.py) ----
SARVAM_API_KEY = "sk_m8utsms9_VZb4YfVeJ4G1GZKVciGETefM"             # https://dashboard.sarvam.ai
SARVAM_BASE_URL = "https://api.sarvam.ai"

# ---- Firebase Analytics — optional, off by default (formerly firebase_analytics.py) ----
FIREBASE_ENABLED = False
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyAs454Hxlfzd2hVD0eG9-36ya0xyGI6dnE",
    "authDomain": "tour-connect-9cdad.firebaseapp.com",
    "projectId": "tour-connect-9cdad",
    "storageBucket": "tour-connect-9cdad.firebasestorage.app",
    "messagingSenderId": "662515250492",
    "appId": "1:662515250492:web:3d7b7eb836ee12c8cdda39",
    "measurementId": "G-1S2PCTCK7S",
}
_FIREBASE_SDK_VERSION = "10.13.0"


# ==========================================================================
# SECTION: DATABASE LAYER  (formerly db.py)
# All MySQL access — locations/categories, the public business directory +
# business self-service portal, the admin panel, and the Go Green rewards
# system (tourists, eco submissions, vouchers, redemptions).
# ==========================================================================

def get_connection():
    """Connects to MySQL using the settings defined in CONFIGURATION above
    (or their .env overrides). ssl_disabled=False is required by managed
    providers like Aiven; local MySQL installs are fine with it disabled."""
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        ssl_disabled=DB_SSL_DISABLED,
    )


# ---- Location & category fetchers ----
def fetch_countries():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM countries")
    res = cur.fetchall()
    conn.close()
    return res


def fetch_states(country_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM states WHERE country_id=%s", (country_id,))
    res = cur.fetchall()
    conn.close()
    return res


def fetch_districts(state_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM districts WHERE state_id=%s", (state_id,))
    res = cur.fetchall()
    conn.close()
    return res


def fetch_cities(district_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM cities WHERE district_id=%s", (district_id,))
    res = cur.fetchall()
    conn.close()
    return res


def fetch_categories():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM categories")
    res = cur.fetchall()
    conn.close()
    return res


# ---- Business auth & self-service portal ----
def register_business_with_auth(owner_name, b_name, cat_id, country_id, state_id,
                                 district_id, city_id, desc, phone, email, website, password):
    """Registers a new business with a login (email + password). Starts 'Pending'."""
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    conn = get_connection()
    cur = conn.cursor()
    try:
        query = """
        INSERT INTO businesses
        (owner_name, business_name, category_id, country_id, state_id, district_id, city_id,
         description, contact_no, email, website, password_hash, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending')
        """
        cur.execute(query, (owner_name, b_name, cat_id, country_id, state_id, district_id,
                             city_id, desc, phone, email, website, hashed_pw))
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        print("Registration Error:", e)
        return False
    finally:
        conn.close()


def verify_business_login(email, password):
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    query = "SELECT * FROM businesses WHERE email = %s AND password_hash = %s"
    cur.execute(query, (email, hashed_pw))
    biz = cur.fetchone()
    conn.close()
    return biz


def update_business_profile(biz_id, b_name, owner_name, phone, website, desc):
    conn = get_connection()
    cur = conn.cursor()
    query = "UPDATE businesses SET business_name=%s, owner_name=%s, contact_no=%s, website=%s, description=%s WHERE id=%s"
    cur.execute(query, (b_name, owner_name, phone, website, desc, biz_id))
    conn.commit()
    conn.close()


def change_business_password(biz_id, new_password):
    hashed_pw = hashlib.sha256(new_password.encode()).hexdigest()
    conn = get_connection()
    cur = conn.cursor()
    query = "UPDATE businesses SET password_hash=%s WHERE id=%s"
    cur.execute(query, (hashed_pw, biz_id))
    conn.commit()
    conn.close()


def save_business_media(business_id, file_path, file_type='Image'):
    conn = get_connection()
    cur = conn.cursor()
    query = "INSERT INTO business_media (business_id, file_type, file_path) VALUES (%s, %s, %s)"
    cur.execute(query, (business_id, file_type, file_path))
    conn.commit()
    conn.close()


def fetch_business_media(business_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM business_media WHERE business_id = %s ORDER BY uploaded_at DESC", (business_id,))
    res = cur.fetchall()
    conn.close()
    return res


# ---- Catalog, offers & coverage requests ----
def add_catalog_item(business_id, item_name, price, desc):
    conn = get_connection()
    cur = conn.cursor()
    query = "INSERT INTO business_catalog (business_id, item_name, price, description) VALUES (%s, %s, %s, %s)"
    cur.execute(query, (business_id, item_name, price, desc))
    conn.commit()
    conn.close()


def add_business_offer(business_id, title, desc, discount, valid_until):
    conn = get_connection()
    cur = conn.cursor()
    query = "INSERT INTO business_offers (business_id, title, description, discount_percentage, valid_until) VALUES (%s, %s, %s, %s, %s)"
    cur.execute(query, (business_id, title, desc, discount, valid_until))
    conn.commit()
    conn.close()


def fetch_business_catalog(business_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM business_catalog WHERE business_id = %s", (business_id,))
    data = cur.fetchall()
    conn.close()
    return data


def fetch_business_offers(business_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM business_offers WHERE business_id = %s", (business_id,))
    data = cur.fetchall()
    conn.close()
    return data


def submit_location_request(biz_id, req_type, loc_name):
    conn = get_connection()
    cur = conn.cursor()
    query = "INSERT INTO location_requests (business_id, requested_type, location_name) VALUES (%s, %s, %s)"
    cur.execute(query, (biz_id, req_type, loc_name))
    conn.commit()
    conn.close()


def submit_category_request(biz_id, cat_name):
    conn = get_connection()
    cur = conn.cursor()
    query = "INSERT INTO category_requests (business_id, category_name) VALUES (%s, %s)"
    cur.execute(query, (biz_id, cat_name))
    conn.commit()
    conn.close()


# ---- Admin review of business coverage requests ----
def get_pending_location_requests():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    query = """
    SELECT r.*, b.business_name
    FROM location_requests r
    JOIN businesses b ON r.business_id = b.id
    WHERE r.status = 'Pending'
    ORDER BY r.created_at ASC
    """
    cur.execute(query)
    res = cur.fetchall()
    conn.close()
    return res


def update_location_request_status(request_id, status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE location_requests SET status=%s WHERE id=%s", (status, request_id))
    conn.commit()
    conn.close()


def get_pending_category_requests():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    query = """
    SELECT r.*, b.business_name
    FROM category_requests r
    JOIN businesses b ON r.business_id = b.id
    WHERE r.status = 'Pending'
    ORDER BY r.created_at ASC
    """
    cur.execute(query)
    res = cur.fetchall()
    conn.close()
    return res


def update_category_request_status(request_id, status, approve_and_add=False):
    """
    status: 'Approved' or 'Rejected'. If approve_and_add is True and the
    category name doesn't already exist, it's inserted into `categories`
    so it immediately shows up in the dropdowns everywhere.
    """
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT category_name FROM category_requests WHERE id=%s", (request_id,))
    row = cur.fetchone()

    cur2 = conn.cursor()
    cur2.execute("UPDATE category_requests SET status=%s WHERE id=%s", (status, request_id))

    if status == "Approved" and approve_and_add and row and row["category_name"]:
        cur2.execute("INSERT IGNORE INTO categories (name) VALUES (%s)", (row["category_name"],))

    conn.commit()
    conn.close()


# ---- Public directory & admin — businesses ----
def search_businesses(city_id, category_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    query = """
    SELECT b.*, c.name as category_name
    FROM businesses b
    JOIN categories c ON b.category_id = c.id
    WHERE b.city_id = %s AND b.category_id = %s AND b.status = 'Approved'
    """
    cur.execute(query, (city_id, category_id))
    res = cur.fetchall()
    conn.close()
    return res


def search_businesses_by_text(query_text, limit=20):
    """
    Free-text search across approved businesses, used by the Tourist
    Portal's voice search (and usable for a typed search too). Matches
    against business name, description, category name, and city name, so
    a translated voice query like "hotel in jaipur" or "eco friendly
    homestay" finds something even without picking dropdowns first.
    """
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    like = f"%{query_text.strip()}%"
    cur.execute(
        """
        SELECT b.*, c.name as category_name, ct.name as city_name
        FROM businesses b
        JOIN categories c ON b.category_id = c.id
        JOIN cities ct ON b.city_id = ct.id
        WHERE b.status = 'Approved'
          AND (
                b.business_name LIKE %s
                OR b.description LIKE %s
                OR c.name LIKE %s
                OR ct.name LIKE %s
              )
        ORDER BY b.rating DESC
        LIMIT %s
        """,
        (like, like, like, like, limit),
    )
    res = cur.fetchall()
    conn.close()
    return res


def get_pending_businesses():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    query = """
    SELECT b.id, b.business_name, b.owner_name, b.contact_no, c.name as category
    FROM businesses b
    JOIN categories c ON b.category_id = c.id
    WHERE b.status = 'Pending'
    """
    cur.execute(query)
    res = cur.fetchall()
    conn.close()
    return res


def update_status(business_id, status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE businesses SET status=%s WHERE id=%s", (status, business_id))
    conn.commit()
    conn.close()


def update_rating(business_id, rating):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE businesses SET rating=%s WHERE id=%s", (rating, business_id))
    conn.commit()
    conn.close()


# ---- Admin auth ----
def verify_admin(username, password):
    hashed_input = hashlib.sha256(password.encode()).hexdigest()
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    query = "SELECT * FROM admin_users WHERE username = %s AND password_hash = %s"
    cur.execute(query, (username, hashed_input))
    user = cur.fetchone()
    conn.close()
    return user is not None


def add_new_admin(username, password):
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    conn = get_connection()
    cur = conn.cursor()
    try:
        query = "INSERT INTO admin_users (username, password_hash) VALUES (%s, %s)"
        cur.execute(query, (username, hashed_pw))
        conn.commit()
        return True
    except Exception as e:
        print("Error adding admin:", e)
        return False
    finally:
        conn.close()


# ---- Go Green: tourists, eco submissions, vouchers, redemptions ----
def get_or_create_tourist(name, email, phone=""):
    """Looks up a tourist by email; creates the record on first visit."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM tourists WHERE email=%s", (email,))
    existing = cur.fetchone()
    if existing:
        conn.close()
        return existing

    cur2 = conn.cursor()
    cur2.execute(
        "INSERT INTO tourists (name, email, phone) VALUES (%s, %s, %s)",
        (name, email, phone),
    )
    conn.commit()
    new_id = cur2.lastrowid
    conn.close()
    return {"id": new_id, "name": name, "email": email, "phone": phone, "points": 0}


def get_tourist_by_email(email):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM tourists WHERE email=%s", (email,))
    res = cur.fetchone()
    conn.close()
    return res


def create_eco_submission(tourist_id, activity_type, video_path, ai_result):
    """Stores the upload + AI suggestion. Always starts as 'Pending' for admin review."""
    conn = get_connection()
    cur = conn.cursor()
    query = """
    INSERT INTO eco_submissions
        (tourist_id, activity_type, video_path, ai_verdict, ai_confidence, ai_reasoning, points_suggested, status)
    VALUES (%s, %s, %s, %s, %s, %s, %s, 'Pending')
    """
    cur.execute(query, (
        tourist_id, activity_type, video_path,
        ai_result.get("verdict", "Uncertain"),
        ai_result.get("confidence", 0.0),
        ai_result.get("reasoning", ""),
        ai_result.get("points_suggested", 0),
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_eco_submission_ai(submission_id, ai_result):
    """Overwrites the stored AI verdict/confidence/reasoning/points on a
    submission — used when a tourist hits 'Try AI Check Again' after the
    AI service failed or gave an Uncertain/Fake read the first time."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE eco_submissions
        SET ai_verdict=%s, ai_confidence=%s, ai_reasoning=%s, points_suggested=%s
        WHERE id=%s
        """,
        (
            ai_result.get("verdict", "Uncertain"),
            ai_result.get("confidence", 0.0),
            ai_result.get("reasoning", ""),
            ai_result.get("points_suggested", 0),
            submission_id,
        ),
    )
    conn.commit()
    conn.close()


def get_pending_eco_submissions():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    query = """
    SELECT s.*, t.name AS tourist_name, t.email AS tourist_email
    FROM eco_submissions s
    JOIN tourists t ON s.tourist_id = t.id
    WHERE s.status = 'Pending'
    ORDER BY s.submitted_at DESC
    """
    cur.execute(query)
    res = cur.fetchall()
    conn.close()
    return res


def get_all_eco_submissions():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    query = """
    SELECT s.*, t.name AS tourist_name, t.email AS tourist_email
    FROM eco_submissions s
    JOIN tourists t ON s.tourist_id = t.id
    ORDER BY s.created_at DESC
    """
    cur.execute(query)
    res = cur.fetchall()
    conn.close()
    return res


def decide_eco_submission(submission_id, tourist_id, decision, points_awarded, reviewed_by):
    """
    decision: 'Approved' or 'Rejected'. This is the admin's final call —
    the AI verdict is only ever a suggestion feeding into this screen.
    On approval, points_awarded is credited to the tourist's balance.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE eco_submissions SET status=%s, points_awarded=%s, reviewed_by=%s WHERE id=%s",
        (decision, points_awarded if decision == "Approved" else 0, reviewed_by, submission_id),
    )
    if decision == "Approved" and points_awarded > 0:
        cur.execute(
            "UPDATE tourists SET points = points + %s WHERE id=%s",
            (points_awarded, tourist_id),
        )
    conn.commit()
    conn.close()


def get_active_vouchers():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM vouchers WHERE active=1 AND stock > 0 ORDER BY points_required ASC")
    res = cur.fetchall()
    conn.close()
    return res


def get_voucher_for_partner(partner_name):
    """
    Finds an active, in-stock voucher tied to a specific hotel/partner name,
    so the Tourist Portal can surface the same reward that appears in the
    Go Green "Redeem Vouchers" tab, right on that hotel's listing.
    """
    if not partner_name:
        return None

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """
        SELECT * FROM vouchers 
    WHERE partner_name = %s
        ORDER BY points_required ASC
        LIMIT 1
        """,
        (partner_name,),
    )
    voucher = cur.fetchone()

    if not voucher:
        cur.execute(
            """
            SELECT * FROM vouchers
            WHERE active = 1 AND stock > 0
              AND (
                    LOWER(partner_name) LIKE CONCAT('%%', LOWER(%s), '%%')
                    OR LOWER(%s) LIKE CONCAT('%%', LOWER(partner_name), '%%')
                  )
            ORDER BY points_required ASC
            LIMIT 1
            """,
            (partner_name, partner_name),
        )
        voucher = cur.fetchone()

    conn.close()
    return voucher


def redeem_voucher(tourist_id, voucher_id):
    """Atomically checks points/stock, deducts both, and logs the redemption."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM tourists WHERE id=%s FOR UPDATE", (tourist_id,))
    tourist = cur.fetchone()
    cur.execute("SELECT * FROM vouchers WHERE id=%s FOR UPDATE", (voucher_id,))
    voucher = cur.fetchone()

    if not tourist or not voucher:
        conn.close()
        return False, "Not found."
    if tourist["points"] < voucher["points_required"]:
        conn.close()
        return False, "Not enough points."
    if voucher["stock"] <= 0:
        conn.close()
        return False, "Voucher out of stock."

    cur2 = conn.cursor()
    cur2.execute("UPDATE tourists SET points = points - %s WHERE id=%s",
                 (voucher["points_required"], tourist_id))
    cur2.execute("UPDATE vouchers SET stock = stock - 1 WHERE id=%s", (voucher_id,))
    cur2.execute(
        "INSERT INTO redemptions (tourist_id, voucher_id, points_spent) VALUES (%s, %s, %s)",
        (tourist_id, voucher_id, voucher["points_required"]),
    )
    conn.commit()
    conn.close()
    return True, "Redeemed!"


# ==========================================================================
# SECTION: AI VIDEO VERIFICATION  (formerly groq_verify.py)
# Groq's chat API doesn't accept raw video, so: pull a handful of evenly
# spaced frames out of the uploaded video (OpenCV), send those frames + a
# prompt to a Groq vision model, and ask it to return strict JSON:
# verdict / confidence / reasoning.
# ==========================================================================

def extract_frames(video_path: str, num_frames: int = MAX_FRAMES):
    """Grab `num_frames` evenly spaced frames from the video as base64 JPEGs."""
    if cv2 is None:
        return []

    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []

    if total <= 0:
        cap.release()
        return frames

    step = max(total // num_frames, 1)
    for i in range(num_frames):
        frame_index = min(i * step, total - 1)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = cap.read()
        if not ok:
            continue
        # Downscale a bit — keeps each image well under Groq's per-image size limit
        # and keeps the request fast/cheap.
        h, w = frame.shape[:2]
        if w > 800:
            scale = 800 / w
            frame = cv2.resize(frame, (800, int(h * scale)))
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if ok:
            frames.append(base64.b64encode(buf).decode("utf-8"))

    cap.release()
    return frames


def _fallback_result(reason: str):
    # service_ok=False means the AI itself couldn't run (missing key, network
    # error, bad video file, etc.) — NOT that it looked at the video and
    # judged it fake. The UI shows a "we can't check this right now, it'll be
    # reviewed within 24-48 hrs" message instead of a rejection.
    return {
        "verdict": "Uncertain",
        "confidence": 0.0,
        "reasoning": reason,
        "points_suggested": 0,
        "service_ok": False,
    }


def analyze_submission(video_path: str, activity_type: str) -> dict:
    """
    Returns a dict: {verdict, confidence, reasoning, points_suggested, service_ok}
    verdict is one of 'Genuine' / 'Fake' / 'Uncertain'.
    service_ok is False only when the AI check itself couldn't run at all
    (no API key, network/API error, unreadable video) — it is True whenever
    the model actually returned a judgement, even 'Fake' or 'Uncertain'.
    This function never touches the database or awards points — the caller
    decides what to do with the result (auto-approve / queue for admin /
    show a "try again later" message).
    """
    if Groq is None:
        return _fallback_result("The 'groq' package isn't installed — skipped AI check, needs manual review.")

    api_key = GROQ_API_KEY
    if not api_key or api_key == "gsk_your_key_here":
        return _fallback_result("GROQ_API_KEY is not set in the CONFIGURATION section — skipped AI check, needs manual review.")

    frames = extract_frames(video_path)
    if not frames:
        return _fallback_result("Could not read any frames from the uploaded video file.")

    prompt = (
        "You are a fraud-detection reviewer for a tourism sustainability rewards program. "
        f"A user submitted a video claiming to show them personally doing a '{activity_type}' "
        "eco-friendly activity (for example: planting a tree, cleaning up litter, or segregating "
        "waste) in order to earn reward points. You are shown several frames sampled from that video.\n\n"
        "Judge whether the activity shown looks like a real, currently-performed action by the "
        "person filming it, or whether it looks staged, reused/stock footage, a photo of a screen, "
        "AI-generated, unrelated to the claimed activity, or otherwise not genuine.\n\n"
        "Respond with STRICT JSON only, no extra text, in exactly this shape:\n"
        '{"verdict": "Genuine" | "Fake" | "Uncertain", "confidence": <0.0-1.0>, '
        '"reasoning": "<1-3 short sentences>"}'
    )

    content = [{"type": "text", "text": prompt}]
    for f in frames:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{f}"},
        })

    raw = ""
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[{"role": "user", "content": content}],
            temperature=0.2,
            max_tokens=300,
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
    except json.JSONDecodeError:
        return _fallback_result(f"Model returned non-JSON output, needs manual review: {raw[:200]}")
    except Exception as e:
        return _fallback_result(f"AI check failed ({e}), needs manual review.")

    verdict = data.get("verdict", "Uncertain")
    if verdict not in ("Genuine", "Fake", "Uncertain"):
        verdict = "Uncertain"
    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))
    reasoning = str(data.get("reasoning", ""))[:500]

    # Simple, transparent points heuristic — tune freely for your event.
    # Admin can always override the final awarded amount for anything that
    # lands in the manual queue.
    if verdict == "Genuine" and confidence >= AUTO_APPROVE_CONFIDENCE:
        points_suggested = 50
    elif verdict == "Genuine":
        points_suggested = 25
    elif verdict == "Uncertain":
        points_suggested = 10
    else:
        points_suggested = 0

    return {
        "verdict": verdict,
        "confidence": confidence,
        "reasoning": reasoning,
        "points_suggested": points_suggested,
        "service_ok": True,
    }


# ==========================================================================
# SECTION: SARVAM AI — INDIC LANGUAGE + VOICE SUPPORT  (formerly sarvam_ai.py)
# Wraps three Sarvam AI APIs: /translate (text->text), /speech-to-text
# (voice->text, optionally translated to English), and /text-to-speech
# (text->spoken audio).
#
# Garhwali note: no major Indic-language AI service (Sarvam included) has a
# dedicated Garhwali model — it isn't one of India's 22 officially
# scheduled languages. Since Garhwali is written in Devanagari and its
# speakers are overwhelmingly also fluent in Hindi, the picker offers
# "Garhwali" but routes it through Hindi (hi-IN) under the hood, with a
# note in the UI so nobody's misled into thinking there's real Garhwali
# translation happening.
# ==========================================================================

# Languages offered in the app's picker: code -> display label. Codes are
# Sarvam's BCP-47-style codes. "gw-IN" is NOT a real Sarvam code — it's our
# own placeholder that _resolve_lang() maps to Hindi (hi-IN) below.
LANGUAGES = {
    "en-IN": "English",
    "hi-IN": "Hindi",
    "gw-IN": "Garhwali (गढ़वळि) — via Hindi",
    "bn-IN": "Bengali",
    "gu-IN": "Gujarati",
    "kn-IN": "Kannada",
    "ml-IN": "Malayalam",
    "mr-IN": "Marathi",
    "od-IN": "Odia",
    "pa-IN": "Punjabi",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
    "ur-IN": "Urdu",
    "ne-IN": "Nepali",
}

# Sarvam's Bulbul TTS model only speaks a subset of the languages Sarvam
# can translate/transcribe into. Anything not in this set falls back to
# text-only (no "🔊 Listen" audio) rather than erroring.
_TTS_SUPPORTED = {
    "en-IN", "hi-IN", "gw-IN", "bn-IN", "gu-IN", "kn-IN",
    "ml-IN", "mr-IN", "od-IN", "pa-IN", "ta-IN", "te-IN",
}


def _resolve_lang(lang_code):
    """Garhwali has no real Sarvam model — call Hindi under the hood."""
    return "hi-IN" if lang_code == "gw-IN" else lang_code


def is_configured():
    return bool(SARVAM_API_KEY) and SARVAM_API_KEY != "your_sarvam_api_key_here"


def tts_supported(lang_code):
    return lang_code in _TTS_SUPPORTED


def _sarvam_headers():
    return {"api-subscription-key": SARVAM_API_KEY}


@st.cache_data(show_spinner=False, ttl=3600)
def translate_text(text, target_lang_code, source_lang_code="en-IN"):
    """
    Translates `text` from source_lang_code to target_lang_code using
    Sarvam's sarvam-translate:v1 model (widest language coverage).
    Returns the translated string, or the original text unchanged if
    Sarvam isn't configured, the languages match, or the call fails —
    callers don't need to special-case failures, the UI just stays in
    whatever language it already had.
    """
    target_lang_code = _resolve_lang(target_lang_code)
    source_lang_code = _resolve_lang(source_lang_code)

    if not text or not text.strip() or target_lang_code == source_lang_code:
        return text
    if not is_configured():
        return text

    try:
        resp = requests.post(
            f"{SARVAM_BASE_URL}/translate",
            headers=_sarvam_headers(),
            json={
                "input": text[:2000],  # sarvam-translate:v1 cap
                "source_language_code": source_lang_code,
                "target_language_code": target_lang_code,
                "model": "sarvam-translate:v1",
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("translated_text", text)
    except Exception:
        # Network hiccup, quota exceeded, bad key, etc. — degrade to
        # English rather than breaking the page.
        return text


def speech_to_text(audio_bytes, filename="speech.webm", translate_to_english=True):
    """
    Sends recorded audio to Sarvam's Saaras v3 speech-to-text model.

    If translate_to_english is True, asks Saaras to translate the speech
    directly into English (mode="translate") regardless of which Indic
    language was spoken — handy for feeding into an English-only search/
    matching function without a separate translate step. If False, returns
    a plain transcript in the language spoken.

    Returns (text, detected_language_code) — (None, None) if Sarvam isn't
    configured or the call fails.
    """
    if not is_configured():
        return None, None

    try:
        files = {"file": (filename, audio_bytes, "audio/webm")}
        data = {
            "model": "saaras:v3",
            "language_code": "unknown",  # auto-detect the spoken language
            "mode": "translate" if translate_to_english else "transcribe",
        }
        resp = requests.post(
            f"{SARVAM_BASE_URL}/speech-to-text",
            headers=_sarvam_headers(),
            files=files,
            data=data,
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
        return body.get("transcript"), body.get("language_code")
    except Exception:
        return None, None


def text_to_speech(text, target_lang_code, speaker="anushka"):
    """
    Synthesizes `text` in target_lang_code using Sarvam's Bulbul v3 TTS.
    Returns raw WAV audio bytes, or None if Sarvam isn't configured, the
    language has no TTS voice, the text is empty, or the call fails.
    """
    target_lang_code = _resolve_lang(target_lang_code)

    if not text or not text.strip() or not is_configured():
        return None
    if not tts_supported(target_lang_code):
        return None

    try:
        resp = requests.post(
            f"{SARVAM_BASE_URL}/text-to-speech",
            headers=_sarvam_headers(),
            json={
                "text": text[:1500],
                "target_language_code": target_lang_code,
                "model": "bulbul:v3",
                "speaker": speaker,
            },
            timeout=30,
        )
        resp.raise_for_status()
        audios = resp.json().get("audios", [])
        if not audios:
            return None
        return base64.b64decode(audios[0])
    except Exception:
        return None


# ==========================================================================
# SECTION: FIREBASE ANALYTICS — optional  (formerly firebase_analytics.py)
# Streamlit doesn't give a supported way to inject arbitrary <script> tags
# into the real top-level page, so this uses the standard workaround: a
# components.html() call whose JS reaches out to `window.parent.document`
# (the real page, since the iframe is same-origin) and appends the real
# Firebase/gtag script tags there. No new pip dependency — Firebase loads
# from Google's CDN in the browser.
# ==========================================================================

def init():
    """
    Loads the Firebase compat SDK (app + analytics) into the parent page
    and calls firebase.initializeApp(...) + firebase.analytics() once.
    Safe to call on every rerun — it guards against double-loading with a
    flag on window.parent. No-op unless FIREBASE_ENABLED=True.
    """
    if not FIREBASE_ENABLED:
        return
    components.html(
        f"""
        <script>
        (function() {{
            var top = window.parent;
            if (top.__tourconnect_firebase_ready || top.__tourconnect_firebase_loading) {{
                return;
            }}
            top.__tourconnect_firebase_loading = true;

            function loadScript(src) {{
                return new Promise(function(resolve, reject) {{
                    var s = top.document.createElement('script');
                    s.src = src;
                    s.onload = resolve;
                    s.onerror = reject;
                    top.document.head.appendChild(s);
                }});
            }}

            loadScript("https://www.gstatic.com/firebasejs/{_FIREBASE_SDK_VERSION}/firebase-app-compat.js")
                .then(function() {{
                    return loadScript("https://www.gstatic.com/firebasejs/{_FIREBASE_SDK_VERSION}/firebase-analytics-compat.js");
                }})
                .then(function() {{
                    var config = {json.dumps(FIREBASE_CONFIG)};
                    top.firebase.initializeApp(config);
                    top.firebase.analytics();
                    top.__tourconnect_firebase_ready = true;
                }})
                .catch(function(err) {{
                    console.error("Firebase Analytics failed to load:", err);
                }});
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


def log_event(event_name, params=None):
    """
    Logs a custom Firebase Analytics event from the parent page. Streamlit
    reruns the whole script on every interaction rather than doing real
    page navigation, so this is how you get the equivalent of page-view /
    section-view / action events. No-op unless FIREBASE_ENABLED=True.
    """
    if not FIREBASE_ENABLED:
        return
    params = params or {}
    components.html(
        f"""
        <script>
        (function() {{
            var top = window.parent;
            function fire() {{
                if (top.firebase && top.firebase.analytics) {{
                    top.firebase.analytics().logEvent(
                        {json.dumps(event_name)}, {json.dumps(params)}
                    );
                }}
            }}
            if (top.__tourconnect_firebase_ready) {{
                fire();
            }} else {{
                // Analytics may still be loading (init() runs on the same
                // rerun) — poll briefly rather than dropping the event.
                var tries = 0;
                var iv = setInterval(function() {{
                    tries += 1;
                    if (top.__tourconnect_firebase_ready) {{
                        clearInterval(iv);
                        fire();
                    }} else if (tries > 20) {{
                        clearInterval(iv);
                    }}
                }}, 250);
            }}
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


def log_page_view(section_name):
    """Convenience wrapper: logs a 'page_view' event for a nav section."""
    log_event("page_view", {"page_title": section_name, "page_location": section_name})


# ==========================================================================
# SECTION: IN-BROWSER CAMERA/MICROPHONE RECORDERS
# (formerly video_recorder.py + voice_recorder.py, plus their two
# components/*/index.html static assets)
#
# Streamlit's components.v1.declare_component() needs a real directory on
# disk containing an index.html — it can't take raw HTML as a Python string
# directly for a stateful (bidirectional) component. So this file embeds
# both tiny widgets' HTML/JS as string constants below and auto-writes them
# to a hidden `_tourconnect_components` folder next to this script the first
# time it runs (and re-writes them if this file's copy ever changes). You
# never have to create or manage that folder by hand — it's regenerated
# automatically, so this .py file is still the only thing you need to copy
# around or version-control.
# ==========================================================================

_VIDEO_RECORDER_HTML = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8" />
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 8px;
    font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, sans-serif;
    background: transparent;
  }
  #wrap { max-width: 480px; }
  video {
    width: 100%;
    max-height: 320px;
    background: #000;
    border-radius: 8px;
    display: block;
  }
  .row { margin-top: 8px; display: flex; gap: 8px; flex-wrap: wrap; }
  button {
    border: 1px solid #d0d0d0;
    background: #ffffff;
    color: #262730;
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 14px;
    cursor: pointer;
  }
  button:disabled { opacity: 0.4; cursor: not-allowed; }
  button.primary { background: #21c45d; color: white; border-color: #21c45d; }
  button.danger { background: #ff4b4b; color: white; border-color: #ff4b4b; }
  #status { margin-top: 6px; font-size: 13px; color: #555; min-height: 18px; }
  #timer { font-weight: 600; color: #ff4b4b; }
</style>
</head>
<body>
<div id="wrap">
  <video id="live" autoplay muted playsinline></video>
  <video id="playback" controls playsinline style="display:none;"></video>

  <div class="row">
    <button id="btnStart">🔴 Start Recording</button>
    <button id="btnStop" disabled>⏹ Stop</button>
    <button id="btnUse" class="primary" style="display:none;">✅ Use this recording</button>
    <button id="btnRetake" class="danger" style="display:none;">🔁 Retake</button>
  </div>
  <div id="status">Click "Start Recording" and allow camera access.</div>
</div>

<script>
  // ---- Minimal Streamlit component <-> parent messaging (no external JS needed) ----
  function sendMessageToStreamlitClient(type, data) {
    var outData = Object.assign({ isStreamlitMessage: true, type: type }, data);
    window.parent.postMessage(outData, "*");
  }
  function notifyRender() {
    sendMessageToStreamlitClient("streamlit:componentReady", { apiVersion: 1 });
  }
  function setFrameHeight() {
    var h = document.getElementById("wrap").scrollHeight + 24;
    sendMessageToStreamlitClient("streamlit:setFrameHeight", { height: h });
  }
  function sendValue(value) {
    sendMessageToStreamlitClient("streamlit:setComponentValue", { value: value, dataType: "json" });
  }

  const MAX_SECONDS = 60; // auto-stop safety cap so uploads stay a reasonable size

  const liveVideo = document.getElementById("live");
  const playbackVideo = document.getElementById("playback");
  const btnStart = document.getElementById("btnStart");
  const btnStop = document.getElementById("btnStop");
  const btnUse = document.getElementById("btnUse");
  const btnRetake = document.getElementById("btnRetake");
  const statusEl = document.getElementById("status");

  let mediaStream = null;
  let mediaRecorder = null;
  let chunks = [];
  let recordedBlob = null;
  let timerInterval = null;
  let secondsElapsed = 0;

  function pickMimeType() {
    const candidates = [
      "video/webm;codecs=vp9,opus",
      "video/webm;codecs=vp8,opus",
      "video/webm",
      "video/mp4",
    ];
    for (const c of candidates) {
      if (window.MediaRecorder && MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(c)) {
        return c;
      }
    }
    return "";
  }

  async function startCamera() {
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      liveVideo.srcObject = mediaStream;
    } catch (err) {
      statusEl.textContent = "⚠️ Could not access camera/mic: " + err.message;
      throw err;
    }
  }

  async function startRecording() {
    statusEl.textContent = "Requesting camera access...";
    try {
      if (!mediaStream) await startCamera();
    } catch (e) {
      return;
    }
    chunks = [];
    recordedBlob = null;
    const mimeType = pickMimeType();
    try {
      mediaRecorder = mimeType ? new MediaRecorder(mediaStream, { mimeType }) : new MediaRecorder(mediaStream);
    } catch (e) {
      statusEl.textContent = "⚠️ Recording isn't supported in this browser.";
      return;
    }
    mediaRecorder.ondataavailable = (e) => { if (e.data && e.data.size > 0) chunks.push(e.data); };
    mediaRecorder.onstop = onRecordingStopped;
    mediaRecorder.start();

    secondsElapsed = 0;
    timerInterval = setInterval(() => {
      secondsElapsed += 1;
      statusEl.innerHTML = "Recording... <span id='timer'>" + secondsElapsed + "s</span> (auto-stops at " + MAX_SECONDS + "s)";
      if (secondsElapsed >= MAX_SECONDS) stopRecording();
    }, 1000);

    btnStart.disabled = true;
    btnStop.disabled = false;
    setFrameHeight();
  }

  function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }
    clearInterval(timerInterval);
    btnStop.disabled = true;
  }

  function onRecordingStopped() {
    const mimeType = (mediaRecorder && mediaRecorder.mimeType) || "video/webm";
    recordedBlob = new Blob(chunks, { type: mimeType });

    liveVideo.style.display = "none";
    playbackVideo.style.display = "block";
    playbackVideo.src = URL.createObjectURL(recordedBlob);

    btnStart.style.display = "none";
    btnStop.style.display = "none";
    btnUse.style.display = "inline-block";
    btnRetake.style.display = "inline-block";
    statusEl.textContent = "Recording finished (" + secondsElapsed + "s). Review it, then use it or retake.";

    if (mediaStream) {
      mediaStream.getTracks().forEach((t) => t.stop());
      mediaStream = null;
    }
    setFrameHeight();
  }

  function useRecording() {
    if (!recordedBlob) return;
    statusEl.textContent = "Preparing video for upload...";
    const reader = new FileReader();
    reader.onloadend = () => {
      sendValue(reader.result); // data:video/webm;base64,....
      statusEl.textContent = "✅ Video ready — go back to Streamlit and click 'Submit for AI Review'.";
      btnUse.disabled = true;
    };
    reader.readAsDataURL(recordedBlob);
  }

  function retake() {
    recordedBlob = null;
    playbackVideo.style.display = "none";
    playbackVideo.removeAttribute("src");
    liveVideo.style.display = "block";
    btnStart.style.display = "inline-block";
    btnStop.style.display = "inline-block";
    btnUse.style.display = "none";
    btnUse.disabled = false;
    btnRetake.style.display = "none";
    btnStart.disabled = false;
    btnStop.disabled = true;
    statusEl.textContent = 'Click "Start Recording" and allow camera access.';
    sendValue(null);
    startCamera().catch(() => {});
    setFrameHeight();
  }

  btnStart.addEventListener("click", startRecording);
  btnStop.addEventListener("click", stopRecording);
  btnUse.addEventListener("click", useRecording);
  btnRetake.addEventListener("click", retake);

  window.addEventListener("load", () => {
    notifyRender();
    setFrameHeight();
    startCamera().catch(() => {});
  });
</script>
</body>
</html>
"""

_VOICE_RECORDER_HTML = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8" />
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 8px;
    font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, sans-serif;
    background: transparent;
  }
  #wrap { max-width: 420px; }
  .row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
  button {
    border: 1px solid #d0d0d0;
    background: #ffffff;
    color: #262730;
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 14px;
    cursor: pointer;
  }
  button:disabled { opacity: 0.4; cursor: not-allowed; }
  button.primary { background: #21c45d; color: white; border-color: #21c45d; }
  button.danger { background: #ff4b4b; color: white; border-color: #ff4b4b; }
  #status { margin-top: 6px; font-size: 13px; color: #555; min-height: 18px; }
  #timer { font-weight: 600; color: #ff4b4b; }
  #mic-icon { font-size: 20px; }
  audio { width: 100%; margin-top: 6px; display: none; }
</style>
</head>
<body>
<div id="wrap">
  <div class="row">
    <span id="mic-icon">🎙️</span>
    <button id="btnStart">Start Speaking</button>
    <button id="btnStop" disabled>⏹ Stop</button>
    <button id="btnUse" class="primary" style="display:none;">✅ Use this</button>
    <button id="btnRetake" class="danger" style="display:none;">🔁 Retry</button>
  </div>
  <audio id="playback" controls></audio>
  <div id="status">Tap "Start Speaking" and allow microphone access.</div>
</div>

<script>
  function sendMessageToStreamlitClient(type, data) {
    var outData = Object.assign({ isStreamlitMessage: true, type: type }, data);
    window.parent.postMessage(outData, "*");
  }
  function notifyRender() {
    sendMessageToStreamlitClient("streamlit:componentReady", { apiVersion: 1 });
  }
  function setFrameHeight() {
    var h = document.getElementById("wrap").scrollHeight + 24;
    sendMessageToStreamlitClient("streamlit:setFrameHeight", { height: h });
  }
  function sendValue(value) {
    sendMessageToStreamlitClient("streamlit:setComponentValue", { value: value, dataType: "json" });
  }

  const MAX_SECONDS = 20; // speech clips should be short — keeps STT fast & cheap

  const btnStart = document.getElementById("btnStart");
  const btnStop = document.getElementById("btnStop");
  const btnUse = document.getElementById("btnUse");
  const btnRetake = document.getElementById("btnRetake");
  const statusEl = document.getElementById("status");
  const playback = document.getElementById("playback");

  let mediaStream = null;
  let mediaRecorder = null;
  let chunks = [];
  let recordedBlob = null;
  let timerInterval = null;
  let secondsElapsed = 0;

  function pickMimeType() {
    const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
    for (const c of candidates) {
      if (window.MediaRecorder && MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported(c)) return c;
    }
    return "";
  }

  async function startRecording() {
    statusEl.textContent = "Requesting microphone access...";
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      statusEl.textContent = "⚠️ Could not access microphone: " + err.message;
      return;
    }

    chunks = [];
    recordedBlob = null;
    const mimeType = pickMimeType();
    try {
      mediaRecorder = mimeType ? new MediaRecorder(mediaStream, { mimeType }) : new MediaRecorder(mediaStream);
    } catch (e) {
      statusEl.textContent = "⚠️ Recording isn't supported in this browser.";
      return;
    }
    mediaRecorder.ondataavailable = (e) => { if (e.data && e.data.size > 0) chunks.push(e.data); };
    mediaRecorder.onstop = onRecordingStopped;
    mediaRecorder.start();

    secondsElapsed = 0;
    timerInterval = setInterval(() => {
      secondsElapsed += 1;
      statusEl.innerHTML = "🔴 Listening... <span id='timer'>" + secondsElapsed + "s</span> (auto-stops at " + MAX_SECONDS + "s)";
      if (secondsElapsed >= MAX_SECONDS) stopRecording();
    }, 1000);

    btnStart.disabled = true;
    btnStop.disabled = false;
    setFrameHeight();
  }

  function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop();
    clearInterval(timerInterval);
    btnStop.disabled = true;
  }

  function onRecordingStopped() {
    const mimeType = (mediaRecorder && mediaRecorder.mimeType) || "audio/webm";
    recordedBlob = new Blob(chunks, { type: mimeType });

    playback.style.display = "block";
    playback.src = URL.createObjectURL(recordedBlob);

    btnStart.style.display = "none";
    btnStop.style.display = "none";
    btnUse.style.display = "inline-block";
    btnRetake.style.display = "inline-block";
    statusEl.textContent = "Got it (" + secondsElapsed + "s). Listen back, then use it or retry.";

    if (mediaStream) {
      mediaStream.getTracks().forEach((t) => t.stop());
      mediaStream = null;
    }
    setFrameHeight();
  }

  function useRecording() {
    if (!recordedBlob) return;
    statusEl.textContent = "Sending...";
    const reader = new FileReader();
    reader.onloadend = () => {
      sendValue(reader.result);
      statusEl.textContent = "✅ Sent — processing in the app below.";
      btnUse.disabled = true;
    };
    reader.readAsDataURL(recordedBlob);
  }

  function retake() {
    recordedBlob = null;
    playback.style.display = "none";
    playback.removeAttribute("src");
    btnStart.style.display = "inline-block";
    btnStop.style.display = "inline-block";
    btnUse.style.display = "none";
    btnUse.disabled = false;
    btnRetake.style.display = "none";
    btnStart.disabled = false;
    btnStop.disabled = true;
    statusEl.textContent = 'Tap "Start Speaking" and allow microphone access.';
    sendValue(null);
    setFrameHeight();
  }

  btnStart.addEventListener("click", startRecording);
  btnStop.addEventListener("click", stopRecording);
  btnUse.addEventListener("click", useRecording);
  btnRetake.addEventListener("click", retake);

  window.addEventListener("load", () => {
    notifyRender();
    setFrameHeight();
  });
</script>
</body>
</html>
"""


_COMPONENTS_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tourconnect_components")


def _ensure_component_dir(name, html):
    """Writes `html` to _tourconnect_components/<name>/index.html if it
    doesn't already match what's on disk, and returns that directory."""
    d = os.path.join(_COMPONENTS_ROOT, name)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "index.html")
    needs_write = True
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            needs_write = f.read() != html
    if needs_write:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
    return d


_video_recorder_component = components.declare_component(
    "video_recorder", path=_ensure_component_dir("video_recorder", _VIDEO_RECORDER_HTML)
)
_voice_recorder_component = components.declare_component(
    "voice_recorder", path=_ensure_component_dir("voice_recorder", _VOICE_RECORDER_HTML)
)

# Maps the MIME type MediaRecorder reports back to a sensible file extension.
_VIDEO_MIME_TO_EXT = {
    "video/webm": ".webm",
    "video/mp4": ".mp4",
    "video/ogg": ".ogv",
}
_AUDIO_MIME_TO_EXT = {
    "audio/webm": ".webm",
    "audio/mp4": ".mp4",
    "audio/ogg": ".ogg",
}


def record_video(key=None):
    """
    Renders the in-browser camera recorder widget. Returns a base64 data
    URL string (e.g. "data:video/webm;base64,....") once the user has
    recorded a clip and clicked "Use this recording", or None while
    nothing has been captured yet.
    """
    return _video_recorder_component(key=key, default=None)


def decode_recorded_video(data_url):
    """
    Splits a "data:<mime>;base64,<data>" string into raw bytes plus a file
    extension suitable for saving alongside uploaded videos. Returns
    (video_bytes, extension) or (None, None) if data_url is empty/malformed.
    """
    if not data_url or "," not in data_url:
        return None, None

    header, encoded = data_url.split(",", 1)
    mime = "video/webm"
    if ":" in header and ";" in header:
        mime = header.split(":", 1)[1].split(";", 1)[0]

    extension = _VIDEO_MIME_TO_EXT.get(mime, ".webm")

    try:
        video_bytes = base64.b64decode(encoded)
    except Exception:
        return None, None

    return video_bytes, extension


def record_voice(key=None):
    """
    Renders the in-browser microphone recorder widget. Returns a base64
    data URL string once the user records and clicks "Use this", or None
    while nothing has been captured yet.
    """
    return _voice_recorder_component(key=key, default=None)


def decode_recorded_audio(data_url):
    """
    Splits a "data:<mime>;base64,<data>" string into raw bytes plus a file
    extension. Returns (audio_bytes, extension) or (None, None) if
    data_url is empty or malformed.
    """
    if not data_url or "," not in data_url:
        return None, None

    header, encoded = data_url.split(",", 1)
    mime = "audio/webm"
    if ":" in header and ";" in header:
        mime = header.split(":", 1)[1].split(";", 1)[0]

    extension = _AUDIO_MIME_TO_EXT.get(mime, ".webm")

    try:
        audio_bytes = base64.b64decode(encoded)
    except Exception:
        return None, None

    return audio_bytes, extension


st.set_page_config(page_title="TourConnect", page_icon="🗺️", layout="wide")

init()

# ---------------------------------------------------------
# Indic language support (Sarvam AI) — language picker + helpers
# ---------------------------------------------------------
if "ui_lang" not in st.session_state:
    st.session_state["ui_lang"] = "en-IN"

with st.sidebar:
    st.selectbox(
        "🌐 Language / भाषा",
        list(LANGUAGES.keys()),
        format_func=lambda code: LANGUAGES[code],
        key="ui_lang",
    )
    if st.session_state["ui_lang"] == "gw-IN":
        st.caption(
            "ℹ️ No AI service (including Sarvam) has a dedicated Garhwali "
            "model yet — it's not one of India's 22 scheduled languages. "
            "This shows Hindi instead, which almost all Garhwali speakers "
            "read fine since it's the same Devanagari script."
        )
    if not is_configured():
        st.caption("⚠️ Sarvam API key not set — language/voice features are off. See the CONFIGURATION section at the top of this file.")


def t(text):
    """
    Translates a UI string into the currently selected language, with
    caching (via translate_text's @st.cache_data) so the same
    label isn't re-translated on every rerun. Falls back to the original
    English text untouched if Sarvam isn't configured, the language is
    English, or the API call fails — so the app never breaks because of
    this, it just stays in English for that string.
    """
    return translate_text(text, st.session_state["ui_lang"])


def speak_button(text, key):
    """
    Renders a small "🔊 Listen" button that, on click, translates `text`
    into the selected language (if needed) and plays it back via Sarvam's
    text-to-speech. Silently does nothing if Sarvam isn't configured or
    the selected language has no TTS voice — no error shown, since this
    is a nice-to-have, not a blocker.
    """
    lang = st.session_state["ui_lang"]
    if not is_configured() or not tts_supported(lang):
        return
    if st.button("🔊 " + t("Listen"), key=key):
        with st.spinner(t("Preparing audio...")):
            audio_bytes = text_to_speech(t(text), lang)
        if audio_bytes:
            st.audio(audio_bytes, format="audio/wav")
        else:
            st.caption(t("Audio isn't available right now."))


st.title("🗺️ TourConnect — " + t("Tourism & Local Discovery Platform"))

# ---------------------------------------------------------
# Session state
# ---------------------------------------------------------
if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False
if "biz_user" not in st.session_state:
    st.session_state["biz_user"] = None  # logged-in business dict
if "tourist" not in st.session_state:
    st.session_state["tourist"] = None  # dict: id, name, email, phone, points
if "last_eco_submission" not in st.session_state:
    st.session_state["last_eco_submission"] = None


def _render_ai_outcome(ai_result, submission_id, tourist):
    """
    Shows the right message for one AI check result, and does the
    auto-approve DB write if it qualifies. Returns 'approved', 'manual',
    or 'service_down' so the caller knows whether to keep offering a retry.
    """
    if not ai_result.get("service_ok", True):
        st.warning(
            "⚠️ Right now the server can't auto-approve this submission, "
            "but it has been saved and our team will review and approve it "
            "manually within **24–48 hours**. If you think this was a "
            "temporary glitch, you can try the AI check again below."
        )
        return "service_down"

    if (
        ai_result["verdict"] == "Genuine"
        and ai_result["confidence"] >= AUTO_APPROVE_CONFIDENCE
    ):
        decide_eco_submission(
            submission_id, tourist["id"], "Approved",
            ai_result["points_suggested"], reviewed_by="AI-Auto",
        )
        st.session_state["tourist"] = get_tourist_by_email(tourist["email"])
        log_event("eco_points_earned", {"points": ai_result["points_suggested"]})
        st.success(
            f"🎉 Approved automatically! You earned "
            f"**{ai_result['points_suggested']} points**.\n\n"
            f"*AI note: {ai_result['reasoning']}*"
        )
        return "approved"

    st.info(
        f"**AI first-pass result:** {ai_result['verdict']} "
        f"(confidence {ai_result['confidence']:.0%})\n\n"
        f"*{ai_result['reasoning']}*\n\n"
        "This needs a closer look, so it's been sent to our team for manual "
        "review — you'll be credited if approved. You can also try the AI "
        "check again below if you think a clearer look would change this."
    )
    return "manual"


def _identify_tourist_inline(widget_prefix):
    """
    Compact name/email/phone capture used outside the Go Green tab (e.g.
    redeeming a hotel voucher straight from the Tourist Portal). Writes into
    the SAME st.session_state["tourist"] used by "Go Green & Earn", so the
    points balance and redemption history stay unified across the app.
    """
    st.caption("Enter your name & email (same ones you use for Go Green) to link your points.")
    col_n, col_e, col_p = st.columns(3)
    name = col_n.text_input("Name", key=f"{widget_prefix}_name")
    email = col_e.text_input("Email", key=f"{widget_prefix}_email")
    phone = col_p.text_input("Phone (optional)", key=f"{widget_prefix}_phone")
    if st.button("Link my points", key=f"{widget_prefix}_link_btn"):
        if name and email:
            st.session_state["tourist"] = get_or_create_tourist(name, email, phone)
            st.rerun()
        else:
            st.warning("Name and email are required to redeem.")


def _render_hotel_voucher(business, widget_prefix):
    """
    Shown inside a business's detail expander on the Tourist Portal. Looks
    up any active voucher tied to that business's name (matched against
    vouchers.partner_name) and, if the tourist is identified and has enough
    points, lets them redeem it right there using the exact same
    redeem_voucher() logic as the "🎁 Redeem Vouchers" tab in Go Green.
    """
    voucher = get_voucher_for_partner(business["business_name"])
    if not voucher:
        return

    st.divider()
    st.markdown(
        f"🎁 **Eco-reward available here:** {voucher['title']} "
        f"— costs **{voucher['points_required']} pts** · {voucher['stock']} left"
    )

    tourist = st.session_state.get("tourist")
    if not tourist:
        _identify_tourist_inline(widget_prefix)
        return

    st.write(f"Signed in as **{tourist['name']}** · balance: **{tourist['points']} pts**")
    if tourist["points"] < voucher["points_required"]:
        st.info("Not enough points yet for this discount — keep earning in 🌱 Go Green & Earn!")
        return

    if st.button(f"Redeem: {voucher['title']}", key=f"{widget_prefix}_redeem_btn"):
        ok, msg = redeem_voucher(tourist["id"], voucher["id"])
        if ok:
            st.session_state["tourist"] = get_tourist_by_email(tourist["email"])
            log_event("voucher_redeemed", {"voucher": voucher["title"], "source": "hotel_listing"})
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)


def _render_business_expander(b):
    """
    Shared renderer for one business result card — used by both the
    dropdown-filter search and the voice search below, so descriptions,
    offers, catalog items, and the hotel voucher/redeem block all show up
    the same way (translated + with a "🔊 Listen" option) no matter which
    search path found the business.
    """
    with st.expander(f"⭐ {b['rating']}/5 — {b['business_name']}"):
        st.write(f"**{t('Description')}:** {t(b['description'])}")
        speak_button(b["description"], key=f"speak_desc_{b['id']}")
        st.write(f"**{t('Owner')}:** {b['owner_name']}")
        st.write(f"**{t('Phone')}:** {b['contact_no']} | **{t('Email')}:** {b['email']}")
        st.write(f"**{t('Website')}:** {b['website']}")

        offers = fetch_business_offers(b['id'])
        if offers:
            st.markdown("---")
            st.write("🔥 **" + t("Active Promotional Offers") + ":**")
            for o in offers:
                st.write(
                    f"• **{t(o['title'])}** ({o['discount_percentage']}% {t('OFF')}) "
                    f"— {t('Valid till')} {o['valid_until']}"
                )

        catalog = fetch_business_catalog(b['id'])
        if catalog:
            st.markdown("---")
            st.write("📋 **" + t("Services & Catalog") + ":**")
            for item in catalog:
                st.write(f"• **{t(item['item_name'])}** — ₹{item['price']} ({t(item['description'])})")

        _render_hotel_voucher(b, widget_prefix=f"hotel_{b['id']}")


# ---------------------------------------------------------
if "tourist_user" not in st.session_state:
    st.session_state["tourist_user"] = None

# Top Navigation
# ---------------------------------------------------------
nav = st.sidebar.radio(
    t("Navigation"),
    ["🌍 Tourist Portal", "🌱 Go Green & Earn", "🏢 Business Portal", "👨‍💼 Admin Panel"],
    format_func=t,
    key="main_navigation_radio"
)

if st.session_state.get("_last_nav_logged") != nav:
    log_page_view(nav)
    st.session_state["_last_nav_logged"] = nav

# ===========================================================
# MODULE: PUBLIC TOURIST DIRECTORY
# ===========================================================
if nav == "🌍 Tourist Portal":
    st.header(t("Find Local Services"))

    with st.expander("🎤 " + t("Or search by voice")):
        st.caption(
            t(
                "Speak in any supported language — e.g. \"I want a hotel in "
                "Jaipur\" — in Hindi, Tamil, or whichever language you picked "
                "in the sidebar. It gets translated and matched automatically."
            )
        )
        if not is_configured():
            st.caption("⚠️ " + t("Voice search needs a Sarvam API key — see the CONFIGURATION section at the top of this file."))
        else:
            if "voice_search_key_version" not in st.session_state:
                st.session_state["voice_search_key_version"] = 0
            vs_key = f"voice_search_{st.session_state['voice_search_key_version']}"

            voice_data_url = record_voice(key=vs_key)
            voice_bytes, _ = decode_recorded_audio(voice_data_url)

            if voice_bytes:
                with st.spinner(t("Understanding your voice search...")):
                    transcript, _detected_lang = speech_to_text(
                        voice_bytes, translate_to_english=True
                    )
                if transcript:
                    st.success(f"{t('Heard')}: \u201c{transcript}\u201d")
                    st.session_state["voice_search_results"] = search_businesses_by_text(transcript)
                    log_event("voice_search", {"query": transcript})
                else:
                    st.warning(t("Couldn't understand that — please try again."))
                st.session_state["voice_search_key_version"] += 1
                st.rerun()

    voice_results = st.session_state.get("voice_search_results")
    if voice_results is not None:
        st.subheader(t("Voice search results"))
        if voice_results:
            for b in voice_results:
                _render_business_expander(b)
        else:
            st.info(t("No matching businesses found — try different words, or use the filters below."))
        if st.button(t("Clear voice search results"), key="clear_voice_results_btn"):
            st.session_state["voice_search_results"] = None
            st.rerun()
        st.divider()

    col1, col2, col3, col4 = st.columns(4)

    countries = {c['name']: c['id'] for c in fetch_countries()}
    c_selected = col1.selectbox(t("Country"), list(countries.keys()), key="tourist_country") if countries else None

    states = {s['name']: s['id'] for s in fetch_states(countries[c_selected])} if c_selected else {}
    s_selected = col2.selectbox(t("State"), list(states.keys()), key="tourist_state") if states else None

    districts = {d['name']: d['id'] for d in fetch_districts(states[s_selected])} if s_selected else {}
    d_selected = col3.selectbox(t("District"), list(districts.keys()), key="tourist_district") if states else None

    cities = {ct['name']: ct['id'] for ct in fetch_cities(districts[d_selected])} if d_selected else {}
    city_selected = col4.selectbox(t("City"), list(cities.keys()), key="tourist_city") if d_selected else None

    categories = {cat['name']: cat['id'] for cat in fetch_categories()}
    cat_selected = st.selectbox(t("Category"), list(categories.keys()), key="tourist_category") if categories else None

    if st.button(t("Search Businesses"), key="tourist_search_btn") and city_selected and cat_selected:
        results = search_businesses(cities[city_selected], categories[cat_selected])
        st.subheader(f"{t('Results for')} {cat_selected} {t('in')} {city_selected}")

        if results:
            for b in results:
                _render_business_expander(b)
        else:
            st.info(t("No approved businesses found for this location."))

# ===========================================================
# MODULE: GO GREEN & EARN (AI-verified eco actions -> points -> vouchers)
# ===========================================================
elif nav == "🌱 Go Green & Earn":
    st.header("🌱 " + t("Go Green & Earn Rewards"))
    st.caption(
        t(
            "Record yourself planting a tree, cleaning up litter, or segregating waste, "
            "upload the video, and our AI does a first-pass genuineness check. "
            "Every submission is still reviewed by an admin before points are credited."
        )
    )

    with st.expander("👤 " + t("Your details"), expanded=st.session_state["tourist"] is None):
        name = st.text_input(t("Name"), value=(st.session_state["tourist"] or {}).get("name", ""))
        email = st.text_input(t("Email"), value=(st.session_state["tourist"] or {}).get("email", ""))
        phone = st.text_input(t("Phone (optional)"), value=(st.session_state["tourist"] or {}).get("phone", ""))
        if st.button(t("Continue"), key="tourist_identify_btn"):
            if name and email:
                st.session_state["tourist"] = get_or_create_tourist(name, email, phone)
                st.rerun()
            else:
                st.warning(t("Name and email are required."))

    tourist = st.session_state["tourist"]

    if tourist:
        st.success(f"{t('Welcome')}, {tourist['name']}! 🌟 {t('Your balance')}: **{tourist['points']} {t('points')}**")

        tab_submit, tab_redeem = st.tabs(["📤 " + t("Submit an Eco Action"), "🎁 " + t("Redeem Vouchers")])

        with tab_submit:
            activity_type = st.selectbox(
                t("What did you do?"),
                ["Tree Plantation", "Waste Cleanup", "Waste Segregation", "Other"],
                key="eco_activity_type",
            )

            video_source = st.radio(
                t("How do you want to provide your video?"),
                ["📤 Upload a file", "🎥 Record with camera"],
                key="eco_video_source",
                horizontal=True,
            )

            video_bytes = None
            video_filename = None

            if video_source == "📤 Upload a file":
                video_file = st.file_uploader(
                    t("Upload your video (mp4/mov/avi)"), type=["mp4", "mov", "avi"], key="eco_video_uploader"
                )
                if video_file:
                    video_bytes = video_file.getbuffer()
                    video_filename = video_file.name
            else:
                st.caption(
                    t(
                        "Uses your device's webcam or phone camera. Allow camera/microphone "
                        "access when your browser asks, record your eco-action, then click "
                        "\"Use this recording\" inside the widget below."
                    )
                )
                if "eco_recorder_key_version" not in st.session_state:
                    st.session_state["eco_recorder_key_version"] = 0
                recorder_key = f"eco_recorder_{st.session_state['eco_recorder_key_version']}"

                recorded_data_url = record_video(key=recorder_key)
                recorded_bytes, recorded_ext = decode_recorded_video(recorded_data_url)

                if recorded_bytes:
                    st.success("✅ " + t("Recording captured — ready to submit below."))
                    video_bytes = recorded_bytes
                    video_filename = f"recorded_{uuid.uuid4().hex}{recorded_ext}"
                    if st.button("🔁 " + t("Record a different clip"), key="eco_record_again_btn"):
                        st.session_state["eco_recorder_key_version"] += 1
                        st.rerun()

            if st.button(t("Submit for AI Review"), key="eco_submit_btn"):
                if not video_bytes:
                    st.warning(t("Please record or upload a video first."))
                else:
                    os.makedirs("uploads/eco", exist_ok=True)
                    safe_name = f"{uuid.uuid4().hex}_{video_filename}"
                    video_path = os.path.join("uploads/eco", safe_name)
                    with open(video_path, "wb") as f:
                        f.write(bytes(video_bytes))

                    with st.spinner("AI is reviewing your video... this can take a moment."):
                        ai_result = analyze_submission(video_path, activity_type)

                    submission_id = create_eco_submission(
                        tourist["id"], activity_type, video_path, ai_result
                    )
                    outcome = _render_ai_outcome(ai_result, submission_id, tourist)

                    st.session_state["last_eco_submission"] = (
                        None if outcome == "approved"
                        else {"id": submission_id, "video_path": video_path, "activity_type": activity_type}
                    )

                    if video_source == "🎥 Record with camera":
                        st.session_state["eco_recorder_key_version"] = (
                            st.session_state.get("eco_recorder_key_version", 0) + 1
                        )

            last = st.session_state.get("last_eco_submission")
            if last:
                st.divider()
                if st.button("🔁 Try AI Check Again", key=f"retry_{last['id']}"):
                    with st.spinner("Re-running AI check..."):
                        ai_result = analyze_submission(
                            last["video_path"], last["activity_type"]
                        )
                    update_eco_submission_ai(last["id"], ai_result)
                    outcome = _render_ai_outcome(ai_result, last["id"], tourist)
                    if outcome == "approved":
                        st.session_state["last_eco_submission"] = None

        with tab_redeem:
            vouchers = get_active_vouchers()
            if not vouchers:
                st.info(t("No vouchers available right now — check back soon!"))
            else:
                for v in vouchers:
                    col_v1, col_v2 = st.columns([3, 1])
                    col_v1.write(
                        f"**{t(v['title'])}** — {v['partner_name']}  \n"
                        f"{t('Costs')} **{v['points_required']} {t('pts')}** · {v['stock']} {t('left')}"
                    )
                    if col_v2.button(t("Redeem"), key=f"redeem_{v['id']}"):
                        ok, msg = redeem_voucher(tourist["id"], v["id"])
                        if ok:
                            st.session_state["tourist"] = get_tourist_by_email(tourist["email"])
                            log_event("voucher_redeemed", {"voucher": v["title"], "source": "go_green_tab"})
                            st.success(t(msg))
                            st.rerun()
                        else:
                            st.error(t(msg))
    else:
        st.info(t("Enter your name and email above to start earning points."))

# ===========================================================
# MODULE: BUSINESS PORTAL (login, registration, self-service dashboard)
# ===========================================================
elif nav == "🏢 Business Portal":

    # ---- NOT LOGGED IN: login or apply ----
    if st.session_state["biz_user"] is None:
        auth_mode = st.radio("Business Access", ["Login to Portal", "New Business Application"], horizontal=True)

        if auth_mode == "Login to Portal":
            st.subheader("🔑 Business Owner Login")
            with st.form("biz_login_form"):
                b_email = st.text_input("Registered Email")
                b_pass = st.text_input("Password", type="password")

                if st.form_submit_button("Login"):
                    user = verify_business_login(b_email, b_pass)
                    if user:
                        st.session_state["biz_user"] = user
                        st.success(f"Welcome back, {user['business_name']}!")
                        st.rerun()
                    else:
                        st.error("Invalid Email or Password.")

        else:
            st.subheader("📋 Register New Business")
            st.info(
                "💡 **Can't find your State or City?** Select the nearest available location to complete your "
                "initial application. Once logged in, submit a request under **📍 Location Requests** in your "
                "Business Panel, and our team will add your exact area."
            )
            with st.form("new_reg_form"):
                b_name = st.text_input("Business Name*")
                owner_name = st.text_input("Owner Name*")

                countries = {c['name']: c['id'] for c in fetch_countries()}
                c_sel = st.selectbox("Country", list(countries.keys()), key="reg_c") if countries else None

                states = {s['name']: s['id'] for s in fetch_states(countries[c_sel])} if c_sel else {}
                s_sel = st.selectbox("State", list(states.keys()), key="reg_s") if c_sel else None

                districts = {d['name']: d['id'] for d in fetch_districts(states[s_sel])} if s_sel else {}
                d_sel = st.selectbox("District", list(districts.keys()), key="reg_d") if s_sel else None

                cities = {ct['name']: ct['id'] for ct in fetch_cities(districts[d_sel])} if d_sel else {}
                ct_sel = st.selectbox("City", list(cities.keys()), key="reg_ct") if d_sel else None

                categories = {cat['name']: cat['id'] for cat in fetch_categories()}
                cat_sel = st.selectbox("Category", list(categories.keys()), key="reg_cat") if categories else None

                phone = st.text_input("Contact Number")
                email = st.text_input("Account Email*")
                password = st.text_input("Set Password*", type="password")
                website = st.text_input("Website")
                desc = st.text_area("Description")

                uploaded_file = st.file_uploader("Upload Business Image (optional)", type=["jpg", "png", "jpeg"])

                if st.form_submit_button("Submit Registration"):
                    if not email or not password or not b_name or not ct_sel or not cat_sel:
                        st.warning("Please fill out all required fields marked with (*).")
                    else:
                        new_biz_id = register_business_with_auth(
                            owner_name, b_name, categories[cat_sel],
                            countries[c_sel], states[s_sel], districts[d_sel], cities[ct_sel],
                            desc, phone, email, website, password
                        )
                        if new_biz_id and uploaded_file is not None:
                            os.makedirs("uploads", exist_ok=True)
                            file_path = os.path.join("uploads", f"biz_{new_biz_id}_{uploaded_file.name}")
                            with open(file_path, "wb") as f:
                                f.write(uploaded_file.getbuffer())
                            save_business_media(new_biz_id, file_path)

                        if new_biz_id:
                            st.success("Registration submitted! You can log in once approved by Admin.")
                        else:
                            st.error("Registration failed. That email may already be registered, or a dropdown selection is invalid.")

    # ---- LOGGED IN: business dashboard ----
    else:
        biz = st.session_state["biz_user"]

        st.sidebar.markdown(f"**Logged in as:** {biz['business_name']}")
        if st.sidebar.button("🚪 Logout Business", key="logout_biz_btn"):
            st.session_state["biz_user"] = None
            st.rerun()

        biz_nav = st.sidebar.radio(
            "Portal Navigation",
            [
                "📊 Dashboard",
                "👤 Business Profile",
                "🖼️ Media Management",
                "📍 Location Requests",
                "🏷️ Category Requests",
                "⚙️ Account Settings",
            ],
        )

        st.title(f"🏢 {biz['business_name']}")

        if biz_nav == "📊 Dashboard":
            st.header("Business Dashboard Overview")

            c1, c2, c3 = st.columns(3)
            c1.metric("Account Status", biz['status'])
            c2.metric("Rating Badge", f"⭐ {biz['rating']}/5")
            c3.metric("Email", biz['email'])

            st.divider()
            b_tab1, b_tab2 = st.tabs(["📋 Catalog Services", "🔥 Active Deals & Offers"])

            with b_tab1:
                st.subheader("Add Catalog Items")
                with st.form("add_cat_item_form"):
                    item_name = st.text_input("Service / Product Name")
                    item_price = st.number_input("Price (INR)", min_value=0.0, step=50.0)
                    item_desc = st.text_area("Description")
                    if st.form_submit_button("Add Item"):
                        if item_name and item_price:
                            add_catalog_item(biz['id'], item_name, item_price, item_desc)
                            st.success("Item added to catalog!")
                            st.rerun()

                st.subheader("Current Catalog")
                catalog = fetch_business_catalog(biz['id'])
                if catalog:
                    for item in catalog:
                        st.write(f"• **{item['item_name']}** — ₹{item['price']} ({item['description']})")
                else:
                    st.caption("No catalog items published.")

            with b_tab2:
                st.subheader("Create Promotional Deals")
                with st.form("add_promo_form"):
                    offer_title = st.text_input("Offer Title")
                    discount = st.slider("Discount (%)", 1, 100, 10)
                    valid_till = st.date_input("Valid Until")
                    offer_desc = st.text_area("Offer Details")
                    if st.form_submit_button("Publish Offer"):
                        if offer_title:
                            add_business_offer(biz['id'], offer_title, offer_desc, discount, valid_till)
                            st.success("Offer published!")
                            st.rerun()

                st.subheader("Published Offers")
                offers = fetch_business_offers(biz['id'])
                if offers:
                    for o in offers:
                        st.write(f"🏷️ **{o['title']}** ({o['discount_percentage']}% OFF) — Valid till {o['valid_until']}")
                else:
                    st.caption("No active deals currently published.")

        elif biz_nav == "👤 Business Profile":
            st.header("Business Profile Details")
            with st.form("edit_profile_form"):
                new_b_name = st.text_input("Business Name", value=biz['business_name'])
                new_owner = st.text_input("Owner Name", value=biz['owner_name'])
                new_phone = st.text_input("Contact Number", value=biz['contact_no'])
                new_web = st.text_input("Website", value=biz['website'] or "")
                new_desc = st.text_area("Business Description", value=biz['description'] or "")

                if st.form_submit_button("Update Profile"):
                    update_business_profile(biz['id'], new_b_name, new_owner, new_phone, new_web, new_desc)
                    st.session_state["biz_user"]["business_name"] = new_b_name
                    st.session_state["biz_user"]["owner_name"] = new_owner
                    st.session_state["biz_user"]["contact_no"] = new_phone
                    st.session_state["biz_user"]["website"] = new_web
                    st.session_state["biz_user"]["description"] = new_desc
                    st.success("Profile updated successfully!")
                    st.rerun()

        elif biz_nav == "🖼️ Media Management":
            st.header("Media & Gallery Uploads")
            uploaded_file = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"], key="biz_media_uploader")
            if uploaded_file is not None:
                os.makedirs("uploads", exist_ok=True)
                file_path = os.path.join("uploads", f"biz_{biz['id']}_{uploaded_file.name}")
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                save_business_media(biz['id'], file_path)
                st.success("Image saved to gallery!")

            st.subheader("Gallery")
            media = fetch_business_media(biz['id'])
            if media:
                cols = st.columns(4)
                for i, m in enumerate(media):
                    if os.path.exists(m['file_path']):
                        cols[i % 4].image(m['file_path'], use_container_width=True)
            else:
                st.caption("No images uploaded yet.")

        elif biz_nav == "📍 Location Requests":
            st.header("Location Coverage Requests")
            st.caption("Submit a request if your target City or District is missing from dropdown options.")

            with st.form("loc_req_form"):
                req_type = st.selectbox("Type", ["City", "District", "State"])
                loc_name = st.text_input("Location Name")
                if st.form_submit_button("Send Request"):
                    if loc_name:
                        submit_location_request(biz['id'], req_type, loc_name)
                        st.success("Location request sent to admin!")
                    else:
                        st.warning("Please provide a location name.")

        elif biz_nav == "🏷️ Category Requests":
            st.header("Category Expansion Requests")
            st.caption("Request new business categories if your industry sector isn't listed.")

            with st.form("cat_req_form"):
                cat_name = st.text_input("Proposed Category Name")
                if st.form_submit_button("Send Category Request"):
                    if cat_name:
                        submit_category_request(biz['id'], cat_name)
                        st.success("Category request sent to admin!")
                    else:
                        st.warning("Please enter a category name.")

        elif biz_nav == "⚙️ Account Settings":
            st.header("Account & Security Settings")
            with st.form("change_pass_form"):
                p1 = st.text_input("New Password", type="password")
                p2 = st.text_input("Confirm New Password", type="password")
                if st.form_submit_button("Change Password"):
                    if p1 and p1 == p2:
                        change_business_password(biz['id'], p1)
                        st.success("Password updated successfully!")
                    else:
                        st.error("Passwords do not match or field is empty.")

# ===========================================================
# MODULE: ADMIN PANEL (SECURE AUTH & MANAGEMENT)
# ===========================================================
elif nav == "👨‍💼 Admin Panel":
    st.header("Admin Operations")

    if not st.session_state["admin_logged_in"]:
        st.subheader("🔒 Admin Login")
        with st.form("admin_login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_btn = st.form_submit_button("Login")

            if login_btn:
                if verify_admin(username, password):
                    st.session_state["admin_logged_in"] = True
                    st.session_state["admin_username"] = username
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password!")

    else:
        if st.sidebar.button("🚪 Logout Admin", key="logout_btn"):
            st.session_state["admin_logged_in"] = False
            st.rerun()

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
            ["Pending Approvals", "🌱 Eco Submissions", "Manage Ratings",
             "📍 Location Requests", "🏷️ Category Requests", "Add New Admin"]
        )

        with tab1:
            st.subheader("Pending Registration Requests")
            pending = get_pending_businesses()
            if pending:
                for item in pending:
                    col_info, col_btn1, col_btn2 = st.columns([3, 1, 1])
                    col_info.write(f"**{item['business_name']}** ({item['category']}) — Owner: {item['owner_name']}")

                    if col_btn1.button("Approve", key=f"app_{item['id']}"):
                        update_status(item['id'], 'Approved')
                        st.rerun()

                    if col_btn2.button("Reject", key=f"rej_{item['id']}"):
                        update_status(item['id'], 'Rejected')
                        st.rerun()
            else:
                st.write("No pending business approvals.")

        with tab2:
            st.subheader("🌱 Go Green Submissions — Manual Review Queue")
            st.caption(
                "Confident 'Genuine' videos are already auto-approved and won't show up here. "
                "What's left below is either something the AI flagged as Fake/Uncertain, or a "
                "submission the AI service couldn't check at all (shown in its reasoning) — "
                "both need a human decision."
            )
            pending_eco = get_pending_eco_submissions()
            if not pending_eco:
                st.write("No pending eco submissions.")
            else:
                for sub in pending_eco:
                    with st.expander(
                        f"{sub['activity_type']} — {sub['tourist_name']} "
                        f"(AI: {sub['ai_verdict']}, {sub['ai_confidence']:.0%})"
                    ):
                        st.write(f"**Tourist:** {sub['tourist_name']} ({sub['tourist_email']})")
                        st.write(f"**Activity:** {sub['activity_type']}")
                        st.write(f"**AI verdict:** {sub['ai_verdict']} — confidence {sub['ai_confidence']:.0%}")
                        st.write(f"**AI reasoning:** {sub['ai_reasoning']}")
                        st.write(f"**AI-suggested points:** {sub['points_suggested']}")

                        if os.path.exists(sub["video_path"]):
                            st.video(sub["video_path"])
                        else:
                            st.warning("Video file not found on disk.")

                        award_points = st.number_input(
                            "Points to award if approved",
                            min_value=0, max_value=500,
                            value=int(sub["points_suggested"]),
                            step=5,
                            key=f"pts_{sub['id']}",
                        )

                        col_a, col_r = st.columns(2)
                        if col_a.button("✅ Approve", key=f"eco_app_{sub['id']}"):
                            decide_eco_submission(
                                sub["id"], sub["tourist_id"], "Approved",
                                award_points, st.session_state.get("admin_username", "admin"),
                            )
                            st.rerun()
                        if col_r.button("❌ Reject", key=f"eco_rej_{sub['id']}"):
                            decide_eco_submission(
                                sub["id"], sub["tourist_id"], "Rejected",
                                0, st.session_state.get("admin_username", "admin"),
                            )
                            st.rerun()

        with tab3:
            st.subheader("Assign Badge Ratings")
            b_id = st.number_input("Business ID", min_value=1, step=1)
            new_rating = st.slider("Rating Stars", 1, 5, 3)
            if st.button("Update Rating", key="update_rating_btn"):
                update_rating(b_id, new_rating)
                st.success("Rating updated successfully!")

        with tab4:
            st.subheader("📍 Pending Location Coverage Requests")
            st.caption(
                "Businesses submit these when their real City/District/State isn't in the "
                "dropdowns yet. Approve here as an acknowledgement, then add the actual "
                "row to countries/states/districts/cities in the database so it shows up "
                "in the dropdowns everywhere."
            )
            loc_requests = get_pending_location_requests()
            if loc_requests:
                for r in loc_requests:
                    col_info, col_a, col_r = st.columns([3, 1, 1])
                    col_info.write(
                        f"**{r['business_name']}** requests **{r['requested_type']}**: "
                        f"*{r['location_name']}*"
                    )
                    if col_a.button("Approve", key=f"locreq_app_{r['id']}"):
                        update_location_request_status(r['id'], "Approved")
                        st.rerun()
                    if col_r.button("Reject", key=f"locreq_rej_{r['id']}"):
                        update_location_request_status(r['id'], "Rejected")
                        st.rerun()
            else:
                st.write("No pending location requests.")

        with tab5:
            st.subheader("🏷️ Pending Category Requests")
            cat_requests = get_pending_category_requests()
            if cat_requests:
                for r in cat_requests:
                    col_info, col_a, col_r = st.columns([3, 1, 1])
                    col_info.write(f"**{r['business_name']}** proposes category: *{r['category_name']}*")
                    if col_a.button("Approve & Add", key=f"catreq_app_{r['id']}"):
                        update_category_request_status(r['id'], "Approved", approve_and_add=True)
                        st.success(f"'{r['category_name']}' added to categories.")
                        st.rerun()
                    if col_r.button("Reject", key=f"catreq_rej_{r['id']}"):
                        update_category_request_status(r['id'], "Rejected")
                        st.rerun()
            else:
                st.write("No pending category requests.")

        with tab6:
            st.subheader("Create New Admin Account")
            with st.form("add_admin_form"):
                new_user = st.text_input("New Admin Username")
                new_pass = st.text_input("New Admin Password", type="password")
                confirm_pass = st.text_input("Confirm Password", type="password")
                create_btn = st.form_submit_button("Create Admin")

                if create_btn:
                    if not new_user or not new_pass:
                        st.warning("Please fill out all fields.")
                    elif new_pass != confirm_pass:
                        st.error("Passwords do not match!")
                    else:
                        success = add_new_admin(new_user, new_pass)
                        if success:
                            st.success(f"Admin '{new_user}' created successfully!")
                        else:
                            st.error("Failed to create admin. Username might already exist.")
