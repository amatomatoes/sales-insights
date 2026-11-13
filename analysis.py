"""
analysis.py

The "brain" of the Sales Insights app. Each function takes the sales data
(a pandas DataFrame) and answers one business question.

The Streamlit app (coming next) will call these functions and display
the results. Keeping the analysis separate from the app makes it easier
to test and to reuse.
"""

import pandas as pd

# The columns we need in an uploaded sales file.
REQUIRED_COLUMNS = ["transaction_id", "datetime", "product", "quantity", "total"]

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday",
             "Friday", "Saturday", "Sunday"]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def load_sales(file):
    """Read a sales CSV and make sure it has what we need.

    `file` can be a file path or an uploaded file from Streamlit.
    """
    df = pd.read_csv(file)

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Your file is missing these columns: {', '.join(missing)}")

    # Turn the text dates into real dates so we can group by day, hour, week.
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["date"] = df["datetime"].dt.date
    df["hour"] = df["datetime"].dt.hour
    df["weekday"] = df["datetime"].dt.day_name()
    return df


# ---------------------------------------------------------------------------
# Question 1: How is the business doing overall?
# ---------------------------------------------------------------------------
def summary_metrics(df):
    """Headline numbers: total revenue, number of sales, average sale size."""
    revenue = df["total"].sum()
    transactions = df["transaction_id"].nunique()
    days = df["date"].nunique()
    return {
        "revenue": revenue,
        "transactions": transactions,
        "avg_sale": revenue / transactions,     # average amount per customer
        "revenue_per_day": revenue / days,
        "first_date": df["date"].min(),
        "last_date": df["date"].max(),
    }


# ---------------------------------------------------------------------------
# Question 2: What sells best (and worst)?
# ---------------------------------------------------------------------------
def product_performance(df):
    """Revenue and units sold for every product, best first.

    `share` is the percent of total revenue each product brings in.
    """
    table = (
        df.groupby("product")
          .agg(revenue=("total", "sum"), units=("quantity", "sum"))
          .sort_values("revenue", ascending=False)
    )
    table["share"] = table["revenue"] / table["revenue"].sum() * 100
    return table


# ---------------------------------------------------------------------------
# Question 3: When is the business busiest?
# ---------------------------------------------------------------------------
def busy_times(df):
    """A table of average revenue for each weekday (rows) and hour (columns).

    We divide by how many of each weekday appear in the data, so the numbers
    mean "on a typical Saturday at noon, you make $X".
    """
    totals = df.pivot_table(index="weekday", columns="hour",
                            values="total", aggfunc="sum", fill_value=0)
    days_per_weekday = df.groupby("weekday")["date"].nunique()
    averages = totals.div(days_per_weekday, axis=0)
    return averages.reindex(DAY_ORDER)


def revenue_by_weekday(df):
    """Average revenue for each day of the week."""
    daily = df.groupby(["date", "weekday"])["total"].sum().reset_index()
    return daily.groupby("weekday")["total"].mean().reindex(DAY_ORDER)


# ---------------------------------------------------------------------------
# Question 4: What is changing over time?
# ---------------------------------------------------------------------------
def weekly_revenue(df):
    """Total revenue per week, for a trend line."""
    return df.set_index("datetime")["total"].resample("W").sum()


def product_trends(df, weeks=4):
    """Compare each product's units sold in the first vs. the last few weeks.

    Returns the percent change, so +80 means "selling 80% more than before".
    """
    start = df["datetime"].min()
    end = df["datetime"].max()
    window = pd.Timedelta(weeks=weeks)

    early = df[df["datetime"] < start + window].groupby("product")["quantity"].sum()
    late = df[df["datetime"] > end - window].groupby("product")["quantity"].sum()

    trends = pd.DataFrame({"early_units": early, "recent_units": late}).fillna(0)
    trends["change_pct"] = (
        (trends["recent_units"] - trends["early_units"]) / trends["early_units"] * 100
    )
    return trends.sort_values("change_pct", ascending=False)


# ---------------------------------------------------------------------------
# Question 5: What should the owner actually know? (plain-English summary)
# ---------------------------------------------------------------------------
def generate_insights(df):
    """Turn the numbers above into short sentences a shop owner can act on."""
    insights = []

    # Best seller
    products = product_performance(df)
    top = products.index[0]
    insights.append(
        f"💰 **{top}** is your top earner, bringing in "
        f"{products.loc[top, 'share']:.0f}% of all revenue."
    )

    # Top 3 products' combined share
    top3_share = products["share"].head(3).sum()
    insights.append(
        f"📦 Your top 3 products make up {top3_share:.0f}% of revenue. "
        f"Never let them run out."
    )

    # Busiest day
    by_day = revenue_by_weekday(df)
    best_day, worst_day = by_day.idxmax(), by_day.idxmin()
    diff = (by_day.max() / by_day.min() - 1) * 100
    insights.append(
        f"📅 **{best_day}** is your busiest day, making {diff:.0f}% more than "
        f"{worst_day}, your slowest day."
    )

    # Peak hours: the 3-hour stretch with the most revenue
    by_hour = df.groupby("hour")["total"].sum()
    rolling = by_hour.rolling(3).sum()
    end_hour = int(rolling.idxmax())
    peak_share = rolling.max() / by_hour.sum() * 100
    insights.append(
        f"⏰ Your rush is **{_fmt_hour(end_hour - 2)}–{_fmt_hour(end_hour + 1)}**, "
        f"which brings in {peak_share:.0f}% of daily revenue. Schedule extra staff then."
    )

    # Fastest growing and fastest declining products
    trends = product_trends(df)
    rising, falling = trends.index[0], trends.index[-1]
    if trends.loc[rising, "change_pct"] > 15:
        insights.append(
            f"📈 **{rising}** is taking off: sales are up "
            f"{trends.loc[rising, 'change_pct']:.0f}% compared to when your data starts."
        )
    if trends.loc[falling, "change_pct"] < -15:
        insights.append(
            f"📉 **{falling}** is fading: sales are down "
            f"{abs(trends.loc[falling, 'change_pct']):.0f}%. Consider a promo or "
            f"dropping it from the menu."
        )

    return insights


def _fmt_hour(hour):
    """Turn 13 into '1pm', 9 into '9am'."""
    suffix = "am" if hour < 12 else "pm"
    return f"{(hour - 1) % 12 + 1}{suffix}"


# ---------------------------------------------------------------------------
# Quick test: run this file directly to see the insights in the terminal.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    data = load_sales("sample_cafe_sales.csv")
    m = summary_metrics(data)
    print(f"Revenue: ${m['revenue']:,.0f} | Sales: {m['transactions']:,} | "
          f"Avg sale: ${m['avg_sale']:.2f}\n")
    for line in generate_insights(data):
        print("-", line.replace("**", ""))
