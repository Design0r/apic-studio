import sys

from apic_studio.app import Application
from apic_studio.resource import resources  # noqa: F401


def main():
    app = Application()
    app.run()
    sys.exit(0)


if __name__ == "__main__":
    main()
