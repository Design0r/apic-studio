import sys

from apic_studio import Application
from apic_studio.resource import resources  # noqa: F401


def main():
    app = Application()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
