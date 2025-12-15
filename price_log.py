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

    st.title("Login")

    password = st.text_input("Password", type="password")

    if st.button("Sign in", type="primary"):
        if password == st.secrets["APP_PASSWORD"]:
            st.session_state.authed = True
            st.rerun()
        else:
            st.error("Incorrect password")

    st.stop()


# -------------------------------------------------------------------
# SUPABASE CONFIG (FROM STREAMLIT SECRETS)
# -------------------------------------------------------------------

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE)


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
    if val is None:
        return None
    cleaned = re.sub(r"[^0-9.]", "", str(val))
    if cleaned.count(".") > 1:
        parts = cleaned.split(".")
        cleaned = parts[0] + "." + "".join(parts[1:])
    return cleaned if cleaned else None


def format_price(val):
    return f"${float(val):,.2f}"


def safe_range(limit):
    return (0, max(0, int(limit) - 1))


# =========================================================
# DATA LOADERS
# =========================================================

def load_brand_levels(limit=5000):
    start, end = safe_range(limit)
    res = (
        supabase.table("brand_price_levels")
        .select("brand,price_level")
        .order("brand")
        .range(start, end)
        .execute()
        .data
    ) or []

    out = []
    for r in res:
        brand = normalize_label(r.get("brand"))
        level = normalize_label(r.get("price_level"))
        if brand:
            out.append({"brand": brand, "price_level": level})

    return sorted(out, key=lambda x: x["brand"])


def load_categories_for_brand(brand, limit=10000):
    start, end = safe_range(limit)
    res = (
        supabase.table("sales")
        .select("category")
        .eq("brand", brand)
        .range(start, end)
        .execute()
        .data
    ) or []

    cats = {normalize_label(r.get("category")) for r in res if r.get("category")}
    return sorted(c for c in cats if c)


def upsert_brand_level(brand, price_level):
    supabase.table("brand_price_levels").upsert(
        {"brand": brand, "price_level": price_level},
        on_conflict="brand",
    ).execute()


def insert_sale(brand, category, price, on_sale, price_level):
    supabase.table("sales").insert(
        {
            "brand": brand,
            "category": category,
            "price": float(price),
            "on_sale": bool(on_sale),
            "price_level": price_level or "",
        }
    ).execute()


# =========================================================
# MAIN APP
# =========================================================

def main():
    st.set_page_config(page_title="HOB Upscale Price Log", layout="wide")
    require_login()

    BRAND_PLACEHOLDER = "(click or type to search)"
    BRAND_ADD_NEW = "(add new brand)"
    PRICE_LEVELS = ["VERY HIGH END", "HIGH END", "MID HIGH"]

    BRAND_SELECT = "(select brand)"
    CATEGORY_SELECT = "(select category)"

    # -------------------------
    # STYLING
    # -------------------------
    st.markdown(
        """
        <style>
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div {
            background-color: #CDCDCD !important;
        }

        input::placeholder {
            color: #5f5f5f;
        }

        button[kind="primary"] {
            background-color: #228B22 !important;
            color: white !important;
            border: none !important;
        }

        button[kind="primary"]:hover {
            background-color: #1e7a1e !important;
        }

        div[data-testid="stAlert"][role="alert"] {
            border-left: 6px solid #228B22 !important;
            border-radius: 10px;
        }

        div[data-testid="stAlert"] svg {
            color: #228B22 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    tab_new, tab_search = st.tabs(["New Sale", "Price Search"])

    # =========================
    # NEW SALE
    # =========================
    with tab_new:
        st.header("Record a new sale")

        brands = load_brand_levels()
        brand_list = [b["brand"] for b in brands]
        brand_to_level = {b["brand"]: b["price_level"] for b in brands}

        selected_brand = st.selectbox(
            "Brand",
            [BRAND_PLACEHOLDER, BRAND_ADD_NEW] + brand_list,
            key="ns_brand",
        )

        final_brand = ""
        brand_price_level = ""

        if selected_brand == BRAND_ADD_NEW:
            raw_brand = st.text_input(
                "New brand name",
                placeholder="Enter new brand name",
                key="ns_new_brand",
            )
            final_brand = normalize_label(raw_brand)

            brand_price_level = st.selectbox(
                "Select price level for this new brand",
                PRICE_LEVELS,
                key="ns_new_brand_level",
            )

        elif selected_brand != BRAND_PLACEHOLDER:
            final_brand = selected_brand
            brand_price_level = brand_to_level.get(final_brand, "")
            if brand_price_level:
                st.info(f"PRICE LEVEL FOR {final_brand}: {brand_price_level}")

        st.subheader("Category")

        if not final_brand:
            st.selectbox(
                "Category",
                ["Select brand first"],
                disabled=True,
                key="ns_cat_disabled",
            )
            final_category = ""
        else:
            categories = load_categories_for_brand(final_brand)
            category_choice = st.selectbox(
                "Category",
                ["ADD NEW CATEGORY"] + categories,
                key="ns_category",
            )

            if category_choice == "ADD NEW CATEGORY":
                final_category = normalize_label(
                    st.text_input(
                        "New category name",
                        placeholder="Enter new category",
                        key="ns_new_cat",
                    )
                )
            else:
                final_category = category_choice

        st.subheader("Price")

        raw_price = st.text_input(
            "Price",
            placeholder="Enter price (numbers only)",
            label_visibility="collapsed",
            key="ns_price",
        )

        cleaned_price = clean_price_input(raw_price)
        if cleaned_price:
            st.caption(f"Interpreted as {format_price(cleaned_price)}")

        on_sale = st.checkbox("On sale?", key="ns_on_sale")

        if st.button("Save sale", type="primary"):
            if not final_brand or not final_category or not cleaned_price:
                st.error("Please complete all required fields.")
                st.stop()

            if selected_brand == BRAND_ADD_NEW:
                upsert_brand_level(final_brand, brand_price_level)

            insert_sale(
                final_brand,
                final_category,
                cleaned_price,
                on_sale,
                brand_price_level,
            )

            st.success("Sale saved.")

    # =========================
    # PRICE SEARCH
    # =========================
    with tab_search:
        st.header("Price Search")

        brands = [b["brand"] for b in load_brand_levels()]

        search_brand = st.selectbox(
            "Brand",
            [BRAND_SELECT] + brands,
            key="ps_brand",
        )

        if search_brand == BRAND_SELECT:
            st.selectbox(
                "Category",
                ["Select brand first"],
                disabled=True,
                key="ps_cat_disabled",
            )
            st.stop()

        categories = load_categories_for_brand(search_brand)

        search_category = st.selectbox(
            "Category",
            [CATEGORY_SELECT] + categories,
            key="ps_category",
        )

        if search_category == CATEGORY_SELECT:
            st.stop()

        res = (
            supabase.table("sales")
            .select("*")
            .eq("brand", search_brand)
            .eq("category", search_category)
            .execute()
            .data
        ) or []

        if not res:
            st.stop()

        prices = [float(r["price"]) for r in res if r.get("price") is not None]

        st.subheader(f"{len(prices)} SALE(
