import pytest
from src.data_generator.payment_attempt_generator import generate_payment_attempts


def test_consistent_parent_payment_and_method():
  """Test 1: Every generated attempt record must reference the same parent payment_id and retain the constant payment_method."""
  parent_id = "PAY-SEQ-01"
  payment_method = "CARD"

  payment = {
    "payment_id": parent_id,
    "processor": "STRIPE",
    "status": "SUCCESS",
    "created_at": "2026-10-13T10:00:00Z",
    "payment_method": payment_method
  }

  attempts = generate_payment_attempts(payment, planned_attempts=3)

  # Ensure we actually generated a full 3-attempt sequence
  assert len(attempts) == 3

  # Verify relational consistency across every record in the sequence
  for att in attempts:
    assert att["payment_id"] == parent_id
    assert att["payment_method"] == payment_method


def test_success_status_only_on_final_attempt():
  """Test 2: For a successful payment with 3 planned attempts, only the final record has SUCCESS status; earlier attempts are FAILED."""
  payment = {
    "payment_id": "PAY-SEQ-02",
    "processor": "STRIPE",
    "status": "SUCCESS",
    "created_at": "2026-10-13T10:00:00Z",
    "payment_method": "BANK_TRANSFER"
  }

  attempts = generate_payment_attempts(payment, planned_attempts=3)
  assert len(attempts) == 3

  # Check that all intermediate (earlier) attempts are FAILED
  for att in attempts[:-1]:
    assert att["status"] == "FAILED"

  # Check that the final attempt is strictly SUCCESS
  final_attempt = attempts[-1]
  assert final_attempt["status"] == "SUCCESS"
  assert final_attempt["attempt_number"] == len(attempts)