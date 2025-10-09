"""
Check if we have published_at data that we can use for accurate DTS
"""
import pandas as pd
from pathlib import Path

DATA_DIR = Path("data/processed")

print("="*70)
print("CHECKING FOR PUBLISHED_AT DATA")
print("="*70)

# Load listings
listings_file = DATA_DIR / "listings.parquet"
listings_df = pd.read_parquet(listings_file)

print(f"\nListings columns: {list(listings_df.columns)}")

if 'published_at' in listings_df.columns:
    print("\n✅ FOUND published_at column!")
    
    listings_df['published_at'] = pd.to_datetime(listings_df['published_at'])
    listings_df['first_seen_at'] = pd.to_datetime(listings_df['first_seen_at'])
    
    print("\nSample data:")
    print(listings_df[['item_id', 'published_at', 'first_seen_at', 'status']].head(10).to_string())
    
    print("\npublished_at stats:")
    print(f"  Min: {listings_df['published_at'].min()}")
    print(f"  Max: {listings_df['published_at'].max()}")
    print(f"  Unique values: {listings_df['published_at'].nunique()}")
    
    print("\nfirst_seen_at stats:")
    print(f"  Min: {listings_df['first_seen_at'].min()}")
    print(f"  Max: {listings_df['first_seen_at'].max()}")
    print(f"  Unique values: {listings_df['first_seen_at'].nunique()}")
    
    # Check if published_at varies (real data) vs first_seen_at (all same)
    if listings_df['published_at'].nunique() > 100:
        print("\n✅ published_at has real variation - this is the ACTUAL listing date!")
        print(f"   {listings_df['published_at'].nunique()} unique values")
    else:
        print("\n❌ published_at doesn't vary much")
    
    # Compare for sold items
    sold_items = listings_df[listings_df['status'] == 'sold']
    if len(sold_items) > 0:
        print(f"\nSold items sample:")
        print(sold_items[['item_id', 'published_at', 'first_seen_at']].head(10).to_string())
        
        # Calculate difference
        sold_items['days_since_published'] = (
            sold_items['first_seen_at'] - sold_items['published_at']
        ).dt.total_seconds() / (24 * 3600)
        
        print(f"\nDays between published_at and first_seen_at (when scraper found it):")
        print(f"  Mean: {sold_items['days_since_published'].mean():.1f} days")
        print(f"  Median: {sold_items['days_since_published'].median():.1f} days")
        print(f"  Min: {sold_items['days_since_published'].min():.1f} days")
        print(f"  Max: {sold_items['days_since_published'].max():.1f} days")
        
else:
    print("\n❌ No published_at column found")
    print("Your days-to-sell calculations will be inaccurate")

print("\n" + "="*70)