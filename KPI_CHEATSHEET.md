# KPI Calculation - Quick Reference Cheat Sheet

## 🚀 Quick Commands

```bash
# Calculate all KPIs (full report)
python calculate_kpis.py

# Test specific combinations
python test_kpis.py --all-combos

# Compare brands side-by-side
python test_kpis.py --compare-brands

# Show liquidity ranking
python test_kpis.py --liquidity

# Interactive filtering
python test_kpis.py --interactive

# Show available filters
python test_kpis.py --filters
```

---

## 📊 KPI Formulas

| KPI | Formula | Good Value | Bad Value |
|-----|---------|------------|-----------|
| **DTS Median** | sold_at - first_seen_at | <10 days | >30 days |
| **30d Sell-Through** | (Sold ≤30d / Total sold) × 100 | >50% | <30% |
| **Discount-to-Sell** | ((First - Last) / First) × 100 | 0-10% | >25% |
| **Liquidity Score** | (Sell-Through × 0.5) + (Speed × 0.5) | 75+ (A) | <25 (D) |

---

## 🎯 Interpreting Results

### Days-to-Sell (DTS)
- **0-7 days:** 🔥 Hot items - very high demand
- **8-14 days:** ✅ Good - healthy sales velocity
- **15-30 days:** ⚠️ Slow - consider price adjustments
- **30+ days:** 🐌 Very slow - overpriced or low demand

### Sell-Through Rate
- **>60%:** 🌟 Excellent - strong market demand
- **40-60%:** ✅ Good - healthy demand
- **20-40%:** ⚠️ Fair - moderate interest
- **<20%:** ❌ Poor - weak demand

### Price Distribution
- **P25:** Budget/entry price point
- **P50 (Median):** Typical market price
- **P75:** Premium price point
- **Spread (P75-P25):** Market price range

### Discount-to-Sell
- **0%:** Items sell at original price (best!)
- **1-10%:** Minor adjustments needed
- **10-20%:** Moderate discounting
- **>20%:** Heavy discounting required

### Liquidity Score
- **A (75-100):** 🚀 Excellent - items convert fast
- **B (50-74):** ✅ Good - healthy liquidity
- **C (25-49):** ⚠️ Fair - slower conversion
- **D (0-24):** ❌ Poor - very illiquid

---

## 🔍 Filtering Options

```python
# Single filter
kpis = calculate_all_kpis(brand="Zara")

# Multiple filters
kpis = calculate_all_kpis(
    brand="Zara",
    category="Dress",
    audience="Mujer",
    season="summer"
)

# Filter options:
# - brand: "Zara", "Mango", "Nike", "H&M", "Levi's"
# - category: "Dress", "Sneakers", "T-shirt", "Jeans"
# - audience: "Mujer", "Hombre"
# - status: "active", "sold"
# - season: "summer", "winter"
```

---

## 📁 Output Files

| File | Content | Usage |
|------|---------|-------|
| `kpis_complete_report.csv` | All calculated KPIs | Import to dashboard |
| `summary_report.csv` | Quick stats by segment | Client reports |

---

## 🎨 Dashboard Mapping

| Dashboard Section | KPI to Use |
|-------------------|------------|
| **Overview - Liquidity Ranking** | `liquidity['score']` + `liquidity['grade']` |
| **Brand View - Price Boxplot** | `price_distribution['p25/p50/p75']` |
| **Brand View - DTS Bar** | `dts['median']` |
| **Brand View - Sell-Through Bar** | `sell_through_30d['percentage']` |
| **Calculator - Price Range** | `price_distribution['p25']` to `['p75']` |
| **Calculator - Est. Days** | `dts['median']` |

---

## ⚠️ Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "No sold events" | Only ran pipeline once | Wait 48h, run again |
| All KPIs = None | <20 sold items | Collect more data |
| DTS > 60 days | Wrong first_seen_at | Check data quality |
| Discount = 0% | No price changes | This is good! |
| Low liquidity | Long DTS + low sell-through | Normal for some brands |

---

## 💻 Code Snippets

### Access Specific Metrics
```python
kpis = calculate_all_kpis(brand="Zara")

# Days to Sell
median_dts = kpis['dts']['median']
mean_dts = kpis['dts']['mean']

# Sell-Through
sell_through_pct = kpis['sell_through_30d']['percentage']

# Price
p25 = kpis['price_distribution']['p25']
p50 = kpis['price_distribution']['p50']
p75 = kpis['price_distribution']['p75']

# Liquidity
score = kpis['liquidity']['score']
grade = kpis['liquidity']['grade']
```

### Check if Data Exists
```python
if kpis['dts'] is not None:
    print(f"DTS: {kpis['dts']['median']:.1f} days")
else:
    print("Not enough sold items yet")
```

---

## 📊 Expected Values (Typical)

Based on fast fashion market:

| Brand | DTS (days) | Sell-Through | Avg Price | Liquidity |
|-------|-----------|--------------|-----------|-----------|
| **Zara** | 8-12 | 45-55% | €25-35 | B (60-70) |
| **Mango** | 10-15 | 40-50% | €30-40 | B (55-65) |
| **Nike** | 7-10 | 50-60% | €40-60 | B/A (65-75) |
| **H&M** | 8-12 | 45-55% | €10-20 | B (60-70) |
| **Levi's** | 15-25 | 30-45% | €30-50 | C (45-55) |

*Note: Actual values depend on your specific market data*

---

## 🎯 For Client Presentation

### Key Talking Points

1. **DTS = "How fast do items sell?"**
   - Lower is better
   - Industry benchmark: 14 days

2. **Sell-Through = "What % converts in 30 days?"**
   - Higher is better
   - >50% = strong demand

3. **Liquidity = "Overall market health"**
   - A/B = Healthy market
   - C/D = Sluggish market

4. **Discount-to-Sell = "Pricing pressure"**
   - 0% = No pressure (ideal)
   - >15% = Heavy pressure

---

## 📞 Support

If KPIs don't make sense:
1. Run `python inspect_data.py --sold`
2. Check sold item counts
3. Verify data collection timeframe
4. Ensure at least 48 hours between scrapes

---

**Print this for quick reference while building your dashboard!** 📌