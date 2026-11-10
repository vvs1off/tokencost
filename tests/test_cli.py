import io
import json

import pytest

from tokencost.cli import main


def test_text_json(capsys):
    rc = main(["--text", "cat dog", "-m", "medium", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["input_tokens"] == 2
    assert out["models"][0]["model"] == "medium"
    # 2 tokens * 3.0 / 1e6
    assert out["models"][0]["input_cost"] == pytest.approx(6e-6)


def test_text_human(capsys):
    rc = main(["--text", "hello world"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "input tokens:" in out
    assert "UNVERIFIED" in out


def test_file(capsys, fixtures_dir):
    rc = main([str(fixtures_dir / "sample.txt"), "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["input_tokens"] > 0
    assert out["file_count"] == 1


def test_stdin(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("cat dog"))
    rc = main(["-"])
    assert rc == 0
    assert "input tokens:  2" in capsys.readouterr().out


def test_list_models(capsys):
    rc = main(["--list-models"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "medium" in out


def test_file_not_found(capsys):
    rc = main(["/no/such/file.xyz"])
    assert rc == 1
    assert "tokencost:" in capsys.readouterr().err


def test_unknown_model(capsys):
    rc = main(["--text", "hi", "-m", "nope"])
    assert rc == 1
    assert "unknown model" in capsys.readouterr().err


def test_no_input_errors(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    rc = main([])
    assert rc == 1


def test_negative_output_tokens_is_usage(capsys):
    rc = main(["--text", "hi", "--output-tokens", "-5"])
    assert rc == 2


def test_repo_mode_by_file(capsys, tmp_path):
    (tmp_path / "a.py").write_text("cat dog", encoding="utf-8")
    (tmp_path / "b.py").write_text("hello", encoding="utf-8")
    rc = main([str(tmp_path), "--include", "*.py", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["file_count"] == 2
    paths = {f["path"] for f in out["files"]}
    assert paths == {"a.py", "b.py"}


def test_pricing_override(capsys, fixtures_dir):
    rc = main(
        [
            "--text",
            "cat dog",
            "-m",
            "custom",
            "--pricing",
            str(fixtures_dir / "pricing_override.json"),
            "--json",
        ]
    )
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["models"][0]["model"] == "custom"
    assert out["prices_verified"] is True


def test_output_tokens_cost(capsys):
    rc = main(["--text", "cat dog", "-m", "medium", "--output-tokens", "1000000", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    # output 15.0 per 1M * 1M = 15.0
    assert out["models"][0]["output_cost"] == pytest.approx(15.0)


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
