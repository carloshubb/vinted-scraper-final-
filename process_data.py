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
    
    return 'Average/Poor'  # Default to lower tier


# ============================================================================
# DATA PROCESSING
# ============================================================================

def load_latest_scrape():
    """Load the most recent scrape file."""
    from pathlib import Path
    
    # Check multiple locations
    locations = [
        Path("data/scrapes"),   # data/scrapes folder (where scraper saves)
        Path("data"),           # data folder
        Path("."),              # current directory
        DATA_DIR.parent,        # parent of processed folder
    ]
    
    scrape_files = []
    for location in locations:
        if location.exists():
            scrape_files.extend(location.glob("vinted_scrape_*.csv"))
    
    if not scrape_files:
        logger.error("No scrape files found!")
        logger.error("Checked locations:")
        for loc in locations:
            logger.error(f"  - {loc.absolute()}")
        logger.error("\nPlease ensure CSV file is in one of these locations:")
        logger.error("  - data/scrapes/vinted_scrape_*.csv")
        logger.error("  - data/vinted_scrape_*.csv")
        logger.error("  - vinted_scrape_*.csv (current directory)")
        return None
    
    # Sort by modification time (newest first)
    scrape_files = sorted(scrape_files, key=lambda x: x.stat().st_mtime, reverse=True)
    
    latest_file = scrape_files[0]  # FIXED: was [-1], should be [0] for newest
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
    current_df['scrape_filename'] = scrape_filename
    
    # Apply normalizations
    current_df['brand_norm'] = current_df['brand_raw'].apply(normalize_brand)
    current_df['category_norm'] = current_df.apply(
        lambda row: normalize_category(row['category_raw'], row['title']), 
        axis=1
    )
    current_df['condition_bucket'] = current_df['condition_raw'].apply(normalize_condition)
    
    # Add status field (default to 'active' for new items)
    if 'status' not in current_df.columns:
        current_df['status'] = 'active'
    
    # Add first_seen_at and last_seen_at
    current_df['first_seen_at'] = current_timestamp
    current_df['last_seen_at'] = current_timestamp
    
    # FIXED: Preserve published_at from scraper (don't overwrite)
    if 'published_at' in current_df.columns:
        current_df['published_at'] = pd.to_datetime(current_df['published_at'])
    
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


def detect_sold_items(current_df, previous_df, hours_threshold=48):  # FIXED: 48 hours per spec
    """Detect items that disappeared (likely sold)."""
    if previous_df is None or len(previous_df) == 0:
        logger.info("No previous data for sold item detection")
        return pd.DataFrame()
    
    logger.info("Detecting sold items...")
    
    current_ids = set(current_df['item_id'].unique())
    previous_ids = set(previous_df['item_id'].unique())
    
    # Items that were in previous but not in current
    missing_ids = previous_ids - current_ids
    
    if len(missing_ids) == 0:
        logger.info("No items disappeared since last scrape")
        return pd.DataFrame()
    
    sold_events = []
    current_time = datetime.now()
    
    for item_id in missing_ids:
        item = previous_df[previous_df['item_id'] == item_id].iloc[0]
        
        # Calculate time since last seen
        last_seen = pd.to_datetime(item['last_seen_at'])
        time_diff = current_time - last_seen
        
        # FIXED: Use published_at if available, otherwise first_seen_at
        if 'published_at' in item and pd.notna(item['published_at']):
            listing_date = pd.to_datetime(item['published_at'])
        else:
            listing_date = pd.to_datetime(item['first_seen_at'])
        
        # Calculate days to sell (as float for precision)
        days_to_sell = (current_time - listing_date).total_seconds() / (24 * 3600)
        
        # FIXED: Sold confidence per spec (≥48h = 1.0, 24-48h = 0.5, <24h = 0.0)
        if time_diff >= timedelta(hours=48):
            confidence = 1.0  # High confidence - missing for 48+ hours
        elif time_diff >= timedelta(hours=24):
            confidence = 0.5  # Medium confidence - missing for 24-48 hours
        else:
            confidence = 0.0  # Low confidence - just disappeared
        
        sold_events.append({
            'event_id': f"SE_{item_id}_{int(current_time.timestamp())}",
            'item_id': item_id,
            'brand': item.get('brand_norm', item.get('brand_raw', 'Unknown')),
            'category': item.get('category_norm', item.get('category_raw', 'Unknown')),
            'condition': item.get('condition_bucket', item.get('condition_raw', 'Unknown')),
            'audience': item.get('audience', 'Unknown'),
            'last_price': item['price'],
            'currency': item.get('currency', 'EUR'),
            'sold_at': current_time,
            'published_at': listing_date,  # FIXED: Use actual published_at
            'first_seen_at': pd.to_datetime(item['first_seen_at']),
            'days_to_sell': days_to_sell,
            'sold_confidence': confidence,
            'season': item.get('season', None)
        })
    
    events_df = pd.DataFrame(sold_events)
    logger.info(f"Detected {len(events_df)} potentially sold items")
    logger.info(f"  - High confidence (≥48h): {len(events_df[events_df['sold_confidence'] == 1.0])}")
    logger.info(f"  - Medium confidence (24-48h): {len(events_df[events_df['sold_confidence'] == 0.5])}")
    logger.info(f"  - Low confidence (<24h): {len(events_df[events_df['sold_confidence'] == 0.0])}")
    
    return events_df


def update_listings_database(current_df, previous_df):
    """Update the main listings database."""
    logger.info("Updating listings database...")
    
    if previous_df is None or len(previous_df) == 0:
        # First run - all items are new
        updated_df = current_df.copy()
        logger.info(f"First run: Added {len(updated_df)} new listings")
    else:
        # Update existing items and add new ones
        current_ids = set(current_df['item_id'].unique())
        previous_ids = set(previous_df['item_id'].unique())
        
        # New items
        new_ids = current_ids - previous_ids
        new_items = current_df[current_df['item_id'].isin(new_ids)].copy()
        
        # Existing items (update last_seen_at and price)
        existing_ids = current_ids & previous_ids
        existing_current = current_df[current_df['item_id'].isin(existing_ids)].copy()
        existing_previous = previous_df[previous_df['item_id'].isin(existing_ids)].copy()
        
        # FIXED: Ensure datetime columns are datetime before merge
        for col in ['first_seen_at', 'published_at']:
            if col in existing_previous.columns:
                existing_previous[col] = pd.to_datetime(existing_previous[col])
        
        # FIXED: Keep both first_seen_at AND published_at from previous data
        existing_current = existing_current.merge(
            existing_previous[['item_id', 'first_seen_at', 'published_at']], 
            on='item_id', 
            suffixes=('', '_prev')
        )
        # Use previous values for first_seen_at and published_at
        existing_current['first_seen_at'] = existing_current['first_seen_at_prev']
        if 'published_at_prev' in existing_current.columns:
            existing_current['published_at'] = existing_current['published_at_prev']
        existing_current = existing_current.drop(columns=[c for c in existing_current.columns if c.endswith('_prev')])
        
        # Mark sold items in previous data
        sold_ids = previous_ids - current_ids
        sold_items = previous_df[previous_df['item_id'].isin(sold_ids)].copy()
        sold_items['status'] = 'sold'
        sold_items['last_seen_at'] = datetime.now()
        
        # Combine all items
        updated_df = pd.concat([existing_current, new_items, sold_items], ignore_index=True)
        
        logger.info(f"Database update:")
        logger.info(f"  - New items: {len(new_items)}")
        logger.info(f"  - Updated items: {len(existing_current)}")
        logger.info(f"  - Sold items: {len(sold_items)}")
    
    # CRITICAL FIX: Ensure all datetime columns are properly typed before saving
    datetime_cols = ['first_seen_at', 'last_seen_at', 'published_at', 'scrape_timestamp']
    for col in datetime_cols:
        if col in updated_df.columns:
            updated_df[col] = pd.to_datetime(updated_df[col], errors='coerce')
    
    return updated_df


def save_processed_data(listings_df, price_events_df, sold_events_df):
    """Save all processed data to parquet files."""
    logger.info("Saving processed data...")
    
    # CRITICAL FIX: Clean and validate data before saving
    # Ensure all datetime columns are properly typed
    datetime_cols = ['first_seen_at', 'last_seen_at', 'published_at', 'scrape_timestamp']
    for col in datetime_cols:
        if col in listings_df.columns:
            listings_df[col] = pd.to_datetime(listings_df[col], errors='coerce')
    
    # Remove any rows with invalid critical data
    before_count = len(listings_df)
    listings_df = listings_df.dropna(subset=['item_id', 'price'])
    after_count = len(listings_df)
    if before_count != after_count:
        logger.warning(f"Removed {before_count - after_count} rows with invalid data")
    
    # Save main listings database
    listings_file = DATA_DIR / "processed" / "listings.parquet"
    try:
        listings_df.to_parquet(listings_file, index=False)
        logger.info(f"Saved {len(listings_df)} listings to {listings_file}")
    except Exception as e:
        logger.error(f"Error saving listings: {e}")
        # Try CSV fallback
        csv_file = DATA_DIR / "processed" / "listings.csv"
        listings_df.to_csv(csv_file, index=False)
        logger.info(f"Saved as CSV fallback: {csv_file}")
        raise
    
    # Save price events (append mode)
    price_events_file = DATA_DIR / "processed" / "price_events.parquet"
    if not price_events_df.empty:
        # Ensure datetime columns
        if 'changed_at' in price_events_df.columns:
            price_events_df['changed_at'] = pd.to_datetime(price_events_df['changed_at'])
        
        if price_events_file.exists():
            existing_events = pd.read_parquet(price_events_file)
            price_events_df = pd.concat([existing_events, price_events_df], ignore_index=True)
        price_events_df.to_parquet(price_events_file, index=False)
        logger.info(f"Saved {len(price_events_df)} price events to {price_events_file}")
    
    # Save sold events (append mode)
    sold_events_file = DATA_DIR / "processed" / "sold_events.parquet"
    if not sold_events_df.empty:
        # Ensure datetime columns
        for col in ['sold_at', 'published_at', 'first_seen_at']:
            if col in sold_events_df.columns:
                sold_events_df[col] = pd.to_datetime(sold_events_df[col], errors='coerce')
        
        if sold_events_file.exists():
            existing_sold = pd.read_parquet(sold_events_file)
            sold_events_df = pd.concat([existing_sold, sold_events_df], ignore_index=True)
        sold_events_df.to_parquet(sold_events_file, index=False)
        logger.info(f"Saved {len(sold_events_df)} sold events to {sold_events_file}")
    
    # Also save a timestamped backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = DATA_DIR / "processed" / f"listings_backup_{timestamp}.parquet"
    listings_df.to_parquet(backup_file, index=False)
    logger.info(f"Created backup at {backup_file}")


def generate_summary_report(listings_df, price_events_df, sold_events_df):
    """Generate a summary report of the processing."""
    logger.info("\n" + "="*60)
    logger.info("PROCESSING SUMMARY")
    logger.info("="*60)
    
    # Overall stats
    logger.info(f"\nTotal Listings: {len(listings_df)}")
    logger.info(f"  - Active: {len(listings_df[listings_df['status'] == 'active'])}")
    logger.info(f"  - Sold: {len(listings_df[listings_df['status'] == 'sold'])}")
    
    # By brand
    logger.info("\nListings by Brand:")
    for brand in sorted(listings_df['brand_norm'].unique()):
        count = len(listings_df[listings_df['brand_norm'] == brand])
        active = len(listings_df[(listings_df['brand_norm'] == brand) & (listings_df['status'] == 'active')])
        logger.info(f"  {brand}: {count} total ({active} active)")
    
    # By category
    logger.info("\nListings by Category:")
    for cat in sorted(listings_df['category_norm'].unique()):
        count = len(listings_df[listings_df['category_norm'] == cat])
        logger.info(f"  {cat}: {count}")
    
    # Events
    logger.info(f"\nPrice Changes: {len(price_events_df)}")
    logger.info(f"Sold Items: {len(sold_events_df)}")
    
    # Price stats
    logger.info("\nPrice Statistics:")
    logger.info(f"  Mean: €{listings_df['price'].mean():.2f}")
    logger.info(f"  Median: €{listings_df['price'].median():.2f}")
    logger.info(f"  P25: €{listings_df['price'].quantile(0.25):.2f}")
    logger.info(f"  P75: €{listings_df['price'].quantile(0.75):.2f}")
    
    logger.info("="*60 + "\n")


# ============================================================================
# MAIN PROCESSING PIPELINE
# ============================================================================

def process_pipeline():
    """Main data processing pipeline."""
    logger.info("Starting data processing pipeline...")
    
    # Step 1: Load latest scrape
    result = load_latest_scrape()
    if result is None:
        logger.error("No scrape data found. Run the scraper first!")
        return
    
    current_df, scrape_filename = result
    
    # Step 2: Load previous listings database
    previous_df = load_previous_listings()
    
    # Step 3: Process new scrape with normalization
    current_df = process_new_scrape(current_df, scrape_filename)
    
    # Step 4: Detect price changes
    price_events_df = detect_price_changes(current_df, previous_df)
    
    # Step 5: Detect sold items (FIXED: 48 hour threshold)
    sold_events_df = detect_sold_items(current_df, previous_df, hours_threshold=48)
    
    # Step 6: Update listings database
    updated_listings_df = update_listings_database(current_df, previous_df)
    
    # Step 7: Save all processed data
    save_processed_data(updated_listings_df, price_events_df, sold_events_df)
    
    # Step 8: Generate summary report
    generate_summary_report(updated_listings_df, price_events_df, sold_events_df)
    
    logger.info("✅ Data processing pipeline completed successfully!")
    
    return updated_listings_df, price_events_df, sold_events_df


if __name__ == "__main__":
    process_pipeline()