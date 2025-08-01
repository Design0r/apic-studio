import os

from PySide6.QtCore import QRegularExpression, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from apic_studio.core.settings import SettingsManager


class LogHighlighter(QSyntaxHighlighter):
    RED = "#ff2424"
    DARK_RED = "#ff2424"
    ORANGE = "#ff8324"
    DARK_GREY = "#676767"
    GREY = "#c7c7c7"
    GREEN = "#52ff46"
    BLUE = "#4693ff"

    def __init__(self, parent: QPlainTextEdit):
        super().__init__(parent.document())
        self.rules = []

        def make_fmt(color_name: str, bold: bool = False, italic: bool = False):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color_name))
            if bold:
                fmt.setFontWeight(QFont.Weight.Bold)
            if italic:
                fmt.setFontItalic(True)
            return fmt

        # Severity formats
        self.rules.append(
            (
                QRegularExpression(r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})?\]"),
                make_fmt(self.DARK_GREY),
            )
        )

        # Log levels
        self.rules.append(
            (QRegularExpression(r"\[ERROR\]"), make_fmt(self.RED, bold=True))
        )
        self.rules.append(
            (
                QRegularExpression(r"\[WARNING\]|\[WARN\]"),
                make_fmt(self.ORANGE, bold=True),
            )
        )
        self.rules.append((QRegularExpression(r"\[INFO\]"), make_fmt(self.GREEN)))
        self.rules.append((QRegularExpression(r"\[DEBUG\]"), make_fmt(self.GREY)))
        self.rules.append(
            (QRegularExpression(r"\[CRITICAL\]"), make_fmt(self.RED, bold=True))
        )

        # Traceback header
        self.rules.append(
            (
                QRegularExpression(r"Traceback \(most recent call last\):"),
                make_fmt(self.RED, bold=True),
            )
        )

        # Exception class names ending with Error/Exception
        self.rules.append(
            (
                QRegularExpression(r"\b[A-Za-z_]+(?:Error|Exception)\b"),
                make_fmt(self.RED, italic=True),
            )
        )

        # File references (e.g., File "path", line 95, in connect)
        self.rules.append(
            (
                QRegularExpression(r'File "[^"]+", line \d+, in [\w_]+'),
                make_fmt(self.BLUE),
            )
        )

    def highlightBlock(self, text: str):
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)


def read_last_lines(path: str, num_lines: int = 1000, encoding: str = "utf-8"):
    """
    Efficiently read the last `num_lines` lines from a potentially large file.
    """
    line_terminator = b"\n"
    buffer = bytearray()
    lines = []
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        block_size = 4096
        while len(lines) <= num_lines and f.tell() > 0:
            read_size = min(block_size, f.tell())
            f.seek(-read_size, os.SEEK_CUR)
            chunk = f.read(read_size)
            f.seek(-read_size, os.SEEK_CUR)
            buffer[0:0] = chunk  # prepend
            lines = buffer.split(line_terminator)
            if f.tell() == 0:
                break

        decoded: list[str] = []
        for line in lines[-num_lines:]:
            try:
                decoded.append(line.decode(encoding, errors="replace"))
            except Exception:
                decoded.append(line.decode("utf-8", errors="replace"))
        return "\n".join(decoded)


class LogViewer(QWidget):
    POLL_INTERVAL_MS = 1000

    def __init__(
        self, parent: QWidget | None = None, f: Qt.WindowType = Qt.WindowType.Window
    ) -> None:
        super().__init__(parent, f)

        self.settings = SettingsManager()

        self.setWindowTitle("Log Viewer")
        self.setWindowIcon(QIcon(":icons/apic_logo.png"))
        self.setWindowFlag(Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._file = None
        self._inode = None
        self._position = 0
        self._auto_scroll = True

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

        self.highlighter = LogHighlighter(self.text)

        self._load_initial_tail()
        self._start_polling()

    def init_widgets(self):
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        # Controls
        self.auto_scroll_cb = QCheckBox("Auto-scroll")
        self.auto_scroll_cb.setChecked(True)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter / search (regex)")
        self.clear_btn = QPushButton("Clear")
        self.reload_btn = QPushButton("Reload All")
        self.status_label = QLabel("")

    def init_layouts(self):
        controls = QHBoxLayout()
        controls.addWidget(self.auto_scroll_cb)
        controls.addWidget(QLabel("Search:"))
        controls.addWidget(self.search_input)
        controls.addWidget(self.reload_btn)
        controls.addWidget(self.clear_btn)
        controls.addStretch()
        controls.addWidget(self.status_label)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(4)
        self.main_layout.addLayout(controls)
        self.main_layout.addWidget(self.text)

    def init_signals(self):
        self.auto_scroll_cb.toggled.connect(self._on_auto_scroll_toggled)
        self.clear_btn.clicked.connect(self.text.clear)
        self.reload_btn.clicked.connect(self._force_reload)
        self.search_input.textChanged.connect(self._apply_filter)
        # detect user scroll to disable auto-scroll if they scroll up
        self.text.verticalScrollBar().valueChanged.connect(self._on_scroll)

    def _on_auto_scroll_toggled(self, checked: bool):
        self._auto_scroll = checked

    def _on_scroll(self, value: int):
        sb = self.text.verticalScrollBar()
        at_bottom = value >= sb.maximum() - 2  # tolerance
        if not at_bottom:
            self.auto_scroll_cb.setChecked(False)
        else:
            self.auto_scroll_cb.setChecked(True)

    def _load_initial_tail(self):
        try:
            tail = read_last_lines(str(self.settings.LOGGING_PATH), num_lines=500)
            self.text.setPlainText(tail)
            self._open_file_for_tail()
            self._scroll_to_bottom()
            self.status_label.setText(
                f"Loaded tail of {os.path.basename(self.settings.LOGGING_PATH)}"
            )
        except Exception as e:
            self.status_label.setText(f"Error loading log: {e}")

    def _open_file_for_tail(self):
        try:
            if self._file:
                self._file.close()
            self._file = open(
                self.settings.LOGGING_PATH, "r", encoding="utf-8", errors="replace"
            )
            st = os.fstat(self._file.fileno())
            self._inode = (st.st_dev, st.st_ino)
            self._file.seek(0, os.SEEK_END)
            self._position = self._file.tell()
        except Exception as e:
            self.status_label.setText(f"Tail open failed: {e}")
            self._file = None
            self._inode = None
            self._position = 0

    def _start_polling(self):
        self._timer = QTimer(self)
        self._timer.setInterval(self.POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._check_updates)
        self._timer.start()

    def _check_updates(self):
        path = self.settings.LOGGING_PATH
        try:
            if not os.path.exists(path):
                return
            current_stat = os.stat(path)
            if (
                self._inode is None
                or (current_stat.st_dev, current_stat.st_ino) != self._inode
            ):
                self.status_label.setText(
                    "Log file was rotated/reopened; reloading tail."
                )
                self._load_initial_tail()
                return

            if self._file is None:
                self._open_file_for_tail()
                return

            self._file.seek(0, os.SEEK_END)
            new_size = self._file.tell()
            if new_size < self._position:
                # truncated
                self.status_label.setText("Log truncated; reloading tail.")
                self._load_initial_tail()
                return
            elif new_size == self._position:
                return  # nothing new

            self._file.seek(self._position)
            new_data = self._file.read()
            self._position = self._file.tell()
            if new_data:
                self._append_text(new_data)
        except Exception as e:
            self.status_label.setText(f"Polling error: {e}")

    def _append_text(self, text: str):
        cursor = self.text.textCursor()
        at_bottom = self._auto_scroll and self._is_at_bottom()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        if self._auto_scroll and at_bottom:
            self._scroll_to_bottom()

    def _is_at_bottom(self) -> bool:
        sb = self.text.verticalScrollBar()
        return sb.value() >= sb.maximum() - 2

    def _scroll_to_bottom(self):
        self.text.moveCursor(QTextCursor.MoveOperation.End)
        self.text.verticalScrollBar().setValue(self.text.verticalScrollBar().maximum())

    def _force_reload(self):
        self._load_initial_tail()

    def _apply_filter(self, pattern: str):
        if not pattern:
            self._force_reload()
            return

        try:
            regex = QRegularExpression(pattern)
            full = self.text.toPlainText().splitlines()
            filtered = [line for line in full if regex.match(line).hasMatch()]
            self.text.setPlainText("\n".join(filtered))
            self._scroll_to_bottom()
            self.status_label.setText(
                f"Filter applied: {pattern} ({len(filtered)} lines)"
            )
        except Exception as e:
            self.status_label.setText(f"Filter error: {e}")
