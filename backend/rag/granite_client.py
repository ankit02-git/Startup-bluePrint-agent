"""
IBM Granite LLM client via ibm-watsonx-ai SDK.
Handles authentication and text generation with IBM Granite models.
"""
import os
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env from the backend directory (works regardless of cwd)
_ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

logger = logging.getLogger(__name__)

WATSONX_API_KEY = os.getenv("WATSONX_API_KEY", "")
WATSONX_URL = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "")
GRANITE_MODEL_ID = os.getenv("GRANITE_MODEL_ID", "ibm/granite-13b-instruct-v2")


def _build_generate_params() -> dict:
    return {
        "decoding_method": "greedy",
        "max_new_tokens": 1500,
        "min_new_tokens": 100,
        "stop_sequences": ["</s>", "Human:", "User:"],
        "repetition_penalty": 1.1,
        "temperature": 0.7,
    }


class GraniteClient:
    """Thin wrapper around ibm-watsonx-ai for IBM Granite text generation."""

    def __init__(self):
        self._model = None

    def _get_model(self):
        if self._model is not None:
            return self._model

        if not WATSONX_API_KEY or not WATSONX_PROJECT_ID:
            raise EnvironmentError(
                "WATSONX_API_KEY and WATSONX_PROJECT_ID must be set in environment variables. "
                "Please copy .env.example to .env and fill in your IBM Cloud credentials."
            )

        try:
            from ibm_watsonx_ai import Credentials
            from ibm_watsonx_ai.foundation_models import ModelInference

            credentials = Credentials(
                url=WATSONX_URL,
                api_key=WATSONX_API_KEY,
            )

            # Use chat completions params — correct API for granite-4-h-small
            params = {
                "max_tokens": 1500,
                "temperature": 0.7,
            }

            self._model = ModelInference(
                model_id=GRANITE_MODEL_ID,
                credentials=credentials,
                project_id=WATSONX_PROJECT_ID,
                params=params,
            )
            logger.info("IBM Granite model initialized: %s", GRANITE_MODEL_ID)
        except ImportError as e:
            raise ImportError(
                "ibm-watsonx-ai is not installed. Run: pip install ibm-watsonx-ai"
            ) from e

        return self._model

    def generate(self, prompt: str, max_tokens: int = 1500) -> str:
        """Generate text using IBM Granite chat API. Retries on 429 rate-limit errors."""
        import time
        model = self._get_model()
        messages = [{"role": "user", "content": prompt}]
        last_exc = None
        for attempt in range(4):
            try:
                response = model.chat(messages=messages)
                # chat() returns a dict with choices
                if isinstance(response, dict):
                    choices = response.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "").strip()
                return str(response).strip()
            except Exception as e:
                last_exc = e
                err_str = str(e)
                if "429" in err_str or "consumption_limit" in err_str:
                    wait = 15 * (attempt + 1)
                    logger.warning("Rate limited (attempt %d). Retrying in %ds...", attempt + 1, wait)
                    time.sleep(wait)
                    continue
                logger.error("IBM Granite generation error: %s", e)
                raise RuntimeError(f"Failed to generate response from IBM Granite: {e}") from e
        raise RuntimeError(f"IBM Granite rate limit — all retries exhausted: {last_exc}")

    def is_configured(self) -> bool:
        """Check if IBM watsonx credentials are configured."""
        return bool(WATSONX_API_KEY and WATSONX_PROJECT_ID)


# Singleton
_granite_client: Optional[GraniteClient] = None


def get_granite_client() -> GraniteClient:
    global _granite_client
    if _granite_client is None:
        _granite_client = GraniteClient()
    return _granite_client
