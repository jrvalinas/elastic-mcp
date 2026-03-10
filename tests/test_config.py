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
