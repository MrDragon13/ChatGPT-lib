from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from media.commands.schema import parse_command
from media.domain.errors import AmbiguousIdentityError, PathPolicyError, ProviderUnavailableError, TransactionValidationError
from media.providers.base import CanonicalMetadata, ProviderCandidate
from media.repository.yaml_repo import YamlRepository
from media.service.path_policy import verify_changed_paths
from media.service.recommend import build_recommend_context
from media.service.transaction import execute_command
from media.tools.common import load_yaml
from media.tools.rebuild import check_generated, rebuild_generated
from tests.media.fixture_repo import copy_fixture_repo


def snapshot(root:Path)->dict[str,bytes]: return {str(path.relative_to(root)):path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}
class NewMovieProvider:
    def search_work(self,title:str,year:int|None=None): return [ProviderCandidate('movie',777,'Новый фильм','New Film',2025)]
    def fetch_work(self,media_type:str,provider_id:int): return CanonicalMetadata(identity={'format':'movie','title_original':'New Film','title_ru':'Новый фильм','year':2025,'external_ids':{'tmdb':{'media_type':'movie','id':777},'imdb':'tt7777777'}},external={'runtime_min':101,'provenance':{'provider':'tmdb','provider_id':777,'fetched_at':'2026-10-01T00:00:00Z'}})
class AmbiguousNewMovieProvider(NewMovieProvider):
    def search_work(self,title:str,year:int|None=None): return [ProviderCandidate('movie',777,'Новый фильм','New Film',2025),ProviderCandidate('movie',778,'Новый фильм','New Film',2024)]
class OfflineProvider:
    def search_work(self,title:str,year:int|None=None): raise ProviderUnavailableError('offline')
    def fetch_work(self,media_type:str,provider_id:int): raise ProviderUnavailableError('offline')

def test_e2e_primary_and_partner_feedback_is_one_atomic_command(tmp_path):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/'media'); command=parse_command({'schema_version':1,'operation_id':'123e4567-e89b-42d3-a456-426614174301','operation':'record_viewing_feedback','work_ref':{'id':'unwatched-fit-2020'},'target_updates':[{'target':'primary','viewing':{'status':'watched'},'rating':{'score':8.5,'source':'explicit_approx','confidence':'high'}},{'target':'partner','viewing':{'status':'watched'},'reaction':{'value':'liked','source':'explicit','confidence':'exact'}}]}); result=execute_command(root,command,now=datetime(2026,10,1,tzinfo=timezone.utc)); work=load_yaml(root/'media/data/works/unwatched-fit-2020.yaml'); assert result.status=='applied'; assert work['viewer_signals']['primary']['rating']['score']==8.5; assert work['viewer_signals']['partner']['reaction']['value']=='liked'; assert check_generated(root/'media')==[]
def test_e2e_add_new_tmdb_work_validates_and_rebuilds(tmp_path):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/'media'); command=parse_command({'schema_version':1,'operation_id':'123e4567-e89b-42d3-a456-426614174302','operation':'add_work','work_ref':{'title':'New Film','year':2025}}); result=execute_command(root,command,provider=NewMovieProvider(),now=datetime(2026,10,1,tzinfo=timezone.utc)); assert result.status=='applied'; assert (root/'media/data/works/new-film-2025.yaml').exists(); assert check_generated(root/'media')==[]
def test_e2e_unknown_work_and_feedback_are_one_atomic_command(tmp_path):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/'media'); command=parse_command({'schema_version':1,'operation_id':'123e4567-e89b-42d3-a456-426614174307','operation':'record_viewing_feedback','create_if_missing':True,'work_ref':{'title':'New Film','year':2025},'target_updates':[{'target':'primary','viewing':{'status':'watched'},'rating':{'score':6,'source':'explicit','confidence':'exact'}},{'target':'partner','viewing':{'status':'watched'},'reaction':{'value':'mixed','source':'explicit','confidence':'high'}}]}); result=execute_command(root,command,provider=NewMovieProvider(),now=datetime(2026,10,1,tzinfo=timezone.utc)); work=load_yaml(root/'media/data/works/new-film-2025.yaml'); assert result.status=='applied'; assert result.changed_entities==('new-film-2025',); assert work['viewer_signals']['primary']['rating']['score']==6; assert work['viewer_signals']['partner']['reaction']['value']=='mixed'; assert check_generated(root/'media')==[]
def test_e2e_create_if_missing_provider_outage_rolls_back_everything(tmp_path):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/'media'); command=parse_command({'schema_version':1,'operation_id':'123e4567-e89b-42d3-a456-426614174308','operation':'record_viewing_feedback','create_if_missing':True,'work_ref':{'title':'New Film','year':2025},'target_updates':[{'target':'primary','viewing':{'status':'watched'}}]}); before=snapshot(root)
    with pytest.raises(ProviderUnavailableError): execute_command(root,command,provider=OfflineProvider())
    assert snapshot(root)==before
def test_e2e_create_if_missing_ambiguous_provider_rolls_back_everything(tmp_path):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/'media'); command=parse_command({'schema_version':1,'operation_id':'123e4567-e89b-42d3-a456-426614174309','operation':'record_viewing_feedback','create_if_missing':True,'work_ref':{'title':'New Film'},'target_updates':[{'target':'primary','viewing':{'status':'watched'}}]}); before=snapshot(root)
    with pytest.raises(AmbiguousIdentityError): execute_command(root,command,provider=AmbiguousNewMovieProvider())
    assert snapshot(root)==before
def test_e2e_create_if_missing_existing_work_does_not_need_provider(tmp_path):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/'media'); command=parse_command({'schema_version':1,'operation_id':'123e4567-e89b-42d3-a456-426614174310','operation':'record_viewing_feedback','create_if_missing':True,'work_ref':{'id':'arrival-2016'},'target_updates':[{'target':'primary','reaction':{'value':'liked','source':'explicit','confidence':'exact'}}]}); result=execute_command(root,command,provider=OfflineProvider()); assert result.status=='applied'
def test_e2e_recommend_context_uses_compact_retrieval(tmp_path,monkeypatch):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/'media'); request=parse_command({'schema_version':1,'operation':'recommend_context','target':'primary','only_unwatched':True,'limit':3})
    def forbidden_scan(self): raise AssertionError('recommendation retrieval should not scan full work YAML')
    monkeypatch.setattr(YamlRepository,'iter_works',forbidden_scan); context=build_recommend_context(root/'media',request); assert context['candidates']; assert len(context['candidates'])<=3
def test_e2e_duplicate_operation_has_no_second_effect(tmp_path):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/'media'); command=parse_command({'schema_version':1,'operation_id':'123e4567-e89b-42d3-a456-426614174303','operation':'set_interest','work_ref':{'id':'unwatched-fit-2020'},'target':'primary','state':'candidate','priority':2}); first=execute_command(root,command); after=snapshot(root); second=execute_command(root,command); assert first.status=='applied'; assert second.status=='already_applied'; assert snapshot(root)==after
def test_e2e_ambiguous_identity_changes_nothing(tmp_path):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/'media'); command=parse_command({'schema_version':1,'operation_id':'123e4567-e89b-42d3-a456-426614174304','operation':'set_interest','work_ref':{'title':'Dune'},'target':'primary','state':'shortlist','priority':3}); before=snapshot(root)
    with pytest.raises(AmbiguousIdentityError): execute_command(root,command)
    assert snapshot(root)==before
def test_e2e_invalid_term_changes_nothing(tmp_path):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/'media'); command=parse_command({'schema_version':1,'operation_id':'123e4567-e89b-42d3-a456-426614174305','operation':'record_viewing_feedback','work_ref':{'id':'arrival-2016'},'target_updates':[{'target':'primary','feedback':{'summary':'invalid term','signals':[{'term':'missing.term','sentiment':'negative','strength':2,'source':'explicit','confidence':'high'}]}}]}); before=snapshot(root)
    with pytest.raises(TransactionValidationError): execute_command(root,command)
    assert snapshot(root)==before
def test_e2e_stale_generated_artifact_fails_check(tmp_path):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/'media'); index=root/'media/generated/index.jsonl'; index.write_text(index.read_text(encoding='utf-8')+'{}\n',encoding='utf-8'); assert 'generated/index.jsonl' in check_generated(root/'media')
def test_e2e_architecture_path_is_rejected():
    with pytest.raises(PathPolicyError): verify_changed_paths('record_viewing_feedback',['media/service/transaction.py'])
    with pytest.raises(PathPolicyError): verify_changed_paths('record_viewing_feedback',['media/vocabulary.yaml'])
def test_e2e_provider_outage_does_not_block_existing_feedback(tmp_path):
    root=copy_fixture_repo(tmp_path); rebuild_generated(root/'media'); command=parse_command({'schema_version':1,'operation_id':'123e4567-e89b-42d3-a456-426614174306','operation':'record_viewing_feedback','work_ref':{'id':'arrival-2016'},'target_updates':[{'target':'primary','reaction':{'value':'liked','source':'explicit','confidence':'exact'}}]}); result=execute_command(root,command,provider=OfflineProvider()); assert result.status=='applied'
