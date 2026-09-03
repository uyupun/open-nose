"""簡略化した鼻の幾何モデル(PROJECT.md の「モデル・変数・評価関数(暫定仕様 v0)」に対応)。

正確な人体計測データではなく、実験用の簡略近似。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import trimesh

# 輪郭生成に使う点数(多いほど滑らかになる)
_NUM_RING_POINTS = 32
# スーパー楕円の角丸具合(大きいほど四角に近づく)
_SUPERELLIPSE_ROUNDNESS = 4.0
# 鼻孔楕円体の奥行き(y方向)を長径・短径に対してどれだけ薄く潰すか
_NOSTRIL_DEPTH_RATIO = 0.6
# 鼻孔を配置するy位置(鼻先=0からnose_lenに対する比率)
_NOSTRIL_Y_RATIO = 0.12
# 鼻孔を配置するz位置(鼻先断面の奥行きに対する比率。表面よりやや内側)
_NOSTRIL_Z_RATIO = 0.7


@dataclass
class NoseParams:
    """鼻モデルの寸法パラメータ(単位: mm)。"""

    bridge_w: float = 20.0
    bridge_h: float = 15.0
    tip_w: float = 34.0
    tip_h: float = 24.0
    nose_len: float = 45.0
    nostril_a: float = 6.0
    nostril_b: float = 4.0
    nostril_gap: float = 18.0
    nostril_tilt_deg: float = 20.0


def _superellipse_ring(half_width: float, half_depth: float) -> np.ndarray:
    """角丸四角形(スーパー楕円)の輪郭点を (_NUM_RING_POINTS, 2) で返す。"""
    t = np.linspace(0, 2 * np.pi, _NUM_RING_POINTS, endpoint=False)
    ct, st = np.cos(t), np.sin(t)
    x = np.sign(ct) * np.abs(ct) ** (2 / _SUPERELLIPSE_ROUNDNESS) * half_width
    z = np.sign(st) * np.abs(st) ** (2 / _SUPERELLIPSE_ROUNDNESS) * half_depth
    return np.stack([x, z], axis=1)


def _build_body(params: NoseParams) -> trimesh.Trimesh:
    """鼻筋(y=nose_len)から鼻先(y=0)へテーパーするロフト形状。"""
    num_points = _NUM_RING_POINTS
    bridge_ring = _superellipse_ring(params.bridge_w / 2, params.bridge_h / 2)
    tip_ring = _superellipse_ring(params.tip_w / 2, params.tip_h / 2)

    bridge_verts = np.column_stack(
        [bridge_ring[:, 0], np.full(num_points, params.nose_len), bridge_ring[:, 1]]
    )
    tip_verts = np.column_stack(
        [tip_ring[:, 0], np.zeros(num_points), tip_ring[:, 1]]
    )

    bridge_center_idx = 2 * num_points
    tip_center_idx = 2 * num_points + 1
    vertices = np.vstack(
        [bridge_verts, tip_verts, [[0.0, params.nose_len, 0.0]], [[0.0, 0.0, 0.0]]]
    )

    faces = []
    for i in range(num_points):
        j = (i + 1) % num_points
        faces.append([i, num_points + j, num_points + i])
        faces.append([i, j, num_points + j])
        faces.append([bridge_center_idx, j, i])
        faces.append([tip_center_idx, num_points + i, num_points + j])

    return trimesh.Trimesh(vertices=vertices, faces=np.array(faces), process=True)


def _build_nostril(params: NoseParams, side: Literal[-1, 1]) -> trimesh.Trimesh:
    """鼻孔を表す楕円体(現時点ではボディへのブーリアン減算はせず、表面近くに配置するのみ)。"""
    mesh = trimesh.creation.icosphere(subdivisions=2, radius=1.0)

    scale = np.eye(4)
    scale[0, 0] = params.nostril_a
    scale[1, 1] = params.nostril_b * _NOSTRIL_DEPTH_RATIO
    scale[2, 2] = params.nostril_b
    mesh.apply_transform(scale)

    tilt = np.radians(params.nostril_tilt_deg) * side
    rotate = trimesh.transformations.rotation_matrix(tilt, [0, 1, 0])
    mesh.apply_transform(rotate)

    x_pos = side * params.nostril_gap / 2
    y_pos = params.nose_len * _NOSTRIL_Y_RATIO
    z_pos = params.tip_h / 2 * _NOSTRIL_Z_RATIO
    mesh.apply_translation([x_pos, y_pos, z_pos])

    return mesh


def build_nose_scene() -> trimesh.Scene:
    params = NoseParams()

    body = _build_body(params)
    body.visual.face_colors = [255, 220, 200, 255]

    left = _build_nostril(params, side=-1)
    right = _build_nostril(params, side=1)
    for nostril in (left, right):
        nostril.visual.face_colors = [120, 60, 60, 255]

    return trimesh.Scene({"body": body, "nostril_left": left, "nostril_right": right})


def main() -> None:
    scene = build_nose_scene()

    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "nose.obj"
    scene.export(out_path)

    print(f"exported: {out_path}")
    for name, geom in scene.geometry.items():
        print(f"  {name}: {len(geom.vertices)} verts, {len(geom.faces)} faces")


if __name__ == "__main__":
    main()
