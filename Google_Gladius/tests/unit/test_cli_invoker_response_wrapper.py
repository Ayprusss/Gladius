"""Unit tests for ClaudeClient response wrapper handling"""
import pytest
import json
from src.claude_client.cli_invoker import ClaudeClient


class TestClaudeClientResponseWrapper:
    """Test ClaudeClient handling of various response formats"""

    def test_parse_flat_json(self):
        """Test parsing flat JSON (backward compatibility)"""
        client = ClaudeClient()
        output = json.dumps({
            "summary": "Test summary",
            "plan": ["step 1", "step 2"]
        })

        result = client._parse_json_output(output)

        assert result["summary"] == "Test summary"
        assert result["plan"] == ["step 1", "step 2"]

    def test_parse_wrapper_with_content_list(self):
        """Test parsing Claude CLI wrapper format with content list"""
        client = ClaudeClient()

        # Simulate actual Claude CLI response wrapper
        wrapper = {
            "type": "result",
            "subtype": "tool_use",
            "id": "4cc0-b22e-8cc503412afb",
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "summary": "Test summary",
                        "plan": ["step 1", "step 2"],
                        "files_to_change": [],
                        "test_plan": [],
                        "assumptions": [],
                        "risks": []
                    })
                }
            ]
        }

        output = json.dumps(wrapper)
        result = client._parse_json_output(output)

        assert result["summary"] == "Test summary"
        assert result["plan"] == ["step 1", "step 2"]

    def test_parse_wrapper_with_string_content(self):
        """Test parsing wrapper with string content"""
        client = ClaudeClient()

        wrapper = {
            "type": "result",
            "content": json.dumps({
                "summary": "Test",
                "plan": []
            })
        }

        output = json.dumps(wrapper)
        result = client._parse_json_output(output)

        assert result["summary"] == "Test"

    def test_parse_wrapper_with_dict_content(self):
        """Test parsing wrapper with dict content"""
        client = ClaudeClient()

        wrapper = {
            "type": "result",
            "content": {
                "summary": "Test",
                "plan": []
            }
        }

        output = json.dumps(wrapper)
        result = client._parse_json_output(output)

        assert result["summary"] == "Test"

    def test_parse_wrapper_with_data_field(self):
        """Test parsing wrapper with 'data' field"""
        client = ClaudeClient()

        wrapper = {
            "type": "result",
            "data": {
                "summary": "Test",
                "plan": []
            }
        }

        output = json.dumps(wrapper)
        result = client._parse_json_output(output)

        assert result["summary"] == "Test"

    def test_parse_markdown_wrapped_json(self):
        """Test parsing JSON from markdown code block"""
        client = ClaudeClient()

        output = """```json
{
    "summary": "Test",
    "plan": []
}
```"""

        result = client._parse_json_output(output)
        assert result["summary"] == "Test"

    def test_parse_mixed_text_and_json(self):
        """Test extracting JSON from mixed text"""
        client = ClaudeClient()

        output = """Some text before
{
    "summary": "Test",
    "plan": []
}
Some text after"""

        result = client._parse_json_output(output)
        assert result["summary"] == "Test"

    def test_parse_nested_content_items(self):
        """Test parsing nested content items (complex wrapper)"""
        client = ClaudeClient()

        wrapper = {
            "type": "result",
            "content": [
                {"type": "thinking", "text": "Internal reasoning..."},
                {
                    "type": "text",
                    "text": json.dumps({
                        "summary": "Actual result",
                        "plan": ["step"]
                    })
                }
            ]
        }

        output = json.dumps(wrapper)
        result = client._parse_json_output(output)

        assert result["summary"] == "Actual result"

    def test_invalid_json_raises(self):
        """Test that invalid JSON raises JSONDecodeError"""
        client = ClaudeClient()

        with pytest.raises(json.JSONDecodeError):
            client._parse_json_output("not valid json at all")

    def test_wrapper_without_valid_content(self):
        """Test wrapper with no valid JSON content"""
        client = ClaudeClient()

        # Wrapper with content but no valid JSON
        wrapper = {
            "type": "result",
            "content": [
                {"type": "text", "text": "Just plain text"}
            ]
        }

        output = json.dumps(wrapper)

        # Should return the wrapper itself since no nested JSON found
        result = client._parse_json_output(output)
        assert result["type"] == "result"

    def test_empty_wrapper(self):
        """Test empty wrapper structure"""
        client = ClaudeClient()

        wrapper = {
            "type": "result",
            "content": []
        }

        output = json.dumps(wrapper)
        result = client._parse_json_output(output)

        # Should return wrapper as-is
        assert result["type"] == "result"
        assert result["content"] == []

    def test_non_result_type_passthrough(self):
        """Test that non-result types are passed through"""
        client = ClaudeClient()

        data = {
            "type": "error",
            "message": "Something failed"
        }

        output = json.dumps(data)
        result = client._parse_json_output(output)

        assert result["type"] == "error"
        assert result["message"] == "Something failed"
