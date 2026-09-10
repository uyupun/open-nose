"""鼻栓本体のプレースホルダー。"""

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

    lengthは、鼻栓プレースホルダーとしての寸法だけでなく、露出端
    (plug_outer_end、frame_model.connector_pointsのダイブ区間の目標点)を
    鼻本体メッシュの範囲(tip_cap_min_y)からどれだけ引き離すかも兼ねている。
    露出端のyは_PLUG_Y_OFFSET - length/2で決まり、これが鼻本体メッシュの
    範囲から近すぎると、ダイブ区間のチューブ(半径arm_thickness/2)の
    終端キャップが実際にメッシュへ食い込む(ダイブの向きが鼻表面沿いの
    高さから鼻栓の実際の深さへ大きく下がる必要があるため、常にy軸に
    対して斜めになり、キャップがy方向に半径分近く広がるため)。既定値
    (8.0mm)では余裕が0.25mmしかなく、arm_thickness=0.5mm(探索範囲の
    下限)を超えるとほぼ確実に違反していたため、12.0mmに引き上げて
    余裕を約2.25mmに拡大した。実測ではarm_thickness=4.4mm程度までは
    安全(探索範囲の上限8.0mmまでは余裕でカバーできていない)。他の閾値と
    同様、暫定値でGAを実際に動かしながら見直す前提。
    """

    diameter: float = 6.0
    length: float = 12.0

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


# 鼻栓プレースホルダーの色(青、強めの半透明)。フレームのステムは鼻栓の
# 中を軸方向に通って刺さる(models.frame_model.stem_points参照)ため、
# 鼻栓が不透明に近い(以前はalpha=200)とステムが隠れて「刺さっているか」
# を目視できない。フレーム(alpha=200)より十分低いalphaにして、鼻栓越しに
# ステムが見えるようにする。OBJはalphaを保持できないため、この効果を
# 確認するにはglTF(.glb)で書き出す(export_model.py/export_frame.py参照)
_PLUG_COLOR = [120, 160, 220, 80]


def build_plug_pair(
    plug: PlugParams, gap: float, depth_front: float
) -> tuple[trimesh.Trimesh, trimesh.Trimesh]:
    """左右の鼻栓プレースホルダーを構築する(着色済み)。"""
    plug_left, plug_right = (
        _build_plug(plug, gap=gap, depth_front=depth_front, side=side)
        for side in (-1, 1)
    )
    plug_left.visual.face_colors = _PLUG_COLOR
    plug_right.visual.face_colors = _PLUG_COLOR
    return plug_left, plug_right
