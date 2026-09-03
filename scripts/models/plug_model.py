"""鼻栓本体のプレースホルダー(PROJECT.md の「鼻栓寸法」に対応)。"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import trimesh

from .nose_model import nostril_depth_z

# 鼻栓プレースホルダー(円柱)のy方向の配置オフセット(鼻孔中心からの
# ずらし量、mm。正は鼻の内部方向、負は鼻先の外側方向)。鼻孔と同じく
# y=0中心に置くと、円柱が鼻の表面(肌)から突き抜けて見えてしまう
# (手前側にはみ出す、または奥に入りすぎて側面から突き抜けるなど)。
# 断面が細長い楕円(鼻孔)と円柱の組み合わせのため、突き抜けるか
# どうかは単純な数式では決めづらく、インタラクティブビューアでの
# 目視確認を元に調整した値
_PLUG_Y_OFFSET = -0.6


@dataclass(frozen=True)
class PlugParams:
    """鼻栓本体の仮寸法パラメータ(単位: mm)。

    既製品を使う想定のプレースホルダーで、円柱として単純化している。
    後から実際の製品寸法に合わせて調整する。
    """

    diameter: float = 6.0
    length: float = 8.0

    def __post_init__(self) -> None:
        for name in ("diameter", "length"):
            value = getattr(self, name)
            if value <= 0:
                raise ValueError(f"{name} は正の値にすること: {value}")


def plug_center(gap: float, depth_front: float, side: Literal[-1, 1]) -> np.ndarray:
    """指定側の鼻栓プレースホルダーの中心座標を返す。

    形状(diameter/length)には依存しないためPlugParamsは受け取らない。
    frame_model側が保持部の目標位置として参照するために公開している。
    """
    x_pos = side * gap / 2
    z_pos = nostril_depth_z(depth_front)
    return np.array([x_pos, _PLUG_Y_OFFSET, z_pos])


def plug_outer_end(
    plug: PlugParams, gap: float, depth_front: float, side: Literal[-1, 1]
) -> np.ndarray:
    """指定側の鼻栓プレースホルダーの、外側(鼻の外に露出している側)の端点座標を返す。

    yが負の向き(_PLUG_Y_OFFSETの正負の説明を参照)が鼻先の外側方向なので、
    中心からlength/2だけ-y方向にずらした点が露出端になる。frame_modelの
    保持部は、鼻孔の奥にあたる中心ではなくこの露出端を目標位置にする
    """
    center = plug_center(gap, depth_front, side)
    return center - np.array([0.0, plug.length / 2, 0.0])


def _build_plug(
    plug: PlugParams, gap: float, depth_front: float, side: Literal[-1, 1]
) -> trimesh.Trimesh:
    """鼻栓本体(円柱)のプレースホルダーを、指定側の鼻孔位置に配置する。

    鼻孔の深さ方向はnostril_depth_zと同じy軸(鼻先から鼻の内部へ向かう
    向き)。trimesh.creation.cylinderの既定の軸はzなので、x軸まわりに
    90度回転させてyに揃える。配置位置(x_pos・y_pos・z_pos)はplug_centerと
    同じ値を使う
    """
    mesh = trimesh.creation.cylinder(radius=plug.diameter / 2, height=plug.length)
    rotate_to_y = trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
    mesh.apply_transform(rotate_to_y)
    mesh.apply_translation(plug_center(gap, depth_front, side))

    return mesh


def build_plug_pair(
    plug: PlugParams, gap: float, depth_front: float
) -> tuple[trimesh.Trimesh, trimesh.Trimesh]:
    """左右の鼻栓プレースホルダーを構築する(着色済み)。"""
    plug_left, plug_right = (
        _build_plug(plug, gap=gap, depth_front=depth_front, side=side)
        for side in (-1, 1)
    )
    plug_left.visual.face_colors = [120, 160, 220, 200]
    plug_right.visual.face_colors = [120, 160, 220, 200]
    return plug_left, plug_right
