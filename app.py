"""
app.py

The Sales Insights web app. It shows the results from analysis.py as an
interactive dashboard in the browser.

Run it from PyCharm's Terminal with:   streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import analysis
import loader

SAMPLE_FILE = Path(__file__).parent / "sample_cafe_sales.csv"
NOT_IN_FILE = "— not in my file —"

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
    st.caption("Works with sales exports from Square, Shopify, Clover and most "
               "other point-of-sale systems.")
    st.divider()
    st.caption("No file? The app shows a demo café's data until you upload one.")

# ---------------------------------------------------------------------------
# Step 1: read the file (the upload, or the demo data)
# ---------------------------------------------------------------------------
if uploaded is None:
    raw = loader.read_file(SAMPLE_FILE)
    source = "demo café data"
    file_key = "demo"
else:
    try:
        raw = loader.read_file(uploaded)
    except Exception:
        st.error("Sorry, we couldn't open that file. Make sure it's a CSV export "
                 "of your sales.")
        st.stop()
    source = uploaded.name
    # A unique key per file, so the column choices reset when a new file arrives.
    file_key = f"{uploaded.name}-{uploaded.size}"

# ---------------------------------------------------------------------------
# Step 2: match the columns (guessed automatically, owner can fix them)
# ---------------------------------------------------------------------------
mapping = loader.guess_columns(raw)

if uploaded is not None:
    needs_help = bool(loader.missing_required(mapping))
    with st.expander("🔎 Column matching: check that we read your file correctly",
                     expanded=needs_help):
        if needs_help:
            st.warning("We couldn't find everything automatically. Please choose "
                       "the matching columns below.")
        else:
            st.caption("We matched your columns automatically. Change any that look wrong.")

        options = [NOT_IN_FILE] + list(raw.columns)
        left, right = st.columns(2)
        for i, (field, info) in enumerate(loader.FIELDS.items()):
            guess = mapping[field]
            index = options.index(guess) if guess in options else 0
            label = info["label"] + (" *" if info["required"] else "")
            box = left if i % 2 == 0 else right
            choice = box.selectbox(label, options, index=index, key=f"{file_key}-{field}")
            mapping[field] = None if choice == NOT_IN_FILE else choice

        st.caption("\\* Required. You also need either a line total or a unit price.")
        st.markdown("**First rows of your file:**")
        st.dataframe(raw.head(5), hide_index=True)

# ---------------------------------------------------------------------------
# Step 3: clean the data into our standard format
# ---------------------------------------------------------------------------
try:
    df, notes = loader.standardize(raw, mapping)
except ValueError as error:
    st.error(str(error))
    st.stop()
except Exception:
    st.error("Sorry, something in this file couldn't be read. Check the column "
             "matching above.")
    st.stop()

has_time = loader.has_time_of_day(df)
all_sales = df  # keep the full data; `df` becomes the filtered view below

# ---------------------------------------------------------------------------
# Step 4: filters in the sidebar (date range and categories)
# ---------------------------------------------------------------------------
first_day, last_day = all_sales["date"].min(), all_sales["date"].max()
with st.sidebar:
    st.header("Filters")
    picked = st.date_input(
        "Date range", value=(first_day, last_day),
        min_value=first_day, max_value=last_day, key=f"{file_key}-dates",
    )
    # While the owner is picking, the calendar briefly returns just one date.
    if isinstance(picked, (tuple, list)) and len(picked) == 2:
        start_date, end_date = picked
    else:
        start_date, end_date = first_day, last_day
        st.caption("Pick an end date to apply the range.")

    all_categories = sorted(all_sales["category"].unique())
    chosen_categories = None
    if len(all_categories) > 1:  # no point filtering if there's only one
        chosen_categories = st.multiselect(
            "Categories", all_categories, placeholder="All categories",
            key=f"{file_key}-categories",
        )

df = analysis.filter_sales(all_sales, start_date, end_date, chosen_categories)
if df.empty:
    st.warning("No sales match these filters. Try a wider date range or "
               "different categories.")
    st.stop()

metrics = analysis.summary_metrics(df)
banner = (f"Showing **{source}** from {metrics['first_date']:%b %d, %Y} "
          f"to {metrics['last_date']:%b %d, %Y}")
if chosen_categories:
    banner += f", categories: **{', '.join(chosen_categories)}**"
if len(df) < len(all_sales):
    share = len(df) / len(all_sales)
    banner += " (less than 1% of your data)" if share < 0.01 else f" ({share:.0%} of your data)"
st.info(banner + ".")
if chosen_categories:
    st.caption("ℹ️ With categories selected, 'Number of sales' counts sales that "
               "included those items, and 'Average sale' adds up only those items.")
for note in notes:
    st.caption(f"ℹ️ {note}")

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
    # Real shops can have hundreds of items, so the chart shows the top 15
    # and the table below lists everything.
    top_products = products.head(15)
    title = "Revenue by product" if len(products) <= 15 else "Top 15 products by revenue"
    fig = px.bar(
        top_products.sort_values("revenue"),
        x="revenue", y="product", orientation="h",
        labels={"revenue": "Revenue ($)", "product": ""},
        title=title,
    )
    fig.update_layout(height=max(300, 32 * len(top_products)))
    st.plotly_chart(fig, width="stretch")

    st.dataframe(
        products.rename(columns={"product": "Product", "revenue": "Revenue ($)",
                                 "units": "Units sold", "share": "% of revenue"}),
        hide_index=True, width="stretch",
        column_config={
            "Revenue ($)": st.column_config.NumberColumn(format="$%.0f"),
            "% of revenue": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )

with tab_times:
    if has_time:
        heat = analysis.busy_times(df)
        heat.columns = [analysis._fmt_hour(h) for h in heat.columns]
        fig = px.imshow(
            heat, text_auto=".0f", aspect="auto", color_continuous_scale="Blues",
            labels={"x": "Hour", "y": "", "color": "Avg revenue ($)"},
            title="Average revenue by day and hour (darker = busier)",
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("Your file has dates but no times, so we can't show busy hours. "
                "Export a report that includes the time of each sale to see them.")

    by_day = analysis.revenue_by_weekday(df).reset_index()
    fig = px.bar(by_day, x="weekday", y="total",
                 labels={"weekday": "", "total": "Average revenue ($)"},
                 title="Average revenue by day of the week")
    st.plotly_chart(fig, width="stretch")

with tab_trends:
    weekly = analysis.weekly_revenue(df).reset_index()
    fig = px.line(weekly, x="datetime", y="total", markers=True,
                  labels={"datetime": "Week", "total": "Revenue ($)"},
                  title="Weekly revenue")
    st.plotly_chart(fig, width="stretch")

    trends = analysis.product_trends(df)
    if trends.empty:
        st.info("Product trends need at least 8 weeks of sales: we compare the "
                "first 4 weeks with the most recent 4. Upload more history or "
                "widen the date range.")
    else:
        # Show the 10 biggest movers in each direction so the chart stays readable.
        trends = trends.rename_axis("product").reset_index()
        movers = pd.concat([trends.head(10), trends.tail(10)]).drop_duplicates("product")
        movers["direction"] = movers["change_pct"].apply(
            lambda x: "Growing" if x > 0 else "Shrinking")
        fig = px.bar(
            movers.sort_values("change_pct"),
            x="change_pct", y="product", orientation="h", color="direction",
            color_discrete_map={"Growing": "#2e9e5b", "Shrinking": "#d64545"},
            labels={"change_pct": "Change in units sold (%)", "product": "",
                    "direction": ""},
            title="Biggest movers: last 4 weeks vs. first 4 weeks",
        )
        fig.update_layout(height=max(300, 32 * len(movers)))
        st.plotly_chart(fig, width="stretch")
