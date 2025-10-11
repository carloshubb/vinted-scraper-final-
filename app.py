"""
Vinted Market Intelligence Dashboard
Streamlit application with 4 pages: Overview, Brand Analysis, Calculator, Downloads
FIXED: Added PDF export functionality
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
from datetime import datetime
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from calculate_kpis import (
    calculate_all_kpis,
    load_all_data,
    calculate_liquidity_score
)

# Page configuration
st.set_page_config(
    page_title="Vinted Market Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .liquidity-a { color: #28a745; font-weight: bold; }
    .liquidity-b { color: #17a2b8; font-weight: bold; }
    .liquidity-c { color: #ffc107; font-weight: bold; }
    .liquidity-d { color: #dc3545; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Load data function with caching
@st.cache_data(ttl=3600)
def load_dashboard_data():
    """Load all data for dashboard."""
    try:
        listings_df, price_events_df, sold_events_df = load_all_data()
        return listings_df, price_events_df, sold_events_df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.info("Please run the data pipeline first: `python run_pipeline.py`")
        return None, None, None

# PDF Generation Function
def generate_pdf_report(listings_df, sold_events_df):
    """Generate 1-page PDF summary report."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    story.append(Paragraph("Vinted Market Intelligence Report", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Summary Stats Table
    summary_data = [
        ['Metric', 'Value'],
        ['Total Listings', f"{len(listings_df):,}"],
        ['Active Items', f"{len(listings_df[listings_df['status'] == 'active']):,}"],
        ['Sold Items', f"{len(sold_events_df):,}"],
        ['Avg Price', f"€{listings_df['price'].mean():.2f}"],
        ['Median Price', f"€{listings_df['price'].median():.2f}"],
    ]
    
    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Brand KPIs Table
    story.append(Paragraph("Brand Performance Summary", styles['Heading2']))
    story.append(Spacer(1, 0.1*inch))
    
    brand_data = [['Brand', 'Active', 'Sold', 'Median DTS', 'Sell-Through', 'Liquidity']]
    
    for brand in sorted(listings_df['brand_norm'].unique()):
        kpis = calculate_all_kpis(brand=brand)
        active_count = len(listings_df[(listings_df['brand_norm'] == brand) & (listings_df['status'] == 'active')])
        sold_count = len(sold_events_df[sold_events_df['brand'] == brand]) if len(sold_events_df) > 0 else 0
        
        dts = f"{kpis['dts']['median']:.1f}d" if kpis['dts'] else "N/A"
        st_rate = f"{kpis['sell_through_30d']['percentage']:.1f}%" if kpis['sell_through_30d'] else "N/A"
        liq_score = f"{kpis['liquidity']['score']:.0f} ({kpis['liquidity']['grade']})" if kpis['liquidity'] else "N/A"
        
        brand_data.append([brand, str(active_count), str(sold_count), dts, st_rate, liq_score])
    
    brand_table = Table(brand_data, colWidths=[1.2*inch, 0.8*inch, 0.8*inch, 1*inch, 1*inch, 1.2*inch])
    brand_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(brand_table)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

# Load data
listings_df, price_events_df, sold_events_df = load_dashboard_data()

if listings_df is None:
    st.stop()

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Select Page",
    ["Overview", "Brand·Category Analysis", "Price Calculator", "Downloads"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Data Summary")
st.sidebar.metric("Total Listings", f"{len(listings_df):,}")
st.sidebar.metric("Active Items", f"{len(listings_df[listings_df['status'] == 'active']):,}")
st.sidebar.metric("Sold Items", f"{len(sold_events_df):,}")
st.sidebar.metric("Price Changes", f"{len(price_events_df):,}")

# Get last update time
if 'scrape_timestamp' in listings_df.columns:
    last_update = pd.to_datetime(listings_df['scrape_timestamp']).max()
    st.sidebar.info(f"Last updated: {last_update.strftime('%Y-%m-%d %H:%M')}")

# ============================================================================
# PAGE 1: OVERVIEW - LIQUIDITY RANKING
# ============================================================================

if page == "Overview":
    st.markdown('<p class="main-header">Market Overview - Liquidity Ranking</p>', unsafe_allow_html=True)
    
    st.markdown("""
    This dashboard provides market intelligence for the Vinted Spain secondary fashion market.
    The **Liquidity Score** indicates how quickly items convert to sales (0-100 scale).
    """)
    
    st.markdown("---")
    
    # Calculate liquidity for each brand
    brands = sorted(listings_df['brand_norm'].unique())
    
    liquidity_data = []
    for brand in brands:
        kpis = calculate_all_kpis(brand=brand)
        
        if kpis['liquidity'] and kpis['dts'] and kpis['sell_through_30d']:
            liquidity_data.append({
                'Brand': brand,
                'Liquidity Score': kpis['liquidity']['score'],
                'Grade': kpis['liquidity']['grade'],
                'DTS (days)': kpis['dts']['median'],
                'Sell-Through 30d (%)': kpis['sell_through_30d']['percentage'],
                'Active Items': len(listings_df[(listings_df['brand_norm'] == brand) & (listings_df['status'] == 'active')]),
                'Sold Items': kpis['sell_through_30d']['total_sold']
            })
    
    if liquidity_data:
        liquidity_df = pd.DataFrame(liquidity_data).sort_values('Liquidity Score', ascending=False)
        
        # Display as table with color coding
        st.subheader("Brand Liquidity Ranking")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Create styled table
            def grade_color(val):
                if val == 'A':
                    return 'background-color: #d4edda; color: #155724'
                elif val == 'B':
                    return 'background-color: #d1ecf1; color: #0c5460'
                elif val == 'C':
                    return 'background-color: #fff3cd; color: #856404'
                else:
                    return 'background-color: #f8d7da; color: #721c24'
            
            styled_df = liquidity_df.style.applymap(grade_color, subset=['Grade'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("### Grade Legend")
            st.markdown("""
            - **A (75-100)**: Excellent liquidity
            - **B (50-74)**: Good liquidity
            - **C (25-49)**: Fair liquidity
            - **D (0-24)**: Poor liquidity
            
            **Metrics:**
            - **DTS**: Days to Sell (median)
            - **Sell-Through**: % sold in 30 days
            """)
        
        # Visualization
        st.markdown("---")
        st.subheader("Liquidity Score Comparison")
        
        fig = go.Figure()
        
        colors_map = ['#28a745' if g == 'A' else '#17a2b8' if g == 'B' else '#ffc107' if g == 'C' else '#dc3545' 
                  for g in liquidity_df['Grade']]
        
        fig.add_trace(go.Bar(
            x=liquidity_df['Brand'],
            y=liquidity_df['Liquidity Score'],
            text=liquidity_df['Grade'],
            textposition='outside',
            marker_color=colors_map,
            hovertemplate='<b>%{x}</b><br>Score: %{y:.1f}<br>Grade: %{text}<extra></extra>'
        ))
        
        fig.update_layout(
            title="Brand Liquidity Scores",
            xaxis_title="Brand",
            yaxis_title="Liquidity Score (0-100)",
            yaxis_range=[0, 100],
            height=400,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Key insights
        st.markdown("---")
        st.subheader("Key Insights")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            top_brand = liquidity_df.iloc[0]
            st.metric(
                "Most Liquid Brand",
                top_brand['Brand'],
                f"Score: {top_brand['Liquidity Score']:.1f}"
            )
        
        with col2:
            fastest_dts = liquidity_df.loc[liquidity_df['DTS (days)'].idxmin()]
            st.metric(
                "Fastest Selling",
                fastest_dts['Brand'],
                f"{fastest_dts['DTS (days)']:.1f} days"
            )
        
        with col3:
            best_sellthrough = liquidity_df.loc[liquidity_df['Sell-Through 30d (%)'].idxmax()]
            st.metric(
                "Best Sell-Through",
                best_sellthrough['Brand'],
                f"{best_sellthrough['Sell-Through 30d (%)']:.1f}%"
            )
    
    else:
        st.warning("Not enough data to calculate liquidity scores. Please run the pipeline at least twice (48 hours apart).")

# ============================================================================
# PAGE 2: BRAND·CATEGORY ANALYSIS
# ============================================================================

elif page == "Brand·Category Analysis":
    st.markdown('<p class="main-header">Brand·Category Deep Dive</p>', unsafe_allow_html=True)
    
    # Filters
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
    
    # Apply filters for KPIs
    brand_filter = None if selected_brand == 'All' else selected_brand
    category_filter = None if selected_category == 'All' else selected_category
    audience_filter = None if selected_audience == 'All' else selected_audience
    season_filter = None if selected_season == 'All' else selected_season
    
    # Calculate KPIs
    kpis = calculate_all_kpis(
        brand=brand_filter,
        category=category_filter,
        audience=audience_filter,
        season=season_filter
    )
    
    st.markdown("---")
    
    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if kpis['dts']:
            st.metric(
                "Days to Sell (Median)",
                f"{kpis['dts']['median']:.1f} days",
                f"Range: {kpis['dts']['p25']:.0f}-{kpis['dts']['p75']:.0f}d"
            )
        else:
            st.metric("Days to Sell", "N/A", "Need sold items")
    
    with col2:
        if kpis['sell_through_30d']:
            st.metric(
                "30-Day Sell-Through",
                f"{kpis['sell_through_30d']['percentage']:.1f}%",
                f"{kpis['sell_through_30d']['sold_30d']} / {kpis['sell_through_30d']['total_sold']}"
            )
        else:
            st.metric("Sell-Through", "N/A", "Need sold items")
    
    with col3:
        if kpis['price_distribution']:
            st.metric(
                "Median Price",
                f"€{kpis['price_distribution']['p50']:.2f}",
                f"Range: €{kpis['price_distribution']['p25']:.0f}-€{kpis['price_distribution']['p75']:.0f}"
            )
        else:
            st.metric("Median Price", "N/A")
    
    with col4:
        if kpis['liquidity']:
            grade_class = f"liquidity-{kpis['liquidity']['grade'].lower()}"
            st.metric(
                "Liquidity Score",
                f"{kpis['liquidity']['score']:.1f}",
                f"Grade: {kpis['liquidity']['grade']}"
            )
        else:
            st.metric("Liquidity", "N/A", "Need sold items")
    
    st.markdown("---")
    
    # Filter data for visualizations
    filtered_df = listings_df.copy()
    if brand_filter:
        filtered_df = filtered_df[filtered_df['brand_norm'] == brand_filter]
    if category_filter:
        filtered_df = filtered_df[filtered_df['category_norm'] == category_filter]
    if audience_filter:
        filtered_df = filtered_df[filtered_df['audience'] == audience_filter]
    if season_filter:
        filtered_df = filtered_df[filtered_df['season'] == season_filter]
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Price Distribution by Status")
        
        if len(filtered_df) > 0:
            # Box plot
            fig = go.Figure()
            
            for status in ['active', 'sold']:
                status_df = filtered_df[filtered_df['status'] == status]
                if len(status_df) > 0:
                    fig.add_trace(go.Box(
                        y=status_df['price'],
                        name=status.capitalize(),
                        boxmean='sd'
                    ))
            
            fig.update_layout(
                yaxis_title="Price (€)",
                height=400,
                showlegend=True
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data matching filters")
    
    with col2:
        st.subheader("Sales Velocity Metrics")
        
        if kpis['dts'] and kpis['sell_through_30d']:
            # Create metrics bar chart
            metrics_data = {
                'Metric': ['DTS (days)', 'Sell-Through (%)'],
                'Value': [kpis['dts']['median'], kpis['sell_through_30d']['percentage']],
                'Benchmark': [14, 50]  # Industry benchmarks
            }
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=metrics_data['Metric'],
                y=metrics_data['Value'],
                name='Actual',
                marker_color='#1f77b4'
            ))
            fig.add_trace(go.Bar(
                x=metrics_data['Metric'],
                y=metrics_data['Benchmark'],
                name='Benchmark',
                marker_color='#ff7f0e'
            ))
            
            fig.update_layout(
                barmode='group',
                height=400,
                yaxis_title="Value"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Need sold items data for sales velocity metrics")
    
    # Price distribution histogram
    st.markdown("---")
    st.subheader("Detailed Price Distribution")
    
    if len(filtered_df) > 0:
        fig = px.histogram(
            filtered_df[filtered_df['price'] > 0],
            x='price',
            nbins=30,
            color='status',
            title="Price Distribution Histogram",
            labels={'price': 'Price (€)', 'count': 'Number of Items'}
        )
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Data table
    st.markdown("---")
    st.subheader("Item Listings")
    
    display_cols = ['brand_norm', 'category_norm', 'title', 'price', 'condition_bucket', 'status', 'season']
    display_cols = [col for col in display_cols if col in filtered_df.columns]
    
    st.dataframe(
        filtered_df[display_cols].head(100),
        use_container_width=True,
        hide_index=True
    )

# ============================================================================
# PAGE 3: PRICE CALCULATOR
# ============================================================================

elif page == "Price Calculator":
    st.markdown('<p class="main-header">Smart Price Calculator</p>', unsafe_allow_html=True)
    
    st.markdown("""
    Get pricing recommendations and estimated time-to-sell based on historical data.
    Select your item characteristics below.
    """)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Item Details")
        
        calc_brand = st.selectbox(
            "Brand",
            sorted(listings_df['brand_norm'].unique()),
            key="calc_brand"
        )
        
        calc_category = st.selectbox(
            "Category",
            sorted(listings_df['category_norm'].unique()),
            key="calc_category"
        )
        
        calc_audience = st.selectbox(
            "Audience",
            sorted(listings_df['audience'].unique()),
            key="calc_audience"
        )
        
        if 'season' in listings_df.columns:
            seasons = ['Any'] + sorted(listings_df['season'].dropna().unique().tolist())
            calc_season = st.selectbox("Season (optional)", seasons, key="calc_season")
            calc_season = None if calc_season == 'Any' else calc_season
        else:
            calc_season = None
    
    with col2:
        st.subheader("Market Data")
        
        # Calculate KPIs for selected combination
        calc_kpis = calculate_all_kpis(
            brand=calc_brand,
            category=calc_category,
            audience=calc_audience,
            season=calc_season
        )
        
        if calc_kpis['price_distribution']:
            st.success(f"✓ Found {calc_kpis['price_distribution']['count']} comparable items")
            
            # Show price range
            st.markdown("###Recommended Price Range")
            
            p25 = calc_kpis['price_distribution']['p25']
            p50 = calc_kpis['price_distribution']['p50']
            p75 = calc_kpis['price_distribution']['p75']
            
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                st.metric("Budget Price", f"€{p25:.2f}", "25th percentile")
            with col_b:
                st.metric("Market Price", f"€{p50:.2f}", "50th percentile (median)")
            with col_c:
                st.metric("Premium Price", f"€{p75:.2f}", "75th percentile")
            
            # Show time to sell
            st.markdown("###Estimated Time to Sell")
            
            if calc_kpis['dts']:
                dts_median = calc_kpis['dts']['median']
                dts_p25 = calc_kpis['dts']['p25']
                dts_p75 = calc_kpis['dts']['p75']
                
                st.info(f"""
                **Median**: {dts_median:.0f} days  
                **Fast sale (25%)**: {dts_p25:.0f} days  
                **Slow sale (75%)**: {dts_p75:.0f} days
                """)
                
                # Recommendations
                st.markdown("###Pricing Strategy")
                
                if dts_median < 10:
                    st.success("High demand! You can price at the premium range.")
                elif dts_median < 20:
                    st.info("Good demand. Market price recommended.")
                else:
                    st.warning("Slower sales. Consider budget pricing for faster turnover.")
            
            else:
                st.warning("Not enough sold items data for time-to-sell estimates")
        
        else:
            st.error("No data found for this combination")
    
    st.markdown("---")
    
    # Advanced calculator
    st.subheader("Custom Price Estimator")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        your_price = st.number_input(
            "Your asking price (€)",
            min_value=1.0,
            max_value=500.0,
            value=float(p50) if calc_kpis['price_distribution'] else 25.0,
            step=1.0
        )
    
    with col2:
        if calc_kpis['price_distribution']:
            percentile = None
            if your_price <= p25:
                percentile = "Budget (bottom 25%)"
                color = "🟢"
            elif your_price <= p50:
                percentile = "Below market (25-50%)"
                color = "🟡"
            elif your_price <= p75:
                percentile = "Above market (50-75%)"
                color = "🟠"
            else:
                percentile = "Premium (top 25%)"
                color = "🔴"
            
            st.metric("Price Positioning", f"{color} {percentile}")
    
    with col3:
        if calc_kpis['dts'] and calc_kpis['price_distribution']:
            # Estimate DTS based on price positioning
            if your_price <= p25:
                estimated_dts = calc_kpis['dts']['p25']
                speed = "Fast"
            elif your_price <= p50:
                estimated_dts = calc_kpis['dts']['median']
                speed = "Average"
            elif your_price <= p75:
                estimated_dts = calc_kpis['dts']['p75']
                speed = "Slower"
            else:
                estimated_dts = calc_kpis['dts']['p75'] * 1.5
                speed = "Slow"
            
            st.metric("Estimated Days to Sell", f"{estimated_dts:.0f} days", speed)

# ============================================================================
# PAGE 4: DOWNLOADS (WITH PDF)
# ============================================================================

elif page == "Downloads":
    st.markdown('<p class="main-header">Export Data & Reports</p>', unsafe_allow_html=True)
    
    st.markdown("Download data and reports for further analysis.")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("CSV Exports")
        
        # Listings export
        st.markdown("### Active Listings")
        active_df = listings_df[listings_df['status'] == 'active']
        csv_active = active_df.to_csv(index=False)
        st.download_button(
            label="Download Active Listings (CSV)",
            data=csv_active,
            file_name=f"vinted_active_listings_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        st.info(f"{len(active_df):,} active listings")
        
        # Sold items export
        if len(sold_events_df) > 0:
            st.markdown("### Sold Items")
            csv_sold = sold_events_df.to_csv(index=False)
            st.download_button(
                label="Download Sold Items (CSV)",
                data=csv_sold,
                file_name=f"vinted_sold_items_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            st.info(f"{len(sold_events_df):,} sold items")
        
        # Price events export
        if len(price_events_df) > 0:
            st.markdown("### Price Changes")
            csv_prices = price_events_df.to_csv(index=False)
            st.download_button(
                label="Download Price Changes (CSV)",
                data=csv_prices,
                file_name=f"vinted_price_changes_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            st.info(f"{len(price_events_df):,} price changes")
    
    with col2:
        st.subheader("Summary Reports")
        
        # KPI Summary CSV
        st.markdown("### KPI Summary Report (CSV)")
        
        # Generate summary for all brands
        summary_data = []
        for brand in sorted(listings_df['brand_norm'].unique()):
            kpis = calculate_all_kpis(brand=brand)
            summary_data.append({
                'Brand': brand,
                'Active Items': len(listings_df[(listings_df['brand_norm'] == brand) & (listings_df['status'] == 'active')]),
                'Median DTS (days)': kpis['dts']['median'] if kpis['dts'] else None,
                'Sell-Through 30d (%)': kpis['sell_through_30d']['percentage'] if kpis['sell_through_30d'] else None,
                'Median Price (€)': kpis['price_distribution']['p50'] if kpis['price_distribution'] else None,
                'Liquidity Score': kpis['liquidity']['score'] if kpis['liquidity'] else None,
                'Grade': kpis['liquidity']['grade'] if kpis['liquidity'] else None
            })
        
        summary_df = pd.DataFrame(summary_data)
        csv_summary = summary_df.to_csv(index=False)
        
        st.download_button(
            label="Download KPI Summary (CSV)",
            data=csv_summary,
            file_name=f"vinted_kpi_summary_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
        
        # PDF Export (FIXED: Added functionality)
        st.markdown("### 1-Page PDF Report")
        st.markdown("Generate a comprehensive 1-page summary report in PDF format.")
        
        if st.button("Generate PDF Report", type="primary"):
            with st.spinner("Generating PDF..."):
                try:
                    pdf_buffer = generate_pdf_report(listings_df, sold_events_df)
                    
                    st.download_button(
                        label="Download PDF Report",
                        data=pdf_buffer,
                        file_name=f"vinted_market_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf"
                    )
                    st.success("PDF report generated successfully!")
                except Exception as e:
                    st.error(f"Error generating PDF: {e}")
                    st.info("Make sure reportlab is installed: `pip install reportlab`")
    
    st.markdown("---")
    st.info("""
    **Export Options:**
    - **CSV files**: Raw data for analysis in Excel, Python, R
    - **PDF report**: 1-page executive summary with key metrics
    - All exports include data from the latest scrape
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p><strong>Vinted Market Intelligence Dashboard</strong></p>
    <p>Data updates every 48 hours | Last refresh: {}</p>
    <p style='font-size: 0.8rem;'>5 Combos: Zara·Dresses·Women | Mango·Dresses·Women | Nike·Sneakers·Men | H&M·T-shirt·Men | Levi's·Jeans·Men</p>
</div>
""".format(datetime.now().strftime('%Y-%m-%d %H:%M')), unsafe_allow_html=True)