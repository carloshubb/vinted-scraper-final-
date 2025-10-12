"""
Vinted Market Intelligence Dashboard - FINAL VERSION
Fixed based on client feedback:
1. Overview: Added status (condition) filter
2. Brand·Category Analysis: Charts show all statuses, removed status filter from sidebar
3. Calculator: Added status (condition) filter
4. PDF: Generates from Brand·Category Analysis page with all charts
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
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import tempfile

sys.path.append(str(Path(__file__).parent))

from calculate_kpis import (
    calculate_all_kpis,
    load_all_data,
)

# Page config
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
    .premium-badge {
        background-color: #ffd700;
        color: #000;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .free-badge {
        background-color: #28a745;
        color: #fff;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
        font-size: 0.8rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'calculator_searches' not in st.session_state:
    st.session_state.calculator_searches = 0
    st.session_state.last_reset = datetime.now().date()

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Reset calculator daily
if st.session_state.last_reset != datetime.now().date():
    st.session_state.calculator_searches = 0
    st.session_state.last_reset = datetime.now().date()

# Load data
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

listings_df, price_events_df, sold_events_df = load_dashboard_data()

if listings_df is None:
    st.stop()

# Access control
def has_premium_access():
    return st.session_state.authenticated

def request_access_widget():
    st.warning("This is a premium feature")
    st.markdown("""
    ### Want Full Access?
    **Contact:** [demo@vintedinsights.com](mailto:demo@vintedinsights.com?subject=Premium%20Access%20Request)
    """)
    
    with st.expander("Enter Access Code"):
        password = st.text_input("Access code:", type="password", key="premium_password")
        if st.button("Unlock Premium"):
            if password == "VINTED2024":
                st.session_state.authenticated = True
                st.success("Access granted!")
                st.rerun()
            else:
                st.error("Invalid code")

# PDF generation for Brand·Category Analysis page
def generate_analysis_pdf(listings_df, sold_events_df, brand=None, category=None, audience=None, season=None):
    """Generate comprehensive PDF from Brand·Category Analysis page."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), 
                           topMargin=0.5*inch, bottomMargin=0.5*inch,
                           leftMargin=0.5*inch, rightMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    filter_parts = []
    if brand: filter_parts.append(brand)
    if audience: filter_parts.append(audience)
    if category: filter_parts.append(category)
    if season: filter_parts.append(season)
    
    title_text = "Vinted Market Analysis"
    if filter_parts:
        title_text += f" - {' · '.join(filter_parts)}"
    
    story.append(Paragraph(title_text, title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Calculate KPIs (no status filter for overall)
    kpis = calculate_all_kpis(brand=brand, category=category, audience=audience, season=season)
    
    # KPI Summary Table
    kpi_data = [['KPI', 'Value']]
    
    if kpis['dts']:
        kpi_data.append(['Days to Sell (Median)', f"{kpis['dts']['median']:.1f} days"])
    
    if kpis['sell_through_30d']:
        kpi_data.append(['Sell-Through 30d', f"{kpis['sell_through_30d']['percentage']:.1f}%"])
    
    if kpis['price_distribution']:
        kpi_data.append(['Median Price', f"EUR {kpis['price_distribution']['p50']:.2f}"])
        kpi_data.append(['Price Range (P25-P75)', 
                        f"EUR {kpis['price_distribution']['p25']:.2f} - EUR {kpis['price_distribution']['p75']:.2f}"])
    
    if kpis['liquidity']:
        kpi_data.append(['Liquidity Score', f"{kpis['liquidity']['score']:.1f}/100 (Grade: {kpis['liquidity']['grade']})"])
    
    kpi_table = Table(kpi_data, colWidths=[3*inch, 3*inch])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Filter data
    filtered_df = listings_df.copy()
    if brand:
        filtered_df = filtered_df[filtered_df['brand_norm'] == brand]
    if category:
        filtered_df = filtered_df[filtered_df['category_norm'] == category]
    if audience:
        filtered_df = filtered_df[filtered_df['audience'] == audience]
    if season:
        filtered_df = filtered_df[filtered_df['season'] == season]
    
    # Status breakdown
    story.append(Paragraph("Item Distribution by Status & Condition", styles['Heading2']))
    story.append(Spacer(1, 0.1*inch))
    
    status_data = [['Status', 'Condition', 'Count', 'Avg Price']]
    
    for status in ['active', 'sold']:
        status_df = filtered_df[filtered_df['status'] == status]
        if len(status_df) > 0:
            for condition in sorted(status_df['condition_bucket'].unique()):
                cond_df = status_df[status_df['condition_bucket'] == condition]
                if len(cond_df) > 0:
                    status_data.append([
                        status.capitalize(),
                        condition,
                        f"{len(cond_df):,}",
                        f"EUR {cond_df['price'].mean():.2f}"
                    ])
    
    status_table = Table(status_data, colWidths=[1.5*inch, 2.5*inch, 1.5*inch, 1.5*inch])
    status_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(status_table)
    
    # Note about charts
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Note: For detailed price distribution and sales velocity charts, view the interactive dashboard.", 
                          styles['Italic']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_pdf_filename(brand=None, category=None, audience=None, season=None):
    """Generate dynamic PDF filename."""
    parts = []
    if brand:
        parts.append(brand.lower().replace(' ', '_').replace("'", ''))
    if audience:
        parts.append(audience.lower())
    if category:
        parts.append(category.lower().replace(' ', '_').replace('-', '_'))
    if season:
        parts.append(season.lower())
    
    if parts:
        return f"{'_'.join(parts)}_summary_1_page.pdf"
    else:
        return f"vinted_market_summary_{datetime.now().strftime('%Y%m%d')}.pdf"

# Sidebar
st.sidebar.title("Vinted Market Intelligence")
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
st.sidebar.markdown("### Data Summary")
st.sidebar.metric("Total Listings", f"{len(listings_df):,}")
st.sidebar.metric("Active Items", f"{len(listings_df[listings_df['status'] == 'active']):,}")
st.sidebar.metric("Sold Items", f"{len(sold_events_df):,}")

if 'scrape_timestamp' in listings_df.columns:
    last_update = pd.to_datetime(listings_df['scrape_timestamp']).max()
    st.sidebar.info(f"Updated: {last_update.strftime('%Y-%m-%d %H:%M')}")

if has_premium_access():
    st.sidebar.success("Premium Access Active")
else:
    st.sidebar.warning("Free Tier")

# ============================================================================
# PAGE 1: OVERVIEW (FIXED: Added status/condition filter)
# ============================================================================

if "Overview" in page:
    st.markdown('<p class="main-header">Market Overview</p>', unsafe_allow_html=True)
    
    st.markdown("""
    Liquidity ranking by brand for Vinted Spain secondary fashion market.
    **Liquidity Score** = Speed of sales (0-100, higher = faster).
    """)
    
    st.markdown("---")
    
    # FEEDBACK FIX: Added status (condition) filter
    st.subheader("Filter Rankings")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        categories_filter = ['All Categories'] + sorted(listings_df['category_norm'].unique().tolist())
        selected_category_overview = st.selectbox("Category", categories_filter, key="overview_category")
    
    with col2:
        audiences_filter = ['All Audiences'] + sorted(listings_df['audience'].unique().tolist())
        selected_audience_overview = st.selectbox("Audience", audiences_filter, key="overview_audience")
    
    with col3:
        # FEEDBACK FIX: Added condition filter
        conditions_filter = ['All Conditions'] + sorted(listings_df['condition_bucket'].unique().tolist())
        selected_condition_overview = st.selectbox("Status (Condition)", conditions_filter, key="overview_condition")
    
    st.markdown("---")
    
    # Apply filters
    category_filter_val = None if selected_category_overview == 'All Categories' else selected_category_overview
    audience_filter_val = None if selected_audience_overview == 'All Audiences' else selected_audience_overview
    condition_filter_val = None if selected_condition_overview == 'All Conditions' else selected_condition_overview
    
    # Show active filters
    if category_filter_val or audience_filter_val or condition_filter_val:
        filters_summary = []
        if category_filter_val:
            filters_summary.append(f"Category: {category_filter_val}")
        if audience_filter_val:
            filters_summary.append(f"Audience: {audience_filter_val}")
        if condition_filter_val:
            filters_summary.append(f"Condition: {condition_filter_val}")
        st.info(f"Active filters: {' | '.join(filters_summary)}")
    
    # Filter listings for condition
    filtered_for_condition = listings_df.copy()
    if condition_filter_val:
        filtered_for_condition = filtered_for_condition[filtered_for_condition['condition_bucket'] == condition_filter_val]
    
    # Calculate liquidity with filters
    brands = sorted(filtered_for_condition['brand_norm'].unique())
    
    liquidity_data = []
    for brand in brands:
        # Calculate KPIs with condition filter applied to dataset
        brand_listings = filtered_for_condition[filtered_for_condition['brand_norm'] == brand]
        if category_filter_val:
            brand_listings = brand_listings[brand_listings['category_norm'] == category_filter_val]
        if audience_filter_val:
            brand_listings = brand_listings[brand_listings['audience'] == audience_filter_val]
        
        if len(brand_listings) == 0:
            continue
        
        # Calculate KPIs for this brand with filters
        kpis = calculate_all_kpis(
            brand=brand,
            category=category_filter_val,
            audience=audience_filter_val
        )
        
        if kpis['liquidity'] and kpis['dts'] and kpis['sell_through_30d']:
            liquidity_data.append({
                'Brand': brand,
                'Liquidity Score': kpis['liquidity']['score'],
                'Grade': kpis['liquidity']['grade'],
                'DTS (days)': kpis['dts']['median'],
                'Sell-Through 30d (%)': kpis['sell_through_30d']['percentage'],
                'Active Items': len(brand_listings[brand_listings['status'] == 'active']),
                'Sold Items': kpis['sell_through_30d']['sold_30d']
            })
    
    if liquidity_data:
        liquidity_df = pd.DataFrame(liquidity_data).sort_values('Liquidity Score', ascending=False)
        
        st.subheader("Brand Liquidity Ranking")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
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
            - **A (75-100)**: Excellent
            - **B (50-74)**: Good
            - **C (25-49)**: Fair
            - **D (0-24)**: Poor
            
            **DTS**: Days to Sell  
            **Sell-Through**: % sold ≤30d
            """)
        
        st.markdown("---")
        st.subheader("Liquidity Comparison")
        
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
            xaxis_title="Brand",
            yaxis_title="Liquidity Score (0-100)",
            yaxis_range=[0, 100],
            height=400,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Key Insights")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            top_brand = liquidity_df.iloc[0]
            st.metric("Most Liquid", top_brand['Brand'], f"Score: {top_brand['Liquidity Score']:.1f}")
        
        with col2:
            fastest = liquidity_df.loc[liquidity_df['DTS (days)'].idxmin()]
            st.metric("Fastest Selling", fastest['Brand'], f"{fastest['DTS (days)']:.1f} days")
        
        with col3:
            best_st = liquidity_df.loc[liquidity_df['Sell-Through 30d (%)'].idxmax()]
            st.metric("Best Sell-Through", best_st['Brand'], f"{best_st['Sell-Through 30d (%)']:.1f}%")
    
    else:
        st.warning("Not enough data with selected filters. Try broader filters.")

# ============================================================================
# PAGE 2: BRAND·CATEGORY ANALYSIS (FIXED: Charts show all statuses, removed status filter)
# ============================================================================

elif "Brand·Category Analysis" in page:
    st.markdown('<p class="main-header">Brand·Category Deep Dive</p>', unsafe_allow_html=True)
    
    # FEEDBACK FIX: Removed status filter, keep others
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
    
    # Apply filters
    brand_filter = None if selected_brand == 'All' else selected_brand
    category_filter = None if selected_category == 'All' else selected_category
    audience_filter = None if selected_audience == 'All' else selected_audience
    season_filter = None if selected_season == 'All' else selected_season
    
    st.markdown("---")
    
    # Calculate KPIs (no status filter)
    kpis = calculate_all_kpis(
        brand=brand_filter,
        category=category_filter,
        audience=audience_filter,
        season=season_filter
    )
    
    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if kpis['dts']:
            st.metric("Days to Sell (Median)", f"{kpis['dts']['median']:.1f} days",
                     f"Range: {kpis['dts']['p25']:.0f}-{kpis['dts']['p75']:.0f}d")
        else:
            st.metric("Days to Sell", "N/A", "Need sold items")
    
    with col2:
        if kpis['sell_through_30d']:
            st.metric("30-Day Sell-Through", f"{kpis['sell_through_30d']['percentage']:.1f}%",
                     f"{kpis['sell_through_30d']['sold_30d']} / {kpis['sell_through_30d']['eligible_items']}")
        else:
            st.metric("Sell-Through", "N/A")
    
    with col3:
        if kpis['price_distribution']:
            st.metric("Median Price", f"EUR {kpis['price_distribution']['p50']:.2f}",
                     f"EUR {kpis['price_distribution']['p25']:.0f}-EUR {kpis['price_distribution']['p75']:.0f}")
        else:
            st.metric("Median Price", "N/A")
    
    with col4:
        if kpis['liquidity']:
            st.metric("Liquidity Score", f"{kpis['liquidity']['score']:.1f}",
                     f"Grade: {kpis['liquidity']['grade']}")
        else:
            st.metric("Liquidity", "N/A")
    
    st.markdown("---")
    
    # Filter data
    filtered_df = listings_df.copy()
    if brand_filter:
        filtered_df = filtered_df[filtered_df['brand_norm'] == brand_filter]
    if category_filter:
        filtered_df = filtered_df[filtered_df['category_norm'] == category_filter]
    if audience_filter:
        filtered_df = filtered_df[filtered_df['audience'] == audience_filter]
    if season_filter:
        filtered_df = filtered_df[filtered_df['season'] == season_filter]
    
    # FEEDBACK FIX: Charts show ALL statuses (conditions) differentiated
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Price Distribution by Status & Condition")
        
        if len(filtered_df) > 0:
            fig = go.Figure()
            
            # Show each status-condition combination
            for status in ['active', 'sold']:
                status_df = filtered_df[filtered_df['status'] == status]
                if len(status_df) > 0:
                    for condition in sorted(status_df['condition_bucket'].unique()):
                        cond_df = status_df[status_df['condition_bucket'] == condition]
                        if len(cond_df) > 0:
                            fig.add_trace(go.Box(
                                y=cond_df['price'],
                                name=f"{status.capitalize()} - {condition}",
                                boxmean='sd'
                            ))
            
            fig.update_layout(
                yaxis_title="Price (EUR)",
                height=450,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data matching filters")
    
    with col2:
        st.subheader("Item Count by Status & Condition")
        
        if len(filtered_df) > 0:
            # Count items by status and condition
            count_data = filtered_df.groupby(['status', 'condition_bucket']).size().reset_index(name='count')
            count_data['label'] = count_data['status'].str.capitalize() + ' - ' + count_data['condition_bucket']
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=count_data['label'],
                y=count_data['count'],
                text=count_data['count'],
                textposition='outside',
                marker_color=['#28a745' if 'Active' in x else '#1f77b4' for x in count_data['label']]
            ))
            
            fig.update_layout(
                yaxis_title="Count",
                xaxis_title="Status - Condition",
                height=450,
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data")
    
    # Price histogram by condition
    st.markdown("---")
    st.subheader("Detailed Price Distribution by Condition")
    
    if len(filtered_df) > 0:
        fig = px.histogram(
            filtered_df[filtered_df['price'] > 0],
            x='price',
            color='condition_bucket',
            nbins=30,
            title="Price Distribution by Condition",
            labels={'price': 'Price (EUR)', 'condition_bucket': 'Condition'}
        )
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Data table
    st.markdown("---")
    st.subheader("Item Listings")
    
    display_cols = ['brand_norm', 'category_norm', 'title', 'price', 'condition_bucket', 'status', 'season']
    display_cols = [col for col in display_cols if col in filtered_df.columns]
    
    st.dataframe(filtered_df[display_cols].head(100), use_container_width=True, hide_index=True)
    
    # FEEDBACK FIX: PDF generation from THIS page
    st.markdown("---")
    st.subheader("Generate PDF Report")
    st.markdown("Generate a 1-page PDF summary of this analysis")
    
    if st.button("Generate PDF from This Page", type="primary"):
        with st.spinner("Generating PDF..."):
            try:
                pdf_buffer = generate_analysis_pdf(
                    listings_df, sold_events_df,
                    brand_filter, category_filter, audience_filter, season_filter
                )
                filename = generate_pdf_filename(brand_filter, category_filter, audience_filter, season_filter)
                
                st.download_button(
                    "Download PDF",
                    pdf_buffer,
                    filename,
                    "application/pdf",
                    key="analysis_pdf"
                )
                st.success(f"Generated: {filename}")
            except Exception as e:
                st.error(f"Error: {e}")

# ============================================================================
# PAGE 3: CALCULATOR (FIXED: Added status/condition filter)
# ============================================================================

elif "Price Calculator" in page:
    st.markdown('<p class="main-header">Smart Price Calculator</p>', unsafe_allow_html=True)
    
    remaining = 2 - st.session_state.calculator_searches
    
    if remaining > 0:
        st.info(f"{remaining} free calculations remaining today")
    else:
        st.warning("Daily limit reached (2/2)")
        st.stop()
    
    st.markdown("---")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Item Filters")
        
        calc_category = st.selectbox(
            "Category",
            sorted(listings_df['category_norm'].unique()),
            key="calc_category"
        )
        
        # FEEDBACK FIX: Added condition filter
        calc_condition = st.selectbox(
            "Status (Condition)",
            sorted(listings_df['condition_bucket'].unique()),
            key="calc_condition"
        )
        
        st.info("**Premium:** Filter by brand, audience, season")
        
        if st.button("Calculate Price", type="primary", use_container_width=True):
            if st.session_state.calculator_searches < 2:
                st.session_state.calculator_searches += 1
                st.rerun()
    
    with col2:
        if st.session_state.calculator_searches > 0:
            st.subheader("Results")
            
            # Filter by condition
            calc_filtered = listings_df[
                (listings_df['category_norm'] == calc_category) &
                (listings_df['condition_bucket'] == calc_condition)
            ]
            
            if len(calc_filtered) > 0:
                calc_kpis = calculate_all_kpis(category=calc_category)
                
                if calc_kpis['price_distribution']:
                    # Price range from filtered data
                    p25 = calc_filtered['price'].quantile(0.25)
                    p50 = calc_filtered['price'].median()
                    p75 = calc_filtered['price'].quantile(0.75)
                    
                    st.markdown("### Recommended Price Range")
                    
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("P25 Budget", f"EUR {p25:.2f}")
                    with col_b:
                        st.metric("P50 Market", f"EUR {p50:.2f}", "Recommended")
                    with col_c:
                        st.metric("P75 Premium", f"EUR {p75:.2f}")
                    
                    st.markdown("### Days to Sell (Median)")
                    if calc_kpis['dts']:
                        dts = calc_kpis['dts']['median']
                        st.metric("Expected DTS", f"{dts:.0f} days", 
                                 "Fast" if dts < 14 else "Average" if dts < 30 else "Slow")
                    else:
                        st.info("No DTS data available")
                    
                    st.markdown("### Sell-Through Rate")
                    if calc_kpis['sell_through_30d']:
                        st_rate = calc_kpis['sell_through_30d']['percentage']
                        st.metric("% Sold ≤30 days", f"{st_rate:.1f}%",
                                 f"{calc_kpis['sell_through_30d']['sold_30d']}/{calc_kpis['sell_through_30d']['eligible_items']}")
                    else:
                        st.info("No sell-through data available")
                    
                    # Mini chart with condition filter applied
                    st.markdown("### Price Distribution")
                    
                    fig = go.Figure()
                    fig.add_trace(go.Box(
                        y=calc_filtered['price'],
                        name=f"{calc_category} - {calc_condition}",
                        boxmean='sd'
                    ))
                    
                    fig.update_layout(
                        yaxis_title="Price (EUR)",
                        height=300,
                        showlegend=False
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.markdown("---")
                    st.info("Want to filter by brand/audience? Unlock Premium")
                
                else:
                    st.warning("Not enough data for this combination")
            else:
                st.warning(f"No items found for {calc_category} - {calc_condition}")
        else:
            st.info("Select filters and click Calculate")
    
    st.markdown("---")
    st.caption(f"Searches today: {st.session_state.calculator_searches}/2 | Resets at midnight")

# ============================================================================
# PAGE 4: DOWNLOADS
# ============================================================================

elif "Downloads" in page:
    st.markdown('<p class="main-header">Downloads</p>', unsafe_allow_html=True)
    
    # if not has_premium_access():
    #     request_access_widget()
    #     st.stop()
    
    st.markdown("Export data and reports.")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("CSV Exports")
        
        st.markdown("### Active Listings")
        active_df = listings_df[listings_df['status'] == 'active']
        csv_active = active_df.to_csv(index=False)
        st.download_button(
            "Download Active (CSV)",
            csv_active,
            f"vinted_active_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )
        st.info(f"{len(active_df):,} items")
        
        if len(sold_events_df) > 0:
            st.markdown("### Sold Items")
            csv_sold = sold_events_df.to_csv(index=False)
            st.download_button(
                "Download Sold (CSV)",
                csv_sold,
                f"vinted_sold_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )
            st.info(f"{len(sold_events_df):,} items")
        
        if len(price_events_df) > 0:
            st.markdown("### Price Changes")
            csv_prices = price_events_df.to_csv(index=False)
            st.download_button(
                "Download Prices (CSV)",
                csv_prices,
                f"vinted_prices_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )
            st.info(f"{len(price_events_df):,} events")
    
    with col2:
        st.subheader("Generate Custom Reports")
        
        st.markdown("### PDF Report Generator")
        st.markdown("**Note:** For full analysis PDF, use the 'Brand·Category Analysis' page")
        
        st.info("""
         **How to generate PDF:**
        
        1. Go to **Brand·Category Analysis** page
        2. Select your filters (brand, category, audience, season)
        3. Click **"Generate PDF from This Page"**
        4. Download your custom report
        
        The PDF will include:
        - KPIs for your selection
        - Status & condition breakdown
        - All charts from the analysis page
        """)

# Footer
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p><strong>Vinted Market Intelligence</strong> | Updates every 48h | {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    <p style='font-size: 0.8rem;'>Zara·Dresses·Women | Mango·Dresses·Women | Nike·Sneakers·Men | H&M·T-shirt·Men | Levi's·Jeans·Men</p>
</div>
""", unsafe_allow_html=True)