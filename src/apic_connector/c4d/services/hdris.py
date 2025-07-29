from pathlib import Path

import c4d


def hdri_import_as_dome(path: Path):
    RS_LIGHT_TYPE_DOME = 4
    REDSHIFT_LIGHT_ID = 1036751
    light = c4d.BaseObject(REDSHIFT_LIGHT_ID)
    light[c4d.REDSHIFT_LIGHT_TYPE] = RS_LIGHT_TYPE_DOME
    light[c4d.REDSHIFT_LIGHT_DOME_TEX0, c4d.REDSHIFT_FILE_PATH] = str(path)
    light.SetName(path.stem)

    c4d.documents.GetActiveDocument().InsertObject(light)
    c4d.EventAdd()


def hdri_import_as_area(path: Path):
    RS_LIGHT_TYPE_DOME = 3
    REDSHIFT_LIGHT_ID = 1036751
    light = c4d.BaseObject(REDSHIFT_LIGHT_ID)
    light[c4d.REDSHIFT_LIGHT_TYPE] = RS_LIGHT_TYPE_DOME
    light[c4d.REDSHIFT_LIGHT_PHYSICAL_TEXTURE, c4d.REDSHIFT_FILE_PATH] = str(path)
    light.SetName(path.stem)

    c4d.documents.GetActiveDocument().InsertObject(light)
    c4d.EventAdd()
