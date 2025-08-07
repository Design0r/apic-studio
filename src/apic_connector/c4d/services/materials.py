from pathlib import Path
from typing import Optional

import c4d
from shared.logger import Logger
from shared.utils import sanitize_string

from .core import globalize_filenames


def export_selected(file_path: str, globalize_textures: bool):
    if globalize_textures:
        globalize_filenames()

    doc = c4d.documents.GetActiveDocument()
    sel = doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_SELECTIONORDER)
    if not sel:
        c4d.gui.MessageDialog("No objects selected, please select at least one mesh")
        return

    flags = c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST | c4d.SAVEDOCUMENTFLAGS_0
    result = c4d.documents.SaveDocument(doc, file_path, flags, c4d.FORMAT_C4DEXPORT)
    if result:
        Logger.debug(f"export succeeded: {file_path}")
    else:
        Logger.error(f"export failed: {file_path}")


def get_material_names() -> list[str]:
    doc = c4d.documents.GetActiveDocument()
    materials = doc.GetMaterials()
    return [m.GetName() for m in materials]


def get_materials(name_filter: Optional[list[str]]) -> list[c4d.BaseMaterial]:
    doc = c4d.documents.GetActiveDocument()
    materials = doc.GetMaterials()
    if name_filter:
        filter_set = set(name_filter)
        return [m for m in materials if m.GetName() in filter_set]

    return [m for m in materials]


def export_materials(
    names: Optional[list[str]], path: str, globalize_textures: bool
) -> bool:
    if globalize_textures:
        globalize_filenames()

    doc = c4d.documents.GetActiveDocument()
    mats = doc.GetMaterials()

    if names:
        name_set = set(names)
        mats = [m for m in mats if m.GetName() in name_set]

    flags = c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST

    success = True
    for m in mats:
        tmp = c4d.documents.BaseDocument()
        tmp.InsertMaterial(m.GetClone())
        name = sanitize_string(m.GetName())
        full_path = Path(path, name, f"{name}.c4d")

        if c4d.documents.SaveDocument(tmp, str(full_path), flags, c4d.FORMAT_C4DEXPORT):
            Logger.debug(f"export material succeeded: {full_path}")
        else:
            Logger.info(f"export material failed: {full_path}")
            success = False

    return success


def apply_material(obj: c4d.BaseObject, mtl: c4d.BaseMaterial):
    ttag = c4d.TextureTag()
    ttag.SetMaterial(mtl)

    obj.InsertTag(ttag)
