"""
Data inspection tool to verify processed data quality
"""
import pandas as pd
from pathlib import Path
import sys

DATA_DIR = Path("data/processed")


def inspect_listings():
    """Inspect the listings database."""
    listings_file = DATA_DIR / "listings.parquet"
    
    if not listings_file.exists():
        print("❌ No listings.parquet found. Run the pipeline first!")
        return None
    
    df = pd.read_parquet(listings_file)
    
    print("\n" + "="*70)
    print("LISTINGS DATABASE INSPECTION")
    print("="*70)
    
    # Basic info
    print(f"\n📊 Total Records: {len(df)}")
    print(f"   Columns: {len(df.columns)}")
    print(f"   Memory Usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
    
    # Status breakdown
    print("\n📈 Status Breakdown:")
    for status, count in df['status'].value_counts().items():
        print(f"   {status}: {count} ({count/len(df)*100:.1f}%)")
    
    # Brand distribution
    print("\n🏷️  Brand Distribution:")
    for brand, count in df['brand_norm'].value_counts().items():
        active = len(df[(df['brand_norm'] == brand) & (df['status'] == 'active')])
        sold = len(df[(df['brand_norm'] == brand) & (df['status'] == 'sold')])
        print(f"   {brand}: {count} total ({active} active, {sold} sold)")
    
    # Category distribution
    print("\n📦 Category Distribution:")
    for cat, count in df['category_norm'].value_counts().items():
        print(f"   {cat}: {count}")
    
    # Condition distribution
    print("\n✨ Condition Distribution:")
    for cond, count in df['condition_bucket'].value_counts().items():
        print(f"   {cond}: {count}")
    
    # Audience distribution
    print("\n👥 Audience Distribution:")
    for aud, count in df['audience'].value_counts().items():
        print(f"   {aud}: {count}")
    
    # Season info (if exists)
    if 'season' in df.columns:
        season_count = df['season'].notna().sum()
        print(f"\n🌡️  Items with Season Info: {season_count} ({season_count/len(df)*100:.1f}%)")
        if season_count > 0:
            for season, count in df['season'].value_counts().items():
                print(f"   {season}: {count}")
    
    # Price statistics
    print("\n💰 Price Statistics:")
    print(f"   Mean: €{df['price'].mean():.2f}")
    print(f"   Median: €{df['price'].median():.2f}")
    print(f"   P25: €{df['price'].quantile(0.25):.2f}")
    print(f"   P75: €{df['price'].quantile(0.75):.2f}")
    print(f"   Min: €{df['price'].min():.2f}")
    print(f"   Max: €{df['price'].max():.2f}")
    
    # Date range
    print("\n📅 Date Range:")
    print(f"   First Seen: {df['first_seen_at'].min()}")
    print(f"   Last Seen: {df['last_seen_at'].max()}")
    
    # Data quality checks
    print("\n🔍 Data Quality Checks:")
    print(f"   Missing brand_norm: {df['brand_norm'].isna().sum()}")
    print(f"   Missing category_norm: {df['category_norm'].isna().sum()}")
    print(f"   Missing condition_bucket: {df['condition_bucket'].isna().sum()}")
    print(f"   Zero prices: {(df['price'] == 0).sum()}")
    print(f"   Duplicate item_ids: {df['item_id'].duplicated().sum()}")
    
    return df


def inspect_price_events():
    """Inspect price change events."""
    price_file = DATA_DIR / "price_events.parquet"
    
    if not price_file.exists():
        print("\n⚠️  No price_events.parquet found (no price changes detected yet)")
        return None
    
    df = pd.read_parquet(price_file)
    
    print("\n" + "="*70)
    print("PRICE EVENTS INSPECTION")
    print("="*70)
    
    print(f"\n💱 Total Price Changes: {len(df)}")
    
    if len(df) > 0:
        # Price change statistics
        df['price_diff'] = df['new_price'] - df['old_price']
        df['price_change_pct'] = (df['price_diff'] / df['old_price']) * 100
        
        print(f"\n📊 Price Change Statistics:")
        print(f"   Average change: €{df['price_diff'].mean():.2f} ({df['price_change_pct'].mean():.1f}%)")
        print(f"   Median change: €{df['price_diff'].median():.2f} ({df['price_change_pct'].median():.1f}%)")
        print(f"   Price increases: {(df['price_diff'] > 0).sum()}")
        print(f"   Price decreases: {(df['price_diff'] < 0).sum()}")
        
        print(f"\n🏷️  Price Changes by Brand:")
        for brand, count in df['brand'].value_counts().items():
            avg_change = df[df['brand'] == brand]['price_change_pct'].mean()
            print(f"   {brand}: {count} changes (avg {avg_change:+.1f}%)")
        
        # Recent events
        print(f"\n🕒 Recent Price Changes (last 5):")
        recent = df.nlargest(5, 'changed_at')[['item_id', 'brand', 'old_price', 'new_price', 'changed_at']]
        print(recent.to_string(index=False))
    
    return df


def inspect_sold_events():
    """Inspect sold item events."""
    sold_file = DATA_DIR / "sold_events.parquet"
    
    if not sold_file.exists():
        print("\n⚠️  No sold_events.parquet found (no sold items detected yet)")
        return None
    
    df = pd.read_parquet(sold_file)
    
    print("\n" + "="*70)
    print("SOLD EVENTS INSPECTION")
    print("="*70)
    
    print(f"\n📦 Total Sold Items: {len(df)}")
    
    if len(df) > 0:
        # Confidence distribution
        print(f"\n✅ Confidence Distribution:")
        for conf, count in df['sold_confidence'].value_counts().sort_index(ascending=False).items():
            label = {1.0: "High (≥48h)", 0.5: "Medium (24-48h)", 0.0: "Low (<24h)"}.get(conf, "Unknown")
            print(f"   {label}: {count} ({count/len(df)*100:.1f}%)")
        
        # Days to sell statistics
        print(f"\n⏱️  Days to Sell Statistics:")
        print(f"   Mean: {df['days_to_sell'].mean():.1f} days")
        print(f"   Median: {df['days_to_sell'].median():.1f} days")
        print(f"   P25: {df['days_to_sell'].quantile(0.25):.1f} days")
        print(f"   P75: {df['days_to_sell'].quantile(0.75):.1f} days")
        print(f"   Min: {df['days_to_sell'].min():.0f} days")
        print(f"   Max: {df['days_to_sell'].max():.0f} days")
        
        # Sold in 30 days
        sold_30d = len(df[df['days_to_sell'] <= 30])
        print(f"\n📈 Sold within 30 days: {sold_30d} ({sold_30d/len(df)*100:.1f}%)")
        
        # By brand
        print(f"\n🏷️  Sold Items by Brand:")
        for brand in df['brand'].value_counts().index:
            brand_df = df[df['brand'] == brand]
            count = len(brand_df)
            avg_dts = brand_df['days_to_sell'].median()
            avg_price = brand_df['last_price'].mean()
            print(f"   {brand}: {count} items (median {avg_dts:.0f} days, avg €{avg_price:.2f})")
        
        # By category
        print(f"\n📦 Sold Items by Category:")
        for cat in df['category'].value_counts().index:
            cat_df = df[df['category'] == cat]
            count = len(cat_df)
            avg_dts = cat_df['days_to_sell'].median()
            print(f"   {cat}: {count} items (median {avg_dts:.0f} days)")
        
        # By condition
        print(f"\n✨ Sold Items by Condition:")
        for cond in df['condition'].value_counts().index:
            cond_df = df[df['condition'] == cond]
            count = len(cond_df)
            avg_dts = cond_df['days_to_sell'].median()
            print(f"   {cond}: {count} items (median {avg_dts:.0f} days)")
        
        # Recent sales
        print(f"\n🕒 Recent Sales (last 5):")
        recent = df.nlargest(5, 'sold_at')[['brand', 'category', 'last_price', 'days_to_sell', 'sold_confidence']]
        print(recent.to_string(index=False))
    
    return df


def show_sample_records(df, n=5):
    """Show sample records from a dataframe."""
    if df is None or len(df) == 0:
        print("No data to display")
        return
    
    print(f"\n📋 Sample Records (first {n}):")
    print("-" * 70)
    
    # Select key columns
    if 'brand_norm' in df.columns:
        cols = ['item_id', 'brand_norm', 'category_norm', 'price', 'condition_bucket', 'status']
        print(df[cols].head(n).to_string(index=False))
    else:
        print(df.head(n).to_string(index=False))


def export_summary_report():
    """Export a summary report to CSV."""
    listings_df = pd.read_parquet(DATA_DIR / "listings.parquet")
    
    # Create summary by brand and category
    summary = listings_df.groupby(['brand_norm', 'category_norm', 'status']).agg({
        'item_id': 'count',
        'price': ['mean', 'median', 'min', 'max']
    }).round(2)
    
    summary.columns = ['count', 'avg_price', 'median_price', 'min_price', 'max_price']
    summary = summary.reset_index()
    
    output_file = DATA_DIR / "summary_report.csv"
    summary.to_csv(output_file, index=False)
    print(f"\n📄 Summary report exported to: {output_file}")
    
    return summary


def main():
    """Main inspection routine."""
    print("\n" + "🔍 " * 20)
    print("VINTED DATA INSPECTION TOOL")
    print("🔍 " * 20)
    
    # Check if data exists
    if not DATA_DIR.exists():
        print("\n❌ No processed data found!")
        print("   Run: python run_pipeline.py")
        return
    
    # Inspect all data sources
    listings_df = inspect_listings()
    price_events_df = inspect_price_events()
    sold_events_df = inspect_sold_events()
    
    # Show sample records
    if listings_df is not None:
        show_sample_records(listings_df)
    
    # Export summary
    if listings_df is not None and len(listings_df) > 0:
        try:
            export_summary_report()
        except Exception as e:
            print(f"\n⚠️  Could not export summary: {e}")
    
    print("\n" + "="*70)
    print("✅ INSPECTION COMPLETE")
    print("="*70)
    
    # Recommendations
    print("\n💡 Recommendations:")
    if listings_df is not None:
        if len(listings_df[listings_df['status'] == 'sold']) == 0:
            print("   ⏳ No sold items yet. Run the pipeline again in 48 hours to detect sales.")
        if price_events_df is None or len(price_events_df) == 0:
            print("   ⏳ No price changes yet. Run the pipeline again in 48 hours to track changes.")
        
        # Check data quality
        zero_prices = (listings_df['price'] == 0).sum()
        if zero_prices > 0:
            print(f"   ⚠️  Found {zero_prices} items with zero price - check scraper")
        
        missing_brands = listings_df['brand_norm'].isna().sum()
        if missing_brands > 0:
            print(f"   ⚠️  Found {missing_brands} items with missing brand - check normalization")
    
    print("\n📊 Next Steps:")
    print("   1. Review the data quality checks above")
    print("   2. Run: python calculate_kpis.py")
    print("   3. Launch dashboard: streamlit run app.py")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--listings":
            inspect_listings()
        elif sys.argv[1] == "--prices":
            inspect_price_events()
        elif sys.argv[1] == "--sold":
            inspect_sold_events()
        elif sys.argv[1] == "--export":
            export_summary_report()
        else:
            print("Usage:")
            print("  python inspect_data.py              # Full inspection")
            print("  python inspect_data.py --listings   # Listings only")
            print("  python inspect_data.py --prices     # Price events only")
            print("  python inspect_data.py --sold       # Sold events only")
            print("  python inspect_data.py --export     # Export summary CSV")
    else:
        main()