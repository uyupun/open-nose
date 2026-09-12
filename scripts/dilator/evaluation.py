"""拡張ブリッジ型フレームの評価関数(3目的+制約)。

frame_model.build_frame が作るチューブメッシュを経由せず、経路の点列
(build_paths)と鼻本体メッシュだけを使って評価する(earrings/spiral.
evaluation.pyと同じ理由: GAが個体ごとに繰り返し呼び出しても軽量)。

## 目的・制約の構成方針

earrings/spiral.evaluation.pyと同じ方針(本質的なトレードオフだけを
目的とし、残りは制約として0以下判定にする)を踏襲する。ただしこの設計は
「デザイン重視から機能面重視に」というユーザー方針のもと、目的の中身が
大きく変わる:

- **目的(3つ、NSGA-IIが探索するトレードオフ)**: extension_force(機能性、
  鼻腔を広げる拡張力、最大化)・pain(快適さ、皮膚にかかる圧力、最小化)・
  inconspicuousness(意匠性、目立たなさ、最大化)。earrings/spiralの
  visibility(目立つほど良い、意匠として主張する)とは正反対の方向を
  最大化する点が、この設計の最大の特徴(ユーザー指定: 「目立たなさ」を
  重視)
- **制約(6つ)**: thickness_order_margin・curvature_margin・
  bridge_clearance_margin・stem_clearance_margin・plug_insertion_margin・
  plug_overshoot_margin(FrameScore参照)。実際の閾値はいずれも暫定値で、
  NSGA-IIを実際に動かしながら見直す前提

## extension_force(拡張力)とpain(圧力)の構成

実際の鼻腔拡張テープと同じ「平らな板ばねを鼻の丸みに合わせて曲げる」
原理を、frame_model.bridge_curvatureが測る実際の曲率半径(actual_radius)
とfrmae.natural_radius(自然な曲率半径、値が大きいほど平ら)の差から
近似する(frame_model.pyのモジュールdocstring「拡張力の物理近似」参照):

- **extension_force = 拡張力 ∝ バネ剛性 × たわみ**。ブリッジを片持ち梁と
  みなすと、その剛性は線材の曲げ剛性EI(I∝線径^4)に比例し、梁の全長L
  の3乗に反比例する(k=3EI/L^3。earrings.evaluationの_clamp_forceと
  同じ考え方)。たわみは曲率の差(1/actual_radius - 1/natural_radius)。
  natural_radiusがactual_radiusより小さい(=鼻より曲がっている)場合は
  拡張力ではなく逆向きの力になってしまうため、0にクランプする
  (curvature_marginが制約としてこれを弾くので、実行可能な個体では
  常に正になるはずだが、念のため)
- **pain = 圧力 ∝ 拡張力 / 接触面積**。接触面積は「ブリッジが実際に
  鼻に触れている長さ×線径」。ブリッジは鼻の前面形状に沿わせる設計
  (frame_model.pyのbridge_points)であり、意図的に押し込む区間を作らない
  earrings/spiralのコイルと異なり全長が接触想定のため、接触長は単純に
  ブリッジの経路長(bridge_curvatureが返すpath_length)を使う

## inconspicuousness(目立たなさ)の構成

inconspicuousness = -(ブリッジが鼻の前面から実際に浮いている量)。
frame_model.BRIDGE_OFFSET(固定値)とブリッジの半径(bridge_thickness/2)
の和で近似する(この2つの合計がブリッジ表面が前面から離れる量の
理論値。earrings.frame_model.hoop_protrusionのような実測ではなく理論値
にしたのは、ブリッジは前面形状に追従して作られており、実測しても
ほぼこの理論値に一致するため)。bridge_thicknessが大きいほど目立つが
extension_force(剛性∝線径^4)にも効くため、この2つは本質的な
トレードオフになる。
"""

from dataclasses import dataclass

import numpy as np

from commons.nose_model import NoseParams, build_nose_body
from commons.plug_model import PlugParams
from dilator.frame_model import (
    BRIDGE_OFFSET,
    FrameParams,
    bridge_clearance_margin,
    bridge_curvature,
    bridge_points,
    build_paths,
    curvature_margin,
    plug_insertion_margin,
    plug_overshoot_margin,
    stem_clearance_margin,
    thickness_order_margin,
    validate_target_reach,
)

# retention(バネ剛性)の正規化に使う基準値(mm)。FrameParamsの既定値での
# ブリッジ経路長(bridge_curvatureのpath_length、実測44.3mm)と同じにして、
# 既定値で剛性が1になるようにする(earrings.evaluationの_REF_RING_LENGTH
# と同じ考え方)
_REF_BRIDGE_THICKNESS = 1.4
_REF_BRIDGE_LENGTH = 44.3


def _extension_force(
    frame: FrameParams, actual_radius: float, path_length: float
) -> float:
    """拡張力(機能性、最大化)の代理指標(バネ剛性×たわみ、既定値で
    剛性1に正規化)。モジュールdocstring「extension_force(拡張力)と
    pain(圧力)の構成」参照。extension_force・painの両方から参照される。
    """
    deflection = max(1 / actual_radius - 1 / frame.natural_radius, 0.0)
    stiffness = (frame.bridge_thickness / _REF_BRIDGE_THICKNESS) ** 4 / (
        path_length / _REF_BRIDGE_LENGTH
    ) ** 3
    return stiffness * deflection


@dataclass(frozen=True)
class FrameScore:
    """フレームの評価値(目的3つ+制約6つ。モジュールdocstring参照)。

    目的(extension_force/pain/inconspicuousness)はNSGA-IIが探索する
    トレードオフ。painのみ最小化、他は最大化。制約(thickness_order_margin
    以下の6項目)は実行不可能個体を除外するための値で、いずれも0以下で
    あるべき。
    """

    # 目的(3つ)
    extension_force: float  # 機能性: 鼻腔を広げる拡張力(既定値=1の相対値、最大化)
    pain: float  # 快適さ: 皮膚にかかる圧力(拡張力/接触面積、最小化)
    inconspicuousness: float  # 意匠性: 目立たなさ(-突き出し量mm、最大化)
    # 制約(6つ。すべて0以下であるべき)
    thickness_order_margin: float  # ブリッジがステムより太いか(0以下であるべき)
    curvature_margin: float  # natural_radiusが十分平らか(0以下であるべき)
    bridge_clearance_margin: float  # ブリッジのめり込み超過量(0以下であるべき)
    stem_clearance_margin: float  # ステムのめり込み量(0以下であるべき)
    plug_insertion_margin: float  # ステムの刺さり込みが最小長さに足りているか(0以下であるべき)
    plug_overshoot_margin: float  # ステムが鼻栓を突き抜けていないか(0以下であるべき)


# 0以下が合格ラインの制約に共通で使う、浮動小数点誤差を吸収するための
# ごく小さな余裕(mm)。earrings/spiral.evaluation._MARGIN_EPSILONと同じ
_MARGIN_EPSILON = 1e-6


def constraint_values(score: FrameScore) -> tuple[float, ...]:
    """FrameScoreの6つの制約値を、NSGA-II(pymoo等)が使う規約(0以下=
    実行可能、正=違反量)に変換したタプルを返す。
    """
    return (
        score.thickness_order_margin - _MARGIN_EPSILON,
        score.curvature_margin - _MARGIN_EPSILON,
        score.bridge_clearance_margin - _MARGIN_EPSILON,
        score.stem_clearance_margin - _MARGIN_EPSILON,
        score.plug_insertion_margin - _MARGIN_EPSILON,
        score.plug_overshoot_margin - _MARGIN_EPSILON,
    )


def evaluate_frame(
    frame: FrameParams, plug: PlugParams, params: NoseParams
) -> FrameScore:
    """FrameParams から機能性・快適さ・意匠性の評価値を計算する。

    frameに依存しない検証(validate_target_reach。PlugParams/NoseParams
    にしか依存せず、GAの探索中は結果が変わらない)は例外で即座に止める。
    frameに依存する検証(curvature_margin等)は例外で止めず、制約値として
    FrameScoreに含める(earrings/spiral.evaluation.pyと同じ方針)。
    """
    validate_target_reach(plug, params)
    body = build_nose_body(params)
    bridge = bridge_points(params)
    actual_radius, path_length = bridge_curvature(bridge)

    coil, stem_left, stem_right = build_paths(frame, plug, params)
    stems = [stem_left, stem_right]

    insertion_margins = [
        plug_insertion_margin(plug, params, stem, side)
        for stem, side in zip(stems, (-1, 1))
    ]
    overshoot_margins = [
        plug_overshoot_margin(plug, params, stem, side)
        for stem, side in zip(stems, (-1, 1))
    ]

    force = _extension_force(frame, actual_radius, path_length)
    contact_length = path_length
    area = contact_length * frame.bridge_thickness

    return FrameScore(
        extension_force=force,
        pain=force / area,
        inconspicuousness=-(BRIDGE_OFFSET + frame.bridge_thickness / 2),
        thickness_order_margin=thickness_order_margin(frame),
        curvature_margin=curvature_margin(frame, bridge),
        bridge_clearance_margin=bridge_clearance_margin(frame, coil, body),
        stem_clearance_margin=stem_clearance_margin(stems, body, frame.stem_thickness),
        plug_insertion_margin=max(insertion_margins),
        plug_overshoot_margin=max(overshoot_margins),
    )
