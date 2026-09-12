"""フレームの仮形状(FrameParamsの6変数)。

アルファベット小文字の「b」をモチーフにした、片側1個の独立したクリップ
形状(issue: 「両鼻を同時に挟む」形状から「片方の鼻ごとに独立して使える」
形状への変更)。太いリング(ring_*、bの丸い部分)の上端が鼻翼の外側の
皮膚に掛かり、鼻の横に張り出しながら鼻の下(鼻栓の露出面より下の空間)へ
回り込み、そこで小さく曲がって細いステム(stem_*、bのまっすぐな縦棒)へ
連続する。ステムは鼻栓(ティッシュ等。PlugParamsはプレースホルダーとして
実体を維持)の軸に沿って、その下部から真っ直ぐ上へ突き刺さる(実際の
フックピアスがフープの片端を刺し込む位置関係)。鼻翼の薄い壁が「外側の
リング」と「鼻孔の中のステム+鼻栓」の間に挟まれることで保持される
(ただし皮膚は貫通せず、クリップとして外側から押さえるだけ)。

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
  からframe.ring_depthだけ内側に押し込んだ点で、ここが経路の始点。
  大きな円弧(半径frame.ring_radius)が、中心から見た始点の方向phi_end
  (=180度-ring_gap_deg。90度なら真上)から外側(360度、鼻の横で皮膚より
  外に膨らむ部分)を経て下端(270度)まで回り込み、そこから鼻の下(鼻栓の
  露出面より下の空間)を内側へ直線で進み、半径_FILLET_RADIUSの小さな
  曲げで上向きに変わって鼻栓の軸(x=nostril_gap/2)の真下に達する。
  上方の残りの角度(内側上方=鼻翼の壁が上方へつながっている場所)が
  隙間。接触点を(横端ではなく)円弧の始点に置くことで、フープの横側が
  皮膚より外側へ膨らみ、鼻の横にフープが見える。
- **ステム(stem_points)**: 小さな曲げの終わり(鼻栓の軸の真下、露出面
  より下)から鼻栓の軸に沿ってframe.stem_lengthだけ真上(+y、鼻の奥)へ
  伸びる直線。鼻栓の下部から軸に沿って真っ直ぐ刺さる(ユーザーの
  スケッチ「大きな丸→鼻の下を通る→小さく曲がって縦棒→鼻栓の下から
  刺さる」を再現したもの)。フックが軸まで届くこと(hook_reach_margin)と
  始点が露出面より下にあること(stem_entry_margin)は制約として要求する。

## 探索変数・ファイル内の並び順

FrameParamsの6変数: ring_radius/ring_gap_deg/ring_thickness/ring_depth
(リングの形状)、stem_length/stem_thickness(ステムの形状)。「リングは
太く、ステムは細く」というユーザー要望はthickness_order_marginで制約
として保証する(FrameParams.__post_init__のコメント参照)。

ファイル内の並び順: 定数・FrameParams → 経路の点列を計算する関数
(ring_points, stem_points, build_side_paths等) → メッシュ化・幾何
判定のユーティリティ(_tube_mesh, _signed_distance_to_body) →
validate_*(build_frame_pairが呼ぶ順) → build_frame_pair。

frameに依存する検証(thickness_order_margin/hook_reach_margin/
stem_entry_margin/hoop_visibility_margin/ring_clearance_margin/
stem_clearance_margin/plug_insertion_margin/plug_overshoot_margin)は、
例外を送出するvalidate_*(build_frame_pairのメッシュ生成が使う)と、
違反量を返すだけの*_margin(scripts/earrings/evaluation.pyの
evaluate_frameが制約として使う)の2種類を用意している。
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
# 距離、mm)。固定値。鼻翼の中腹に置くことで、実際の鼻ピアスのフープが
# 鼻翼に掛かるのと同じ高さでリングが鼻翼を押さえる。以前は2.0(鼻孔の
# 縁のすぐ上)だったが、それだとリング全体が鼻栓の周りの低い位置に
# 収まってしまい「リングが鼻翼まで届かない」「鼻ピアスらしく見えない」
# という指摘を受けたため、鼻翼の隆起(commons.nose_model._ALAE_BUMP_SPAN
# ≈7mm)の中ほどまで上げた。リングの中心・下端はここから半径と隙間の
# 角度で決まる(モジュールdocstring「幾何」参照)ため、下端が鼻孔の縁の
# 下(鼻の下面≈-4.35mm)まで抜けるには半径が約4.5mm以上必要になる。
# 既定のNoseParamsで、鼻栓の軸の高さ(z)におけるこの高さの鼻翼の皮膚が、
# レイキャストで実測できる(validate_ring_height)範囲の値
_RING_CONTACT_Y = 4.0
# リングの円弧を近似する折れ線の分割数
_RING_SAMPLES = 32
# _skin_xがレイを飛ばし始める、鼻の外側の十分遠い位置(x座標の絶対値、mm)。
# 既定のNoseParamsの最大半幅(約18.6mm)より大きければよい
_SKIN_RAY_ORIGIN_X = 40.0
# フックの下端で向きを内側→上へ変える小さな曲げの半径(mm)と、その四分円を
# 近似する点数。曲げが小さいほど「大きな丸+まっすぐな棒」というbの形が
# はっきりするが、線材(ring_thickness最大2.5mm)を折り返せる程度の半径は
# 必要。ユーザーのスケッチの小さな曲げに合わせた暫定値
_FILLET_RADIUS = 1.5
_FILLET_SAMPLES = 6
# フープの最外点(鼻から最も離れた点)が、その高さの鼻翼の皮膚より外側へ
# 最低どれだけ出ているべきか(mm)。「フープが鼻の横に見える」は本設計の
# 要件(以前、フープが鼻孔の中に隠れる形を作ったところ却下された)。
# 突き出し量(hoop_protrusion)はscripts/earrings/evaluation.pyで意匠性の
# 目的(visibility、最大化)にもなっているが、retention(剛性∝1/半径^3)が
# 小さなフープを有利にするため、パレートフロントの保持力側の端では
# フープが鼻孔に隠れうる。見えることは「わざと悪化させる理由がない」
# 水準なので、最低限の突き出しは制約(hoop_visibility_margin)としても
# 要求する。線材が皮膚から離れて見える最小限の目安として置いた暫定値
_MIN_HOOP_PROTRUSION = 1.5
# リングのチューブ表面が鼻本体メッシュへめり込んでよい上限を、線径
# (frame.ring_thickness/2)に対する比率で指定。ring_clearance_marginが
# 使う。ユーザー指摘(候補glbのスクリーンショット: 「まだ鼻にめり込んで
# ますよね。もっと隙間を開けるように」)を受けて、以前の許容量(frame.
# ring_depth+半径。ring_depthで狙った分だけなら常に合格してしまう、
# 事実上無効な閾値だった)を実測ベースの値に置き換えた。
#
# 固定mm値(隙間を要求する側)にしなかったのは、実測(_tube_mesh頂点)で
# ring_depth=0(押し込みなし)でもチューブの円形断面と鼻翼の曲面が
# 完全には一致せず、線径にほぼ比例した残留めり込み(半径の0.34〜0.38倍
# 程度)が避けられないと判明したため。0.3mmのような固定の隙間を要求すると
# 太い線材(radius>0.8mm程度)では常にring_depthを大きく負にする(接触点を
# 皮膚からmm単位で引き離す)しかなくなり、retention(たわみ=ring_depthに
# 比例)がほぼ常に0にクランプされてしまい、保持力のトレードオフ自体が
# 意味をなさなくなる(実測で確認)。半径に比例する値なら、押し込みなし
# (ring_depth=0)での残留めり込みとほぼ同じ水準を上限にでき、線材の
# 太さによらず「ring_depthによる意図的な押し込みが、幾何近似で元々
# 避けられない分を超えて増やさない」という一貫した基準になる。
#
# 比率は0.4だと可行域が線径ごとにほぼ一点(ring_depthの幅0.03〜0.15mm
# 程度)に潰れ、GA(pop=20,gen=10のスモークテスト)がその狭い尾根を
# 見つけられず、全個体がretention=0(ring_depth<=0)に収束してしまった。
# 実測では線径が太いほどめり込み量がring_depthに対してほぼ一定値
# (0.6〜0.7mm)で頭打ちになるため、許容量がこの頭打ち値を超えると太い
# 線材でring_depthが事実上無制限になり、ユーザー指摘の候補を再び許して
# しまう。0.5はこの頭打ちより明確に低く(ユーザー指摘の候補は依然として
# 違反する)、かつ0.4よりは探索できる幅(線径ごとに0.05〜0.2mm程度)が
# 広い妥協点として選んだ
_RING_EMBED_RATIO = 0.5
# リングの接触点(_hook.end_x)を、_skin_x実測値からring_depthで押し込む前に
# あらかじめ外側へ逃がしておく固定オフセット(mm)。build_frame_pairが
# ring_meshの見た目の仕上げに使う丸い先端(_tube_meshのround_start=True。
# ユーザー要望「リングの先端は丸みを帯びてほしい」)は、経路方向にも
# 張り出す球であるため、ring_clearance_marginが検証する平らなキャップより
# 実際にはさらにめり込む。この余分なめり込みは実測でring_radius/
# ring_gap_deg/ring_depth/ring_thicknessをどう変えてもほぼ一定(0.6〜
# 0.7mm程度、_tube_meshのdocstring参照)だったため、ring_depthではなく
# この固定オフセットで打ち消す(実測でoffset=0.8mm程度から丸いキャップの
# めり込みがほぼ0まで下がることを確認した)。ring_depthはこのオフセット
# より後で適用される(_hook参照)ため、ring_depthによる意図的な押し込みの
# トレードオフ自体には影響しない
_ROUND_CAP_OFFSET = 0.8
# フックの大きな円弧の終点(_Hook.bottom_x)から、鼻栓の軸を回り込む
# 曲げの中心(axis_x+_FILLET_RADIUS)までの直線区間(_Hook.run_length、
# リングと鼻栓を刺すステムの間の空間)が最低どれだけ必要か(mm)。
# 0(hook_reach_margin)だけを要求すると、円弧が鼻栓の軸ぎりぎりまで
# 回り込み、リングの丸い部分とステムがほとんど隙間なく隣り合う、
# 窮屈な見た目になる(ユーザー指摘: 「リングと棒の隙間が狭い」)。
# ステムが単独の棒として視認できる最小限の目安として置いた暫定値
_MIN_HOOK_GAP = 3.0
# ステムが鼻栓に刺さっているべき最小の長さを、plug.lengthに対する比率で
# 指定。フレームは「リングが鼻翼を挟む力」と「ステムが鼻栓(ティッシュ)を
# 保持する力」の直列で鼻栓を留めるが、後者は刺さり込みの長さが十分
# あれば律速にならない(ティッシュは軽く、摩擦で十分保持できる)ため、
# 目的(retention)には含めず、この最小長さを満たすことを制約
# (plug_insertion_margin)として要求するだけにする(scripts/earrings/
# evaluation.pyのモジュールdocstring参照)。以前は固定3mm(既定の
# plug.length=12mmの1/4)だったが、GAの結果でステムが短い個体ばかりに
# なり「鼻栓を刺す部分が短い」という指摘を受けたため、鼻栓の大半を
# 貫く0.6(既定で7.2mm)に引き上げた。_MAX_INSERTION_TO_PLUG_LENGTH(0.9)
# との間が、stem_lengthの実質的な可動域になる
_MIN_INSERTION_TO_PLUG_LENGTH = 0.6
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
# ring_depthが取りうる負の値の下限の絶対値(mm)。ring_depthは本来「接触点を
# 皮膚からどれだけ内側へ押し込むか」だが、ring_clearance_marginを線径に
# 比例した実測ベースの閾値(_RING_EMBED_RATIO)に変更したことで、押し込み
# 量0でも許容量を超える(線径が太い)個体では、GAが接触点を皮膚より
# 外側へ引く(ring_depthを負にする)必要が生じうる。無制限に負にできると
# 「鼻から完全に浮いた輪」まで許してしまうため、実測で確認した必要な
# 引き量(最大でも1mm弱、_RING_EMBED_RATIOのコメント参照)を十分に
# 相殺できる範囲の緩い上限として1.0を置いた
_RING_DEPTH_MIN = 1.0

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

    ring_radius: float = 7.5
    ring_gap_deg: float = 80.0
    ring_thickness: float = 1.4
    ring_depth: float = 0.15
    stem_length: float = 10.0
    stem_thickness: float = 1.3

    def __post_init__(self) -> None:
        if self.ring_radius <= 0:
            raise ValueError(f"ring_radius は正の値にすること: {self.ring_radius}")
        if not (0.0 <= self.ring_gap_deg < 360.0):
            raise ValueError(
                f"ring_gap_deg は[0, 360)の範囲にすること: {self.ring_gap_deg}"
            )
        if self.ring_thickness <= 0:
            raise ValueError(f"ring_thickness は正の値にすること: {self.ring_thickness}")
        if self.ring_depth < -_RING_DEPTH_MIN:
            raise ValueError(
                f"ring_depth は{-_RING_DEPTH_MIN}以上にすること: {self.ring_depth}"
            )
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


@dataclass(frozen=True)
class _Hook:
    """フック(リング+ステム)の幾何の中間量(片側、x座標は正の正準値)。

    ring_points/stem_pointsと、フックの成立を検証するhook_reach_margin/
    stem_entry_marginが同じ値を共有するために切り出したもの。
    """

    end_x: float  # 終端(鼻翼の皮膚に掛かる接触点)のx
    end_y: float  # 終端のy(=_RING_CONTACT_Y)
    center_x: float  # 大きな円弧の中心のx
    center_y: float  # 大きな円弧の中心のy
    start_theta: float  # 円弧の開始角(接触点の方向、ラジアン)
    end_theta: float  # 円弧の終了角(ラジアン)。理由はring_pointsのdocstring参照
    bottom_x: float  # 円弧の終点のx
    bottom_y: float  # 円弧の終点(=鼻の下を通る直線区間の始点)のy
    axis_x: float  # 鼻栓の軸のx(=ステムのx)
    run_length: float  # 円弧の終点から曲げの中心までの直線区間の長さ(負なら円弧が鼻栓の軸まで届かない)
    start_y: float  # ステムの始点(小さな曲げの終わり)のy
    z: float  # フックの平面のz(鼻栓の軸の高さ)


def _hook(
    frame: FrameParams, params: NoseParams, body: trimesh.Trimesh, side: Literal[-1, 1]
) -> _Hook:
    """フックの幾何の中間量を計算する(モジュールdocstring「幾何」参照)。"""
    z0 = nostril_depth_z(params.tip_depth_front)
    skin_x = _skin_x(body, _RING_CONTACT_Y, z0, side)
    if skin_x is None:
        raise ValueError(
            f"接触点の高さ(y={_RING_CONTACT_Y})・鼻栓の軸の高さ(z={z0:.2f})で"
            "鼻翼の皮膚が見つからない。_RING_CONTACT_Yを見直すこと"
        )
    end_x = abs(skin_x) + _ROUND_CAP_OFFSET - frame.ring_depth
    end_y = _RING_CONTACT_Y
    phi_end = np.radians(180.0 - frame.ring_gap_deg)
    center_x = end_x - frame.ring_radius * np.cos(phi_end)
    center_y = end_y - frame.ring_radius * np.sin(phi_end)
    axis_x = params.nostril_gap / 2
    fillet_center_x = axis_x + _FILLET_RADIUS

    # 円弧は開始角(start_theta、接触点の方向に2*piを加えて「270度より
    # 大きい」領域に置いた値)から、角度を減らしながら反時計回りに進む。
    # 以前は終了角を270度(full_end_theta、真下)に固定していたが、
    # ring_radiusが大きい・中心が鼻栓の軸から離れているなどの組み合わせ
    # では、270度に達する前に円弧のx座標が鼻栓の軸を追い越して反対側
    # (鼻の中心線寄り)まで入り込み、鼻にめり込む不具合があった(ユーザー
    # 指摘・実測)。円弧がx=fillet_center_xに達する角度(下側の交点)を
    # 求め、270度より先にそこへ達するなら、そこで円弧を打ち切る
    start_theta = 3 * np.pi - np.radians(frame.ring_gap_deg)  # = phi_end + 2*pi
    full_end_theta = 1.5 * np.pi  # 270度(以前の固定終点)
    cos_val = (fillet_center_x - center_x) / frame.ring_radius
    if -1.0 <= cos_val <= 1.0:
        # 中心より下側(y座標が小さい側)の交点。開始角から下側交点までの
        # 円弧が鼻の下を回り込む経路になる(上側の交点だと、鼻翼のすぐ下を
        # かすめるだけの短すぎる経路になってしまう)
        theta_at_fillet = 2 * np.pi - np.arccos(cos_val)
        end_theta = max(theta_at_fillet, full_end_theta)
    else:
        # 円が鼻栓の軸まで届かない(hook_reach_marginが制約として弾く)
        end_theta = full_end_theta

    bottom_x = center_x + frame.ring_radius * np.cos(end_theta)
    bottom_y = center_y + frame.ring_radius * np.sin(end_theta)
    return _Hook(
        end_x=end_x,
        end_y=end_y,
        center_x=center_x,
        center_y=center_y,
        start_theta=start_theta,
        end_theta=end_theta,
        bottom_x=bottom_x,
        bottom_y=bottom_y,
        axis_x=axis_x,
        run_length=bottom_x - fillet_center_x,
        start_y=bottom_y + _FILLET_RADIUS,
        z=z0,
    )


def ring_points(
    frame: FrameParams, params: NoseParams, body: trimesh.Trimesh, side: Literal[-1, 1]
) -> list[np.ndarray]:
    """鼻翼を外側から押さえるリング(フックの丸い部分)の経路(点列)を返す
    (points[0]が鼻翼の皮膚に掛かる終端=接触点、points[-1]が鼻栓の真下で
    ステムへつながる点)。

    xy平面(z=鼻栓の軸の高さ)上の経路で、3区間からなる:

    1. 大きな円弧: 終端(接触点。高さ_RING_CONTACT_Yの鼻翼の外側の皮膚
       (_skin_xで実測)からframe.ring_depthだけ内側に押し込んだ位置。
       ring_clearance_marginの線径比例の許容量(_RING_EMBED_RATIO)を
       超えてしまう場合、GAはring_depthを負にして接触点を皮膚より外側へ
       わずかに引くこともある)から、中心から見た終端の
       方向phi_end=180度-ring_gap_deg(90度なら真上)を
       起点に、外側(360度)を経て、下端(270度)か、鼻栓の軸のx座標に達する
       角度(_hookのdocstring参照)のどちらか手前まで
    2. 直線: 円弧の終点から鼻の下を内側(-x)へ、鼻栓の軸の手前
       _FILLET_RADIUSまで(円弧が既に軸のx座標に達している場合はほぼ
       長さ0になる)
    3. 小さな曲げ: 半径_FILLET_RADIUSの四分円で向きを内側→上へ変え、
       鼻栓の軸(x=nostril_gap/2)の真下で上向きに終わる。ここがステムの
       始点

    鼻本体メッシュを参照するのは接触点の位置決め(_skin_x、1点)だけで、
    経路自体は解析的な円弧と直線(全周を表面に追従させると輪の内側の
    空間がなくなって鼻に張り付いて見える、という以前の問題を避けるため)。
    以前は「円の内側の点で縦棒に接する」1つの円だけの形だったが、それだと
    縦棒がリングの内側に並んで鼻栓の脇を斜めに横切り、鼻栓の真下から
    刺さる形にならなかった(ユーザー指摘)。
    """
    h = _hook(frame, params, body, side)

    # 1. 大きな円弧: 開始角から終了角へ遡る(_hookのdocstring参照)
    phis = np.linspace(h.start_theta, h.end_theta, _RING_SAMPLES)
    xs = [h.center_x + frame.ring_radius * np.cos(phi) for phi in phis]
    ys = [h.center_y + frame.ring_radius * np.sin(phi) for phi in phis]

    # 2. 直線: 円弧の終点から曲げの始点まで(run_lengthが負=フックが軸まで
    #    届かない個体でも点列は作る。hook_reach_marginが制約として弾く)
    fillet_center_x = h.axis_x + _FILLET_RADIUS
    xs.append(fillet_center_x)
    ys.append(h.bottom_y)

    # 3. 小さな曲げ: 中心(fillet_center_x, bottom_y+r)、角度270度→180度
    for t in np.linspace(1.5 * np.pi, np.pi, _FILLET_SAMPLES)[1:]:
        xs.append(fillet_center_x + _FILLET_RADIUS * np.cos(t))
        ys.append(h.start_y + _FILLET_RADIUS * np.sin(t))

    return [np.array([side * x, y, h.z]) for x, y in zip(xs, ys)]


def stem_points(
    frame: FrameParams,
    plug: PlugParams,
    params: NoseParams,
    ring: list[np.ndarray],
    side: Literal[-1, 1],
) -> list[np.ndarray]:
    """鼻栓の軸上をまっすぐ上(+y、鼻の奥)へ伸びるステムの経路(点列、2点)
    を返す(path[0]がリングの終点=小さな曲げの終わり、path[-1]が上端)。

    x・zは鼻栓の軸と同じ(ring[-1]がすでに軸の真下にある)。下端はリングの
    終点(鼻栓の露出面より下)、上端はそこからframe.stem_lengthだけ上。
    鼻栓の露出面より下から軸に沿って入るため、鼻栓の下部から真っ直ぐ
    刺さる(ユーザーのスケッチ通り)。plug/params/sideは現状未使用だが、
    build_side_pathsと同じ引数を受け取っておく。
    """
    start = ring[-1]
    top = start + np.array([0.0, frame.stem_length, 0.0])
    return [start, top]


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
    stem_pointsの引数に含めているが現状未使用(stem_pointsのdocstring
    参照。鼻栓の位置に依存する調整を将来足せるよう受け取っている)。
    """
    ring = ring_points(frame, params, body, side)
    stem = stem_points(frame, plug, params, ring, side)
    return ring, stem


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


def _tube_mesh(
    points: list[np.ndarray], radius: float, round_start: bool = False
) -> trimesh.Trimesh:
    """点列を、半径radiusの円形断面で押し出した1本の連続チューブにする。

    trimesh.creation.sweep_polygonは円形ポリゴンを3D経路に沿って押し出し、
    各内部点でミター(斜め)継ぎの断面リングを共有する単一の連続メッシュを
    返す。始点・終点には自動でキャップが付く(sweep_polygonのcap引数、
    既定True)が、これは平らな円形のキャップになる。round_start=Trueの
    場合、始点に半径radiusの球をブーリアン結合し、丸い(半球状の)先端に
    する(ユーザー要望: リングの先端=鼻翼の皮膚に掛かる接触点を丸くしたい。
    build_frame_pairがring_meshに使う)。

    ring_clearance_marginはround_start=Trueで検証する(実際に書き出される
    ジオメトリで検証するため)。球は経路方向(前後)にも張り出すため平らな
    キャップよりめり込みが大きくなるが、_ROUND_CAP_OFFSET(接触点を
    あらかじめ外側へ逃がす固定オフセット)を導入する前は、この余分な
    めり込みがring_radius/ring_gap_deg/ring_depth/ring_thicknessをどう
    変えてもほぼ一定(0.6〜0.7mm程度)になり、制約として機能しなかった
    (ユーザーが問題視した候補も、素直に許容範囲内に収まっていた「普通の」
    候補も、ほぼ同じめり込み量になってしまっていた)。_ROUND_CAP_OFFSETで
    球の張り出し分をあらかじめ相殺した後は、ring_depthに対して滑らかに
    応答するようになった。
    """
    polygon = Point(0, 0).buffer(radius, resolution=_TUBE_POLYGON_RESOLUTION)
    tube = trimesh.creation.sweep_polygon(polygon, np.array(points))
    if round_start:
        sphere = trimesh.creation.icosphere(subdivisions=2, radius=radius)
        sphere.apply_translation(points[0])
        tube = tube.union(sphere, engine="manifold")
    return tube


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


def hook_reach_margin(
    frame: FrameParams, params: NoseParams, body: trimesh.Trimesh
) -> float:
    """フックの大きな円弧の終点と、鼻栓の軸を回り込む曲げとの間の直線
    区間(_Hook.run_length、リングとステムの間の空間)が_MIN_HOOK_GAPに
    足りない不足量を返す(正=違反量、0以下=十分な隙間がある)。

    以前はrun_length>=0(=円弧が鼻栓の軸を追い越して反対側まで回り込んで
    いないこと)だけを要求していたが、それだとGAがrun_lengthを0近くまで
    詰めた個体を選び、リングの丸い部分とステムがほとんど隙間なく隣り
    合う窮屈な見た目になった(ユーザー指摘: 「リングと棒の隙間が狭い」)。
    左右は鏡映で等しいため片側で判定する。frameに依存する(ring_radius/
    ring_gap_deg/ring_depthの探索でrun_lengthが変わる)ため、
    evaluate_frameは例外で止めずこの値を制約として使う。
    """
    return _MIN_HOOK_GAP - _hook(frame, params, body, 1).run_length


def validate_hook_reach(
    frame: FrameParams, params: NoseParams, body: trimesh.Trimesh
) -> None:
    """hook_reach_marginが正(=違反)の場合に例外を送出する。"""
    margin = hook_reach_margin(frame, params, body)
    if margin > 0:
        raise ValueError(
            f"フックの円弧とステムの間の隙間が_MIN_HOOK_GAP({_MIN_HOOK_GAP}mm)に"
            f"{margin:.3f}mm足りない。ring_radiusを大きくするかring_gap_degを"
            "見直すこと"
        )


def stem_entry_margin(
    frame: FrameParams, plug: PlugParams, params: NoseParams, body: trimesh.Trimesh
) -> float:
    """ステムの始点(小さな曲げの終わり)が鼻栓の露出面より上にある量を
    返す(正=違反量、0以下=露出面より下から入っている)。

    ステムは鼻栓の下部から軸に沿って真っ直ぐ刺さる想定なので、始点は
    露出面(plug_outer_end)より下になければならない。始点のyは接触点の
    高さと半径・隙間で決まる(_Hook.start_y)ため、小さなフープでは
    露出面より上(鼻孔の中)から始まってしまう。左右は鏡映で等しいため
    片側で判定する。
    """
    h = _hook(frame, params, body, 1)
    outer_y = plug_outer_end(plug, params.nostril_gap, params.tip_depth_front, 1)[1]
    return h.start_y - outer_y


def validate_stem_entry(
    frame: FrameParams, plug: PlugParams, params: NoseParams, body: trimesh.Trimesh
) -> None:
    """stem_entry_marginが正(=違反)の場合に例外を送出する。"""
    margin = stem_entry_margin(frame, plug, params, body)
    if margin > 0:
        raise ValueError(
            f"ステムの始点が鼻栓の露出面より{margin:.3f}mm上にある(鼻栓の"
            "下部から刺さらない)。ring_radiusを大きくすること"
        )


def hoop_protrusion(
    params: NoseParams, body: trimesh.Trimesh, sides: list[SidePaths]
) -> float:
    """フープの最外点(鼻から最も離れた点)が、その高さの鼻翼の皮膚より
    外側へ出ている量(mm)を返す。左右のうち小さい方の値。

    最外点(|x|が最大のリング点)と同じ高さ(y)・鼻栓の軸の高さ(z)で
    鼻翼の皮膚のx座標を実測(_skin_x)し、その差を「皮膚からの突き出し」
    とする。その高さに皮膚が見つからない(最外点が鼻の下面より下にある)
    場合は、フープはその高さで鼻に隠れようがないため、皮膚をx=0(鼻の
    中心線)にあるものとみなして最外点のx座標そのものを返す。

    scripts/earrings/evaluation.pyの意匠性の目的(visibility、最大化。
    大きく見えるフープほど鼻ピアスらしい)と、最低限の突き出しを要求する
    制約(hoop_visibility_margin)の両方から参照される。
    """
    z0 = nostril_depth_z(params.tip_depth_front)
    worst = np.inf
    for (ring, _), side in zip(sides, (-1, 1)):
        points = np.array(ring)
        outermost = points[np.argmax(np.abs(points[:, 0]))]
        skin_x = _skin_x(body, float(outermost[1]), z0, side)
        skin = abs(skin_x) if skin_x is not None else 0.0
        worst = min(worst, abs(outermost[0]) - skin)
    return float(worst)


def hoop_visibility_margin(
    params: NoseParams, body: trimesh.Trimesh, sides: list[SidePaths]
) -> float:
    """フープの突き出し(hoop_protrusion)が_MIN_HOOP_PROTRUSIONに足りない
    不足量を返す(正=違反量、0以下=十分見えている)。

    frameに依存する(ring_radius/ring_gap_deg/ring_depthの探索によって
    最外点の位置が変わる)ため、evaluate_frameは例外で止めずこの値を
    制約として使う(_MIN_HOOP_PROTRUSIONのコメント参照)。
    """
    return _MIN_HOOP_PROTRUSION - hoop_protrusion(params, body, sides)


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
    """リングの実際のチューブ表面の鼻本体メッシュへのめり込み量が、線径に
    比例した許容量(_RING_EMBED_RATIO×半径)を超えていないかを返す
    (正=超過量、0以下=許容範囲内)。左右のリング全区間のうち最も厳しい
    点の値。sidesはbuild_side_pathsで左右分を事前計算した(ring_points,
    stem_points)のリスト。frameに依存する(ring_radius/ring_gap_deg/
    ring_depth/ring_thicknessの探索によって結果が変わる)ため、
    evaluate_frameは例外で止めずこの値を制約として使う。build_frame_pair
    (メッシュ生成)は例外で止めたいのでvalidate_ring_clearanceを使う。

    以前はframe.ring_depth+半径(接触点を皮膚の内側へ意図的にring_depthだけ
    押し込んだ分、表面が平坦だと仮定した理論値でめり込むのが「正常」という
    考え方)を許容量にしていたが、これは「ring_depthで狙った分だけなら
    常に合格する」事実上無効な閾値だった(実測してもring_depthを増やす
    ほど許容量も増えるため、常に理論値を下回り違反したことがなかった。
    ユーザー指摘の候補=ring_thickness2.5mm・ring_depth1.44mmでも実測
    めり込みは0.69mm程度に留まり、旧許容量2.69mmを大きく下回っていた)。
    _RING_EMBED_RATIO(同定数のコメント参照)を許容量にすることで、
    ring_depthを大きくしても許容量自体は増えないため、実際に
    めり込みが増えればどこかで違反する(ユーザー指摘の候補=ring_radius
    6.54mm・ring_gap_deg75.01度・ring_thickness2.5mm・ring_depth1.44mmは
    新しい許容量では違反することを実測で確認済み)。円弧が鼻翼の壁を
    貫通する(隙間が狭すぎて内側上方の壁に突っ込む、下端が鼻の下面を
    くぐれず肉に埋まる等)ケースは、めり込み量が許容量を大きく超えるため
    引き続きここで検出される。
    """
    radius = frame.ring_thickness / 2
    allowed_embed = _RING_EMBED_RATIO * radius
    worst = -np.inf
    for ring, _ in sides:
        # round_start=True: build_frame_pairが実際に書き出すジオメトリ
        # (丸い先端)で検証する。_ROUND_CAP_OFFSETの導入前は、丸いキャップの
        # めり込みが設計変数に対してほぼ一定になり制約として機能しなかった
        # ため平らなキャップを使っていたが、_ROUND_CAP_OFFSETで接触点を
        # あらかじめ逃がすようになった今はring_depthに対して滑らかに応答する
        # (_ROUND_CAP_OFFSETのコメント参照)。実際に書き出されない平らな
        # キャップより、実際に書き出されるジオメトリで検証する方が正しい
        tube = _tube_mesh(ring, radius, round_start=True)
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
            f"ring_thickness({frame.ring_thickness})のチューブが、線径に"
            f"比例した許容めり込み量(_RING_EMBED_RATIO={_RING_EMBED_RATIO})を"
            f"{margin:.3f}mm超えて実際に鼻表面へめり込んでいる。ring_depthを"
            "小さくする(または負にする)か、ring_thicknessを太くすること"
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
    """ステムの鼻栓への刺さり込み(plug_insertion_depth)が最小長さ
    (plug.length*_MIN_INSERTION_TO_PLUG_LENGTH)に足りない不足量を返す
    (正=違反量、0以下=十分刺さっている)。
    """
    minimum = plug.length * _MIN_INSERTION_TO_PLUG_LENGTH
    return minimum - plug_insertion_depth(plug, params, stem, side)


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
    validate_hook_reach(frame, params, body)
    validate_stem_entry(frame, plug, params, body)
    validate_hoop_visibility(params, body, sides)
    validate_ring_clearance(frame, sides, body)
    validate_stem_clearance(sides, body, frame.stem_thickness)
    for (_, stem), side in zip(sides, (-1, 1)):
        shortage = plug_insertion_margin(plug, params, stem, side)
        if shortage > 0:
            raise ValueError(
                "ステムの鼻栓への刺さり込みが最小長さ(鼻栓の長さの"
                f"{_MIN_INSERTION_TO_PLUG_LENGTH:.0%})に{shortage:.3f}mm足りない。"
                "stem_lengthを大きくすること"
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
        ring_mesh = _tube_mesh(ring, ring_radius, round_start=True)
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
