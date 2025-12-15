with tab_new:
    st.header("Record a new sale")

    brands = load_brand_levels()
    brand_names = [b["brand"] for b in brands]
    brand_to_level = {b["brand"]: b["price_level"] for b in brands}

    BRAND_PLACEHOLDER = "(click or type to search)"
    BRAND_ADD_NEW = "(add new brand)"
    CATEGORY_SELECT = "(select category)"
    CATEGORY_ADD_NEW = "(add new category)"
    PRICE_LEVELS = ["VERY HIGH END", "HIGH END", "MID HIGH"]

    # Brand row with clear button
    col_brand, col_brand_clear = st.columns([12, 1])
    with col_brand:
        selected_brand = st.selectbox(
            "Brand",
            [BRAND_PLACEHOLDER, BRAND_ADD_NEW] + brand_names,
            key="ns_brand",
        )
    with col_brand_clear:
        st.write("")
        st.write("")
        if st.button("✕", key="clear_brand"):
            for k in ["ns_brand", "ns_new_brand", "ns_new_brand_level", "ns_category", "ns_new_cat", "ns_price", "ns_on_sale"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    final_brand = ""
    brand_price_level = ""

    if selected_brand == BRAND_ADD_NEW:
        raw_brand = st.text_input("New brand name", key="ns_new_brand")
        final_brand = normalize_label(raw_brand)

        brand_price_level = st.selectbox(
            "Select price level for this new brand",
            PRICE_LEVELS,
            key="ns_new_brand_level",
        )

    elif selected_brand != BRAND_PLACEHOLDER:
        final_brand = selected_brand
        brand_price_level = brand_to_level.get(final_brand, "")

    # Category header always
    st.subheader("Category")

    # Category row with clear button
    col_cat, col_cat_clear = st.columns([12, 1])
    with col_cat:
        if not final_brand:
            category_choice = st.selectbox(
                "Category",
                ["Select brand first"],
                disabled=True,
                key="ns_category_disabled",
            )
            final_category = ""
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

    with col_cat_clear:
        st.write("")
        st.write("")
        if st.button("✕", key="clear_category"):
            for k in ["ns_category", "ns_new_cat", "ns_price", "ns_on_sale"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    # Price header always, shown from the start
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

    if st.button("Save sale", type="primary"):
        if not final_brand or not final_category or not cleaned_price:
            st.error("Please complete all required fields.")
        else:
            if selected_brand == BRAND_ADD_NEW:
                upsert_brand_level(final_brand, brand_price_level)

            insert_sale(final_brand, final_category, cleaned_price, on_sale, brand_price_level)
            st.session_state["show_saved_dialog"] = True

    if st.session_state.get("show_saved_dialog"):
        sale_saved_dialog()
