"""フレームの仮形状(FrameParamsの5変数): ゼンマイ(渦巻きばね)状のコイル+ステム。

ユーザーのスケッチ(ピアスの丸い部分を渦巻き状にしたもの)を再現した設計。
鼻栓に刺すステムの部分はearrings(「b」字型)と共通で、鼻翼の外側の皮膚の
1点(アンカー)を起点に、そこから鼻の下を回り込んでステムへつながる
(commons/plug_model.pyのPlugParamsはプレースホルダーとして実体を維持)。
earringsと違うのは、アンカーからもう一方へ伸びる部分が「太いリング1個」
ではなく、半径が徐々に小さくなる渦巻き(コイル)である点。実際の鼻ピアス
のフープのように鼻翼を挟んで留める機構(clip)ではなく、コイルは鼻翼の
外側にぶら下がる装飾で、保持力はもっぱらステムと鼻栓(ティッシュ)の
摩擦に依る(evaluation.pyのモジュールdocstring参照)。

## 幾何(座標系: x=左右、y=鼻先(0)→鼻筋、z=前後(前面が+)。earrings.frame_model
と同じ)

コイルもコネクタもxy平面(z=鼻栓の軸の高さ、nostril_depth_z)の上に描く。

- **アンカー(_anchor)**: 高さ_ANCHOR_Y・鼻栓の軸の高さでx軸方向にレイを
  飛ばして実測した皮膚のx座標(_skin_x)から_ANCHOR_OFFSETだけ外側に
  出た点。ここが経路の分岐点で、片方はコイル、もう片方はコネクタ
  (鼻の下を回り込んでステムへ)につながる。earringsのring_depthのような
  「皮膚に押し込む」量は持たない(クリップとして機能する設計ではなく、
  アンカーは単に皮膚の少し外側に置かれた1点。_ANCHOR_OFFSETの理由は
  同定数のコメント参照)。
- **コイル(spiral_points)**: アンカーを起点(半径frame.start_radius)に、
  中心を挟んで鼻の反対側(外側)へ膨らみながら、鼻先側(+y)へ巻き上がって
  いく渦巻き。半径はframe.turns回転する間にframe.end_radiusまで直線的に
  小さくなる(アルキメデスの渦巻き)。中心は「アンカーから半径分だけ
  外側」に置く(center_x=end_x+start_radius)ため、アンカーは中心から
  見て真後ろ(鼻側、角度π)にある。角度をπから2π*frame.turns分減らし
  ながら進む(sinが正になる向き=鼻先側へ巻き上がる)ことで、ユーザーの
  スケッチのように、アンカーから鼻の横を上がりながら丸まっていく形に
  なる。
- **コネクタ(coil_points内、spiral_pointsの後に続く部分)**: アンカーから
  鼻の下(鼻栓の露出面より下の空間、bottom_y)へ真っ直ぐ降り、そこから
  内側(-x)へ直線移動、鼻栓の軸の手前で半径_FILLET_RADIUSの小さな曲げに
  よって上向きに変わり、鼻栓の軸の真下に達する(earrings.frame_modelの
  ring_pointsが使うのと同じ直線+フィレットの組み立て方)。bottom_yは
  plug_outer_end(鼻栓の露出面)から_BOTTOM_MARGINだけさらに下げた固定値
  (frameのどの変数にも依存しない)なので、earringsのhook_reach_margin/
  stem_entry_marginに相当する制約は不要(構造上つねに満たされる)。
- **ステム(stem_points)**: コネクタの終点(鼻栓の軸の真下、露出面より下)
  から鼻栓の軸に沿ってframe.stem_lengthだけ真上(+y)へ伸びる直線。
  earrings.frame_model.stem_pointsと同じ。

## 探索変数・ファイル内の並び順

FrameParamsの5変数: turns/start_radius/end_radius(コイルの形状)、
wire_thickness(コイル・コネクタ・ステムに共通の線径。1本の連続した
針金という想定のため太さを分けない。earringsの「リングは太くステムは
細く」という方針とは異なる)、stem_length(ステムの長さ)。

ファイル内の並び順: 定数・FrameParams → 経路の点列を計算する関数
(spiral_points, coil_points, stem_points, build_side_paths等) →
メッシュ化・幾何判定のユーティリティ(_tube_mesh, _signed_distance_to_body。
earrings.frame_modelと同一実装) → validate_*(build_frame_pairが呼ぶ順) →
build_frame_pair。

frameに依存する検証(radius_order_margin/coil_clearance_margin/
connector_clearance_margin/stem_clearance_margin/plug_insertion_margin/
plug_overshoot_margin)は、例外を送出するvalidate_*と、違反量を返すだけの
*_margin(scripts/spiral/evaluation.pyのevaluate_frameが制約として使う)の
2種類を用意している(理由はearrings.frame_modelのモジュールdocstring参照)。
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import trimesh
from shapely.geometry import Point

from commons.nose_model import (
    NoseParams,
    build_nose_body,
    nostril_depth_z,
    tip_cap_min_y,
)
from commons.plug_model import PlugParams, plug_outer_end

# フレームのプレースホルダーの色。earrings.frame_model._FRAME_COLORと同じ
# 理由(半透明の鼻本体・鼻栓越しでもコイル・ステムがはっきり見えるように
# 高めのalpha)で同じ値を使う
_FRAME_COLOR = [90, 90, 100, 200]
# アンカー(コイルとコネクタの分岐点)のy座標(mm)。earrings.frame_model.
# _RING_CONTACT_Yと同じ理由(鼻翼の隆起の中ほど)で同じ値を使う
_ANCHOR_Y = 4.0
# _skin_xがレイを飛ばし始める、鼻の外側の十分遠い位置(x座標の絶対値、mm)。
# earrings.frame_model._SKIN_RAY_ORIGIN_Xと同じ
_SKIN_RAY_ORIGIN_X = 40.0
# アンカーを、_skin_xの実測値からどれだけ外側(+x方向)へ逃がすか(mm)。
# earrings.frame_model._ROUND_CAP_OFFSETと同じ理由: build_frame_pairが
# コイルの先端(spiral_pointsの終端、coil_pointsの始端)に丸い先端
# (_tube_meshのround_start=True)を付けるが、アンカー自体もコイルの経路の
# 一部(coil_pointsの終端側)であり、皮膚のごく近くを通るため、実測の
# 半径(wire_thickness/2)相当の位置に置くと球や円形断面の丸みで皮膚へ
# わずかにめり込む。_ROUND_CAP_OFFSETほど厳密に測っていない暫定値
# (GAを動かしながら見直す前提)
_ANCHOR_OFFSET = 0.8
# コネクタが鼻の下を通る高さ(y座標、mm)を、鼻栓の露出面(plug_outer_end)
# からさらにどれだけ下げるか。frameのどの変数にも依存しない固定オフセット
# にすることで、コネクタの終点(=ステムの始点)が常に露出面より下から
# 始まる(earrings.frame_modelのstem_entry_marginに相当する制約が不要に
# なる)。値はearrings.frame_model._FILLET_RADIUS分の余裕を見込んだ暫定値
_BOTTOM_MARGIN = 1.5
# コネクタの小さな曲げ(fillet)の半径(mm)と、その四分円を近似する点数。
# earrings.frame_model._FILLET_RADIUS/_FILLET_SAMPLESと同じ
_FILLET_RADIUS = 1.5
_FILLET_SAMPLES = 6
# spiral_pointsの折れ線近似の分割数。earrings.frame_modelの円弧
# (_RING_SAMPLESで270度程度)よりturns回転分だけ長い経路になりうるため
# 多めに取る
_SPIRAL_SAMPLES = 96
# コイル・コネクタの実際のチューブ表面が鼻本体メッシュへめり込んでよい
# 上限を、線径(frame.wire_thickness/2)に対する比率で指定。earrings.
# frame_model._RING_EMBED_RATIOと同じ理由・同じ値(線材の円形断面が
# 鼻の曲面と完全には一致しないことに由来する、押し込みなしでも避けられない
# 残留めり込みの水準を上限にする)
_EMBED_RATIO = 0.5
# start_radiusに対してend_radiusがどれだけ小さくなければならないか(mm)。
# 0だけを要求する(end_radius<start_radius)と、GAがほぼ差のない値を選び
# 「渦を巻いている」ようには見えない個体になりうるため、視覚的に半径が
# 縮んでいくとわかる最低限の差を要求する暫定値
_MIN_RADIUS_DROP = 1.0
# _tube_meshが使う円形断面ポリゴンの近似精度。earrings.frame_model.
# _TUBE_POLYGON_RESOLUTIONと同じ
_TUBE_POLYGON_RESOLUTION = 8
# _signed_distance_to_bodyが疑似法線による符号判定を信頼する距離の上限
# (mm)。earrings.frame_model._PSEUDO_NORMAL_MAX_DISTANCEと同じ
_PSEUDO_NORMAL_MAX_DISTANCE = 2.0
# ステムが鼻栓に刺さっているべき最小の長さ・上限を、plug.lengthに対する
# 比率で指定。earrings.frame_model._MIN_INSERTION_TO_PLUG_LENGTH/
# _MAX_INSERTION_TO_PLUG_LENGTHと同じ
_MIN_INSERTION_TO_PLUG_LENGTH = 0.6
_MAX_INSERTION_TO_PLUG_LENGTH = 0.9

# 片側のコイル経路・ステム経路の点列のペア(coil_points, stem_points)。
# earrings.frame_model.SidePathsと同じ役割
SidePaths = tuple[list[np.ndarray], list[np.ndarray]]


@dataclass(frozen=True)
class FrameParams:
    """フレームの仮寸法パラメータ(単位: mm)。

    ゼンマイ状のコイル+細いステムという単純なプレースホルダーで、後から
    実際の造形(3Dプリント/粘土)に向けて調整・最適化する。
    """

    turns: float = 2.0
    start_radius: float = 5.0
    end_radius: float = 1.5
    wire_thickness: float = 1.0
    stem_length: float = 10.0

    def __post_init__(self) -> None:
        if self.turns <= 0:
            raise ValueError(f"turns は正の値にすること: {self.turns}")
        if self.start_radius <= 0:
            raise ValueError(f"start_radius は正の値にすること: {self.start_radius}")
        if self.end_radius <= 0:
            raise ValueError(f"end_radius は正の値にすること: {self.end_radius}")
        if self.wire_thickness <= 0:
            raise ValueError(f"wire_thickness は正の値にすること: {self.wire_thickness}")
        if self.stem_length <= 0:
            raise ValueError(f"stem_length は正の値にすること: {self.stem_length}")
        # end_radius < start_radius(渦が中心に向かって細くなる)は検証
        # しない。探索範囲(_SEARCH_SPACE)はそれぞれ独立した範囲を持つため、
        # GAがこの関係を満たさない組み合わせを生成しうる。ここで例外を
        # 送出するとFrameParamsの構築自体が失敗し、evaluate_frame側で
        # 制約として拾えなくなるため、radius_order_margin/validate_
        # radius_order側で扱う(earrings.frame_model.FrameParams.
        # __post_init__のコメント参照)


def _skin_x(body: trimesh.Trimesh, y: float, z: float, side: Literal[-1, 1]) -> float | None:
    """(y, z)の高さで鼻の外側からx軸方向にレイを飛ばし、鼻翼の外側の皮膚に
    最初に当たる点のx座標を返す(当たらなければNone)。

    earrings.frame_model._skin_xと同一実装。
    """
    origin = np.array([[side * _SKIN_RAY_ORIGIN_X, y, z]])
    direction = np.array([[-side, 0.0, 0.0]])
    locations, _, _ = body.ray.intersects_location(origin, direction, multiple_hits=False)
    if len(locations) == 0:
        return None
    return float(locations[0, 0])


def _anchor(
    params: NoseParams, body: trimesh.Trimesh, side: Literal[-1, 1]
) -> tuple[float, float, float]:
    """アンカー(コイルとコネクタの分岐点)のx・y・zを返す(x座標は正の
    正準値。モジュールdocstring「幾何」参照)。"""
    z0 = nostril_depth_z(params.tip_depth_front)
    skin_x = _skin_x(body, _ANCHOR_Y, z0, side)
    if skin_x is None:
        raise ValueError(
            f"アンカーの高さ(y={_ANCHOR_Y})・鼻栓の軸の高さ(z={z0:.2f})で"
            "鼻翼の皮膚が見つからない。_ANCHOR_Yを見直すこと"
        )
    return abs(skin_x) + _ANCHOR_OFFSET, _ANCHOR_Y, z0


def spiral_points(
    frame: FrameParams, params: NoseParams, body: trimesh.Trimesh, side: Literal[-1, 1]
) -> list[np.ndarray]:
    """コイル(渦巻き)の経路(点列)を返す(points[0]がアンカー、points[-1]
    がコイルの先端=渦の中心付近の開放端)。

    中心を(アンカーからframe.start_radiusだけ外側)に置いたアルキメデスの
    渦巻き。アンカーは中心から見て角度π(鼻側)にあり、そこから角度を
    2π*frame.turns分「減らし」ながら進む(sinが正の向き=鼻先側(+y)へ
    巻き上がる)。半径はframe.start_radiusからframe.end_radiusまで
    turns全体で直線的に小さくなる。モジュールdocstring「幾何」参照。
    """
    end_x, end_y, z0 = _anchor(params, body, side)
    center_x = end_x + frame.start_radius
    center_y = end_y
    theta0 = np.pi
    theta1 = theta0 - 2 * np.pi * frame.turns
    thetas = np.linspace(theta0, theta1, _SPIRAL_SAMPLES)
    radii = np.linspace(frame.start_radius, frame.end_radius, _SPIRAL_SAMPLES)
    xs = center_x + radii * np.cos(thetas)
    ys = center_y + radii * np.sin(thetas)
    return [np.array([side * x, y, z0]) for x, y in zip(xs, ys)]


def coil_points(
    frame: FrameParams,
    plug: PlugParams,
    params: NoseParams,
    body: trimesh.Trimesh,
    side: Literal[-1, 1],
) -> list[np.ndarray]:
    """コイル(渦巻きの先端→アンカー)+コネクタ(アンカー→ステムの始点)を
    連結した1本の経路(点列)を返す(points[0]がコイルの先端=開放端、
    points[-1]がステムの始点)。

    spiral_pointsが返す経路(アンカー→コイルの先端)を反転して先頭に置き、
    続けてコネクタ(アンカーから鼻の下を回り込んでステムの軸へ)を繋げる。
    コネクタは3区間: (1) アンカーから鼻の下(bottom_y=鼻栓の露出面より
    _BOTTOM_MARGIN下)へ直線で降りる、(2) 鼻栓の軸の手前_FILLET_RADIUS
    まで内側(-x)へ直線移動、(3) 半径_FILLET_RADIUSの小さな曲げで
    向きを内側→上へ変える(earrings.frame_model.ring_pointsの区間2・3と
    同じ組み立て方)。
    """
    spiral = spiral_points(frame, params, body, side)
    end_x, end_y, z0 = _anchor(params, body, side)
    outer_y = plug_outer_end(plug, params.nostril_gap, params.tip_depth_front, side)[1]
    bottom_y = outer_y - _BOTTOM_MARGIN
    axis_x = params.nostril_gap / 2
    fillet_center_x = axis_x + _FILLET_RADIUS

    xs = [end_x, fillet_center_x]
    ys = [bottom_y, bottom_y]
    for t in np.linspace(1.5 * np.pi, np.pi, _FILLET_SAMPLES)[1:]:
        xs.append(fillet_center_x + _FILLET_RADIUS * np.cos(t))
        ys.append(bottom_y + _FILLET_RADIUS + _FILLET_RADIUS * np.sin(t))
    connector = [np.array([side * x, y, z0]) for x, y in zip(xs, ys)]

    return list(reversed(spiral)) + connector


def stem_points(
    frame: FrameParams, coil: list[np.ndarray]
) -> list[np.ndarray]:
    """鼻栓の軸上をまっすぐ上(+y、鼻の奥)へ伸びるステムの経路(点列、2点)
    を返す(path[0]がコネクタの終点=小さな曲げの終わり、path[-1]が上端)。

    earrings.frame_model.stem_pointsと同じ。
    """
    start = coil[-1]
    top = start + np.array([0.0, frame.stem_length, 0.0])
    return [start, top]


def build_side_paths(
    frame: FrameParams,
    plug: PlugParams,
    params: NoseParams,
    body: trimesh.Trimesh,
    side: Literal[-1, 1],
) -> SidePaths:
    """指定側のコイル経路・ステム経路の点列を返す(メッシュ生成なし)。

    earrings.frame_model.build_side_pathsと同じ役割。
    """
    coil = coil_points(frame, plug, params, body, side)
    stem = stem_points(frame, coil)
    return coil, stem


def _tube_mesh(
    points: list[np.ndarray], radius: float, round_start: bool = False
) -> trimesh.Trimesh:
    """点列を、半径radiusの円形断面で押し出した1本の連続チューブにする。

    earrings.frame_model._tube_meshと同一実装。round_start=Trueは
    points[0](コイルの先端=開放端)を丸くする(ユーザー要望「リングの
    先端は丸みを帯びてほしい」をコイルの先端にも適用する)。
    """
    polygon = Point(0, 0).buffer(radius, resolution=_TUBE_POLYGON_RESOLUTION)
    tube = trimesh.creation.sweep_polygon(polygon, np.array(points))
    if round_start:
        sphere = trimesh.creation.icosphere(subdivisions=2, radius=radius)
        sphere.apply_translation(points[0])
        tube = tube.union(sphere, engine="manifold")
    return tube


def _signed_distance_to_body(
    body: trimesh.Trimesh, points: np.ndarray
) -> np.ndarray:
    """各点から鼻本体表面までの符号付き距離を返す(正=外側、負=内側/めり込み)。

    earrings.frame_model._signed_distance_to_bodyと同一実装。
    """
    closest, distance, triangle_id = trimesh.proximity.closest_point(body, points)
    normals = body.face_normals[triangle_id]
    direction = points - closest
    sign = np.sign(np.einsum("ij,ij->i", direction, normals))

    far = distance > _PSEUDO_NORMAL_MAX_DISTANCE
    if np.any(far):
        inside = body.contains(points[far])
        sign[far] = np.where(inside, -1.0, 1.0)

    return distance * sign


def validate_target_reach(plug: PlugParams, params: NoseParams) -> None:
    """鼻栓の露出端が鼻本体メッシュのy方向の範囲より外側にあることを
    検証する。earrings.frame_model.validate_target_reachと同じ。
    """
    gap = params.nostril_gap
    depth_front = params.tip_depth_front
    min_y = tip_cap_min_y(params)
    for side in (-1, 1):
        target_y = plug_outer_end(plug, gap, depth_front, side)[1]
        if target_y >= min_y:
            raise ValueError(
                "鼻栓の露出端(y="
                f"{target_y:.2f})が鼻本体メッシュの範囲(y>={min_y:.2f})に"
                "重なっている。鼻栓が鼻孔から露出していないため、"
                "PlugParamsのlength/_PLUG_Y_OFFSETを見直すこと"
            )


def validate_anchor_height(params: NoseParams, body: trimesh.Trimesh) -> None:
    """アンカーの高さ(_ANCHOR_Y)・鼻栓の軸の高さ(z)で、左右とも鼻翼の
    皮膚がレイキャストで見つかることを検証する。earrings.frame_model.
    validate_ring_heightと同じ役割。
    """
    z0 = nostril_depth_z(params.tip_depth_front)
    for side in (-1, 1):
        if _skin_x(body, _ANCHOR_Y, z0, side) is None:
            raise ValueError(
                f"アンカーの高さ(y={_ANCHOR_Y})・鼻栓の軸の高さ(z={z0:.2f})で"
                f"鼻翼の皮膚が見つからない(side={side})。_ANCHOR_Yを見直すこと"
            )


def coil_protrusion(
    params: NoseParams, body: trimesh.Trimesh, sides: list[SidePaths]
) -> float:
    """コイルの最外点(鼻から最も離れた点)が、その高さの鼻翼の皮膚より
    外側へ出ている量(mm)を返す。左右のうち小さい方の値。

    earrings.frame_model.hoop_protrusionと同じ考え方だが、コイルは円弧
    ではなく渦巻きなので、最外点はcoilの点列全体(渦巻き+コネクタ)から
    argmaxで探す(コネクタは鼻の下・内側を通るため、実際にはほぼ常に
    渦巻き側の点が選ばれる)。scripts/spiral/evaluation.pyの意匠性の目的
    (visibility、最大化)が参照する。
    """
    z0 = nostril_depth_z(params.tip_depth_front)
    worst = np.inf
    for (coil, _), side in zip(sides, (-1, 1)):
        points = np.array(coil)
        outermost = points[np.argmax(np.abs(points[:, 0]))]
        skin_x = _skin_x(body, float(outermost[1]), z0, side)
        skin = abs(skin_x) if skin_x is not None else 0.0
        worst = min(worst, abs(outermost[0]) - skin)
    return float(worst)


def radius_order_margin(frame: FrameParams) -> float:
    """「渦は外側から中心に向かって細くなる」という設計方針(end_radius が
    start_radius より_MIN_RADIUS_DROP以上小さいこと)への違反量を返す
    (正=違反量、0以下=安全)。

    探索範囲(_SEARCH_SPACE)はstart_radius/end_radiusそれぞれ独立した
    範囲を持つため、GAがこの関係を満たさない組み合わせを生成しうる
    (FrameParams.__post_init__のコメント参照)。
    """
    return frame.end_radius - frame.start_radius + _MIN_RADIUS_DROP


def validate_radius_order(frame: FrameParams) -> None:
    """radius_order_marginが正(=違反)の場合に例外を送出する。"""
    margin = radius_order_margin(frame)
    if margin >= 0:
        raise ValueError(
            f"end_radius({frame.end_radius})はstart_radius({frame.start_radius})"
            f"より_MIN_RADIUS_DROP({_MIN_RADIUS_DROP}mm)以上小さくすること"
            "(渦が中心に向かって細くなる方針のため)"
        )


def _clearance_margin(
    points: list[np.ndarray], radius: float, body: trimesh.Trimesh, round_start: bool = False
) -> float:
    """点列を太さradiusのチューブにしたときの、鼻本体メッシュへのめり込み
    量が_EMBED_RATIO*radiusを超えていないかを返す(正=超過量、0以下=
    許容範囲内)。coil_clearance_margin/connector_clearance_marginが
    共有するロジック(earrings.frame_model.ring_clearance_marginと同じ
    考え方)。
    """
    allowed_embed = _EMBED_RATIO * radius
    tube = _tube_mesh(points, radius, round_start=round_start)
    signed_distance = _signed_distance_to_body(body, tube.vertices)
    embed_amount = -signed_distance
    return float((embed_amount - allowed_embed).max())


def coil_clearance_margin(
    frame: FrameParams, sides: list[SidePaths], body: trimesh.Trimesh
) -> float:
    """コイル(コネクタ含む)の実際のチューブ表面の鼻本体メッシュへの
    めり込み量が、線径に比例した許容量(_EMBED_RATIO)を超えていないかを
    返す(正=超過量、0以下=許容範囲内)。左右のうち最も厳しい点の値。

    コイルは鼻翼を挟むクリップではなく単に外側にぶら下がる装飾なので、
    どの部分も皮膚に意図的にめり込む理由がない(earrings.frame_modelの
    ring_depthのような押し込み変数を持たない)。それでも線材の円形断面と
    鼻の曲面が完全には一致しないため、押し込みなしでも避けられない
    残留めり込みの水準までは許容する(_EMBED_RATIOのコメント参照)。
    round_start=Trueで検証する(build_frame_pairが実際に書き出す
    ジオメトリと一致させるため。earrings.frame_model.ring_clearance_margin
    のdocstring参照)。
    """
    radius = frame.wire_thickness / 2
    return max(_clearance_margin(coil, radius, body, round_start=True) for coil, _ in sides)


def validate_coil_clearance(
    frame: FrameParams, sides: list[SidePaths], body: trimesh.Trimesh
) -> None:
    """coil_clearance_marginが正(=違反)の場合に例外を送出する。"""
    margin = coil_clearance_margin(frame, sides, body)
    if margin > 0:
        raise ValueError(
            f"wire_thickness({frame.wire_thickness})のチューブが、線径に"
            f"比例した許容めり込み量(_EMBED_RATIO={_EMBED_RATIO})を"
            f"{margin:.3f}mm超えて実際に鼻表面へめり込んでいる。turns/"
            "start_radius/end_radiusを見直すこと"
        )


def stem_clearance_margin(
    sides: list[SidePaths], body: trimesh.Trimesh, wire_thickness: float
) -> float:
    """ステムの実際のチューブ表面が、鼻本体メッシュにめり込んでいないかを
    返す(正=めり込み量、0以下=安全)。左右のうち最も厳しい点の値。
    earrings.frame_model.stem_clearance_marginと同じ役割(ただし
    ステムも線径wire_thickness共通のため、許容量なしで単純にめり込みを
    禁止する点も同じ)。
    """
    radius = wire_thickness / 2
    worst = -np.inf
    for _, stem in sides:
        tube = _tube_mesh(stem, radius)
        signed_distance = _signed_distance_to_body(body, tube.vertices)
        worst = max(worst, float(-signed_distance.min()))
    return worst


def validate_stem_clearance(
    sides: list[SidePaths], body: trimesh.Trimesh, wire_thickness: float
) -> None:
    """stem_clearance_marginが正(=めり込み)の場合に例外を送出する。"""
    margin = stem_clearance_margin(sides, body, wire_thickness)
    if margin > 0:
        raise ValueError(
            f"wire_thickness({wire_thickness})のステムが実際に鼻表面へ"
            f"めり込んでいる(最大めり込み量: {margin:.3f}mm)。ステムが鼻孔の"
            "壁や奥の肉と交差している可能性がある"
        )


def plug_insertion_depth(
    plug: PlugParams, params: NoseParams, stem: list[np.ndarray], side: Literal[-1, 1]
) -> float:
    """ステムが鼻栓(PlugParams)の内部に入り込んでいる長さを返す(mm)。
    earrings.frame_model.plug_insertion_depthと同じ。
    """
    outer_y = plug_outer_end(plug, params.nostril_gap, params.tip_depth_front, side)[1]
    inner_y = outer_y + plug.length
    start_y, end_y = stem[0][1], stem[-1][1]
    return min(end_y, inner_y) - max(start_y, outer_y)


def plug_insertion_margin(
    plug: PlugParams, params: NoseParams, stem: list[np.ndarray], side: Literal[-1, 1]
) -> float:
    """刺さり込み(plug_insertion_depth)が最小長さに足りない不足量を返す
    (正=違反量、0以下=十分刺さっている)。earrings.frame_model.
    plug_insertion_marginと同じ。
    """
    minimum = plug.length * _MIN_INSERTION_TO_PLUG_LENGTH
    return minimum - plug_insertion_depth(plug, params, stem, side)


def plug_overshoot_margin(
    plug: PlugParams, params: NoseParams, stem: list[np.ndarray], side: Literal[-1, 1]
) -> float:
    """ステムの先端が鼻栓を突き抜けている量を返す(正=違反量、0以下=安全)。
    earrings.frame_model.plug_overshoot_marginと同じ。
    """
    outer_y = plug_outer_end(plug, params.nostril_gap, params.tip_depth_front, side)[1]
    limit_y = outer_y + plug.length * _MAX_INSERTION_TO_PLUG_LENGTH
    return stem[-1][1] - limit_y


def build_frame_pair(
    frame: FrameParams, plug: PlugParams, params: NoseParams
) -> tuple[trimesh.Trimesh, trimesh.Trimesh]:
    """左右のフレーム(コイル+ステムの2部品からなるチューブ)を構築する
    (着色済み)。"""
    validate_target_reach(plug, params)
    body = build_nose_body(params)
    validate_anchor_height(params, body)
    validate_radius_order(frame)
    sides = [build_side_paths(frame, plug, params, body, side) for side in (-1, 1)]
    validate_coil_clearance(frame, sides, body)
    validate_stem_clearance(sides, body, frame.wire_thickness)
    for (_, stem), side in zip(sides, (-1, 1)):
        shortage = plug_insertion_margin(plug, params, stem, side)
        if shortage > 0:
            raise ValueError(
                "ステムの鼻栓への刺さり込みが最小長さ(鼻栓の長さの"
                f"{_MIN_INSERTION_TO_PLUG_LENGTH:.0%})に{shortage:.3f}mm足りない。"
                "stem_lengthを大きくすること"
            )
        overshoot = plug_overshoot_margin(plug, params, stem, side)
        if overshoot > 0:
            raise ValueError(
                f"ステムが鼻栓を{overshoot:.3f}mm突き抜けている。stem_lengthを"
                "小さくすること"
            )

    radius = frame.wire_thickness / 2

    meshes = []
    for coil, stem in sides:
        coil_mesh = _tube_mesh(coil, radius, round_start=True)
        stem_mesh = _tube_mesh(stem, radius)
        # ブーリアン結合で1つの閉じた立体にする理由はearrings.frame_model.
        # build_frame_pairと同じ(3Dプリント用STLとして正しい単一の
        # 多様体にするため)
        combined = coil_mesh.union(stem_mesh, engine="manifold")
        combined.visual.face_colors = _FRAME_COLOR
        meshes.append(combined)

    return meshes[0], meshes[1]
