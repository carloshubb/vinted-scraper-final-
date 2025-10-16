"""
Market Intelligence Dashboard - COMPLETE FIX
Changes:
1. All calculations use listings.parquet as single source of truth
2. Fixed liquidity score capping at 100
3. Fixed sell-through capping at 100%
4. Correct sold counts everywhere
5. Removed listing_url and scrape_filename from downloads
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys
from datetime import datetime, timedelta
import io
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER

# CLIENT COLORS
PRIMARY_BLUE = '#006064'
ACCENT_CYAN = '#00FFFF'

def safe_sorted(series):
    """Safely sort a pandas series, removing None/NaN values"""
    return sorted([x for x in series.dropna().unique() if x is not None])

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
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def load_dashboard_data():
    try:
        result = load_all_data()
        
        # Handle both old (3 values) and new (2 values) versions
        if len(result) == 3:
            # Old version: listings, price_events, sold_events
            listings_df, price_events_df, _ = result
            logger.warning("Using old load_all_data() format (3 values). Update calculate_kpis.py")
        elif len(result) == 2:
            # New version: listings, price_events
            listings_df, price_events_df = result
        else:
            raise ValueError(f"Unexpected return values from load_all_data(): {len(result)}")
        
        return listings_df, price_events_df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None

listings_df, price_events_df = load_dashboard_data()

if listings_df is None:
    st.stop()

# Sidebar
st.sidebar.title("Market Intelligence")
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

# FIXED: Data Summary with correct counts
st.sidebar.markdown("### Data Summary")

active_count = len(listings_df[listings_df['status'] == 'active'])
sold_count = len(listings_df[listings_df['status'] == 'sold'])
total_count = len(listings_df)

st.sidebar.metric("Total Listings", f"{total_count:,}")
st.sidebar.caption(f"Unique items tracked")

st.sidebar.metric("Active Items", f"{active_count:,}")
st.sidebar.caption("Currently listed")

st.sidebar.metric("Sold Items", f"{sold_count:,}")
st.sidebar.caption("Detected sales")

st.sidebar.metric("Price Changes", f"{len(price_events_df):,}")

if 'scrape_timestamp' in listings_df.columns:
    last_update = pd.to_datetime(listings_df['scrape_timestamp']).max()
    st.sidebar.info(f"Updated: {last_update.strftime('%Y-%m-%d %H:%M')}")

with st.sidebar.expander("ℹ️ About Data Tracking"):
    st.markdown("""
    **How we count items:**
    - **Total = Active + Sold** (unique items)
    - Items marked "sold" when missing ≥48h
    - DTS = (estimated_sold_at - first_seen_at)
    
    **Why tracked brands only in rankings?**
    Rankings focus on target brands (Nike, Zara, etc.)  
    Total database includes all marketplace brands.
    """)


def generate_enhanced_pdf(filtered_all, filtered_sold, brand, category, audience, season):
    """Generate PDF report without Vinted references"""
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
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Secondary Market Intelligence", 
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
        # Calculate DTS correctly
        filtered_sold_calc = filtered_sold.copy()
        filtered_sold_calc['estimated_sold_at'] = pd.to_datetime(filtered_sold_calc['last_seen_at']) + timedelta(hours=24)
        filtered_sold_calc['dts'] = (
            filtered_sold_calc['estimated_sold_at'] - pd.to_datetime(filtered_sold_calc['first_seen_at'])
        ).dt.total_seconds() / (24 * 3600)
        
        summary_data.append(['Median DTS', f"{filtered_sold_calc['dts'].median():.1f} days"])
        summary_data.append(['Mean DTS', f"{filtered_sold_calc['dts'].mean():.1f} days"])
        
        sold_30d = len(filtered_sold_calc[filtered_sold_calc['dts'] <= 30])
        st_rate = min((sold_30d / len(filtered_all)) * 100, 100.0)  # Cap at 100%
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
        
        st_rate = min((len(cond_sold) / len(cond_all)) * 100, 100.0) if len(cond_all) > 0 else 0
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
    
    # Footer
    footer_text = f"Report generated from Market Intelligence Dashboard | {len(filtered_all):,} items analyzed"
    story.append(Paragraph(footer_text, styles['Italic']))
    
    try:
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(f"PDF generation error: {e}")
        return None


# ============================================================================
# PAGE 1: OVERVIEW
# ============================================================================

if "Overview" in page:
    st.markdown(f'<p class="main-header">📊 Market Overview</p>', unsafe_allow_html=True)
    
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
    
    brands = safe_sorted(filtered_for_condition['brand_norm'])
    
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
                'Liquidity Score': kpis['liquidity']['score'],
                'Grade': kpis['liquidity']['grade'],
                'DTS (days)': kpis['dts']['median'],
                'Sell-Through 30d (%)': kpis['sell_through_30d']['percentage'],
                'Total Items': kpis['sell_through_30d']['total_items'],
                'Sold Items': kpis['sell_through_30d']['total_sold']
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
            """)
            
            st.info(f"""
            **Why {len(liquidity_df)} brands?**
            
            This shows tracked target brands.  
            Total database: {total_count:,} items (all brands)
            """)
        
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
        
        st.markdown("---")
        st.subheader("Key Insights")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            top_brand = liquidity_df.iloc[0]
            st.metric("Most Liquid", top_brand['Brand'], f"Score: {top_brand['Liquidity Score']:.1f}")
        
        with col2:
            fastest = liquidity_df.loc[liquidity_df['DTS (days)'].idxmin()]
            st.metric("Fastest DTS", fastest['Brand'], f"{fastest['DTS (days)']:.1f} days")
        
        with col3:
            best_st = liquidity_df.loc[liquidity_df['Sell-Through 30d (%)'].idxmax()]
            st.metric("Best Sell-Through", best_st['Brand'], f"{best_st['Sell-Through 30d (%)']:.1f}%")
    else:
        st.warning("Not enough data with selected filters")

# ============================================================================
# PAGE 2: BRAND·CATEGORY ANALYSIS
# ============================================================================

elif "Brand·Category Analysis" in page:
    st.markdown(f'<p class="main-header">🔍 Brand·Category Analysis</p>', unsafe_allow_html=True)
    
    st.info("Analyzing both sold AND unsold items for accurate sell-through calculations")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        brands = ['All'] + safe_sorted(listings_df['brand_norm'])
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
    
    # Filter all listings
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
        st.warning("No items match the selected filters")
        st.stop()
    
    # Get sold subset
    filtered_sold = filtered_all[filtered_all['status'] == 'sold'].copy()
    
    # Calculate DTS for sold items
    if len(filtered_sold) > 0:
        filtered_sold['estimated_sold_at'] = pd.to_datetime(filtered_sold['last_seen_at']) + timedelta(hours=24)
        filtered_sold['dts_calc'] = (
            filtered_sold['estimated_sold_at'] - pd.to_datetime(filtered_sold['first_seen_at'])
        ).dt.total_seconds() / (24 * 3600)
    
    # KPI Cards
    st.subheader("Overall KPIs")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Items", f"{len(filtered_all):,}")
        st.caption("Active + Sold")
    
    with col2:
        st.metric("Sold Items", f"{len(filtered_sold):,}")
        st.caption(f"({len(filtered_sold)/len(filtered_all)*100:.1f}% of total)")
    
    with col3:
        if len(filtered_sold) > 0 and 'dts_calc' in filtered_sold.columns:
            median_dts = filtered_sold['dts_calc'].median()
            st.metric("Median DTS", f"{median_dts:.1f} days")
            st.caption("From first seen to sold")
        else:
            st.metric("Median DTS", "N/A")
            st.caption("No sold items yet")
    
    with col4:
        if len(filtered_sold) > 0 and 'dts_calc' in filtered_sold.columns:
            sold_30d = len(filtered_sold[filtered_sold['dts_calc'] <= 30])
            st_rate = min((sold_30d / len(filtered_all)) * 100, 100.0)  # Cap at 100%
            st.metric("30d Sell-Through", f"{st_rate:.1f}%")
            st.caption(f"{sold_30d}/{len(filtered_all)} items")
        else:
            st.metric("30d Sell-Through", "0.0%")
            st.caption("No sales yet")
    
    st.markdown("---")
    
    # Charts
    st.subheader("Analysis by Condition")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Price Distribution (All Items)")
        
        fig = go.Figure()
        
        for condition in sorted(filtered_all['condition_bucket'].unique()):
            cond_df = filtered_all[filtered_all['condition_bucket'] == condition]
            if len(cond_df) > 0:
                fig.add_trace(go.Box(
                    y=cond_df['price'],
                    name=condition,
                    boxmean='sd',
                    marker_color=PRIMARY_BLUE
                ))
        
        fig.update_layout(
            yaxis_title="Price (EUR)",
            xaxis_title="Condition",
            height=400,
            showlegend=True,
            plot_bgcolor='white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### Items Count by Condition")
        
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
            xaxis_title="Condition",
            height=400,
            barmode='stack',
            plot_bgcolor='white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Sell-through by condition
    st.markdown("### 30-Day Sell-Through by Condition")
    
    st_by_condition = []
    for condition in sorted(filtered_all['condition_bucket'].unique()):
        all_cond = filtered_all[filtered_all['condition_bucket'] == condition]
        sold_cond = filtered_sold[filtered_sold['condition_bucket'] == condition] if len(filtered_sold) > 0 else pd.DataFrame()
        
        if len(all_cond) > 0:
            sold_30d = len(sold_cond[sold_cond['dts_calc'] <= 30]) if 'dts_calc' in sold_cond.columns and len(sold_cond) > 0 else 0
            st_rate = min((sold_30d / len(all_cond)) * 100, 100.0)  # Cap at 100%
            
            st_by_condition.append({
                'condition': condition,
                'sell_through': st_rate,
                'sold_30d': sold_30d,
                'total': len(all_cond)
            })
    
    if st_by_condition:
        st_df = pd.DataFrame(st_by_condition)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=st_df['condition'],
            y=st_df['sell_through'],
            text=[f"{x:.1f}%<br>({s}/{t})" for x, s, t in zip(st_df['sell_through'], st_df['sold_30d'], st_df['total'])],
            textposition='outside',
            marker_color=PRIMARY_BLUE,
            hovertemplate='<b>%{x}</b><br>Sell-Through: %{y:.1f}%<br><extra></extra>'
        ))
        
        fig.update_layout(
            yaxis_title="Sell-Through Rate (%)",
            xaxis_title="Condition",
            yaxis_range=[0, min(max(st_df['sell_through']) * 1.2, 100)],
            height=400,
            showlegend=False,
            plot_bgcolor='white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.caption("**Formula**: (Items sold ≤30d) / (Total items in segment) × 100")
    
    # Data table
    st.markdown("---")
    st.subheader("Detailed Data")
    
    tab1, tab2 = st.tabs(["Sold Items", "Active Items"])
    
    with tab1:
        if len(filtered_sold) > 0:
            display_cols = ['brand_norm', 'category_norm', 'condition_bucket', 'price', 'first_seen_at', 'last_seen_at']
            display_cols = [col for col in display_cols if col in filtered_sold.columns]
            st.dataframe(filtered_sold[display_cols].head(100), use_container_width=True, hide_index=True)
        else:
            st.info("No sold items in this segment")
    
    with tab2:
        active_items = filtered_all[filtered_all['status'] == 'active']
        if len(active_items) > 0:
            display_cols = ['brand_norm', 'category_norm', 'condition_bucket', 'price', 'first_seen_at', 'last_seen_at']
            display_cols = [col for col in display_cols if col in active_items.columns]
            st.dataframe(active_items[display_cols].head(100), use_container_width=True, hide_index=True)
        else:
            st.info("No active items in this segment")
    
    # PDF Generation
    st.markdown("---")
    st.subheader("Generate PDF Report")
    
    if st.button("Generate Enhanced PDF", type="primary"):
        with st.spinner("Generating PDF..."):
            try:
                pdf_buffer = generate_enhanced_pdf(
                    filtered_all, filtered_sold,
                    brand_filter, category_filter, audience_filter, season_filter
                )
                
                if pdf_buffer:
                    filename = f"market_analysis_{datetime.now().strftime('%Y%m%d')}.pdf"
                    if brand_filter:
                        filename = f"{brand_filter.lower().replace(' ', '_')}_{filename}"
                    
                    st.download_button(
                        label="📥 Download PDF Report",
                        data=pdf_buffer,
                        file_name=filename,
                        mime="application/pdf"
                    )
                    st.success(f"✅ Generated: {filename}")
                
            except Exception as e:
                st.error(f"❌ Error generating PDF: {e}")

# ============================================================================
# PAGE 3: PRICE CALCULATOR
# ============================================================================

elif "Price Calculator" in page:
    st.markdown(f'<p class="main-header">💰 Smart Price Calculator</p>', unsafe_allow_html=True)
    
    st.markdown("Get pricing recommendations and estimated time-to-sell")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Item Details")
        
        calc_brand = st.selectbox(
            "Brand",
            safe_sorted(listings_df['brand_norm']),
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
        
        calc_condition = st.selectbox(
            "Condition",
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
        st.subheader("Market Intelligence")
        
        # Filter by all criteria
        calc_filtered = listings_df[
            (listings_df['brand_norm'] == calc_brand) &
            (listings_df['category_norm'] == calc_category) &
            (listings_df['audience'] == calc_audience) &
            (listings_df['condition_bucket'] == calc_condition)
        ]
        
        if len(calc_filtered) > 0:
            st.success(f"✅ Found {len(calc_filtered):,} comparable items")
            
            # Price range
            p25 = calc_filtered['price'].quantile(0.25)
            p50 = calc_filtered['price'].median()
            p75 = calc_filtered['price'].quantile(0.75)
            
            st.markdown("### 💵 Recommended Price Range")
            
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                st.metric("Budget", f"€{p25:.2f}", "P25")
            with col_b:
                st.metric("Market", f"€{p50:.2f}", "Median")
            with col_c:
                st.metric("Premium", f"€{p75:.2f}", "P75")
            
            # Time to sell
            calc_sold = calc_filtered[calc_filtered['status'] == 'sold']
            
            if len(calc_sold) > 0 and 'first_seen_at' in calc_sold.columns:
                calc_sold = calc_sold.copy()
                calc_sold['estimated_sold_at'] = pd.to_datetime(calc_sold['last_seen_at']) + timedelta(hours=24)
                calc_sold['dts_calc'] = (
                    calc_sold['estimated_sold_at'] - pd.to_datetime(calc_sold['first_seen_at'])
                ).dt.total_seconds() / (24 * 3600)
                
                dts_median = calc_sold['dts_calc'].median()
                dts_p25 = calc_sold['dts_calc'].quantile(0.25)
                dts_p75 = calc_sold['dts_calc'].quantile(0.75)
                
                st.markdown("### ⏱️ Estimated Time to Sell")
                st.info(f"""
                **Median**: {dts_median:.0f} days  
                **Fast (P25)**: {dts_p25:.0f} days  
                **Slow (P75)**: {dts_p75:.0f} days
                """)
                
                if dts_median < 10:
                    st.success("🔥 High demand! Premium pricing recommended")
                elif dts_median < 20:
                    st.info("✅ Good demand. Market price recommended")
                else:
                    st.warning("⏳ Slower sales. Consider budget pricing")
            
            # Price estimator
            st.markdown("---")
            st.markdown("### Your Price Estimator")
            
            your_price = st.number_input(
                "Your asking price (EUR)",
                min_value=1.0,
                max_value=1000.0,
                value=float(p50),
                step=1.0
            )
            
            st.markdown("#### Price Positioning")
            
            if your_price <= p25:
                percentile = "Budget Tier"
                emoji = "🟢"
                desc = "Bottom 25% - Fast sale expected"
            elif your_price <= p50:
                percentile = "Below Market"
                emoji = "🟡"
                desc = "25-50% range - Good value"
            elif your_price <= p75:
                percentile = "Above Market"
                emoji = "🟠"
                desc = "50-75% range - Premium pricing"
            else:
                percentile = "Premium Tier"
                emoji = "🔴"
                desc = "Top 25% - Slower sale possible"
            
            st.markdown(f"""
            <div style='padding: 1rem; background-color: #f0f2f6; border-radius: 0.5rem; border-left: 4px solid {PRIMARY_BLUE};'>
                <h3 style='margin: 0; color: {PRIMARY_BLUE};'>{emoji} {percentile}</h3>
                <p style='margin: 0.5rem 0 0 0; color: #666;'>{desc}</p>
                <p style='margin: 0.5rem 0 0 0; font-size: 0.9rem; color: #888;'>
                    Your price: <strong>€{your_price:.2f}</strong> | Market median: <strong>€{p50:.2f}</strong>
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Estimated DTS based on price
            if len(calc_sold) > 0 and 'dts_calc' in calc_sold.columns:
                st.markdown("#### Estimated Days to Sell")
                
                if your_price <= p25:
                    estimated_dts = dts_p25
                    speed = "Fast"
                elif your_price <= p50:
                    estimated_dts = dts_median
                    speed = "Average"
                elif your_price <= p75:
                    estimated_dts = dts_p75
                    speed = "Slower"
                else:
                    estimated_dts = dts_p75 * 1.3
                    speed = "Slow"
                
                st.metric("", f"{estimated_dts:.0f} days", speed)
        
        else:
            st.error("❌ No comparable items found for this combination")

# ============================================================================
# PAGE 4: DOWNLOADS (FIXED - Remove sensitive columns)
# ============================================================================

elif "Downloads" in page:
    st.markdown(f'<p class="main-header">📥 Downloads</p>', unsafe_allow_html=True)
    
    st.info("⚠️ Note: listing_url and scrape_filename columns removed for privacy")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("CSV Exports")
        
        # FIXED: Remove sensitive columns
        columns_to_remove = ['listing_url', 'scrape_filename']
        
        # Active items
        active_df = listings_df[listings_df['status'] == 'active'].copy()
        for col in columns_to_remove:
            if col in active_df.columns:
                active_df = active_df.drop(columns=[col])
        
        csv_active = active_df.to_csv(index=False)
        st.download_button(
            "📄 Download Active Items (CSV)",
            csv_active,
            f"active_listings_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )
        st.info(f"{len(active_df):,} items")
        
        # Sold items
        sold_df = listings_df[listings_df['status'] == 'sold'].copy()
        if len(sold_df) > 0:
            for col in columns_to_remove:
                if col in sold_df.columns:
                    sold_df = sold_df.drop(columns=[col])
            
            csv_sold = sold_df.to_csv(index=False)
            st.download_button(
                "📄 Download Sold Items (CSV)",
                csv_sold,
                f"sold_listings_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )
            st.info(f"{len(sold_df):,} items")
        
        # Price changes
        if len(price_events_df) > 0:
            csv_prices = price_events_df.to_csv(index=False)
            st.download_button(
                "📄 Download Price Changes (CSV)",
                csv_prices,
                f"price_changes_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )
            st.info(f"{len(price_events_df):,} events")
    
    with col2:
        st.subheader("Data Dictionary")
        
        st.markdown("""
        **Columns included:**
        - `item_id`: Unique identifier
        - `brand_norm`: Normalized brand name
        - `category_norm`: Normalized category
        - `condition_bucket`: Condition tier
        - `price`: Price in EUR
        - `status`: active/sold
        - `first_seen_at`: First detection date
        - `last_seen_at`: Last seen date
        - `audience`: Target demographic
        
        **Columns removed for privacy:**
        - ~~listing_url~~ (platform reference)
        - ~~scrape_filename~~ (internal tracking)
        """)
        
        st.markdown("---")
        st.subheader("Generate Custom Reports")
        st.info("Use 'Brand·Category Analysis' page to generate PDF reports with visualizations")

# Footer
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p><strong>Market Intelligence Dashboard</strong> | {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    <p style='font-size: 0.8rem;'>Secondary market analytics platform</p>
</div>
""", unsafe_allow_html=True)