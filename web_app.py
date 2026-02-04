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

# --- DATABASE LOGIC ---
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

# --- THE POPUP MENU (DIALOG) ---
@st.dialog("📤 Share Your Build")
def show_share_menu(link):
    st.write("Choose a platform to share your PC build:")
    
    # 1. Copy Link Section
    st.text_input("Copy Link manually:", value=link)
    
    # 2. Social Buttons Grid
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)
    
    # Define styles for buttons
    btn_style = """
        <style>
        .share-btn {
            display: inline-block;
            text-decoration: none;
            color: white !important;
            width: 100%;
            padding: 10px;
            text-align: center;
            border-radius: 8px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        </style>
    """
    st.markdown(btn_style, unsafe_allow_html=True)

    # Facebook (Blue)
    with col1:
        fb_url = f"https://www.facebook.com/sharer/sharer.php?u={link}"
        st.markdown(f'<a href="{fb_url}" target="_blank" class="share-btn" style="background-color: #1877F2;">📘 Facebook</a>', unsafe_allow_html=True)

    # WhatsApp (Green)
    with col2:
        wa_url = f"https://api.whatsapp.com/send?text=Check%20out%20this%20PC:%20{link}"
        st.markdown(f'<a href="{wa_url}" target="_blank" class="share-btn" style="background-color: #25D366;">💬 WhatsApp</a>', unsafe_allow_html=True)
    
    # Messenger (Blue-Purple)
    with col3:
        # Note: Messenger sharing often requires mobile app or FB ID, using generic FB share as fallback/redirect
        mess_url = f"fb-messenger://share/?link={link}"
        st.markdown(f'<a href="{mess_url}" target="_blank" class="share-btn" style="background-color: #0084FF;">⚡ Messenger</a>', unsafe_allow_html=True)

    # Email (Grey)
    with col4:
        email_url = f"mailto:?subject=My PC Build&body=Check out this build: {link}"
        st.markdown(f'<a href="{email_url}" class="share-btn" style="background-color: #555;">✉️ Email</a>', unsafe_allow_html=True)
        
    st.caption("Note: Messenger link works best on mobile.")

# --- MAIN APP LOGIC ---
def generate_pc_build(budget):
    conn = get_db_connection()
    if not conn: return None, 0, 0
    
    cursor = conn.cursor()
    remaining = budget
    parts = {}
    
    # LOGIC:
    cpu = get_best_item(cursor, "processors", budget * 0.30) or get_cheapest_item(cursor, "processors")
    if cpu: remaining -= cpu['price']; parts['CPU'] = cpu
    
    mobo = get_best_item(cursor, "motherboards", budget * 0.20) or get_cheapest_item(cursor, "motherboards")
    if mobo: remaining -= mobo['price']; parts['Motherboard'] = mobo
    
    ram = get_best_item(cursor, "rams", budget * 0.10, "DDR4") or get_cheapest_item(cursor, "rams")
    if ram: remaining -= ram['price']; parts['RAM'] = ram
    
    ssd = get_best_item(cursor, "ssds", budget * 0.10) or get_cheapest_item(cursor, "ssds")
    if ssd: remaining -= ssd['price']; parts['Storage'] = ssd

    psu = get_best_item(cursor, "psus", budget * 0.10) or get_cheapest_item(cursor, "psus")
    if psu: remaining -= psu['price']; parts['Power Supply'] = psu
    
    casing = get_best_item(cursor, "casings", 3000) or get_cheapest_item(cursor, "casings")
    if casing: remaining -= casing['price']; parts['Casing'] = casing

    if remaining > 5000:
        gpu = get_best_item(cursor, "gpus", remaining)
        if gpu: remaining -= gpu['price']; parts['Graphics Card'] = gpu
    
    conn.close()
    total_cost = sum(p['price'] for p in parts.values())
    return parts, total_cost, remaining

# --- UI START ---
st.title("🖥️ BD PC Builder AI")
st.caption("Compare prices from Star Tech & Ryans instantly.")

# Handle URL parameters
query_params = st.query_params
default_budget = 30000

if "budget" in query_params:
    try:
        default_budget = int(query_params["budget"])
        st.toast(f"Build loaded for {default_budget} BDT!", icon="✅")
    except:
        pass

# Input
budget_input = st.number_input("💰 What is your Budget (BDT)?", 15000, 500000, 1000, default_budget)

# Actions
if st.button("🚀 Build PC", type="primary"):
    st.query_params["budget"] = budget_input
    parts, total_cost, saved = generate_pc_build(budget_input)
    
    if parts:
        st.divider()
        st.success(f"✅ Build Complete! Total: **{total_cost} BDT**")
        
        # --- THE SINGLE SHARE BUTTON ---
        share_url = f"https://bd-pc-builder.streamlit.app/?budget={budget_input}"
        
        # This button triggers the popup
        if st.button("📤 Share this Build"):
            show_share_menu(share_url)

        # Parts List
        for part_type, item in parts.items():
            with st.container():
                col1, col2 = st.columns([3, 1])
                col1.markdown(f"**{part_type}**")
                col1.caption(item['name'])
                col2.markdown(f"**{item['price']} ৳**")
                if item['url']:
                    col2.link_button("🛒 Buy", f"{item['url']}?ref=YOUR_ID")
                st.divider()
                
        if saved > 0:
            st.warning(f"💵 Unused Budget: {saved} BDT")