from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal, NamedTuple

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QIcon,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPolygon,
    QShowEvent,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressDialog,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from apic_studio.core.settings import SettingsManager
from apic_studio.services import Backup, BackupManager
from shared.logger import Logger

from .buttons import IconButton
from .flow_layout import FlowLayout

ACCENT = "rgb(235, 177, 52)"

DIALOG_STYLE = f"""
QWidget {{background-color: #333; color: #fff}}

QLineEdit, QTextEdit, QSpinBox, QTreeWidget, QScrollArea {{
    background-color: #2a2a2a;
    border: 1px solid #222;
    border-radius: 3px;
    padding: 2px;
}}
QLineEdit:focus, QSpinBox:focus {{border: 1px solid {ACCENT}}}

QPushButton {{
    background-color: #444;
    border: 1px solid #222;
    border-radius: 3px;
    padding: 4px 12px;
}}
QPushButton:hover {{background-color: #505050}}
QPushButton:default {{border: 1px solid {ACCENT}}}
QPushButton:checked {{background-color: {ACCENT}; color: #000}}
QPushButton:disabled {{background-color: #383838; color: #777}}

IconButton {{background-color: transparent; border: none; padding: 0px}}
IconButton:hover {{background-color: #505050}}

QLabel#hint {{color: #aaa}}
"""

# characters Windows does not allow in file and folder names
INVALID_NAME_CHARS = frozenset('\\/:*?"<>|')


def name_problem(name: str, what: str) -> str:
    """Why `name` can't be used as a file / folder name, or "" if it can."""
    if not name.strip():
        return f"Enter a {what} name."

    invalid = sorted(set(name) & INVALID_NAME_CHARS)
    if invalid:
        return f"The name can't contain {' '.join(invalid)}"

    return ""


class BaseDialog(QDialog):
    """Shared window title, icon and look for the app's dialogs."""

    def __init__(self, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(":icons/apic_logo.png"))
        self.setStyleSheet(DIALOG_STYLE)

        # explains why OK is disabled, subclasses place it in their layout
        self.hint = QLabel()
        self.hint.setObjectName("hint")
        self.hint.setWordWrap(True)
        self.hint.setVisible(False)

    def set_problem(self, button: QPushButton, problem: str) -> None:
        """Disable `button` and show `problem` until it is empty."""
        button.setEnabled(not problem)
        self.hint.setText(problem)
        self.hint.setVisible(bool(problem))


class CreatePoolDialog(BaseDialog):
    pool_created = Signal(tuple)

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Create new Pool", parent)

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

        self.validate()

    def init_widgets(self):
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Furniture")

        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Folder the pool is created in")

        self.open_file_dialog = IconButton((27, 27))
        self.open_file_dialog.set_icon(":icons/tabler-icon-folder-open.png")
        self.open_file_dialog.set_tooltip("Browse")

        buttons = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box = QDialogButtonBox(buttons)
        self.ok_btn = self.button_box.button(QDialogButtonBox.StandardButton.Ok)

    def init_layouts(self):
        self.main_layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()
        self.folder_layout = QHBoxLayout()
        self.folder_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.folder_layout.setContentsMargins(0, 0, 0, 0)

        self.folder_layout.addWidget(self.folder_edit)
        self.folder_layout.addWidget(self.open_file_dialog)

        self.form_layout.addRow(QLabel("Pool Name"), self.name_edit)
        self.form_layout.addRow(QLabel("Pool Path"), self.folder_layout)

        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addWidget(self.hint)
        self.main_layout.addWidget(self.button_box)
        self.setMinimumWidth(400)

    def init_signals(self):
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.open_file_dialog.clicked.connect(self.browse_folder)
        self.name_edit.textChanged.connect(self.validate)
        self.folder_edit.textChanged.connect(self.validate)

    def validate(self):
        problem = name_problem(self.name_edit.text(), "pool")
        if not problem and not self.folder_edit.text().strip():
            problem = "Choose the folder the pool is created in."

        self.set_problem(self.ok_btn, problem)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Pool Folder", self.folder_edit.text()
        )
        if not folder:
            return
        self.folder_edit.setText(folder)

    def accept(self) -> None:
        if not self.ok_btn.isEnabled():
            return

        # checked here rather than while typing, a half typed UNC path would
        # block the UI on a network lookup for every key
        folder = Path(self.folder_edit.text().strip())
        if not folder.is_dir():
            self.hint.setText("The pool folder doesn't exist.")
            self.hint.setVisible(True)
            return

        data = (self.name_edit.text().strip(), folder)
        self.pool_created.emit(data)
        super().accept()


class _ConfirmDeleteDialog(BaseDialog):
    """Asks before deleting from disk. Cancel is the default, so Enter is safe."""

    def __init__(self, title: str, message: str, parent: QWidget | None = None):
        super().__init__(title, parent)

        self.label = QLabel(message)
        self.label.setWordWrap(True)
        self.label.setMinimumWidth(320)

        self.button_box = QDialogButtonBox()
        self.delete_btn = self.button_box.addButton(
            "Delete", QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.delete_btn.setStyleSheet(
            "QPushButton {background-color: #8a2d2f}"
            "QPushButton:hover {background-color: #a33538}"
        )
        # a focused auto default button takes over Enter, so Delete never may
        self.delete_btn.setAutoDefault(False)
        self.cancel_btn = self.button_box.addButton(
            QDialogButtonBox.StandardButton.Cancel
        )
        self.cancel_btn.setDefault(True)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.button_box)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def showEvent(self, event: QShowEvent):
        super().showEvent(event)
        self.cancel_btn.setFocus()


class DeletePoolDialog(_ConfirmDeleteDialog):
    pool_deleted = Signal()

    def __init__(self, pool_name: str, parent: QWidget | None = None):
        super().__init__(
            "Delete Pool",
            f"Delete the pool “{pool_name}”?\n\n"
            "This permanently deletes the pool folder and every asset in it "
            "from disk. This can't be undone.",
            parent,
        )

    def accept(self) -> None:
        self.pool_deleted.emit()
        super().accept()


class DeleteAssetDialog(_ConfirmDeleteDialog):
    accepted = Signal()

    def __init__(self, asset_name: str, parent: QWidget | None = None):
        super().__init__(
            f"Delete {asset_name}",
            f"Delete “{asset_name}”?\n\n"
            "This permanently deletes the asset folder from disk, including its "
            "previews, notes and backups. This can't be undone.",
            parent,
        )
        self.asset_name = asset_name

    def accept(self) -> None:
        self.accepted.emit()
        super().accept()


class ExportModelDialog(BaseDialog):
    class ExportType(StrEnum):
        SAVE = "Save current Scene"
        EXPORT = "Export selected"

    @dataclass(slots=True)
    class Data:
        name: str
        ext: str
        export_type: Literal["Save current Scene", "Export selected"]
        copy_textures: bool
        globalize_textures: bool

    finished = Signal(Data)

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Export", parent)

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

        self.validate()

    def init_widgets(self):
        self.name_edit = QLineEdit("")
        self.name_edit.setPlaceholderText("Asset name")
        self.name_edit.setFixedHeight(30)

        self.export_options = QComboBox()
        self.export_options.addItems([self.ExportType.EXPORT, self.ExportType.SAVE])

        self.copy_textues_check = QCheckBox()
        self.copy_textues_check.setChecked(True)
        self.copy_textues_check.setToolTip(
            "Copy the textures next to the asset and point the scene at the copies"
        )
        self.globalize_textures = QCheckBox()
        self.globalize_textures.setChecked(True)
        self.globalize_textures.setToolTip("Make texture paths absolute before saving")

        buttons = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box = QDialogButtonBox(buttons)
        self.ok_btn = self.button_box.button(QDialogButtonBox.StandardButton.Ok)

    def init_layouts(self):
        self.main_layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()

        self.form_layout.addRow("Name", self.name_edit)
        self.form_layout.addRow("Export Options", self.export_options)
        self.form_layout.addRow("Globalize Textures", self.globalize_textures)
        self.form_layout.addRow("Copy Textures and Repath", self.copy_textues_check)

        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addWidget(self.hint)
        self.main_layout.addWidget(self.button_box)

    def init_signals(self):
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.name_edit.textChanged.connect(self.validate)

    def validate(self):
        self.set_problem(self.ok_btn, name_problem(self.name_edit.text(), "asset"))

    def accept(self) -> None:
        if not self.ok_btn.isEnabled():
            return

        super().accept()
        opt = self.export_options.currentText()
        name, ext = (self.name_edit.text().strip(), "c4d")

        data = self.Data(
            name,
            ext,
            self.ExportType(opt).value,
            self.copy_textues_check.isChecked(),
            self.globalize_textures.isChecked(),
        )

        self.finished.emit(data)


class _CheckListDialog(BaseDialog):
    """A filterable list of checkboxes with select all / none and a counter.

    Subclasses add their own options to `options_layout`.
    """

    def __init__(
        self,
        title: str,
        items: list[str],
        noun: str,
        parent: QWidget | None = None,
    ):
        super().__init__(title, parent)
        self.noun = noun
        self._widgets: list[tuple[QCheckBox, str]] = []

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText(f"Filter {noun}s")
        self.filter_edit.setClearButtonEnabled(True)

        self.scroll_widget = QWidget()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumSize(350, 250)

        self.count_label = QLabel()
        self.select_all_btn = QPushButton("Select All")
        self.deselect_all_btn = QPushButton("Select None")

        buttons = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box = QDialogButtonBox(buttons)
        self.ok_btn = self.button_box.button(QDialogButtonBox.StandardButton.Ok)

        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        for item in items:
            self.add_row(item)
        self.scroll_layout.addStretch()

        if not items:
            empty = QLabel(f"No {noun}s found.")
            empty.setObjectName("hint")
            self.scroll_layout.insertWidget(0, empty)

        self.select_layout = QHBoxLayout()
        self.select_layout.addWidget(self.count_label)
        self.select_layout.addStretch()
        self.select_layout.addWidget(self.select_all_btn)
        self.select_layout.addWidget(self.deselect_all_btn)

        self.options_layout = QVBoxLayout()

        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(self.filter_edit)
        self.main_layout.addWidget(self.scroll_area)
        self.main_layout.addLayout(self.select_layout)
        self.main_layout.addLayout(self.options_layout)
        self.main_layout.addWidget(self.hint)
        self.main_layout.addWidget(self.button_box)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.select_all_btn.clicked.connect(lambda: self.set_visible_checked(True))
        self.deselect_all_btn.clicked.connect(lambda: self.set_visible_checked(False))
        self.filter_edit.textChanged.connect(self.apply_filter)

        self.update_count()

    def add_row(self, name: str):
        # the checkbox text is clickable too, "&" would turn into a mnemonic
        checkbox = QCheckBox(name.replace("&", "&&"))
        checkbox.toggled.connect(self.update_count)
        self.scroll_layout.addWidget(checkbox)
        self._widgets.append((checkbox, name))
        return checkbox

    def apply_filter(self, text: str):
        text = text.strip().lower()
        for check, name in self._widgets:
            check.setVisible(text in name.lower())

    def set_visible_checked(self, checked: bool):
        for check, _ in self._widgets:
            if not check.isHidden():
                check.setChecked(checked)

    def selected_names(self) -> list[str]:
        return [name for check, name in self._widgets if check.isChecked()]

    def update_count(self):
        selected = len(self.selected_names())
        self.count_label.setText(f"{selected} of {len(self._widgets)} selected")
        problem = "" if selected else f"Select at least one {self.noun}."
        self.set_problem(self.ok_btn, problem)

    def accept(self) -> None:
        if not self.ok_btn.isEnabled():
            return
        super().accept()


class ExportMaterialDialog(_CheckListDialog):
    @dataclass(slots=True)
    class Data:
        ext: str
        copy_textures: bool
        materials: list[str]
        globalize_textures: bool

    finished = Signal(Data)

    def __init__(self, materials: list[str], parent: QWidget | None = None):
        super().__init__("Export Materials", materials, "material", parent)
        self.materials = materials

        self.copy_textues_check = QCheckBox("Copy Textures and Repath")
        self.copy_textues_check.setChecked(True)
        self.globalize_textures = QCheckBox("Globalize Textures")
        self.globalize_textures.setChecked(True)

        self.options_layout.addWidget(
            self.copy_textues_check, alignment=Qt.AlignmentFlag.AlignRight
        )
        self.options_layout.addWidget(
            self.globalize_textures, alignment=Qt.AlignmentFlag.AlignRight
        )

    def get_selected_materials(self) -> list[str]:
        return self.selected_names()

    def accept(self) -> None:
        if not self.ok_btn.isEnabled():
            return

        super().accept()
        data = self.Data(
            "c4d",
            self.copy_textues_check.isChecked(),
            self.get_selected_materials(),
            self.globalize_textures.isChecked(),
        )
        self.finished.emit(data)


class ScreenshotResult(NamedTuple):
    geometry: tuple[int, int, int, int]
    folder: Path
    asset_name: str


class ScreenshotDialog(QDialog):
    accepted = Signal(ScreenshotResult)

    # distance from the right / bottom edge that grabs a resize instead of a move
    GRIP = 14
    MIN_SIZE = 100
    BORDER_COLOR = QColor(235, 177, 52)

    def __init__(self, model_path: Path, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        # Only the fill is see-through, border, label and buttons stay opaque.
        # Alpha never drops to 0, fully transparent pixels let clicks fall through.
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        opacity = SettingsManager().ModelSettings.screenshot_opacity
        self._fill = QColor(0, 0, 0, max(1, int(opacity * 255)))

        # cursor feedback on hover, not only while a button is held
        self.setMouseTracking(True)

        self.resize(300, 300)
        self.move(QCursor.pos() - QPoint(self.width() // 2, self.height() // 2))

        self.model_path = model_path

        self._drag_offset = QPoint()
        self._resize = False

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        buttons = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_group = QDialogButtonBox(buttons)
        self.button_group.setStyleSheet(
            "QPushButton {background-color: #333; color: #fff;"
            "border: 1px solid #222; border-radius: 3px; padding: 4px 10px}"
            "QPushButton:hover {background-color: #444}"
        )
        self.button_group.setCursor(Qt.CursorShape.ArrowCursor)
        capture_btn = self.button_group.button(QDialogButtonBox.StandardButton.Ok)
        capture_btn.setText("Capture")
        capture_btn.setDefault(True)

        # keep keyboard focus on the frame so the arrow keys reach keyPressEvent,
        # Enter still triggers the default button through QDialog
        for btn in self.button_group.buttons():
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def init_layouts(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8 + self.GRIP, 8 + self.GRIP)
        self.main_layout.addStretch()
        self.main_layout.addWidget(self.button_group)

    def init_signals(self):
        self.button_group.accepted.connect(self.accept)
        self.button_group.rejected.connect(self.reject)

    def _on_grip(self, pos: QPoint) -> bool:
        return (
            pos.x() >= self.width() - self.GRIP or pos.y() >= self.height() - self.GRIP
        )

    def _update_cursor(self, pos: QPoint):
        if self._resize or self._on_grip(pos):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeAllCursor)

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        rect = self.rect()

        painter.fillRect(rect, self._fill)
        painter.setPen(QPen(self.BORDER_COLOR, 2))
        painter.drawRect(rect.adjusted(1, 1, -1, -1))

        # resize grip in the bottom right corner
        w, h = self.width(), self.height()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.BORDER_COLOR)
        painter.drawPolygon(
            QPolygon([QPoint(w, h - self.GRIP), QPoint(w, h), QPoint(w - self.GRIP, h)])
        )

        # size and shortcuts, on a dark plate so they read on any background
        dpr = self.devicePixelRatioF()
        metrics = painter.fontMetrics()
        hints = (
            "Drag to move, corner or wheel to resize",
            "Enter or double click to capture, Esc to cancel",
        )
        lines = [f"{round(w * dpr)} × {round(h * dpr)} px"]
        lines += [hint for hint in hints if metrics.horizontalAdvance(hint) <= w - 32]

        text_w = max(metrics.horizontalAdvance(line) for line in lines)
        text_h = metrics.lineSpacing() * len(lines)
        text_rect = QRect(8, 8, text_w + 8, text_h + 4)

        painter.setBrush(QColor(0, 0, 0, 160))
        painter.drawRoundedRect(text_rect, 3, 3)
        painter.setPen(Qt.GlobalColor.white)
        painter.drawText(
            text_rect.adjusted(4, 2, -4, -2),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "\n".join(lines),
        )

    def accept(self):
        self.accepted.emit(
            ScreenshotResult(
                (
                    self.x(),
                    self.y(),
                    self.width(),
                    self.height(),
                ),
                self.model_path.parent,
                self.model_path.stem,
            )
        )

        super().accept()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        pos = event.position().toPoint()
        if self._on_grip(pos):
            self._resize = True
        else:
            self._drag_offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position().toPoint()

        if not event.buttons() & Qt.MouseButton.LeftButton:
            self._update_cursor(pos)
            return

        if self._resize:
            # thumbnails are square, so the frame stays square too
            self._set_size(max(pos.x(), pos.y()))
        else:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._resize = False
        self._update_cursor(event.position().toPoint())

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.accept()

    def wheelEvent(self, event: QWheelEvent):
        step = 10 if event.angleDelta().y() > 0 else -10
        self._set_size(self.width() + step)

    def keyPressEvent(self, event: QKeyEvent):
        # arrows nudge the frame, shift for bigger steps, ctrl resizes instead
        step = 10 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
        offsets = {
            Qt.Key.Key_Left.value: QPoint(-step, 0),
            Qt.Key.Key_Right.value: QPoint(step, 0),
            Qt.Key.Key_Up.value: QPoint(0, -step),
            Qt.Key.Key_Down.value: QPoint(0, step),
        }
        offset = offsets.get(event.key())
        if offset is None:
            # Enter / Esc are handled by QDialog
            super().keyPressEvent(event)
            return

        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._set_size(self.width() + offset.x() - offset.y())
        else:
            self.move(self.pos() + offset)

    def _set_size(self, size: int):
        size = max(self.MIN_SIZE, size)
        self.resize(size, size)


LEGACY_RENDER_SCENE = "Path/to/render/scene"


class SettingsDialog(BaseDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__("Settings", parent)
        self.settings = SettingsManager()

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

        self.load()

    def init_widgets(self):
        self.core_settings = QGroupBox("Core Settings")
        self.socket_port = QSpinBox()
        self.socket_port.setRange(1, 2**16 - 1)
        self.socket_port.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.addr = QLineEdit()
        self.addr.setPlaceholderText("localhost")
        self.root_path = QLineEdit()
        self.root_path.setPlaceholderText("Folder for the database and logs")
        self.browse_root = QPushButton(QIcon(":icons/tabler-icon-folder-open.png"), "")
        self.browse_root.setToolTip("Browse")

        self.material_settings = QGroupBox("Material Settings")
        self.render_scene = QLineEdit()
        self.render_scene.setPlaceholderText("Cinema 4D scene used to render previews")
        self.browse_render_scene = QPushButton(
            QIcon(":icons/tabler-icon-folder-open.png"), ""
        )
        self.browse_render_scene.setToolTip("Browse")
        self.render_object = QLineEdit()
        self.render_object.setPlaceholderText("Name of the shaderball object")
        self.render_cam = QLineEdit()
        self.render_cam.setPlaceholderText("Name of the render camera")
        self.render_resolution_x = QSpinBox()
        self.render_resolution_y = QSpinBox()
        for spin in (self.render_resolution_x, self.render_resolution_y):
            spin.setFixedWidth(90)
            spin.setRange(1, 5000)
            spin.setSuffix(" px")
            spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

        self.model_settings = QGroupBox("Model Settings")
        self.screenshot_opacity = QSpinBox()
        self.screenshot_opacity.setRange(0, 100)
        self.screenshot_opacity.setSuffix(" %")
        self.screenshot_opacity.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons
        )
        self.screenshot_opacity.setToolTip(
            "How dark the screenshot frame is, 0 % is fully see-through"
        )

        buttons = (
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box = QDialogButtonBox(buttons)
        self.apply_btn = self.button_box.button(QDialogButtonBox.StandardButton.Apply)

    def init_layouts(self):
        self.settings_groups_layout = QVBoxLayout(self)

        self.root_layout = QHBoxLayout()
        self.root_layout.addWidget(self.root_path)
        self.root_layout.addWidget(self.browse_root)

        self.core_settings_layout = QFormLayout(self.core_settings)
        self.core_settings_layout.addRow("Cinema 4D socket address", self.addr)
        self.core_settings_layout.addRow("Cinema 4D socket port", self.socket_port)
        self.core_settings_layout.addRow("Root Path", self.root_layout)

        self.render_scene_layout = QHBoxLayout()
        self.render_scene_layout.addWidget(self.render_scene)
        self.render_scene_layout.addWidget(self.browse_render_scene)

        self.resolution_layout = QHBoxLayout()
        self.resolution_layout.addWidget(self.render_resolution_x)
        self.resolution_layout.addWidget(QLabel("×"))
        self.resolution_layout.addWidget(self.render_resolution_y)
        self.resolution_layout.addStretch()

        self.material_settings_layout = QFormLayout(self.material_settings)
        self.material_settings_layout.addRow(
            QLabel("Render Scene"), self.render_scene_layout
        )
        self.material_settings_layout.addRow(
            QLabel("Render Object"), self.render_object
        )
        self.material_settings_layout.addRow(QLabel("Render Camera"), self.render_cam)
        self.material_settings_layout.addRow(
            QLabel("Render Resolution"), self.resolution_layout
        )

        self.model_settings_layout = QFormLayout(self.model_settings)
        self.model_settings_layout.addRow(
            QLabel("Screenshot Frame Opacity"), self.screenshot_opacity
        )

        self.settings_groups_layout.addWidget(self.core_settings)
        self.settings_groups_layout.addWidget(self.material_settings)
        self.settings_groups_layout.addWidget(self.model_settings)
        self.settings_groups_layout.addStretch()
        self.settings_groups_layout.addWidget(self.button_box)
        self.setMinimumWidth(560)

    def init_signals(self):
        self.browse_render_scene.clicked.connect(self.open_render_scene)
        self.browse_root.clicked.connect(self.set_root_dir)
        self.button_box.accepted.connect(self.store_and_close)
        self.button_box.rejected.connect(self.reject)
        self.apply_btn.clicked.connect(self.store)

    def open_render_scene(self):
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Browse Render Scene",
            self.render_scene.text(),
            filter="Cinema 4D Files (*.c4d)",
        )
        if not file:
            return

        self.render_scene.setText(file)

    def set_root_dir(self):
        # only fills the field, the setting changes on OK / Apply
        dir = QFileDialog.getExistingDirectory(
            self, "Browse Folder", self.root_path.text()
        )
        if not dir:
            return

        self.root_path.setText(dir)

    def load(self):
        core = self.settings.CoreSettings
        mat = self.settings.MaterialSettings
        mod = self.settings.ModelSettings

        self.socket_port.setValue(core.socket_port)
        self.addr.setText(core.socket_addr)
        self.root_path.setText(core.root_path)

        # older configs saved the placeholder as the value
        if mat.render_scene != LEGACY_RENDER_SCENE:
            self.render_scene.setText(mat.render_scene)
        self.render_object.setText(mat.render_object)
        self.render_cam.setText(mat.render_cam)
        self.render_resolution_x.setValue(mat.render_res_x)
        self.render_resolution_y.setValue(mat.render_res_y)

        self.screenshot_opacity.setValue(round(mod.screenshot_opacity * 100))

    def store(self):
        core = self.settings.CoreSettings
        mat = self.settings.MaterialSettings
        mod = self.settings.ModelSettings

        core.socket_port = self.socket_port.value()
        core.socket_addr = self.addr.text().strip() or "localhost"
        root = self.root_path.text().strip()
        if root and root != core.root_path:
            core.set_root_path(root)

        mat.render_res_x = self.render_resolution_x.value()
        mat.render_res_y = self.render_resolution_y.value()
        mat.render_object = self.render_object.text()
        mat.render_scene = self.render_scene.text()
        mat.render_cam = self.render_cam.text()

        mod.screenshot_opacity = self.screenshot_opacity.value() / 100

        # don't wait for a clean shutdown to persist them
        self.settings.save_settings()

    def store_and_close(self):
        self.store()
        self.accept()


class BackupDialog(BaseDialog):
    imported = Signal(Path)
    opened = Signal(Path)
    referenced = Signal(Path)

    def __init__(
        self,
        archive_path: Path,
        parent: QWidget | None = None,
        allow_reference: bool = True,
    ):
        super().__init__("Backup Viewer", parent)
        self.archive_path = archive_path
        self.allow_reference = allow_reference
        self.elements: dict[str, tuple[QTreeWidgetItem, Backup]] = {}
        self.backup = BackupManager()

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

        self.update_buttons()

    def init_widgets(self):
        self.open_model = QPushButton("Open")
        self.import_model = QPushButton("Import")
        self.reference_model = QPushButton("Reference")
        self.reference_model.setVisible(self.allow_reference)

        self.tree_widget = QTreeWidget(self)
        self.tree_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.tree_widget.setHeaderLabels(["Backup", "Version", "Modified"])
        self.tree_widget.setMinimumSize(450, 300)

        # no pool selected comes in as Path(), which would scan the working dir
        has_pool = self.archive_path != Path() and self.archive_path.is_dir()
        pool_backups = self.backup.load_from_pool(self.archive_path) if has_pool else []

        bold = QFont()
        bold.setBold(True)
        for pool_backup in pool_backups:
            archive_item = QTreeWidgetItem(
                self.tree_widget,
                [pool_backup[0].original_name, f"{len(pool_backup)} backups"],
            )
            archive_item.setFont(0, bold)
            # newest first, that's usually the one you are after
            for asset_backup in sorted(pool_backup, key=lambda b: -b.version):
                item = QTreeWidgetItem(
                    archive_item,
                    [
                        asset_backup.name,
                        str(asset_backup.version),
                        self._modified(asset_backup.path),
                    ],
                )
                self.elements[asset_backup.name] = (item, asset_backup)

        self.tree_widget.expandAll()
        for column in range(self.tree_widget.columnCount()):
            self.tree_widget.resizeColumnToContents(column)

        self.empty_label = QLabel(
            "No backups in this pool yet.\n"
            "Right click an asset and choose “Create Backup” to make one."
        )
        self.empty_label.setObjectName("hint")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        has_backups = bool(pool_backups)
        self.tree_widget.setVisible(has_backups)
        self.empty_label.setVisible(not has_backups)

    @staticmethod
    def _modified(path: Path) -> str:
        try:
            modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
            return modified.astimezone().strftime("%Y-%m-%d %H:%M")
        except OSError:
            return ""

    def init_layouts(self):
        self.main_layout = QVBoxLayout(self)
        self.select_layout = QHBoxLayout()

        self.hint.setWordWrap(False)
        self.select_layout.addWidget(self.hint)
        self.select_layout.addStretch()
        self.select_layout.addWidget(self.open_model)
        self.select_layout.addWidget(self.import_model)
        self.select_layout.addWidget(self.reference_model)

        self.main_layout.addWidget(self.tree_widget)
        self.main_layout.addWidget(self.empty_label)
        self.main_layout.addLayout(self.select_layout)

    def init_signals(self):
        self.import_model.clicked.connect(lambda: self.import_selection())
        self.reference_model.clicked.connect(lambda: self.reference_selection())
        self.open_model.clicked.connect(lambda: self.open_selection())
        self.tree_widget.itemSelectionChanged.connect(self.update_buttons)
        self.tree_widget.itemDoubleClicked.connect(self.on_double_click)

    def update_buttons(self):
        selection = self.tree_widget.selectedItems()
        valid = bool(selection) and self.get_item_level(selection[0]) == 1
        for btn in (self.open_model, self.import_model, self.reference_model):
            btn.setEnabled(valid)

        has_backups = bool(self.elements)
        self.hint.setText("Select a backup version." if has_backups else "")
        self.hint.setVisible(has_backups and not valid)

    def on_double_click(self, item: QTreeWidgetItem, column: int):
        if self.get_item_level(item) == 1:
            self.open_selection()

    def import_selection(self):
        path = self.get_selected_path()
        if not path:
            Logger.error(f"can't import model, path is: {path}")
            return
        self.imported.emit(path)
        self.close()

    def reference_selection(self):
        path = self.get_selected_path()
        if not path:
            Logger.error(f"can't reference model, path is: {path}")
            return
        self.referenced.emit(path)
        self.close()

    def open_selection(self):
        path = self.get_selected_path()
        if not path:
            Logger.error(f"can't open model, path is: {path}")
            return
        self.opened.emit(path)
        self.close()

    def get_item_level(self, item: QTreeWidgetItem):
        level = 0
        while i := item.parent():
            item = i
            level += 1
        return level

    def get_selected_path(self) -> Path | None:
        selection = self.tree_widget.selectedItems()
        if not selection:
            Logger.error("select an archived version first")
            return None

        selected = selection[0]
        if not self.get_item_level(selected) == 1:
            Logger.error("select an archived version instead of the group")
            return None

        item_name = selected.text(0)
        element = self.elements.get(item_name)
        if not element:
            Logger.error(f"no archived version found for {item_name}")
            return None

        _, backup = element
        return backup.path


class CreateBackupDialog(BaseDialog):
    # "No" opens without a backup, while Cancel / Esc / closing opens nothing
    declined = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Create Backup", parent)

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        self.label = QLabel("Would you like to create a backup before opening?")

        buttons = (
            QDialogButtonBox.StandardButton.Yes
            | QDialogButtonBox.StandardButton.No
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box = QDialogButtonBox(buttons)
        self.no_btn = self.button_box.button(QDialogButtonBox.StandardButton.No)

    def init_layouts(self):
        self.main_layout = QVBoxLayout(self)

        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.button_box)

    def init_signals(self):
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.no_btn.clicked.connect(self.on_declined)

    def on_declined(self):
        self.declined.emit()
        self.reject()


class ImportModelsDialog(_CheckListDialog):
    finished = Signal(list)

    def __init__(self, models: dict[str, Path], parent: QWidget | None = None):
        super().__init__("Import Models", list(models), "model", parent)
        self.models = models

        for check, name in self._widgets:
            check.setToolTip(str(models[name]))

    def get_selected(self) -> list[Path]:
        return [self.models[name] for name in self.selected_names()]

    def accept(self) -> None:
        if not self.ok_btn.isEnabled():
            return

        super().accept()
        self.finished.emit(self.get_selected())


class ProgressDialog(QProgressDialog):
    def __init__(
        self,
        labelText: str,
        minimum: int,
        maximum: int,
        parent: QWidget | None = None,
    ):
        super().__init__(
            labelText,
            "Cancel",
            minimum,
            maximum,
            parent,
        )
        self.setWindowModality(Qt.WindowModality.WindowModal)
        # self.setCancelButton(None)
        self.setWindowIcon(QIcon(":icons/apic_logo.png"))
        self.setStyleSheet(DIALOG_STYLE)
        self.setWindowTitle("Progress")


class TagDialog(BaseDialog):
    tags_selected = Signal(list)
    tag_created = Signal(str)

    def __init__(
        self,
        tags: list[str],
        selected: list[str] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__("Tags", parent)

        self.all_tags = tags
        self._button_cache: dict[str, QPushButton] = {}
        self._new_tags: list[str] = []

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

        self.add_tags(self.all_tags)
        for tag in selected or []:
            if tag not in self._button_cache:
                # assigned to the asset but missing from the tag table
                self.add_tags([tag])
            self._button_cache[tag].setChecked(True)

        self.name_edit.setFocus()

    def init_widgets(self):
        self.name_edit = QLineEdit("")
        self.name_edit.setPlaceholderText("Search or create a tag")
        self.name_edit.setClearButtonEnabled(True)

        self.scroll_widget = QWidget()
        self.scroll_area = QScrollArea()
        self.scroll_area.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumSize(350, 200)
        self.scroll_area.setWidget(self.scroll_widget)

        buttons = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box = QDialogButtonBox(buttons)

        # Enter in the search field picks / creates a tag instead of closing
        for btn in self.button_box.buttons():
            btn.setAutoDefault(False)
            btn.setDefault(False)

    def init_layouts(self):
        self.tag_layout = FlowLayout(self.scroll_widget)
        self.tag_layout.setContentsMargins(4, 4, 4, 4)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.addWidget(self.name_edit)
        self.main_layout.addWidget(self.hint)
        self.main_layout.addWidget(self.scroll_area)
        self.main_layout.addWidget(self.button_box)

    def init_signals(self):
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.name_edit.textChanged.connect(self.on_text_changed)
        self.name_edit.returnPressed.connect(self.on_return)

    def _find(self, text: str) -> str | None:
        """The existing tag matching `text`, ignoring case."""
        text = text.strip().lower()
        return next((t for t in self._button_cache if t.lower() == text), None)

    def on_text_changed(self, text: str):
        needle = text.strip().lower()
        for tag, btn in self._button_cache.items():
            btn.setVisible(needle in tag.lower())

        if needle and self._find(needle) is None:
            self.hint.setText(f"Press Enter to create the tag “{text.strip()}”.")
            self.hint.setVisible(True)
        else:
            self.hint.setVisible(False)

    def on_return(self):
        text = self.name_edit.text().strip()
        if not text:
            self.accept()
            return

        tag = self._find(text)
        if tag is None:
            tag = text
            self._new_tags.append(tag)
            self.add_tags([tag])

        self._button_cache[tag].setChecked(True)
        self.name_edit.clear()

    def accept(self) -> None:
        tags = [tag for tag, btn in self._button_cache.items() if btn.isChecked()]

        for tag in self._new_tags:
            self.tag_created.emit(tag)

        self.tags_selected.emit(tags)
        super().accept()

    def add_tags(self, tags: list[str]):
        for tag in tags:
            btn = QPushButton(tag.replace("&", "&&"))
            btn.setCheckable(True)
            btn.setAutoDefault(False)
            self._button_cache[tag] = btn
            self.tag_layout.addWidget(btn)


class RenameAssetDialog(BaseDialog):
    asset_renamed = Signal(str)

    def __init__(self, old_name: str, parent: QWidget | None = None):
        super().__init__("Rename Asset", parent)

        self.old_name = old_name

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

        self.name_edit.selectAll()
        self.validate()

    def init_widgets(self):
        self.name_edit = QLineEdit(self.old_name)
        self.name_edit.setMinimumWidth(250)

        buttons = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box = QDialogButtonBox(buttons)
        self.ok_btn = self.button_box.button(QDialogButtonBox.StandardButton.Ok)

    def init_layouts(self):
        self.main_layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()

        self.form_layout.addRow(QLabel("New Name"), self.name_edit)
        self.form_layout.setContentsMargins(0, 5, 0, 5)

        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addWidget(self.hint)
        self.main_layout.addWidget(self.button_box)

    def init_signals(self):
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.name_edit.textChanged.connect(self.validate)

    def validate(self):
        name = self.name_edit.text().strip()
        problem = name_problem(name, "new")
        if not problem and name == self.old_name:
            # nothing to point out, OK just has nothing to do yet
            self.ok_btn.setEnabled(False)
            self.hint.setVisible(False)
            return

        self.set_problem(self.ok_btn, problem)

    def accept(self) -> None:
        if not self.ok_btn.isEnabled():
            return

        self.asset_renamed.emit(self.name_edit.text().strip())
        super().accept()


class ExportRenderSettingsDialog(BaseDialog):
    @dataclass
    class Data:
        name: str
        export_c4d: bool
        export_rs: bool

    finished = Signal(Data)

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Export Render Settings", parent)

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

        self.validate()

    def init_widgets(self):
        self.name_edit = QLineEdit("")
        self.name_edit.setPlaceholderText("Preset name")
        self.name_edit.setFixedHeight(30)

        self.c4d_settings = QCheckBox()
        self.c4d_settings.setChecked(True)
        self.rs_settings = QCheckBox()
        self.rs_settings.setChecked(True)

        buttons = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box = QDialogButtonBox(buttons)
        self.ok_btn = self.button_box.button(QDialogButtonBox.StandardButton.Ok)

    def init_layouts(self):
        self.main_layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()

        self.form_layout.addRow("Name", self.name_edit)
        self.form_layout.addRow("Cinema 4D Settings", self.c4d_settings)
        self.form_layout.addRow("Redshift Settings", self.rs_settings)

        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addWidget(self.hint)
        self.main_layout.addWidget(self.button_box)

    def init_signals(self):
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.name_edit.textChanged.connect(self.validate)
        self.c4d_settings.toggled.connect(self.validate)
        self.rs_settings.toggled.connect(self.validate)

    def validate(self):
        problem = name_problem(self.name_edit.text(), "preset")
        if not problem and not (
            self.c4d_settings.isChecked() or self.rs_settings.isChecked()
        ):
            problem = "Choose at least one kind of settings to export."

        self.set_problem(self.ok_btn, problem)

    def accept(self) -> None:
        if not self.ok_btn.isEnabled():
            return

        super().accept()

        data = self.Data(
            self.name_edit.text().strip(),
            self.c4d_settings.isChecked(),
            self.rs_settings.isChecked(),
        )

        self.finished.emit(data)


HELP_TEXT = """
<h3>Getting around</h3>
<ul>
<li>The sidebar switches between asset types, the dropdown at the top picks the pool.</li>
<li>Click an asset to see its details, notes and tags on the right.</li>
<li>Right click an asset to import, open, reference, back up, rename or delete it.</li>
<li>The button at the bottom of the sidebar shows the Cinema 4D connection,
click it to reconnect.</li>
</ul>
<h3>Shortcuts</h3>
<table cellspacing="4">
<tr><td><b>Ctrl+F</b></td><td>Search the current pool</td></tr>
<tr><td><b>Esc</b></td><td>Clear the search</td></tr>
<tr><td><b>Ctrl+S</b></td><td>Save the asset notes</td></tr>
</table>
<h3>Screenshot frame</h3>
<table cellspacing="4">
<tr><td><b>Drag</b></td><td>Move the frame</td></tr>
<tr><td><b>Corner, wheel, Ctrl+Arrows</b></td><td>Resize</td></tr>
<tr><td><b>Arrows</b></td><td>Nudge by 1 px, with Shift by 10 px</td></tr>
<tr><td><b>Enter, double click</b></td><td>Capture</td></tr>
<tr><td><b>Esc</b></td><td>Cancel</td></tr>
</table>
"""


class HelpDialog(BaseDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__("Help", parent)

        label = QLabel(HELP_TEXT)
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setMinimumWidth(420)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(label)
        layout.addWidget(button_box)


def files_dialog(
    title: str = "Select Files", parent: QWidget | None = None
) -> tuple[list[str], str]:
    folder = QFileDialog.getOpenFileNames(parent, title)
    return folder


def folder_dialog(title: str = "Select Folder", parent: QWidget | None = None) -> str:
    folder = QFileDialog.getExistingDirectory(parent, title)
    return folder
