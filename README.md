# 📊 Sales Insights

**Turn a small business's sales data into plain-English advice.**

Most small shops and cafés have months of sales data sitting in their point-of-sale system, but no time or tools to make sense of it. Sales Insights lets an owner upload a sales export and instantly see what's selling, when they're busiest, and what's changing, with clear, actionable tips instead of raw numbers.

🔗 **Live demo:** _coming soon_

![Screenshot of the dashboard](screenshot.png)

## What it does

- **Headline numbers:** total revenue, number of sales, average sale and revenue per day
- **Key insights in plain English**, for example:
  - "Saturday is your busiest day, making 61% more than Monday."
  - "Your rush is 7am–10am, which brings in 36% of daily revenue. Schedule extra staff then."
  - "Banana Bread is fading: sales are down 66%. Consider a promo or dropping it from the menu."
- **Product performance:** revenue ranking and each product's share of sales
- **Busy-times heatmap:** average revenue by day of the week and hour
- **Trends:** weekly revenue and which products are growing or shrinking

## Built with

- **Python** and **pandas** for data analysis
- **Streamlit** for the web app
- **Plotly** for interactive charts

## Run it yourself

```bash
git clone https://github.com/YOUR-USERNAME/sales-insights.git
cd sales-insights
pip install -r requirements.txt
streamlit run app.py
```

The app opens in your browser with demo data from a fictional café. Upload your own CSV from the sidebar to analyze it.

### Using your own data

Your CSV needs these columns:

| Column | Example |
|---|---|
| `transaction_id` | 100245 |
| `datetime` | 2026-05-01 08:42:00 |
| `product` | Latte |
| `quantity` | 1 |
| `total` | 5.25 |

## Project structure

| File | Purpose |
|---|---|
| `app.py` | The Streamlit web app (layout and charts) |
| `analysis.py` | All analysis logic, kept separate from the app so it's easy to test and reuse |
| `generate_sample_data.py` | Creates a realistic synthetic dataset with planted trends to validate the analysis |
| `sample_cafe_sales.csv` | 6 months of synthetic café sales (~26,500 transactions) |

## How I validated it

The demo dataset is generated with known patterns built in: a morning rush, busier weekends, one product steadily growing and one declining. The analysis detects all of them without being told about them, which confirms the logic works before it's used on real data.

## What's next

- [ ] Connect directly to Square and Shopify so owners don't need to export files
- [ ] Forecast next week's sales to help with ordering and staffing
- [ ] Pilot with local Calgary businesses

## Author

**Amatus Ghislain Bagaragaza**, Data Science student at the University of Calgary
