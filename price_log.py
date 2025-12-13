import re
import difflib
import streamlit as st
import pandas as pd
from supabase import create_client


# -------------------------------------------------------------------
# SUPABASE CONFIG
# -------------------------------------------------------------------

# Your Supabase project URL
SUPABASE_URL = "https://kvfnffdnplmxgdltywbn.supabase.co"

# Your service_role key
SUPABASE_SERVICE_ROLE = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt2Zm5mZmRucGxteGdkbHR5d2JuIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTI1MzI0NiwiZXhwIjoyMDgwODI5MjQ2fQ.oHDnmLEOyqN1hM0Qd5S4u1sEtEjsgp1OPmAyHuShO3U"
)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE)



# -------------------------------------------------
# HELPERS
# -------------------------------------------------

def clean_price_input(val: str):
    """Keep only digits and decimal point. Convert empty to None."""
    if val is None:
        return None
    cleaned = re.sub(r"[^0-9.]", "", val)
    return cleaned if cleaned != "" else None


def format_price(val):
    """Format as $0.00."""
    try:
        return f"${float(val):,.2f}"
    except Exception:
        return val


def normalize_label(name: str) -> str:
    """
    Normalize labels so that variations collapse together:
    - sweater / SWEATERS / sweater. / sweater!
    - lululemon / lulu lemon.
    """
    if not name:
        return ""
    name = name.upper().strip()
    # keep letters, numbers, space, &, /
    name = re.sub(r"[^A-Z0-9 &/]", "", name)
    # simple plural cleanup: drop trailing S for longer words
    if len(name) > 3 and name.endswith("S"):
        name = name[:-1]
    # collapse multiple spaces
    name = re.sub(r"\s+", " ", name).strip()
    return name


def find_similar_label(name: str, existing_labels, cutoff: float = 0.82):
    """
    Find close matches to `name` among existing_labels using normalized forms.
    Returns a list of existing labels (original spelling) that are similar.
    """
    if not name:
        return []
    norm_name = normalize_label(name)
    norm_map = {
        normalize_label(lbl): lbl
        for lbl in existing_labels
        if lbl
    }
    matches_norm = difflib.get_close_matches(
        norm_name,
        list(norm_map.keys()),
        n=3,
        cutoff=cutoff,
    )
    return [norm_map[n] for n in matches_norm]


def load_brand_levels():
    """Load brands + price levels from Supabase."""
    resp = supabase.table("brand_price_levels").select("*").execute()
    data = resp.data or []
    # normalize brand field for safety
    for row in data:
        if row.get("brand"):
            row["brand"] = normalize_label(row["brand"])
    return sorted(data, key=lambda r: r.get("brand", ""))


def load_all_categories():
    """Load all unique categories from sales table."""
    resp = supabase.table("sales").select("category").execute()
    data = resp.data or []
    cats = sorted({
        normalize_label(r.get("category") or "")
        for r in data
        if r.get("category")
    })
    return cats


# -------------------------------------------------
# MAIN APP
# -------------------------------------------------

def main():
    st.set_page_config(page_title="HOB Upscale Price Log", layout="wide")
    tab_new, tab_search = st.tabs(["New Sale", "Price Search"])

    # ------------------ NEW SALE TAB ------------------
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
        brand_list = [b["brand"] for b in brand_rows]
        all_categories = load_all_categories()

        # ---------- BRAND with SMART MERGE ----------
        st.subheader("Brand")

        brand_choice = st.selectbox(
            "Brand",
            brand_list + ["ADD NEW BRAND"],
        )

        new_brand_raw = ""
        similar_brands = []
        brand_resolution = None
        brand_price_level = None

        pl_options = ["VERY HIGH END", "HIGH END", "MID HIGH", "MID", "LOW"]

        if brand_choice == "ADD NEW BRAND":
            new_brand_raw = st.text_input("New brand name").strip()

            if new_brand_raw:
                similar_brands = find_similar_label(new_brand_raw, brand_list)
                if similar_brands:
                    options = [f"KEEP NEW: {normalize_label(new_brand_raw)}"] + [
                        f"USE EXISTING: {b}" for b in similar_brands
                    ]
                    brand_resolution = st.radio(
                        "We found similar existing brands. Choose one:",
                        options,
                        key="brand_resolution",
                    )

            # Decide how to get price level
            if similar_brands and brand_resolution and brand_resolution.startswith("USE EXISTING: "):
                existing_brand_name = brand_resolution.replace("USE EXISTING: ", "")
                match = next((b for b in brand_rows if b["brand"] == existing_brand_name), None)
                if match and match.get("price_level"):
                    brand_price_level = match["price_level"]
                    st.info(f"PRICE LEVEL FOR {existing_brand_name}: {brand_price_level}")
                else:
                    brand_price_level = st.selectbox(
                        "Select price level for this brand",
                        pl_options,
                    )
            else:
                brand_price_level = st.selectbox(
                    "Select price level for this new brand",
                    pl_options,
                )
        else:
            # Existing brand: show or choose its price level
            match = next((b for b in brand_rows if b["brand"] == brand_choice), None)
            if match and match.get("price_level"):
                brand_price_level = match["price_level"]
                st.info(f"PRICE LEVEL FOR {brand_choice}: {brand_price_level}")
            else:
                brand_price_level = st.selectbox(
                    "Select price level for this brand",
                    pl_options,
                )

        # ---------- CATEGORY with SMART MERGE ----------
        st.subheader("Category")

        category_choice = st.selectbox(
            "Category",
            all_categories + ["ADD NEW CATEGORY"],
        )

        new_category_raw = ""
        similar_cats = []
        cat_resolution = None

        if category_choice == "ADD NEW CATEGORY":
            new_category_raw = st.text_input("New category name").strip()
            if new_category_raw:
                similar_cats = find_similar_label(new_category_raw, all_categories)
                if similar_cats:
                    options = [f"KEEP NEW: {normalize_label(new_category_raw)}"] + [
                        f"USE EXISTING: {c}" for c in similar_cats
                    ]
                    cat_resolution = st.radio(
                        "We found similar existing categories. Choose one:",
                        options,
                        key="cat_resolution",
                    )

        # ---------- PRICE ----------
        st.subheader("Price")

        raw_price = st.text_input(
            "Enter price (numbers only)",
            placeholder="34.99",
        )
        cleaned_price = clean_price_input(raw_price)

        if cleaned_price:
            st.caption(f"Interpreted as {format_price(cleaned_price)}")

        on_sale = st.checkbox("On sale?")
        notes = st.text_area("Notes (optional)")

        # ---------- SAVE ----------
        if st.button("Save sale"):
            # Resolve final brand
            if brand_choice == "ADD NEW BRAND":
                if not new_brand_raw:
                    st.error("Please enter a brand name.")
                    return

                # Force resolution if there are similar brands
                if similar_brands and brand_resolution is None:
                    st.error(
                        "Please choose whether to use an existing brand or keep the new one."
                    )
                    return

                if similar_brands and brand_resolution.startswith("USE EXISTING: "):
                    final_brand = brand_resolution.replace("USE EXISTING: ", "")
                    is_new_brand = False
                else:
                    final_brand = normalize_label(new_brand_raw)
                    is_new_brand = True
            else:
                final_brand = brand_choice
                is_new_brand = False

            # Resolve final category
            if category_choice == "ADD NEW CATEGORY":
                if not new_category_raw:
                    st.error("Please enter a category name.")
                    return

                if similar_cats and cat_resolution is None:
                    st.error(
                        "Please choose whether to use an existing category or keep the new one."
                    )
                    return

                if similar_cats and cat_resolution.startswith("USE EXISTING: "):
                    final_category = cat_resolution.replace("USE EXISTING: ", "")
                else:
                    final_category = normalize_label(new_category_raw)
            else:
                final_category = category_choice

            # Validation
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

            # Upsert brand-level mapping
            supabase.table("brand_price_levels").upsert(
                {
                    "brand": final_brand,
                    "price_level": brand_price_level,
                },
                on_conflict="brand",
            ).execute()

            # Insert sale row
            supabase.table("sales").insert(
                {
                    "brand": final_brand,
                    "category": final_category,
                    "price": float(cleaned_price),
                    "on_sale": on_sale,
                    "notes": notes,
                    "price_level": brand_price_level,
                }
            ).execute()

            st.success(
                f"Saved sale for {final_brand} · {final_category} · "
                f"{format_price(cleaned_price)}"
                + (" (ON SALE)" if on_sale else "")
            )

    # ------------------ SEARCH TAB ------------------
    with tab_search:
        st.header("Price Search")

        brand_rows = load_brand_levels()
        brand_list = [b["brand"] for b in brand_rows]
        search_brand = st.selectbox("Brand", ["(ALL BRANDS)"] + brand_list)

        all_categories = load_all_categories()
        search_category = st.selectbox(
            "Category",
            ["(ALL CATEGORIES)"] + all_categories,
        )

        query = supabase.table("sales").select("*")
        if search_brand != "(ALL BRANDS)":
            query = query.eq("brand", search_brand)
        if search_category != "(ALL CATEGORIES)":
            query = query.eq("category", search_category)

        res = query.execute().data or []

        if not res:
            st.info("No matching sales found.")
            return

        prices = [float(r["price"]) for r in res if r.get("price") is not None]
        if prices:
            avg_p = sum(prices) / len(prices)
            low_p = min(prices)
            high_p = max(prices)
        else:
            avg_p = low_p = high_p = 0.0

        discount_count = sum(1 for r in res if r.get("on_sale"))

        st.subheader(f"{len(res)} SALE(S) FOUND.")
        st.subheader(f"{discount_count} SALE(S) WITH DISCOUNTS APPLIED.")

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
