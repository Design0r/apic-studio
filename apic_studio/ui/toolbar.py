from enum import Enum
from typing import Callable, Optional, Union

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core import Logger
from .buttons import SidebarButton

SIDEBAR_STYLE = """
QWidget{
    background-color: rgb(38,38,38);
    color: rgb(255,255,255);
}

QPushButton{
    background-color: none;
    border-radius: 5px;
}

QPushButton::hover{
    background-color: rgb(235, 177, 52);
}

QPushButton::checked{
    background-color: rgb(235, 177, 52);
}
"""

TOOLBAR_STYLE = """
QWidget{
    background-color: rgb(50,50,50);
}

QPushButton{
    background-color: none;
    border-radius: 5px;
}

QPushButton::hover{
    background-color: rgb(235, 177, 52);
}

QComboBox, QAbstractItemView{
    background-color: rgb(38,38,38);
    border: 1px solid black;
    border-radius: 5px;
    font-size: 10pt;
    color: white;
}

QLineEdit{
    background-color: rgb(38,38,38);
    font-size: 10pt;
    border-radius: 5px;
    border: 1px solid black;

}



QLabel{
    font-size: 12pt;
    color: white;
}
"""

STATUSBAR_STYLE = """
QWidget{
    background-color: rgb(50,50,50);
}


QLabel{
    font-size: 8pt;
    color: white;
}
"""


class ToolbarDirection(Enum):
    Horizontal = 0
    Vertical = 1


class Toolbar(QWidget):
    def __init__(
        self,
        direction: ToolbarDirection,
        thickness: int,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.direction = direction
        self.thickness = thickness

        # self.setAttribute(Qt.WA_StyledBackground, True)

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        if self.direction == ToolbarDirection.Horizontal:
            self.setFixedHeight(self.thickness)
        elif self.direction == ToolbarDirection.Vertical:
            self.setFixedWidth(self.thickness)

    def init_layouts(self) -> None:
        if self.direction == ToolbarDirection.Horizontal:
            self.main_layout = QHBoxLayout(self)
            self.main_layout.setContentsMargins(2, 2, 2, 2)
            return

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(2, 2, 2, 2)

    def init_signals(self):
        pass

    def add_widgets(self, widgets: list[QWidget], stretch: bool = True):
        for widget in widgets:
            self.main_layout.addWidget(widget)

        if stretch:
            self.main_layout.addStretch()


class Sidebar(Toolbar):
    def __init__(self, width: int, parent: Optional[QWidget] = None):
        super().__init__(ToolbarDirection.Vertical, width, parent)
        self.setStyleSheet(SIDEBAR_STYLE)
        self.buttons = (
            self.materials,
            self.models,
            self.lightsets,
            self.hdris,
            self.utilities,
            self.help,
            self.about,
            self.settings_btn,
        )

    def init_widgets(self):
        super().init_widgets()

        size = 25
        btn_size = (size, size)
        icon_size = btn_size

        self.materials = SidebarButton(btn_size)
        self.materials.set_icon(":icons/tabler-icon-crystal-ball.png", icon_size)
        self.materials.set_tooltip("Materials")
        self.materials.activated.connect(self.highlight_modes)

        self.models = SidebarButton(btn_size)
        self.models.set_icon(":icons/tabler-icon-box.png", icon_size)
        self.models.set_tooltip("Models")
        self.models.activated.connect(self.highlight_modes)

        self.lightsets = SidebarButton(btn_size)
        self.lightsets.set_icon(":icons/tabler-icon-lamp.png", icon_size)
        self.lightsets.set_tooltip("Lightsets")
        self.lightsets.activated.connect(self.highlight_modes)

        self.hdris = SidebarButton(btn_size)
        self.hdris.set_icon(":icons/tabler-icon-bulb.png", icon_size)
        self.hdris.set_tooltip("HDRIs")
        self.hdris.activated.connect(self.highlight_modes)

        self.utilities = SidebarButton(btn_size)
        self.utilities.set_icon(":icons/tabler-icon-script.png", icon_size)
        self.utilities.set_tooltip("Utilities")
        self.utilities.activated.connect(self.highlight_modes)

        self.help = SidebarButton(btn_size)
        self.help.set_icon(":icons/tabler-icon-help.png", icon_size)
        self.help.set_tooltip("Help")
        self.help.activated.connect(self.highlight_modes)

        self.about = SidebarButton(btn_size)
        self.about.set_icon(":icons/tabler-icon-info-circle.png", icon_size)
        self.about.set_tooltip("About Render Vault")
        self.about.activated.connect(self.highlight_modes)

        self.settings_btn = SidebarButton(btn_size)
        self.settings_btn.set_icon(":icons/tabler-icon-settings.png", icon_size)
        self.settings_btn.set_tooltip("Settings")
        self.settings_btn.activated.connect(self.highlight_modes)

    def _add_button(
        self,
        size: tuple[int, int],
        icon: str,
        icon_size: tuple[int, int],
        tooltip: str,
        activated_fn: Callable[..., None],
    ):
        pass

    def init_layouts(self) -> None:
        super().init_layouts()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.main_layout.addWidget(self.materials)
        self.main_layout.addWidget(self.models)
        self.main_layout.addWidget(self.lightsets)
        self.main_layout.addWidget(self.hdris)
        self.main_layout.addWidget(self.utilities)
        self.main_layout.addStretch()
        self.main_layout.addWidget(self.help)
        self.main_layout.addWidget(self.about)
        self.main_layout.addWidget(self.settings_btn)

    def highlight_modes(self, button: Union[SidebarButton, int]):
        for btn in self.buttons:
            btn.setChecked(False)

        if isinstance(button, SidebarButton):
            button.setChecked(True)
        else:
            self.buttons[button - 1].setChecked(True)


class Status:
    LoadingUI = "Loading UI"
    LoadingAssets = "Loading Assets"
    Idle = "Idle"


class Statusbar(Toolbar):
    def __init__(
        self,
        thickness: int,
        direction: ToolbarDirection = ToolbarDirection.Horizontal,
        parent=None,
    ):
        super().__init__(direction, thickness, parent)
        self.settings = SettingsManager
        self.ui_scale = self.settings.window_settings.ui_scale
        self.thickness = 30 * self.ui_scale
        self.setStyleSheet(STATUSBAR_STYLE)

    def init_widgets(self):
        super().init_widgets()
        self.info = QLineEdit("")
        self.info.setReadOnly(True)
        self.info.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.info.setCursorPosition(0)
        self.info.setMinimumWidth(20)

        self.clear_btn = QPushButton("x")
        self.clear_btn.setFixedWidth(15)
        self.clear_btn.setStyleSheet(
            "QPushButton{border: none;}QPushButton::hover{background-color: rgb(100,100,100);}"
        )

    def init_layouts(self) -> None:
        super().init_layouts()
        self.main_layout.setAlignment(Qt.AlignHCenter)
        self.main_layout.setContentsMargins(0, 0, 10, 0)

        self.main_layout.addWidget(self.info)
        self.main_layout.addWidget(self.clear_btn)

    def init_signals(self) -> None:
        Logger.register_callback(self.update_info)
        self.clear_btn.clicked.connect(lambda: self.update_info("Clear", ""))

    def update_info(self, level: str, text: str) -> None:
        self.info.setText(text)

        if level == "Info":
            self.info.setStyleSheet("background-color: rgb(50,100,50)")
        elif level == "Warning":
            self.info.setStyleSheet("background-color: rgb(100,100,50)")
        elif level == "Error":
            self.info.setStyleSheet("background-color: rgb(100,50,50)")
        elif level == "Clear":
            self.info.setStyleSheet("background-color: rgb(50,50,50)")

        self.info.setCursorPosition(0)

    def update_status(self, status: Status):
        pass
