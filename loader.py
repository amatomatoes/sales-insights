"""
loader.py

Reads a sales file from (almost) any point-of-sale system and turns it into
one standard format that analysis.py understands.

Real exports all look different. Square calls the product column "Item" and
splits date and time into two columns. Shopify calls it "Lineitem name" and
puts the order number in a column called "Name". Money often comes as text
like "$5.25". This file handles all of that in three steps:

    1. read_file()      -> open the CSV, whatever its encoding
    2. guess_columns()  -> work out which column means what
    3. standardize()    -> clean everything into our standard format

The app shows the guesses from step 2 so the owner can fix any wrong ones.
"""

import re

import pandas as pd

# ---------------------------------------------------------------------------
# The pieces of information we look for, and what each one is called in
# different systems. Names are compared in lowercase with punctuation removed,
# so "Item Name", "item_name" and "ITEM-NAME" all match "item name".
# Earlier names in each list win if a file has more than one match.
# ---------------------------------------------------------------------------
FIELDS = {
    "date": {
        "label": "Date (or date + time)",
        "required": True,
        "names": ["datetime", "date time", "timestamp", "created at", "order date",
                  "transaction date", "sale date", "paid at", "date", "day"],
    },
    "time": {
        "label": "Time (if separate from date)",
        "required": False,
        "names": ["time", "order time", "sale time", "transaction time"],
    },
    "product": {
        "label": "Product / item name",
        "required": True,
        "names": ["product", "lineitem name", "item", "item name", "product name",
                  "line item", "menu item", "description", "product title"],
    },
    "total": {
        "label": "Line total ($)",
        "required": False,  # either this or unit price is needed (checked later)
        "names": ["total", "net sales", "line total", "item total", "gross sales",
                  "sales", "amount", "revenue", "net total"],
    },
    "unit_price": {
        "label": "Unit price ($)",
        "required": False,
        "names": ["unit price", "lineitem price", "price", "item price",
                  "price each"],
    },
    "quantity": {
        "label": "Quantity",
        "required": False,
        "names": ["quantity", "qty", "lineitem quantity", "units", "quantity sold",
                  "items sold", "count"],
    },
    "transaction_id": {
        "label": "Order / transaction ID",
        "required": False,
        "names": ["transaction id", "order id", "order number", "order", "receipt",
                  "receipt number", "ticket", "check number", "payment id"],
    },
    "category": {
        "label": "Category",
        "required": False,
        "names": ["category", "product type", "item category", "department", "type"],
    },
}

NOT_PRESENT = None  # what a field maps to when the file doesn't have it


def _normalize(name):
    """'Lineitem_Name ' -> 'lineitem name' so names compare easily."""
    return re.sub(r"[^a-z0-9]+", " ", str(name).lower()).strip()


# ---------------------------------------------------------------------------
# Step 1: read the file
# ---------------------------------------------------------------------------
def read_file(file):
    """Open a CSV from a path or a Streamlit upload.

    Some systems save files in older text encodings, so if the normal one
    fails we try again with a more forgiving one.
    """
    try:
        return pd.read_csv(file, encoding="utf-8-sig")
    except UnicodeDecodeError:
        if hasattr(file, "seek"):
            file.seek(0)  # an uploaded file must be rewound before re-reading
        return pd.read_csv(file, encoding="latin-1")


# ---------------------------------------------------------------------------
# Step 2: guess which column is which
# ---------------------------------------------------------------------------
def guess_columns(raw):
    """Return {field: column name in the file, or None} for every field."""
    by_normalized = {_normalize(col): col for col in raw.columns}
    is_shopify_style = any(n.startswith("lineitem") for n in by_normalized)

    mapping = {}
    used = set()
    for field, info in FIELDS.items():
        names = list(info["names"])
        if is_shopify_style:
            # In Shopify files "Total" is the whole order's total, repeated on
            # every line, so we must NOT use it as a line total. "Name" holds
            # the order number.
            if field == "total":
                names = []
            if field == "transaction_id":
                names = ["name"] + names
        mapping[field] = NOT_PRESENT
        for name in names:
            col = by_normalized.get(name)
            if col is not None and col not in used:
                mapping[field] = col
                used.add(col)
                break

    # If we found a line total, we don't also need the unit price.
    if mapping["total"] is not NOT_PRESENT:
        mapping["unit_price"] = NOT_PRESENT
    return mapping


def missing_required(mapping):
    """List the human-readable names of required info that isn't mapped."""
    missing = [FIELDS[f]["label"] for f, info in FIELDS.items()
               if info["required"] and mapping.get(f) is NOT_PRESENT]
    if mapping.get("total") is NOT_PRESENT and mapping.get("unit_price") is NOT_PRESENT:
        missing.append("Line total ($) or Unit price ($)")
    return missing


# ---------------------------------------------------------------------------
# Step 3: clean everything into the standard format
# ---------------------------------------------------------------------------
def _to_money(series):
    """Turn text like '$1,234.50', 'CA$5.25' or '(3.00)' into numbers."""
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(float)
    text = series.astype(str).str.strip()
    negative = text.str.startswith("(") | text.str.startswith("-")
    digits = text.str.replace(r"[^0-9.]", "", regex=True)
    values = pd.to_numeric(digits, errors="coerce")
    return values.where(~negative, -values)


def standardize(raw, mapping):
    """Build the standard sales table from a raw export.

    Returns (df, notes). `notes` are plain-English messages about anything
    we had to assume or skip, so the owner knows what happened.
    """
    problems = missing_required(mapping)
    if problems:
        raise ValueError("Please tell us which column has: " + ", ".join(problems))

    notes = []
    col = mapping.get

    # --- Date and time -----------------------------------------------------
    when = raw[col("date")].astype(str)
    if col("time") is not NOT_PRESENT:
        when = when + " " + raw[col("time")].astype(str)
    # Remove time-zone endings like "-0600" or "Z" so every sale keeps the
    # shop's local time (8am stays 8am).
    when = when.str.replace(r"\s*(Z|[+-]\d{2}:?\d{2})$", "", regex=True)
    df = pd.DataFrame({
        "datetime": pd.to_datetime(when, errors="coerce", format="mixed"),
        "product": raw[col("product")].astype(str).str.strip(),
    })
    if df["datetime"].dt.tz is not None:
        df["datetime"] = df["datetime"].dt.tz_localize(None)  # drop time zones

    # --- Quantity ------------------------------------------------------------
    if col("quantity") is not NOT_PRESENT:
        df["quantity"] = pd.to_numeric(raw[col("quantity")], errors="coerce").fillna(1)
    else:
        df["quantity"] = 1
        notes.append("No quantity column found, so we counted each row as 1 item.")

    # --- Money -------------------------------------------------------------
    if col("total") is not NOT_PRESENT:
        df["total"] = _to_money(raw[col("total")])
    else:
        df["total"] = _to_money(raw[col("unit_price")]) * df["quantity"]

    # --- Category (optional) ---------------------------------------------------
    if col("category") is not NOT_PRESENT:
        df["category"] = raw[col("category")].fillna("Uncategorized").astype(str)
    else:
        df["category"] = "Uncategorized"

    # --- Remove rows we can't use -----------------------------------------------
    bad = df["datetime"].isna() | df["total"].isna() | df["product"].isin(["", "nan"])
    if bad.any():
        notes.append(f"Skipped {bad.sum():,} row(s) with an unreadable date, "
                     f"price or product name.")
    df = df[~bad].copy()
    raw = raw.loc[df.index]
    if df.empty:
        raise ValueError("We couldn't read any sales from this file. Check that the "
                         "columns are matched correctly.")

    # --- Transaction IDs -------------------------------------------------------
    has_time = has_time_of_day(df)
    if col("transaction_id") is not NOT_PRESENT:
        df["transaction_id"] = raw[col("transaction_id")].astype(str)
    elif has_time:
        # Items rung up at the exact same moment were almost certainly one sale.
        df["transaction_id"] = df["datetime"].astype(str)
        notes.append("No order ID column found, so items sold at the exact same "
                     "time were grouped as one sale.")
    else:
        df["transaction_id"] = df.index.astype(str)
        notes.append("No order ID column found, so each row was counted as its "
                     "own sale. 'Average sale' may be lower than reality.")

    if not has_time:
        notes.append("No time of day found, so busy-hour charts are hidden.")

    # --- Helper columns used by the analysis ---------------------------------
    df["date"] = df["datetime"].dt.date
    df["hour"] = df["datetime"].dt.hour
    df["weekday"] = df["datetime"].dt.day_name()
    return df.sort_values("datetime").reset_index(drop=True), notes


def has_time_of_day(df):
    """True if the data includes times, not just dates (all at midnight)."""
    times = df["datetime"].dt.hour * 60 + df["datetime"].dt.minute
    return times.nunique() > 1


def load_sales(file):
    """Shortcut: read, guess and standardize in one go (used for testing)."""
    raw = read_file(file)
    df, _ = standardize(raw, guess_columns(raw))
    return df
