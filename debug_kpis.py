"""
Debug Script for KPI Calculation Issues
Run this to investigate the 375,700% sell-through and 187,895 liquidity score problems
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

sys.path.append(str(Path(__file__).parent))
from calculate_kpis import load_all_data, calculate_all_kpis

def main():
    print("="*80)
    print("KPI CALCULATION DEBUG SCRIPT")
    print("="*80)
    
    # Load data
    print("\n1. Loading data...")
    listings_df, price_events_df, sold_events_df = load_all_data()
    
    print(f"   Listings: {len(listings_df):,}")
    print(f"   Price events: {len(price_events_df):,}")
    print(f"   Sold events: {len(sold_events_df):,}")
    
    # Check data sanity
    print("\n2. Data Sanity Checks:")
    active_count = len(listings_df[listings_df['status'] == 'active'])
    sold_in_listings = len(listings_df[listings_df['status'] == 'sold'])
    print(f"   Active in listings: {active_count:,}")
    print(f"   Sold in listings: {sold_in_listings:,}")
    print(f"   Total in listings: {len(listings_df):,}")
    print(f"   Sold events table: {len(sold_events_df):,}")
    
    if len(sold_events_df) > len(listings_df):
        print("   ⚠️  WARNING: More sold events than total listings!")
        print("   This is OK if sold_events accumulates over time")
    
    # Check sold events data quality
    print("\n3. Sold Events Quality:")
    if len(sold_events_df) > 0:
        print(f"   Confidence distribution:")
        print(sold_events_df['sold_confidence'].value_counts())
        
        print(f"\n   Days to sell stats:")
        print(sold_events_df['days_to_sell'].describe())
        
        print(f"\n   Listing age stats:")
        if 'listing_age_days' in sold_events_df.columns:
            print(sold_events_df['listing_age_days'].describe())
        else:
            print("   ⚠️  WARNING: listing_age_days column missing!")
    
    # Test each brand individually
    print("\n4. Testing Brand KPIs:")
    print("="*80)
    
    for brand in sorted(listings_df['brand_norm'].unique()):
        print(f"\n--- {brand} ---")
        
        # Count items
        brand_listings = listings_df[listings_df['brand_norm'] == brand]
        brand_active = len(brand_listings[brand_listings['status'] == 'active'])
        brand_sold_events = sold_events_df[sold_events_df['brand'] == brand] if len(sold_events_df) > 0 else pd.DataFrame()
        
        print(f"Active items: {brand_active:,}")
        print(f"Sold events: {len(brand_sold_events):,}")
        
        # Calculate KPIs
        try:
            kpis = calculate_all_kpis(brand=brand)
            
            # Check DTS
            if kpis['dts']:
                print(f"DTS median: {kpis['dts']['median']:.2f} days")
                if kpis['dts']['median'] < 0:
                    print("   ❌ ERROR: Negative DTS!")
                elif kpis['dts']['median'] > 100:
                    print("   ⚠️  WARNING: DTS > 100 days")
            else:
                print("DTS: No data")
            
            # Check Sell-Through
            if kpis['sell_through_30d']:
                st_pct = kpis['sell_through_30d']['percentage']
                sold_30d = kpis['sell_through_30d']['sold_30d']
                eligible = kpis['sell_through_30d']['eligible_items']
                
                print(f"Sell-Through: {st_pct:.2f}%")
                print(f"  Numerator (sold ≤30d): {sold_30d}")
                print(f"  Denominator (eligible): {eligible}")
                
                if st_pct > 100:
                    print("   ❌ ERROR: Sell-through > 100%!")
                    print(f"   Formula: ({sold_30d} / {eligible}) × 100 = {st_pct:.2f}%")
                    
                    # Debug further
                    if eligible == 0:
                        print("   🔍 ROOT CAUSE: Denominator is ZERO!")
                    elif eligible < 1:
                        print(f"   🔍 ROOT CAUSE: Denominator is too small ({eligible})")
                    else:
                        print(f"   🔍 ROOT CAUSE: Numerator ({sold_30d}) > Denominator ({eligible})")
                
                if st_pct > 1000:
                    print("   ❌ CRITICAL: Sell-through > 1000% - calculation is completely broken!")
            else:
                print("Sell-Through: No data")
            
            # Check Liquidity
            if kpis['liquidity']:
                liq_score = kpis['liquidity']['score']
                st_component = kpis['liquidity']['sell_through_component']
                dts_component = kpis['liquidity']['dts_component']
                
                print(f"Liquidity Score: {liq_score:.2f}")
                print(f"  ST component: {st_component:.2f}/50")
                print(f"  DTS component: {dts_component:.2f}/50")
                
                if liq_score > 100:
                    print("   ❌ ERROR: Liquidity score > 100!")
                    print(f"   Formula: {st_component:.2f} + {dts_component:.2f} = {liq_score:.2f}")
                    
                    if st_component > 50:
                        print(f"   🔍 ROOT CAUSE: ST component > 50 ({st_component:.2f})")
                    if dts_component > 50:
                        print(f"   🔍 ROOT CAUSE: DTS component > 50 ({dts_component:.2f})")
                
                if liq_score > 10000:
                    print("   ❌ CRITICAL: Liquidity > 10,000 - calculation is completely broken!")
            else:
                print("Liquidity: No data")
            
            # Check Price Distribution
            if kpis['price_distribution']:
                print(f"Price P50: EUR {kpis['price_distribution']['p50']:.2f}")
            else:
                print("Price: No data")
            
        except Exception as e:
            print(f"❌ ERROR calculating KPIs: {e}")
            import traceback
            traceback.print_exc()
    
    # Deep dive into sell-through calculation for Mango (the one showing 375,700%)
    print("\n" + "="*80)
    print("5. DEEP DIVE: Mango Sell-Through Calculation")
    print("="*80)
    
    mango_listings = listings_df[listings_df['brand_norm'] == 'Mango']
    mango_sold = sold_events_df[sold_events_df['brand'] == 'Mango'] if len(sold_events_df) > 0 else pd.DataFrame()
    
    print(f"\nMango listings in database: {len(mango_listings):,}")
    print(f"Mango sold events: {len(mango_sold):,}")
    
    if len(mango_listings) > 0:
        # Check published_at dates
        current_time = datetime.now()
        
        mango_listings_copy = mango_listings.copy()
        mango_listings_copy['listing_date'] = pd.to_datetime(mango_listings_copy['published_at'])
        mango_listings_copy['days_since_listed'] = (current_time - mango_listings_copy['listing_date']).dt.days
        
        print(f"\nDays since listed (for Mango):")
        print(mango_listings_copy['days_since_listed'].describe())
        
        # Count eligible (≥30 days)
        eligible_mango = mango_listings_copy[mango_listings_copy['days_since_listed'] >= 30]
        print(f"\nEligible items (≥30 days): {len(eligible_mango):,}")
        
        if len(eligible_mango) == 0:
            print("🔍 ROOT CAUSE: NO eligible items (all listings < 30 days old)")
            print("   This causes division by zero or tiny denominator!")
        
        # Count sold in 30d
        if len(mango_sold) > 0:
            mango_sold_30d = mango_sold[mango_sold['days_to_sell'] <= 30]
            print(f"Sold in ≤30 days: {len(mango_sold_30d):,}")
            
            # Manual calculation
            if len(eligible_mango) > 0:
                manual_rate = (len(mango_sold_30d) / len(eligible_mango)) * 100
                print(f"\nManual calculation: ({len(mango_sold_30d)} / {len(eligible_mango)}) × 100 = {manual_rate:.2f}%")
            else:
                print(f"\nManual calculation: ({len(mango_sold_30d)} / 0) × 100 = ERROR (division by zero)")
    
    # Summary
    print("\n" + "="*80)
    print("6. SUMMARY OF FINDINGS")
    print("="*80)
    
    print("\n🔍 Likely Root Causes:")
    print("1. Sell-through denominator (eligible items) is ZERO or very small")
    print("   → All items are < 30 days old, no items are eligible yet")
    print("2. This causes division by zero or huge percentages")
    print("3. Broken sell-through cascades to liquidity score calculation")
    
    print("\n💡 Recommended Fixes:")
    print("1. Add check: if eligible_items == 0, return null or 0% (not calculate)")
    print("2. Add validation: if percentage > 100, log error and cap at 100")
    print("3. Wait for data maturity (items need to be listed >30 days)")
    print("4. OR: Change formula to use total listings instead of eligible")
    
    print("\n" + "="*80)
    print("DEBUG SCRIPT COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()