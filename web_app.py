import streamlit as st
import sqlite3

# --- PAGE SETUP ---
st.set_page_config(
    page_title="BD PC Builder", 
    page_icon="🖥️", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- DATABASE CONNECTION ---
def get_db_connection():
    try:
        conn = sqlite3.connect('tech_data.db')
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        st.error(f"Database Error: {e}")
        return None

# --- BUILD LOGIC (Same as before) ---
def get_best_item(cursor, table, max_price, spec_constraint=None):
    query = f"SELECT * FROM {table} WHERE price <= ? AND price > 0"
    params = [max_price]
    if spec_constraint:
        query += " AND spec_tag LIKE ?"
        params.append(f"%{spec_constraint}%")
    query += " ORDER BY price DESC LIMIT 1"
    cursor.execute(query, params)
    return cursor.fetchone()

def get_cheapest_item(cursor, table):
    query = f"SELECT * FROM {table} WHERE price > 0 ORDER BY price ASC LIMIT 1"
    cursor.execute(query)
    return cursor.fetchone()

def generate_pc_build(budget):
    conn = get_db_connection()
    if not conn: return None, 0, 0
    
    cursor = conn.cursor()
    remaining = budget
    parts = {}
    
    # 1. CPU (30%)
    cpu = get_best_item(cursor, "processors", budget * 0.30) or get_cheapest_item(cursor, "processors")
    if cpu: remaining -= cpu['price']; parts['CPU'] = cpu
    
    # 2. Motherboard (20%)
    mobo = get_best_item(cursor, "motherboards", budget * 0.20) or get_cheapest_item(cursor, "motherboards")
    if mobo: remaining -= mobo['price']; parts['Motherboard'] = mobo
    
    # 3. RAM (10%)
    ram = get_best_item(cursor, "rams", budget * 0.10, "DDR4") or get_cheapest_item(cursor, "rams")
    if ram: remaining -= ram['price']; parts['RAM'] = ram
    
    # 4. Storage (10%)
    ssd = get_best_item(cursor, "ssds", budget * 0.10) or get_cheapest_item(cursor, "ssds")
    if ssd: remaining -= ssd['price']; parts['Storage'] = ssd

    # 5. PSU (10%)
    psu = get_best_item(cursor, "psus", budget * 0.10) or get_cheapest_item(cursor, "psus")
    if psu: remaining -= psu['price']; parts['Power Supply'] = psu
    
    # 6. Casing (Fixed ~3000)
    casing = get_best_item(cursor, "casings", 3000) or get_cheapest_item(cursor, "casings")
    if casing: remaining -= casing['price']; parts['Casing'] = casing

    # 7. GPU (Remaining Cash > 5k)
    if remaining > 5000:
        gpu = get_best_item(cursor, "gpus", remaining)
        if gpu: remaining -= gpu['price']; parts['Graphics Card'] = gpu
    
    conn.close()
    
    total_cost = sum(p['price'] for p in parts.values())
    return parts, total_cost, remaining

# --- THE APP UI ---
st.title("🖥️ BD PC Builder AI")
st.caption("Compare prices from Star Tech & Ryans instantly.")

# 1. CHECK URL FOR SHARED BUDGET
# st.query_params returns a dictionary-like object of the URL parameters
query_params = st.query_params
default_budget = 30000

if "budget" in query_params:
    try:
        # If someone sent a link like ?budget=50000, use that number
        default_budget = int(query_params["budget"])
        st.toast(f"Build loaded for {default_budget} BDT!", icon="✅")
    except:
        pass

# 2. INPUT SECTION
budget_input = st.number_input(
    "💰 What is your Budget (BDT)?", 
    min_value=15000, 
    max_value=500000, 
    step=1000, 
    value=default_budget
)

# 3. BUILD BUTTON
if st.button("🚀 Build PC", type="primary"):
    # Update URL so user can copy it immediately
    st.query_params["budget"] = budget_input
    
    parts, total_cost, saved = generate_pc_build(budget_input)
    
    if parts:
        st.divider()
        st.success(f"✅ Build Complete! Total: **{total_cost} BDT**")
        
        # --- SHARE SECTION (NEW) ---
        share_url = f"https://bd-pc-builder.streamlit.app/?budget={budget_input}"
        
        st.markdown("### 👇 Share this Build")
        
        # Create columns for side-by-side buttons
        share_col1, share_col2 = st.columns(2)
        
        with share_col1:
            # Facebook Share Link (Standard Blue)
            fb_link = f"https://www.facebook.com/sharer/sharer.php?u={share_url}"
            st.markdown(f'''
                <a href="{fb_link}" target="_blank">
                    <button style="
                        background-color: #1877F2; 
                        color: white; 
                        border: none; 
                        padding: 10px 20px; 
                        border-radius: 8px; 
                        font-weight: bold;
                        width: 100%;
                        cursor: pointer;">
                        📘 Share on Facebook
                    </button>
                </a>
            ''', unsafe_allow_html=True)

        with share_col2:
            # WhatsApp Share Link (Standard Green)
            wa_link = f"https://api.whatsapp.com/send?text=Check%20out%20this%20PC%20Build%20I%20created:%20{share_url}"
            st.markdown(f'''
                <a href="{wa_link}" target="_blank">
                    <button style="
                        background-color: #25D366; 
                        color: white; 
                        border: none; 
                        padding: 10px 20px; 
                        border-radius: 8px; 
                        font-weight: bold;
                        width: 100%;
                        cursor: pointer;">
                        💬 Share on WhatsApp
                    </button>
                </a>
            ''', unsafe_allow_html=True)
            
        st.caption(f"Or copy link: `{share_url}`")

        # --- PARTS LIST ---
        for part_type, item in parts.items():
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                # Left Column: Name & Type
                col1.markdown(f"**{part_type}**")
                col1.caption(item['name'])
                
                # Right Column: Price & Button
                col2.markdown(f"**{item['price']} ৳**")
                if item['url']:
                    affiliate_link = f"{item['url']}?ref=YOUR_ID"
                    col2.link_button("🛒 Buy", affiliate_link)
                
                st.divider()
                
        if saved > 0:
            st.warning(f"💵 Money Saved: {saved} BDT")
            
    else:
        st.error("Could not connect to database.")