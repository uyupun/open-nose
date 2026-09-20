"""フレームの仮形状(FrameParamsの6変数): 平べったいブリッジ+左右の脚
(棒+鼻栓を差し込む筒=レンズ)。

実際の鼻腔拡張テープ(ブリーズライト等)を再現した設計。鼻腔拡張テープは、
鼻の実際の丸み(曲率)より平らな板ばねを、小鼻の高さで鼻に貼り付けることで、
板ばねが「元の平らな形に戻ろうとする力」が小鼻を外側に押し開き、鼻腔
(鼻弁)を機械的に広げて呼吸を楽にする(貼るだけで、鼻の中には何も
入れない)。

このプロジェクトは「鼻栓(ティッシュ等)を留める」ことが目的のため、
テープ単体ではなく、ブリッジ(拡張機能)の左右の端から鼻栓の位置まで
脚を伸ばし、鼻栓を留める機能を継続する(ハイブリッド構成)。印刷しやすく
一つずつ装着できるよう、ブリッジ(鼻頭のアーチ状)・左の脚(棒とレンズ)・
右の脚(棒とレンズ)の3部品に分け、ジョイントマットのような嵌め込み
(タブとスロット)で組み立てる。

## 経緯(実測画像を見たユーザーからの指摘への対応。現在も有効な教訓のみ)

- ブリッジは円形断面のチューブではなく、幅(bridge_width)×厚み
  (bridge_thickness)の平らな帯にする(「ブリーズライト同様に平べったく」)。
  幅方向にも実際の鼻の断面に沿わせる(_bridge_grid。「鼻にフィットする
  感じに」)。
- 鼻栓は棒で刺さず、鼻栓を取り囲む肉厚のある中空円筒(レンズ、
  _collar_mesh)に差し込む。螺旋の線材では印刷時に崩れた。
- 左右のレンズの外径が重ならないよう、壁の肉厚は脚の太さから切り離した
  固定値(_COLLAR_WALL_THICKNESS)にする(重なるとブーリアン演算が破綻し
  とがった破片が残った)。
- ブーリアン演算の結果はis_watertight/is_volumeだけでなく、連結成分数
  (body_count)とSTLへの書き出し→読み直し後の水密性まで確認する
  (_largest_component・_clean_boolean_result)。
- 3部品化の最初の版は「丸いペグを丸いソケット穴に差す」構造だったが、
  抜け止めがなく、ボスの円柱が帯の縁から飛び出してジョイントマットの
  嵌め込みとは別物だった(ユーザーのスケッチ: アーチの下縁に、脚の先端の
  矢じり形のタブが平らに嵌まる)。また脚の経路はレンズの面より約2mm下まで
  潜ってから戻る形で、レンズの下にはみ出していた(ユーザーのスケッチ
  「6d」: 棒はレンズの輪の外側に接線でつながり、輪からはみ出さない)。
  ペグ・ソケット・ボス・コネクタのフィレットを継ぎ足す対症療法をやめ、
  次の2点を作り直した:
  (1) 帯とタブ: 帯の下縁に、帯の厚み方向に貫通する矢じり形のスロットを
      切り、脚側には同じ形のタブ(帯そのものと同じ面・同じ厚み)を持たせる
      (_tab_polygon・_tab_prism)。タブは帯の面の法線方向から押し込んで
      嵌め、脚の方向(下向き)にも帯の面に沿った方向にも抜けない。
  (2) 棒とレンズ: 棒はレンズの面の高さまで降りてから、レンズの輪の外側の
      点(鼻中隔と反対側)に、輪の接線方向から入り、輪の壁の中へ円弧に
      沿って溶け込む(_rod_path)。棒の太さは、レンズの面より下・輪の内側
      (鼻栓の空間)・帯の厚みを越えない範囲へなめらかに細くする
      (_rod_radii)。
- 自作の可変半径チューブ(頂点・面を手で組み立てたロフト)はブーリアン
  演算で分裂・退化しやすかった。可変半径の棒は、manifold3dの球の凸包を
  隣り合う点ごとに作って結合する方式(_rod_manifold)にした。凸包は常に
  閉じた凸立体で、隣同士が深く重なるため、触れるだけの関係が生じない。

## 幾何(座標系: x=左右、y=鼻先(0)→鼻筋、z=前後(前面が+)。earrings/spiralと同じ)

- **ブリッジ(bridge_points/_bridge_grid/_ribbon_mesh)**: 高さ_BRIDGE_Yの
  断面の実際の形状(commons.nose_model.surface_profile_at・commons.
  rounded_triangle.rounded_triangle_ring)から前面の丸め弧+直線の辺を
  組み立て、_BRIDGE_Y±bridge_width/2の範囲で格子状にロフトし、表面から
  BRIDGE_OFFSET(肌側の面)〜BRIDGE_OFFSET+bridge_thickness(外側の面)の
  帯にする。
- **タブ・スロット(_tab_frame/_tab_polygon/_tab_prism)**: 帯の下縁
  (y=_BRIDGE_Y-bridge_width/2)の、帯の端から内側へ入った位置に置く。
  帯の面内の2次元座標(u=帯に沿った横方向、v=帯の下縁から上向き)で
  矢じり形の多角形を作り、帯の法線方向に押し出した角柱で帯を切る。
  タブ=帯∩角柱(帯と完全に同じ面・同じ厚み)、スロット=帯−(角柱を
  _TAB_CLEARANCEだけ太らせたもの)。
- **棒(_rod_path/_rod_radii/_rod_manifold)**: タブの首の中から始まり、
  鼻の側面に沿って_SIDE_FOLLOW_END_Yまで降り(_side_follow_points)、
  レンズの面の高さ(筒の厚みの中央)で輪の外側の接点に接線方向から到達する
  エルミート曲線を通り、輪の壁の中心線に沿って_ROD_JOINT_ARC_DEGだけ
  進む。
- **レンズ(_collar_geometry/_collar_mesh)**: 鼻栓の軸を中心にした中空円筒。
  鼻栓の露出端からわずか(_COLLAR_PLUG_INSET)奥から、frame.collar_length
  だけ伸びる。

## 拡張力の物理近似(evaluation.pyが計算に使う幾何量)

ブリッジは平らな長方形断面の板ばね(実際のブリーズライトと同じ形状)と
みなす。装着後の実際の曲率(1/actual_radius、bridge_curvatureが実測)は
鼻の形状で決まり自由変数ではない。frame.natural_radius(装着前の自然な
曲率半径。値が大きいほど平ら)がactual_radiusより大きい(平らな)場合、
装着時にブリッジは自然な形より強く曲げられることになり、その反発力が
小鼻を外側へ開く。deflection(たわみ)=1/actual_radius-1/natural_radius
(正であるほど拡張力が強い)。長方形断面の梁の曲げ剛性は幅に比例し厚みの
3乗に比例する。evaluation.pyの_extension_force参照。

## 探索変数・ファイル内の並び順

FrameParamsの6変数: natural_radius(拡張力の源)、bridge_width/
bridge_thickness(平らなブリッジの幅・厚み)、leg_thickness(棒の太さ)、
collar_length(レンズの厚み)、tab_head_oversize(タブの矢じりの張り出し量)。

ファイル内の並び順: 定数・データクラス → 経路・寸法を計算する関数
(bridge_points, _tab_frame, _rod_path, build_paths等) → メッシュ化・
幾何判定のユーティリティ → 各種*_margin/validate_* → build_bridge_piece・
build_leg_piece。
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import trimesh
from manifold3d import Manifold, Mesh, OpType
from shapely.geometry import Polygon

from commons.nose_model import (
    NoseParams,
    build_nose_body,
    nostril_depth_z,
    surface_profile_at,
    tip_cap_min_y,
)
from commons.plug_model import PlugParams, plug_outer_end
from commons.rounded_triangle import POINTS_PER_CORNER, rounded_triangle_ring

# フレームのプレースホルダーの色。earrings/spiralの_FRAME_COLORと同じ
_FRAME_COLOR = [90, 90, 100, 200]
# ブリッジの高さ(y座標、mm)。当初は4.0(鼻翼の隆起の中ほど、earrings.
# frame_model._RING_CONTACT_Yと同じ値)。実際に印刷して合わせたユーザーの
# 「棒が鼻まで届かない。アーチをもっと鼻筋側へ上げて棒を伸ばしてほしい」で
# 8.0へ、続く「棒を2倍くらい長くしてほしい」で28.0へ上げたが、今度は
# 「やはり棒が長すぎた。今の3分の2くらい」という指摘を受けて14.0へ下げた。
# 棒(タブ〜レンズ)の長さは実測14.7→21.1→42.3→27.7mm。鼻の長さ
# (NoseParams.nose_len=52.2mm)の1/4ほどの高さで、小鼻の隆起のすぐ上に
# 帯が乗る位置になる
_BRIDGE_Y = 14.0
# ブリッジの帯の肌側の面を、鼻の表面(最近接点)からどれだけ外側
# (その点の三角形の法線方向)へ逃がすか(mm)。帯(_ribbon_mesh)が幅方向に
# も鼻の表面に沿う格子で作られるため小さい値で足りる。棒の鼻の側面に沿う
# 区間も、帯の厚みの中央(BRIDGE_OFFSET+bridge_thickness/2)を通すことで
# タブとの継ぎ目に段差(折れ)ができないようにしている
BRIDGE_OFFSET = 0.4
# ブリッジの端(鼻の側面の外縁とみなす位置)を、断面の「直線の辺」
# (_side_edge_span: 前面の丸め弧の端から背面角の丸め弧の端まで)の
# どこに置くかで指定する(0=前面寄りの端、1=背面角の手前)。
# 以前はhalf_width(角を丸める前の三角形の半幅)に対する比率だったが、
# 丸めで実際の断面は半幅よりずっと小さく、比率0.5〜0.6でも帯の端が鼻の
# 表面より外(空中)に出ていた。タブもスロットも鼻に乗っていない位置に
# 置かれるため、直線の辺そのものを基準に測る形に改めた。0.55は、帯の端を
# 鼻の側面の見える範囲に置きつつ、タブのスロット(周りの肉を含む)が
# 直線部分に収まる(tab_fit_margin)値
_BRIDGE_SIDE_EDGE_RATIO = 0.75
# ブリッジを幅方向(y方向)にも鼻の表面に沿わせる際の、断面のロフト本数
_BRIDGE_WIDTH_SAMPLES = 5
# 棒が鼻の側面に沿う区間(_side_follow_points)の下端のy座標(mm)と、
# その折れ線近似の分割数。ここから先はレンズの接点の真上へ向かう
# エルミート曲線になる(_rod_path)。-1.0にしていたが、鼻孔とレンズが
# 大きくなり、鼻の側面を降り切ってから横移動するとレンズの真上を
# 通れず壁を斜めに横切ってしまうため、0.5へ上げて早めに切り替える
_SIDE_FOLLOW_END_Y = 0.5
_SIDE_FOLLOW_SAMPLES = 8
# natural_radiusがactual_radiusより何倍大きくなければならないか。1.0だけを
# 要求するとGAがほぼ同じ値を選び拡張力がほぼ0の個体になりうるため、
# 「平らな板を曲げて留める」とわかる最低限の比率を要求する暫定値
_MIN_CURVATURE_RATIO = 1.2
# ブリッジ・棒の表面が鼻本体メッシュへめり込んでよい上限(線径の半分・
# 帯の厚みの半分に対する比率)。earrings.frame_model._RING_EMBED_RATIOと
# 同じ理由・同じ値(曲面と完全には一致しないことに由来する残留めり込み
# だけを許容する)
_EMBED_RATIO = 0.5
# validate_*が「違反」と判定する閾値(mm)。margin>0をそのまま使うと、
# 探索範囲の境界ちょうどの値(例: tab_head_oversize=0.35、はめあい0.15mm、
# 要求0.20mm)が浮動小数点の丸め(2e-17)で違反扱いになるため、ごく小さな
# 許容差を置く(scripts/dilator/evaluation._MARGIN_EPSILONと同じ役割)
_MARGIN_TOLERANCE = 1e-6
# _signed_distance_to_bodyが疑似法線による符号判定を信頼する距離の上限
# (mm)。earrings/spiralと同じ
_PSEUDO_NORMAL_MAX_DISTANCE = 2.0

# レンズ(筒)の内径を鼻栓の半径からどれだけ離すか(mm、差し込みの隙間)。
# 壁を厚くする余地を作るため0.3から縮めた(鼻栓は柔らかいティッシュ等の
# 想定なので、差し込みには支障がない)。0.3→0.15→0.10と縮めて壁に回して
# いたが、実際に印刷したユーザーから「鼻栓がはまらないので穴をもう少し
# 広げてほしい」という指摘を受けて0.20へ戻した(鼻栓自体もPlugParams.
# diameter=10.0mmへ実測に合わせたため、穴は実測10.40mmになる)
_COLLAR_CLEARANCE = 0.20
# レンズの壁の肉厚(mm、leg_thicknessから独立した固定値)。ユーザー指摘
# (「レンズ部分とそれの棒の部分もう少し太くしてください。印刷時に上手く
# 印刷できないので」)を受けて0.75mmから厚くした。左右のレンズは鼻栓の軸
# (x=±nostril_gap/2=±4.25mm)を中心にするため、外径がこれを超えると互いに
# ぶつかる。鼻孔の中心間(NoseParams.nostril_gap)を実測に合わせて14.0mmへ
# 広げたため、以前(8.5mm)より余裕ができ、ユーザー要望(「全体的に太く」)に
# 沿って1.05→1.45mmへ厚くした(実測: r_outer=6.65mm、左右の間に0.70mmの
# 隙間が残る。validate_collar_no_overlapも参照)。この肉厚は、棒がレンズへ
# 溶け込む区間の太さ(=肉厚−_ROD_LENS_GAP、直径2.80mm)の上限にもなる
# (_rod_radii参照)ため、_MIN_ROD_DIAMETERと一緒に決める必要がある
_COLLAR_WALL_THICKNESS = 1.45
# レンズの下端(y_start)を、鼻栓の露出端(plug_outer_end)からどれだけ奥
# (鼻側)に置くか(mm)。露出端ちょうどに置くと、鼻栓の端面と同じ高さの
# 面が並び、差し込んだ鼻栓が抜けやすい。鼻栓の端がわずかにレンズの下へ
# 出る程度の暫定値。レンズが使えるのは鼻栓の露出部(実測2.25mm)だけで、
# ここを削ったぶんだけcollar_lengthの上限が伸びる(実測: 0.3mmで1.9mm、
# 0.15mmで2.1mm)。棒の太さがcollar_lengthで頭打ちになるため(_rod_radii)、
# ユーザー要望「まだ太くして欲しい」に合わせて0.3→0.15mmに詰めた
_COLLAR_PLUG_INSET = 0.15

# 棒がレンズの輪の壁の中へ溶け込む区間の長さ(輪の中心線に沿った角度、度)。
# ユーザーのスケッチ「6d」のように、棒は輪の外側の接点から輪の接線方向に
# 入り、そのまま輪の一部として続いて見える。短すぎると棒の先端の丸い
# 端が輪の途中に浮いて見えるため、壁の中に十分埋もれる長さにした
_ROD_JOINT_ARC_DEG = 60.0
# 棒のエルミート曲線(鼻の側面の下端→レンズの接点の真上)の近似点数と、
# そこからレンズの外周面へまっすぐ降りる区間の点数
_ROD_STEM_SAMPLES = 40
_ROD_DROP_SAMPLES = 8
# 棒を球の凸包の連鎖で作るときの、球の中心の間隔(mm)。_rod_radiiが
# 点ごとに半径を変えるため、細かいほどなめらかに太さが変わる
_ROD_SAMPLE_SPACING = 0.2
# 棒の球の近似精度(manifold3d.Manifold.sphereのcircular_segments)
_ROD_SPHERE_SEGMENTS = 24
# 棒がレンズの下端・内径に対して残す余裕(mm)。0にすると棒の表面と
# レンズの面がちょうど一致し(触れるだけの関係)、lens_protrusion_marginが
# 常に0(境界)になって余裕の有無が分からなくなるため、わずかに離す
_ROD_LENS_GAP = 0.05
# 棒の半径の下限(mm)。経路上のどの点でも、太さの上限(_rod_radii)が
# これを下回ることは通常ないが、球が退化しないための安全値として置く
# (実際に下回る場合はrod_thickness_margin・lens_protrusion_marginが
# GAの制約として検出する)
_ROD_MIN_RADIUS = 0.2
# 棒の直径の最小値(mm)。ユーザー指摘(「印刷時に上手く印刷できない」
# 「まだ太くして欲しい」)への対応で、棒の最も細いところがノズル(0.4mm)の
# 3本分→9本分を下回らないことをGAの制約(rod_thickness_margin)として要求
# する。最も細いのはレンズへ溶け込む区間と、タブの首の中(上限は
# bridge_thickness)。レンズ付近の上限は「壁の肉厚」(直径2.80mmまで)と
# 「レンズの厚み」(直径collar_lengthまで)の小さい方で、後者が効くため、
# collar_lengthの探索範囲の下限と一緒に決めること(レンズの厚みは鼻栓の
# 露出部2.25mmに収める必要があり、2.1mm程度が上限)
_MIN_ROD_DIAMETER = 1.9

# タブ(脚側)・スロット(ブリッジ側)の寸法(mm)。ユーザーのスケッチ
# (アーチの下縁に、下から伸びる棒の先の矢じり形のタブが嵌まる)に従い、
# 帯の面内で「首」(幅=leg_thickness)の上に、首より左右へtab_head_
# oversizeずつ張り出した矢じり形の「頭」を置く。
# 首の長さ(帯の下縁から頭の付け根まで)。細かい印刷でも確実に嵌まるよう
# ユーザー要望で0.7→1.0→1.2mmと伸ばした
_TAB_NECK_LENGTH = 1.2
# 頭の長さ(付け根=最も広い「返し」から先端まで)。同じくユーザー要望で
# 1.1→1.4→1.7mmと伸ばした。首+頭+はめあい+肉(=3.85mm)がbridge_widthに
# 収まる必要がある(tab_fit_margin)ため、探索範囲の下限と一緒に決めること
_TAB_HEAD_LENGTH = 1.7
# 頭の先端の半幅を、首の半幅に対する比率で指定(1未満で先すぼまりの
# 矢じり形。0にすると先端がとがり、印刷でつぶれやすい)
_TAB_TIP_RATIO = 0.5
# スロットをタブよりどれだけ太らせるか(mm、面内の片側)。FDM印刷の寸法
# 誤差があっても嵌まるよう、ユーザー要望で0.1mmから広げた。抜け止めの
# 引っかかりはtab_head_oversizeからこの値を引いた残りになるため、
# tab_retention_marginが最低限の引っかかりを要求する
_TAB_CLEARANCE = 0.15
# スロットの周り(帯の上縁側・帯の端側)に最低限残す帯の肉(mm)。これより
# 薄いと、押し込んだときにスロットの縁が割れる
_TAB_MIN_WALL = 0.8
# タブ(=帯と同じ厚み)の最小の厚み(mm)。ユーザー要望(「アーチ状の
# ジョイントのような連結部分も同様に太さ調整して」「まだ太くして欲しい」)で
# 0.8→1.0→1.8→2.4mmと上げた(FDMの0.2mm積層で12層)。棒もタブの首の中では
# この厚みまでしか太くできないため、_MIN_ROD_DIAMETER以上にしている
_MIN_TAB_THICKNESS = 2.4
# 抜け止めの引っかかり(tab_head_oversizeからはめあいの隙間を引いた残り)の
# 最小値(mm)。これを下回ると、押し込んでも「返し」が効かず抜けてしまう。
# ユーザー要望(「まだ太くして欲しい」)で0.2→0.3mmに上げ、返しそのものも
# 印刷でつぶれない大きさにした
_MIN_TAB_RETENTION = 0.3
# スロットの差し口(帯の外側の面)に付ける面取り(リードイン)の、面内の
# 広がり(mm)と、帯の厚み方向の深さ(mm)、階段状に近似する段数。タブが
# 多少ずれていても押し込むだけで位置が決まるようにするため(ユーザー要望
# 「細かな印刷でも上手く連結できるような工夫」)。まっすぐな角柱を段階的に
# 太らせて重ねる(すべて深く重なるため、ブーリアン結合が安定する)
_TAB_LEAD_IN = 0.25
_TAB_LEAD_IN_DEPTH = 0.4
_TAB_LEAD_IN_STEPS = 3
# タブの角柱の、帯の法線方向の押し出し長さ(mm、帯の厚みより十分長い)
_TAB_PRISM_DEPTH = 10.0
# タブの首の下端を、帯の下縁よりどれだけ下まで伸ばして角柱を作るか(mm)。
# スロットを帯の下縁まで確実に開通させるための余裕
_TAB_PRISM_BELOW_EDGE = 2.0


@dataclass(frozen=True)
class FrameParams:
    """フレームの仮寸法パラメータ(単位: mm)。

    ブリーズライト型の平らなブリッジ+棒+鼻栓を差し込むレンズという
    プレースホルダーで、後から実際の造形(3Dプリント/粘土)に向けて調整・
    最適化する。
    """

    natural_radius: float = 60.0
    bridge_width: float = 5.0
    bridge_thickness: float = 2.8
    leg_thickness: float = 3.2
    collar_length: float = 2.08
    tab_head_oversize: float = 0.55

    def __post_init__(self) -> None:
        for name in (
            "natural_radius",
            "bridge_width",
            "bridge_thickness",
            "leg_thickness",
            "collar_length",
            "tab_head_oversize",
        ):
            value = getattr(self, name)
            if value <= 0:
                raise ValueError(f"{name} は正の値にすること: {value}")


@dataclass(frozen=True)
class CollarGeometry:
    """レンズ(鼻栓を差し込む肉厚のある中空円筒)の位置・寸法。"""

    center_x: float  # 円筒の中心軸のx(=side*nostril_gap/2)
    y_start: float  # 円筒のy方向の範囲の始点(鼻の外側、下端)
    y_end: float  # 円筒のy方向の範囲の終点(=y_start+frame.collar_length)
    center_z: float  # 円筒の中心軸のz(=鼻栓の軸の深さ)
    r_inner: float  # 内径(鼻栓が差し込まれる側)
    r_outer: float  # 外径


@dataclass(frozen=True)
class TabFrame:
    """タブ・スロットを置く位置と、帯の面に沿った局所座標系。

    centerは帯の下縁の、帯の厚みの中央の点。anchorはそのもとになった鼻の
    表面上の点(法線方向へ浮かせる前)で、棒が鼻の側面に沿って降りる区間
    (_side_follow_points)の起点に使う(浮かせた後のcenterを起点にすると、
    表面からの距離を二重に足してしまい、棒の最初の数点が帯の内部に入る)。
    uは帯に沿った横方向(帯の端へ向かう向き)、vは帯の面内で下縁から上へ
    向かう向き、nは帯の面の法線(鼻の外側向き)。u・v・nは単位ベクトルで
    互いに直交する。
    """

    center: np.ndarray
    anchor: np.ndarray
    u: np.ndarray
    v: np.ndarray
    n: np.ndarray
    neck_half_width: float  # 首の半幅(=leg_thickness/2)
    head_half_width: float  # 頭の付け根の半幅(=首の半幅+tab_head_oversize)


@dataclass(frozen=True)
class RodPath:
    """棒の中心線の点列と、点ごとの半径(_rod_radii参照)。"""

    points: np.ndarray  # shape (N, 3)
    radii: np.ndarray  # shape (N,)


# ブリッジの点列・左右の棒・左右のレンズの寸法。build_pathsが返し、
# 各種*_margin・build_leg_piece・scripts/dilator/evaluation.pyの間で共通の
# 型として使う
FramePaths = tuple[list[np.ndarray], RodPath, RodPath, CollarGeometry, CollarGeometry]


def _collar_radii(plug: PlugParams) -> tuple[float, float]:
    """レンズの内径・外径(半径、mm)を返す。

    内径=鼻栓の半径+_COLLAR_CLEARANCE、外径=内径+_COLLAR_WALL_THICKNESS
    (_COLLAR_WALL_THICKNESSのコメントの通り、frameには依存しない)。
    """
    r_inner = plug.diameter / 2 + _COLLAR_CLEARANCE
    r_outer = r_inner + _COLLAR_WALL_THICKNESS
    return r_inner, r_outer


def _offset_along_surface_normal(
    body: trimesh.Trimesh, points: np.ndarray, offset: float | np.ndarray
) -> np.ndarray:
    """各点(鼻の表面上の解析的な点)を、その点に最も近い鼻本体メッシュの
    三角形の法線方向へoffsetだけ外側に浮かせて返す。offsetは点ごとに
    変える((N,1)の配列)こともできる。
    """
    _, _, triangle_id = trimesh.proximity.closest_point(body, points)
    return points + body.face_normals[triangle_id] * offset


def bridge_points(body: trimesh.Trimesh, params: NoseParams) -> list[np.ndarray]:
    """ブリッジ(小鼻の高さを左右に横断する経路)の点列を返す
    (points[0]が+x側の端、points[-1]が-x側の端)。

    frame(FrameParams)に依存しない(NoseParamsだけで決まる幾何、装着後の
    実際の曲率は鼻の形状そのもの)ため、frame引数を取らない。高さ_BRIDGE_Y
    の断面(_bridge_profile_points)をBRIDGE_OFFSETだけ鼻の表面から浮かせる。
    拡張力の計算(bridge_curvature)に使う。
    """
    points = _bridge_profile_points(params, _BRIDGE_Y)
    return list(_offset_along_surface_normal(body, points, BRIDGE_OFFSET))


def _side_edge_span(params: NoseParams, y: float) -> tuple[np.ndarray, np.ndarray]:
    """高さyの断面の、+x側の「直線の辺」の両端(x, z)を返す。

    角丸三角形の輪郭は[背面左角の弧, ブーメラン, 背面右角の弧, 前面角の弧]
    の順に並ぶ(commons.rounded_triangle.rounded_triangle_ring)。+x側の
    直線の辺は、背面右角の弧の終点(外側、xが大きい)から前面角の弧の
    始点(内側)までの区間で、フレームの帯・タブ・棒はこの範囲の中に
    置かなければ鼻の表面から浮く。戻り値は(内側の端, 外側の端)。
    """
    half_width, depth_back, depth_front = surface_profile_at(params, y)
    ring_2d = rounded_triangle_ring(half_width, depth_back, depth_front)
    return ring_2d[-POINTS_PER_CORNER], ring_2d[-POINTS_PER_CORNER - 1]


def _side_edge_x(params: NoseParams, y: float, ratio: float) -> float:
    """高さyの断面の直線の辺を、内側の端から外側の端へratioだけ進んだ位置のx。"""
    inner, outer = _side_edge_span(params, y)
    return float(inner[0] + ratio * (outer[0] - inner[0]))


def _bridge_profile_points(params: NoseParams, y: float) -> np.ndarray:
    """bridge_pointsと同じ組み立て方(高さyの断面の前面の丸め弧+直線の
    延長)を、任意の高さyについて評価する(オフセット前、鼻の表面上の
    生の点)。bridge_points(y=_BRIDGE_Y)・_bridge_grid(yを複数評価して
    ブリッジを幅方向にも鼻の表面に沿わせる)の共通実装。
    """
    half_width, depth_back, depth_front = surface_profile_at(params, y)
    ring_2d = rounded_triangle_ring(half_width, depth_back, depth_front)
    front_arc = ring_2d[-POINTS_PER_CORNER:]  # xが+から-へ並ぶ(丸め弧)

    # 丸め弧が接する辺の傾き(角丸三角形の前面頂点(0, depth_front)から
    # 背面の角(half_width, -depth_back)への向き)。丸め弧の両端は、
    # 定義によりこの辺の上にある(rounded_triangle.pyの_fillet_corner参照)
    edge_slope = (-depth_back - depth_front) / half_width
    target_x = _side_edge_x(params, y, _BRIDGE_SIDE_EDGE_RATIO)

    right_tangent_x, right_tangent_z = front_arc[0]
    right_end_z = right_tangent_z + (target_x - right_tangent_x) * edge_slope

    xs = np.concatenate([[target_x], front_arc[:, 0], [-target_x]])
    zs = np.concatenate([[right_end_z], front_arc[:, 1], [right_end_z]])
    return np.stack([xs, np.full(len(xs), y), zs], axis=1)
def _bridge_grid(params: NoseParams, width: float) -> np.ndarray:
    """ブリッジを幅方向(y方向、_BRIDGE_Y±width/2)にも鼻の表面に沿わせる
    ための格子点(オフセット前、鼻の表面上の生の点)を返す(shape:
    (_BRIDGE_WIDTH_SAMPLES, 13, 3))。

    以前はブリッジの中心の経路(bridge_points、高さ_BRIDGE_Yのみ)を
    グローバルなy軸方向に±width/2だけ平行移動して長方形の断面を作って
    いたが、鼻の断面(half_width・depth_back・depth_front)は高さyに
    よって変わる(commons.nose_model.surface_profile_at)ため、この平行
    移動では特にbridge_widthが大きいとき、実際の鼻の丸みから外れた
    (めり込む、または不自然に浮いた)形になってしまう(ユーザー指摘:
    「縦が長すぎる」「鼻にフィットする感じに調整して」)。_bridge_profile_
    pointsを複数の高さyで評価し、各高さの断面をそのまま並べる(ロフト)
    ことで、幅方向にも実際の鼻の丸みに沿う帯を作る。
    """
    ys = np.linspace(_BRIDGE_Y - width / 2, _BRIDGE_Y + width / 2, _BRIDGE_WIDTH_SAMPLES)
    return np.stack([_bridge_profile_points(params, float(y)) for y in ys], axis=0)
def bridge_curvature(bridge: list[np.ndarray]) -> tuple[float, float]:
    """ブリッジの実際の曲率半径(actual_radius)と経路長(path_length)を返す。

    ブリッジはx=0を中心に左右対称なので、両端(points[0], points[-1])を
    結ぶ弦と、中央の点(x=0、_BRIDGE_SAMPLESを奇数にしているため必ず
    存在する)のその弦からの離れ(サジタ、sagitta)から、浅い円弧の近似式
    sagitta≈(chord/2)^2/(2*radius)を使って半径を逆算する(chord・sagitta
    ともにブリッジの実際の3D座標から直接測るため、鼻の断面形状の詳細
    (rounded_triangle等)を再実装せずに済む)。

    scripts/dilator/evaluation.pyのretention(拡張力)の計算、および
    curvature_marginの両方から参照される。
    """
    p0, p_mid, p1 = bridge[0], bridge[len(bridge) // 2], bridge[-1]
    chord_vec = p1 - p0
    chord = float(np.linalg.norm(chord_vec))
    chord_dir = chord_vec / chord
    to_mid = p_mid - p0
    sagitta = float(np.linalg.norm(to_mid - np.dot(to_mid, chord_dir) * chord_dir))
    actual_radius = (chord / 2) ** 2 / (2 * sagitta)
    path_length = float(
        np.sum(np.linalg.norm(np.diff(np.array(bridge), axis=0), axis=1))
    )
    return actual_radius, path_length
def _edge_z_at(params: NoseParams, y: float, target_x: float) -> float:
    """高さyの断面で、丸め弧が接する辺(_bridge_profile_pointsのdocstring
    参照。角丸三角形の辺そのもので直線)を、指定したx=target_xまで延長
    した位置のzを返す。_bridge_profile_pointsのx=target_x部分の式と同じ
    だが、target_xをその高さ自身のhalf_widthから決めず、呼び出し側が
    指定できるようにしたもの(_tab_frame・_side_follow_pointsが使う)。
    """
    half_width, depth_back, depth_front = surface_profile_at(params, y)
    ring_2d = rounded_triangle_ring(half_width, depth_back, depth_front)
    front_arc = ring_2d[-POINTS_PER_CORNER:]
    edge_slope = (-depth_back - depth_front) / half_width
    right_tangent_x, right_tangent_z = front_arc[0]
    return right_tangent_z + (target_x - right_tangent_x) * edge_slope


def _mirror(vector: np.ndarray, side: Literal[-1, 1]) -> np.ndarray:
    """x成分にsideを掛けた(side=-1ならx軸について鏡映した)ベクトルを返す。"""
    return vector * np.array([side, 1.0, 1.0])


def _tab_frame(
    frame: FrameParams, params: NoseParams, body: trimesh.Trimesh, side: Literal[-1, 1]
) -> TabFrame:
    """タブ・スロットの位置と局所座標系(TabFrame)を返す。

    帯の下縁(y=_BRIDGE_Y-bridge_width/2)の、帯の端から内側へ入った位置に
    置く。帯の端のxは高さごとに違う(half_width(y)*_BRIDGE_HALF_SPAN_RATIO)
    ため、最も内側になる上縁の高さの端を基準にし、そこから帯に沿って
    (頭の半幅+_TAB_CLEARANCE+_TAB_MIN_WALL)だけ内側にする(スロットの
    端側に_TAB_MIN_WALLの肉が必ず残る)。帯の下縁付近の断面は、丸め弧の
    外側の直線の辺の上にある(_edge_z_at)ため、その辺の向きをuにする。
    中心は鼻の表面から帯の厚みの中央(BRIDGE_OFFSET+bridge_thickness/2)
    だけ浮かせた点。まず+x側で計算してからsideで鏡映する。
    """
    y_edge = _BRIDGE_Y - frame.bridge_width / 2
    # 帯の端のxは高さごとに違う(断面が鼻先へ向かって広がる)ため、最も
    # 内側になる上縁の高さの端を基準にする
    x_end = _side_edge_x(params, _BRIDGE_Y + frame.bridge_width / 2, _BRIDGE_SIDE_EDGE_RATIO)
    half_width, depth_back, depth_front = surface_profile_at(params, y_edge)
    edge_slope = (-depth_back - depth_front) / half_width
    u_xz = np.array([1.0, edge_slope]) / np.hypot(1.0, edge_slope)

    neck_half_width = frame.leg_thickness / 2
    head_half_width = neck_half_width + frame.tab_head_oversize
    inset = head_half_width + _TAB_CLEARANCE + _TAB_MIN_WALL
    x_anchor = x_end - inset * u_xz[0]
    raw = np.array([[x_anchor, y_edge, _edge_z_at(params, y_edge, x_anchor)]])
    _, _, triangle_id = trimesh.proximity.closest_point(body, raw)
    n = body.face_normals[triangle_id[0]]
    center = raw[0] + n * (BRIDGE_OFFSET + frame.bridge_thickness / 2)

    u = np.array([u_xz[0], 0.0, u_xz[1]])
    u = u - np.dot(u, n) * n
    u /= np.linalg.norm(u)
    v = np.cross(n, u)
    if v[1] < 0:
        v = -v
    return TabFrame(
        center=_mirror(center, side),
        anchor=_mirror(raw[0], side),
        u=_mirror(u, side),
        v=_mirror(v, side),
        n=_mirror(n, side),
        neck_half_width=neck_half_width,
        head_half_width=head_half_width,
    )


def _collar_geometry(
    frame: FrameParams, plug: PlugParams, params: NoseParams, side: Literal[-1, 1]
) -> CollarGeometry:
    """レンズの位置・寸法を返す(鼻栓の位置とframe.collar_lengthだけで決まる)。"""
    r_inner, r_outer = _collar_radii(plug)
    outer_y = plug_outer_end(plug, params.nostril_gap, params.tip_depth_front, side)[1]
    y_start = outer_y + _COLLAR_PLUG_INSET
    return CollarGeometry(
        center_x=side * params.nostril_gap / 2,
        y_start=y_start,
        y_end=y_start + frame.collar_length,
        center_z=nostril_depth_z(params.tip_depth_front),
        r_inner=r_inner,
        r_outer=r_outer,
    )


def _side_follow_points(
    body: trimesh.Trimesh,
    params: NoseParams,
    x: float,
    y_start: float,
    offset: float,
    end_offset: float | None = None,
) -> np.ndarray:
    """高さをy_startから_SIDE_FOLLOW_END_Yまで下げながら、鼻の側面に沿わせた
    点列を返す(鼻の表面からoffsetだけ浮かせる)。xは始点(帯の下縁)の値。

    各高さで、帯と同じ式(角丸三角形の前面頂点から背面の角への辺)でzを
    求めるため、帯の下縁の点(_tab_frameのcenter)からちょうど連続する。

    xは一定ではなく、始点での「断面の直線の辺(_side_edge_span)の中での
    位置の比率」を保ったまま下ろす。鼻は鼻先へ向かって広がるため、xを
    固定すると棒が鼻の側面から内側(正面側)へ寄っていき、鼻孔の真上に
    降りてしまう。鼻孔の中心間を実測(14.0mm)に合わせて広げた際に、棒が
    レンズの穴を塞ぐ状態(lens_protrusion_margin違反)として表面化した
    ため、鼻の広がりに追従させている。
    """
    ys = np.linspace(y_start, _SIDE_FOLLOW_END_Y, _SIDE_FOLLOW_SAMPLES)
    inner, outer = _side_edge_span(params, float(y_start))
    ratio = (x - inner[0]) / (outer[0] - inner[0])
    raw = []
    for y in ys:
        x_at_y = _side_edge_x(params, float(y), ratio)
        raw.append([x_at_y, y, _edge_z_at(params, float(y), x_at_y)])
    offsets = np.linspace(offset, offset if end_offset is None else end_offset, len(ys))
    return _offset_along_surface_normal(body, np.array(raw), offsets[:, None])


def _hermite(
    p0: np.ndarray, m0: np.ndarray, p1: np.ndarray, m1: np.ndarray, samples: int
) -> np.ndarray:
    """3次エルミート曲線(p0で接線m0、p1で接線m1)の点列を返す。"""
    t = np.linspace(0.0, 1.0, samples)[:, None]
    h00 = 2 * t**3 - 3 * t**2 + 1
    h10 = t**3 - 2 * t**2 + t
    h01 = -2 * t**3 + 3 * t**2
    h11 = t**3 - t**2
    return h00 * p0 + h10 * m0 + h01 * p1 + h11 * m1


def _resample(points: np.ndarray, spacing: float) -> np.ndarray:
    """折れ線を、弧長でほぼspacing間隔の点列に取り直す(重複点は除く)。"""
    segment = np.linalg.norm(np.diff(points, axis=0), axis=1)
    points = points[np.concatenate([[True], segment > 1e-9])]
    arc = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))])
    count = max(int(np.ceil(arc[-1] / spacing)) + 1, 2)
    samples = np.linspace(0.0, arc[-1], count)
    return np.stack([np.interp(samples, arc, points[:, k]) for k in range(3)], axis=1)


def _rod_radii(
    frame: FrameParams, tab: TabFrame, collar: CollarGeometry, points: np.ndarray
) -> np.ndarray:
    """棒の点ごとの半径を返す。基本はleg_thickness/2で、次の範囲を
    越えないよう、なめらかに細くする。

    - 帯の近く: 帯の下縁より上(タブの首の中)では、帯の厚みの半分と首の
      半幅のうち小さい方。下縁から下へ離れるほど、離れた距離まで太く
      なってよい(その球が帯の下縁の面より上に届かないため、帯の厚みから
      はみ出さず、スロットの縁にもぶつからない。ユーザー指摘「アーチの
      太さに収まるように」)。下縁からの距離は、y座標の差ではなく帯の面内の
      v方向(TabFrame)で測る: 棒は鼻の側面に沿って降りる間にu方向(帯に
      沿った横方向)にもずれていくため、y差で測ると、下縁のずっと下にある
      太い球が、スロットから離れた位置で帯の下面に食い込む(実測: 組み
      立てた状態での帯と脚の重なりが2.1mm^3)。
    - レンズの近く: 球がレンズの下端(y_start)より下に出ず、内径(鼻栓の
      空間)にも入らない。さらにレンズの真上付近では、レンズの上端(y_end)
      も越えない(ユーザー指摘「レンズからはみ出さない
      ように」)。棒の軸はレンズの外周面(r_outer)の上を通る(_rod_path)
      ため、内径までの余裕は壁の肉厚そのものになり、レンズの厚み
      (collar_length)と壁の肉厚の両方をそのまま太さに使える(軸を壁の
      中心に置いていた以前は、太さが壁の肉厚の半分までに制限され、実測で
      直径0.71mmまで細くなって印刷できなかった)。
    - いずれの上限にも_ROD_LENS_GAPの余裕を見込む(面が一致して「触れる
      だけの関係」になるのを避ける)。

    最も細くなるのはレンズへ溶け込む区間で、その太さはrod_thickness_margin
    (GAの制約)が_MIN_ROD_DIAMETERを下回らないか監視する。
    """
    y = points[:, 1]
    rho = np.hypot(points[:, 0] - collar.center_x, points[:, 2] - collar.center_z)
    below_edge = -((points - tab.center) @ tab.v)
    near_tab = min(frame.bridge_thickness / 2, tab.neck_half_width)
    radii = np.full(len(points), frame.leg_thickness / 2)
    radii = np.minimum(radii, np.maximum(near_tab, below_edge))
    radii = np.minimum(radii, y - collar.y_start - _ROD_LENS_GAP)
    # 内径(鼻栓の空間)・上端に関する制限は、レンズの近く(上端から棒の
    # 太さ以内の高さ)の点にだけかける。高さを見ずに半径方向だけで判定すると、
    # レンズの軸の近くを通るタブ付近の点(レンズより10mm以上高い)まで
    # 巻き込み、そこで棒が極端に細くなってしまう(実測: 直径0.4mm)。
    # 上端の制限はさらに、中心がレンズの外周面より内側にある点(=レンズの
    # 真上にかかる点)だけに絞る。レンズの外側を立ち上がる区間にかけると、
    # 上端をまたぐ高さでやはり極端に細くなる
    # 鼻栓の空間(内径より内側の円筒)に入らないこと。レンズより上にある
    # 球は、半径方向に逃げても(rho-r_inner)、高さで逃げても(y-y_end。
    # 球がレンズの上面より上に収まる)よいので、緩い方を使う。以前は高さの
    # 逃げ道がなく、レンズの真上を通る区間で上面までの距離が負になって
    # 常に下限(_ROD_MIN_RADIUS)まで潰れていた(実測: 直径0.4mm)
    bore_allowance = rho - collar.r_inner - _ROD_LENS_GAP
    above_lens = y >= collar.y_end
    radii = np.minimum(
        radii,
        np.where(
            above_lens,
            np.maximum(bore_allowance, y - collar.y_end - _ROD_LENS_GAP),
            bore_allowance,
        ),
    )
    # 「レンズの厚みの範囲では上面も突き抜けない」という制限は置かない。
    # 棒は外周面(rho=r_outer)を降りて壁の中へ溶け込む設計なので、この
    # 制限をかけると溶け込み始める1点(y=y_endの真下)だけ上面までの距離が
    # ほぼ0になり、そこで棒が下限まで潰れる(実測: 直径0.4mm。rho<r_outerの
    # 判定が浮動小数点の誤差で変わるため、同じ形でも潰れたり潰れなかったり
    # する不安定さもあった)。上面から多少ふくらむのは輪と棒の継ぎ目として
    # 意図どおりで、鼻に当たるかはleg_clearance_margin・
    # collar_clearance_marginが別に見ている
    return np.maximum(radii, _ROD_MIN_RADIUS)


def _rod_path(
    frame: FrameParams,
    params: NoseParams,
    body: trimesh.Trimesh,
    tab: TabFrame,
    collar: CollarGeometry,
    side: Literal[-1, 1],
) -> RodPath:
    """棒の中心線と点ごとの半径を返す(モジュールdocstring「幾何」参照)。

    1. タブの首の中(帯の下縁から_TAB_NECK_LENGTHの半分だけ上)から始まる。
    2. 帯の下縁から_SIDE_FOLLOW_END_Yまで、帯の厚みの中央の高さで鼻の
       側面に沿って降りる(_side_follow_points)。
    3. レンズの輪の外周面(半径r_outer)の、鼻中隔と
       反対側(外側)の点を接点とし、レンズの厚みの中央の高さで、輪の
       接線方向(-z、鼻の前面側から後ろへ)から到達するエルミート曲線で
       つなぐ。到達時の接線にy成分がないため、棒はレンズの面の中で輪に
       接して入る(ユーザーのスケッチ「6d」)。
    4. 輪の外周面に沿って_ROD_JOINT_ARC_DEGだけ進み、輪の壁の中へ
       溶け込む(棒の半径は壁の肉厚まで使えるので、_rod_radiiが許す限り
       太いまま輪に繋がる)。
    まず+x側で計算してからsideで鏡映する。
    """
    canonical_anchor = _mirror(tab.anchor, side)
    start = _mirror(tab.center, side) + _mirror(tab.v, side) * (_TAB_NECK_LENGTH / 2)
    # 起点は鼻の表面上の点(anchor)で、そこから同じオフセットで浮かせる
    # (TabFrameのdocstring参照。side_follow[0]はちょうどtab.centerになる)
    # 鼻の表面からの浮かせ量は、帯との継ぎ目では帯の厚みの中央(タブと
    # 段差なくつながる高さ)だが、そのままだと棒が帯より太いとき(leg_
    # thickness>bridge_thickness)に棒の下側が鼻へ食い込む(実測: 既定
    # 形状でleg_clearance_marginの余裕が0.004mmしか残らなかった)。
    # 降りるにつれて棒の半径ぶんの高さへなめらかに移す
    side_follow = _side_follow_points(
        body,
        params,
        float(canonical_anchor[0]),
        float(canonical_anchor[1]),
        BRIDGE_OFFSET + frame.bridge_thickness / 2,
        BRIDGE_OFFSET + max(frame.bridge_thickness, frame.leg_thickness) / 2,
    )

    axis_x = abs(collar.center_x)
    # 棒の軸はレンズの外周面の上を通す(_rod_radiiのdocstring参照。壁の
    # 中心を通すと太さが壁の肉厚の半分までに制限され、印刷できない細さに
    # なるため)。棒はここから内側へ半径ぶん食い込み、壁と深く重なる
    r_arc = collar.r_outer
    y_mid = (collar.y_start + collar.y_end) / 2
    stem_start = side_follow[-1]
    # 接点は、輪の中心から見て棒が降りてきた向きにある外周上の点にする。
    # 以前は輪の最も外側(x最大)の点に固定していたが、鼻孔の中心間と
    # レンズの外径が大きくなると、降りてきた位置からそこへ回り込む途中で
    # 棒が穴の真上を横切り、鼻栓の入り口を塞いでいた(実測: 穴へ1.2mm
    # 食い込む)。降りてきた向きの点を使えば、棒は輪へ真っ直ぐ降りて
    # そのまま接線方向へ続く
    radial = np.array([stem_start[0] - axis_x, stem_start[2] - collar.center_z])
    radial /= np.linalg.norm(radial)
    start_angle = float(np.arctan2(radial[1], radial[0]))
    # 接点から、輪に沿って_ROD_JOINT_ARC_DEGだけ(角度が減る向き=鼻の
    # 前面側から背面側へ)進む
    angles = start_angle - np.radians(np.linspace(0.0, _ROD_JOINT_ARC_DEG, 8))
    arc = np.stack(
        [
            axis_x + r_arc * np.cos(angles),
            np.full(len(angles), y_mid),
            collar.center_z + r_arc * np.sin(angles),
        ],
        axis=1,
    )
    contact = arc[0]
    # 接点の真上(レンズの上面より棒の半径ぶん上)を経由してから、外周面に
    # 沿ってまっすぐ降りて輪に入る。エルミート曲線で接点へ直接つなぐと、
    # 棒が輪の壁(内径〜外径の間)を斜めに横切り、その区間で壁の残り厚み
    # (rho-r_inner)しか太さを使えず極端に細くなっていた(実測: 直径0.4mm)。
    # レンズより上では棒はいくら太くてもよい(_rod_radii参照)ので、横移動は
    # すべて上で済ませる
    hold = np.array([contact[0], collar.y_end + frame.leg_thickness / 2, contact[2]])
    direction = side_follow[-1] - side_follow[-2]
    direction /= np.linalg.norm(direction)
    span = float(np.linalg.norm(hold - stem_start))
    stem = _hermite(
        stem_start, direction * span, hold, np.array([0.0, -1.0, 0.0]) * span,
        _ROD_STEM_SAMPLES,
    )
    drop = np.linspace(hold, contact, _ROD_DROP_SAMPLES)
    stem = np.vstack([stem, drop[1:]])
    canonical = _resample(
        np.vstack([[start], side_follow, stem[1:], arc[1:]]), _ROD_SAMPLE_SPACING
    )
    points = canonical * np.array([side, 1.0, 1.0])
    return RodPath(points=points, radii=_rod_radii(frame, tab, collar, points))


def build_paths(
    frame: FrameParams, plug: PlugParams, params: NoseParams, body: trimesh.Trimesh
) -> FramePaths:
    """ブリッジの点列・左右の棒・左右のレンズの寸法を返す(メッシュ生成なし)。

    bodyは呼び出し側がbuild_nose_body(params)で構築済みのものを渡す
    (重複構築を避けるため)。
    """
    bridge = bridge_points(body, params)
    rods = {}
    collars = {}
    for side in (-1, 1):
        tab = _tab_frame(frame, params, body, side)
        collars[side] = _collar_geometry(frame, plug, params, side)
        rods[side] = _rod_path(frame, params, body, tab, collars[side], side)
    return bridge, rods[-1], rods[1], collars[-1], collars[1]


def _collar_mesh(geometry: CollarGeometry) -> trimesh.Trimesh:
    """CollarGeometryから、肉厚のある中空円筒(パイプ状)のメッシュを
    構築する(鼻栓はこの内側=筒の中へ差し込む想定)。

    trimesh.creation.annulusは既定でz軸に沿った円環(y方向の範囲は
    [-height/2, height/2])を返すため、commons.plug_model._build_plugの
    円柱と同じ手順(x軸まわりに90度回転してy軸に揃える)で向きを合わせる。
    """
    length = geometry.y_end - geometry.y_start
    mesh = trimesh.creation.annulus(
        r_min=geometry.r_inner, r_max=geometry.r_outer, height=length
    )
    rotate_to_y = trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0])
    mesh.apply_transform(rotate_to_y)
    y_mid = (geometry.y_start + geometry.y_end) / 2
    mesh.apply_translation([geometry.center_x, y_mid, geometry.center_z])
    return mesh


def _tab_polygon(tab: TabFrame, grow: float) -> Polygon:
    """タブの2次元の形(帯の面内の座標u・v)を返す。grow>0ならその分だけ
    外側に太らせた形(スロット用)を返す。

    首(幅=2*neck_half_width)は帯の下縁より_TAB_PRISM_BELOW_EDGEだけ下
    から_TAB_NECK_LENGTHまで。その上に、付け根の半幅head_half_width・先端の
    半幅neck_half_width*_TAB_TIP_RATIO・長さ_TAB_HEAD_LENGTHの矢じり形の
    頭を置く。付け根の段差(首の半幅→頭の半幅)が抜け止めの「返し」になる。
    """
    neck = tab.neck_half_width
    head = tab.head_half_width
    tip = neck * _TAB_TIP_RATIO
    top = _TAB_NECK_LENGTH + _TAB_HEAD_LENGTH
    polygon = Polygon(
        [
            (-neck, -_TAB_PRISM_BELOW_EDGE),
            (neck, -_TAB_PRISM_BELOW_EDGE),
            (neck, _TAB_NECK_LENGTH),
            (head, _TAB_NECK_LENGTH),
            (tip, top),
            (-tip, top),
            (-head, _TAB_NECK_LENGTH),
            (-neck, _TAB_NECK_LENGTH),
        ]
    )
    return polygon.buffer(grow, join_style="mitre") if grow > 0 else polygon


def _tab_prism(tab: TabFrame, grow: float, z_from: float | None = None) -> Manifold:
    """_tab_polygonを帯の法線方向(n)に押し出した角柱を返す。

    z_fromを省略すると帯の厚みの中央を中心に_TAB_PRISM_DEPTHだけ(帯を
    確実に貫通する長さ)押し出す。z_fromを指定すると、帯の面内座標系での
    その高さ(法線方向、中央が0、外側が正)から外側へだけ押し出す
    (_tab_slotの面取り用)。
    """
    z_low = -_TAB_PRISM_DEPTH / 2 if z_from is None else z_from
    mesh = trimesh.creation.extrude_polygon(
        _tab_polygon(tab, grow), _TAB_PRISM_DEPTH / 2 - z_low
    )
    mesh.apply_translation([0.0, 0.0, z_low])
    transform = np.eye(4)
    transform[:3, 0] = tab.u
    transform[:3, 1] = tab.v
    transform[:3, 2] = tab.n if np.linalg.det(np.stack([tab.u, tab.v, tab.n], 1)) > 0 else -tab.n
    transform[:3, 3] = tab.center
    mesh.apply_transform(transform)
    return _to_manifold(mesh)


def _tab_slot(tab: TabFrame, thickness: float) -> Manifold:
    """スロット(帯から切り取る側)の角柱を返す。

    タブより_TAB_CLEARANCEだけ太い角柱に、帯の外側の面から
    _TAB_LEAD_IN_DEPTHの深さまで、外側ほど広がる面取り(リードイン)を
    _TAB_LEAD_IN_STEPS段の階段で近似して重ねる。タブが多少ずれていても、
    押し込むだけで位置が決まって入る(ユーザー要望「細かな印刷でも上手く
    連結できるような工夫」)。段はいずれも帯を貫通する長さまで外側へ
    伸ばすため互いに深く重なり、ブーリアン結合が安定する。
    """
    prisms = [_tab_prism(tab, _TAB_CLEARANCE)]
    for step in range(1, _TAB_LEAD_IN_STEPS + 1):
        grow = _TAB_CLEARANCE + _TAB_LEAD_IN * step / _TAB_LEAD_IN_STEPS
        z_from = thickness / 2 - _TAB_LEAD_IN_DEPTH * (
            _TAB_LEAD_IN_STEPS - step + 1
        ) / _TAB_LEAD_IN_STEPS
        prisms.append(_tab_prism(tab, grow, z_from))
    return Manifold.batch_boolean(prisms, OpType.Add)


def _to_manifold(mesh: trimesh.Trimesh) -> Manifold:
    """trimeshの閉じたメッシュをmanifold3dのManifoldに変換する。"""
    return Manifold(
        Mesh(
            vert_properties=np.asarray(mesh.vertices, dtype=np.float32),
            tri_verts=np.asarray(mesh.faces, dtype=np.uint32),
        )
    )


def _to_trimesh(manifold: Manifold) -> trimesh.Trimesh:
    """manifold3dのManifoldを、連結成分・退化面の後処理をしたtrimeshに変換する。"""
    mesh = manifold.to_mesh()
    result = trimesh.Trimesh(
        vertices=mesh.vert_properties[:, :3], faces=mesh.tri_verts, process=True
    )
    return _clean_boolean_result(_largest_component(result))


def _rod_manifold(rod: RodPath) -> Manifold:
    """棒を、隣り合う2点の球(半径は点ごと)の凸包を連ねて結合した立体にする。

    凸包は常に閉じた凸立体で、隣り合う凸包は球1個分まるごと重なるため、
    触れるだけの関係が生じずブーリアン結合が安定する。半径が点ごとに違う
    場合も、凸包が2つの球をなめらかにつなぐテーパーになる。
    """
    spheres = [
        Manifold.sphere(float(radius), _ROD_SPHERE_SEGMENTS).translate(
            tuple(float(c) for c in point)
        )
        for point, radius in zip(rod.points, rod.radii)
    ]
    hulls = [Manifold.batch_hull([a, b]) for a, b in zip(spheres[:-1], spheres[1:])]
    return Manifold.batch_boolean(hulls, OpType.Add)


def _clean_boolean_result(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """ブーリアン演算(manifold3d)の結果から、位置ベースの頂点マージで
    露呈するdegenerate面(3頂点のうち2つが同一座標に退化した、面積ほぼ0の
    三角形)を取り除く。

    build_bridge_pieceの出力は、メモリ上ではis_watertight/is_volumeが
    Trueになる(trimeshの標準の水密判定は頂点のINDEXの対応関係だけを見る
    ため)が、STL等へ書き出して読み直す(=座標ベースで頂点を再統合する
    処理を経る)と、同一座標にもかかわらず別々のindexを持っていた頂点が
    1つに統合され、is_watertight=Falseになることが実測でわかった(3D
    プリント用に書き出すファイルこそが実際に重要なため、これは見過ごせない
    不具合)。ユーザーがview_nose.pyでSTLを開き直した際に「穴が空いてない
    ように見える」と報告したのがこの症状で、実際には差分(穴)自体は
    正しく開いていたが、上記の座標統合後に露呈するdegenerate面が
    non-manifoldな縁(78本、4面で共有される辺)を作っていたため、ビューア
    (trimesh経由)が正しく閉じた立体として扱えていなかった。

    根本原因は、manifold3dのブーリアン出力が、面同士が浅い角度で接する
    箇所(帯とスロットの角柱の交差など)に、ほぼ同一座標の
    頂点を複数の別indexで重複して持つこと(scipy.spatial.cKDTreeで
    厳密に距離0のペアを複数実測で確認)。trimeshのmerge_vertices()で
    座標ベースに統合すると、これらの三角形の3頂点のうち2つが同一indexに
    潰れる(例: 面[51, 54, 54])。

    除去には、trimesh標準のnondegenerate_faces()(面積・オリエンテッド
    バウンディングボックスの短辺の長さで判定)ではなく、「3頂点のうち
    2つ以上のindexが一致している」という直接的な条件を使う。実測で、
    nondegenerate_faces()の面積ベースの判定は誤検出することがわかった:
    棒+レンズの部品(build_leg_piece)では、merge_vertices()自体は頂点を
    1つも統合しない(=このバグに該当する重複頂点が元々存在しない)のに、
    nondegenerate_faces()がたまたま面積の小さい(だが3頂点とも別indexの、
    正当な)三角形を1つ誤って検出し、それを取り除くとメッシュに本物の
    穴が開いてwatertight=Falseになってしまった(脚の断面と筒の接続部に
    実際に存在する細い三角形)。index一致による判定はこの種の誤検出を
    起こさない(実測: 上記のブリッジの78個の退化面はすべてこの条件に
    合致し、除去後にis_watertight/is_volumeが座標統合後もTrueになり、
    STLへの書き出し→読み直し後もTrueのままになることを確認。一方、脚の
    部品ではこの条件に合致する面が0個で、何も除去されない)。
    """
    mesh = mesh.copy()
    mesh.merge_vertices()
    faces = mesh.faces
    has_duplicate_index = (
        (faces[:, 0] == faces[:, 1])
        | (faces[:, 1] == faces[:, 2])
        | (faces[:, 0] == faces[:, 2])
    )
    mesh.update_faces(~has_duplicate_index)
    mesh.remove_unreferenced_vertices()
    return mesh


def _largest_component(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """meshの連結成分のうち、体積(絶対値)が最大のものを返す(1つしかなければ
    meshをそのまま返す)。

    ブーリアン演算の数値的な丸めに由来する、体積がほぼ0の破片を取り除く。
    捨てる成分の体積の合計が最大成分の1%を超える場合は、意図した形状の
    一部が分離したとみなし例外を送出する(符号付きの体積のまま比較すると、
    向きの乱れた負の体積の大きな成分を見逃すため絶対値で比較する)。
    """
    parts = mesh.split(only_watertight=False)
    if len(parts) <= 1:
        return mesh
    parts_by_volume = sorted(parts, key=lambda part: abs(part.volume), reverse=True)
    largest = parts_by_volume[0]
    discarded_volume = sum(abs(part.volume) for part in parts_by_volume[1:])
    if discarded_volume > abs(largest.volume) * 0.01:
        raise ValueError(
            f"ブーリアン演算の結果が{len(parts)}個の連結成分に分裂し、"
            f"捨てる分(体積合計{discarded_volume:.3f}mm^3)が無視できない"
            f"(最大成分{abs(largest.volume):.3f}mm^3の1%超)"
        )
    return largest


def _surface_normals(body: trimesh.Trimesh, points: np.ndarray) -> np.ndarray:
    """各点に最も近い鼻本体メッシュの三角形の法線を返す(正規化前)。
    _ribbon_meshがブリッジの格子点の各点の向きを決めるために使う。

    _offset_along_surface_normalと同じ最近接三角形の法線を求める処理だが、
    すでにオフセット済みの点(表面のごく近く)に対して法線だけを求め直す
    (点自体は動かさない)。
    """
    _, _, triangle_id = trimesh.proximity.closest_point(body, points)
    return body.face_normals[triangle_id]
def _ribbon_mesh(
    body: trimesh.Trimesh, params: NoseParams, width: float, thickness: float
) -> trimesh.Trimesh:
    """幅width(y方向)×厚みthickness(表面法線方向)の帯状のメッシュ
    (ブリーズライトの平べったいテープを模したブリッジ)を、鼻の表面に
    沿わせて構築する(棒(_rod_manifold、球の凸包の連なり)と対になる、
    平らな断面専用の構築)。

    _bridge_gridで得た格子点(_BRIDGE_WIDTH_SAMPLES行×13列、幅方向にも
    鼻の実際の丸みに沿う)を、鼻の表面(BRIDGE_OFFSET)からthicknessだけ
    離れた2枚の格子(bottom・top)としてオフセットし、その間を側面で
    閉じた1つのシェル(殻)にする。1次元の経路をwidth方向に単純に
    平行移動するだけの以前の実装は、鼻の断面が高さによって変わることを
    無視するため、
    bridge_widthが大きいほど実際の鼻の丸みから外れた形になっていた
    (_bridge_gridのdocstring参照)。

    面の向き(winding)は、平坦な格子・実際の湾曲した格子の両方で
    is_volume(閉じた向き一貫の立体)になることを確認済みの組み合わせ
    (下面はa,c,b/a,d,c、上面はa,b,c/a,c,d、側面はwall関数のreverse
    フラグの通り)。
    """
    grid = _bridge_grid(params, width)
    rows, cols, _ = grid.shape
    flat = grid.reshape(-1, 3)
    normals = _surface_normals(body, flat)
    normals = normals / np.linalg.norm(normals, axis=1, keepdims=True)
    bottom = flat + normals * BRIDGE_OFFSET
    top = flat + normals * (BRIDGE_OFFSET + thickness)
    vertices = np.concatenate([bottom, top], axis=0)

    def bottom_index(r: int, c: int) -> int:
        return r * cols + c

    def top_index(r: int, c: int) -> int:
        return rows * cols + r * cols + c

    faces = []
    for r in range(rows - 1):
        for c in range(cols - 1):
            a, b, cc, d = (
                bottom_index(r, c),
                bottom_index(r, c + 1),
                bottom_index(r + 1, c + 1),
                bottom_index(r + 1, c),
            )
            faces.append([a, cc, b])
            faces.append([a, d, cc])
    for r in range(rows - 1):
        for c in range(cols - 1):
            a, b, cc, d = (
                top_index(r, c),
                top_index(r, c + 1),
                top_index(r + 1, c + 1),
                top_index(r + 1, c),
            )
            faces.append([a, b, cc])
            faces.append([a, cc, d])

    def wall(bottom_line: list[int], top_line: list[int], reverse: bool) -> None:
        for i in range(len(bottom_line) - 1):
            a, b = bottom_line[i], bottom_line[i + 1]
            c, d = top_line[i + 1], top_line[i]
            if reverse:
                a, b, c, d = b, a, d, c
            faces.append([a, b, c])
            faces.append([a, c, d])

    wall(
        [bottom_index(0, c) for c in range(cols)],
        [top_index(0, c) for c in range(cols)],
        reverse=False,
    )
    wall(
        [bottom_index(rows - 1, c) for c in range(cols)],
        [top_index(rows - 1, c) for c in range(cols)],
        reverse=True,
    )
    wall(
        [bottom_index(r, 0) for r in range(rows)],
        [top_index(r, 0) for r in range(rows)],
        reverse=True,
    )
    wall(
        [bottom_index(r, cols - 1) for r in range(rows)],
        [top_index(r, cols - 1) for r in range(rows)],
        reverse=False,
    )

    mesh = trimesh.Trimesh(vertices=vertices, faces=np.array(faces), process=True)
    # 面の頂点順(winding)は上の組み立てで一貫した向きになるが、外向き/
    # 内向きの向き自体は鼻の実際の法線の向き次第で反転しうるため、体積が
    # 負(=内向き)ならまとめて反転する
    if mesh.volume < 0:
        mesh.invert()
    return mesh
def _signed_distance_to_body(
    body: trimesh.Trimesh, points: np.ndarray
) -> np.ndarray:
    """各点から鼻本体表面までの符号付き距離を返す(正=外側、負=内側/めり込み)。

    earrings/spiralの_signed_distance_to_bodyと同一実装。
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
    検証する。earrings/spiralのvalidate_target_reachと同じ。
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
def validate_collar_no_overlap(plug: PlugParams, params: NoseParams) -> None:
    """左右の筒(collar)の外径同士が重なっていないことを検証する。

    中空円筒(穴の空いた形状)同士が重なると、ブーリアン結合
    (manifold3d)がうまく解決できず、とがった破片が残ることをユーザーが
    実際に3Dプリントした結果で確認した(_COLLAR_WALL_THICKNESSのコメント
    参照)。筒の外径(_collar_radii)はNoseParams・PlugParamsの固定値
    (_COLLAR_WALL_THICKNESSも定数)だけで決まりframeに依存しないため、
    validate_target_reachと同じく常に例外を送出する(GAの制約には
    含めない。frameを変えても結果が変わらない値を制約にしても意味が
    ないため)。_COLLAR_WALL_THICKNESSをこの検証に通るよう選んでいるので
    通常は発生しないが、NoseParams(nostril_gap)やPlugParams(diameter)を
    変更した場合の安全装置として置く。
    """
    _, r_outer = _collar_radii(plug)
    overlap = 2 * r_outer - params.nostril_gap
    if overlap > 0:
        raise ValueError(
            f"左右の筒(外径{r_outer:.2f}mm)が{overlap:.3f}mm重なっている。"
            "_COLLAR_WALL_THICKNESSを小さくするか、PlugParams.diameterを"
            "見直すこと"
        )
def curvature_margin(frame: FrameParams, bridge: list[np.ndarray]) -> float:
    """natural_radiusが、装着後の実際の曲率半径(actual_radius)の
    _MIN_CURVATURE_RATIO倍以上あるかを返す(正=不足量、0以下=十分平ら)。

    natural_radius(自然な曲率半径)がactual_radius(装着後の実際の曲率
    半径)以下だと、装着してもブリッジが自然な形よりむしろ緩まる(拡張力が
    発生しない、または逆に締まる)方向になってしまう(モジュールdocstring
    「拡張力の物理近似」参照)。frameに依存する(natural_radiusの探索、かつ
    actual_radiusはbridge_width/bridge_thicknessに依存しないがブリッジの
    経路自体はframeに依存しないため実質NoseParamsだけで決まる)ため、
    evaluate_frameは例外で止めずこの値を制約として使う。
    """
    actual_radius, _ = bridge_curvature(bridge)
    return actual_radius * _MIN_CURVATURE_RATIO - frame.natural_radius
def validate_curvature(frame: FrameParams, bridge: list[np.ndarray]) -> None:
    """curvature_marginが正(=違反)の場合に例外を送出する。"""
    margin = curvature_margin(frame, bridge)
    if margin > _MARGIN_TOLERANCE:
        raise ValueError(
            f"natural_radius({frame.natural_radius})が、装着後の実際の曲率"
            f"半径の{_MIN_CURVATURE_RATIO}倍に{margin:.3f}mm足りない。"
            "natural_radiusを大きくする(より平らにする)こと"
        )
def bridge_clearance_margin(
    frame: FrameParams, params: NoseParams, body: trimesh.Trimesh
) -> float:
    """ブリッジ(長方形断面のリボン)の実際の頂点の鼻本体メッシュへの
    めり込み量が、厚みに比例した許容量(_EMBED_RATIO)を超えていないかを
    返す(正=超過量、0以下=許容範囲内)。earrings.frame_model.
    ring_clearance_marginと同じ考え方(ブリッジは鼻表面に沿わせて曲げる
    設計だが、押し込みは意図していないため、長方形断面が曲面と完全に
    一致しないことに由来する残留めり込みの水準までしか許容しない)。
    """
    radius = frame.bridge_thickness / 2
    allowed_embed = _EMBED_RATIO * radius
    ribbon = _ribbon_mesh(body, params, frame.bridge_width, frame.bridge_thickness)
    signed_distance = _signed_distance_to_body(body, ribbon.vertices)
    embed_amount = -signed_distance
    return float((embed_amount - allowed_embed).max())
def validate_bridge_clearance(
    frame: FrameParams, params: NoseParams, body: trimesh.Trimesh
) -> None:
    """bridge_clearance_marginが正(=違反)の場合に例外を送出する。"""
    margin = bridge_clearance_margin(frame, params, body)
    if margin > _MARGIN_TOLERANCE:
        raise ValueError(
            f"bridge_thickness({frame.bridge_thickness})のリボンが、厚みに"
            f"比例した許容めり込み量(_EMBED_RATIO={_EMBED_RATIO})を"
            f"{margin:.3f}mm超えて実際に鼻表面へめり込んでいる"
        )


def leg_clearance_margin(rods: list[RodPath], body: trimesh.Trimesh) -> float:
    """棒(点ごとの半径の球の連なり)の鼻本体メッシュへのめり込み量が、
    その点の半径に比例した許容量(_EMBED_RATIO)を超えていないかを返す
    (正=超過量、0以下=許容範囲内。左右のうち厳しい方)。

    棒はレンズへ向かう途中で鼻の下端(tip_cap_min_y、鼻本体メッシュが
    y方向に途切れる開いた縁)の近くを通るため、疑似法線による符号判定
    (_signed_distance_to_body)は誤判定する(実測: 鼻の外の点を
    「めり込み1.4mm」と判定した)。trimesh.Trimesh.containsによる正確な
    内外判定で符号を決める(collar_clearance_marginと同じ)。
    """
    worst = -np.inf
    for rod in rods:
        _, distance, _ = trimesh.proximity.closest_point(body, rod.points)
        inside = body.contains(rod.points)
        signed = np.where(inside, -distance, distance)
        embed = rod.radii - signed
        worst = max(worst, float((embed - _EMBED_RATIO * rod.radii).max()))
    return worst


def validate_leg_clearance(rods: list[RodPath], body: trimesh.Trimesh) -> None:
    """leg_clearance_marginが正(=違反)の場合に例外を送出する。"""
    margin = leg_clearance_margin(rods, body)
    if margin > _MARGIN_TOLERANCE:
        raise ValueError(
            f"棒が、線径に比例した許容めり込み量(_EMBED_RATIO={_EMBED_RATIO})を"
            f"{margin:.3f}mm超えて鼻表面へめり込んでいる"
        )


def lens_protrusion_margin(rods: list[RodPath], collars: list[CollarGeometry]) -> float:
    """棒がレンズからはみ出していないかを返す(正=はみ出し量、0以下=収まって
    いる。左右のうち厳しい方)。

    ユーザー指摘(「レンズからはみ出てる」「レンズからはみ出さないように」)の
    判定。棒の各点の球について、
    - レンズの外径の内側(中心軸からの距離-半径<r_outer)にかかる球の下端が、
      レンズの下端(y_start)より下に出ていないか
    - レンズの厚みの範囲にかかる球の内側の端が、内径(鼻栓の空間)に
      入っていないか
    を調べ、最大のはみ出し量を返す。_rod_radiiはこれを満たすように太さを
    決めるが、太さの下限(_ROD_MIN_RADIUS_RATIO)で打ち切られる場合や、
    経路の変更で満たせなくなった場合をGAの制約として検出する。
    """
    worst = -np.inf
    for rod, collar in zip(rods, collars):
        y = rod.points[:, 1]
        r = rod.radii
        rho = np.hypot(rod.points[:, 0] - collar.center_x, rod.points[:, 2] - collar.center_z)
        over_footprint = rho - r < collar.r_outer
        below = np.where(over_footprint, collar.y_start - (y - r), -np.inf)
        within_height = (y - r < collar.y_end) & (y + r > collar.y_start)
        into_hole = np.where(within_height, collar.r_inner - (rho - r), -np.inf)
        worst = max(worst, float(below.max()), float(into_hole.max()))
    return worst


def validate_lens_protrusion(rods: list[RodPath], collars: list[CollarGeometry]) -> None:
    """lens_protrusion_marginが正(=違反)の場合に例外を送出する。"""
    margin = lens_protrusion_margin(rods, collars)
    if margin > _MARGIN_TOLERANCE:
        raise ValueError(f"棒がレンズから{margin:.3f}mmはみ出している")


def rod_thickness_margin(rods: list[RodPath]) -> float:
    """棒の最も細いところの直径が、印刷に必要な最小値(_MIN_ROD_DIAMETER)を
    下回っていないかを返す(正=不足量、0以下=十分。左右のうち厳しい方)。

    ユーザー指摘(「レンズ部分とそれの棒の部分もう少し太くしてください。
    印刷時に上手く印刷できないので」)への対応。棒はレンズへ溶け込む区間で
    最も細くなり、その太さはレンズの壁の肉厚(_COLLAR_WALL_THICKNESS)と
    レンズの厚み(frame.collar_length)で決まる(_rod_radii参照)ため、
    collar_lengthが小さい個体をGAが避けるように誘導する。
    """
    thinnest = min(float(rod.radii.min()) * 2 for rod in rods)
    return _MIN_ROD_DIAMETER - thinnest


def validate_rod_thickness(rods: list[RodPath]) -> None:
    """rod_thickness_marginが正(=違反)の場合に例外を送出する。"""
    margin = rod_thickness_margin(rods)
    if margin > _MARGIN_TOLERANCE:
        raise ValueError(
            f"棒の最も細いところが、印刷に必要な最小直径({_MIN_ROD_DIAMETER}mm)に"
            f"{margin:.3f}mm足りない。collar_lengthを大きくすること"
        )


def tab_retention_margin(frame: FrameParams) -> float:
    """嵌め込みの「返し」が実際に引っかかる量(タブの頭の張り出しから
    はめあいの隙間を引いた残り)が、最小値(_MIN_TAB_RETENTION)を下回って
    いないかを返す(正=不足量、0以下=十分)。

    スロットはタブより_TAB_CLEARANCEだけ大きいため、tab_head_oversizeが
    それに近いと「返し」が実質的に効かず、押し込んでも抜けてしまう。
    """
    return _MIN_TAB_RETENTION - (frame.tab_head_oversize - _TAB_CLEARANCE)


def validate_tab_retention(frame: FrameParams) -> None:
    """tab_retention_marginが正(=違反)の場合に例外を送出する。"""
    margin = tab_retention_margin(frame)
    if margin > _MARGIN_TOLERANCE:
        raise ValueError(
            f"タブの返しの引っかかりが最小値({_MIN_TAB_RETENTION}mm)に"
            f"{margin:.3f}mm足りない。tab_head_oversizeを大きくすること"
        )


def tab_fit_margin(frame: FrameParams, params: NoseParams) -> float:
    """スロットが帯の中に、周りに_TAB_MIN_WALLの肉を残して収まるかを返す
    (正=不足量、0以下=収まる)。

    - 縦(帯の幅方向): 首+頭+_TAB_CLEARANCE+_TAB_MIN_WALLが、bridge_width
      以下であること(スロットの上に肉が残り、帯が上下に分断されない)。
    - 横(帯に沿った方向): スロット(タブ+はめあい+周りに残す肉)が、断面の
      直線の辺(_side_edge_span)の中に、内側・外側とも収まること。丸め弧の
      部分にかかると、タブの平らな角柱と帯の曲面がずれて嵌め込みの面が
      合わず、さらに外側へ出ると帯そのものが鼻から浮く。
    """
    vertical = (
        _TAB_NECK_LENGTH + _TAB_HEAD_LENGTH + _TAB_CLEARANCE + _TAB_MIN_WALL
    ) - frame.bridge_width

    y_edge = _BRIDGE_Y - frame.bridge_width / 2
    x_end = _side_edge_x(params, _BRIDGE_Y + frame.bridge_width / 2, _BRIDGE_SIDE_EDGE_RATIO)
    half_width, depth_back, depth_front = surface_profile_at(params, y_edge)
    edge_slope = (-depth_back - depth_front) / half_width
    u_x = 1.0 / np.hypot(1.0, edge_slope)
    head_half_width = frame.leg_thickness / 2 + frame.tab_head_oversize
    inset = head_half_width + _TAB_CLEARANCE + _TAB_MIN_WALL
    inner_edge_x = x_end - 2 * inset * u_x
    inner, outer = _side_edge_span(params, y_edge)
    lateral = max(float(inner[0]) - inner_edge_x, x_end - float(outer[0]))
    return max(vertical, lateral)


def validate_tab_fit(frame: FrameParams, params: NoseParams) -> None:
    """tab_fit_marginが正(=違反)の場合に例外を送出する。"""
    margin = tab_fit_margin(frame, params)
    if margin > _MARGIN_TOLERANCE:
        raise ValueError(
            f"タブのスロットが帯に収まらない(不足{margin:.3f}mm)。bridge_widthを"
            "大きくするか、leg_thickness/tab_head_oversizeを小さくすること"
        )


def tab_thickness_margin(frame: FrameParams) -> float:
    """タブ(=帯と同じ厚み)が印刷・嵌め込みに耐える厚みかを返す
    (正=不足量、0以下=十分)。_MIN_TAB_THICKNESS参照。
    """
    return _MIN_TAB_THICKNESS - frame.bridge_thickness


def validate_tab_thickness(frame: FrameParams) -> None:
    """tab_thickness_marginが正(=違反)の場合に例外を送出する。"""
    margin = tab_thickness_margin(frame)
    if margin > _MARGIN_TOLERANCE:
        raise ValueError(
            f"bridge_thickness({frame.bridge_thickness})がタブの最小の厚み"
            f"({_MIN_TAB_THICKNESS}mm)に{margin:.3f}mm足りない"
        )


def collar_clearance_margin(
    collars: list[CollarGeometry], body: trimesh.Trimesh
) -> float:
    """左右の筒(collar)が、鼻本体メッシュにめり込んでいないかを返す
    (正=めり込み量、0以下=安全)。左右のうち最も厳しい点の値。

    筒は鼻栓を取り囲む空間(鼻孔の外、鼻栓の露出部分の周り)を通る想定で、
    脚とは異なり鼻表面に沿わせる意図がないため、めり込みは一切許容しない
    (以前のstem_clearance_marginと同じ方針)。

    _tube_clearance_margin(疑似法線による符号判定、bridge_clearance_
    margin・leg_clearance_marginが使う)は使わず、trimesh.Trimesh.
    containsによる正確な内外判定を直接使う。筒は鼻の下端(commons.
    nose_model.tip_cap_min_y、鼻本体メッシュがy方向に途切れる開いた縁)の
    すぐ近くを通ることがあり、その境界付近では疑似法線による符号判定が
    誤判定する(実測: 鼻の外(contains()=False)にある点を、疑似法線は
    「めり込んでいる」と誤って判定した)。containsはレイキャストによる
    正確な判定で、この境界付近でも誤らない。
    """
    worst = -1.0
    for geometry in collars:
        mesh = _collar_mesh(geometry)
        inside = body.contains(mesh.vertices)
        if np.any(inside):
            _, distance, _ = trimesh.proximity.closest_point(body, mesh.vertices[inside])
            worst = max(worst, float(distance.max()))
    return worst
def validate_collar_clearance(collars: list[CollarGeometry], body: trimesh.Trimesh) -> None:
    """collar_clearance_marginが正(=めり込み)の場合に例外を送出する。"""
    margin = collar_clearance_margin(collars, body)
    if margin > _MARGIN_TOLERANCE:
        raise ValueError(
            f"筒(collar)が実際に鼻表面へめり込んでいる(最大めり込み量: "
            f"{margin:.3f}mm)。筒が鼻孔の壁や中隔と交差している可能性が"
            "ある(leg_thicknessを小さくすること)"
        )


def collar_position_margin(
    plug: PlugParams, params: NoseParams, collar: CollarGeometry, side: Literal[-1, 1]
) -> float:
    """レンズのy方向の範囲が、鼻栓の全長(露出端から奥まで)からはみ出して
    いる量を返す(正=違反量、0以下=鼻栓の範囲内)。
    """
    outer_y = plug_outer_end(plug, params.nostril_gap, params.tip_depth_front, side)[1]
    below = outer_y - collar.y_start
    above = collar.y_end - (outer_y + plug.length)
    return max(below, above)


def validate_collar_position(
    plug: PlugParams, params: NoseParams, collar: CollarGeometry, side: Literal[-1, 1]
) -> None:
    """collar_position_marginが正(=違反)の場合に例外を送出する。"""
    margin = collar_position_margin(plug, params, collar, side)
    if margin > _MARGIN_TOLERANCE:
        raise ValueError(
            f"レンズが鼻栓の範囲から{margin:.3f}mmはみ出している。collar_lengthを見直すこと"
        )


def build_bridge_piece(frame: FrameParams, params: NoseParams) -> trimesh.Trimesh:
    """ブリッジ単体(平らな帯)を、左右のタブを嵌めるスロット付きで構築する
    (着色済み)。

    スロットは、帯の下縁から帯の厚み方向に貫通する矢じり形の切り欠き
    (_tab_slot)。左右の脚のタブを帯の面の法線方向から押し込んで嵌める
    (ジョイントマットと同じ)。差し口(帯の外側の面)には、押し込むだけで
    位置が決まるよう面取り(リードイン)を付ける。
    """
    validate_tab_thickness(frame)
    validate_tab_retention(frame)
    validate_tab_fit(frame, params)
    body = build_nose_body(params)
    validate_curvature(frame, bridge_points(body, params))
    validate_bridge_clearance(frame, params, body)

    ribbon = _to_manifold(
        _ribbon_mesh(body, params, frame.bridge_width, frame.bridge_thickness)
    )
    slots = [
        _tab_slot(_tab_frame(frame, params, body, side), frame.bridge_thickness)
        for side in (-1, 1)
    ]
    mesh = _to_trimesh(Manifold.batch_boolean([ribbon, *slots], OpType.Subtract))
    mesh.visual.face_colors = _FRAME_COLOR
    return mesh


def build_leg_piece(
    frame: FrameParams, plug: PlugParams, params: NoseParams, side: Literal[-1, 1]
) -> trimesh.Trimesh:
    """左右いずれか片側の、タブ+棒+レンズを単一の部品として構築する
    (着色済み)。

    タブは帯とタブの角柱の共通部分(帯と完全に同じ面・同じ厚み)。棒は
    _rod_manifold(球の凸包の連なり)、レンズは中空円筒。3つはいずれも
    深く重なる(棒の始点はタブの首の中、棒の終端は輪の壁の中)ため、
    触れるだけの関係にならない。
    """
    validate_target_reach(plug, params)
    validate_collar_no_overlap(plug, params)
    validate_tab_thickness(frame)
    validate_tab_retention(frame)
    validate_tab_fit(frame, params)
    body = build_nose_body(params)
    tab = _tab_frame(frame, params, body, side)
    collar = _collar_geometry(frame, plug, params, side)
    rod = _rod_path(frame, params, body, tab, collar, side)
    validate_leg_clearance([rod], body)
    validate_collar_clearance([collar], body)
    validate_collar_position(plug, params, collar, side)
    validate_lens_protrusion([rod], [collar])
    validate_rod_thickness([rod])

    ribbon = _to_manifold(
        _ribbon_mesh(body, params, frame.bridge_width, frame.bridge_thickness)
    )
    tab_solid = ribbon ^ _tab_prism(tab, 0.0)
    lens = _to_manifold(_collar_mesh(collar))
    mesh = _to_trimesh(
        Manifold.batch_boolean([_rod_manifold(rod), lens, tab_solid], OpType.Add)
    )
    mesh.visual.face_colors = _FRAME_COLOR
    return mesh
