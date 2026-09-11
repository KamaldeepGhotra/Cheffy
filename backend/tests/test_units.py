import re
from pathlib import Path

import pytest

from app.units import CANONICAL_UNITS, DEFAULT_UNIT, UNIT_VOCABULARY, normalize_unit


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("cups", "cup"),
        ("Cloves", "clove"),
        ("lbs", "lb"),
        ("Pounds", "lb"),
        ("tablespoons", "tbsp"),
        ("tsps", "tsp"),
        ("whole", "each"),
        ("ea", "each"),
        ("pcs", "piece"),
        ("packages", "pack"),
        ("litres", "l"),
    ],
)
def test_aliases_map_to_canonical(raw, expected):
    assert normalize_unit(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", None])
def test_empty_becomes_each(raw):
    assert normalize_unit(raw) == "each"
    assert DEFAULT_UNIT == "each"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("pinch", "pinch"),
        ("leaves", "leaves"),
        ("  Fl Oz  ", "fl oz"),
    ],
)
def test_unknown_unit_passes_through_lowercased(raw, expected):
    assert normalize_unit(raw) == expected


def test_trailing_period_is_ignored():
    assert normalize_unit("lbs.") == "lb"
    assert normalize_unit("oz.") == "oz"


def test_canonical_units_are_idempotent():
    for unit in CANONICAL_UNITS:
        assert normalize_unit(unit) == unit


def test_vocabulary_is_the_canonical_keys():
    assert UNIT_VOCABULARY == list(CANONICAL_UNITS)
    assert len(set(UNIT_VOCABULARY)) == len(UNIT_VOCABULARY)


def test_no_alias_belongs_to_two_units():
    seen = {}
    for unit, aliases in CANONICAL_UNITS.items():
        for alias in aliases:
            assert alias not in seen, f"{alias!r} listed under both {seen[alias]} and {unit}"
            seen[alias] = unit


def test_table_matches_frontend_units_js():
    source = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "units.js").read_text()
    block = re.search(r"const UNIT_ALIASES = \{(.*?)\n\}", source, re.S).group(1)
    frontend = {
        key: re.findall(r"'([^']+)'", aliases)
        for key, aliases in re.findall(r"(\w+): \[([^\]]*)\]", block)
    }
    assert frontend == CANONICAL_UNITS
