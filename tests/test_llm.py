from datamate.llm import LLMConfig, LocalLLMClient


def test_llm_config_defaults() -> None:
    config = LLMConfig()
    assert config.model_name == "Qwen/Qwen2.5-Coder-7B-Instruct"
    assert config.load_in_4bit is False
    assert config.temperature <= 0.05


def test_extract_python_code_from_markdown() -> None:
    client = LocalLLMClient()
    text = "Here is the code:\n```python\nresult = 42\n```\nHope it helps."
    extracted = client.extract_python_code(text)
    assert extracted == "result = 42"


def test_extract_python_code_raw() -> None:
    client = LocalLLMClient()
    text = "result = 100\nprint(result)"
    extracted = client.extract_python_code(text)
    assert "result = 100" in extracted

