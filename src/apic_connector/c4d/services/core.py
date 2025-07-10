import c4d
from shared.logger import Logger


def import_file(doc: c4d.BaseDocument, file_path: str) -> bool:
    result = c4d.documents.MergeDocument(
        doc,
        file_path,
        c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS,
    )
    if result:
        Logger.debug(f"import succeeded: {file_path}")
    else:
        Logger.error(f"import failed: {file_path}")

    return result
