import pandas as pd
from migrate import clean


def make_row(**overrides):
    """Helper to build a single-row DataFrame with sensible defaults, easy to override per test."""
    base = {
        "record_id": 1,
        "customer_name": "Jane Doe",
        "customer_email": "jane@example.com",
        "order_date": "2024-01-15",
        "product": "widget",
        "amount": 100.0,
        "region": "us",
        "status": "complete",
    }
    base.update(overrides)
    return pd.DataFrame([base])


def test_removes_exact_duplicates():
    df = pd.concat([make_row(), make_row()], ignore_index=True)
    result = clean(df)
    assert len(result) == 1


def test_region_normalisation_lowercase():
    df = make_row(region="us")
    result = clean(df)
    assert result.iloc[0]["region"] == "US"


def test_region_normalisation_full_name():
    df = make_row(region="United States")
    result = clean(df)
    assert result.iloc[0]["region"] == "US"


def test_region_unknown_when_blank():
    df = make_row(region="")
    result = clean(df)
    assert result.iloc[0]["region"] == "Unknown"


def test_status_normalisation():
    df = make_row(status="COMPLETE")
    result = clean(df)
    assert result.iloc[0]["status"] == "Complete"


def test_status_unknown_when_missing():
    df = make_row(status=None)
    result = clean(df)
    assert result.iloc[0]["status"] == "Unknown"


def test_drops_row_with_missing_email():
    df = make_row(customer_email=None)
    result = clean(df)
    assert len(result) == 0


def test_handles_multiple_date_formats():
    df = pd.concat([
        make_row(record_id=1, customer_email="a@x.com", order_date="2024-01-15"),
        make_row(record_id=2, customer_email="b@x.com", order_date="15/01/2024"),
        make_row(record_id=3, customer_email="c@x.com", order_date="01-15-2024"),
    ], ignore_index=True)
    result = clean(df)
    # All three should parse successfully and survive cleaning
    assert len(result) == 3
    assert result["order_date"].notna().all()