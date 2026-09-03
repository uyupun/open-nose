"""鼻モデルをインタラクティブビューアで確認するスクリプト。"""

from nose_model import build_nose_scene

# カメラを既定位置より少し下にずらす(上側の余白を減らすため)
_CAMERA_Y_OFFSET = -8.0


def main() -> None:
    scene = build_nose_scene()
    camera_transform = scene.camera_transform.copy()
    camera_transform[1, 3] += _CAMERA_Y_OFFSET
    scene.camera_transform = camera_transform
    scene.show()


if __name__ == "__main__":
    main()
