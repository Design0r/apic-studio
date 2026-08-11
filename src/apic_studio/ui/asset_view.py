from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QRect,
    QSize,
    Qt,
)
from PySide6.QtGui import QColor, QFontMetrics, QImage, QPainter, QPen
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from apic_studio.core import Asset

# item data roles, offset from UserRole
KEY_ROLE = int(Qt.ItemDataRole.UserRole)
ASSET_ROLE = KEY_ROLE + 1
FILE_ROLE = KEY_ROLE + 2
SIZE_ROLE = KEY_ROLE + 3
TYPE_ROLE = KEY_ROLE + 4
IMAGE_ROLE = KEY_ROLE + 5

Index = Union[QModelIndex, QPersistentModelIndex]


class AssetRow:
    """One tile's worth of data. `file` is the asset folder until it loads."""

    __slots__ = ("key", "asset", "file", "size", "type", "image")

    def __init__(self, path: Path) -> None:
        self.key = path.stem
        self.asset = path
        self.file = path
        self.size = ""
        self.type = ""
        self.image: Optional[QImage] = None


class AssetModel(QAbstractListModel):
    def __init__(self, parent: Optional[QObject] = None) -> None:
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

    def row_at(self, index: Index) -> Optional[AssetRow]:
        if not index.isValid():
            return None

        i = index.row()
        if not 0 <= i < len(self._rows):
            return None

        return self._rows[i]

    def files(self) -> list[Path]:
        return [row.file for row in self._rows]

    # --- mutations ---

    def set_assets(self, paths: list[Path]) -> None:
        self.beginResetModel()
        self._rows = [AssetRow(p) for p in paths]
        self._reindex()
        self.endResetModel()

    def update_asset(self, asset: Asset) -> bool:
        i = self._by_key.get(asset.path.stem)
        if i is None:
            return False

        row = self._rows[i]
        row.file = asset.file
        row.size = asset.format_size()
        row.type = asset.suffix
        row.image = asset.icon

        idx = self.index(i, 0)
        self.dataChanged.emit(idx, idx)

        return True

    def rename(self, asset_dir: Path, asset: Asset) -> bool:
        for i, row in enumerate(self._rows):
            if row.asset != asset_dir:
                continue

            row.key = asset.path.stem
            row.asset = asset.path
            row.file = asset.file
            row.size = asset.format_size()
            row.type = asset.suffix
            row.image = asset.icon
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
    """Paints an asset tile: thumbnail, name, then size and type."""

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

    def sizeHint(self, option: QStyleOptionViewItem, index: Index) -> QSize:
        return QSize(self.WIDTH, self.ICON_AREA + self.NAME_HEIGHT + self.INFO_HEIGHT)

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: Index
    ) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        rect = option.rect  # type: ignore[attr-defined]
        state = option.state  # type: ignore[attr-defined]
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

        image = index.data(IMAGE_ROLE)
        if isinstance(image, QImage) and not image.isNull():
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
        font = painter.font()

        font.setPointSize(10)
        painter.setFont(font)
        name = QFontMetrics(font).elidedText(
            str(index.data(Qt.ItemDataRole.DisplayRole) or ""),
            Qt.TextElideMode.ElideRight,
            name_rect.width() - 8,
        )
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignCenter, name)

        font.setPointSize(8)
        painter.setFont(font)
        size_rect = QRect(
            info_rect.x(), info_rect.y(), rect.width() // 2, info_rect.height()
        )
        type_rect = QRect(
            middle, info_rect.y(), rect.width() - rect.width() // 2, info_rect.height()
        )
        painter.drawText(
            size_rect, Qt.AlignmentFlag.AlignCenter, f"Size: {index.data(SIZE_ROLE)}"
        )
        painter.drawText(
            type_rect, Qt.AlignmentFlag.AlignCenter, f"Type: {index.data(TYPE_ROLE)}"
        )

        if hovered:
            # outline the whole tile, a thumbnail can cover most of the fill
            inset = self.HOVER_OUTLINE // 2
            painter.setPen(QPen(self.ACCENT, self.HOVER_OUTLINE))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect.adjusted(inset, inset, -inset - 1, -inset - 1))

        painter.restore()
