"""水引型の器具を、設計変数(MizuhikiParams)を指定してglTF(.glb)に出力し、
評価関数(evaluation.evaluate_frame)の結果を表示するスクリプト。

MizuhikiParamsの各フィールドに対応するCLI引数で候補を指定する。省略すると
既定形状になる。export_model.pyが出力するoutput/mizuhiki/base.glb(常に既定
形状)とは別ファイルに書き出す。出力ファイル名は省略すると実行時刻から自動
生成する(複数の候補を見比べるとき、後から実行したものが前のものを上書き
しないようにするため)。

--stlを付けると、器具(左右)だけを鼻に着けた向きのSTL(<出力名>_left.stl・
_right.stl)として、--printを付けると、そのまま刷れる向き(輪の底面をベッドに
置き、着けたときの上を上にする。<出力名>_left_print.stl・_right_print.stl)の
STLとしても書き出す。単位はmm。刷るときはツリーサポートとブリムを使う。
"""

import argparse
import sys
from dataclasses import fields
from datetime import datetime
from pathlib import Path

# scripts/ をimportパスに加える(export_model.pyと同じ理由)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from commons.nose_model import NoseParams  # noqa: E402
from mizuhiki.evaluation import evaluate_frame, format_score  # noqa: E402
from mizuhiki.export_model import OUTPUT_DIR  # noqa: E402
from mizuhiki.frame_model import MizuhikiParams, print_orientation  # noqa: E402
from mizuhiki.scene import build_full_scene  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    for f in fields(MizuhikiParams):
        parser.add_argument(f"--{f.name.replace('_', '-')}", type=float, default=f.default)
    parser.add_argument(
        "--output-name",
        type=str,
        default=None,
        help=f"出力ファイル名({OUTPUT_DIR}/以下)。省略すると実行時刻から自動生成する",
    )
    parser.add_argument("--stl", action="store_true", help="器具(左右)を鼻に着けた向きのSTLとしても書き出す")
    parser.add_argument("--print", action="store_true", help="器具(左右)をそのまま刷れる向きのSTLとしても書き出す")
    return parser.parse_args()


def export_candidate(frame: MizuhikiParams, name: str, stl: bool = False, printable: bool = False) -> Path:
    """候補を鼻モデルと組み合わせてOUTPUT_DIR/<name>.glbに書き出し、必要なら
    器具単体のSTLも書き出す。書き出したglbのパスを返す。"""
    scene = build_full_scene(frame)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{name}.glb"
    scene.export(out_path)
    print(f"exported: {out_path}")
    for side in ("left", "right"):
        mesh = scene.geometry[f"frame_mizuhiki_{side}"]
        outputs = []
        if stl:
            outputs.append((OUTPUT_DIR / f"{name}_{side}.stl", mesh))
        if printable:
            outputs.append((OUTPUT_DIR / f"{name}_{side}_print.stl", print_orientation(mesh)))
        for stl_path, stl_mesh in outputs:
            stl_mesh.export(stl_path)
            x, y, z = stl_mesh.extents
            print(
                f"exported: {stl_path} (watertight={stl_mesh.is_watertight}, "
                f"{x:.1f} x {y:.1f} x {z:.1f} mm, {stl_mesh.volume:.1f} mm^3)"
            )
    return out_path


def main() -> None:
    args = _parse_args()
    frame = MizuhikiParams(**{f.name: getattr(args, f.name) for f in fields(MizuhikiParams)})
    name = args.output_name or f"candidate_{datetime.now():%Y%m%d_%H%M%S}"
    name = name.removesuffix(".glb")
    export_candidate(frame, name, stl=args.stl, printable=args.print)
    print(frame)
    print(format_score(evaluate_frame(frame, NoseParams())))


if __name__ == "__main__":
    main()
