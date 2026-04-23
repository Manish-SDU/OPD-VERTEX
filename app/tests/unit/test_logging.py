"""Unit tests for the AOP logging system."""

from __future__ import annotations

import logging

import pytest

from app.infrastructure.logging.aspects import (
    apply_logging_aspect,
    get_component_logger,
    log_method,
    log_performance,
    log_service,
)


# ── get_component_logger ───────────────────────────────────────────────


class TestGetComponentLogger:
    def test_returns_namespaced_logger(self):
        logger = get_component_logger("service", "patients")
        assert logger.name == "opd_vertex.service.patients"

    def test_without_module(self):
        logger = get_component_logger("middleware")
        assert logger.name == "opd_vertex.middleware"


# ── log_method decorator ──────────────────────────────────────────────


class TestLogMethod:
    def test_preserves_return_value(self):
        @log_method("test", "unit")
        def add(a, b):
            return a + b

        assert add(2, 3) == 5

    def test_preserves_function_name(self):
        @log_method("test", "unit")
        def my_function():
            pass

        assert my_function.__name__ == "my_function"

    def test_logs_entry_and_exit(self, caplog):
        @log_method("test", "unit", level=logging.INFO)
        def greet(name):
            return f"Hello {name}"

        with caplog.at_level(logging.INFO, logger="opd_vertex.test.unit"):
            result = greet("World")

        assert result == "Hello World"
        messages = [r.message for r in caplog.records]
        assert any("[ENTER]" in m for m in messages)
        assert any("[EXIT]" in m for m in messages)

    def test_logs_error_on_exception(self, caplog):
        @log_method("test", "unit", level=logging.INFO)
        def fail():
            raise ValueError("boom")

        with caplog.at_level(logging.INFO, logger="opd_vertex.test.unit"):
            try:
                fail()
            except ValueError:
                pass

        messages = [r.message for r in caplog.records]
        assert any("[ERROR]" in m for m in messages)

    def test_propagates_exception(self):
        @log_method("test", "unit")
        def fail():
            raise RuntimeError("critical")

        try:
            fail()
            assert False, "Should have raised"
        except RuntimeError as e:
            assert str(e) == "critical"

    def test_log_args_includes_arguments(self, caplog):
        @log_method("test", "unit", log_args=True, level=logging.INFO)
        def compute(x, y):
            return x * y

        with caplog.at_level(logging.INFO, logger="opd_vertex.test.unit"):
            compute(3, 7)

        messages = " ".join(r.message for r in caplog.records)
        assert "args=" in messages

    def test_log_result_includes_return(self, caplog):
        @log_method("test", "unit", log_result=True, level=logging.INFO)
        def get_value():
            return 42

        with caplog.at_level(logging.INFO, logger="opd_vertex.test.unit"):
            get_value()

        messages = " ".join(r.message for r in caplog.records)
        assert "result=42" in messages


# ── log_service shortcut ──────────────────────────────────────────────


class TestLogService:
    def test_uses_info_level(self, caplog):
        @log_service("payments")
        def process():
            return "done"

        with caplog.at_level(logging.INFO, logger="opd_vertex.service.payments"):
            process()

        assert len(caplog.records) >= 2
        assert all(r.levelno == logging.INFO for r in caplog.records)


# ── apply_logging_aspect (class-level AOP) ────────────────────────────


class TestApplyLoggingAspect:
    def test_wraps_all_public_methods(self, caplog):
        @apply_logging_aspect("test", "cls")
        class MyService:
            def do_work(self):
                return "result"

            def other_method(self):
                return 123

        svc = MyService()
        with caplog.at_level(logging.DEBUG, logger="opd_vertex.test.cls"):
            assert svc.do_work() == "result"
            assert svc.other_method() == 123

        method_names = [r.message for r in caplog.records]
        assert any("do_work" in m for m in method_names)
        assert any("other_method" in m for m in method_names)

    def test_skips_private_methods(self, caplog):
        @apply_logging_aspect("test", "cls")
        class MyService:
            def _private(self):
                return "secret"

            def public(self):
                return self._private()

        svc = MyService()
        with caplog.at_level(logging.DEBUG, logger="opd_vertex.test.cls"):
            result = svc.public()

        assert result == "secret"
        # Only "public" should appear as an [ENTER]/[EXIT] target,
        # "_private" must NOT be wrapped by the aspect.
        logged_targets = [
            r.message.split("]", 1)[1].strip().split()[0]
            for r in caplog.records
            if "[ENTER]" in r.message or "[EXIT]" in r.message
        ]
        assert all("_private" not in t.split(".")[-1] for t in logged_targets)

    def test_exclude_parameter_skips_methods(self, caplog):
        @apply_logging_aspect("test", "cls", exclude=frozenset({"skip_me"}))
        class MyService:
            def skip_me(self):
                return "skipped"

            def log_me(self):
                return "logged"

        svc = MyService()
        with caplog.at_level(logging.DEBUG, logger="opd_vertex.test.cls"):
            svc.skip_me()
            svc.log_me()

        messages = " ".join(r.message for r in caplog.records)
        assert "skip_me" not in messages
        assert "log_me" in messages

    def test_error_logging_on_class_method(self, caplog):
        @apply_logging_aspect("test", "cls")
        class MyService:
            def fail(self):
                raise ValueError("class method error")

        svc = MyService()
        with caplog.at_level(logging.DEBUG, logger="opd_vertex.test.cls"):
            try:
                svc.fail()
            except ValueError:
                pass

        messages = " ".join(r.message for r in caplog.records)
        assert "[ERROR]" in messages


# ── log_performance aspect ────────────────────────────────────────────


class TestLogPerformance:
    def test_fast_call_does_not_emit_slow_warning(self, caplog):
        @log_performance(threshold_ms=1000, component="test", module="perf")
        def fast():
            return 1

        with caplog.at_level(logging.WARNING, logger="opd_vertex.test.perf"):
            fast()

        slow_records = [r for r in caplog.records if "[SLOW]" in r.message]
        assert len(slow_records) == 0

    def test_preserves_return_value(self):
        @log_performance(threshold_ms=1000)
        def compute():
            return 42

        assert compute() == 42

    def test_preserves_function_name(self):
        @log_performance(threshold_ms=1000)
        def my_perf_fn():
            pass

        assert my_perf_fn.__name__ == "my_perf_fn"

    def test_propagates_exception(self):
        @log_performance(threshold_ms=1000)
        def risky():
            raise RuntimeError("kaboom")

        with pytest.raises(RuntimeError, match="kaboom"):
            risky()

    def test_slow_call_emits_warning(self, caplog):
        import time as _time

        @log_performance(threshold_ms=1, component="test", module="perf")
        def slow():
            _time.sleep(0.005)

        with caplog.at_level(logging.WARNING, logger="opd_vertex.test.perf"):
            slow()

        slow_records = [r for r in caplog.records if "[SLOW]" in r.message]
        assert len(slow_records) == 1
        assert "slow" in slow_records[0].message
