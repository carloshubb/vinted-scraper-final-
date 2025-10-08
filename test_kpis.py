"""
Interactive KPI testing tool
Test different filter combinations
"""
from calculate_kpis import (
    calculate_all_kpis, 
    print_kpi_report,
    load_all_data
)
import sys


def test_specific_combo(brand, category):
    """Test KPIs for a specific brand-category combination."""
    print(f"\n{'='*70}")
    print(f"Testing: {brand} - {category}")
    print(f"{'='*70}")
    
    kpis = calculate_all_kpis(brand=brand, category=category)
    print_kpi_report(kpis, f"{brand} - {category}")
    
    return kpis


def test_all_combos():
    """Test all brand-category combinations from the original scrape."""
    combos = [
        ("Zara", "Dress"),
        ("Mango", "Dress"),
        ("Nike", "Sneakers"),
        ("H&M", "T-shirt"),
        ("Levi's", "Jeans")
    ]
    
    results = {}
    for brand, category in combos:
        results[f"{brand}-{category}"] = test_specific_combo(brand, category)
    
    return results


def test_by_season():
    """Test KPIs split by season."""
    print("\n" + "="*70)
    print("Testing KPIs by Season")
    print("="*70)
    
    for season in ['summer', 'winter']:
        print(f"\n--- {season.upper()} ---")
        kpis = calculate_all_kpis(season=season)
        print_kpi_report(kpis, f"{season.capitalize()} Items")


def test_by_condition():
    """Test KPIs split by condition bucket."""
    print("\n" + "="*70)
    print("Testing KPIs by Condition")
    print("="*70)
    
    conditions = ['New/Like new', 'Very good/Good', 'Average/Poor']
    
    listings_df, _, _ = load_all_data()
    
    for condition in conditions:
        # Filter listings by condition
        count = len(listings_df[listings_df['condition_bucket'] == condition])
        print(f"\n--- {condition} ({count} items) ---")
        
        # Note: We can't filter calculate_all_kpis by condition directly
        # because sold_events doesn't have condition_bucket readily accessible
        # This is a demonstration of what you could do with more complex filtering


def show_available_filters():
    """Show what filters are available in the data."""
    print("\n" + "="*70)
    print("Available Filters")
    print("="*70)
    
    listings_df, _, sold_df = load_all_data()
    
    print("\n🏷️  Brands:")
    for brand in sorted(listings_df['brand_norm'].unique()):
        count = len(listings_df[listings_df['brand_norm'] == brand])
        print(f"   - {brand} ({count} items)")
    
    print("\n📦 Categories:")
    for cat in sorted(listings_df['category_norm'].unique()):
        count = len(listings_df[listings_df['category_norm'] == cat])
        print(f"   - {cat} ({count} items)")
    
    print("\n👥 Audiences:")
    for aud in sorted(listings_df['audience'].unique()):
        count = len(listings_df[listings_df['audience'] == aud])
        print(f"   - {aud} ({count} items)")
    
    print("\n✨ Conditions:")
    for cond in sorted(listings_df['condition_bucket'].unique()):
        count = len(listings_df[listings_df['condition_bucket'] == cond])
        print(f"   - {cond} ({count} items)")
    
    if 'season' in listings_df.columns:
        season_count = listings_df['season'].notna().sum()
        if season_count > 0:
            print(f"\n🌡️  Seasons ({season_count} items with season data):")
            for season in sorted(listings_df['season'].dropna().unique()):
                count = len(listings_df[listings_df['season'] == season])
                print(f"   - {season} ({count} items)")


def compare_brands():
    """Create a brand comparison table."""
    print("\n" + "="*70)
    print("BRAND COMPARISON TABLE")
    print("="*70)
    
    brands = ["Zara", "Mango", "Nike", "H&M", "Levi's"]
    
    print(f"\n{'Brand':<12} {'DTS (days)':<12} {'Sell-Thru':<12} {'Median Price':<15} {'Liquidity':<12}")
    print("-" * 70)
    
    for brand in brands:
        kpis = calculate_all_kpis(brand=brand)
        
        dts = f"{kpis['dts']['median']:.1f}" if kpis['dts'] else "N/A"
        sell_through = f"{kpis['sell_through_30d']['percentage']:.1f}%" if kpis['sell_through_30d'] else "N/A"
        price = f"€{kpis['price_distribution']['p50']:.2f}" if kpis['price_distribution'] else "N/A"
        liquidity = f"{kpis['liquidity']['score']:.0f} ({kpis['liquidity']['grade']})" if kpis['liquidity'] else "N/A"
        
        print(f"{brand:<12} {dts:<12} {sell_through:<12} {price:<15} {liquidity:<12}")
    
    print("\n" + "="*70)


def interactive_mode():
    """Interactive mode for testing custom filters."""
    print("\n" + "🎯 "*20)
    print("INTERACTIVE KPI CALCULATOR")
    print("🎯 "*20)
    
    show_available_filters()
    
    print("\n" + "="*70)
    print("Enter filters (press Enter to skip):")
    print("="*70)
    
    brand = input("\nBrand (e.g., Zara): ").strip() or None
    category = input("Category (e.g., Dress): ").strip() or None
    audience = input("Audience (e.g., Mujer): ").strip() or None
    season = input("Season (e.g., summer, winter): ").strip() or None
    
    if not any([brand, category, audience, season]):
        print("\n⚠️  No filters specified. Calculating overall KPIs...")
    
    print("\n🔄 Calculating KPIs with your filters...")
    kpis = calculate_all_kpis(
        brand=brand,
        category=category,
        audience=audience,
        season=season
    )
    
    filter_desc = []
    if brand: filter_desc.append(brand)
    if category: filter_desc.append(category)
    if audience: filter_desc.append(audience)
    if season: filter_desc.append(season)
    
    title = " × ".join(filter_desc) if filter_desc else "Overall"
    print_kpi_report(kpis, f"KPIs for {title}")


def quick_liquidity_ranking():
    """Show liquidity ranking of all brands."""
    print("\n" + "="*70)
    print("LIQUIDITY RANKING (Highest to Lowest)")
    print("="*70)
    print("\nLiquidity = How fast items sell")
    print("Score: 0-100 (Higher = Better)")
    print("="*70)
    
    brands = ["Zara", "Mango", "Nike", "H&M", "Levi's"]
    rankings = []
    
    for brand in brands:
        kpis = calculate_all_kpis(brand=brand)
        if kpis['liquidity']:
            rankings.append({
                'brand': brand,
                'score': kpis['liquidity']['score'],
                'grade': kpis['liquidity']['grade'],
                'dts': kpis['dts']['median'] if kpis['dts'] else None,
                'sell_through': kpis['sell_through_30d']['percentage'] if kpis['sell_through_30d'] else None
            })
    
    # Sort by liquidity score
    rankings.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"\n{'Rank':<6} {'Brand':<12} {'Score':<10} {'Grade':<8} {'DTS':<12} {'30d Sell-Thru':<15}")
    print("-" * 70)
    
    for i, r in enumerate(rankings, 1):
        dts_str = f"{r['dts']:.1f}d" if r['dts'] else "N/A"
        st_str = f"{r['sell_through']:.1f}%" if r['sell_through'] else "N/A"
        print(f"{i:<6} {r['brand']:<12} {r['score']:<10.1f} {r['grade']:<8} {dts_str:<12} {st_str:<15}")
    
    print("\n💡 Interpretation:")
    print("   A (75-100): Excellent liquidity - items sell very fast")
    print("   B (50-74):  Good liquidity - items sell reasonably fast")
    print("   C (25-49):  Fair liquidity - slower sales")
    print("   D (0-24):   Poor liquidity - very slow sales")
    print("\n" + "="*70)


def main():
    """Main testing menu."""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "--all-combos":
            test_all_combos()
        elif command == "--compare-brands":
            compare_brands()
        elif command == "--liquidity":
            quick_liquidity_ranking()
        elif command == "--season":
            test_by_season()
        elif command == "--filters":
            show_available_filters()
        elif command == "--interactive":
            interactive_mode()
        else:
            print("Unknown command. Available options:")
            print("  --all-combos      Test all brand-category combos")
            print("  --compare-brands  Compare all brands side-by-side")
            print("  --liquidity       Show liquidity ranking")
            print("  --season          Compare summer vs winter")
            print("  --filters         Show available filters")
            print("  --interactive     Interactive filter mode")
    else:
        # Default: show menu
        print("\n" + "🧪 "*20)
        print("KPI TESTING TOOL")
        print("🧪 "*20)
        print("\nWhat would you like to test?")
        print("\n1. Test all brand-category combinations")
        print("2. Compare all brands side-by-side")
        print("3. Show liquidity ranking")
        print("4. Compare summer vs winter items")
        print("5. Show available filters")
        print("6. Interactive mode (custom filters)")
        print("7. Exit")
        
        choice = input("\nEnter choice (1-7): ").strip()
        
        if choice == "1":
            test_all_combos()
        elif choice == "2":
            compare_brands()
        elif choice == "3":
            quick_liquidity_ranking()
        elif choice == "4":
            test_by_season()
        elif choice == "5":
            show_available_filters()
        elif choice == "6":
            interactive_mode()
        elif choice == "7":
            print("\n👋 Goodbye!")
        else:
            print("\n⚠️  Invalid choice")


if __name__ == "__main__":
    main()