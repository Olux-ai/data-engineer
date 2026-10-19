import pytest
from datetime import datetime, timezone
from src.data_generator.payment_attempt_generator import generate_payment_attempts
from src.data_generator.errors import RETRYABLE_ERROR_CODES


def test_single_attempt_success():
  """Test that a single-attempt successful payment produces 1 SUCCESS attempt with no error code."""
  payment = {
      "payment_id": "PAY-3001",
      "processor": "STRIPE",
      "status": "SUCCESS",
      "created_at": "2026-10-12T10:00:00Z",
      "payment_method": "CARD"
  }

  attempts = generate_payment_attempts(payment, planned_attempts=1)

  assert len(attempts) == 1
  att = attempts[0]
  assert att["attempt_number"] == 1
  assert att["status"] == "SUCCESS"
  assert att["error_code"] is None
  assert att["processor_transaction_id"] is not None
  assert att["completed_at"] is not None
  assert att["processor"] == "STRIPE"


def test_two_attempt_success():
  """Test that a two-attempt successful payment fails attempt 1 with a retryable error and succeeds on attempt 2."""
  payment = {
      "payment_id": "PAY-3002",
      "processor": "STRIPE",
      "status": "SUCCESS",
      "created_at": "2026-10-12T10:00:00Z",
      "payment_method": "BANK_TRANSFER"
  }

  attempts = generate_payment_attempts(payment, planned_attempts=2)

  assert len(attempts) == 2

  # Attempt 1: Fails with retryable error from approved set
  assert attempts[0]["attempt_number"] == 1
  assert attempts[0]["status"] == "FAILED"
  assert attempts[0]["error_code"] in RETRYABLE_ERROR_CODES
  assert attempts[0]["processor_transaction_id"] is None
  assert attempts[0]["processor"] == "STRIPE"

  # Attempt 2: Succeeds
  assert attempts[1]["attempt_number"] == 2
  assert attempts[1]["status"] == "SUCCESS"
  assert attempts[1]["error_code"] is None
  assert attempts[1]["processor_transaction_id"] is not None
  assert attempts[1]["processor"] == "STRIPE"


def test_three_attempt_success_with_failover():
  """Test that three planned attempts fail twice with retryable errors on STRIPE, triggering failover to ADYEN on attempt 3 which succeeds."""
  payment = {
      "payment_id": "PAY-3003",
      "processor": "STRIPE",
      "status": "SUCCESS",
      "created_at": "2026-10-12T10:00:00Z",
      "payment_method": "WALLET"
  }

  attempts = generate_payment_attempts(payment, planned_attempts=3)

  assert len(attempts) == 3

  # Attempt 1: Fails on STRIPE with retryable error
  assert attempts[0]["attempt_number"] == 1
  assert attempts[0]["status"] == "FAILED"
  assert attempts[0]["error_code"] in RETRYABLE_ERROR_CODES
  assert attempts[0]["processor"] == "STRIPE"

  # Attempt 2: Fails on STRIPE with retryable error (triggering cyclic shift)
  assert attempts[1]["attempt_number"] == 2
  assert attempts[1]["status"] == "FAILED"
  assert attempts[1]["error_code"] in RETRYABLE_ERROR_CODES
  assert attempts[1]["processor"] == "STRIPE"

  # Attempt 3: Succeeds on ADYEN
  assert attempts[2]["attempt_number"] == 3
  assert attempts[2]["status"] == "SUCCESS"
  assert attempts[2]["error_code"] is None
  assert attempts[2]["processor_transaction_id"] is not None
  assert attempts[2]["processor"] == "ADYEN"