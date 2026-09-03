"""鼻モデル(鼻本体+鼻栓プレースホルダー)を生成し、output/nose.obj に出力するスクリプト。"""

from pathlib import Path

from models.scene import build_full_scene


def main() -> None:
    scene = build_full_scene()

    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "nose.obj"
    scene.export(out_path)

    print(f"exported: {out_path}")
    for name, geom in scene.geometry.items():
        print(f"  {name}: {len(geom.vertices)} verts, {len(geom.faces)} faces")


if __name__ == "__main__":
    main()
