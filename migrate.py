import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

REGION_MAP = {
    "us": "US",
    "united states": "US",
    "emea": "EMEA",
    "apac": "APAC",
    "": "Unknown",
}

STATUS_MAP = {
    "complete": "Complete",
    "pending": "Pending",
    "cancelled": "Cancelled",
}


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize the messy legacy export into clean, consistent values."""
    df = df.copy()

    # Dates came in multiple formats (YYYY-MM-DD, DD/MM/YYYY, etc.) — parse flexibly
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce", format="mixed")

    # Region had inconsistent casing and full names mixed with abbreviations
    df["region"] = df["region"].fillna("").str.lower().map(REGION_MAP).fillna("Unknown")

    # Status had inconsistent casing and some nulls
    df["status"] = df["status"].fillna("unknown").str.lower().map(STATUS_MAP).fillna("Unknown")

    before = len(df)
    df = df.drop_duplicates(subset=["customer_email", "order_date", "amount", "product"])
    print(f"Removed {before - len(df)} duplicate rows")

    before = len(df)
    df = df.dropna(subset=["order_date", "customer_email"])
    print(f"Dropped {before - len(df)} rows with unparseable dates or missing email")

    return df


def load(df: pd.DataFrame):
    with engine.begin() as conn:
        # Ensure schema exists
        conn.execute(text(open("schema.sql").read()))

        # Load dimension: region
        for region in df["region"].unique():
            conn.execute(
                text("INSERT INTO dim_region (region_name) VALUES (:r) ON CONFLICT DO NOTHING"),
                {"r": region},
            )

        # Load dimension: customer (deduplicated by email)
        customers = df.drop_duplicates(subset=["customer_email"])
        for _, row in customers.iterrows():
            conn.execute(
                text("""
                    INSERT INTO dim_customer (customer_name, customer_email)
                    VALUES (:n, :e)
                    ON CONFLICT (customer_email) DO NOTHING
                """),
                {"n": row["customer_name"], "e": row["customer_email"]},
            )

        # Load fact table: orders, joined against the dimensions just inserted
        for _, row in df.iterrows():
            conn.execute(
                text("""
                    INSERT INTO fact_orders
                        (customer_id, region_id, order_date, product, amount, status, source_record_id)
                    SELECT c.customer_id, r.region_id, :d, :p, :a, :s, :rid
                    FROM dim_customer c, dim_region r
                    WHERE c.customer_email = :e AND r.region_name = :region
                """),
                {
                    "d": row["order_date"].date(),
                    "p": row["product"],
                    "a": row["amount"],
                    "s": row["status"],
                    "rid": row["record_id"],
                    "e": row["customer_email"],
                    "region": row["region"],
                },
            )


if __name__ == "__main__":
    raw = pd.read_csv("data/raw_legacy_export.csv")
    print(f"Loaded {len(raw)} raw rows from CSV")

    cleaned = clean(raw)
    print(f"{len(cleaned)} rows remain after cleaning")

    load(cleaned)
    print(f"Migration complete: {len(cleaned)} rows loaded into fact_orders")