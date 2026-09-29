"""水引型設計の既定構成一式(鼻本体・鼻栓・器具)を生成し、
output/mizuhiki/base.glb に出力するスクリプト。"""

import sys
from pathlib import Path

# scripts/ をimportパスに加える(`uv run python scripts/mizuhiki/xxx.py`で
# 実行するとsys.path[0]はscripts/mizuhiki/になり、commons/mizuhikiパッケージ
# が見つからないため)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mizuhiki.scene import build_full_scene  # noqa: E402

# 出力先。設計ごとに分ける
OUTPUT_DIR = Path("output/mizuhiki")


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
