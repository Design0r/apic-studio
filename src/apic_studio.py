import os
from pathlib import Path

from apic_studio.app import Application
from apic_studio.resources import resources  # noqa: F401

os.environ["IMAGEIO_FREEIMAGE_LIB"] = str(
    Path(__file__).parent.parent
    / "_internal"
    / "imageio"
    / "freeimage"
    / "freeimage.dll"
)


def main():
    app = Application()
    app.init()
    app.run()
    app.shutdown()


if __name__ == "__main__":
    main()
