import pytest
from src.data_generator.errors import (
  is_retryable_error,
  select_error_code,
  RETRYABLE_ERROR_CODES,
  ALL_ERROR_CODES
)


@pytest.mark.parametrize(
  "error_code, expected",
  [
    ("PROCESSOR_TIMEOUT", True),
    ("PROCESSOR_UNAVAILABLE", True),
    ("NETWORK_ERROR", True),
    ("INSUFFICIENT_FUNDS", False),
    ("CARD_DECLINED", False),
    ("INVALID_ACCOUNT", False),
    ("processor_timeout", True),  # Lowercase handling
    ("  NETWORK_ERROR  ", True),    # Surrounding whitespace handling
    ("insufficient_funds", False), # Lowercase non-retryable handling
    ("", False),                   # Empty string
    (None, False),        # None value
  ],
)
def test_is_retryable_error(error_code, expected):
  """Test error classification for various retryable and non-retryable error strings."""
  assert is_retryable_error(error_code) == expected


def test_select_error_code_retryable_only():
  """Test that select_error_code(retryable_only=True) always returns a retryable error."""
  for _ in range(50):
    code = select_error_code(retryable_only=True)
    assert code in RETRYABLE_ERROR_CODES


def test_select_error_code_any():
  """Test that select_error_code(retryable_only=False) always returns a valid recognized error."""
  for _ in range(50):
    code = select_error_code(retryable_only=False)
    assert code in ALL_ERROR_CODES


@pytest.mark.parametrize("invalid_arg", ["yes", 1, 0, 1.5, None, "True"])
def test_select_error_code_invalid_retryable_only(invalid_arg):
  """Test that passing non-boolean values to retryable_only raises a ValueError."""
  with pytest.raises(ValueError, match="must be a boolean"):
    select_error_code(retryable_only=invalid_arg)