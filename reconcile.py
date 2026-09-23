import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))


def get_migrated_stats():
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM fact_orders")).scalar()
        total = conn.execute(text("SELECT SUM(amount) FROM fact_orders")).scalar()
        by_region = conn.execute(text("""
            SELECT r.region_name, COUNT(*) AS orders, SUM(f.amount) AS total
            FROM fact_orders f
            JOIN dim_region r ON f.region_id = r.region_id
            GROUP BY r.region_name
            ORDER BY r.region_name
        """)).fetchall()
    return count, total, by_region


def get_expected_stats():
    raw = pd.read_csv("data/raw_legacy_export.csv")
    # Mirror the same dedup logic used in migrate.py's clean() function,
    # so we're comparing against what SHOULD have survived cleaning.
    dedup = raw.drop_duplicates(subset=["customer_email", "order_date", "amount", "product"])
    dedup = dedup.dropna(subset=["customer_email"])
    return len(raw), len(dedup), dedup["amount"].sum()


def main():
    raw_count, expected_count, expected_total = get_expected_stats()
    migrated_count, migrated_total, by_region = get_migrated_stats()

    print("=" * 50)
    print("RECONCILIATION REPORT")
    print("=" * 50)
    print(f"Raw source rows (incl. duplicates):     {raw_count}")
    print(f"Expected unique rows after cleaning:    {expected_count}")
    print(f"Rows actually migrated:                 {migrated_count}")
    print(f"Row count difference:                   {expected_count - migrated_count}")
    print()
    print(f"Expected total amount (source, dedup'd): {expected_total:,.2f}")
    print(f"Migrated total amount (warehouse):       {float(migrated_total):,.2f}")

    amount_diff = abs(expected_total - float(migrated_total))
    print(f"Amount discrepancy:                      {amount_diff:,.2f}")
    print()
    print("Breakdown by region:")
    for region, orders, total in by_region:
        print(f"  {region:10s}  {orders:5d} orders   {float(total):>12,.2f}")

    print()
    status = "PASS" if amount_diff < 1.00 else "FAIL — investigate discrepancy"
    print(f"RESULT: {status}")
    print("=" * 50)


if __name__ == "__main__":
    main()