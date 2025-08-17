from silhouette_core.alignment_engine import (
    load_persona_config,
    violates_alignment,
    format_response,
)

def test_violates_alignment_true():
    deny_list = ["malicious", "deceptive"]
    assert violates_alignment("Perform malicious action", deny_list)

def test_violates_alignment_false():
    deny_list = ["malicious", "deceptive"]
    assert not violates_alignment("Hello world", deny_list)

def test_format_response_friendly():
    assert format_response("hi there", "friendly").startswith("😊")

def test_load_persona_config():
    config = load_persona_config("docs/alignment_kernel/persona.dsl")
    assert config["tone"]["style"] == "neutral"
    deny = config["limits"]["deny_on"]
    assert "malicious" in deny
    assert "disallowed" in deny
