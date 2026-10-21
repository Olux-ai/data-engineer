from datetime import datetime, timezone
import random
from unittest.mock import patch
import pytest

# -------------------------------------------------------------
# GLOBAL CONSTANTS & SCHEMAS
# -------------------------------------------------------------
VALID_STATUSES = {"SUCCESS", "FAILED", "PENDING"}

RETRYABLE_ERROR_CODES = [
    "PROCESSOR_TIMEOUT",
    "PROCESSOR_UNAVAILABLE",
    "NETWORK_ERROR",
]

NON_RETRYABLE_ERROR_CODES = [
    "INSUFFICIENT_FUNDS",
    "CARD_DECLINED",
    "INVALID_ACCOUNT",
]

ALL_ERROR_CODES = RETRYABLE_ERROR_CODES + NON_RETRYABLE_ERROR_CODES


# -------------------------------------------------------------
# CORE LOGIC FUNCTIONS
# -------------------------------------------------------------
def determine_payment_lifecycle(
    target_status: str, attempt_count: int = None
) -> dict:
  """Determines the total attempt count and retry behavior for a payment based on target status.

  Rules:
    - SUCCESS: Requires 1, 2, or 3 attempts (Simulates optional prior retries
    before succeeding)
    - FAILED:  Requires 1, 2, or 3 attempts (Simulates max retries exhausted or
    instant hard decline)
    - PENDING: Strictly 1 attempt (In-flight transactions have no retries yet)

  Args:
    target_status (str): Approved execution status ('SUCCESS', 'FAILED',
      'PENDING').
    attempt_count (int, optional): Explicit total attempt override (must be
      between 1 and 3). If None, randomly assigns a valid attempt count.

  Returns:
    dict: Target metadata containing assigned attempt count and operational
    retry rules.
  """
  normalized_status = str(target_status).upper().strip()

  # Validation constraint check
  if normalized_status not in VALID_STATUSES:
    raise ValueError(
        f"Invalid status '{target_status}'. Must be one of {VALID_STATUSES}"
    )

  # Determine attempt count based on status business rules
  if normalized_status == "PENDING":
    attempts = 1
  else:
    if attempt_count is not None:
      if attempt_count not in {1, 2, 3}:
        raise ValueError(
            f"Attempt count for {normalized_status} must be 1, 2, or 3. Got"
            f" {attempt_count}"
        )
      attempts = attempt_count
    else:
      roll = random.randint(1, 100)

      if normalized_status == "SUCCESS":
        if roll <= 65:
          attempts = 1
        elif roll <= 90:
          attempts = 2
        else:
          attempts = 3

      elif normalized_status == "FAILED":
        if roll <= 70:
          attempts = 1
        elif roll <= 90:
          attempts = 2
        else:
          attempts = 3

  return {
      "target_status": normalized_status,
      "attempts_required": attempts,
      "description": (
          f"{normalized_status} finalized after {attempts} attempt(s)."
      ),
  }


def generate_payment_attempts(payment: dict, attempt_count: int):
  """Validates input parameters for payment attempt generation.

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
  if "payment_id" not in payment or not payment["payment_id"]:
    raise ValueError("Invalid payment: 'payment_id' is missing or empty.")

  # 3. Check payment has a valid status
  status = str(payment.get("status", "")).upper().strip()
  if status not in VALID_STATUSES:
    raise ValueError(
        f"Invalid payment: status '{payment.get('status')}' is invalid. Must be"
        f" one of {VALID_STATUSES}."
    )

  # 4. Check attempt_count is 1, 2, or 3
  if not isinstance(attempt_count, int) or attempt_count not in {1, 2, 3}:
    raise ValueError(
        "Invalid input: 'attempt_count' must be an integer (1, 2, or 3). Got"
        f" {attempt_count}."
    )

  # 5. Check PENDING status business rule (strictly 1 attempt)
  if status == "PENDING" and attempt_count != 1:
    raise ValueError(
        "Business rule violation: PENDING payments can only have exactly 1"
        f" attempt. Got attempt_count={attempt_count}."
    )

  return True  # Inputs are valid


def select_error_code(retryable_only: bool = False) -> str:
  """Selects a random error code based on retryability requirements.

  Args:
    retryable_only (bool): If True, selects only from RETRYABLE_ERROR_CODES. If
      False, selects from ALL_ERROR_CODES. Defaults to False.

  Returns:
    str: Randomly selected error code string.
  """
  if type(retryable_only) is not bool:
    raise ValueError(
        "Invalid input: 'retryable_only' must be a boolean (True or False). Got"
        f" {type(retryable_only).__name__}."
    )

  if retryable_only:
    return random.choice(RETRYABLE_ERROR_CODES)

  return random.choice(ALL_ERROR_CODES)


# -------------------------------------------------------------
# TEST & SIMULATION RUNNERS
# -------------------------------------------------------------
def run_statistical_distribution_test(iterations: int = 10_000):
  """Runs Monte Carlo simulations to verify random distribution probabilities."""
  print(
      f"\n🧪 Running Statistical Distribution Test ({iterations:,} iterations"
      " per status)..."
  )
  print("=" * 65)

  for target in ["SUCCESS", "FAILED"]:
    counts = {1: 0, 2: 0, 3: 0}

    for _ in range(iterations):
      res = determine_payment_lifecycle(target)
      counts[res["attempts_required"]] += 1

    pct_1 = (counts[1] / iterations) * 100
    pct_2 = (counts[2] / iterations) * 100
    pct_3 = (counts[3] / iterations) * 100

    expected = "65% / 25% / 10%" if target == "SUCCESS" else "70% / 20% / 10%"

    print(f"📊 Target Status: {target}")
    print(f"   • Expected Distribution: {expected}")
    print(f"   • 1 Attempt : {counts[1]:>5,} ({pct_1:5.2f}%)")
    print(f"   • 2 Attempts: {counts[2]:>5,} ({pct_2:5.2f}%)")
    print(f"   • 3 Attempts: {counts[3]:>5,} ({pct_3:5.2f}%)")
    print("-" * 65)


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
    assert (
        code_retryable in RETRYABLE_ERROR_CODES
    ), f"Got non-retryable code: {code_retryable}"
  print("✓ PASS: retryable_only=True repeatedly returns valid retryable errors")

  # Test 3: retryable_only=False selection pool
  codes_all = {select_error_code(retryable_only=False) for _ in range(200)}
  assert codes_all.issubset(set(ALL_ERROR_CODES))
  print(
      "✓ PASS: retryable_only=False sampled across pool"
      f" ({len(codes_all)} unique codes seen)"
  )

  print("\n--- Validating Type Enforcement ---")

  # Test 4-6: Reject non-boolean inputs (including integers like 1/0)
  invalid_inputs = [1, 0, "True", "False", None, [True], 1.0]
  for invalid in invalid_inputs:
    try:
      select_error_code(invalid)
    except ValueError as e:
      print(f"✓ PASS: Correctly rejected input ({invalid}) -> {e}")
    else:
      raise AssertionError(f"Expected ValueError for input: {invalid!r}")

  print("=======================================================")


# -------------------------------------------------------------
# PYTEST UNIT TESTS
# -------------------------------------------------------------
@patch("random.choice")
def test_select_error_code_mocked(mock_choice):
  mock_choice.side_effect = ["NETWORK_ERROR", "INSUFFICIENT_FUNDS"]

  assert select_error_code(retryable_only=True) == "NETWORK_ERROR"
  assert select_error_code(retryable_only=False) == "INSUFFICIENT_FUNDS"
  assert mock_choice.call_count == 2


# -------------------------------------------------------------
# EXECUTION DEMONSTRATION MAIN BLOCK
# -------------------------------------------------------------
if __name__ == "__main__":
  # 1. Lifecycle Evaluation Demo
  test_cases = [
      {"status": "SUCCESS", "explicit_attempts": 1},
      {"status": "SUCCESS", "explicit_attempts": 3},
      {"status": "FAILED", "explicit_attempts": 2},
      {"status": "PENDING", "explicit_attempts": None},
  ]

  print("=======================================================")
  print(" PAYMENT LIFECYCLE ATTEMPT EVALUATION")
  print("=======================================================")
  for test in test_cases:
    result = determine_payment_lifecycle(
        test["status"], test["explicit_attempts"]
    )
    print(
        f"• Status: {result['target_status']:<7} | Attempts:"
        f" {result['attempts_required']} -> {result['description']}"
    )
  print("=======================================================")

  # Run statistical sampling test
  run_statistical_distribution_test(iterations=10_000)

  # 2. Input Validation Demo
  valid_payment = {
      "payment_id": "PAY_1001",
      "status": "SUCCESS",
      "amount_minor": 2500,
      "currency": "USD",
  }

  print("=======================================================")
  print(" PAYMENT ATTEMPTS INPUT VALIDATION")
  print("=======================================================")

  try:
    generate_payment_attempts(valid_payment, 2)
    print("✓ PASS: Valid payment and attempt count accepted.")
  except ValueError as e:
    print(f"✗ FAIL: {e}")

  invalid_cases = [
      ({"payment": None, "attempts": 2}, "Missing payment"),
      ({"payment": {"status": "SUCCESS"}, "attempts": 1}, "Missing payment_id"),
      (
          {
              "payment": {"payment_id": "PAY_1", "status": "UNKNOWN"},
              "attempts": 1,
          },
          "Invalid status",
      ),
      (
          {"payment": valid_payment, "attempts": 5},
          "Invalid attempt_count (>3)",
      ),
  ]

  for case, description in invalid_cases:
    try:
      generate_payment_attempts(case["payment"], case["attempts"])
      print(f"✗ FAIL: Should have rejected ({description})")
    except ValueError as e:
      print(f"✓ PASS: Correctly rejected ({description}) -> {e}")

  print("=======================================================")

  # 3. Pending Status Rule Demo
  pending_payment = {
      "payment_id": "PAY_2002",
      "status": "PENDING",
      "amount_minor": 5000,
      "currency": "EUR",
  }

  print("=======================================================")
  print(" PENDING STATUS BUSINESS RULE VALIDATION")
  print("=======================================================")

  try:
    generate_payment_attempts(pending_payment, 1)
    print("✓ PASS: PENDING payment with attempt_count=1 accepted.")
  except ValueError as e:
    print(f"✗ FAIL: {e}")

  try:
    generate_payment_attempts(pending_payment, 2)
    print(
        "✗ FAIL: PENDING payment with attempt_count=2 should have been"
        " rejected."
    )
  except ValueError as e:
    print(f"✓ PASS: Correctly rejected PENDING attempt_count=2 -> {e}")

  print("=======================================================")

  # 4. Error Code Selection Verification Suite
  run_tests()