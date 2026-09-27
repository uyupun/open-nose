"""NSGA-IIの候補(拡張ブリッジ型FrameParamsの8変数)を鼻モデルと組み合わせて
glTF(.glb)に出力するスクリプト。

FrameParamsの各フィールドに対応するCLI引数で候補フレームを指定する。省略すると既定
形状になる。export_model.pyが出力するoutput/dilator/base.glb(常に既定形状)
とは別ファイルに書き出すため、既定形状を上書きしない。出力ファイル名は
省略すると実行時刻から自動生成する(複数の候補を見比べるとき、後から
実行したものが前のものを上書きしてしまわないようにするため)。
--output-nameで明示的に指定することもできる。

.glbを使うのは、フレームの半透明(alpha)をOBJ+MTLでは保持できないため
(dilator.frame_model._FRAME_COLORのdocstring参照)。

--stlを付けると、鼻本体・鼻栓を含まないフレーム単体を3Dプリント用のSTL
としても書き出す。フレームはブリッジ(鼻筋のアーチ状の帯)・左の脚(棒と
レンズ)・右の脚(棒とレンズ)の3つの別々の部品なので、STLも3ファイル
(<出力名>_frame_bridge.stl・_frame_leg_left.stl・_frame_leg_right.stl)
になる。脚は装着した形のまま(dilator.frame_model.build_leg_piece)、
ブリッジは装着した形ではなく、同じアーチの曲がりを弱めた(少し開いた)
自然な形(dilator.frame_model.build_bridge_print_piece)で出力する(鼻の上で曲げて
貼ったときの曲げ戻りが、ブリーズライトのように小鼻を引き上げる力になる
ため)。それぞれ別々に3Dプリントし、ブリッジを鼻に貼ってから、脚の上端の
小さなC字を帯の端から滑り込ませ、帯の上下の縁を抱かせて組み立てる
(dilator.frame_model._leg_connector)。STLは色を持たないため
寸法だけの出力で、単位はmm(スライサー側でmmとして読み込むこと)。
"""

import argparse
import sys
from dataclasses import fields
from datetime import datetime
from pathlib import Path

# scripts/ をimportパスに加える(`uv run python scripts/dilator/xxx.py`で
# 実行するとsys.path[0]はscripts/dilator/になり、commons/dilatorパッケージ
# が見つからないため)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from commons.nose_model import NoseParams  # noqa: E402
from dilator.export_model import OUTPUT_DIR  # noqa: E402
from dilator.frame_model import FrameParams, build_bridge_print_piece  # noqa: E402
from dilator.scene import build_full_scene  # noqa: E402


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
        help="フレーム単体を3Dプリント用STLとしても書き出す",
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
        # ブリッジは装着した形(scene)ではなく、印刷する自然な形で出力する
        # (dilator.frame_model.build_bridge_print_piece参照)
        printed = {"frame_bridge": build_bridge_print_piece(frame, NoseParams())}
        for geom_name in ("frame_bridge", "frame_leg_left", "frame_leg_right"):
            mesh = printed.get(geom_name, scene.geometry[geom_name])
            stl_path = OUTPUT_DIR / f"{out_path.stem}_{geom_name}.stl"
            mesh.export(stl_path)
            x, y, z = mesh.extents
            print(
                f"exported: {stl_path} (watertight={mesh.is_watertight}, "
                f"{x:.1f} x {y:.1f} x {z:.1f} mm, {mesh.volume:.1f} mm^3)"
            )


if __name__ == "__main__":
    main()
