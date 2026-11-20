"""Streamlit glue for the Google OAuth flow.

Google redirects the browser away and back, which starts a NEW Streamlit
session. The OAuth state therefore cannot live in st.session_state; pending
sign-ins are kept in a process-wide dictionary keyed by the state value.
"""

from __future__ import annotations

import time
from typing import Dict, Optional, Tuple

import streamlit as st

from . import google_cal
from .config import DEFAULT_REDIRECT_URI, OAUTH_PENDING_MAX, OAUTH_PENDING_TTL_SECONDS
from .ui import flash

TOKEN_KEY = "google_token_json"


@st.cache_resource
def _pending_sign_ins() -> Dict[str, Dict]:
    return {}


def _prune(pending: Dict[str, Dict]) -> None:
    cutoff = time.time() - OAUTH_PENDING_TTL_SECONDS
    for state in [s for s, entry in pending.items() if entry["created"] < cutoff]:
        del pending[state]
    while len(pending) >= OAUTH_PENDING_MAX:
        del pending[min(pending, key=lambda s: pending[s]["created"])]


def get_config() -> Optional[Dict[str, str]]:
    """OAuth client settings from .streamlit/secrets.toml, or None if not configured."""
    try:
        section = st.secrets["google_calendar"]
        client_id, client_secret = section["client_id"], section["client_secret"]
        redirect_uri = section.get("redirect_uri", DEFAULT_REDIRECT_URI)
    except Exception:  # no secrets file, missing section or missing keys
        return None
    if not (client_id and client_secret):
        return None
    return {"client_id": client_id, "client_secret": client_secret, "redirect_uri": redirect_uri}


def authorization_url(config: Dict[str, str]) -> str:
    """Create a sign-in URL and remember its state for the return trip."""
    url, state, code_verifier = google_cal.create_authorization(config)
    pending = _pending_sign_ins()
    _prune(pending)
    pending[state] = {"code_verifier": code_verifier, "created": time.time()}
    return url


def handle_callback(config: Optional[Dict[str, str]]) -> None:
    """Complete sign-in when Google redirects back with ?code=... or ?error=..."""
    params = st.query_params
    code, state, error = params.get("code"), params.get("state"), params.get("error")
    if not (code or error):
        return
    st.query_params.clear()

    if error:
        flash("Google sign-in was cancelled or denied ({}).".format(error), "warning")
        st.rerun()
    if not config:
        flash("Google returned an authorization code, but OAuth credentials are not configured.", "error")
        st.rerun()

    entry = _pending_sign_ins().pop(state, None) if state else None
    if entry is None or time.time() - entry["created"] > OAUTH_PENDING_TTL_SECONDS:
        flash("Google sign-in expired or was not recognised. Please connect again.", "error")
        st.rerun()

    try:
        st.session_state[TOKEN_KEY] = google_cal.exchange_code(config, code, state, entry["code_verifier"])
        flash("Google Calendar connected successfully.")
    except Exception as exc:
        flash("Google sign-in failed: {}".format(exc), "error")
    st.rerun()


def get_service() -> Optional[Tuple[object, object]]:
    """Return (service, credentials) for the connected account, or None."""
    token_json = st.session_state.get(TOKEN_KEY)
    if not token_json:
        return None
    try:
        return google_cal.build_service(token_json)
    except Exception as exc:
        st.warning("Could not initialize Google Calendar. Reconnect your account. Details: {}".format(exc))
        return None


def save_credentials(credentials) -> None:
    """Persist refreshed tokens so they are not refreshed on every rerun."""
    st.session_state[TOKEN_KEY] = credentials.to_json()


def disconnect() -> None:
    st.session_state.pop(TOKEN_KEY, None)
