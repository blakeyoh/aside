import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Mock UI modules BEFORE importing anything that uses them
mock_ctk = MagicMock()
mock_tk = MagicMock()
sys.modules["customtkinter"] = mock_ctk
sys.modules["tkinter"] = mock_tk

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from aside import permissions
from aside.ui import settings
from aside.config import DICTIONARY_FILE

class TestSecurityFix(unittest.TestCase):

    @patch("webbrowser.open")
    def test_open_privacy_pane_uses_webbrowser(self, mock_open):
        permissions.open_privacy_pane("microphone")
        expected_url = "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"
        mock_open.assert_called_once_with(expected_url)

    @patch("webbrowser.open")
    def test_settings_lambda_uses_webbrowser(self, mock_open):
        # We've mocked customtkinter.CTkButton as part of mock_ctk
        mock_app = MagicMock()
        mock_app.cfg = {
            "model_size": "base",
            "language": "en",
            "hotkey": {"modifiers": ["ctrl"], "trigger": "space"},
            "toggle_hotkey": None,
            "punctuation": {}
        }
        mock_frame = MagicMock()

        # We need to make sure CTkButton returns something that doesn't crash
        # and we can capture its call
        settings.build_settings(mock_app, mock_frame)

        # Find the button that has "Edit Dictionary" text
        edit_btn_call = None
        for call in mock_ctk.CTkButton.call_args_list:
            if call.kwargs.get("text") == "Edit Dictionary":
                edit_btn_call = call
                break

        self.assertIsNotNone(edit_btn_call, "Could not find Edit Dictionary button call")
        command = edit_btn_call.kwargs.get("command")
        self.assertTrue(callable(command))

        # Call the command and check if webbrowser.open was called
        command()
        mock_open.assert_called_once_with(str(DICTIONARY_FILE))

if __name__ == "__main__":
    unittest.main()
