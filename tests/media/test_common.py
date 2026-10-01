from pathlib import Path

from media.tools.common import dump_yaml, iter_jsonl, iter_yaml_files, load_yaml, write_jsonl


def test_yaml_round_trip_preserves_unicode_none_and_nested_lists(tmp_path: Path):
    path = tmp_path / "данные.yaml"
    data = {"title": "Интерстеллар", "value": None, "nested": [{"x": 1}, ["а", None]]}
    dump_yaml(path, data)
    assert load_yaml(path) == data
    assert "Интерстеллар" in path.read_text(encoding="utf-8")


def test_iter_yaml_files_is_lexicographically_stable(tmp_path: Path):
    for name in ["z.yaml", "a.yml", "m.yaml", "ignore.txt"]:
        (tmp_path / name).write_text("{}\n", encoding="utf-8")
    assert [p.name for p in iter_yaml_files(tmp_path)] == ["a.yml", "m.yaml", "z.yaml"]


def test_iter_jsonl_returns_physical_line_numbers_and_skips_blank_lines(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    path.write_text('{"a":1}\n\n  \n{"b":2}\n', encoding="utf-8")
    assert list(iter_jsonl(path)) == [(1, {"a": 1}), (4, {"b": 2})]


def test_write_jsonl_is_utf8_and_one_row_per_line(tmp_path: Path):
    path = tmp_path / "index.jsonl"
    write_jsonl(path, [{"title": "Амели"}, {"n": 2}])
    assert path.read_text(encoding="utf-8") == '{"title":"Амели"}\n{"n":2}\n'
