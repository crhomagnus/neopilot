"""
NeoPilot Tool Registry
Defines tools that Claude can call during teaching sessions.
Each tool maps to an action the thin client can execute.
"""

from __future__ import annotations

from typing import Any


def get_teaching_tools() -> list[dict[str, Any]]:
    """
    Returns the tool definitions for Claude's tool-use feature.
    These follow the Anthropic tool-use schema.
    """
    return [
        # ─── ACI (Agent-Computer Interface) ───────────────────────────────
        {
            "name": "click",
            "description": (
                "Click at specific screen coordinates. Use this to interact with UI elements "
                "like buttons, menus, tabs, and form fields. Always verify the target element "
                "is visible in the screenshot before clicking."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate (pixels from left)"},
                    "y": {"type": "integer", "description": "Y coordinate (pixels from top)"},
                    "button": {
                        "type": "string",
                        "enum": ["left", "right", "middle"],
                        "default": "left",
                        "description": "Mouse button to click",
                    },
                    "clicks": {
                        "type": "integer",
                        "default": 1,
                        "description": "Number of clicks (1=single, 2=double)",
                    },
                },
                "required": ["x", "y"],
            },
        },
        {
            "name": "type_text",
            "description": (
                "Type text using the keyboard. Use for filling form fields, writing in editors, "
                "entering commands, etc. The target input must be focused first."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to type"},
                    "delay_ms": {
                        "type": "integer",
                        "default": 20,
                        "description": "Delay between keystrokes in milliseconds",
                    },
                },
                "required": ["text"],
            },
        },
        {
            "name": "hotkey",
            "description": (
                "Press a keyboard shortcut. Keys are specified as a list "
                "(e.g., ['ctrl', 's'] for save, ['alt', 'F4'] for close)."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of keys to press simultaneously",
                    },
                },
                "required": ["keys"],
            },
        },
        {
            "name": "mouse_move",
            "description": "Move the mouse cursor to specific coordinates without clicking.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "Target X coordinate"},
                    "y": {"type": "integer", "description": "Target Y coordinate"},
                },
                "required": ["x", "y"],
            },
        },
        {
            "name": "scroll",
            "description": "Scroll at the current mouse position or specified coordinates.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["up", "down", "left", "right"],
                    },
                    "amount": {
                        "type": "integer",
                        "default": 3,
                        "description": "Number of scroll steps",
                    },
                    "x": {"type": "integer", "description": "Optional X coordinate"},
                    "y": {"type": "integer", "description": "Optional Y coordinate"},
                },
                "required": ["direction"],
            },
        },
        {
            "name": "drag",
            "description": "Click and drag from one position to another.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "start_x": {"type": "integer"},
                    "start_y": {"type": "integer"},
                    "end_x": {"type": "integer"},
                    "end_y": {"type": "integer"},
                    "button": {
                        "type": "string",
                        "enum": ["left", "right"],
                        "default": "left",
                    },
                },
                "required": ["start_x", "start_y", "end_x", "end_y"],
            },
        },
        {
            "name": "wait",
            "description": "Wait for a specified duration before the next action.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "duration_ms": {
                        "type": "integer",
                        "description": "Duration to wait in milliseconds",
                        "default": 1000,
                    },
                },
                "required": [],
            },
        },
        # ─── Screenshot Request ───────────────────────────────────────────
        {
            "name": "request_screenshot",
            "description": (
                "Request a fresh screenshot from the client. Use this when you need to see "
                "the current state of the screen after an action, or when the last screenshot "
                "is stale. This pauses the action sequence until the client sends the new image."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "object",
                        "description": "Optional region to capture (x, y, width, height)",
                        "properties": {
                            "x": {"type": "integer"},
                            "y": {"type": "integer"},
                            "width": {"type": "integer"},
                            "height": {"type": "integer"},
                        },
                    },
                },
                "required": [],
            },
        },
        # ─── Teaching Overlay ─────────────────────────────────────────────
        {
            "name": "overlay_arrow",
            "description": (
                "Draw an arrow on the screen to point the student to a UI element. "
                "Use to guide attention before explaining or asking the student to click."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "start_x": {"type": "integer"},
                    "start_y": {"type": "integer"},
                    "end_x": {"type": "integer", "description": "Arrow tip X (points to target)"},
                    "end_y": {"type": "integer", "description": "Arrow tip Y (points to target)"},
                    "color": {"type": "string", "default": "#FF4444"},
                    "label": {
                        "type": "string",
                        "description": "Optional text label near the arrow",
                    },
                    "duration_ms": {"type": "integer", "default": 5000},
                },
                "required": ["start_x", "start_y", "end_x", "end_y"],
            },
        },
        {
            "name": "overlay_highlight",
            "description": (
                "Highlight a rectangular region on screen to draw the student's attention. "
                "Use blink mode for actions, solid mode for reference areas."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                    "width": {"type": "integer"},
                    "height": {"type": "integer"},
                    "mode": {
                        "type": "string",
                        "enum": ["blink", "solid", "pulse", "fade"],
                        "default": "blink",
                    },
                    "color": {"type": "string", "default": "#44AAFF"},
                    "duration_ms": {"type": "integer", "default": 4000},
                },
                "required": ["x", "y", "width", "height"],
            },
        },
        {
            "name": "overlay_text",
            "description": (
                "Show a text bubble on screen with an instruction or explanation for the student. "
                "Position it near the relevant UI element but not overlapping it."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Instruction text to display"},
                    "x": {"type": "integer", "description": "X position of the text bubble"},
                    "y": {"type": "integer", "description": "Y position of the text bubble"},
                    "font_size": {"type": "integer", "default": 16},
                    "background_color": {"type": "string", "default": "#1A1A2E"},
                    "text_color": {"type": "string", "default": "#FFFFFF"},
                    "duration_ms": {"type": "integer", "default": 6000},
                },
                "required": ["text", "x", "y"],
            },
        },
        {
            "name": "clear_overlays",
            "description": "Remove all active overlays from the screen.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        # ─── Teaching / Interaction ───────────────────────────────────────
        {
            "name": "speak",
            "description": (
                "Narrate text aloud via text-to-speech. Use for verbal explanations "
                "while the student watches the screen."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to speak aloud"},
                    "language": {"type": "string", "default": "pt-BR"},
                    "wait_for_completion": {"type": "boolean", "default": True},
                },
                "required": ["text"],
            },
        },
        {
            "name": "ask_student",
            "description": (
                "Ask the student a question and wait for their response (text or voice). "
                "Use to check understanding, confirm they're ready for the next step, "
                "or get information about their goal."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Question to ask the student"},
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional multiple-choice options",
                    },
                    "timeout_seconds": {"type": "integer", "default": 60},
                },
                "required": ["question"],
            },
        },
        {
            "name": "evaluate_action",
            "description": (
                "Evaluate whether the student correctly performed the expected action. "
                "Compare the before/after screenshots and check if the expected change occurred."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "expected_change": {
                        "type": "string",
                        "description": "Description of what should have changed",
                    },
                    "success_criteria": {
                        "type": "string",
                        "description": "How to determine if the action was correct",
                    },
                },
                "required": ["expected_change"],
            },
        },
        {
            "name": "set_teaching_phase",
            "description": (
                "Change the current teaching phase. "
                "demo = teacher demonstrates, exercise = student practices with guidance, "
                "assessment = student works independently, adaptive = customized remediation."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "phase": {
                        "type": "string",
                        "enum": ["demo", "exercise", "assessment", "adaptive_path"],
                    },
                },
                "required": ["phase"],
            },
        },
    ]


def get_tool_names() -> list[str]:
    """Get the list of all registered tool names."""
    return [t["name"] for t in get_teaching_tools()]
