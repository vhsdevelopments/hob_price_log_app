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




# =============================
# HELPERS
# =============================
def normalize(text):
    return str(text).strip().upper() if text else None

def clean_price(val):
    if not val:
        return None
    cleaned = re.sub(r"[^0-9.]", "", val)
    return float(cleaned) if cleaned else None

def fetch_sales():
    resp = supabase.table("sales").select("*").execute()
    return pd.DataFrame(resp.data or [])

def fetch_brands():
    df = fetch_sales()
    if df.empty:
        return []
    return sorted(df["brand"].dropna().unique().tolist())

def fetch_categories_for_brand(brand):
    df = fetch_sales()
    if df.empty:
        return []
    return sorted(
        df[df["brand"] == brand]["category"]
        .dropna()
        .unique()
        .tolist()
    )

def fetch_price_level(brand):
    resp = (
        supabase.table("brand_price_levels")
        .select("price_level")
        .eq("brand", brand)
        .limit(1)
        .execute()
    )
    if resp.data:
        return resp.data[0]["price_level"]
    return None

# =============================
# PAGE SETUP
# =============================
st.set_page_config(page_title="HOB Price Log", layout="wide")
st.title("HOB / SALE PRICE LOG")

tabs = st.tabs(["New Sale", "Price Search"])

# =============================
# NEW SALE TAB
# =============================
with tabs[0]:
    st.header("Record a new sale")

    st.markdown("""
    **INSTRUCTIONS**
    1. Select a brand or add a new one  
    2. Select a category or add a new one  
    3. Enter price  
    4. If brand is new, select price level
    """)

    ADD_NEW = "ADD NEW"

    # -------- BRAND --------
    brands = fetch_brands()
    brand_choice = st.selectbox(
        "Brand",
        [ADD_NEW] + brands,
        index=None,
        placeholder="Select brand"
    )

    brand = None
    price_level = None

    if brand_choice == ADD_NEW:
        new_brand = st.text_input("New brand name")
        brand = normalize(new_brand)
        if brand:
            price_level = st.selectbox(
                "Price level",
                ["VERY HIGH END", "HIGH END", "MID HIGH", "MID", "LOW"],
                index=None,
                placeholder="Select price level"
            )
    elif brand_choice:
        brand = brand_choice
        price_level = fetch_price_level(brand)
        if price_level:
            st.info(f"PRICE LEVEL FOR {brand}: {price_level}")

    # -------- CATEGORY --------
    if not brand:
        st.selectbox(
            "Category",
            [],
            index=None,
            placeholder="Select brand first",
            disabled=True
        )
        category = None
    else:
        categories = fetch_categories_for_brand(brand)
        category_choice = st.selectbox(
            "Category",
            [ADD_NEW] + categories,
            index=None,
            placeholder="Select category"
        )

        if category_choice == ADD_NEW:
            new_cat = st.text_input("New category name")
            category = normalize(new_cat)
        else:
            category = normalize(category_choice)

    # -------- PRICE --------
    price_input = st.text_input(
        "Price",
        placeholder="Numbers only"
    )
    price = clean_price(price_input)

    on_sale = st.checkbox("On sale?")
    notes = st.text_area("Notes (optional)")

    # -------- SAVE --------
    if st.button("Save sale"):
        if not all([brand, category, price]):
            st.error("Brand, category, and price are required.")
        else:
            supabase.table("sales").insert({
                "brand": brand,
                "category": category,
                "price": price,
                "on_sale": on_sale,
                "notes": notes
            }).execute()

            if price_level and not fetch_price_level(brand):
                supabase.table("brand_price_levels").insert({
                    "brand": brand,
                    "price_level": price_level
                }).execute()

            st.success("Sale saved successfully.")

# =============================
# PRICE SEARCH TAB
# =============================
with tabs[1]:
    st.header("Price Search")

    df = fetch_sales()

    if df.empty:
        st.info("No sales recorded yet.")
    else:
        brand = st.selectbox(
            "Brand",
            sorted(df["brand"].unique()),
            index=None,
            placeholder="Select brand"
        )

        if brand:
            cats = sorted(df[df["brand"] == brand]["category"].unique())
            category = st.selectbox(
                "Category",
                cats,
                index=None,
                placeholder="Select category"
            )

            if category:
                subset = df[
                    (df["brand"] == brand) &
                    (df["category"] == category)
                ]

                total_sales = len(subset)
                on_sale_count = subset["on_sale"].sum()

                st.markdown(f"### {total_sales} SALE(S) FOUND")
                st.markdown(f"### {on_sale_count} SALE(S) WITH DISCOUNTS APPLIED")

                level = fetch_price_level(brand)
                if level:
                    st.markdown(f"**PRICE LEVEL:** {level}")

                st.markdown(f"**AVERAGE PRICE SOLD:** ${subset['price'].mean():.2f}")
                st.markdown(f"**LOWEST PRICE SOLD:** ${subset['price'].min():.2f}")
                st.markdown(f"**HIGHEST PRICE SOLD:** ${subset['price'].max():.2f}")


