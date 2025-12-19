import re
import streamlit as st
from supabase import create_client
import streamlit.components.v1 as components

# =========================================================
# SUPABASE CONFIG
# =========================================================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================================================
# CONSTANTS
# =========================================================
BRAND_PLACEHOLDER = "Select a brand"
BRAND_ADD_NEW = "Add new brand"

CATEGORY_PLACEHOLDER = "Select a category"
CATEGORY_ADD_NEW = "Add new category"

PRICE_LEVEL_SELECT = "Select price level"
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


def ensure_form_version():
    if "ns_form_version" not in st.session_state:
        st.session_state["ns_form_version"] = 0


def k(base: str) -> str:
    return f"{base}_{st.session_state['ns_form_version']}"


def clear_new_sale_form():
    st.session_state["ns_form_version"] += 1
    st.session_state["show_saved_dialog"] = False


def set_page(page_name: str):
    st.session_state["page"] = page_name


def sign_out():
    st.session_state["authed"] = False
    st.session_state["page"] = "New Sale"
    st.rerun()


def start_card():
    st.markdown('<div class="hob-card">', unsafe_allow_html=True)


def end_card():
    st.markdown("</div>", unsafe_allow_html=True)


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
        .stApp {
            background: #f6eff2;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="hob-shell">', unsafe_allow_html=True)
    st.markdown('<div class="hob-center">', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="hob-login-title">HOB Price Log</div>
        <div class="hob-login-sub">Upscale Price Tracker</div>
        """,
        unsafe_allow_html=True,
    )

    start_card()
    st.markdown('<div class="hob-card-title">Login</div>', unsafe_allow_html=True)
    password = st.text_input("", type="password", placeholder="Enter password", label_visibility="collapsed")
    if st.button("Sign In", use_container_width=True):
        if password == st.secrets["APP_PASSWORD"]:
            st.session_state.authed = True
            st.session_state["page"] = "New Sale"
            st.rerun()
        else:
            st.error("Incorrect password")
    end_card()

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.stop()


# =========================================================
# DIALOG
# =========================================================
@st.dialog("Sale saved")
def sale_saved_dialog():
    st.write("The sale has been recorded successfully.")
    if st.button("Continue", use_container_width=True):
        clear_new_sale_form()
        st.rerun()


# =========================================================
# UI STYLE
# =========================================================
def inject_css():
    st.markdown(
        """
        <style>
        :root { color-scheme: light !important; }

        .stApp {
            background: radial-gradient(1200px 600px at 50% 0%, #f9f2f5 0%, #f6eff2 45%, #f3e8ed 100%);
        }

        .hob-shell {
            max-width: 980px;
            margin: 0 auto;
            padding: 18px 18px 40px 18px;
        }

        .hob-topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 6px 16px 6px;
        }

        .hob-brand {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .hob-logo {
            width: 34px;
            height: 34px;
            border-radius: 999px;
            background: #f1dfe7;
            display: grid;
            place-items: center;
            border: 1px solid rgba(143,47,74,0.18);
        }

        .hob-brand-text {
            line-height: 1.05;
        }

        .hob-brand-title {
            font-family: Georgia, serif;
            font-weight: 700;
            letter-spacing: 0.2px;
            color: #2f1d23;
            font-size: 20px;
        }

        .hob-brand-sub {
            color: rgba(47,29,35,0.60);
            font-size: 13px;
            margin-top: 2px;
        }

        .hob-signout button {
            border-radius: 999px !important;
            border: 1px solid rgba(143,47,74,0.20) !important;
            background: rgba(255,255,255,0.75) !important;
            color: #8f2f4a !important;
            padding: 10px 14px !important;
        }

        .hob-nav {
            background: rgba(255,255,255,0.70);
            border: 1px solid rgba(143,47,74,0.14);
            border-radius: 16px;
            padding: 10px;
            box-shadow: 0 10px 30px rgba(47,29,35,0.06);
        }

        .hob-page-title {
            font-family: Georgia, serif;
            font-weight: 700;
            color: #2f1d23;
            font-size: 30px;
            margin-top: 20px;
        }

        .hob-page-sub {
            color: rgba(47,29,35,0.60);
            font-size: 14px;
            margin-top: 6px;
            margin-bottom: 18px;
        }

        .hob-card {
            background: rgba(255,255,255,0.75);
            border: 1px solid rgba(143,47,74,0.12);
            border-radius: 18px;
            padding: 18px 18px 16px 18px;
            box-shadow: 0 18px 40px rgba(47,29,35,0.07);
            margin-top: 14px;
        }

        .hob-card-title {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #8f2f4a;
            font-weight: 700;
            margin-bottom: 10px;
        }

        .hob-foot {
            text-align: center;
            color: rgba(47,29,35,0.55);
            font-size: 12px;
            margin-top: 26px;
        }

        .hob-login-title {
            font-family: Georgia, serif;
            font-weight: 700;
            color: #2f1d23;
            font-size: 28px;
            text-align: center;
            margin-top: 24px;
        }

        .hob-login-sub {
            text-align: center;
            color: rgba(47,29,35,0.60);
            font-size: 13px;
            margin-top: 6px;
            margin-bottom: 18px;
        }

        .hob-center {
            max-width: 460px;
            margin: 0 auto;
            padding-top: 40px;
        }

        .stTextInput > div > div,
        div[data-baseweb="select"] > div {
            background: rgba(249,242,245,0.90) !important;
            border: 1px solid rgba(143,47,74,0.18) !important;
            border-radius: 12px !important;
        }

        input::placeholder {
            color: rgba(47,29,35,0.45) !important;
        }

        div[data-baseweb="select"] span {
            color: rgba(47,29,35,0.92) !important;
        }

        .stCheckbox label {
            color: rgba(47,29,35,0.78) !important;
        }

        .hob-primary button {
            background: #8f2f4a !important;
            color: white !important;
            border: 0 !important;
            border-radius: 14px !important;
            padding: 12px 14px !important;
            box-shadow: 0 10px 18px rgba(143,47,74,0.20);
        }

        .hob-primary button:hover {
            background: #7e2841 !important;
        }

        .hob-ghost button {
            background: rgba(255,255,255,0.55) !important;
            color: #8f2f4a !important;
            border: 1px solid rgba(143,47,74,0.35) !important;
            border-radius: 14px !important;
            padding: 12px 14px !important;
        }

        .hob-ghost button:hover {
            background: rgba(255,255,255,0.80) !important;
        }

        .hob-muted {
            color: rgba(47,29,35,0.55);
        }

        button[title="Settings"] { display: none !important; }
        header { visibility: hidden; height: 0px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# NAV
# =========================================================
def nav_bar():
    if "page" not in st.session_state:
        st.session_state["page"] = "New Sale"

    start_card()
    st.markdown('<div class="hob-nav">', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    page = st.session_state["page"]

    with c1:
        if page == "New Sale":
            st.markdown('<div class="hob-primary">', unsafe_allow_html=True)
            if st.button("➕  New Sale", use_container_width=True):
                set_page("New Sale")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            if st.button("➕  New Sale", use_container_width=True):
                set_page("New Sale")
                st.rerun()

    with c2:
        if page == "Search":
            st.markdown('<div class="hob-primary">', unsafe_allow_html=True)
            if st.button("🔍  Search", use_container_width=True):
                set_page("Search")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            if st.button("🔍  Search", use_container_width=True):
                set_page("Search")
                st.rerun()

    with c3:
        if page == "About":
            st.markdown('<div class="hob-primary">', unsafe_allow_html=True)
            if st.button("ⓘ  About", use_container_width=True):
                set_page("About")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            if st.button("ⓘ  About", use_container_width=True):
                set_page("About")
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    end_card()


# =========================================================
# PAGES
# =========================================================
def page_new_sale():
    st.markdown('<div class="hob-page-title">Record a New Sale</div>', unsafe_allow_html=True)
    st.markdown('<div class="hob-page-sub">Log pricing information for donated items</div>', unsafe_allow_html=True)

    brands = load_brand_levels()
    brand_names = [b["brand"] for b in brands]
    brand_to_level = {b["brand"]: b["price_level"] for b in brands}

    start_card()
    st.markdown('<div class="hob-card-title">🏷️&nbsp; Brand</div>', unsafe_allow_html=True)

    selected_brand = st.selectbox(
        "",
        [BRAND_PLACEHOLDER, BRAND_ADD_NEW] + brand_names,
        key=k("ns_brand"),
        label_visibility="collapsed",
    )

    final_brand = ""
    brand_price_level = ""

    if selected_brand == BRAND_ADD_NEW:
        final_brand = normalize_label(
            st.text_input("", placeholder="New brand name", key=k("ns_new_brand"), label_visibility="collapsed")
        )

        brand_price_level_choice = st.selectbox(
            "",
            [PRICE_LEVEL_SELECT] + PRICE_LEVELS,
            index=0,
            key=k("ns_new_brand_level"),
            label_visibility="collapsed",
        )

        brand_price_level = (
            brand_price_level_choice if brand_price_level_choice != PRICE_LEVEL_SELECT else ""
        )

    elif selected_brand != BRAND_PLACEHOLDER:
        final_brand = selected_brand
        brand_price_level = brand_to_level.get(final_brand, "")

    end_card()

    start_card()
    st.markdown('<div class="hob-card-title">📁&nbsp; Category</div>', unsafe_allow_html=True)

    final_category = ""

    if not final_brand:
        st.selectbox(
            "",
            ["Select brand first"],
            disabled=True,
            key=k("ns_cat_disabled"),
            label_visibility="collapsed",
        )
    else:
        categories = load_categories_for_brand(final_brand)
        category_choice = st.selectbox(
            "",
            [CATEGORY_PLACEHOLDER, CATEGORY_ADD_NEW] + categories,
            key=k("ns_category"),
            label_visibility="collapsed",
        )

        if category_choice == CATEGORY_ADD_NEW:
            final_category = normalize_label(
                st.text_input("", placeholder="New category name", key=k("ns_new_cat"), label_visibility="collapsed")
            )
        elif category_choice != CATEGORY_PLACEHOLDER:
            final_category = category_choice
        else:
            final_category = ""

    end_card()

    start_card()
    st.markdown('<div class="hob-card-title">💲&nbsp; Price</div>', unsafe_allow_html=True)

    price_disabled = not (final_brand and final_category)

    raw_price = st.text_input(
        "",
        placeholder="Enter price (numbers only)",
        key=k("ns_price"),
        disabled=price_disabled,
        label_visibility="collapsed",
    )

    cleaned_price = clean_price_input(raw_price)

    if cleaned_price and not price_disabled:
        st.markdown(f'<div class="hob-muted">Interpreted as {format_price(cleaned_price)}</div>', unsafe_allow_html=True)

    on_sale = st.checkbox("On sale?", key=k("ns_on_sale"), disabled=price_disabled)

    end_card()

    col_save, col_clear = st.columns([3, 1])

    with col_save:
        st.markdown('<div class="hob-primary">', unsafe_allow_html=True)
        if st.button("✅  Save Sale", use_container_width=True, key=k("ns_save_btn")):
            if not final_brand or not final_category or not cleaned_price:
                st.error("Please complete all required fields.")
            elif selected_brand == BRAND_ADD_NEW and not brand_price_level:
                st.error("Please select a price level for this new brand.")
            else:
                if selected_brand == BRAND_ADD_NEW:
                    upsert_brand_level(final_brand, brand_price_level)

                insert_sale(
                    final_brand,
                    final_category,
                    cleaned_price,
                    on_sale,
                    brand_price_level,
                )
                st.session_state["show_saved_dialog"] = True
        st.markdown("</div>", unsafe_allow_html=True)

    with col_clear:
        st.markdown('<div class="hob-ghost">', unsafe_allow_html=True)
        if st.button("↩️  Clear", use_container_width=True, key=k("clear_form_btn")):
            clear_new_sale_form()
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

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
                  const t = (b.innerText || "").trim();
                  if (t === "↩️  Clear" || t === "Clear") {
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


def page_search():
    st.markdown('<div class="hob-page-title">Price Search</div>', unsafe_allow_html=True)
    st.markdown('<div class="hob-page-sub">Look up historical pricing data</div>', unsafe_allow_html=True)

    start_card()
    st.markdown('<div class="hob-card-title">🔎&nbsp; Search Criteria</div>', unsafe_allow_html=True)

    brands = [b["brand"] for b in load_brand_levels()]

    c1, c2 = st.columns(2)

    with c1:
        search_brand = st.selectbox(
            "Brand",
            [BRAND_PLACEHOLDER] + brands,
            key="ps_brand",
        )

    with c2:
        if search_brand == BRAND_PLACEHOLDER:
            st.selectbox(
                "Category",
                ["Select brand first"],
                disabled=True,
                key="ps_cat_disabled",
            )
            search_category = "Select brand first"
        else:
            categories = load_categories_for_brand(search_brand)
            search_category = st.selectbox(
                "Category",
                [CATEGORY_PLACEHOLDER] + categories,
                key="ps_category",
            )

    end_card()

    if search_brand != BRAND_PLACEHOLDER and search_category != CATEGORY_PLACEHOLDER and search_category != "Select brand first":
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

            start_card()
            st.markdown(f'<div class="hob-card-title">📊&nbsp; Results</div>', unsafe_allow_html=True)

            st.markdown(f"**{sale_count} sale(s) found.**")
            st.markdown(f"**{discount_count} sale(s) with discounts applied.**")

            if price_level:
                st.markdown(f"**Price level:** {price_level}")
            st.markdown(f"**Average price sold:** {format_price(avg_price)}")
            st.markdown(f"**Lowest price sold:** {format_price(low_price)}")
            st.markdown(f"**Highest price sold:** {format_price(high_price)}")

            end_card()
        else:
            start_card()
            st.markdown('<div class="hob-card-title">🔍&nbsp; Results</div>', unsafe_allow_html=True)
            st.write("No sales found for this brand and category yet.")
            end_card()
    else:
        st.markdown(
            """
            <div style="height: 240px; display: grid; place-items: center; color: rgba(47,29,35,0.55);">
              <div style="text-align: center;">
                <div style="font-size: 52px; opacity: 0.25;">🔎</div>
                <div style="margin-top: 10px; font-size: 16px;">Select a brand and category to view pricing history</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def page_about():
    st.markdown(
        """
        <div style="text-align:center; margin-top: 16px;">
          <div style="font-size: 56px; opacity: 0.25;">🤍</div>
          <div class="hob-page-title" style="margin-top: 6px;">About This Tool</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    start_card()
    st.markdown(
        """
        This internal tool was created to help us price every donation with care and consistency at the Hospice Opportunity Boutique (HOB).

        Each item donated helps sustain the work of Vancouver Hospice Society, turning generosity into free bereavement support and compassionate end of life care.

        By recording sales and pricing trends in one place, this tool helps volunteers make confident pricing decisions, ensuring every donation is valued and makes the greatest possible impact.
        """.strip()
    )
    end_card()

    c1, c2, c3 = st.columns(3)
    with c1:
        start_card()
        st.markdown('<div style="text-align:center; font-size: 28px; opacity: 0.9;">🎁</div>', unsafe_allow_html=True)
        st.markdown('<div style="text-align:center; font-weight:700; color:#2f1d23;">Donations</div>', unsafe_allow_html=True)
        st.markdown('<div style="text-align:center;" class="hob-muted">Every item supports our mission</div>', unsafe_allow_html=True)
        end_card()
    with c2:
        start_card()
        st.markdown('<div style="text-align:center; font-size: 28px; opacity: 0.9;">👥</div>', unsafe_allow_html=True)
        st.markdown('<div style="text-align:center; font-weight:700; color:#2f1d23;">Volunteers</div>', unsafe_allow_html=True)
        st.markdown('<div style="text-align:center;" class="hob-muted">Empowered with data insights</div>', unsafe_allow_html=True)
        end_card()
    with c3:
        start_card()
        st.markdown('<div style="text-align:center; font-size: 28px; opacity: 0.9;">🕊️</div>', unsafe_allow_html=True)
        st.markdown('<div style="text-align:center; font-weight:700; color:#2f1d23;">Community</div>', unsafe_allow_html=True)
        st.markdown('<div style="text-align:center;" class="hob-muted">Compassionate care for all</div>', unsafe_allow_html=True)
        end_card()

    st.markdown(
        """
        <div style="text-align:center; margin-top: 14px; color: rgba(47,29,35,0.62);">
          <div><b>Developed by Cecilia Abreu</b></div>
          <div>Property of Vancouver Hospice Society</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# MAIN
# =========================================================
def main():
    st.set_page_config(page_title="HOB Price Log", layout="wide")
    inject_css()
    require_login()
    ensure_form_version()

    if "show_saved_dialog" not in st.session_state:
        st.session_state["show_saved_dialog"] = False

    st.markdown('<div class="hob-shell">', unsafe_allow_html=True)

    top_left, top_right = st.columns([5, 1])
    with top_left:
        st.markdown(
            """
            <div class="hob-topbar">
              <div class="hob-brand">
                <div class="hob-logo">♡</div>
                <div class="hob-brand-text">
                  <div class="hob-brand-title">HOB Price Log</div>
                  <div class="hob-brand-sub">Upscale Price Tracker</div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with top_right:
        st.markdown('<div class="hob-signout">', unsafe_allow_html=True)
        if st.button("Sign Out", use_container_width=True):
            sign_out()
        st.markdown("</div>", unsafe_allow_html=True)

    nav_bar()

    page = st.session_state.get("page", "New Sale")
    if page == "New Sale":
        page_new_sale()
    elif page == "Search":
        page_search()
    else:
        page_about()

    st.markdown('<div class="hob-foot">© 2025 Vancouver Hospice Society</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
