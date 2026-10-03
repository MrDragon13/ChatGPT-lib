from pathlib import Path

from media.tools.build_profiles import build_profile, write_profiles
from media.tools.common import dump_yaml, load_yaml, write_jsonl


def seed(tmp_path: Path) -> Path:
    media=tmp_path/'media'
    for d in ['data/works','data/collections','data/interactions','preferences/explicit','config','generated/profiles']:(media/d).mkdir(parents=True,exist_ok=True)
    dump_yaml(media/'config/viewers.yaml', {'schema_version':4,'viewers':{'primary':{},'partner':{}}})
    dump_yaml(media/'config/groups.yaml', {'schema_version':4,'groups':{'couple':{'members':['primary','partner']}}})
    dump_yaml(media/'preferences/explicit/primary.yaml', {'schema_version':4,'target':'primary','preferences':[], 'rules':[{'id':'slow','statement':'Slow can be fine','source':'explicit','confidence':'exact'}], 'constraints':[]})
    dump_yaml(media/'data/works/a.yaml', {'schema_version':4,'id':'a','entity_type':'work','identity':{'format':'movie','title_original':'A','title_ru':'A','year':2020},'metadata':{'semantic':{'traits':[{'term':'pacing.slow','source':'llm_inferred','confidence':'high'}]}},'viewer_signals':{'primary':{'viewing':{'status':'watched'},'rating':{'score':4.0,'source':'explicit','confidence':'exact'},'rewatch':{'intent':'high'},'relations':[{'target_id':'b','type':'similar_to','strength':2,'source':'explicit','confidence':'high'}],'feedback':{'summary':'bad overall','signals':[{'term':'story.intrigue','sentiment':'positive','strength':3,'source':'explicit','confidence':'high'}]}},'partner':{'viewing':{'status':'watched'},'reaction':{'value':'liked','source':'explicit','confidence':'high'},'feedback':{'signals':[{'term':'story.intrigue','sentiment':'negative','strength':1,'source':'explicit','confidence':'high'}]}}},'group_signals':{'couple':{'feedback':{'signals':[{'term':'story.intrigue','sentiment':'positive','strength':3,'source':'explicit','confidence':'high'}]}}}})
    dump_yaml(media/'data/works/b.yaml', {'schema_version':4,'id':'b','entity_type':'work','identity':{'format':'movie','title_original':'B','title_ru':'B','year':2021}})
    write_jsonl(media/'data/interactions/2026-10.jsonl',[{'schema_version':4,'id':'e1','entity_type':'interaction','at':'2026-10-01T20:00:00+02:00','target':'couple','type':'selected','work_id':'a'},{'schema_version':4,'id':'e2','entity_type':'interaction','at':'2026-10-02T20:00:00+02:00','target':'couple','type':'skipped','work_id':'a'}])
    return media


def add_rated_trait_work(media: Path, work_id: str, score: float, term: str='characters.charisma', confidence: str='high') -> None:
    dump_yaml(media/f'data/works/{work_id}.yaml', {
        'schema_version':4,'id':work_id,'entity_type':'work',
        'identity':{'format':'movie','title_original':work_id,'title_ru':work_id,'year':2022},
        'metadata':{'semantic':{'traits':[{'term':term,'source':'llm_inferred','confidence':confidence}]}},
        'viewer_signals':{'primary':{'viewing':{'status':'watched'},'rating':{'score':score,'source':'explicit','confidence':'exact'}}},
    })


def test_summary_counts_non_affinity_signal_evidence_for_viewer_and_group(tmp_path: Path):
    media=seed(tmp_path)
    primary=build_profile(media,'primary')
    assert primary['summary']['ratings_count']==1
    assert primary['summary']['viewing_count']==1
    assert primary['summary']['rewatch_count']==1
    assert primary['summary']['relations_count']==1
    couple=build_profile(media,'couple')
    assert couple['summary']['ratings_count']==1
    assert couple['summary']['reactions_count']==1
    assert couple['summary']['viewing_count']==2
    assert couple['summary']['rewatch_count']==1
    assert couple['summary']['relations_count']==1


def test_primary_affinity_keeps_explicit_feedback_and_adds_weak_rating_trait(tmp_path: Path):
    media=seed(tmp_path); profile=build_profile(media,'primary')
    assert profile['affinities']['story.intrigue']['score']==1.0
    slow=profile['affinities']['pacing.slow']
    assert slow['score'] < 0
    assert slow['confidence'] == 'low'
    assert slow['evidence'][0]['source_kind'] == 'rating_trait'
    assert slow['evidence'][0]['rating_score'] == 4.0
    assert profile['rules'][0]['id']=='slow'


def test_partner_sparse_reaction_does_not_invent_term_affinity(tmp_path: Path):
    media=seed(tmp_path); profile=build_profile(media,'partner'); assert profile['affinities']['story.intrigue']['score']==-1.0; assert profile['summary']['reactions_count']==1


def test_couple_aggregates_member_evidence_and_direct_group_evidence_not_simple_profile_average(tmp_path: Path):
    media=seed(tmp_path); profile=build_profile(media,'couple'); score=profile['affinities']['story.intrigue']['score']; assert score>0.5; assert profile['affinities']['story.intrigue']['evidence_count']==3; assert profile['summary']['selected_count']==1; assert profile['summary']['skipped_count']==1


def test_explicit_term_preference_participates_with_exact_provenance(tmp_path: Path):
    media=seed(tmp_path); dump_yaml(media/'preferences/explicit/primary.yaml', {'schema_version':4,'target':'primary','preferences':[{'id':'intrigue','statement':'Люблю интригу','term':'story.intrigue','affinity':1.0,'source':'explicit','confidence':'exact'}], 'rules':[], 'constraints':[]}); profile=build_profile(media,'primary'); assert any(e['source_kind']=='explicit_preference' for e in profile['affinities']['story.intrigue']['evidence'])


def test_high_and_low_ratings_create_weak_signed_trait_evidence(tmp_path: Path):
    media=seed(tmp_path); add_rated_trait_work(media,'high',9.5); add_rated_trait_work(media,'low',2.0,term='visuals.strong')
    profile=build_profile(media,'primary')
    assert profile['affinities']['characters.charisma']['score'] > 0
    assert profile['affinities']['characters.charisma']['confidence'] == 'low'
    assert profile['affinities']['visuals.strong']['score'] < 0
    assert profile['affinities']['visuals.strong']['confidence'] == 'low'


def test_neutral_rating_does_not_create_trait_affinity(tmp_path: Path):
    media=seed(tmp_path); add_rated_trait_work(media,'neutral',5.5)
    profile=build_profile(media,'primary')
    assert 'characters.charisma' not in profile['affinities']


def test_explicit_feedback_dominates_rating_trait_evidence(tmp_path: Path):
    media=seed(tmp_path)
    add_rated_trait_work(media,'rated',2.0,term='story.intrigue')
    profile=build_profile(media,'primary')
    intrigue=profile['affinities']['story.intrigue']
    assert intrigue['score'] > 0.7
    assert any(e['source_kind']=='rating_trait' for e in intrigue['evidence'])
    assert any(e['source_kind']=='feedback' for e in intrigue['evidence'])


def test_repeated_independent_high_ratings_can_raise_confidence_but_single_cannot(tmp_path: Path):
    media=seed(tmp_path); add_rated_trait_work(media,'one',10.0)
    one=build_profile(media,'primary')['affinities']['characters.charisma']
    assert one['confidence']=='low'
    for idx in range(2,7): add_rated_trait_work(media,f'w{idx}',10.0)
    repeated=build_profile(media,'primary')['affinities']['characters.charisma']
    assert repeated['evidence_count']==6
    assert repeated['confidence'] in {'medium','high'}


def test_write_profiles_outputs_all_configured_targets_deterministically(tmp_path: Path):
    media=seed(tmp_path); paths=write_profiles(media); assert sorted(p.stem for p in paths)==['couple','partner','primary']; before={p.name:p.read_bytes() for p in paths}; paths2=write_profiles(media); assert {p.name:p.read_bytes() for p in paths2}==before; assert load_yaml(media/'generated/profiles/couple.yaml')['target']=='couple'
