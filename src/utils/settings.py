from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AibaSettings(BaseSettings):
    """Central configuration for AIBA, loaded from .env and environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Gemini / LLM ---
    gemini_api_key: str = Field(
        default="",
        validation_alias="GEMINI_API_KEY",
        description="Google Gemini API key (from Google AI Studio).",
    )

    gemini_main_model: str = Field(
        default="gemini-3.5-flash",
        validation_alias="GEMINI_MAIN_MODEL",
        description="Gemini model to use for the main agent (e.g., gemini-3.5-flash).",
    )

    gemini_sub_model: str = Field(
        default="gemini-3.1-flash-lite",
        validation_alias="GEMINI_SUB_MODEL",
        description="Gemini model to use for sub-agents (e.g., gemini-3.1-flash-lite).",
    )

    # --- Observability ---
    logfire_enabled: bool = Field(
        default=False,
        validation_alias="LOGFIRE_ENABLED",
        description="Enable Logfire observability.",
    )

    logfire_token: str = Field(
        default="",
        validation_alias="LOGFIRE_TOKEN",
        description="Logfire API token (required if logfire_enabled is True).",
    )

    # --- Sub-Agent Orchestration ---
    max_concurrent_sub_agents: int = Field(
        default=5,
        ge=1,
        le=50,
        validation_alias="MAX_CONCURRENT_SUB_AGENTS",
        description="Maximum number of sub-agents to run concurrently.",
    )

    request_timeout_seconds: int = Field(
        default=60,
        ge=10,
        validation_alias="REQUEST_TIMEOUT_SECONDS",
        description="Timeout in seconds for LLM requests and tool calls.",
    )

    # --- Playwright Browser ---
    playwright_headless: bool = Field(
        default=True,
        validation_alias="PLAYWRIGHT_HEADLESS",
        description="Run Chromium in headless mode.",
    )

    # --- Web Search ---
    web_search_engine: str = Field(
        default="duckduckgo",
        validation_alias="WEB_SEARCH_ENGINE",
        description=(
            "Web search backend. 'duckduckgo' (free, no quota) or 'native' "
            "(Gemini's built-in Google Search — 5,000 prompts/month free, "
            "then $14/1K queries)."
        ),
    )

    # --- SMTP / Email ---
    smtp_host: str = Field(
        default="smtp.gmail.com",
        validation_alias="SMTP_HOST",
        description="SMTP server hostname.",
    )
    smtp_port: int = Field(
        default=587,
        validation_alias="SMTP_PORT",
        description="SMTP server port (587 for TLS, 465 for SSL).",
    )
    smtp_username: str = Field(
        default="",
        validation_alias="SMTP_USERNAME",
        description="SMTP login username (Gmail address).",
    )
    smtp_password: str = Field(
        default="",
        validation_alias="SMTP_PASSWORD",
        description="SMTP password (Gmail App Password).",
    )
    sender_email: str = Field(
        default="",
        validation_alias="SENDER_EMAIL",
        description="Default From: address for outgoing emails.",
    )

    # --- User Profile ---
    user_profile: str = Field(
        default="",
        validation_alias="USER_PROFILE",
        description="Your skills, experience, and background — used by templates like job_search to tailor results.",
    )

    # --- Guardrails (pydantic-ai-shields) ---
    guardrails_enabled: bool = Field(
        default=True,
        validation_alias="GUARDRAILS_ENABLED",
        description="Enable guardrails: CostTracking, ToolGuard, SecretRedaction, InputGuard.",
    )
    cost_budget_usd: float = Field(
        default=1.0,
        ge=0.01,
        validation_alias="COST_BUDGET_USD",
        description="Maximum USD budget per agent run for CostTracking guardrail.",
    )
    require_approval_for: list[str] = Field(
        default=[],
        validation_alias="REQUIRE_APPROVAL_FOR",
        description="Tool names that require human approval via ToolGuard (comma-separated in .env).",
    )
