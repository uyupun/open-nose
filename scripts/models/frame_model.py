"""フレームの仮形状(PROJECT.md の「フレームの設計変数(暫定4変数)」に対応)。

メガネのように鼻筋(鼻の付け根)まで伸ばす必要はなく、実物の鼻クリップ
(水泳用など)のように鼻先まわりだけで完結する小さなクリップとして表現する。
鼻中隔の上あたりを起点に、鼻の前面より外側を保ちながら鼻栓の露出端まで
伸びるプレースホルダー(円柱の連結)にしている(_build_arm, _build_holder参照)。
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import trimesh

from .nose_model import NoseParams, surface_profile, tip_cap_depth_front, tip_cap_min_y
from .plug_model import PlugParams, plug_outer_end

# フレームのプレースホルダーの色(グレー、半透明)
_FRAME_COLOR = [90, 90, 100, 220]
# 保持部(先端の球)の半径を、arm_thicknessに対する何倍にするか
_HOLDER_RADIUS_RATIO = 1.4
# アームの起点(クリップ位置)のy座標(鼻先=0からの距離、mm)。鼻中隔の
# 上あたり、鼻翼が始まる手前を想定した固定値(_ALAE_BUMP_SPANの範囲内)
_ARM_ANCHOR_Y = 6.0
# アーム・保持部への接続経路を近似する区間の分割数。鼻先に近づくほど
# 前面の迫り出しが変化するため、直線1本ではなく複数区間の折れ線で
# 表面のカーブに追従させる(_build_arm参照)
_ARM_SAMPLES = 5
# 保持部への接続経路(_build_holder)を近似する折れ線の分割数。多いほど
# 各yでの実測値(_depth_front_at)に沿った経路になり、表面に近づく
_CONNECTOR_SAMPLES = 24
# アーム・保持部を鼻の表面からどれだけ浮かせるか(mm)。0だと表面にちょうど
# 接してしまい、断面の丸め計算の誤差でわずかにめり込む可能性があるため
_SURFACE_CLEARANCE = 0.8


@dataclass(frozen=True)
class FrameParams:
    """フレームの仮寸法パラメータ(単位: mmおよび度)。

    棒状のアーム+球状の保持部という単純なプレースホルダーで、
    後から実際の造形(3Dプリント/粘土)に向けて調整・最適化する。
    """

    clip_angle: float = 20.0
    arm_length: float = 6.0
    arm_thickness: float = 2.0
    holder_offset: float = 12.0

    def __post_init__(self) -> None:
        for name in ("arm_length", "arm_thickness"):
            value = getattr(self, name)
            if value <= 0:
                raise ValueError(f"{name} は正の値にすること: {value}")
        if not (0.0 < self.clip_angle < 180.0):
            raise ValueError(
                f"clip_angle は0〜180度の範囲にすること: {self.clip_angle}"
            )
        if self.holder_offset < 0:
            raise ValueError(f"holder_offset は0以上にすること: {self.holder_offset}")


def _depth_front_at(params: NoseParams, y: float) -> float:
    """yにおける前面迫り出しを返す。y>=0はsurface_profile(通常のテーパー)、
    y<0は鼻先の丸め区間の実測値(tip_cap_depth_front)を使い分ける
    (surface_profileの延長では丸め処理による窄まりが反映されないため)。
    """
    if y >= 0:
        return surface_profile(params, y)[2]
    return tip_cap_depth_front(params, y)


def _build_arm(
    frame: FrameParams, params: NoseParams, side: Literal[-1, 1]
) -> tuple[trimesh.Trimesh, np.ndarray]:
    """鼻中隔の上あたり(前面表面のすぐ外)を起点に、clip_angleで開きながら
    鼻先方向へarm_length伸びる1本のアーム(複数区間の折れ線)を返す。

    起点・経路とも、その時点のyにおける前面迫り出し(surface_profileの
    depth_front)より確実に外側(z方向)を保つことで、鼻の内部を貫通しない
    ようにしている(depth_front(y)はそのyの断面が取りうる最大のzなので、
    zがそれを上回っている限りxがどの値でも外側にいることが保証される)。
    xは起点(鼻中隔中央、x=0)からclip_angleに応じて左右に開いていく
    (小さいほど鼻中隔寄りにきつく締まり、大きいほど鼻翼側まで開く)。
    あわせてアーム下端の座標も返す(_build_holderが保持部への接続に使う)。
    """
    ys = np.linspace(_ARM_ANCHOR_Y, _ARM_ANCHOR_Y - frame.arm_length, _ARM_SAMPLES)

    points = []
    for y in ys:
        _, _, depth_front = surface_profile(params, y)
        z = depth_front + _SURFACE_CLEARANCE
        x = side * np.tan(np.radians(frame.clip_angle)) * (_ARM_ANCHOR_Y - y)
        points.append([x, y, z])

    segments = [
        trimesh.creation.cylinder(
            radius=frame.arm_thickness / 2, segment=[points[i], points[i + 1]]
        )
        for i in range(len(points) - 1)
    ]
    mesh = trimesh.util.concatenate(segments)
    return mesh, np.array(points[-1])


def _build_holder(
    frame: FrameParams, params: NoseParams, arm_end: np.ndarray, target: np.ndarray
) -> trimesh.Trimesh:
    """アーム下端(arm_end)から鼻栓の露出端(target)まで到達する接続部と、
    その先端の保持部(球)を返す。

    arm_endからtargetへ直線で向かうと鼻の内部を貫通しうるため、まず
    _build_armと同じ考え方(その時点のyでの前面迫り出しより外側を保つ)で
    targetのx, yまで折れ線で近づく(_CONNECTOR_SAMPLES点、xはarm_endから
    targetまで線形補間)。鼻先の丸め区間(tip_cap_depth_front)は
    yが進むにつれ必要な高さが下がっていく形状なので、区間ごとに
    実測値を計算することで表面に近い経路になる。
    最後にtargetへ向けてzを差し込む(approach→holder_pos)。targetのyは
    鼻本体メッシュの範囲より外側(build_frame_pairが検証する)なので、
    この区間は鼻の実体が存在しない位置を通ることになり安全。
    holder_offsetは、この最後の区間でtargetまでの距離を超えないよう
    クランプした上での実際の到達距離
    """
    ys = np.linspace(arm_end[1], target[1], _CONNECTOR_SAMPLES)
    xs = np.linspace(arm_end[0], target[0], _CONNECTOR_SAMPLES)

    path = [arm_end]
    for i in range(1, _CONNECTOR_SAMPLES):
        y = ys[i]
        z = _depth_front_at(params, y) + _SURFACE_CLEARANCE
        path.append(np.array([xs[i], y, z]))
    approach = path[-1]

    dive = target - approach
    dive_dist = np.linalg.norm(dive)
    dive_dir = dive / dive_dist
    holder_pos = approach + dive_dir * min(frame.holder_offset, dive_dist)

    path.append(holder_pos)
    segments = [
        trimesh.creation.cylinder(radius=frame.arm_thickness / 2, segment=[path[i], path[i + 1]])
        for i in range(len(path) - 1)
        if not np.allclose(path[i], path[i + 1])
    ]
    holder = trimesh.creation.icosphere(
        subdivisions=2, radius=frame.arm_thickness * _HOLDER_RADIUS_RATIO
    )
    holder.apply_translation(holder_pos)

    return trimesh.util.concatenate(segments + [holder])


def build_frame_pair(
    frame: FrameParams, plug: PlugParams, params: NoseParams
) -> tuple[trimesh.Trimesh, trimesh.Trimesh]:
    """左右のフレーム(アーム+保持部)を構築する(着色済み)。"""
    gap = params.nostril_gap
    depth_front = params.tip_depth_front

    # _build_holderの最終区間(approach→holder_pos)が安全な理由は、targetの
    # yが鼻本体メッシュのy方向の範囲より外側にあることに依存している。
    # PlugParams/NoseParamsの組み合わせによってはこの前提が崩れうるため、
    # ここで明示的に検証する
    min_y = tip_cap_min_y(params)
    for side in (-1, 1):
        target_y = plug_outer_end(plug, gap, depth_front, side)[1]
        if target_y >= min_y:
            raise ValueError(
                "鼻栓の露出端(y="
                f"{target_y:.2f})が鼻本体メッシュの範囲(y>={min_y:.2f})に"
                "重なっている。保持部の経路が鼻を貫通する可能性があるため、"
                "PlugParamsのlength/_PLUG_Y_OFFSETを見直すこと"
            )

    sides = []
    for side in (-1, 1):
        arm, arm_end = _build_arm(frame, params, side)
        target = plug_outer_end(plug, gap, depth_front, side)
        holder = _build_holder(frame, params, arm_end, target)

        combined = trimesh.util.concatenate([arm, holder])
        combined.visual.face_colors = _FRAME_COLOR
        sides.append(combined)

    return sides[0], sides[1]
