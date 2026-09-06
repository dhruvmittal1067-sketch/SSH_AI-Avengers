"""
firebase_analytics.py
----------------------
Adds Firebase Analytics (Google Analytics under the hood) to the Streamlit
app. Streamlit itself doesn't give a supported way to inject arbitrary
<script> tags into the real top-level page — st.markdown(unsafe_allow_html)
does not execute <script> content, and components.v1.html() renders its
own sandboxed iframe. So this uses the standard, widely-used workaround:
a components.html() call whose JS reaches out to `window.parent.document`
(the real page, since the iframe is same-origin, served by this same
Streamlit app) and appends the real Firebase/gtag script tags there. Once
loaded, `window.parent.firebase` behaves like normal Firebase Analytics.

No new pip dependency — Firebase is loaded from Google's CDN in the
browser, same as the JS snippet you'd get from the Firebase console.

Usage in app.py:
    import firebase_analytics
    firebase_analytics.init()                       # once, near the top
    firebase_analytics.log_page_view("Tourist Portal")   # on nav change
"""

import json
import streamlit.components.v1 as components

# Values straight from the Firebase console's web app config for
# "tour-connect-9cdad". The apiKey in a Firebase *web* config is not a
# secret — it just identifies the project to Google's servers — so it's
# fine to ship in client-side code like this.
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


# Set to True if you want Firebase Analytics. Leave False to skip it
# entirely — nothing else in the app depends on it.
FIREBASE_ENABLED = False


def init():
    """
    Loads the Firebase compat SDK (app + analytics) into the parent page
    and calls firebase.initializeApp(...) + firebase.analytics() once.
    Safe to call on every rerun — it guards against double-loading with a
    flag on window.parent.

    No-op unless FIREBASE_ENABLED=true is set — so local/dev runs need no
    Firebase setup at all.
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
    section-view / action events (e.g. call this when the sidebar nav
    changes, or after a successful redemption).

    No-op unless FIREBASE_ENABLED=true is set.
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
