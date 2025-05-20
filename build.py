import shutil
import sys
from pathlib import Path

import PyInstaller.__main__


class Builder:
    def __init__(self, build_dir: Path):
        self._ressources: list[Path] = []
        self._copies: list[tuple[Path, Path]] = []
        self._namespace = ""
        self.build_dir = build_dir

    def set_namespace(self, namespace: str):
        self._namespace = namespace

    def add_ressource(self, path: Path | str, rename: str = ""):
        path = self._to_path(path)
        if rename:
            new_path = self.build_dir / rename
            self._copies.append((path, new_path))
            return

        self._ressources.append(path)

    def add_copy(self, src: Path | str, dst: Path | str):
        self._copies.append((self._to_path(src), self._to_path(dst)))

    def add_ext_copy(self, src: Path | str, dst: Path | str):
        self.add_copy(src, dst)

    def _to_path(self, path: str | Path) -> Path:
        if isinstance(path, Path):
            return path
        return Path(path)

    def _handle_namespace(self, path: Path) -> Path:
        if path.parent.name == self.build_dir.name:
            return path.parent / self._namespace / path.name
        return path

    def _copy(self, src: Path, dst: Path):
        dst = self._handle_namespace(dst)
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copytree(
                    src,
                    dst,
                    dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                )
                print(f"copied directory: {src} to: {dst}")
            except Exception as e:
                print(src, dst, e)
            return

        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(src, self._handle_namespace(dst))
            print(f"copied file: {src} to: {dst}")
        except Exception as e:
            print(src, dst, e)

    def build(self):
        for r in self._ressources:
            self._copy(r, self.build_dir / r.name)

        for s, d in self._copies:
            self._copy(s, d)

        print("build complete!")


def main():
    CWD = Path(__file__).parent
    PyInstaller.__main__.run(
        [
            "src/apic_studio.py",
            "--onefile",
            "--name",
            "Apic Studio",
            "--noconsole",
            "--icon",
            r".\src\apic_studio\resources\icons\apic_logo.ico",
        ]
    )

    b = Builder(CWD / "dist")

    if sys.platform == "win32":
        src = CWD / "src" / "apic_connector.py"
        dst = r"W:\Pipeline\Apic_Cinema_Pipeline\Plugins\apic_studio\apic_connector.pyp"
        b.add_ext_copy(src, dst)

    b.set_namespace("apic_connector_plugin")
    b.add_ressource(CWD / "src" / "apic_connector.py", rename="apic_connector.pyp")
    b.add_ressource(CWD / "src" / "shared")
    b.add_ressource(CWD / "src" / "apic_connector")
    b.build()


if __name__ == "__main__":
    main()
