import base64
from pathlib import Path

from media.tools.build_index import write_index


def test_diagnostic_regenerated_index(tmp_path: Path):
    output = tmp_path / "index.jsonl"
    write_index(Path("media"), output)
    payload = base64.b64encode(output.read_bytes()).decode("ascii")
    print("MEDIA_INDEX_B64_BEGIN" + payload + "MEDIA_INDEX_B64_END")
    raise AssertionError("diagnostic regenerated index")
