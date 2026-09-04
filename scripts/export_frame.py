"""NSGA-IIの候補(FrameParamsの12変数)を鼻モデルと組み合わせてglTF(.glb)に出力するスクリプト。

FrameParamsの各フィールドに対応するCLI引数で候補フレームを指定する。省略すると既定
形状になる。export_model.pyが出力するoutput/base.glb(常に既定形状)とは
別ファイルに書き出すため、既定形状を上書きしない。出力ファイル名は
省略すると実行時刻から自動生成する(複数の候補を見比べるとき、後から
実行したものが前のものを上書きしてしまわないようにするため)。
--output-nameで明示的に指定することもできる。

.glbを使うのは、フレームの半透明(alpha)をOBJ+MTLでは保持できないため
(models.frame_model._FRAME_COLORのdocstring参照)。
"""

import argparse
from dataclasses import fields
from datetime import datetime
from pathlib import Path

from models.frame_model import FrameParams
from models.scene import build_full_scene


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    for f in fields(FrameParams):
        parser.add_argument(f"--{f.name.replace('_', '-')}", type=float, default=f.default)
    parser.add_argument(
        "--output-name",
        type=str,
        default=None,
        help="出力ファイル名(output/以下)。省略すると実行時刻から自動生成する",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    frame = FrameParams(**{f.name: getattr(args, f.name) for f in fields(FrameParams)})
    scene = build_full_scene(frame)

    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)
    out_name = args.output_name or f"candidate_{datetime.now():%Y%m%d_%H%M%S}.glb"
    out_path = out_dir / out_name
    scene.export(out_path)

    print(f"exported: {out_path}")
    for geom_name, geom in scene.geometry.items():
        print(f"  {geom_name}: {len(geom.vertices)} verts, {len(geom.faces)} faces")


if __name__ == "__main__":
    main()
