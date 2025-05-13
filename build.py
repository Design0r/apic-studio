import shutil
from pathlib import Path


def main():
    src = Path(__file__).parent.absolute() / "apic_connector.py"
    dst = r"W:\Pipeline\Apic_Cinema_Pipeline\Plugins\apic_studio\apic_connector.pyp"

    shutil.copy2(str(src), dst)


if __name__ == "__main__":
    main()
