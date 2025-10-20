"""
Market Intelligence Dashboard - COMPLETE FINAL VERSION
Features:
1. Fast loading with optimizations
2. Client-required KPIs: Total Items, Median Price, DTS, Sell-Through
3. Three charts by condition: Price, DTS, Sell-Through
4. PDF generation with embedded chart images
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
import sys
from datetime import datetime, timedelta
import io
import tempfile
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.platypus import Image as RLImage
from reportlab.lib.enums import TA_CENTER
import plotly.io as pio

# CLIENT COLORS
PRIMARY_BLUE = '#006064'
ACCENT_CYAN = '#00FFFF'

def safe_sorted(series):
    """Safely sort a pandas series, removing None/NaN values"""
    return sorted([x for x in series.dropna().unique() if x is not None])

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

# ============================================================================
# DATA LOADING - OPTIMIZED
# ============================================================================

@st.cache_data(ttl=7200, show_spinner=False)
def load_listings_data():
    """Load listings data efficiently"""
    try:
        DATA_DIR = Path("data/processed")
        listings_file = DATA_DIR / "listings.parquet"
        
        if not listings_file.exists():
            return None
        
        df = pd.read_parquet(listings_file)
        
        # Convert dates
        for col in ['first_seen_at', 'last_seen_at', 'published_at', 'scrape_timestamp']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

@st.cache_data(ttl=7200, show_spinner=False)
def load_price_events_data():
    """Load price events data"""
    try:
        DATA_DIR = Path("data/processed")
        price_file = DATA_DIR / "price_events.parquet"
        
        if not price_file.exists():
            return pd.DataFrame()
        
        return pd.read_parquet(price_file)
    except:
        return pd.DataFrame()

# ============================================================================
# PDF GENERATION WITH CHARTS
# ============================================================================

def generate_pdf_with_charts(filtered_all, filtered_sold, metrics_df, brand, category, audience, season):
    """Generate PDF with KPIs, tables, and chart images"""
    
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
    filter_parts = [f for f in [brand, category, audience, season] if f and f != 'All']
    title_text = f"Market Analysis Report - {' · '.join(filter_parts)}" if filter_parts else "Market Analysis Report"
    
    story.append(Paragraph(title_text, title_style))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Market Intelligence Dashboard", 
        styles['Normal']
    ))
    story.append(Spacer(1, 0.2*inch))
    
    # Summary KPIs
    story.append(Paragraph("Key Performance Indicators", heading_style))
    
    median_price = filtered_all['price'].median()
    
    if len(filtered_sold) > 0:
        sold_calc = filtered_sold.copy()
        sold_calc['estimated_sold_at'] = pd.to_datetime(sold_calc['last_seen_at']) + timedelta(hours=24)
        sold_calc['dts'] = (
            sold_calc['estimated_sold_at'] - pd.to_datetime(sold_calc['first_seen_at'])
        ).dt.total_seconds() / (24 * 3600)
        
        median_dts = sold_calc['dts'].median()
        sold_30d = len(sold_calc[sold_calc['dts'] <= 30])
        st_rate = min((sold_30d / len(filtered_all)) * 100, 100.0)
    else:
        median_dts = None
        st_rate = 0.0
    
    kpi_data = [
        ['Metric', 'Value'],
        ['Total Items Analyzed', f"{len(filtered_all):,}"],
        ['Active Listings', f"{len(filtered_all[filtered_all['status']=='active']):,}"],
        ['Sold Items', f"{len(filtered_sold):,}"],
        ['Median Price', f"EUR {median_price:.2f}"],
        ['Median DTS', f"{median_dts:.1f} days" if median_dts else 'N/A'],
        ['30-Day Sell-Through Rate', f"{st_rate:.1f}%"]
    ]
    
    kpi_table = Table(kpi_data, colWidths=[3.5*inch, 3*inch])
    kpi_table.setStyle(TableStyle([
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
    
    story.append(kpi_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Condition Summary Table
    story.append(Paragraph("Analysis by Condition", heading_style))
    
    condition_data = [['Condition', 'Total Items', 'Median Price', 'Median DTS', 'Sell-Through']]
    
    for _, row in metrics_df.iterrows():
        condition_data.append([
            row['condition'],
            f"{int(row['total_items']):,}",
            f"EUR {row['median_price']:.2f}",
            f"{row['median_dts']:.1f}d" if pd.notna(row['median_dts']) else "N/A",
            f"{row['sell_through']:.1f}%"
        ])
    
    cond_table = Table(condition_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    cond_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(PRIMARY_BLUE)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    
    story.append(cond_table)
    story.append(PageBreak())
    
    # Charts as Images
    story.append(Paragraph("Visualizations by Condition", heading_style))
    story.append(Spacer(1, 0.2*inch))
    
    try:
        # Chart 1: Median Price
        fig_price = go.Figure()
        fig_price.add_trace(go.Bar(
            x=metrics_df['condition'],
            y=metrics_df['median_price'],
            text=[f"€{x:.2f}" for x in metrics_df['median_price']],
            textposition='outside',
            marker_color=PRIMARY_BLUE
        ))
        fig_price.update_layout(
            title="Median Price by Condition (EUR)",
            xaxis_title="Condition",
            yaxis_title="Price (EUR)",
            height=350,
            width=700,
            showlegend=False,
            plot_bgcolor='white'
        )
        
        img_price = pio.to_image(fig_price, format='png', width=700, height=350)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            tmp.write(img_price)
            tmp_path_price = tmp.name
        
        story.append(RLImage(tmp_path_price, width=7*inch, height=3.5*inch))
        story.append(Spacer(1, 0.2*inch))
        
        # Chart 2: Median DTS
        dts_data = metrics_df[metrics_df['median_dts'].notna()]
        if len(dts_data) > 0:
            fig_dts = go.Figure()
            fig_dts.add_trace(go.Bar(
                x=dts_data['condition'],
                y=dts_data['median_dts'],
                text=[f"{x:.1f}d" for x in dts_data['median_dts']],
                textposition='outside',
                marker_color='#0097A7'
            ))
            fig_dts.update_layout(
                title="Median Days-to-Sell by Condition",
                xaxis_title="Condition",
                yaxis_title="Days",
                height=350,
                width=700,
                showlegend=False,
                plot_bgcolor='white'
            )
            
            img_dts = pio.to_image(fig_dts, format='png', width=700, height=350)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                tmp.write(img_dts)
                tmp_path_dts = tmp.name
            
            story.append(RLImage(tmp_path_dts, width=7*inch, height=3.5*inch))
            story.append(Spacer(1, 0.2*inch))
        
        # Chart 3: Sell-Through
        fig_st = go.Figure()
        fig_st.add_trace(go.Bar(
            x=metrics_df['condition'],
            y=metrics_df['sell_through'],
            text=[f"{x:.1f}%" for x in metrics_df['sell_through']],
            textposition='outside',
            marker_color='#00ACC1'
        ))
        fig_st.update_layout(
            title="30-Day Sell-Through Rate by Condition (%)",
            xaxis_title="Condition",
            yaxis_title="Sell-Through (%)",
            height=350,
            width=700,
            showlegend=False,
            plot_bgcolor='white'
        )
        
        img_st = pio.to_image(fig_st, format='png', width=700, height=350)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            tmp.write(img_st)
            tmp_path_st = tmp.name
        
        story.append(RLImage(tmp_path_st, width=7*inch, height=3.5*inch))
        
    except Exception as e:
        story.append(Paragraph(f"Note: Charts could not be generated ({str(e)})", styles['Normal']))
    
    # Footer
    story.append(Spacer(1, 0.3*inch))
    methodology = """
    <b>Methodology:</b><br/>
    • DTS = (estimated_sold_at - first_seen_at) where estimated_sold_at = last_seen_at + 24h<br/>
    • Sell-Through = (items sold ≤30 days) / (total items) × 100<br/>
    • Sold detection: Items missing ≥48 hours
    """
    story.append(Paragraph(methodology, styles['Normal']))
    
    try:
        doc.build(story)
        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(f"PDF generation error: {e}")
        return None

# ============================================================================
# LOAD DATA
# ============================================================================

with st.spinner('⚡ Loading data...'):
    listings_df = load_listings_data()
    price_events_df = load_price_events_data()

if listings_df is None:
    st.error("❌ No data found. Please run data processing pipeline.")
    st.info("""
    **Steps:**
    1. Run: `python vinted_scraper.py`
    2. Run: `python process_data.py`
    3. Refresh this page
    """)
    st.stop()

# ============================================================================
# SIDEBAR
# ============================================================================

st.sidebar.title("Market Intelligence")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    [
        "📊 Overview",
        "🔍 Brand·Category Analysis",
        "💰 Price Calculator",
        "📥 Downloads"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📈 Data Summary")

active_count = len(listings_df[listings_df['status'] == 'active'])
sold_count = len(listings_df[listings_df['status'] == 'sold'])
total_count = len(listings_df)

st.sidebar.metric("Total Listings", f"{total_count:,}")
st.sidebar.metric("Active Items", f"{active_count:,}")
st.sidebar.metric("Sold Items", f"{sold_count:,}")

if 'scrape_timestamp' in listings_df.columns:
    last_update = pd.to_datetime(listings_df['scrape_timestamp']).max()
    st.sidebar.info(f"Updated: {last_update.strftime('%Y-%m-%d %H:%M')}")

# ============================================================================
# PAGE 1: OVERVIEW
# ============================================================================

if "Overview" in page:
    st.markdown(f'<p class="main-header">📊 Market Overview</p>', unsafe_allow_html=True)
    st.markdown("Brand liquidity rankings")
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
    
    # Top 15 brands by volume
    brand_counts = filtered['brand_norm'].value_counts().head(15)
    top_brands = brand_counts.index.tolist()
    
    if len(top_brands) == 0:
        st.warning("No brands found with selected filters")
        st.stop()
    
    # Calculate KPIs
    with st.spinner(f'Calculating KPIs for top {len(top_brands)} brands...'):
        liquidity_data = []
        progress_bar = st.progress(0)
        
        for idx, brand in enumerate(top_brands):
            brand_data = filtered[filtered['brand_norm'] == brand]
            brand_sold = brand_data[brand_data['status'] == 'sold'].copy()
            
            if len(brand_data) < 10:
                continue
            
            # Calculate DTS
            if len(brand_sold) > 0:
                brand_sold['estimated_sold_at'] = pd.to_datetime(brand_sold['last_seen_at']) + timedelta(hours=24)
                brand_sold['dts'] = (
                    brand_sold['estimated_sold_at'] - pd.to_datetime(brand_sold['first_seen_at'])
                ).dt.total_seconds() / (24 * 3600)
                
                median_dts = brand_sold['dts'].median()
                sold_30d = len(brand_sold[brand_sold['dts'] <= 30])
                st_rate = min((sold_30d / len(brand_data)) * 100, 100.0)
                
                # Liquidity score
                st_normalized = min(st_rate / 50, 1.0)
                sell_through_score = st_normalized * 50
                dts_score = max(0, (1 - (median_dts / 30)) * 50)
                liq_score = min(sell_through_score + dts_score, 100.0)
                
                if liq_score >= 75:
                    grade = 'A'
                elif liq_score >= 50:
                    grade = 'B'
                elif liq_score >= 25:
                    grade = 'C'
                else:
                    grade = 'D'
                
                liquidity_data.append({
                    'Brand': brand,
                    'Liquidity Score': liq_score,
                    'Grade': grade,
                    'DTS (days)': median_dts,
                    'Sell-Through (%)': st_rate,
                    'Total Items': len(brand_data),
                    'Sold Items': len(brand_sold)
                })
            
            progress_bar.progress((idx + 1) / len(top_brands))
        
        progress_bar.empty()
    
    if liquidity_data:
        liquidity_df = pd.DataFrame(liquidity_data).sort_values('Liquidity Score', ascending=False)
        
        st.subheader("Brand Liquidity Ranking")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
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
            st.info(f"Showing top {len(liquidity_df)} brands")
        
        # Chart
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
        st.warning("Not enough data to calculate rankings")

# ============================================================================
# PAGE 2: BRAND·CATEGORY ANALYSIS
# ============================================================================

elif "Brand·Category Analysis" in page:
    st.markdown(f'<p class="main-header">🔍 Brand·Category Analysis</p>', unsafe_allow_html=True)
    st.info("Analyzing market performance by condition segment")
    
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
    
    filtered_sold = filtered_all[filtered_all['status'] == 'sold'].copy()
    
    # Calculate DTS for sold items
    if len(filtered_sold) > 0:
        filtered_sold['estimated_sold_at'] = pd.to_datetime(filtered_sold['last_seen_at']) + timedelta(hours=24)
        filtered_sold['dts_calc'] = (
            filtered_sold['estimated_sold_at'] - pd.to_datetime(filtered_sold['first_seen_at'])
        ).dt.total_seconds() / (24 * 3600)
    
    st.markdown("---")
    
    # KPI CARDS - CLIENT REQUIREMENT
    st.subheader("Key Performance Indicators")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Items", f"{len(filtered_all):,}")
        st.caption("Active + Sold")
    
    with col2:
        median_price = filtered_all['price'].median()
        st.metric("Median Price", f"€{median_price:.2f}")
        st.caption("All conditions")
    
    with col3:
        if len(filtered_sold) > 0 and 'dts_calc' in filtered_sold.columns:
            median_dts = filtered_sold['dts_calc'].median()
            st.metric("Median DTS", f"{median_dts:.1f} days")
            st.caption("First seen → sold")
        else:
            st.metric("Median DTS", "N/A")
            st.caption("No sold items")
    
    with col4:
        if len(filtered_sold) > 0 and 'dts_calc' in filtered_sold.columns:
            sold_30d = len(filtered_sold[filtered_sold['dts_calc'] <= 30])
            st_rate = min((sold_30d / len(filtered_all)) * 100, 100.0)
            st.metric("30d Sell-Through", f"{st_rate:.1f}%")
            st.caption(f"{sold_30d}/{len(filtered_all)} items")
        else:
            st.metric("30d Sell-Through", "0.0%")
            st.caption("No sales yet")
    
    st.markdown("---")
    
    # CALCULATE METRICS BY CONDITION
    st.subheader("Analysis by Condition")
    
    condition_metrics = []
    for condition in sorted(filtered_all['condition_bucket'].unique()):
        cond_all = filtered_all[filtered_all['condition_bucket'] == condition]
        cond_sold = filtered_sold[filtered_sold['condition_bucket'] == condition] if len(filtered_sold) > 0 else pd.DataFrame()
        
        median_price_cond = cond_all['price'].median()
        
        if len(cond_sold) > 0 and 'dts_calc' in cond_sold.columns:
            median_dts_cond = cond_sold['dts_calc'].median()
            sold_30d_cond = len(cond_sold[cond_sold['dts_calc'] <= 30])
            st_rate_cond = min((sold_30d_cond / len(cond_all)) * 100, 100.0)
        else:
            median_dts_cond = None
            st_rate_cond = 0.0
        
        condition_metrics.append({
            'condition': condition,
            'total_items': len(cond_all),
            'median_price': median_price_cond,
            'median_dts': median_dts_cond,
            'sell_through': st_rate_cond
        })
    
    metrics_df = pd.DataFrame(condition_metrics)
    
    # CHART 1: MEDIAN PRICE BY CONDITION
    st.markdown("### 💰 Median Price by Condition")
    
    fig_price = go.Figure()
    fig_price.add_trace(go.Bar(
        x=metrics_df['condition'],
        y=metrics_df['median_price'],
        text=[f"€{x:.2f}" for x in metrics_df['median_price']],
        textposition='outside',
        marker_color=PRIMARY_BLUE,
        hovertemplate='<b>%{x}</b><br>Median Price: €%{y:.2f}<br><extra></extra>'
    ))
    
    fig_price.update_layout(
        xaxis_title="Condition",
        yaxis_title="Median Price (EUR)",
        height=400,
        showlegend=False,
        plot_bgcolor='white',
        yaxis_range=[0, metrics_df['median_price'].max() * 1.2]
    )
    
    st.plotly_chart(fig_price, use_container_width=True)
    
    # CHART 2: MEDIAN DTS BY CONDITION
    st.markdown("### ⏱️ Median Days-to-Sell by Condition")
    
    dts_data = metrics_df[metrics_df['median_dts'].notna()]
    
    if len(dts_data) > 0:
        fig_dts = go.Figure()
        fig_dts.add_trace(go.Bar(
            x=dts_data['condition'],
            y=dts_data['median_dts'],
            text=[f"{x:.1f}d" for x in dts_data['median_dts']],
            textposition='outside',
            marker_color='#0097A7',
            hovertemplate='<b>%{x}</b><br>Median DTS: %{y:.1f} days<br><extra></extra>'
        ))
        
        fig_dts.update_layout(
            xaxis_title="Condition",
            yaxis_title="Days to Sell",
            height=400,
            showlegend=False,
            plot_bgcolor='white',
            yaxis_range=[0, dts_data['median_dts'].max() * 1.2]
        )
        
        st.plotly_chart(fig_dts, use_container_width=True)
    else:
        st.info("No sold items to calculate DTS")
    
    # CHART 3: 30-DAY SELL-THROUGH BY CONDITION
    st.markdown("### 📈 30-Day Sell-Through Rate by Condition")
    
    fig_st = go.Figure()
    fig_st.add_trace(go.Bar(
        x=metrics_df['condition'],
        y=metrics_df['sell_through'],
        text=[f"{x:.1f}%" for x in metrics_df['sell_through']],
        textposition='outside',
        marker_color='#00ACC1',
        hovertemplate='<b>%{x}</b><br>Sell-Through: %{y:.1f}%<br><extra></extra>'
    ))
    
    fig_st.update_layout(
        xaxis_title="Condition",
        yaxis_title="Sell-Through Rate (%)",
        height=400,
        showlegend=False,
        plot_bgcolor='white',
        yaxis_range=[0, min(metrics_df['sell_through'].max() * 1.2, 100)]
    )
    
    st.plotly_chart(fig_st, use_container_width=True)
    st.caption("**Formula**: (Items sold ≤30d) / (Total items in segment) × 100")
    
    # SUMMARY TABLE
    st.markdown("---")
    st.subheader("Summary Table by Condition")
    
    summary_table = metrics_df.copy()
    summary_table.columns = ['Condition', 'Total Items', 'Median Price (EUR)', 'Median DTS (days)', 'Sell-Through (%)']
    summary_table['Median Price (EUR)'] = summary_table['Median Price (EUR)'].apply(lambda x: f"€{x:.2f}")
    summary_table['Median DTS (days)'] = summary_table['Median DTS (days)'].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "N/A")
    summary_table['Sell-Through (%)'] = summary_table['Sell-Through (%)'].apply(lambda x: f"{x:.1f}%")
    
    st.dataframe(summary_table, use_container_width=True, hide_index=True)
    
    # DATA PREVIEW
    st.markdown("---")
    st.subheader("Detailed Data Preview")
    
    tab1, tab2 = st.tabs(["Sold Items", "Active Items"])
    
    with tab1:
        if len(filtered_sold) > 0:
            display_cols = ['brand_norm', 'category_norm', 'condition_bucket', 'price', 'first_seen_at', 'last_seen_at']
            display_cols = [col for col in display_cols if col in filtered_sold.columns]
            st.dataframe(filtered_sold[display_cols].head(100), use_container_width=True, hide_index=True)
            st.caption(f"Showing first 100 of {len(filtered_sold):,} sold items")
        else:
            st.info("No sold items in this segment")
    
    with tab2:
        active_items = filtered_all[filtered_all['status'] == 'active']
        if len(active_items) > 0:
            display_cols = ['brand_norm', 'category_norm', 'condition_bucket', 'price', 'first_seen_at', 'last_seen_at']
            display_cols = [col for col in display_cols if col in active_items.columns]
            st.dataframe(active_items[display_cols].head(100), use_container_width=True, hide_index=True)
            st.caption(f"Showing first 100 of {len(active_items):,} active items")
        else:
            st.info("No active items in this segment")
    
    # PDF GENERATION
    st.markdown("---")
    st.subheader("📄 Generate PDF Report")
    
    st.info("Report will include: Summary KPIs, Condition Analysis Table, and Chart Images (Price, DTS, Sell-Through)")
    
    if st.button("🎨 Generate Enhanced PDF Report", type="primary"):
        with st.spinner("Generating PDF with charts..."):
            try:
                pdf_buffer = generate_pdf_with_charts(
                    filtered_all, 
                    filtered_sold, 
                    metrics_df,
                    selected_brand, 
                    selected_category, 
                    selected_audience, 
                    selected_season
                )
                
                if pdf_buffer:
                    filename = f"market_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                    if selected_brand != 'All':
                        filename = f"{selected_brand.lower().replace(' ', '_')}_{filename}"
                    
                    st.download_button(
                        label="📥 Download PDF Report",
                        data=pdf_buffer,
                        file_name=filename,
                        mime="application/pdf"
                    )
                    st.success(f"✅ Generated: {filename}")
                else:
                    st.error("Failed to generate PDF")
                
            except Exception as e:
                st.error(f"❌ Error generating PDF: {e}")
                import traceback
                st.code(traceback.format_exc())

# ============================================================================
# PAGE 3: PRICE CALCULATOR
# ============================================================================

elif "Price Calculator" in page:
    st.markdown(f'<p class="main-header">💰 Smart Price Calculator</p>', unsafe_allow_html=True)
    st.markdown("Get pricing recommendations based on market data")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Item Details")
        
        calc_brand = st.selectbox("Brand", safe_sorted(listings_df['brand_norm']), key="calc_brand")
        calc_category = st.selectbox("Category", safe_sorted(listings_df['category_norm']), key="calc_category")
        calc_audience = st.selectbox("Audience", safe_sorted(listings_df['audience']), key="calc_audience")
        calc_condition = st.selectbox("Condition", safe_sorted(listings_df['condition_bucket']), key="calc_condition")
        
        if 'season' in listings_df.columns:
            seasons = ['Any'] + safe_sorted(listings_df['season'])
            calc_season = st.selectbox("Season", seasons, key="calc_season")
            calc_season = None if calc_season == 'Any' else calc_season
        else:
            calc_season = None
    
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
            
            st.markdown("### 💵 Recommended Price Range")
            
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                st.metric("Budget", f"€{p25:.2f}", "P25")
            with col_b:
                st.metric("Market", f"€{p50:.2f}", "Median")
            with col_c:
                st.metric("Premium", f"€{p75:.2f}", "P75")
            
            # Time to sell estimate
            calc_sold = calc_filtered[calc_filtered['status'] == 'sold'].copy()
            
            if len(calc_sold) > 0 and 'first_seen_at' in calc_sold.columns:
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
# PAGE 4: DOWNLOADS
# ============================================================================

elif "Downloads" in page:
    st.markdown(f'<p class="main-header">📥 Downloads</p>', unsafe_allow_html=True)
    
    st.info("⚠️ Note: listing_url and scrape_filename columns removed for privacy")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("CSV Exports")
        
        # Remove sensitive columns
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