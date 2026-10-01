from pathlib import Path
from media.tools.rebuild import check_generated, rebuild_generated
from tests.media.fixture_repo import copy_fixture_repo

def tree_bytes(root:Path): return {str(p.relative_to(root)):p.read_bytes() for p in sorted(root.rglob('*')) if p.is_file()}
def test_two_text_rebuilds_are_byte_identical(tmp_path):
    root=copy_fixture_repo(tmp_path); one=tmp_path/'one'; two=tmp_path/'two'; rebuild_generated(root/'media',one); rebuild_generated(root/'media',two); assert tree_bytes(one)==tree_bytes(two)
def test_stale_index_is_detected(tmp_path):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/'media'); index=root/'media/generated/index.jsonl'; index.write_text(index.read_text(encoding='utf-8')+'{}\n',encoding='utf-8'); assert 'generated/index.jsonl' in check_generated(root/'media')
def test_stale_profile_is_detected(tmp_path):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/'media'); profile=root/'media/generated/profiles/primary.yaml'; profile.write_text(profile.read_text(encoding='utf-8')+'# stale\n',encoding='utf-8'); assert 'generated/profiles/primary.yaml' in check_generated(root/'media')
