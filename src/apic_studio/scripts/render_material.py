import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Optional

import c4d

from apic_connector.c4d.services import core


def parse_args() -> Namespace:
    p = ArgumentParser()
    p.add_argument(
        "--scene", "-s", type=str, help="c4d render scene path", required=True
    )
    p.add_argument(
        "--materials",
        "-m",
        type=str,
        help="c4d material scene paths as a list",
        required=True,
    )
    p.add_argument(
        "--object", "-obj", type=str, help="render object name", required=True
    )
    p.add_argument(
        "--extension", "-e", type=str, help="output file extension", default=".png"
    )
    p.add_argument("--camera", "-c", type=str, help="render object name")
    p.add_argument(
        "--width", "-rx", type=float, help="render resolution width", default=350.0
    )
    p.add_argument(
        "--height", "-ry", type=float, help="render resolution height", default=350.0
    )

    return p.parse_args(sys.argv[1:])


def bake_linear_to_srgb(bmp: c4d.bitmaps.BaseBitmap):
    w, h = bmp.GetSize()

    mode = getattr(
        c4d,
        "COLORSPACETRANSFORMATION_LINEAR_TO_VIEW",
        c4d.COLORSPACETRANSFORMATION_LINEAR_TO_SRGB,
    )
    for y in range(h):
        for x in range(w):
            # read raw 0–255 floats as a Vector
            vec = bmp.GetPixelDirect(x, y)

            # normalize to [0,1]
            lin = c4d.Vector(vec.x / 255.0, vec.y / 255.0, vec.z / 255.0)

            # apply standard Rec.709→sRGB transfer
            srgb = c4d.utils.TransformColor(lin, mode)

            r = int(max(0, min(255, srgb.x * 255)))
            g = int(max(0, min(255, srgb.y * 255)))
            b = int(max(0, min(255, srgb.z * 255)))

            bmp.SetPixel(x, y, r, g, b)


def render_document_to_file(doc: "c4d.BaseDocument"):
    rd = doc.GetActiveRenderData()
    bc = rd.GetDataInstance()

    w = int(bc[c4d.RDATA_XRES])
    h = int(bc[c4d.RDATA_YRES])
    bmp = c4d.bitmaps.BaseBitmap()
    if bmp.Init(w, h, 32) != c4d.IMAGERESULT_OK:
        raise RuntimeError("Failed to init BaseBitmap")

    result = c4d.documents.RenderDocument(
        doc,
        bc,
        bmp,
        c4d.RENDERFLAGS_EXTERNAL,
    )
    if result == c4d.RENDERRESULT_OK:
        print("Render complete")
    else:
        raise RuntimeError(f"Render failed (code {result})")

    bake_linear_to_srgb(bmp)

    out_path = bc[c4d.RDATA_PATH]
    if not bmp.Save(out_path, c4d.FILTER_PNG):
        raise RuntimeError(f"Failed to save render to: {out_path}")

    print(f"Saved render to {out_path}")


def set_render_camera(doc: "c4d.BaseDocument", name: str):
    cam = doc.SearchObject(name)
    if not cam:
        raise ValueError(f"Failed to set render camera. {name} not found.")

    take_data = doc.GetTakeData()
    if not take_data:
        raise RuntimeError("No TakeData on document; cannot set TAKEBASE_CAMERA.")

    take = take_data.GetCurrentTake()
    cam_descid = c4d.DescID(
        c4d.DescLevel(c4d.TAKEBASE_CAMERA, c4d.DTYPE_BASELISTLINK, 0)
    )
    take.SetParameter(cam_descid, cam, c4d.DESCFLAGS_SET_0)
    c4d.EventAdd()


def set_render_settings(doc: "c4d.BaseDocument", path: str, res: tuple[float, float]):
    rd = doc.GetActiveRenderData()
    data = rd.GetDataInstance()
    data[c4d.RDATA_PATH] = path
    data[c4d.RDATA_XRES] = res[0]
    data[c4d.RDATA_YRES] = res[1]

    data[c4d.RDATA_RENDERENGINE] = c4d.VPrsrenderer
    rd.SetData(data)

    c4d.EventAdd()


def apply_material(obj: c4d.BaseObject, mtl: Optional[c4d.BaseMaterial]):
    if not mtl:
        return
    ttag = c4d.TextureTag()
    ttag.SetMaterial(mtl)
    obj.InsertTag(ttag)


def main():
    c4d.StopAllThreads()
    args = parse_args()

    doc = c4d.documents.LoadDocument(
        args.scene, c4d.SCENEFILTER_MATERIALS | c4d.SCENEFILTER_OBJECTS
    )
    if not doc:
        raise RuntimeError(f"Failed to load base scene file: {args.scene}")

    c4d.documents.InsertBaseDocument(doc)

    set_render_camera(doc, args.camera)
    for mat in args.materials.split(","):
        mat_path = Path(mat)
        mat_name = mat_path.stem
        output_path = str(Path(mat_path).parent / f"{mat_name}{args.extension}")
        if not core.import_file(mat):
            raise RuntimeError(f"Failed to load material file: {mat}")

        set_render_settings(doc, output_path, (args.width, args.height))
        obj = doc.SearchObject(args.object)
        if not obj:
            continue
        apply_material(obj, doc.SearchMaterial(mat_name))
        render_document_to_file(doc)

        obj.KillTag(c4d.TAG_TEXTURE, 0)


if __name__ == "__main__":
    main()
