from config.loader import get_crew_model, get_agent_model, get_target_repo


# ── get_crew_model ─────────────────────────────────────────────────────────────

def test_crew_model_returns_configured_value():
    cfg = {"crew_models": {"default": "qwen2.5:7b"}, "llm_fallback": {"model": "llama3.1:8b"}}
    assert get_crew_model(cfg, "default") == "qwen2.5:7b"

def test_crew_model_falls_back_to_llm_fallback():
    cfg = {"crew_models": {}, "llm_fallback": {"model": "llama3.1:8b"}}
    assert get_crew_model(cfg, "unknown") == "llama3.1:8b"

def test_crew_model_falls_back_to_hardcoded_default_when_config_empty():
    assert get_crew_model({}, "any") == "llama3.1:8b"

def test_crew_model_falls_back_to_hardcoded_default_when_fallback_key_missing():
    assert get_crew_model({"crew_models": {}}, "missing") == "llama3.1:8b"


# ── get_agent_model ────────────────────────────────────────────────────────────

def test_agent_model_returns_configured_value():
    cfg = {"agent_models": {"builder": "qwen2.5-coder:7b"}, "llm_fallback": {"model": "llama3.1:8b"}}
    assert get_agent_model(cfg, "builder") == "qwen2.5-coder:7b"

def test_agent_model_falls_back_to_llm_fallback():
    cfg = {"llm_fallback": {"model": "llama3.1:8b"}}
    assert get_agent_model(cfg, "nonexistent") == "llama3.1:8b"

def test_agent_model_falls_back_to_hardcoded_default_when_config_empty():
    assert get_agent_model({}, "any") == "llama3.1:8b"


# ── get_target_repo ────────────────────────────────────────────────────────────

def test_target_repo_none_when_not_set():
    assert get_target_repo({}) is None

def test_target_repo_resolves_runtime_override(tmp_path):
    result = get_target_repo({"_target_repo": str(tmp_path)})
    assert result == str(tmp_path.resolve())

def test_target_repo_resolves_yaml_config(tmp_path):
    result = get_target_repo({"crew": {"target_repo": str(tmp_path)}})
    assert result == str(tmp_path.resolve())

def test_target_repo_runtime_takes_priority_over_yaml(tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    cfg = {"_target_repo": str(tmp_path), "crew": {"target_repo": str(other)}}
    assert get_target_repo(cfg) == str(tmp_path.resolve())

def test_target_repo_none_when_yaml_value_is_null():
    assert get_target_repo({"crew": {"target_repo": None}}) is None
