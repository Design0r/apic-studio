import sys
from argparse import ArgumentParser, Namespace

import c4d

from apic_connector.c4d.services import core


def parse_args() -> Namespace:
    p = ArgumentParser()
    p.add_argument(
        "--scene", "-s", type=str, help="c4d render scene path", required=True
    )
    p.add_argument(
        "--material_path",
        "-mp",
        type=str,
        help="c4d material scene path",
        required=True,
    )
    p.add_argument(
        "--material_name",
        "-mn",
        type=str,
        help="c4d material scene path",
        required=True,
    )
    p.add_argument(
        "--object", "-obj", type=str, help="render object name", required=True
    )
    p.add_argument("--output", "-o", type=str, help="render output path", required=True)
    p.add_argument("--camera", "-c", type=str, help="render object name")
    p.add_argument(
        "--width", "-rx", type=float, help="render resolution width", default=350.0
    )
    p.add_argument(
        "--height", "-ry", type=float, help="render resolution height", default=350.0
    )

    return p.parse_args(sys.argv[1:])


def render_document_to_file(doc: "c4d.BaseDocument"):
    rd = doc.GetActiveRenderData()
    bc = rd.GetDataInstance()

    bmp = c4d.bitmaps.MultipassBitmap(
        int(bc[c4d.RDATA_XRES]), int(bc[c4d.RDATA_YRES]), c4d.COLORMODE_RGB
    )
    bmp.AddChannel(True, True)

    result = c4d.documents.RenderDocument(
        doc,
        bc,
        bmp,
        c4d.RENDERFLAGS_EXTERNAL,
    )
    if result == c4d.RENDERRESULT_OK:
        print(f"Render complete: {bc[c4d.RDATA_PATH]}")
    else:
        raise RuntimeError(f"Render failed (code {result})")

    out_path = bc[c4d.RDATA_PATH]
    if not bmp.Save(out_path, c4d.FILTER_PNG):
        raise RuntimeError(f"Failed to save render to: {out_path}")

    print(f"✅ Saved render to {out_path}")


def set_camera(doc: "c4d.BaseDocument", name: str):
    camera = doc.SearchObject(name)
    if not camera:
        raise ValueError(f"Failed to set render camera. {name} not found.")
    viewport = doc.GetRenderBaseDraw()
    viewport[c4d.BASEDRAW_DATA_CAMERA] = camera


def set_render_settings(doc: "c4d.BaseDocument", path: str, res: tuple[float, float]):
    rd = doc.GetActiveRenderData()
    data = rd.GetDataInstance()
    data[c4d.RDATA_PATH] = path
    data[c4d.RDATA_XRES] = res[0]
    data[c4d.RDATA_YRES] = res[1]

    data[c4d.RDATA_RENDERENGINE] = c4d.VPrsrenderer
    rd.SetData(data)
    c4d.EventAdd()


def apply_material(obj: c4d.BaseObject, mtl: c4d.BaseMaterial):
    ttag = c4d.TextureTag()
    ttag.SetMaterial(mtl)
    obj.InsertTag(ttag)


def main():
    args = parse_args()
    print(args)

    doc = c4d.documents.GetActiveDocument()
    if not core.import_file(args.scene):
        raise RuntimeError(f"Failed to load base scene file: {args.scene}")

    if not core.import_file(args.material_path):
        raise RuntimeError(f"Failed to load material file: {args.material_path}")

    set_camera(doc, args.camera)
    set_render_settings(doc, args.output, (args.width, args.height))
    apply_material(
        doc.SearchObject(args.object), doc.SearchMaterial(args.material_name)
    )
    render_document_to_file(doc)


if __name__ == "__main__":
    main()
