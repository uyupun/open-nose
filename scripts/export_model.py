"""鼻本体・鼻栓・フレームの既定構成一式を生成し、output/base.glb に出力するスクリプト。

glTF(.glb)形式を使うのは、フレームの半透明(alpha)をOBJ+MTLでは保持できない
ため(models.frame_model._FRAME_COLORのdocstring参照)。
"""

from pathlib import Path

from models.scene import build_full_scene


def main() -> None:
    scene = build_full_scene()

    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "base.glb"
    scene.export(out_path)

    print(f"exported: {out_path}")
    for name, geom in scene.geometry.items():
        print(f"  {name}: {len(geom.vertices)} verts, {len(geom.faces)} faces")


if __name__ == "__main__":
    main()
