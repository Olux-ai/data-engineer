import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

from src.data_generator.attempt_id import create_attempt_id
from src.data_generator.errors import select_error_code, is_retryable_error
from src.data_generator.processors import select_processor

VALID_TARGET_STATUSES = {"SUCCESS", "FAILED", "PENDING"}
PROCESSOR_FALLBACK_ORDER = ["STRIPE", "ADYEN", "FLUTTERWAVE"]
VALID_PAYMENT_METHODS = {"CARD", "BANK_TRANSFER", "WALLET"}

def generate_payment_attempts(payment: Dict[str, Any], planned_attempts: int) -> List[Dict[str, Any]]:
  """
  Orchestrates the generation of payment attempt records with strict upfront validation
  and lifecycle branches for PENDING, SUCCESS, and FAILED.
  """
  # 1. Validate that payment is a dictionary
  if not isinstance(payment, dict):
    raise TypeError(f"Invalid input: 'payment' must be a dictionary. Got {type(payment).__name__}.")

  # 2. Validate payment_id exists
  if "payment_id" not in payment or not str(payment["payment_id"]).strip():
    raise KeyError("Invalid input: parent payment dictionary is missing required 'payment_id'.")
  payment_id = str(payment["payment_id"]).strip()

  # 3. Validate parent payment processor
  if "processor" not in payment:
    raise KeyError("Invalid input: parent payment dictionary is missing required 'processor' key.")

  raw_processor = payment["processor"]
  if not isinstance(raw_processor, str):
    raise TypeError(f"Invalid input: processor must be a string. Got {type(raw_processor).__name__}.")

  initial_processor = raw_processor.strip().upper()
  if initial_processor not in PROCESSOR_FALLBACK_ORDER:
    raise ValueError(f"Invalid processor '{raw_processor}'. Must be one of {PROCESSOR_FALLBACK_ORDER}.")

  # 4. Validate planned_attempts (must be a strict integer, not a bool, between 1 and 3)
  if isinstance(planned_attempts, bool) or not isinstance(planned_attempts, int):
    raise ValueError(f"Invalid input: 'planned_attempts' must be an integer. Got {type(planned_attempts).__name__}.")

  if not (1 <= planned_attempts <= 3):
    raise ValueError(f"Invalid input: 'planned_attempts' must be between 1 and 3. Got {planned_attempts}.")

  # 5. Validate parent payment status
  if "status" not in payment:
    raise KeyError("Invalid input: parent payment dictionary is missing required 'status' key.")

  raw_status = payment["status"]
  if not isinstance(raw_status, str):
    raise TypeError(f"Invalid input: payment status must be a string. Got {type(raw_status).__name__}.")

  target_status = raw_status.strip().upper()
  if target_status not in VALID_TARGET_STATUSES:
    raise ValueError(f"Invalid status '{raw_status}'. Must be one of {VALID_TARGET_STATUSES}.")

  # 6. Enforce business rule: PENDING payments must have exactly one planned attempt
  if target_status == "PENDING" and planned_attempts != 1:
    raise ValueError(f"Business rule violation: PENDING payments require exactly 1 planned attempt. Got {planned_attempts}.")

  # 7. Validate and parse parent created_at timestamp (must be timezone-aware UTC)
  if "created_at" not in payment:
    raise KeyError("Invalid input: parent payment dictionary is missing required 'created_at' key.")

  try:
    parent_created_at = datetime.fromisoformat(str(payment["created_at"]).replace("Z", "+00:00"))
  except (ValueError, TypeError) as e:
    raise ValueError(f"Invalid 'created_at' format: {payment['created_at']}. Must be ISO-8601 UTC string.") from e

  if (
    parent_created_at.tzinfo is None
    or parent_created_at.utcoffset() != timedelta(0)
  ):
    raise ValueError(
      f"Invalid 'created_at': {payment['created_at']}. "
      "Must be a timezone-aware UTC timestamp."
    )
  # 8. Validate payment method explicitly
  if "payment_method" not in payment:
    raise KeyError("Invalid input: parent payment dictionary is missing required 'payment_method' key.")

  raw_payment_method = payment["payment_method"]
  if not isinstance(raw_payment_method, str):
    raise TypeError(f"Invalid input: payment_method must be a string. Got {type(raw_payment_method).__name__}.")

  payment_method = raw_payment_method.strip().upper()
  if payment_method not in VALID_PAYMENT_METHODS:
    raise ValueError(f"Invalid payment_method '{raw_payment_method}'. Must be one of {VALID_PAYMENT_METHODS}.")

  # Initialize lifecycle state variables
  attempt_records = []
  attempt_number = 1
  current_processor = initial_processor
  consecutive_retryable_failures = 0

  # Attempt 1 begins 0 to 2 seconds after parent payment creation
  current_time = parent_created_at + timedelta(seconds=random.uniform(0, 2))

  # Run the loop up to the planned attempt limit
  while attempt_number <= planned_attempts:
    if target_status == "PENDING":
      payment_attempt_id = create_attempt_id(payment_id, attempt_number)
      created_at_str = current_time.isoformat().replace("+00:00", "Z")

      attempt_record = {
        "payment_attempt_id": payment_attempt_id,
        "payment_id": payment_id,
        "attempt_number": attempt_number,
        "processor": current_processor,
        "payment_method": payment_method,
        "status": "PENDING",
        "error_code": None,
        "processor_transaction_id": None,
        "created_at": created_at_str,
        "completed_at": None
      }
      attempt_records.append(attempt_record)
      break

    elif target_status == "SUCCESS":
      payment_attempt_id = create_attempt_id(payment_id, attempt_number)
      created_at_str = current_time.isoformat().replace("+00:00", "Z")

      if attempt_number < planned_attempts:
        attempt_status = "FAILED"
        error_code = select_error_code(retryable_only=True)
        processor_transaction_id = None
        completed_at_dt = current_time + timedelta(seconds=random.uniform(2, 15))
        completed_at_str = completed_at_dt.isoformat().replace("+00:00", "Z")
      else:
        attempt_status = "SUCCESS"
        error_code = None
        processor_transaction_id = f"TXN-{random.randint(100000, 999999)}"
        completed_at_dt = current_time + timedelta(seconds=random.uniform(2, 10))
        completed_at_str = completed_at_dt.isoformat().replace("+00:00", "Z")

      attempt_record = {
        "payment_attempt_id": payment_attempt_id,
        "payment_id": payment_id,
        "attempt_number": attempt_number,
        "processor": current_processor,
        "payment_method": payment_method,
        "status": attempt_status,
        "error_code": error_code,
        "processor_transaction_id": processor_transaction_id,
        "created_at": created_at_str,
        "completed_at": completed_at_str
      }
      attempt_records.append(attempt_record)

      if attempt_status == "FAILED":
        consecutive_retryable_failures += 1
        current_processor = select_processor(current_processor, consecutive_retryable_failures)
        current_time = completed_at_dt + timedelta(seconds=random.uniform(1, 3))
        attempt_number += 1
      else:
        break

    elif target_status == "FAILED":
      payment_attempt_id = create_attempt_id(payment_id, attempt_number)
      created_at_str = current_time.isoformat().replace("+00:00", "Z")

      error_code = select_error_code()
      is_retryable = is_retryable_error(error_code)

      completed_at_dt = current_time + timedelta(seconds=random.uniform(2, 15))
      completed_at_str = completed_at_dt.isoformat().replace("+00:00", "Z")

      attempt_record = {
        "payment_attempt_id": payment_attempt_id,
        "payment_id": payment_id,
        "attempt_number": attempt_number,
        "processor": current_processor,
        "payment_method": payment_method,
        "status": "FAILED",
        "error_code": error_code,
        "processor_transaction_id": None,
        "created_at": created_at_str,
        "completed_at": completed_at_str
      }
      attempt_records.append(attempt_record)

      # If the error is non-retryable, terminate immediately
      if not is_retryable:
        break

      # If retryable, stop if we reached planned_attempts limit
      if attempt_number >= planned_attempts:
        break

      # Otherwise, increment consecutive retryable failures, shift processor, and continue
      consecutive_retryable_failures += 1
      current_processor = select_processor(current_processor, consecutive_retryable_failures)
      current_time = completed_at_dt + timedelta(seconds=random.uniform(1, 3))
      attempt_number += 1

  return attempt_records