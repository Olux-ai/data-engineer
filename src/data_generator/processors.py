PROCESSOR_FALLBACK_ORDER = [
  "STRIPE",
  "ADYEN",
  "FLUTTERWAVE"
]

def select_processor(current_processor: str, consecutive_retryable_failures: int) -> str:
  """
  Selects the gateway processor for a payment attempt based on consecutive retry failure count.

  Rules:
    1. consecutive_retryable_failures must be an integer strictly equal to 0, 1, or 2 (booleans rejected).
    2. 0 or 1 consecutive failure: retain current processor.
    3. 2 consecutive failures: switch to next processor in cyclic order.
    4. Unknown processor or invalid failure counts raise ValueError.
  """
  # Reject unknown processor
  if not isinstance(current_processor, str):
    raise TypeError(f"Invalid processor type: expected str, got {type(current_processor).__name__}.")

  normalized_processor = current_processor.strip().upper()
  if normalized_processor not in PROCESSOR_FALLBACK_ORDER:
    raise ValueError(
      f"Unknown processor '{current_processor}'. "
      f"Must be one of {PROCESSOR_FALLBACK_ORDER}."
    )

  # Strict validation: reject booleans and ensure failure count is an int between 0 and 2
  if (
    isinstance(consecutive_retryable_failures, bool)
    or not isinstance(consecutive_retryable_failures, int)
    or consecutive_retryable_failures not in {0, 1, 2}
  ):
    raise ValueError(
      f"Invalid failure count: {consecutive_retryable_failures}. "
      f"Count must be an integer between 0 and 2."
    )

  # 0 or 1 failure: retain current processor
  if consecutive_retryable_failures in {0, 1}:
    return normalized_processor

  # 2 failures: switch to next processor in cyclic order
  current_index = PROCESSOR_FALLBACK_ORDER.index(normalized_processor)
  next_index = (current_index + 1) % len(PROCESSOR_FALLBACK_ORDER)

  return PROCESSOR_FALLBACK_ORDER[next_index]