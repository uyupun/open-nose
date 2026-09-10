"""フレームの仮形状(FrameParamsの6変数)。

アルファベット小文字の「b」をモチーフにした、片側1個の独立したクリップ
形状(issue: 「両鼻を同時に挟む」形状から「片方の鼻ごとに独立して使える」
形状への変更)。細いステム(stem_*、bのまっすぐな縦棒)を鼻孔の中で
鼻栓(ティッシュ等。PlugParamsはプレースホルダーとして実体を維持)に
突き刺し、その下端から続く太いリング(ring_*、bの丸い部分)が鼻孔の縁の
下をくぐって外側へ回り込み、鼻翼の外側の皮膚に押し当たる。鼻翼の薄い
壁が「鼻孔の内側にあるステム+鼻栓」と「外側にあるリング」の間に
挟まれることで保持される(実際の鼻ピアスのフープが鼻翼に掛かっている
のと同じ位置関係。ただし皮膚は貫通せず、クリップとして外側から押さえる
だけ)。

以前(issue #1〜#3)はメガネのように鼻中隔付近から左右対称に伸びる
アーム+自由に曲がるコネクタという構成だったが、左右が常に対で機能する
形状で、片方だけを取り外して使う用途に馴染まなかった。「b」字型は左右で
形状のロジックを共有しつつ(sideで鏡映するだけ)、1個ずつ独立して機能
するクリップになる。

## 幾何(座標系: x=左右、y=鼻先(0)→鼻筋、z=前後(前面が+))

「b」の文字はxy平面(z=鼻栓の軸の高さ、plug_model.plug_centerと同じ
nostril_depth_z)の上に描く。この平面は鼻栓の軸(y方向)を含み、鼻翼の
壁に対しておおよそ垂直なので、この平面内の円が鼻翼を「くぐって回り
込む」フープになる。

- **リング(ring_points)**: 実際の鼻ピアスのフープと同じく、フープの
  「上端」が鼻翼の外側の皮膚に掛かる。接触点は、高さ_RING_CONTACT_Y・
  鼻栓の軸の高さでx軸方向にレイを飛ばして実測した皮膚のx座標(skin_x)
  からframe.ring_depthだけ内側に押し込んだ点で、ここが円弧の終端。
  円の中心は終端から半径frame.ring_radius・角度phi_end(=180度-
  ring_gap_deg。中心から見た終端の方向)だけ戻った位置にあり、円弧は
  中心から見て内側(phi=180度、鼻孔の中にある「棒との接点」)から
  下端(270度、鼻孔の縁の下の空間)・外側(360度、鼻の横で皮膚より外に
  膨らむ部分)を経て終端(540度-ring_gap_deg)まで、(360-ring_gap_deg)度
  ぶん描く。残りの角度(内側上方=鼻翼の壁が上方へつながっている場所)が
  隙間。接触点を(横端ではなく)終端に置くことで、鼻翼が鼻先寄りほど
  広がっている分だけフープの横側が皮膚より外側へ膨らみ、鼻の横に
  フープが見える(以前、接触点を横端に置いたところフープ全体が鼻孔に
  隠れて見えなくなった)。
- **ステム(stem_points)**: リングの内側の接点(phi=180度、鼻孔の中)から
  鼻栓の軸方向(+y、鼻の奥)へframe.stem_lengthだけまっすぐ伸びる直線。
  円の内側の点では円弧の接線がちょうどy方向なので、リングの円弧は
  折れ目なくそのまま縦棒へつながる(「b」の丸が縦棒へ続く形)。棒を
  接点より下(鼻栓の露出面側)へ突き出させることは意図的にしない
  (以前、露出面より下まで棒を通したところ、棒の下端がリングから
  はみ出した「継ぎ足し」に見えた)。鼻栓の露出部分(鼻の下面より下)の
  中はリングの円弧自体(下端から接点へ立ち上がる区間)が通るため、
  鼻栓越しにフレームが鼻栓へ入って上へ抜ける様子は見える。x座標は
  リングの半径と隙間の角度から決まるため鼻栓の軸とは一般にずれるが、
  鼻栓の半径の内側に収まっていれば(stem_plug_margin)鼻栓に突き
  刺さっていることに変わりはない。

## 探索変数・ファイル内の並び順

FrameParamsの6変数: ring_radius/ring_gap_deg/ring_thickness/ring_depth
(リングの形状)、stem_length/stem_thickness(ステムの形状)。「リングは
太く、ステムは細く」というユーザー要望はthickness_order_marginで制約
として保証する(FrameParams.__post_init__のコメント参照)。

ファイル内の並び順: 定数・FrameParams → 経路の点列を計算する関数
(ring_points, stem_points, build_side_paths等) → メッシュ化・幾何
判定のユーティリティ(_tube_mesh, _signed_distance_to_body) →
validate_*(build_frame_pairが呼ぶ順) → build_frame_pair。

frameに依存する検証(thickness_order_margin/stem_plug_margin/
hoop_visibility_margin/ring_clearance_margin/stem_clearance_margin/
plug_insertion_margin/plug_overshoot_margin)は、例外を送出するvalidate_*(build_frame_pairの
メッシュ生成が使う)と、違反量を返すだけの*_margin(scripts/
evaluation.pyのevaluate_frameが制約として使う)の2種類を用意している。
frameは遺伝的アルゴリズムの探索変数なので、evaluate_frame側で例外を
送出すると不正な個体1つで評価ループ全体が止まってしまうため。一方、
frameに依存しない検証(validate_target_reach/validate_ring_height。
PlugParams/NoseParamsにしか依存せず、探索中は結果が変わらない)は
*_marginを用意せず、常に例外を送出する(問題設定そのものの誤りとして
扱う)。
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

# フレームのプレースホルダーの色(グレー、やや不透明寄り)。鼻本体
# (alpha=140)・鼻栓(commons.plug_model._PLUG_COLOR、alpha=80)より高い
# alphaにして、皮膚や鼻栓の中を通るステムがそれらの向こう側でも
# はっきり見えるようにする(commons.nose_model.build_nose_body参照)。
# 以前は140(鼻本体より低い値)だったが、ステムが鼻孔の中を通る設計に
# なってから皮膚越しにほぼ見えなくなった(実機で確認)ため引き上げた。
# OBJはalphaを保持できないため、この効果を確認するにはglTF(.glb)で
# 書き出す(export_model.py/export_frame.py参照)
_FRAME_COLOR = [90, 90, 100, 200]
# リングの終端(鼻翼の外側の皮膚に掛かる接触点)のy座標(鼻先=0からの
# 距離、mm)。固定値。鼻翼の中腹(鼻孔の縁より少し上)に置くことで、実際の
# 鼻ピアスのフープが鼻翼に掛かるのと同じ高さでリングが鼻翼を押さえる。
# リングの中心・下端はここから半径と隙間の角度で決まる(モジュール
# docstring「幾何」参照)。既定のNoseParamsで、鼻栓の軸の高さ(z)における
# この高さの鼻翼の皮膚が、レイキャストで実測できる(validate_ring_height)
# 範囲の値
_RING_CONTACT_Y = 2.0
# リングの円弧を近似する折れ線の分割数
_RING_SAMPLES = 32
# _skin_xがレイを飛ばし始める、鼻の外側の十分遠い位置(x座標の絶対値、mm)。
# 既定のNoseParamsの最大半幅(約18.6mm)より大きければよい
_SKIN_RAY_ORIGIN_X = 40.0
# フープの最外点(鼻から最も離れた点)が、その高さの鼻翼の皮膚より外側へ
# 最低どれだけ出ているべきか(mm)。「フープが鼻の横に見える」は本設計の
# 要件(以前、フープが鼻孔の中に隠れる形を作ったところ却下された)だが、
# retention(剛性∝1/半径^3)もfit_gap(皮膚への密着)も小さなフープを
# 有利にするため、目的だけに任せるとGAはフープを鼻孔に隠してしまう。
# 見えることは「わざと悪化させる理由がない」水準なので制約
# (hoop_visibility_margin)にする。線材が皮膚から離れて見える最小限の
# 目安として置いた暫定値
_MIN_HOOP_PROTRUSION = 1.5
# ステムが鼻栓に刺さっているべき最小の長さ(mm)。フレームは「リングが
# 鼻翼を挟む力」と「ステムが鼻栓(ティッシュ)を保持する力」の直列で
# 鼻栓を留めるが、後者は刺さり込みの長さが十分あれば律速にならない
# (ティッシュは軽く、摩擦で十分保持できる)ため、目的(retention)には
# 含めず、この最小長さを満たすことを制約(plug_insertion_margin)として
# 要求するだけにする(scripts/earrings/evaluation.pyのモジュールdocstring参照)。
# 既定のplug.length(12mm)の1/4程度で、ティッシュを串刺しにして
# 抜けない程度の目安として置いた暫定値
_MIN_PLUG_INSERTION = 3.0
# ステムが鼻栓に刺さって良い深さの上限を、plug.lengthに対する比率で
# 指定。これを超えて刺さると、ステムの先端が鼻栓を突き抜けて鼻の奥の
# 粘膜側まで達してしまう(plug_overshoot_margin参照)
_MAX_INSERTION_TO_PLUG_LENGTH = 0.9
# _tube_meshが使う円形断面ポリゴンの近似精度。shapelyのbufferのresolutionは
# 「1/4円あたりの分割数」なので、8を指定すると32角形になる
_TUBE_POLYGON_RESOLUTION = 8
# _signed_distance_to_bodyが疑似法線による符号判定を信頼する距離の上限
# (mm)。これを超える点は低速だが距離に依存せず正確なbody.contains()で
# 符号を求め直す(同関数のdocstring参照。旧設計から実測に基づく値を継承)
_PSEUDO_NORMAL_MAX_DISTANCE = 2.0

# 片側のリング経路・ステム経路の点列のペア(ring_points, stem_points)。
# build_side_pathsが返し、各種validate_*・build_frame_pair・
# scripts/earrings/evaluation.pyの間で共通の型として使う
SidePaths = tuple[list[np.ndarray], list[np.ndarray]]


@dataclass(frozen=True)
class FrameParams:
    """フレームの仮寸法パラメータ(単位: mmおよび度)。

    「b」字型(太いリング+細いステム)のクリップという単純なプレース
    ホルダーで、後から実際の造形(3Dプリント/粘土)に向けて調整・
    最適化する。
    """

    ring_radius: float = 4.0
    ring_gap_deg: float = 90.0
    ring_thickness: float = 1.4
    ring_depth: float = 0.8
    stem_length: float = 5.0
    stem_thickness: float = 1.2

    def __post_init__(self) -> None:
        if self.ring_radius <= 0:
            raise ValueError(f"ring_radius は正の値にすること: {self.ring_radius}")
        if not (0.0 <= self.ring_gap_deg < 360.0):
            raise ValueError(
                f"ring_gap_deg は[0, 360)の範囲にすること: {self.ring_gap_deg}"
            )
        if self.ring_thickness <= 0:
            raise ValueError(f"ring_thickness は正の値にすること: {self.ring_thickness}")
        if self.ring_depth < 0:
            raise ValueError(f"ring_depth は0以上にすること: {self.ring_depth}")
        if self.stem_length <= 0:
            raise ValueError(f"stem_length は正の値にすること: {self.stem_length}")
        if self.stem_thickness <= 0:
            raise ValueError(f"stem_thickness は正の値にすること: {self.stem_thickness}")
        # 「リングは太く、ステムは細く」という設計方針(ring_thickness>
        # stem_thickness)はここでは検証しない。探索範囲(_SEARCH_SPACE)は
        # ring_thickness/stem_thicknessそれぞれ独立した範囲を持つため、GAが
        # この関係を満たさない組み合わせを生成しうる。ここで例外を送出すると
        # FrameParamsの構築自体が失敗し、frameに依存する他の検証と違って
        # evaluate_frame側で制約として拾うことができない(モジュール
        # docstring参照)。そのため、この関係はthickness_order_margin
        # (frameに依存する制約、evaluate_frameが使う)/validate_thickness_
        # order(build_frame_pairが使う、例外を送出する版)側で扱う


def _skin_x(body: trimesh.Trimesh, y: float, z: float, side: Literal[-1, 1]) -> float | None:
    """(y, z)の高さで鼻の外側からx軸方向にレイを飛ばし、鼻翼の外側の皮膚に
    最初に当たる点のx座標を返す(当たらなければNone)。

    y・zを固定してxだけを実測するので、鼻本体メッシュの三角形分割の
    粗さの影響で値がジグザグすることがない(以前、最近接点+面法線で
    表面に追従させた際にジグザグに破綻した経緯がある)。
    """
    origin = np.array([[side * _SKIN_RAY_ORIGIN_X, y, z]])
    direction = np.array([[-side, 0.0, 0.0]])
    locations, _, _ = body.ray.intersects_location(origin, direction, multiple_hits=False)
    if len(locations) == 0:
        return None
    return float(locations[0, 0])


def ring_points(
    frame: FrameParams, params: NoseParams, body: trimesh.Trimesh, side: Literal[-1, 1]
) -> list[np.ndarray]:
    """鼻翼を外側から押さえるリングの経路(点列)を返す(points[0]が鼻翼の
    皮膚に掛かる終端=接触点、points[-1]が鼻孔の中にある内側の接点=
    ステムの接続点)。

    xy平面(z=鼻栓の軸の高さ)上の円弧。終端(接触点)は高さ_RING_CONTACT_Y
    の鼻翼の外側の皮膚(_skin_xで実測)からframe.ring_depthだけ内側に
    押し込んだ位置。中心から見た終端の方向がphi_end=180度-ring_gap_deg
    (ring_gap_deg=90度なら真上、小さいほど内側上方へ回り込む)になるよう
    中心を置き、円弧は内側の接点(phi=180度)から下端(270度)・外側(360度)
    を経て終端(540度-ring_gap_deg)まで、(360-ring_gap_deg)度ぶん描く。
    残りの角度(内側上方)が隙間で、そこを鼻翼の壁が上方へ通り抜ける
    (モジュールdocstring「幾何」参照)。点列は終端から接点へ向かう順に
    並べる(points[-1]がステムの始点と一致するように)。

    鼻本体メッシュを参照するのは接触点の位置決め(_skin_x、1点)だけで、
    円弧自体は解析的な円のまま(全周を表面に追従させると輪の内側の空間が
    なくなって鼻に張り付いて見える、という以前の問題を避けるため)。
    """
    z0 = nostril_depth_z(params.tip_depth_front)
    skin_x = _skin_x(body, _RING_CONTACT_Y, z0, side)
    if skin_x is None:
        raise ValueError(
            f"接触点の高さ(y={_RING_CONTACT_Y})・鼻栓の軸の高さ(z={z0:.2f})で"
            "鼻翼の皮膚が見つからない。_RING_CONTACT_Yを見直すこと"
        )
    end_x = abs(skin_x) - frame.ring_depth
    end_y = _RING_CONTACT_Y
    phi_end = np.radians(180.0 - frame.ring_gap_deg)
    center_x = end_x - frame.ring_radius * np.cos(phi_end)
    center_y = end_y - frame.ring_radius * np.sin(phi_end)

    # 終端(3*pi - gap ≡ 540度 - gap)から内側の接点(pi)へ遡る
    phis = np.linspace(3 * np.pi - np.radians(frame.ring_gap_deg), np.pi, _RING_SAMPLES)

    points = []
    for phi in phis:
        x = center_x + frame.ring_radius * np.cos(phi)
        y = center_y + frame.ring_radius * np.sin(phi)
        points.append(np.array([side * x, y, z0]))
    return points


def stem_points(
    frame: FrameParams,
    plug: PlugParams,
    params: NoseParams,
    ring_end: np.ndarray,
    side: Literal[-1, 1],
) -> list[np.ndarray]:
    """リングの内側の接点(ring_end、鼻孔の中)から鼻栓の軸方向(+y、鼻の奥)
    へframe.stem_lengthだけまっすぐ伸びる経路(点列、2点)を返す(path[0]が
    ring_end、path[-1]が上端=鼻の奥側の先端)。

    接点では円弧の接線がy方向なので、リングの円弧はここで折れ目なく
    ステムへつながる(モジュールdocstring「幾何」参照)。plug/params/side
    は現状未使用だが、鼻栓の位置に依存する調整(刺さり始めの位置など)を
    将来足せるよう、build_side_pathsと同じ引数を受け取っておく。

    向きを鼻栓の軸(plug_model.plug_outer_endのdocstring「yが負の向きが
    鼻先の外側方向」参照)に固定しているのは、「b」の縦棒がティッシュに
    突き刺さって見えるようにするため。以前は鼻の外側のリングから鼻栓の
    露出端へ斜めに向かう直線にしていたが、鼻栓の脇をかすめる向きに
    なって「刺さっている」ように見えなかった。
    """
    top = ring_end + np.array([0.0, frame.stem_length, 0.0])
    return [ring_end, top]


def build_side_paths(
    frame: FrameParams,
    plug: PlugParams,
    params: NoseParams,
    body: trimesh.Trimesh,
    side: Literal[-1, 1],
) -> SidePaths:
    """指定側のリング経路・ステム経路の点列を返す(メッシュ生成なし)。

    build_frame_pair・各種validate_*・scripts/earrings/evaluation.pyのいずれからも
    参照される。左右分をまとめて1度だけ計算し、呼び出し側で使い回す
    ことで、ring_points/stem_pointsの重複計算を避ける。bodyはring_points
    が鼻翼の皮膚の位置決め(_skin_x)に使う。呼び出し側がbuild_nose_body
    (params)で構築済みのものを渡す(重複構築を避けるため)。plugは
    stem_pointsがステムの下端(鼻栓の露出端基準)を決めるのに使う。
    """
    ring = ring_points(frame, params, body, side)
    stem = stem_points(frame, plug, params, ring[-1], side)
    return ring, stem


def ring_upper_points(ring: list[np.ndarray]) -> np.ndarray:
    """リングのうち上半分(yがリングのy範囲の中央より上)、つまり鼻の横で
    鼻翼の皮膚に沿って見える部分の点列を返す(該当なしなら空配列)。

    この部分は実際の鼻ピアスのフープが鼻翼の皮膚に沿って見える部分に
    相当し、evaluation.pyのfit_gap(皮膚からの浮き)の評価対象になる。
    下半分(鼻孔の縁の下の空間、鼻孔の中の接点まわり)は、皮膚から
    離れているのが正常なため対象外。中心のy座標をring_pointsから
    引き回さずy範囲の中央で代用しているのは、点列だけから判定できる
    方が呼び出し側(evaluation.py)が単純になるため。
    """
    arr = np.array(ring)
    mid_y = (arr[:, 1].min() + arr[:, 1].max()) / 2
    return arr[arr[:, 1] > mid_y]


def ring_contact_length(
    frame: FrameParams, ring: list[np.ndarray], body: trimesh.Trimesh
) -> float:
    """リングのうち実際に鼻の皮膚に触れている(チューブ表面が皮膚に達して
    いる)部分の弧長(mm)を返す。

    リングの中心線の各点について鼻本体メッシュまでの符号付き距離
    (_signed_distance_to_body)を求め、それがチューブの半径以下(=線材の
    表面が皮膚に達している、またはめり込んでいる)の点を「接触」とみなし、
    接触点の数×点の間隔(弧長/(点数-1))で長さにする。接触点が0の場合は
    0を返す(終端はring_depth>0で必ず皮膚の内側にあるため、通常は少なく
    とも1点は接触する)。

    scripts/earrings/evaluation.pyのpain(皮膚にかかる圧力の代理指標=挟み力/
    接触面積)が接触面積(接触長×線径)を求めるために使う。以前のように
    リングの弧長全体を接触面積の代理にすると、今の設計では大半が空中に
    浮いている円弧まで「押さえている」ことになり、GAが半径を大きくする
    ほど有利になる誤った圧力がかかっていた。
    """
    points = np.array(ring)
    signed = _signed_distance_to_body(body, points)
    contact = signed <= frame.ring_thickness / 2
    n_contact = int(contact.sum())
    if n_contact == 0:
        return 0.0
    arc_length = float(np.sum(np.linalg.norm(np.diff(points, axis=0), axis=1)))
    spacing = arc_length / (len(points) - 1)
    return n_contact * spacing


def _tube_mesh(points: list[np.ndarray], radius: float) -> trimesh.Trimesh:
    """点列を、半径radiusの円形断面で押し出した1本の連続チューブにする。

    trimesh.creation.sweep_polygonは円形ポリゴンを3D経路に沿って押し出し、
    各内部点でミター(斜め)継ぎの断面リングを共有する単一の連続メッシュを
    返す。始点・終点には自動でキャップが付く(sweep_polygonのcap引数、
    既定True)。
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
    距離)。

    この疑似法線による符号判定は、問い合わせ点が表面のごく近くにある
    前提でのみ信頼できる。距離が_PSEUDO_NORMAL_MAX_DISTANCEを超える点
    だけは body.contains()(レイキャストベースの厳密な内外判定。疑似法線
    と違い距離に依存せず正確だが、点ごとにレイを飛ばすため低速)で符号を
    求め直す(旧設計での実測に基づく閾値をそのまま継承)。

    closest_point(rtreeによる空間索引を使う高速版)を使う。総当たりの
    closest_point_naiveは、evaluate_frameを繰り返し呼び出す用途(GA)では
    支配的なボトルネックになることが実測で判明した(1回あたり約0.7秒)。
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
    検証する。

    鼻栓が鼻孔から露出していない(鼻の中に完全に埋まっている)設定では、
    ステムを刺す・鼻栓を交換するといった実際の使い方が成り立たない。
    問題設定そのものの妥当性確認としてbuild_frame_pair(メッシュ生成)・
    evaluate_frame(評価)の両方から共通で呼び出す。
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


def validate_ring_height(params: NoseParams, body: trimesh.Trimesh) -> None:
    """接触点の高さ(_RING_CONTACT_Y)・鼻栓の軸の高さ(z)で、左右とも
    鼻翼の皮膚がレイキャストで見つかることを検証する。

    _RING_CONTACT_Yは固定の定数で、FrameParamsのどの探索変数を動かしても
    結果は変わらないため、既定のNoseParamsでは常に満たされる。ただし
    鼻先の丸めが深い・鼻孔が下寄りなど別の鼻モデルではこの高さに皮膚が
    存在しない可能性があるため、build_frame_pair・evaluate_frameの
    両方から共通で呼び出して検証する。
    """
    z0 = nostril_depth_z(params.tip_depth_front)
    for side in (-1, 1):
        if _skin_x(body, _RING_CONTACT_Y, z0, side) is None:
            raise ValueError(
                f"接触点の高さ(y={_RING_CONTACT_Y})・鼻栓の軸の高さ"
                f"(z={z0:.2f})で鼻翼の皮膚が見つからない(side={side})。"
                "_RING_CONTACT_Yを見直すこと"
            )


def thickness_order_margin(frame: FrameParams) -> float:
    """「リングは太く、ステムは細く」という設計方針(ring_thickness>
    stem_thickness)への違反量を返す(正=違反量、0以下=安全)。

    探索範囲(_SEARCH_SPACE)はring_thickness/stem_thicknessそれぞれ独立
    した範囲を持つため、GAがこの関係を満たさない組み合わせ(ring_thickness
    <= stem_thickness)を生成しうる。FrameParams.__post_init__では検証
    せず、frameに依存する制約としてここで扱う(FrameParams.__post_init__
    のコメント参照)。
    """
    return frame.stem_thickness - frame.ring_thickness


def validate_thickness_order(frame: FrameParams) -> None:
    """thickness_order_marginが正(=違反)の場合に例外を送出する。

    build_frame_pair(メッシュ生成)から使う想定。evaluate_frame(評価)は
    frameに依存するこの検証を例外ではなく制約として扱うため、
    thickness_order_marginを直接使う。
    """
    margin = thickness_order_margin(frame)
    if margin >= 0:
        raise ValueError(
            f"ring_thickness({frame.ring_thickness})はstem_thickness"
            f"({frame.stem_thickness})より大きくすること(リングは太く、"
            "ステムは細くする方針のため)"
        )


def stem_plug_margin(
    frame: FrameParams, plug: PlugParams, params: NoseParams, sides: list[SidePaths]
) -> float:
    """ステム(チューブ表面まで含む)が鼻栓の円柱の内側に収まらずはみ出して
    いる量を返す(正=違反量、0以下=安全)。左右のうち最も厳しい側の値。

    ステムのx座標はリングの直径で決まる(モジュールdocstring「幾何」参照)
    ため、鼻栓の軸(x=nostril_gap/2)とは一般にずれる。ずれが鼻栓の半径から
    ステムの半径を引いた値を超えると、ステムが鼻栓の外(鼻孔の壁側)を
    通ることになり「鼻栓に刺さっている」状態でなくなる。frameに依存する
    (ring_radius/ring_depth/stem_thicknessの探索によって結果が変わる)ため、
    evaluate_frameは例外で止めずこの値を制約として使う。

    z方向は、リングの平面が鼻栓の軸の高さに固定されている(ring_points
    参照)ため常に一致し、検証不要。
    """
    plug_axis_x = params.nostril_gap / 2
    allowed = plug.diameter / 2 - frame.stem_thickness / 2
    worst = -np.inf
    for _, stem in sides:
        offset = abs(abs(stem[0][0]) - plug_axis_x)
        worst = max(worst, offset - allowed)
    return worst


def validate_stem_plug(
    frame: FrameParams, plug: PlugParams, params: NoseParams, sides: list[SidePaths]
) -> None:
    """stem_plug_marginが正(=違反)の場合に例外を送出する。"""
    margin = stem_plug_margin(frame, plug, params, sides)
    if margin > 0:
        raise ValueError(
            f"ステムが鼻栓の円柱から{margin:.3f}mmはみ出している(鼻栓に"
            "刺さっていない)。ring_radius/ring_depthを見直し、ステムのx座標"
            "(鼻翼の皮膚 - ring_depth - 2*ring_radius)が鼻栓の軸に近づくよう"
            "にすること"
        )


def hoop_visibility_margin(
    params: NoseParams, body: trimesh.Trimesh, sides: list[SidePaths]
) -> float:
    """フープの最外点が皮膚より外側へ出ている量が_MIN_HOOP_PROTRUSIONに
    足りない不足量を返す(正=違反量、0以下=十分見えている)。左右のうち
    最も厳しい側の値。

    最外点(|x|が最大のリング点)と同じ高さ(y)・鼻栓の軸の高さ(z)で
    鼻翼の皮膚のx座標を実測(_skin_x)し、その差を「皮膚からの突き出し」
    とする。その高さに皮膚が見つからない(最外点が鼻の下面より下にある)
    場合は、フープはその高さで鼻に隠れようがないため違反なしとする。
    frameに依存する(ring_radius/ring_gap_deg/ring_depthの探索によって
    最外点の位置が変わる)ため、evaluate_frameは例外で止めずこの値を
    制約として使う(_MIN_HOOP_PROTRUSIONのコメント参照)。
    """
    z0 = nostril_depth_z(params.tip_depth_front)
    worst = -np.inf
    for (ring, _), side in zip(sides, (-1, 1)):
        points = np.array(ring)
        outermost = points[np.argmax(np.abs(points[:, 0]))]
        skin_x = _skin_x(body, float(outermost[1]), z0, side)
        if skin_x is None:
            continue
        protrusion = abs(outermost[0]) - abs(skin_x)
        worst = max(worst, _MIN_HOOP_PROTRUSION - protrusion)
    return worst if worst > -np.inf else -_MIN_HOOP_PROTRUSION


def validate_hoop_visibility(
    params: NoseParams, body: trimesh.Trimesh, sides: list[SidePaths]
) -> None:
    """hoop_visibility_marginが正(=違反)の場合に例外を送出する。"""
    margin = hoop_visibility_margin(params, body, sides)
    if margin > 0:
        raise ValueError(
            f"フープの最外点の皮膚からの突き出しが{_MIN_HOOP_PROTRUSION}mmに"
            f"{margin:.3f}mm足りない(フープが鼻に隠れて見えない)。"
            "ring_radiusを大きくするかring_gap_degを見直すこと"
        )


def ring_clearance_margin(
    frame: FrameParams, sides: list[SidePaths], body: trimesh.Trimesh
) -> float:
    """リングの実際のチューブ表面が、意図しためり込み量を超えて鼻本体
    メッシュにめり込んでいないかを返す(正=超過量、0以下=安全)。左右の
    リング全区間のうち最も厳しい点の値。sidesはbuild_side_pathsで左右分を
    事前計算した(ring_points, stem_points)のリスト。frameに依存する
    (ring_radius/ring_gap_deg/ring_depth/ring_thicknessの探索によって
    結果が変わる)ため、evaluate_frameは例外で止めずこの値を制約として
    使う。build_frame_pair(メッシュ生成)は例外で止めたいので
    validate_ring_clearanceを使う。

    リングの接触点はframe.ring_depthだけ皮膚の内側へ意図的に押し込んで
    いる(クリップとして鼻翼を押さえる設計。モジュールdocstring参照)ため、
    断面の最も内側の頂点は、表面が平坦だと仮定した理論値でframe.
    ring_depth+radius(半径)分だけめり込むのが正常。この理論値を許容量と
    し、実測のめり込み量(_signed_distance_to_bodyが返す符号付き距離の
    負の値)がこれを超えた分だけを違反として検出する。円弧が鼻翼の壁を
    貫通する(隙間が狭すぎて内側上方の壁に突っ込む、下端が鼻の下面を
    くぐれず肉に埋まる等)ケースは、めり込み量が壁の厚みに達するため
    ここで検出される。
    """
    radius = frame.ring_thickness / 2
    allowed_embed = frame.ring_depth + radius
    worst = -np.inf
    for ring, _ in sides:
        tube = _tube_mesh(ring, radius)
        signed_distance = _signed_distance_to_body(body, tube.vertices)
        embed_amount = -signed_distance  # 正=めり込み量
        worst = max(worst, float((embed_amount - allowed_embed).max()))
    return worst


def validate_ring_clearance(
    frame: FrameParams, sides: list[SidePaths], body: trimesh.Trimesh
) -> None:
    """ring_clearance_marginが正(=違反)の場合に例外を送出する。"""
    margin = ring_clearance_margin(frame, sides, body)
    if margin > 0:
        raise ValueError(
            f"ring_thickness({frame.ring_thickness})のチューブが、意図した"
            f"めり込み量(ring_depth={frame.ring_depth})を超えて実際に鼻表面へ"
            f"めり込んでいる(超過量: {margin:.3f}mm)。ring_radius/"
            "ring_gap_degを見直し、円弧が鼻翼の壁を貫通しないようにすること"
        )


def stem_clearance_margin(
    sides: list[SidePaths], body: trimesh.Trimesh, stem_thickness: float
) -> float:
    """ステムの実際のチューブ表面が、鼻本体メッシュにめり込んでいないかを
    返す(正=めり込み量、0以下=安全)。左右のうち最も厳しい点の値。

    ステムは鼻孔(鼻本体メッシュから鼻孔の楕円体をくり抜いた空洞)の中を
    鼻栓の軸方向に伸びる想定なので、鼻本体メッシュとは非接触であるべき。
    ステムのx座標が鼻孔の壁に近い、または鼻孔の空洞の奥行きを超えて
    伸びる(stem_lengthが長すぎる)と壁や奥の肉にめり込む。
    ring_clearance_marginと同じ符号付き距離ベースの検証で検出する。
    """
    radius = stem_thickness / 2
    worst = -np.inf
    for _, stem in sides:
        tube = _tube_mesh(stem, radius)
        signed_distance = _signed_distance_to_body(body, tube.vertices)
        min_signed = float(signed_distance.min())
        worst = max(worst, -min_signed)
    return worst


def validate_stem_clearance(
    sides: list[SidePaths], body: trimesh.Trimesh, stem_thickness: float
) -> None:
    """stem_clearance_marginが正(=めり込み)の場合に例外を送出する。"""
    margin = stem_clearance_margin(sides, body, stem_thickness)
    if margin > 0:
        raise ValueError(
            f"stem_thickness({stem_thickness})のチューブが実際に鼻表面へ"
            f"めり込んでいる(最大めり込み量: {margin:.3f}mm)。ステムが鼻孔の"
            "壁や奥の肉と交差している可能性がある"
        )


def plug_insertion_depth(
    plug: PlugParams, params: NoseParams, stem: list[np.ndarray], side: Literal[-1, 1]
) -> float:
    """ステムが鼻栓(PlugParams)の内部に入り込んでいる長さを返す(mm。
    0以下は鼻栓と重なっていないことを意味する)。

    ステムは鼻栓の軸方向(+y)の直線なので、ステムのy区間と鼻栓のy区間
    (露出端plug_outer_endから鼻の奥へplug.length)の重なりの長さで
    表せる。retentionの計算(evaluate_frame)、および刺さり込み不足を
    検出する制約(plug_insertion_margin)の両方から参照される。
    """
    outer_y = plug_outer_end(plug, params.nostril_gap, params.tip_depth_front, side)[1]
    inner_y = outer_y + plug.length
    start_y, end_y = stem[0][1], stem[-1][1]
    return min(end_y, inner_y) - max(start_y, outer_y)


def plug_insertion_margin(
    plug: PlugParams, params: NoseParams, stem: list[np.ndarray], side: Literal[-1, 1]
) -> float:
    """ステムの鼻栓への刺さり込み(plug_insertion_depth)が_MIN_PLUG_
    INSERTIONに足りない不足量を返す(正=違反量、0以下=十分刺さっている)。
    """
    return _MIN_PLUG_INSERTION - plug_insertion_depth(plug, params, stem, side)


def plug_overshoot_margin(
    plug: PlugParams, params: NoseParams, stem: list[np.ndarray], side: Literal[-1, 1]
) -> float:
    """ステムの先端が、鼻栓の露出端からplug.length*_MAX_INSERTION_TO_
    PLUG_LENGTHより奥へ出ている量を返す(正=違反量、0以下=安全)。

    鼻栓(円柱)の長さを超えて刺さると、ステムの先端が鼻栓を突き抜けて
    鼻の奥の粘膜側まで達してしまう可能性がある。
    """
    outer_y = plug_outer_end(plug, params.nostril_gap, params.tip_depth_front, side)[1]
    limit_y = outer_y + plug.length * _MAX_INSERTION_TO_PLUG_LENGTH
    return stem[-1][1] - limit_y


def build_frame_pair(
    frame: FrameParams, plug: PlugParams, params: NoseParams
) -> tuple[trimesh.Trimesh, trimesh.Trimesh]:
    """左右のフレーム(リング+ステムの2部品からなるチューブ)を構築する
    (着色済み)。"""
    validate_target_reach(plug, params)
    body = build_nose_body(params)
    validate_ring_height(params, body)
    validate_thickness_order(frame)
    sides = [build_side_paths(frame, plug, params, body, side) for side in (-1, 1)]
    validate_stem_plug(frame, plug, params, sides)
    validate_hoop_visibility(params, body, sides)
    validate_ring_clearance(frame, sides, body)
    validate_stem_clearance(sides, body, frame.stem_thickness)
    for (_, stem), side in zip(sides, (-1, 1)):
        shortage = plug_insertion_margin(plug, params, stem, side)
        if shortage > 0:
            raise ValueError(
                f"ステムの鼻栓への刺さり込みが{_MIN_PLUG_INSERTION}mmに"
                f"{shortage:.3f}mm足りない。stem_lengthを大きくすること"
            )
        overshoot = plug_overshoot_margin(plug, params, stem, side)
        if overshoot > 0:
            raise ValueError(
                f"ステムが鼻栓を{overshoot:.3f}mm突き抜けている。stem_lengthを"
                "小さくすること"
            )

    ring_radius = frame.ring_thickness / 2
    stem_radius = frame.stem_thickness / 2

    meshes = []
    for ring, stem in sides:
        ring_mesh = _tube_mesh(ring, ring_radius)
        stem_mesh = _tube_mesh(stem, stem_radius)
        # 単純な連結(concatenate)ではなくブーリアン結合(manifold3d)で
        # 1つの閉じた立体にする。リングとステムは接点で重なっているため、
        # 連結のままだと2つの殻が重なった非多様体メッシュになり、3Dプリント
        # 用のSTL(export_frame.py --stl)としてスライサーが警告・誤解釈
        # しうる。_tube_meshが返すチューブは両端キャップ付きで閉じている
        # (実測でis_watertight)ため、結合結果も閉じた単一の立体になる
        combined = ring_mesh.union(stem_mesh, engine="manifold")
        combined.visual.face_colors = _FRAME_COLOR
        meshes.append(combined)

    return meshes[0], meshes[1]
