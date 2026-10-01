import json
from pathlib import Path
import pytest
from media.domain.errors import ProviderUnavailableError
from media.providers.tmdb import TMDBProvider
FIXTURES=Path(__file__).parents[1]/"fixtures"/"tmdb"
def fake_request(url,headers):
    if "/search/multi" in url: return json.loads((FIXTURES/"search_arrival.json").read_text(encoding="utf-8"))
    if "/movie/329865" in url: return json.loads((FIXTURES/"movie_arrival.json").read_text(encoding="utf-8"))
    raise AssertionError(url)
def test_tmdb_normalizes_arrival_identity_and_provenance():
    provider=TMDBProvider("token",request_json=fake_request); candidates=provider.search_work("Arrival",2016); assert [(c.media_type,c.provider_id) for c in candidates]==[("movie",329865)]; metadata=provider.fetch_work("movie",329865); assert metadata.identity["title_original"]=="Arrival"; assert metadata.identity["title_ru"]=="Прибытие"; assert metadata.identity["year"]==2016; assert metadata.identity["external_ids"]["tmdb"]=={"media_type":"movie","id":329865}; assert metadata.identity["external_ids"]["imdb"]=="tt2543164"; assert metadata.external["runtime_min"]==116; assert metadata.external["provenance"]["provider"]=="tmdb"; assert metadata.external["directors"][0]["name"]=="Denis Villeneuve"
def test_search_filters_out_person_results(): assert all(candidate.media_type in {"movie","tv"} for candidate in TMDBProvider("token",request_json=fake_request).search_work("Arrival"))
def test_provider_wraps_transport_failure():
    def broken(url,headers): raise OSError("offline")
    with pytest.raises(ProviderUnavailableError): TMDBProvider("token",request_json=broken).search_work("Arrival")
