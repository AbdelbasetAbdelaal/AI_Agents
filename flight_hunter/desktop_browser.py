"""Optional desktop browser for Flight Hunter AI.

This is a user-operated browser. It does not inspect page DOM, call private
endpoints, automate searches, or extract third-party fares.
"""
from __future__ import annotations

# Older/integrated GPUs may not support the EGL/OpenGL context requested by
# Chromium inside Qt WebEngine. Configure software rendering before importing
# Qt WebEngine or constructing QApplication.
import os

os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--disable-gpu --disable-gpu-compositing",
)
os.environ.setdefault("QT_OPENGL", "software")

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView

from .browser_utils import normalize_browser_url

HOME_HTML = """<!doctype html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{font-family:Tahoma,Arial,sans-serif;background:#f3f6fa;color:#172b40;margin:0;padding:42px}
main{max-width:920px;margin:auto;background:white;border-radius:18px;padding:32px;box-shadow:0 8px 32px #17324b12}
h1{color:#145b78}p{line-height:1.9}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}
a{display:block;padding:15px;border:1px solid #dbe5ed;border-radius:12px;color:#145b78;text-decoration:none;font-weight:bold}
small{color:#607487}.notice{background:#fff7e6;padding:14px;border-radius:10px;margin-top:22px}
</style></head>
<body><main><small>FLIGHT HUNTER AI · DESKTOP BROWSER</small>
<h1>متصفح البحث عن الرحلات ✈️</h1>
<p>افتح مواقع شركات الطيران ومواقع المقارنة وتصفحها بنفسك داخل نافذة مستقلة.</p>
<div class="grid">
<a href="https://eg.wego.com/">ويجو مصر</a><a href="https://sa.wego.com/">ويجو السعودية</a>
<a href="https://eg.wingie.com/">وينجي مصر</a><a href="https://sa.wingie.com/">وينجي السعودية</a>
<a href="https://www.google.com/travel/flights">Google Flights</a>
<a href="https://www.egyptair.com/ar/Pages/HomePage.aspx">مصر للطيران</a>
<a href="https://www.saudia.com/">الخطوط السعودية</a><a href="https://www.flynas.com/">طيران ناس</a>
</div>
<div class="notice"><b>تنبيه مهم:</b> المتصفح مخصص للتصفح اليدوي فقط. لا يجمع التطبيق الأسعار من الصفحات ولا يقرأ محتواها آلياً ولا يستدعي واجهات داخلية. استخدم المواقع وفق شروطها، وأدخل عروض الأسعار المسموح باستخدامها في شاشة المقارنة داخل Flight Hunter AI.</div>
</main></body></html>
"""


class BrowserPage(QWebEnginePage):
    def __init__(self, profile, tab_widget: QTabWidget, parent=None):
        super().__init__(profile, parent)
        self._tab_widget = tab_widget

    def createWindow(self, window_type):
        view = BrowserView(self._tab_widget)
        index = self._tab_widget.addTab(view, "تبويب جديد")
        self._tab_widget.setCurrentIndex(index)
        return view.page()


class BrowserView(QWebEngineView):
    def __init__(self, tabs: QTabWidget, parent=None):
        super().__init__(parent)
        self._tabs = tabs
        self.setPage(BrowserPage(self.page().profile(), tabs, self))
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        self.urlChanged.connect(self._sync_url)
        self.titleChanged.connect(self._sync_title)

    def _sync_url(self, url: QUrl):
        window = self.window()
        if isinstance(window, BrowserWindow) and window.current_view() is self:
            window.address.setText(url.toString())

    def _sync_title(self, title: str):
        index = self._tabs.indexOf(self)
        if index >= 0:
            self._tabs.setTabText(index, (title or "صفحة جديدة")[:28])


class BrowserWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Flight Hunter AI — متصفح سطح المكتب")
        self.resize(1360, 900)
        self.setMinimumSize(900, 620)

        root = QWidget(self)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        toolbar = QToolBar("التنقل")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.address = QLineEdit()
        self.address.setPlaceholderText("اكتب عنوان الموقع ثم اضغط Enter")
        self.address.returnPressed.connect(self.navigate)
        self.address.setClearButtonEnabled(True)

        for label, callback in [
            ("رجوع", self.go_back),
            ("تقدم", self.go_forward),
            ("تحديث", self.reload_page),
            ("الرئيسية", self.go_home),
        ]:
            action = QAction(label, self)
            action.triggered.connect(callback)
            toolbar.addAction(action)
        toolbar.addWidget(self.address)

        open_button = QPushButton("فتح")
        open_button.clicked.connect(self.navigate)
        toolbar.addWidget(open_button)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self._tab_changed)
        layout.addWidget(self.tabs, 1)

        footer = QLabel("تصفح يدوي فقط — لا يتم استخراج الأسعار أو قراءة صفحات المواقع آلياً.")
        footer.setStyleSheet("color:#607487;padding:5px;")
        layout.addWidget(footer)
        self.setCentralWidget(root)

        new_tab_action = QAction("تبويب جديد", self)
        new_tab_action.setShortcut(QKeySequence.AddTab)
        new_tab_action.triggered.connect(lambda: self.add_tab())
        self.addAction(new_tab_action)

        close_tab_action = QAction("إغلاق التبويب", self)
        close_tab_action.setShortcut(QKeySequence.Close)
        close_tab_action.triggered.connect(lambda: self.close_tab(self.tabs.currentIndex()))
        self.addAction(close_tab_action)

        self.add_tab(home=True)

    def add_tab(self, url: str | None = None, home: bool = False):
        view = BrowserView(self.tabs)
        index = self.tabs.addTab(view, "Flight Hunter AI")
        self.tabs.setCurrentIndex(index)
        if home or not url:
            view.setHtml(HOME_HTML, QUrl("https://flighthunter.local/"))
        else:
            view.setUrl(QUrl(url))
        return view

    def current_view(self) -> BrowserView | None:
        view = self.tabs.currentWidget()
        return view if isinstance(view, BrowserView) else None

    def navigate(self):
        try:
            url = normalize_browser_url(self.address.text())
        except ValueError as exc:
            QMessageBox.warning(self, "رابط غير صالح", str(exc))
            return
        view = self.current_view()
        if view:
            view.setUrl(QUrl(url))

    def go_back(self):
        if self.current_view():
            self.current_view().back()

    def go_forward(self):
        if self.current_view():
            self.current_view().forward()

    def reload_page(self):
        if self.current_view():
            self.current_view().reload()

    def go_home(self):
        view = self.current_view()
        if view:
            view.setHtml(HOME_HTML, QUrl("https://flighthunter.local/"))

    def close_tab(self, index: int):
        if self.tabs.count() <= 1:
            self.go_home()
            return
        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)
        if widget:
            widget.deleteLater()

    def _tab_changed(self, _index: int):
        view = self.current_view()
        if view:
            self.address.setText(view.url().toString())


def main():
    # This attribute must be set before QApplication is created.
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL)
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("Flight Hunter AI")
    window = BrowserWindow()
    window.show()
    return app.exec()
