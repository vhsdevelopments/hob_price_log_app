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

# Do not hard code your service role key into GitHub
# Put it in Streamlit secrets or an environment variable
# Streamlit secrets key name can be SUPABASE_SERVICE_ROLE
SUPABASE_SERVICE_ROLE = (
    st.secrets.get("SUPABASE_SERVICE_ROLE", "") if hasattr(st, "secrets") else ""
) or os.getenv("SUPABASE_SERVICE_ROLE", "")

if not SUPABASE_SERVICE_ROLE:
    st.error("Missing SUPABASE_SERVICE_ROLE. Add it to Streamlit secrets or environment variables.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE)


# =========================================================
# HELPERS
# =========================================================

def normalize_label(name: str) -> str:
    if not name:
        return ""
    name = name.upper().strip()
    name = re.sub(r"[^A-Z0-9 &/]", "", name)
    if len(name) > 3 and name.endswith("S"):
        name = name[:-1]
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
    return cleaned if cleaned != "" else None


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
        .order("brand", desc=False)
        .range(start, end)
        .execute()
    )
    data = resp.data or []
    cleaned = []
    for row in data:
        b = normalize_label(row.get("brand") or "")
        pl = normalize_label(row.get("price_level") or "")
        if b:
            cleaned.append({"brand": b, "price_level": pl})
    cleaned = sorted(cleaned, key=lambda r: r["brand"])
    return cleaned


def load_categories_for_brand(brand: str, limit: int = 10000):
    if not brand:
        return []
    start, end = safe_range(limit)
    resp = (
        supabase.table("sales")
        .select("category")
        .eq("brand", brand)
        .range(start, end)
        .execute()
    )
    data = resp.data or []
    cats = sorted({
        normalize_label(r.get("category") or "")
        for r in data
        if r.get("category")
    })
    return [c for c in cats if c]


def upsert_brand_level(brand: str, price_level: str):
    supabase.table("brand_price_levels").upsert(
        {"brand": brand, "price_level": price_level},
        on_conflict="brand",
    ).execute()


def insert_sale(brand: str, category: str, price: float, on_sale: bool, notes: str, price_level: str):
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

def brand_dropdown_options(brand_list):
    return ["ADD NEW BRAND"] + brand_list


def category_dropdown_options(category_list):
    return ["ADD NEW CATEGORY"] + category_list


# =========================================================
# MAIN APP
# =========================================================

def main():
    st.set_page_config(page_title="HOB Upscale Price Log", layout="wide")

    tab_new, tab_search = st.tabs(["New Sale", "Price Search"])

    # Only these price levels exist
    pl_options = ["VERY HIGH END", "HIGH END", "MID HIGH"]

    # =========================
    # NEW SALE TAB
    # =========================
    with tab_new:
        st.header("Record a new sale")

        st.markdown(
            """
            **INSTRUCTIONS:**
            1. SELECT A BRAND OR INPUT NEW BRAND NAME  
            2. SELECT A CATEGORY OR INPUT NEW CATEGORY  
            3. ADD PRICE  
            4. IF BRAND IS NEW, SELECT A PRICE LEVEL  
            """
        )

        brand_rows = load_brand_levels()
        brand_list = sorted({b["brand"] for b in brand_rows if b.get("brand")})
        brand_to_level = {b["brand"]: b.get("price_level") for b in brand_rows if b.get("brand")}

        st.subheader("Brand")

        selected_brand = st.selectbox(
            "Brand",
            options=brand_dropdown_options(brand_list),
            index=0,
            placeholder="Select brand",
            key="new_brand_selectbox",
        )

        final_brand = ""
        brand_price_level = ""
        is_new_brand = False

        new_brand_raw = ""
        brand_resolution = None
        similar_brands = []

        if selected_brand == "ADD NEW BRAND":
            is_new_brand = True

            new_brand_raw = st.text_input(
                "New brand name",
                key="new_brand_text_input",
            ).strip()

            if new_brand_raw:
                similar_brands = find_similar_label(new_brand_raw, brand_list)
                if similar_brands:
                    options = [f"KEEP NEW: {normalize_label(new_brand_raw)}"] + [
                        f"USE EXISTING: {b}" for b in similar_brands
                    ]
                    brand_resolution = st.radio(
                        "We found similar existing brands. Choose one:",
                        options,
                        key="new_brand_resolution_radio",
                    )

            if similar_brands and brand_resolution and brand_resolution.startswith("USE EXISTING: "):
                final_brand = brand_resolution.replace("USE EXISTING: ", "").strip()
                is_new_brand = False

                brand_price_level = brand_to_level.get(final_brand, "")
                if brand_price_level:
                    st.info(f"PRICE LEVEL FOR {final_brand}: {brand_price_level}")
                else:
                    brand_price_level = st.selectbox(
                        "Select price level for this brand",
                        pl_options,
                        key="existing_brand_missing_pl_selectbox",
                    )
            else:
                final_brand = normalize_label(new_brand_raw) if new_brand_raw else ""

                # This only appears when ADD NEW BRAND is selected
                brand_price_level = st.selectbox(
                    "Select price level for this new brand",
                    pl_options,
                    key="new_brand_pl_selectbox",
                )

        else:
            final_brand = selected_brand
            brand_price_level = brand_to_level.get(final_brand, "")

            if brand_price_level:
                st.info(f"PRICE LEVEL FOR {final_brand}: {brand_price_level}")
            else:
                # Only show this if existing brand has no saved price level
                brand_price_level = st.selectbox(
                    "Select price level for this brand",
                    pl_options,
                    key="existing_brand_pl_selectbox",
                )

        st.subheader("Category")

        if not final_brand:
            st.selectbox(
                "Category",
                options=[],
                index=None,
                placeholder="Select brand first",
                disabled=True,
                key="new_category_disabled_selectbox",
            )
            category_choice = None
            new_category_raw = ""
            cat_resolution = None
            similar_cats = []
            final_category = ""
        else:
            categories_for_brand = load_categories_for_brand(final_brand)

            category_choice = st.selectbox(
                "Category",
                options=category_dropdown_options(categories_for_brand),
                index=None,
                placeholder="Select category",
                key="new_category_selectbox",
            )

            new_category_raw = ""
            cat_resolution = None
            similar_cats = []
            final_category = ""

            if category_choice == "ADD NEW CATEGORY":
                new_category_raw = st.text_input(
                    "New category name",
                    key="new_category_text_input",
                ).strip()

                if new_category_raw:
                    similar_cats = find_similar_label(new_category_raw, categories_for_brand)
                    if similar_cats:
                        options = [f"KEEP NEW: {normalize_label(new_category_raw)}"] + [
                            f"USE EXISTING: {c}" for c in similar_cats
                        ]
                        cat_resolution = st.radio(
                            "We found similar existing categories for this brand. Choose one:",
                            options,
                            key="new_category_resolution_radio",
                        )

                if similar_cats and cat_resolution and cat_resolution.startswith("USE EXISTING: "):
                    final_category = cat_resolution.replace("USE EXISTING: ", "").strip()
                else:
                    final_category = normalize_label(new_category_raw) if new_category_raw else ""
            elif category_choice:
                final_category = category_choice

        st.subheader("Price")

        raw_price = st.text_input(
            "Enter price (numbers only)",
            placeholder="34.99",
            key="new_price_text_input",
        )
        cleaned_price = clean_price_input(raw_price)
        if cleaned_price:
            st.caption(f"Interpreted as {format_price(cleaned_price)}")

        on_sale = st.checkbox("On sale?", key="new_on_sale_checkbox")
        notes = st.text_area("Notes (optional)", key="new_notes_text_area")

        if st.button("Save sale", key="new_save_button"):
            if selected_brand == "ADD NEW BRAND" and not new_brand_raw:
                st.error("Please enter a brand name.")
                return

            if selected_brand == "ADD NEW BRAND" and similar_brands and brand_resolution is None:
                st.error("Please choose whether to use an existing brand or keep the new one.")
                return

            if not final_brand:
                st.error("Please select or enter a brand.")
                return

            if not final_category:
                st.error("Please select or enter a category.")
                return

            if not cleaned_price:
                st.error("Please enter a valid price.")
                return

            if not brand_price_level:
                st.error("Please select a price level.")
                return

            if brand_price_level not in pl_options:
                st.error("Price level must be VERY HIGH END, HIGH END, or MID HIGH.")
                return

            upsert_brand_level(final_brand, brand_price_level)

            insert_sale(
                brand=final_brand,
                category=final_category,
                price=float(cleaned_price),
                on_sale=on_sale,
                notes=notes,
                price_level=brand_price_level,
            )

            st.success(
                f"Saved sale for {final_brand} · {final_category} · {format_price(cleaned_price)}"
                + (" (ON SALE)" if on_sale else "")
            )

    # =========================
    # PRICE SEARCH TAB
    # =========================
    with tab_search:
        st.header("Price Search")

        brand_rows = load_brand_levels()
        brand_list = sorted({b["brand"] for b in brand_rows if b.get("brand")})

        search_brand = st.selectbox(
            "Brand",
            options=brand_list,
            index=None,
            placeholder="Select brand",
            key="search_brand_selectbox",
        )

        if not search_brand:
            st.selectbox(
                "Category",
                options=[],
                index=None,
                placeholder="Select brand first",
                disabled=True,
                key="search_category_disabled_selectbox",
            )
            st.info("Select a brand to see categories and results.")
            return

        categories_for_brand = load_categories_for_brand(search_brand)
        search_category = st.selectbox(
            "Category",
            options=categories_for_brand,
            index=None,
            placeholder="Select category",
            key="search_category_selectbox",
        )

        if not search_category:
            st.info("Select a category to see results.")
            return

        res = (
            supabase.table("sales")
            .select("*")
            .eq("brand", search_brand)
            .eq("category", search_category)
            .range(0, 10000)
            .execute()
            .data
        ) or []

        if not res:
            st.info("No matching sales found.")
            return

        prices = [float(r["price"]) for r in res if r.get("price") is not None]
        avg_p = sum(prices) / len(prices) if prices else 0.0
        low_p = min(prices) if prices else 0.0
        high_p = max(prices) if prices else 0.0

        discount_count = sum(1 for r in res if r.get("on_sale"))

        price_level = ""
        for r in res:
            if r.get("price_level"):
                price_level = normalize_label(str(r.get("price_level")))
                break

        st.subheader(f"{len(res)} SALE(S) FOUND.")
        st.subheader(f"{discount_count} SALE(S) WITH DISCOUNTS APPLIED.")

        if price_level:
            st.write("")
            st.write(f"**PRICE LEVEL:** {price_level}")

        st.write("")
        st.write(f"**AVERAGE PRICE SOLD:** {format_price(avg_p)}")
        st.write(f"**LOWEST PRICE SOLD:** {format_price(low_p)}")
        st.write(f"**HIGHEST PRICE SOLD:** {format_price(high_p)}")

        df = pd.DataFrame(res)
        if "price" in df.columns:
            df["price"] = df["price"].apply(format_price)
        st.dataframe(df, use_container_width=True)


if __name__ == "__main__":
    main()
