import json
import pytest
from unittest.mock import MagicMock, patch

import tools.vision_inspect_tool as vit
from tools.vision_inspect_tool import (
    VisionInspectAPITool,
    VisionInspectWriteTool,
    VisionInspectReadTool,
)


# ── VisionInspectAPITool — URL construction ────────────────────────────────────

def _make_tool():
    return VisionInspectAPITool(base_url="http://localhost:8000", timeout=5.0)

def _mock_get(mock_client, json_data):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = json_data
    mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
    return mock_client.return_value.__enter__.return_value

def _mock_post(mock_client, json_data):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = json_data
    mock_client.return_value.__enter__.return_value.post.return_value = mock_resp
    return mock_client.return_value.__enter__.return_value


def test_url_strips_trailing_slash_from_base():
    tool = VisionInspectAPITool(base_url="http://localhost:8000/", timeout=5.0)
    with patch("tools.vision_inspect_tool.httpx.Client") as mc:
        client = _mock_get(mc, {"ok": True})
        tool._run("GET", "/health", "")
        url = client.get.call_args[0][0]
        assert url == "http://localhost:8000/health"

def test_url_strips_leading_slash_from_path():
    tool = _make_tool()
    with patch("tools.vision_inspect_tool.httpx.Client") as mc:
        client = _mock_get(mc, {})
        tool._run("GET", "/inspections", "")
        url = client.get.call_args[0][0]
        assert url == "http://localhost:8000/inspections"


# ── VisionInspectAPITool — POST payload ───────────────────────────────────────

def test_post_empty_payload_sends_empty_dict():
    tool = _make_tool()
    with patch("tools.vision_inspect_tool.httpx.Client") as mc:
        client = _mock_post(mc, {})
        tool._run("POST", "/inspections", "")
        client.post.assert_called_once_with("http://localhost:8000/inspections", json={})

def test_post_valid_json_payload_is_parsed():
    tool = _make_tool()
    with patch("tools.vision_inspect_tool.httpx.Client") as mc:
        client = _mock_post(mc, {})
        tool._run("POST", "/inspections", '{"limit": 10}')
        client.post.assert_called_once_with(
            "http://localhost:8000/inspections", json={"limit": 10}
        )

def test_method_is_case_insensitive():
    tool = _make_tool()
    with patch("tools.vision_inspect_tool.httpx.Client") as mc:
        client = _mock_post(mc, {})
        tool._run("post", "/run", "")
        assert client.post.called


# ── VisionInspectAPITool — error handling ─────────────────────────────────────

def test_connect_error_returns_friendly_message():
    import httpx
    tool = _make_tool()
    with patch("tools.vision_inspect_tool.httpx.Client") as mc:
        mc.return_value.__enter__.return_value.get.side_effect = httpx.ConnectError("refused")
        result = tool._run("GET", "/health", "")
        assert "Cannot connect" in result

def test_http_status_error_includes_status_code():
    import httpx
    tool = _make_tool()
    with patch("tools.vision_inspect_tool.httpx.Client") as mc:
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "Not Found"
        mc.return_value.__enter__.return_value.get.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=mock_resp
        )
        result = tool._run("GET", "/missing", "")
        assert "404" in result


# ── VisionInspectWriteTool / ReadTool — path safety ──────────────────────────

def test_write_blocks_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(vit, "_VI_ROOT", tmp_path)
    result = VisionInspectWriteTool()._run("../outside.txt", "bad")
    assert "Access denied" in result

def test_write_creates_file(tmp_path, monkeypatch):
    monkeypatch.setattr(vit, "_VI_ROOT", tmp_path)
    VisionInspectWriteTool()._run("backend/main.py", "# hello")
    assert (tmp_path / "backend" / "main.py").read_text(encoding="utf-8") == "# hello"

def test_read_blocks_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(vit, "_VI_ROOT", tmp_path)
    result = VisionInspectReadTool()._run("../outside.txt")
    assert "Access denied" in result

def test_read_returns_error_for_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(vit, "_VI_ROOT", tmp_path)
    result = VisionInspectReadTool()._run("nonexistent.py")
    assert "not found" in result
