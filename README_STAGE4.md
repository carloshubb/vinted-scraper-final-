# Stage 4: Streamlit Dashboard - Complete Guide

## 🎨 Overview

Stage 4 delivers a professional, interactive dashboard with 4 main pages:

1. **🏠 Overview** - Liquidity ranking by brand
2. **📈 Brand·Category Analysis** - Deep dive with filters and charts
3. **🧮 Price Calculator** - Smart pricing recommendations
4. **📥 Downloads** - Export data as CSV

---

## 🚀 Quick Start

### **1. Install Dashboard Dependencies**

```bash
pip install streamlit plotly
```

Or use the requirements file:

```bash
pip install -r requirements.txt
```

### **2. Launch the Dashboard**

```bash
streamlit run app.py
```

The dashboard will open in your browser at `http://localhost:8501`

---

## 📊 Dashboard Pages

### **Page 1: Overview - Liquidity Ranking** 🏠

**What it shows:**
- Liquidity ranking table (all brands)
- Color-coded grades (A/B/C/D)
- Interactive bar chart
- Key insights (top performer, fastest selling, best sell-through)

**Key Features:**
- Automatic ranking by liquidity score
- Visual grade indicators
- Summary metrics in sidebar

**Client Value:**
> "Which brands are most liquid in the market?"

---

### **Page 2: Brand·Category Analysis** 📈

**What it shows:**
- 4 KPI cards (DTS, Sell-Through, Price, Liquidity)
- Price distribution boxplot (active vs sold)
- Sales velocity metrics vs benchmarks
- Price histogram
- Item listings table

**Filters:**
- Brand
- Category
- Audience
- Season (if available)

**Key Features:**
- Real-time filtering
- Interactive Plotly charts
- Benchmark comparisons
- Drill-down to item level

**Client Value:**
> "How is Zara performing vs Nike in dresses?"

---

### **Page 3: Price Calculator** 🧮

**What it shows:**
- Recommended price ranges (P25/P50/P75)
- Estimated days to sell
- Pricing strategy recommendations
- Custom price evaluator

**How it works:**
1. User selects: Brand, Category, Audience, Season
2. System calculates KPIs for that combination
3. Shows 3 price tiers:
   - **Budget**: 25th percentile (fast sale)
   - **Market**: 50th percentile (median)
   - **Premium**: 75th percentile (slower sale)

**Smart Features:**
- Price positioning indicator (🟢🟡🟠🔴)
- Dynamic DTS estimates based on pricing
- Strategy recommendations based on demand

**Client Value:**
> "What should I price my Zara dress at to sell within 10 days?"

---

### **Page 4: Downloads** 📥

**What it provides:**
- Active listings CSV export
- Sold items CSV export
- Price changes CSV export
- KPI summary report (all brands)

**Export Format:**
All exports include timestamp in filename:
- `vinted_active_listings_20251006.csv`
- `vinted_sold_items_20251006.csv`
- `vinted_kpi_summary_20251006.csv`

**Client Value:**
> "Export data for Excel analysis and stakeholder reports"

---

## 🎨 Dashboard Features

### **✨ Interactive Elements**

1. **Sidebar Navigation**
   - Page selector with icons
   - Real-time data summary
   - Last update timestamp

2. **Dynamic Filtering**
   - Brand, Category, Audience, Season filters
   - Instant chart updates
   - Filter combinations preserved

3. **Hover Tooltips**
   - All charts show detailed info on hover
   - Price ranges, counts, percentages

4. **Color Coding**
   - Grade A: Green (excellent)
   - Grade B: Blue (good)
   - Grade C: Yellow (fair)
   - Grade D: Red (poor)

5. **Responsive Layout**
   - Wide layout mode
   - Auto-adjusting columns
   - Mobile-friendly

---

## 🔧 Configuration

### **Data Refresh**

The dashboard caches data for 1 hour (3600 seconds). To force refresh:

```python
# In app.py, line 46:
@st.cache_data(ttl=3600)  # Change to lower value for more frequent updates
```

Or click **"Clear Cache"** in Streamlit's hamburger menu (⋮)

---

### **Custom Styling**

Edit the CSS in `app.py` (lines 24-38) to customize:

```python
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;      # Header size
        color: #1f77b4;         # Header color
    }
    .metric-card {
        background-color: #f0f2f6;  # Card background
    }
</style>
""", unsafe_allow_html=True)
```

---

### **Benchmark Values**

Industry benchmarks (line 391):

```python
'Benchmark': [14, 50]  # DTS: 14 days, Sell-Through: 50%
```

Adjust these based on your market research.

---

## 📊 Data Requirements

### **Minimum Data for Full Functionality**

| Page | Requirement | Why |
|------|-------------|-----|
| Overview | 50+ sold items per brand | Liquidity calculation |
| Analysis | Any listings | Price charts work |
| Calculator | 20+ items per combo | Price ranges |
| Downloads | Any data | Always works |

### **What Happens with Insufficient Data**

- **No sold items**: Shows "N/A" for DTS, Sell-Through, Liquidity
- **Few items (<10)**: Shows warning, calculations may be unreliable
- **No data for filters**: Shows "No data matching filters"

**Solution**: Run pipeline at least twice, 48 hours apart

---

## 🚀 Deployment Options

### **Option 1: Local (Development)**

```bash
streamlit run app.py
```

Access at `http://localhost:8501`

---

### **Option 2: Streamlit Cloud (Production)**

**Steps:**

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial dashboard"
   git push origin main
   ```

2. **Deploy on Streamlit Cloud**
   - Go to https://share.streamlit.io
   - Click "New app"
   - Connect GitHub repo
   - Set main file: `app.py`
   - Click "Deploy"

3. **Configure Secrets** (if needed)
   - Settings → Secrets
   - Add any API keys or credentials

**Free Tier:**
- ✅ Unlimited public apps
- ✅ 1GB RAM per app
- ✅ Auto-updates from GitHub

---

### **Option 3: Heroku / Railway / Render**

Create `setup.sh`:

```bash
mkdir -p ~/.streamlit/

echo "\
[server]\n\
headless = true\n\
port = $PORT\n\
enableCORS = false\n\
\n\
" > ~/.streamlit/config.toml
```

Create `Procfile`:

```
web: sh setup.sh && streamlit run app.py
```

---

## 🔄 Automation Integration

### **Scheduled Updates with GitHub Actions**

Your dashboard auto-refreshes when new data arrives. Combine with Stage 5 automation:

**`.github/workflows/scrape.yml`** (excerpt):

```yaml
- name: Run pipeline
  run: python run_pipeline.py

- name: Commit updated data
  run: |
    git add data/
    git commit -m "Auto update $(date)"
    git push
```

**Result**: Dashboard updates every 48 hours automatically!

---

## 💡 Usage Tips

### **For Presentations**

1. **Start with Overview page** - Show liquidity ranking
2. **Drill into top brand** - Use Analysis page filters
3. **Demo Calculator** - Live pricing example
4. **Show Downloads** - Export capability

### **For Daily Monitoring**

1. Bookmark the **Overview page**
2. Check liquidity changes
3. Look for grade changes (B→A or B→C)
4. Export weekly KPI summary

### **For Client Delivery**

1. **Screenshot Overview** - Liquidity ranking
2. **Export KPI Summary CSV** - Attach to email
3. **Calculator demo** - Show pricing tool
4. **Schedule monthly review** - Track trends

---

## 🐛 Troubleshooting

### **Issue: "Error loading data"**

**Cause**: Missing parquet files

**Solution**:
```bash
# Run pipeline first
python run_pipeline.py
```

---

### **Issue: All KPIs show "N/A"**

**Cause**: No sold items yet (only ran pipeline once)

**Solution**: Wait 48 hours, run pipeline again

---

### **Issue: "Module not found: streamlit"**

**Solution**:
```bash
pip install streamlit plotly
```

---

### **Issue: Dashboard is slow**

**Causes:**
1. Large dataset (>50k items)
2. Complex filters
3. Cache disabled

**Solutions:**
1. Reduce cache TTL: `@st.cache_data(ttl=1800)`
2. Sample data for development
3. Deploy to cloud (better resources)

---

### **Issue: Charts not displaying**

**Cause**: Plotly not installed

**Solution**:
```bash
pip install plotly
```

---

### **Issue: Unicode errors on Windows**

**Cause**: Console encoding issues

**Solution**: The dashboard works fine in browser (ignore console warnings)

---

## 📈 Performance Optimization

### **For Large Datasets (>10k items)**

```python
# Add sampling for development
@st.cache_data(ttl=3600)
def load_dashboard_data(sample=False):
    listings_df, price_events_df, sold_events_df = load_all_data()
    
    if sample:
        listings_df = listings_df.sample(n=1000)
    
    return listings_df, price_events_df, sold_events_df
```

### **Reduce KPI Calculation Time**

Cache KPI calculations:

```python
@st.cache_data(ttl=3600)
def get_cached_kpis(brand, category, audience, season):
    return calculate_all_kpis(brand, category, audience, season)
```

---

## 🎯 Next Steps

### **Enhancement Ideas**

1. **Add Time Series Charts**
   - Track price trends over time
   - Show liquidity score evolution

2. **Add Competitor Comparison**
   - Side-by-side brand metrics
   - Market share calculations

3. **Add Alerts**
   - Email when liquidity drops below threshold
   - Notify on significant price changes

4. **Add PDF Export**
   ```python
   pip install reportlab
   # Generate PDF reports
   ```

5. **Add Authentication**
   ```python
   # For client-specific dashboards
   pip install streamlit-authenticator
   ```

---

## 📊 Dashboard Metrics

### **What the Client Gets**

✅ **4 Complete Pages**
- Overview with liquidity ranking
- Brand analysis with filters
- Price calculator
- Data export functionality

✅ **Interactive Charts**
- Boxplots, bar charts, histograms
- Hover tooltips
- Responsive design

✅ **Real-time Filtering**
- Brand, Category, Audience, Season
- Instant updates

✅ **CSV Downloads**
- Active listings
- Sold items
- Price changes
- KPI summaries

✅ **Professional Design**
- Clean layout
- Color-coded grades
- Mobile-friendly

---

## 🎉 Stage 4 Complete!

You now have a **production-ready dashboard** that:

✅ Displays all required KPIs  
✅ Provides interactive filtering  
✅ Includes price calculator  
✅ Exports data to CSV  
✅ Ready for deployment  

**Test it:**
```bash
streamlit run app.py
```

**Deploy it:**
Push to GitHub → Deploy to Streamlit Cloud

---

## 📞 Final Deliverables Checklist

- [ ] `app.py` - Dashboard application
- [ ] Data pipeline running (Stage 2) ✅
- [ ] KPI calculation working (Stage 3) ✅
- [ ] Dashboard launches locally
- [ ] All 4 pages functional
- [ ] CSV exports working
- [ ] Deployed to Streamlit Cloud (optional)
- [ ] GitHub Actions automation (Stage 5)

**You're 90% done with the project!** 🎊

Only Stage 5 (Automation) remains - and that's just setting up GitHub Actions to run every 48 hours!