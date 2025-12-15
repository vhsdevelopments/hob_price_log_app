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
    return cleaned


def format_price(val):
    return f"${float(val):,.2f}"


# =========================================================
# DATA LOADERS
# =========================================================

def load_brand_levels():
    res = (
        supabase.table("brand_price_levels")
        .select("brand, price_level")
        .order("brand")
        .execute()
        .data
    ) or []

    return [
        {
            "brand": normalize_label(r.get("brand")),
            "price_level": normalize_label(r.get("price_level")),
        }
        for r in res
        if r.get("brand")
    ]


def load_categories_for_brand(brand):
    res = (
        supabase.table("sales")
        .select("category")
        .eq("brand", brand)
        .execute()
        .data
    ) or []

    return sorted(
        {normalize_label(r.get("category")) for r in res if r.get("category")}
    )


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
            "price_level": price_level,
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
    BRAND_SELECT = "(select brand)"
    CATEGORY_SELECT = "(select category)"
    PRICE_LEVELS = ["VERY HIGH END", "HIGH END", "MID HIGH"]

    # -------------------------
    # GLOBAL STYLING
    # -------------------------
    st.markdown(
        """
        <style>
        :root { color-scheme: light !important; }

        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div {
            background-color: #CDCDCD !important;
        }

        button[kind="primary"] {
            background-color: #228B22 !important;
            color: white !important;
            border: none !important;
        }

        div[data-testid="stAlert"][role="alert"] {
            border-left: 6px solid #228B22 !important;
        }

        button[title="Settings"] {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    tab_new, tab_search, tab_about = st.tabs(
        ["New Sale", "Price Search", "About"]
    )

    # =========================
    # NEW SALE
    # =========================
    with tab_new:
        st.header("Record a new sale")

        brands = load_brand_levels()
        brand_names = [b["brand"] for b in brands]
        brand_to_level = {b["brand"]: b["price_level"] for b in brands}

        selected_brand = st.selectbox(
            "Brand",
            [BRAND_PLACEHOLDER, BRAND_ADD_NEW] + brand_names,
        )

        final_brand = ""
        price_level = ""

        if selected_brand == BRAND_ADD_NEW:
            final_brand = normalize_label(
                st.text_input("New brand name", placeholder="Enter new brand")
            )
            price_level = st.selectbox(
                "Select price level for this new brand",
                PRICE_LEVELS,
            )
        elif selected_brand != BRAND_PLACEHOLDER:
            final_brand = selected_brand
            price_level = brand_to_level.get(final_brand, "")

        if not final_brand:
            st.selectbox("Category", ["Select brand first"], disabled=True)
            st.stop()

        categories = load_categories_for_brand(final_brand)
        category_choice = st.selectbox(
            "Category",
            categories + ["ADD NEW CATEGORY"],
        )

        if category_choice == "ADD NEW CATEGORY":
            category = normalize_label(
                st.text_input("New category name", placeholder="Enter new category")
            )
        else:
            category = category_choice

        price_raw = st.text_input(
            "Price",
            placeholder="Enter price (numbers only)",
            label_visibility="collapsed",
        )

        price = clean_price_input(price_raw)
        on_sale = st.checkbox("On sale?")

        if st.button("Save sale", type="primary"):
            if not final_brand or not category or not price:
                st.error("Please complete all required fields.")
                st.stop()

            if selected_brand == BRAND_ADD_NEW:
                upsert_brand_level(final_brand, price_level)

            insert_sale(final_brand, category, price, on_sale, price_level)
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
        )

        if search_brand == BRAND_SELECT:
            st.selectbox("Category", ["Select brand first"], disabled=True)
            st.stop()

        categories = load_categories_for_brand(search_brand)
        search_category = st.selectbox(
            "Category",
            [CATEGORY_SELECT] + categories,
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

        prices = [float(r["price"]) for r in res if r.get("price") is not None]

        st.subheader(f"{len(prices)} SALE(S) FOUND.")
        st.subheader(
            f"{sum(1 for r in res if r.get('on_sale'))} SALE(S) WITH DISCOUNTS APPLIED."
        )

        avg_price = sum(prices) / len(prices)

        st.markdown(
            f"""
            <div style="font-size:18px; line-height:1.8;">
            <b>PRICE LEVEL:</b> {brand_to_level.get(search_brand, "")}<br>
            <b>AVERAGE PRICE SOLD:</b> {format_price(avg_price)}<br>
            <b>LOWEST PRICE SOLD:</b> {format_price(min(prices))}<br>
            <b>HIGHEST PRICE SOLD:</b> {format_price(max(prices))}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # =========================
    # ABOUT
    # =========================
    with tab_about:
        st.header("About this app")

        st.markdown(
            """
            ### HOB Upscale Price Log

            This internal tool was developed to support pricing consistency and
            data informed decision making at **The Hospice Opportunity Boutique (HOB)**.

            The app allows staff and volunteers to:
            • Record completed sales by brand and category  
            • Track pricing trends over time  
            • Review average, lowest, and highest selling prices  
            • Apply brand level pricing guidance for upscale items  

            By centralizing this information, the app supports fair, consistent,
            and confident pricing across the store.

            ---

            **Developed by:**  
            Cecilia Abreu  

            **For:**  
            Vancouver Hospice Society  

            **Purpose:**  
            Internal operational tool supporting hospice funding through retail operations.

            ---

            © Vancouver Hospice Society. All rights reserved.
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
