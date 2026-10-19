import pandas as pd
import pytest

from src.validation.validate_payments import run_validation_framework


@pytest.fixture
def validation_environment(tmp_path, monkeypatch):
  monkeypatch.chdir(tmp_path)

  raw_dir = tmp_path / "data" / "raw"
  raw_dir.mkdir(parents=True)

  raw_path = raw_dir / "payments.csv"

  payments = pd.DataFrame([
    {
      "payment_id": "PAY-001",
      "customer_id": "CUS-001",
      "merchant_id": "MER-001",
      "amount_minor": 15000,
      "currency": "USD",
      "status": "SUCCESS",
      "created_at": "2026-10-01T10:00:00Z",
  },
  {
    "payment_id": "PAY-001",
    "customer_id": "CUS-002",
    "merchant_id": "MER-002",
    "amount_minor": 20000,
    "currency": "EUR",
    "status": "FAILED",
    "created_at": "2026-10-01T10:05:00Z",
  },
  {
    "payment_id": "PAY-002",
    "customer_id": "CUS-003",
    "merchant_id": "MER-003",
    "amount_minor": 25000,
    "currency": "GBP",
    "status": "SUCCESS",
    "created_at": "2026-10-01T10:10:00Z",
  },
])

  payments.to_csv(raw_path, index=False)

  return tmp_path, raw_path


def test_all_records_with_duplicate_payment_ids_are_rejected(
  validation_environment,
):
  tmp_path, raw_path = validation_environment

  run_validation_framework(str(raw_path))

  processed = pd.read_csv(
    tmp_path / "data" / "processed" / "payments.csv"
  )

  rejected = pd.read_csv(
    tmp_path / "data" / "rejected" / "rejected_payments.csv"
  )

  assert len(processed) == 1
  assert processed["payment_id"].tolist() == ["PAY-002"]

  assert len(rejected) == 2
  assert rejected["payment_id"].tolist() == [
    "PAY-001",
    "PAY-001",
  ]

  assert rejected["validation_errors"].str.contains(
    "Duplicate payment_id"
  ).all()


def test_all_three_occurrences_of_a_duplicate_id_are_rejected(
  validation_environment,
):
  tmp_path, raw_path = validation_environment

  payments = pd.read_csv(raw_path)

  third_record = payments.iloc[[0]].copy()
  third_record["customer_id"] = "CUS-004"

  payments = pd.concat(
    [payments, third_record],
    ignore_index=True,
  )

  payments.to_csv(raw_path, index=False)

  run_validation_framework(str(raw_path))

  processed = pd.read_csv(
    tmp_path / "data" / "processed" / "payments.csv"
  )

  rejected = pd.read_csv(
    tmp_path / "data" / "rejected" / "rejected_payments.csv"
  )

  assert len(processed) == 1
  assert processed["payment_id"].tolist() == ["PAY-002"]

  assert len(rejected) == 3
  assert rejected["payment_id"].tolist().count("PAY-001") == 3

  assert rejected["validation_errors"].str.contains(
    "Duplicate payment_id"
  ).all()