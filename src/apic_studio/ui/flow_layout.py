from typing import Optional

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtWidgets import QApplication, QLayout, QLayoutItem, QSizePolicy, QWidget


class FlowLayout(QLayout):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(0, 0, 0, 0)
        self._item_list: list[QLayoutItem] = []

    def __del__(self) -> None:
        item: Optional[QLayoutItem] = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item: QLayoutItem) -> None:
        self._item_list.append(item)

    def count(self) -> int:
        return len(self._item_list)

    def itemAt(self, index: int) -> Optional[QLayoutItem]:
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index: int) -> Optional[QLayoutItem]:
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        height: int = self._do_layout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size: QSize = QSize()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        size += QSize(
            2 * self.contentsMargins().top(), 2 * self.contentsMargins().top()
        )
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        x = rect.x()
        y = rect.y()
        line_height = 0

        # cache spacing + style info once
        spacing = self.spacing()
        policy = QSizePolicy.ControlType.PushButton
        style = (
            self.parentWidget().style()
            if self.parentWidget() is not None
            else QApplication.style()
        )

        layout_spacing_x: int = style.layoutSpacing(
            policy, policy, Qt.Orientation.Horizontal
        )
        layout_spacing_y: int = style.layoutSpacing(
            policy, policy, Qt.Orientation.Vertical
        )
        space_x = spacing + layout_spacing_x
        space_y = spacing + layout_spacing_y

        # Qt rect.right() is inclusive; cache bounds
        left = rect.x()
        right = rect.right()

        for item in self._item_list:
            if item.isEmpty():
                continue

            hint = item.sizeHint()
            w = hint.width()
            h = hint.height()

            next_x = x + w + space_x

            # Wrap if the current item would overflow the line
            # (only if there is already something on this line)
            if (x > left) and (next_x - space_x > right) and (line_height > 0):
                x = left
                y += line_height + space_y
                next_x = x + w + space_x
                line_height = 0

            if not test_only:
                # use integer overload to avoid temporary QRect/QPoint allocations
                item.setGeometry(QRect(x, y, w, h))

            x = next_x
            if h > line_height:
                line_height = h

        return (y + line_height) - rect.y()
