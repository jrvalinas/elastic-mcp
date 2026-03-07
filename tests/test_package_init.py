import importlib
import sys


def test_package_init_is_lazy() -> None:
    sys.modules.pop("mcp_elastic_logs", None)
    sys.modules.pop("mcp_elastic_logs.server", None)

    module = importlib.import_module("mcp_elastic_logs")

    assert module.__all__ == ["mcp"]
    assert "mcp_elastic_logs.server" not in sys.modules
