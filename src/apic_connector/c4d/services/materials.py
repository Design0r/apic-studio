from pathlib import Path
from typing import Optional

import c4d
from shared.logger import Logger
from shared.utils import sanitize_string


def export_selected(file_path: str):
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


def export_materials(names: Optional[list[str]], path: str) -> bool:
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


def save_material_preview(
    mat: c4d.BaseMaterial, filepath: str, fmt: int = c4d.FILTER_PNG
) -> bool:
    c4d.StopAllThreads()
    mat.SetParameter(
        c4d.DescID(c4d.MATERIAL_PREVIEWSIZE),
        c4d.MATERIAL_PREVIEWSIZE_512,
        c4d.DESCFLAGS_SET_0,
    )
    mat.Update(True, True)
    c4d.EventAdd()
    bmp = mat.GetPreview()
    if bmp is None:
        Logger.error(f"no preview available for material {mat.GetName()}")
        return False

    if not bmp.Save(filepath, fmt):
        Logger.error(f"Failed to save preview to {filepath}")
        return False

    return True


def save_material_previews(materials: list[c4d.BaseMaterial], path: str):
    for mat in materials:
        name = sanitize_string(mat.GetName())
        full_path = Path(path, name, f"{name}.png")
        save_material_preview(mat, str(full_path))


def render_material():
    tmp = c4d.documents.BaseDocument()
    path = Path("C:\\Users\\TheApic\\Desktop\\test-render.c4d")
    ok = c4d.documents.MergeDocument(
        tmp,
        str(path),
        c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS,
    )

    if not ok:
        Logger.error(f"failed to load document: {path}")
        return

    sphere = [o for o in tmp.GetObjects() if o.GetName() == "obj"]


def apply_material(obj: c4d.BaseObject, mtl: c4d.BaseMaterial):
    ttag = c4d.TextureTag()
    ttag.SetMaterial(mtl)

    obj.InsertTag(ttag)
