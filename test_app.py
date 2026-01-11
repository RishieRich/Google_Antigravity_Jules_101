
import unittest
from unittest.mock import MagicMock, patch
import app

class TestApp(unittest.TestCase):
    def setUp(self):
        # Reset the global client before each test
        app._GROQ_CLIENT = None

    @patch('app.Groq')
    @patch.dict(app.os.environ, {"GROQ_API_KEY": "fake_key"})
    def test_client_singleton(self, mock_groq):
        """Test that _client returns a singleton instance."""
        client1 = app._client()
        client2 = app._client()
        self.assertIs(client1, client2)
        mock_groq.assert_called_once()

    @patch('app.Groq')
    def test_client_missing_key(self, mock_groq):
        """Test that _client raises RuntimeError if GROQ_API_KEY is missing."""
        with patch.dict(app.os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                app._client()

    @patch('app._client')
    def test_call_groq(self, mock_get_client):
        """Test call_groq function."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "Response content"
        mock_client.chat.completions.create.return_value = mock_resp

        messages = [{"role": "user", "content": "hi"}]
        result = app.call_groq(messages, "model-x", max_tokens=100)

        self.assertEqual(result, "Response content")
        mock_client.chat.completions.create.assert_called_with(
            model="model-x",
            messages=messages,
            temperature=0.4, # default
            max_tokens=100
        )

    @patch('app.call_groq')
    def test_robust_chat_success(self, mock_call_groq):
        """Test robust_chat success on first try."""
        mock_call_groq.return_value = "Success"

        text, model, latency = app.robust_chat([], max_tokens=500)

        self.assertEqual(text, "Success")
        self.assertEqual(model, app.DEFAULT_MODEL)
        mock_call_groq.assert_called_with([], model=app.DEFAULT_MODEL, temperature=0.4, max_tokens=500)

    @patch('app.call_groq')
    def test_robust_chat_fallback(self, mock_call_groq):
        """Test robust_chat fallback mechanism."""
        # First call raises Exception, second succeeds
        mock_call_groq.side_effect = [Exception("Fail"), "Success"]

        text, model, latency = app.robust_chat([], max_tokens=500)

        self.assertEqual(text, "Success")
        self.assertEqual(model, app.FALLBACK_MODELS[0])
        self.assertEqual(mock_call_groq.call_count, 2)
        # Check calls
        calls = mock_call_groq.call_args_list
        self.assertEqual(calls[0].kwargs['model'], app.DEFAULT_MODEL)
        self.assertEqual(calls[1].kwargs['model'], app.FALLBACK_MODELS[0])

    @patch('app.robust_chat')
    def test_run_decision_arena(self, mock_robust_chat):
        """Test run_decision_arena logic."""
        mock_robust_chat.return_value = ("Mocked Response", "model-x", 0.1)

        output, meta = app.run_decision_arena("My problem", "Balanced", 3)

        self.assertIn("Builder", output)
        self.assertIn("Challenger", output)
        self.assertIn("Judge", output)
        self.assertIn("Mocked Response", output)

        # Verify max_tokens calculation and propagation
        # depth 3 -> 650 + 3*150 = 1100
        expected_max_tokens = 1100

        # robust_chat is called 3 times (Builder, Challenger, Judge)
        self.assertEqual(mock_robust_chat.call_count, 3)
        for call in mock_robust_chat.call_args_list:
            self.assertEqual(call.kwargs['max_tokens'], expected_max_tokens)

if __name__ == '__main__':
    unittest.main()
