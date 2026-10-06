from dataclasses import dataclass

import c4d

from shared.logger import Logger

from .core import get_default_render_path, get_document_path

# Redshift VideoPost plugin ID
ID_REDSHIFT_VIDEOPOST = 1036219

# IDs for the wrapper container (chosen high to avoid collisions)
ID_MAGIC = 1099990
ID_RENDERDATA = 1099991
ID_VIDEOPOSTS = 1099992
MAGIC_VALUE = 0x52534554  # "RSET"

# IDs inside each video post entry
ID_VP_TYPE = 0
ID_VP_DATA = 1


def _iter_videoposts(rd):
    vp = rd.GetFirstVideoPost()
    while vp:
        yield vp
        vp = vp.GetNext()


def _find_videopost(rd, vp_type):
    for vp in _iter_videoposts(rd):
        if vp.GetType() == vp_type:
            return vp
    return None


@dataclass
class OutputPaths:
    image: str
    multipass_image: str


def get_output_paths() -> OutputPaths:
    doc = c4d.documents.GetActiveDocument()
    rd = doc.GetActiveRenderData()

    return OutputPaths(rd[c4d.RDATA_PATH], rd[c4d.RDATA_MULTIPASS_FILENAME])


def _apply_output_paths(rd, image_path: str | None, multipass_path: str | None) -> None:
    if image_path is not None:
        rd[c4d.RDATA_PATH] = image_path
    if multipass_path is not None:
        rd[c4d.RDATA_MULTIPASS_FILENAME] = multipass_path


def set_output_paths(
    image_path: str | None = None, multipass_path: str | None = None
) -> None:
    doc = c4d.documents.GetActiveDocument()
    rd = doc.GetActiveRenderData()

    doc.StartUndo()
    doc.AddUndo(c4d.UNDOTYPE_CHANGE_SMALL, rd)
    _apply_output_paths(rd, image_path, multipass_path)
    doc.EndUndo()
    c4d.EventAdd()


def export_redshift_settings(file_path: str) -> bool:
    doc = c4d.documents.GetActiveDocument()
    rd = doc.GetActiveRenderData()

    vp = _find_videopost(rd, ID_REDSHIFT_VIDEOPOST)
    if vp is None:
        Logger.warning("No Redshift video post found in the active render settings.")
        return False

    root = c4d.BaseContainer()
    root.SetInt32(ID_MAGIC, MAGIC_VALUE)
    # No ID_RENDERDATA here, only the Redshift video post

    entry = c4d.BaseContainer()
    entry.SetInt32(ID_VP_TYPE, vp.GetType())
    entry.SetContainer(ID_VP_DATA, vp.GetData())

    vps = c4d.BaseContainer()
    vps.SetContainer(0, entry)
    root.SetContainer(ID_VIDEOPOSTS, vps)

    hf = c4d.storage.HyperFile()
    if not hf.Open(0, file_path, c4d.FILEOPEN_WRITE, c4d.FILEDIALOG_NONE):
        return False

    hf.WriteContainer(root)
    hf.Close()
    Logger.info(f"Redshift settings saved to: {file_path}")
    return True


def export_all_settings(file_path: str) -> bool:
    doc = c4d.documents.GetActiveDocument()
    rd = doc.GetActiveRenderData()

    root = c4d.BaseContainer()
    root.SetInt32(ID_MAGIC, MAGIC_VALUE)
    root.SetContainer(ID_RENDERDATA, rd.GetData())

    # Collect all video posts (Redshift included)
    vps = c4d.BaseContainer()
    for i, vp in enumerate(_iter_videoposts(rd)):
        entry = c4d.BaseContainer()
        entry.SetInt32(ID_VP_TYPE, vp.GetType())
        entry.SetContainer(ID_VP_DATA, vp.GetData())
        vps.SetContainer(i, entry)
        Logger.info(f"Exporting video post: {vp.GetName()} ({vp.GetType()})")
    root.SetContainer(ID_VIDEOPOSTS, vps)

    hf = c4d.storage.HyperFile()
    if not hf.Open(0, file_path, c4d.FILEOPEN_WRITE, c4d.FILEDIALOG_NONE):
        return False

    hf.WriteContainer(root)
    hf.Close()
    Logger.info(f"Settings saved to: {file_path}")
    return True


def export_c4d_settings(file_path: str) -> bool:
    doc = c4d.documents.GetActiveDocument()
    rd = doc.GetActiveRenderData()

    hf = c4d.storage.HyperFile()

    if hf.Open(0, file_path, c4d.FILEOPEN_WRITE, c4d.FILEDIALOG_NONE):
        # Directly serialize the BaseContainer block into the file
        hf.WriteContainer(rd.GetData())
        hf.Close()
        Logger.info("Settings exported")

    else:
        return False

    return True


def import_settings(file_path: str) -> bool:
    doc = c4d.documents.GetActiveDocument()
    rd = doc.GetActiveRenderData()

    # Keep the scene's own output paths, the imported preset shouldn't override them
    paths = get_output_paths()

    hf = c4d.storage.HyperFile()
    if not hf.Open(0, file_path, c4d.FILEOPEN_READ, c4d.FILEDIALOG_NONE):
        return False

    root = hf.ReadContainer()
    hf.Close()
    if not root:
        return False

    doc.StartUndo()
    doc.AddUndo(c4d.UNDOTYPE_CHANGE, rd)

    # Legacy file (old export): plain RenderData container only
    if root.GetInt32(ID_MAGIC) != MAGIC_VALUE:
        rd.SetData(root)
        Logger.info("Legacy settings loaded (no video post data).")
    else:
        # Render settings (incl. RDATA_RENDERENGINE -> Redshift)
        if root.GetType(ID_RENDERDATA) == c4d.DA_CONTAINER:
            rd.SetData(root.GetContainer(ID_RENDERDATA))
            rd[c4d.RDATA_RENDERENGINE] = ID_REDSHIFT_VIDEOPOST

        # Video posts
        vps = root.GetContainer(ID_VIDEOPOSTS)
        for _, entry in vps:
            if not isinstance(entry, c4d.BaseContainer):
                continue

            vp_type = entry.GetInt32(ID_VP_TYPE)
            vp_data = entry.GetContainer(ID_VP_DATA)

            vp = _find_videopost(rd, vp_type)
            if vp is None:
                vp = c4d.documents.BaseVideoPost(vp_type)
                if vp is None:
                    Logger.info(
                        f"Could not create video post {vp_type} (plugin missing?)"
                    )
                    continue
                rd.InsertVideoPost(vp)
                doc.AddUndo(c4d.UNDOTYPE_NEW, vp)
            else:
                doc.AddUndo(c4d.UNDOTYPE_CHANGE, vp)

            vp.SetData(vp_data)
            Logger.info(f"Imported video post: {vp.GetName()} ({vp_type})")

    default = get_default_render_path(get_document_path())
    _apply_output_paths(
        rd,
        paths.image or str(default) or None,
        paths.multipass_image or str(default) or None,
    )

    doc.EndUndo()
    c4d.EventAdd()
    Logger.info(f"Settings loaded from: {file_path}")
    return True
