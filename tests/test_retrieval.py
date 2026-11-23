from features.retrieval import documents, BM25, tokenize, search, search_courts, search_events

def test_dataset_sizes_and_ids():
    courts, events = documents('courts'), documents('events')
    assert len(courts) >= 30 and len(events) >= 30
    assert len({x['venue_id'] for x in courts}) == len(courts)
    assert len({x['event_id'] for x in events}) == len(events)

def test_keyword_search():
    out = search('indoor basketball court', 'courts', 'keyword', k=5)
    assert len(out['results']) == 5
    assert out['results'][0]['venue_id'].startswith('VEN-')

def test_hybrid_search():
    assert len(search_courts('Tempe basketball gym',k=3)) == 3
    assert len(search_events('3v3 beginner basketball',k=4)) == 4

def test_empty_query_and_method_validation():
    assert search(' ','courts')['results'] == []
    import pytest
    with pytest.raises(ValueError):search('test','courts','invalid')

def test_bm25_nonnegative():
    assert min(BM25(['basketball court','tennis']).score('basketball')) >= 0
