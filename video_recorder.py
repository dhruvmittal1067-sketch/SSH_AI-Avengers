"""
video_recorder.py
------------------
Thin wrapper around a small vanilla-JS/HTML Streamlit component that lets
the user record a video with their device camera (webcam or phone camera)
directly in the browser, as an alternative to uploading a pre-recorded
file. No extra Python packages are required — this uses Streamlit's
built-in `components.v1.declare_component`, pointed at the static
`components/video_recorder/index.html` next to this file.

Usage:
    from video_recorder import record_video

    data_url = record_video(key="eco_recorder_0")
    if data_url:
        video_bytes, extension = decode_recorded_video(data_url)
"""

import os
import base64

import streamlit.components.v1 as components

_COMPONENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "components", "video_recorder")

_video_recorder_component = components.declare_component(
    "video_recorder",
    path=_COMPONENT_DIR,
)

# Maps the MIME type MediaRecorder reports back to a sensible file extension.
_MIME_TO_EXT = {
    "video/webm": ".webm",
    "video/mp4": ".mp4",
    "video/ogg": ".ogv",
}


def record_video(key=None):
    """
    Renders the in-browser camera recorder widget.

    Returns a base64 data URL string (e.g. "data:video/webm;base64,....")
    once the user has recorded a clip and clicked "Use this recording",
    or None while nothing has been captured yet.
    """
    return _video_recorder_component(key=key, default=None)


def decode_recorded_video(data_url):
    """
    Splits a "data:<mime>;base64,<data>" string into raw bytes plus a
    file extension suitable for saving alongside uploaded videos.
    Returns (video_bytes, extension) or (None, None) if data_url is empty
    or malformed.
    """
    if not data_url or "," not in data_url:
        return None, None

    header, encoded = data_url.split(",", 1)
    mime = "video/webm"
    if ":" in header and ";" in header:
        mime = header.split(":", 1)[1].split(";", 1)[0]

    extension = _MIME_TO_EXT.get(mime, ".webm")

    try:
        video_bytes = base64.b64decode(encoded)
    except Exception:
        return None, None

    return video_bytes, extension
