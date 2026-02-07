import streamlit as st
import sqlite3

# --- PAGE CONFIG ---
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

# --- HELPERS ---
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

# --- SHARE POPUP ---
@st.dialog("📤 Share Your Build")
def show_share_menu(link):
    st.write("Choose a platform to share your PC build:")
    st.text_input("Copy Link manually:", value=link)
    
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)
    
    btn_style = """
        <style>
        .share-btn {
            display: inline-block; text-decoration: none; color: white !important;
            width: 100%; padding: 10px; text-align: center; border-radius: 8px;
            font-weight: bold; margin-bottom: 10px;
        }
        </style>
    """
    st.markdown(btn_style, unsafe_allow_html=True)

    with col1:
        st.markdown(f'<a href="https://www.facebook.com/sharer/sharer.php?u={link}" target="_blank" class="share-btn" style="background-color: #1877F2;">📘 Facebook</a>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<a href="https://api.whatsapp.com/send?text=Check%20out%20this%20PC:%20{link}" target="_blank" class="share-btn" style="background-color: #25D366;">💬 WhatsApp</a>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<a href="fb-messenger://share/?link={link}" target="_blank" class="share-btn" style="background-color: #0084FF;">⚡ Messenger</a>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<a href="mailto:?subject=My PC Build&body=Check out this build: {link}" class="share-btn" style="background-color: #555;">✉️ Email</a>', unsafe_allow_html=True)

# --- BUILD LOGIC ---
def generate_pc_build(budget):
    conn = get_db_connection()
    if not conn: return None, 0, 0
    cursor = conn.cursor()
    remaining = budget
    parts = {}
    
    # Priority List
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
    return parts, sum(p['price'] for p in parts.values()), remaining

# --- UI START ---
st.title("🖥️ BD PC Builder AI v2.1") # Verifying text
st.caption("Compare prices from Star Tech & Ryans instantly.")

# --- CRASH FIX LOGIC ---
query_params = st.query_params
raw_budget = 30000

if "budget" in query_params:
    try:
        raw_budget = int(query_params["budget"])
    except:
        pass

# Force the value to be safe
safe_budget = max(15000, min(500000, raw_budget))

# WE ADDED key="budget_v2" TO RESET THE WIDGET MEMORY
budget_input = st.number_input(
    "💰 What is your Budget (BDT)?", 
    min_value=15000, 
    max_value=500000, 
    step=1000, 
    value=safe_budget,
    key="budget_v2" 
)

if "budget" in query_params:
    try:
        raw_budget = int(query_params["budget"])
    except:
        pass

# Force the value to be safe
safe_budget = max(15000, min(500000, raw_budget))

budget_input = st.number_input("💰 What is your Budget (BDT)?", 15000, 500000, 1000, safe_budget)

# --- SESSION STATE MEMORY ---
if "build_results" not in st.session_state:
    st.session_state.build_results = None

if st.button("🚀 Build PC", type="primary"):
    st.query_params["budget"] = budget_input
    parts, total_cost, saved = generate_pc_build(budget_input)
    st.session_state.build_results = {"parts": parts, "total": total_cost, "saved": saved}

# Display Results from Memory
if st.session_state.build_results:
    data = st.session_state.build_results
    parts = data["parts"]
    
    if parts:
        st.divider()
        st.success(f"✅ Build Complete! Total: **{data['total']} BDT**")
        
        share_url = f"https://bd-pc-builder.streamlit.app/?budget={budget_input}"
        if st.button("📤 Share this Build"):
            show_share_menu(share_url)

        for part_type, item in parts.items():
            with st.container():
                col1, col2 = st.columns([3, 1])
                col1.markdown(f"**{part_type}**")
                col1.caption(item['name'])
                col2.markdown(f"**{item['price']} ৳**")
                if item['url']:
                    col2.link_button("🛒 Buy", f"{item['url']}?ref=YOUR_ID")
                st.divider()
                
        if data["saved"] > 0:
            st.warning(f"💵 Unused Budget: {data['saved']} BDT")