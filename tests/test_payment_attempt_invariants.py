import pytest
from unittest.mock import patch
from src.data_generator.payment_attempt_generator import generate_payment_attempts


def test_attempt_numbering_consecutive():
  """Rule 1: Attempts for the same payment must be numbered consecutively, starting at 1."""
  payment = {
    "payment_id": "PAY-INV-01",
    "processor": "STRIPE",
    "status": "SUCCESS",
    "created_at": "2026-10-13T10:00:00Z",
    "payment_method": "CARD"
  }

  # Generate a multi-attempt sequence
  attempts = generate_payment_attempts(payment, planned_attempts=3)

  # Explicitly assert that a three-attempt sequence was actually generated
  assert len(attempts) == 3

  # Extract attempt numbers and verify sequential order starting at 1
  attempt_numbers = [att["attempt_number"] for att in attempts]
  expected_sequence = list(range(1, len(attempts) + 1))

  assert attempt_numbers == expected_sequence
  assert attempt_numbers[0] == 1


def test_successful_attempt_invariants():
  """Rule 2: A successful attempt must have error_code=None and a non-empty processor_transaction_id."""
  payment = {
    "payment_id": "PAY-INV-02",
    "processor": "STRIPE",
    "status": "SUCCESS",
    "created_at": "2026-10-13T10:00:00Z",
    "payment_method": "BANK_TRANSFER"
  }

  attempts = generate_payment_attempts(payment, planned_attempts=1)
  assert len(attempts) == 1

  success_attempt = attempts[0]
  assert success_attempt["status"] == "SUCCESS"
  assert success_attempt["error_code"] is None

  # Verify processor transaction ID is present, a string, and non-empty
  tx_id = success_attempt["processor_transaction_id"]
  assert tx_id is not None
  assert isinstance(tx_id, str)
  assert len(tx_id.strip()) > 0


@patch("src.data_generator.payment_attempt_generator.select_error_code")
def test_failed_attempt_invariants(mock_select_error):
  """Rule 3: A failed attempt must have a non-empty error_code and processor_transaction_id=None."""
  mock_select_error.return_value = "INSUFFICIENT_FUNDS"

  payment = {
    "payment_id": "PAY-INV-03",
    "processor": "STRIPE",
    "status": "FAILED",
    "created_at": "2026-10-13T10:00:00Z",
    "payment_method": "WALLET"
  }

  attempts = generate_payment_attempts(payment, planned_attempts=1)
  assert len(attempts) == 1

  failed_attempt = attempts[0]
  assert failed_attempt["status"] == "FAILED"
  assert failed_attempt["processor_transaction_id"] is None

  # Verify error code is present, a string, and non-empty
  err_code = failed_attempt["error_code"]
  assert err_code is not None
  assert isinstance(err_code, str)
  assert len(err_code.strip()) > 0

  # Confirm the error selector was invoked exactly once for the single attempt
  assert mock_select_error.call_count == 1