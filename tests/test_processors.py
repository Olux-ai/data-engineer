import pytest
from src.data_generator.processors import select_processor


def test_zero_failures_retain_processor():
  """Test that 0 failures retain the current processor."""
  assert select_processor("STRIPE", 0) == "STRIPE"
  assert select_processor("ADYEN", 0) == "ADYEN"


def test_one_failure_retain_processor():
  """Test that 1 failure retains the current processor."""
  assert select_processor("STRIPE", 1) == "STRIPE"
  assert select_processor("FLUTTERWAVE", 1) == "FLUTTERWAVE"


def test_two_failures_cyclic_switching():
  """Test that 2 consecutive failures cycle processors correctly."""
  assert select_processor("STRIPE", 2) == "ADYEN"
  assert select_processor("ADYEN", 2) == "FLUTTERWAVE"
  assert select_processor("FLUTTERWAVE", 2) == "STRIPE"


def test_unknown_processor_raises_value_error():
  """Test that an unknown processor raises a ValueError."""
  with pytest.raises(ValueError, match="Unknown processor"):
    select_processor("UNKNOWN_GATEWAY", 0)


def test_negative_failure_count_raises_value_error():
  """Test that a negative failure count raises a ValueError."""
  with pytest.raises(ValueError, match="Invalid failure count"):
    select_processor("STRIPE", -1)


def test_failure_count_above_two_raises_value_error():
  """Test that a failure count of 3 or higher raises a ValueError."""
  with pytest.raises(ValueError, match="Invalid failure count"):
    select_processor("STRIPE", 3)


@pytest.mark.parametrize("invalid_bool", [True, False])
def test_boolean_failure_count_raises_value_error(invalid_bool):
  """Test that boolean failure counts (True/False) are explicitly rejected with ValueError."""
  with pytest.raises(ValueError, match="Invalid failure count"):
    select_processor("STRIPE", invalid_bool)