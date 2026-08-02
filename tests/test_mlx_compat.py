import os
import unittest
from unittest.mock import patch

from helpers.llm_utils import (
    _parse_mlx_tool_calls,
    get_chat_model,
    get_domain_embedding_model,
    get_local_llm_backend,
    provider_configured,
)


class LocalBackendCompatibilityTests(unittest.TestCase):
    def test_ollama_remains_the_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_local_llm_backend(), "ollama")

    def test_mlx_is_opt_in_and_uses_its_own_configuration(self):
        env = {
            "LOCAL_LLM_BACKEND": "mlx",
            "MLX_BASE_URL": "http://127.0.0.1:8080/v1",
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(get_local_llm_backend(), "mlx")
            self.assertTrue(provider_configured("local"))

    def test_ollama_configuration_still_enables_local_provider(self):
        env = {
            "LOCAL_LLM_BACKEND": "ollama",
            "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertTrue(provider_configured("local"))


class MLXToolCallCompatibilityTests(unittest.TestCase):
    def test_plain_json_tool_call_is_normalized(self):
        calls = _parse_mlx_tool_calls(
            '{"name":"lookup_customer","parameters":{"customer_id":"C001"}}'
        )
        self.assertEqual(calls[0]["name"], "lookup_customer")
        self.assertEqual(calls[0]["args"], {"customer_id": "C001"})

    def test_non_tool_json_is_left_alone(self):
        self.assertEqual(_parse_mlx_tool_calls('{"answer": 42}'), [])

    def test_plain_text_is_left_alone(self):
        self.assertEqual(_parse_mlx_tool_calls("Hello from MLX"), [])


class MLXModelRequestCompatibilityTests(unittest.TestCase):
    @patch("helpers.llm_utils.is_mlx_available", return_value=True)
    @patch("helpers.llm_utils.MLXChatOpenAI")
    def test_gemma_4_disables_hidden_thinking(self, chat_model, _available):
        with patch.dict(
            os.environ,
            {
                "LOCAL_LLM_BACKEND": "mlx",
                "MLX_BASE_URL": "http://127.0.0.1:8080/v1",
            },
            clear=True,
        ):
            get_chat_model(
                "mlx-community/gemma-4-26b-a4b-it-4bit",
                provider="local",
            )

        self.assertEqual(
            chat_model.call_args.kwargs["extra_body"],
            {"chat_template_kwargs": {"enable_thinking": False}},
        )

    @patch("helpers.llm_utils.is_mlx_available", return_value=True)
    @patch("helpers.llm_utils.MLXChatOpenAI")
    def test_other_mlx_models_keep_their_request_shape(self, chat_model, _available):
        with patch.dict(
            os.environ,
            {
                "LOCAL_LLM_BACKEND": "mlx",
                "MLX_BASE_URL": "http://127.0.0.1:8080/v1",
            },
            clear=True,
        ):
            get_chat_model(
                "mlx-community/Llama-3.2-3B-Instruct-4bit",
                provider="local",
            )

        self.assertNotIn("extra_body", chat_model.call_args.kwargs)


class MLXEmbeddingCompatibilityTests(unittest.TestCase):
    @patch("helpers.llm_utils.resolve_embedding_provider", return_value="local")
    def test_mlx_uses_its_local_sentence_transformer_model(self, _resolve):
        with patch.dict(
            os.environ,
            {
                "LOCAL_LLM_BACKEND": "mlx",
                "MLX_EMBEDDING_MODEL": "sentence-transformers/test-model",
            },
            clear=True,
        ):
            self.assertEqual(
                get_domain_embedding_model({}),
                "sentence-transformers/test-model",
            )

    @patch("helpers.llm_utils.resolve_embedding_provider", return_value="local")
    def test_ollama_keeps_its_existing_embedding_model(self, _resolve):
        with patch.dict(
            os.environ,
            {
                "LOCAL_LLM_BACKEND": "ollama",
                "OLLAMA_EMBEDDING_MODEL": "nomic-embed-text",
            },
            clear=True,
        ):
            self.assertEqual(
                get_domain_embedding_model({}),
                "nomic-embed-text",
            )


if __name__ == "__main__":
    unittest.main()
