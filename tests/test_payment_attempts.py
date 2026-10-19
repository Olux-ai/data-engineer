import pytest
from datetime import datetime, timezone
from src.data_generator.payment_attempt_generator import generate_payment_attempts


def test_valid_pending_payment():
  """Test that a valid pending payment with UTC timestamp produces exactly one correct attempt."""
  payment = {
    "payment_id": "PAY-2001",
    "processor": "STRIPE",
    "status": "PENDING",
    "created_at": "2026-10-11T12:00:00Z",
    "payment_method": "CARD"
  }

  attempts = generate_payment_attempts(payment, planned_attempts=1)

  assert len(attempts) == 1
  att = attempts[0]
  assert att["payment_attempt_id"] == "PAY-2001-ATT-001"
  assert att["payment_id"] == "PAY-2001"
  assert att["attempt_number"] == 1
  assert att["processor"] == "STRIPE"
  assert att["payment_method"] == "CARD"
  assert att["status"] == "PENDING"
  assert att["error_code"] is None
  assert att["processor_transaction_id"] is None
  assert att["completed_at"] is None

  # Strengthened UTC timestamp validation
  created_at_dt = datetime.fromisoformat(
    att["created_at"].replace("Z", "+00:00")
  )
  assert created_at_dt.tzinfo is not None
  assert created_at_dt.utcoffset() == timezone.utc.utcoffset(created_at_dt)


def test_pending_multiple_attempts_raises_value_error():
  """Test that a pending payment with more than 1 planned attempt raises a ValueError."""
  payment = {
    "payment_id": "PAY-2002",
    "processor": "STRIPE",
    "status": "PENDING",
    "created_at": "2026-10-11T12:00:00Z",
    "payment_method": "CARD"
  }

  with pytest.raises(ValueError, match="PENDING payments require exactly 1 planned attempt"):
    generate_payment_attempts(payment, planned_attempts=2)


def test_naive_timestamp_raises_value_error():
  """Test that a timestamp without timezone info (naive) raises a ValueError."""
  payment = {
    "payment_id": "PAY-2003",
    "processor": "STRIPE",
    "status": "PENDING",
    "created_at": "2026-10-11T12:00:00",  # Naive datetime
    "payment_method": "CARD"
  }

  with pytest.raises(ValueError, match="Must be a timezone-aware UTC timestamp"):
    generate_payment_attempts(payment, planned_attempts=1)


def test_missing_payment_method_raises_key_error():
  """Test that omitting the payment_method key raises a KeyError."""
  payment = {
    "payment_id": "PAY-2004",
    "processor": "STRIPE",
    "status": "PENDING",
    "created_at": "2026-10-11T12:00:00Z"
    # Missing payment_method
  }

  with pytest.raises(KeyError, match="missing required 'payment_method' key"):
    generate_payment_attempts(payment, planned_attempts=1)


def test_unsupported_payment_method_raises_value_error():
  """Test that an unsupported payment method raises a ValueError."""
  payment = {
    "payment_id": "PAY-2005",
    "processor": "STRIPE",
    "status": "PENDING",
    "created_at": "2026-10-11T12:00:00Z",
    "payment_method": "CRYPTO"  # Unsupported
  }

  with pytest.raises(ValueError, match="Invalid payment_method"):
    generate_payment_attempts(payment, planned_attempts=1)


@pytest.mark.parametrize(
  "created_at_val, should_pass",
  [
    ("2026-10-13T10:00:00Z", True),          # Valid UTC (Z suffix)
    ("2026-10-13T10:00:00+00:00", True),     # Valid UTC (+00:00 offset)
    ("2026-10-13T10:00:00+02:00", False),    # Invalid offset (+02:00)
    ("2026-10-13T10:00:00-05:00", False),    # Invalid offset (-05:00)
    ("2026-10-13T10:00:00", False),          # Naive timestamp (no tz)
  ],
)
def test_created_at_utc_validation(created_at_val, should_pass):
  """Test that parent 'created_at' strictly enforces timezone-aware UTC format."""
  payment = {
    "payment_id": "PAY-UTC-01",
    "processor": "STRIPE",
    "status": "PENDING",
    "created_at": created_at_val,
    "payment_method": "CARD"
  }

  if should_pass:
    attempts = generate_payment_attempts(payment, planned_attempts=1)
    assert len(attempts) == 1
  else:
    with pytest.raises(ValueError, match="Must be a timezone-aware UTC timestamp"):
      generate_payment_attempts(payment, planned_attempts=1)