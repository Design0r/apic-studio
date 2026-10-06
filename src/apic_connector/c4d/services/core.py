from pathlib import Path

import c4d

from shared.logger import Logger


def get_document_path() -> Path | None:
    doc = c4d.documents.GetActiveDocument()

    directory = doc.GetDocumentPath()
    if not directory:
        return None

    return Path(directory, doc.GetDocumentName())


PROJECT_ROOTS = (
    Path(r"\\apicnas\Produktion\Projekte"),
    Path(r"W:\Projekte"),
)


def get_project_path(document: Path) -> Path | None:
    for folder in document.parents:
        if folder.parent in PROJECT_ROOTS:
            return folder
    return None


def get_default_render_path(document: Path | None) -> Path | None:
    if not document:
        return None

    proj = get_project_path(document)
    if proj is None:
        return None

    return proj / "400_3D/460_renderings/$prj/$take/$prj_$take"


def import_file(file_path: str) -> bool:
    result = c4d.documents.MergeDocument(
        c4d.documents.GetActiveDocument(),
        file_path,
        c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS,
    )
    if result:
        Logger.debug(f"import succeeded: {file_path}")
    else:
        Logger.error(f"import failed: {file_path}")

    return result


def open_file(file_path: str):
    c4d.documents.LoadFile(file_path)


def save_file_as(file_path: str, globalize_textures: bool) -> bool:
    if globalize_textures:
        globalize_filenames()

    doc = c4d.documents.GetActiveDocument()
    res = c4d.documents.SaveDocument(
        doc, file_path, c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST, c4d.FORMAT_C4DEXPORT
    )
    if not res:
        Logger.info(f"save scene failed: {file_path}")
        return res

    Logger.info(f"save scene succeeded: {file_path}")
    return res


def globalize_filenames():
    c4d.CallCommand(1029486)  # open project asset inspector
    c4d.CallCommand(1029813)  # select all assets
    c4d.CallCommand(1029820)  # globalize


def load_xref(file_path: str):
    doc = c4d.documents.GetActiveDocument()

    obj = c4d.BaseObject(c4d.Oxref)
    doc.InsertObject(obj)

    fileId = c4d.DescID(c4d.DescLevel(c4d.ID_CA_XREF_FILE, c4d.DTYPE_FILENAME, 0))
    obj.SetParameter(fileId, file_path, c4d.DESCFLAGS_SET_USERINTERACTION)  # type: ignore

    c4d.EventAdd()
