"""
KPI Calculation Engine for Vinted Market Intelligence
Calculates all required metrics with filtering capabilities
"""
import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime, timedelta

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = Path("data/processed")


# ============================================================================
# DATA LOADING
# ============================================================================

def load_all_data():
    """Load all processed data files."""
    logger.info("Loading processed data...")
    
    # Load listings
    listings_file = DATA_DIR / "listings.parquet"
    if not listings_file.exists():
        raise FileNotFoundError("listings.parquet not found. Run the pipeline first!")
    listings_df = pd.read_parquet(listings_file)
    logger.info(f"Loaded {len(listings_df)} listings")
    
    # Load price events (optional)
    price_events_file = DATA_DIR / "price_events.parquet"
    if price_events_file.exists():
        price_events_df = pd.read_parquet(price_events_file)
        logger.info(f"Loaded {len(price_events_df)} price events")
    else:
        price_events_df = pd.DataFrame()
        logger.warning("No price_events.parquet found")
    
    # Load sold events (optional)
    sold_events_file = DATA_DIR / "sold_events.parquet"
    if sold_events_file.exists():
        sold_events_df = pd.read_parquet(sold_events_file)
        logger.info(f"Loaded {len(sold_events_df)} sold events")
    else:
        sold_events_df = pd.DataFrame()
        logger.warning("No sold_events.parquet found")
    
    return listings_df, price_events_df, sold_events_df


# ============================================================================
# FILTERING FUNCTIONS
# ============================================================================

def apply_filters(df, brand=None, category=None, audience=None, status=None, season=None):
    """Apply filters to dataframe."""
    filtered = df.copy()
    
    if brand:
        if isinstance(brand, str):
            brand = [brand]
        # Check which column name exists
        brand_col = 'brand_norm' if 'brand_norm' in filtered.columns else 'brand'
        if brand_col in filtered.columns:
            filtered = filtered[filtered[brand_col].isin(brand)]
    
    if category:
        if isinstance(category, str):
            category = [category]
        # Check which column name exists
        cat_col = 'category_norm' if 'category_norm' in filtered.columns else 'category'
        if cat_col in filtered.columns:
            filtered = filtered[filtered[cat_col].isin(category)]
    
    if audience:
        if isinstance(audience, str):
            audience = [audience]
        if 'audience' in filtered.columns:
            filtered = filtered[filtered['audience'].isin(audience)]
    
    if status:
        if isinstance(status, str):
            status = [status]
        if 'status' in filtered.columns:
            filtered = filtered[filtered['status'].isin(status)]
    
    if season:
        if isinstance(season, str):
            season = [season]
        if 'season' in filtered.columns:
            filtered = filtered[filtered['season'].isin(season)]
    
    return filtered


# ============================================================================
# KPI CALCULATIONS
# ============================================================================

def calculate_days_to_sell(sold_events_df, brand=None, category=None, audience=None, season=None):
    """
    Calculate Days-to-Sell (DTS) - Median days from first_seen to sold
    
    Returns:
        dict with median, mean, p25, p75
    """
    if sold_events_df.empty:
        logger.warning("No sold events available for DTS calculation")
        return None
    
    # Apply filters
    filtered = apply_filters(
        sold_events_df, 
        brand=brand, 
        category=category, 
        audience=audience, 
        season=season
    )
    
    # Only use high confidence sales (≥48h missing)
    high_confidence = filtered[filtered['sold_confidence'] >= 0.5]
    
    if len(high_confidence) == 0:
        logger.warning("No high-confidence sold items for DTS calculation")
        return None
    
    dts_stats = {
        'median': high_confidence['days_to_sell'].median(),
        'mean': high_confidence['days_to_sell'].mean(),
        'p25': high_confidence['days_to_sell'].quantile(0.25),
        'p75': high_confidence['days_to_sell'].quantile(0.75),
        'count': len(high_confidence),
        'min': high_confidence['days_to_sell'].min(),
        'max': high_confidence['days_to_sell'].max()
    }
    
    return dts_stats


def calculate_sell_through_30d(sold_events_df, listings_df, brand=None, category=None, audience=None, season=None):
    """
    Calculate 30-day sell-through rate
    % of items that sold within 30 days
    
    Returns:
        dict with percentage and counts
    """
    if sold_events_df.empty:
        logger.warning("No sold events available for sell-through calculation")
        return None
    
    # Apply filters to sold items
    filtered_sold = apply_filters(
        sold_events_df, 
        brand=brand, 
        category=category, 
        audience=audience, 
        season=season
    )
    
    # Only high confidence
    high_confidence = filtered_sold[filtered_sold['sold_confidence'] >= 0.5]
    
    if len(high_confidence) == 0:
        return None
    
    # Count sold within 30 days
    sold_30d = high_confidence[high_confidence['days_to_sell'] <= 30]
    
    sell_through = {
        'percentage': (len(sold_30d) / len(high_confidence)) * 100,
        'sold_30d': len(sold_30d),
        'total_sold': len(high_confidence)
    }
    
    return sell_through


def calculate_price_distribution(listings_df, brand=None, category=None, audience=None, status=None, season=None):
    """
    Calculate price distribution (P25, P50/Median, P75)
    
    Returns:
        dict with percentiles and stats
    """
    # Apply filters
    filtered = apply_filters(
        listings_df, 
        brand=brand, 
        category=category, 
        audience=audience, 
        status=status, 
        season=season
    )
    
    if len(filtered) == 0:
        logger.warning("No items match the filters for price distribution")
        return None
    
    # Remove zero prices
    filtered = filtered[filtered['price'] > 0]
    
    price_stats = {
        'p25': filtered['price'].quantile(0.25),
        'p50': filtered['price'].median(),
        'p75': filtered['price'].quantile(0.75),
        'mean': filtered['price'].mean(),
        'min': filtered['price'].min(),
        'max': filtered['price'].max(),
        'std': filtered['price'].std(),
        'count': len(filtered)
    }
    
    return price_stats


def calculate_discount_to_sell(price_events_df, sold_events_df, brand=None, category=None, audience=None, season=None):
    """
    Calculate average discount-to-sell
    Average % price reduction before selling
    
    Returns:
        dict with discount statistics
    """
    if price_events_df.empty or sold_events_df.empty:
        logger.warning("Need both price events and sold events for discount calculation")
        return None
    
    # Filter sold events
    filtered_sold = apply_filters(
        sold_events_df, 
        brand=brand, 
        category=category, 
        audience=audience, 
        season=season
    )
    
    if len(filtered_sold) == 0:
        return None
    
    # Get item_ids of sold items
    sold_item_ids = set(filtered_sold['item_id'])
    
    # Find price changes for sold items
    sold_price_changes = price_events_df[price_events_df['item_id'].isin(sold_item_ids)]
    
    if len(sold_price_changes) == 0:
        logger.info("No price changes found for sold items (items sold at original price)")
        return {
            'avg_discount_pct': 0.0,
            'median_discount_pct': 0.0,
            'items_with_discount': 0,
            'total_sold_items': len(filtered_sold)
        }
    
    # Calculate discount for each item (compare first price to last price)
    discounts = []
    for item_id in sold_item_ids:
        item_changes = sold_price_changes[sold_price_changes['item_id'] == item_id]
        if len(item_changes) > 0:
            # Get first price (could be old_price of first event)
            first_price = item_changes.iloc[0]['old_price']
            # Get last price (new_price of last event)
            last_price = item_changes.iloc[-1]['new_price']
            
            if first_price > 0:
                discount_pct = ((first_price - last_price) / first_price) * 100
                discounts.append({
                    'item_id': item_id,
                    'first_price': first_price,
                    'last_price': last_price,
                    'discount_pct': discount_pct
                })
    
    if len(discounts) == 0:
        return {
            'avg_discount_pct': 0.0,
            'median_discount_pct': 0.0,
            'items_with_discount': 0,
            'total_sold_items': len(filtered_sold)
        }
    
    discounts_df = pd.DataFrame(discounts)
    
    discount_stats = {
        'avg_discount_pct': discounts_df['discount_pct'].mean(),
        'median_discount_pct': discounts_df['discount_pct'].median(),
        'items_with_discount': len(discounts_df),
        'total_sold_items': len(filtered_sold),
        'max_discount': discounts_df['discount_pct'].max(),
        'min_discount': discounts_df['discount_pct'].min()
    }
    
    return discount_stats


def calculate_liquidity_score(dts_stats, sell_through_stats):
    """
    Calculate liquidity score (0-100)
    Higher score = more liquid (sells faster)
    
    Formula: 
    - 50% based on sell-through rate (higher is better)
    - 50% based on inverse of DTS (lower DTS is better)
    """
    if dts_stats is None or sell_through_stats is None:
        return None
    
    # Sell-through component (0-50 points)
    sell_through_score = (sell_through_stats['percentage'] / 100) * 50
    
    # DTS component (0-50 points, inverse scaled)
    # Assume 30 days = 0 points, 0 days = 50 points
    max_dts = 30
    dts_median = dts_stats['median']
    dts_score = max(0, (1 - (dts_median / max_dts)) * 50)
    
    liquidity = {
        'score': sell_through_score + dts_score,
        'sell_through_component': sell_through_score,
        'dts_component': dts_score,
        'grade': 'A' if (sell_through_score + dts_score) >= 75 else 
                 'B' if (sell_through_score + dts_score) >= 50 else 
                 'C' if (sell_through_score + dts_score) >= 25 else 'D'
    }
    
    return liquidity


# ============================================================================
# COMPREHENSIVE KPI CALCULATION
# ============================================================================

def calculate_all_kpis(brand=None, category=None, audience=None, status=None, season=None):
    """
    Calculate all KPIs with optional filters
    
    Returns:
        dict containing all KPIs
    """
    logger.info("Calculating KPIs...")
    
    # Load data
    listings_df, price_events_df, sold_events_df = load_all_data()
    
    # Apply filters for logging
    filter_desc = []
    if brand: filter_desc.append(f"Brand: {brand}")
    if category: filter_desc.append(f"Category: {category}")
    if audience: filter_desc.append(f"Audience: {audience}")
    if status: filter_desc.append(f"Status: {status}")
    if season: filter_desc.append(f"Season: {season}")
    
    if filter_desc:
        logger.info(f"Filters applied: {', '.join(filter_desc)}")
    else:
        logger.info("No filters applied (calculating overall KPIs)")
    
    # Calculate all KPIs
    kpis = {}
    
    # 1. Days to Sell (DTS)
    logger.info("Calculating Days-to-Sell (DTS)...")
    kpis['dts'] = calculate_days_to_sell(
        sold_events_df, brand, category, audience, season
    )
    
    # 2. 30-day Sell-Through Rate
    logger.info("Calculating 30-day sell-through rate...")
    kpis['sell_through_30d'] = calculate_sell_through_30d(
        sold_events_df, listings_df, brand, category, audience, season
    )
    
    # 3. Price Distribution
    logger.info("Calculating price distribution...")
    kpis['price_distribution'] = calculate_price_distribution(
        listings_df, brand, category, audience, status, season
    )
    
    # 4. Discount to Sell
    logger.info("Calculating discount-to-sell...")
    kpis['discount_to_sell'] = calculate_discount_to_sell(
        price_events_df, sold_events_df, brand, category, audience, season
    )
    
    # 5. Liquidity Score
    logger.info("Calculating liquidity score...")
    kpis['liquidity'] = calculate_liquidity_score(
        kpis['dts'], kpis['sell_through_30d']
    )
    
    # Add metadata
    kpis['metadata'] = {
        'calculated_at': datetime.now().isoformat(),
        'filters': {
            'brand': brand,
            'category': category,
            'audience': audience,
            'status': status,
            'season': season
        },
        'data_counts': {
            'total_listings': len(listings_df),
            'active_listings': len(listings_df[listings_df['status'] == 'active']),
            'sold_items': len(sold_events_df),
            'price_changes': len(price_events_df)
        }
    }
    
    return kpis


def calculate_kpis_by_brand():
    """Calculate KPIs for each brand separately."""
    logger.info("\n" + "="*70)
    logger.info("CALCULATING KPIs BY BRAND")
    logger.info("="*70)
    
    listings_df, _, _ = load_all_data()
    brands = sorted(listings_df['brand_norm'].unique())
    
    brand_kpis = {}
    
    for brand in brands:
        logger.info(f"\nProcessing: {brand}")
        brand_kpis[brand] = calculate_all_kpis(brand=brand)
    
    return brand_kpis


def calculate_kpis_by_category():
    """Calculate KPIs for each category separately."""
    logger.info("\n" + "="*70)
    logger.info("CALCULATING KPIs BY CATEGORY")
    logger.info("="*70)
    
    listings_df, _, _ = load_all_data()
    categories = sorted(listings_df['category_norm'].unique())
    
    category_kpis = {}
    
    for category in categories:
        logger.info(f"\nProcessing: {category}")
        category_kpis[category] = calculate_all_kpis(category=category)
    
    return category_kpis


def calculate_kpis_by_brand_category():
    """Calculate KPIs for each brand+category combination."""
    logger.info("\n" + "="*70)
    logger.info("CALCULATING KPIs BY BRAND × CATEGORY")
    logger.info("="*70)
    
    listings_df, _, _ = load_all_data()
    combos = listings_df.groupby(['brand_norm', 'category_norm']).size().reset_index()[['brand_norm', 'category_norm']]
    
    combo_kpis = {}
    
    for _, row in combos.iterrows():
        brand = row['brand_norm']
        category = row['category_norm']
        key = f"{brand} - {category}"
        
        logger.info(f"\nProcessing: {key}")
        combo_kpis[key] = calculate_all_kpis(brand=brand, category=category)
    
    return combo_kpis


# ============================================================================
# REPORTING & EXPORT
# ============================================================================

def print_kpi_report(kpis, title="KPI Report"):
    """Pretty print KPI results."""
    print("\n" + "="*70)
    print(f"{title}")
    print("="*70)
    
    # Days to Sell
    if kpis['dts']:
        print("\n📊 Days-to-Sell (DTS):")
        print(f"   Median: {kpis['dts']['median']:.1f} days")
        print(f"   Mean: {kpis['dts']['mean']:.1f} days")
        print(f"   P25-P75: {kpis['dts']['p25']:.1f} - {kpis['dts']['p75']:.1f} days")
        print(f"   Range: {kpis['dts']['min']:.0f} - {kpis['dts']['max']:.0f} days")
        print(f"   Sample: {kpis['dts']['count']} sold items")
    else:
        print("\n📊 Days-to-Sell (DTS): No data available")
    
    # Sell-Through
    if kpis['sell_through_30d']:
        print("\n📈 30-Day Sell-Through Rate:")
        print(f"   {kpis['sell_through_30d']['percentage']:.1f}%")
        print(f"   ({kpis['sell_through_30d']['sold_30d']} of {kpis['sell_through_30d']['total_sold']} items)")
    else:
        print("\n📈 30-Day Sell-Through Rate: No data available")
    
    # Price Distribution
    if kpis['price_distribution']:
        print("\n💰 Price Distribution:")
        print(f"   P25: €{kpis['price_distribution']['p25']:.2f}")
        print(f"   P50 (Median): €{kpis['price_distribution']['p50']:.2f}")
        print(f"   P75: €{kpis['price_distribution']['p75']:.2f}")
        print(f"   Mean: €{kpis['price_distribution']['mean']:.2f}")
        print(f"   Range: €{kpis['price_distribution']['min']:.2f} - €{kpis['price_distribution']['max']:.2f}")
        print(f"   Sample: {kpis['price_distribution']['count']} items")
    else:
        print("\n💰 Price Distribution: No data available")
    
    # Discount to Sell
    if kpis['discount_to_sell']:
        print("\n💸 Discount-to-Sell:")
        print(f"   Average: {kpis['discount_to_sell']['avg_discount_pct']:.1f}%")
        print(f"   Median: {kpis['discount_to_sell']['median_discount_pct']:.1f}%")
        print(f"   Items discounted: {kpis['discount_to_sell']['items_with_discount']} of {kpis['discount_to_sell']['total_sold_items']}")
    else:
        print("\n💸 Discount-to-Sell: No data available")
    
    # Liquidity Score
    if kpis['liquidity']:
        print("\n🌊 Liquidity Score:")
        print(f"   Overall: {kpis['liquidity']['score']:.1f}/100 (Grade: {kpis['liquidity']['grade']})")
        print(f"   Sell-Through Component: {kpis['liquidity']['sell_through_component']:.1f}/50")
        print(f"   Speed Component: {kpis['liquidity']['dts_component']:.1f}/50")
    else:
        print("\n🌊 Liquidity Score: No data available")
    
    print("\n" + "="*70)


def export_kpis_to_csv(all_kpis, filename="kpis_report.csv"):
    """Export KPIs to CSV format."""
    rows = []
    
    for key, kpis in all_kpis.items():
        row = {'segment': key}
        
        # DTS
        if kpis.get('dts'):
            row['dts_median'] = kpis['dts']['median']
            row['dts_mean'] = kpis['dts']['mean']
            row['dts_p25'] = kpis['dts']['p25']
            row['dts_p75'] = kpis['dts']['p75']
        
        # Sell-through
        if kpis.get('sell_through_30d'):
            row['sell_through_30d_pct'] = kpis['sell_through_30d']['percentage']
            row['sold_30d_count'] = kpis['sell_through_30d']['sold_30d']
        
        # Price
        if kpis.get('price_distribution'):
            row['price_p25'] = kpis['price_distribution']['p25']
            row['price_p50'] = kpis['price_distribution']['p50']
            row['price_p75'] = kpis['price_distribution']['p75']
            row['price_mean'] = kpis['price_distribution']['mean']
        
        # Discount
        if kpis.get('discount_to_sell'):
            row['avg_discount_pct'] = kpis['discount_to_sell']['avg_discount_pct']
            row['median_discount_pct'] = kpis['discount_to_sell']['median_discount_pct']
        
        # Liquidity
        if kpis.get('liquidity'):
            row['liquidity_score'] = kpis['liquidity']['score']
            row['liquidity_grade'] = kpis['liquidity']['grade']
        
        rows.append(row)
    
    df = pd.DataFrame(rows)
    output_file = DATA_DIR / filename
    df.to_csv(output_file, index=False)
    logger.info(f"✅ Exported KPIs to {output_file}")
    
    return df


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function."""
    logger.info("\n" + "🎯 "*20)
    logger.info("VINTED KPI CALCULATION ENGINE")
    logger.info("🎯 "*20)
    
    try:
        # Calculate overall KPIs
        logger.info("\nCalculating overall KPIs (no filters)...")
        overall_kpis = calculate_all_kpis()
        print_kpi_report(overall_kpis, "OVERALL KPIs")
        
        # Calculate by brand
        brand_kpis = calculate_kpis_by_brand()
        for brand, kpis in brand_kpis.items():
            print_kpi_report(kpis, f"KPIs for {brand}")
        
        # Calculate by category
        category_kpis = calculate_kpis_by_category()
        for category, kpis in category_kpis.items():
            print_kpi_report(kpis, f"KPIs for {category}")
        
        # Export all to CSV
        logger.info("\nExporting results...")
        
        all_kpis = {'Overall': overall_kpis}
        all_kpis.update({f"Brand: {k}": v for k, v in brand_kpis.items()})
        all_kpis.update({f"Category: {k}": v for k, v in category_kpis.items()})
        
        export_kpis_to_csv(all_kpis, "kpis_complete_report.csv")
        
        logger.info("\n✅ KPI calculation completed successfully!")
        logger.info(f"📊 Results saved to: {DATA_DIR / 'kpis_complete_report.csv'}")
        
    except Exception as e:
        logger.error(f"❌ Error calculating KPIs: {e}")
        raise


if __name__ == "__main__":
    main()