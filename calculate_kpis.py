"""
KPI Calculation Engine - FIXED DATA CONSISTENCY
Changes:
1. Use ONLY listings.parquet as source of truth
2. Calculate sold from status='sold' in listings (not sold_events)
3. Ensure denominators always = numerators when filtered
4. Cap liquidity score at 100
5. Cap sell-through at 100%
"""
import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = Path("data/processed")


def load_all_data():
    """Load all processed data files."""
    logger.info("Loading processed data...")
    
    listings_file = DATA_DIR / "listings.parquet"
    if not listings_file.exists():
        raise FileNotFoundError("listings.parquet not found. Run the pipeline first!")
    listings_df = pd.read_parquet(listings_file)
    
    for col in ['first_seen_at', 'last_seen_at', 'published_at', 'scrape_timestamp']:
        if col in listings_df.columns:
            listings_df[col] = pd.to_datetime(listings_df[col])
    
    logger.info(f"Loaded {len(listings_df)} listings")
    
    # Price events (keep for discount calculations)
    price_events_file = DATA_DIR / "price_events.parquet"
    if price_events_file.exists():
        price_events_df = pd.read_parquet(price_events_file)
        if 'changed_at' in price_events_df.columns:
            price_events_df['changed_at'] = pd.to_datetime(price_events_df['changed_at'])
        logger.info(f"Loaded {len(price_events_df)} price events")
    else:
        price_events_df = pd.DataFrame()
    
    # We don't use sold_events anymore - all data comes from listings
    
    return listings_df, price_events_df


def apply_filters(df, brand=None, category=None, audience=None, status=None, season=None):
    """Apply filters to dataframe."""
    filtered = df.copy()
    
    if brand:
        if isinstance(brand, str):
            brand = [brand]
        brand_col = 'brand_norm' if 'brand_norm' in filtered.columns else 'brand'
        if brand_col in filtered.columns:
            filtered = filtered[filtered[brand_col].isin(brand)]
    
    if category:
        if isinstance(category, str):
            category = [category]
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


def calculate_days_to_sell_from_listings(listings_df, brand=None, category=None, audience=None, season=None):
    """
    FIXED: Calculate DTS from listings.parquet only
    Uses sold items with proper date calculations
    """
    filtered = apply_filters(listings_df, brand=brand, category=category, audience=audience, season=season)
    
    # Get only sold items
    sold_items = filtered[filtered['status'] == 'sold'].copy()
    
    if len(sold_items) == 0:
        logger.warning("No sold items match filters for DTS calculation")
        return None
    
    # Calculate DTS: (last_seen_at + 24h) - first_seen_at
    sold_items['estimated_sold_at'] = pd.to_datetime(sold_items['last_seen_at']) + timedelta(hours=24)
    sold_items['days_to_sell'] = (
        sold_items['estimated_sold_at'] - pd.to_datetime(sold_items['first_seen_at'])
    ).dt.total_seconds() / (24 * 3600)
    
    # Remove invalid values
    sold_items = sold_items[sold_items['days_to_sell'] > 0]
    
    if len(sold_items) == 0:
        return None
    
    dts_stats = {
        'median': sold_items['days_to_sell'].median(),
        'mean': sold_items['days_to_sell'].mean(),
        'p25': sold_items['days_to_sell'].quantile(0.25),
        'p75': sold_items['days_to_sell'].quantile(0.75),
        'count': len(sold_items),
        'min': sold_items['days_to_sell'].min(),
        'max': sold_items['days_to_sell'].max()
    }
    
    return dts_stats


def calculate_sell_through_30d(listings_df, brand=None, category=None, audience=None, season=None):
    """
    FIXED: Correct 30-Day Sell-Through from listings only
    
    Formula: (Items sold ≤30 days from first_seen_at) / (All items in segment)
    Both numerator and denominator come from same filtered set
    """
    # Filter all items (active + sold)
    filtered_all = apply_filters(listings_df, brand=brand, category=category, audience=audience, season=season)
    
    if len(filtered_all) == 0:
        logger.warning("No listings match filters for sell-through calculation")
        return None
    
    # Total items in segment
    denominator = len(filtered_all)
    
    # Get sold items from the same filtered set
    sold_items = filtered_all[filtered_all['status'] == 'sold'].copy()
    
    if len(sold_items) == 0:
        return {
            'percentage': 0.0,
            'sold_30d': 0,
            'total_items': denominator,
            'total_sold': 0,
            'note': 'No sold items yet'
        }
    
    # Calculate DTS for sold items
    sold_items['estimated_sold_at'] = pd.to_datetime(sold_items['last_seen_at']) + timedelta(hours=24)
    sold_items['days_to_sell'] = (
        sold_items['estimated_sold_at'] - pd.to_datetime(sold_items['first_seen_at'])
    ).dt.total_seconds() / (24 * 3600)
    
    # Count items sold within 30 days
    sold_30d = sold_items[sold_items['days_to_sell'] <= 30]
    numerator = len(sold_30d)
    
    # Calculate percentage (cap at 100%)
    sell_through_pct = min((numerator / denominator) * 100, 100.0)
    
    return {
        'percentage': sell_through_pct,
        'sold_30d': numerator,
        'total_sold': len(sold_items),
        'total_items': denominator,
        'formula': f'{numerator} sold ≤30d / {denominator} total items'
    }


def calculate_price_distribution(listings_df, brand=None, category=None, audience=None, status=None, season=None):
    """Calculate price distribution (P25, P50/Median, P75)."""
    filtered = apply_filters(listings_df, brand=brand, category=category, audience=audience, status=status, season=season)
    
    if len(filtered) == 0:
        logger.warning("No items match the filters for price distribution")
        return None
    
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


def calculate_discount_to_sell(price_events_df, listings_df, brand=None, category=None, audience=None, season=None):
    """
    FIXED: Calculate average discount-to-sell using listings as source of truth
    """
    if price_events_df.empty:
        logger.warning("No price events available for discount calculation")
        return None
    
    # Get sold items from listings
    filtered_sold = apply_filters(listings_df, brand=brand, category=category, audience=audience, season=season)
    filtered_sold = filtered_sold[filtered_sold['status'] == 'sold']
    
    if len(filtered_sold) == 0:
        return None
    
    sold_item_ids = set(filtered_sold['item_id'])
    sold_price_changes = price_events_df[price_events_df['item_id'].isin(sold_item_ids)]
    
    if len(sold_price_changes) == 0:
        return {
            'avg_discount_pct': 0.0,
            'median_discount_pct': 0.0,
            'items_with_discount': 0,
            'total_sold_items': len(filtered_sold)
        }
    
    discounts = []
    for item_id in sold_item_ids:
        item_changes = sold_price_changes[sold_price_changes['item_id'] == item_id].sort_values('changed_at')
        if len(item_changes) > 0:
            first_price = item_changes.iloc[0]['old_price']
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
    
    return {
        'avg_discount_pct': discounts_df['discount_pct'].mean(),
        'median_discount_pct': discounts_df['discount_pct'].median(),
        'items_with_discount': len(discounts_df),
        'total_sold_items': len(filtered_sold),
        'max_discount': discounts_df['discount_pct'].max(),
        'min_discount': discounts_df['discount_pct'].min()
    }


def calculate_liquidity_score(dts_stats, sell_through_stats):
    """
    FIXED: Calculate liquidity score (0-100) with proper capping
    """
    if dts_stats is None or sell_through_stats is None:
        return None
    
    # Sell-through component (max 50 points)
    # Cap at 50% sell-through = max score
    st_normalized = min(sell_through_stats['percentage'] / 50, 1.0)
    sell_through_score = st_normalized * 50
    
    # DTS component (max 50 points)
    # 0 days = 50 points, 30 days = 0 points
    max_dts = 30
    dts_median = dts_stats['median']
    dts_score = max(0, (1 - (dts_median / max_dts)) * 50)
    
    # Total score (capped at 100)
    total_score = min(sell_through_score + dts_score, 100.0)
    
    if total_score >= 75:
        grade = 'A'
    elif total_score >= 50:
        grade = 'B'
    elif total_score >= 25:
        grade = 'C'
    else:
        grade = 'D'
    
    return {
        'score': total_score,
        'sell_through_component': sell_through_score,
        'dts_component': dts_score,
        'grade': grade
    }


def calculate_all_kpis(brand=None, category=None, audience=None, status=None, season=None):
    """Calculate all KPIs with optional filters."""
    logger.info("Calculating KPIs...")
    
    listings_df, price_events_df = load_all_data()
    
    filter_desc = []
    if brand: filter_desc.append(f"Brand: {brand}")
    if category: filter_desc.append(f"Category: {category}")
    if audience: filter_desc.append(f"Audience: {audience}")
    if status: filter_desc.append(f"Status: {status}")
    if season: filter_desc.append(f"Season: {season}")
    
    if filter_desc:
        logger.info(f"Filters applied: {', '.join(filter_desc)}")
    
    kpis = {}
    
    logger.info("Calculating Days-to-Sell (DTS)...")
    kpis['dts'] = calculate_days_to_sell_from_listings(listings_df, brand, category, audience, season)
    
    logger.info("Calculating 30-day sell-through rate...")
    kpis['sell_through_30d'] = calculate_sell_through_30d(listings_df, brand, category, audience, season)
    
    logger.info("Calculating price distribution...")
    kpis['price_distribution'] = calculate_price_distribution(listings_df, brand, category, audience, status, season)
    
    logger.info("Calculating discount-to-sell...")
    kpis['discount_to_sell'] = calculate_discount_to_sell(price_events_df, listings_df, brand, category, audience, season)
    
    logger.info("Calculating liquidity score...")
    kpis['liquidity'] = calculate_liquidity_score(kpis['dts'], kpis['sell_through_30d'])
    
    # Get correct counts from filtered data
    filtered_all = apply_filters(listings_df, brand=brand, category=category, audience=audience, season=season)
    
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
            'total_listings': len(filtered_all),
            'active_listings': len(filtered_all[filtered_all['status'] == 'active']),
            'sold_items': len(filtered_all[filtered_all['status'] == 'sold']),
            'price_changes': len(price_events_df)
        }
    }
    
    return kpis


def print_kpi_report(kpis, title="KPI Report"):
    """Pretty print KPI results."""
    print("\n" + "="*70)
    print(f"{title}")
    print("="*70)
    
    if kpis['dts']:
        print("\n[DTS] Days-to-Sell:")
        print(f"   Median: {kpis['dts']['median']:.1f} days")
        print(f"   Mean: {kpis['dts']['mean']:.1f} days")
        print(f"   P25-P75: {kpis['dts']['p25']:.1f} - {kpis['dts']['p75']:.1f} days")
        print(f"   Sample: {kpis['dts']['count']} sold items")
    else:
        print("\n[DTS] Days-to-Sell: No data available")
    
    if kpis['sell_through_30d']:
        print("\n[SELL-THROUGH] 30-Day Sell-Through Rate:")
        print(f"   {kpis['sell_through_30d']['percentage']:.1f}%")
        print(f"   ({kpis['sell_through_30d']['sold_30d']} sold ≤30d / {kpis['sell_through_30d']['total_items']} total items)")
        print(f"   Total sold: {kpis['sell_through_30d']['total_sold']}")
    else:
        print("\n[SELL-THROUGH] 30-Day Sell-Through Rate: No data available")
    
    if kpis['price_distribution']:
        print("\n[PRICE] Price Distribution:")
        print(f"   P25: EUR {kpis['price_distribution']['p25']:.2f}")
        print(f"   P50 (Median): EUR {kpis['price_distribution']['p50']:.2f}")
        print(f"   P75: EUR {kpis['price_distribution']['p75']:.2f}")
        print(f"   Sample: {kpis['price_distribution']['count']} items")
    else:
        print("\n[PRICE] Price Distribution: No data available")
    
    if kpis['discount_to_sell']:
        print("\n[DISCOUNT] Discount-to-Sell:")
        print(f"   Average: {kpis['discount_to_sell']['avg_discount_pct']:.1f}%")
        print(f"   Median: {kpis['discount_to_sell']['median_discount_pct']:.1f}%")
    else:
        print("\n[DISCOUNT] Discount-to-Sell: No data available")
    
    if kpis['liquidity']:
        print("\n[LIQUIDITY] Liquidity Score:")
        print(f"   Overall: {kpis['liquidity']['score']:.1f}/100 (Grade: {kpis['liquidity']['grade']})")
    else:
        print("\n[LIQUIDITY] Liquidity Score: No data available")
    
    print("\n" + "="*70)


def calculate_kpis_by_brand():
    """Calculate KPIs for each brand separately."""
    logger.info("\n" + "="*70)
    logger.info("CALCULATING KPIs BY BRAND")
    logger.info("="*70)
    
    listings_df, _ = load_all_data()
    brand_col = 'brand_norm' if 'brand_norm' in listings_df.columns else 'brand'
    
    brands = listings_df[brand_col].dropna().unique()
    brands = sorted([b for b in brands if b is not None])
    
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
    
    listings_df, _ = load_all_data()
    cat_col = 'category_norm' if 'category_norm' in listings_df.columns else 'category'
    
    categories = listings_df[cat_col].dropna().unique()
    categories = sorted([c for c in categories if c is not None])
    
    category_kpis = {}
    for category in categories:
        logger.info(f"\nProcessing: {category}")
        category_kpis[category] = calculate_all_kpis(category=category)
    
    return category_kpis


def export_kpis_to_csv(all_kpis, filename="kpis_report.csv"):
    """Export KPIs to CSV format."""
    rows = []
    
    for key, kpis in all_kpis.items():
        row = {'segment': key}
        
        if kpis.get('dts'):
            row['dts_median'] = kpis['dts']['median']
            row['dts_mean'] = kpis['dts']['mean']
            row['dts_p25'] = kpis['dts']['p25']
            row['dts_p75'] = kpis['dts']['p75']
        
        if kpis.get('sell_through_30d'):
            row['sell_through_30d_pct'] = kpis['sell_through_30d']['percentage']
            row['sold_30d_count'] = kpis['sell_through_30d']['sold_30d']
            row['total_sold'] = kpis['sell_through_30d']['total_sold']
            row['total_items'] = kpis['sell_through_30d']['total_items']
        
        if kpis.get('price_distribution'):
            row['price_p25'] = kpis['price_distribution']['p25']
            row['price_p50'] = kpis['price_distribution']['p50']
            row['price_p75'] = kpis['price_distribution']['p75']
            row['price_mean'] = kpis['price_distribution']['mean']
        
        if kpis.get('discount_to_sell'):
            row['avg_discount_pct'] = kpis['discount_to_sell']['avg_discount_pct']
            row['median_discount_pct'] = kpis['discount_to_sell']['median_discount_pct']
        
        if kpis.get('liquidity'):
            row['liquidity_score'] = kpis['liquidity']['score']
            row['liquidity_grade'] = kpis['liquidity']['grade']
        
        rows.append(row)
    
    df = pd.DataFrame(rows)
    output_file = DATA_DIR / filename
    df.to_csv(output_file, index=False)
    logger.info(f"[OK] Exported KPIs to {output_file}")
    
    return df


def main():
    """Main execution function."""
    logger.info("\n" + "="*60)
    logger.info("MARKET INTELLIGENCE KPI ENGINE")
    logger.info("="*60)
    
    try:
        logger.info("\nCalculating overall KPIs (no filters)...")
        overall_kpis = calculate_all_kpis()
        print_kpi_report(overall_kpis, "OVERALL KPIs")
        
        brand_kpis = calculate_kpis_by_brand()
        for brand, kpis in brand_kpis.items():
            print_kpi_report(kpis, f"KPIs for {brand}")
        
        category_kpis = calculate_kpis_by_category()
        for category, kpis in category_kpis.items():
            print_kpi_report(kpis, f"KPIs for {category}")
        
        logger.info("\nExporting results...")
        
        all_kpis = {'Overall': overall_kpis}
        all_kpis.update({f"Brand: {k}": v for k, v in brand_kpis.items()})
        all_kpis.update({f"Category: {k}": v for k, v in category_kpis.items()})
        
        export_kpis_to_csv(all_kpis, "kpis_complete_report.csv")
        
        logger.info("\n[OK] KPI calculation completed successfully!")
        logger.info(f"[REPORT] Results saved to: {DATA_DIR / 'kpis_complete_report.csv'}")
        
    except Exception as e:
        logger.error(f"[FAIL] Error calculating KPIs: {e}")
        raise


if __name__ == "__main__":
    main()