"""
voice_recorder.py
------------------
Same pattern as video_recorder.py, but for audio-only input — used for
voice search / voice input in the tourist-facing parts of the app. No
extra Python package required, built on Streamlit's own
components.v1.declare_component.

Usage:
    from voice_recorder import record_voice

    data_url = record_voice(key="voice_search_0")
    if data_url:
        audio_bytes, extension = decode_recorded_audio(data_url)
"""

import os
import base64

import streamlit.components.v1 as components

_COMPONENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "components", "voice_recorder")

_voice_recorder_component = components.declare_component(
    "voice_recorder",
    path=_COMPONENT_DIR,
)

_MIME_TO_EXT = {
    "audio/webm": ".webm",
    "audio/mp4": ".mp4",
    "audio/ogg": ".ogg",
}


def record_voice(key=None):
    """
    Renders the in-browser microphone recorder widget. Returns a base64
    data URL string once the user records and clicks "Use this", or None
    while nothing has been captured yet.
    """
    return _voice_recorder_component(key=key, default=None)


def decode_recorded_audio(data_url):
    """
    Splits a "data:<mime>;base64,<data>" string into raw bytes plus a
    file extension. Returns (audio_bytes, extension) or (None, None) if
    data_url is empty or malformed.
    """
    if not data_url or "," not in data_url:
        return None, None

    header, encoded = data_url.split(",", 1)
    mime = "audio/webm"
    if ":" in header and ";" in header:
        mime = header.split(":", 1)[1].split(";", 1)[0]

    extension = _MIME_TO_EXT.get(mime, ".webm")

    try:
        audio_bytes = base64.b64decode(encoded)
    except Exception:
        return None, None

    return audio_bytes, extension
