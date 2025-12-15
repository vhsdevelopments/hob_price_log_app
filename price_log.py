import re
import streamlit as st
from supabase import create_client


# =========================================================
# LOGIN
# =========================================================

def require_login():
    if "authed" not in st.session_state:
        st.session_state.authed = False

    if st.session_state.authed:
        return

    st.markdown(
        """
        <style>
        div[data-baseweb="input"] > div {
            background-color: #CDCDCD !important;
        }
        button[kind="primary"] {
            background-color: #228B22 !important;
            color: white !important;
            border: none !important;
        }
        button[kind="primary"]:hover {
            background-color: #1e7a1e !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("Login")
    password = st.text_input("Password", type="password", placeholder="Enter password")

    if st.button("Sign in", type="primary"):
        if password == st.secrets["APP_PASSWORD"]:
            st.session_state.authed = True
            st.rerun()
        else:
            st.error("Incorrect password")

    st.stop()


# =========================================================
# SUPABASE CONFIG (FROM SECRETS)
# =========================================================

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# =========================================================
# HELPERS
# =========================================================

def normalize_label(name: str) -> str:
    if not name:
        return ""
    name = name.upper().strip()
    name = re.sub(r"[^A-Z0-9 &/]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def clean_price_input(val):
    if not val:
        return None
    cleaned = re.sub(r"[^0-9.]", "", str(val))
    if cleaned.count(".") > 1:
        parts = cleaned.split(".")
        cleaned = parts[0] + "." + "".join(parts[1:])
    return cleaned if cleaned else None


def format_price(val):
    return f"${float(val):,.2f}"


# =========================================================
# DATA
# =========================================================

def load_brand_levels():
    res = (
        supabase.table("brand_price_levels")
        .select("brand, price_level")
