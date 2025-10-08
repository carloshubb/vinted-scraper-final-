# Stage 3: KPI Calculation Engine - Complete Guide

## 📊 Overview

Stage 3 calculates all the key performance indicators (KPIs) required by your client:
- **Days-to-Sell (DTS)** - How long items take to sell
- **30-day Sell-Through Rate** - % of items sold within 30 days
- **Price Distribution** - P25, P50 (median), P75
- **Discount-to-Sell** - Average price reduction before selling
- **Liquidity Score** - Overall market liquidity (0-100 scale)

---

## 📁 New Files

### **1. `calculate_kpis.py`** (Main Engine)
Complete KPI calculation engine with filtering capabilities.

### **2. `test_kpis.py`** (Testing Tool)
Interactive tool for testing different filter combinations.

---

## 🚀 Quick Start

### **Prerequisites**

You must have completed Stage 2 and have:
- ✅ `data/processed/listings.parquet`
- ✅ `data/processed/sold_events.parquet` (at least some sold items)
- ✅ `data/processed/price_events.parquet` (optional, but recommended)

**Note:** If you've only run the pipeline once, you won't have sold items yet. Run it again after 48 hours.

---

### **Basic Usage**

Calculate all KPIs (overall + by brand + by category):

```bash
python calculate_kpis.py
```

**Output:**
```
📊 Days-to-Sell (DTS):
   Median: 12.5 days
   Mean: 15.3 days
   P25-P75: 7.0 - 22.0 days

📈 30-Day Sell-Through Rate:
   45.2% (120 of 265 items)

💰 Price Distribution:
   P25: €15.00
   P50 (Median): €25.00
   P75: €40.00

💸 Discount-to-Sell:
   Average: 12.5%
   Median: 10.0%

🌊 Liquidity Score:
   Overall: 62.3/100 (Grade: B)
```

---

## 🔍 Understanding Each KPI

### **1. Days-to-Sell (DTS)**

**What it measures:** How long items take to sell (from first_seen to sold_at)

**Formula:**
```
DTS = sold_at - first_seen_at (in days)
```

**Filtering:**
- Only includes high-confidence sales (sold_confidence ≥ 0.5)
- Items missing for ≥24 hours

**Key Metrics:**
- **Median DTS** - Most important (not skewed by outliers)
- **P25-P75** - Range where 50% of items sell
- **Mean** - Average (can be skewed by slow sellers)

**Interpretation:**
- `<7 days` - Very fast moving
- `7-14 days` - Fast moving
- `15-30 days` - Average
- `>30 days` - Slow moving

---

### **2. 30-Day Sell-Through Rate**

**What it measures:** What % of items sell within 30 days

**Formula:**
```
Sell-Through = (Items sold ≤30 days / Total sold items) × 100
```

**Why 30 days?**
- Industry standard for "fast fashion"
- Indicates market demand strength

**Interpretation:**
- `>60%` - Excellent demand
- `40-60%` - Good demand
- `20-40%` - Moderate demand
- `<20%` - Weak demand

---

### **3. Price Distribution**

**What it measures:** Price ranges and typical prices

**Metrics:**
- **P25** - 25th percentile (budget range)
- **P50** - Median (typical price)
- **P75** - 75th percentile (premium range)

**Why use percentiles?**
- Not affected by extreme prices (€1 or €999)
- Shows realistic price ranges

**Usage:**
- Set competitive prices
- Identify pricing sweet spots
- Understand market segmentation

---

### **4. Discount-to-Sell**

**What it measures:** Average price reduction needed to make a sale

**Formula:**
```
Discount % = ((First Price - Last Price) / First Price) × 100
```

**Only includes:**
- Items that had at least one price change
- Items that eventually sold

**Interpretation:**
- `0-5%` - Items sell at near-original price
- `5-15%` - Modest discounts needed
- `15-30%` - Significant discounts
- `>30%` - Heavy discounting required

**Note:** If 0%, items are selling at original price (good sign!)

---

### **5. Liquidity Score**

**What it measures:** Overall market liquidity (how easily items convert to cash)

**Formula:**
```
Liquidity = (Sell-Through Component × 50%) + (Speed Component × 50%)

Where:
- Sell-Through Component = (30d sell-through % / 100) × 50
- Speed Component = (1 - (DTS median / 30 days)) × 50
```

**Grading Scale:**
- **A (75-100):** Excellent liquidity - Items fly off shelves
- **B (50-74):** Good liquidity - Healthy sales velocity
- **C (25-49):** Fair liquidity - Slower but acceptable
- **D (0-24):** Poor liquidity - Very slow sales

**Use Case:**
This is your **"Liquidity Ranking by Brand"** for the dashboard overview!

---

## 🎯 Testing & Exploration

### **Test All Combinations**

Test each of your 5 brand-category combos:

```bash
python test_kpis.py --all-combos
```

Output shows KPIs for:
- Zara - Dress
- Mango - Dress
- Nike - Sneakers
- H&M - T-shirt
- Levi's - Jeans

---

### **Compare Brands Side-by-Side**

```bash
python test_kpis.py --compare-brands
```

**Output:**
```
Brand        DTS (days)   Sell-Thru    Median Price    Liquidity   
----------------------------------------------------------------------
Zara         10.5         52.3%        €28.00          68 (B)
Mango        12.0         48.1%        €32.00          64 (B)
Nike         8.5          58.7%        €45.00          72 (B)
H&M          9.0          55.2%        €12.00          70 (B)
Levi's       15.5         38.9%        €35.00          54 (B)
```

---

### **Show Liquidity Ranking**

Perfect for your dashboard's "Overview" page!

```bash
python test_kpis.py --liquidity
```

**Output:**
```
LIQUIDITY RANKING (Highest to Lowest)

Rank   Brand        Score      Grade    DTS          30d Sell-Thru  
----------------------------------------------------------------------
1      Nike         72.3       B        8.5d         58.7%
2      H&M          70.1       B        9.0d         55.2%
3      Zara         67.8       B        10.5d        52.3%
4      Mango        63.5       B        12.0d        48.1%
5      Levi's       53.9       B        15.5d        38.9%
```

---

### **Compare Seasons**

If you have seasonal data:

```bash
python test_kpis.py --season
```

Shows KPIs for summer vs winter items separately.

---

### **Interactive Mode**

Test custom filter combinations:

```bash
python test_kpis.py --interactive
```

Prompts you to enter:
- Brand (e.g., "Zara")
- Category (e.g., "Dress")
- Audience (e.g., "Mujer")
- Season (e.g., "summer")

---

### **Show Available Filters**

See what values you can filter by:

```bash
python test_kpis.py --filters
```

---

## 💻 Programmatic Usage

Use KPIs in your own Python scripts:

```python
from calculate_kpis import calculate_all_kpis, print_kpi_report

# Calculate KPIs for Zara dresses
kpis = calculate_all_kpis(brand="Zara", category="Dress")

# Print formatted report
print_kpi_report(kpis, "Zara Dresses")

# Access specific metrics
if kpis['dts']:
    median_dts = kpis['dts']['median']
    print(f"Zara dresses sell in {median_dts:.1f} days (median)")

if kpis['price_distribution']:
    median_price = kpis['price_distribution']['p50']
    print(f"Median price: €{median_price:.2f}")

if kpis['liquidity']:
    score = kpis['liquidity']['score']
    grade = kpis['liquidity']['grade']
    print(f"Liquidity: {score:.1f}/100 (Grade {grade})")
```

---

## 📊 Exported Data

### **KPI Report CSV**

After running `calculate_kpis.py`, you'll get:

**File:** `data/processed/kpis_complete_report.csv`

**Columns:**
- `segment` - What filters were applied (e.g., "Brand: Zara")
- `dts_median`, `dts_mean`, `dts_p25`, `dts_p75`
- `sell_through_30d_pct`, `sold_30d_count`
- `price_p25`, `price_p50`, `price_p75`, `price_mean`
- `avg_discount_pct`, `median_discount_pct`
- `liquidity_score`, `liquidity_grade`

**Usage:**
- Import into Excel for client reports
- Feed into Streamlit dashboard
- Share with stakeholders

---

## 🐛 Troubleshooting

### **Issue: "No sold events available"**

**Cause:** You haven't run the pipeline at least twice (48 hours apart)

**Solution:**
1. Run `python run_pipeline.py` now
2. Wait 48 hours
3. Run `python run_pipeline.py` again
4. Now run `python calculate_kpis.py`

---

### **Issue: All KPIs show "No data available"**

**Cause:** Not enough sold items for statistical analysis

**Solution:**
- Check `inspect_data.py --sold` to see how many sold items you have
- Need at least ~20-30 sold items per segment for meaningful KPIs
- Wait longer between scrapes or increase scraping frequency

---

### **Issue: DTS is very high (>60 days)**

**Possible causes:**
1. Items genuinely take long to sell (normal for some brands)
2. Your `first_seen_at` dates might be incorrect
3. Not enough data yet (early in data collection)

**Check:**
```bash
python inspect_data.py --sold
```

Look at the `days_to_sell` distribution.

---

### **Issue: Discount-to-sell is 0%**

**Interpretation:** This is actually GOOD!

It means items are selling at their original price without markdowns. High-demand items often show 0% discount-to-sell.

---

### **Issue: Liquidity scores seem low**

**Causes:**
- Long DTS (>20 days median)
- Low sell-through (<40%)
- Natural for certain categories (jeans take longer than t-shirts)

**This is useful data!** It shows which brands/categories have poor liquidity.

---

## 📈 Expected Results

### **After First Complete Run (48+ hours of data)**

**Overall KPIs:**
- DTS Median: 10-20 days (varies by brand)
- 30d Sell-Through: 35-55%
- Sold Items: 100-500 (out of 4,800)
- Liquidity Scores: Mostly B/C grades

**By Brand (typical ranges):**
- **Fast Fashion (Zara, H&M):** DTS ~8-12 days, Liquidity B
- **Mid-tier (Mango):** DTS ~10-15 days, Liquidity B/C
- **Sportswear (Nike):** DTS ~7-10 days, Liquidity B/A
- **Denim (Levi's):** DTS ~15-25 days, Liquidity C

---

## 🎯 Using KPIs in Dashboard

These KPIs feed directly into your Streamlit dashboard:

### **Overview Page**
- **Liquidity Ranking Table** ← Use `test_kpis.py --liquidity` output
- Show top-to-bottom brand ranking

### **Brand·Category View**
- **Boxplot of prices** ← Use `price_distribution` (P25, P50, P75)
- **DTS bar chart** ← Use `dts['median']`
- **Sell-through bar** ← Use `sell_through_30d['percentage']`

### **Calculator**
User selects: Brand, Category, Audience, Season
You show:
- **Price range** ← P25-P75 from `price_distribution`
- **Estimated days to sell** ← `dts['median']`

---

## 🔄 Integration with Pipeline

Add KPI calculation to your automated workflow:

**Option 1: Manual after each scrape**
```bash
python run_pipeline.py
python calculate_kpis.py
```

**Option 2: Update `run_pipeline.py`** (add at the end):
```python
# At the end of run_full_pipeline()
logger.info("\n[3/3] Calculating KPIs...")
from calculate_kpis import main as calculate_kpis_main
calculate_kpis_main()
```

---

## 📝 Next Steps

After completing Stage 3, you're ready for:

✅ **Stage 4: Streamlit Dashboard**
- Use the KPI calculations
- Create interactive visualizations
- Build the price calculator
- Add CSV/PDF export

All the hard work is done - Stage 4 is mostly UI!

---

## 💡 Pro Tips

1. **Run KPIs daily** to see trends over time
2. **Export CSVs** for stakeholder reports
3. **Use interactive mode** to explore data before building dashboard
4. **Compare weekday vs weekend** by filtering on published_at
5. **Track discount patterns** to optimize pricing strategies

---

**Stage 3 Complete! 🎉**

You now have a full KPI engine that can calculate all required metrics with flexible filtering. This is the analytics brain of your dashboard!