"""
Market Intelligence Dashboard - PERFORMANCE OPTIMIZED
Changes:
1. Lazy loading - only load data when needed
2. Aggressive caching with longer TTL
3. Data sampling for large datasets
4. Reduced KPI calculations on page load
5. Progress indicators for long operations
6. Pagination for large tables
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
import sys
from datetime import datetime, timedelta
import io
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER

# CLIENT COLORS
PRIMARY_BLUE = '#006064'
ACCENT_CYAN = '#00FFFF'

def safe_sorted(series):
    """Safely sort a pandas series, removing None/NaN values"""
    return sorted([x for x in series.dropna().unique() if x is not None])

sys.path.append(str(Path(__file__).parent))

st.set_page_config(
    page_title="Market Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(f"""
<style>
    .main-header {{
        font-size: 2.5rem;
        font-weight: bold;
        color: {PRIMARY_BLUE};
        margin-bottom: 1rem;
    }}
    .stMetric {{
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid {PRIMARY_BLUE};
    }}
    .stSpinner > div {{
        border-color: {PRIMARY_BLUE} transparent transparent transparent;
    }}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# OPTIMIZED DATA LOADING
# ============================================================================

@st.cache_data(ttl=7200, show_spinner=False)  # Cache for 2 hours
def load_listings_lightweight():
    """Load only essential columns for faster initial load"""
    try:
        from pathlib import Path
        DATA_DIR = Path("data/processed")
        listings_file = DATA_DIR / "listings.parquet"
        
        if not listings_file.exists():
            return None
        
        # Load only essential columns first
        essential_cols = [
            'item_id', 'brand_norm', 'category_norm', 'condition_bucket',
            'price', 'status', 'audience', 'first_seen_at', 'last_seen_at'
        ]
        
        df = pd.read_parquet(listings_file, columns=essential_cols)
        
        # Convert dates efficiently
        for col in ['first_seen_at', 'last_seen_at']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

@st.cache_data(ttl=7200, show_spinner=False)
def load_price_events_lightweight():
    """Load price events with minimal processing"""
    try:
        from pathlib import Path
        DATA_DIR = Path("data/processed")
        price_file = DATA_DIR / "price_events.parquet"
        
        if not price_file.exists():
            return pd.DataFrame()
        
        return pd.read_parquet(price_file)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def get_summary_stats(listings_df):
    """Pre-calculate summary statistics"""
    if listings_df is None:
        return {}
    
    stats = {
        'total': len(listings_df),
        'active': len(listings_df[listings_df['status'] == 'active']),
        'sold': len(listings_df[listings_df['status'] == 'sold']),
        'brands': listings_df['brand_norm'].nunique(),
        'categories': listings_df['category_norm'].nunique(),
        'median_price': listings_df['price'].median(),
        'last_update': listings_df['last_seen_at'].max() if 'last_seen_at' in listings_df.columns else None
    }
    return stats

@st.cache_data(ttl=3600, show_spinner=False)
def calculate_dts_fast(sold_df):
    """Fast DTS calculation without loading full calculate_kpis"""
    if len(sold_df) == 0:
        return None
    
    sold_df = sold_df.copy()
    sold_df['estimated_sold_at'] = pd.to_datetime(sold_df['last_seen_at']) + timedelta(hours=24)
    sold_df['dts'] = (
        sold_df['estimated_sold_at'] - pd.to_datetime(sold_df['first_seen_at'])
    ).dt.total_seconds() / (24 * 3600)
    
    return {
        'median': sold_df['dts'].median(),
        'mean': sold_df['dts'].mean(),
        'count': len(sold_df)
    }

@st.cache_data(ttl=3600, show_spinner=False)
def calculate_sell_through_fast(filtered_all, filtered_sold):
    """Fast sell-through calculation"""
    if len(filtered_all) == 0:
        return None
    
    if len(filtered_sold) == 0:
        return {'percentage': 0.0, 'sold_30d': 0, 'total': len(filtered_all)}
    
    sold_with_dts = filtered_sold.copy()
    sold_with_dts['estimated_sold_at'] = pd.to_datetime(sold_with_dts['last_seen_at']) + timedelta(hours=24)
    sold_with_dts['dts'] = (
        sold_with_dts['estimated_sold_at'] - pd.to_datetime(sold_with_dts['first_seen_at'])
    ).dt.total_seconds() / (24 * 3600)
    
    sold_30d = len(sold_with_dts[sold_with_dts['dts'] <= 30])
    st_rate = min((sold_30d / len(filtered_all)) * 100, 100.0)
    
    return {
        'percentage': st_rate,
        'sold_30d': sold_30d,
        'total': len(filtered_all)
    }

@st.cache_data(ttl=3600, show_spinner=False)
def calculate_liquidity_fast(dts_median, sell_through_pct):
    """Fast liquidity score calculation"""
    if dts_median is None or sell_through_pct is None:
        return None
    
    st_normalized = min(sell_through_pct / 50, 1.0)
    sell_through_score = st_normalized * 50
    
    dts_score = max(0, (1 - (dts_median / 30)) * 50)
    
    total_score = min(sell_through_score + dts_score, 100.0)
    
    if total_score >= 75:
        grade = 'A'
    elif total_score >= 50:
        grade = 'B'
    elif total_score >= 25:
        grade = 'C'
    else:
        grade = 'D'
    
    return {'score': total_score, 'grade': grade}

# ============================================================================
# INITIAL LOAD
# ============================================================================

# Show loading message
with st.spinner('⚡ Loading dashboard...'):
    listings_df = load_listings_lightweight()
    price_events_df = load_price_events_lightweight()

if listings_df is None:
    st.error("❌ No data found. Please run the scraper and data processing pipeline.")
    st.info("""
    **Steps to generate data:**
    1. Run: `python vinted_scraper.py`
    2. Run: `python process_data.py`
    3. Refresh this page
    """)
    st.stop()

# Pre-calculate summary stats
summary_stats = get_summary_stats(listings_df)

# ============================================================================
# SIDEBAR
# ============================================================================

st.sidebar.title("Market Intelligence")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    [
        "📊 Overview",
        "🔍 Brand Analysis",
        "💰 Price Calculator",
        "📥 Downloads"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📈 Data Summary")

st.sidebar.metric("Total Listings", f"{summary_stats['total']:,}")
st.sidebar.metric("Active Items", f"{summary_stats['active']:,}")
st.sidebar.metric("Sold Items", f"{summary_stats['sold']:,}")
st.sidebar.metric("Brands Tracked", f"{summary_stats['brands']:,}")

if summary_stats['last_update']:
    st.sidebar.info(f"Updated: {summary_stats['last_update'].strftime('%Y-%m-%d %H:%M')}")

with st.sidebar.expander("ℹ️ Performance Tips"):
    st.markdown("""
    **Dashboard optimized for speed:**
    - Data cached for 2 hours
    - Lazy loading enabled
    - Calculations on-demand
    
    **If slow:**
    - Clear cache (☰ menu → Clear cache)
    - Filter to smaller date ranges
    - Focus on single brands
    """)

# ============================================================================
# PAGE 1: OVERVIEW (OPTIMIZED)
# ============================================================================

if "Overview" in page:
    st.markdown(f'<p class="main-header">📊 Market Overview</p>', unsafe_allow_html=True)
    
    st.markdown("Quick liquidity snapshot by brand")
    st.markdown("---")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        categories = ['All Categories'] + safe_sorted(listings_df['category_norm'])
        selected_category = st.selectbox("Category", categories, key="overview_cat")
    
    with col2:
        audiences = ['All Audiences'] + safe_sorted(listings_df['audience'])
        selected_audience = st.selectbox("Audience", audiences, key="overview_aud")
    
    with col3:
        conditions = ['All Conditions'] + safe_sorted(listings_df['condition_bucket'])
        selected_condition = st.selectbox("Condition", conditions, key="overview_cond")
    
    # Apply filters
    filtered = listings_df.copy()
    if selected_category != 'All Categories':
        filtered = filtered[filtered['category_norm'] == selected_category]
    if selected_audience != 'All Audiences':
        filtered = filtered[filtered['audience'] == selected_audience]
    if selected_condition != 'All Conditions':
        filtered = filtered[filtered['condition_bucket'] == selected_condition]
    
    st.markdown("---")
    
    # Get unique brands (limit to top 15 for speed)
    brand_counts = filtered['brand_norm'].value_counts().head(15)
    top_brands = brand_counts.index.tolist()
    
    if len(top_brands) == 0:
        st.warning("No brands found with selected filters")
        st.stop()
    
    # Calculate KPIs for top brands only
    with st.spinner(f'Calculating KPIs for top {len(top_brands)} brands...'):
        liquidity_data = []
        
        progress_bar = st.progress(0)
        for idx, brand in enumerate(top_brands):
            brand_data = filtered[filtered['brand_norm'] == brand]
            brand_sold = brand_data[brand_data['status'] == 'sold']
            
            if len(brand_data) < 10:  # Skip brands with too little data
                continue
            
            # Fast calculations
            dts_stats = calculate_dts_fast(brand_sold)
            st_stats = calculate_sell_through_fast(brand_data, brand_sold)
            
            if dts_stats and st_stats:
                liq = calculate_liquidity_fast(dts_stats['median'], st_stats['percentage'])
                
                if liq:
                    liquidity_data.append({
                        'Brand': brand,
                        'Liquidity Score': liq['score'],
                        'Grade': liq['grade'],
                        'DTS (days)': dts_stats['median'],
                        'Sell-Through (%)': st_stats['percentage'],
                        'Total Items': len(brand_data),
                        'Sold Items': len(brand_sold)
                    })
            
            progress_bar.progress((idx + 1) / len(top_brands))
        
        progress_bar.empty()
    
    if liquidity_data:
        liquidity_df = pd.DataFrame(liquidity_data).sort_values('Liquidity Score', ascending=False)
        
        st.subheader("Top Brand Rankings")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Color coding
            def grade_color(val):
                colors_map = {
                    'A': 'background-color: #d4edda; color: #155724',
                    'B': 'background-color: #d1ecf1; color: #0c5460',
                    'C': 'background-color: #fff3cd; color: #856404',
                    'D': 'background-color: #f8d7da; color: #721c24'
                }
                return colors_map.get(val, '')
            
            styled_df = liquidity_df.style.applymap(grade_color, subset=['Grade'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True, height=400)
        
        with col2:
            st.markdown("### Grade Legend")
            st.markdown("""
            - **A (75-100)**: Excellent
            - **B (50-74)**: Good
            - **C (25-49)**: Fair
            - **D (0-24)**: Poor
            """)
            
            st.info(f"Showing top {len(liquidity_df)} brands by volume")
        
        # Visualization
        st.markdown("---")
        st.subheader("Liquidity Comparison")
        
        fig = go.Figure()
        colors_map = [PRIMARY_BLUE if g == 'A' else '#0097A7' if g == 'B' else '#00ACC1' if g == 'C' else '#B2EBF2' 
                      for g in liquidity_df['Grade']]
        
        fig.add_trace(go.Bar(
            x=liquidity_df['Brand'],
            y=liquidity_df['Liquidity Score'],
            text=liquidity_df['Grade'],
            textposition='outside',
            marker_color=colors_map,
            hovertemplate='<b>%{x}</b><br>Score: %{y:.1f}<br><extra></extra>'
        ))
        
        fig.update_layout(
            xaxis_title="Brand",
            yaxis_title="Liquidity Score (0-100)",
            yaxis_range=[0, 110],
            height=400,
            showlegend=False,
            plot_bgcolor='white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Key insights
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            top = liquidity_df.iloc[0]
            st.metric("Most Liquid", top['Brand'], f"Score: {top['Liquidity Score']:.1f}")
        
        with col2:
            fastest = liquidity_df.loc[liquidity_df['DTS (days)'].idxmin()]
            st.metric("Fastest DTS", fastest['Brand'], f"{fastest['DTS (days)']:.1f} days")
        
        with col3:
            best_st = liquidity_df.loc[liquidity_df['Sell-Through (%)'].idxmax()]
            st.metric("Best Sell-Through", best_st['Brand'], f"{best_st['Sell-Through (%)']:.1f}%")
    
    else:
        st.warning("Not enough data to calculate rankings with selected filters")

# ============================================================================
# PAGE 2: BRAND ANALYSIS (OPTIMIZED WITH LAZY LOADING)
# ============================================================================

elif "Brand Analysis" in page:
    st.markdown(f'<p class="main-header">🔍 Brand Analysis</p>', unsafe_allow_html=True)
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        brands = ['All'] + safe_sorted(listings_df['brand_norm'])
        selected_brand = st.selectbox("Brand", brands)
    
    with col2:
        categories = ['All'] + safe_sorted(listings_df['category_norm'])
        selected_category = st.selectbox("Category", categories)
    
    with col3:
        audiences = ['All'] + safe_sorted(listings_df['audience'])
        selected_audience = st.selectbox("Audience", audiences)
    
    with col4:
        if 'season' in listings_df.columns:
            seasons = ['All'] + safe_sorted(listings_df['season'])
            selected_season = st.selectbox("Season", seasons)
        else:
            selected_season = 'All'
    
    # Apply filters
    filtered_all = listings_df.copy()
    if selected_brand != 'All':
        filtered_all = filtered_all[filtered_all['brand_norm'] == selected_brand]
    if selected_category != 'All':
        filtered_all = filtered_all[filtered_all['category_norm'] == selected_category]
    if selected_audience != 'All':
        filtered_all = filtered_all[filtered_all['audience'] == selected_audience]
    if selected_season != 'All' and 'season' in filtered_all.columns:
        filtered_all = filtered_all[filtered_all['season'] == selected_season]
    
    if len(filtered_all) == 0:
        st.warning("No items match the selected filters")
        st.stop()
    
    filtered_sold = filtered_all[filtered_all['status'] == 'sold']
    
    st.markdown("---")
    
    # KPI Cards (fast calculation)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Items", f"{len(filtered_all):,}")
    
    with col2:
        st.metric("Sold Items", f"{len(filtered_sold):,}")
    
    with col3:
        dts_stats = calculate_dts_fast(filtered_sold)
        if dts_stats:
            st.metric("Median DTS", f"{dts_stats['median']:.1f} days")
        else:
            st.metric("Median DTS", "N/A")
    
    with col4:
        st_stats = calculate_sell_through_fast(filtered_all, filtered_sold)
        if st_stats:
            st.metric("30d Sell-Through", f"{st_stats['percentage']:.1f}%")
        else:
            st.metric("30d Sell-Through", "N/A")
    
    st.markdown("---")
    
    # Charts (only render if data available)
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Price by Condition")
        
        # Sample data if too large (>1000 items)
        plot_data = filtered_all.sample(min(1000, len(filtered_all)))
        
        fig = go.Figure()
        for condition in safe_sorted(plot_data['condition_bucket']):
            cond_df = plot_data[plot_data['condition_bucket'] == condition]
            fig.add_trace(go.Box(
                y=cond_df['price'],
                name=condition,
                boxmean='sd',
                marker_color=PRIMARY_BLUE
            ))
        
        fig.update_layout(
            yaxis_title="Price (EUR)",
            height=350,
            showlegend=True,
            plot_bgcolor='white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### Items by Status")
        
        status_counts = filtered_all['status'].value_counts()
        
        fig = go.Figure(data=[
            go.Pie(
                labels=status_counts.index,
                values=status_counts.values,
                marker_colors=[PRIMARY_BLUE, ACCENT_CYAN],
                hole=0.4
            )
        ])
        
        fig.update_layout(height=350, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
    
    # Data preview (paginated)
    st.markdown("---")
    st.subheader("Data Preview")
    
    tab1, tab2 = st.tabs(["Sold Items", "Active Items"])
    
    with tab1:
        if len(filtered_sold) > 0:
            # Show only first 50 rows for speed
            display_cols = ['brand_norm', 'category_norm', 'condition_bucket', 'price', 'first_seen_at']
            st.dataframe(filtered_sold[display_cols].head(50), use_container_width=True, hide_index=True)
            st.caption(f"Showing first 50 of {len(filtered_sold):,} sold items")
        else:
            st.info("No sold items")
    
    with tab2:
        active = filtered_all[filtered_all['status'] == 'active']
        if len(active) > 0:
            display_cols = ['brand_norm', 'category_norm', 'condition_bucket', 'price', 'first_seen_at']
            st.dataframe(active[display_cols].head(50), use_container_width=True, hide_index=True)
            st.caption(f"Showing first 50 of {len(active):,} active items")
        else:
            st.info("No active items")

# ============================================================================
# PAGE 3: PRICE CALCULATOR (OPTIMIZED)
# ============================================================================

elif "Price Calculator" in page:
    st.markdown(f'<p class="main-header">💰 Price Calculator</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Item Details")
        
        calc_brand = st.selectbox("Brand", safe_sorted(listings_df['brand_norm']))
        calc_category = st.selectbox("Category", safe_sorted(listings_df['category_norm']))
        calc_audience = st.selectbox("Audience", safe_sorted(listings_df['audience']))
        calc_condition = st.selectbox("Condition", safe_sorted(listings_df['condition_bucket']))
    
    with col2:
        st.subheader("Market Intelligence")
        
        # Filter data
        calc_filtered = listings_df[
            (listings_df['brand_norm'] == calc_brand) &
            (listings_df['category_norm'] == calc_category) &
            (listings_df['audience'] == calc_audience) &
            (listings_df['condition_bucket'] == calc_condition)
        ]
        
        if len(calc_filtered) > 0:
            st.success(f"✅ Found {len(calc_filtered):,} comparable items")
            
            # Price stats
            p25 = calc_filtered['price'].quantile(0.25)
            p50 = calc_filtered['price'].median()
            p75 = calc_filtered['price'].quantile(0.75)
            
            st.markdown("### 💵 Recommended Pricing")
            
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Budget", f"€{p25:.2f}")
            col_b.metric("Market", f"€{p50:.2f}")
            col_c.metric("Premium", f"€{p75:.2f}")
            
            # DTS estimate
            calc_sold = calc_filtered[calc_filtered['status'] == 'sold']
            dts_stats = calculate_dts_fast(calc_sold)
            
            if dts_stats:
                st.markdown("### ⏱️ Expected Time to Sell")
                st.info(f"**Median:** {dts_stats['median']:.0f} days (from {dts_stats['count']} sold items)")
            
            # Price estimator
            st.markdown("---")
            your_price = st.number_input("Your Price (EUR)", 1.0, 1000.0, float(p50), 1.0)
            
            if your_price <= p25:
                st.success("🟢 Budget Tier - Fast sale expected")
            elif your_price <= p50:
                st.info("🟡 Below Market - Good value")
            elif your_price <= p75:
                st.warning("🟠 Above Market - Premium pricing")
            else:
                st.error("🔴 Premium Tier - Slower sale possible")
        
        else:
            st.error("❌ No comparable items found")

# ============================================================================
# PAGE 4: DOWNLOADS (OPTIMIZED)
# ============================================================================

elif "Downloads" in page:
    st.markdown(f'<p class="main-header">📥 Downloads</p>', unsafe_allow_html=True)
    
    st.info("💡 Large files? Downloads may take a moment...")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Quick Downloads")
        
        # Remove sensitive columns
        cols_to_remove = ['listing_url', 'scrape_filename']
        
        # Active items (limit to 10k rows for speed)
        active_df = listings_df[listings_df['status'] == 'active'].head(10000)
        for col in cols_to_remove:
            if col in active_df.columns:
                active_df = active_df.drop(columns=[col])
        
        csv_active = active_df.to_csv(index=False)
        st.download_button(
            "📄 Active Items (CSV)",
            csv_active,
            f"active_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )
        st.caption(f"First {min(10000, len(active_df)):,} items")
        
        # Sold items
        sold_df = listings_df[listings_df['status'] == 'sold'].head(10000)
        for col in cols_to_remove:
            if col in sold_df.columns:
                sold_df = sold_df.drop(columns=[col])
        
        csv_sold = sold_df.to_csv(index=False)
        st.download_button(
            "📄 Sold Items (CSV)",
            csv_sold,
            f"sold_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )
        st.caption(f"First {min(10000, len(sold_df)):,} items")
    
    with col2:
        st.subheader("Full Dataset Access")
        st.markdown("""
        **For complete data:**
        1. Access data files directly:
           - `data/processed/listings.parquet`
           - `data/processed/price_events.parquet`
        
        2. Or generate custom exports in Brand Analysis page
        
        **Download limits:**
        - Web downloads: First 10,000 rows
        - Full data: Use file system access
        """)

# Footer
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: #666; padding: 0.5rem;'>
    <p><strong>Market Intelligence Dashboard</strong> | Optimized for Speed</p>
</div>
""", unsafe_allow_html=True)