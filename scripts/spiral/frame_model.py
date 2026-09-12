"""フレームの仮形状(FrameParamsの6変数): ゼンマイ(渦巻きばね)状のコイル+ステム。

ユーザーのスケッチ(ピアスの丸い部分を渦巻き状にしたもの)を再現した設計。
鼻栓に刺すステムの部分はearrings(「b」字型)と共通で、鼻翼の外側の皮膚に
沿って登る区間を経て、鼻の下を回り込んでステムへつながる(commons/
plug_model.pyのPlugParamsはプレースホルダーとして実体を維持)。earringsと
違うのは、その先(鼻翼の隆起の上端から先)が「太いリング1個」ではなく、
半径が徐々に小さくなる渦巻き(コイル)である点。実際の鼻ピアスのフープの
ように鼻翼を挟んで留める機構(clip)ではなく、コイルは鼻翼の外側に
ぶら下がる装飾で、保持力はもっぱらステムと鼻栓(ティッシュ)の摩擦に依る
(evaluation.pyのモジュールdocstring参照)。

以前(1つ前の版)は鼻翼の1点(固定高さのアンカー)から渦巻きが始まる形に
したが、ユーザー指摘「もっとピアスの時みたいに、鼻に沿うように途中まで
伸ばし、その後丸くなるようにしてほしい」を受けて、アンカー1点ではなく
鼻翼の皮膚に沿って一定区間(_FOLLOW_START_Y〜_FOLLOW_END_Y)登る経路
(_follow_points)を挟むようにした。渦巻きはこの区間の上端から始まる。

## 幾何(座標系: x=左右、y=鼻先(0)→鼻筋、z=前後(前面が+)。earrings.frame_model
と同じ)

コイル・追従区間・コネクタはすべてxy平面(z=鼻栓の軸の高さ、
nostril_depth_z)の上に描く。

- **追従区間(_follow_points)**: 高さ_FOLLOW_START_Yから_FOLLOW_END_Yまで、
  鼻栓の軸の高さでx軸方向にレイを飛ばして実測した皮膚のx座標(_skin_x)
  に_SKIN_OFFSETだけ足した位置を、高さを刻みながら辿った経路。実際の
  皮膚の輪郭に追従するため、この区間は「鼻に沿う」ように見える
  (earringsの円弧のような解析的な形ではなく、_skin_xの実測値をそのまま
  つなぐ)。
- **コイル(coil_points内)**: 追従区間の上端(半径frame.start_radius)を
  起点に巻き上がっていく渦巻き。半径はframe.turns回転する間にframe.
  end_radiusまで直線的に小さくなる(アルキメデスの渦巻き)。中心は、
  起点における追従区間の向き(tangent、末尾2点の差分)に直交する外向き
  (nose_normal)へ半径分だけ離れた位置に置く。これにより、起点での
  渦巻きの向きが追従区間の向きと一致し(接線方向が連続になり)、以前の
  「中心を常に+x方向に固定する」方式で生じていた接続点の折れ曲がりが
  なくなる(coil_pointsのdocstring参照)。
- **コネクタ(coil_points内、追従区間の後に続く部分)**: 追従区間の下端
  から鼻の下(鼻栓の露出面より下の空間、bottom_y)の少し上まで真っ直ぐ
  降り、半径_FILLET_RADIUSの小さな曲げで向きを下向き→内側へ変え(下降用
  フィレット。以前は曲げのない直角のコーナーで、ユーザー指摘「直角では
  なく丸みを帯びさせてほしい」を受けて追加した)、内側(-x)へ直線移動、
  鼻栓の軸の手前でもう一つの半径_FILLET_RADIUSの小さな曲げによって
  上向きに変わり、鼻栓の軸の真下に達する(earrings.frame_modelの
  ring_pointsが使うのと同じ直線+フィレットの組み立て方を2箇所に増やした
  もの)。bottom_yはplug_outer_end(鼻栓の露出面)から_BOTTOM_MARGINだけ
  さらに下げた固定値(frameのどの変数にも依存しない)なので、earringsの
  hook_reach_margin/stem_entry_marginに相当する制約は不要(構造上つねに
  満たされる)。
- **ステム(stem_points)**: コネクタの終点(鼻栓の軸の真下、露出面より下)
  から鼻栓の軸に沿ってframe.stem_lengthだけ真上(+y)へ伸びる直線。
  earrings.frame_model.stem_pointsと同じ。

## 探索変数・ファイル内の並び順

FrameParamsの6変数: turns/start_radius/end_radius(コイルの形状)、
coil_thickness(追従区間・コイル・コネクタの太さ)、stem_thickness
(ステムの太さ)、stem_length(ステムの長さ)。ユーザー指摘「評価後が
細すぎるので、鼻栓に刺す部分以外はピアス同様に太くしてほしい」を受けて、
以前は1本の針金という想定でwire_thicknessを共通にしていたのを、
earringsと同じ「リング(に相当する部分)は太く、ステムは細く」という
方針に変更した(thickness_order_margin参照)。

ファイル内の並び順: 定数・FrameParams → 経路の点列を計算する関数
(_follow_points, coil_points, stem_points, build_side_paths等) →
メッシュ化・幾何判定のユーティリティ(_tube_mesh, _signed_distance_to_body。
earrings.frame_modelと同一実装) → validate_*(build_frame_pairが呼ぶ順) →
build_frame_pair。

frameに依存する検証(thickness_order_margin/radius_order_margin/
coil_clearance_margin/stem_clearance_margin/plug_insertion_margin/
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
# 追従区間(_follow_points)の下端・上端のy座標(mm)。下端は鼻孔の縁の
# すぐ上、上端は鼻翼の隆起(commons.nose_model._ALAE_BUMP_SPAN≈7mm)の
# 上寄りまでを目安にした暫定値(以前の単一のアンカー高さ_ANCHOR_Y=4.0の
# 前後をカバーする範囲)。上端が渦巻きの起点になる
_FOLLOW_START_Y = 1.0
_FOLLOW_END_Y = 8.0
# 追従区間の折れ線近似の分割数
_FOLLOW_SAMPLES = 10
# _skin_xがレイを飛ばし始める、鼻の外側の十分遠い位置(x座標の絶対値、mm)。
# earrings.frame_model._SKIN_RAY_ORIGIN_Xと同じ
_SKIN_RAY_ORIGIN_X = 40.0
# 追従区間の各点を、_skin_xの実測値からどれだけ外側(+x方向)へ逃がすか
# (mm)。earrings.frame_model._ROUND_CAP_OFFSETと同じ理由: 追従区間の
# 上端(コイルの起点)には丸い先端(_tube_meshのround_start=True)が
# 付かないが、区間全体が皮膚のごく近くを通るため、実測の皮膚位置ちょうど
# に置くと線材の円形断面で皮膚へわずかにめり込む。_ROUND_CAP_OFFSETほど
# 厳密に測っていない暫定値(GAを動かしながら見直す前提)
_SKIN_OFFSET = 0.8
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
# 渦巻き区間の折れ線近似の分割数。earrings.frame_modelの円弧
# (_RING_SAMPLESで270度程度)よりturns回転分だけ長い経路になりうるため
# 多めに取る
_SPIRAL_SAMPLES = 96
# コイル(追従区間+渦巻き+コネクタ)の実際のチューブ表面が鼻本体メッシュへ
# めり込んでよい上限を、線径(frame.coil_thickness/2)に対する比率で指定。
# earrings.frame_model._RING_EMBED_RATIOと同じ理由・同じ値(線材の円形
# 断面が鼻の曲面と完全には一致しないことに由来する、押し込みなしでも
# 避けられない残留めり込みの水準を上限にする)
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

    turns: float = 0.75
    start_radius: float = 5.0
    end_radius: float = 1.5
    coil_thickness: float = 2.0
    stem_thickness: float = 1.0
    stem_length: float = 10.0

    def __post_init__(self) -> None:
        if self.turns <= 0:
            raise ValueError(f"turns は正の値にすること: {self.turns}")
        if self.start_radius <= 0:
            raise ValueError(f"start_radius は正の値にすること: {self.start_radius}")
        if self.end_radius <= 0:
            raise ValueError(f"end_radius は正の値にすること: {self.end_radius}")
        if self.coil_thickness <= 0:
            raise ValueError(f"coil_thickness は正の値にすること: {self.coil_thickness}")
        if self.stem_thickness <= 0:
            raise ValueError(f"stem_thickness は正の値にすること: {self.stem_thickness}")
        if self.stem_length <= 0:
            raise ValueError(f"stem_length は正の値にすること: {self.stem_length}")
        # end_radius < start_radius(渦が中心に向かって細くなる)、
        # coil_thickness > stem_thickness(太さの順序)はここでは検証
        # しない。探索範囲(_SEARCH_SPACE)はそれぞれ独立した範囲を持つため、
        # GAがこれらの関係を満たさない組み合わせを生成しうる。ここで例外を
        # 送出するとFrameParamsの構築自体が失敗し、evaluate_frame側で
        # 制約として拾えなくなるため、radius_order_margin/thickness_
        # order_margin(とそれぞれのvalidate_*)側で扱う(earrings.
        # frame_model.FrameParams.__post_init__のコメント参照)


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


def _follow_points(
    params: NoseParams, body: trimesh.Trimesh, side: Literal[-1, 1]
) -> list[np.ndarray]:
    """鼻翼の皮膚に沿って登る経路の点列を返す(points[0]が下端
    _FOLLOW_START_Y、points[-1]が上端_FOLLOW_END_Y=渦巻きの起点)。
    x座標は正の正準値(coil_pointsがsideを掛けて鏡映する)。

    各高さで_skin_xを実測し、_SKIN_OFFSETだけ外側にずらした点をつなぐ。
    ユーザー指摘「もっとピアスの時みたいに、鼻に沿うように途中まで伸ばし、
    その後丸くなるようにしてほしい」への対応(モジュールdocstring参照)。
    """
    z0 = nostril_depth_z(params.tip_depth_front)
    ys = np.linspace(_FOLLOW_START_Y, _FOLLOW_END_Y, _FOLLOW_SAMPLES)
    points = []
    for y in ys:
        skin_x = _skin_x(body, float(y), z0, side)
        if skin_x is None:
            raise ValueError(
                f"追従区間の高さ(y={y:.2f})・鼻栓の軸の高さ(z={z0:.2f})で"
                "鼻翼の皮膚が見つからない。_FOLLOW_START_Y/_FOLLOW_END_Yを"
                "見直すこと"
            )
        x = abs(skin_x) + _SKIN_OFFSET
        points.append(np.array([x, float(y), z0]))
    return points


def coil_points(
    frame: FrameParams,
    plug: PlugParams,
    params: NoseParams,
    body: trimesh.Trimesh,
    side: Literal[-1, 1],
) -> list[np.ndarray]:
    """渦巻きの先端→追従区間→コネクタを連結した1本の経路(点列)を返す
    (points[0]が渦巻きの先端=開放端、points[-1]がステムの始点)。

    _follow_pointsが返す経路(下端→上端)を反転して渦巻きに繋げ
    (渦巻きの起点=_follow_pointsの上端)、続けて追従区間を下端まで
    引き返し、コネクタ(鼻の下を回り込んでステムの軸へ)を繋げる
    (モジュールdocstring「幾何」参照)。

    渦巻きの中心は、以前は起点(追従区間の上端)から常に+x方向
    (center_x=end_x+start_radius)に置いていたが、追従区間自体は_skin_x
    の実測値をつないだ経路のためy方向まっすぐとは限らず、この固定方向
    だと追従区間の実際の向きと渦巻きの向きが揃わず、接続点で折れ曲がって
    見える不具合があった(ユーザー指摘: 「丸みに入る前が直角に曲がって
    いる」)。追従区間の終端の向き(tangent、末尾2点の差分)を実測し、
    それに直交する外向き(nose_normal)に中心を置くことで、接続点での
    向きが連続になる(滑らかにつながる)ようにした。
    """
    follow = _follow_points(params, body, side)
    end_x, end_y, z0 = float(follow[-1][0]), float(follow[-1][1]), float(follow[-1][2])

    tangent = np.array([follow[-1][0] - follow[-2][0], follow[-1][1] - follow[-2][1]])
    tangent = tangent / np.linalg.norm(tangent)
    # tangentを-90度回転した向き(外向き=鼻から離れる方向になるのは、
    # tangentがおおむね+y方向を向いている限りtangent[1]>0だから)
    nose_normal = np.array([tangent[1], -tangent[0]])

    center_x = end_x + frame.start_radius * nose_normal[0]
    center_y = end_y + frame.start_radius * nose_normal[1]
    theta0 = np.arctan2(-nose_normal[1], -nose_normal[0])
    theta1 = theta0 - 2 * np.pi * frame.turns
    thetas = np.linspace(theta0, theta1, _SPIRAL_SAMPLES)
    radii = np.linspace(frame.start_radius, frame.end_radius, _SPIRAL_SAMPLES)
    spiral = [
        np.array([side * (center_x + r * np.cos(t)), center_y + r * np.sin(t), z0])
        for t, r in zip(thetas, radii)
    ]

    outer_y = plug_outer_end(plug, params.nostril_gap, params.tip_depth_front, side)[1]
    bottom_y = outer_y - _BOTTOM_MARGIN
    axis_x = params.nostril_gap / 2
    fillet_center_x = axis_x + _FILLET_RADIUS
    start_x = float(follow[0][0])

    # コネクタは4区間: (1) 追従区間の下端から、鼻の下の高さ(bottom_y)の
    # _FILLET_RADIUS上まで直線で降りる、(2) 半径_FILLET_RADIUSの小さな
    # 曲げで向きを下向き→内側へ変える(下降用フィレット。ユーザー指摘
    # 「直角ではなく丸みを帯びさせてほしい」への対応。以前はここが
    # 曲げのない直角のコーナーだった)、(3) 鼻栓の軸の手前_FILLET_RADIUS
    # まで内側(-x)へ直線移動、(4) 半径_FILLET_RADIUSの小さな曲げで
    # 向きを内側→上へ変える(上昇用フィレット、以前からあるもの)
    descent_center_x = start_x - _FILLET_RADIUS
    descent_center_y = bottom_y + _FILLET_RADIUS
    xs = [start_x]
    ys = [descent_center_y]
    for t in np.linspace(0.0, -0.5 * np.pi, _FILLET_SAMPLES)[1:]:
        xs.append(descent_center_x + _FILLET_RADIUS * np.cos(t))
        ys.append(descent_center_y + _FILLET_RADIUS * np.sin(t))
    xs.append(fillet_center_x)
    ys.append(bottom_y)
    for t in np.linspace(1.5 * np.pi, np.pi, _FILLET_SAMPLES)[1:]:
        xs.append(fillet_center_x + _FILLET_RADIUS * np.cos(t))
        ys.append(bottom_y + _FILLET_RADIUS + _FILLET_RADIUS * np.sin(t))
    connector = [np.array([side * x, y, z0]) for x, y in zip(xs, ys)]

    # 追従区間はここまで正の正準x座標のまま扱ってきた(側の鏡映は最後に
    # まとめて適用する)。spiral[0]は追従区間の上端(follow[-1])と同じ点
    # なので、追従区間を逆順にたどる際は先頭(follow[-1])を除く
    # (重複を避ける)
    follow_mirrored = [np.array([side * p[0], p[1], p[2]]) for p in follow]
    return list(reversed(spiral)) + list(reversed(follow_mirrored))[1:] + connector


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


def validate_follow_height(params: NoseParams, body: trimesh.Trimesh) -> None:
    """追従区間の下端・上端(_FOLLOW_START_Y/_FOLLOW_END_Y)・鼻栓の軸の
    高さ(z)で、左右とも鼻翼の皮膚がレイキャストで見つかることを検証する。
    earrings.frame_model.validate_ring_heightと同じ役割。
    """
    z0 = nostril_depth_z(params.tip_depth_front)
    for side in (-1, 1):
        for y in (_FOLLOW_START_Y, _FOLLOW_END_Y):
            if _skin_x(body, y, z0, side) is None:
                raise ValueError(
                    f"追従区間の高さ(y={y})・鼻栓の軸の高さ(z={z0:.2f})で"
                    f"鼻翼の皮膚が見つからない(side={side})。_FOLLOW_START_Y/"
                    "_FOLLOW_END_Yを見直すこと"
                )


def coil_protrusion(
    params: NoseParams, body: trimesh.Trimesh, sides: list[SidePaths]
) -> float:
    """コイルの最外点(鼻から最も離れた点)が、その高さの鼻翼の皮膚より
    外側へ出ている量(mm)を返す。左右のうち小さい方の値。

    earrings.frame_model.hoop_protrusionと同じ考え方だが、コイルは円弧
    ではなく渦巻きなので、最外点はcoilの点列全体(追従区間+渦巻き+
    コネクタ)からargmaxで探す(追従区間・コネクタは鼻の下・皮膚のすぐ
    近くを通るため、実際にはほぼ常に渦巻き側の点が選ばれる)。scripts/
    spiral/evaluation.pyの意匠性の目的(visibility、最大化)が参照する。
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


def thickness_order_margin(frame: FrameParams) -> float:
    """「コイルは太く、ステムは細く」という設計方針(coil_thickness>
    stem_thickness)への違反量を返す(正=違反量、0以下=安全)。

    ユーザー指摘「評価後が細すぎるので、鼻栓に刺す部分以外はピアス同様に
    太くしてほしい」への対応。earrings.frame_model.thickness_order_margin
    と同じ役割。
    """
    return frame.stem_thickness - frame.coil_thickness


def validate_thickness_order(frame: FrameParams) -> None:
    """thickness_order_marginが正(=違反)の場合に例外を送出する。"""
    margin = thickness_order_margin(frame)
    if margin >= 0:
        raise ValueError(
            f"coil_thickness({frame.coil_thickness})はstem_thickness"
            f"({frame.stem_thickness})より大きくすること(コイルは太く、"
            "ステムは細くする方針のため)"
        )


def _clearance_margin(
    points: list[np.ndarray], radius: float, body: trimesh.Trimesh, round_start: bool = False
) -> float:
    """点列を太さradiusのチューブにしたときの、鼻本体メッシュへのめり込み
    量が_EMBED_RATIO*radiusを超えていないかを返す(正=超過量、0以下=
    許容範囲内)。coil_clearance_marginが使うロジック(earrings.
    frame_model.ring_clearance_marginと同じ考え方)。
    """
    allowed_embed = _EMBED_RATIO * radius
    tube = _tube_mesh(points, radius, round_start=round_start)
    signed_distance = _signed_distance_to_body(body, tube.vertices)
    embed_amount = -signed_distance
    return float((embed_amount - allowed_embed).max())


def coil_clearance_margin(
    frame: FrameParams, sides: list[SidePaths], body: trimesh.Trimesh
) -> float:
    """コイル(追従区間+渦巻き+コネクタ)の実際のチューブ表面の鼻本体
    メッシュへのめり込み量が、線径に比例した許容量(_EMBED_RATIO)を
    超えていないかを返す(正=超過量、0以下=許容範囲内)。左右のうち
    最も厳しい点の値。

    コイルは鼻翼を挟むクリップではなく単に外側にぶら下がる装飾なので、
    どの部分も皮膚に意図的にめり込む理由がない(earrings.frame_modelの
    ring_depthのような押し込み変数を持たない)。それでも線材の円形断面と
    鼻の曲面が完全には一致しないため、押し込みなしでも避けられない
    残留めり込みの水準までは許容する(_EMBED_RATIOのコメント参照)。
    round_start=Trueで検証する(build_frame_pairが実際に書き出す
    ジオメトリと一致させるため。earrings.frame_model.ring_clearance_margin
    のdocstring参照)。
    """
    radius = frame.coil_thickness / 2
    return max(_clearance_margin(coil, radius, body, round_start=True) for coil, _ in sides)


def validate_coil_clearance(
    frame: FrameParams, sides: list[SidePaths], body: trimesh.Trimesh
) -> None:
    """coil_clearance_marginが正(=違反)の場合に例外を送出する。"""
    margin = coil_clearance_margin(frame, sides, body)
    if margin > 0:
        raise ValueError(
            f"coil_thickness({frame.coil_thickness})のチューブが、線径に"
            f"比例した許容めり込み量(_EMBED_RATIO={_EMBED_RATIO})を"
            f"{margin:.3f}mm超えて実際に鼻表面へめり込んでいる。turns/"
            "start_radius/end_radiusを見直すこと"
        )


def stem_clearance_margin(
    sides: list[SidePaths], body: trimesh.Trimesh, stem_thickness: float
) -> float:
    """ステムの実際のチューブ表面が、鼻本体メッシュにめり込んでいないかを
    返す(正=めり込み量、0以下=安全)。左右のうち最も厳しい点の値。
    earrings.frame_model.stem_clearance_marginと同じ役割。
    """
    radius = stem_thickness / 2
    worst = -np.inf
    for _, stem in sides:
        tube = _tube_mesh(stem, radius)
        signed_distance = _signed_distance_to_body(body, tube.vertices)
        worst = max(worst, float(-signed_distance.min()))
    return worst


def validate_stem_clearance(
    sides: list[SidePaths], body: trimesh.Trimesh, stem_thickness: float
) -> None:
    """stem_clearance_marginが正(=めり込み)の場合に例外を送出する。"""
    margin = stem_clearance_margin(sides, body, stem_thickness)
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
    validate_follow_height(params, body)
    validate_radius_order(frame)
    validate_thickness_order(frame)
    sides = [build_side_paths(frame, plug, params, body, side) for side in (-1, 1)]
    validate_coil_clearance(frame, sides, body)
    validate_stem_clearance(sides, body, frame.stem_thickness)
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

    coil_radius = frame.coil_thickness / 2
    stem_radius = frame.stem_thickness / 2

    meshes = []
    for coil, stem in sides:
        coil_mesh = _tube_mesh(coil, coil_radius, round_start=True)
        stem_mesh = _tube_mesh(stem, stem_radius)
        # ブーリアン結合で1つの閉じた立体にする理由はearrings.frame_model.
        # build_frame_pairと同じ(3Dプリント用STLとして正しい単一の
        # 多様体にするため)
        combined = coil_mesh.union(stem_mesh, engine="manifold")
        combined.visual.face_colors = _FRAME_COLOR
        meshes.append(combined)

    return meshes[0], meshes[1]
