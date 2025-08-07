import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path

import c4d
import cv2
import numpy as np

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


def bake_linear_to_srgb(bmp: c4d.bitmaps.MultipassBitmap):
    w, h = bmp.GetSize()
    for y in range(h):
        for x in range(w):
            # read raw 0–255 floats as a Vector
            vec = bmp.GetPixelDirect(x, y)
            # normalize to [0,1]
            lin = c4d.Vector(vec.x / 255.0, vec.y / 255.0, vec.z / 255.0)

            # apply standard Rec.709→sRGB transfer
            srgb = c4d.utils.TransformColor(
                lin, c4d.COLORSPACETRANSFORMATION_LINEAR_TO_SRGB
            )

            # clamp back to [0,255] ints and write
            bmp.SetPixel(
                x,
                y,
                int(max(0, min(255, srgb.x * 255))),
                int(max(0, min(255, srgb.y * 255))),
                int(max(0, min(255, srgb.z * 255))),
            )


def render_document_to_file(doc: "c4d.BaseDocument"):
    rd = doc.GetActiveRenderData()
    bc = rd.GetDataInstance()

    bmp = c4d.bitmaps.MultipassBitmap(
        int(bc[c4d.RDATA_XRES]), int(bc[c4d.RDATA_YRES]), c4d.COLORMODE_RGB
    )
    # bmp.AddChannel(True, True)

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

    print(f"Saved render to {out_path}")


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


def reinhard_tonemap(img: cv2.Mat, exposure: float = 1.0, white: float = 1.0):
    return img * (1.0 + (img / (white**2))) / (exposure + img)


def apply_gamma(file: str):
    img = cv2.imread(file, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"Failed to load image: {file}")
    img_f = img.astype(np.float32) / 255.0
    corrected = np.power(img_f, 1.0 / 2.2)
    out = np.clip(corrected * 255.0, 0, 255).round().astype(np.uint8)

    if not cv2.imwrite(file, out):
        raise RuntimeError(f"Failed to save image to: {file}")
    print(f"Saved gamma‑corrected image to {file}")


def main():
    args = parse_args()

    doc = c4d.documents.LoadDocument(
        args.scene, c4d.SCENEFILTER_MATERIALS | c4d.SCENEFILTER_OBJECTS
    )
    if not doc:
        raise RuntimeError(f"Failed to load base scene file: {args.scene}")

    c4d.documents.InsertBaseDocument(doc)

    set_camera(doc, args.camera)
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
        apply_gamma(output_path)
        obj.KillTag(c4d.TAG_TEXTURE, 0)


if __name__ == "__main__":
    main()
