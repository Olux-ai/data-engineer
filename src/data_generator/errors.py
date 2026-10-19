import random

# Core error code classification sets
RETRYABLE_ERROR_CODES = [
  "PROCESSOR_TIMEOUT",
  "PROCESSOR_UNAVAILABLE",
  "NETWORK_ERROR"
]

NON_RETRYABLE_ERROR_CODES = [
  "INSUFFICIENT_FUNDS",
  "CARD_DECLINED",
  "INVALID_ACCOUNT"
]

ALL_ERROR_CODES = RETRYABLE_ERROR_CODES + NON_RETRYABLE_ERROR_CODES


def is_retryable_error(error_code: str) -> bool:
  """Determines whether a gateway/network error code is retryable."""
  if not error_code or not isinstance(error_code, str):
    return False

  normalized_code = error_code.strip().upper()
  return normalized_code in RETRYABLE_ERROR_CODES


def select_error_code(retryable_only: bool = False) -> str:
  """Selects a random error code based on retryability requirements."""
  if not isinstance(retryable_only, bool):
    raise ValueError(f"Invalid input: 'retryable_only' must be a boolean. Got {type(retryable_only).__name__}.")

  if retryable_only:
    return random.choice(RETRYABLE_ERROR_CODES)

  return random.choice(ALL_ERROR_CODES)