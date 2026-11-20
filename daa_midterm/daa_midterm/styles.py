"""Custom CSS for the Streamlit app."""

import streamlit as st

CSS = """
<style>
:root {
    --rp-panel: rgba(20, 29, 52, .78);
    --rp-border: rgba(148, 163, 184, .17);
    --rp-muted: #9aa8c2;
    --rp-text: #edf3ff;
}
.stApp { background: radial-gradient(circle at 12% 0%, #18284c 0, #0b1020 42%, #090e1b 100%); }
[data-testid="stHeader"] { background: rgba(7, 12, 25, .72); }
[data-testid="stSidebar"] { background: rgba(9, 15, 29, .94); border-right: 1px solid var(--rp-border); }
.block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1500px; }
h1, h2, h3 { letter-spacing: -.035em; }
h1 { color: var(--rp-text); font-weight: 800; }
[data-testid="stMetric"] {
    background: linear-gradient(145deg, rgba(30, 43, 74, .9), rgba(17, 25, 45, .88));
    border: 1px solid var(--rp-border); padding: 16px 18px; border-radius: 16px;
}
[data-testid="stMetricLabel"] { color: #aab8d2; }
[data-testid="stMetricValue"] { color: #f5f8ff; }
div[data-testid="stTabs"] button { border-radius: 10px 10px 0 0; font-weight: 650; }
div.stButton > button, div.stDownloadButton > button, div.stLinkButton > a {
    border-radius: 10px; font-weight: 650; min-height: 2.65rem;
}
.rp-hero {
    padding: 25px 28px; border-radius: 22px; border: 1px solid rgba(155, 176, 255, .22); margin-bottom: 22px;
    background: linear-gradient(115deg, rgba(63, 91, 169, .38), rgba(33, 50, 91, .20) 56%, rgba(22, 130, 145, .15));
}
.rp-eyebrow { color: #9db6ff; font-size: .76rem; font-weight: 800; letter-spacing: .16em; text-transform: uppercase; }
.rp-hero h1 { margin: 7px 0 6px 0; font-size: clamp(2rem, 4vw, 3rem); }
.rp-hero p { color: #bfcae2; margin: 0; font-size: 1rem; }
.rp-pill {
    display: inline-block; background: rgba(124, 156, 255, .14); color: #b9cbff;
    border: 1px solid rgba(124, 156, 255, .28); padding: 4px 10px; border-radius: 999px;
    font-size: .76rem; font-weight: 700;
}
.rp-footer { color: #7f8ca7; font-size: .78rem; border-top: 1px solid var(--rp-border); padding-top: 15px; margin-top: 28px; }
</style>
"""


def inject_styles() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
