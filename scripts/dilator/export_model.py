"""拡張ブリッジ型設計の既定構成一式(鼻本体・鼻栓・フレーム)を生成し、
output/dilator/base.glb に出力するスクリプト。

glTF(.glb)形式を使うのは、フレームの半透明(alpha)をOBJ+MTLでは保持できない
ため(dilator.frame_model._FRAME_COLORのdocstring参照)。
"""

import sys
from pathlib import Path

# scripts/ をimportパスに加える(`uv run python scripts/dilator/xxx.py`で
# 実行するとsys.path[0]はscripts/dilator/になり、commons/dilatorパッケージ
# が見つからないため)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dilator.scene import build_full_scene  # noqa: E402

# 出力先。設計ごとに分ける(earringsはoutput/earrings/、spiralはoutput/spiral/、
# 元の設計はoutput/models/)
OUTPUT_DIR = Path("output/dilator")


def main() -> None:
    scene = build_full_scene()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "base.glb"
    scene.export(out_path)

    print(f"exported: {out_path}")
    for name, geom in scene.geometry.items():
        print(f"  {name}: {len(geom.vertices)} verts, {len(geom.faces)} faces")


if __name__ == "__main__":
    main()
