import os
import re
import difflib
import streamlit as st
import pandas as pd
from supabase import create_client


# -------------------------------------------------------------------
# SUPABASE CONFIG
# -------------------------------------------------------------------



SUPABASE_URL = "https://kvfnffdnplmxgdltywbn.supabase.co"

SUPABASE_SERVICE_ROLE = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt2Zm5mZmRucGxteGdkbHR5d2JuIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTI1MzI0NiwiZXhwIjoyMDgwODI5MjQ2fQ.oHDnmLEOyqN1hM0Qd5S4u1sEtEjsgp1OPmAyHuShO3U"
)

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


def find_similar_label(name: str, existing_labels, cutoff: float = 0.82):
    if not name:
        return []
    norm_name = normalize_label(name)
    norm_map = {normalize_label(lbl): lbl for lbl in existing_labels if lbl}
    matches_norm = difflib.get_close_matches(
        norm_name,
        list(norm_map.keys()),
        n=3,
        cutoff=cutoff,
    )
    return [norm_map[n] for n in matches_norm]


def clean_price_input(val: str):
    if val is None:
        return None
    cleaned = re.sub(r"[^0-9.]", "", str(val))
    if cleaned.count(".") > 1:
        parts = cleaned.split(".")
        cleaned = parts[0] + "." + "".join(parts[1:])
    return cleaned if cleaned else None


def format_price(val):
    try:
        return f"${float(val):,.2f}"
    except Exception:
        return str(val)


def safe_range(limit: int):
    return (0, max(0, int(limit) - 1))


# =========================================================
# DATA LOADERS
# =========================================================

def load_brand_levels(limit: int = 5000):
    start, end = safe_range(limit)
    resp = (
        supabase.table("brand_price_levels")
        .select("brand,price_level")
        .order("brand")
        .range(start, end)
        .execute()
    )
    data = resp.data or []
    out = []
    for r in data:
        b = normalize_label(r.get("brand"))
        pl = normalize_label(r.get("price_level"))
        if b:
            out.append({"brand": b, "price_level": pl})
    return sorted(out, key=lambda x: x["brand"])


def load_categories_for_brand(brand: str, limit: int = 10000):
    start, end = safe_range(limit)
    resp = (
        supabase.table("sales")
        .select("category")
        .eq("brand", brand)
        .range(start, end)
        .execute()
    )
    data = resp.data or []
    cats = {
        normalize_label(r.get("category"))
        for r in data
        if r.get("category")
    }
    return sorted(c for c in cats if c)


def upsert_brand_level(brand: str, price_level: str):
    supabase.table("brand_price_levels").upsert(
        {"brand": brand, "price_level": price_level},
        on_conflict="brand",
    ).execute()


def insert_sale(brand, category, price, on_sale, notes, price_level):
    supabase.table("sales").insert(
        {
            "brand": brand,
            "category": category,
            "price": float(price),
            "on_sale": bool(on_sale),
            "notes": notes or "",
            "price_level": price_level,
        }
    ).execute()


# =========================================================
# UI HELPERS
# =========================================================

def brand_dropdown_options(brands):
    return ["SEARCH EXISTING BRAND", "ADD NEW BRAND"] + brands


def category_dropdown_options(categories):
    return ["ADD NEW CATEGORY"] + categories


# =========================================================
# MAIN APP
# =========================================================

def main():
    st.set_page_config(page_title="HOB Upscale Price Log", layout="wide")

    tab_new, tab_search = st.tabs(["New Sale", "Price Search"])

    PRICE_LEVELS = ["VERY HIGH END", "HIGH END", "MID HIGH"]

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
            options=brand_dropdown_options(brand_list),
            key="brand_select",
        )

        final_brand = ""
        brand_price_level = ""

        if selected_brand == "ADD NEW BRAND":
            raw_brand = st.text_input("New brand name", key="new_brand").strip()
            final_brand = normalize_label(raw_brand)

            brand_price_level = st.selectbox(
                "Select price level for this new brand",
                PRICE_LEVELS,
                key="new_brand_pl",
            )

        elif selected_brand != "SEARCH EXISTING BRAND":
            final_brand = selected_brand
            brand_price_level = brand_to_level.get(final_brand, "")

            if brand_price_level:
                st.info(f"PRICE LEVEL FOR {final_brand}: {brand_price_level}")

        st.subheader("Category")

        if not final_brand:
            st.selectbox(
                "Category",
                options=["Select brand first"],
                disabled=True,
                key="cat_disabled",
            )
            final_category = ""
        else:
            categories = load_categories_for_brand(final_brand)
            category_choice = st.selectbox(
                "Category",
                options=category_dropdown_options(categories),
                key="category_select",
            )

            if category_choice == "ADD NEW CATEGORY":
                final_category = normalize_label(
                    st.text_input("New category name", key="new_cat")
                )
            else:
                final_category = category_choice

        st.subheader("Price")

        raw_price = st.text_input("Enter price (numbers only)", key="price")
        cleaned_price = clean_price_input(raw_price)
        if cleaned_price:
            st.caption(f"Interpreted as {format_price(cleaned_price)}")

        on_sale = st.checkbox("On sale?")
        notes = st.text_area("Notes (optional)")

        if st.button("Save sale"):
            if not final_brand:
                st.error("Please select or enter a brand.")
                return
            if not final_category:
                st.error("Please select or enter a category.")
                return
            if not cleaned_price:
                st.error("Please enter a valid price.")
                return
            if selected_brand == "ADD NEW BRAND":
                upsert_brand_level(final_brand, brand_price_level)

            insert_sale(
                final_brand,
                final_category,
                cleaned_price,
                on_sale,
                notes,
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
    options=["SELECT BRAND"] + brands,
    index=0,
    key="search_brand",
)
if search_brand == "SELECT BRAND":
    st.selectbox(
        "Category",
        options=["Select brand first"],
        disabled=True,
        key="search_category_disabled",
    )
    st.info("Select a brand to see results.")
    return

        categories = load_categories_for_brand(search_brand)
        search_category = st.selectbox("Category", categories, key="search_cat")

        res = (
            supabase.table("sales")
            .select("*")
            .eq("brand", search_brand)
            .eq("category", search_category)
            .execute()
            .data
        ) or []

        if not res:
            st.info("No matching sales found.")
            return

        prices = [r["price"] for r in res if r.get("price") is not None]

        st.subheader(f"{len(prices)} SALE(S) FOUND.")
        st.subheader(f"{sum(1 for r in res if r.get('on_sale'))} SALE(S) WITH DISCOUNTS APPLIED.")

        pl = next((r["price_level"] for r in res if r.get("price_level")), "")
        if pl:
            st.write(f"**PRICE LEVEL:** {pl}")

        st.write(f"**AVERAGE PRICE SOLD:** {format_price(sum(prices)/len(prices))}")
        st.write(f"**LOWEST PRICE SOLD:** {format_price(min(prices))}")
        st.write(f"**HIGHEST PRICE SOLD:** {format_price(max(prices))}")


if __name__ == "__main__":
    main()





