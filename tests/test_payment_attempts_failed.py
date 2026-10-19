import pytest
from unittest.mock import patch
from src.data_generator.payment_attempt_generator import generate_payment_attempts
from src.data_generator.errors import RETRYABLE_ERROR_CODES


@patch("src.data_generator.payment_attempt_generator.select_error_code")
def test_non_retryable_failure_stops_immediately(mock_select_error):
  """Test that a non-retryable error on attempt 1 stops generation immediately (1 attempt)."""
  mock_select_error.return_value = "INSUFFICIENT_FUNDS"

  payment = {
    "payment_id": "PAY-FAIL-01",
    "processor": "STRIPE",
    "status": "FAILED",
    "created_at": "2026-10-13T10:00:00Z",
    "payment_method": "CARD"
  }

  attempts = generate_payment_attempts(payment, planned_attempts=3)

  assert len(attempts) == 1
  assert attempts[0]["payment_attempt_id"] == "PAY-FAIL-01-ATT-001"
  assert attempts[0]["attempt_number"] == 1
  assert attempts[0]["status"] == "FAILED"
  assert attempts[0]["error_code"] == "INSUFFICIENT_FUNDS"
  assert attempts[0]["processor_transaction_id"] is None
  assert attempts[0]["completed_at"] is not None
  assert attempts[0]["processor"] == "STRIPE"
  assert mock_select_error.call_count == 1


@patch("src.data_generator.payment_attempt_generator.select_error_code")
def test_retryable_then_non_retryable_failure_stops(mock_select_error):
  """Test that a retryable error on attempt 1 followed by a non-retryable error on attempt 2 stops at 2 attempts."""
  mock_select_error.side_effect = ["NETWORK_ERROR", "CARD_DECLINED"]

  payment = {
    "payment_id": "PAY-FAIL-02",
    "processor": "STRIPE",
    "status": "FAILED",
    "created_at": "2026-10-13T10:00:00Z",
    "payment_method": "CARD"
  }

  attempts = generate_payment_attempts(payment, planned_attempts=3)

  assert len(attempts) == 2

  assert attempts[0]["attempt_number"] == 1
  assert attempts[0]["status"] == "FAILED"
  assert attempts[0]["error_code"] == "NETWORK_ERROR"
  assert attempts[0]["processor"] == "STRIPE"

  assert attempts[1]["attempt_number"] == 2
  assert attempts[1]["status"] == "FAILED"
  assert attempts[1]["error_code"] == "CARD_DECLINED"
  assert attempts[1]["processor"] == "STRIPE"

  assert mock_select_error.call_count == 2


@patch("src.data_generator.payment_attempt_generator.select_error_code")
def test_retryable_failures_stop_at_attempt_limit(mock_select_error):
  """Test that consecutive retryable errors up to planned_attempts=3 exhaust all attempts and trigger failover."""
  mock_select_error.side_effect = ["PROCESSOR_TIMEOUT", "PROCESSOR_UNAVAILABLE", "NETWORK_ERROR"]

  payment = {
    "payment_id": "PAY-FAIL-03",
    "processor": "STRIPE",
    "status": "FAILED",
    "created_at": "2026-10-13T10:00:00Z",
    "payment_method": "CARD"
  }

  attempts = generate_payment_attempts(payment, planned_attempts=3)

  assert len(attempts) == 3

  for i, att in enumerate(attempts, start=1):
    assert att["attempt_number"] == i
    assert att["status"] == "FAILED"
    assert att["error_code"] in RETRYABLE_ERROR_CODES

  # Verify processor failover after 2 consecutive retryable failures (Attempt 3 shifts to ADYEN)
  assert attempts[0]["processor"] == "STRIPE"
  assert attempts[1]["processor"] == "STRIPE"
  assert attempts[2]["processor"] == "ADYEN"
  assert mock_select_error.call_count == 3