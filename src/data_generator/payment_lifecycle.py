import random
from unittest.mock import patch
import pytest

def determine_payment_lifecycle(target_status: str, attempt_count: int = None) -> dict:
  """
  Determines the total attempt count and retry behavior for a payment based on target status.

  Rules:
    - SUCCESS: Requires 1, 2, or 3 attempts (Simulates optional prior retries before succeeding)
    - FAILED:  Requires 1, 2, or 3 attempts (Simulates max retries exhausted or instant hard decline)
    - PENDING: Strictly 1 attempt (In-flight transactions have no retries yet)

  Args:
    target_status (str): Approved execution status ('SUCCESS', 'FAILED', 'PENDING').
    attempt_count (int, optional): Explicit total attempt override (must be between 1 and 3).
    If None, randomly assigns a valid attempt count.

  Returns:
    dict: Target metadata containing assigned attempt count and operational retry rules.
  """
  normalized_status = str(target_status).upper().strip()

  # Validation constraint check
  valid_statuses = {'SUCCESS', 'FAILED', 'PENDING'}
  if normalized_status not in valid_statuses:
    raise ValueError(f"Invalid status '{target_status}'. Must be one of {valid_statuses}")

  # Determine attempt count based on status business rules
  if normalized_status == 'PENDING':
    attempts = 1

  else:
    if attempt_count is not None:
      if attempt_count not in {1, 2, 3}:
        raise ValueError(
          f"Attempt count for {normalized_status} must be 1, 2, or 3. Got {attempt_count}"
        )
      attempts = attempt_count

    else:
      roll = random.randint(1, 100)

      if normalized_status == 'SUCCESS':
        if roll <= 65:
          attempts = 1
        elif roll <= 90:
          attempts = 2
        else:
          attempts = 3

      elif normalized_status == 'FAILED':
        if roll <= 70:
          attempts = 1
        elif roll <= 90:
          attempts = 2
        else:
          attempts = 3

  return {
    "target_status": normalized_status,
    "attempts_required": attempts,
    "description": f"{normalized_status} finalized after {attempts} attempt(s)."
  }


def run_statistical_distribution_test(iterations: int = 10_000):
  """Runs Monte Carlo simulations to verify random distribution probabilities."""
  print(f"\n🧪 Running Statistical Distribution Test ({iterations:,} iterations per status)...")
  print("=" * 65)

  for target in ['SUCCESS', 'FAILED']:
    counts = {1: 0, 2: 0, 3: 0}

    for _ in range(iterations):
      res = determine_payment_lifecycle(target)
      counts[res['attempts_required']] += 1

    pct_1 = (counts[1] / iterations) * 100
    pct_2 = (counts[2] / iterations) * 100
    pct_3 = (counts[3] / iterations) * 100

    expected = "65% / 25% / 10%" if target == 'SUCCESS' else "70% / 20% / 10%"

    print(f"📊 Target Status: {target}")
    print(f"   • Expected Distribution: {expected}")
    print(f"   • 1 Attempt : {counts[1]:>5,} ({pct_1:5.2f}%)")
    print(f"   • 2 Attempts: {counts[2]:>5,} ({pct_2:5.2f}%)")
    print(f"   • 3 Attempts: {counts[3]:>5,} ({pct_3:5.2f}%)")
    print("-" * 65)


# -------------------------------------------------------------
# EXECUTION DEMONSTRATION
# -------------------------------------------------------------
if __name__ == "__main__":
  test_cases = [
    {"status": "SUCCESS", "explicit_attempts": 1},
    {"status": "SUCCESS", "explicit_attempts": 3},
    {"status": "FAILED",  "explicit_attempts": 2},
    {"status": "PENDING", "explicit_attempts": None},
  ]

  print("=======================================================")
  print(" PAYMENT LIFECYCLE ATTEMPT EVALUATION")
  print("=======================================================")
  for test in test_cases:
    result = determine_payment_lifecycle(test["status"], test["explicit_attempts"])
    print(f"• Status: {result['target_status']:<7} | Attempts: {result['attempts_required']} -> {result['description']}")
  print("=======================================================")

  # Run statistical sampling test
  run_statistical_distribution_test(iterations=10_000)

VALID_STATUSES = {'SUCCESS', 'FAILED', 'PENDING'}
def generate_payment_attempts(payment: dict, attempt_count: int):
    """
    Validates input parameters for payment attempt generation.

    Validation Checks:
      1. payment is provided (not None / empty).
      2. payment contains 'payment_id'.
      3. payment contains a valid status ('SUCCESS', 'FAILED', 'PENDING').
      4. attempt_count is an integer equal to 1, 2, or 3.
    """

    # 1. Check payment is provided
    if not isinstance(payment, dict) or not payment:
      raise ValueError("Invalid input: 'payment' dictionary must be provided.")

    # 2. Check payment has payment_id
    if 'payment_id' not in payment or not payment['payment_id']:
      raise ValueError("Invalid payment: 'payment_id' is missing or empty.")

    # 3. Check payment has a valid status
    status = str(payment.get('status', '')).upper().strip()
    if status not in VALID_STATUSES:
      raise ValueError(f"Invalid payment: status '{payment.get('status')}' is invalid. Must be one of {VALID_STATUSES}.")

    # 4. Check attempt_count is 1, 2, or 3
    if not isinstance(attempt_count, int) or attempt_count not in {1, 2, 3}:
      raise ValueError(f"Invalid input: 'attempt_count' must be an integer (1, 2, or 3). Got {attempt_count}.")


    # 5. Check PENDING status business rule (strictly 1 attempt)
    if status == 'PENDING' and attempt_count != 1:
      raise ValueError(f"Business rule violation: PENDING payments can only have exactly 1 attempt. Got attempt_count={attempt_count}.")

    return True  # Inputs are valid


# -------------------------------------------------------------
# VALIDATION TEST DEMONSTRATION
# -------------------------------------------------------------
if __name__ == "__main__":
  valid_payment = {
    "payment_id": "PAY_1001",
    "status": "SUCCESS",
    "amount_minor": 2500,
    "currency": "USD"
  }

  print("=======================================================")
  print(" PAYMENT ATTEMPTS INPUT VALIDATION")
  print("=======================================================")

  # Valid execution
  try:
    generate_payment_attempts(valid_payment, 2)
    print("✓ PASS: Valid payment and attempt count accepted.")
  except ValueError as e:
    print(f"✗ FAIL: {e}")

  # Test cases for failures
  invalid_cases = [
    ({"payment": None, "attempts": 2}, "Missing payment"),
    ({"payment": {"status": "SUCCESS"}, "attempts": 1}, "Missing payment_id"),
    ({"payment": {"payment_id": "PAY_1", "status": "UNKNOWN"}, "attempts": 1}, "Invalid status"),
    ({"payment": valid_payment, "attempts": 5}, "Invalid attempt_count (>3)"),
  ]

  for case, description in invalid_cases:
    try:
      generate_payment_attempts(case["payment"], case["attempts"])
      print(f"✗ FAIL: Should have rejected ({description})")
    except ValueError as e:
      print(f"✓ PASS: Correctly rejected ({description}) -> {e}")

  print("=======================================================")

if __name__ == "__main__":
  pending_payment = {
    "payment_id": "PAY_2002",
    "status": "PENDING",
    "amount_minor": 5000,
    "currency": "EUR"
  }

  print("=======================================================")
  print(" PENDING STATUS BUSINESS RULE VALIDATION")
  print("=======================================================")

  # Valid PENDING payment (1 attempt)
  try:
    generate_payment_attempts(pending_payment, 1)
    print("✓ PASS: PENDING payment with attempt_count=1 accepted.")
  except ValueError as e:
    print(f"✗ FAIL: {e}")

  # Invalid PENDING payment (>1 attempt)
  try:
    generate_payment_attempts(pending_payment, 2)
    print("✗ FAIL: PENDING payment with attempt_count=2 should have been rejected.")
  except ValueError as e:
    print(f"✓ PASS: Correctly rejected PENDING attempt_count=2 -> {e}")

  print("=======================================================")


  test_cases = [
    ("PROCESSOR_TIMEOUT", True),
    ("PROCESSOR_UNAVAILABLE", True),
    ("NETWORK_ERROR", True),
    ("INSUFFICIENT_FUNDS", False),
    ("CARD_DECLINED", False),
    ("INVALID_ACCOUNT", False),
  ]

  for code, expected in test_cases:
    result = is_retryable_error(code)
    status = "✓ PASS" if result == expected else "✗ FAIL"
    print(f"{status}: is_retryable_error('{code}') -> {result}")

  print("=======================================================")

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


def select_error_code(retryable_only: bool = False) -> str:
  """
  Selects a random error code based on retryability requirements.

  Args:
    retryable_only (bool): If True, selects only from RETRYABLE_ERROR_CODES.
    If False, selects from ALL_ERROR_CODES. Defaults to False.

  Returns:
    str: Randomly selected error code string.
  """
  # Requirement 6: Reject inputs that aren't Booleans
  if type(retryable_only) is not bool:
    raise ValueError(f"Invalid input: 'retryable_only' must be a boolean (True or False). Got {type(retryable_only).__name__}.")

  # Requirement 2: Select from retryable errors only
  if retryable_only:
    return random.choice(RETRYABLE_ERROR_CODES)

  # Requirement 4 & 8: Select from all errors and return string
  return random.choice(ALL_ERROR_CODES)


# -------------------------------------------------------------
# VERIFICATION & TEST SUITE
# -------------------------------------------------------------
def run_tests():
  print("=======================================================")
  print(" SELECT ERROR CODE — VERIFICATION SUITE")
  print("=======================================================")

  # Test 1: Default behavior (retryable_only=False)
  code_default = select_error_code()
  assert code_default in ALL_ERROR_CODES
  print(f"✓ PASS: Default selection -> '{code_default}' (Valid error code)")


  # Test 2: retryable_only=True selection constraint
  for _ in range(50):
    code_retryable = select_error_code(retryable_only=True)
    assert code_retryable in RETRYABLE_ERROR_CODES, f"Got non-retryable code: {code_retryable}"
  print("✓ PASS: retryable_only=True repeatedly returns valid retryable errors")

  # Test 3: retryable_only=False selection pool
  codes_all = {select_error_code(retryable_only=False) for _ in range(200)}
  assert codes_all.issubset(set(ALL_ERROR_CODES))
  print(f"✓ PASS: retryable_only=False sampled across pool ({len(codes_all)} unique codes seen)")

  print("\n--- Validating Type Enforcement ---")

  # Test 4: Reject non-boolean inputs (including integers like 1/0)
  invalid_inputs = [1, 0, "True", "False", None, [True], 1.0]
  for invalid in invalid_inputs:
    try:
      select_error_code(invalid)
      print(f"✗ FAIL: Should have rejected input {invalid} of type {type(invalid).__name__}")
    except ValueError as e:
      print(f"✓ PASS: Correctly rejected input ({invalid}) -> {e}")

  # Test 5: Reject non-boolean inputs (including integers like 1/0)
    try:
      select_error_code(invalid)
    except ValueError:
      pass
    else:
      raise AssertionError(
        f"Expected ValueError for input: {invalid!r}"
      )

  # Test 6: Invalid input that isn't rejected will cause the test suite to fail
    try:
      select_error_code(invalid)
    except ValueError:
      pass
    else:
      raise AssertionError(
        f"Expected ValueError for input: {invalid!r}"
      )
  print("=======================================================")


if __name__ == "__main__":
  run_tests()

@patch("random.choice")
def test_select_error_code_mocked(mock_choice):
  # Force random.choice to return specific sequence
  mock_choice.side_effect = ["NETWORK_ERROR", "INSUFFICIENT_FUNDS"]

  assert select_error_code(retryable_only=True) == "NETWORK_ERROR"
  assert select_error_code(retryable_only=False) == "INSUFFICIENT_FUNDS"
  assert mock_choice.call_count == 2

# Determine if an intermediate or final failed attempt requires strictly retryable errors
# or can accept any error code (both retryable and non-retryable).

is_final_attempt = (attempt_number == total_attempts)

if target_status == "SUCCESS":
  retryable_only = True

elif target_status == "FAILED":
  if is_final_attempt:
    retryable_only = False
  else:
    retryable_only = True
