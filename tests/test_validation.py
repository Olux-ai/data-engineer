import os
import pandas as pd


SOURCE_PATH = "data/raw/payments.csv"
TEST_PATH = "tests/data/invalid_payments.csv"


def create_invalid_test_data():
  print("Creating validation failure test dataset...")

  if not os.path.exists(SOURCE_PATH):
    print(f"ERROR: Source dataset not found at '{SOURCE_PATH}'")
    return

  # Load a copy of the clean dataset
  df = pd.read_csv(SOURCE_PATH)

  if len(df) < 6:
    print("ERROR: Dataset must contain at least 6 records.")
    return

  # 1. Invalid currency
  df.loc[0, "currency"] = "XYZ"

  # 2. Invalid status
  df.loc[1, "status"] = "UNKNOWN"

  # 3. Negative amount
  df.loc[2, "amount_minor"] = -500

  # 4. Duplicate payment_id
  df.loc[3, "payment_id"] = df.loc[4, "payment_id"]

  # 5. Missing payment_id
  df.loc[5, "payment_id"] = None

  # Create test directory
  os.makedirs(os.path.dirname(TEST_PATH), exist_ok=True)

  # Save corrupted test dataset
  df.to_csv(TEST_PATH, index=False)

  print("\nTest dataset created successfully.")
  print(f"Records: {len(df):,}")
  print(f"Saved to: {TEST_PATH}")

  print("\nInjected test failures:")
  print("1. Invalid currency: XYZ")
  print("2. Invalid status: UNKNOWN")
  print("3. Negative amount: -500")
  print("4. Duplicate payment_id")
  print("5. Missing payment_id")


if __name__ == "__main__":
  create_invalid_test_data()