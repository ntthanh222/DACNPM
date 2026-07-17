from pathlib import Path


def test_rasa_actions_httpx_pin_is_chromadb_client_compatible():
    requirements = (
        Path(__file__).resolve().parents[1] / "requirements-actions.txt"
    ).read_text(encoding="utf-8")

    assert "chromadb-client==1.5.9" in requirements
    assert "httpx==0.28.1" in requirements
    assert "httpx>=0.24,<0.26" not in requirements
