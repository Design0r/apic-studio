from pathlib import Path

from apic_studio.core import db


def run():
    paths = db.select_all()

    for name, pool in paths.items():
        if name == "TEXURES":
            continue
        for k, v in pool.items():
            path = Path(v)
            if not path.exists():
                continue

            for asset_folder in path.iterdir():
                if not asset_folder.is_dir():
                    continue
                for file in asset_folder.iterdir():
                    if file.is_dir():
                        continue
                    if file.stem.startswith("."):
                        continue
                    if file.suffix in (".jpg", ".png") and not file.stem.endswith(
                        "-thumbnail"
                    ):
                        new_path = file.parent / f"{file.stem}-thumbnail{file.suffix}"
                        print("renaming", file, "to", new_path)
                        path.rename(new_path)
