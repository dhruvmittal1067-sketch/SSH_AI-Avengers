"""
sarvam_ai.py
------------
Wraps the three Sarvam AI APIs this app uses for Indic-language and
voice support:
  - /translate            (text -> text, one Indic language to another)
  - /speech-to-text        (voice -> text, optionally translated to English)
  - /text-to-speech        (text -> spoken audio)

SETUP: paste your Sarvam API key into SARVAM_API_KEY below and save the
file. Get a free key (Sarvam gives free credits to start) at
https://dashboard.sarvam.ai

IMPORTANT — Garhwali: Sarvam AI (like every major Indic-language API right
now) only supports India's 22 officially scheduled languages, and Garhwali
is not one of them — it's a regional language of Uttarakhand without its
own model anywhere yet. Since Garhwali is written in Devanagari and its
speakers are overwhelmingly also fluent in Hindi, this app offers
"Garhwali" in the language picker but routes it through Hindi (hi-IN)
under the hood, with a note in the UI so nobody's misled into thinking
there's real Garhwali translation happening.
"""

import base64
import requests
import streamlit as st

# ============================================================
# EDIT THIS WITH YOUR OWN SARVAM API KEY
# ============================================================
SARVAM_API_KEY = "sk_m8utsms9_VZb4YfVeJ4G1GZKVciGETefM"
# ============================================================

_BASE_URL = "https://api.sarvam.ai"

# Languages actually offered in the app's picker: code -> display label.
# Codes are Sarvam's BCP-47-style codes. "gw-IN" is NOT a real Sarvam code —
# it's our own placeholder that _resolve_lang() maps to Hindi (hi-IN) below,
# since Sarvam has no Garhwali model to call.
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


def _headers():
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
            f"{_BASE_URL}/translate",
            headers=_headers(),
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
            f"{_BASE_URL}/speech-to-text",
            headers=_headers(),
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
            f"{_BASE_URL}/text-to-speech",
            headers=_headers(),
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
