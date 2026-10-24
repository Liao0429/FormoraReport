"""设置中心：主题、输出目录、AI 模式配置（密钥加密）、隐私说明。"""

from __future__ import annotations

from PySide6.QtWidgets import (
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
from formora.core.errors import FormoraError
from formora.ui.widgets import Card, hint_label, primary_button, secondary_button


class SettingsPage(QWidget):
    def __init__(self, state, on_theme_change):
        super().__init__()
        self.state = state
        self.on_theme_change = on_theme_change
        self._build()
        self._load()

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

        # AI 设置
        ai_card = Card("AI 智能模式（可选）")
        ai_hint = hint_label(
            "AI 模式是可选增强，需你主动启用。启用后，生成内容会调用你配置的模型；"
            "密钥不明文落盘、不进日志，但会作为认证凭据随每个 AI 请求发送到你配置的 API 服务器。"
            "AI 不会在后台静默上传文档。"
        )
        ai_card.add_widget(ai_hint)
        ai_form = QFormLayout()
        self.ai_enabled = QCheckBox("启用 AI 智能模式")
        ai_form.addRow("", self.ai_enabled)
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
        test_btn = secondary_button("测试连接")
        test_btn.clicked.connect(self._test_ai)
        save_btn = primary_button("保存设置")
        save_btn.clicked.connect(self._save)
        ai_ops.addWidget(test_btn)
        ai_ops.addStretch(1)
        ai_ops.addWidget(save_btn)
        ai_card.add_layout(ai_ops)
        lay.addWidget(ai_card)

        # 隐私
        privacy = Card("隐私与数据")
        privacy.add_widget(
            hint_label(
                "· 无 AI 模式下所有文件都在本机处理，不联网。\n"
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
        self.outdir_edit.setText(cfg.get("output_dir"))
        ai = cfg.get("ai", {})
        self.ai_enabled.setChecked(bool(ai.get("enabled")))
        self.ai_base.setText(ai.get("base_url", ""))
        self.ai_model.setText(ai.get("model", ""))
        self.ai_temp.setValue(int(round((ai.get("temperature", 0.2) or 0.2) * 100)))

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
        # 临时用当前界面值测试，不落盘
        base_url = self.ai_base.text().strip()
        model = self.ai_model.text().strip()
        key = self.ai_key.text().strip() or self.state.config.get_ai_api_key()
        if not base_url or not model or not key:
            QMessageBox.warning(self, "提示", "请填写 API 地址、模型和密钥。")
            return
        try:
            summary = client.test_connection(base_url, model, key)
            QMessageBox.information(self, "连接成功", f"模型响应正常。\n{summary}")
        except FormoraError as e:
            QMessageBox.critical(self, "连接失败", str(e))

    def _pick_output_dir(self):
        path = QFileDialog.getExistingDirectory(
            self, "选择输出目录", self.outdir_edit.text()
        )
        if path:
            self.outdir_edit.setText(path)
