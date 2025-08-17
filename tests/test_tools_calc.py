import pytest

from silhouette_core.tools import safe_calc


@pytest.mark.parametrize(
    "expr,expected",
    [
        ("2+2", "4"),
        ("3*7", "21"),
        ("10-3", "7"),
        ("8/2", "4.0"),
        ("2**3", "8"),
        ("-5+10", "5"),
    ],
)
def test_calc_happy(expr, expected):
    assert safe_calc(expr) == expected


@pytest.mark.parametrize(
    "expr",
    [
        "import os",
        "__import__('os')",
        "open('x')",
        "lambda: 1",
        "[1,2][0]",
        "{1:2}[1]",
        "(1,2)[0]",
    ],
)
def test_calc_disallowed(expr):
    out = safe_calc(expr)
    assert out.startswith("[tool:calc] error")


def test_calc_length_guard():
    expr = "1+" * 300
    out = safe_calc(expr)
    assert "expression too long" in out


def test_calc_div_zero():
    out = safe_calc("1/0")
    assert out.startswith("[tool:calc] error")

