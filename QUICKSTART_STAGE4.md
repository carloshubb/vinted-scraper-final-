# Stage 4 Dashboard - Quick Start Guide

## ⚡ 5-Minute Setup

### **Step 1: Install Dependencies**

```bash
pip install streamlit plotly
```

### **Step 2: Verify Data Files Exist**

```bash
# Check for required files
dir data\processed\listings.parquet
dir data\processed\sold_events.parquet
```

If files are missing:
```bash
python run_pipeline.py
```

### **Step 3: Launch Dashboard**

```bash
streamlit run app.py
```

Dashboard opens at: `http://localhost:8501`

---

## 🎯 What You'll See

### **First Time (After 1 Pipeline Run)**

✅ **Overview**: "Not enough data" warning (normal!)  
✅ **Analysis**: Price charts work  
✅ **Calculator**: Price ranges work  
✅ **Downloads**: CSV exports work  

**Why**: Need 2+ pipeline runs (48h apart) for sold items

---

### **After 2nd Pipeline Run (48 hours later)**

✅ **Overview**: Full liquidity ranking  
✅ **Analysis**: All KPIs displayed  
✅ **Calculator**: DTS estimates  
✅ **Downloads**: All exports  

**Now**: Fully functional dashboard!

---

## 📊 Page Navigation

### **Page 1: Overview** 🏠
Shows liquidity ranking of all brands

**What to check:**
- Is Zara ranked?
- Are grades showing (A/B/C/D)?
- Is the bar chart visible?

---

### **Page 2: Brand Analysis** 📈
Deep dive with filters

**Try this:**
1. Select "Zara" in Brand filter
2. Select "Dress" in Category filter
3. Check if KPI cards update
4. Scroll down to see charts

---

### **Page 3: Calculator** 🧮
Price recommendations

**Try this:**
1. Select: Brand = "Zara", Category = "Dress"
2. Check recommended prices (Budget/Market/Premium)
3. Enter a custom price (e.g., €30)
4. See positioning and estimated DTS

---

### **Page 4: Downloads** 📥
Export data

**Try this:**
1. Click "Download Active Listings (CSV)"
2. Open in Excel
3. Verify data looks correct

---

## 🐛 Quick Troubleshooting

### **"Error loading data"**
```bash
# Run pipeline first
python run_pipeline.py
```

### **All KPIs show "N/A"**
- Normal after first run
- Wait 48h, run pipeline again
- Then you'll see full KPIs

### **"Module not found"**
```bash
pip install streamlit plotly
```

### **Port already in use**
```bash
# Stop other Streamlit instances or use different port
streamlit run app.py --server.port 8502
```

---

## ✅ Success Checklist

After launching dashboard:

- [ ] Overview page loads
- [ ] You see 4 navigation options
- [ ] Sidebar shows data summary
- [ ] Can switch between pages
- [ ] Charts are interactive (hover works)
- [ ] Filters update the data
- [ ] CSV download works

**If all checked**: Dashboard is working! 🎉

---

## 🚀 Next Steps

1. **Test all features** - Click everything!
2. **Run 2nd pipeline** - After 48 hours
3. **Deploy to cloud** - Streamlit Cloud (optional)
4. **Set up automation** - Stage 5 (GitHub Actions)

---

## 💡 Pro Tips

1. **Clear cache**: Hamburger menu (⋮) → "Clear cache"
2. **Refresh data**: Re-run pipeline, then clear cache
3. **Full screen**: Press F11 for presentation mode
4. **Share link**: Deploy to Streamlit Cloud for shareable URL

---

## 📞 Need Help?

**Check these files:**
- `README_STAGE4.md` - Full documentation
- `app.py` - Dashboard code (line ~46 has cache settings)
- `calculate_kpis.py` - KPI calculation logic

**Common fixes:**
```bash
# Reinstall dependencies
pip install --upgrade streamlit plotly pandas

# Check Python version (need 3.8+)
python --version

# Verify data files
dir data\processed\*.parquet
```

---

**Ready?** → `streamlit run app.py` 🚀