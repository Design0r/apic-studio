import c4d
from shared.logger import Logger


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


def save_file_as(file_path: str) -> bool:
    doc = c4d.documents.GetActiveDocument()
    res = c4d.documents.SaveDocument(
        doc, file_path, c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST, c4d.FORMAT_C4DEXPORT
    )
    if not res:
        Logger.info(f"saven scene failed: {file_path}")
        return res

    Logger.info(f"saven scene succeeded: {file_path}")
    return res
