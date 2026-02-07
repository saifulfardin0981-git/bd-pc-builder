import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import re

# --- CONFIGURATION ---
DATABASE_NAME = 'tech_data.db'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def clean_price(price_text):
    if not price_text or "stock" in price_text.lower(): return 0
    clean_text = price_text.replace('৳', '').replace(',', '').strip()
    if clean_text.isdigit(): return int(clean_text)
    match = re.search(r'\d+', clean_text)
    if match: return int(match.group())
    return 0

def get_specs_from_name(name, category):
    spec_tag = "General"
    name_upper = name.upper()
    
    if category == "RAM":
        if "DDR5" in name_upper: spec_tag = "DDR5"
        elif "DDR4" in name_upper: spec_tag = "DDR4"
        elif "DDR3" in name_upper: spec_tag = "DDR3"
    elif category == "SSD":
        if "NVME" in name_upper or "M.2" in name_upper: spec_tag = "NVMe"
        else: spec_tag = "SATA"
    elif category == "Motherboard":
         if "INTEL" in name_upper or "LGA" in name_upper: spec_tag = "Intel"
         elif "AMD" in name_upper or "AM4" in name_upper or "AM5" in name_upper: spec_tag = "AMD"
    elif category == "GPU":
        if "RTX" in name_upper or "GTX" in name_upper: spec_tag = "Nvidia"
        elif "RX" in name_upper or "RADEON" in name_upper: spec_tag = "AMD"

    return spec_tag

def setup_database():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    tables = ['processors', 'motherboards', 'rams', 'ssds', 'gpus', 'psus', 'casings']
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table}") 
        cursor.execute(f'''
            CREATE TABLE {table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, price INTEGER, spec_tag TEXT, url TEXT
            )
        ''')
    conn.commit()
    conn.close()

def scrape_category(base_url, category_name, table_name):
    print(f"--- Scraping {category_name} ---")
    
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    total_count = 0
    
    # --- NEW: LOOP THROUGH PAGES 1 TO 5 ---
    for page_num in range(1, 6): 
        # Construct URL with page number (e.g., ?page=2)
        target_url = f"{base_url}?page={page_num}"
        print(f"  > Visiting Page {page_num}...")
        
        try:
            response = requests.get(target_url, headers=HEADERS)
            soup = BeautifulSoup(response.text, 'html.parser')
            products = soup.find_all('div', class_='p-item')
            
            # STOP if no products found on this page
            if not products:
                print("    x No more products found. Stopping.")
                break
            
            count_on_page = 0
            for product in products:
                name_tag = product.find('h4', class_='p-item-name')
                price_div = product.find('div', class_='p-item-price')
                link_tag = product.find('a', href=True)
                
                if name_tag and price_div:
                    name = name_tag.text.strip()
                    
                    price_tag = price_div.find('span', class_='price-new')
                    if not price_tag:
                        price_tag = price_div.find('span')
                    
                    raw_price = price_tag.text.strip() if price_tag else "0"
                    price = clean_price(raw_price)
                    url = link_tag['href'] if link_tag else ""
                    
                    if price > 0:
                        spec_tag = get_specs_from_name(name, category_name)
                        cursor.execute(f'INSERT INTO {table_name} (name, price, spec_tag, url) VALUES (?, ?, ?, ?)', 
                                       (name, price, spec_tag, url))
                        count_on_page += 1
            
            total_count += count_on_page
            time.sleep(1) # Wait 1 sec between pages to be polite
            
        except Exception as e:
            print(f"❌ Error on Page {page_num}: {e}")

    conn.commit()
    conn.close()
    print(f"✅ Finished {category_name}. Total Saved: {total_count} items.\n")

if __name__ == "__main__":
    setup_database()
    target_urls = [
        ("https://www.startech.com.bd/component/processor", "CPU", "processors"),
        ("https://www.startech.com.bd/component/motherboard", "Motherboard", "motherboards"),
        ("https://www.startech.com.bd/component/ram", "RAM", "rams"),
        ("https://www.startech.com.bd/component/graphics-card", "GPU", "gpus"),
        ("https://www.startech.com.bd/ssd", "SSD", "ssds"),
        ("https://www.startech.com.bd/component/power-supply", "PSU", "psus"),
        ("https://www.startech.com.bd/component/casing", "Casing", "casings"),
    ]
    
    print("🚀 Starting Multi-Page Scrape (Max 5 pages per category)...")
    for url, cat, table in target_urls:
        scrape_category(url, cat, table)
        
    print("\n🎉 DATABASE UPDATED! You now have hundreds of products.")