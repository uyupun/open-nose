"""ゼンマイ(渦巻き)型フレームの評価関数(3目的+制約)。

frame_model.build_frame_pair が作るチューブメッシュを経由せず、経路の点列
(build_side_paths)と鼻本体メッシュだけを使って評価する(earrings.
evaluation.pyと同じ理由: GAが個体ごとに繰り返し呼び出しても軽量)。

## 目的・制約の構成方針

earrings.evaluation.pyと同じ方針(本質的なトレードオフだけを目的とし、
残りは制約として0以下判定にする)を踏襲する。ただしゼンマイ型は
earrings(「b」字型)と保持の仕組みが根本的に違うため、目的の中身は
まったく別物になる:

- **保持の仕組みの違い**: earringsのリングは鼻翼を外側から挟む
  クリップ(ring_depthで皮膚に押し込み、ばねの反発力で留める)だったが、
  ゼンマイ型のコイルは鼻翼の外側にぶら下がる装飾で、皮膚を挟む機構を
  持たない(frame_model.pyのモジュールdocstring参照)。保持力はもっぱら
  ステムと鼻栓(ティッシュ)の摩擦に依るため、earringsのretention
  (挟み力、ring_depthとring_thicknessから計算)に相当する目的が存在
  しない。ステムの刺さり込みが十分であることは(earringsと同じく)
  制約(plug_insertion_margin)として要求するだけにする
- **目的(3つ、NSGA-IIが探索するトレードオフ)**: visibility(意匠性、
  コイルの突き出し量、最大化)・weight(快適さの代理指標、コイル+
  コネクタ+ステムの体積、最小化)・turns(意匠性、渦の巻き数、最大化)。
  visibilityとturnsはどちらも意匠性だが独立した軸である(半径を保った
  まま巻き数だけ増やす、逆に巻き数を保ったまま半径を大きくする、が
  それぞれ可能で、どちらもweightを増やす方向に働くため、この2つと
  weightの間に本質的なトレードオフがある)
- **制約(5つ)**: radius_order_margin・coil_clearance_margin・
  stem_clearance_margin・plug_insertion_margin・plug_overshoot_margin
  (FrameScore参照)。実際の閾値はいずれも暫定値で、NSGA-IIを実際に
  動かしながら見直す前提

## weight(重さ)の構成

weight = コイル(渦巻き+コネクタ)の経路長×断面積(π×(wire_thickness/2)^2)
+ ステムの体積。針金1本の実際の体積の代理指標で、値が大きいほど鼻栓
(ティッシュ)にかかる重さ・てこの力が増え、外れやすくなる・不快になる
と考えられるため最小化する。frame_modelがコイル・ステムを同じ線径
(wire_thickness)にしているため、断面積は共通で経路長の合計だけで
決まる。

## visibility・turns(意匠性)の構成

visibility = コイルの最外点が鼻翼の皮膚より外側へ出ている量
(earrings.evaluation.pyのhoop_protrusionと同じ考え方だが、コイルは円弧
ではなく渦巻きなので、最外点はコイルの点列全体から探す)。turns =
frame.turnsそのもの(渦の巻き数)。どちらも大きいほど「ゼンマイらしい」
見た目になるが、重さも増える。
"""

from dataclasses import dataclass

import numpy as np

from commons.nose_model import NoseParams, build_nose_body
from commons.plug_model import PlugParams
from spiral.frame_model import (
    FrameParams,
    SidePaths,
    build_side_paths,
    coil_clearance_margin,
    coil_protrusion,
    plug_insertion_margin,
    plug_overshoot_margin,
    radius_order_margin,
    stem_clearance_margin,
    validate_anchor_height,
    validate_target_reach,
)


def _path_length(points: list[np.ndarray]) -> float:
    """点列を順に結んだ折れ線の全長(隣接点間のユークリッド距離の合計)を返す。

    earrings.evaluation._path_lengthと同じ。
    """
    return sum(
        float(np.linalg.norm(points[i + 1] - points[i])) for i in range(len(points) - 1)
    )


def _weight(frame: FrameParams, coil_length: float) -> float:
    """重さ(快適さの代理指標、最小化)。コイル+コネクタ+ステムを1本の
    針金とみなした体積(mm^3)。モジュールdocstring「weight(重さ)の構成」
    参照。
    """
    total_length = coil_length + frame.stem_length
    area = np.pi * (frame.wire_thickness / 2) ** 2
    return total_length * area


@dataclass(frozen=True)
class FrameScore:
    """フレームの評価値(目的3つ+制約5つ。モジュールdocstring参照)。

    目的(visibility/weight/turns)はNSGA-IIが探索するトレードオフ。
    weightのみ最小化、他は最大化。制約(radius_order_margin以下の5項目)は
    実行不可能個体を除外するための値で、いずれも0以下であるべき。
    """

    # 目的(3つ)
    visibility: float  # 意匠性: コイルの皮膚からの突き出し(mm、最大化)
    weight: float  # 快適さ: コイル+ステムの体積(mm^3、最小化)
    turns: float  # 意匠性: 渦の巻き数(最大化)
    # 制約(5つ。すべて0以下であるべき)
    radius_order_margin: float  # 渦が中心に向かって細くなっているか(0以下であるべき)
    coil_clearance_margin: float  # コイルのめり込み超過量(0以下であるべき)
    stem_clearance_margin: float  # ステムのめり込み量(0以下であるべき)
    plug_insertion_margin: float  # ステムの刺さり込みが最小長さに足りているか(0以下であるべき)
    plug_overshoot_margin: float  # ステムが鼻栓を突き抜けていないか(0以下であるべき)


# 0以下が合格ラインの制約に共通で使う、浮動小数点誤差を吸収するための
# ごく小さな余裕(mm)。earrings.evaluation._MARGIN_EPSILONと同じ
_MARGIN_EPSILON = 1e-6


def constraint_values(score: FrameScore) -> tuple[float, ...]:
    """FrameScoreの5つの制約値を、NSGA-II(pymoo等)が使う規約(0以下=
    実行可能、正=違反量)に変換したタプルを返す。
    """
    return (
        score.radius_order_margin - _MARGIN_EPSILON,
        score.coil_clearance_margin - _MARGIN_EPSILON,
        score.stem_clearance_margin - _MARGIN_EPSILON,
        score.plug_insertion_margin - _MARGIN_EPSILON,
        score.plug_overshoot_margin - _MARGIN_EPSILON,
    )


def evaluate_frame(
    frame: FrameParams, plug: PlugParams, params: NoseParams
) -> FrameScore:
    """FrameParams から快適さ・意匠性の評価値を計算する。

    frameに依存しない検証(validate_target_reach/validate_anchor_height)は
    例外で即座に止める。frameに依存する検証(radius_order_margin等)は
    例外で止めず、制約値としてFrameScoreに含める(earrings.evaluation.py
    と同じ方針)。
    """
    validate_target_reach(plug, params)
    body = build_nose_body(params)
    validate_anchor_height(params, body)
    sides: list[SidePaths] = [
        build_side_paths(frame, plug, params, body, side) for side in (-1, 1)
    ]

    coil_length = _path_length(sides[0][0])
    visibility = coil_protrusion(params, body, sides)

    insertion_margins = [
        plug_insertion_margin(plug, params, stem, side)
        for (_, stem), side in zip(sides, (-1, 1))
    ]
    overshoot_margins = [
        plug_overshoot_margin(plug, params, stem, side)
        for (_, stem), side in zip(sides, (-1, 1))
    ]

    return FrameScore(
        visibility=visibility,
        weight=_weight(frame, coil_length),
        turns=frame.turns,
        radius_order_margin=radius_order_margin(frame),
        coil_clearance_margin=coil_clearance_margin(frame, sides, body),
        stem_clearance_margin=stem_clearance_margin(sides, body, frame.wire_thickness),
        plug_insertion_margin=max(insertion_margins),
        plug_overshoot_margin=max(overshoot_margins),
    )
