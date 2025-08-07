from typing import Any

from argparse import ArgumentParser, Namespace
import c4d

def parse_args() -> Namespace:
    p = ArgumentParser()
    p.add_argument(
        "--scene", "-s", type=str, help="c4d render scene path", required=True
    )
    p.add_argument(
        "--target", "-t", type=str, help="output to copy the assets to path", required=True
    )

    return p.parse_args(sys.argv[1:])

def main():
    assets: list[dict[str, Any]] = []
    doc = c4d.documents.GetActiveDocument()
    res = c4d.documents.GetAllAssetsNew(
        doc,
        allowDialogs=False,
        lastPath="",
        flags=c4d.ASSETDATA_FLAG_0,
        assetList=assets,
    )

    if res == c4d.GETALLASSETSRESULT_FAILED:
        raise RuntimeError(f"Failed to gather assets for '{doc.GetDocumentPath()}'")
    if res == c4d.GETALLASSETSRESULT_MISSING:
        print("Some assets could not be resolved on disk")
    
    for asset in assets:



if __name__ == "__main__":
    main()
