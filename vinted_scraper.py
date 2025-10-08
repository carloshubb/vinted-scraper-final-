import time
from playwright.sync_api import sync_playwright
import json
import csv
from datetime import datetime
import re
import random
import logging
import pandas as pd
import os

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Combos with updated catalog_ids and brand_ids
combos = [
    {"brand": "Zara", "category": "Dresses", "audience": "Women", "catalog_ids": [10], "brand_ids": [12]},
    {"brand": "Mango", "category": "Dresses", "audience": "Women", "catalog_ids": [10], "brand_ids": [15]},
    {"brand": "Nike", "category": "Sneakers", "audience": "Men", "catalog_ids": [1242], "brand_ids": [53]},
    {"brand": "H&M", "category": "T-shirt", "audience": "Men", "catalog_ids": [77], "brand_ids": [7]},
    {"brand": "Levi's", "category": "Jeans", "audience": "Men", "catalog_ids": [257], "brand_ids": [10]}
]

# Season keywords - Fixed encoding
season_keywords = {
    "summer": ["SS24", "spring/summer", "verano", "primavera/verano", "summer"],
    "winter": ["FW24", "fall/winter", "invierno", "otoño/invierno", "winter"]
}

def extract_season(title, description):
    """Extract season information from title and description."""
    text = (title + " " + description).lower()
    for season, kws in season_keywords.items():
        for kw in kws:
            if kw.lower() in text:
                return season, kw
    return None, None

def build_api_url(combo, page=1, per_page=960):
    """Build API URL with configurable per_page parameter."""
    params = {
        "page": page,
        "per_page": per_page,
        "search_text": "",
        "catalog_ids": ",".join(map(str, combo["catalog_ids"])),
        "brand_ids": ",".join(map(str, combo["brand_ids"])),
        "order": "relevance",
        "status_ids": "",
        "color_ids": "",
        "patterns_ids": "",
        "material_ids": ""
    }
    query = "&".join([f"{k}={v}" for k, v in params.items() if v])
    return f"https://www.vinted.es/api/v2/catalog/items?{query}"

def scrape_vinted(headless=True, per_page=960):
    """Main scraping function."""
    data = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            bypass_csp=True,
            java_script_enabled=True,
            extra_http_headers={
                "Accept": "application/json",
                "Accept-Language": "es-ES,es;q=0.9",
                "Referer": "https://www.vinted.es/",
                "Accept-Encoding": "gzip, deflate, br"
            }
        )
        page = context.new_page()

        # Load homepage for cookies
        logger.info("Loading homepage to capture cookies")
        try:
            page.goto("https://www.vinted.es/", timeout=60000)
            time.sleep(5)
            cookies = context.cookies()
            logger.info(f"Cookies captured: {len(cookies)}")
        except Exception as e:
            logger.error(f"Failed to load homepage: {e}")

        for combo in combos:
            logger.info(f"Scraping combo: {combo['brand']} - {combo['category']} - {combo['audience']}")
            page_num = 1
            total_pages = 10
            
            while True:
                api_url = build_api_url(combo, page=page_num, per_page=per_page)
                retries = 3
                items = []
                
                for attempt in range(retries):
                    try:
                        logger.info(f"Page {page_num}, Attempt {attempt+1}: Fetching {api_url}")
                        response = page.evaluate(f"""
                            async () => {{
                                const resp = await fetch('{api_url}', {{
                                    method: 'GET',
                                    headers: {{ 'Accept': 'application/json' }},
                                    credentials: 'include'
                                }});
                                return {{ status: resp.status, body: await resp.text() }};
                            }}
                        """)
                        logger.info(f"API Response status: {response['status']}")

                        # Save response for debugging (first page only)
                        if page_num == 1:
                            debug_file = f"debug_response_{combo['brand']}_page{page_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                            with open(debug_file, 'w', encoding='utf-8') as f:
                                f.write(response['body'])
                            logger.info(f"Saved API response to {debug_file}")

                        if response['status'] != 200:
                            raise Exception(f"HTTP {response['status']}: {response['body'][:200]}")

                        json_data = json.loads(response['body'])
                        items = json_data.get('items', [])
                        logger.info(f"Page {page_num}: Found {len(items)} items")

                        if not items:
                            logger.info(f"No more items on page {page_num}, stopping")
                            break

                        for item in items:
                            title = item.get('title', 'Unknown')
                            brand_raw = item.get('brand_title', item.get('brand', {}).get('title', combo['brand']))
                            
                            # Log brand mismatches but include item
                            if combo['brand'].lower() not in brand_raw.lower():
                                logger.warning(f"Brand mismatch: {title} (brand: {brand_raw}, expected: {combo['brand']})")
                            
                            category_raw = combo['category']
                            
                            # Log category mismatches but include item
                            if combo['category'].lower() not in title.lower() and combo['category'].lower() not in category_raw.lower():
                                logger.warning(f"Category mismatch: {title} (category: {category_raw}, expected: {combo['category']})")
                            
                            # Extract size
                            size_raw = ''
                            if item.get('size_title'):
                                size_raw = item.get('size_title')
                            elif item.get('size') and isinstance(item.get('size'), dict):
                                size_raw = item.get('size', {}).get('title', '')
                            
                            condition_raw = item.get('status', '')
                            
                            # Parse price safely
                            price_dict = item.get('price', {})
                            try:
                                if isinstance(price_dict, dict) and price_dict.get('amount'):
                                    amount = str(price_dict.get('amount', '0')).replace(',', '.')
                                    price = float(amount)
                                else:
                                    price = 0.0
                            except (ValueError, AttributeError):
                                price = 0.0
                            
                            currency = price_dict.get('currency', 'EUR') if isinstance(price_dict, dict) else 'EUR'
                            published_at = item.get('created_at_ts', item.get('created_at', datetime.now().isoformat()))
                            
                            # Get item_id
                            item_id = item.get('id', 'Unknown')
                            listing_url = item.get('url', f"https://www.vinted.es/items/{item_id}")
                            seller_id = str(item.get('user', {}).get('id', 'Unknown'))
                            audience = combo['audience']
                            description = item.get('description', '')
                            season, season_keyword = extract_season(title, description)
                            visible = item.get('is_visible', True)

                            item_data = {
                                "item_id": item_id,
                                "brand_raw": brand_raw,
                                "category_raw": category_raw,
                                "title": title,
                                "size_raw": size_raw,
                                "condition_raw": condition_raw,
                                "audience": audience,
                                "price": price,
                                "currency": currency,
                                "published_at": published_at,
                                "listing_url": listing_url,
                                "seller_id": seller_id,
                                "visible": visible,
                                "season": season,
                                "season_keyword": season_keyword
                            }
                            data.append(item_data)
                            logger.info(f"Scraped: {title} ({price} {currency})")

                        # Update pagination
                        pagination = json_data.get('pagination', {})
                        logger.info(f"Pagination: {pagination}")
                        total_pages = pagination.get('total_pages', None)
                        total_entries = pagination.get('total_entries', None)
                        
                        if total_pages:
                            logger.info(f"Total pages: {total_pages}, Total items: {total_entries}")
                            if page_num >= total_pages:
                                logger.info(f"Reached total pages ({page_num}/{total_pages}), stopping")
                                break
                        elif not pagination.get('next_page') or len(items) < per_page:
                            logger.info(f"No next page or partial page ({len(items)} items), stopping")
                            break
                        
                        # Safety limit
                        if page_num >= 10:
                            logger.warning(f"Reached maximum page limit (10), stopping")
                            break

                        page_num += 1
                        break
                        
                    except Exception as e:
                        logger.error(f"Page {page_num}, Attempt {attempt+1} failed: {e}")
                        time.sleep(2 ** attempt + random.uniform(0, 1))
                        if attempt == retries - 1:
                            logger.warning(f"Failed for {combo['brand']} page {page_num}")
                            break
                
                if not items or (total_pages and page_num >= total_pages) or page_num >= 10:
                    break
                
                # Adaptive delay
                delay = min(5 + (page_num // 5), 10)
                logger.info(f"Waiting {delay}s before next page...")
                time.sleep(delay)

            time.sleep(5)

        browser.close()

    
# Save CSV
    if not data:
        logger.error("No data collected! Check debug_response_*.json files.")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filename = f"vinted_scrape_{timestamp}.csv"

    # Ensure folder exists: root/data/scrapes
    output_dir = os.path.join(os.getcwd(), "data", "scrapes")
    os.makedirs(output_dir, exist_ok=True)

    # Full file path
    filepath = os.path.join(output_dir, filename)

    df = pd.DataFrame(data)

    # Remove duplicates based on item_id
    original_count = len(df)
    df = df.drop_duplicates(subset=['item_id'], keep='first')
    removed_dupes = original_count - len(df)

    if removed_dupes > 0:
        logger.info(f"Removed {removed_dupes} duplicate items")

    df.to_csv(filepath, index=False, encoding='utf-8')
    logger.info(f"Saved {len(df)} items to {filepath}")

if __name__ == "__main__":
    scrape_vinted(headless=True, per_page=960)