"""PDF 导出器测试：LibreOffice/Word 探测、成功与失败路径（全部离线 mock）。"""
from __future__ import annotations

import subprocess
import sys
import types
from pathlib import Path

import pytest

from formora.core import pdf_exporter
from formora.core.errors import ExternalDependencyError


class TestFindLibreOffice:
    def test_none_found(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: None)
        monkeypatch.setattr("os.path.exists", lambda p: False)
        assert pdf_exporter.find_libreoffice() is None

    def test_found_via_which(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "C:/fake/soffice.exe" if name == "soffice" else None)
        result = pdf_exporter.find_libreoffice()
        assert result == Path("C:/fake/soffice.exe")

    def test_found_via_candidate(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: None)
        first = pdf_exporter._LIBREOFFICE_CANDIDATES[0]
        monkeypatch.setattr("os.path.exists", lambda p: p == first)
        result = pdf_exporter.find_libreoffice()
        assert result == Path(first)


class TestHasWordCom:
    def test_true(self, monkeypatch):
        monkeypatch.setattr("importlib.util.find_spec", lambda name: object())
        assert pdf_exporter.has_word_com() is True

    def test_false(self, monkeypatch):
        monkeypatch.setattr("importlib.util.find_spec", lambda name: None)
        assert pdf_exporter.has_word_com() is False


def _install_fake_win32com(monkeypatch, word_instance):
    """注入假的 win32com 包 + win32com.client 模块。"""
    fake_client = types.ModuleType("win32com.client")
    fake_client.Dispatch = lambda app: word_instance
    # 需要同时覆盖顶层 win32com 包，并设置 client 属性，
    # 否则 import win32com.client 后 win32com.client 无法解析。
    fake_pkg = types.ModuleType("win32com")
    fake_pkg.client = fake_client
    fake_pkg.__path__ = []
    # 本机可能已真实导入 win32com.client（pywin32），必须同时覆盖子模块，
    # 否则 import win32com.client 会拿到真实的 client 导致冲突
    monkeypatch.setitem(sys.modules, "win32com", fake_pkg)
    monkeypatch.setitem(sys.modules, "win32com.client", fake_client)


class TestExportPdf:
    def test_missing_docx_raises(self, tmp_path):
        with pytest.raises(ExternalDependencyError):
            pdf_exporter.export_pdf(tmp_path / "不存在.docx", tmp_path / "out.pdf")

    def test_libreoffice_success(self, tmp_path, monkeypatch):
        docx = tmp_path / "报告.docx"
        docx.write_bytes(b"fake-docx")
        monkeypatch.setattr(pdf_exporter, "find_libreoffice",
                            lambda: Path("C:/fake/soffice.exe"))

        def fake_run(cmd, check=True, capture_output=True, timeout=120):
            outdir = Path(cmd[cmd.index("--outdir") + 1])
            predicted = outdir / (Path(cmd[-1]).stem + ".pdf")
            predicted.write_bytes(b"fake-pdf")

        monkeypatch.setattr("subprocess.run", fake_run)
        out = pdf_exporter.export_pdf(docx, tmp_path / "out" / "报告.pdf")
        assert out.exists()
        assert out.read_bytes() == b"fake-pdf"

    def test_libreoffice_timeout(self, tmp_path, monkeypatch):
        docx = tmp_path / "报告.docx"
        docx.write_bytes(b"fake-docx")
        monkeypatch.setattr(pdf_exporter, "find_libreoffice",
                            lambda: Path("C:/fake/soffice.exe"))
        monkeypatch.setattr("subprocess.run",
                            lambda *a, **k: (_ for _ in ()).throw(subprocess.TimeoutExpired("cmd", 120)))
        with pytest.raises(ExternalDependencyError):
            pdf_exporter.export_pdf(docx, tmp_path / "out.pdf")

    def test_libreoffice_called_process_error(self, tmp_path, monkeypatch):
        docx = tmp_path / "报告.docx"
        docx.write_bytes(b"fake-docx")
        monkeypatch.setattr(pdf_exporter, "find_libreoffice",
                            lambda: Path("C:/fake/soffice.exe"))
        err = subprocess.CalledProcessError(1, "cmd", stderr=b"boom")
        monkeypatch.setattr("subprocess.run",
                            lambda *a, **k: (_ for _ in ()).throw(err))
        with pytest.raises(ExternalDependencyError):
            pdf_exporter.export_pdf(docx, tmp_path / "out.pdf")

    def test_no_converter_raises(self, tmp_path, monkeypatch):
        docx = tmp_path / "报告.docx"
        docx.write_bytes(b"fake-docx")
        monkeypatch.setattr(pdf_exporter, "find_libreoffice", lambda: None)
        monkeypatch.setattr(pdf_exporter, "has_word_com", lambda: False)
        with pytest.raises(ExternalDependencyError):
            pdf_exporter.export_pdf(docx, tmp_path / "out.pdf")

    def test_word_com_success(self, tmp_path, monkeypatch):
        docx = tmp_path / "报告.docx"
        docx.write_bytes(b"fake-docx")
        monkeypatch.setattr(pdf_exporter, "find_libreoffice", lambda: None)
        monkeypatch.setattr(pdf_exporter, "has_word_com", lambda: True)

        calls = {"quit": 0}

        class FakeDoc:
            def SaveAs(self, path, FileFormat=17):
                Path(path).write_bytes(b"fake-pdf")

            def Close(self, save):
                pass

        class FakeWord:
            Visible = False

            @property
            def Documents(self):
                return self

            def Open(self, path):
                return FakeDoc()

            def Quit(self):
                calls["quit"] += 1

        _install_fake_win32com(monkeypatch, FakeWord())
        out = pdf_exporter.export_pdf(docx, tmp_path / "报告.pdf")
        assert out.exists()
        assert out.read_bytes() == b"fake-pdf"
        assert calls["quit"] == 1

    def test_word_open_failure(self, tmp_path, monkeypatch):
        docx = tmp_path / "报告.docx"
        docx.write_bytes(b"fake-docx")
        monkeypatch.setattr(pdf_exporter, "find_libreoffice", lambda: None)
        monkeypatch.setattr(pdf_exporter, "has_word_com", lambda: True)

        class BrokenWord:
            Visible = False

            @property
            def Documents(self):
                return self

            def Open(self, path):
                raise RuntimeError("Word 无法打开文档")

            def Quit(self):
                pass

        _install_fake_win32com(monkeypatch, BrokenWord())
        with pytest.raises(ExternalDependencyError):
            pdf_exporter.export_pdf(docx, tmp_path / "报告.pdf")
