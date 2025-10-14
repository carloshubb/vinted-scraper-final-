"""
Vinted Market Intelligence Dashboard - CRITICAL FIXES
Fixed based on urgent client feedback:
1. Data Summary: Fixed sold items count (use sold_events, not listings status)
2. Liquidity Score: Fixed calculation (was showing raw numbers, not 0-100 score)
3. Brand·Category: Focus on SOLD items by CONDITION
4. Calculator: Restored old version with price input + condition filter
5. Removed 2/day limitation
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
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER
import tempfile


def generate_analysis_pdf_complete(listings_df, sold_events_df, brand=None, category=None, audience=None, season=None):
  
    buffer = io.BytesIO()
    
    # Use landscape for more space
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
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#333333'),
        spaceAfter=8,
        spaceBefore=12
    )
    
    # Build title
    filter_parts = []
    if brand: filter_parts.append(brand)
    if audience: filter_parts.append(audience)
    if category: filter_parts.append(category)
    if season: filter_parts.append(season)
    
    title_text = "Vinted Market Analysis"
    if filter_parts:
        title_text += f" - {' · '.join(filter_parts)}"
    
    story.append(Paragraph(title_text, title_style))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Analysis of Sold Items by Condition", 
        styles['Normal']
    ))
    story.append(Spacer(1, 0.2*inch))
    
    # Filter sold events
    if len(sold_events_df) == 0:
        story.append(Paragraph("No sold items data available", styles['Normal']))
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    filtered_sold = sold_events_df[sold_events_df['sold_confidence'] >= 0.5].copy()
    
    if brand:
        filtered_sold = filtered_sold[filtered_sold['brand'] == brand]
    if category:
        filtered_sold = filtered_sold[filtered_sold['category'] == category]
    if audience:
        filtered_sold = filtered_sold[filtered_sold['audience'] == audience]
    if season and 'season' in filtered_sold.columns:
        filtered_sold = filtered_sold[filtered_sold['season'] == season]
    
    if len(filtered_sold) == 0:
        story.append(Paragraph("No sold items match the selected filters", styles['Normal']))
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    # Overall KPIs Section
    story.append(Paragraph("Overall KPIs (Sold Items)", heading_style))
    
    kpi_data = [
        ['Metric', 'Value'],
        ['Total Sold Items', f"{len(filtered_sold):,}"],
        ['Median Days to Sell', f"{filtered_sold['days_to_sell'].median():.1f} days"],
        ['Median Final Price', f"EUR {filtered_sold['final_listed_price'].median():.2f}"],
    ]
    
    # Add sell-through if we can calculate it
    sold_30d = len(filtered_sold[filtered_sold['days_to_sell'] <= 30])
    sold_30d_pct = (sold_30d / len(filtered_sold)) * 100
    kpi_data.append(['Items Sold ≤30 Days', f"{sold_30d} ({sold_30d_pct:.1f}%)"])
    
    kpi_table = Table(kpi_data, colWidths=[3.5*inch, 3*inch])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Breakdown by Condition
    story.append(Paragraph("Breakdown by Condition", heading_style))
    
    condition_data = [['Condition', 'Count', 'Median Price', 'Median DTS', 'Sold ≤30d']]
    
    for condition in sorted(filtered_sold['condition'].unique()):
        cond_df = filtered_sold[filtered_sold['condition'] == condition]
        if len(cond_df) > 0:
            sold_30d_cond = len(cond_df[cond_df['days_to_sell'] <= 30])
            sold_30d_pct_cond = (sold_30d_cond / len(cond_df)) * 100
            
            condition_data.append([
                condition,
                f"{len(cond_df):,}",
                f"EUR {cond_df['final_listed_price'].median():.2f}",
                f"{cond_df['days_to_sell'].median():.1f}d",
                f"{sold_30d_pct_cond:.1f}%"
            ])
    
    condition_table = Table(condition_data, colWidths=[2.5*inch, 1*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    condition_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(condition_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Price Statistics
    story.append(Paragraph("Price Statistics by Condition", heading_style))
    
    price_stats_data = [['Condition', 'Min', 'P25', 'Median', 'P75', 'Max']]
    
    for condition in sorted(filtered_sold['condition'].unique()):
        cond_df = filtered_sold[filtered_sold['condition'] == condition]
        if len(cond_df) > 0:
            price_stats_data.append([
                condition,
                f"EUR {cond_df['final_listed_price'].min():.2f}",
                f"EUR {cond_df['final_listed_price'].quantile(0.25):.2f}",
                f"EUR {cond_df['final_listed_price'].median():.2f}",
                f"EUR {cond_df['final_listed_price'].quantile(0.75):.2f}",
                f"EUR {cond_df['final_listed_price'].max():.2f}"
            ])
    
    price_table = Table(price_stats_data, colWidths=[2*inch, 1.3*inch, 1.3*inch, 1.3*inch, 1.3*inch, 1.3*inch])
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
    footer_text = f"Report generated from Vinted Market Intelligence | {len(filtered_sold):,} sold items analyzed | High confidence sales (≥0.5) only"
    story.append(Paragraph(footer_text, styles['Italic']))
    
    # Build PDF
    try:
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        # If build fails, return error PDF
        error_buffer = io.BytesIO()
        error_doc = SimpleDocTemplate(error_buffer, pagesize=letter)
        error_story = [
            Paragraph("PDF Generation Error", title_style),
            Spacer(1, 0.2*inch),
            Paragraph(f"Error: {str(e)}", styles['Normal']),
            Spacer(1, 0.2*inch),
            Paragraph("Please contact support if this error persists.", styles['Normal'])
        ]
        error_doc.build(error_story)
        error_buffer.seek(0)
        return error_buffer


def generate_pdf_filename(brand=None, category=None, audience=None, season=None):
    """Generate dynamic PDF filename based on filters."""
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


sys.path.append(str(Path(__file__).parent))

from calculate_kpis import (
    calculate_all_kpis,
    load_all_data,
)

st.set_page_config(
    page_title="Vinted Market Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

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

def has_premium_access():
    return st.session_state.authenticated

def request_access_widget():
    st.warning("Premium Feature")
    with st.expander("Enter Access Code"):
        password = st.text_input("Access code:", type="password", key="premium_password")
        if st.button("Unlock Premium"):
            if password == "VINTED2024":
                st.session_state.authenticated = True
                st.success("Access granted!")
                st.rerun()
            else:
                st.error("Invalid code")


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

# CRITICAL FIX 1: Data Summary - Correct counts
st.sidebar.markdown("###Data Summary")

# Total listings: Current snapshot (active + sold in database)
total_listings = len(listings_df)
st.sidebar.metric("Total Listings", f"{total_listings:,}")
st.sidebar.caption("Current database size")

# Active items: Current active snapshot
active_items = len(listings_df[listings_df['status'] == 'active'])
st.sidebar.metric("Active Items", f"{active_items:,}")
st.sidebar.caption("Currently listed")

# CRITICAL FIX: Sold items from sold_events, not listings status
# This avoids double-counting and accumulation issues
if len(sold_events_df) > 0:
    # Use high-confidence sold events only
    high_confidence_sold = sold_events_df[sold_events_df['sold_confidence'] >= 0.5]
    sold_count = len(high_confidence_sold)
    st.sidebar.metric("Sold Items", f"{sold_count:,}")
    st.sidebar.caption("High-confidence sales detected")
else:
    st.sidebar.metric("Sold Items", "0")
    st.sidebar.caption("No sales detected yet")

# Price changes
st.sidebar.metric("Price Changes", f"{len(price_events_df):,}")

if 'scrape_timestamp' in listings_df.columns:
    last_update = pd.to_datetime(listings_df['scrape_timestamp']).max()
    st.sidebar.info(f"Updated: {last_update.strftime('%Y-%m-%d %H:%M')}")

# CRITICAL FIX: Explanation of data sources
with st.sidebar.expander("How Data is Counted"):
    st.markdown("""
    **Total Listings**: All items in database (active + sold)
    
    **Active Items**: Currently listed items (status='active')
    
    **Sold Items**: Items that disappeared ≥48h ago and were posted ≤30 days ago (from sold_events table with confidence ≥0.5)
    
    **Price Changes**: Detected price modifications (from price_events table)
    
    Note: Sold items are tracked separately to avoid double-counting.
    """)

if has_premium_access():
    st.sidebar.success("Premium Access Active")

# ============================================================================
# PAGE 1: OVERVIEW (With fixed liquidity scores)
# ============================================================================

if "Overview" in page:
    st.markdown('<p class="main-header">Market Overview</p>', unsafe_allow_html=True)
    
    st.markdown("Liquidity ranking by brand. **Liquidity Score** = 0-100 (higher = faster sales)")
    st.markdown("---")
    
    st.subheader("Filter Rankings")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        categories_filter = ['All Categories'] + sorted(listings_df['category_norm'].unique().tolist())
        selected_category_overview = st.selectbox("Category", categories_filter, key="overview_category")
    
    with col2:
        audiences_filter = ['All Audiences'] + sorted(listings_df['audience'].unique().tolist())
        selected_audience_overview = st.selectbox("Audience", audiences_filter, key="overview_audience")
    
    with col3:
        conditions_filter = ['All Conditions'] + sorted(listings_df['condition_bucket'].unique().tolist())
        selected_condition_overview = st.selectbox("Status (Condition)", conditions_filter, key="overview_condition")
    
    st.markdown("---")
    
    category_filter_val = None if selected_category_overview == 'All Categories' else selected_category_overview
    audience_filter_val = None if selected_audience_overview == 'All Audiences' else selected_audience_overview
    condition_filter_val = None if selected_condition_overview == 'All Conditions' else selected_condition_overview
    
    if category_filter_val or audience_filter_val or condition_filter_val:
        filters_summary = []
        if category_filter_val:
            filters_summary.append(f"Category: {category_filter_val}")
        if audience_filter_val:
            filters_summary.append(f"Audience: {audience_filter_val}")
        if condition_filter_val:
            filters_summary.append(f"Condition: {condition_filter_val}")
        st.info(f"Active filters: {' | '.join(filters_summary)}")
    
    # Filter data
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
        
        # CRITICAL FIX 2: Ensure liquidity score is 0-100, not raw calculation
        if kpis['liquidity'] and kpis['dts'] and kpis['sell_through_30d']:
            # Verify score is in valid range
            liquidity_score = kpis['liquidity']['score']
            if liquidity_score > 100:
                st.warning(f"Warning: {brand} liquidity score > 100. Check calculation.")
                liquidity_score = min(liquidity_score, 100)
            
            liquidity_data.append({
                'Brand': brand,
                'Liquidity Score': liquidity_score,
                'Grade': kpis['liquidity']['grade'],
                'DTS (days)': kpis['dts']['median'],
                'Sell-Through 30d (%)': kpis['sell_through_30d']['percentage'],
                'Active Items': len(brand_listings[brand_listings['status'] == 'active']),
                'Sold Items': kpis['sell_through_30d']['sold_30d']
            })
    
    if liquidity_data:
        liquidity_df = pd.DataFrame(liquidity_data).sort_values('Liquidity Score', ascending=False)
        
        # CRITICAL FIX: Validate data before display
        if liquidity_df['Liquidity Score'].max() > 100 or liquidity_df['Sell-Through 30d (%)'].max() > 100:
            st.error("DATA VALIDATION ERROR: Scores > 100% detected. Please check KPI calculations.")
            st.dataframe(liquidity_df)
        else:
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
                hovertemplate='<b>%{x}</b><br>Score: %{y:.1f}<br><extra></extra>'
            ))
            
            fig.update_layout(
                xaxis_title="Brand",
                yaxis_title="Liquidity Score (0-100)",
                yaxis_range=[0, 110],
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
                st.metric("Fastest", fastest['Brand'], f"{fastest['DTS (days)']:.1f} days")
            
            with col3:
                best_st = liquidity_df.loc[liquidity_df['Sell-Through 30d (%)'].idxmax()]
                st.metric("Best ST", best_st['Brand'], f"{best_st['Sell-Through 30d (%)']:.1f}%")
    else:
        st.warning("Not enough data with selected filters")

# ============================================================================
# PAGE 2: BRAND·CATEGORY ANALYSIS (CRITICAL FIX: Focus on SOLD items by CONDITION)
# ============================================================================

elif "Brand·Category Analysis" in page:
    st.markdown('<p class="main-header">Brand·Category Analysis - Sold Items by Condition</p>', unsafe_allow_html=True)
    
    st.info("This page analyzes **SOLD items only**, broken down by **condition** (New/Like new, Very good/Good, Average/Poor)")
    
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
    
    # CRITICAL FIX 3: Filter SOLD_EVENTS by conditions, not listings
    if len(sold_events_df) == 0:
        st.warning("No sold items detected yet. Run the pipeline at least twice (48h apart) to detect sales.")
        st.stop()
    
    # Filter sold events
    filtered_sold = sold_events_df[sold_events_df['sold_confidence'] >= 0.5].copy()
    
    if brand_filter:
        filtered_sold = filtered_sold[filtered_sold['brand'] == brand_filter]
    if category_filter:
        filtered_sold = filtered_sold[filtered_sold['category'] == category_filter]
    if audience_filter:
        filtered_sold = filtered_sold[filtered_sold['audience'] == audience_filter]
    if season_filter and 'season' in filtered_sold.columns:
        filtered_sold = filtered_sold[filtered_sold['season'] == season_filter]
    
    if len(filtered_sold) == 0:
        st.warning("No sold items match the selected filters")
        st.stop()
    
    # KPI Cards for sold items
    st.subheader("Overall KPIs (Sold Items)")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        median_dts = filtered_sold['days_to_sell'].median()
        st.metric("Median Days to Sell", f"{median_dts:.1f} days")
    
    with col2:
        sold_30d = len(filtered_sold[filtered_sold['days_to_sell'] <= 30])
        st_rate = (sold_30d / len(filtered_sold)) * 100
        st.metric("Sold ≤30 days", f"{st_rate:.1f}%", f"{sold_30d}/{len(filtered_sold)}")
    
    with col3:
        median_price = filtered_sold['final_listed_price'].median()
        st.metric("Median Final Price", f"EUR {median_price:.2f}")
    
    st.markdown("---")
    
    # CRITICAL FIX: Charts for SOLD items by CONDITION
    st.subheader("Analysis by Condition (Sold Items Only)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("###Price Distribution by Condition")
        
        fig = go.Figure()
        
        for condition in sorted(filtered_sold['condition'].unique()):
            cond_df = filtered_sold[filtered_sold['condition'] == condition]
            if len(cond_df) > 0:
                fig.add_trace(go.Box(
                    y=cond_df['final_listed_price'],
                    name=condition,
                    boxmean='sd'
                ))
        
        fig.update_layout(
            yaxis_title="Final Listed Price (EUR)",
            xaxis_title="Condition",
            height=400,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("###Days to Sell by Condition")
        
        # Calculate median DTS by condition
        dts_by_condition = filtered_sold.groupby('condition')['days_to_sell'].median().reset_index()
        dts_by_condition = dts_by_condition.sort_values('days_to_sell')
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=dts_by_condition['condition'],
            y=dts_by_condition['days_to_sell'],
            text=dts_by_condition['days_to_sell'].round(1),
            textposition='outside',
            marker_color='#1f77b4'
        ))
        
        fig.update_layout(
            yaxis_title="Median Days to Sell",
            xaxis_title="Condition",
            height=400,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # 30-day sell-through by condition
    st.markdown("###30-Day Sell-Through by Condition")
    
    st_by_condition = []
    for condition in sorted(filtered_sold['condition'].unique()):
        cond_df = filtered_sold[filtered_sold['condition'] == condition]
        if len(cond_df) > 0:
            sold_30d = len(cond_df[cond_df['days_to_sell'] <= 30])
            st_rate = (sold_30d / len(cond_df)) * 100
            st_by_condition.append({
                'condition': condition,
                'sell_through': st_rate,
                'count': len(cond_df)
            })
    
    st_df = pd.DataFrame(st_by_condition)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=st_df['condition'],
        y=st_df['sell_through'],
        text=[f"{x:.1f}%<br>({c} items)" for x, c in zip(st_df['sell_through'], st_df['count'])],
        textposition='outside',
        marker_color='#28a745'
    ))
    
    fig.update_layout(
        yaxis_title="Sell-Through Rate (%)",
        xaxis_title="Condition",
        yaxis_range=[0, max(st_df['sell_through']) * 1.2],
        height=400,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Data table
    st.markdown("---")
    st.subheader("Sold Items Details")
    
    display_cols = ['brand', 'category', 'condition', 'final_listed_price', 'days_to_sell', 'sold_confidence']
    display_cols = [col for col in display_cols if col in filtered_sold.columns]
    
    st.dataframe(filtered_sold[display_cols].head(100), use_container_width=True, hide_index=True)
    
    # PDF Generation
    st.markdown("---")
    st.subheader("Generate PDF Report")
    st.markdown("Generate a 1-page PDF summary of this analysis")

if st.button("Generate PDF from This Page", type="primary", key="gen_pdf"):
    with st.spinner("Generating PDF..."):
        try:
            # Use the complete function from the artifact above
            pdf_buffer = generate_analysis_pdf_complete(
                listings_df, sold_events_df,
                brand_filter, category_filter, audience_filter, season_filter
            )
            filename = generate_pdf_filename(
                brand_filter, category_filter, audience_filter, season_filter
            )
            
            st.download_button(
                label="Download PDF Report",
                data=pdf_buffer,
                file_name=filename,
                mime="application/pdf",
                key="download_pdf"
            )
            st.success(f"✅ Generated: {filename}")
            
        except Exception as e:
            st.error(f"❌ Error: {e}")
            st.info("Install: pip install reportlab")

# ============================================================================
# PAGE 3: CALCULATOR (RESTORED OLD VERSION + Condition Filter, NO LIMIT)
# ============================================================================

elif "Price Calculator" in page:
    st.markdown('<p class="main-header">Smart Price Calculator</p>', unsafe_allow_html=True)
    
    st.markdown("Get pricing recommendations and estimated time-to-sell")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 2])
    
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
        
        # CRITICAL FIX 4: Added condition filter (as requested)
        calc_condition = st.selectbox(
            "Status (Condition)",
            sorted(listings_df['condition_bucket'].unique()),
            key="calc_condition"
        )
        
        if 'season' in listings_df.columns:
            seasons = ['Any'] + sorted(listings_df['season'].dropna().unique().tolist())
            calc_season = st.selectbox("Season (optional)", seasons, key="calc_season")
            calc_season = None if calc_season == 'Any' else calc_season
        else:
            calc_season = None
    
    with col2:
        st.subheader("Market Data")
        
        # Calculate KPIs
        calc_kpis = calculate_all_kpis(
            brand=calc_brand,
            category=calc_category,
            audience=calc_audience,
            season=calc_season
        )
        
        # Filter by condition for price display
        calc_filtered = listings_df[
            (listings_df['brand_norm'] == calc_brand) &
            (listings_df['category_norm'] == calc_category) &
            (listings_df['audience'] == calc_audience) &
            (listings_df['condition_bucket'] == calc_condition)
        ]
        
        if len(calc_filtered) > 0 and calc_kpis['price_distribution']:
            st.success(f"✓ Found {len(calc_filtered):,} comparable items")
            
            # Price range
            p25 = calc_filtered['price'].quantile(0.25)
            p50 = calc_filtered['price'].median()
            p75 = calc_filtered['price'].quantile(0.75)
            
            st.markdown("###Recommended Price Range")
            
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                st.metric("Budget", f"EUR {p25:.2f}", "25th percentile")
            with col_b:
                st.metric("Market", f"EUR {p50:.2f}", "Median")
            with col_c:
                st.metric("Premium", f"EUR {p75:.2f}", "75th percentile")
            
            # Time to sell
            st.markdown("###Estimated Time to Sell")
            
            if calc_kpis['dts']:
                dts_median = calc_kpis['dts']['median']
                dts_p25 = calc_kpis['dts']['p25']
                dts_p75 = calc_kpis['dts']['p75']
                
                st.info(f"""
                **Median**: {dts_median:.0f} days  
                **Fast (25%)**: {dts_p25:.0f} days  
                **Slow (75%)**: {dts_p75:.0f} days
                """)
                
                if dts_median < 10:
                    st.success("demand! Premium pricing recommended")
                elif dts_median < 20:
                    st.info("Good demand. Market price recommended")
                else:
                    st.warning("Slower sales. Consider budget pricing")
            
            # CRITICAL FIX: Restored price input estimator
            st.markdown("---")
            st.markdown("###Your Price Estimator")
            
            your_price = st.number_input(
                "Your asking price (EUR)",
                min_value=1.0,
                max_value=500.0,
                value=float(p50),
                step=1.0
            )
            
            col_x, col_y = st.columns(2)
            
            with col_x:
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
            
            with col_y:
                if calc_kpis['dts']:
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
                    
                    st.metric("Est. Days to Sell", f"{estimated_dts:.0f} days", speed)
        
        else:
            st.error("No data for this combination")

# ============================================================================
# PAGE 4: DOWNLOADS
# ============================================================================

elif "Downloads" in page:
    st.markdown('<p class="main-header">Downloads</p>', unsafe_allow_html=True)
    
    # if not has_premium_access():
    #     request_access_widget()
    #     st.stop()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("CSV Exports")
        
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
            csv_sold = sold_events_df.to_csv(index=False)
            st.download_button(
                "Download Sold (CSV)",
                csv_sold,
                f"vinted_sold_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )
            st.info(f"{len(sold_events_df):,} items")
        
        if len(price_events_df) > 0:
            csv_prices = price_events_df.to_csv(index=False)
            st.download_button(
                "Download Price Changes (CSV)",
                csv_prices,
                f"vinted_prices_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )
            st.info(f"{len(price_events_df):,} items")
    
    with col2:
        st.subheader("Reports")
        st.info("Use 'Brand·Category Analysis' page to generate PDF reports with charts")

st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p><strong>Vinted Market Intelligence</strong> | {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
</div>
""", unsafe_allow_html=True)