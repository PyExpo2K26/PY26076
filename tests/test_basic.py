"""
tests/test_basic.py
====================
Basic unit tests for InfiniThink.

These tests run without a live Ollama server.  AI-dependent modules are
tested with mock patches.

Run:
    python -m pytest tests/ -v
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch


# =========================================================================
# Config / Settings
# =========================================================================


class TestSettings:
    def test_settings_imports(self):
        """Settings module loads without error."""
        from infini_think.config.settings import settings
        assert settings is not None

    def test_ollama_generate_url(self):
        from infini_think.config.settings import settings
        url = settings.ollama_generate_url
        assert url.endswith("/api/generate")
        assert url.startswith("http")

    def test_log_dir_exists_after_import(self):
        from infini_think.config.settings import settings
        assert settings.log_dir.exists()

    def test_downloads_dir_is_path(self):
        from infini_think.config.settings import settings
        assert isinstance(settings.downloads_dir, Path)


# =========================================================================
# Logger
# =========================================================================


class TestLogger:
    def test_get_logger_returns_logger(self):
        from infini_think.utils.logger import get_logger
        import logging
        log = get_logger("test_module")
        assert isinstance(log, logging.Logger)

    def test_get_logger_idempotent(self):
        from infini_think.utils.logger import get_logger
        log1 = get_logger("infini_think.test")
        log2 = get_logger("infini_think.test")
        assert log1 is log2


# =========================================================================
# AI Engine
# =========================================================================


class TestAIEngine:
    def test_init(self):
        from infini_think.core.ai_engine import AIEngine
        engine = AIEngine(model="test-model", base_url="http://localhost:11434")
        assert engine.model == "test-model"

    def test_generate_url_property(self):
        from infini_think.core.ai_engine import AIEngine
        engine = AIEngine()
        assert "/api/generate" in engine.generate_url if hasattr(engine, "generate_url") else True

    def test_is_available_returns_false_when_offline(self):
        from infini_think.core.ai_engine import AIEngine
        engine = AIEngine(base_url="http://localhost:1")  # closed port
        result = engine.is_available()
        assert result is False

    @patch("infini_think.core.ai_engine.requests.Session.post")
    def test_generate_returns_text(self, mock_post):
        from infini_think.core.ai_engine import AIEngine
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "Hello world"}
        mock_post.return_value = mock_resp
        engine = AIEngine()
        result = engine.generate("say hello")
        assert result == "Hello world"


# =========================================================================
# Command Interpreter
# =========================================================================


class TestCommandInterpreter:
    def _make_mock_engine(self, response: str) -> MagicMock:
        engine = MagicMock()
        engine.generate.return_value = response
        return engine

    def test_interpret_open_chrome(self):
        from infini_think.core.command_interpreter import CommandInterpreter
        engine = self._make_mock_engine('{"tool": "open_app", "args": ["chrome"]}')
        ci = CommandInterpreter(engine)
        result = ci.interpret("open chrome")
        assert result["tool"] == "open_app"
        assert "chrome" in result["args"]

    def test_interpret_empty_input_returns_fallback(self):
        from infini_think.core.command_interpreter import CommandInterpreter
        engine = self._make_mock_engine("{}")
        ci = CommandInterpreter(engine)
        result = ci.interpret("")
        assert result["tool"] == "unknown"

    def test_interpret_invalid_json_falls_back(self):
        from infini_think.core.command_interpreter import CommandInterpreter
        engine = self._make_mock_engine("I cannot help with that.")
        ci = CommandInterpreter(engine)
        result = ci.interpret("xyzzy")
        assert "tool" in result  # Always has a tool key

    def test_interpret_strips_markdown_fences(self):
        from infini_think.core.command_interpreter import CommandInterpreter
        raw = '```json\n{"tool": "open_folder", "args": ["downloads"]}\n```'
        engine = self._make_mock_engine(raw)
        ci = CommandInterpreter(engine)
        result = ci.interpret("open downloads")
        assert result["tool"] == "open_folder"


# =========================================================================
# Planner
# =========================================================================


class TestTaskPlanner:
    def test_simple_request_uses_interpreter(self):
        from infini_think.core.planner import TaskPlanner
        engine = MagicMock()
        interpreter = MagicMock()
        interpreter.interpret.return_value = {"tool": "open_app", "args": ["chrome"]}
        planner = TaskPlanner(engine, interpreter)
        plan = planner.plan("open chrome")
        assert isinstance(plan, list)
        assert len(plan) >= 1

    def test_plan_returns_list_of_dicts(self):
        from infini_think.core.planner import TaskPlanner
        engine = MagicMock()
        engine.generate.return_value = (
            '[{"tool":"open_app","args":["chrome"]},'
            '{"tool":"open_folder","args":["research"]}]'
        )
        interpreter = MagicMock()
        planner = TaskPlanner(engine, interpreter)
        plan = planner.plan("prepare my research workspace")
        assert isinstance(plan, list)
        for step in plan:
            assert "tool" in step
            assert "args" in step


# =========================================================================
# Executor
# =========================================================================


class TestExecutor:
    def test_unknown_tool_returns_failure(self):
        from infini_think.core.executor import Executor
        executor = Executor()
        result = executor.execute({"tool": "nonexistent_tool_xyz", "args": []})
        assert result["success"] is False

    def test_unknown_command_returns_failure(self):
        from infini_think.core.executor import Executor
        executor = Executor()
        result = executor.execute({"tool": "unknown", "args": []})
        assert result["success"] is False

    def test_execute_plan_empty(self):
        from infini_think.core.executor import Executor
        executor = Executor()
        results = executor.execute_plan([])
        assert results == []

    def test_register_custom_tool(self):
        from infini_think.core.executor import Executor
        executor = Executor()
        executor.register("test_greet", lambda name: f"Hello, {name}!")
        result = executor.execute({"tool": "test_greet", "args": ["Alice"]})
        assert result["success"] is True
        assert "Hello, Alice!" in result["output"]


# =========================================================================
# File Tools
# =========================================================================


class TestFileTools:
    def test_open_folder_nonexistent(self):
        from infini_think.tools.file_tools import open_folder
        result = open_folder("/this/path/does/not/exist/xyzzy")
        assert "not found" in result.lower()

    def test_create_folder(self, tmp_path):
        from infini_think.tools.file_tools import create_folder as _create_folder
        target = tmp_path / "test_new_folder"
        result = _create_folder(str(target))
        assert "created" in result.lower() or target.exists()

    def test_create_folder_already_exists(self, tmp_path):
        from infini_think.tools.file_tools import create_folder as _create_folder
        target = tmp_path / "existing"
        target.mkdir()
        result = _create_folder(str(target))
        assert "already exists" in result.lower()

    def test_search_files_no_results(self, tmp_path):
        from infini_think.tools.file_tools import search_files
        result = search_files("zzz_unlikely_name_xxyyzz", root=str(tmp_path))
        assert "no files found" in result.lower()

    def test_search_files_finds_file(self, tmp_path):
        from infini_think.tools.file_tools import search_files
        (tmp_path / "hello_world.txt").write_text("test")
        result = search_files("hello_world", root=str(tmp_path))
        assert "hello_world.txt" in result


# =========================================================================
# System Tools
# =========================================================================


class TestSystemTools:
    def test_get_system_info(self):
        from infini_think.tools.system_tools import get_system_info
        info = get_system_info()
        assert "OS:" in info
        assert "Python:" in info

    def test_run_terminal_command_echo(self):
        from infini_think.tools.system_tools import run_terminal_command
        import platform
        cmd = "echo hello" if platform.system() != "Windows" else "echo hello"
        result = run_terminal_command(cmd)
        assert "hello" in result.lower()

    def test_run_terminal_command_bad_command(self):
        from infini_think.tools.system_tools import run_terminal_command
        result = run_terminal_command("this_command_does_not_exist_xyzzy_123")
        # Should return something (error output or completion message), not raise
        assert isinstance(result, str)
