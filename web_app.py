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

# --- HELPER: WATTAGE PARSER (For PSU Capacity) ---
def get_wattage(name):
    """Extracts wattage number from PSU name (e.g., 'Corsair CV650' -> 650)"""
    match = re.search(r'(\d{3,4})\s*[Ww]', name) 
    if match:
        return int(match.group(1))
    return 0 

# --- HELPER: ESTIMATED CONSUMPTION CALCULATOR ---
def calculate_estimated_wattage(parts):
    """Calculates total estimated power draw of the system"""
    total_draw = 50 # Base system (Fans, RAM, SSD, Mobo)
    
    # 1. CPU Power Estimate (TDP + Turbo)
    if 'CPU' in parts:
        name = parts['CPU']['name'].upper()
        if "I9" in name or "RYZEN 9" in name: total_draw += 250
        elif "I7" in name or "RYZEN 7" in name: total_draw += 200
        elif "I5" in name or "RYZEN 5" in name: total_draw += 120
        else: total_draw += 80 # i3 or basic CPUs
        
    # 2. GPU Power Estimate (TGP)
    if 'Graphics Card' in parts:
        name = parts['Graphics Card']['name'].upper()
        if "4090" in name: total_draw += 450
        elif "4080" in name or "7900" in name: total_draw += 320
        elif "4070" in name or "6900" in name or "6800" in name: total_draw += 285
        elif "3080" in name: total_draw += 320
        elif "3070" in name or "6700" in name: total_draw += 220
        elif "4060" in name or "3060" in name or "7600" in name: total_draw += 170
        elif "6600" in name or "3050" in name: total_draw += 130
        else: total_draw += 100 # Low end GPU

    return total_draw

# --- HELPER: DATABASE FETCHERS ---
def get_best_item(cursor, table, max_price, spec_constraint=None, min_watts=0):
    query = f"SELECT * FROM {table} WHERE price <= ? AND price > 0"
    params = [max_price]
    
    if spec_constraint:
        query += " AND spec_tag LIKE ?"
        params.append(f"%{spec_constraint}%")
    
    query += " ORDER BY price DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
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
    with col1: st.markdown(f'<a href="https://www.facebook.com/sharer/sharer.php?u={link}" target="_blank" class="share-btn" style="background-color: #1877F2;">📘 Facebook</a>', unsafe_allow_html=True)
    with col2: st.markdown(f'<a href="https://api.whatsapp.com/send?text=Check%20out%20this%20PC:%20{link}" target="_blank" class="share-btn" style="background-color: #25D366;">💬 WhatsApp</a>', unsafe_allow_html=True)
    with col3: st.markdown(f'<a href="fb-messenger://share/?link={link}" target="_blank" class="share-btn" style="background-color: #0084FF;">⚡ Messenger</a>', unsafe_allow_html=True)
    with col4: st.markdown(f'<a href="mailto:?subject=My PC Build&body=Check out this build: {link}" class="share-btn" style="background-color: #555;">✉️ Email</a>', unsafe_allow_html=True)

# --- MASTER BUILD LOGIC ---
def generate_pc_build(budget):
    conn = get_db_connection()
    if not conn: return None, 0, 0, 0
    
    cursor = conn.cursor()
    remaining = budget
    parts = {}
    
    # --- PHASE 1: CORE COMPONENTS ---
    cpu = get_best_item(cursor, "processors", budget * 0.30) or get_cheapest_item(cursor, "processors")
    if cpu: 
        remaining -= cpu['price']
        parts['CPU'] = cpu
        cpu_name = cpu['name'].upper()
        if "INTEL" in cpu_name: cpu_type = "Intel"
        elif "AMD" in cpu_name or "RYZEN" in cpu_name: cpu_type = "AMD"
        else: cpu_type = None

        mobo_budget = budget * 0.20
        mobo = None
        if cpu_type: mobo = get_best_item(cursor, "motherboards", mobo_budget, cpu_type)
        if not mobo: mobo = get_best_item(cursor, "motherboards", mobo_budget) or get_cheapest_item(cursor, "motherboards")
            
        if mobo:
            remaining -= mobo['price']
            parts['Motherboard'] = mobo
            mobo_name = mobo['name'].upper()
            ram_type = "DDR4"
            if "DDR5" in mobo_name or " D5 " in mobo_name or any(x in mobo_name for x in ["X670", "B650", "AM5", "Z790", "A620"]):
                if "D4" not in mobo_name: ram_type = "DDR5"
            
            ram = get_best_item(cursor, "rams", budget * 0.10, ram_type) or get_best_item(cursor, "rams", budget * 0.10, "DDR4") or get_cheapest_item(cursor, "rams")
            if ram:
                remaining -= ram['price']
                parts['RAM'] = ram
    
    ssd = get_best_item(cursor, "ssds", budget * 0.10) or get_cheapest_item(cursor, "ssds")
    if ssd: remaining -= ssd['price']; parts['Storage'] = ssd
    
    casing = get_best_item(cursor, "casings", 5000) or get_cheapest_item(cursor, "casings")
    if casing: remaining -= casing['price']; parts['Casing'] = casing

    gpu = None
    if remaining > 10000:
        gpu = get_best_item(cursor, "gpus", remaining)
        if gpu: 
            remaining -= gpu['price']
            parts['Graphics Card'] = gpu

    # --- PHASE 2: SAFETY & PSU ---
    # We use the same Wattage Logic here for safety
    estimated_watts = calculate_estimated_wattage(parts)
    recommended_psu_watts = estimated_watts + 150 # Add 150W headroom for safety

    # --- SMART BUDGET CAP (The Fix) ---
    # Don't spend 10% blindly. Cap it for mid-range builds.
    if budget < 60000:
        psu_cap = 3500  # Enough for 450W decent PSU
    elif budget < 100000:
        psu_cap = 5000  # Enough for 550W/650W Bronze
    else:
        psu_cap = budget * 0.10 # Unlock premium budget for high-end builds
    
    # Try to find the BEST PSU that fits in our SMART CAP
    psu = get_best_item(cursor, "psus", psu_cap, min_watts=recommended_psu_watts)
    
    # Fallback 1: If Smart Cap was too tight, try the cheapest SAFE option (ignore cap)
    if not psu:
        psu = get_cheapest_item(cursor, "psus", min_watts=recommended_psu_watts)
        
    # Fallback 2: If still nothing (very rare), just get best available
    if not psu:
         psu = get_best_item(cursor, "psus", budget * 0.10) 

    if psu: 
        remaining -= psu['price']
        parts['Power Supply'] = psu

    # --- PHASE 3: BUDGET SWEEPER ---
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

    # Recalculate watts after upgrades
    final_watts = calculate_estimated_wattage(parts)
    
    conn.close()
    return parts, sum(p['price'] for p in parts.values()), remaining, final_watts

# --- UI START ---
st.title("🖥️ BD PC Builder AI v4.1")
st.caption("Auto-updates daily. Smart Compatibility. Wattage Safe.")

query_params = st.query_params
safe_budget = 40000
if "budget" in query_params:
    try:
        safe_budget = int(query_params["budget"])
    except:
        pass

budget_input = st.number_input(
    "💰 What is your Budget (BDT)?", 
    min_value=15000, max_value=500000, step=1000, value=safe_budget, key="budget_v41"
)

if "build_results" not in st.session_state:
    st.session_state.build_results = None

if st.button("🚀 Build PC", type="primary"):
    st.query_params["budget"] = budget_input
    parts, total_cost, saved, watts = generate_pc_build(budget_input)
    st.session_state.build_results = {"parts": parts, "total": total_cost, "saved": saved, "watts": watts}

if st.session_state.build_results:
    data = st.session_state.build_results
    parts = data["parts"]
    
    if parts:
        st.divider()
        st.success(f"✅ Build Complete! Total: **{data['total']} BDT**")
        
        # --- NEW: TOP BAR (Share + Power) ---
        col1, col2 = st.columns([1, 1])
        
        with col1:
             share_url = f"https://bd-pc-builder.streamlit.app/?budget={budget_input}"
             if st.button("📤 Share this Build", use_container_width=True):
                 show_share_menu(share_url)
                 
        with col2:
            # Show Estimated Power in a nice metric box
            st.metric(label="⚡ Estimated Power", value=f"{data['watts']}W")

        st.divider()

        # --- COMPONENT LIST ---
        for part_type, item in parts.items():
            with st.container():
                col_img, col_details, col_price = st.columns([1, 2, 1])
                
                with col_img:
                    if item['image_url']: st.image(item['image_url'], width=80)
                    else: st.write("📦")

                with col_details:
                    st.markdown(f"**{part_type}**")
                    st.caption(item['name'])
                    if part_type == "Power Supply":
                         watts = get_wattage(item['name'])
                         if watts > 0: st.caption(f"⚡ Capacity: {watts}W")

                with col_price:
                    st.markdown(f"**{item['price']} ৳**")
                    if item['url']: st.link_button("🛒 Buy", f"{item['url']}?ref=YOUR_ID")
                
                st.divider()
                
        if data["saved"] > 0:
            st.warning(f"💵 Unused Budget: {data['saved']} BDT")