"""拡張ブリッジ型フレームの評価関数(3目的+制約)。

frame_model.build_bridge_piece/build_leg_pieceが作るメッシュを経由せず、
経路の点列(build_paths)と鼻本体メッシュだけを使って評価する
(earrings/spiral.evaluation.pyと同じ理由: GAが個体ごとに繰り返し呼び
出しても軽量)。

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
- **制約(10個)**: curvature_margin・bridge_clearance_margin・
  leg_clearance_margin・collar_clearance_margin・collar_position_margin・
  lens_protrusion_margin・rod_thickness_margin・tab_fit_margin・
  tab_thickness_margin・tab_retention_margin(FrameScore参照)。実際の閾値はいずれも暫定値で、NSGA-IIを実際に
  動かしながら見直す前提。

後半の3つは、ユーザーが実機のレンダリング(view_nose.pyでSTLを開いた
スクリーンショット)で指摘した2点、
(1)「レンズ(鼻栓を差し込む筒)から棒がはみ出ている」
(2)「ジョイントマットのような嵌め込む構造になっていない」
への対応として新設した。形状そのもの(frame_model)を作り直したうえで、
「作り方を変えたから大丈夫」で終わらせず、実際の寸法から毎回検証する:

- lens_protrusion_margin: 棒の各点の球が、レンズの下端より下に出ていない
  か・レンズの内径(鼻栓の空間)に入っていないかを、実際の中心線と点ごとの
  半径から測る(frame_model.lens_protrusion_margin参照)
- tab_fit_margin: 嵌め込みのスロットが、帯(ブリッジ)の幅・直線部分の
  中に、周りに必要な肉(_TAB_MIN_WALL)を残して収まるか
- tab_thickness_margin: タブ(帯と同じ厚み)が、嵌め込みの曲げに耐える
  最小の厚み(_MIN_TAB_THICKNESS)を満たすか

さらに、実際に印刷したユーザーからの「レンズと棒をもう少し太く(印刷
できない)」「連結部も細かい印刷で確実に」という指摘を受けて2つ追加した:

- rod_thickness_margin: 棒の最も細いところ(レンズへ溶け込む区間)の直径が
  印刷に必要な最小値(_MIN_ROD_DIAMETER)以上か。collar_lengthが小さいほど
  細くなるため、GAが極端に薄いレンズを選ばないよう誘導する
- tab_retention_margin: 嵌め込みの「返し」の引っかかり(tab_head_oversize
  からはめあいの隙間_TAB_CLEARANCEを引いた残り)が最小値
  (_MIN_TAB_RETENTION)以上か。隙間を広げた分、返しも大きくしないと
  抜けてしまうため

FrameParamsにはこの他tab_head_oversize(タブの矢じりの張り出し量、抜け
止めの引っかかり)があるが、目的には現れない(抜け止めの効き自体は
探索範囲の選び方で保証し、寸法として収まるかはtab_fit_marginが見る)。

## extension_force(拡張力)とpain(圧力)の構成

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
- **帯だけでなく棒も直列のバネとして数える**(_rod_stiffness)。鼻腔を
  実際に広げるのは、帯が曲げ戻ろうとする力が棒→レンズ→鼻栓と伝わった
  先の成分であり、棒が細ければそこでたわんで力が逃げる。棒は約42mmと
  帯(約19mm)より長いため、実測ではこちらが律速になる。左右2本は並列、
  その合計と帯が直列: 1/k = 1/k_帯 + 1/k_棒2本。
  これを入れる前は、目的3つがいずれもbridge_thicknessのほぼ一次従属に
  なっていて(実測: force-pain相関+0.99、thickness-inconspicuousness
  相関-1.00)、パレートフロントが3次元空間の1本の直線に退化していた
  (output/dilator/evolution.png)。leg_thicknessを含む3変数が目的に
  一切現れていなかったのが原因で、棒を直列バネにすることで、太さ・長さが
  拡張力に効くようになる
- **pain = 圧力 ∝ 拡張力 / 接触面積**。接触面積は「ブリッジが実際に
  鼻に触れている面の面積」。ブリッジは長方形断面のリボンで、鼻表面に
  接する面はその幅(bridge_width)側の広い面のため、接触面積は
  経路長(path_length)×bridge_widthで近似する(以前の円形断面時代は
  bridge_thicknessを使っていたが、リボンの接触面はwidth側のため変更)

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
bridge_width≈上限)。投影面積にすることで、bridge_width・leg_thickness・
collar_lengthが「太く/長くすれば拡張力は上がるが目立つ」という本来の
トレードオフとして効くようになる。
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
    build_paths,
    collar_clearance_margin,
    collar_position_margin,
    curvature_margin,
    leg_clearance_margin,
    lens_protrusion_margin,
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
    frame: FrameParams, actual_radius: float, path_length: float, rods: list[RodPath]
) -> float:
    """拡張力(機能性、最大化)の代理指標(バネ剛性×たわみ、基準の帯で
    剛性1に正規化)。モジュールdocstring「extension_force(拡張力)と
    pain(圧力)の構成」参照。extension_force・painの両方から参照される。
    """
    deflection = max(1 / actual_radius - 1 / frame.natural_radius, 0.0)
    bridge_stiffness = (
        frame.bridge_width * frame.bridge_thickness**3 / 12
    ) / path_length**3
    # 左右の棒は並列(2本で1つのバネ)、それが帯と直列につながる
    rods_stiffness = sum(_rod_stiffness(rod) for rod in rods)
    stiffness = 1 / (1 / bridge_stiffness + 1 / rods_stiffness)
    return stiffness / _REF_STIFFNESS * deflection


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
    extension_force: float  # 機能性: 鼻腔を広げる拡張力(基準の帯の剛性=1の相対値、最大化)
    pain: float  # 快適さ: 皮膚にかかる圧力(拡張力/接触面積、最小化)
    inconspicuousness: float  # 意匠性: 目立たなさ(-正面から見た投影面積mm^2、最大化)
    # 制約(10個。すべて0以下であるべき)
    curvature_margin: float  # natural_radiusが十分平らか(0以下であるべき)
    bridge_clearance_margin: float  # ブリッジのめり込み超過量(0以下であるべき)
    leg_clearance_margin: float  # 棒のめり込み超過量(0以下であるべき)
    collar_clearance_margin: float  # レンズのめり込み量(0以下であるべき)
    collar_position_margin: float  # レンズが鼻栓の範囲内か(左右のうち厳しい方、0以下であるべき)
    lens_protrusion_margin: float  # 棒がレンズからはみ出していないか(0以下であるべき)
    rod_thickness_margin: float  # 棒の最も細いところが印刷できる太さか(0以下であるべき)
    tab_fit_margin: float  # 嵌め込みのスロットが帯に収まるか(0以下であるべき)
    tab_thickness_margin: float  # タブの厚みが足りているか(0以下であるべき)
    tab_retention_margin: float  # 嵌め込みの返しが実際に引っかかるか(0以下であるべき)


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
        score.tab_fit_margin - _MARGIN_EPSILON,
        score.tab_thickness_margin - _MARGIN_EPSILON,
        score.tab_retention_margin - _MARGIN_EPSILON,
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
    bridge = bridge_points(body, params)
    actual_radius, path_length = bridge_curvature(bridge)

    _, left_rod, right_rod, left_collar, right_collar = build_paths(frame, plug, params, body)
    rods = [left_rod, right_rod]
    collars = [left_collar, right_collar]

    force = _extension_force(frame, actual_radius, path_length, rods)
    contact_area = path_length * frame.bridge_width

    return FrameScore(
        extension_force=force,
        pain=force / contact_area,
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
        tab_fit_margin=tab_fit_margin(frame, params),
        tab_thickness_margin=tab_thickness_margin(frame),
        tab_retention_margin=tab_retention_margin(frame),
    )
