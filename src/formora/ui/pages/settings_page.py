"""设置中心：主题、输出目录、AI 模式配置（密钥加密）、隐私说明。"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from formora.ai import client
from formora.core.chart import BLUE_ORANGE_COLORS
from formora.ui.widgets import Card, hint_label, primary_button, secondary_button


class _TestConnectionThread(QThread):
    """后台执行 AI 连接测试，避免阻塞 UI 主线程（最长 20s）。"""

    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, base_url: str, model: str, key: str):
        super().__init__()
        self._base_url = base_url
        self._model = model
        self._key = key

    def run(self):
        try:
            summary = client.test_connection(self._base_url, self._model, self._key)
            self.finished_ok.emit(summary)
        except Exception as e:
            self.failed.emit(str(e))


class SettingsPage(QWidget):
    def __init__(self, state, on_theme_change):
        super().__init__()
        self.state = state
        self.on_theme_change = on_theme_change
        self._test_thread = None
        self._build()
        self._load()
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._wait_for_test_thread)

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        title = QLabel("设置中心")
        title.setObjectName("AppTitle")
        lay.addWidget(title)

        # 通用设置
        general = Card("通用")
        form = QFormLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["浅色", "深色"])
        form.addRow("主题", self.theme_combo)

        self.outdir_edit = QLineEdit()
        outdir_btn = secondary_button("浏览…")
        outdir_btn.clicked.connect(self._pick_output_dir)
        outdir_row = QHBoxLayout()
        outdir_row.addWidget(self.outdir_edit, 1)
        outdir_row.addWidget(outdir_btn)
        form.addRow("输出目录", outdir_row)
        general.add_layout(form)
        lay.addWidget(general)

        # 图表样式
        chart_card = Card("图表样式")
        chart_form = QFormLayout()
        self.chart_colors_combo = QComboBox()
        self.chart_colors_combo.addItems(["默认", "蓝橙"])
        chart_form.addRow("颜色主题", self.chart_colors_combo)

        self.chart_dpi_combo = QComboBox()
        self.chart_dpi_combo.addItems(["100", "150", "200"])
        chart_form.addRow("DPI", self.chart_dpi_combo)

        self.chart_grid_check = QCheckBox("显示网格")
        chart_form.addRow("", self.chart_grid_check)
        chart_card.add_layout(chart_form)
        lay.addWidget(chart_card)

        # AI 设置
        ai_card = Card("AI 智能模式（可选）")
        ai_hint = hint_label(
            "AI 辅助是可选增强，默认开启。关闭「启用 AI 辅助」后，不会上传任何数据；"
            "启用后，生成内容会调用你配置的模型。密钥不明文落盘、不进日志，但会作为认证凭据"
            "随每个 AI 请求发送到你配置的 API 服务器。AI 不会在后台静默上传文档。"
        )
        ai_card.add_widget(ai_hint)
        ai_form = QFormLayout()
        self.ai_enabled = QCheckBox("启用 AI 辅助")
        ai_form.addRow("", self.ai_enabled)
        self.ai_enabled.toggled.connect(self._on_ai_enabled_toggled)
        self.ai_base = QLineEdit()
        self.ai_base.setPlaceholderText("https://api.openai.com/v1")
        ai_form.addRow("API 地址", self.ai_base)
        self.ai_model = QLineEdit()
        self.ai_model.setPlaceholderText("gpt-4o-mini")
        ai_form.addRow("模型名称", self.ai_model)
        self.ai_key = QLineEdit()
        self.ai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.ai_key.setPlaceholderText("留空表示不修改已保存的密钥")
        ai_form.addRow("API 密钥", self.ai_key)
        self.ai_temp = QSpinBox()
        self.ai_temp.setRange(0, 100)
        self.ai_temp.setSuffix("%")
        ai_form.addRow("温度", self.ai_temp)
        ai_card.add_layout(ai_form)

        ai_ops = QHBoxLayout()
        self.test_btn = secondary_button("测试连接")
        self.test_btn.clicked.connect(self._test_ai)
        save_btn = primary_button("保存设置")
        save_btn.clicked.connect(self._save)
        ai_ops.addWidget(self.test_btn)
        ai_ops.addStretch(1)
        ai_ops.addWidget(save_btn)
        ai_card.add_layout(ai_ops)
        lay.addWidget(ai_card)

        # 隐私
        privacy = Card("隐私与数据")
        privacy.add_widget(
            hint_label(
                "· 关闭「启用 AI 辅助」后，所有文件都在本机处理，不联网，不上传任何数据。\n"
                "· AI 模式下，仅在你点击生成/审查时发送必要内容到所配置的 API。\n"
                "· API 密钥用 Windows DPAPI 加密存储，不明文落盘。\n"
                "· 日志仅记录操作摘要，不包含文档正文与密钥。"
            )
        )
        lay.addWidget(privacy)
        lay.addStretch(1)

    def _load(self):
        cfg = self.state.config
        self.theme_combo.setCurrentIndex(
            0 if cfg.get("theme", "light") == "light" else 1
        )
        self.outdir_edit.setText(cfg.get("output_dir") or "")
        ai = cfg.get("ai", {}) or {}
        self.ai_enabled.setChecked(bool(ai.get("enabled")))
        self._on_ai_enabled_toggled(self.ai_enabled.isChecked())
        self.ai_base.setText(ai.get("base_url") or "")
        self.ai_model.setText(ai.get("model") or "")
        temp = ai.get("temperature", 0.2)
        if temp is None:
            temp = 0.2
        self.ai_temp.setValue(round(float(temp) * 100))

        chart_cfg = cfg.get("chart", {}) or {}
        if not isinstance(chart_cfg, dict):
            chart_cfg = {}
        colors = chart_cfg.get("colors") or []
        self.chart_colors_combo.setCurrentIndex(
            0 if colors != BLUE_ORANGE_COLORS else 1
        )
        dpi = chart_cfg.get("dpi", 150)
        try:
            dpi = int(dpi) if dpi else 150
        except (TypeError, ValueError):
            dpi = 150
        self.chart_dpi_combo.setCurrentIndex({100: 0, 150: 1, 200: 2}.get(dpi, 1))
        grid = chart_cfg.get("grid", True)
        self.chart_grid_check.setChecked(True if grid is None else bool(grid))

    def _on_ai_enabled_toggled(self, checked: bool):
        """隐私开关：关闭 AI 辅助后禁用 AI 配置输入，确保不会上传任何数据。"""
        for w in (
            self.ai_base,
            self.ai_model,
            self.ai_key,
            self.ai_temp,
            self.test_btn,
        ):
            w.setEnabled(checked)

    def _save(self):
        cfg = self.state.config
        cfg.set("theme", "light" if self.theme_combo.currentIndex() == 0 else "dark")
        cfg.set("output_dir", self.outdir_edit.text().strip())
        ai = cfg.get("ai", {})
        ai["enabled"] = self.ai_enabled.isChecked()
        ai["base_url"] = self.ai_base.text().strip()
        ai["model"] = self.ai_model.text().strip()
        ai["temperature"] = self.ai_temp.value() / 100.0
        cfg.set("ai", ai)

        chart_cfg = dict(cfg.get("chart", {}) or {})
        if not isinstance(chart_cfg, dict):
            chart_cfg = {}
        chart_cfg["colors"] = (
            []
            if self.chart_colors_combo.currentIndex() == 0
            else list(BLUE_ORANGE_COLORS)
        )
        chart_cfg["dpi"] = int(self.chart_dpi_combo.currentText())
        chart_cfg["grid"] = self.chart_grid_check.isChecked()
        cfg.set("chart", chart_cfg)

        # 密钥：仅当输入了新内容才更新
        if self.ai_key.text().strip():
            cfg.set_ai_api_key(self.ai_key.text().strip())
            self.ai_key.clear()
        cfg.save()
        self.on_theme_change(
            "light" if self.theme_combo.currentIndex() == 0 else "dark"
        )
        QMessageBox.information(self, "已保存", "设置已保存。")

    def _test_ai(self):
        # 临时用当前界面值测试，不落盘；后台线程执行，避免阻塞 UI
        thread = getattr(self, "_test_thread", None)
        if thread is not None:
            try:
                if thread.isRunning():
                    return
            except RuntimeError:
                # 旧线程对象已被 finished→deleteLater 销毁，清理悬空引用后继续
                self._test_thread = None
        base_url = self.ai_base.text().strip()
        model = self.ai_model.text().strip()
        key = self.ai_key.text().strip() or self.state.config.get_ai_api_key()
        if not base_url or not model or not key:
            QMessageBox.warning(self, "提示", "请填写 API 地址、模型和密钥。")
            return
        self.test_btn.setEnabled(False)
        self.test_btn.setText("测试中…")
        thread = _TestConnectionThread(base_url, model, key)
        self._test_thread = thread
        thread.finished_ok.connect(self._on_test_ok)
        thread.failed.connect(self._on_test_failed)
        thread.finished.connect(self._on_test_finished)
        # 线程结束后安全释放 C++ 对象，避免内存泄漏
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def _on_test_ok(self, summary: str):
        QMessageBox.information(self, "连接成功", f"模型响应正常。\n{summary}")

    def _on_test_failed(self, msg: str):
        QMessageBox.critical(self, "连接失败", msg)

    def _on_test_finished(self):
        self.test_btn.setEnabled(True)
        self.test_btn.setText("测试连接")
        # 释放线程引用；C++ 对象由 finished→deleteLater 负责销毁，避免悬空指针
        self._test_thread = None

    def closeEvent(self, event):
        # 防止页面在测试线程仍运行时销毁导致 "QThread: Destroyed while thread is still running"
        self._wait_for_test_thread(3000)
        super().closeEvent(event)

    def _wait_for_test_thread(self, timeout_ms: int = 5000) -> None:
        """等待后台测试线程结束（页面关闭/应用退出时调用），并清理失效引用。"""
        thread = getattr(self, "_test_thread", None)
        if thread is None:
            return
        try:
            if thread.isRunning():
                thread.wait(timeout_ms)
        except RuntimeError:
            # C++ 对象已被销毁（线程早已结束），仅需清理悬空引用
            self._test_thread = None
            return
        if not thread.isRunning():
            # 线程已结束：释放引用；finished 槽可能因事件循环退出/页面隐藏不再投递
            self._test_thread = None

    def _pick_output_dir(self):
        path = QFileDialog.getExistingDirectory(
            self, "选择输出目录", self.outdir_edit.text()
        )
        if path:
            self.outdir_edit.setText(path)
