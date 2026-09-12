"""拡張ブリッジ型設計の鼻モデルをインタラクティブビューアで確認するスクリプト。

引数を省略すると既定形状(FrameParamsの既定値)をその場で生成して表示する。
ファイルパスを渡すと、そのOBJ/STL/glTF等を読み込んで表示する(scripts/
dilator/export_frame.pyが出力するoutput/dilator/candidate_*.glbや、
--stlで書き出したフレーム単体のSTLを確認する用途)。
"""

import argparse
import sys
from pathlib import Path

# scripts/ をimportパスに加える(`uv run python scripts/dilator/xxx.py`で
# 実行するとsys.path[0]はscripts/dilator/になり、commons/dilatorパッケージ
# が見つからないため)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from commons.viewer import load_for_viewer, show_scene  # noqa: E402
from dilator.scene import build_full_scene  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "file",
        type=Path,
        nargs="?",
        default=None,
        help="表示するOBJ/STL/glTF等のパス。省略すると既定形状を生成して表示する",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    scene = load_for_viewer(args.file) if args.file else build_full_scene()
    show_scene(scene)


if __name__ == "__main__":
    main()
