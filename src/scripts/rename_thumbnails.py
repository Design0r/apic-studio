from pathlib import Path
from sys import stderr

from apic_studio.core import db, settings


def run():
    s = settings.SettingsManager()
    s.load_settings()

    s.CoreSettings.db_path = (
        "\\\\apicnas\\Produktion\\Pipeline\\Apic Studio\\apic_studio.db"
    )

    db.init_db()
    paths = db.select(db.Tables.APIC_MODELS)

    for k, v in paths.items():
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
                    try:
                        file.rename(new_path)
                    except Exception as e:
                        print(e, file=stderr)


if __name__ == "__main__":
    run()
