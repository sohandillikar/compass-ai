from __future__ import annotations

from compass_cli.fuzzy import course_variants, normalize_course_canonical


def test_normalize_course_canonical_zero_pads_to_three_digits():
    assert normalize_course_canonical("ECS 36C") == "ecs036c"
    assert normalize_course_canonical("ECS036C") == "ecs036c"
    assert normalize_course_canonical("MAT 21A") == "mat021a"
    assert normalize_course_canonical("MAT111") == "mat111"


def test_normalize_course_canonical_ignores_trailing_course_name():
    assert normalize_course_canonical("ECS036C - Data Structures") == "ecs036c"
    assert normalize_course_canonical("ECS 36C Data Structures") == "ecs036c"


def test_course_variants_include_padded_and_unpadded_tokens():
    v = course_variants("ECS 36C")
    assert "ecs036c" in v
    assert "ecs36c" in v
    assert "036c" in v
    assert "36c" in v

