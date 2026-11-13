"""
app.py

The Sales Insights web app. It shows the results from analysis.py as an
interactive dashboard in the browser.

Run it from PyCharm's Terminal with:   streamlit run app.py
"""

from pathlib import Path

import plotly.express as px
import streamlit as st

import analysis

SAMPLE_FILE = Path(__file__).parent / "sample_cafe_sales.csv"

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Sales Insights", page_icon="📊", layout="wide")

st.title("📊 Sales Insights")
st.caption("Upload your sales data and see what's selling, when you're busy, "
           "and what's changing, in plain English.")

# ---------------------------------------------------------------------------
# Sidebar: choose the data
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Your data")
    uploaded = st.file_uploader("Upload a sales CSV", type="csv")
    st.markdown(
        "**Required columns:** `transaction_id`, `datetime`, `product`, "
        "`quantity`, `total`"
    )
    st.divider()
    st.caption("No file? The app shows a demo café's data until you upload one.")

# Use the uploaded file if there is one, otherwise the demo data.
try:
    if uploaded is not None:
        df = analysis.load_sales(uploaded)
        source = uploaded.name
    else:
        df = analysis.load_sales(SAMPLE_FILE)
        source = "demo café data"
except ValueError as error:
    # load_sales raises ValueError when columns are missing.
    st.error(str(error))
    st.stop()
except Exception:
    st.error("Sorry, we couldn't read that file. Make sure it's a CSV export of your sales.")
    st.stop()

metrics = analysis.summary_metrics(df)
st.info(f"Showing **{source}** from {metrics['first_date']:%b %d, %Y} "
        f"to {metrics['last_date']:%b %d, %Y}.")

# ---------------------------------------------------------------------------
# Headline numbers
# ---------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total revenue", f"${metrics['revenue']:,.0f}")
col2.metric("Number of sales", f"{metrics['transactions']:,}")
col3.metric("Average sale", f"${metrics['avg_sale']:.2f}")
col4.metric("Revenue per day", f"${metrics['revenue_per_day']:,.0f}")

# ---------------------------------------------------------------------------
# Plain-English insights (the part owners care about most)
# ---------------------------------------------------------------------------
st.subheader("💡 Key insights")
for insight in analysis.generate_insights(df):
    st.markdown(f"- {insight}")

st.divider()

# ---------------------------------------------------------------------------
# Detailed charts, in tabs
# ---------------------------------------------------------------------------
tab_products, tab_times, tab_trends = st.tabs(
    ["🏆 Products", "⏰ Busy times", "📈 Trends"]
)

with tab_products:
    products = analysis.product_performance(df).reset_index()
    fig = px.bar(
        products.sort_values("revenue"),
        x="revenue", y="product", orientation="h",
        labels={"revenue": "Revenue ($)", "product": ""},
        title="Revenue by product",
    )
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        products.rename(columns={"product": "Product", "revenue": "Revenue ($)",
                                 "units": "Units sold", "share": "% of revenue"}),
        hide_index=True, use_container_width=True,
        column_config={
            "Revenue ($)": st.column_config.NumberColumn(format="$%.0f"),
            "% of revenue": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )

with tab_times:
    heat = analysis.busy_times(df)
    heat.columns = [analysis._fmt_hour(h) for h in heat.columns]
    fig = px.imshow(
        heat, text_auto=".0f", aspect="auto", color_continuous_scale="Blues",
        labels={"x": "Hour", "y": "", "color": "Avg revenue ($)"},
        title="Average revenue by day and hour (darker = busier)",
    )
    st.plotly_chart(fig, use_container_width=True)

    by_day = analysis.revenue_by_weekday(df).reset_index()
    fig = px.bar(by_day, x="weekday", y="total",
                 labels={"weekday": "", "total": "Average revenue ($)"},
                 title="Average revenue by day of the week")
    st.plotly_chart(fig, use_container_width=True)

with tab_trends:
    weekly = analysis.weekly_revenue(df).reset_index()
    fig = px.line(weekly, x="datetime", y="total", markers=True,
                  labels={"datetime": "Week", "total": "Revenue ($)"},
                  title="Weekly revenue")
    st.plotly_chart(fig, use_container_width=True)

    trends = analysis.product_trends(df).reset_index()
    trends["direction"] = trends["change_pct"].apply(
        lambda x: "Growing" if x > 0 else "Shrinking")
    fig = px.bar(
        trends.sort_values("change_pct"),
        x="change_pct", y="product", orientation="h", color="direction",
        color_discrete_map={"Growing": "#2e9e5b", "Shrinking": "#d64545"},
        labels={"change_pct": "Change in units sold (%)", "product": "",
                "direction": ""},
        title="Product trends: last 4 weeks vs. first 4 weeks",
    )
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)
