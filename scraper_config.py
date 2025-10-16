"""
Scraper Configuration File
Customize scraping behavior without modifying main scraper code
"""

# ============================================================================
# SCRAPING STRATEGY
# ============================================================================

# Choose one of these strategies:
STRATEGY = "category_wide"  # Options: "category_wide", "brand_specific", "hybrid"

# ============================================================================
# CATEGORY-WIDE COMBOS (Recommended for Demo)
# ============================================================================
# Scrapes entire categories, captures ALL brands naturally

CATEGORY_WIDE_COMBOS = [
    {
        "category": "Dresses",
        "audience": "Women",
        "catalog_ids": [10],
        "order": "newest_first",  # Options: "newest_first", "relevance", "price_low_to_high", "price_high_to_low"
        "max_pages": 10  # 10 pages × 960 items = ~9,600 items max
    },
    {
        "category": "Sneakers",
        "audience": "Men",
        "catalog_ids": [1242],
        "order": "newest_first",
        "max_pages": 10
    },
    {
        "category": "Jeans",
        "audience": "Men",
        "catalog_ids": [257],
        "order": "newest_first",
        "max_pages": 8
    },
    {
        "category": "T-shirt",
        "audience": "Men",
        "catalog_ids": [77],
        "order": "newest_first",
        "max_pages": 8
    }
]

# ============================================================================
# BRAND-SPECIFIC COMBOS (Original Approach)
# ============================================================================
# Only use if you want to target specific brands

BRAND_SPECIFIC_COMBOS = [
    {
        "brand": "Zara",
        "category": "Dresses",
        "audience": "Women",
        "catalog_ids": [10],
        "brand_ids": [12],
        "order": "relevance",
        "max_pages": 10
    },
    {
        "brand": "Mango",
        "category": "Dresses",
        "audience": "Women",
        "catalog_ids": [10],
        "brand_ids": [15],
        "order": "relevance",
        "max_pages": 10
    },
    {
        "brand": "Nike",
        "category": "Sneakers",
        "audience": "Men",
        "catalog_ids": [1242],
        "brand_ids": [53],
        "order": "relevance",
        "max_pages": 10
    }
]

# ============================================================================
# HYBRID COMBOS (Best of Both)
# ============================================================================
# Captures both newest items AND popular items per category

HYBRID_COMBOS = [
    # Round 1: Newest items (fresh inventory)
    {
        "category": "Dresses",
        "audience": "Women",
        "catalog_ids": [10],
        "order": "newest_first",
        "max_pages": 5
    },
    # Round 2: Popular items (high-velocity)
    {
        "category": "Dresses",
        "audience": "Women",
        "catalog_ids": [10],
        "order": "relevance",
        "max_pages": 3
    },
    # Sneakers
    {
        "category": "Sneakers",
        "audience": "Men",
        "catalog_ids": [1242],
        "order": "newest_first",
        "max_pages": 5
    },
    {
        "category": "Sneakers",
        "audience": "Men",
        "catalog_ids": [1242],
        "order": "relevance",
        "max_pages": 3
    }
]

# ============================================================================
# ANTI-DETECTION SETTINGS
# ============================================================================

# Delays (in seconds)
DELAYS = {
    "homepage_load": (4, 7),           # Range: random between min and max
    "between_pages": (10, 15),         # Base delay between pages
    "between_categories": (15, 25),    # Delay between different categories
    "retry_base": 2,                   # Exponential backoff base
    "retry_jitter": (0, 2),            # Random jitter on retries
    "min_delay": 8                     # Absolute minimum delay
}

# User Agents (rotated randomly)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

# Time window restrictions (24-hour format)
SCRAPING_HOURS = {
    "enabled": False,      # Set True to enable time restrictions
    "start_hour": 10,      # Start scraping at 10:00
    "end_hour": 18         # Stop scraping at 18:00
}

# Request settings
REQUEST_SETTINGS = {
    "per_page": 960,       # Items per page (max supported by Vinted)
    "timeout": 60000,      # Page load timeout (milliseconds)
    "retries": 3           # Number of retries per failed request
}

# ============================================================================
# CATALOG IDS REFERENCE (Vinted Categories)
# ============================================================================
# Common Vinted catalog_ids for reference:

VINTED_CATALOG_IDS = {
    # Women
    "women_dresses": [10],
    "women_tops": [77],
    "women_jeans": [257],
    "women_shoes": [16],
    "women_bags": [23],
    "women_accessories": [30],
    
    # Men  
    "men_tshirts": [77],
    "men_jeans": [257],
    "men_sneakers": [1242],
    "men_jackets": [271],
    "men_shirts": [81],
    
    # Kids
    "kids_clothing": [290],
    "kids_shoes": [308]
}

# ============================================================================
# BRAND IDS REFERENCE (Vinted Brands)
# ============================================================================
# Common Vinted brand_ids for reference (only needed for BRAND_SPECIFIC_COMBOS):

VINTED_BRAND_IDS = {
    "Zara": [12],
    "H&M": [7],
    "Mango": [15],
    "Nike": [53],
    "Adidas": [14],
    "Levi's": [10],
    "Pull&Bear": [82],
    "Bershka": [19],
    "Stradivarius": [104]
}

# ============================================================================
# HELPER FUNCTION
# ============================================================================

def get_combos():
    """Return the appropriate combos based on STRATEGY setting"""
    if STRATEGY == "category_wide":
        return CATEGORY_WIDE_COMBOS
    elif STRATEGY == "brand_specific":
        return BRAND_SPECIFIC_COMBOS
    elif STRATEGY == "hybrid":
        return HYBRID_COMBOS
    else:
        raise ValueError(f"Unknown strategy: {STRATEGY}")

# ============================================================================
# EXPORT CONFIGURATION
# ============================================================================

def get_config():
    """Get complete configuration dictionary"""
    return {
        "combos": get_combos(),
        "delays": DELAYS,
        "user_agents": USER_AGENTS,
        "scraping_hours": SCRAPING_HOURS,
        "request_settings": REQUEST_SETTINGS
    }