from __future__ import annotations

from pathlib import Path
from typing import Union

from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QRect,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QFontMetrics, QImage, QPainter, QPen
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from apic_studio.core import Asset

# item data roles, offset from UserRole
KEY_ROLE = int(Qt.ItemDataRole.UserRole)
ASSET_ROLE = KEY_ROLE + 1
FILE_ROLE = KEY_ROLE + 2
SIZE_ROLE = KEY_ROLE + 3
TYPE_ROLE = KEY_ROLE + 4
IMAGE_ROLE = KEY_ROLE + 5
# the whole row in one call, so painting a tile crosses the proxy once
ROW_ROLE = KEY_ROLE + 6

Index = Union[QModelIndex, QPersistentModelIndex]


class AssetRow:
    """One tile's worth of data. `file` is the asset folder until it loads.

    Everything the delegate draws is kept ready to paint: the labels are built
    once here rather than per frame, and the elided name is cached until either
    the tile width or the delegate's font generation changes.
    """

    __slots__ = (
        "asset",
        "elided",
        "elided_gen",
        "elided_width",
        "file",
        "image",
        "key",
        "requested",
        "size",
        "size_text",
        "type",
        "type_text",
    )

    def __init__(self, path: Path) -> None:
        self.key = path.stem
        self.asset = path
        self.file = path
        self.size = ""
        self.type = ""
        self.size_text = "Size: "
        self.type_text = "Type: "
        self.image: QImage | None = None
        # the viewport sets this when it asks the loader for the thumbnail, so
        # a tile is never queued twice while it waits
        self.requested = False

        self.elided = ""
        self.elided_width = -1
        self.elided_gen = -1

    def set_asset(self, asset: Asset) -> None:
        self.key = asset.path.stem
        self.asset = asset.path
        self.file = asset.file
        self.size = asset.format_size()
        self.type = asset.suffix
        self.size_text = f"Size: {self.size}"
        self.type_text = f"Type: {self.type}"
        self.image = asset.icon
        self.requested = True

        # the name may have changed, drop the elision cached for the old one
        self.elided_width = -1


class AssetModel(QAbstractListModel):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._rows: list[AssetRow] = []
        self._by_key: dict[str, int] = {}

    def rowCount(self, parent: Index = QModelIndex()) -> int:
        if (
            isinstance(parent, (QModelIndex, QPersistentModelIndex))
            and parent.isValid()
        ):
            return 0
        return len(self._rows)

    def data(self, index: Index, role: int = Qt.ItemDataRole.DisplayRole):
        row = self.row_at(index)
        if row is None:
            return None

        if role == ROW_ROLE:
            return row
        if role in (Qt.ItemDataRole.DisplayRole, KEY_ROLE):
            return row.key
        if role == Qt.ItemDataRole.ToolTipRole:
            return str(row.file)
        if role == ASSET_ROLE:
            return row.asset
        if role == FILE_ROLE:
            return row.file
        if role == SIZE_ROLE:
            return row.size
        if role == TYPE_ROLE:
            return row.type
        if role == IMAGE_ROLE:
            return row.image

        return None

    # --- lookups ---

    def row_at(self, index: Index) -> AssetRow | None:
        if not index.isValid():
            return None

        i = index.row()
        if not 0 <= i < len(self._rows):
            return None

        return self._rows[i]

    def assets(self) -> list[Path]:
        return [row.asset for row in self._rows]

    # --- mutations ---

    def set_assets(self, paths: list[Path]) -> None:
        self.beginResetModel()
        self._rows = [AssetRow(p) for p in paths]
        self._reindex()
        self.endResetModel()

    def update_asset(self, asset: Asset) -> AssetRow | None:
        i = self._by_key.get(asset.path.stem)
        if i is None:
            return None

        row = self._rows[i]
        row.set_asset(asset)

        idx = self.index(i, 0)
        self.dataChanged.emit(idx, idx)

        return row

    def rename(self, asset_dir: Path, asset: Asset) -> bool:
        for i, row in enumerate(self._rows):
            if row.asset != asset_dir:
                continue

            row.set_asset(asset)
            self._reindex()

            idx = self.index(i, 0)
            self.dataChanged.emit(idx, idx)

            return True

        return False

    def remove(self, asset_dir: Path) -> bool:
        for i, row in enumerate(self._rows):
            if row.asset != asset_dir:
                continue

            self.beginRemoveRows(QModelIndex(), i, i)
            del self._rows[i]
            self._reindex()
            self.endRemoveRows()

            return True

        return False

    def _reindex(self) -> None:
        self._by_key = {row.key: i for i, row in enumerate(self._rows)}


class AssetDelegate(QStyledItemDelegate):
    """Paints an asset tile: thumbnail, name, then size and type.

    A tile is only painted when it is on screen, which makes the delegate the
    one place that knows what the user is actually looking at. It reports the
    span of rows each repaint covered so the viewport can load those thumbnails
    and leave the rest of the pool alone.
    """

    rows_painted = Signal(int, int)  # first, last row of the repaint that ended

    ICON_AREA = 200
    NAME_HEIGHT = 26
    INFO_HEIGHT = 24
    WIDTH = 200

    BACKGROUND = QColor(60, 60, 60)
    BACKGROUND_HOVER = QColor(82, 82, 82)
    HOVER = QColor(128, 128, 128)
    SELECTED = QColor(235, 177, 52)
    ACCENT = QColor(235, 177, 52)
    BORDER = QColor(0, 0, 0)
    TEXT = QColor(255, 255, 255)
    HOVER_OUTLINE = 2

    NAME_POINT_SIZE = 10
    INFO_POINT_SIZE = 8

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # building a QFont and its metrics is far too expensive to redo for
        # every tile of every frame, so they are cached until the font changes
        self._base_font: QFont | None = None
        self._name_font = QFont()
        self._name_metrics = QFontMetrics(self._name_font)
        self._info_font = QFont()
        # bumped on a font change, which is what stales the rows' cached elision
        self._font_gen = 0

        self._painted_first = -1
        self._painted_last = -1

    def _note_painted(self, row: int) -> None:
        """Widen the span this repaint has covered, reported once it finishes."""
        if self._painted_first < 0:
            self._painted_first = self._painted_last = row
            # a zero timer, so the span goes out after the paint event rather
            # than from inside it, where touching the model would re-enter
            QTimer.singleShot(0, self._flush_painted)
            return

        if row < self._painted_first:
            self._painted_first = row
        elif row > self._painted_last:
            self._painted_last = row

    def _flush_painted(self) -> None:
        first, last = self._painted_first, self._painted_last
        self._painted_first = self._painted_last = -1

        if first >= 0:
            self.rows_painted.emit(first, last)

    def _sync_fonts(self, base: QFont) -> None:
        if self._base_font is not None and self._base_font == base:
            return

        self._base_font = QFont(base)

        self._name_font = QFont(base)
        self._name_font.setPointSize(self.NAME_POINT_SIZE)
        self._name_metrics = QFontMetrics(self._name_font)

        self._info_font = QFont(base)
        self._info_font.setPointSize(self.INFO_POINT_SIZE)

        self._font_gen += 1

    def sizeHint(self, option: QStyleOptionViewItem, index: Index) -> QSize:
        return QSize(self.WIDTH, self.ICON_AREA + self.NAME_HEIGHT + self.INFO_HEIGHT)

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: Index
    ) -> None:
        row = index.data(ROW_ROLE)
        if not isinstance(row, AssetRow):
            painter.fillRect(option.rect, self.BACKGROUND)
            return

        self._note_painted(index.row())
        self._sync_fonts(option.font)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        rect = option.rect
        state = option.state
        hovered = bool(state & QStyle.StateFlag.State_MouseOver)
        selected = bool(state & QStyle.StateFlag.State_Selected)

        icon_rect = QRect(rect.x(), rect.y(), rect.width(), self.ICON_AREA)
        name_rect = QRect(
            rect.x(), icon_rect.bottom() + 1, rect.width(), self.NAME_HEIGHT
        )
        info_rect = QRect(
            rect.x(), name_rect.bottom() + 1, rect.width(), self.INFO_HEIGHT
        )

        painter.fillRect(rect, self.BACKGROUND_HOVER if hovered else self.BACKGROUND)
        if selected:
            painter.fillRect(icon_rect, self.SELECTED)
        elif hovered:
            painter.fillRect(icon_rect, self.HOVER)

        image = row.image
        if image is not None and not image.isNull():
            # the loader already decoded to the display size, so just centre it
            x = icon_rect.x() + (icon_rect.width() - image.width()) // 2
            y = icon_rect.y() + (icon_rect.height() - image.height()) // 2
            painter.drawImage(x, y, image)

        painter.setPen(self.BORDER)
        painter.drawRect(rect.adjusted(0, 0, -1, -1))
        painter.drawLine(
            rect.left(), icon_rect.bottom(), rect.right(), icon_rect.bottom()
        )
        painter.drawLine(
            rect.left(), name_rect.bottom(), rect.right(), name_rect.bottom()
        )
        middle = rect.left() + rect.width() // 2
        painter.drawLine(middle, info_rect.top(), middle, info_rect.bottom())

        painter.setPen(self.TEXT)
        painter.setFont(self._name_font)

        width = name_rect.width()
        if row.elided_width != width or row.elided_gen != self._font_gen:
            # elidedText has to shape the string, so keep the result around
            row.elided = self._name_metrics.elidedText(
                row.key, Qt.TextElideMode.ElideRight, width - 8
            )
            row.elided_width = width
            row.elided_gen = self._font_gen

        painter.drawText(name_rect, Qt.AlignmentFlag.AlignCenter, row.elided)

        painter.setFont(self._info_font)
        size_rect = QRect(
            info_rect.x(), info_rect.y(), rect.width() // 2, info_rect.height()
        )
        type_rect = QRect(
            middle, info_rect.y(), rect.width() - rect.width() // 2, info_rect.height()
        )
        painter.drawText(size_rect, Qt.AlignmentFlag.AlignCenter, row.size_text)
        painter.drawText(type_rect, Qt.AlignmentFlag.AlignCenter, row.type_text)

        if hovered:
            # outline the whole tile, a thumbnail can cover most of the fill
            inset = self.HOVER_OUTLINE // 2
            painter.setPen(QPen(self.ACCENT, self.HOVER_OUTLINE))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect.adjusted(inset, inset, -inset - 1, -inset - 1))

        painter.restore()
