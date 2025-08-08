import shutil
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Any

import c4d
import maxon


def parse_args() -> Namespace:
    p = ArgumentParser()
    p.add_argument(
        "--scene", "-s", type=str, help="c4d render scene path", required=True
    )

    return p.parse_args(sys.argv[1:])


def get_assets_to_copy(doc: "c4d.BaseDocument", target: Path) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    res = c4d.documents.GetAllAssetsNew(
        doc,
        allowDialogs=False,
        lastPath="",
        flags=c4d.ASSETDATA_FLAG_0,
        assetList=assets,
    )
    if res == c4d.GETALLASSETSRESULT_FAILED:
        print(f"Failed to gather assets for '{doc.GetDocumentPath()}'")
        return []
    if res == c4d.GETALLASSETSRESULT_MISSING:
        print("Some assets could not be resolved on disk")

    filtered: list[dict[str, Any]] = []
    for a in assets:
        filename = Path(a["filename"])
        if filename.parent != target and filename.suffix != ".c4d" and a["nodeSpace"]:
            filtered.append(a)

    return filtered


def relink_node_asset(item: dict[str, Any], new_path: str):
    owner = item.get("owner")  # c4d.BaseMaterial
    if not owner:
        raise ValueError("No owner found.")

    node_path = item.get("nodePath", "")  # e.g. 'texturesampler@...'
    node_space = item.get("nodeSpace", "")
    if not node_path or not node_space:
        raise ValueError("No nodeSpace or nodePath found.")

    nm = owner.GetNodeMaterialReference()
    if not nm:
        raise ValueError("No node material reference.")

    graph = nm.GetGraph(node_space)
    if graph.IsNullValue():
        raise ValueError("No graph found.")

    with graph.BeginTransaction() as tr:
        node = graph.GetNode(maxon.NodePath(node_path))
        if node.IsNullValue():
            raise ValueError("Node is null.")
        # Redshift TextureSampler → input 'tex0' → child port 'path'
        if (
            node_space == "com.redshift3d.redshift4c4d.class.nodespace"
            and node.GetId().ToString().split("@")[0] == "texturesampler"
        ):
            path_port = (
                node.GetInputs()
                .FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.tex0")
                .FindChild("path")
            )
            if not path_port.IsNullValue():
                path_port.SetPortValue(new_path)
        tr.Commit()

    print(f"Relinked asset {Path(new_path).name}")


def copy_file(src: Path, dst: Path):
    if not src.exists() or dst.exists():
        return

    shutil.copy2(src, dst)
    print(f"Copied {src.name} to {dst}")


def main():
    args = parse_args()
    doc = c4d.documents.LoadDocument(
        args.scene, c4d.SCENEFILTER_MATERIALS | c4d.SCENEFILTER_OBJECTS
    )
    if not doc:
        raise RuntimeError(f"Failed to load base scene file: {args.scene}")

    c4d.documents.InsertBaseDocument(doc)
    print(f"Loaded scene {args.scene}")

    tex = Path(args.scene).parent / "tex"
    tex.mkdir(exist_ok=True)

    while assets := get_assets_to_copy(doc, tex):
        for asset in assets:
            asset_path = Path(asset["filename"])
            if asset_path.suffix == ".c4d":
                continue

            new_asset_path = tex / asset_path.name
            copy_file(asset_path, new_asset_path)
            try:
                relink_node_asset(asset, str(new_asset_path))
            except Exception as e:
                print(f"Failed to relink asset: {asset}\n{e}")
                break

    ok = c4d.documents.SaveDocument(
        doc, args.scene, c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST, c4d.FORMAT_C4DEXPORT
    )
    if not ok:
        print(f"failed to save document {args.scene}")

    print("Document saved")


if __name__ == "__main__":
    main()
