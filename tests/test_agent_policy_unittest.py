from __future__ import annotations

import unittest

from app.agent_policy import (
    AGENT_INSTRUCTIONS,
    AGENT_TOOLS,
    AgentConfigurationError,
    validate_agent_steps,
    validate_tool_arguments,
)


class AgentPolicyTests(unittest.TestCase):
    def test_tools_are_strict_and_read_only(self) -> None:
        self.assertEqual(
            {tool["name"] for tool in AGENT_TOOLS},
            {"get_event_context", "get_incident_report"},
        )
        for tool in AGENT_TOOLS:
            parameters = tool["parameters"]
            self.assertEqual(tool["type"], "function")
            self.assertIs(tool["strict"], True)
            self.assertIs(parameters["additionalProperties"], False)
            self.assertEqual(
                set(parameters["required"]), set(parameters["properties"])
            )
            self.assertIn("Read-only", tool["description"])

    def test_prompt_marks_logs_untrusted_and_forbids_execution(self) -> None:
        normalized_prompt = " ".join(AGENT_INSTRUCTIONS.split())
        self.assertIn("untrusted data", normalized_prompt)
        self.assertIn(
            "Do not claim that a remediation action was executed",
            normalized_prompt,
        )
        self.assertIn("human approval", normalized_prompt)

    def test_tool_arguments_cannot_cross_incident_scope(self) -> None:
        validate_tool_arguments(
            {"event_id": "event-1"},
            expected_key="event_id",
            expected_value="event-1",
        )
        with self.assertRaises(ValueError):
            validate_tool_arguments(
                {"event_id": "event-2"},
                expected_key="event_id",
                expected_value="event-1",
            )
        with self.assertRaises(ValueError):
            validate_tool_arguments(
                {"event_id": "event-1", "extra": "not-allowed"},
                expected_key="event_id",
                expected_value="event-1",
            )

    def test_step_limit_has_hard_bounds(self) -> None:
        validate_agent_steps(1)
        validate_agent_steps(8)
        for invalid in (0, 9):
            with self.assertRaises(AgentConfigurationError):
                validate_agent_steps(invalid)


if __name__ == "__main__":
    unittest.main()
