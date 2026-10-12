"""Entrypoint for {{project_name}}."""

import logging
import sys

from .agent import Agent
from .config import config

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main() -> None:
    """Run the agent."""
    agent = Agent()
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Hello world!"
    result = agent.run(prompt)
    print(result)


if __name__ == "__main__":
    main()
