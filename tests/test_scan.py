from tokencost.scan import read_file_text, scan_tree


def _write(path, text="hello world\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_scans_plain_tree(tmp_path):
    _write(tmp_path / "a.txt")
    _write(tmp_path / "sub" / "b.txt")
    files = scan_tree(tmp_path)
    assert [f.path for f in files] == ["a.txt", "sub/b.txt"]


def test_gitignore_excludes(tmp_path):
    _write(tmp_path / "keep.py")
    _write(tmp_path / "skip.log")
    (tmp_path / ".gitignore").write_text("*.log\n", encoding="utf-8")
    files = scan_tree(tmp_path)
    # .gitignore is itself tracked by git, so it is counted; *.log is not.
    assert [f.path for f in files] == [".gitignore", "keep.py"]


def test_gitignore_directory(tmp_path):
    _write(tmp_path / "src" / "main.py")
    _write(tmp_path / "build" / "out.o", "x")
    (tmp_path / ".gitignore").write_text("build/\n", encoding="utf-8")
    files = scan_tree(tmp_path)
    assert [f.path for f in files] == [".gitignore", "src/main.py"]


def test_gitignore_negation(tmp_path):
    _write(tmp_path / "a.log")
    _write(tmp_path / "keep.log")
    (tmp_path / ".gitignore").write_text("*.log\n!keep.log\n", encoding="utf-8")
    files = scan_tree(tmp_path)
    assert [f.path for f in files] == [".gitignore", "keep.log"]


def test_no_gitignore_flag(tmp_path):
    _write(tmp_path / "skip.log")
    (tmp_path / ".gitignore").write_text("*.log\n", encoding="utf-8")
    files = scan_tree(tmp_path, use_gitignore=False)
    assert [f.path for f in files] == [".gitignore", "skip.log"]


def test_git_dir_always_skipped(tmp_path):
    _write(tmp_path / ".git" / "config", "x")
    _write(tmp_path / "a.txt")
    files = scan_tree(tmp_path)
    assert [f.path for f in files] == ["a.txt"]


def test_include_glob(tmp_path):
    _write(tmp_path / "a.py")
    _write(tmp_path / "b.txt")
    files = scan_tree(tmp_path, include=["*.py"])
    assert [f.path for f in files] == ["a.py"]


def test_exclude_glob(tmp_path):
    _write(tmp_path / "a.py")
    _write(tmp_path / "b.txt")
    files = scan_tree(tmp_path, exclude=["*.txt"])
    assert [f.path for f in files] == ["a.py"]


def test_binary_skipped(tmp_path):
    (tmp_path / "bin").write_bytes(b"\x00\x01\x02binary")
    _write(tmp_path / "ok.txt")
    files = scan_tree(tmp_path)
    assert [f.path for f in files] == ["ok.txt"]


def test_read_file_text(tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("content", encoding="utf-8")
    assert read_file_text(p) == "content"
