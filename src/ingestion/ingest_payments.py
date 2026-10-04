import os
import pandas as pd

def run_ingestion_pipeline():
  print("📥 Starting Payment Data Ingestion Pipeline...")
  
  # Define exact path structures
  SOURCE_PATH = "data/source/payments.csv"
  RAW_PATH = "data/raw/payments.csv"
  
  # 1. Check if the source file exists
  if not os.path.isfile(SOURCE_PATH):
    print(f"❌ CRITICAL ERROR: Source file not found at '{SOURCE_PATH}'.")
    print("Please run your 'generate_payments.py' script first to build the source file.")
    return

  try:
    # 2. Read source CSV file exactly as it is
    print(f"📖 Reading data from source landing area: '{SOURCE_PATH}'...")
    df_raw = pd.read_csv(SOURCE_PATH)
    
    # 3. Count records
    record_count = len(df_raw)
    
    # 4. Write exactly to data/raw/payments.csv (Preserving raw state)
    print(f"💾 Writing raw dataset to storage path: '{RAW_PATH}'...")
    
    # Ensure the destination directory path exists
    os.makedirs(os.path.dirname(RAW_PATH), exist_ok=True)
    
    # Save file without touching row indexing structure
    df_raw.to_csv(RAW_PATH, index=False)
    print("✅ File written successfully.")
    
    # 5. Print ingestion summary matrix
    print("\n=============================================")
    print("PAYMENT INGESTION")
    print("=============================================")
    print(f"• Ingestion Status:   SUCCESS")
    print(f"• Source Path:        {SOURCE_PATH}")
    print(f"• Destination Path:   {RAW_PATH}")
    print(f"• Ingestion time:       {pd.Timestamp.now()} ...")
    print(f"• Total Rows Loaded:  {record_count:,} records")
    print("=============================================")
      
  except Exception as e:
    print(f"❌ CRITICAL ERROR: Ingestion failed due to a pipeline exception.")
    print(f"Details: {str(e)}")

if __name__ == "__main__":
  run_ingestion_pipeline()
