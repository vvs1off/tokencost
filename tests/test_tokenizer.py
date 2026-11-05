import pytest

from tokencost.tokenizer import estimate_tokens


def test_empty_is_zero():
    assert estimate_tokens("") == 0


def test_single_short_word_is_one():
    assert estimate_tokens("cat") == 1


def test_two_words():
    # "cat" -> 1, "dog" -> 1
    assert estimate_tokens("cat dog") == 2


def test_punctuation_counts():
    # "foo"(1) + "."(1) + "bar"(1)
    assert estimate_tokens("foo.bar") == 3


def test_digits_fragment_more():
    # ceil(5/3) == 2
    assert estimate_tokens("12345") == 2


def test_newlines_count():
    assert estimate_tokens("a\nb") == estimate_tokens("a") + estimate_tokens("b") + 1


def test_deterministic():
    text = "The quick brown fox jumps over the lazy dog."
    assert estimate_tokens(text) == estimate_tokens(text)


def test_chars_method():
    assert estimate_tokens("abcd", method="chars") == 1
    assert estimate_tokens("a" * 8, method="chars") == 2


def test_chars_method_custom_divisor():
    assert estimate_tokens("a" * 10, method="chars", chars_per_token=5) == 2


def test_unknown_method_raises():
    with pytest.raises(ValueError):
        estimate_tokens("x", method="nope")


def test_bad_divisor_raises():
    with pytest.raises(ValueError):
        estimate_tokens("x", method="chars", chars_per_token=0)


def test_heuristic_longer_word_more_tokens():
    assert estimate_tokens("antidisestablishmentarianism") > estimate_tokens("cat")
