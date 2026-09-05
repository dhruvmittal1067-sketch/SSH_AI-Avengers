import os
import streamlit as st
import db 


st.set_page_config(page_title="TourConnect", page_icon="🗺️", layout="wide")

st.title("🗺️ TourConnect — Tourism & Local Discovery Platform")

# Initialize Session States
if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False

if "biz_user" not in st.session_state:
    st.session_state["biz_user"] = None

if "tourist_user" not in st.session_state:
    st.session_state["tourist_user"] = None

# Top Navigation
nav = st.sidebar.radio(
    "Navigation", 
    ["🌍 Tourist Portal", "🏢 Business Portal", "👨‍💼 Admin Panel"],
    key="main_navigation_radio"
)

# ---------------------------------------------------------
# MODULE 1: PUBLIC TOURIST DIRECTORY
# ---------------------------------------------------------
if nav == "🌍 Tourist Portal":
    
    # Top Bar: User Status & Auth
    auth_col1, auth_col2 = st.columns([3, 1])
    with auth_col1:
        if st.session_state["tourist_user"]:
            st.success(f"👋 Welcome back, **{st.session_state['tourist_user']['full_name']}**!")
        else:
            st.caption("💡 Sign in to save favorite places and view your search history.")

    with auth_col2:
        if st.session_state["tourist_user"]:
            if st.button("🚪 Logout Tourist", key="tourist_logout_btn"):
                st.session_state["tourist_user"] = None
                st.rerun()
        else:
            with st.popover("🔑 Tourist Login / Sign Up"):
                auth_tab1, auth_tab2 = st.tabs(["Login", "Sign Up"])
                
                with auth_tab1:
                    with st.form("tourist_login_form"):
                        t_email = st.text_input("Email")
                        t_pass = st.text_input("Password", type="password")
                        if st.form_submit_button("Log In"):
                            user = db.verify_user_login(t_email, t_pass)
                            if user:
                                st.session_state["tourist_user"] = user
                                st.success("Logged in!")
                                st.rerun()
                            else:
                                st.error("Invalid credentials.")
                                
                with auth_tab2:
                    with st.form("tourist_signup_form"):
                        reg_name = st.text_input("Full Name*")
                        reg_email = st.text_input("Email*")
                        reg_phone = st.text_input("Phone Number")
                        reg_pass = st.text_input("Password*", type="password")
                        if st.form_submit_button("Register"):
                            if reg_name and reg_email and reg_pass:
                                uid = db.register_user(reg_name, reg_email, reg_phone, reg_pass)
                                if uid:
                                    st.success("Account created! Please log in.")
                                else:
                                    st.error("Registration failed. Email might already be taken.")

    st.divider()

    # Main Directory Tabs
    if st.session_state["tourist_user"]:
        main_tab, fav_tab, history_tab = st.tabs(["🔍 Search Directory", "❤️ Saved Favorites", "📜 Search History"])
    else:
        main_tab = st.container()
        fav_tab, history_tab = None, None

    with main_tab:
        st.header("Find Local Services")
        col1, col2, col3, col4 = st.columns(4)

        countries = {c['name']: c['id'] for c in db.fetch_countries()}
        c_selected = col1.selectbox("Country", list(countries.keys()), key="tourist_country") if countries else None

        states = {s['name']: s['id'] for s in db.fetch_states(countries[c_selected])} if c_selected else {}
        s_selected = col2.selectbox("State", list(states.keys()), key="tourist_state") if states else None

        districts = {d['name']: d['id'] for d in db.fetch_districts(states[s_selected])} if s_selected else {}
        d_selected = col3.selectbox("District", list(districts.keys()), key="tourist_district") if states else None

        cities = {ct['name']: ct['id'] for ct in db.fetch_cities(districts[d_selected])} if d_selected else {}
        city_selected = col4.selectbox("City", list(cities.keys()), key="tourist_city") if d_selected else None

        categories = {cat['name']: cat['id'] for cat in db.fetch_categories()}
        cat_selected = st.selectbox("Category", list(categories.keys()), key="tourist_category") if categories else None

        if st.button("Search Businesses", key="tourist_search_btn") and city_selected and cat_selected:
            # Track Search History if Logged In
            if st.session_state["tourist_user"]:
                db.save_search_history(st.session_state["tourist_user"]["id"], city_selected, cat_selected)

            results = db.search_businesses(cities[city_selected], categories[cat_selected])
            st.subheader(f"Results for {cat_selected} in {city_selected}")

            if results:
                for b in results:
                    with st.expander(f"⭐ {b['rating']}/5 — {b['business_name']}"):
                        st.write(f"**Description:** {b['description']}")
                        st.write(f"**Owner:** {b['owner_name']}")
                        st.write(f"**Phone:** {b['contact_no']} | **Email:** {b['email']}")
                        st.write(f"**Website:** {b['website']}")

                        # Favorite Toggle for Logged In Users
                        if st.session_state["tourist_user"]:
                            if st.button(f"❤️ Save to Favorites", key=f"fav_btn_{b['id']}"):
                                db.add_favorite(st.session_state["tourist_user"]["id"], b['id'])
                                st.toast(f"Saved {b['business_name']} to your favorites!")

                        offers = db.fetch_business_offers(b['id'])
                        if offers:
                            st.markdown("---")
                            st.write("🔥 **Active Promotional Offers:**")
                            for o in offers:
                                st.write(f"• **{o['title']}** ({o['discount_percentage']}% OFF) — Valid till {o['valid_until']}")

                        catalog = db.fetch_business_catalog(b['id'])
                        if catalog:
                            st.markdown("---")
                            st.write("📋 **Services & Catalog:**")
                            for item in catalog:
                                st.write(f"• **{item['item_name']}** — ₹{item['price']} ({item['description']})")
            else:
                st.info("No approved businesses found for this location.")

    # Favorites Tab
    if fav_tab and st.session_state["tourist_user"]:
        with fav_tab:
            st.header("Your Saved Destinations & Businesses")
            favs = db.fetch_user_favorites(st.session_state["tourist_user"]["id"])
            if favs:
                for f in favs:
                    col_f1, col_f2 = st.columns([4, 1])
                    with col_f1:
                        st.write(f"### {f['business_name']} ({f['category_name']})")
                        st.write(f"**Rating:** ⭐ {f['rating']}/5 | **Phone:** {f['contact_no']}")
                        st.write(f"**Description:** {f['description']}")
                    with col_f2:
                        if st.button("❌ Remove", key=f"rem_fav_{f['id']}"):
                            db.remove_favorite(st.session_state["tourist_user"]["id"], f['id'])
                            st.rerun()
                    st.divider()
            else:
                st.info("You haven't saved any favorite spots yet!")

    # Search History Tab
    if history_tab and st.session_state["tourist_user"]:
        with history_tab:
            st.header("Recent Searches")
            history = db.fetch_user_search_history(st.session_state["tourist_user"]["id"])
            if history:
                for h in history:
                    st.write(f"🔍 **{h['category_name']}** in **{h['city_name']}** — *{h['searched_at']}*")
            else:
                st.info("No recent search history found.")
# ---------------------------------------------------------
# MODULE 2: BUSINESS PORTAL
# ---------------------------------------------------------
elif nav == "🏢 Business Portal":
    
    # 1. NOT LOGGED IN ACCESS
    if st.session_state["biz_user"] is None:
        auth_mode = st.radio("Business Access", ["Login to Portal", "New Business Application"], horizontal=True)

        if auth_mode == "Login to Portal":
            st.subheader("🔑 Business Owner Login")
            with st.form("biz_login_form"):
                b_email = st.text_input("Registered Email")
                b_pass = st.text_input("Password", type="password")
                
                if st.form_submit_button("Login"):
                    user = db.verify_business_login(b_email, b_pass)
                    if user:
                        st.session_state["biz_user"] = user
                        st.success(f"Welcome back, {user['business_name']}!")
                        st.rerun()
                    else:
                        st.error("Invalid Email or Password.")

        else:
            st.subheader("📋 Register New Business")
            st.info(
             "💡 **Can't find your State or City?** Select the nearest available location to complete your initial application. "
             "Once logged in, submit a request under **📍 Location Requests** in your Business Panel, and our team will add your exact area.")
            with st.form("new_reg_form"):
               
                
                b_name = st.text_input("Business Name*")
                owner_name = st.text_input("Owner Name*")
                
                countries = {c['name']: c['id'] for c in db.fetch_countries()}
                c_sel = st.selectbox("Country", list(countries.keys()), key="reg_c") if countries else None

                states = {s['name']: s['id'] for s in db.fetch_states(countries[c_sel])} if c_sel else {}
                s_sel = st.selectbox("State", list(states.keys()), key="reg_s") if c_sel else None

                districts = {d['name']: d['id'] for d in db.fetch_districts(states[s_sel])} if s_sel else {}
                d_sel = st.selectbox("District", list(districts.keys()), key="reg_d") if s_sel else None

                cities = {ct['name']: ct['id'] for ct in db.fetch_cities(districts[d_sel])} if d_sel else {}
                ct_sel = st.selectbox("City", list(cities.keys()), key="reg_ct") if d_sel else None

                categories = {cat['name']: cat['id'] for cat in db.fetch_categories()}
                cat_sel = st.selectbox("Category", list(categories.keys()), key="reg_cat") if categories else None

                phone = st.text_input("Contact Number")
                email = st.text_input("Account Email*")
                password = st.text_input("Set Password*", type="password")
                website = st.text_input("Website")
                desc = st.text_area("Description")

                if st.form_submit_button("Submit Registration"):
                    if not email or not password or not b_name or not ct_sel or not cat_sel:
                        st.warning("Please fill out all required fields marked with (*).")
                    else:
                        res = db.register_business_with_auth(
                            owner_name, b_name, categories[cat_sel],
                            countries[c_sel], states[s_sel], districts[d_sel], cities[ct_sel],
                            desc, phone, email, website, password
                        )
                        if res:
                            st.success("Registration submitted! You can log in once approved by Admin.")
                        else:
                            st.error("Registration failed. Make sure all dropdown selections are valid and email is unique.")

    # 2. LOGGED IN BUSINESS DASHBOARD
    else:
        biz = st.session_state["biz_user"]

        st.sidebar.markdown(f"**Logged in as:** {biz['business_name']}")
        if st.sidebar.button("🚪 Logout Business", key="logout_biz_btn"):
            st.session_state["biz_user"] = None
            st.rerun()

        # Business Panel Navigation Sub-Menu
        biz_nav = st.sidebar.radio(
            "Portal Navigation",
            [
                "📊 Dashboard",
                "👤 Business Profile",
                "🖼️ Media Management",
                "📍 Location Requests",
                "🏷️ Category Requests",
                "⚙️ Account Settings"
            ]
        )

        st.title(f"🏢 {biz['business_name']}")

        # SUB-SECTION 1: DASHBOARD
        if biz_nav == "📊 Dashboard":
            st.header("Business Dashboard Overview")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Account Status", biz['status'])
            c2.metric("Rating Badge", f"⭐ {biz['rating']}/5")
            c3.metric("Email", biz['email'])

            st.divider()
            b_tab1, b_tab2 = st.tabs(["📋 Catalog Services", "🔥 Active Deals & Offers"])

            with b_tab1:
                st.subheader("Add Catalog Items")
                with st.form("add_cat_item_form"):
                    item_name = st.text_input("Service / Product Name")
                    item_price = st.number_input("Price (INR)", min_value=0.0, step=50.0)
                    item_desc = st.text_area("Description")
                    if st.form_submit_button("Add Item"):
                        if item_name and item_price:
                            db.add_catalog_item(biz['id'], item_name, item_price, item_desc)
                            st.success("Item added to catalog!")
                            st.rerun()

                st.subheader("Current Catalog")
                catalog = db.fetch_business_catalog(biz['id'])
                if catalog:
                    for item in catalog:
                        st.write(f"• **{item['item_name']}** — ₹{item['price']} ({item['description']})")
                else:
                    st.caption("No catalog items published.")

            with b_tab2:
                st.subheader("Create Promotional Deals")
                with st.form("add_promo_form"):
                    offer_title = st.text_input("Offer Title")
                    discount = st.slider("Discount (%)", 1, 100, 10)
                    valid_till = st.date_input("Valid Until")
                    offer_desc = st.text_area("Offer Details")
                    if st.form_submit_button("Publish Offer"):
                        if offer_title:
                            db.add_business_offer(biz['id'], offer_title, offer_desc, discount, valid_till)
                            st.success("Offer published!")
                            st.rerun()

                st.subheader("Published Offers")
                offers = db.fetch_business_offers(biz['id'])
                if offers:
                    for o in offers:
                        st.write(f"🏷️ **{o['title']}** ({o['discount_percentage']}% OFF) — Valid till {o['valid_until']}")
                else:
                    st.caption("No active deals currently published.")

        # SUB-SECTION 2: BUSINESS PROFILE
        elif biz_nav == "👤 Business Profile":
            st.header("Business Profile Details")
            with st.form("edit_profile_form"):
                new_b_name = st.text_input("Business Name", value=biz['business_name'])
                new_owner = st.text_input("Owner Name", value=biz['owner_name'])
                new_phone = st.text_input("Contact Number", value=biz['contact_no'])
                new_web = st.text_input("Website", value=biz['website'])
                new_desc = st.text_area("Business Description", value=biz['description'])

                if st.form_submit_button("Update Profile"):
                    db.update_business_profile(biz['id'], new_b_name, new_owner, new_phone, new_web, new_desc)
                    st.session_state["biz_user"]["business_name"] = new_b_name
                    st.session_state["biz_user"]["owner_name"] = new_owner
                    st.session_state["biz_user"]["contact_no"] = new_phone
                    st.session_state["biz_user"]["website"] = new_web
                    st.session_state["biz_user"]["description"] = new_desc
                    st.success("Profile updated successfully!")
                    st.rerun()

        # SUB-SECTION 3: MEDIA MANAGEMENT
        elif biz_nav == "🖼️ Media Management":
            st.header("Media & Gallery Uploads")
            uploaded_file = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"], key="biz_media_uploader")
            if uploaded_file is not None:
                os.makedirs("uploads", exist_ok=True)
                file_path = os.path.join("uploads", f"biz_{biz['id']}_{uploaded_file.name}")
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.success("Image saved to gallery!")

        # SUB-SECTION 4: LOCATION REQUESTS
        elif biz_nav == "📍 Location Requests":
            st.header("Location Coverage Requests")
            st.caption("Submit a request if your target City or District is missing from dropdown options.")
            
            with st.form("loc_req_form"):
                req_type = st.selectbox("Type", ["City", "District", "State"])
                loc_name = st.text_input("Location Name")
                if st.form_submit_button("Send Request"):
                    if loc_name:
                        db.submit_location_request(biz['id'], req_type, loc_name)
                        st.success("Location request sent to admin!")
                    else:
                        st.warning("Please provide a location name.")

        # SUB-SECTION 5: CATEGORY REQUESTS
        elif biz_nav == "🏷️ Category Requests":
            st.header("Category Expansion Requests")
            st.caption("Request new business categories if your industry sector isn't listed.")
            
            with st.form("cat_req_form"):
                cat_name = st.text_input("Proposed Category Name")
                if st.form_submit_button("Send Category Request"):
                    if cat_name:
                        db.submit_category_request(biz['id'], cat_name)
                        st.success("Category request sent to admin!")
                    else:
                        st.warning("Please enter a category name.")

        # SUB-SECTION 6: ACCOUNT SETTINGS
        elif biz_nav == "⚙️ Account Settings":
            st.header("Account & Security Settings")
            with st.form("change_pass_form"):
                p1 = st.text_input("New Password", type="password")
                p2 = st.text_input("Confirm New Password", type="password")
                if st.form_submit_button("Change Password"):
                    if p1 and p1 == p2:
                        db.change_business_password(biz['id'], p1)
                        st.success("Password updated successfully!")
                    else:
                        st.error("Passwords do not match or field is empty.")

# ---------------------------------------------------------
# MODULE 3: ADMIN PANEL
# ---------------------------------------------------------
elif nav == "👨‍💼 Admin Panel":
    st.header("Admin Operations Panel")

    if not st.session_state["admin_logged_in"]:
        st.subheader("🔒 Admin Login")
        with st.form("admin_login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if db.verify_admin(username, password):
                    st.session_state["admin_logged_in"] = True
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password!")
    else:
        if st.sidebar.button("🚪 Logout Admin", key="logout_btn"):
            st.session_state["admin_logged_in"] = False
            st.rerun()

        # Expanded Admin Control Tabs
        admin_tab1, admin_tab2, admin_tab3, admin_tab4, admin_tab5 = st.tabs([
            "📋 Pending Registrations", 
            "📍 Location Requests", 
            "🏷️ Category Requests", 
            "🏢 Manage All Businesses", 
            "⚙️ Admin Settings"
        ])

        # Tab 1: Pending Approvals
        with admin_tab1:
            st.subheader("Pending Business Application Queue")
            pending = db.get_pending_businesses()
            if pending:
                for item in pending:
                    col_info, col_btn1, col_btn2 = st.columns([3, 1, 1])
                    col_info.write(f"**{item['business_name']}** ({item['category']}) — Owner: {item['owner_name']}")
                    
                    if col_btn1.button("Approve", key=f"app_{item['id']}"):
                        db.update_status(item['id'], 'Approved')
                        st.success(f"Approved {item['business_name']}")
                        st.rerun()

                    if col_btn2.button("Reject", key=f"rej_{item['id']}"):
                        db.update_status(item['id'], 'Rejected')
                        st.warning(f"Rejected {item['business_name']}")
                        st.rerun()
            else:
                st.info("No pending business approvals.")

        # Tab 2: Location Expansion Requests
        with admin_tab2:
            st.subheader("Pending Location Coverage Requests")
            loc_reqs = db.fetch_location_requests()
            if loc_reqs:
                for lr in loc_reqs:
                    st.write(f"**Request from:** {lr['business_name']} | **Type:** {lr['requested_type']} | **Name:** `{lr['location_name']}`")
                    
                    # Select Parent ID based on type
                    with st.form(f"approve_loc_form_{lr['id']}"):
                        if lr['requested_type'] == "City":
                            districts = {d['name']: d['id'] for d in db.fetch_districts(1)} # Default fetch or dynamic district picker
                            parent_id = st.number_input("Assign to District ID", min_value=1, step=1)
                        elif lr['requested_type'] == "District":
                            parent_id = st.number_input("Assign to State ID", min_value=1, step=1)
                        else:
                            parent_id = st.number_input("Assign to Country ID", min_value=1, step=1)
                            
                        if st.form_submit_button(f"Approve & Add {lr['requested_type']}"):
                            if db.approve_location_request(lr['id'], lr['requested_type'], lr['location_name'], parent_id):
                                st.success(f"Added {lr['location_name']} to database!")
                                st.rerun()
                            else:
                                st.error("Failed to approve request.")
                    st.divider()
            else:
                st.info("No location requests pending.")

        # Tab 3: Category Requests
        with admin_tab3:
            st.subheader("Pending Category Requests")
            cat_reqs = db.fetch_category_requests()
            if cat_reqs:
                for cr in cat_reqs:
                    col_c1, col_c2 = st.columns([3, 1])
                    col_c1.write(f"**Business:** {cr['business_name']} $\\rightarrow$ Proposed Category: **{cr['category_name']}**")
                    if col_c2.button("Approve Category", key=f"app_cat_{cr['id']}"):
                        if db.approve_category_request(cr['id'], cr['category_name']):
                            st.success(f"Added category '{cr['category_name']}'!")
                            st.rerun()
            else:
                st.info("No category requests pending.")

        # Tab 4: Manage All Businesses
        with admin_tab4:
            st.subheader("All Registered Businesses")
            all_biz = db.fetch_all_businesses()
            if all_biz:
                for b in all_biz:
                    with st.expander(f"[{b['status']}] {b['business_name']} — {b['category']} (Rating: ⭐ {b['rating']}/5)"):
                        st.write(f"**Owner:** {b['owner_name']} | **Contact:** {b['contact_no']}")
                        
                        col_s1, col_s2, col_s3 = st.columns(3)
                        new_status = col_s1.selectbox("Status", ["Approved", "Pending", "Rejected", "Suspended"], index=["Approved", "Pending", "Rejected", "Suspended"].index(b['status']), key=f"status_sel_{b['id']}")
                        if col_s1.button("Update Status", key=f"up_stat_{b['id']}"):
                            db.update_status(b['id'], new_status)
                            st.success("Status updated!")
                            st.rerun()
                            
                        new_rat = col_s2.slider("Badge Rating", 1, 5, b['rating'], key=f"rat_sl_{b['id']}")
                        if col_s2.button("Update Rating", key=f"up_rat_{b['id']}"):
                            db.update_rating(b['id'], new_rat)
                            st.success("Rating updated!")
                            st.rerun()
            else:
                st.info("No businesses found.")

        # Tab 5: Admin Settings
        with admin_tab5:
            st.subheader("Create New Admin Account")
            with st.form("add_admin_form"):
                new_user = st.text_input("New Admin Username")
                new_pass = st.text_input("New Admin Password", type="password")
                confirm_pass = st.text_input("Confirm Password", type="password")

                if st.form_submit_button("Create Admin"):
                    if not new_user or not new_pass:
                        st.warning("Please fill out all fields.")
                    elif new_pass != confirm_pass:
                        st.error("Passwords do not match!")
                    else:
                        if db.add_new_admin(new_user, new_pass):
                            st.success(f"Admin '{new_user}' created successfully!")
                        else:
                            st.error("Username already exists or database error occurred.")