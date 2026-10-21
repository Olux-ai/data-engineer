from unittest.mock import patch
import pytest
from src.data_generator.errors import RETRYABLE_ERROR_CODES
from src.data_generator.payment_attempt_generator import generate_payment_attempts


def make_failed_payment(payment_id):
  return {
      "payment_id": payment_id,
      "processor": "STRIPE",
      "status": "FAILED",
      "created_at": "2026-10-13T10:00:00Z",
      "payment_method": "CARD",
  }


@patch("src.data_generator.payment_attempt_generator.select_error_code")
def test_intermediate_failed_attempts_require_retryable_errors(mock_select_error):
  """Intermediate attempts must select retryable errors."""
  mock_select_error.side_effect = [
      "NETWORK_ERROR",
      "PROCESSOR_TIMEOUT",
      "CARD_DECLINED",
  ]

  attempts = generate_payment_attempts(
      make_failed_payment("PAY-FAIL-01"), planned_attempts=3
  )

  assert len(attempts) == 3

  for index, attempt in enumerate(attempts[:-1], start=1):
    assert attempt["attempt_number"] == index
    assert attempt["status"] == "FAILED"
    assert attempt["error_code"] in RETRYABLE_ERROR_CODES

  assert attempts[-1]["attempt_number"] == 3
  assert attempts[-1]["status"] == "FAILED"
  assert attempts[-1]["error_code"] == "CARD_DECLINED"
  assert mock_select_error.call_count == 3
  assert mock_select_error.call_args_list[0].kwargs == {"retryable_only": True}
  assert mock_select_error.call_args_list[1].kwargs == {"retryable_only": True}
  assert mock_select_error.call_args_list[2].kwargs == {"retryable_only": False}


@patch("src.data_generator.payment_attempt_generator.select_error_code")
def test_final_non_retryable_failure_stops_after_planned_attempts(
    mock_select_error,
):
  """The final attempt may use a non-retryable error."""
  mock_select_error.side_effect = [
      "NETWORK_ERROR",
      "PROCESSOR_TIMEOUT",
      "INSUFFICIENT_FUNDS",
  ]

  attempts = generate_payment_attempts(
      make_failed_payment("PAY-FAIL-02"), planned_attempts=3
  )

  assert len(attempts) == 3
  assert [attempt["attempt_number"] for attempt in attempts] == [1, 2, 3]
  assert attempts[-1]["error_code"] == "INSUFFICIENT_FUNDS"
  assert mock_select_error.call_count == 3


@patch("src.data_generator.payment_attempt_generator.select_error_code")
def test_single_failed_attempt_can_use_non_retryable_error(mock_select_error):
  """A single planned attempt is also the final attempt."""
  mock_select_error.return_value = "INSUFFICIENT_FUNDS"

  attempts = generate_payment_attempts(
      make_failed_payment("PAY-FAIL-03"), planned_attempts=1
  )

  assert len(attempts) == 1
  assert attempts[0]["attempt_number"] == 1
  assert attempts[0]["error_code"] == "INSUFFICIENT_FUNDS"
  assert mock_select_error.call_count == 1
  assert mock_select_error.call_args.kwargs == {"retryable_only": False}


@patch("src.data_generator.payment_attempt_generator.select_error_code")
def test_retryable_failures_exhaust_attempt_limit_and_trigger_failover(
    mock_select_error,
):
  """Retryable failures continue through the planned attempts."""
  mock_select_error.side_effect = [
      "PROCESSOR_TIMEOUT",
      "PROCESSOR_UNAVAILABLE",
      "NETWORK_ERROR",
  ]

  attempts = generate_payment_attempts(
      make_failed_payment("PAY-FAIL-04"), planned_attempts=3
  )

  assert len(attempts) == 3

  for index, attempt in enumerate(attempts, start=1):
    assert attempt["attempt_number"] == index
    assert attempt["status"] == "FAILED"
    assert attempt["error_code"] in RETRYABLE_ERROR_CODES

  assert attempts[0]["processor"] == "STRIPE"
  assert attempts[1]["processor"] == "STRIPE"
  assert attempts[2]["processor"] == "ADYEN"
  assert mock_select_error.call_count == 3
