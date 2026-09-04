"""鼻モデルをインタラクティブビューアで確認するスクリプト。

引数を省略すると既定形状(FrameParamsの既定値)をその場で生成して表示する。
ファイルパスを渡すと、そのOBJ/glTF等を読み込んで表示する(scripts/
export_frame.pyが出力するoutput/candidate_*.glb等を確認する用途)。
"""

import argparse
from pathlib import Path

import trimesh

from models.scene import build_full_scene

# カメラを既定位置より少し下にずらす(上側の余白を減らすため)
_CAMERA_Y_OFFSET = -8.0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "file",
        type=Path,
        nargs="?",
        default=None,
        help="表示するOBJ等のパス。省略すると既定形状を生成して表示する",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    # force="scene": 単一ジオメトリのファイルでもSceneとして読み込む
    # (Trimeshにはcamera_transformがなく、下のカメラ調整が使えないため)
    scene = trimesh.load(args.file, force="scene") if args.file else build_full_scene()

    camera_transform = scene.camera_transform.copy()
    camera_transform[1, 3] += _CAMERA_Y_OFFSET
    scene.camera_transform = camera_transform
    scene.show()


if __name__ == "__main__":
    main()
