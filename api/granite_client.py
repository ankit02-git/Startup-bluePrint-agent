"""
IBM Granite client — reads credentials from environment variables.
On Vercel these are set in the project dashboard (Settings > Environment Variables).
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

WATSONX_API_KEY   = os.getenv("WATSONX_API_KEY", "")
WATSONX_URL       = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "")
GRANITE_MODEL_ID  = os.getenv("GRANITE_MODEL_ID", "ibm/granite-4-h-small")


class GraniteClient:
    def __init__(self):
        self._model = None

    def _get_model(self):
        if self._model is not None:
            return self._model

        if not WATSONX_API_KEY or not WATSONX_PROJECT_ID:
            raise EnvironmentError(
                "WATSONX_API_KEY and WATSONX_PROJECT_ID must be set as "
                "Vercel environment variables."
            )

        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference

        credentials = Credentials(url=WATSONX_URL, api_key=WATSONX_API_KEY)
        params = {"max_tokens": 1500, "temperature": 0.7}

        self._model = ModelInference(
            model_id=GRANITE_MODEL_ID,
            credentials=credentials,
            project_id=WATSONX_PROJECT_ID,
            params=params,
        )
        logger.info("IBM Granite model initialized: %s", GRANITE_MODEL_ID)
        return self._model

    def generate(self, prompt: str, max_tokens: int = 1500) -> str:
        """Chat completion with 4-attempt retry on 429 rate limits."""
        import time
        model = self._get_model()
        messages = [{"role": "user", "content": prompt}]
        last_exc = None

        for attempt in range(4):
            try:
                response = model.chat(messages=messages)
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
                logger.error("IBM Granite error: %s", e)
                raise RuntimeError(f"IBM Granite failed: {e}") from e

        raise RuntimeError(f"IBM Granite rate limit exhausted: {last_exc}")

    def is_configured(self) -> bool:
        return bool(WATSONX_API_KEY and WATSONX_PROJECT_ID)


_granite_client: Optional[GraniteClient] = None


def get_granite_client() -> GraniteClient:
    global _granite_client
    if _granite_client is None:
        _granite_client = GraniteClient()
    return _granite_client
