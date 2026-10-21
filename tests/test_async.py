# -*- coding: utf-8 -*-
"""Desktop test for the timer-based async helper."""

from __future__ import absolute_import, print_function

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_ui_smoke import (Session, _build_components, _build_enigma,
                           _build_screens)


class Signal(object):
    def __init__(self):
        self.callbacks = []

    def append(self, callback):
        self.callbacks.append(callback)

    def remove(self, callback):
        if callback in self.callbacks:
            self.callbacks.remove(callback)


class ManualTimer(object):
    """A timer that only runs when the test explicitly fires it."""

    def __init__(self):
        self.callback = Signal()
        self.running = False

    def start(self, interval=0, single=True):
        self.running = True

    def stop(self):
        self.running = False

    def fire(self):
        for callback in list(self.callback.callbacks):
            if self.running:
                callback()


def main():
    saved = {}
    for name, module in list(_build_enigma().items()):
        saved[name] = sys.modules.get(name)
        sys.modules[name] = module
    sys.modules["enigma"].eTimer = ManualTimer
    for name, module in _build_components().items():
        saved[name] = sys.modules.get(name)
        sys.modules[name] = module
    for name, module in _build_screens().items():
        saved[name] = sys.modules.get(name)
        sys.modules[name] = module

    try:
        from IPTVPlayerPro.ui import base

        class Screen(base.AsyncScreen):
            def __init__(self):
                base.AsyncScreen.__init__(self, Session())

        screen = Screen()
        result = {}
        screen.run_async(
            lambda: 42,
            lambda value: result.update(value=value),
            lambda error: result.update(error=error),
            timeout=2,
        )
        timer = screen._timers[-1]
        deadline = time.time() + 2
        while "value" not in result and time.time() < deadline:
            timer.fire()
            time.sleep(0.01)
        assert result.get("value") == 42

        # A slow worker must produce a timeout through on_error instead of
        # leaving the screen waiting forever.
        slow = Screen()
        failed = {}
        slow.run_async(
            lambda: time.sleep(0.5),
            lambda value: failed.update(value=value),
            lambda error: failed.update(error=error),
            timeout=0.1,
        )
        timer = slow._timers[-1]
        deadline = time.time() + 2
        while "error" not in failed and time.time() < deadline:
            timer.fire()
            time.sleep(0.01)
        assert failed.get("error") is not None
        assert not timer.running
        print("Async helper tests passed.")
    finally:
        for name, module in saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


if __name__ == "__main__":
    main()
