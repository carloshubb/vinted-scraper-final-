"""
Market Intelligence Dashboard - MODERN CARD DESIGN
Styled like the client's reference image:
- Gradient card backgrounds
- Rounded corners
- Modern typography
- Clean, minimal design
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
from datetime import datetime
import io
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# CLIENT COLORS
PRIMARY_BLUE = '#006064'
ACCENT_CYAN = '#00FFFF'
GRADIENT_START = '#00838F'
GRADIENT_END = '#006064'

sys.path.append(str(Path(__file__).parent))

from calculate_kpis import (
    calculate_all_kpis,
    load_all_data,
)

st.set_page_config(
    page_title="Market Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# MODERN CARD DESIGN CSS
st.markdown(f"""
<style>
    /* Main header styling */
    .main-header {{
        font-size: 2.5rem;
        font-weight: 700;
        color: {PRIMARY_BLUE};
        margin-bottom: 1rem;
        letter-spacing: -0.5px;
    }}
    
    /* Modern card styling */
    .modern-card {{
        background: linear-gradient(135deg, {GRADIENT_START} 0%, {GRADIENT_END} 100%);
        border-radius: 16px;
        padding: 1.5rem;
        color: white;
        box-shadow: 0 4px 12px rgba(0, 96, 100, 0.15);
        margin-bottom: 1rem;
        transition: transform 0.2s;
    }}
    
    .modern-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 96, 100, 0.25);
    }}
    
    .card-title {{
        font-size: 0.9rem;
        font-weight: 500;
        opacity: 0.9;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    
    .card-value {{
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
        line-height: 1;
    }}
    
    .card-subtitle {{
        font-size: 0.85rem;
        opacity: 0.8;
    }}
    
    /* Progress bar styling */
    .progress-container {{
        background: rgba(255, 255, 255, 0.2);
        border-radius: 12px;
        height: 12px;
        margin: 0.75rem 0;
        overflow: hidden;
    }}
    
    .progress-bar {{
        background: linear-gradient(90deg, {ACCENT_CYAN} 0%, rgba(255, 255, 255, 0.9) 100%);
        height: 100%;
        border-radius: 12px;
        transition: width 0.5s ease;
    }}
    
    /* Metric card */
    .metric-card {{
        background: white;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        border-left: 4px solid {PRIMARY_BLUE};
        margin-bottom: 1rem;
    }}
    
    .metric-label {{
        font-size: 0.85rem;
        color: #666;
        font-weight: 500;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }}
    
    .metric-value {{
        font-size: 2rem;
        font-weight: 700;
        color: {PRIMARY_BLUE};
        margin-bottom: 0.25rem;
    }}
    
    .metric-delta {{
        font-size: 0.85rem;
        color: #888;
    }}
    
    /* Ranking bar */
    .ranking-bar {{
        background: #f0f4f8;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: all 0.2s;
    }}
    
    .ranking-bar:hover {{
        background: #e6f0f5;
        transform: translateX(4px);
    }}
    
    .ranking-brand {{
        font-weight: 600;
        color: {PRIMARY_BLUE};
    }}
    
    .ranking-score {{
        font-weight: 700;
        font-size: 1.1rem;
        color: {PRIMARY_BLUE};
    }}
    
    /* Grade badge */
    .grade-badge {{
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
    }}
    
    .grade-A {{ background: #d4edda; color: #155724; }}
    .grade-B {{ background: #d1ecf1; color: #0c5460; }}
    .grade-C {{ background: #fff3cd; color: #856404; }}
    .grade-D {{ background: #f8d7da; color: #721c24; }}
    
    /* Remove default streamlit metric styling */
    [data-testid="stMetricValue"] {{
        font-size: 2rem;
        color: {PRIMARY_BLUE};
    }}
    
    /* Sidebar styling */
    .css-1d391kg {{
        background: linear-gradient(180deg, #f8fafb 0%, #ffffff 100%);
    }}
    
    /* Button styling */
    .stButton>button {{
        background: linear-gradient(135deg, {GRADIENT_START} 0%, {GRADIENT_END} 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        font-weight: 600;
        transition: all 0.2s;
    }}
    
    .stButton>button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 96, 100, 0.3);
    }}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def load_dashboard_data():
    try:
        listings_df, price_events_df, sold_events_df = load_all_data()
        return listings_df, price_events_df, sold_events_df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None, None

listings_df, price_events_df, sold_events_df = load_dashboard_data()

if listings_df is None:
    st.stop()

# Sidebar with modern cards
st.sidebar.title("📊 Market Intelligence")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    [
        "Overview",
        "Brand·Category Analysis",
        "Price Calculator",
        "Downloads"
    ]
)

st.sidebar.markdown("---")

# Modern data summary cards
active_count = len(listings_df[listings_df['status'] == 'active'])
sold_count = len(listings_df[listings_df['status'] == 'sold'])
total_count = active_count + sold_count

st.sidebar.markdown(f"""
<div class="modern-card">
    <div class="card-title">Total Listings</div>
    <div class="card-value">{total_count:,}</div>
    <div class="card-subtitle">Active + Sold items</div>
    <div class="progress-container">
        <div class="progress-bar" style="width: 100%"></div>
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"""
<div class="modern-card">
    <div class="card-title">Active Items</div>
    <div class="card-value">{active_count:,}</div>
    <div class="card-subtitle">{active_count/total_count*100:.1f}% of total</div>
    <div class="progress-container">
        <div class="progress-bar" style="width: {active_count/total_count*100}%"></div>
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"""
<div class="modern-card">
    <div class="card-title">Sold Items</div>
    <div class="card-value">{sold_count:,}</div>
    <div class="card-subtitle">{sold_count/total_count*100:.1f}% of total</div>
    <div class="progress-container">
        <div class="progress-bar" style="width: {sold_count/total_count*100}%"></div>
    </div>
</div>
""", unsafe_allow_html=True)

if 'scrape_timestamp' in listings_df.columns:
    last_update = pd.to_datetime(listings_df['scrape_timestamp']).max()
    st.sidebar.info(f"📅 Updated: {last_update.strftime('%Y-%m-%d %H:%M')}")

# ============================================================================
# PAGE 1: OVERVIEW WITH MODERN CARDS
# ============================================================================

if "Overview" in page:
    st.markdown('<p class="main-header">Market Overview</p>', unsafe_allow_html=True)
    
    # Top KPIs in modern cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">📊 Total Items</div>
            <div class="metric-value">{total_count:,}</div>
            <div class="metric-delta">In database</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if sold_count > 0:
            avg_dts = 0
            if 'first_seen_at' in listings_df.columns:
                sold_items = listings_df[listings_df['status'] == 'sold'].copy()
                if len(sold_items) > 0:
                    sold_items['dts'] = (
                        pd.to_datetime(sold_items['last_seen_at']) - 
                        pd.to_datetime(sold_items['first_seen_at'])
                    ).dt.total_seconds() / (24 * 3600) + 1
                    avg_dts = sold_items['dts'].median()
            
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">⚡ Median DTS</div>
                <div class="metric-value">{avg_dts:.1f}</div>
                <div class="metric-delta">days to sell</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col3:
        median_price = listings_df['price'].median()
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">💰 Median Price</div>
            <div class="metric-value">€{median_price:.0f}</div>
            <div class="metric-delta">market average</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">🔄 Price Changes</div>
            <div class="metric-value">{len(price_events_df):,}</div>
            <div class="metric-delta">detected</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Filters
    st.subheader("🎯 Filter Rankings")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        categories_filter = ['All Categories'] + sorted(listings_df['category_norm'].unique().tolist())
        selected_category_overview = st.selectbox("Category", categories_filter, key="overview_category")
    
    with col2:
        audiences_filter = ['All Audiences'] + sorted(listings_df['audience'].unique().tolist())
        selected_audience_overview = st.selectbox("Audience", audiences_filter, key="overview_audience")
    
    with col3:
        conditions_filter = ['All Conditions'] + sorted(listings_df['condition_bucket'].unique().tolist())
        selected_condition_overview = st.selectbox("Condition", conditions_filter, key="overview_condition")
    
    category_filter_val = None if selected_category_overview == 'All Categories' else selected_category_overview
    audience_filter_val = None if selected_audience_overview == 'All Audiences' else selected_audience_overview
    condition_filter_val = None if selected_condition_overview == 'All Conditions' else selected_condition_overview
    
    st.markdown("---")
    
    # Calculate liquidity rankings
    filtered_for_condition = listings_df.copy()
    if condition_filter_val:
        filtered_for_condition = filtered_for_condition[filtered_for_condition['condition_bucket'] == condition_filter_val]
    
    brands = sorted(filtered_for_condition['brand_norm'].unique())
    
    liquidity_data = []
    for brand in brands:
        brand_listings = filtered_for_condition[filtered_for_condition['brand_norm'] == brand]
        if category_filter_val:
            brand_listings = brand_listings[brand_listings['category_norm'] == category_filter_val]
        if audience_filter_val:
            brand_listings = brand_listings[brand_listings['audience'] == audience_filter_val]
        
        if len(brand_listings) == 0:
            continue
        
        kpis = calculate_all_kpis(
            brand=brand,
            category=category_filter_val,
            audience=audience_filter_val
        )
        
        if kpis['liquidity'] and kpis['dts'] and kpis['sell_through_30d']:
            liquidity_data.append({
                'Brand': brand,
                'Score': kpis['liquidity']['score'],
                'Grade': kpis['liquidity']['grade'],
                'DTS': kpis['dts']['median'],
                'ST': kpis['sell_through_30d']['percentage']
            })
    
    if liquidity_data:
        liquidity_df = pd.DataFrame(liquidity_data).sort_values('Score', ascending=False)
        
        st.subheader("🏆 Brand Liquidity Ranking")
        
        # Modern ranking bars
        for idx, row in liquidity_df.iterrows():
            grade_class = f"grade-{row['Grade']}"
            progress_width = min(row['Score'], 100)
            
            st.markdown(f"""
            <div class="ranking-bar">
                <div style="flex: 1;">
                    <span class="ranking-brand">{row['Brand']}</span>
                    <span class="grade-badge {grade_class}">{row['Grade']}</span>
                </div>
                <div style="flex: 2; padding: 0 1rem;">
                    <div class="progress-container" style="margin: 0;">
                        <div class="progress-bar" style="width: {progress_width}%; background: linear-gradient(90deg, {PRIMARY_BLUE} 0%, {ACCENT_CYAN} 100%);"></div>
                    </div>
                </div>
                <div>
                    <span class="ranking-score">{row['Score']:.1f}</span>
                    <span style="color: #888; font-size: 0.85rem;"> / 100</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Chart
        fig = go.Figure()
        
        colors_map = [PRIMARY_BLUE if g == 'A' else '#0097A7' if g == 'B' else '#00ACC1' if g == 'C' else '#B2EBF2' 
                      for g in liquidity_df['Grade']]
        
        fig.add_trace(go.Bar(
            x=liquidity_df['Brand'],
            y=liquidity_df['Score'],
            text=liquidity_df['Grade'],
            textposition='outside',
            marker_color=colors_map,
            marker_line_color=PRIMARY_BLUE,
            marker_line_width=2,
            hovertemplate='<b>%{x}</b><br>Score: %{y:.1f}<br><extra></extra>'
        ))
        
        fig.update_layout(
            title="Liquidity Score Comparison",
            xaxis_title="Brand",
            yaxis_title="Liquidity Score (0-100)",
            yaxis_range=[0, 110],
            height=400,
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(family="Arial, sans-serif")
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Key insights in modern cards
        st.subheader("💡 Key Insights")
        
        col1, col2, col3 = st.columns(3)
        
        top_brand = liquidity_df.iloc[0]
        fastest = liquidity_df.loc[liquidity_df['DTS'].idxmin()]
        best_st = liquidity_df.loc[liquidity_df['ST'].idxmax()]
        
        with col1:
            st.markdown(f"""
            <div class="modern-card">
                <div class="card-title">🥇 Most Liquid</div>
                <div class="card-value">{top_brand['Brand']}</div>
                <div class="card-subtitle">Score: {top_brand['Score']:.1f}/100</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="modern-card">
                <div class="card-title">⚡ Fastest DTS</div>
                <div class="card-value">{fastest['Brand']}</div>
                <div class="card-subtitle">{fastest['DTS']:.1f} days average</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="modern-card">
                <div class="card-title">📈 Best Sell-Through</div>
                <div class="card-value">{best_st['Brand']}</div>
                <div class="card-subtitle">{best_st['ST']:.1f}% in 30 days</div>
            </div>
            """, unsafe_allow_html=True)
    
    else:
        st.warning("⚠️ Not enough data with selected filters")

# ============================================================================
# PAGE 2: BRAND·CATEGORY ANALYSIS
# ============================================================================

elif "Brand·Category Analysis" in page:
    st.markdown('<p class="main-header">Brand·Category Analysis</p>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        brands = ['All'] + sorted(listings_df['brand_norm'].unique().tolist())
        selected_brand = st.selectbox("Brand", brands)
    
    with col2:
        categories = ['All'] + sorted(listings_df['category_norm'].unique().tolist())
        selected_category = st.selectbox("Category", categories)
    
    with col3:
        audiences = ['All'] + sorted(listings_df['audience'].unique().tolist())
        selected_audience = st.selectbox("Audience", audiences)
    
    with col4:
        if 'season' in listings_df.columns:
            seasons = ['All'] + sorted(listings_df['season'].dropna().unique().tolist())
            selected_season = st.selectbox("Season", seasons)
        else:
            selected_season = None
    
    brand_filter = None if selected_brand == 'All' else selected_brand
    category_filter = None if selected_category == 'All' else selected_category
    audience_filter = None if selected_audience == 'All' else selected_audience
    season_filter = None if selected_season == 'All' else selected_season
    
    st.markdown("---")
    
    # Filter data
    filtered_all = listings_df.copy()
    
    if brand_filter:
        filtered_all = filtered_all[filtered_all['brand_norm'] == brand_filter]
    if category_filter:
        filtered_all = filtered_all[filtered_all['category_norm'] == category_filter]
    if audience_filter:
        filtered_all = filtered_all[filtered_all['audience'] == audience_filter]
    if season_filter and 'season' in filtered_all.columns:
        filtered_all = filtered_all[filtered_all['season'] == season_filter]
    
    if len(filtered_all) == 0:
        st.warning("⚠️ No items match the selected filters")
        st.stop()
    
    filtered_sold = filtered_all[filtered_all['status'] == 'sold'].copy()
    
    # Modern KPI cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">📊 Total Items</div>
            <div class="metric-value">{len(filtered_all):,}</div>
            <div class="metric-delta">Active + Sold</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">✅ Sold Items</div>
            <div class="metric-value">{len(filtered_sold):,}</div>
            <div class="metric-delta">{len(filtered_sold)/len(filtered_all)*100:.1f}% of total</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        if len(filtered_sold) > 0 and 'first_seen_at' in filtered_sold.columns:
            filtered_sold['dts_calc'] = (
                pd.to_datetime(filtered_sold['last_seen_at']) - 
                pd.to_datetime(filtered_sold['first_seen_at'])
            ).dt.total_seconds() / (24 * 3600) + 1
            median_dts = filtered_sold['dts_calc'].median()
            
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">⏱️ Median DTS</div>
                <div class="metric-value">{median_dts:.1f}</div>
                <div class="metric-delta">days to sell</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-label">⏱️ Median DTS</div>
                <div class="metric-value">N/A</div>
                <div class="metric-delta">No sold items</div>
            </div>
            """, unsafe_allow_html=True)
    
    with col4:
        if len(filtered_sold) > 0 and 'dts_calc' in filtered_sold.columns:
            sold_30d = len(filtered_sold[filtered_sold['dts_calc'] <= 30])
            st_rate = (sold_30d / len(filtered_all)) * 100
            
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">📈 30d Sell-Through</div>
                <div class="metric-value">{st_rate:.1f}%</div>
                <div class="metric-delta">{sold_30d}/{len(filtered_all)} items</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-label">📈 30d Sell-Through</div>
                <div class="metric-value">0.0%</div>
                <div class="metric-delta">No sales yet</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Charts
    st.subheader("📈 Analysis by Condition")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Price Distribution")
        
        fig = go.Figure()
        
        for condition in sorted(filtered_all['condition_bucket'].unique()):
            cond_df = filtered_all[filtered_all['condition_bucket'] == condition]
            if len(cond_df) > 0:
                fig.add_trace(go.Box(
                    y=cond_df['price'],
                    name=condition,
                    boxmean='sd',
                    marker_color=PRIMARY_BLUE,
                    line=dict(color=PRIMARY_BLUE)
                ))
        
        fig.update_layout(
            yaxis_title="Price (EUR)",
            height=400,
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### Items by Condition & Status")
        
        condition_counts = filtered_all.groupby(['condition_bucket', 'status']).size().reset_index(name='count')
        
        fig = go.Figure()
        
        for status in ['active', 'sold']:
            status_data = condition_counts[condition_counts['status'] == status]
            fig.add_trace(go.Bar(
                x=status_data['condition_bucket'],
                y=status_data['count'],
                name=status.capitalize(),
                marker_color=PRIMARY_BLUE if status == 'active' else ACCENT_CYAN
            ))
        
        fig.update_layout(
            yaxis_title="Count",
            height=400,
            barmode='stack',
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # PDF button
    st.markdown("---")
    if st.button("📄 Generate PDF Report", type="primary"):
        with st.spinner("Generating PDF..."):
            try:
                pdf_buffer = generate_enhanced_pdf(
                    filtered_all, filtered_sold,
                    brand_filter, category_filter, audience_filter, season_filter
                )
                
                filename = f"market_analysis_{datetime.now().strftime('%Y%m%d')}.pdf"
                
                st.download_button(
                    label="📥 Download PDF",
                    data=pdf_buffer,
                    file_name=filename,
                    mime="application/pdf"
                )
                st.success(f"✅ Generated: {filename}")
                
            except Exception as e:
                st.error(f"❌ Error: {e}")

# ============================================================================
# PAGE 3: PRICE CALCULATOR
# ============================================================================

elif "Price Calculator" in page:
    st.markdown('<p class="main-header">💰 Smart Price Calculator</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("🏷️ Item Details")
        
        calc_brand = st.selectbox("Brand", sorted(listings_df['brand_norm'].unique()), key="calc_brand")
        calc_category = st.selectbox("Category", sorted(listings_df['category_norm'].unique()), key="calc_category")
        calc_audience = st.selectbox("Audience", sorted(listings_df['audience'].unique()), key="calc_audience")
        calc_condition = st.selectbox("Condition", sorted(listings_df['condition_bucket'].unique()), key="calc_condition")
    
    with col2:
        st.subheader("📊 Market Intelligence")
        
        calc_filtered = listings_df[
            (listings_df['brand_norm'] == calc_brand) &
            (listings_df['category_norm'] == calc_category) &
            (listings_df['audience'] == calc_audience) &
            (listings_df['condition_bucket'] == calc_condition)
        ]
        
        if len(calc_filtered) > 0:
            p25 = calc_filtered['price'].quantile(0.25)
            p50 = calc_filtered['price'].median()
            p75 = calc_filtered['price'].quantile(0.75)
            
            st.markdown("### 💵 Recommended Price Range")
            
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                st.markdown(f"""
                <div class="modern-card" style="background: linear-gradient(135deg, #43A047 0%, #2E7D32 100%);">
                    <div class="card-title">Budget</div>
                    <div class="card-value">€{p25:.2f}</div>
                    <div class="card-subtitle">P25 - Quick sale</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_b:
                st.markdown(f"""
                <div class="modern-card">
                    <div class="card-title">Market</div>
                    <div class="card-value">€{p50:.2f}</div>
                    <div class="card-subtitle">Median - Recommended</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_c:
                st.markdown(f"""
                <div class="modern-card" style="background: linear-gradient(135deg, #FB8C00 0%, #EF6C00 100%);">
                    <div class="card-title">Premium</div>
                    <div class="card-value">€{p75:.2f}</div>
                    <div class="card-subtitle">P75 - Top tier</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("### 🎯 Your Price Estimator")
            
            your_price = st.number_input(
                "Your asking price (EUR)",
                min_value=1.0,
                max_value=1000.0,
                value=float(p50),
                step=1.0
            )
            
            # Price positioning with modern card
            if your_price <= p25:
                position = "Budget Tier"
                emoji = "🟢"
                desc = "Bottom 25% - Fast sale expected"
                gradient = "linear-gradient(135deg, #43A047 0%, #2E7D32 100%)"
            elif your_price <= p50:
                position = "Below Market"
                emoji = "🟡"
                desc = "25-50% range - Good value"
                gradient = "linear-gradient(135deg, #FDD835 0%, #F9A825 100%)"
            elif your_price <= p75:
                position = "Above Market"
                emoji = "🟠"
                desc = "50-75% range - Premium pricing"
                gradient = "linear-gradient(135deg, #FB8C00 0%, #EF6C00 100%)"
            else:
                position = "Premium Tier"
                emoji = "🔴"
                desc = "Top 25% - Slower sale possible"
                gradient = "linear-gradient(135deg, #E53935 0%, #C62828 100%)"
            
            st.markdown(f"""
            <div class="modern-card" style="background: {gradient};">
                <div class="card-title">{emoji} Price Positioning</div>
                <div class="card-value">{position}</div>
                <div class="card-subtitle">{desc}</div>
                <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid rgba(255,255,255,0.3);">
                    <div style="display: flex; justify-content: space-between; font-size: 0.9rem;">
                        <span>Your price: <strong>€{your_price:.2f}</strong></span>
                        <span>Market: <strong>€{p50:.2f}</strong></span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # DTS estimation
            calc_sold = calc_filtered[calc_filtered['status'] == 'sold']
            
            if len(calc_sold) > 0 and 'first_seen_at' in calc_sold.columns:
                calc_sold['dts_calc'] = (
                    pd.to_datetime(calc_sold['last_seen_at']) - 
                    pd.to_datetime(calc_sold['first_seen_at'])
                ).dt.total_seconds() / (24 * 3600) + 1
                
                dts_p25 = calc_sold['dts_calc'].quantile(0.25)
                dts_median = calc_sold['dts_calc'].median()
                dts_p75 = calc_sold['dts_calc'].quantile(0.75)
                
                if your_price <= p25:
                    estimated_dts = dts_p25
                    speed_emoji = "⚡"
                    speed_label = "Fast"
                elif your_price <= p50:
                    estimated_dts = dts_median
                    speed_emoji = "✅"
                    speed_label = "Average"
                elif your_price <= p75:
                    estimated_dts = dts_p75
                    speed_emoji = "⏳"
                    speed_label = "Slower"
                else:
                    estimated_dts = dts_p75 * 1.3
                    speed_emoji = "🐌"
                    speed_label = "Slow"
                
                st.markdown(f"""
                <div class="modern-card">
                    <div class="card-title">⏰ Estimated Time to Sell</div>
                    <div class="card-value">{estimated_dts:.0f} days</div>
                    <div class="card-subtitle">{speed_emoji} {speed_label} expected</div>
                    <div style="margin-top: 1rem; font-size: 0.85rem; opacity: 0.9;">
                        Based on {len(calc_sold)} comparable sold items
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        else:
            st.error("❌ No comparable items found")

# ============================================================================
# PAGE 4: DOWNLOADS
# ============================================================================

elif "Downloads" in page:
    st.markdown('<p class="main-header">📥 Downloads</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 CSV Exports")
        
        active_df = listings_df[listings_df['status'] == 'active']
        csv_active = active_df.to_csv(index=False)
        st.download_button(
            "📄 Download Active Items",
            csv_active,
            f"active_listings_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            use_container_width=True
        )
        st.info(f"📦 {len(active_df):,} items")
        
        sold_df = listings_df[listings_df['status'] == 'sold']
        if len(sold_df) > 0:
            csv_sold = sold_df.to_csv(index=False)
            st.download_button(
                "📄 Download Sold Items",
                csv_sold,
                f"sold_listings_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv",
                use_container_width=True
            )
            st.info(f"📦 {len(sold_df):,} items")
        
        if len(price_events_df) > 0:
            csv_prices = price_events_df.to_csv(index=False)
            st.download_button(
                "📄 Download Price Changes",
                csv_prices,
                f"price_changes_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv",
                use_container_width=True
            )
            st.info(f"📦 {len(price_events_df):,} events")
    
    with col2:
        st.subheader("📄 PDF Reports")
        
        st.markdown("""
        <div class="metric-card">
            <div class="metric-label">💡 How to Generate PDFs</div>
            <div style="margin-top: 0.5rem; font-size: 0.95rem; color: #666;">
                1. Go to <strong>Brand·Category Analysis</strong><br/>
                2. Apply your desired filters<br/>
                3. Click <strong>"Generate PDF Report"</strong><br/>
                4. Download your custom report
            </div>
        </div>
        """, unsafe_allow_html=True)


# ============================================================================
# PDF GENERATION FUNCTION
# ============================================================================

def generate_enhanced_pdf(filtered_all, filtered_sold, brand, category, audience, season):
    """Generate PDF with comprehensive statistics"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(letter), 
        topMargin=0.5*inch, 
        bottomMargin=0.5*inch,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor(PRIMARY_BLUE),
        alignment=TA_CENTER,
        spaceAfter=12
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor(PRIMARY_BLUE),
        spaceAfter=8,
        spaceBefore=12
    )
    
    # Title
    filter_parts = [f for f in [brand, category, audience, season] if f]
    title_text = f"Market Analysis Report - {' · '.join(filter_parts)}" if filter_parts else "Market Analysis Report"
    
    story.append(Paragraph(title_text, title_style))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Comprehensive Market Intelligence", 
        styles['Normal']
    ))
    story.append(Spacer(1, 0.2*inch))
    
    # Summary KPIs
    story.append(Paragraph("Executive Summary", heading_style))
    
    summary_data = [
        ['Metric', 'Value'],
        ['Total Items Analyzed', f"{len(filtered_all):,}"],
        ['Active Listings', f"{len(filtered_all[filtered_all['status']=='active']):,}"],
        ['Sold Items', f"{len(filtered_sold):,}"],
    ]
    
    if len(filtered_sold) > 0 and 'first_seen_at' in filtered_sold.columns:
        filtered_sold_calc = filtered_sold.copy()
        filtered_sold_calc['dts'] = (
            pd.to_datetime(filtered_sold_calc['last_seen_at']) - 
            pd.to_datetime(filtered_sold_calc['first_seen_at'])
        ).dt.total_seconds() / (24 * 3600) + 1
        
        summary_data.append(['Median DTS', f"{filtered_sold_calc['dts'].median():.1f} days"])
        summary_data.append(['Mean DTS', f"{filtered_sold_calc['dts'].mean():.1f} days"])
        
        sold_30d = len(filtered_sold_calc[filtered_sold_calc['dts'] <= 30])
        st_rate = (sold_30d / len(filtered_all)) * 100
        summary_data.append(['30d Sell-Through Rate', f"{st_rate:.1f}%"])
        summary_data.append(['Items Sold ≤30 Days', f"{sold_30d:,}"])
    
    if len(filtered_all) > 0:
        summary_data.append(['Median Price', f"EUR {filtered_all['price'].median():.2f}"])
        summary_data.append(['Price Range', f"EUR {filtered_all['price'].min():.2f} - EUR {filtered_all['price'].max():.2f}"])
    
    summary_table = Table(summary_data, colWidths=[3.5*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(PRIMARY_BLUE)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Condition breakdown
    story.append(Paragraph("Breakdown by Condition", heading_style))
    
    condition_data = [['Condition', 'Total Items', 'Active', 'Sold', 'Sell-Through %', 'Median Price']]
    
    for condition in sorted(filtered_all['condition_bucket'].unique()):
        cond_all = filtered_all[filtered_all['condition_bucket'] == condition]
        cond_sold = filtered_sold[filtered_sold['condition_bucket'] == condition] if len(filtered_sold) > 0 else pd.DataFrame()
        cond_active = cond_all[cond_all['status'] == 'active']
        
        st_rate = (len(cond_sold) / len(cond_all)) * 100 if len(cond_all) > 0 else 0
        median_price = cond_all['price'].median() if len(cond_all) > 0 else 0
        
        condition_data.append([
            condition,
            f"{len(cond_all):,}",
            f"{len(cond_active):,}",
            f"{len(cond_sold):,}",
            f"{st_rate:.1f}%",
            f"EUR {median_price:.2f}"
        ])
    
    cond_table = Table(condition_data, colWidths=[2*inch, 1.3*inch, 1.3*inch, 1.3*inch, 1.3*inch, 1.3*inch])
    cond_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(PRIMARY_BLUE)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    
    story.append(cond_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Price statistics
    story.append(Paragraph("Price Statistics by Condition", heading_style))
    
    price_data = [['Condition', 'Min', 'P25', 'Median', 'P75', 'Max']]
    
    for condition in sorted(filtered_all['condition_bucket'].unique()):
        cond_all = filtered_all[filtered_all['condition_bucket'] == condition]
        if len(cond_all) > 0:
            price_data.append([
                condition,
                f"EUR {cond_all['price'].min():.2f}",
                f"EUR {cond_all['price'].quantile(0.25):.2f}",
                f"EUR {cond_all['price'].median():.2f}",
                f"EUR {cond_all['price'].quantile(0.75):.2f}",
                f"EUR {cond_all['price'].max():.2f}"
            ])
    
    price_table = Table(price_data, colWidths=[2*inch, 1.3*inch, 1.3*inch, 1.3*inch, 1.3*inch, 1.3*inch])
    price_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    
    story.append(price_table)
    
    # Footer
    story.append(Spacer(1, 0.3*inch))
    footer_text = f"Report generated from Market Intelligence Dashboard | {len(filtered_all):,} items analyzed"
    story.append(Paragraph(footer_text, styles['Italic']))
    
    # Methodology
    story.append(Spacer(1, 0.2*inch))
    methodology = """
    <b>Calculation Methodology:</b><br/>
    • <b>DTS</b>: (last_seen_at + 24h) - first_seen_at<br/>
    • <b>Sell-Through</b>: (Sold ≤30d / Total items) × 100<br/>
    • <b>Confidence</b>: Items missing ≥48h
    """
    story.append(Paragraph(methodology, styles['Normal']))
    
    try:
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        error_buffer = io.BytesIO()
        error_doc = SimpleDocTemplate(error_buffer, pagesize=letter)
        error_story = [
            Paragraph("PDF Generation Error", title_style),
            Spacer(1, 0.2*inch),
            Paragraph(f"Error: {str(e)}", styles['Normal'])
        ]
        error_doc.build(error_story)
        error_buffer.seek(0)
        return error_buffer


# Footer
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: #888; padding: 1rem;'>
    <p style='font-weight: 600; color: {PRIMARY_BLUE};'>Market Intelligence Dashboard</p>
    <p style='font-size: 0.85rem;'>{datetime.now().strftime('%Y-%m-%d %H:%M')} | Data source: Marketplace scraping engine</p>
</div>
""", unsafe_allow_html=True)