import sys

from PySide6.QtWidgets import QApplication

from apic_studio.core.settings import SettingsManager  # noqa: F401
from apic_studio.resource import resources  # noqa: F401
from apic_studio.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    MainWindow.show_window()
    SettingsManager().load_settings()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
