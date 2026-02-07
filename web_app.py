import streamlit as st
import sqlite3
import re

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

# --- HELPER: WATTAGE PARSER ---
def get_wattage(name):
    """Extracts wattage number from PSU name (e.g., 'Corsair CV650' -> 650)"""
    match = re.search(r'(\d{3,4})\s*[Ww]', name) # Looks for 450W, 650w, 1000W
    if match:
        return int(match.group(1))
    return 0 # Could not read wattage

# --- HELPER: DATABASE FETCHERS ---
def get_best_item(cursor, table, max_price, spec_constraint=None, min_watts=0):
    query = f"SELECT * FROM {table} WHERE price <= ? AND price > 0"
    params = [max_price]
    
    if spec_constraint:
        query += " AND spec_tag LIKE ?"
        params.append(f"%{spec_constraint}%")
    
    query += " ORDER BY price DESC" # Prefer expensive/better items first
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    # Filter for Wattage (Only for PSUs)
    if min_watts > 0 and table == 'psus':
        valid_psus = [row for row in rows if get_wattage(row['name']) >= min_watts]
        return valid_psus[0] if valid_psus else None
        
    return rows[0] if rows else None

def get_cheapest_item(cursor, table, min_watts=0):
    cursor.execute(f"SELECT * FROM {table} WHERE price > 0 ORDER BY price ASC")
    rows = cursor.fetchall()
    
    if min_watts > 0 and table == 'psus':
        valid_psus = [row for row in rows if get_wattage(row['name']) >= min_watts]
        return valid_psus[0] if valid_psus else None
        
    return rows[0] if rows else None

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

# --- MASTER BUILD LOGIC ---
def generate_pc_build(budget):
    conn = get_db_connection()
    if not conn: return None, 0, 0
    
    cursor = conn.cursor()
    remaining = budget
    parts = {}
    
    # --- PHASE 1: CORE COMPONENTS ---
    
    # 1. CPU (The Brain)
    cpu = get_best_item(cursor, "processors", budget * 0.30) or get_cheapest_item(cursor, "processors")
    if cpu: 
        remaining -= cpu['price']
        parts['CPU'] = cpu
        
        # Smart Type Detection
        cpu_name = cpu['name'].upper()
        if "INTEL" in cpu_name: cpu_type = "Intel"
        elif "AMD" in cpu_name or "RYZEN" in cpu_name: cpu_type = "AMD"
        else: cpu_type = None

        # 2. Motherboard
        mobo_budget = budget * 0.20
        mobo = None
        if cpu_type: mobo = get_best_item(cursor, "motherboards", mobo_budget, cpu_type)
        if not mobo: mobo = get_best_item(cursor, "motherboards", mobo_budget) or get_cheapest_item(cursor, "motherboards")
            
        if mobo:
            remaining -= mobo['price']
            parts['Motherboard'] = mobo
            
            # 3. RAM (DDR5 Logic)
            mobo_name = mobo['name'].upper()
            ram_type = "DDR4"
            if "DDR5" in mobo_name or " D5 " in mobo_name or any(x in mobo_name for x in ["X670", "B650", "AM5", "Z790", "A620"]):
                if "D4" not in mobo_name: ram_type = "DDR5"
            
            ram = get_best_item(cursor, "rams", budget * 0.10, ram_type) or get_best_item(cursor, "rams", budget * 0.10, "DDR4") or get_cheapest_item(cursor, "rams")
            if ram:
                remaining -= ram['price']
                parts['RAM'] = ram
    
    # 4. Storage
    ssd = get_best_item(cursor, "ssds", budget * 0.10) or get_cheapest_item(cursor, "ssds")
    if ssd: remaining -= ssd['price']; parts['Storage'] = ssd
    
    # 5. Casing (Set aside fixed amount)
    casing = get_best_item(cursor, "casings", 5000) or get_cheapest_item(cursor, "casings")
    if casing: remaining -= casing['price']; parts['Casing'] = casing

    # 6. GPU (Graphics Card) - Takes bulk of remaining budget
    # We select GPU *before* PSU so we know how much power we need
    gpu = None
    if remaining > 10000:
        gpu = get_best_item(cursor, "gpus", remaining)
        if gpu: 
            remaining -= gpu['price']
            parts['Graphics Card'] = gpu

    # --- PHASE 2: WATTAGE SAFETY CHECK ⚡ ---
    required_watts = 450 # Base system requirement
    
    # Add GPU Power
    if gpu:
        gpu_name = gpu['name'].upper()
        if "4090" in gpu_name: required_watts = 850
        elif "4080" in gpu_name or "7900" in gpu_name: required_watts = 750
        elif "4070" in gpu_name or "3080" in gpu_name or "6800" in gpu_name: required_watts = 650
        elif "3070" in gpu_name or "4060" in gpu_name: required_watts = 550
    
    # Add CPU Power (Rough Estimate)
    if cpu:
        cpu_name = cpu['name'].upper()
        if "I9" in cpu_name or "RYZEN 9" in cpu_name: required_watts += 100 # Add extra headroom

    # 7. PSU (Power Supply) - Now with Wattage Filter
    psu_budget = max(budget * 0.10, 4000) # Ensure at least decent budget for PSU
    if remaining < 0: psu_budget = 3000 # Emergency fallback
    
    # Try to find a PSU that fits Budget AND Wattage
    psu = get_best_item(cursor, "psus", psu_budget, min_watts=required_watts)
    
    # If budget is too low for high wattage, prioritize wattage (Safety First!)
    if not psu:
        psu = get_cheapest_item(cursor, "psus", min_watts=required_watts)
        
    # If STILL no PSU (very rare), just get the best we can afford (Last Resort)
    if not psu:
         psu = get_best_item(cursor, "psus", psu_budget)

    if psu: 
        remaining -= psu['price']
        parts['Power Supply'] = psu

    # --- PHASE 3: THE "BUDGET SWEEPER" (Spend the Leftover Cash) ---
    # Re-invest unused money into better parts
    upgrade_order = [
        ('Graphics Card', 'gpus', None),
        ('CPU', 'processors', None),
        ('RAM', 'rams', ram_type),
        ('Storage', 'ssds', None),
        ('Motherboard', 'motherboards', cpu_type)
    ]

    for part_name, table, constraint in upgrade_order:
        if part_name in parts and remaining > 1000:
            current_item = parts[part_name]
            current_price = current_item['price']
            potential_budget = current_price + remaining
            
            better_item = get_best_item(cursor, table, potential_budget, constraint)
            
            if better_item and better_item['price'] > current_price:
                cost_diff = better_item['price'] - current_price
                parts[part_name] = better_item
                remaining -= cost_diff

    conn.close()
    return parts, sum(p['price'] for p in parts.values()), remaining

# --- UI START ---
st.title("🖥️ BD PC Builder AI v4.0")
st.caption("Auto-updates daily. Smart Compatibility. Wattage Safe.")

# --- SAFE URL HANDLING ---
query_params = st.query_params
raw_budget = 40000

if "budget" in query_params:
    try:
        raw_budget = int(query_params["budget"])
    except:
        pass

safe_budget = max(15000, min(500000, raw_budget))

budget_input = st.number_input(
    "💰 What is your Budget (BDT)?", 
    min_value=15000, 
    max_value=500000, 
    step=1000, 
    value=safe_budget,
    key="budget_v4"
)

# --- SESSION STATE MEMORY ---
if "build_results" not in st.session_state:
    st.session_state.build_results = None

if st.button("🚀 Build PC", type="primary"):
    st.query_params["budget"] = budget_input
    parts, total_cost, saved = generate_pc_build(budget_input)
    st.session_state.build_results = {"parts": parts, "total": total_cost, "saved": saved}

# Display Results
if st.session_state.build_results:
    data = st.session_state.build_results
    parts = data["parts"]
    
    if parts:
        st.divider()
        st.success(f"✅ Build Complete! Total: **{data['total']} BDT**")
        
        share_url = f"https://bd-pc-builder.streamlit.app/?budget={budget_input}"
        if st.button("📤 Share this Build"):
            show_share_menu(share_url)

        # --- IMAGE LAYOUT ---
        for part_type, item in parts.items():
            with st.container():
                col_img, col_details, col_price = st.columns([1, 2, 1])
                
                with col_img:
                    if item['image_url']:
                        st.image(item['image_url'], width=80)
                    else:
                        st.write("📦")

                with col_details:
                    st.markdown(f"**{part_type}**")
                    st.caption(item['name'])
                    # Show Wattage info for PSU
                    if part_type == "Power Supply":
                         watts = get_wattage(item['name'])
                         if watts > 0: st.caption(f"⚡ Capacity: {watts}W")

                with col_price:
                    st.markdown(f"**{item['price']} ৳**")
                    if item['url']:
                        st.link_button("🛒 Buy", f"{item['url']}?ref=YOUR_ID")
                
                st.divider()
                
        if data["saved"] > 0:
            st.warning(f"💵 Unused Budget: {data['saved']} BDT")