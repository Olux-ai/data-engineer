import pandas as pd

from src.validation.validate_payments import run_validation_framework


def test_missing_raw_file_returns_without_crashing(tmp_path, monkeypatch):
  """A missing raw file should not crash the validation framework."""
  monkeypatch.chdir(tmp_path)

  result = run_validation_framework("data/raw/missing_payments.csv")

  assert result is None


def test_missing_required_columns_returns_without_crashing(
  tmp_path, monkeypatch
):
  """A dataset missing required columns should stop validation safely."""
  monkeypatch.chdir(tmp_path)

  raw_dir = tmp_path / "data" / "raw"
  raw_dir.mkdir(parents=True)

  raw_file = raw_dir / "payments.csv"

  # Deliberately omit required payment columns.
  pd.DataFrame(
    {
      "payment_id": ["PAY-001"],
      "amount_minor": [5000],
    }
  ).to_csv(raw_file, index=False)

  result = run_validation_framework(str(raw_file))

  assert result is None
