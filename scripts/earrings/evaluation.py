"""フレームの評価関数(機能性・快適さ・意匠性の3目的+制約)。

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
  最大化)・pain(快適さ、最小化)・fit_gap(意匠性、最小化)
- **制約(9つ、実行不可能個体を除外するための閾値判定)**: fit_gap_max・
  proportion_penalty・thickness_order_margin・stem_plug_margin・
  hoop_visibility_margin・ring_clearance_margin・stem_clearance_margin・
  plug_insertion_margin・plug_overshoot_margin(FrameScore参照)。実際の
  閾値はいずれも暫定値で、NSGA-IIを実際に動かしながら見直す前提。
  hoop_visibility_margin(フープが鼻の横に見えること)は、retention
  (剛性∝1/半径^3)・fit_gap(皮膚への密着)がどちらも小さなフープを
  有利にするため、目的だけに任せるとGAがフープを鼻孔の中に隠して
  しまう(実際に確認)ことへの対策として置いた設計要件の制約

## retention(挟み力)とpain(圧力)の構成

「b」字型は、C字のリングがバネとして開かれ、鼻翼の壁を「鼻孔の中の
ステム+鼻栓」と「外側のリングの終端」で挟む力で鼻に留まる(earrings.
frame_modelのモジュールdocstring参照)。この挟み力と、それが皮膚に
与える圧力を、次の単純な代理指標で表す:

- **retention = 挟み力 ∝ バネ剛性 × たわみ**。C字リング(円弧状の
  線材バネ)の開口部の剛性は、線材の曲げ剛性EI(I∝線径^4)に比例し、
  半径の3乗に反比例する(曲げ変形の基本式)。たわみはring_depth
  (終端を皮膚へ押し込む量)。既定値で1になるよう正規化した
  ring_depth × (ring_thickness/既定)^4 / (ring_radius/既定)^3。
  大きなフープほど柔らかく、太い線ほど硬い、という実物のフープの
  挙動に対応する
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

ステムが鼻栓(ティッシュ)を保持する力は、フレーム→鼻翼の挟みと直列に
働くが、刺さり込みの長さが十分あれば律速にならない(ティッシュは軽い)
ため、目的には含めず「最低earrings.frame_model._MIN_PLUG_INSERTIONだけ
刺さっていること」の制約(plug_insertion_margin)として扱う。この結果
stem_length/stem_thicknessは目的に直接効かず、制約(刺さり込み・
突き抜け・鼻栓内に収まる・太さの順序・プロポーション)を満たす範囲で
自由になる。
"""

from dataclasses import dataclass

import numpy as np
import trimesh

from earrings.frame_model import (
    FrameParams,
    SidePaths,
    build_side_paths,
    hoop_visibility_margin,
    plug_insertion_margin,
    plug_overshoot_margin,
    ring_clearance_margin,
    ring_contact_length,
    ring_upper_points,
    stem_clearance_margin,
    stem_plug_margin,
    thickness_order_margin,
    validate_ring_height,
    validate_target_reach,
)
from commons.nose_model import NoseParams, build_nose_body
from commons.plug_model import PlugParams

# プロポーション評価(下限)で許容する、太さ(stem_thickness)/全長 比の下限。
# 固定の「理想比率」を目標にすると設計者個人の美意識を客観指標と偽装する
# ことになるため、範囲内は罰則0とし、下回った分だけを罰則にする
# (毛髪のように細く見える、という明らかに破綻したケースだけを弾く緩い値)
_MIN_THICKNESS_RATIO = 0.03
# プロポーション評価(上限)で、stem_thicknessの太さを頭打ちにする基準。
# plug.diameterに対する倍率(挟んでいる相手=鼻栓より太い棒にする理由は
# ない、という考え方)
_MAX_THICKNESS_TO_PLUG_DIAMETER = 1.0
# retention(バネ剛性)の正規化に使う基準値(mm)。FrameParamsの既定値と
# 同じにして、既定値で剛性が1になるようにする。剛性は線径の4乗/半径の
# 3乗という強い非線形なので、正規化しないと探索範囲内で数桁の値になり
# 表示・比較しづらい(パレート順位は単調変換で変わらないため、値の
# 見やすさだけの措置)
_REF_RING_THICKNESS = 1.4
_REF_RING_RADIUS = 4.0


def _path_length(points: list[np.ndarray]) -> float:
    """点列を順に結んだ折れ線の全長(隣接点間のユークリッド距離の合計)を返す。"""
    return sum(
        float(np.linalg.norm(points[i + 1] - points[i])) for i in range(len(points) - 1)
    )


def _clamp_force(frame: FrameParams) -> float:
    """リングの挟み力の代理指標(バネ剛性×たわみ、既定値で剛性1に正規化)。
    理由はモジュールdocstring「retention(挟み力)とpain(圧力)の構成」参照。
    retention・painの両方から参照される。
    """
    stiffness = (frame.ring_thickness / _REF_RING_THICKNESS) ** 4 / (
        frame.ring_radius / _REF_RING_RADIUS
    ) ** 3
    return stiffness * frame.ring_depth


def _retention(frame: FrameParams) -> float:
    """保持力(機能性、最大化)。リングの挟み力そのもの(_clamp_force)。

    左右のリングは形状が鏡映で等しいため片側で十分。
    """
    return _clamp_force(frame)


def _pain(frame: FrameParams, contact_length: float) -> float:
    """痛み(快適さ、最小化)。皮膚にかかる圧力の代理指標=挟み力/接触面積。

    接触面積は接触長×線径。接触長は線径を下限にする(接触が1点に近くても
    線材の断面程度の面積では触れているとみなす。0除算の回避も兼ねる)。
    contact_lengthは片側のリングの実測値(earrings.frame_model.
    ring_contact_length)。左右は鏡映で等しいため片側で十分。
    """
    area = max(contact_length, frame.ring_thickness) * frame.ring_thickness
    return _clamp_force(frame) / area


def _fit_gap(
    sides: list[SidePaths], body: trimesh.Trimesh, ring_thickness: float
) -> tuple[float, float]:
    """視覚的な自然さ。リングのうち鼻翼の皮膚に沿って上る部分(earrings.
    frame_model.ring_upper_points)の"円柱表面"から鼻本体表面までの距離の
    (平均, 最悪点)を返す。値が小さいほど、実際の鼻ピアスのフープが
    鼻翼の皮膚に沿って見えるのと同じく、リングが鼻翼に密着して自然に
    見える。平均は目的(fit_gap)、最悪点は制約(fit_gap_max)として使う
    (FrameScore参照)。

    リングの下端(鼻孔の縁の下の空間)・内側の端(鼻孔の中)は、皮膚から
    離れているのが正常(輪の内側に空間があるからこそピアスらしく見える)
    なので評価対象にしない。ステムも鼻孔の中を通る想定で皮膚との距離に
    意味がないため対象外。対象の点が1つもない側(ring_gap_degが大きく、
    接触点より上の円弧が存在しない場合)は0(=浮きなし)として扱う。

    半径分を引くのは中心線からの距離が、実際に見える太いチューブ表面の
    隙間より過大に出るため。

    closest_point(rtreeによる空間索引を使う高速版)を使う。総当たりの
    closest_point_naiveより速く、結果は変わらない(frame_model.
    _signed_distance_to_bodyのdocstring参照)。
    """
    means, maxes = [], []
    for ring, _ in sides:
        upper = ring_upper_points(ring)
        if len(upper) == 0:
            means.append(0.0)
            maxes.append(0.0)
            continue
        _, distance, _ = trimesh.proximity.closest_point(body, upper)
        tube_distance = np.maximum(distance - ring_thickness / 2, 0.0)
        means.append(float(np.mean(tube_distance)))
        maxes.append(float(np.max(tube_distance)))
    return max(means), max(maxes)


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
        # リングの弧長+ステムの全長(ring[-1]==stem[0]で接続しているので
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

    目的(retention/pain/fit_gap)はNSGA-IIが探索するトレードオフ。
    retentionのみ最大化、他は最小化。制約(fit_gap_max以下の9項目)は
    実行不可能個体を除外するための値で、いずれも0または一定値以下で
    あるべき(わざと悪化させて選ぶ理由がない)。

    thickness_order_margin/stem_plug_margin/hoop_visibility_margin/
    ring_clearance_margin/stem_clearance_margin/plug_insertion_margin/
    plug_overshoot_marginは、
    earrings.frame_model.pyのvalidate_*(build_frame_pairが使う、例外を
    送出する版)と対になる制約値。frameの探索によって結果が変わる検証
    なので、evaluate_frameは例外で止めずこれらを制約として返す
    (earrings.frame_model.pyのモジュールdocstring参照)。
    """

    # 目的(3つ)
    retention: float  # 機能性: リングの挟み力(既定値=1の相対値、最大化)
    pain: float  # 快適さ: 皮膚にかかる圧力(挟み力/接触面積、最小化)
    fit_gap: float  # 意匠性: リングの鼻翼への密着・平均(mm、最小化)
    # 制約(9つ。すべて0または一定値以下であるべき)
    fit_gap_max: float  # 局所的な浮きの最悪点(閾値: _FIT_GAP_MAX_THRESHOLD)
    proportion_penalty: float  # 太さの破綻(0であるべき)
    thickness_order_margin: float  # リングがステムより太いか(0以下であるべき)
    stem_plug_margin: float  # ステムが鼻栓の円柱内に収まっているか(0以下であるべき)
    hoop_visibility_margin: float  # フープが皮膚より外に出て見えるか(0以下であるべき)
    ring_clearance_margin: float  # リングのめり込み超過量(0以下であるべき)
    stem_clearance_margin: float  # ステムのめり込み量(0以下であるべき)
    plug_insertion_margin: float  # ステムの刺さり込みが最小長さに足りているか(0以下であるべき)
    plug_overshoot_margin: float  # ステムが鼻栓を突き抜けていないか(0以下であるべき)


# 0以下が合格ラインの制約に共通で使う、浮動小数点誤差を吸収するための
# ごく小さな余裕(mm、または比率)
_MARGIN_EPSILON = 1e-6

# fit_gap_maxの許容値(mm)。鼻栓自体の直径(plug.diameterの既定値6.0mm)を
# 「これ以上局所的に離れていたら明らかに顔から浮いて見える」の目安にする
# (フレームが挟んでいる相手=鼻栓より大きく浮くのは不自然、という考え方)
_FIT_GAP_MAX_THRESHOLD = 6.0


def constraint_values(score: FrameScore) -> tuple[float, ...]:
    """FrameScoreの9つの制約値を、NSGA-II(pymoo等)が使う規約(0以下=
    実行可能、正=違反量)に変換したタプルを返す。

    すでに0以下が合格ラインの8項目は_MARGIN_EPSILONを引くだけ(境界の
    誤差吸収)。fit_gap_maxは実際の閾値を引く。
    """
    return (
        score.fit_gap_max - _FIT_GAP_MAX_THRESHOLD,
        score.proportion_penalty - _MARGIN_EPSILON,
        score.thickness_order_margin - _MARGIN_EPSILON,
        score.stem_plug_margin - _MARGIN_EPSILON,
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
    例外で即座に止める。frameに依存する検証(stem_plug_margin等)は例外で
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
    fit_gap, fit_gap_max = _fit_gap(sides, body, frame.ring_thickness)
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
        retention=_retention(frame),
        pain=_pain(frame, contact_length),
        fit_gap=fit_gap,
        fit_gap_max=fit_gap_max,
        proportion_penalty=_proportion_penalty(
            sides, frame.stem_thickness, max_thickness
        ),
        thickness_order_margin=thickness_order_margin(frame),
        stem_plug_margin=stem_plug_margin(frame, plug, params, sides),
        hoop_visibility_margin=hoop_visibility_margin(params, body, sides),
        ring_clearance_margin=ring_clearance_margin(frame, sides, body),
        stem_clearance_margin=stem_clearance_margin(sides, body, frame.stem_thickness),
        plug_insertion_margin=max(insertion_margins),
        plug_overshoot_margin=max(overshoot_margins),
    )
