import pytest

from backend.utils import validators


@pytest.mark.parametrize(
    ("value", "cleaned"),
    [("CVE-2024-1234", "CVE-2024-1234"), (" cve-1999-00001 ", "CVE-1999-00001")],
)
def test_validate_cve_id_accepts_and_normalizes_valid_ids(value, cleaned):
    result = validators.validate_cve_id(value)

    assert result == {"valid": True, "error": None, "cleaned_cve": cleaned}


@pytest.mark.parametrize("value", ["CVE-24-1234", "CVE-2024-123", "CVE-2024-1234-extra", "", None])
def test_validate_cve_id_rejects_invalid_ids(value):
    result = validators.validate_cve_id(value)

    assert result["valid"] is False
    assert result["cleaned_cve"] is None


@pytest.mark.parametrize("value", ["https://example.com/path", "http://example.com"])
def test_validate_url_accepts_http_and_https(value):
    assert validators.validate_url(value)["cleaned_url"] == value


@pytest.mark.parametrize("value", ["example.com", "ftp://example.com", "https://"])
def test_validate_url_rejects_missing_or_invalid_schemes(value):
    assert validators.validate_url(value)["valid"] is False


def test_validate_password_reports_complexity_and_length():
    strong = validators.validate_password("Abcdef1!")
    short = validators.validate_password("Ab1!")

    assert strong["valid"] is True
    assert strong["checks"] == {"has_upper": True, "has_lower": True, "has_digit": True, "has_special": True}
    assert strong["strength_score"] == 80
    assert short["valid"] is False
    assert short["strength"] == "TOO_SHORT"


def test_sanitize_input_strips_tags_dangerous_characters_and_whitespace():
    sanitized = validators.sanitize_input("  <script>alert('x')</script> Hello & goodbye;  ")

    assert sanitized == "alert(x) Hello goodbye"


def test_validate_search_query_sanitizes_and_enforces_minimum_length():
    valid = validators.validate_search_query(" <b>vulnerability</b> ")
    invalid = validators.validate_search_query(" <i>x</i> ")

    assert valid == {"valid": True, "error": None, "sanitized_query": "vulnerability"}
    assert invalid["valid"] is False
    assert invalid["sanitized_query"] is None


def test_validate_pagination_params_applies_defaults_and_maximum_page_size():
    defaults = validators.validate_pagination_params(0, 0)
    capped = validators.validate_pagination_params(3, 250)

    assert defaults == {"valid": True, "error": None, "page": 1, "page_size": 20, "offset": 0}
    assert capped["page_size"] == 100
    assert capped["offset"] == 200


def test_validate_api_key_strips_required_prefix():
    valid = validators.validate_api_key("Bearer secret-token")
    invalid = validators.validate_api_key("secret-token")

    assert valid == {"valid": True, "error": None, "cleaned_key": "secret-token"}
    assert invalid["valid"] is False


@pytest.mark.parametrize("value", ["user@example.com", " User.Name+tag@example.co.uk "])
def test_validate_email_normalizes_valid_addresses(value):
    assert validators.validate_email(value)["valid"] is True


@pytest.mark.parametrize("value", ["user@example", "user@@example.com", "not an email", ""])
def test_validate_email_rejects_invalid_addresses(value):
    result = validators.validate_email(value)

    assert result["valid"] is False
    assert result["cleaned_email"] is None
