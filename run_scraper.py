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


# Season keywords - Fixed encoding issue
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

def parse_price(price_dict):
    """Safely parse price with better error handling."""
    try:
        if not isinstance(price_dict, dict):
            return 0.0, 'EUR'
        
        amount = price_dict.get('amount', '0')
        currency = price_dict.get('currency', 'EUR')
        
        if not amount:
            return 0.0, currency
        
        # Handle both comma and dot as decimal separator
        amount_str = str(amount).replace(',', '.')
        price = float(amount_str)
        return price, currency
    except (ValueError, AttributeError, TypeError) as e:
        logger.warning(f"Price parsing error: {e}, defaulting to 0.0")
        return 0.0, 'EUR'

def build_api_url(combo, page=1, per_page=960):
    """Build API URL with configurable per_page parameter."""
    params = {
        "page": page,
        "per_page": per_page,  # Set to 960 to get all items in one page
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

def fetch_api_data(page, api_url, attempt, max_retries=3):
    """Fetch data from API with retry logic."""
    try:
        logger.info(f"Attempt {attempt+1}/{max_retries}: Fetching {api_url}")
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
        
        if response['status'] != 200:
            raise Exception(f"HTTP {response['status']}: {response['body'][:200]}")
        
        return json.loads(response['body'])
    except Exception as e:
        logger.error(f"Attempt {attempt+1} failed: {e}")
        if attempt < max_retries - 1:
            # Exponential backoff with jitter
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            logger.info(f"Waiting {wait_time:.2f}s before retry...")
            time.sleep(wait_time)
            return None
        else:
            logger.error(f"All {max_retries} attempts failed")
            return None

def save_debug_response(response_body, combo, page_num):
    """Save API response for debugging."""
    debug_file = f"debug_response_{combo['brand']}_page{page_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(response_body)
        logger.info(f"Saved debug response to {debug_file}")
    except Exception as e:
        logger.warning(f"Failed to save debug file: {e}")

def extract_item_data(item, combo, seen_item_ids):
    """Extract and validate item data."""
    item_id = item.get('id')
    
    # Deduplication check
    if item_id in seen_item_ids:
        logger.debug(f"Skipping duplicate item ID: {item_id}")
        return None
    
    title = item.get('title', 'Unknown')
    brand_raw = item.get('brand_title', item.get('brand', {}).get('title', combo['brand']))
    category_raw = combo['category']
    
    # Log mismatches but continue processing
    if combo['brand'].lower() not in brand_raw.lower():
        logger.warning(f"Brand mismatch: {title} (brand: {brand_raw}, expected: {combo['brand']})")
    
    if combo['category'].lower() not in title.lower() and combo['category'].lower() not in category_raw.lower():
        logger.warning(f"Category mismatch: {title} (category: {category_raw}, expected: {combo['category']})")
    
    # Extract size with better fallback logic
    size_raw = ''
    if item.get('size_title'):
        size_raw = item.get('size_title')
    elif item.get('size') and isinstance(item.get('size'), dict):
        size_raw = item.get('size', {}).get('title', '')
    
    condition_raw = item.get('status', '')
    price, currency = parse_price(item.get('price', {}))
    
    published_at = item.get('created_at_ts', item.get('created_at', datetime.now().isoformat()))
    listing_url = item.get('url', f"https://www.vinted.es/items/{item_id}")
    seller_id = str(item.get('user', {}).get('id', 'Unknown'))
    audience = combo['audience']
    description = item.get('description', '')
    season, season_keyword = extract_season(title, description)
    visible = item.get('is_visible', True)
    
    seen_item_ids.add(item_id)
    
    return {
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

def scrape_combo_pages(page, combo, per_page=960):
    """Scrape all pages for a given combo."""
    combo_data = []
    seen_item_ids = set()
    page_num = 1
    consecutive_empty_pages = 0
    max_empty_pages = 2  # Stop after 2 consecutive empty pages
    max_pages = 10  # Maximum pages to scrape per combo (960 items x 10 = 9600 max)
    
    logger.info(f"Starting scrape for: {combo['brand']} - {combo['category']} - {combo['audience']}")
    
    while True:
        api_url = build_api_url(combo, page=page_num, per_page=per_page)
        
        # Retry logic
        json_data = None
        for attempt in range(3):
            json_data = fetch_api_data(page, api_url, attempt)
            if json_data:
                break
        
        if not json_data:
            logger.warning(f"Failed to fetch page {page_num} for {combo['brand']}, moving to next combo")
            break
        
        # Save debug response (only first page and error pages)
        if page_num == 1:
            save_debug_response(json.dumps(json_data), combo, page_num)
        
        items = json_data.get('items', [])
        logger.info(f"Page {page_num}: Found {len(items)} items")
        
        # Check for empty pages
        if not items:
            consecutive_empty_pages += 1
            logger.info(f"Empty page {page_num} ({consecutive_empty_pages}/{max_empty_pages})")
            if consecutive_empty_pages >= max_empty_pages:
                logger.info(f"Stopping after {consecutive_empty_pages} consecutive empty pages")
                break
        else:
            consecutive_empty_pages = 0
        
        # Process items
        for item in items:
            item_data = extract_item_data(item, combo, seen_item_ids)
            if item_data:
                combo_data.append(item_data)
                logger.info(f"Scraped: {item_data['title']} ({item_data['price']} {item_data['currency']})")
        
        # Check pagination
        pagination = json_data.get('pagination', {})
        total_pages = pagination.get('total_pages')
        total_entries = pagination.get('total_entries')
        
        if total_pages:
            logger.info(f"Progress: Page {page_num}/{total_pages}, Total items available: {total_entries}")
            if page_num >= total_pages:
                logger.info(f"Reached final page ({page_num}/{total_pages})")
                break
        
        # Stop conditions
        if not pagination.get('next_page') or len(items) < per_page:
            logger.info(f"No next page or partial page ({len(items)}/{per_page} items)")
            break
        
        page_num += 1
        
        # Adaptive delay based on page number
        delay = min(3 + (page_num // 10), 8)  # Increases delay every 10 pages, max 8s
        logger.info(f"Waiting {delay}s before next page...")
        time.sleep(delay)
    
    logger.info(f"Completed {combo['brand']}: Collected {len(combo_data)} unique items")
    return combo_data

def scrape_vinted(headless=True, per_page=96):
    """Main scraping function with improved structure."""
    all_data = []
    
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
            browser.close()
            return
        
        # Scrape each combo
        for idx, combo in enumerate(combos, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing combo {idx}/{len(combos)}")
            logger.info(f"{'='*60}\n")
            
            combo_data = scrape_combo_pages(page, combo, per_page=per_page)
            all_data.extend(combo_data)
            
            # Delay between combos
            if idx < len(combos):
                logger.info(f"Waiting 5s before next combo...")
                time.sleep(5)
        
        browser.close()
    
    # Save results
def save_scrape_results(all_data, logger):
    if not all_data:
        logger.error("No data collected! Check debug_response_*.json files.")
        return

    # Timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    # Ensure output folder exists
    output_dir = os.path.join(os.getcwd(), "data", "scrapes")
    os.makedirs(output_dir, exist_ok=True)

    # File paths
    csv_filepath = os.path.join(output_dir, f"vinted_scrape_{timestamp}.csv")
    json_filepath = os.path.join(output_dir, f"vinted_scrape_{timestamp}.json")

    # Convert to DataFrame
    df = pd.DataFrame(all_data)

    # Remove duplicates
    original_count = len(df)
    df = df.drop_duplicates(subset=['item_id'], keep='first')
    removed_dupes = original_count - len(df)
    if removed_dupes > 0:
        logger.info(f"Removed {removed_dupes} duplicate items")

    # Save CSV
    df.to_csv(csv_filepath, index=False, encoding='utf-8')
    # Save JSON
    with open(json_filepath, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    logger.info(f"\n{'='*60}")
    logger.info(f"SUCCESS: Saved {len(df)} unique items")
    logger.info(f"CSV: {csv_filepath}")
    logger.info(f"JSON: {json_filepath}")
    logger.info(f"{'='*60}\n")

    # Brand summary
    logger.info("Summary by brand:")
    for brand in df['brand_raw'].unique():
        count = len(df[df['brand_raw'] == brand])
        logger.info(f"  {brand}: {count} items")

    
if __name__ == "__main__":
    scrape_vinted(headless=True, per_page=96)