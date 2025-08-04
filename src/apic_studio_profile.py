from apic_studio.app import Application
from apic_studio.core.utils import profile
from apic_studio.resources import resources  # noqa: F401


def main():
    app = Application()
    app.run()


if __name__ == "__main__":
    profile(main)
