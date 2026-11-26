import pytest

from features.retrieval import BM25, documents, search, search_courts, search_events


def test_dataset_sizes_and_ids():
    courts, events = documents("courts"), documents("events")
    assert len(courts) >= 30 and len(events) >= 30
    assert len({item["venue_id"] for item in courts}) == len(courts)
    assert len({item["event_id"] for item in events}) == len(events)


def test_keyword_search():
    out = search("indoor basketball court", "courts", "keyword", k=5)
    assert len(out["results"]) == 5
    assert out["results"][0]["venue_id"].startswith("VEN-")


def test_hybrid_search():
    assert len(search_courts("Tempe basketball gym", k=3)) == 3
    assert len(search_events("3v3 beginner basketball", k=4)) == 4


def test_empty_query_and_method_validation():
    assert search(" ", "courts")["results"] == []
    with pytest.raises(ValueError):
        search("test", "courts", "invalid")


def test_bm25_nonnegative():
    assert min(BM25(["basketball court", "tennis"]).score("basketball")) >= 0


# Person 1: new structured filtering tests. These call the real synthetic data.
@pytest.mark.parametrize("method", ["keyword", "semantic", "hybrid"])
def test_court_city_indoor_filters(method):
    out = search(
        "basketball court", "courts", method, k=10,
        filters={"city": " tUcSoN ", "indoor": True},
    )
    assert out["results"]
    assert all(item["city"] == "Tucson" and item["indoor"] for item in out["results"])
    assert out["total_candidates"] >= len(out["results"])


@pytest.mark.parametrize("method", ["keyword", "semantic", "hybrid"])
def test_event_city_skill_and_format_filters(method):
    out = search(
        "basketball tournament", "events", method, k=10,
        filters={"city": "Phoenix", "skill_level": "beginner", "format": "3v3"},
    )
    assert out["results"]
    assert all(
        item["city"] == "Phoenix"
        and item["skill_level"] == "Beginner"
        and item["format"] == "3v3"
        for item in out["results"]
    )


def test_amenities_and_rate_filter():
    out = search(
        "indoor basketball gym", "courts", "keyword", k=15,
        filters={"amenities": ["parking", "scoreboard"], "max_hourly_rate": 60},
    )
    assert out["results"]
    assert all(
        {"parking", "scoreboard"}.issubset(set(item["amenities"]))
        and item["hourly_rate"] <= 60
        for item in out["results"]
    )


def test_no_matching_filters_returns_empty_not_unrelated_results():
    out = search("basketball court", "courts", filters={"city": "Nonexistent City"})
    assert out["results"] == []
    assert out["total_candidates"] == 0


def test_filters_applied_before_top_k():
    out = search("gym", "courts", "keyword", k=1, filters={"city": "Tucson"})
    assert len(out["results"]) == 1
    assert out["results"][0]["city"] == "Tucson"


def test_invalid_filter_types_and_categories_are_rejected():
    with pytest.raises(ValueError):
        search("court", "courts", filters={"indoor": "yes"})
    with pytest.raises(ValueError):
        search("court", "courts", filters={"skill_level": "Beginner"})
    with pytest.raises(ValueError):
        search("court", "courts", filters={"max_hourly_rate": -10})
    with pytest.raises(ValueError):
        search("event", "events", filters={"amenities": ["parking"]})
