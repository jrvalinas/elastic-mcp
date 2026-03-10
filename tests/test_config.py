import pytest

from mcp_elastic_logs.config import ElasticConfig


def test_config_allows_missing_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ELASTICSEARCH_URL", "http://localhost:9200")
    monkeypatch.delenv("ELASTICSEARCH_API_KEY", raising=False)
    monkeypatch.delenv("ELASTICSEARCH_USERNAME", raising=False)
    monkeypatch.delenv("ELASTICSEARCH_PASSWORD", raising=False)

    config = ElasticConfig.from_env()

    assert config.url == "http://localhost:9200"
    assert config.api_key is None
    assert config.username is None
    assert config.password is None
    assert config.field_mapping.model_dump() == {
        "timestamp_field": None,
        "message_field": None,
        "level_field": None,
        "service_field": None,
        "correlation_field": None,
        "hostname_field": None,
        "extra_timestamp_candidates": [],
        "extra_message_candidates": [],
        "extra_level_candidates": [],
        "extra_service_candidates": [],
        "extra_correlation_candidates": [],
        "extra_hostname_candidates": [],
        "extra_message_fallbacks": [],
    }
