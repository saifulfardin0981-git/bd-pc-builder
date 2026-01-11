import streamlit as st
import sqlite3

# --- SETUP PAGE CONFIG ---
st.set_page_config(page_title="BD PC Builder", page_icon="🖥️", layout="centered")

# --- DATABASE CONNECTION ---
def get_db_connection():
    conn = sqlite3.connect('tech_data.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- LOGIC (Same as your API) ---
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

# --- THE UI CODE ---
st.title("🖥️ BD PC Builder AI")
st.write("Enter your budget, and we will build the best PC for you using live market prices from Bangladesh.")

# 1. Input Section
budget = st.number_input("💰 What is your Budget (BDT)?", min_value=15000, max_value=500000, step=1000, value=30000)

if st.button("🚀 Build My PC"):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    st.divider()
    
    # --- LOGIC COPY ---
    remaining = budget
    parts = {}
    
    # Allocation Strategy
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

    # GPU gets the rest
    if remaining > 5000:
        gpu = get_best_item(cursor, "gpus", remaining)
        if gpu: remaining -= gpu['price']; parts['Graphics Card'] = gpu
    
    conn.close()

    # --- DISPLAY RESULTS ---
    total_cost = sum(p['price'] for p in parts.values())
    
    st.success(f"✅ Build Complete! Total Cost: **{total_cost} BDT**")
    
    # Show parts in a nice list
    for part_type, item in parts.items():
        with st.container():
            col1, col2 = st.columns([3, 1])
            col1.markdown(f"**{part_type}**")
            col1.text(item['name'])
            col2.markdown(f"**{item['price']} ৳**")
            
            # --- AFFILIATE LINK LOGIC ---
            if item['url']:
                # 1. Take the original link
                # 2. Add your ID to the end (e.g. ?ref=samiul)
                # CHANGE 'YOUR_ID' to your real Star Tech username later!
                affiliate_link = f"{item['url']}?ref=YOUR_ID"
                
                # 3. Show a nice button
                col2.link_button("🛒 Buy Now", affiliate_link)
            
            st.divider()
            
    if remaining > 0:
        st.info(f"💵 Money Saved: {remaining} BDT")