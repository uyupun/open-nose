"""鼻モデルをインタラクティブビューアで確認するスクリプト。"""

from nose_model import build_nose_scene


def main() -> None:
    build_nose_scene().show()


if __name__ == "__main__":
    main()
