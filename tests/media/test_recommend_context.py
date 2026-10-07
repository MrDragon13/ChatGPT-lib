from media.commands.schema import parse_command
from media.repository.index_repo import IndexRepository
from media.service.recommend import build_recommend_context
from media.tools.common import dump_yaml
from tests.media.fixture_repo import append_material_rating_event, copy_fixture_repo, prepare_derived


def request(target="primary", **overrides):
    data={"schema_version":1,"operation":"recommend_context","target":target,"only_unwatched":True,"include_not_interested":False,"limit":20}; data.update(overrides); return parse_command(data)

def ids(context): return [item["id"] for item in context["candidates"]]

def _write_similarity(root):
    path=root/"media/data/relations/similarity/primary.yaml"; path.parent.mkdir(parents=True,exist_ok=True)
    dump_yaml(path,{"schema_version":1,"target":"primary","relations":[{"type":"similar","left":{"kind":"canonical","work_id":"arrival-2016"},"right":{"kind":"canonical","work_id":"unwatched-fit-2020"},"terms":["story.intrigue"],"note":"Оба держат интригой","updated_at":"2026-10-03T20:00:00+00:00","provenance":{"source":"explicit"}}]})


def _write_candidate(root, work_id, traits, priority=0):
    semantic=[{"term":term,"source":"llm_inferred","confidence":"high"} for term in traits]
    work={
        "schema_version":4,
        "entity_type":"work",
        "id":work_id,
        "identity":{"format":"movie","title_original":work_id,"title_ru":work_id,"year":2026},
        "metadata":{"external":{"runtime_min":100}},
        "target_states":{"primary":{"interest":{"state":"shortlist","priority":priority}}},
    }
    if semantic:
        work["metadata"]["semantic"]={"traits":semantic}
    dump_yaml(root/f"media/data/works/{work_id}.yaml",work)


def _write_primary_profile(root, scores):
    affinities={
        term:{"score":score,"confidence":"high" if score>0 else "low","evidence_count":2,"evidence":[]}
        for term,score in scores.items()
    }
    dump_yaml(root/"media/generated/profiles/primary.yaml",{
        "schema_version":4,
        "target":"primary",
        "generated_from":"test-fixture",
        "affinities":affinities,
        "explicit_preferences":[],
        "rules":[],
        "constraints":[],
        "summary":{},
        "evidence":{"entity_count":0},
    })


def _ranking_fixture(tmp_path):
    root=copy_fixture_repo(tmp_path)
    candidates={
        "rank-net4-concern":["story.intrigue","action.strong","visuals.strong","humor.witty","tone.light","humor.absurd"],
        "rank-net2-zero":["story.intrigue","action.strong"],
        "rank-net2-concern":["story.intrigue","action.strong","visuals.strong","humor.absurd"],
        "rank-net1-zero":["story.intrigue"],
        "rank-net1-concern":["story.intrigue","action.strong","humor.absurd"],
        "rank-fallback-a":["worldbuilding.strong"],
        "rank-fallback-b":["worldbuilding.strong"],
        "rank-fallback-low":[],
    }
    for work_id,traits in candidates.items():
        priority=5 if work_id in {"rank-fallback-a","rank-fallback-b"} else (1 if work_id=="rank-fallback-low" else 0)
        _write_candidate(root,work_id,traits,priority=priority)
    prepare_derived(root)
    _write_primary_profile(root,{
        "story.intrigue":1.0,
        "action.strong":0.7,
        "visuals.strong":0.4,
        "humor.witty":0.2,
        "tone.light":0.1,
        "humor.absurd":-0.1,
    })
    return root


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


def test_candidate_evidence_includes_explicit_similarity_without_match_score(tmp_path):
    root=copy_fixture_repo(tmp_path); prepare_derived(root); _write_similarity(root)
    context=build_recommend_context(root/"media",request("primary"))
    candidate=next(item for item in context["candidates"] if item["id"]=="unwatched-fit-2020")
    assert candidate["evidence"]["similarities"]==[{
        "other":{"kind":"canonical","work_id":"arrival-2016"},
        "terms":["story.intrigue"],
        "note":"Оба держат интригой",
        "updated_at":"2026-10-03T20:00:00+00:00",
        "provenance":{"source":"explicit"},
    }]
    assert "match_score" not in candidate


def test_sign_aware_order_uses_net_then_concerns_and_never_rewards_negative_match(tmp_path):
    root=_ranking_fixture(tmp_path)
    ordered=ids(build_recommend_context(root/"media",request(limit=50)))

    assert ordered.index("rank-net4-concern") < ordered.index("rank-net2-zero")
    assert ordered.index("rank-net2-zero") < ordered.index("rank-net2-concern")
    assert ordered.index("rank-net1-zero") < ordered.index("rank-net1-concern")


def test_adding_strength_cannot_worsen_and_adding_concern_cannot_improve_rank(tmp_path):
    root=_ranking_fixture(tmp_path)
    ordered=ids(build_recommend_context(root/"media",request(limit=50)))

    assert ordered.index("rank-net2-zero") < ordered.index("rank-net1-zero")
    assert ordered.index("rank-net2-zero") < ordered.index("rank-net1-concern")


def test_personalized_candidates_always_precede_fallback_and_fallback_is_priority_then_id(tmp_path):
    root=_ranking_fixture(tmp_path)
    context=build_recommend_context(root/"media",request(limit=50))
    ordered=ids(context)

    last_personalized=max(index for index,item in enumerate(context["candidates"]) if item["ranking_basis"]=="trait_overlap")
    first_fallback=min(index for index,item in enumerate(context["candidates"]) if item["ranking_basis"]=="none")
    assert last_personalized < first_fallback
    assert ordered.index("rank-fallback-a") < ordered.index("rank-fallback-b") < ordered.index("rank-fallback-low")
    assert ordered==ids(build_recommend_context(root/"media",request(limit=50)))


def test_recommendation_observability_preserves_legacy_lists_and_adds_details_basis_reason(tmp_path):
    root=copy_fixture_repo(tmp_path); prepare_derived(root)
    context=build_recommend_context(root/"media",request(limit=50))
    personalized=next(item for item in context["candidates"] if item["id"]=="unwatched-fit-2020")
    fallback=next(item for item in context["candidates"] if item["ranking_basis"]=="none")

    assert personalized["evidence"]["strengths"]==["story.intrigue"]
    assert personalized["evidence"]["concerns"]==[]
    assert personalized["evidence"]["evidence_details"]["strengths"]==[{
        "term":"story.intrigue",
        "direction":"positive",
        "affinity_score":1.0,
        "confidence":"high",
        "evidence_count":1,
    }]
    assert personalized["ranking_basis"]=="trait_overlap"
    assert personalized["fallback_reason"] is None
    assert "net_directional_count" not in personalized
    assert "match_score" not in personalized
    assert fallback["fallback_reason"] in {"no_semantic_fingerprint","no_matching_affinities"}


def test_coverage_reconciles_pool_and_returned_and_limit_does_not_change_pool_counts(tmp_path):
    root=_ranking_fixture(tmp_path)
    one=build_recommend_context(root/"media",request(limit=1))
    many=build_recommend_context(root/"media",request(limit=50))

    pool_keys={"pool_total","pool_with_fingerprint","pool_with_personalized_basis","pool_fallback"}
    assert {key:one["coverage"][key] for key in pool_keys}=={key:many["coverage"][key] for key in pool_keys}
    assert many["coverage"]["pool_with_personalized_basis"]+many["coverage"]["pool_fallback"]==many["coverage"]["pool_total"]
    assert many["coverage"]["returned_with_personalized_basis"]+many["coverage"]["returned_fallback"]==many["coverage"]["returned_total"]
    assert one["coverage"]["returned_total"]==1
    assert many["coverage"]["returned_total"]==len(many["candidates"])


def test_limitations_are_top_level_fact_only_and_deterministically_ordered(tmp_path):
    root=copy_fixture_repo(tmp_path); prepare_derived(root); _write_primary_profile(root,{})
    context=build_recommend_context(root/"media",request(limit=50))

    assert context["coverage"]["pool_total"]>0
    assert context["coverage"]["pool_with_personalized_basis"]==0
    assert context["coverage"]["returned_fallback"]>0
    assert context["limitations"]==[
        "partial_semantic_coverage",
        "fallback_candidates_present",
        "no_personalized_candidates",
    ]


def test_recommend_context_exposes_due_reanalysis_without_blocking_context_build(tmp_path):
    root=copy_fixture_repo(tmp_path)
    for index in range(5):
        append_material_rating_event(
            root,
            score=7.0 + index / 2,
            event_id=f"123e4567-e89b-42d3-a456-4266141747{index:02d}",
            at=f"2026-10-07T14:0{index}:00Z",
        )
    prepare_derived(root)
    context=build_recommend_context(root/"media",request("primary"))
    assert context["reanalysis"]["due"] is True
    assert context["candidates"]
    assert "taste_reanalysis_due" in context["limitations"]
