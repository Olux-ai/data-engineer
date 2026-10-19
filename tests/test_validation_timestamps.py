import pandas as pd
import pytest

from src.validation.validate_payments import run_validation_framework


@pytest.fixture
def timestamp_validation_environment(tmp_path, monkeypatch):
  # Run the test inside a temporary directory.
  monkeypatch.chdir(tmp_path)

  raw_dir = tmp_path / "data" / "raw"
  raw_dir.mkdir(parents=True)

  raw_path = raw_dir / "payments.csv"

  # Create two valid records with unique payment IDs.
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
      "payment_id": "PAY-002",
      "customer_id": "CUS-002",
      "merchant_id": "MER-002",
      "amount_minor": 20000,
      "currency": "EUR",
      "status": "FAILED",
      "created_at": "2026-10-01T10:05:00Z",
    },
])

  payments.to_csv(raw_path, index=False)

  return tmp_path, raw_path


def test_valid_timestamps_are_accepted(
  timestamp_validation_environment,
):
  tmp_path, raw_path = timestamp_validation_environment

  run_validation_framework(str(raw_path))

  processed = pd.read_csv(
    tmp_path / "data" / "processed" / "payments.csv"
  )

  rejected = pd.read_csv(
    tmp_path / "data" / "rejected" / "rejected_payments.csv"
  )

  # Both records should pass validation.
  assert len(processed) == 2
  assert rejected.empty


def test_invalid_timestamp_is_rejected(
  timestamp_validation_environment,
):
  tmp_path, raw_path = timestamp_validation_environment

  # Introduce an invalid timestamp into the first record.
  payments = pd.read_csv(raw_path)
  payments.loc[0, "created_at"] = "not-a-date"
  payments.to_csv(raw_path, index=False)

  run_validation_framework(str(raw_path))

  processed = pd.read_csv(
    tmp_path / "data" / "processed" / "payments.csv"
  )

  rejected = pd.read_csv(
    tmp_path / "data" / "rejected" / "rejected_payments.csv"
  )

  # The invalid record should be rejected, while the valid one passes.
  assert len(processed) == 1
  assert len(rejected) == 1

  assert rejected.iloc[0]["payment_id"] == "PAY-001"

  assert (
    "ERR_TIME: created_at is not a valid timestamp"
    in rejected.iloc[0]["validation_errors"]
  )