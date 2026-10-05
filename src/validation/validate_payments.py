import os
import pandas as pd

def run_validation_framework(raw_path="data/raw/payments.csv"):
  print(" Initializing Core Payments Validation Framework...")
  
  # Define exact path parameters
  RAW_PATH = raw_path
  PROCESSED_PATH = "data/processed/payments.csv"
  REJECTED_PATH = "data/rejected/rejected_payments.csv"
  
  # Reference configuration schemas
  REQUIRED_COLUMNS = ['payment_id', 'customer_id', 'merchant_id', 'amount_minor', 'currency', 'status', 'created_at']
  VALID_CURRENCIES = {'USD', 'EUR', 'GBP', 'NGN'}
  VALID_STATUSES = {'SUCCESS', 'FAILED', 'PENDING'}
  
  # Ensure environment structure is complete
  os.makedirs(os.path.dirname(PROCESSED_PATH), exist_ok=True)
  os.makedirs(os.path.dirname(REJECTED_PATH), exist_ok=True)
  
  # Check if raw data exists before checking files
  if not os.path.exists(RAW_PATH):
    print(f" CRITICAL ERROR: Raw ingested file not found at '{RAW_PATH}'. Run ingestion pipeline first.")
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
    print(f" CRITICAL METADATA FAILURE: Missing required columns: {missing_cols}")
    print("Framework halting execution to prevent pipeline crash.")
    return

  # Initialize an audit log trace column on every row to capture failure reasons
  df['validation_errors'] = [[] for _ in range(len(df))]
  
  # -------------------------------------------------------------
  # RULE 2: Primary Key Constraints (Nulls & Uniqueness)
  # -------------------------------------------------------------
  # Flag missing primary key records
  null_payment_mask = df['payment_id'].isnull()
  df.loc[null_payment_mask, 'validation_errors'].apply(lambda x: x.append("ERR_REQD: payment_id is missing/null"))
  
  # Flag duplicate keys (Keep the first instance as valid, flag subsequent as corrupt)
  duplicate_mask = df.duplicated(subset=['payment_id'], keep='first') & df['payment_id'].notnull()
  df.loc[duplicate_mask, 'validation_errors'].apply(lambda x: x.append("ERR_UNIQ: Duplicate payment_id encountered"))
  
  # -------------------------------------------------------------
  # RULE 3: Financial Sanity Constraints (Positive Integers)
  # -------------------------------------------------------------
  # Step 1: Convert raw amount to numeric representation upfront
  amount_numeric = pd.to_numeric(df['amount_minor'], errors='coerce')
  
  # Step 2: Validate non-numeric / null values
  invalid_type_mask = amount_numeric.isnull()
  df.loc[invalid_type_mask, 'validation_errors'].apply(
    lambda x: x.append("ERR_VAL: amount_minor is missing or not a valid numeric data type")
  )
  
  # Step 3: Validate that valid numbers are positive (> 0)
  invalid_range_mask = amount_numeric.notnull() & (amount_numeric <= 0)
  df.loc[invalid_range_mask, 'validation_errors'].apply(
    lambda x: x.append("ERR_VAL: amount_minor must be a positive value greater than zero")
  )
  
  # Step 4: Validate that valid numbers are whole integers (no float values)
  invalid_int_mask = amount_numeric.notnull() & (amount_numeric % 1 != 0)
  df.loc[invalid_int_mask, 'validation_errors'].apply(
    lambda x: x.append("ERR_VAL: amount_minor must be a positive integer")
  )
  
  # -------------------------------------------------------------
  # RULE 4: Currency Code Enumeration Check
  # -------------------------------------------------------------
  invalid_currency_mask = ~df['currency'].isin(VALID_CURRENCIES) | df['currency'].isnull()
  df.loc[invalid_currency_mask, 'validation_errors'].apply(lambda x: x.append("ERR_CURR: Currency code invalid or outside accepted global domain"))
  
  # -------------------------------------------------------------
  # RULE 5: Operational Status State Check
  # -------------------------------------------------------------
  invalid_status_mask = ~df['status'].isin(VALID_STATUSES) | df['status'].isnull()
  df.loc[invalid_status_mask, 'validation_errors'].apply(lambda x: x.append("ERR_STAT: Execution status does not match approved transaction states"))

  # -------------------------------------------------------------
  # PIPELINE ROUTING ENGINE & LOG ENTRY SPLITTING
  # -------------------------------------------------------------
  # A row is valid only if its audit log array remains completely empty
  is_valid_mask = df['validation_errors'].apply(len) == 0
  
  df_processed = df[is_valid_mask].copy()
  df_rejected = df[~is_valid_mask].copy()
  
  # Flatten the audit array into a comma-separated string for readability inside the CSV
  if not df_rejected.empty:
    df_rejected['validation_errors'] = df_rejected['validation_errors'].apply(lambda errors: " | ".join(errors))

  # Drop the temporary audit column from the production-ready clean dataset
  df_processed = df_processed.drop(columns=['validation_errors'])
  
  # Commit files to their respective pipeline folders
  df_processed.to_csv(PROCESSED_PATH, index=False)
  df_rejected.to_csv(REJECTED_PATH, index=False)
  
  # Calculate performance metrics
  passed_count = len(df_processed)
  failed_count = len(df_rejected)
  pass_rate = (passed_count / total_records) * 100 if total_records > 0 else 0
  
  # -------------------------------------------------------------
  # METRICS DISPLAY LAYOUT
  # -------------------------------------------------------------
  print("\n=======================================================")
  print(" DATA QUALITY FRAMEWORK COMPLIANCE REPORT")
  print("=======================================================")
  print(f"• Raw Records Evaluated:   {total_records:,}")
  print(f"• Clean Records Processed: {passed_count:,} (✓ Saved to {PROCESSED_PATH})")
  print(f"• Corrupt Records Rejected: {failed_count:,} (⚠ Saved to {REJECTED_PATH})")
  print(f"• Data Platform Pass Rate: {pass_rate:.2f}%")
  print("=======================================================")
  
  if failed_count > 0:
    print("\n BREAKDOWN OF DETECTED DATA FAULTS:")
    # Explode the error arrays to easily count individual rules broken
    all_errors = df[~is_valid_mask]['validation_errors'].explode()
    error_counts = all_errors.value_counts()
    for err, count in error_counts.items():
      print(f"  -> {err}: {count:,} instances")
  print("=======================================================\n")

if __name__ == "__main__":
    run_validation_framework()