"""
Test script for Vinted scraper
Run this to verify everything works before full scraping
"""

from vinted_scraper import VintedScraper
import json

def test_single_page():
    """Test scraping a single page"""
    print("\n" + "="*70)
    print("TEST 1: Single Page Scrape - Zara Dresses Women")
    print("="*70)
    
    scraper = VintedScraper()
    
    try:
        listings = scraper.scrape_listings(
            brand="Zara",
            category="Dresses",
            audience="Women",
            max_pages=1  # Only 1 page for testing
        )
        
        if listings:
            print(f"\n✓ SUCCESS: Retrieved {len(listings)} listings")
            
            # Show first listing details
            print("\n" + "-"*70)
            print("SAMPLE LISTING:")
            print("-"*70)
            sample = listings[0]
            for key, value in sample.items():
                if key not in ['description']:  # Skip long description
                    print(f"{key:20} : {value}")
            
            # Save test results
            scraper.save_to_csv(listings, 'test_zara_single_page.csv')
            
            return True
        else:
            print("\n✗ FAILED: No listings retrieved")
            return False
            
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        return False


def test_multiple_pages():
    """Test scraping multiple pages"""
    print("\n" + "="*70)
    print("TEST 2: Multiple Pages - Zara Dresses Women (3 pages)")
    print("="*70)
    
    scraper = VintedScraper()
    
    try:
        listings = scraper.scrape_listings(
            brand="Zara",
            category="Dresses",
            audience="Women",
            max_pages=3
        )
        
        if listings:
            print(f"\n✓ SUCCESS: Retrieved {len(listings)} total listings")
            scraper.save_to_csv(listings, 'test_zara_multi_page.csv')
            return True
        else:
            print("\n✗ FAILED: No listings retrieved")
            return False
            
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        return False


def test_different_brands():
    """Test different brand/category combinations"""
    print("\n" + "="*70)
    print("TEST 3: Different Brands (1 page each)")
    print("="*70)
    
    scraper = VintedScraper()
    
    test_combos = [
        ('Zara', 'Dresses', 'Women'),
        ('Mango', 'Dresses', 'Women'),
        ('Nike', 'Sneakers', 'Men'),
    ]
    
    results = {}
    
    for brand, category, audience in test_combos:
        print(f"\nTesting: {brand} · {category} · {audience}")
        try:
            listings = scraper.scrape_listings(
                brand=brand,
                category=category,
                audience=audience,
                max_pages=1
            )
            results[brand] = len(listings)
            print(f"  ✓ {len(listings)} listings")
        except Exception as e:
            results[brand] = 0
            print(f"  ✗ Error: {str(e)}")
    
    print("\n" + "-"*70)
    print("RESULTS SUMMARY:")
    print("-"*70)
    for brand, count in results.items():
        status = "✓" if count > 0 else "✗"
        print(f"{status} {brand:20} : {count:>4} listings")
    
    return all(count > 0 for count in results.values())


def test_data_quality():
    """Test data quality and required fields"""
    print("\n" + "="*70)
    print("TEST 4: Data Quality Check")
    print("="*70)
    
    scraper = VintedScraper()
    
    listings = scraper.scrape_listings(
        brand="Zara",
        category="Dresses",
        audience="Women",
        max_pages=1
    )
    
    if not listings:
        print("✗ No listings to check")
        return False
    
    required_fields = [
        'listing_id', 'brand_raw', 'category_raw', 'title', 'size_raw',
        'condition_raw', 'audience', 'price', 'currency', 'published_at',
        'listing_url', 'seller_id', 'visible', 'scraped_at'
    ]
    
    print(f"\nChecking {len(listings)} listings for required fields...")
    
    missing_fields = {}
    for field in required_fields:
        count = sum(1 for listing in listings if not listing.get(field))
        if count > 0:
            missing_fields[field] = count
    
    if missing_fields:
        print("\n⚠ WARNING: Some fields are missing data:")
        for field, count in missing_fields.items():
            print(f"  {field:20} : {count}/{len(listings)} listings missing")
        return False
    else:
        print("\n✓ All required fields present in all listings")
        
        # Check season keyword extraction
        with_season = sum(1 for l in listings if l.get('season_keyword'))
        print(f"✓ Season keywords found: {with_season}/{len(listings)} listings")
        
        # Check price range
        prices = [l['price'] for l in listings if l.get('price', 0) > 0]
        if prices:
            print(f"✓ Price range: €{min(prices):.2f} - €{max(prices):.2f}")
        
        return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "#"*70)
    print("#" + " "*68 + "#")
    print("#" + " VINTED SCRAPER - TEST SUITE ".center(68) + "#")
    print("#" + " "*68 + "#")
    print("#"*70)
    
    tests = [
        ("Single Page Scrape", test_single_page),
        ("Multiple Pages Scrape", test_multiple_pages),
        ("Different Brands", test_different_brands),
        ("Data Quality Check", test_data_quality),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n✗ TEST CRASHED: {str(e)}")
            results[test_name] = False
    
    # Final summary
    print("\n" + "#"*70)
    print("# FINAL RESULTS")
    print("#"*70)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status:12} : {test_name}")
    
    total = len(results)
    passed = sum(results.values())
    
    print("#"*70)
    print(f"# TOTAL: {passed}/{total} tests passed")
    print("#"*70 + "\n")
    
    if passed == total:
        print("🎉 All tests passed! Ready for production scraping.")
    else:
        print("⚠ Some tests failed. Check the output above for details.")


if __name__ == "__main__":
    # Run all tests
    run_all_tests()
    
    # Or run individual tests:
    # test_single_page()
    # test_multiple_pages()
    # test_different_brands()
    # test_data_quality()