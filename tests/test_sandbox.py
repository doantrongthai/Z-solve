from datamate.sandbox import execute_sandboxed_pandas, validate_python_code


def test_validate_code_safe() -> None:
    safe_code = "result = dfs['table1']['col'].sum()"
    is_valid, error = validate_python_code(safe_code)
    assert is_valid is True
    assert error is None


def test_validate_code_blocked_import() -> None:
    malicious_code = "import os\nos.system('echo hi')"
    is_valid, error = validate_python_code(malicious_code)
    assert is_valid is False
    assert "Import" in str(error)


def test_validate_code_blocked_dunder() -> None:
    dunder_code = "result = __builtins__"
    is_valid, error = validate_python_code(dunder_code)
    assert is_valid is False


def test_execute_sandboxed_pandas_success() -> None:
    code = "result = int(dfs['sales']['amount'].sum())"
    context = {
        "tables": {"sales": [{"amount": 100}, {"amount": 200}]},
        "as_of_date": "2026-03-04",
        "calendar": [],
    }
    result = execute_sandboxed_pandas(code, context)
    assert result.is_success is True
    assert result.output_value == 300


def test_execute_sandboxed_pandas_runtime_error() -> None:
    code = "result = dfs['non_existent_table']['col'].sum()"
    context = {"tables": {}, "as_of_date": "2026-03-04", "calendar": []}
    result = execute_sandboxed_pandas(code, context)
    assert result.is_success is False
    assert "KeyError" in str(result.error_message)

