"""水引型の評価関数(3目的+制約11個)。

frame_model.build_manifoldが作る立体を経由せず、紐の中心線(build_paths)と
鼻本体メッシュだけで評価する(dilator/evaluation.pyと同じ理由: 立体を作ると
1個体に約2秒かかるが、中心線なら約0.2秒で、GAが個体ごとに繰り返し呼び出せる)。

## 目的(3つ、いずれも最大化)

この器具の役目は、鼻栓(丸めたティッシュ)をつかむことと、鼻栓を「隠すもの」
から「装うもの」に変えることの2つ。後者は、ユーザーがこれまでの試作で
示した美の軸「横顔で見せ、正面では控えめに」(鼻の下だけの形は目に留まらず
世間の目を変えられない一方、正面で主張すると仮装やピアスに見える)を
そのまま2つの目的に分けた。

1. profile_presence: 横顔での存在感。真横から見た、輪より上(渡り・結び・
   端)の見える面積(mm^2)。結びが小鼻の上で見えるほど大きい
2. frontal_restraint: 正面での控えめさ。-(正面から見た左右の器具の見える
   面積mm^2)。輪は鼻の下で必ず見えるので、差がつくのは結びが鼻の正面寄り
   に回り込むかどうかと、紐の太さ
3. tissue_grip: ティッシュをつかむ面の広さ。輪の内側の面積(2π×内半径×
   輪の高さ、mm^2)。紐を太くすると輪が高くなってよくつかむが、正面から
   見える帯も太くなる

見える面積は、紐の表面のうち視線の側の点から視線の向きへ光線を飛ばし、
鼻に当たる(鼻の陰に隠れる)点を除いてから、紐の太さで太らせた線の投影の
和として測る(_visible_area)。結びが小鼻の後ろ寄り(顔との境目の側)に
あるほど正面からは鼻の陰に隠れ、横顔では見えたままになる。この差が
1と2のトレードオフになる。

## 制約(11個。MizuhikiScore参照。すべて0以下であるべき)

- 結びが読める: knot_open_margin(横顔で、三つ輪の3つの輪の穴が抜けて見える。
  最初の最適化では、紐を太く・結びを小さくした候補が選ばれ、輪の穴が潰れて
  三つ輪に見えなくなった(既定の形の穴は0.8〜1.0mm^2、候補は0.4mm^2以下)。
  水引の結びは輪が読めることが意匠の核なので制約にした)

- 肌に当たらない・寄り添う: clearance_margin(紐と肌のすき間の最小が
  SKIN_GAPを下回らない)・knot_hug_margin(結びと端が肌から浮きすぎない。
  すき間の9割がこの値以下)・knot_on_skin_margin(結びと端のほとんどが小鼻の
  面の上に乗る。小鼻からはみ出した点は肌に沿わせられず宙に浮く)
- 小鼻の範囲に収まる: cheek_margin(顔(鼻モデルの背面、z=-2.2)に当たら
  ない)・ala_top_margin(結びが小鼻の上端より上の鼻の側面へ上がらない)・
  tail_low_margin(結びと端が鼻の底面より_TAIL_DROP以上下へ垂れない。
  垂れると、鼻の下にぶら下がる紐に見える)
- 左右が当たらない: pair_gap_margin
- FDM(0.4mmノズル)で刷れる: neck_margin(紐のつなぎ目の厚み)・
  cord_margin(紐の直径)・bed_area_margin(刷る向きで、輪の底がベッドに
  着く面積)

閾値はいずれも暫定値で、実際に印刷・装着しながら見直す前提。
"""

from dataclasses import dataclass

import numpy as np
import trimesh
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from commons.nose_model import NoseParams, build_nose_body, tip_cap_min_y
from mizuhiki.frame_model import (
    GRIP_RADIUS,
    SKIN_GAP,
    MizuhikiParams,
    MizuhikiPaths,
    bed_contact_width,
    build_paths,
    neck_thickness,
    ring_height,
    surface_frame,
)

# 紐と肌のすき間の下限(mm)。中心線はSKIN_GAPで肌から離しているので、曲がり
# などで削れる分として少しだけ許す
_MIN_CLEARANCE = SKIN_GAP - 0.05
# 結び・端の肌からの浮き(9割の点がこの値以下、mm)
_MAX_KNOT_GAP = 0.8
# 結び・端のうち、小鼻の面の上に乗っている点の割合の下限
_MIN_KNOT_ON_SKIN = 0.95
# 顔(鼻モデルの背面)とのすき間の下限(mm)
_CHEEK_GAP = 0.3
# 結びの上端の上限(mm)。鼻モデルの小鼻の膨らみ(commons.nose_model.
# _ALAE_BUMP_SPAN)は鼻先の底面から約7mmまでで、結びの上の輪がそこから
# 少しはみ出す程度(2mm)までは許す(ユーザーが選んだ形の上端は8.8mm)。
# これより上へ上がると、小鼻に添える結びではなく、鼻の側面に貼った飾りに見える
_ALA_TOP = 9.0
# 結び・端の下端の下限(鼻の底面からの距離、mm)。端の先が小鼻の裾に触れる
# のはよいが、これより下へ垂れると、鼻の下にぶら下がる紐に見える
_TAIL_DROP = 1.0
# 左右の器具のすき間の下限(mm)
_MIN_PAIR_GAP = 1.0
# FDM(0.4mmノズル): つなぎ目の厚み・紐の直径の下限(mm)。0.8mmは線2本分
_MIN_NECK = 0.6
_MIN_CORD = 0.8
# 横顔で、三つ輪の輪の穴(3番目に大きい穴)の面積の下限(mm^2)。直径約0.8mmで、
# 紐と紐のすき間が刷ってもくっつかない幅の目安でもある
_MIN_LOOP_HOLE = 0.5
# 刷る向きで輪の底がベッドに着く面積の下限(mm^2)。ブリムを付ける前提で、
# 風切羽(輪の底面が平らな板)の28mm^2と同じ水準
_MIN_BED_AREA = 20.0
# 見える面積を測るときに光線を飛ばす点の間引き(中心線の何点おきか)
_VISIBILITY_STRIDE = 2


@dataclass(frozen=True)
class MizuhikiScore:
    """水引型の評価値(目的3つ+制約11個。モジュールdocstring参照)。

    目的はNSGA-IIが探索するトレードオフで、いずれも最大化。制約は
    実行不可能な個体を除外するための値で、いずれも0以下であるべき。
    """

    # 目的(3つ)
    profile_presence: float  # 意匠: 横顔で見える結びの面積(mm^2、最大化)
    frontal_restraint: float  # 意匠: -正面から見える器具の面積(mm^2、最大化)
    tissue_grip: float  # 機能: 輪がティッシュをつかむ面積(mm^2、最大化)
    # 制約(11個。すべて0以下であるべき)
    knot_open_margin: float  # 横顔で三つ輪の穴が抜けて見えるか
    clearance_margin: float  # 紐が肌に近づきすぎていないか
    knot_hug_margin: float  # 結びと端が肌から浮きすぎていないか
    knot_on_skin_margin: float  # 結びと端が小鼻の面に乗っているか
    cheek_margin: float  # 顔に当たらないか
    ala_top_margin: float  # 結びが小鼻の上端を越えていないか
    tail_low_margin: float  # 結びと端が鼻の底面より下へ垂れていないか
    pair_gap_margin: float  # 左右の器具が当たらないか
    neck_margin: float  # 紐のつなぎ目が刷れる厚みか
    cord_margin: float  # 紐が刷れる太さか
    bed_area_margin: float  # 輪の底がベッドに着く面積が足りるか


# 0以下が合格ラインの制約に共通で使う、浮動小数点誤差を吸収するための
# ごく小さな余裕(dilator.evaluation._MARGIN_EPSILONと同じ)
_MARGIN_EPSILON = 1e-6

CONSTRAINT_NAMES: tuple[str, ...] = (
    "knot_open_margin",
    "clearance_margin",
    "knot_hug_margin",
    "knot_on_skin_margin",
    "cheek_margin",
    "ala_top_margin",
    "tail_low_margin",
    "pair_gap_margin",
    "neck_margin",
    "cord_margin",
    "bed_area_margin",
)


def constraint_values(score: MizuhikiScore) -> tuple[float, ...]:
    """11個の制約値を、NSGA-II(pymoo)の規約(0以下=実行可能、正=違反量)に
    変換したタプルを返す。"""
    return tuple(getattr(score, name) - _MARGIN_EPSILON for name in CONSTRAINT_NAMES)


def _skin_gaps(body: trimesh.Trimesh, points: np.ndarray, radius: float) -> np.ndarray:
    """紐の中心線の各点での、紐の表面と肌のすき間(外向きの法線に沿って)。"""
    closest, normals = surface_frame(body, points)
    return np.einsum("ij,ij->i", points - closest, normals) - radius


def _visible_area(
    body: trimesh.Trimesh, lines: list[np.ndarray], radius: float, view: np.ndarray, axes: tuple[int, int]
) -> float:
    """紐(中心線の点列のリスト)を、視線の向きview(見る人の側への単位
    ベクトル)から見たときの、見える部分の投影面積(mm^2)。

    紐の表面の視線側の点から視線の向きへ光線を飛ばし、鼻に当たる点(鼻の
    陰に隠れる点)を除いて、見える点が続く区間ごとに、紐の太さで太らせた線を
    視線に垂直な面(axesの2軸)へ投影して重ね合わせる。
    """
    shapes = []
    for line in lines:
        points = line[::_VISIBILITY_STRIDE]
        hidden = body.ray.intersects_any(points + view * radius, np.tile(view, (len(points), 1)))
        run: list[np.ndarray] = []
        for point, is_hidden in zip(points, hidden):
            if not is_hidden:
                run.append(point[list(axes)])
                continue
            if len(run) >= 2:
                shapes.append(LineString(run).buffer(radius))
            run = []
        if len(run) >= 2:
            shapes.append(LineString(run).buffer(radius))
    return float(unary_union(shapes).area) if shapes else 0.0


def _loop_holes(paths: MizuhikiPaths, radius: float) -> list[float]:
    """結びを真横から見たとき(紐の太さで太らせた投影)に抜けて見える穴の
    面積(mm^2、大きい順)。三つ輪なら、3つの輪と中央の小さな穴。"""
    shapes = [LineString(strand[paths.knot][:, [2, 1]]).buffer(radius) for strand in paths.strands]
    union = unary_union(shapes)
    polygons = getattr(union, "geoms", [union])
    return sorted((Polygon(ring).area for polygon in polygons for ring in polygon.interiors), reverse=True)


def evaluate_frame(
    frame: MizuhikiParams, params: NoseParams, body: trimesh.Trimesh | None = None
) -> MizuhikiScore:
    """MizuhikiParamsから意匠・機能の評価値と制約値を計算する。"""
    body = body if body is not None else build_nose_body(params)
    paths: MizuhikiPaths = build_paths(frame, params, body)
    r = frame.cord_radius
    upper = slice(paths.entry.start, len(paths.path))
    ornament = slice(paths.knot.start, len(paths.path))

    side_lines = [strand[upper] for strand in paths.strands]
    presence = _visible_area(body, side_lines, r, np.array([1.0, 0.0, 0.0]), (2, 1))
    # 左右は鏡映で、正面から見える面積は同じ
    front = 2 * _visible_area(body, list(paths.strands), r, np.array([0.0, 0.0, 1.0]), (0, 1))
    grip = 2 * np.pi * GRIP_RADIUS * ring_height(frame)

    every = np.vstack(paths.strands)
    knot = np.vstack([strand[ornament] for strand in paths.strands])
    knot_gaps = _skin_gaps(body, knot, r)
    holes = _loop_holes(paths, r) + [0.0, 0.0, 0.0]

    return MizuhikiScore(
        profile_presence=presence,
        frontal_restraint=-front,
        tissue_grip=float(grip),
        knot_open_margin=_MIN_LOOP_HOLE - holes[2],
        clearance_margin=_MIN_CLEARANCE - float(_skin_gaps(body, every, r).min()),
        knot_hug_margin=float(np.percentile(knot_gaps, 90)) - _MAX_KNOT_GAP,
        knot_on_skin_margin=_MIN_KNOT_ON_SKIN - paths.knot_on_skin,
        cheek_margin=(body.bounds[0][2] + _CHEEK_GAP) - float((every[:, 2] - r).min()),
        ala_top_margin=float((knot[:, 1] + r).max()) - _ALA_TOP,
        tail_low_margin=(tip_cap_min_y(params) - _TAIL_DROP) - float((knot[:, 1] - r).min()),
        pair_gap_margin=_MIN_PAIR_GAP / 2 - float((every[:, 0] - r).min()),
        neck_margin=_MIN_NECK - neck_thickness(frame),
        cord_margin=_MIN_CORD - 2 * r,
        bed_area_margin=_MIN_BED_AREA - 2 * np.pi * (GRIP_RADIUS + r) * bed_contact_width(frame),
    )


# 目的の表示名(format_score・optimize.pyの表・グラフで共通)
OBJECTIVE_LABELS: dict[str, str] = {
    "profile_presence": "横顔での存在感(真横から見える結びの面積 mm^2、大きいほど良い)",
    "frontal_restraint": "正面での控えめさ(-正面から見える器具の面積 mm^2、大きいほど良い)",
    "tissue_grip": "ティッシュをつかむ面積(輪の内側 mm^2、大きいほど良い)",
}
_CONSTRAINT_LABELS: dict[str, str] = {
    "knot_open_margin": "横顔で三つ輪の穴が抜けて見える",
    "clearance_margin": "紐が肌に近づきすぎない",
    "knot_hug_margin": "結びと端が肌から浮きすぎない",
    "knot_on_skin_margin": "結びと端が小鼻の面に乗る",
    "cheek_margin": "顔(頬)に当たらない",
    "ala_top_margin": "結びが小鼻の上端を越えない",
    "tail_low_margin": "結びと端が鼻の下へ垂れない",
    "pair_gap_margin": "左右の器具が当たらない",
    "neck_margin": "紐のつなぎ目が刷れる厚み",
    "cord_margin": "紐が刷れる太さ",
    "bed_area_margin": "輪の底がベッドに着く面積",
}


def format_score(score: MizuhikiScore) -> str:
    """評価値を、目的と制約(合否と余裕)の表にした文字列。"""
    lines = ["目的:"]
    for name, label in OBJECTIVE_LABELS.items():
        lines.append(f"  {getattr(score, name):9.2f}  {label}")
    violated = [name for name, value in zip(CONSTRAINT_NAMES, constraint_values(score)) if value > 0]
    lines.append(f"制約: {len(CONSTRAINT_NAMES) - len(violated)}/{len(CONSTRAINT_NAMES)} 合格(値は0以下が合格)")
    for name in CONSTRAINT_NAMES:
        value = getattr(score, name)
        mark = "NG" if name in violated else "OK"
        lines.append(f"  {mark} {value:8.3f}  {_CONSTRAINT_LABELS[name]}({name})")
    return "\n".join(lines)
