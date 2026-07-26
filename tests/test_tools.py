from src.tools.calculator import calculator


def test_calculator_basic():
    assert calculator("2 + 2") == "4"


def test_calculator_precedence():
    assert calculator("2 + 3 * 4") == "14"


def test_calculator_parens():
    assert calculator("17 * (3 + 5)") == "136"


def test_calculator_invalid_expression():
    result = calculator("import os")
    assert result.startswith("Error")


def test_calculator_rejects_non_numeric():
    result = calculator("'a' + 'b'")
    assert result.startswith("Error")
