from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile
import uuid
import pandas as pd


def write_run_report(report_path, report):
  """Write a pipeline run report to a temporary file, then replace the old report."""
  report_path = Path(report_path)
  report_path.parent.mkdir(parents=True, exist_ok=True)

  temporary_path = None

  try:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".tmp",
        prefix="run_report_",
        dir=report_path.parent,
        delete=False,
    ) as report_file:
      temporary_path = Path(report_file.name)
      json.dump(report, report_file, indent=2)
      report_file.flush()
      os.fsync(report_file.fileno())

    os.replace(temporary_path, report_path)

  finally:
    if temporary_path is not None and temporary_path.exists():
      temporary_path.unlink()


def stage_csv_output(dataframe, output_path):
  """Write a DataFrame to a temporary CSV beside its final destination."""
  output_path = Path(output_path)
  output_path.parent.mkdir(parents=True, exist_ok=True)

  temporary_path = None

  try:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        suffix=".tmp",
        prefix=f"{output_path.stem}_",
        dir=output_path.parent,
        delete=False,
    ) as temporary_file:
      temporary_path = Path(temporary_file.name)
      dataframe.to_csv(temporary_file, index=False)
      temporary_file.flush()
      os.fsync(temporary_file.fileno())

    return temporary_path

  except Exception:
    if temporary_path is not None and temporary_path.exists():
      temporary_path.unlink()
    raise


def backup_existing_output(output_path):
  """Create a temporary backup of an existing output file."""
  output_path = Path(output_path)

  if not output_path.exists():
    return None

  with tempfile.NamedTemporaryFile(
      mode="wb",
      suffix=".bak",
      prefix=f"{output_path.stem}_",
      dir=output_path.parent,
      delete=False,
  ) as backup_file:
    backup_path = Path(backup_file.name)

    with output_path.open("rb") as original_file:
      shutil.copyfileobj(original_file, backup_file)

    backup_file.flush()
    os.fsync(backup_file.fileno())

  return backup_path


def run_validation_framework(raw_path="data/raw/payments.csv"):
  print(" Initializing Core Payments Validation Framework...")

  # Define exact path parameters
  RAW_PATH = raw_path
  PROCESSED_PATH = "data/processed/payments.csv"
  REJECTED_PATH = "data/rejected/rejected_payments.csv"
  RUN_REPORT_PATH = "data/reports/latest_run.json"

  # Reference configuration schemas
  REQUIRED_COLUMNS = [
      "payment_id",
      "customer_id",
      "merchant_id",
      "amount_minor",
      "currency",
      "status",
      "created_at",
  ]
  VALID_CURRENCIES = {"USD", "EUR", "GBP", "NGN"}
  VALID_STATUSES = {"SUCCESS", "FAILED", "PENDING"}

  run_started_at = datetime.now(timezone.utc)

  run_report = {
      "run_id": str(uuid.uuid4()),
      "started_at": run_started_at.isoformat(),
      "completed_at": None,
      "status": "RUNNING",
      "input_records": 0,
      "processed_records": 0,
      "rejected_records": 0,
      "pass_rate": 0.0,
      "error_message": None,
  }

  # Ensure environment structure is complete
  os.makedirs(os.path.dirname(PROCESSED_PATH), exist_ok=True)
  os.makedirs(os.path.dirname(REJECTED_PATH), exist_ok=True)
  os.makedirs(os.path.dirname(RUN_REPORT_PATH), exist_ok=True)

  # Check if raw data exists before checking files
  if not os.path.exists(RAW_PATH):
    error_message = (
        f"Raw ingested file not found at '{RAW_PATH}'. "
        "Run ingestion pipeline first."
    )

    run_report["status"] = "FAILED"
    run_report["completed_at"] = datetime.now(timezone.utc).isoformat()
    run_report["error_message"] = error_message

    write_run_report(RUN_REPORT_PATH, run_report)

    print(f"CRITICAL ERROR: {error_message}")
    return

  # Load data matrix
  df = pd.read_csv(RAW_PATH)
  total_records = len(df)
  print(f" Loaded {total_records:,} records from raw ingestion vault.")
  # -------------------------------------------------------------
  # RULE 1: Global Schema Layout Constraint Check (Required Columns)
  # -------------------------------------------------------------
  missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
  if missing_cols:
    error_message = f"Missing required columns: {missing_cols}"

    run_report["status"] = "FAILED"
    run_report["input_records"] = total_records
    run_report["completed_at"] = datetime.now(timezone.utc).isoformat()
    run_report["error_message"] = error_message

    write_run_report(RUN_REPORT_PATH, run_report)

    print(f"CRITICAL METADATA FAILURE: {error_message}")
    print("Framework halting execution to prevent pipeline crash.")
    return

  # Initialize an audit log trace column on every row to capture failure reasons
  df["validation_errors"] = [[] for _ in range(len(df))]

  # RULE 2: Validate required field values
  REQUIRED_VALUE_COLUMNS = ["customer_id", "merchant_id", "created_at"]

  for column in REQUIRED_VALUE_COLUMNS:
    missing_value_mask = (
        df[column].isna() | df[column].astype("string").str.strip().eq("")
    )

    df.loc[missing_value_mask, "validation_errors"].apply(
        lambda errors: errors.append(f"ERR_REQD: {column} is missing or blank")
    )

  # RULE 3: Timestamp Format and Validity Check
  parsed_timestamps = pd.to_datetime(
      df["created_at"], format="ISO8601", errors="coerce", utc=True
  )

  invalid_timestamp_mask = (
      df["created_at"].notna()
      & df["created_at"].astype("string").str.strip().ne("")
      & parsed_timestamps.isna()
  )

  df.loc[invalid_timestamp_mask, "validation_errors"].apply(
      lambda errors: errors.append("ERR_TIME: created_at is not a valid timestamp")
  )

  # -------------------------------------------------------------
  # RULE 4: Primary Key Constraints (Nulls & Uniqueness)
  # -------------------------------------------------------------
  payment_id = df["payment_id"].astype("string").str.strip()

  missing_payment_id_mask = payment_id.isna() | payment_id.eq("")

  duplicate_payment_id_mask = (
      payment_id.notna() & payment_id.ne("") & payment_id.duplicated(keep=False)
  )

  df.loc[missing_payment_id_mask, "validation_errors"].apply(
      lambda errors: errors.append("ERR_REQD: payment_id is missing/null")
  )

  df.loc[duplicate_payment_id_mask, "validation_errors"].apply(
      lambda errors: errors.append("ERR_UNIQ: Duplicate payment_id encountered")
  )

  # -------------------------------------------------------------
  # RULE 5: Financial Sanity Constraints (Positive Integers)
  # -------------------------------------------------------------
  amount_numeric = pd.to_numeric(df["amount_minor"], errors="coerce")

  invalid_type_mask = amount_numeric.isnull()
  df.loc[invalid_type_mask, "validation_errors"].apply(
      lambda x: x.append(
          "ERR_VAL: amount_minor is missing or not a valid numeric data type"
      )
  )

  invalid_range_mask = amount_numeric.notnull() & (amount_numeric <= 0)
  df.loc[invalid_range_mask, "validation_errors"].apply(
      lambda x: x.append(
          "ERR_VAL: amount_minor must be a positive value greater than zero"
      )
  )

  invalid_int_mask = amount_numeric.notnull() & (amount_numeric % 1 != 0)
  df.loc[invalid_int_mask, "validation_errors"].apply(
      lambda x: x.append("ERR_VAL: amount_minor must be a positive integer")
  )
  df["amount_minor"] = amount_numeric

  # -------------------------------------------------------------
  # RULE 6: Currency Code Enumeration Check
  # -------------------------------------------------------------
  invalid_currency_mask = ~df["currency"].isin(VALID_CURRENCIES) | df[
      "currency"
  ].isnull()
  df.loc[invalid_currency_mask, "validation_errors"].apply(
      lambda x: x.append(
          "ERR_CURR: Currency code invalid or outside accepted global domain"
      )
  )

  # -------------------------------------------------------------
  # RULE 7: Operational Status State Check
  # -------------------------------------------------------------
  invalid_status_mask = ~df["status"].isin(VALID_STATUSES) | df[
      "status"
  ].isnull()
  df.loc[invalid_status_mask, "validation_errors"].apply(
      lambda x: x.append(
          "ERR_STAT: Execution status does not match approved transaction states"
      )
  )

  # -------------------------------------------------------------
  # PIPELINE ROUTING ENGINE & LOG ENTRY SPLITTING
  # -------------------------------------------------------------
  is_valid_mask = df["validation_errors"].apply(len) == 0

  df_processed = df[is_valid_mask].copy()
  df_rejected = df[~is_valid_mask].copy()

  if not df_rejected.empty:
    df_rejected["validation_errors"] = df_rejected["validation_errors"].apply(
        lambda errors: " | ".join(errors)
    )

  df_processed = df_processed.drop(columns=["validation_errors"])

  passed_count = len(df_processed)
  failed_count = len(df_rejected)

  accounted_records = passed_count + failed_count

  if accounted_records != total_records:
    raise RuntimeError(
        f"Reconciliation failed: input={total_records}, "
        f"processed={passed_count}, rejected={failed_count}, "
        f"accounted={accounted_records}"
    )

  pass_rate = (
      (passed_count / total_records) * 100 if total_records > 0 else 0
  )

  # Stage both outputs and initialize backup trackers.
  staged_processed_path = None
  staged_rejected_path = None
  processed_backup_path = None
  rejected_backup_path = None
  processed_published = False
  rejected_published = False

  try:
    # Stage both new outputs first.
    staged_processed_path = stage_csv_output(
        df_processed,
        PROCESSED_PATH,
    )

    staged_rejected_path = stage_csv_output(
        df_rejected,
        REJECTED_PATH,
    )

    # Back up existing outputs before publishing new ones.
    processed_backup_path = backup_existing_output(
        PROCESSED_PATH,
    )

    rejected_backup_path = backup_existing_output(
        REJECTED_PATH,
    )

    # Publish the staged outputs.
    os.replace(staged_processed_path, PROCESSED_PATH)
    staged_processed_path = None
    processed_published = True

    os.replace(staged_rejected_path, REJECTED_PATH)
    staged_rejected_path = None
    rejected_published = True

  except Exception as exc:
    rollback_errors = []

    for output_path, backup_path, was_published in (
        (PROCESSED_PATH, processed_backup_path, processed_published),
        (REJECTED_PATH, rejected_backup_path, rejected_published),
    ):
      if not was_published:
        continue

      try:
        if backup_path is not None:
          os.replace(backup_path, output_path)

          if output_path == PROCESSED_PATH:
            processed_backup_path = None
          else:
            rejected_backup_path = None
        else:
          output_path_obj = Path(output_path)
          if output_path_obj.exists():
            output_path_obj.unlink()

      except Exception as rollback_exc:
        rollback_errors.append(
            f"Could not restore {output_path}: {rollback_exc}"
        )

    run_report["completed_at"] = datetime.now(timezone.utc).isoformat()
    run_report["status"] = "FAILED"
    run_report["input_records"] = total_records
    run_report["processed_records"] = passed_count
    run_report["rejected_records"] = failed_count
    run_report["pass_rate"] = round(pass_rate, 2)
    run_report["error_message"] = str(exc)

    if rollback_errors:
      run_report["error_message"] += (
          " | Rollback issues: " + "; ".join(rollback_errors)
      )

    write_run_report(RUN_REPORT_PATH, run_report)
    raise

  finally:
    # Remove temporary staged files that were not published.
    for staged_path in (
        staged_processed_path,
        staged_rejected_path,
    ):
      if staged_path is not None and staged_path.exists():
        staged_path.unlink()

    # Remove backups after successful publishing or completed rollback.
    for backup_path in (
        processed_backup_path,
        rejected_backup_path,
    ):
      if backup_path is not None and backup_path.exists():
        backup_path.unlink()

  # Mark the run successful only after both outputs are published.
  run_report["completed_at"] = datetime.now(timezone.utc).isoformat()
  run_report["status"] = "SUCCESS"
  run_report["input_records"] = total_records
  run_report["processed_records"] = passed_count
  run_report["rejected_records"] = failed_count
  run_report["pass_rate"] = round(pass_rate, 2)
  run_report["error_message"] = None

  write_run_report(RUN_REPORT_PATH, run_report)

  # -------------------------------------------------------------
  # METRICS DISPLAY LAYOUT
  # -------------------------------------------------------------
  print("\n=======================================================")
  print(" DATA QUALITY FRAMEWORK COMPLIANCE REPORT")
  print("=======================================================")
  print(f"• Raw Records Evaluated:    {total_records:,}")
  print(f"• Clean Records Processed: {passed_count:,} (✓ Saved to {PROCESSED_PATH})")
  print(f"• Corrupt Records Rejected: {failed_count:,} (⚠ Saved to {REJECTED_PATH})")
  print(f"• Data Platform Pass Rate: {pass_rate:.2f}%")
  print("=======================================================")

  if failed_count > 0:
    print("\n BREAKDOWN OF DETECTED DATA FAULTS:")

# Explode the error arrays to easily count individual rules broken
    all_errors = df[~is_valid_mask]["validation_errors"].explode()
    error_counts = all_errors.value_counts()
    for err, count in error_counts.items():
      print(f"  -> {err}: {count:,} instances")
  print("=======================================================\n")


if __name__ == "__main__":
  run_validation_framework()