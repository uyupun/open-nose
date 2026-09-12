"""フレームの仮形状(FrameParamsの4変数): ブリーズライト型の外側ブリッジ+ステム。

実際の鼻腔拡張テープ(ブリーズライト等)を再現した設計。鼻腔拡張テープは、
鼻の実際の丸み(曲率)より平らな板ばねを、小鼻の高さで鼻に貼り付けることで、
板ばねが「元の平らな形に戻ろうとする力」が小鼻を外側に押し開き、鼻腔
(鼻弁)を機械的に広げて呼吸を楽にする(貼るだけで、鼻の中には何も
入れない)。

このプロジェクトは「鼻栓(ティッシュ等)を留める」ことが目的のため、
テープ単体ではなく、ブリッジ(拡張機能)の左右の端からearrings/spiralと
同様のステムを伸ばし、鼻栓に刺して保持する機能を継続する(ハイブリッド
構成)。earrings/spiralが左右独立の2部品だったのに対し、この設計は
「両方の小鼻を同時に押し開く」という機構上、左右をブリッジでつないだ
1本の連続した部品になる。

## 幾何(座標系: x=左右、y=鼻先(0)→鼻筋、z=前後(前面が+)。earrings/spiralと同じ)

- **ブリッジ(bridge_points)**: 高さ_BRIDGE_Y(小鼻の隆起のあたり、
  earrings.frame_model._RING_CONTACT_Yと同じ理由で同じ高さ)で、鼻の
  実際の前面形状(commons.nose_model.front_surface_z_at_offset。実測
  ではなく解析的な近似式)に沿って、左の小鼻の外縁(x=-half_width)から
  右の小鼻の外縁(x=+half_width)まで横断する経路。half_widthは
  commons.nose_model.surface_profile_atの解析値(鼻本体メッシュを
  構築しなくても求まる)。各点は前面からBRIDGE_OFFSETだけ外側
  (+z方向)に浮かせる(円形断面のチューブが曲面にわずかにめり込む
  ことを避けるための、earrings.frame_model._ROUND_CAP_OFFSETと同じ
  発想の暫定値)。
- **コネクタ(_connector_points)**: ブリッジの各端から鼻の下(鼻栓の
  露出面より下の空間)へ回り込み、ステムの軸へ達する経路。spiral.
  frame_model.coil_pointsのコネクタ(直線+2箇所のフィレット)と同一の
  組み立て方。
- **ステム(stem_points)**: コネクタの終点から鼻栓の軸に沿って
  frame.stem_lengthだけ真上へ伸びる直線。earrings/spiral共通。

## 拡張力の物理近似(evaluation.pyが計算に使う幾何量)

ブリッジは板ばねとみなす。装着後の実際の曲率(1/actual_radius、
bridge_curvatureが実測)は鼻の形状で決まり自由変数ではない。frame.
natural_radius(装着前の自然な曲率半径。値が大きいほど平ら)が
actual_radiusより大きい(平らな)場合、装着時にブリッジは自然な形より
強く曲げられることになり、その反発力が小鼻を外側へ開く(ブリーズライト
と同じ原理)。deflection(たわみ)=1/actual_radius - 1/natural_radius
(正であるほど拡張力が強い)。curvature_margin(natural_radius >
actual_radiusを要求)を参照。

## 探索変数・ファイル内の並び順

FrameParamsの4変数: natural_radius(拡張力の源)、bridge_thickness
(ブリッジの太さ。拡張力にも「目立たなさ」にも効く)、stem_thickness
(ステムの太さ。細いまま)、stem_length。「ブリッジは太く、ステムは
細く」という設計方針はthickness_order_marginで保証する(earrings/
spiralと同じ)。

ファイル内の並び順: 定数・FrameParams → 経路の点列を計算する関数
(bridge_points, build_paths等) → 幾何量の計測(bridge_curvature) →
メッシュ化・幾何判定のユーティリティ(_tube_mesh, _signed_distance_to_body) →
validate_*(build_frameが呼ぶ順) → build_frame。
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import trimesh
from shapely.geometry import Point

from commons.nose_model import (
    NoseParams,
    build_nose_body,
    front_surface_z_at_offset,
    nostril_depth_z,
    surface_profile_at,
    tip_cap_min_y,
)
from commons.plug_model import PlugParams, plug_outer_end

# フレームのプレースホルダーの色。earrings/spiralの_FRAME_COLORと同じ
_FRAME_COLOR = [90, 90, 100, 200]
# ブリッジの高さ(y座標、mm)。earrings.frame_model._RING_CONTACT_Yと同じ
# 理由(鼻翼の隆起の中ほど)で同じ値を使う。実際の鼻腔拡張テープも
# ちょうどこのあたり(小鼻の一番張り出した高さ)に貼る
_BRIDGE_Y = 4.0
# ブリッジの各点を、鼻の前面(解析的な近似式)からどれだけ外側(+z方向)へ
# 逃がすか(mm)。earrings.frame_model._ROUND_CAP_OFFSETと同じ理由
# (円形断面のチューブが曲面と完全に一致しないことに由来する残留めり込み
# の回避)。front_surface_z_at_offsetは線形近似で、実際の鼻表面は中央と
# 両端の間で近似直線よりも前方(+z)に膨らんでいるため、1.0mm程度では
# 実測(bridge_clearance_margin)で越えてしまうことを確認した(既定形状で
# 実測0.72mmのめり込み、許容量0.35mmを超過)。2.0mmまで引き上げて安全
# マージンを持たせた
BRIDGE_OFFSET = 2.0
# ブリッジの折れ線近似の分割数(奇数にして中央=x=0の点を確実に含める。
# bridge_curvatureがこの中央点をたわみ量の測定に使う)
_BRIDGE_SAMPLES = 21
# コネクタの小さな曲げ(fillet)の半径(mm)と、その四分円を近似する点数。
# spiral.frame_model._FILLET_RADIUS/_FILLET_SAMPLESと同じ
_FILLET_RADIUS = 1.5
_FILLET_SAMPLES = 6
# コネクタが鼻の下を通る高さ(y座標、mm)を、鼻栓の露出面(plug_outer_end)
# からさらにどれだけ下げるか。spiral.frame_model._BOTTOM_MARGINと同じ
_BOTTOM_MARGIN = 1.5
# natural_radiusがactual_radiusよりどれだけ大きくなければならないか
# (比率)。1.0(同じ)だけを要求すると、GAがほぼ同じ値を選び拡張力が
# ほぼ0の個体になりうるため、実際に「平らな板を曲げて留める」とわかる
# 最低限の比率を要求する暫定値
_MIN_CURVATURE_RATIO = 1.2
# ブリッジの実際のチューブ表面が鼻本体メッシュへめり込んでよい上限を、
# 線径(frame.bridge_thickness/2)に対する比率で指定。earrings.frame_model.
# _RING_EMBED_RATIOと同じ理由・同じ値
_EMBED_RATIO = 0.5
# _tube_meshが使う円形断面ポリゴンの近似精度。earrings/spiralと同じ
_TUBE_POLYGON_RESOLUTION = 8
# _signed_distance_to_bodyが疑似法線による符号判定を信頼する距離の上限
# (mm)。earrings/spiralと同じ
_PSEUDO_NORMAL_MAX_DISTANCE = 2.0
# ステムが鼻栓に刺さっているべき最小の長さ・上限を、plug.lengthに対する
# 比率で指定。earrings/spiralと同じ
_MIN_INSERTION_TO_PLUG_LENGTH = 0.6
_MAX_INSERTION_TO_PLUG_LENGTH = 0.9

# ブリッジ+左右のコネクタを1本につないだ経路と、左右のステムの経路。
# build_pathsが返し、各種validate_*・build_frame・scripts/dilator/
# evaluation.pyの間で共通の型として使う。earrings/spiralのSidePaths
# (左右独立)と異なり、ブリッジは左右をまたぐ1本の部品のため、
# (coil, stem_left, stem_right)の3つ組にする
FramePaths = tuple[list[np.ndarray], list[np.ndarray], list[np.ndarray]]


@dataclass(frozen=True)
class FrameParams:
    """フレームの仮寸法パラメータ(単位: mm)。

    ブリーズライト型のブリッジ+左右のステムという単純なプレースホルダーで、
    後から実際の造形(3Dプリント/粘土)に向けて調整・最適化する。
    """

    natural_radius: float = 60.0
    bridge_thickness: float = 1.4
    stem_thickness: float = 1.0
    stem_length: float = 10.0

    def __post_init__(self) -> None:
        if self.natural_radius <= 0:
            raise ValueError(f"natural_radius は正の値にすること: {self.natural_radius}")
        if self.bridge_thickness <= 0:
            raise ValueError(f"bridge_thickness は正の値にすること: {self.bridge_thickness}")
        if self.stem_thickness <= 0:
            raise ValueError(f"stem_thickness は正の値にすること: {self.stem_thickness}")
        if self.stem_length <= 0:
            raise ValueError(f"stem_length は正の値にすること: {self.stem_length}")
        # 「ブリッジは太く、ステムは細く」(bridge_thickness>stem_thickness)は
        # ここでは検証しない。探索範囲はそれぞれ独立した範囲を持つため、GAが
        # この関係を満たさない組み合わせを生成しうる。ここで例外を送出すると
        # FrameParamsの構築自体が失敗し、evaluate_frame側で制約として拾えない
        # ため、thickness_order_margin/validate_thickness_order側で扱う
        # (earrings.frame_model.FrameParams.__post_init__のコメント参照)


def bridge_points(params: NoseParams) -> list[np.ndarray]:
    """ブリッジ(小鼻の高さを左右に横断する経路)の点列を返す
    (points[0]が左端、points[-1]が右端)。

    frame(FrameParams)に依存しない(NoseParamsだけで決まる幾何、装着後の
    実際の曲率は鼻の形状そのもの)ため、frame引数を取らない。
    モジュールdocstring「幾何」参照。
    """
    half_width, _, _ = surface_profile_at(params, _BRIDGE_Y)
    xs = np.linspace(-half_width, half_width, _BRIDGE_SAMPLES)
    return [
        np.array([x, _BRIDGE_Y, front_surface_z_at_offset(params, _BRIDGE_Y, x) + BRIDGE_OFFSET])
        for x in xs
    ]


def bridge_curvature(bridge: list[np.ndarray]) -> tuple[float, float]:
    """ブリッジの実際の曲率半径(actual_radius)と経路長(path_length)を返す。

    ブリッジはx=0を中心に左右対称なので、両端(points[0], points[-1])を
    結ぶ弦と、中央の点(x=0、_BRIDGE_SAMPLESを奇数にしているため必ず
    存在する)のその弦からの離れ(サジタ、sagitta)から、浅い円弧の近似式
    sagitta≈(chord/2)^2/(2*radius)を使って半径を逆算する(chord・sagitta
    ともにブリッジの実際の3D座標から直接測るため、鼻の断面形状の詳細
    (rounded_triangle等)を再実装せずに済む)。

    scripts/dilator/evaluation.pyのretention(拡張力)の計算、および
    curvature_marginの両方から参照される。
    """
    p0, p_mid, p1 = bridge[0], bridge[len(bridge) // 2], bridge[-1]
    chord_vec = p1 - p0
    chord = float(np.linalg.norm(chord_vec))
    chord_dir = chord_vec / chord
    to_mid = p_mid - p0
    sagitta = float(np.linalg.norm(to_mid - np.dot(to_mid, chord_dir) * chord_dir))
    actual_radius = (chord / 2) ** 2 / (2 * sagitta)
    path_length = float(
        np.sum(np.linalg.norm(np.diff(np.array(bridge), axis=0), axis=1))
    )
    return actual_radius, path_length


def _connector_points(
    bridge_end: np.ndarray,
    plug: PlugParams,
    params: NoseParams,
    side: Literal[-1, 1],
) -> list[np.ndarray]:
    """ブリッジの端(bridge_end)から鼻の下を回り込んでステムの始点まで
    (bridge_endを含まない)の経路(点列)を返す(path[-1]がステムの始点)。

    直線で鼻の下(bottom_y)の少し上まで降り、半径_FILLET_RADIUSの小さな
    曲げで向きを下向き→内側へ変え、内側へ直線移動、鼻栓の軸の手前で
    もう一つの小さな曲げで上向きに変わる。spiral.frame_model.coil_points
    のコネクタと同一の組み立て方(理由もそちらのモジュールdocstring参照)。

    z座標はbridge_end(前面+BRIDGE_OFFSET、鼻の表面付近)ではなく、
    鼻栓の軸の深さ(nostril_depth_z)を使う。ステムは鼻栓の軸上を通る
    必要があり(earrings/spiral共通)、これはブリッジが乗る前面の深さとは
    別物のため、bridge_endのzをそのまま引き継ぐとステムが鼻栓の軸から
    外れた深さに配置されてしまう(実測で発覚: stem_clearance_marginが
    最大1.67mmのめり込みを検出した)。bridge_end→connector[0]の区間
    (実装上は隣接する2点の間の暗黙の直線)でzがbridge_endの値から
    nostril_depth_zへ遷移する。
    """
    canonical_x = abs(float(bridge_end[0]))
    z0 = nostril_depth_z(params.tip_depth_front)
    outer_y = plug_outer_end(plug, params.nostril_gap, params.tip_depth_front, side)[1]
    bottom_y = outer_y - _BOTTOM_MARGIN
    axis_x = params.nostril_gap / 2
    fillet_center_x = axis_x + _FILLET_RADIUS
    descent_center_x = canonical_x - _FILLET_RADIUS
    descent_center_y = bottom_y + _FILLET_RADIUS

    xs = [canonical_x]
    ys = [descent_center_y]
    for t in np.linspace(0.0, -0.5 * np.pi, _FILLET_SAMPLES)[1:]:
        xs.append(descent_center_x + _FILLET_RADIUS * np.cos(t))
        ys.append(descent_center_y + _FILLET_RADIUS * np.sin(t))
    xs.append(fillet_center_x)
    ys.append(bottom_y)
    for t in np.linspace(1.5 * np.pi, np.pi, _FILLET_SAMPLES)[1:]:
        xs.append(fillet_center_x + _FILLET_RADIUS * np.cos(t))
        ys.append(bottom_y + _FILLET_RADIUS + _FILLET_RADIUS * np.sin(t))
    return [np.array([side * x, y, z0]) for x, y in zip(xs, ys)]


def stem_points(frame: FrameParams, start: np.ndarray) -> list[np.ndarray]:
    """鼻栓の軸上をまっすぐ上(+y、鼻の奥)へ伸びるステムの経路(点列、2点)
    を返す(path[0]=start、path[-1]が上端)。earrings/spiralのstem_pointsと
    同じ考え方(startがコネクタの終点=小さな曲げの終わり)。
    """
    top = start + np.array([0.0, frame.stem_length, 0.0])
    return [start, top]


def build_paths(
    frame: FrameParams, plug: PlugParams, params: NoseParams
) -> FramePaths:
    """ブリッジ+左右のコネクタを1本につないだ経路と、左右のステムの経路を
    返す(メッシュ生成なし)。

    reversed(左コネクタ) + ブリッジ + 右コネクタ、の順で1本の経路になる
    (coil[0]が左ステムの始点、coil[-1]が右ステムの始点。モジュール
    docstring「幾何」参照)。build_frame・各種validate_*・scripts/dilator/
    evaluation.pyのいずれからも参照される。
    """
    bridge = bridge_points(params)
    left_connector = _connector_points(bridge[0], plug, params, side=-1)
    right_connector = _connector_points(bridge[-1], plug, params, side=1)
    coil = list(reversed(left_connector)) + bridge + right_connector
    stem_left = stem_points(frame, coil[0])
    stem_right = stem_points(frame, coil[-1])
    return coil, stem_left, stem_right


def _tube_mesh(points: list[np.ndarray], radius: float) -> trimesh.Trimesh:
    """点列を、半径radiusの円形断面で押し出した1本の連続チューブにする。

    earrings/spiralの_tube_meshと同一実装(round_start引数は今回の設計
    では使わないため省いている。ブリッジの両端は鼻栓へのステムに
    つながる中間点であり、開放端(丸めるべき先端)を持たないため)。
    """
    polygon = Point(0, 0).buffer(radius, resolution=_TUBE_POLYGON_RESOLUTION)
    return trimesh.creation.sweep_polygon(polygon, np.array(points))


def _signed_distance_to_body(
    body: trimesh.Trimesh, points: np.ndarray
) -> np.ndarray:
    """各点から鼻本体表面までの符号付き距離を返す(正=外側、負=内側/めり込み)。

    earrings/spiralの_signed_distance_to_bodyと同一実装。
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
    検証する。earrings/spiralのvalidate_target_reachと同じ。
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


def thickness_order_margin(frame: FrameParams) -> float:
    """「ブリッジは太く、ステムは細く」という設計方針(bridge_thickness>
    stem_thickness)への違反量を返す(正=違反量、0以下=安全)。
    earrings/spiralのthickness_order_marginと同じ役割。
    """
    return frame.stem_thickness - frame.bridge_thickness


def validate_thickness_order(frame: FrameParams) -> None:
    """thickness_order_marginが正(=違反)の場合に例外を送出する。"""
    margin = thickness_order_margin(frame)
    if margin >= 0:
        raise ValueError(
            f"bridge_thickness({frame.bridge_thickness})はstem_thickness"
            f"({frame.stem_thickness})より大きくすること(ブリッジは太く、"
            "ステムは細くする方針のため)"
        )


def curvature_margin(frame: FrameParams, bridge: list[np.ndarray]) -> float:
    """natural_radiusが、装着後の実際の曲率半径(actual_radius)の
    _MIN_CURVATURE_RATIO倍以上あるかを返す(正=不足量、0以下=十分平ら)。

    natural_radius(自然な曲率半径)がactual_radius(装着後の実際の曲率
    半径)以下だと、装着してもブリッジが自然な形よりむしろ緩まる(拡張力が
    発生しない、または逆に締まる)方向になってしまう(モジュールdocstring
    「拡張力の物理近似」参照)。frameに依存する(natural_radiusの探索、かつ
    actual_radiusはbridge_thicknessに依存しないがブリッジの経路自体は
    frameに依存しないため実質NoseParamsだけで決まる)ため、evaluate_frameは
    例外で止めずこの値を制約として使う。
    """
    actual_radius, _ = bridge_curvature(bridge)
    return actual_radius * _MIN_CURVATURE_RATIO - frame.natural_radius


def validate_curvature(frame: FrameParams, bridge: list[np.ndarray]) -> None:
    """curvature_marginが正(=違反)の場合に例外を送出する。"""
    margin = curvature_margin(frame, bridge)
    if margin > 0:
        raise ValueError(
            f"natural_radius({frame.natural_radius})が、装着後の実際の曲率"
            f"半径の{_MIN_CURVATURE_RATIO}倍に{margin:.3f}mm足りない。"
            "natural_radiusを大きくする(より平らにする)こと"
        )


def bridge_clearance_margin(
    frame: FrameParams, coil: list[np.ndarray], body: trimesh.Trimesh
) -> float:
    """ブリッジ(コネクタ含む)の実際のチューブ表面の鼻本体メッシュへの
    めり込み量が、線径に比例した許容量(_EMBED_RATIO)を超えていないかを
    返す(正=超過量、0以下=許容範囲内)。earrings.frame_model.
    ring_clearance_marginと同じ考え方(ブリッジは鼻表面に沿わせて曲げる
    設計だが、押し込みは意図していないため、線材の円形断面が曲面と
    完全に一致しないことに由来する残留めり込みの水準までしか許容しない)。
    """
    radius = frame.bridge_thickness / 2
    allowed_embed = _EMBED_RATIO * radius
    tube = _tube_mesh(coil, radius)
    signed_distance = _signed_distance_to_body(body, tube.vertices)
    embed_amount = -signed_distance
    return float((embed_amount - allowed_embed).max())


def validate_bridge_clearance(
    frame: FrameParams, coil: list[np.ndarray], body: trimesh.Trimesh
) -> None:
    """bridge_clearance_marginが正(=違反)の場合に例外を送出する。"""
    margin = bridge_clearance_margin(frame, coil, body)
    if margin > 0:
        raise ValueError(
            f"bridge_thickness({frame.bridge_thickness})のチューブが、線径に"
            f"比例した許容めり込み量(_EMBED_RATIO={_EMBED_RATIO})を"
            f"{margin:.3f}mm超えて実際に鼻表面へめり込んでいる"
        )


def stem_clearance_margin(
    stems: list[list[np.ndarray]], body: trimesh.Trimesh, stem_thickness: float
) -> float:
    """ステムの実際のチューブ表面が、鼻本体メッシュにめり込んでいないかを
    返す(正=めり込み量、0以下=安全)。左右のうち最も厳しい点の値。
    earrings/spiralのstem_clearance_marginと同じ。
    """
    radius = stem_thickness / 2
    worst = -np.inf
    for stem in stems:
        tube = _tube_mesh(stem, radius)
        signed_distance = _signed_distance_to_body(body, tube.vertices)
        worst = max(worst, float(-signed_distance.min()))
    return worst


def validate_stem_clearance(
    stems: list[list[np.ndarray]], body: trimesh.Trimesh, stem_thickness: float
) -> None:
    """stem_clearance_marginが正(=めり込み)の場合に例外を送出する。"""
    margin = stem_clearance_margin(stems, body, stem_thickness)
    if margin > 0:
        raise ValueError(
            f"stem_thickness({stem_thickness})のステムが実際に鼻表面へ"
            f"めり込んでいる(最大めり込み量: {margin:.3f}mm)。ステムが鼻孔の"
            "壁や奥の肉と交差している可能性がある"
        )


def plug_insertion_depth(
    plug: PlugParams, params: NoseParams, stem: list[np.ndarray], side: Literal[-1, 1]
) -> float:
    """ステムが鼻栓(PlugParams)の内部に入り込んでいる長さを返す(mm)。
    earrings/spiralのplug_insertion_depthと同じ。
    """
    outer_y = plug_outer_end(plug, params.nostril_gap, params.tip_depth_front, side)[1]
    inner_y = outer_y + plug.length
    start_y, end_y = stem[0][1], stem[-1][1]
    return min(end_y, inner_y) - max(start_y, outer_y)


def plug_insertion_margin(
    plug: PlugParams, params: NoseParams, stem: list[np.ndarray], side: Literal[-1, 1]
) -> float:
    """刺さり込み(plug_insertion_depth)が最小長さに足りない不足量を返す
    (正=違反量、0以下=十分刺さっている)。earrings/spiralと同じ。
    """
    minimum = plug.length * _MIN_INSERTION_TO_PLUG_LENGTH
    return minimum - plug_insertion_depth(plug, params, stem, side)


def plug_overshoot_margin(
    plug: PlugParams, params: NoseParams, stem: list[np.ndarray], side: Literal[-1, 1]
) -> float:
    """ステムの先端が鼻栓を突き抜けている量を返す(正=違反量、0以下=安全)。
    earrings/spiralと同じ。
    """
    outer_y = plug_outer_end(plug, params.nostril_gap, params.tip_depth_front, side)[1]
    limit_y = outer_y + plug.length * _MAX_INSERTION_TO_PLUG_LENGTH
    return stem[-1][1] - limit_y


def build_frame(
    frame: FrameParams, plug: PlugParams, params: NoseParams
) -> trimesh.Trimesh:
    """フレーム(ブリッジ+左右のステムからなる1本の連続したチューブ)を
    構築する(着色済み)。earrings/spiralのbuild_frame_pairと異なり、左右
    独立の2部品ではなく単一のメッシュを返す(モジュールdocstring参照)。
    """
    validate_target_reach(plug, params)
    body = build_nose_body(params)
    validate_thickness_order(frame)
    coil, stem_left, stem_right = build_paths(frame, plug, params)
    bridge = bridge_points(params)
    validate_curvature(frame, bridge)
    validate_bridge_clearance(frame, coil, body)
    stems = [stem_left, stem_right]
    validate_stem_clearance(stems, body, frame.stem_thickness)
    for stem, side in zip(stems, (-1, 1)):
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

    bridge_radius = frame.bridge_thickness / 2
    stem_radius = frame.stem_thickness / 2
    bridge_mesh = _tube_mesh(coil, bridge_radius)
    stem_left_mesh = _tube_mesh(stem_left, stem_radius)
    stem_right_mesh = _tube_mesh(stem_right, stem_radius)
    # ブーリアン結合で1つの閉じた立体にする理由はearrings/spiralと同じ
    # (3Dプリント用STLとして正しい単一の多様体にするため)
    combined = bridge_mesh.union(stem_left_mesh, engine="manifold").union(
        stem_right_mesh, engine="manifold"
    )
    combined.visual.face_colors = _FRAME_COLOR
    return combined
