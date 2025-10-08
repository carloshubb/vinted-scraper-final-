"""
SQL Query Interface for Vinted Data
Allows SQL queries on Parquet files using DuckDB or Pandas
"""
import pandas as pd
from pathlib import Path
import sys

# Try to import DuckDB (optional, faster)
try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False
    print("⚠️  DuckDB not installed. Using Pandas only (slower).")
    print("   Install with: pip install duckdb")

DATA_DIR = Path("data/processed")


# ============================================================================
# DATA LOADING
# ============================================================================

def load_tables():
    """Load all parquet files as DataFrames."""
    tables = {}
    
    # Load listings
    listings_file = DATA_DIR / "listings.parquet"
    if listings_file.exists():
        tables['listings'] = pd.read_parquet(listings_file)
        print(f"✓ Loaded listings: {len(tables['listings'])} rows")
    
    # Load price events
    price_file = DATA_DIR / "price_events.parquet"
    if price_file.exists():
        tables['price_events'] = pd.read_parquet(price_file)
        print(f"✓ Loaded price_events: {len(tables['price_events'])} rows")
    
    # Load sold events
    sold_file = DATA_DIR / "sold_events.parquet"
    if sold_file.exists():
        tables['sold_events'] = pd.read_parquet(sold_file)
        print(f"✓ Loaded sold_events: {len(tables['sold_events'])} rows")
    
    return tables


# ============================================================================
# SQL QUERY ENGINE (using DuckDB)
# ============================================================================

def query_sql(sql, tables=None):
    """
    Execute SQL query on Parquet data using DuckDB.
    
    Args:
        sql: SQL query string
        tables: Optional dict of DataFrames (auto-loaded if None)
    
    Returns:
        DataFrame with results
    
    Example:
        query_sql("SELECT * FROM listings WHERE price > 50 LIMIT 10")
    """
    if not HAS_DUCKDB:
        print("❌ DuckDB not installed. Use query_pandas() instead.")
        return None
    
    if tables is None:
        tables = load_tables()
    
    # Create DuckDB connection
    con = duckdb.connect(':memory:')
    
    # Register tables
    for name, df in tables.items():
        con.register(name, df)
    
    # Execute query
    try:
        result = con.execute(sql).fetchdf()
        print(f"✓ Query returned {len(result)} rows")
        return result
    except Exception as e:
        print(f"❌ SQL Error: {e}")
        return None
    finally:
        con.close()


# ============================================================================
# PANDAS QUERY INTERFACE
# ============================================================================

def query_pandas(table_name, filter_expr=None, columns=None, sort_by=None, limit=None):
    """
    Query data using Pandas (simpler but less powerful than SQL).
    
    Args:
        table_name: 'listings', 'price_events', or 'sold_events'
        filter_expr: Pandas query string (e.g., "price > 50 and brand_norm == 'Zara'")
        columns: List of columns to return
        sort_by: Column name to sort by
        limit: Max number of rows
    
    Returns:
        DataFrame with results
    
    Example:
        query_pandas('listings', 
                     filter_expr="price > 50 and brand_norm == 'Zara'",
                     columns=['title', 'price', 'brand_norm'],
                     sort_by='price',
                     limit=10)
    """
    tables = load_tables()
    
    if table_name not in tables:
        print(f"❌ Table '{table_name}' not found")
        return None
    
    df = tables[table_name].copy()
    
    # Apply filter
    if filter_expr:
        try:
            df = df.query(filter_expr)
        except Exception as e:
            print(f"❌ Filter error: {e}")
            return None
    
    # Select columns
    if columns:
        df = df[columns]
    
    # Sort
    if sort_by:
        df = df.sort_values(sort_by, ascending=False)
    
    # Limit
    if limit:
        df = df.head(limit)
    
    print(f"✓ Query returned {len(df)} rows")
    return df


# ============================================================================
# COMMON SQL QUERIES (Pre-built)
# ============================================================================

class CommonQueries:
    """Collection of common SQL queries for Vinted data."""
    
    @staticmethod
    def top_brands_by_volume(limit=10):
        """Get brands with most listings."""
        sql = f"""
        SELECT 
            brand_norm,
            COUNT(*) as total_items,
            COUNT(CASE WHEN status = 'active' THEN 1 END) as active_items,
            COUNT(CASE WHEN status = 'sold' THEN 1 END) as sold_items,
            ROUND(AVG(price), 2) as avg_price
        FROM listings
        GROUP BY brand_norm
        ORDER BY total_items DESC
        LIMIT {limit}
        """
        return query_sql(sql)
    
    @staticmethod
    def price_trends_by_brand():
        """Average prices by brand and category."""
        sql = """
        SELECT 
            brand_norm,
            category_norm,
            COUNT(*) as items,
            ROUND(AVG(price), 2) as avg_price,
            ROUND(MIN(price), 2) as min_price,
            ROUND(MAX(price), 2) as max_price,
            ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price), 2) as median_price
        FROM listings
        WHERE price > 0
        GROUP BY brand_norm, category_norm
        ORDER BY brand_norm, avg_price DESC
        """
        return query_sql(sql)
    
    @staticmethod
    def fastest_selling_items(limit=20):
        """Items that sold quickest."""
        sql = f"""
        SELECT 
            item_id,
            brand,
            category,
            last_price,
            days_to_sell,
            sold_confidence
        FROM sold_events
        WHERE sold_confidence >= 0.5
        ORDER BY days_to_sell ASC
        LIMIT {limit}
        """
        return query_sql(sql)
    
    @staticmethod
    def slowest_selling_items(limit=20):
        """Items that took longest to sell."""
        sql = f"""
        SELECT 
            item_id,
            brand,
            category,
            last_price,
            days_to_sell,
            sold_confidence
        FROM sold_events
        WHERE sold_confidence >= 0.5
        ORDER BY days_to_sell DESC
        LIMIT {limit}
        """
        return query_sql(sql)
    
    @staticmethod
    def price_changes_by_brand():
        """Brands with most price changes."""
        sql = """
        SELECT 
            brand,
            COUNT(*) as price_changes,
            ROUND(AVG((new_price - old_price) / old_price * 100), 2) as avg_change_pct,
            COUNT(CASE WHEN new_price > old_price THEN 1 END) as price_increases,
            COUNT(CASE WHEN new_price < old_price THEN 1 END) as price_decreases
        FROM price_events
        GROUP BY brand
        ORDER BY price_changes DESC
        """
        return query_sql(sql)
    
    @staticmethod
    def items_by_condition():
        """Distribution of items by condition."""
        sql = """
        SELECT 
            condition_bucket,
            COUNT(*) as items,
            ROUND(AVG(price), 2) as avg_price,
            COUNT(CASE WHEN status = 'sold' THEN 1 END) as sold_count,
            ROUND(COUNT(CASE WHEN status = 'sold' THEN 1 END) * 100.0 / COUNT(*), 2) as sold_percentage
        FROM listings
        GROUP BY condition_bucket
        ORDER BY items DESC
        """
        return query_sql(sql)
    
    @staticmethod
    def seasonal_analysis():
        """Compare summer vs winter items."""
        sql = """
        SELECT 
            season,
            COUNT(*) as items,
            ROUND(AVG(price), 2) as avg_price,
            COUNT(CASE WHEN status = 'sold' THEN 1 END) as sold_items
        FROM listings
        WHERE season IS NOT NULL
        GROUP BY season
        """
        return query_sql(sql)
    
    @staticmethod
    def active_listings_summary():
        """Current active inventory summary."""
        sql = """
        SELECT 
            brand_norm,
            category_norm,
            COUNT(*) as active_items,
            ROUND(AVG(price), 2) as avg_price,
            ROUND(MIN(price), 2) as min_price,
            ROUND(MAX(price), 2) as max_price
        FROM listings
        WHERE status = 'active' AND price > 0
        GROUP BY brand_norm, category_norm
        ORDER BY brand_norm, active_items DESC
        """
        return query_sql(sql)
    
    @staticmethod
    def sold_items_last_n_days(days=7):
        """Items sold in last N days."""
        sql = f"""
        SELECT 
            brand,
            category,
            COUNT(*) as items_sold,
            ROUND(AVG(days_to_sell), 1) as avg_dts,
            ROUND(AVG(last_price), 2) as avg_price
        FROM sold_events
        WHERE sold_at >= CURRENT_DATE - INTERVAL '{days} days'
        AND sold_confidence >= 0.5
        GROUP BY brand, category
        ORDER BY items_sold DESC
        """
        return query_sql(sql)


# ============================================================================
# EXPORT FUNCTIONS
# ============================================================================

def export_query_results(df, filename, format='csv'):
    """
    Export query results to file.
    
    Args:
        df: DataFrame to export
        filename: Output filename (without extension)
        format: 'csv', 'excel', or 'json'
    """
    output_dir = Path("data/exports")
    output_dir.mkdir(exist_ok=True)
    
    if format == 'csv':
        filepath = output_dir / f"{filename}.csv"
        df.to_csv(filepath, index=False)
    elif format == 'excel':
        filepath = output_dir / f"{filename}.xlsx"
        df.to_excel(filepath, index=False)
    elif format == 'json':
        filepath = output_dir / f"{filename}.json"
        df.to_json(filepath, orient='records', indent=2)
    
    print(f"✓ Exported to: {filepath}")
    return filepath


# ============================================================================
# INTERACTIVE QUERY TOOL
# ============================================================================

def interactive_query():
    """Interactive SQL query tool."""
    print("\n" + "="*70)
    print("VINTED SQL QUERY TOOL")
    print("="*70)
    
    # Load tables
    tables = load_tables()
    
    if not tables:
        print("❌ No data found. Run the pipeline first.")
        return
    
    print("\n📊 Available tables:")
    for name, df in tables.items():
        print(f"  - {name} ({len(df)} rows, {len(df.columns)} columns)")
    
    if HAS_DUCKDB:
        print("\n💡 Enter SQL query (or 'help' for examples, 'exit' to quit):")
        
        while True:
            query = input("\nSQL> ").strip()
            
            if query.lower() == 'exit':
                break
            elif query.lower() == 'help':
                show_examples()
            elif query:
                result = query_sql(query, tables)
                if result is not None and len(result) > 0:
                    print("\n" + result.to_string())
    else:
        print("\n⚠️  Install DuckDB for SQL support: pip install duckdb")


def show_examples():
    """Show example queries."""
    print("""
    📖 Example SQL Queries:
    
    1. Top 10 most expensive items:
       SELECT title, brand_norm, price FROM listings ORDER BY price DESC LIMIT 10
    
    2. Zara items under €30:
       SELECT * FROM listings WHERE brand_norm = 'Zara' AND price < 30
    
    3. Items sold in less than 5 days:
       SELECT * FROM sold_events WHERE days_to_sell < 5
    
    4. Average price by brand:
       SELECT brand_norm, AVG(price) as avg_price FROM listings GROUP BY brand_norm
    
    5. Price changes that increased:
       SELECT * FROM price_events WHERE new_price > old_price
    
    📚 Pre-built queries available via CommonQueries class:
       - CommonQueries.top_brands_by_volume()
       - CommonQueries.price_trends_by_brand()
       - CommonQueries.fastest_selling_items()
    """)


# ============================================================================
# MAIN CLI
# ============================================================================

def main():
    """Main CLI interface."""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'interactive':
            interactive_query()
        elif command == 'top-brands':
            print("\n🏆 Top Brands by Volume:")
            result = CommonQueries.top_brands_by_volume()
            if result is not None:
                print(result.to_string(index=False))
        elif command == 'price-trends':
            print("\n💰 Price Trends by Brand:")
            result = CommonQueries.price_trends_by_brand()
            if result is not None:
                print(result.to_string(index=False))
        elif command == 'fastest-selling':
            print("\n⚡ Fastest Selling Items:")
            result = CommonQueries.fastest_selling_items()
            if result is not None:
                print(result.to_string(index=False))
        elif command == 'active-summary':
            print("\n📊 Active Listings Summary:")
            result = CommonQueries.active_listings_summary()
            if result is not None:
                print(result.to_string(index=False))
        else:
            print(f"Unknown command: {command}")
            print_usage()
    else:
        print_usage()


def print_usage():
    """Print usage instructions."""
    print("""
    Usage: python sql_queries.py [command]
    
    Commands:
      interactive        - Interactive SQL query tool
      top-brands        - Show top brands by volume
      price-trends      - Show price trends by brand
      fastest-selling   - Show fastest selling items
      active-summary    - Show active inventory summary
    
    Or import and use in Python:
      from sql_queries import query_sql, CommonQueries
      
      # Custom SQL
      df = query_sql("SELECT * FROM listings WHERE price > 50")
      
      # Pre-built queries
      df = CommonQueries.top_brands_by_volume()
    """)


if __name__ == "__main__":
    main()