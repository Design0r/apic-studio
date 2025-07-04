import c4d


def export_selected(file_path: str):
    doc = c4d.documents.GetActiveDocument()
    sel = doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_SELECTIONORDER)
    if not sel:
        c4d.gui.MessageDialog("No objects selected, please select at least one mesh")
        return

    flags = c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST | c4d.SAVEDOCUMENTFLAGS_0
    result = c4d.documents.SaveDocument(doc, file_path, flags, c4d.FORMAT_C4DEXPORT)
    if result:
        print(f"Export succeeded:\n{file_path}")
    else:
        print("Export failed. Check console for errors.")


def import_file(file_path: str):
    result = c4d.documents.MergeDocument(
        c4d.documents.GetActiveDocument(),
        file_path,
        c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS,
    )

    print(f"Import result: {result}")
