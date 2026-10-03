from media.commands.schema import parse_command
from media.repository.index_repo import IndexRepository
from media.service.recommend import build_recommend_context
from tests.media.fixture_repo import copy_fixture_repo, prepare_derived


def request(target="primary", **overrides):
    data={"schema_version":1,"operation":"recommend_context","target":target,"only_unwatched":True,"include_not_interested":False,"limit":20}; data.update(overrides); return parse_command(data)

def ids(context): return [item["id"] for item in context["candidates"]]

def test_recommend_context_has_strengths_and_concerns_but_no_match_score(tmp_path):
    root=copy_fixture_repo(tmp_path); prepare_derived(root); context=build_recommend_context(root/"media",request()); candidate=next(x for x in context["candidates"] if x["id"]=="unwatched-fit-2020"); assert "strengths" in candidate["evidence"]; assert "concerns" in candidate["evidence"]; assert "story.intrigue" in candidate["evidence"]["strengths"]; assert "match_score" not in candidate

def test_primary_only_unwatched_excludes_watched(tmp_path):
    root=copy_fixture_repo(tmp_path); prepare_derived(root); context=build_recommend_context(root/"media",request("primary")); assert "arrival-2016" not in ids(context); assert "watched-by-primary-only" not in ids(context)

def test_couple_only_unwatched_excludes_only_if_every_member_watched(tmp_path):
    root=copy_fixture_repo(tmp_path); prepare_derived(root); context=build_recommend_context(root/"media",request("couple")); assert "arrival-2016" not in ids(context); assert "watched-by-primary-only" in ids(context)

def test_not_interested_is_excluded_by_default_and_can_be_included(tmp_path):
    root=copy_fixture_repo(tmp_path); prepare_derived(root); assert "dune-1984" not in ids(build_recommend_context(root/"media",request("primary"))); assert "dune-1984" in ids(build_recommend_context(root/"media",request("primary",include_not_interested=True,only_unwatched=False)))

def test_runtime_max_is_hard_filter_and_order_is_stable(tmp_path):
    root=copy_fixture_repo(tmp_path); prepare_derived(root); context=build_recommend_context(root/"media",request("primary",runtime_max=120)); assert "dune-2021" not in ids(context); first=ids(context); second=ids(build_recommend_context(root/"media",request("primary",runtime_max=120))); assert first==second


def test_internal_recommendation_candidates_are_bounded_to_local_index(tmp_path):
    root = copy_fixture_repo(tmp_path)
    prepare_derived(root)
    local_ids = {
        row["id"]
        for row in IndexRepository(root / "media" / "generated" / "index.jsonl").rows()
    }
    context = build_recommend_context(
        root / "media",
        request("couple", text="Что посмотреть из нашей медиатеки?", limit=50),
    )
    assert local_ids
    assert set(ids(context)) <= local_ids
