import c4d


def export_selected():
    doc = c4d.documents.GetActiveDocument()
    sel = doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_SELECTIONORDER)
    if not sel:
        c4d.gui.MessageDialog("No objects selected, please select at least one mesh")
        return

    path = c4d.storage.SaveDialog(
        type=c4d.FILESELECTTYPE_ANYTHING, title="Export Selected", force_suffix="fbx"
    )

    if not path:
        return

    temp = c4d.documents.BaseDocument()
    for obj in sel:
        temp.InsertObject(obj)

    flags = c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST | c4d.SAVEDOCUMENTFLAGS_0
    result = c4d.documents.SaveDocument(temp, path, flags, c4d.FORMAT_FBX_EXPORT)
    if result:
        c4d.gui.MessageDialog(f"Export succeeded:\n{path}")
    else:
        c4d.gui.MessageDialog("Export failed. Check console for errors.")
