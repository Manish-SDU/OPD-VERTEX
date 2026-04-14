"""MongoDB seed helpers for prompt bootstrap."""

from __future__ import annotations

from app.infrastructure.bootstrap.prompt_seed import PromptBootstrapSeeder
from app.infrastructure.db.mongo.connection import get_database


def seed_llm_prompts() -> None:
    PromptBootstrapSeeder(get_database()).seed()


if __name__ == "__main__":
    seed_llm_prompts()
    print("Prompt bootstrap seed completed.")
