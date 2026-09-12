"""NSGA-IIの候補(ゼンマイ型FrameParamsの5変数)を鼻モデルと組み合わせてglTF
(.glb)に出力するスクリプト。

FrameParamsの各フィールドに対応するCLI引数で候補フレームを指定する。省略すると既定
形状になる。export_model.pyが出力するoutput/spiral/base.glb(常に既定形状)
とは別ファイルに書き出すため、既定形状を上書きしない。出力ファイル名は
省略すると実行時刻から自動生成する(複数の候補を見比べるとき、後から
実行したものが前のものを上書きしてしまわないようにするため)。
--output-nameで明示的に指定することもできる。

.glbを使うのは、フレームの半透明(alpha)をOBJ+MTLでは保持できないため
(spiral.frame_model._FRAME_COLORのdocstring参照)。

--stlを付けると、鼻本体・鼻栓を含まないフレーム(左右それぞれ)だけを
3Dプリント用のSTLとしても書き出す(<出力名>_frame_left.stl /
_frame_right.stl)。STLは色を持たないため寸法だけの出力で、単位はmm
(スライサー側でmmとして読み込むこと)。フレームはコイル+ステムを
ブーリアン結合した閉じた単一の立体(spiral.frame_model.build_frame_pair
参照)で、コイルの平面がxy平面に平行なので、そのまま読み込めば平置きに
なる。
"""

import argparse
import sys
from dataclasses import fields
from datetime import datetime
from pathlib import Path

# scripts/ をimportパスに加える(`uv run python scripts/spiral/xxx.py`で
# 実行するとsys.path[0]はscripts/spiral/になり、commons/spiralパッケージ
# が見つからないため)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spiral.export_model import OUTPUT_DIR  # noqa: E402
from spiral.frame_model import FrameParams  # noqa: E402
from spiral.scene import build_full_scene  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    for f in fields(FrameParams):
        parser.add_argument(f"--{f.name.replace('_', '-')}", type=float, default=f.default)
    parser.add_argument(
        "--output-name",
        type=str,
        default=None,
        help=f"出力ファイル名({OUTPUT_DIR}/以下)。省略すると実行時刻から自動生成する",
    )
    parser.add_argument(
        "--stl",
        action="store_true",
        help="フレーム(左右)だけを3Dプリント用STLとしても書き出す",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    frame = FrameParams(**{f.name: getattr(args, f.name) for f in fields(FrameParams)})
    scene = build_full_scene(frame)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_name = args.output_name or f"candidate_{datetime.now():%Y%m%d_%H%M%S}.glb"
    out_path = OUTPUT_DIR / out_name
    scene.export(out_path)

    print(f"exported: {out_path}")
    for geom_name, geom in scene.geometry.items():
        print(f"  {geom_name}: {len(geom.vertices)} verts, {len(geom.faces)} faces")

    if args.stl:
        for side in ("left", "right"):
            mesh = scene.geometry[f"frame_{side}"]
            stl_path = OUTPUT_DIR / f"{out_path.stem}_frame_{side}.stl"
            mesh.export(stl_path)
            x, y, z = mesh.extents
            print(
                f"exported: {stl_path} (watertight={mesh.is_watertight}, "
                f"{x:.1f} x {y:.1f} x {z:.1f} mm, {mesh.volume:.1f} mm^3)"
            )


if __name__ == "__main__":
    main()
