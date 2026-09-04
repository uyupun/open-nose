"""フレームの仮形状(PROJECT.md の「フレームの設計変数(暫定5変数)」に対応)。

メガネのように鼻筋(鼻の付け根)まで伸ばす必要はなく、実物の鼻クリップ
(水泳用など)のように鼻先まわりだけで完結する小さなクリップとして表現する。
鼻中隔の上あたりを起点に、鼻翼・鼻尖の少し上に沿ってarm_length伸びる
アーム(arm_points)と、そこから鼻栓の露出端まで伸びるコネクタ
(connector_points)の2区間で構成する。メッシュ化(_tube_mesh)では
アーム+コネクタを1本の連続したチューブとして表現する(以前は区間ごとに
独立した円柱を生成して結合していたが、継ぎ目が別部品に見える原因になって
いたため撤廃した。_tube_mesh参照)。先端の保持部(球)は、鼻栓の実在への
依存がholder_size_penaltyという後付けの制約1つだけだったこと、コネクタの
終端(reach_gap制約により鼻栓の露出端にほぼ一致する)がすでに到達点を
兼ねていたことから、独立した部品としては廃止した(チューブ自体の終端
キャップが到達点になる)。

アーム(arm_points)はgrip_depth分だけ意図的に鼻表面へめり込ませ、メガネの
アームが鼻に沿って保持力を得るのと同じ発想で接触区間を形成する。実際の
鼻クリップが鼻を挟み込んで保持力を得る挙動の、変形計算なしの幾何的な近似
(PROJECT.md「鼻の弾力(変形)は扱わない」補足を参照)。コネクタ
(connector_points)は鼻栓の露出端へ向かう到達経路であり、鼻の前面より
外側を保ちながら非接触を保つ。

経路の点列(arm_points, connector_points)は、メッシュ生成(build_frame_pair)
だけでなくscripts/evaluation.pyの評価関数からも参照される。評価側はチューブ
メッシュを経由せず、点列と鼻本体メッシュの距離だけで計算できるようにする
ため、点列の計算とメッシュ化(_tube_mesh)を分離している。

ファイル内の並び順: 定数・FrameParams → 経路の点列を計算する関数
(arm_points, connector_points, build_side_paths等) → メッシュ化・幾何
判定のユーティリティ(_tube_mesh, _signed_distance_to_body) →
validate_*(build_frame_pairが呼ぶ順) → build_frame_pair。

frameに依存する検証(grip_depth_margin/arm_clearance_margin/
grip_ring_margin)は、例外を送出するvalidate_*(build_frame_pairの
メッシュ生成が使う)と、違反量を返すだけの*_margin(scripts/evaluation.py
のevaluate_frameが制約として使う)の2種類を用意している。frameは
遺伝的アルゴリズムの探索変数なので、evaluate_frame側で例外を送出すると
不正な個体1つで評価ループ全体が止まってしまうため。一方、frameに依存
しない検証(validate_target_reach, validate_anchor_height。PlugParams/
NoseParamsにしか依存せず、探索中は結果が変わらない)は*_marginを
用意せず、常に例外を送出する(問題設定そのものの誤りとして扱う)。
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import trimesh
from shapely.geometry import Point

from .nose_model import (
    NoseParams,
    back_surface_z_at_center,
    build_nose_body,
    front_surface_z_at_center,
    front_surface_z_at_offset,
    surface_profile_at,
    tip_cap_min_y,
)
from .plug_model import PlugParams, plug_outer_end

# フレームのプレースホルダーの色(グレー、半透明)。鼻表面との位置関係
# (めり込み・浮き)が透けて見えるよう、鼻本体(不透明)・鼻栓(alpha=200)より
# 低いalphaにしている。OBJはalphaを保持できないため、この効果を確認するには
# glTF(.glb)で書き出す(export_model.py/export_frame.py参照)
_FRAME_COLOR = [90, 90, 100, 140]
# アームの起点(クリップ位置)のy座標(鼻先=0からの距離、mm)。鼻中隔の
# 上あたり、鼻翼が始まる手前を想定した固定値(_ALAE_BUMP_SPANの範囲内)
_ARM_ANCHOR_Y = 6.0
# 鼻の中腹(メガネのブリッジ・鼻孔拡張テープと干渉しうる領域)の下限を、
# 鼻筋〜鼻先の長さ(nose_len)に対する比率で定義する。アーム起点がこれを
# 超えて上に伸びると、他の日用品(メガネ・テープ)と干渉する可能性がある
_MID_NOSE_RATIO = 0.5
# アーム・保持部への接続経路を近似する区間の分割数。鼻先に近づくほど
# 前面の迫り出しが変化するため、直線1本ではなく複数区間の折れ線で
# 表面のカーブに追従させる(arm_points参照)
_ARM_SAMPLES = 5
# 保持部への接続経路(connector_points)を近似する折れ線の分割数。多いほど
# 各yでの実測値(_depth_front_at)に沿った経路になり、表面に近づく
_CONNECTOR_SAMPLES = 24
# コネクタ(connector_points、鼻栓へ向かう非接触区間)の「円柱の表面」を
# 鼻の表面からどれだけ浮かせるか(mm)。0だと表面にちょうど接してしまい、
# 断面の丸め計算の誤差でわずかにめり込む可能性があるため。中心線
# (connector_pointsが計算する点列)はこれに加えてarm_thickness/2(円柱の
# 半径)も上乗せした位置に置く必要がある(中心線だけを浮かせても、円柱の
# 実体は半径の分だけ表面に近づくため)。アーム(arm_points)は現在は全区間が
# grip_depthで意図的に鼻表面へ埋め込まれる接触区間のため対象外
_SURFACE_CLEARANCE = 0.8
# arm_lengthの下限(mm)。3Dプリントでの最小造形サイズの目安であると同時に、
# evaluation.pyの現行の評価関数がarm_lengthを直接評価しておらず(smoothness
# はむしろarm_lengthが短いほど改善する)、放置すると0近くへ退化しうるための
# 暫定的な歯止め(→ PROJECT.md「評価関数のスコープ外・既知の限界」参照)
_MIN_ARM_LENGTH = 1.0
# clip_angleの上限(度)。90度に近づくとtan()が発散し(90度でarm_pointsの
# x座標が無限大)幾何が破綻するため、現実的なクリップの開き角(せいぜい
# 45〜60度程度)に絞って数値的な特異点を避ける
_MAX_CLIP_ANGLE = 60.0
# validate_grip_ringが起点の円形断面をサンプルする点数。36点(10度刻み)
# だと、真の最大突き出し点(赤道付近)がサンプル点からわずかにずれている
# 場合に見逃すことがある(実測でmm未満・3Dプリンタの造形精度を下回る
# 程度の超過を見逃す例を確認)。72点に増やして角度分解能を上げる
_GRIP_RING_SAMPLES = 72
# 押し込み方向の理論値(平坦面近似)からの許容誤差(mm)。局所的な曲率・
# サンプリング分解能による小さなズレを吸収するための余裕
# (validate_grip_ringのdocstring参照)
_GRIP_RING_TOLERANCE = 0.15
# _tube_meshが使う円形断面ポリゴンの近似精度。shapelyのbufferのresolutionは
# 「1/4円あたりの分割数」なので、8を指定すると32角形になる。以前の
# _polyline_mesh(trimesh.creation.cylinderの既定sections=32)と同等の
# 滑らかさを保つ
_TUBE_POLYGON_RESOLUTION = 8

# 片側のアーム経路・コネクタ経路の点列のペア(points, path)。
# build_side_pathsが返し、validate_arm_clearance・build_frame_pair・
# scripts/evaluation.pyの間で共通の型として使う
SidePaths = tuple[list[np.ndarray], list[np.ndarray]]


@dataclass(frozen=True)
class FrameParams:
    """フレームの仮寸法パラメータ(単位: mmおよび度)。

    アーム+コネクタの1本の連続したチューブという単純なプレースホルダーで、
    後から実際の造形(3Dプリント/粘土)に向けて調整・最適化する。
    """

    clip_angle: float = 20.0
    arm_length: float = 6.0
    arm_thickness: float = 2.0
    holder_offset: float = 12.0
    grip_depth: float = 0.5

    def __post_init__(self) -> None:
        if self.arm_length < _MIN_ARM_LENGTH:
            raise ValueError(
                f"arm_length は{_MIN_ARM_LENGTH}mm以上にすること: {self.arm_length}"
            )
        if self.arm_thickness <= 0:
            raise ValueError(f"arm_thickness は正の値にすること: {self.arm_thickness}")
        if not (0.0 < self.clip_angle <= _MAX_CLIP_ANGLE):
            raise ValueError(
                f"clip_angle は0〜{_MAX_CLIP_ANGLE}度の範囲にすること: {self.clip_angle}"
            )
        if self.holder_offset < 0:
            raise ValueError(f"holder_offset は0以上にすること: {self.holder_offset}")
        if self.grip_depth < 0:
            raise ValueError(f"grip_depth は0以上にすること: {self.grip_depth}")


def _depth_front_at(params: NoseParams, y: float) -> float:
    """yにおける前面迫り出しを返す。y<0(鼻先の丸め区間)ではsurface_profileの
    単純延長ではなく丸め処理による窄まりを反映した値を使う
    (nose_model.surface_profile_at参照)。
    """
    return surface_profile_at(params, y)[2]


def arm_points(
    frame: FrameParams, params: NoseParams, side: Literal[-1, 1]
) -> list[np.ndarray]:
    """鼻中隔の上あたり(起点)からclip_angleで開きながら鼻先方向へ
    arm_length伸びる、アームの経路(点列)を返す(points[0]が起点、
    points[-1]がアーム下端)。

    メガネのアームが鼻翼・鼻尖の少し上に沿って保持力を得るのと同じ発想で、
    アーム全区間をgrip_depthの分だけ前面境界より内側(z方向)にめり込ませる
    (実際の鼻クリップが鼻中隔〜鼻翼まわりを挟み込んで保持力を得る挙動の
    近似。モジュールdocstring参照)。以前は起点(points[0])だけがこの挙動で、
    それ以外は表面から離す設計だったが、clip_angleでxが0から開くほど
    実際の表面(丸め三角形断面の背面角へ向けて後退する)から乖離していく
    ため、アームが鼻表面から浮いて見える原因になっていた。基準面には
    x=0でfront_surface_z_at_center(フィレット済みリングの実測値、最も
    精度が高い)、x≠0ではfront_surface_z_at_offset(前面エッジの直線近似。
    実測手段がないため。いずれもdocstring参照)を使い分ける。
    xは起点(鼻中隔中央、x=0)からclip_angleに応じて左右に開いていく
    (小さいほど鼻中隔寄りにきつく締まり、大きいほど鼻翼側まで開く)。
    """
    ys = np.linspace(_ARM_ANCHOR_Y, _ARM_ANCHOR_Y - frame.arm_length, _ARM_SAMPLES)

    points = []
    for i, y in enumerate(ys):
        x = side * np.tan(np.radians(frame.clip_angle)) * (_ARM_ANCHOR_Y - y)
        front_z = (
            front_surface_z_at_center(params, y)
            if i == 0
            else front_surface_z_at_offset(params, y, x)
        )
        z = front_z - frame.grip_depth
        points.append(np.array([x, y, z]))
    return points


def connector_points(
    frame: FrameParams, params: NoseParams, arm_end: np.ndarray, target: np.ndarray
) -> list[np.ndarray]:
    """アーム下端(arm_end)から鼻栓の露出端(target)まで到達する経路(点列)を
    返す(path[0]がarm_end、path[-1]がtargetへ向けた最終到達点)。

    arm_endからtargetへ直線で向かうと鼻の内部を貫通しうるため、まず
    arm_pointsと同じ考え方(その時点のyでの前面迫り出しより外側を保つ)で
    targetのx, yまで折れ線で近づく(_CONNECTOR_SAMPLES点、xはarm_endから
    targetまで線形補間)。鼻先の丸め区間(tip_cap_depth_front)はyが進むに
    つれ必要な高さが下がっていく形状なので、区間ごとに実測値を計算する
    ことで表面に近い経路になる。
    最後にtargetへ向けてzを差し込む(approach→path[-1])。targetのyは
    鼻本体メッシュの範囲より外側(validate_target_reachが検証する)なので、
    この区間は鼻の実体が存在しない位置を通ることになり安全。
    holder_offsetは、この最後の区間でtargetまでの距離を超えないよう
    クランプした上での実際の到達距離(target - path[-1]が0でなければ、
    到達しきれていないことを意味する)
    """
    ys = np.linspace(arm_end[1], target[1], _CONNECTOR_SAMPLES)
    xs = np.linspace(arm_end[0], target[0], _CONNECTOR_SAMPLES)
    standoff = _SURFACE_CLEARANCE + frame.arm_thickness / 2

    path = [arm_end]
    for i in range(1, _CONNECTOR_SAMPLES):
        y = ys[i]
        z = _depth_front_at(params, y) + standoff
        path.append(np.array([xs[i], y, z]))
    approach = path[-1]

    dive = target - approach
    dive_dist = np.linalg.norm(dive)
    dive_dir = dive / dive_dist
    holder_pos = approach + dive_dir * min(frame.holder_offset, dive_dist)

    path.append(holder_pos)
    return path


def build_side_paths(
    frame: FrameParams, plug: PlugParams, params: NoseParams, side: Literal[-1, 1]
) -> SidePaths:
    """指定側のアーム経路・コネクタ経路の点列を返す(メッシュ生成なし)。

    build_frame_pair・validate_arm_clearance・scripts/evaluation.pyの
    いずれからも参照される。左右分をまとめて1度だけ計算し、呼び出し側で
    使い回すことで、arm_points/connector_pointsの重複計算を避ける。
    """
    points = arm_points(frame, params, side)
    arm_end = points[-1]
    target = plug_outer_end(plug, params.nostril_gap, params.tip_depth_front, side)
    path = connector_points(frame, params, arm_end, target)
    return points, path


def full_path_points(points: list[np.ndarray], path: list[np.ndarray]) -> list[np.ndarray]:
    """アーム(points)とコネクタ(path)を1本の折れ線に結合した点列を返す。

    points[-1]とpath[0]は同じ点(arm_end)のため、重複しないようpath[1:]を
    使う。evaluation.pyのproportion_penalty(全長の計算)・smoothness(経路
    全体の折れ角の計算)の両方から参照される。
    """
    return points + path[1:]


def surface_following_points(path: list[np.ndarray]) -> np.ndarray:
    """コネクタのうち、鼻表面に沿わせている(接触しない)区間だけの点列を返す。

    アーム(arm_points)は全区間がgrip_depthで意図的に鼻表面へ埋め込まれる
    接触区間(evaluation.pyのretention/grip_depth_margin/grip_ring_margin
    で別途評価する)なので対象外。コネクタ最終点(path[-1])は鼻栓へ
    意図的に離れていくダイブ区間の到達点なので除外する。path[0]はarm_end
    (=arm_pointsの最終点)と同じ点のため、重複しないようpath[1:-1]を使う。
    evaluation.pyのfit_gap、およびarm_clearance_marginの両方から参照される。
    """
    return np.array(path[1:-1])


def _tube_mesh(points: list[np.ndarray], radius: float) -> trimesh.Trimesh:
    """点列を、半径radiusの円形断面で押し出した1本の連続チューブにする。

    以前(_polyline_mesh)は区間ごとに独立した(両端に平らな蓋がついた)
    円柱を生成してconcatenateしていたが、隣接区間が頂点を共有しない
    別部品の寄せ集めになり、「複数の独立したパーツがはっきり折れて
    つながっている」ように見える原因になっていた(issue #2)。
    trimesh.creation.sweep_polygonは円形ポリゴンを3D経路に沿って押し出し、
    各内部点でミター(斜め)継ぎの断面リングを共有する単一の連続メッシュを
    返すため、この問題が起きない。始点・終点には自動でキャップが付く
    (sweep_polygonのcap引数、既定True)。
    """
    polygon = Point(0, 0).buffer(radius, resolution=_TUBE_POLYGON_RESOLUTION)
    return trimesh.creation.sweep_polygon(polygon, np.array(points))


def _signed_distance_to_body(
    body: trimesh.Trimesh, points: np.ndarray
) -> np.ndarray:
    """各点から鼻本体表面までの符号付き距離を返す(正=外側、負=内側/めり込み)。

    trimesh.proximity.closest_pointは符号なし距離しか返さないため、
    「表面のすぐ近くにいる(安全)」と「わずかにめり込んでいる(危険)」を
    区別できない。最近接点の三角形の法線と、その点から問い合わせ点への
    向きの内積の符号を使って外側/内側を判定する(疑似法線による符号付き
    距離。body.contains()のような別のアルゴリズムに切り替えるのではなく、
    この判定方法自体は複数回のレビューで正しさを確認済みのため維持する)。

    closest_point(rtreeによる空間索引を使う高速版)を使う。総当たりの
    closest_point_naiveは、evaluate_frameを繰り返し呼び出す用途(GA)では
    支配的なボトルネックになることが実測で判明した(1回あたり約0.7秒)。
    closest_pointは同じ最近接点探索を高速化するだけで結果は変わらない
    (実測で全点について両者の距離・最近接点が完全一致することを確認済み)。
    """
    closest, distance, triangle_id = trimesh.proximity.closest_point(body, points)
    normals = body.face_normals[triangle_id]
    direction = points - closest
    sign = np.sign(np.einsum("ij,ij->i", direction, normals))
    return distance * sign


def validate_target_reach(plug: PlugParams, params: NoseParams) -> None:
    """鼻栓の露出端(connector_pointsの目標)が鼻本体メッシュのy方向の範囲
    より外側にあることを検証する。

    connector_pointsの最終区間(approach→path[-1])が鼻を貫通しない安全性は、
    targetのyが鼻本体メッシュのy範囲より外側にあることに依存している。
    PlugParams/NoseParamsの組み合わせによってはこの前提が崩れうるため、
    build_frame_pair(メッシュ生成)・evaluate_frame(評価)の両方から
    共通で呼び出して検証する。
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
                "重なっている。保持部の経路が鼻を貫通する可能性があるため、"
                "PlugParamsのlength/_PLUG_Y_OFFSETを見直すこと"
            )


def grip_depth_margin(
    frame: FrameParams, params: NoseParams, sides: list[SidePaths]
) -> float:
    """grip_depth+半径(arm_thickness/2)が、アーム上の各点における鼻の
    局所的な厚み(前面〜背面の実際のz)をどれだけ超えているかを返す
    (正=違反量、0以下=安全。左右のアーム全区間のうち最も厳しい点の値)。
    前面〜背面方向=z方向の1次元チェックで、側方への突き抜けは
    grip_ring_margin側で別途扱う。sidesはbuild_side_pathsで左右分を
    事前計算した(points, path)のリスト(呼び出し側で1度だけ計算し、
    他の検証と使い回すことで重複計算を避けるため)。

    超えるとその点の円柱が鼻の背面(反対側)を突き抜ける非物理的な状態になる。
    frameに依存する(=FrameParamsの探索によって結果が変わる)ため、
    evaluate_frameは例外で止めずこの値を制約として使う。build_frame_pair
    (メッシュ生成)は例外で止めたいのでvalidate_grip_depthを使う。

    各点の前面境界(=embed前のfront_z)は、point.z(=front_z - grip_depth、
    arm_points参照)から`+ grip_depth`で復元できる(x=0か否かでarm_pointsが
    front_surface_z_at_center/front_surface_z_at_offsetを使い分けている
    のと同じ計算をここで再現する必要がなく、実際に使われた値と確実に
    一致する)。背面境界にはback_surface_z_at_centerを使う(単純な
    -depth_backをそのまま使うと、ブーメラン形状による後退を無視してしまい
    実際より安全域を大きく見積もる)。背面のブーメラン膨らみはx=0付近で
    最大になり、xが離れるほど小さくなる(_boomerang_bowが両端で元の直線
    に戻る)ため、中心以外の点でもback_surface_z_at_center(x=0での値)を
    使うと実際の背面より手前(浅い)に見積もることになり、安全側(=違反を
    見逃さない方向)の近似になる。

    アームは円柱の中心線であり、実際にめり込むのは中心線(grip_depth)だけ
    でなく半径(arm_thickness/2)の分だけさらに深い位置までである
    (arm_clearance_marginの調査で判明。半径を考慮しないと、太い
    arm_thicknessと組み合わせたgrip_depthで実際には鼻を突き抜けている
    状態を見逃す)。
    """
    total_depth = frame.grip_depth + frame.arm_thickness / 2
    worst = -np.inf
    for points, _ in sides:
        for x, y, z in points:
            front_z = z + frame.grip_depth
            back_z = back_surface_z_at_center(params, y)
            max_depth = front_z - back_z
            worst = max(worst, total_depth - max_depth)
    return worst


def validate_grip_depth(
    frame: FrameParams, params: NoseParams, sides: list[SidePaths]
) -> None:
    """grip_depth_marginが正(=違反)の場合に例外を送出する。

    build_frame_pair(メッシュ生成)から使う想定。evaluate_frame(評価)は
    frameに依存するこの検証を例外ではなく制約として扱うため、
    grip_depth_marginを直接使う(モジュールdocstring・grip_depth_margin
    のdocstring参照)。
    """
    margin = grip_depth_margin(frame, params, sides)
    if margin >= 0:
        raise ValueError(
            f"grip_depth({frame.grip_depth})+半径({frame.arm_thickness / 2})が"
            f"アーム上のどこかで鼻の厚みを超えており(超過量: "
            f"{margin:.3f}mm)、鼻を突き抜けてしまう"
        )


def validate_anchor_height(params: NoseParams) -> None:
    """アーム起点(_ARM_ANCHOR_Y)が鼻の中腹(_MID_NOSE_RATIO)より下にある
    ことを検証する。

    _ARM_ANCHOR_Yは現状固定の定数で、5つの設計変数(FrameParams)の
    どれを動かしても値は変わらないため、デフォルトのNoseParamsでは常に
    満たされる。ただしnose_lenが小さい鼻モデル(将来、多様な鼻形状に
    対応する場合)ではこの前提が崩れうるため、build_frame_pair・
    evaluate_frameの両方から共通で呼び出して検証する。
    """
    mid_nose_y = params.nose_len * _MID_NOSE_RATIO
    if _ARM_ANCHOR_Y >= mid_nose_y:
        raise ValueError(
            f"アーム起点(y={_ARM_ANCHOR_Y})が鼻の中腹(y={mid_nose_y:.2f})以上に"
            "あり、メガネのブリッジや鼻孔拡張テープと干渉する可能性がある"
        )


def arm_clearance_margin(
    sides: list[SidePaths], body: trimesh.Trimesh, arm_thickness: float
) -> float:
    """コネクタの表面沿い区間(非接触区間、実際のチューブメッシュ)が、鼻本体
    メッシュにどれだけめり込んでいるかを返す(正=めり込み量、0以下=安全)。
    sidesはbuild_side_pathsで左右分を事前計算した(points, path)のリスト
    (呼び出し側で1度だけ計算し、メッシュ生成・他の検証と使い回すことで
    重複計算を避けるため)。frameに依存する(arm_thicknessの探索によって
    結果が変わる)ため、evaluate_frameは例外で止めずこの値を制約として
    使う。build_frame_pair(メッシュ生成)は例外で止めたいのでvalidate_
    arm_clearanceを使う。

    connector_pointsのstandoff(_SURFACE_CLEARANCE+半径)は、その時点の
    yでの前面最大値(depth_front)からのz軸方向のオフセットに過ぎない。
    これは「centerlineが貫通しない」ことは保証するが(depth_frontはその
    yでの最大zなので、zがそれを上回れば貫通しない)、鼻表面がyに対して
    傾いている箇所(鼻先の丸め区間など)では、centerlineから表面までの
    実際のユークリッド距離がstandoffより小さくなりうる。この誤差は
    半径が大きいほど拡大するため、arm_thicknessが太い場合は名目上の
    standoffを確保していても円柱が実際には表面へめり込むことがある。

    当初は中心線(surface_following_points)から表面までの符号なし距離が
    半径以上あるかで検証していたが、符号なし距離では「表面のすぐ近くに
    いる(安全)」と「わずかにめり込んでいる(危険)」を区別できないという
    欠陥があった。実際に生成されるチューブメッシュ(_tube_mesh)の頂点に
    対して符号付き距離(_signed_distance_to_body)を使うよう修正した
    (この関数がチェックする表面沿い区間そのものは、実測ではarm_thickness=
    6mm程度まで十分な余裕(2mm以上)があり、めり込みは発生しなかった。
    実際にめり込みが起きていたのはこの関数の対象外であるアーム(意図的な
    grip_depthのめり込み区間)側で、半径を考慮していなかったgrip_depth_margin
    の不備だった。そちらを別途修正済み)。

    その後、evaluate_frameを繰り返し呼び出すベンチマークで、この関数が
    全体の実行時間の大半(1回あたり約1.8秒)を占めていることが判明した。
    改善案として(a)中心点まわりにx-z平面内で円をサンプルする(円柱
    メッシュを生成しない)方式、(b)円柱の円周分割数を減らす方式を試したが、
    どちらも実測で既定値の計算結果からずれ(前者は経路が傾いた区間で
    断面の向きがズレる、後者は円周方向のサンプルが粗くなり実際の違反を
    見逃す例が確認できた。128通りのパラメータで比較したところ符号が
    反転する=違反を見逃すケースが実在した)、正確さを犠牲にする近似だった
    ため採用を見送った。代わりに_signed_distance_to_body側の距離計算を
    rtree(空間索引)で高速化する方式を採用した(このモジュールの計算内容
    は一切変えず、同じ計算を速くしただけなので近似ではない)。
    """
    radius = arm_thickness / 2
    worst = -np.inf
    for _, path in sides:
        surface_points = surface_following_points(path)
        tube = _tube_mesh(list(surface_points), radius)
        signed_distance = _signed_distance_to_body(body, tube.vertices)
        min_signed = float(signed_distance.min())
        worst = max(worst, -min_signed)
    return worst


def validate_arm_clearance(
    sides: list[SidePaths], body: trimesh.Trimesh, arm_thickness: float
) -> None:
    """arm_clearance_marginが正(=めり込み)の場合に例外を送出する。

    build_frame_pair(メッシュ生成)から使う想定。evaluate_frame(評価)は
    frameに依存するこの検証を例外ではなく制約として扱うため、
    arm_clearance_marginを直接使う(モジュールdocstring参照)。
    """
    margin = arm_clearance_margin(sides, body, arm_thickness)
    if margin > 0:
        raise ValueError(
            f"arm_thickness({arm_thickness})のチューブが実際に鼻表面へ"
            f"めり込んでいる(最大めり込み量: {margin:.3f}mm)。"
            "arm_thicknessを小さくすること"
        )


def grip_ring_margin(
    frame: FrameParams, body: trimesh.Trimesh, sides: list[SidePaths]
) -> float:
    """アーム上の各点の円形断面(半径arm_thickness/2、中心は各点そのもの)が、
    想定をどれだけ超えて鼻本体メッシュから突き出しているかを返す
    (正=違反量、0以下=安全。左右のアーム全区間のうち最も厳しい点の値)。
    frameに依存する(grip_depth・arm_thicknessの探索によって結果が変わる)
    ため、evaluate_frameは例外で止めずこの値を制約として使う。
    build_frame_pair(メッシュ生成)は例外で止めたいのでvalidate_grip_ringを
    使う。sidesはbuild_side_pathsで左右分を事前計算した(points, path)の
    リスト(呼び出し側で1度だけ計算し、他の検証と使い回すことで重複計算を
    避けるため)。

    半径がgrip_depthより大きい場合、断面の押し込み方向の先端が元の表面
    位置より外側に出るのは物理的に正常(指で肉を軽く押し込む形と同じで、
    半径の分だけ完全に埋没している必要はない)。平坦面を仮定すると、この
    先端での突き出し量の理論値は`max(0, radius - grip_depth)`になる
    (押し込み方向となす角θでの理論的な突き出し量は`radius*cos(θ) - grip_depth`
    で、θ=0(先端)が最大)。この理論値はgrip_depthのみに依存し位置に
    依存しないため、アーム上のどの点でも同じallowedを使う。

    実際の鼻表面は平坦ではなくフィレットで丸められている。grip_depthが
    半径に対して十分深い組み合わせでは、前面コーナーが凸面のため実際の
    突き出し量はこの平坦面近似の理論値を上回らない(むしろ理論値より
    埋め込みやすい方向に働く)ことを実測で確認している。一方、grip_depth
    が半径に近い/それを下回る領域(理論値がほぼ0近辺になる領域)では、
    実際の突き出し量が理論値を数百マイクロメートル単位で上回ることが
    ある(実測例: grip_depth=5.0, arm_thickness=8.0で理論値0mmに対し実測
    約0.317mm)。この場合も_GRIP_RING_TOLERANCEを明確に超えるため、
    この関数自体は正しく違反を検出する(=近似の誤差を許容誤差の中に
    収めようとしているのではなく、理論値+許容誤差という単純な基準の中で
    危険な組み合わせを検出できていることを実測で確認している、という
    位置づけ)。円周上の全点(_GRIP_RING_SAMPLES点、10度未満の角度分解能)
    の実測値(符号付き距離)と理論値+_GRIP_RING_TOLERANCEの差を返す。

    (このチェックの前身は「押し込み方向を除いた左右の赤道2点だけを検証」
    する方式だったが、実際には赤道が最も安全側に振れる方向で、そこから
    20度ずれただけで別の方向での突き抜けを見逃していたため、全周を
    理論値ベースで検証する方式に置き換えた)

    x=0(起点)以外の点では、押し込み方向を常にz軸とみなす近似を使う
    (front_surface_z_at_offsetと同様、中心から離れるほど実際の局所法線
    方向とのズレが増えるが、_GRIP_RING_TOLERANCEと同じ精神で許容する)。
    """
    radius = frame.arm_thickness / 2
    theta = np.linspace(-np.pi, np.pi, _GRIP_RING_SAMPLES, endpoint=False)
    allowed = max(0.0, radius - frame.grip_depth) + _GRIP_RING_TOLERANCE
    worst = -np.inf
    for points, _ in sides:
        for x, y, z in points:
            ring = np.stack(
                [
                    x + radius * np.sin(theta),
                    np.full(_GRIP_RING_SAMPLES, y),
                    z + radius * np.cos(theta),
                ],
                axis=1,
            )
            signed_distance = _signed_distance_to_body(body, ring)
            worst = max(worst, float(signed_distance.max()) - allowed)
    return worst


def validate_grip_ring(
    frame: FrameParams, body: trimesh.Trimesh, sides: list[SidePaths]
) -> None:
    """grip_ring_marginが正(=違反)の場合に例外を送出する。

    build_frame_pair(メッシュ生成)から使う想定。evaluate_frame(評価)は
    frameに依存するこの検証を例外ではなく制約として扱うため、
    grip_ring_marginを直接使う(モジュールdocstring参照)。
    """
    margin = grip_ring_margin(frame, body, sides)
    if margin > 0:
        raise ValueError(
            f"grip_depth({frame.grip_depth})とarm_thickness"
            f"({frame.arm_thickness})の組み合わせで、アーム上のどこかの断面が"
            f"想定を{margin:.3f}mm超えて鼻表面から突き出している。grip_depthを"
            "大きくするかarm_thicknessを小さくすること"
        )


def build_frame_pair(
    frame: FrameParams, plug: PlugParams, params: NoseParams
) -> tuple[trimesh.Trimesh, trimesh.Trimesh]:
    """左右のフレーム(アーム+コネクタの1本の連続したチューブ)を構築する(着色済み)。"""
    validate_target_reach(plug, params)
    validate_anchor_height(params)
    body = build_nose_body(params)
    sides = [build_side_paths(frame, plug, params, side) for side in (-1, 1)]
    validate_grip_depth(frame, params, sides)
    validate_arm_clearance(sides, body, frame.arm_thickness)
    validate_grip_ring(frame, body, sides)

    radius = frame.arm_thickness / 2

    meshes = []
    for points, path in sides:
        combined = _tube_mesh(full_path_points(points, path), radius)
        combined.visual.face_colors = _FRAME_COLOR
        meshes.append(combined)

    return meshes[0], meshes[1]
