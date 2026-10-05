import sys
import os

# Add the parent directory (project root) to Python's module search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Now import your validation function
from src.validation.validate_payments import run_validation_framework


run_validation_test = run_validation_framework(
  "tests/data/invalid_payments.csv"
)