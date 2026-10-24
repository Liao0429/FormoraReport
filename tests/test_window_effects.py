"""窗口系统效果测试：DWM 不可用/非 Windows 时安全降级。"""

from __future__ import annotations

from formora.ui import window_effects as we


class TestDwmUnavailable:
    def test_set_window_attribute_false(self, monkeypatch):
        monkeypatch.setattr(we, "_dwmapi", None)
        assert we._set_window_attribute(0, 1, 1) is False

    def test_apply_system_backdrop_false(self, monkeypatch):
        monkeypatch.setattr(we, "_dwmapi", None)
        assert we.apply_system_backdrop(0) is False

    def test_apply_window_corner_false(self, monkeypatch):
        monkeypatch.setattr(we, "_dwmapi", None)
        assert we.apply_window_corner(0) is False

    def test_apply_immersive_dark_mode_false(self, monkeypatch):
        monkeypatch.setattr(we, "_dwmapi", None)
        assert we.apply_immersive_dark_mode(0, True) is False


class TestNonWindows:
    def test_is_mica_supported_false(self, monkeypatch):
        monkeypatch.setattr(we, "_IS_WINDOWS", False)
        monkeypatch.setattr(we, "_dwmapi", None)
        assert we.is_mica_supported() is False

    def test_setup_glass_window_false(self, monkeypatch):
        monkeypatch.setattr(we, "_IS_WINDOWS", False)
        assert we.setup_glass_window(None) is False
