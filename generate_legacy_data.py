import pandas as pd
from faker import Faker
import random

fake = Faker()
Faker.seed(42)
random.seed(42)

def messy_date():
    """Simulate a legacy system that exported dates in inconsistent formats."""
    d = fake.date_between(start_date='-3y', end_date='today')
    fmt = random.choice(["%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y", "%d-%b-%Y"])
    return d.strftime(fmt)

def build_rows(n=2000):
    rows = []
    for i in range(n):
        customer_id = random.randint(1, 400)  # deliberate overlap across records
        rows.append({
            "record_id": i,
            "customer_name": fake.name(),
            "customer_email": fake.email(),
            "order_date": messy_date(),
            "product": fake.word(),
            "amount": round(random.uniform(10, 5000), 2),
            "region": random.choice(["US", "us", "United States", "EMEA", "emea", "APAC", ""]),
            "status": random.choice(["Complete", "complete", "COMPLETE", "Pending", "cancelled", None]),
        })
    return rows

if __name__ == "__main__":
    rows = build_rows(2000)
    # inject duplicate rows on purpose, like a real messy export often has
    rows += random.sample(rows, 150)

    df = pd.DataFrame(rows)
    df.to_csv("data/raw_legacy_export.csv", index=False)
    print(f"Generated {len(df)} raw rows (including intentional duplicates and inconsistencies)")