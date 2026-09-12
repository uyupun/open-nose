"""鼻ピアス型(「b」字)フレームの評価関数(機能性・快適さ・意匠性の3目的+制約)。

frame_model.build_frame_pair が作るチューブメッシュを経由せず、経路の点列
(build_side_paths)と鼻本体メッシュだけを使って評価する。メッシュの生成
コストを払わずに済むため、遺伝的アルゴリズムが個体ごとに繰り返し
呼び出す用途でも軽量に計算できる。

## 目的・制約の構成方針

各評価項目を「意匠性」のような1軸のサブ項目にまとめて重み付けで1つの
スカラーに合成する設計は、その重みを恣意的に決める必要が生じるため避けて
いる。代わりに、本質的なトレードオフ(良し悪しの間で選択の余地があり、
わざと悪化させて選ぶ理由がありうるもの)だけを目的とし、残りは「一定水準を
満たしていれば良い(わざと悪化させる理由がない)」制約として0以下判定に
している:

- **目的(3つ、NSGA-IIが探索するトレードオフ)**: retention(機能性、
  最大化)・pain(快適さ、最小化)・visibility(意匠性、最大化)
- **制約(9つ、実行不可能個体を除外するための閾値判定)**:
  proportion_penalty・thickness_order_margin・hook_reach_margin・
  stem_entry_margin・hoop_visibility_margin・ring_clearance_margin・
  stem_clearance_margin・plug_insertion_margin・plug_overshoot_margin
  (FrameScore参照)。実際の閾値はいずれも暫定値で、NSGA-IIを実際に
  動かしながら見直す前提

## retention(挟み力)とpain(圧力)の構成

「b」字型は、C字のリングがバネとして開かれ、鼻翼の壁を「鼻孔の中の
ステム+鼻栓」と「外側のリングの終端」で挟む力で鼻に留まる(earrings.
frame_modelのモジュールdocstring参照)。この挟み力と、それが皮膚に
与える圧力を、次の単純な代理指標で表す:

- **retention = 挟み力 ∝ バネ剛性 × たわみ**。フック(円弧+鼻の下を
  通る直線+小さな曲げ)を片持ち梁とみなすと、その剛性は線材の曲げ剛性
  EI(I∝線径^4)に比例し、梁の全長Lの3乗に反比例する(k=3EI/L^3)。Lは
  earrings.frame_model.ring_pointsの経路の実際の全長(_path_length)。
  以前はLの代わりにring_radius(円弧の半径)を使っていたが、フックが
  「円弧+直線+曲げ」の複合経路になった後は、隙間角度(ring_gap_deg)や
  直線区間の長さが変わっても半径が同じなら剛性が変わらず、実際には
  より柔らかい個体を過大評価していた(_clamp_forceのdocstring参照)。
  たわみはmax(ring_depth, 0)(終端を皮膚へ押し込む量。0未満クランプの
  理由は_clamp_forceのdocstring参照)。既定値で1になるよう正規化した
  ring_depth × (ring_thickness/既定)^4 × (経路長/既定)^-3。大きく柔らかい
  フープほどたわみにくく、太い線ほど硬い、という実物のフープの挙動に
  対応する
- **pain = 圧力 ∝ 挟み力 / 接触面積**。接触面積は「実際に皮膚に触れて
  いるリングの弧長(earrings.frame_model.ring_contact_length、メッシュに
  対する符号付き距離で実測)×線径」。点接触に近い場合でも線径×線径の
  面積は持つとみなし、接触長の下限を線径にする

以前はretention=ring_depth×ring_thickness×弧長+刺さり込み×stem_
thickness、pain=ring_depthとしていたが、(1) リング項(mm^3)とステム項
(mm^2)の次元が合っていない、(2) リングの大半が意図的に空中に浮く設計に
なった後も弧長全体を接触面積の代理にしていたため、半径を大きくするほど
retentionが増える誤った圧力がかかっていた、(3) 太さがretentionを増やす
一方painに一切効かないため、ring_thicknessが探索範囲の上限に張り付き
トレードオフとして機能していなかった、という3点が実際のGA実行で確認
されたため置き換えた。新しい定義では太い線は挟み力も圧力も上げるため、
太さの違う個体がパレートフロント上に並ぶ。

## visibility(意匠性)の構成

visibility = フープの最外点が鼻翼の皮膚より外側へ出ている量
(earrings.frame_model.hoop_protrusion、mm)。実際の鼻ピアスのフープは
鼻の横に見えてこそ装飾であり、大きく張り出すほどピアスらしい。一方で
大きなフープはバネとして柔らかく(retention∝1/半径^3)、剛性を保とうと
すれば線を太くして圧力が上がるため、retention/painとの本質的な
トレードオフになる。

以前は意匠性をfit_gap(リングの上側の円弧がどれだけ皮膚に沿っているか、
最小化)としていたが、それだとGAが皮膚に張り付いた小さなリングを最良と
みなし、(1) 実物としては鼻翼に通せない(沿わせすぎ)、(2) リングが
鼻栓の周りの低い位置に収まって鼻翼まで届かず、鼻ピアスらしく見えない、
という指摘を受けたため、方向を逆にした。皮膚への密着は目的にも制約にも
していない(めり込みすぎだけをring_clearance_marginが弾く)。

ステムが鼻栓(ティッシュ)を保持する力は、フレーム→鼻翼の挟みと直列に
働くが、刺さり込みの長さが十分あれば律速にならない(ティッシュは軽い)
ため、目的には含めず「最低plug.length×earrings.frame_model._MIN_
INSERTION_TO_PLUG_LENGTHだけ刺さっていること」の制約(plug_insertion_
margin)として扱う。この結果stem_length/stem_thicknessは目的に直接効かず、
制約(刺さり込み・突き抜け・太さの順序・プロポーション)を満たす範囲で
自由になる。
"""

from dataclasses import dataclass

import numpy as np

from commons.nose_model import NoseParams, build_nose_body
from commons.plug_model import PlugParams
from earrings.frame_model import (
    FrameParams,
    SidePaths,
    build_side_paths,
    hook_reach_margin,
    hoop_protrusion,
    hoop_visibility_margin,
    plug_insertion_margin,
    plug_overshoot_margin,
    ring_clearance_margin,
    ring_contact_length,
    stem_clearance_margin,
    stem_entry_margin,
    thickness_order_margin,
    validate_ring_height,
    validate_target_reach,
)

# プロポーション評価(下限)で許容する、太さ(stem_thickness)/全長 比の下限。
# 固定の「理想比率」を目標にすると設計者個人の美意識を客観指標と偽装する
# ことになるため、範囲内は罰則0とし、下回った分だけを罰則にする
# (毛髪のように細く見える、という明らかに破綻したケースだけを弾く緩い値)
_MIN_THICKNESS_RATIO = 0.03
# プロポーション評価(上限)で、stem_thicknessの太さを頭打ちにする基準。
# plug.diameterに対する倍率(挟んでいる相手=鼻栓より太い棒にする理由は
# ない、という考え方)
_MAX_THICKNESS_TO_PLUG_DIAMETER = 1.0
# retention(バネ剛性)の正規化に使う基準値(mm)。FrameParamsの既定値
# (ring_radius=7.5, ring_gap_deg=80.0)でのリング経路長(_path_length(ring)、
# 実測31.9mm)と同じにして、既定値で剛性が1になるようにする。剛性は線径の
# 4乗/経路長の3乗という強い非線形なので、正規化しないと探索範囲内で数桁の
# 値になり表示・比較しづらい(パレート順位は単調変換で変わらないため、値の
# 見やすさだけの措置)
_REF_RING_THICKNESS = 1.4
_REF_RING_LENGTH = 31.9


def _path_length(points: list[np.ndarray]) -> float:
    """点列を順に結んだ折れ線の全長(隣接点間のユークリッド距離の合計)を返す。"""
    return sum(
        float(np.linalg.norm(points[i + 1] - points[i])) for i in range(len(points) - 1)
    )


def _clamp_force(frame: FrameParams, ring_length: float) -> float:
    """リングの挟み力の代理指標(バネ剛性×たわみ、既定値で剛性1に正規化)。
    理由はモジュールdocstring「retention(挟み力)とpain(圧力)の構成」参照。
    retention・painの両方から参照される。

    片持ち梁のたわみ剛性(k=3EI/L^3)にならい、Lをearrings.frame_model.
    ring_pointsの経路(大きな円弧+鼻の下を通る直線+小さな曲げ)の実際の
    全長とする。以前はring_radius(円弧の半径)を使っていたが、フックが
    「円弧+直線+曲げ」の複合経路になった後は、隙間角度(ring_gap_deg)や
    鼻の下を通る直線区間の長さ(円弧の中心と鼻栓の軸の距離で決まる)が
    変わっても半径が同じなら剛性の見積もりが変わらず、実際にはより長い
    経路(=より柔らかい)個体を過大評価していた。経路長を使えば、隙間が
    狭く円弧が長い個体や、直線区間が長い個体を正しく「柔らかい」と
    評価できる。

    たわみ(frame.ring_depth)は0未満を0にクランプする。earrings.
    frame_model.ring_clearance_marginを実測の隙間ベースの制約に変更した
    後、線材が細い個体では接触点を皮膚より外側へ引く(ring_depthを負に
    する)ことでしか隙間を満たせない場合がある(earrings.frame_model.
    FrameParams参照)。この場合は皮膚に触れてすらいないため、挟み力は
    負ではなく0が正しい。
    """
    deflection = max(frame.ring_depth, 0.0)
    stiffness = (frame.ring_thickness / _REF_RING_THICKNESS) ** 4 / (
        ring_length / _REF_RING_LENGTH
    ) ** 3
    return stiffness * deflection


def _retention(frame: FrameParams, ring_length: float) -> float:
    """保持力(機能性、最大化)。リングの挟み力そのもの(_clamp_force)。

    左右のリングは形状が鏡映で等しいため片側で十分。
    """
    return _clamp_force(frame, ring_length)


def _pain(frame: FrameParams, ring_length: float, contact_length: float) -> float:
    """痛み(快適さ、最小化)。皮膚にかかる圧力の代理指標=挟み力/接触面積。

    接触面積は接触長×線径。接触長は線径を下限にする(接触が1点に近くても
    線材の断面程度の面積では触れているとみなす。0除算の回避も兼ねる)。
    contact_lengthは片側のリングの実測値(earrings.frame_model.
    ring_contact_length)。左右は鏡映で等しいため片側で十分。
    """
    area = max(contact_length, frame.ring_thickness) * frame.ring_thickness
    return _clamp_force(frame, ring_length) / area


def _proportion_penalty(
    sides: list[SidePaths], stem_thickness: float, max_thickness: float
) -> float:
    """プロポーションの破綻(制約)。下限は太さ(stem_thickness)/全長比が
    _MIN_THICKNESS_RATIOを下回った分(細すぎ)、上限はstem_thicknessが
    max_thickness(plug.diameter基準の頭打ち値)を超えた分(太すぎ)を
    罰則にする(範囲内は0)。範囲内は0で、わざと少し破綻させたい理由が
    ないため目的ではなく制約として扱う(FrameScore参照)。

    stem_thicknessだけを対象にするのは、「リングは太く、ステムは細く」
    という設計方針(earrings.frame_model.thickness_order_margin)のもとでは、
    太さが破綻しうるのは細い方のstem_thicknessだからである。
    """
    penalties = []
    for ring, stem in sides:
        # リングの経路長+ステムの全長(ring[-1]==stem[0]で接続しているので
        # 単純な和でよい)
        length = _path_length(ring) + _path_length(stem)
        ratio = stem_thickness / length
        too_thin = max(0.0, _MIN_THICKNESS_RATIO - ratio)
        too_thick = max(0.0, stem_thickness - max_thickness)
        penalties.append(too_thin + too_thick)
    return max(penalties)


@dataclass(frozen=True)
class FrameScore:
    """フレームの評価値(目的3つ+制約9つ。モジュールdocstring参照)。

    目的(retention/pain/visibility)はNSGA-IIが探索するトレードオフ。
    painのみ最小化、他は最大化。制約(proportion_penalty以下の9項目)は
    実行不可能個体を除外するための値で、いずれも0以下であるべき
    (わざと悪化させて選ぶ理由がない)。

    thickness_order_margin以下の制約は、earrings.frame_model.pyの
    validate_*(build_frame_pairが使う、例外を送出する版)と対になる
    制約値。frameの探索によって結果が変わる検証なので、evaluate_frameは
    例外で止めずこれらを制約として返す(earrings.frame_model.pyの
    モジュールdocstring参照)。
    """

    # 目的(3つ)
    retention: float  # 機能性: リングの挟み力(既定値=1の相対値、最大化)
    pain: float  # 快適さ: 皮膚にかかる圧力(挟み力/接触面積、最小化)
    visibility: float  # 意匠性: フープの皮膚からの突き出し(mm、最大化)
    # 制約(9つ。すべて0以下であるべき)
    proportion_penalty: float  # 太さの破綻(0であるべき)
    thickness_order_margin: float  # リングがステムより太いか(0以下であるべき)
    hook_reach_margin: float  # リングとステムの間に最低限の隙間があるか(0以下であるべき)
    stem_entry_margin: float  # ステムが鼻栓の露出面より下から入っているか(0以下であるべき)
    hoop_visibility_margin: float  # フープが最低限皮膚より外に出ているか(0以下であるべき)
    ring_clearance_margin: float  # リング表面と鼻表面の隙間が最低限あるか(0以下であるべき)
    stem_clearance_margin: float  # ステムのめり込み量(0以下であるべき)
    plug_insertion_margin: float  # ステムの刺さり込みが最小長さに足りているか(0以下であるべき)
    plug_overshoot_margin: float  # ステムが鼻栓を突き抜けていないか(0以下であるべき)


# 0以下が合格ラインの制約に共通で使う、浮動小数点誤差を吸収するための
# ごく小さな余裕(mm、または比率)
_MARGIN_EPSILON = 1e-6


def constraint_values(score: FrameScore) -> tuple[float, ...]:
    """FrameScoreの9つの制約値を、NSGA-II(pymoo等)が使う規約(0以下=
    実行可能、正=違反量)に変換したタプルを返す。

    いずれも0以下が合格ラインなので、_MARGIN_EPSILONを引くだけ(境界の
    誤差吸収)。
    """
    return (
        score.proportion_penalty - _MARGIN_EPSILON,
        score.thickness_order_margin - _MARGIN_EPSILON,
        score.hook_reach_margin - _MARGIN_EPSILON,
        score.stem_entry_margin - _MARGIN_EPSILON,
        score.hoop_visibility_margin - _MARGIN_EPSILON,
        score.ring_clearance_margin - _MARGIN_EPSILON,
        score.stem_clearance_margin - _MARGIN_EPSILON,
        score.plug_insertion_margin - _MARGIN_EPSILON,
        score.plug_overshoot_margin - _MARGIN_EPSILON,
    )


def evaluate_frame(
    frame: FrameParams, plug: PlugParams, params: NoseParams
) -> FrameScore:
    """FrameParams から機能性・快適さ・意匠性の評価値を計算する。

    frameに依存しない検証(validate_target_reach/validate_ring_height。
    PlugParams/NoseParamsにしか依存せず、GAの探索中は結果が変わらない)は
    例外で即座に止める。frameに依存する検証(hook_reach_margin等)は例外で
    止めず、制約値としてFrameScoreに含める(earrings.frame_model.pyの
    モジュールdocstring参照)。
    """
    validate_target_reach(plug, params)
    body = build_nose_body(params)
    validate_ring_height(params, body)
    sides: list[SidePaths] = [
        build_side_paths(frame, plug, params, body, side) for side in (-1, 1)
    ]

    max_thickness = plug.diameter * _MAX_THICKNESS_TO_PLUG_DIAMETER
    ring_length = _path_length(sides[0][0])
    contact_length = ring_contact_length(frame, sides[0][0], body)

    insertion_margins = [
        plug_insertion_margin(plug, params, stem, side)
        for (_, stem), side in zip(sides, (-1, 1))
    ]
    overshoot_margins = [
        plug_overshoot_margin(plug, params, stem, side)
        for (_, stem), side in zip(sides, (-1, 1))
    ]

    return FrameScore(
        retention=_retention(frame, ring_length),
        pain=_pain(frame, ring_length, contact_length),
        visibility=hoop_protrusion(params, body, sides),
        proportion_penalty=_proportion_penalty(
            sides, frame.stem_thickness, max_thickness
        ),
        thickness_order_margin=thickness_order_margin(frame),
        hook_reach_margin=hook_reach_margin(frame, params, body),
        stem_entry_margin=stem_entry_margin(frame, plug, params, body),
        hoop_visibility_margin=hoop_visibility_margin(params, body, sides),
        ring_clearance_margin=ring_clearance_margin(frame, sides, body),
        stem_clearance_margin=stem_clearance_margin(sides, body, frame.stem_thickness),
        plug_insertion_margin=max(insertion_margins),
        plug_overshoot_margin=max(overshoot_margins),
    )
