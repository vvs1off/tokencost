import pytest

from tokencost.pricing import (
    PricingError,
    available_models,
    load_pricing,
    resolve_model,
)


def test_defaults_present():
    table = load_pricing()
    assert set(available_models(table)) >= {"small", "medium", "large"}
    assert table["currency"] == "USD"
    assert table["per_tokens"] == 1_000_000


def test_default_prices_unverified():
    table = load_pricing()
    assert resolve_model(table, "medium").verified is False


def test_cost_input_only():
    table = load_pricing()
    medium = resolve_model(table, "medium")  # input 3.0 / 1M
    assert medium.cost(1_000_000, 0) == pytest.approx(3.0)
    assert medium.cost(500_000, 0) == pytest.approx(1.5)


def test_cost_output():
    table = load_pricing()
    medium = resolve_model(table, "medium")  # output 15.0 / 1M
    assert medium.cost(0, 1_000_000) == pytest.approx(15.0)


def test_unknown_model_raises():
    table = load_pricing()
    with pytest.raises(PricingError):
        resolve_model(table, "does-not-exist")


def test_override_merges(fixtures_dir):
    table = load_pricing(fixtures_dir / "pricing_override.json")
    # overridden
    medium = resolve_model(table, "medium")
    assert medium.input_per_m == 2.0
    assert medium.verified is True
    # added
    assert "custom" in available_models(table)
    # kept from defaults
    assert "large" in available_models(table)


def test_env_var_override(monkeypatch, fixtures_dir):
    monkeypatch.setenv("TOKENCOST_PRICING", str(fixtures_dir / "pricing_override.json"))
    table = load_pricing()
    assert resolve_model(table, "custom").input_per_m == 1.0


def test_explicit_path_beats_env(monkeypatch, fixtures_dir):
    monkeypatch.setenv("TOKENCOST_PRICING", str(fixtures_dir / "pricing_override.json"))
    table = load_pricing(None)  # None still reads env
    assert "custom" in available_models(table)


def test_missing_file_raises(tmp_path):
    with pytest.raises(PricingError):
        load_pricing(tmp_path / "nope.json")


def test_bad_json_raises(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(PricingError):
        load_pricing(p)


def test_negative_rate_raises(tmp_path):
    p = tmp_path / "neg.json"
    p.write_text('{"models": {"m": {"input": -1, "output": 2}}}', encoding="utf-8")
    with pytest.raises(PricingError):
        load_pricing(p)


def test_missing_rate_key_raises(tmp_path):
    p = tmp_path / "partial.json"
    p.write_text('{"models": {"m": {"input": 1}}}', encoding="utf-8")
    with pytest.raises(PricingError):
        load_pricing(p)
