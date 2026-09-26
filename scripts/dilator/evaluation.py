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
実測の相関はextension_force-plug_hold −0.25、extension_force-
inconspicuousness +0.07、plug_hold-inconspicuousness −0.64で、3つとも
独立した軸として働いている(最後の組は、太い棒ほど硬いが目立つという
トレードオフそのもの)。

**制約(16個。FrameScore参照。すべて0以下であるべき)**

探索範囲(dilator/optimize._SEARCH_SPACE)からランダムに400件を評価した
ときの違反率(=GAの探索で実際に効いている度合い):

- 形が成立するかを決める、実際に効く制約: rod_thickness_margin 51.5%・
  skin_pressure_margin 34.2%・clip_skin_margin 33.8%・clip_strain_margin
  26.8%・clip_retention_margin 23.5%・joint_access_margin 20.2%・
  clip_fit_margin 6.2%・rod_kink_margin 1.8%
- 安全網(この探索範囲では違反しないが、幾何の作り方を変えたときに
  退行を検出する): curvature_margin・bridge_clearance_margin・
  leg_clearance_margin・collar_clearance_margin・collar_position_margin・
  lens_protrusion_margin・blade_twist_margin・tape_area_margin。この種の
  制約は過去の改修で実際に「棒がレンズの穴を塞ぐ」「棒が0.4mmまで潰れる」
  といった退行を捕まえている。leg_clearance(以前21%)とblade_twist(以前
  30%)は、棒の経路を平滑化し、板のねじれを回転最小化フレームで均等に
  配るようにしてから違反しなくなった(鼻から離す補正と平滑化を交互に
  かけるので食い込まず、ねじれは経路の曲がりの分だけ少なくて済む)

連結部をエッジクリップに変えたのに伴い、矢じりタブ用の3つ(tab_fit・
tab_thickness・tab_retention)をクリップ用の3つ(clip_fit・clip_strain・
clip_retention)に置き換え、クリップの内側の縁が肌に食い込む深さを見る
clip_skin_marginを加えた。

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
- **印刷する形が自然な形**。この式は、帯を曲率半径natural_radiusの形で
  印刷し(frame_model.build_bridge_print_piece)、装着時に鼻の上の円弧
  (actual_radius)まで曲げることが前提。装着した形のまま印刷すると
  たわみが0になり、この拡張力は出ない
- **skin_pressure(面圧、制約)= 拡張力 / 貼り代の面積**。テープを貼る
  面(frame_model.tape_pad_area、帯の両端のうち肌から_TAPE_MAX_GAP以内の
  区間)にかかる面圧。帯を一定の曲率の円弧にして(両端を鼻の角に沿って
  丸めるのをやめて)からは、貼り代が両端の2〜3mmに縮んだため、この制約が
  最もよく効く(探索範囲の一様サンプルで約8割が違反)。
  上限(_MAX_SKIN_PRESSURE)を超えると、痛みの前にテープが剥がれて力が
  肌へ伝わらない。以前はこれをpainとして目的にしていたが、拡張力・
  接触面積がどちらもbridge_widthに比例して約分され、実質extension_force
  の定数倍(相関+0.99)にしかならなかったため、制約へ移した

## plug_hold(鼻栓の保持剛性)の構成

plug_hold = 左右の棒を「クリップ側が固定端・リングの中心が荷重点」の
3次元の曲がり梁とみなし、リングをいちばんたわみやすい向き(x・y・zの
うち最悪)に押したときのバネ定数の合計(_plug_hold・_rod_stiffness)。
カスティリアノの定理で、各点の曲げモーメントを断面の幅の向き・厚みの
向き・経路の向きに分解して積分する:

    δ/P = ∫ [ M_w²/I_w + M_t²/I_t + M_s²/(G/E·J) ] ds

棒は平たいブレードで、経路に沿ってねじれる(アーチの面→リングの面)。
以前は全長を弱軸だけで測っていたため、ねじれて強い向きで受けている
区間の剛性を捨てていた(実測: 同じ形で3.8→16.1、ただしこれはy方向だけの
値で、最悪の向きで測ると8〜12程度)。3次元で分解すると、どこでどちら向きに
ねじるかがそのまま保持剛性に効く。

棒が柔らかいとリングが振られて鼻栓がぐらつく。太い棒ほど高いが、
そのぶん目立つ(inconspicuousness)ので、leg_thicknessと装着位置
(bridge_y、棒の長さを決める)に本質的なトレードオフができる。実測の
相関はleg_thickness +0.92、bridge_y -0.57。

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
bridge_width≈上限)。棒は平たいブレードとして、各区間の断面を正面から見た向きへ射影した
見かけの幅で測り、リングは鼻中隔側を開いたC字の分だけ細く、連結部の
クリップの影(clip_frontal_area)も加える(以前はブレードを丸棒、リングを
閉じた輪として数え、クリップは数えていなかった。実測で片側あたり
クリップ20mm^2・リングの開口-4.7mm^2の差)。

投影面積にすることで、bridge_width(実測相関-0.36)・
leg_thickness(-0.84)・bridge_y(-0.18、高い位置ほど棒が長くなる)が
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
    _BLADE_ASPECT,
    _OPEN_RING_GAP_DEG,
    CollarGeometry,
    TabFrame,
    _blade_frames,
    clip_frontal_area,
    clip_skin_margin,
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
    blade_twist_margin,
    rod_kink_margin,
    rod_thickness_margin,
    clip_fit_margin,
    clip_retention_margin,
    clip_strain_margin,
    validate_collar_no_overlap,
    validate_target_reach,
)

# バネ剛性の正規化に使う基準値(mm)。剛性は「断面二次モーメント/長さ^3」
# (ヤング率Eは共通なので約分される)で測り、この基準の帯の剛性を1とする
# (earrings.evaluationの_REF_RING_LENGTHと同じ考え方)
_REF_BRIDGE_WIDTH = 6.0
_REF_BRIDGE_THICKNESS = 1.0
_REF_BRIDGE_LENGTH = 23.5
# ねじりの剛性に使う、せん断弾性率とヤング率の比(G/E=1/(2(1+ν))、
# 樹脂のポアソン比ν≈0.35)
_SHEAR_RATIO = 1 / 2.7
_REF_STIFFNESS = (
    _REF_BRIDGE_WIDTH * _REF_BRIDGE_THICKNESS**3 / 12
) / _REF_BRIDGE_LENGTH**3
# 貼り代にかかってよい面圧の上限(extension_forceと同じ正規化での値を
# 面積mm^2で割ったもの)。これを超えると、痛い前に両面テープが剥がれて
# 拡張力が肌へ伝わらない(どちらも同じ面圧で決まるので1つの制約にして
# いる)。探索範囲の中で実際に効く(=硬すぎる帯を弾く)水準に置いた
# 暫定値で、テープの実物の保持力(N/cm^2)で置き換える前提
_MAX_SKIN_PRESSURE = 0.0015


def _rod_stiffness(rod: RodPath, tab: TabFrame, collar: CollarGeometry) -> float:
    """片側の棒(ブレード)で、リングをいちばんたわみやすい向きに押したときの
    バネ定数(E=1、単位mm)を返す。

    棒を、クリップ側を固定端・リングの中心を荷重点とする3次元の曲がり梁と
    みなし、カスティリアノの定理でたわみを求めてその逆数を取る:

        δ/P = ∫ [ M_w²/I_w + M_t²/I_t + M_s²/(G/E·J) ] ds

    Mは各点での曲げモーメント(= 荷重点までの腕 × 荷重の向き)で、断面の
    幅の向き(w)・厚みの向き(t)・経路の向き(s)に分解する。ブレードの断面は
    角丸長方形(幅=radii*2、厚み=幅/_BLADE_ASPECT)なので
    I_w=幅·厚み³/12(弱い)、I_t=厚み·幅³/12(強い)、ねじりはJ≈幅·厚み³/3。

    以前は全長を弱軸のI_wだけで測っていた。ブレードは経路に沿ってねじれ、
    場所によっては荷重に対して幅の向き(強い向き)で受けるので、実際より
    弱く見積もっていたうえ、「どこでどちら向きにねじるか」が剛性にどう
    効くかを評価できていなかった。3次元で分解すれば、ねじれの造形がそのまま
    保持剛性に反映される。

    荷重の向きはx・y・zの3通りを試し、いちばんたわむ(=いちばん弱い)向きの
    値を返す。鼻栓の軸の向き(y)だけで押すと、縦に降りる棒の区間はほぼ
    引っ張り・圧縮で受けて曲がらないため、棒の長さ(装着位置bridge_y)が
    剛性に効かなくなった(実測: 相関-0.74→-0.08)。リングは鼻栓の出し入れ
    だけでなく、顔に触れたときなど横からも押されるので、最も弱い向きで
    評価する。
    """
    points, radii = rod.points, rod.radii
    _, wide, thick = _blade_frames(
        points, np.asarray(tab.u, dtype=float), np.array([0.0, 1.0, 0.0])
    )
    segments = np.diff(points, axis=0)
    lengths = np.linalg.norm(segments, axis=1)
    tangents = segments / np.maximum(lengths[:, None], 1e-9)
    middles = (points[:-1] + points[1:]) / 2
    width = (radii[:-1] + radii[1:])
    thickness = width / _BLADE_ASPECT
    i_weak = width * thickness**3 / 12
    i_strong = thickness * width**3 / 12
    torsion = width * thickness**3 / 3
    load_point = np.array(
        [collar.center_x, (collar.y_start + collar.y_end) / 2, collar.center_z]
    )
    w_mid = (wide[:-1] + wide[1:]) / 2
    t_mid = (thick[:-1] + thick[1:]) / 2
    worst = 0.0
    for load in np.eye(3):
        moment = np.cross(load_point - middles, load)
        compliance = np.sum(
            (
                np.einsum("ij,ij->i", moment, w_mid) ** 2 / i_weak
                + np.einsum("ij,ij->i", moment, t_mid) ** 2 / i_strong
                + np.einsum("ij,ij->i", moment, tangents) ** 2
                / (_SHEAR_RATIO * torsion)
            )
            * lengths
        )
        worst = max(worst, float(compliance))
    return 1.0 / worst if worst > 0 else np.inf


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


def _plug_hold(
    rods: list[RodPath], tabs: list[TabFrame], collars: list[CollarGeometry]
) -> float:
    """鼻栓の保持剛性(機能性、最大化)。左右の棒を、タブ側を固定端・
    レンズ側を荷重点とする片持ち梁とみなしたときのバネ定数の合計
    (基準の帯の剛性=1で正規化)。

    棒が柔らかいとレンズが振られ、差した鼻栓がぐらついて抜けやすい。
    太く短い棒ほど高いが、そのぶん目立つ(inconspicuousness)ため、
    leg_thicknessと装着位置(bridge_y、棒の長さを決める)に本質的な
    トレードオフを作る。
    """
    return (
        sum(
            _rod_stiffness(rod, tab, collar)
            for rod, tab, collar in zip(rods, tabs, collars)
        )
        / _REF_STIFFNESS
    )


def _visible_area(
    frame: FrameParams,
    bridge: list[np.ndarray],
    rods: list[RodPath],
    tabs: list[TabFrame],
    collars: list[CollarGeometry],
) -> float:
    """フレームを顔の正面(x-y平面)から見たときの投影面積(mm^2)を返す。

    モジュールdocstring「inconspicuousness(目立たなさ)の構成」参照。
    部品ごとの影の面積を単純に足す(重なりは無視する近似):

    - ブリッジ: 正面から見た経路長 × 帯の幅
    - 棒(ブレード): 各区間の正面から見た長さ × その区間の見かけの幅。
      見かけの幅は、断面(幅・厚み)を正面から見た経路に垂直な向きへ射影した
      長さで、ブレードが正面を向いてねじれている区間ほど太く見える
    - リング: 筒を正面から見た長方形。鼻中隔側を_OPEN_RING_GAP_DEGだけ
      開いたC字なので、横幅は外径×(1+cos(開口/2))
    - クリップ: 帯の下縁を挟む箱(clip_frontal_area)
    """
    points = np.array(bridge)
    area = float(np.sum(np.linalg.norm(np.diff(points[:, :2], axis=0), axis=1)))
    area *= frame.bridge_width
    for rod, tab in zip(rods, tabs):
        _, wide, thick = _blade_frames(
            rod.points, np.asarray(tab.u, dtype=float), np.array([0.0, 1.0, 0.0])
        )
        step = np.diff(rod.points[:, :2], axis=0)
        length = np.linalg.norm(step, axis=1)
        across = np.stack([-step[:, 1], step[:, 0], np.zeros(len(step))], axis=1)
        across /= np.maximum(length[:, None], 1e-9)
        half_width = (rod.radii[:-1] + rod.radii[1:]) / 2
        apparent = 2 * half_width * np.abs(np.einsum("ij,ij->i", wide[:-1], across)) + (
            2 * half_width / _BLADE_ASPECT
        ) * np.abs(np.einsum("ij,ij->i", thick[:-1], across))
        area += float(np.sum(length * apparent))
        area += clip_frontal_area(tab, frame)
    open_half = np.radians(_OPEN_RING_GAP_DEG) / 2
    for collar in collars:
        area += collar.r_outer * (1 + np.cos(open_half)) * (collar.y_end - collar.y_start)
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
    # 制約(16個。すべて0以下であるべき)
    curvature_margin: float  # natural_radiusが十分平らか(0以下であるべき)
    bridge_clearance_margin: float  # ブリッジのめり込み超過量(0以下であるべき)
    leg_clearance_margin: float  # 棒のめり込み超過量(0以下であるべき)
    collar_clearance_margin: float  # レンズのめり込み量(0以下であるべき)
    collar_position_margin: float  # レンズが鼻栓の範囲内か(左右のうち厳しい方、0以下であるべき)
    lens_protrusion_margin: float  # 棒がレンズからはみ出していないか(0以下であるべき)
    rod_thickness_margin: float  # 棒の最も細いところが印刷できる太さか(0以下であるべき)
    rod_kink_margin: float  # 棒の曲がりが急すぎて自己交差していないか(0以下であるべき)
    blade_twist_margin: float  # ブレードのねじれが急すぎないか(0以下であるべき)
    clip_fit_margin: float  # クリップと帯の穴が帯に収まるか(0以下であるべき)
    clip_strain_margin: float  # 着脱時にクリップの顎が折れないか(0以下であるべき)
    clip_retention_margin: float  # クリップの突起が帯の穴に十分かかるか(0以下であるべき)
    clip_skin_margin: float  # クリップが肌に食い込みすぎないか(0以下であるべき)
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
        score.blade_twist_margin - _MARGIN_EPSILON,
        score.clip_fit_margin - _MARGIN_EPSILON,
        score.clip_strain_margin - _MARGIN_EPSILON,
        score.clip_retention_margin - _MARGIN_EPSILON,
        score.clip_skin_margin - _MARGIN_EPSILON,
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

    _, left_rod, right_rod, left_collar, right_collar, left_tab, right_tab = (
        build_paths(frame, plug, params, body)
    )
    rods = [left_rod, right_rod]
    collars = [left_collar, right_collar]
    tabs = [left_tab, right_tab]

    force = _extension_force(frame, params, actual_radius, path_length)
    pad_area = tape_pad_area(frame, params)

    return FrameScore(
        extension_force=force,
        plug_hold=_plug_hold(rods, tabs, collars),
        inconspicuousness=-_visible_area(frame, bridge, rods, tabs, collars),
        curvature_margin=curvature_margin(frame, bridge),
        bridge_clearance_margin=bridge_clearance_margin(frame, params, body),
        leg_clearance_margin=leg_clearance_margin(rods, tabs, body),
        collar_clearance_margin=collar_clearance_margin(collars, body),
        collar_position_margin=max(
            collar_position_margin(plug, params, left_collar, -1),
            collar_position_margin(plug, params, right_collar, 1),
        ),
        lens_protrusion_margin=lens_protrusion_margin(rods, collars),
        rod_thickness_margin=rod_thickness_margin(rods),
        rod_kink_margin=rod_kink_margin(rods),
        blade_twist_margin=blade_twist_margin(rods, tabs),
        clip_fit_margin=clip_fit_margin(frame, params),
        clip_strain_margin=clip_strain_margin(frame),
        clip_retention_margin=clip_retention_margin(frame),
        clip_skin_margin=clip_skin_margin(frame, tabs, body),
        skin_pressure_margin=force / pad_area - _MAX_SKIN_PRESSURE,
        tape_area_margin=tape_area_margin(frame, params),
        joint_access_margin=joint_access_margin(frame, params, body),
    )
