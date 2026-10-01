from media.repository.index_repo import IndexRepository
from media.repository.sqlite_repo import SQLiteRepository
from tests.media.fixture_repo import copy_fixture_repo, prepare_derived


def test_sqlite_repository_returns_same_work_ids_as_index_for_simple_search(tmp_path):
    root=copy_fixture_repo(tmp_path); prepare_derived(root); media=root/"media"; index_ids=[row["id"] for row in IndexRepository(media/"generated/index.jsonl").search("dune")]; sqlite_ids=[row["id"] for row in SQLiteRepository(media/"generated/database.sqlite").search("dune")]; assert sqlite_ids==index_ids

def test_sqlite_repository_is_read_only_surface(tmp_path):
    root=copy_fixture_repo(tmp_path); prepare_derived(root); repo=SQLiteRepository(root/"media/generated/database.sqlite"); assert not hasattr(repo,"write"); assert not hasattr(repo,"apply_changeset")
