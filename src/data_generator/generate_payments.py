import os
import uuid
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_payment_data(num_records=10000):
    print(f"🚀 Initializing deterministic generation of {num_records:,} payment records...")
    
    # Set static seeds for strict reproducibility
    SEED = 42
    random.seed(SEED)
    np.random.seed(SEED)
    
    # Your Custom Distributions
    statuses = ['SUCCESS', 'FAILED', 'PENDING']
    status_weights = [0.70, 0.15, 0.15]

    currencies = ['USD', 'EUR', 'GBP', 'NGN']
    currency_weights = [0.60, 0.15, 0.15, 0.10]
    
    # 👥 Generate structured pools of recurring identities
    customer_pool = [f"CUST-{i:05d}" for i in range(1, 1501)]
    merchant_pool = [f"MERCH-{i:03d}" for i in range(1, 51)]
    
    # Base timestamp set to exactly 30 days ago
    start_date = datetime.now() - timedelta(days=30)
    
    data_list = []
    
    # Core Generator Loop
    for i in range(num_records):
        payment_id = f"PAY-{str(uuid.uuid4())[:13].upper()}"
        customer_id = random.choice(customer_pool)
        merchant_id = random.choice(merchant_pool)
        
        # Stagger timestamps across the historical window sequentially
        random_seconds = random.randint(0, 30 * 24 * 60 * 60)
        created_at = start_date + timedelta(seconds=random_seconds)
        
        # Pull values based on your explicit mathematical weights
        currency = np.random.choice(currencies, p=currency_weights)
        status = np.random.choice(statuses, p=status_weights)
        
        # Use minor currency units to avoid floating-point precision issues.
        amount_minor = random.randint(500, 150000)
        
        # Construct row dictionary
        data_list.append({
            "payment_id": payment_id,
            "customer_id": customer_id,
            "merchant_id": merchant_id,
            "amount_minor": amount_minor,
            "currency": currency,
            "status": status,
            "created_at": created_at
        })
        
    #Assemble the Pandas Matrix DataFrame
    df = pd.DataFrame(data_list)
    
    # Target directory routing 
    output_path = "data/source/payments.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save file
    df.to_csv(output_path, index=False)
    print(f"✅ Production dataset saved successfully to: '{output_path}'")
    
    # Show structural diagnostics to confirm code execution matches your setup
    print("\n--- TRANSACTION STATUS DISTRIBUTION MATCH ---")
    print(df['status'].value_counts(normalize=True).round(2) * 100)
    
    print("\n--- CURRENCY DISTRIBUTION MATCH ---")
    print(df['currency'].value_counts(normalize=True).round(2) * 100)

if __name__ == "__main__":
    generate_payment_data()
