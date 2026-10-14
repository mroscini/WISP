from __future__ import annotations

import sys
import types

import pytest

from wisp.button import watch_gpio_button


class StopWatching(Exception):
    pass


def test_gpio_button_invokes_callback_with_debounce(monkeypatch):
    captured = {}

    class Request:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read_edge_events(self):
            return [object()]

    fake_gpiod = types.ModuleType("gpiod")
    fake_line = types.ModuleType("gpiod.line")
    fake_line.Bias = types.SimpleNamespace(PULL_UP="pull-up")
    fake_line.Edge = types.SimpleNamespace(FALLING="falling", RISING="rising")

    def line_settings(**values):
        captured["settings"] = values
        return values

    def request_lines(chip, **values):
        captured["chip"] = chip
        captured["request"] = values
        return Request()

    fake_gpiod.LineSettings = line_settings
    fake_gpiod.request_lines = request_lines
    monkeypatch.setitem(sys.modules, "gpiod", fake_gpiod)
    monkeypatch.setitem(sys.modules, "gpiod.line", fake_line)

    def callback():
        raise StopWatching

    with pytest.raises(StopWatching):
        watch_gpio_button("/dev/gpiochip2", 17, callback, debounce_ms=125)

    assert captured["chip"] == "/dev/gpiochip2"
    assert captured["settings"]["edge_detection"] == "falling"
    assert captured["settings"]["debounce_period"].total_seconds() == 0.125
    assert 17 in captured["request"]["config"]
