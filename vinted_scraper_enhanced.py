"""
Enhanced Vinted Scraper - Category-Wide with Configuration Support
Version: 2.0
Features:
- Category-wide scraping (all brands)
- Configurable via scraper_config.py
- Enhanced anti-detection
- Comprehensive logging and statistics
"""
import time
from playwright.sync_api import sync_playwright
import json
from datetime import datetime
import random
import logging
import pandas as pd
import os
import sys

# Import configuration
try:
    from scraper_config import get_config
    config = get_config()
    combos = config['combos']
    DELAYS = config['delays']
    USER_AGENTS = config['user_agents']
    SCRAPING_HOURS = config['scraping_hours']
    REQUEST_SETTINGS = config['request_settings']
except ImportError:
    logger.error("[ERROR] scraper_config.py not found! Using default settings.")
    sys.exit(1)

# Logging setup with UTF-8 support for Windows
import sys
if sys.platform == 'win32':
    # Fix Windows console encoding issues
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
    sys.stderr.reconfigure(encoding='utf-8') if hasattr(sys.stderr, 'reconfigure') else None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Season keywords
season_keywords = {
    "summer": ["SS24", "SS25", "spring/summer", "verano", "primavera/verano", "summer"],
    "winter": ["FW24", "FW25", "fall/winter", "invierno", "otoo/invierno", "winter"]
}

def extract_season(title, description):
    """Extract season information from title and description."""
    text = (title + " " + description).lower()
    for season, kws in season_keywords.items():
        for kw in kws:
            if kw.lower() in text:
                return season, kw
    return None, None

def parse_vinted_timestamp(timestamp_value):
    """Parse Vinted timestamp (unix or ISO format)"""
    if not timestamp_value:
        return None
    
    try:
        if isinstance(timestamp_value, (int, float)):
            return datetime.fromtimestamp(timestamp_value)
        elif isinstance(timestamp_value, str):
            try:
                ts = float(timestamp_value)
                return datetime.fromtimestamp(ts)
            except ValueError:
                return datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
    except Exception as e:
        logger.warning(f"Could not parse timestamp '{timestamp_value}': {e}")
        return None

def build_api_url(combo, page=1):
    """Build API URL from combo configuration"""
    per_page = REQUEST_SETTINGS['per_page']
    
    params = {
        "page": page,
        "per_page": per_page,
        "search_text": "",
        "catalog_ids": ",".join(map(str, combo["catalog_ids"])),
        "order": combo.get("order", "newest_first"),
        "status_ids": "",
        "color_ids": "",
        "patterns_ids": "",
        "material_ids": ""
    }
    
    # Add brand_ids only if specified (for brand-specific combos)
    if "brand_ids" in combo:
        params["brand_ids"] = ",".join(map(str, combo["brand_ids"]))
    
    query = "&".join([f"{k}={v}" for k, v in params.items() if v])
    return f"https://www.vinted.es/api/v2/catalog/items?{query}"

def is_scraping_hours():
    """Check if current time is within configured scraping window"""
    if not SCRAPING_HOURS['enabled']:
        return True
    
    current_hour = datetime.now().hour
    start = SCRAPING_HOURS['start_hour']
    end = SCRAPING_HOURS['end_hour']
    
    if start <= current_hour <= end:
        return True
    
    logger.warning(f" Outside scraping window (current: {current_hour}:00, allowed: {start}:00-{end}:00)")
    return False

def random_delay(delay_range):
    """Generate random delay from configured range"""
    min_delay, max_delay = delay_range
    return random.uniform(min_delay, max_delay)

def scrape_vinted(headless=True):
    """
    Main scraping function with full configuration support
    """
    # Check scraping hours
    if not is_scraping_hours():
        logger.warning("Skipping scrape - outside configured hours")
        return
    
    data = []
    scrape_timestamp = datetime.now()
    
    # Randomly select user agent
    selected_ua = random.choice(USER_AGENTS)
    logger.info(f"[WEB] Using User-Agent: {selected_ua[:60]}...")
    logger.info(f"[CONFIG] Strategy: {len(combos)} combos configured")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=selected_ua,
            viewport={"width": 1280, "height": 720},
            bypass_csp=True,
            java_script_enabled=True,
            extra_http_headers={
                "Accept": "application/json",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                "Referer": "https://www.vinted.es/",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin"
            }
        )
        page = context.new_page()

        # Load homepage for cookies
        logger.info("[INIT] Loading homepage to capture cookies...")
        try:
            page.goto("https://www.vinted.es/", timeout=REQUEST_SETTINGS['timeout'])
            delay = random_delay(DELAYS['homepage_load'])
            time.sleep(delay)
            cookies = context.cookies()
            logger.info(f"[OK] Cookies captured: {len(cookies)}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to load homepage: {e}")
            browser.close()
            return

        # Process each combo
        for combo_idx, combo in enumerate(combos):
            logger.info(f"\n{'='*70}")
            logger.info(f"[{combo_idx+1}/{len(combos)}] SCRAPING COMBO")
            logger.info(f"{'='*70}")
            logger.info(f"[CATEGORIES] Category: {combo.get('category', 'N/A')}")
            logger.info(f"[AUDIENCE] Audience: {combo.get('audience', 'N/A')}")
            logger.info(f"[TOP 15 BRANDS]  Brand: {combo.get('brand', 'ALL BRANDS')}")
            logger.info(f"[TOTAL] Order: {combo.get('order', 'newest_first')}")
            logger.info(f"[PAGE] Max Pages: {combo.get('max_pages', 10)}")
            logger.info(f"{'='*70}")
            
            page_num = 1
            max_pages_limit = combo.get('max_pages', 10)
            combo_items = 0
            
            while page_num <= max_pages_limit:
                api_url = build_api_url(combo, page=page_num)
                items = []
                
                # Retry logic
                for attempt in range(REQUEST_SETTINGS['retries']):
                    try:
                        logger.info(f"[PAGE] Page {page_num}/{max_pages_limit} - Attempt {attempt+1}")
                        
                        response = page.evaluate(f"""
                            async () => {{
                                const resp = await fetch('{api_url}', {{
                                    method: 'GET',
                                    headers: {{ 
                                        'Accept': 'application/json',
                                        'X-Requested-With': 'XMLHttpRequest'
                                    }},
                                    credentials: 'include'
                                }});
                                return {{ 
                                    status: resp.status, 
                                    body: await resp.text(),
                                    headers: Object.fromEntries(resp.headers.entries())
                                }};
                            }}
                        """)
                        
                        if response['status'] != 200:
                            logger.error(f"[ERROR] HTTP {response['status']}: {response['body'][:200]}")
                            raise Exception(f"HTTP {response['status']}")

                        json_data = json.loads(response['body'])
                        items = json_data.get('items', [])
                        
                        logger.info(f"[OK] Page {page_num}: Found {len(items)} items")

                        if not items:
                            logger.info(f"[STOP] No items on page {page_num} - end of results")
                            break

                        # Process items
                        for item in items:
                            title = item.get('title', 'Unknown')
                            
                            # Extract brand (actual brand from API)
                            brand_raw = item.get('brand_title', 
                                               item.get('brand', {}).get('title', 'Unknown'))
                            
                            category_raw = combo.get('category', 'Unknown')
                            
                            # Extract size
                            size_raw = ''
                            if item.get('size_title'):
                                size_raw = item.get('size_title')
                            elif item.get('size') and isinstance(item.get('size'), dict):
                                size_raw = item.get('size', {}).get('title', '')
                            
                            condition_raw = item.get('status', '')
                            
                            # Parse price
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
                            
                            # Extract timestamp
                            published_at_raw = None
                            photo_data = item.get('photo', {})
                            if isinstance(photo_data, dict):
                                high_res = photo_data.get('high_resolution', {})
                                if isinstance(high_res, dict):
                                    published_at_raw = high_res.get('timestamp')
                            
                            if not published_at_raw:
                                published_at_raw = (
                                    item.get('created_at_ts') or
                                    item.get('created_at') or
                                    item.get('updated_at_ts')
                                )
                            
                            published_at = parse_vinted_timestamp(published_at_raw)
                            if published_at is None:
                                published_at = scrape_timestamp
                            
                            # Other fields
                            item_id = item.get('id', 'Unknown')
                            listing_url = item.get('url', f"https://www.vinted.es/items/{item_id}")
                            seller_id = str(item.get('user', {}).get('id', 'Unknown'))
                            audience = combo.get('audience', 'Unknown')
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
                                "published_at": published_at.isoformat(),
                                "listing_url": listing_url,
                                "seller_id": seller_id,
                                "visible": visible,
                                "season": season,
                                "season_keyword": season_keyword,
                                "scrape_timestamp": scrape_timestamp.isoformat()
                            }
                            data.append(item_data)
                            combo_items += 1

                        # Check pagination
                        pagination = json_data.get('pagination', {})
                        api_total_pages = pagination.get('total_pages', None)
                        total_entries = pagination.get('total_entries', None)
                        
                        if api_total_pages:
                            logger.info(f"[TOTAL] API: {total_entries:,} items, {api_total_pages} pages available")
                        
                        # Stop if no more pages
                        if not pagination.get('next_page') or len(items) < REQUEST_SETTINGS['per_page']:
                            logger.info(f" No more pages available")
                            break

                        page_num += 1
                        break  # Success, exit retry loop
                        
                    except Exception as e:
                        logger.error(f"[ERROR] Attempt {attempt+1} failed: {e}")
                        
                        if attempt < REQUEST_SETTINGS['retries'] - 1:
                            retry_delay = (DELAYS['retry_base'] ** attempt) + random_delay(DELAYS['retry_jitter'])
                            logger.info(f"[WAIT] Retrying in {retry_delay:.1f}s...")
                            time.sleep(retry_delay)
                        else:
                            logger.warning(f"[WARNING] All retries exhausted for page {page_num}")
                            break
                
                # Exit if no items were retrieved
                if not items:
                    break
                
                # Delay before next page
                if page_num <= max_pages_limit:
                    base_delay = random_delay(DELAYS['between_pages'])
                    page_factor = (page_num // 3) * 1.0  # Increase delay every 3 pages
                    jitter = random.uniform(-1, 2)
                    delay = max(DELAYS['min_delay'], base_delay + page_factor + jitter)
                    
                    logger.info(f"[WAIT] Waiting {delay:.1f}s before next page...")
                    time.sleep(delay)

            logger.info(f"[OK] Combo complete: {combo_items:,} items from {combo.get('category', 'combo')}")
            
            # Delay between combos
            if combo_idx < len(combos) - 1:
                inter_combo_delay = random_delay(DELAYS['between_categories'])
                logger.info(f"[PAUSE]  Waiting {inter_combo_delay:.1f}s before next combo...")
                time.sleep(inter_combo_delay)

        browser.close()

    # Save results
    if not data:
        logger.error("[ERROR] No data collected! Check logs for errors.")
        return

    save_results(data)

def save_results(data):
    """Save scraped data to CSV with comprehensive statistics"""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filename = f"vinted_scrape_{timestamp}.csv"

    # Ensure output directory
    output_dir = os.path.join(os.getcwd(), "data", "scrapes")
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    # Convert to DataFrame
    df = pd.DataFrame(data)

    # Remove duplicates
    original_count = len(df)
    df = df.drop_duplicates(subset=['item_id'], keep='first')
    removed_dupes = original_count - len(df)

    if removed_dupes > 0:
        logger.info(f"[CLEAN] Removed {removed_dupes} duplicate items")

    # Save to CSV
    df.to_csv(filepath, index=False, encoding='utf-8')
    
    # Print comprehensive statistics
    logger.info(f"\n{'='*70}")
    logger.info(f"[OK] SCRAPING COMPLETE")
    logger.info(f"{'='*70}")
    logger.info(f"[TOTAL] Total unique items: {len(df):,}")
    logger.info(f"[FILE] Saved to: {filepath}")
    
    # Category breakdown
    logger.info(f"\n[CATEGORIES] Items by Category:")
    for category in sorted(df['category_raw'].unique()):
        cat_count = len(df[df['category_raw'] == category])
        pct = (cat_count / len(df)) * 100
        logger.info(f"   {category:20s}: {cat_count:6,} ({pct:5.1f}%)")
    
    # Brand breakdown (top 15)
    logger.info(f"\n[TOP 15 BRANDS]  Top 15 Brands:")
    brand_counts = df['brand_raw'].value_counts().head(15)
    for brand, count in brand_counts.items():
        pct = (count / len(df)) * 100
        logger.info(f"   {brand:20s}: {count:6,} ({pct:5.1f}%)")
    
    # Audience breakdown
    logger.info(f"\n[AUDIENCE] Items by Audience:")
    for audience in sorted(df['audience'].unique()):
        aud_count = len(df[df['audience'] == audience])
        pct = (aud_count / len(df)) * 100
        logger.info(f"   {audience:20s}: {aud_count:6,} ({pct:5.1f}%)")
    
    # Date range
    df['published_at'] = pd.to_datetime(df['published_at'])
    logger.info(f"\n[DATE RANGE] Published Date Range:")
    logger.info(f"  Earliest: {df['published_at'].min().strftime('%Y-%m-%d %H:%M')}")
    logger.info(f"  Latest:   {df['published_at'].max().strftime('%Y-%m-%d %H:%M')}")
    logger.info(f"  Span:     {(df['published_at'].max() - df['published_at'].min()).days} days")
    logger.info(f"  Unique dates: {df['published_at'].dt.date.nunique()}")
    
    # Price statistics
    logger.info(f"\n[PRICES (EUR)] Price Statistics (EUR):")
    logger.info(f"  Min:     {df['price'].min():8.2f}")
    logger.info(f"  P25:     {df['price'].quantile(0.25):8.2f}")
    logger.info(f"  Median:  {df['price'].median():8.2f}")
    logger.info(f"  P75:     {df['price'].quantile(0.75):8.2f}")
    logger.info(f"  Max:     {df['price'].max():8.2f}")
    logger.info(f"  Mean:    {df['price'].mean():8.2f}")
    
    # Season breakdown (if available)
    if 'season' in df.columns and df['season'].notna().any():
        logger.info(f"\n[SEASONS]  Items by Season:")
        season_counts = df['season'].value_counts()
        for season, count in season_counts.items():
            pct = (count / len(df)) * 100
            logger.info(f"   {season:20s}: {count:6,} ({pct:5.1f}%)")
    
    logger.info(f"\n{'='*70}")
    logger.info(f"[OK] Ready for processing! Run: python process_data.py")
    logger.info(f"{'='*70}\n")

if __name__ == "__main__":
    logger.info(f"\n{'='*70}")
    logger.info(f"VINTED SCRAPER v2.0 - CATEGORY-WIDE MODE")
    logger.info(f"{'='*70}")
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        scrape_vinted(headless=True)
    except KeyboardInterrupt:
        logger.warning("\n[WARNING]  Scraping interrupted by user")
    except Exception as e:
        logger.error(f"\n[ERROR] Fatal error: {e}", exc_info=True)
    finally:
        logger.info(f"Ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")