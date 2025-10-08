
# Stage 2: Data Processing & Storage - Complete Guide

## 📁 Project Structure

After Stage 2, your project should look like this:

```
vinted-project/
├── vinted_scraper.py          # Your existing scraper (improved)
├── process_data.py            # NEW: Data processing pipeline
├── run_pipeline.py            # NEW: Complete pipeline runner
├── inspect_data.py            # NEW: Data inspection tool
├── data/
│   ├── vinted_scrape_*.csv    # Raw scrape files (from scraper)
│   └── processed/
│       ├── listings.parquet          # Main database
│       ├── price_events.parquet      # Price change history
│       ├── sold_events.parquet       # Sold items history
│       ├── listings_backup_*.parquet # Timestamped backups
│       └── summary_report.csv        # Summary statistics
├── requirements.txt           # Python dependencies
└── README_STAGE2.md          # This file
```

---

## 🚀 Quick Start

### **Step 1: Install Dependencies**

```bash
pip install pandas pyarrow playwright
```

### **Step 2: First Run (Initial Data Collection)**

Run the complete pipeline for the first time:

```bash
python run_pipeline.py
```

This will:
1. ✅ Scrape 4,800 items from Vinted
2. ✅ Apply normalizations (brand, category, condition)
3. ✅ Save to `data/processed/listings.parquet`
4. ✅ Create initial database

**Expected Output:**
- `data/vinted_scrape_YYYYMMDD_HHMMSS.csv` (raw data)
- `data/processed/listings.parquet` (4,800 records)
- All items marked as "active" status

---

### **Step 3: Inspect Your Data**

Check data quality and see statistics:

```bash
python inspect_data.py
```

**You should see:**
- ✅ 4,800 total listings (all "active")
- ✅ Distribution by brand (Zara, Mango, Nike, H&M, Levi's)
- ✅ Distribution by category (Dress, Sneakers, T-shirt, Jeans)
- ✅ Price statistics (mean, median, P25, P75)
- ⚠️ 0 price changes (expected on first run)
- ⚠️ 0 sold items (expected on first run)

---

### **Step 4: Second Run (48 Hours Later)**

Wait 48 hours, then run the pipeline again:

```bash
python run_pipeline.py
```

This will:
1. ✅ Scrape fresh data (new snapshot)
2. ✅ **Detect price changes** → saved to `price_events.parquet`
3. ✅ **Detect sold items** → saved to `sold_events.parquet`
4. ✅ Update `listings.parquet` with new status

**Expected Output:**
- New items → added with "active" status
- Items still visible → `last_seen_at` updated
- Items disappeared → marked as "sold" with confidence score

---

## 📊 Understanding the Data

### **1. listings.parquet (Main Database)**

Contains all items ever scraped with their current status.

**Key Columns:**
- `item_id`: Unique identifier from Vinted
- `brand_raw` / `brand_norm`: Original and normalized brand names
- `category_raw` / `category_norm`: Original and normalized categories
- `condition_raw` / `condition_bucket`: Original and bucketed conditions
- `price`: Current/last known price
- `status`: "active" or "sold"
- `first_seen_at`: When item was first detected
- `last_seen_at`: When item was last seen in a scrape
- `season` / `season_keyword`: Optional season information

**Normalization Examples:**
- Brand: "ZARA" → "Zara", "H&M divided" → "H&M"
- Category: "Vestidos" → "Dress", "Zapatillas" → "Sneakers"
- Condition: "Nuevo con etiqueta" → "New/Like new"

---

### **2. price_events.parquet (Price Change History)**

Records when an item's price changes between scrapes.

**Key Columns:**
- `event_id`: Unique event identifier
- `item_id`: Which item changed
- `old_price` / `new_price`: Price before and after
- `changed_at`: Timestamp of detection
- `brand` / `category`: For filtering

**Use Cases:**
- Calculate discount-to-sell metrics
- Track pricing strategies by brand
- Identify markdown patterns

---

### **3. sold_events.parquet (Sold Items History)**

Records items that disappeared (likely sold).

**Key Columns:**
- `event_id`: Unique event identifier
- `item_id`: Which item sold
- `last_price`: Final selling price
- `days_to_sell`: Time from first_seen to sold_at
- `sold_confidence`: 1.0 (≥48h), 0.5 (24-48h), 0.0 (<24h)
- `first_seen_at` / `sold_at`: Date range

**Use Cases:**
- Calculate Days-to-Sell (DTS) metrics
- 30-day sell-through rates
- Liquidity analysis by brand/category

---

## 🔧 Advanced Usage

### **Run Only Scraping**

```bash
python run_pipeline.py --scrape-only
```

### **Run Only Processing**

If you already have a scrape file:

```bash
python run_pipeline.py --process-only
```

### **Inspect Specific Data**

```bash
# View only listings
python inspect_data.py --listings

# View only price changes
python inspect_data.py --prices

# View only sold items
python inspect_data.py --sold

# Export summary CSV
python inspect_data.py --export
```

---

## 🎯 Data Quality Checks

The `inspect_data.py` tool automatically checks for:

✅ **Brand Coverage:** All 5 brands present?  
✅ **Category Distribution:** Expected categories mapped correctly?  
✅ **Price Validity:** Any zero/null prices?  
✅ **Duplicate Detection:** Any duplicate item_ids?  
✅ **Normalization Success:** Missing normalized fields?  

---

## 📈 Expected Metrics After 2nd Run

After your second scrape (48 hours later), you should see:

**Listings:**
- ~4,800 active items (new snapshot)
- ~100-500 sold items (items that disappeared)
- ~5,000-5,300 total records (cumulative)

**Price Events:**
- ~50-200 price changes (typical 2-5% of items)
- Mix of increases and decreases

**Sold Events:**
- ~100-500 sold items
- High confidence (1.0): Items missing ≥48 hours
- Median DTS: ~7-14 days (varies by brand)

---

## 🐛 Troubleshooting

### **Issue: "No scrape files found"**

**Solution:** Run the scraper first:
```bash
python vinted_scraper.py
```

### **Issue: "No previous listings found"**

**Expected on first run.** This is normal! After the first run, subsequent runs will have previous data.

### **Issue: Zero price changes/sold items**

**Expected on first run.** Changes are detected by comparing runs. Wait 48 hours and run again.

### **Issue: Too many duplicate items**

Check your scraper's `item_id` extraction. The processor has deduplication, but fix the root cause.

### **Issue: Missing normalized fields**

Check the normalization functions in `process_data.py`. You may need to add more brand/category mappings for Spanish variations.

---

## 📝 Next Steps

Once you've successfully run the pipeline twice (with 48 hours between), you're ready for:

✅ **Stage 3:** KPI Calculation (`calculate_kpis.py`)
- Days-to-Sell (DTS) median
- 30-day sell-through rate
- Price distributions (P25/P50/P75)
- Discount-to-sell metrics

✅ **Stage 4:** Streamlit Dashboard (`app.py`)
- Interactive filters
- Visualizations
- Price calculator
- CSV/PDF exports

✅ **Stage 5:** Automation (GitHub Actions)
- Scheduled scraping every 48 hours
- Automatic data processing
- Cloud deployment

---

## 💡 Pro Tips

1. **Backup Your Data:** The processor creates automatic backups, but keep them safe!

2. **Monitor Logs:** Check `pipeline_*.log` files for detailed execution logs

3. **Incremental Development:** Test with small datasets first, then scale up

4. **Data Validation:** Run `inspect_data.py` after every pipeline run

5. **Storage:** Parquet files are compressed. 10,000 items ≈ 2-3 MB

---

## 📞 Support

If you encounter issues:

1. Check the log files: `pipeline_*.log`
2. Run inspection tool: `python inspect_data.py`
3. Review the debug JSON files in the project root
4. Verify your scraper is collecting all required fields

---

**You've completed Stage 2! 🎉**

Your data infrastructure is now ready to track inventory changes, price fluctuations, and sales over time. This forms the foundation for powerful KPI analysis in Stage 3.