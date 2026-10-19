import pytest
from unittest.mock import patch
from src.data_generator.payment_attempt_generator import generate_payment_attempts


def test_parent_payment_id_consistency():
  """Test 1: Verify that every generated attempt record's payment_id matches the parent payment's ID."""
  parent_id = "PAY-CONSISTENCY-01"
  payment = {
    "payment_id": parent_id,
    "processor": "STRIPE",
    "status": "SUCCESS",
    "created_at": "2026-10-13T10:00:00Z",
    "payment_method": "CARD"
  }

  attempts = generate_payment_attempts(payment, planned_attempts=3)
  assert len(attempts) == 3

  for att in attempts:
    assert att["payment_id"] == parent_id


@patch("src.data_generator.payment_attempt_generator.select_error_code")
def test_payment_method_and_processor_failover_consistency(mock_select_error):
  """
  Test 2: Verify payment method remains constant while processor failover
  correctly switches from STRIPE to ADYEN after two consecutive retryable failures.
  """
  # Force two retryable errors so attempts 1 and 2 fail, triggering failover on attempt 3
  mock_select_error.side_effect = ["PROCESSOR_TIMEOUT", "NETWORK_ERROR"]

  payment_method = "BANK_TRANSFER"
  payment = {
    "payment_id": "PAY-CONSISTENCY-02",
    "processor": "STRIPE",
    "status": "SUCCESS",
    "created_at": "2026-10-13T10:00:00Z",
    "payment_method": payment_method
  }

  attempts = generate_payment_attempts(payment, planned_attempts=3)
  assert len(attempts) == 3

  # Rule A: Payment method must remain unchanged across all attempts
  for att in attempts:
    assert att["payment_method"] == payment_method

  # Rule B & C: Processor failover validation (STRIPE -> STRIPE -> ADYEN)
  assert attempts[0]["processor"] == "STRIPE"
  assert attempts[1]["processor"] == "STRIPE"
  assert attempts[2]["processor"] == "ADYEN"

  # Explicitly verify the first two attempts failed
  assert attempts[0]["status"] == "FAILED"
  assert attempts[1]["status"] == "FAILED"

  # Verify final attempt successfully completed
  assert attempts[2]["status"] == "SUCCESS"
  assert attempts[2]["error_code"] is None
  assert attempts[2]["processor_transaction_id"] is not None