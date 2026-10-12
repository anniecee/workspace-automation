"""Core Agent implementation."""

import logging
from typing import Any

from .config import config

logger = logging.getLogger(__name__)


class Agent:
    """Base Agent class."""

    def __init__(self, name: str = "{{project_name}}"):
        self.name = name
        self.env = config.APP_ENV

    def run(self, prompt: str) -> dict[str, Any]:
        """Process a user prompt and return a response dictionary."""
        logger.info(f"Agent '{self.name}' received prompt: {prompt}")
        # TODO: Implement agent logic, LLM calls, and tool usage
        return {
            "agent": self.name,
            "status": "success",
            "output": f"Processed: {prompt}",
        }
