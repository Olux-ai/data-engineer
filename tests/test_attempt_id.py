import pytest

from src.data_generator.attempt_id import create_attempt_id


def test_create_first_attempt_id():
  assert create_attempt_id("PAY-2001", 1) == "PAY-2001-ATT-001"


def test_create_third_attempt_id():
  assert create_attempt_id("PAY-2001", 3) == "PAY-2001-ATT-003"


def test_empty_payment_id_raises_error():
  with pytest.raises(ValueError):
    create_attempt_id("", 1)


def test_attempt_number_above_limit_raises_error():
  with pytest.raises(ValueError):
    create_attempt_id("PAY-2001", 4)


def test_boolean_attempt_number_raises_error():
  with pytest.raises(ValueError):
    create_attempt_id("PAY-2001", True)