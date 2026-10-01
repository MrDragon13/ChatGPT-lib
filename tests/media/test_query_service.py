from media.service.query import search_works, show_work
from tests.media.fixture_repo import copy_fixture_repo, prepare_derived


def test_index_search_finds_title_without_scanning_full_yaml(tmp_path):
    root = copy_fixture_repo(tmp_path); prepare_derived(root)
    assert search_works(root / "media", "arrival")[0]["id"] == "arrival-2016"


def test_show_work_resolves_full_yaml(tmp_path):
    root = copy_fixture_repo(tmp_path); prepare_derived(root)
    assert show_work(root / "media", "Прибытие")["id"] == "arrival-2016"
