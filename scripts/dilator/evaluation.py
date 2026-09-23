"""拡張ブリッジ型フレームの評価関数(3目的+制約)。

frame_model.build_bridge_piece/build_leg_pieceが作るメッシュを経由せず、
経路の点列(build_paths)と鼻本体メッシュだけを使って評価する
(earrings/spiral.evaluation.pyと同じ理由: GAが個体ごとに繰り返し呼び
出しても軽量)。

## 目的・制約の構成方針

earrings/spiral.evaluation.pyと同じ方針(本質的なトレードオフだけを
目的とし、残りは制約として0以下判定にする)を踏襲する。ただしこの設計は
「デザイン重視から機能面重視に」というユーザー方針のもと、目的の中身が
大きく変わる。

**目的(3つ、NSGA-IIが探索するトレードオフ。いずれも最大化)**

1. extension_force: 両端を両面テープで貼った帯が小鼻を広げる力
2. plug_hold: 棒とレンズが鼻栓を保持する剛性
3. inconspicuousness: 目立たなさ(正面から見た投影面積の符号反転)。
   earrings/spiralのvisibility(目立つほど良い、意匠として主張する)とは
   正反対の方向を最大化する点が、この設計の特徴(ユーザー指定)

以前はpain(圧力=拡張力/接触面積)を2つ目の目的にしていたが、接触面積も
拡張力も同じようにbridge_widthに比例するため、painは実質的に
extension_forceの定数倍(実測の相関+0.99)で、パレートフロントが3次元
空間の1本の直線に退化していた。面圧はskin_pressure_margin(制約)へ移し、
代わりに棒・レンズの役割(鼻栓の保持)をplug_holdとして目的に据えた。
実測の相関はextension_force-plug_hold −0.37、extension_force-
inconspicuousness −0.19、plug_hold-inconspicuousness +0.06で、3つとも
独立した軸として働いている。

**制約(14個。FrameScore参照。すべて0以下であるべき)**

探索範囲(dilator/optimize._SEARCH_SPACE)からランダムに400件を評価した
ときの違反率(=GAの探索で実際に効いている度合い):

- 形が成立するかを決める、実際に効く制約: joint_access_margin(連結部が
  鼻の正面に寄りすぎていないか。ユーザー指摘「メガネをしていると付け
  づらそう」)・collar_clearance_margin 34.0%・
  rod_thickness_margin 31.8%・tab_retention_margin 19.5%・
  tape_area_margin 17.2%・rod_kink_margin 5.8%・skin_pressure_margin 5.8%・
  tab_fit_margin 3.8%・leg_clearance_margin 2.8%・curvature_margin 0.2%
- 安全網(この探索範囲では違反しないが、幾何の作り方を変えたときに
  退行を検出する): bridge_clearance_margin・collar_position_margin・
  lens_protrusion_margin・tab_thickness_margin。前の2つの改修では、この
  種の制約が実際に「棒がレンズの穴を塞ぐ」「棒が0.4mmまで潰れる」と
  いった退行を捕まえている

閾値はいずれも暫定値で、実際に印刷・装着しながら見直す前提。

## extension_force(拡張力)と skin_pressure(面圧)の構成

実際の鼻腔拡張テープと同じ「平らな板ばねを鼻の丸みに合わせて曲げる」
原理を、frame_model.bridge_curvatureが測る実際の曲率半径(actual_radius)
とframe.natural_radius(自然な曲率半径、値が大きいほど平ら)の差から
近似する(frame_model.pyのモジュールdocstring「拡張力の物理近似」参照):

- **extension_force = 拡張力 ∝ バネ剛性 × たわみ**。ブリッジは長方形
  断面(幅bridge_width×厚みbridge_thickness)の板ばね(実際のブリーズ
  ライトと同じ形状)とみなし、その曲げ剛性EIは幅に比例し厚みの3乗に
  比例する(I=width*thickness^3/12)。梁の全長Lの3乗に反比例する
  (k∝EI/L^3。earrings.evaluationの_clamp_forceと同じ考え方)。たわみは
  曲率の差(1/actual_radius - 1/natural_radius)。natural_radiusが
  actual_radiusより小さい(=鼻より曲がっている)場合は拡張力ではなく
  逆向きの力になってしまうため、0にクランプする(curvature_marginが
  制約としてこれを弾くので、実行可能な個体では常に正になるはずだが、
  念のため)
- **外を向いている貼り代の面だけが効く**(frame_model.tape_outward_ratio)。
  帯が曲げ戻る力のうち小鼻を開くのに使えるのは外向き(+x)の成分だけで、
  鼻の背面側へ回り込んだ貼り代は後ろ向きに引くだけで鼻腔を広げない
  (ユーザー指摘「アーチの両端が曲がりすぎている。ブリーズライトのように
  鼻腔を広げる役割にならないといけない」)。貼り代の各区間の外向き法線の
  x成分の平均を拡張力に掛ける。形状の側でも、法線のx成分が
  _MIN_TAPE_NORMAL_Xを下回るところで貼り代を打ち切っている
- **力を出すのは帯だけ**。以前は帯と棒を直列バネとして数えていたが、
  これはアーチが鼻に直接乗って棒から鼻栓へ力を伝える前提の式だった。
  両端を両面テープで貼る構造(ユーザー要望)に変わってからは、小鼻を
  広げる力はテープで固定された帯そのものが出し、棒とレンズはそこから
  ぶら下がって鼻栓を保持する部品なので、直列バネの経路に入らない。
  帯を1mm前後まで薄くした結果、剛性は棒(実測20.9)より帯(同0.483)が
  はるかに低く、直列にすると値がほぼ帯だけで決まるのに棒の寄与が
  あるように見える、という誤解を招く状態にもなっていた
- **装着位置(frame.bridge_y)が拡張力を左右する**。actual_radiusも
  path_lengthも、帯を鼻のどの高さに貼るかで変わる(鼻筋側ほど断面が
  細く平ら)。以前は装着位置が定数で、この2つがframeに依存しない
  =GAから見て定数だったため、拡張力は実質bridge_thicknessだけの関数に
  なっていた。bridge_yを探索変数にしたことで、装着位置そのものも
  最適化の対象になる
- **skin_pressure(面圧、制約)= 拡張力 / 貼り代の面積**。テープを貼る
  面(frame_model.tape_pad_area、連結部より外側の帯の両端)にかかる面圧。
  上限(_MAX_SKIN_PRESSURE)を超えると、痛みの前にテープが剥がれて力が
  肌へ伝わらない。以前はこれをpainとして目的にしていたが、拡張力・
  接触面積がどちらもbridge_widthに比例して約分され、実質extension_force
  の定数倍(相関+0.99)にしかならなかったため、制約へ移した

## plug_hold(鼻栓の保持剛性)の構成

plug_hold = 左右の棒を「タブ側が固定端・レンズ側が荷重点の片持ち梁」と
みなしたバネ定数の合計(_plug_hold・_rod_stiffness)。棒は太さが場所
ごとに変わる(frame_model._rod_radii)ため、一様断面の公式ではなく
カスティリアノの定理 δ/P = ∫ x^2/(E I(x)) dx を点列の上で数値積分して
その逆数を取る。

棒が柔らかいとレンズが振られて鼻栓がぐらつく。太く短い棒ほど高いが、
そのぶん目立つ(inconspicuousness)ので、leg_thicknessと装着位置
(bridge_y、棒の長さを決める)に本質的なトレードオフができる。実測の
相関はleg_thickness +0.67、bridge_y -0.74。

この積分は固定端(タブの首)側の細さに強く効く。タブの首の中では棒は
連結部の厚み(_tab_pad_thickness)までしか太くできないため、「帯を薄く
してもパッドで連結部だけ厚くする」という形の効果もここに現れる。

## inconspicuousness(目立たなさ)の構成

inconspicuousness = -(顔の正面から見たフレームの投影面積mm^2)
(_visible_area)。人から見て「目立つ」のは、鼻の上にどれだけの面積の
異物が見えているかなので、部品ごとの影の面積(ブリッジ=経路長×幅、
棒=区間ごとの長さ×直径、レンズ=外径×厚み)を足して測る。

以前は-(BRIDGE_OFFSET + bridge_thickness/2)、つまりブリッジが鼻の前面
から浮いている量だけだった。これだとbridge_thicknessの一次関数(実測
相関-1.000)にすぎず、実際にはいちばん目立つ「鼻の側面を約42mm下る棒」と
「鼻孔のレンズ」が評価に全く入らないうえ、bridge_widthも目的に現れない
ためGAが常に探索範囲の上限へ張り付いていた(パレートフロントの全個体が
bridge_width≈上限)。投影面積にすることで、bridge_width(実測相関-0.39)・
leg_thickness(-0.64)・bridge_y(-0.64、高い位置ほど棒が長くなる)が
「太く/長くすれば機能は上がるが目立つ」という本来のトレードオフとして
効くようになる。なおcollar_lengthだけは目的にほとんど現れず(±0.06)、
rod_thickness_margin・collar_clearance_marginという制約が実質的に
値を決めている(レンズの厚みは棒の最細部の太さと、鼻栓の露出部に
収まるかで決まる、はめあい寸法のため)。
"""

from dataclasses import dataclass

import numpy as np

from commons.nose_model import NoseParams, build_nose_body
from commons.plug_model import PlugParams
from dilator.frame_model import (
    CollarGeometry,
    FrameParams,
    RodPath,
    bridge_clearance_margin,
    bridge_curvature,
    bridge_points,
    tape_area_margin,
    tape_outward_ratio,
    tape_pad_area,
    build_paths,
    collar_clearance_margin,
    collar_position_margin,
    curvature_margin,
    joint_access_margin,
    leg_clearance_margin,
    lens_protrusion_margin,
    rod_kink_margin,
    rod_thickness_margin,
    tab_fit_margin,
    tab_retention_margin,
    tab_thickness_margin,
    validate_collar_no_overlap,
    validate_target_reach,
)

# バネ剛性の正規化に使う基準値(mm)。剛性は「断面二次モーメント/長さ^3」
# (ヤング率Eは共通なので約分される)で測り、この基準の帯の剛性を1とする
# (earrings.evaluationの_REF_RING_LENGTHと同じ考え方)
_REF_BRIDGE_WIDTH = 6.0
_REF_BRIDGE_THICKNESS = 1.0
_REF_BRIDGE_LENGTH = 23.5
_REF_STIFFNESS = (
    _REF_BRIDGE_WIDTH * _REF_BRIDGE_THICKNESS**3 / 12
) / _REF_BRIDGE_LENGTH**3
# 貼り代にかかってよい面圧の上限(extension_forceと同じ正規化での値を
# 面積mm^2で割ったもの)。これを超えると、痛い前に両面テープが剥がれて
# 拡張力が肌へ伝わらない(どちらも同じ面圧で決まるので1つの制約にして
# いる)。探索範囲の中で実際に効く(=硬すぎる帯を弾く)水準に置いた
# 暫定値で、テープの実物の保持力(N/cm^2)で置き換える前提
_MAX_SKIN_PRESSURE = 0.0015


def _rod_stiffness(rod: RodPath) -> float:
    """棒1本を、タブ側を固定端・レンズ側を荷重点とする片持ち梁とみなした
    ときのバネ剛性(E=1、単位mm)を返す。

    棒は太さが場所ごとに変わる(_rod_radii)ため、一様断面の公式(3EI/L^3)
    ではなく、カスティリアノの定理によるたわみ
    δ/P = ∫ x^2 / (E I(x)) dx(xは荷重点=レンズ側からの距離)を、点列
    (RodPath)の上で数値積分してその逆数を取る。定数係数は帯側と同じく
    省く(_REF_STIFFNESSで正規化するため)。

    この積分はxが大きいところ、つまり固定端(タブの首)側の細さに強く
    効く。タブの首の中では棒はbridge_thicknessまでしか太くできない
    (_rod_radii)ため、「アーチが薄いと、棒が太くても根元で力が逃げる」
    という実際の効き方がそのまま評価に入る。
    """
    points, radii = rod.points, rod.radii
    segment = np.linalg.norm(np.diff(points, axis=0), axis=1)
    # 各区間の代表値(両端の平均)。xは末尾(レンズ側)からの距離
    mid_radii = (radii[:-1] + radii[1:]) / 2
    from_tip = np.concatenate([[0.0], np.cumsum(segment[::-1])])[::-1][:-1]
    second_moment = np.pi * mid_radii**4 / 4
    compliance = float(np.sum(from_tip**2 / second_moment * segment))
    return 1.0 / compliance if compliance > 0 else np.inf


def _extension_force(
    frame: FrameParams,
    params: NoseParams,
    actual_radius: float,
    path_length: float,
) -> float:
    """拡張力(機能性、最大化)の代理指標(帯のバネ剛性×たわみ、基準の帯で
    剛性1に正規化)。モジュールdocstring「extension_force(拡張力)の構成」
    参照。

    小鼻を広げる力を出すのは、両端を両面テープで肌に貼った帯そのもの
    (曲げ戻ろうとする板ばね)。棒とレンズはそこからぶら下がって鼻栓を
    保持する部品で、この力の伝達経路には入らない(以前は帯と棒を直列
    バネとして数えていたが、テープで貼る構造に変えた時点で誤りになった)。
    """
    deflection = max(1 / actual_radius - 1 / frame.natural_radius, 0.0)
    stiffness = (
        frame.bridge_width * frame.bridge_thickness**3 / 12
    ) / path_length**3
    # 力のうち小鼻を外へ開くのに使えるのは、貼り代の面が外を向いている
    # ぶんだけ(frame_model.tape_outward_ratio)
    return stiffness / _REF_STIFFNESS * deflection * tape_outward_ratio(frame, params)


def _plug_hold(rods: list[RodPath]) -> float:
    """鼻栓の保持剛性(機能性、最大化)。左右の棒を、タブ側を固定端・
    レンズ側を荷重点とする片持ち梁とみなしたときのバネ定数の合計
    (基準の帯の剛性=1で正規化)。

    棒が柔らかいとレンズが振られ、差した鼻栓がぐらついて抜けやすい。
    太く短い棒ほど高いが、そのぶん目立つ(inconspicuousness)ため、
    leg_thicknessと装着位置(bridge_y、棒の長さを決める)に本質的な
    トレードオフを作る。
    """
    return sum(_rod_stiffness(rod) for rod in rods) / _REF_STIFFNESS


def _visible_area(
    frame: FrameParams,
    bridge: list[np.ndarray],
    rods: list[RodPath],
    collars: list[CollarGeometry],
) -> float:
    """フレームを顔の正面(x-y平面)から見たときの投影面積(mm^2)を返す。

    モジュールdocstring「inconspicuousness(目立たなさ)の構成」参照。
    部品ごとの影の面積を単純に足す(重なりは無視する近似):

    - ブリッジ: 正面から見た経路長 × 帯の幅
    - 棒: 各区間の正面から見た長さ × その区間の直径(太さが場所ごとに
      変わるため、区間ごとに足す)
    - レンズ: 筒を横から見た長方形(外径 × 厚み)
    """
    points = np.array(bridge)
    area = float(np.sum(np.linalg.norm(np.diff(points[:, :2], axis=0), axis=1)))
    area *= frame.bridge_width
    for rod in rods:
        segment = np.linalg.norm(np.diff(rod.points[:, :2], axis=0), axis=1)
        area += float(np.sum(segment * (rod.radii[:-1] + rod.radii[1:])))
    for collar in collars:
        area += 2 * collar.r_outer * (collar.y_end - collar.y_start)
    return area


@dataclass(frozen=True)
class FrameScore:
    """フレームの評価値(目的3つ+制約10個。モジュールdocstring参照)。

    目的(extension_force/pain/inconspicuousness)はNSGA-IIが探索する
    トレードオフ。painのみ最小化、他は最大化。制約(curvature_margin
    以下の10項目)は実行不可能個体を除外するための値で、いずれも0以下で
    あるべき。
    """

    # 目的(3つ)
    extension_force: float  # 機能性: 小鼻を広げる拡張力(基準の帯の剛性=1の相対値、最大化)
    plug_hold: float  # 機能性: 鼻栓の保持剛性(同じ正規化、最大化)
    inconspicuousness: float  # 意匠性: 目立たなさ(-正面から見た投影面積mm^2、最大化)
    # 制約(14個。すべて0以下であるべき)
    curvature_margin: float  # natural_radiusが十分平らか(0以下であるべき)
    bridge_clearance_margin: float  # ブリッジのめり込み超過量(0以下であるべき)
    leg_clearance_margin: float  # 棒のめり込み超過量(0以下であるべき)
    collar_clearance_margin: float  # レンズのめり込み量(0以下であるべき)
    collar_position_margin: float  # レンズが鼻栓の範囲内か(左右のうち厳しい方、0以下であるべき)
    lens_protrusion_margin: float  # 棒がレンズからはみ出していないか(0以下であるべき)
    rod_thickness_margin: float  # 棒の最も細いところが印刷できる太さか(0以下であるべき)
    rod_kink_margin: float  # 棒の曲がりが急すぎて自己交差していないか(0以下であるべき)
    tab_fit_margin: float  # 嵌め込みのスロットが帯に収まるか(0以下であるべき)
    tab_thickness_margin: float  # タブの厚みが足りているか(0以下であるべき)
    tab_retention_margin: float  # 嵌め込みの返しが実際に引っかかるか(0以下であるべき)
    skin_pressure_margin: float  # 貼り代にかかる面圧が上限以内か(0以下であるべき)
    tape_area_margin: float  # 両面テープの貼り代の面積が足りるか(0以下であるべき)
    joint_access_margin: float  # 連結部が鼻の側面に寄っているか(0以下であるべき)


# 0以下が合格ラインの制約に共通で使う、浮動小数点誤差を吸収するための
# ごく小さな余裕(mm)。earrings/spiral.evaluation._MARGIN_EPSILONと同じ
_MARGIN_EPSILON = 1e-6


def constraint_values(score: FrameScore) -> tuple[float, ...]:
    """FrameScoreの10個の制約値を、NSGA-II(pymoo等)が使う規約(0以下=
    実行可能、正=違反量)に変換したタプルを返す。
    """
    return (
        score.curvature_margin - _MARGIN_EPSILON,
        score.bridge_clearance_margin - _MARGIN_EPSILON,
        score.leg_clearance_margin - _MARGIN_EPSILON,
        score.collar_clearance_margin - _MARGIN_EPSILON,
        score.collar_position_margin - _MARGIN_EPSILON,
        score.lens_protrusion_margin - _MARGIN_EPSILON,
        score.rod_thickness_margin - _MARGIN_EPSILON,
        score.rod_kink_margin - _MARGIN_EPSILON,
        score.tab_fit_margin - _MARGIN_EPSILON,
        score.tab_thickness_margin - _MARGIN_EPSILON,
        score.tab_retention_margin - _MARGIN_EPSILON,
        score.skin_pressure_margin - _MARGIN_EPSILON,
        score.tape_area_margin - _MARGIN_EPSILON,
        score.joint_access_margin - _MARGIN_EPSILON,
    )


def evaluate_frame(
    frame: FrameParams, plug: PlugParams, params: NoseParams
) -> FrameScore:
    """FrameParams から機能性・快適さ・意匠性の評価値を計算する。

    frameに依存しない検証(validate_target_reach・validate_collar_no_
    overlap。PlugParams/NoseParams(と固定値の_COLLAR_WALL_THICKNESS)に
    しか依存せず、GAの探索中は結果が変わらない)は例外で即座に止める。
    frameに依存する検証(curvature_margin等)は例外で止めず、制約値として
    FrameScoreに含める(earrings/spiral.evaluation.pyと同じ方針)。
    """
    validate_target_reach(plug, params)
    validate_collar_no_overlap(plug, params)
    body = build_nose_body(params)
    bridge = bridge_points(body, params, frame.bridge_y, frame.tab_side_ratio)
    actual_radius, path_length = bridge_curvature(bridge)

    _, left_rod, right_rod, left_collar, right_collar = build_paths(frame, plug, params, body)
    rods = [left_rod, right_rod]
    collars = [left_collar, right_collar]

    force = _extension_force(frame, params, actual_radius, path_length)
    pad_area = tape_pad_area(frame, params)

    return FrameScore(
        extension_force=force,
        plug_hold=_plug_hold(rods),
        inconspicuousness=-_visible_area(frame, bridge, rods, collars),
        curvature_margin=curvature_margin(frame, bridge),
        bridge_clearance_margin=bridge_clearance_margin(frame, params, body),
        leg_clearance_margin=leg_clearance_margin(rods, body),
        collar_clearance_margin=collar_clearance_margin(collars, body),
        collar_position_margin=max(
            collar_position_margin(plug, params, left_collar, -1),
            collar_position_margin(plug, params, right_collar, 1),
        ),
        lens_protrusion_margin=lens_protrusion_margin(rods, collars),
        rod_thickness_margin=rod_thickness_margin(rods),
        rod_kink_margin=rod_kink_margin(rods),
        tab_fit_margin=tab_fit_margin(frame, params),
        tab_thickness_margin=tab_thickness_margin(frame),
        tab_retention_margin=tab_retention_margin(frame),
        skin_pressure_margin=force / pad_area - _MAX_SKIN_PRESSURE,
        tape_area_margin=tape_area_margin(frame, params),
        joint_access_margin=joint_access_margin(frame, params, body),
    )
