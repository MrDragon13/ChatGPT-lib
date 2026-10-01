import pytest
from media.commands.schema import parse_command
from media.domain.errors import AmbiguousIdentityError, ProviderUnavailableError
from media.providers.base import CanonicalMetadata, ProviderCandidate
from media.service.transaction import execute_command
from media.tools.common import load_yaml
from tests.media.fixture_repo import copy_fixture_repo
UUID1="123e4567-e89b-42d3-a456-426614174101"; UUID2="123e4567-e89b-42d3-a456-426614174102"
def add(title,year=None,operation_id=UUID1):
    ref={"title":title}
    if year is not None: ref["year"]=year
    return parse_command({"schema_version":1,"operation_id":operation_id,"operation":"add_work","work_ref":ref})
class FakeProvider:
    def __init__(self,candidates=None,fail=False): self.candidates=candidates; self.fail=fail
    def search_work(self,title,year=None):
        if self.fail: raise ProviderUnavailableError("offline")
        return list(self.candidates or [ProviderCandidate("movie",329865,"Прибытие","Arrival",2016)])
    def fetch_work(self,media_type,provider_id):
        if self.fail: raise ProviderUnavailableError("offline")
        return CanonicalMetadata(identity={"format":"movie","title_original":"Arrival","title_ru":"Прибытие","year":2016,"release_date":"2016-11-10","external_ids":{"tmdb":{"media_type":"movie","id":329865},"imdb":"tt2543164"}},external={"runtime_min":116,"genres":["Science Fiction","Drama"],"provenance":{"provider":"tmdb","provider_id":329865,"fetched_at":"2026-10-01T00:00:00Z"}})
def test_existing_tmdb_identity_returns_no_change_not_duplicate(tmp_path):
    root=copy_fixture_repo(tmp_path); provider=FakeProvider(candidates=[ProviderCandidate("movie",329865,"The Arrival Movie","The Arrival Movie",2016)]); result=execute_command(root,add("The Arrival Movie",2016),provider=provider); assert result.status=="no_change"; assert len(list((root/"media/data/works").glob("*.yaml")))==8
def test_add_new_work_creates_canonical_file_and_generated_index(tmp_path):
    root=copy_fixture_repo(tmp_path)
    class NewProvider(FakeProvider):
        def search_work(self,title,year=None): return [ProviderCandidate("movie",777,"Новый фильм","New Film",2025)]
        def fetch_work(self,media_type,provider_id): return CanonicalMetadata(identity={"format":"movie","title_original":"New Film","title_ru":"Новый фильм","year":2025,"external_ids":{"tmdb":{"media_type":"movie","id":777},"imdb":"tt7777777"}},external={"runtime_min":101,"provenance":{"provider":"tmdb","provider_id":777,"fetched_at":"2026-10-01T00:00:00Z"}})
    result=execute_command(root,add("New Film",2025,UUID2),provider=NewProvider()); assert result.status=="applied"; work=load_yaml(root/"media/data/works/new-film-2025.yaml"); assert work["identity"]["external_ids"]["tmdb"]=={"media_type":"movie","id":777}; assert '"id":"new-film-2025"' in (root/"media/generated/index.jsonl").read_text(encoding="utf-8")
def test_multiple_plausible_results_are_ambiguous(tmp_path):
    root=copy_fixture_repo(tmp_path); provider=FakeProvider(candidates=[ProviderCandidate("movie",1,"Twin","Twin",2020),ProviderCandidate("tv",2,"Twin","Twin",2020)])
    with pytest.raises(AmbiguousIdentityError): execute_command(root,add("Twin",2020),provider=provider)
def test_provider_failure_blocks_only_new_provider_dependent_add(tmp_path):
    root=copy_fixture_repo(tmp_path)
    with pytest.raises(ProviderUnavailableError): execute_command(root,add("Brand New",2030),provider=FakeProvider(fail=True))
