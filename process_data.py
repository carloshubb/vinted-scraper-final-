import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import logging
from pathlib import Path

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create data directories
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
(DATA_DIR / "scrapes").mkdir(exist_ok=True)
(DATA_DIR / "processed").mkdir(exist_ok=True)


# ============================================================================
# NORMALIZATION FUNCTIONS
# ============================================================================

def normalize_brand(brand_raw):
    """Normalize brand names to standard format."""
    if pd.isna(brand_raw):
        return brand_raw
    
    brand_map = {
        'zara': 'Zara',
        'zara trafaluc': 'Zara',
        'zara basic': 'Zara',
        'zara trf': 'Zara',
        'h&m': 'H&M',
        'hm': 'H&M',
        'h & m': 'H&M',
        'h&m divided': 'H&M',
        'mango': 'Mango',
        'mango suit': 'Mango',
        'nike': 'Nike',
        'nike sportswear': 'Nike',
        "levi's": "Levi's",
        'levis': "Levi's",
        'levi strauss': "Levi's"
    }
    
    brand_lower = brand_raw.lower().strip()
    return brand_map.get(brand_lower, brand_raw.strip())


def normalize_category(category_raw, title):
    """Normalize categories to standard format."""
    text = (str(category_raw) + " " + str(title)).lower()
    
    # Category mapping with multiple keywords
    if any(word in text for word in ['vestido', 'dress', 'vestidos']):
        return 'Dress'
    elif any(word in text for word in ['zapatilla', 'sneaker', 'deportiva', 'trainer']):
        return 'Sneakers'
    elif any(word in text for word in ['camiseta', 't-shirt', 'tshirt', 'tee', 'top']):
        return 'T-shirt'
    elif any(word in text for word in ['vaquero', 'jean', 'denim', 'pantalón']):
        return 'Jeans'
    
    return category_raw


def normalize_condition(condition_raw):
    """Bucket conditions into 3 standard groups."""
    if pd.isna(condition_raw):
        return 'Unknown'
    
    condition_lower = str(condition_raw).lower()
    
    # New / Like new
    if any(word in condition_lower for word in [
        'nuevo', 'new', 'etiqueta', 'tag', 'sin estrenar',
        'nunca usado', 'never worn', 'con etiqueta'
    ]):
        return 'New/Like new'
    
    # Very good / Good
    elif any(word in condition_lower for word in [
        'muy bueno', 'very good', 'bueno', 'good',
        'excelente', 'excellent', 'perfecto', 'perfect'
    ]):
        return 'Very good/Good'
    
    # Average / Poor
    elif any(word in condition_lower for word in [
        'satisfactorio', 'satisfactory', 'aceptable', 'acceptable',
        'usado', 'used', 'worn', 'fair', 'average', 'poor'
    ]):
        return 'Average/Poor'
    
    return 'Average/Poor'


# ============================================================================
# DATA PROCESSING
# ============================================================================

def load_latest_scrape():
    """Load the most recent scrape file."""
    locations = [
        Path("data/scrapes"),
        Path("data"),
        Path("."),
        DATA_DIR.parent,
    ]
    
    scrape_files = []
    for location in locations:
        if location.exists():
            scrape_files.extend(location.glob("vinted_scrape_*.csv"))
    
    if not scrape_files:
        logger.error("No scrape files found!")
        return None
    
    # Sort by modification time (newest first)
    scrape_files = sorted(scrape_files, key=lambda x: x.stat().st_mtime, reverse=True)
    latest_file = scrape_files[0]
    logger.info(f"Loading latest scrape: {latest_file}")
    
    df = pd.read_csv(latest_file)
    logger.info(f"Loaded {len(df)} items from {latest_file.name}")
    
    return df, latest_file.name


def load_previous_listings():
    """Load previous listings database."""
    listings_file = DATA_DIR / "processed" / "listings.parquet"
    
    if not listings_file.exists():
        logger.info("No previous listings found. This is the first run.")
        return None
    
    df = pd.read_parquet(listings_file)
    logger.info(f"Loaded {len(df)} previous listings")
    return df


def process_new_scrape(current_df, scrape_filename):
    """Process new scrape data with normalization."""
    logger.info("Processing new scrape data...")
    
    # Add timestamp
    current_timestamp = datetime.now()
    current_df['scrape_timestamp'] = current_timestamp
    
    # Apply normalizations
    current_df['brand_norm'] = current_df['brand_raw'].apply(normalize_brand)
    current_df['category_norm'] = current_df.apply(
        lambda row: normalize_category(row['category_raw'], row['title']), 
        axis=1
    )
    current_df['condition_bucket'] = current_df['condition_raw'].apply(normalize_condition)
    
    # Add status field
    if 'status' not in current_df.columns:
        current_df['status'] = 'active'

    # Add first_seen_at and last_seen_at
    current_df['first_seen_at'] = current_timestamp
    current_df['last_seen_at'] = current_timestamp
    
    # Handle published_at with fractional seconds safely
    if 'published_at' in current_df.columns:
        current_df['published_at'] = pd.to_datetime(
            current_df['published_at'],
            format='ISO8601',
            errors='coerce'
        )
    
    logger.info(f"Processed {len(current_df)} items with normalizations")
    
    return current_df

def detect_price_changes(current_df, previous_df):
    """Detect price changes between scrapes."""
    if previous_df is None or len(previous_df) == 0:
        logger.info("No previous data for price change detection")
        return pd.DataFrame()
    
    logger.info("Detecting price changes...")
    
    # Merge on item_id
    merged = current_df.merge(
        previous_df[['item_id', 'price', 'last_seen_at']], 
        on='item_id', 
        suffixes=('_current', '_previous'),
        how='inner'
    )
    
    # Find items where price changed
    price_changed = merged[merged['price_current'] != merged['price_previous']].copy()
    
    if len(price_changed) == 0:
        logger.info("No price changes detected")
        return pd.DataFrame()
    
    # Create price events
    price_events = []
    for _, row in price_changed.iterrows():
        price_events.append({
            'event_id': f"PE_{row['item_id']}_{int(datetime.now().timestamp())}",
            'item_id': row['item_id'],
            'old_price': row['price_previous'],
            'new_price': row['price_current'],
            'changed_at': datetime.now(),
            'brand': row.get('brand_norm', 'Unknown'),
            'category': row.get('category_norm', 'Unknown')
        })
    
    events_df = pd.DataFrame(price_events)
    logger.info(f"Detected {len(events_df)} price changes")
    
    return events_df


def detect_sold_items(current_df, previous_df, hours_threshold=48, max_age_days=90):
    """
    FIXED SOLD DETECTION + DTS CALCULATION (Client's Logic)
    
    Items are considered SOLD if:
    1. Disappeared from current scrape
    2. Were visible in previous scrape
    3. Missing for ≥48 hours
    
    DTS CALCULATION (CLIENT'S CORRECT METHOD):
    - first_seen_at = first scrape where item appeared
    - last_seen_at = last scrape where item was visible
    - estimated_sold_at = last_seen_at + 24 hours (half scrape interval)
    - days_to_sell = (estimated_sold_at - first_seen_at) in days
    """
    if previous_df is None or len(previous_df) == 0:
        logger.info("No previous data for sold item detection")
        return pd.DataFrame()
    
    logger.info("Detecting sold items with CORRECTED DTS calculation...")
    
    current_ids = set(current_df['item_id'].unique())
    previous_ids = set(previous_df['item_id'].unique())
    
    missing_ids = previous_ids - current_ids
    
    if len(missing_ids) == 0:
        logger.info("No items disappeared since last scrape")
        return pd.DataFrame()
    
    sold_events = []
    current_time = datetime.now()
    
    for item_id in missing_ids:
        item = previous_df[previous_df['item_id'] == item_id].iloc[0]
        
        # Get timestamps
        last_seen = pd.to_datetime(item['last_seen_at'])
        first_seen = pd.to_datetime(item['first_seen_at'])
        
        # Calculate time since last seen
        time_diff = current_time - last_seen
        
        # Skip if not missing long enough
        if time_diff < timedelta(hours=hours_threshold):
            continue
        
        # CLIENT'S CORRECT LOGIC: Add 24h to last_seen (half the scrape interval)
        # Because we scrape every 48h, item likely sold midway between last scrape and now
        estimated_sold_at = last_seen + timedelta(hours=24)
        
        # DTS = time from first seen to estimated sale
        days_to_sell = (estimated_sold_at - first_seen).total_seconds() / (24 * 3600)
        
        # Calculate listing age (for filtering very old items)
        listing_age_days = (current_time - first_seen).days
        
        # Skip extremely old items (likely delisted, not sold)
        if listing_age_days > max_age_days:
            continue
        
        # Confidence based on how long item has been missing
        if time_diff >= timedelta(hours=96):  # 4 days
            confidence = 1.0
        elif time_diff >= timedelta(hours=hours_threshold):  # 2 days
            confidence = 0.5
        else:
            continue
        
        final_listed_price = item['price']
        
        sold_events.append({
            'event_id': f"SE_{item_id}_{int(current_time.timestamp())}",
            'item_id': item_id,
            'brand': item.get('brand_norm', item.get('brand_raw', 'Unknown')),
            'category': item.get('category_norm', item.get('category_raw', 'Unknown')),
            'condition': item.get('condition_bucket', item.get('condition_raw', 'Unknown')),
            'audience': item.get('audience', 'Unknown'),
            'final_listed_price': final_listed_price,
            'currency': item.get('currency', 'EUR'),
            'sold_at': estimated_sold_at,  # FIXED: Use estimated sale date
            'first_seen_at': first_seen,   # When we first saw it
            'last_seen_at': last_seen,     # Last time it was visible
            'days_to_sell': days_to_sell,  # FIXED: Correct calculation
            'listing_age_days': listing_age_days,
            'sold_confidence': confidence,
            'season': item.get('season', None)
        })
    
    events_df = pd.DataFrame(sold_events)
    
    if len(events_df) > 0:
        logger.info(f"Detected {len(events_df)} sold items")
        logger.info(f"  - Average DTS (CORRECTED): {events_df['days_to_sell'].mean():.1f} days")
        logger.info(f"  - Median DTS: {events_df['days_to_sell'].median():.1f} days")
        logger.info(f"  - High confidence (≥96h): {len(events_df[events_df['sold_confidence'] == 1.0])}")
    
    return events_df


def update_listings_database(current_df, previous_df):
    """
    FIXED: Update listings database to track unique items only
    """
    logger.info("Updating listings database...")
    
    if previous_df is None or len(previous_df) == 0:
        updated_df = current_df.copy()
        logger.info(f"First run: Added {len(updated_df)} new listings")
    else:
        current_ids = set(current_df['item_id'].unique())
        previous_ids = set(previous_df['item_id'].unique())
        
        # New items
        new_ids = current_ids - previous_ids
        new_items = current_df[current_df['item_id'].isin(new_ids)].copy()
        
        # Existing items (still active) - UPDATE THEM
        existing_ids = current_ids & previous_ids
        existing_current = current_df[current_df['item_id'].isin(existing_ids)].copy()
        existing_previous = previous_df[previous_df['item_id'].isin(existing_ids)].copy()
        
        # Keep first_seen_at from previous, update last_seen_at
        for col in ['first_seen_at']:
            if col in existing_previous.columns:
                existing_previous[col] = pd.to_datetime(existing_previous[col])
        
        existing_current = existing_current.merge(
            existing_previous[['item_id', 'first_seen_at']], 
            on='item_id', 
            suffixes=('', '_prev')
        )
        existing_current['first_seen_at'] = existing_current['first_seen_at_prev']
        existing_current = existing_current.drop(columns=[c for c in existing_current.columns if c.endswith('_prev')])
        
        # Sold items (disappeared) - mark as sold but keep in database
        sold_ids = previous_ids - current_ids
        sold_items = previous_df[previous_df['item_id'].isin(sold_ids)].copy()
        sold_items['status'] = 'sold'
        # Don't update last_seen_at - keep it as the last time we actually saw it
        
        # CRITICAL FIX: Combine WITHOUT duplicates
        updated_df = pd.concat([existing_current, new_items, sold_items], ignore_index=True)
        
        # Remove any duplicates (shouldn't happen, but safety check)
        original_count = len(updated_df)
        updated_df = updated_df.drop_duplicates(subset=['item_id'], keep='last')
        if original_count != len(updated_df):
            logger.warning(f"Removed {original_count - len(updated_df)} duplicate item_ids")
        
        logger.info(f"Database update:")
        logger.info(f"  - New items: {len(new_items)}")
        logger.info(f"  - Updated existing: {len(existing_current)}")
        logger.info(f"  - Marked as sold: {len(sold_items)}")
        logger.info(f"  - Total unique items: {len(updated_df)}")
    
    # Ensure datetime columns
    datetime_cols = ['first_seen_at', 'last_seen_at', 'published_at', 'scrape_timestamp']
    for col in datetime_cols:
        if col in updated_df.columns:
            updated_df[col] = pd.to_datetime(updated_df[col], errors='coerce')
    
    return updated_df


def save_processed_data(listings_df, price_events_df, sold_events_df):
    """Save all processed data to parquet files."""
    logger.info("Saving processed data...")
    
    # Clean datetime columns
    datetime_cols = ['first_seen_at', 'last_seen_at', 'published_at', 'scrape_timestamp']
    for col in datetime_cols:
        if col in listings_df.columns:
            listings_df[col] = pd.to_datetime(listings_df[col], errors='coerce')
    
    # Remove invalid rows
    before_count = len(listings_df)
    listings_df = listings_df.dropna(subset=['item_id', 'price'])
    after_count = len(listings_df)
    if before_count != after_count:
        logger.warning(f"Removed {before_count - after_count} rows with invalid data")
    
    # Save listings
    listings_file = DATA_DIR / "processed" / "listings.parquet"
    listings_df.to_parquet(listings_file, index=False)
    logger.info(f"Saved {len(listings_df)} listings to {listings_file}")
    
    # Save price events
    price_events_file = DATA_DIR / "processed" / "price_events.parquet"
    if not price_events_df.empty:
        if 'changed_at' in price_events_df.columns:
            price_events_df['changed_at'] = pd.to_datetime(price_events_df['changed_at'])
        
        if price_events_file.exists():
            existing_events = pd.read_parquet(price_events_file)
            price_events_df = pd.concat([existing_events, price_events_df], ignore_index=True)
            price_events_df = price_events_df.drop_duplicates(subset=['event_id'], keep='last')
        
        price_events_df.to_parquet(price_events_file, index=False)
        logger.info(f"Saved {len(price_events_df)} price events")
    
    # Save sold events
    sold_events_file = DATA_DIR / "processed" / "sold_events.parquet"
    if not sold_events_df.empty:
        for col in ['sold_at', 'first_seen_at', 'last_seen_at']:
            if col in sold_events_df.columns:
                sold_events_df[col] = pd.to_datetime(sold_events_df[col], errors='coerce')
        
        if sold_events_file.exists():
            existing_sold = pd.read_parquet(sold_events_file)
            sold_events_df = pd.concat([existing_sold, sold_events_df], ignore_index=True)
            sold_events_df = sold_events_df.drop_duplicates(subset=['event_id'], keep='last')
        
        sold_events_df.to_parquet(sold_events_file, index=False)
        logger.info(f"Saved {len(sold_events_df)} sold events")


def generate_summary_report(listings_df, price_events_df, sold_events_df):
    """Generate summary report."""
    logger.info("\n" + "="*60)
    logger.info("PROCESSING SUMMARY")
    logger.info("="*60)
    
    active_count = len(listings_df[listings_df['status'] == 'active'])
    sold_count = len(listings_df[listings_df['status'] == 'sold'])
    total_count = len(listings_df)
    
    logger.info(f"\nTotal Unique Items: {total_count}")
    logger.info(f"  - Active: {active_count}")
    logger.info(f"  - Sold: {sold_count}")
    logger.info(f"  - Verification: {active_count} + {sold_count} = {active_count + sold_count}")
    
    if active_count + sold_count != total_count:
        logger.warning(f"  ⚠ MISMATCH: Expected {total_count}, got {active_count + sold_count}")
    
    logger.info("\nListings by Brand:")
    # Fix: Remove NaN values before sorting
    brands = listings_df['brand_norm'].dropna().unique()
    for brand in sorted(brands):
        count = len(listings_df[listings_df['brand_norm'] == brand])
        active = len(listings_df[(listings_df['brand_norm'] == brand) & (listings_df['status'] == 'active')])
        logger.info(f"  {brand}: {count} total ({active} active)")
    
    logger.info(f"\nPrice Changes: {len(price_events_df)}")
    logger.info(f"Sold Events: {len(sold_events_df)}")
    
    if len(sold_events_df) > 0:
        logger.info(f"\nDTS Statistics (CORRECTED):")
        logger.info(f"  Mean: {sold_events_df['days_to_sell'].mean():.1f} days")
        logger.info(f"  Median: {sold_events_df['days_to_sell'].median():.1f} days")
        logger.info(f"  Min: {sold_events_df['days_to_sell'].min():.1f} days")
        logger.info(f"  Max: {sold_events_df['days_to_sell'].max():.1f} days")
    
    logger.info("="*60 + "\n")

def process_pipeline():
    """Main data processing pipeline."""
    logger.info("Starting data processing pipeline...")
    
    result = load_latest_scrape()
    if result is None:
        logger.error("No scrape data found. Run the scraper first!")
        return
    
    current_df, scrape_filename = result
    previous_df = load_previous_listings()
    current_df = process_new_scrape(current_df, scrape_filename)
    price_events_df = detect_price_changes(current_df, previous_df)
    sold_events_df = detect_sold_items(current_df, previous_df, hours_threshold=48)
    updated_listings_df = update_listings_database(current_df, previous_df)
    save_processed_data(updated_listings_df, price_events_df, sold_events_df)
    generate_summary_report(updated_listings_df, price_events_df, sold_events_df)
    
    logger.info("[OK] Data processing pipeline completed successfully!")
    
    return updated_listings_df, price_events_df, sold_events_df


if __name__ == "__main__":
    process_pipeline()