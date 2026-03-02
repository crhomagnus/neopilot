"""Tests for the tool registry — verify all tools are valid Claude API format."""

import pytest

from backend.app.services.tool_registry import get_teaching_tools, get_tool_names


class TestToolRegistry:
    """Validate tool definitions are correctly formatted for Claude API."""

    def test_tools_not_empty(self):
        tools = get_teaching_tools()
        assert len(tools) > 0

    def test_all_tools_have_required_fields(self):
        """Every tool must have name, description, and input_schema."""
        for tool in get_teaching_tools():
            assert "name" in tool, f"Tool missing 'name': {tool}"
            assert "description" in tool, f"Tool {tool.get('name')} missing 'description'"
            assert "input_schema" in tool, f"Tool {tool['name']} missing 'input_schema'"

    def test_input_schema_is_valid(self):
        """input_schema must be a JSON Schema object with type=object and properties."""
        for tool in get_teaching_tools():
            schema = tool["input_schema"]
            assert schema["type"] == "object", f"Tool {tool['name']}: type must be 'object'"
            assert "properties" in schema, f"Tool {tool['name']}: missing 'properties'"
            assert "required" in schema, f"Tool {tool['name']}: missing 'required'"

    def test_required_fields_exist_in_properties(self):
        """All 'required' fields must be defined in 'properties'."""
        for tool in get_teaching_tools():
            props = tool["input_schema"]["properties"]
            required = tool["input_schema"]["required"]
            for field in required:
                assert field in props, (
                    f"Tool {tool['name']}: required field '{field}' "
                    f"not in properties {list(props.keys())}"
                )

    def test_tool_names_are_unique(self):
        names = get_tool_names()
        assert len(names) == len(set(names)), f"Duplicate tool names: {names}"

    def test_expected_tools_exist(self):
        """Verify core teaching tools are registered."""
        names = set(get_tool_names())
        expected = {
            "click", "type_text", "hotkey", "mouse_move", "scroll", "drag",
            "wait", "request_screenshot",
            "overlay_arrow", "overlay_highlight", "overlay_text", "clear_overlays",
            "speak", "ask_student", "evaluate_action", "set_teaching_phase",
        }
        missing = expected - names
        assert not missing, f"Missing expected tools: {missing}"

    def test_tool_descriptions_are_non_empty(self):
        for tool in get_teaching_tools():
            assert len(tool["description"]) > 10, (
                f"Tool {tool['name']} has too short description"
            )

    def test_click_tool_schema(self):
        """Detailed validation of the click tool schema."""
        tools = {t["name"]: t for t in get_teaching_tools()}
        click = tools["click"]
        props = click["input_schema"]["properties"]
        assert "x" in props
        assert "y" in props
        assert props["x"]["type"] == "integer"
        assert props["y"]["type"] == "integer"
        assert "x" in click["input_schema"]["required"]
        assert "y" in click["input_schema"]["required"]
