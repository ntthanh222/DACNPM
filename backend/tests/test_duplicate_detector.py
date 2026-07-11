from backend.utils import duplicate_detector


def test_duplicate_detector_uses_cached_url_and_titles():
    detector = duplicate_detector.DuplicateDetector(method="both", fuzzy_threshold=0.8)
    detector._existing_urls = {"https://example.test/a"}
    detector._existing_titles = ["Critical security update released"]

    assert detector.is_duplicate({"url": "https://example.test/a", "title": "Another title"}) == "URL already exists"
    result = detector.is_duplicate({"url": "https://example.test/b", "title": "Critical security update release"})
    assert result == "Similar title found: Critical security update released"
    assert detector.is_duplicate({"url": "https://example.test/c", "title": "Different story"}) is None


def test_duplicate_detector_normalizes_text_and_handles_missing_fields():
    detector = duplicate_detector.DuplicateDetector()

    assert detector._normalize_text(" Hello,  WORLD! ") == "hello world"
    assert detector._calculate_similarity("Update!", "update") == 1
    assert detector.is_duplicate({"url": "only-url"}) is None


def test_duplicate_detector_queries_and_caches_fake_supabase(monkeypatch):
    class Result:
        def __init__(self, data): self.data = data

    class Query:
        def __init__(self, data): self.data = data
        def select(self, *_): return self
        def eq(self, *_args, **_kwargs): return self
        def order(self, *_args, **_kwargs): return self
        def limit(self, *_args, **_kwargs): return self
        def execute(self): return Result(self.data)

    class Supabase:
        def table(self, _name): return Query([{"url": "https://db.test", "title": "Database title", "source": "nvd"}])

    monkeypatch.setattr(duplicate_detector, "supabase", Supabase())
    detector = duplicate_detector.DuplicateDetector(method="both")
    assert detector._is_duplicate_by_url("https://db.test") is True
    assert detector._is_duplicate_by_title("Database title", "nvd") == "Database title"
    detector.cache_existing_articles()
    assert detector._existing_urls == {"https://db.test"}
    detector.clear_cache()
    assert detector._existing_urls is None
