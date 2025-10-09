"""
Diagnostic script to check timestamp data quality
"""
import pandas as pd
from pathlib import Path

DATA_DIR = Path("data/processed")

# Load the files
print("="*70)
print("DIAGNOSTIC: CHECKING TIMESTAMP DATA")
print("="*70)

# Check sold_events
sold_file = DATA_DIR / "sold_events.parquet"
if sold_file.exists():
    sold_df = pd.read_parquet(sold_file)
    print(f"\n✅ Found sold_events.parquet with {len(sold_df)} rows")
    print(f"\nColumns: {list(sold_df.columns)}")
    
    # Parse datetime columns
    if 'first_seen' in sold_df.columns:
        sold_df['first_seen'] = pd.to_datetime(sold_df['first_seen'])
    if 'sold_at' in sold_df.columns:
        sold_df['sold_at'] = pd.to_datetime(sold_df['sold_at'])
    
    print("\n" + "="*70)
    print("SAMPLE DATA (first 10 rows)")
    print("="*70)
    
    # Show relevant columns
    cols_to_show = ['item_id', 'first_seen', 'sold_at']
    if all(col in sold_df.columns for col in cols_to_show):
        sample = sold_df[cols_to_show].head(10)
        print(sample.to_string())
        
        # Calculate days_to_sell
        if 'first_seen' in sold_df.columns and 'sold_at' in sold_df.columns:
            sold_df['days_diff'] = (sold_df['sold_at'] - sold_df['first_seen']).dt.total_seconds() / (24 * 3600)
            
            print("\n" + "="*70)
            print("DAYS TO SELL STATISTICS")
            print("="*70)
            print(f"Min: {sold_df['days_diff'].min():.2f} days")
            print(f"Max: {sold_df['days_diff'].max():.2f} days")
            print(f"Mean: {sold_df['days_diff'].mean():.2f} days")
            print(f"Median: {sold_df['days_diff'].median():.2f} days")
            print(f"Count of 0.0 days: {(sold_df['days_diff'] == 0).sum()} / {len(sold_df)}")
            print(f"Count of < 1 day: {(sold_df['days_diff'] < 1).sum()} / {len(sold_df)}")
            
            print("\n" + "="*70)
            print("SAMPLE WITH CALCULATED DAYS")
            print("="*70)
            sample_with_days = sold_df[['item_id', 'first_seen', 'sold_at', 'days_diff']].head(20)
            print(sample_with_days.to_string())
            
            print("\n" + "="*70)
            print("ITEMS WITH NON-ZERO DAYS (if any)")
            print("="*70)
            non_zero = sold_df[sold_df['days_diff'] > 0][['item_id', 'first_seen', 'sold_at', 'days_diff']].head(10)
            if len(non_zero) > 0:
                print(non_zero.to_string())
            else:
                print("❌ NO ITEMS WITH NON-ZERO DAYS TO SELL!")
                print("\n🔍 ROOT CAUSE: All items have first_seen == sold_at")
                print("\nThis means you're either:")
                print("1. Scraping items AFTER they're already sold")
                print("2. Not tracking when items are first listed")
                print("3. The scraper is setting both timestamps to the same value")
    else:
        print(f"❌ Missing required columns. Available: {list(sold_df.columns)}")
else:
    print("❌ sold_events.parquet not found")

# Check listings for comparison
print("\n" + "="*70)
print("CHECKING LISTINGS.PARQUET")
print("="*70)

listings_file = DATA_DIR / "listings.parquet"
if listings_file.exists():
    listings_df = pd.read_parquet(listings_file)
    print(f"\n✅ Found listings.parquet with {len(listings_df)} rows")
    print(f"Columns: {list(listings_df.columns)}")
    
    if 'first_seen' in listings_df.columns:
        listings_df['first_seen'] = pd.to_datetime(listings_df['first_seen'])
    if 'last_seen' in listings_df.columns:
        listings_df['last_seen'] = pd.to_datetime(listings_df['last_seen'])
    
    print("\nSample data:")
    cols = ['item_id', 'status', 'first_seen', 'last_seen']
    if all(c in listings_df.columns for c in cols):
        print(listings_df[cols].head(10).to_string())
    
    if 'status' in listings_df.columns:
        print(f"\nStatus distribution:")
        print(listings_df['status'].value_counts())
else:
    print("❌ listings.parquet not found")

print("\n" + "="*70)
print("DIAGNOSIS COMPLETE")
print("="*70)