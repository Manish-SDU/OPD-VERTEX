"""Application startup bootstrap orchestration."""

from __future__ import annotations

from logging import getLogger

from app.core.config import Settings
from app.infrastructure.bootstrap.mock_consultation_seed import (
    MockConsultationBootstrapSeeder,
)
from app.infrastructure.bootstrap.email_template_seed import (
    EmailTemplateBootstrapSeeder,
)
from app.infrastructure.bootstrap.prompt_seed import PromptBootstrapSeeder
from app.infrastructure.db.mongo.connection import get_database
from app.infrastructure.db.sql.connection import get_session

logger = getLogger("opd_vertex.infrastructure.bootstrap")


class StartupBootstrapper:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def run(self) -> None:
        if self.settings.use_mock_adapters:
            logger.info(
                "Startup bootstrap skipped because USE_MOCK_ADAPTERS is enabled."
            )
            return

        mongo_db = get_database()
        sql_session = get_session()

        try:
            if self.settings.seed_prompts_on_startup:
                PromptBootstrapSeeder(mongo_db).seed()
                EmailTemplateBootstrapSeeder(mongo_db).seed()
            else:
                logger.info("Prompt bootstrap skipped by environment configuration.")

            if self.settings.seed_mock_consultations_on_startup:
                MockConsultationBootstrapSeeder(sql_session, mongo_db).seed()
            else:
                logger.info(
                    "Mock consultation bootstrap skipped by environment configuration."
                )
        finally:
            sql_session.close()
