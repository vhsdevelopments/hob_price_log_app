import re
import streamlit as st
from supabase import create_client
import streamlit.components.v1 as components


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
# SUPABASE CONFIG
# =========================================================

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# =========================================================
# CONSTANTS
# =========================================================

BRAND_PLACEHOLDER = "(click or type to search)"
BRAND_ADD_NEW = "(add new brand)"
BRAND_SELECT = "(select brand)"

CATEGORY_SELECT = "(select category)"
CATEGORY_ADD_NEW = "(add new category)"

PRICE_LEVELS = ["VERY HIGH END", "HIGH END", "MID HIGH"]


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


def clear_new_sale_form():
    for key in [
        "ns_brand",
        "ns_new_brand",
        "ns_new_brand_level",
        "ns_category",
        "ns_new_cat",
        "ns_price",
        "ns_on_sale",
    ]:
        st.session_state.pop(key, None)

    st.session_state["show_saved_dialog"] = False


# =========================================================
# DATA
# =========================================================

def load_brand_levels():
    res = (
        supabase.table("brand_price_levels")
        .select("brand, price_level")
        .order("brand")
        .execute()
        .data
    ) or []

    out = []
    for r in res:
        b = normalize_label(r.get("brand"))
        pl = normalize_label(r.get("price_level"))
        if b:
            out.append({"brand": b, "price_level": pl})
    return out


def get_brand_price_level(brand: str) -> str:
    row = (
        supabase.table("brand_price_levels")
        .select("price_level")
        .eq("brand", brand)
        .limit(1)
        .execute()
        .data
    ) or []
    if not row:
        return ""
    return normalize_label(row[0].get("price_level"))


def load_categories_for_brand(brand):
    res = (
        supabase.table("sales")
        .select("category")
        .eq("brand", brand)
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
# POPUP
# =========================================================

@st.dialog("Sale saved")
def sale_saved_dialog():
    st.write("The sale has been recorded successfully.")

    if st.button("Continue", type="primary"):
        clear_new_sale_form()
        st.rerun()


# =========================================================
# MAIN
# =========================================================

def main():
    st.set_page_config(page_title="HOB Upscale Price Log", layout="wide")
    require_login()

    if "show_saved_dialog" not in st.session_state:
        st.session_state["show_saved_dialog"] = False

    st.markdown(
        """
        <style>
        :root { color-scheme: light !important; }

        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div {
            background-color: #CDCDCD !important;
        }

        input::placeholder { color: #5f5f5f; }

        button[kind="primary"] {
            background-color: #228B22 !important;
            color: white !important;
            border: none !important;
        }

        button[kind="primary"]:hover {
            background-color: #1e7a1e !important;
        }

        button[title="Settings"] { display: none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    tab_new, tab_search, tab_about = st.tabs(["New Sale", "Price Search", "About"])

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
            key="ns_brand",
        )

        final_brand = ""
        brand_price_level = ""

        if selected_brand == BRAND_ADD_NEW:
            final_brand = normalize_label(st.text_input("New brand name", key="ns_new_brand"))
            brand_price_level = st.selectbox(
                "Select price level for this new brand",
                PRICE_LEVELS,
                key="ns_new_brand_level",
            )
        elif selected_brand != BRAND_PLACEHOLDER:
            final_brand = selected_brand
            brand_price_level = brand_to_level.get(final_brand, "")

        st.subheader("Category")

        final_category = ""

        if not final_brand:
            st.selectbox(
                "Category",
                ["Select brand first"],
                disabled=True,
                key="ns_cat_disabled",
            )
        else:
            categories = load_categories_for_brand(final_brand)
            category_choice = st.selectbox(
                "Category",
                [CATEGORY_SELECT, CATEGORY_ADD_NEW] + categories,
                key="ns_category",
            )

            if category_choice == CATEGORY_ADD_NEW:
                final_category = normalize_label(st.text_input("New category name", key="ns_new_cat"))
            elif category_choice != CATEGORY_SELECT:
                final_category = category_choice
            else:
                final_category = ""

        st.subheader("Price")

        price_disabled = not (final_brand and final_category)

        raw_price = st.text_input(
            "Price",
            placeholder="Enter price (numbers only)",
            label_visibility="collapsed",
            key="ns_price",
            disabled=price_disabled,
        )

        cleaned_price = clean_price_input(raw_price)

        if cleaned_price and not price_disabled:
            st.caption(f"Interpreted as {format_price(cleaned_price)}")

        on_sale = st.checkbox("On sale?", key="ns_on_sale", disabled=price_disabled)

        col_save, col_clear = st.columns([2, 2])

        with col_save:
            if st.button("Save sale", type="primary"):
                if not final_brand or not final_category or not cleaned_price:
                    st.error("Please complete all required fields.")
                else:
                    if selected_brand == BRAND_ADD_NEW:
                        upsert_brand_level(final_brand, brand_price_level)

                    insert_sale(final_brand, final_category, cleaned_price, on_sale, brand_price_level)
                    st.session_state["show_saved_dialog"] = True

        with col_clear:
            if st.button("Clear form", key="clear_form_btn"):
                clear_new_sale_form()
                st.rerun()

        components.html(
            """
            <script>
            (function() {
              if (window.__hobEscListenerAdded) return;
              window.__hobEscListenerAdded = true;

              document.addEventListener("keydown", function(e) {
                if (e.key === "Escape") {
                  try {
                    const buttons = window.parent.document.querySelectorAll("button");
                    for (const b of buttons) {
                      if ((b.innerText || "").trim() === "Clear form") {
                        b.click();
                        break;
                      }
                    }
                  } catch (err) {}
                }
              });
            })();
            </script>
            """,
            height=0,
        )

        if st.session_state.get("show_saved_dialog"):
            sale_saved_dialog()

    # =========================
    # PRICE SEARCH
    # =========================
    with tab_search:
        st.header("Price Search")

        brands = [b["brand"] for b in load_brand_levels()]
        search_brand = st.selectbox("Brand", [BRAND_SELECT] + brands, key="ps_brand")

        if search_brand != BRAND_SELECT:
            categories = load_categories_for_brand(search_brand)
            search_category = st.selectbox("Category", [CATEGORY_SELECT] + categories, key="ps_category")

            if search_category != CATEGORY_SELECT:
                res = (
                    supabase.table("sales")
                    .select("*")
                    .eq("brand", search_brand)
                    .eq("category", search_category)
                    .execute()
                    .data
                ) or []

                prices = [float(r["price"]) for r in res if r.get("price") is not None]

                if prices:
                    sale_count = len(prices)
                    discount_count = sum(1 for r in res if r.get("on_sale"))

                    price_level = next(
                        (normalize_label(r.get("price_level")) for r in res if r.get("price_level")),
                        "",
                    )
                    if not price_level:
                        price_level = get_brand_price_level(search_brand)

                    avg_price = sum(prices) / sale_count
                    low_price = min(prices)
                    high_price = max(prices)

                    st.subheader(f"{sale_count} SALE(S) FOUND.")
                    st.subheader(f"{discount_count} SALE(S) WITH DISCOUNTS APPLIED.")

                    if price_level:
                        st.markdown(f"**PRICE LEVEL:** {price_level}")
                    st.markdown(f"**AVERAGE PRICE SOLD:** {format_price(avg_price)}")
                    st.markdown(f"**LOWEST PRICE SOLD:** {format_price(low_price)}")
                    st.markdown(f"**HIGHEST PRICE SOLD:** {format_price(high_price)}")

    # =========================
    # ABOUT
    # =========================
    with tab_about:
        st.header("About this app")
        st.markdown(
            """
            **HOB Upscale Price Log**

            This internal tool supports pricing consistency and informed decision making at The Hospice Opportunity Boutique.

            Developed by Cecilia Abreu  
            Property of Vancouver Hospice Society
            """
        )


if __name__ == "__main__":
    main()
