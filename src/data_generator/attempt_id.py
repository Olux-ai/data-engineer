def create_attempt_id(payment_id: str, attempt_number: int) -> str:
  """Generate a unique, readable ID for a payment attempt."""

  if not isinstance(payment_id, str) or not payment_id.strip():
    raise ValueError("payment_id must be a non-empty string.")

  if isinstance(attempt_number, bool) or not isinstance(attempt_number, int):
    raise ValueError("attempt_number must be an integer.")

  if not 1 <= attempt_number <= 3:
    raise ValueError("attempt_number must be between 1 and 3.")

  clean_payment_id = payment_id.strip()

  return f"{clean_payment_id}-ATT-{attempt_number:03d}"