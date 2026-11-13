"""
generate_sample_data.py

Creates a realistic FAKE sales dataset for a small café, so we can build and
demo the Sales Insights app without needing a real business's data.

Run it with:   python generate_sample_data.py
It writes:     sample_cafe_sales.csv
"""

import numpy as np
import pandas as pd

# A fixed "seed" makes the random numbers the same every run,
# so the dataset (and our results) are reproducible.
rng = np.random.default_rng(seed=42)

# ---------------------------------------------------------------------------
# 1. The menu: product name -> (category, price, how popular it is)
#    "popularity" is a relative weight: higher = sold more often.
# ---------------------------------------------------------------------------
MENU = {
    "Drip Coffee":        ("Coffee",   2.75, 10),
    "Latte":              ("Coffee",   5.25, 9),
    "Cappuccino":         ("Coffee",   4.95, 6),
    "Americano":          ("Coffee",   3.75, 5),
    "Iced Latte":         ("Coffee",   5.75, 4),   # will grow over time
    "Mocha":              ("Coffee",   5.50, 3),
    "Chai Latte":         ("Tea",      5.00, 4),
    "Earl Grey":          ("Tea",      3.25, 2),
    "Matcha Latte":       ("Tea",      5.75, 3),
    "Croissant":          ("Bakery",   3.95, 6),
    "Blueberry Muffin":   ("Bakery",   3.75, 5),
    "Cinnamon Bun":       ("Bakery",   4.50, 4),
    "Banana Bread":       ("Bakery",   3.50, 2),   # will decline over time
    "Breakfast Sandwich": ("Food",     8.50, 5),
    "Turkey Panini":      ("Food",    11.95, 4),
    "Soup of the Day":    ("Food",     7.25, 3),
}

# ---------------------------------------------------------------------------
# 2. When customers come in.
#    Relative traffic for each opening hour (café open 7am to 6pm).
#    Morning rush and lunch rush are the peaks.
# ---------------------------------------------------------------------------
HOURLY_TRAFFIC = {
    7: 8, 8: 14, 9: 11, 10: 8, 11: 9, 12: 13,
    13: 11, 14: 6, 15: 5, 16: 5, 17: 4,
}

# Relative traffic by day of week (0 = Monday ... 6 = Sunday).
# Saturday is the busiest day, Sunday mornings are slower.
DAILY_TRAFFIC = {0: 0.85, 1: 0.9, 2: 0.95, 3: 1.0, 4: 1.1, 5: 1.35, 6: 1.05}

AVG_TRANSACTIONS_PER_DAY = 140
START_DATE = "2026-05-01"
END_DATE = "2026-10-31"


def product_weights(day_index, total_days):
    """Return how likely each product is to be picked on a given day.

    We add two trends so the app has something interesting to find:
      - Iced Latte gets more popular over time (+150% by the end)
      - Banana Bread gets less popular over time (-70% by the end)
    """
    progress = day_index / total_days  # 0.0 at start -> 1.0 at end
    weights = []
    for name, (_, _, popularity) in MENU.items():
        if name == "Iced Latte":
            popularity *= 1 + 1.5 * progress
        elif name == "Banana Bread":
            popularity *= 1 - 0.7 * progress
        weights.append(popularity)
    weights = np.array(weights, dtype=float)
    return weights / weights.sum()  # probabilities must add up to 1


def main():
    days = pd.date_range(START_DATE, END_DATE, freq="D")
    product_names = list(MENU.keys())
    hours = np.array(list(HOURLY_TRAFFIC.keys()))
    hour_probs = np.array(list(HOURLY_TRAFFIC.values()), dtype=float)
    hour_probs /= hour_probs.sum()

    rows = []
    transaction_id = 100000

    for day_index, day in enumerate(days):
        # How many customers today? Busier on weekends, plus random noise.
        expected = AVG_TRANSACTIONS_PER_DAY * DAILY_TRAFFIC[day.weekday()]
        n_transactions = rng.poisson(expected)
        weights = product_weights(day_index, len(days))

        for _ in range(n_transactions):
            transaction_id += 1
            hour = rng.choice(hours, p=hour_probs)
            minute = rng.integers(0, 60)
            timestamp = day + pd.Timedelta(hours=int(hour), minutes=int(minute))

            # Each customer buys 1-3 different items.
            n_items = rng.choice([1, 2, 3], p=[0.55, 0.35, 0.10])
            items = rng.choice(product_names, size=n_items, replace=False, p=weights)

            for item in items:
                category, price, _ = MENU[item]
                quantity = rng.choice([1, 2], p=[0.9, 0.1])
                rows.append({
                    "transaction_id": transaction_id,
                    "datetime": timestamp,
                    "product": item,
                    "category": category,
                    "quantity": quantity,
                    "unit_price": price,
                    "total": round(price * quantity, 2),
                })

    df = pd.DataFrame(rows)
    df.to_csv("sample_cafe_sales.csv", index=False)
    print(f"Wrote {len(df):,} sale lines from {df['transaction_id'].nunique():,} "
          f"transactions to sample_cafe_sales.csv")


if __name__ == "__main__":
    main()
