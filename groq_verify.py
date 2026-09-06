"""
groq_verify.py
--------------
AI verification for "Go Green" submissions.

Groq's chat API does not accept raw video, so the flow is:
  1. Pull a handful of evenly-spaced frames out of the uploaded video (OpenCV).
  2. Send those frames + a prompt to a Groq *vision* model.
  3. Ask the model to return strict JSON: verdict / confidence / reasoning.

SETUP: paste your Groq API key into GROQ_API_KEY below and save the file.
Get a free key at https://console.groq.com/keys
"""

import base64
import json

import cv2
from groq import Groq

# ============================================================
# EDIT THIS WITH YOUR OWN GROQ API KEY
# ============================================================
GROQ_API_KEY = "gsk_your_key_here"
# ============================================================

# meta-llama/llama-4-scout-17b-16e-instruct is Groq's current general-purpose
# vision model (as of the model's last check). If Groq retires/renames it,
# swap in whatever model console.groq.com/docs/vision currently lists —
# e.g. meta-llama/llama-4-maverick-17b-128e-instruct or qwen/qwen3.6-27b.
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

MAX_FRAMES = 5  # keep at or under the model's per-request image limit

# A "Genuine" verdict at or above this confidence gets auto-approved by
# app.py without waiting for an admin. Anything below it — or a
# Fake/Uncertain verdict, or the AI service being unreachable — falls
# through to the manual admin queue instead. Tune this after watching a
# few real submissions come through.
AUTO_APPROVE_CONFIDENCE = 0.75


def extract_frames(video_path: str, num_frames: int = MAX_FRAMES):
    """Grab `num_frames` evenly spaced frames from the video as base64 JPEGs."""
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
    # judged it fake. app.py uses this to show a "we can't check this right
    # now, it'll be reviewed within 24-48 hrs" message instead of a rejection.
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
    This function never touches the database or awards points — app.py
    decides what to do with the result (auto-approve / queue for admin /
    show a "try again later" message).
    """
    api_key = GROQ_API_KEY
    if not api_key or api_key == "gsk_your_key_here":
        return _fallback_result("GROQ_API_KEY is not set in groq_verify.py — skipped AI check, needs manual review.")

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
