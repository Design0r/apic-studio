import c4d
from shared.logger import Logger


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
