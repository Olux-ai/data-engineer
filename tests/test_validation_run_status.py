import json
import pytest
import pandas as pd
import src.validation.validate_payments as validation_module
from src.validation.validate_payments import stage_csv_output
from src.validation.validate_payments import run_validation_framework



def test_missing_input_does_not_modify_existing_processed_output(
  tmp_path, monkeypatch
):
  """A failed run must preserve the last successful output."""
  monkeypatch.chdir(tmp_path)

  processed_dir = tmp_path / "data" / "processed"
  processed_dir.mkdir(parents=True)

  processed_file = processed_dir / "payments.csv"
  previous_output = "payment_id,amount_minor\nPAY-OLD,5000\n"
  processed_file.write_text(previous_output, encoding="utf-8")

  result = run_validation_framework("data/raw/missing_payments.csv")

  assert result is None
  assert processed_file.exists()
  assert processed_file.read_text(encoding="utf-8") == previous_output


def test_missing_raw_file_writes_failed_run_report(tmp_path, monkeypatch):
  monkeypatch.chdir(tmp_path)

  run_validation_framework("data/raw/missing_payments.csv")

  report_path = tmp_path / "data" / "reports" / "latest_run.json"

  assert report_path.exists()

  report = json.loads(report_path.read_text(encoding="utf-8"))

  assert report["status"] == "FAILED"
  assert report["completed_at"] is not None
  assert report["error_message"] is not None
  assert report["input_records"] == 0

def test_missing_required_columns_writes_failed_run_report(
tmp_path, monkeypatch
):

  monkeypatch.chdir(tmp_path)

  raw_dir = tmp_path / "data" / "raw"
  raw_dir.mkdir(parents=True)

  raw_file = raw_dir / "payments.csv"
  pd.DataFrame({
    "payment_id": ["PAY-001"],
    "amount_minor": [5000],
  }).to_csv(raw_file, index=False)

  run_validation_framework(str(raw_file))

  report_path = tmp_path / "data" / "reports" / "latest_run.json"

  assert report_path.exists()

  report = json.loads(report_path.read_text(encoding="utf-8"))

  assert report["status"] == "FAILED"
  assert report["completed_at"] is not None
  assert "Missing required columns" in report["error_message"]
  assert report["input_records"] == 1

def test_successful_validation_writes_run_report(tmp_path, monkeypatch):
  monkeypatch.chdir(tmp_path)

  raw_dir = tmp_path / "data" / "raw"
  raw_dir.mkdir(parents=True)

  raw_file = raw_dir / "payments.csv"

  pd.DataFrame({
  "payment_id": ["PAY-001", "PAY-002", "PAY-003"],
  "customer_id": ["CUS-001", "CUS-002", "CUS-003"],
  "merchant_id": ["MER-001", "MER-001", "MER-002"],
  "amount_minor": [5000, 2500, 3000],
  "currency": ["USD", "EUR", "NGN"],
  "status": ["SUCCESS", "FAILED", "PENDING"],
  "created_at": [
  "2026-10-01T10:00:00Z",
  "2026-10-01T11:00:00Z",
  "2026-10-01T12:00:00Z",
  ],
  }).to_csv(raw_file, index=False)

  run_validation_framework(str(raw_file))

  report_path = tmp_path / "data" / "reports" / "latest_run.json"
  assert report_path.exists()

  report = json.loads(report_path.read_text(encoding="utf-8"))

  assert report["status"] == "SUCCESS"
  assert report["completed_at"] is not None
  assert report["error_message"] is None
  assert report["input_records"] == 3
  assert report["processed_records"] == 3
  assert report["rejected_records"] == 0
  assert report["pass_rate"] == 100.0
  assert report["run_id"]
  assert report["started_at"]



def test_output_write_failure_records_failed_status(tmp_path, monkeypatch):
  monkeypatch.chdir(tmp_path)

  raw_dir = tmp_path / "data" / "raw"
  raw_dir.mkdir(parents=True)

  raw_file = raw_dir / "payments.csv"

  pd.DataFrame({
    "payment_id": ["PAY-001"],
    "customer_id": ["CUS-001"],
    "merchant_id": ["MER-001"],
    "amount_minor": [5000],
    "currency": ["USD"],
    "status": ["SUCCESS"],
    "created_at": ["2026-10-01T10:00:00Z"],
  }).to_csv(raw_file, index=False)

  def fail_csv_write(self, *args, **kwargs):
    raise OSError("Simulated output disk failure")

  monkeypatch.setattr(pd.DataFrame, "to_csv", fail_csv_write)

  with pytest.raises(OSError, match="Simulated output disk failure"):
    run_validation_framework(str(raw_file))

  report_path = tmp_path / "data" / "reports" / "latest_run.json"
  report = json.loads(report_path.read_text(encoding="utf-8"))

  assert report["status"] == "FAILED"
  assert report["completed_at"] is not None
  assert "Simulated output disk failure" in report["error_message"]
  assert report["input_records"] == 1
  assert report["run_id"]
  assert report["started_at"]

def test_output_write_failure_resilience(tmp_path, monkeypatch):
  monkeypatch.chdir(tmp_path)

  raw_dir = tmp_path / "data" / "raw"
  raw_dir.mkdir(parents=True)

  raw_file = raw_dir / "payments.csv"

  pd.DataFrame({
      "payment_id": ["PAY-001"],
      "customer_id": ["CUS-001"],
      "merchant_id": ["MER-001"],
      "amount_minor": [5000],
      "currency": ["USD"],
      "status": ["SUCCESS"],
      "created_at": ["2026-10-01T10:00:00Z"],
  }).to_csv(raw_file, index=False)

  def fail_csv_write(self, *args, **kwargs):
    raise OSError("Simulated output disk failure")

  monkeypatch.setattr(pd.DataFrame, "to_csv", fail_csv_write)

  try:
    run_validation_framework(str(raw_file))
  except OSError as exc:
    assert "Simulated output disk failure" in str(exc)

  report_path = tmp_path / "data" / "reports" / "latest_run.json"

  if report_path.exists():
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] != "SUCCESS"


def test_staging_failure_preserves_existing_outputs(tmp_path, monkeypatch):
  monkeypatch.chdir(tmp_path)

  raw_dir = tmp_path / "data" / "raw"
  raw_dir.mkdir(parents=True)

  raw_file = raw_dir / "payments.csv"
  pd.DataFrame({
      "payment_id": ["PAY-001"],
      "customer_id": ["CUS-001"],
      "merchant_id": ["MER-001"],
      "amount_minor": [5000],
      "currency": ["USD"],
      "status": ["SUCCESS"],
      "created_at": ["2026-10-01T10:00:00Z"],
  }).to_csv(raw_file, index=False)

  processed_path = tmp_path / "data" / "processed" / "payments.csv"
  rejected_path = tmp_path / "data" / "rejected" / "rejected_payments.csv"

  processed_path.parent.mkdir(parents=True)
  rejected_path.parent.mkdir(parents=True)

  previous_processed = "previous processed output"
  previous_rejected = "previous rejected output"

  processed_path.write_text(previous_processed, encoding="utf-8")
  rejected_path.write_text(previous_rejected, encoding="utf-8")

  original_stage_csv_output = stage_csv_output
  call_count = 0

  def fail_on_second_staging(dataframe, output_path):
    nonlocal call_count
    call_count += 1

    if call_count == 2:
      raise OSError("Simulated second staging failure")

    return original_stage_csv_output(dataframe, output_path)

  monkeypatch.setattr(
      "src.validation.validate_payments.stage_csv_output",
      fail_on_second_staging,
  )

  with pytest.raises(OSError, match="Simulated second staging failure"):
    run_validation_framework(str(raw_file))

  assert processed_path.read_text(encoding="utf-8") == previous_processed
  assert rejected_path.read_text(encoding="utf-8") == previous_rejected

def test_second_output_publish_failure_restores_previous_outputs(
tmp_path,
monkeypatch,
):
  monkeypatch.chdir(tmp_path)

# Create a valid raw payment file.
  raw_dir = tmp_path / "data" / "raw"
  raw_dir.mkdir(parents=True)

  raw_file = raw_dir / "payments.csv"

  pd.DataFrame({
      "payment_id": ["PAY-001"],
      "customer_id": ["CUS-001"],
      "merchant_id": ["MER-001"],
      "amount_minor": [5000],
      "currency": ["USD"],
      "status": ["SUCCESS"],
      "created_at": ["2026-10-01T10:00:00Z"],
  }).to_csv(raw_file, index=False)

  # Create existing output files.
  processed_path = (
      tmp_path / "data" / "processed" / "payments.csv"
  )
  rejected_path = (
      tmp_path / "data" / "rejected" / "rejected_payments.csv"
  )

  processed_path.parent.mkdir(parents=True)
  rejected_path.parent.mkdir(parents=True)

  previous_processed = "previous processed output"
  previous_rejected = "previous rejected output"

  processed_path.write_text(
      previous_processed,
      encoding="utf-8",
  )
  rejected_path.write_text(
      previous_rejected,
      encoding="utf-8",
  )

  # Simulate failure on the second output replacement.
  original_replace = validation_module.os.replace
  replace_calls = 0

  def fail_on_second_publish(source, destination):
    nonlocal replace_calls
    replace_calls += 1

    if replace_calls == 2:
        raise OSError("Simulated second publish failure")

    return original_replace(source, destination)

  monkeypatch.setattr(
      validation_module.os,
      "replace",
      fail_on_second_publish,
  )

  # The framework should raise the simulated publishing error.
  with pytest.raises(
      OSError,
      match="Simulated second publish failure",
  ):
      run_validation_framework(str(raw_file))

  # Both files should retain their original contents.
  assert processed_path.read_text(
      encoding="utf-8",
  ) == previous_processed

  assert rejected_path.read_text(
      encoding="utf-8",
  ) == previous_rejected

  # The run report should record the failed execution.
  report_path = tmp_path / "data" / "reports" / "latest_run.json"

  report = json.loads(
      report_path.read_text(encoding="utf-8")
  )

  assert report["status"] == "FAILED"
  assert "Simulated second publish failure" in report["error_message"]
