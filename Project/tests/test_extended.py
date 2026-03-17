import pytest
import os
from unittest.mock import MagicMock, patch
from infini_think.tools.app_tools import close_app, open_url
from infini_think.tools.file_tools import read_file
from infini_think.tools.window_tools import get_active_window_info

def test_close_app_robustness():
    # Verify that close_app handles extra arguments without crashing
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        # The LLM previously sent "close_app('chrome', 'in chrome')" which caused 2 args error
        result = close_app("chrome", "in chrome")
        assert "Closed: chrome" in result

def test_open_url_windows():
    with patch("platform.system", return_value="Windows"):
        with patch("subprocess.run") as mock_run:
            open_url("gemini.google.com", "chrome")
            # Should use 'start chrome "https://gemini.google.com"'
            mock_run.assert_called()
            args, kwargs = mock_run.call_args
            assert 'start chrome "https://gemini.google.com"' in args[0]

def test_read_file_exists(tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello World", encoding="utf-8")
    
    with patch("infini_think.tools.file_tools._smart_find", return_value=test_file):
        result = read_file(str(test_file))
        assert "Hello World" in result

def test_read_file_nonexistent():
    with patch("infini_think.tools.file_tools._smart_find", return_value=None):
        result = read_file("nonexistent.txt")
        assert "File not found" in result

def test_get_active_window_info_windows():
    with patch("platform.system", return_value="Windows"):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="My Chat - Chrome", returncode=0)
            result = get_active_window_info()
            assert "The active window is: My Chat - Chrome" in result
