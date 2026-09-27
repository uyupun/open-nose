"""フレームの仮形状(FrameParamsの8変数): 平べったいブリッジ+左右の脚
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
右の脚(棒とレンズ)の3部品に分け、連結部(既定は、脚の上端の小さなC字が
帯の上下の縁を抱く「帯を抱くC」)で組み立てる。

## 経緯(実測画像を見たユーザーからの指摘への対応。現在も有効な教訓のみ)

- ブリッジは円形断面のチューブではなく、幅(bridge_width)×厚み
  (bridge_thickness)の平らな帯にする(「ブリーズライト同様に平べったく」)。
  帯は鼻の断面(前面の丸め弧+側面の直線の辺)に沿わせるが、両端は
  背面角の丸みに沿って巻き込ませず、まっすぐ伸ばす(_bridge_profile。
  ユーザー指摘「両端の丸みを帯びさせず、アーチをキープするのが良さそう」)。
  一度は帯全体を一定の曲率の円弧にしたが、鼻の側面から浮いて「アーチ状が
  平べったすぎる。前と同じくらいのアーチ状がいい」となり、いまの形にした。
- 印刷するブリッジは、装着した形そのものではなく、その曲がりを
  actual_radius/natural_radiusの割合に弱めた(少し開いた)形にする
  (build_bridge_print_piece・_print_profile)。装着した形のまま印刷すると、
  鼻の上で曲げたときの戻りが生じず、拡張力が出ない。
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
  (1) 帯と脚の連結: 当初は帯の下縁に矢じり形のスロットを切り、脚側の
      タブを押し込む嵌め込みにしたが、その後、帯の下縁を挟むエッジ
      クリップに置き換え、さらに帯を抱くCに置き換えた(下の「幾何」参照)。
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

- **ブリッジ(_bridge_profile/bridge_points/_bridge_grid/_band_mesh)**: 装着した
  形。高さごとに、断面の前面の丸め弧と両側の直線の辺(tab_side_ratioの
  位置まで。1を超えるぶんは辺の向きのまままっすぐ伸ばす)を表面から
  BRIDGE_OFFSETだけ浮かせた曲線を、bridge_y±bridge_width/2の範囲で
  格子状にロフトし、その曲線(肌側の面)から外向きにbridge_thicknessの帯に
  する。両端のうち肌から_TAPE_MAX_GAP以内の区間が両面テープの貼り代
  (_tape_pad)。
- **印刷するブリッジ(build_bridge_print_piece/_print_profile)**: 装着した形と
  同じ弧長・幅・厚みで、曲がりをactual_radius/natural_radiusの割合に
  弱めた形。
- **連結部(_tab_frame/_cuff_groove_local/_cuff_local/_leg_connector)**: 帯の端から
  内側へ入った位置(_tab_frame)の、帯の面内の局所座標(u=帯に沿って帯の端へ
  向かう向き、v=帯の下縁から上向き、n=外向き。_joint_to_worldで帯の曲がりに
  沿って曲げる)で作る。脚の上端が棒と同じ幅の小さなC字になって帯の上下の
  縁を抱き、爪先が縁のV溝(帯の端近くに浅い段)に入る「帯を抱くC」(ユーザーが
  3案の試作を見比べて選んだ)。脚は単体でも使うので、脚側は棒の上端の形
  そのものが連結部を兼ね、仕掛け(溝)は帯の側に置く。
- **棒(_rod_path/_rod_radii/_blade_manifold)**: 連結部の脚側の形の中から始まり(_connector_rod_start)、
  (帯の浮きの高さから肌へ寄りながら)鼻の側面を鼻翼の溝へ向かって_SIDE_FOLLOW_END_Yまで降り(_side_follow_points)、
  レンズの面の高さ(筒の厚みの中央)で輪の外側の接点に接線方向から到達する
  エルミート曲線を通り、輪の壁の中心線に沿って_ROD_JOINT_ARC_DEGだけ
  進む。
- **レンズ(_collar_geometry/_collar_mesh)**: 鼻栓の軸を中心にした中空円筒。
  鼻栓の露出端からわずか(_COLLAR_PLUG_INSET)奥から、frame.collar_length
  だけ伸びる。鼻栓はこの設計では共通の既定位置より_PLUG_DROPだけ
  鼻の外へ飛び出している想定(DILATOR_PLUG)。

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

FrameParamsの8変数: natural_radius(拡張力の源)、tab_side_ratio(連結部の
位置)、bridge_y(帯を貼る高さ)、bridge_width/bridge_thickness(平らな
ブリッジの幅・厚み)、leg_thickness(棒の太さ)、collar_length(レンズの
厚み)、cuff_detent(連結部の帯を抱くCが帯の端近くの浅い段を越える
ときの締めしろ)。

ファイル内の並び順: 定数・データクラス → 経路・寸法を計算する関数
(bridge_points, _tab_frame, _rod_path, build_paths等) → メッシュ化・
幾何判定のユーティリティ → 各種*_margin/validate_* → build_bridge_piece・
build_bridge_print_piece・build_leg_piece。
"""

from dataclasses import dataclass
from typing import Literal

import functools

import numpy as np
import trimesh
from manifold3d import CrossSection, Manifold, Mesh, OpType
from scipy.spatial import cKDTree
from shapely.geometry import LineString, MultiPoint, Point, Polygon

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
# (装着位置そのものはFrameParams.bridge_yとしてGAの探索変数にした。
# ここに残すのは、その既定値の根拠と経緯)
_DEFAULT_BRIDGE_Y = 14.0
# ブリッジの帯の肌側の面を、鼻の表面(最近接点)からどれだけ外側
# (その点の三角形の法線方向)へ逃がすか(mm)。帯(_band_mesh)が幅方向に
# も鼻の表面に沿う格子で作られるため小さい値で足りる。棒の鼻の側面に沿う
# 区間も、帯の厚みの中央(BRIDGE_OFFSET+bridge_thickness/2)を通すことで
# タブとの継ぎ目に段差(折れ)ができないようにしている
BRIDGE_OFFSET = 0.4
# タブ(連結部)を置く位置を、断面の「直線の辺」(_side_edge_span: 前面の
# 丸め弧の端から背面角の丸め弧の端まで)のどこにするかで指定する
# (0=前面寄りの端、1=背面角の手前)。連結部の中心はここから内側に入る
# (_tab_frame)。
# 以前はhalf_width(角を丸める前の三角形の半幅)に対する比率だったが、
# 丸めで実際の断面は半幅よりずっと小さく、比率0.5〜0.6でも帯の端が鼻の
# 表面より外(空中)に出ていた。連結部が鼻に乗っていない位置に
# 置かれるため、直線の辺そのものを基準に測る形に改めた。
# 1を超える値では、帯の端を直線の辺の先へまっすぐ伸ばす(_bridge_profile。
# 「アーチを前みたいに長く」。背面角の丸みに沿わせて巻き込ませない)
_DEFAULT_TAB_SIDE_EDGE_RATIO = 1.25

# この設計で想定する鼻栓の位置。丸めたティッシュの鼻栓は、実際には
# 共通の既定位置(commons.plug_model._PLUG_Y_OFFSET、鼻の下端から約3.5mm
# 露出)よりもう少し鼻から飛び出しており、それを掴むレンズ・棒も
# そのぶん下にずれるはず(ユーザー指摘)。共通の既定値は他の設計
# (earrings/spiral/models)も使うため、この設計だけ_PLUG_DROPだけ
# 鼻の外側(-y)へずらす(鼻の下端から約6.5mm露出)
_PLUG_DROP = 3.0
DILATOR_PLUG = PlugParams(y_offset=PlugParams().y_offset - _PLUG_DROP)
# 連結部が鼻の側面にどれだけ寄っていなければならないか(断面の最大xに
# 対するタブ中心のxの比率)。ユーザー指摘「アーチと棒の接続部分、もう少し
# 外側にあってもいい。今だと鼻の正面に沿っていて、メガネをしていると
# 付けづらそう」への対応。正面寄りにあると、メガネの鼻パッドやブリッジと
# 干渉するうえ、タブを押し込むときに指が正面から入らない
# (鼻の断面を丸くした分、平らな連結部を置ける「直線の辺」が
# 短くなり、連結部を外へ寄せられる限界も下がった。丸める前は0.85まで
# 届いたが、いまは1.0(直線の辺の外端)でも0.70前後。さらに連結部を
# クリップにして幅が広がり、中心がそのぶん内側へ寄ったため0.66→0.62)
_MIN_JOINT_LATERAL_RATIO = 0.62
# 帯を、タブの位置よりさらに外側へ伸ばす長さ(mm、断面の輪郭に沿って
# 測る)。ユーザー要望「アーチの両端に医療用両面テープを貼ってブリーズ
# ライトのように小鼻を広げたい。今は連結部が端にあってテープが貼れない」
# への対応で、連結部はそのままに、その外側にテープの貼り代を作る。
# 直線の辺を越えて背面角の丸め弧にかかるぶんは、輪郭に沿って曲げる
# (_side_outline)ので鼻から浮かない
_BRIDGE_TAPE_SPAN = 6.0
# 貼り代の区間を輪郭に沿って何点で近似するか(断面ごとの点数を揃える
# ため固定。_bridge_gridがこの点数で格子を組む)
_BRIDGE_TAPE_SAMPLES = 5
# 貼り代を伸ばしてよいのは、断面の輪郭の外向き法線のx成分がこの値以上の
# 範囲まで(ユーザー指摘「アーチの両端が曲がりすぎている。ブリーズライトの
# ように鼻腔を広げる役割にならないといけない」)。鼻の側面から背面へ回り
# 込んだ範囲に貼り代を伸ばしても、帯が曲げ戻る力は外(+x、小鼻を開く向き)
# ではなく後ろ向きになり、鼻腔を広げる働きをしない(実測: 連結部から6mm
# 外側では法線のx成分が0.34、8mmでは0.08まで落ちる)。0.5は、力の半分以上が
# 外向きに使える範囲という意味
_MIN_TAPE_NORMAL_X = 0.5
# 帯の端を肌へ押し付けて届く、帯の肌側の面と肌のすき間(mm、BRIDGE_OFFSETを
# 超えるぶん)。帯は印刷したときは装着した形より開いた形
# (build_bridge_print_piece)で、装着するときに曲げて両端を肌へ押し付けるので、
# 端のあたりはこの程度なら押さえれば届く
_TAPE_MAX_GAP = 1.0
# 帯の断面の経路を何点で表すか(弧長で等間隔)。前面の丸め弧と直線の辺で
# 点の密度が極端に違うと、なめらかなアーチへ寄せる処理が効かない
_BRIDGE_PROFILE_SAMPLES = 81
# ブリッジを幅方向(y方向)にも鼻の表面に沿わせる際の、断面のロフト本数。
# 帯の持ち上げ量(_bridge_profile)は高さで変わるので、粗いと断面の間で帯の
# 面が折れ線になり、帯に沿わせた連結部と0.2mmずれた(5本のとき)
_BRIDGE_WIDTH_SAMPLES = 9
# 棒が鼻の側面に沿う区間(_side_follow_points)の下端のy座標(mm)と、
# その折れ線近似の分割数。ここから先はレンズの接点の真上へ向かう
# エルミート曲線になる(_rod_path)。-1.0にしていたが、鼻孔とレンズが
# 大きくなり、鼻の側面を降り切ってから横移動するとレンズの真上を
# 通れず壁を斜めに横切ってしまうため、0.5へ上げて早めに切り替える
_SIDE_FOLLOW_END_Y = -0.5
# 鼻の面ごとの法線でギザついた経路を均す移動平均の回数
_SIDE_FOLLOW_SMOOTH_PASSES = 3
# 棒が向かう鼻翼の溝の位置(断面の背面角の丸め弧の中での比率。0=側面の
# 直線の辺が終わって顔の側へ回り込み始める稜線、1=背面寄り)と、連結部の
# 真下から溝へ移り切るまでに降りる高さ(mm)。0.15〜0.5と奥へ入れるほど
# 溝らしくなるが、この鼻モデルの背面角は丸めが小さく、棒が鼻へめり込む
# (leg_clearance_margin)。移り方も6mmで急に寄せると曲がりが急になりすぎる
# (rod_kink_margin)。実測でどちらも満たせたのが稜線(0.0)・14mm
_CREASE_FRAC = 0.0
_CREASE_BLEND = 14.0
# 棒が鼻の表面に対して最低限あけるすきま(mm、線径の半分のうちめり込みを
# 許さない分に足す)と、押し出し量を均す移動平均の回数(_keep_off_body)
_ROD_BODY_GAP = 0.05
_ROD_PUSH_SMOOTH_PASSES = 20
_ROD_PUSH_ROUNDS = 6
# レンズへ入る手前で押し出しを0へ落とす距離(mm)
_ROD_PUSH_TAPER = 4.0
# 棒の経路を滑らかにするときの、元の経路からずれてよいおおよその量(mm)と、
# スプラインを当てはめる前に取り直す点の間隔(mm)
# (平滑化と鼻から離す補正を交互にかける回数ぶん、ずれの許容量を並べる)
_PATH_SMOOTH_TOLERANCES = (0.6, 0.4, 0.25)
_PATH_SMOOTH_SPACING = 0.5
# リングの壁に溶け込む円弧の点数(粗いと円弧の途中で折れる。8点では
# 8.6度ずつ折れていた)
_ROD_ARC_SAMPLES = 40
# 降下から輪の接線方向へ向きを変える角の丸めの半径を、棒の太さ
# (leg_thickness)に対する比率で指定。半分(=棒の半幅)では、幅の広い板が
# 半径1.5mmで急に折れ曲がって見えた
_ROD_CORNER_RADIUS_RATIO = 1.0
# 棒の幅をならすときの窓の長さ(mm)
_RADII_SMOOTH_WINDOW = 2.0
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
# 探索範囲の境界ちょうどの値(例: 溝の両脇の肉がちょうど最小値になる
# bridge_thickness)が浮動小数点の丸め(2e-17)で違反扱いになるため、ごく小さな
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
# 棒のエルミート曲線(鼻の側面の下端→レンズの接点の手前)の近似点数と、
# そこから輪の接線方向へ向きを変える四分円の点数
_ROD_STEM_SAMPLES = 40
_ROD_CORNER_SAMPLES = 12
# 棒を球の凸包の連鎖で作るときの、球の中心の間隔(mm)。_rod_radiiが
# 点ごとに半径を変えるため、細かいほどなめらかに太さが変わる
_ROD_SAMPLE_SPACING = 0.2
# 棒の球の近似精度(manifold3d.Manifold.sphereのcircular_segments)
_ROD_SPHERE_SEGMENTS = 24
# 棒の断面(角丸長方形)の幅と厚みの比。棒を丸線から平たいブレードへ
# 変えたのは「棒とリングがスタイリッシュに見えない」というユーザー指摘への
# 対応で、アーチ(帯)・棒・リングで断面の言語が3つに分かれていたのを板に
# 統一するため。1.0だと丸棒と同じ見え方になるので、はっきり平たいと分かる比。
# 実測では、この比で棒の厚みがアーチの厚み(1.3mm前後)とほぼ同じになる
_BLADE_ASPECT = 2.2
# ブレードの断面の角の丸めと、輪郭の点数
_BLADE_CORNER_RATIO = 0.35
_BLADE_SECTION_POINTS = 24
# ブレードの断面を置く間隔(mm)。1つ飛ばしの断面どうしの凸包でつなぐので
# (_blade_manifold)、この間隔が細かいほど表面がなめらかになる
_BLADE_SLICE_SPACING = 0.25
# 凸包の両端の断面を経路の向きへ外へずらす量(mm、_blade_manifold参照)
_BLADE_CAP_OFFSET = 0.02
# リング(レンズ)を鼻中隔側でC字に開く角度(度)。閉じた輪が2つ鼻孔に並ぶ
# 構図がいちばん「器具」に見える原因だったため、視覚的にいちばん重い要素を
# 開いて軽くする。開く向きは鼻中隔側で、棒が合流する外側は閉じたまま残る
_OPEN_RING_GAP_DEG = 100.0
# 棒の曲がりの半径が、その場所の棒の半径の何倍以上必要か
# (rod_kink_marginが制約として監視する)。0.5→0.3と緩めていたが、経路を
# 平滑化スプラインで一本の曲線にし(_smooth_path)、板のねじれを回転最小化
# フレームで均等に配る(_blade_frames)ようにしてから、実測の最小曲がり半径は
# 半幅の1.1〜2.6倍になった。ユーザー指摘「うねる部分をもっと滑らかに。
# 不格好でスタイリッシュでない、印刷も難しそう」を評価に反映するため、
# 「板が自分の半幅より急には曲がらない」ことを要求する1.0へ上げた
_MIN_TURN_RADIUS_RATIO = 1.0
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
_MIN_ROD_WIDTH = 1.9
# 棒(ブレード)の厚み方向(幅/_BLADE_ASPECT)の最小値(mm)。薄い側は板として
# 成立する厚みがあればよいので、帯本体と同じ水準(FDMの0.2mm積層で4層)
_MIN_ROD_THICKNESS = 0.8
# ブレードが1mmあたりねじれてよい角度の上限(度/mm)。アーチの面からリングの
# 面へ約90度回すのに短い棒しかないと、「ねじれた板」ではなく「ひねって折り
# 曲げた板」に見える(実測: 棒25mmで3.6度/mm)。31mm前後で3.0度/mmを切り、
# 一本の線として読めるようになる
_MAX_BLADE_TWIST_RATE = 3.0

# 連結部を帯の曲線に沿って曲げるための、帯に沿った向きの分割数
_JOINT_BEND_DIVISIONS = 16
# 連結部は「帯を抱くC」(イヤーカフ・吊り橋のケーブルバンドから着想)。脚の
# 上端が棒と同じ幅の小さなC字になって帯の上下の縁を抱き、爪先が縁のV溝に
# 収まる。帯の端から滑り込ませる。ユーザー指摘「棒とCの部分はアーチを外して
# 単体でも使うので、今だと不格好」を受けて、脚の上端が単体でも仕上がった形に
# なる3方式(フレンチクリート・帯を抱くC・鍵穴掛け)を試作して見比べ、
# ユーザーがこれを選んだ。以前のエッジクリップは帯の下縁だけを下から挟んで
# いたため、脚にかかる下向きの荷重がそのまま外れる向きに働いた
# 縁の溝を掘る範囲の内側の端(帯の端からの弧長、mm)。帯の端から約10mmは
# まっすぐなので(_bridge_profile)、その中に収める。脚はこの範囲で位置を選べる
_CONNECTOR_S_END = 9.0
# 帯を抱くC
_CUFF_GAP = 0.12  # Cと帯の外面・縁のすき間
_CUFF_ARM = 0.8  # 上下の腕の厚み(帯の幅方向)
_CUFF_BACK = 1.2  # 背(帯の外面に沿う部分)の厚み
_CUFF_ARM_REACH = -0.3  # 腕の先端の位置(帯の厚みの中央からの法線方向。帯の肌側の面より手前)
_CUFF_RIDGE_HALF = 0.2  # 爪(溝に入る山)の底の半幅
_CUFF_RIDGE_TIP = 0.2  # 爪の先端が帯の縁から入る深さ
_CUFF_GROOVE_HALF = 0.25  # 縁のV溝の口の半幅
_CUFF_GROOVE_DEPTH = 0.3  # 縁のV溝の深さ
# 帯の端近くの、溝が浅くなる段(爪が越えるとカチッと止まる)。深さは爪の
# 先端よりFrameParams.cuff_detentだけ浅い。出入口は45度の坂にする(垂直な
# 段だと爪の端面が突っかかって乗り上げない)。範囲は帯の端からの弧長で、
# (坂の始まり, 平らな部分の始まり, 平らな部分の終わり, 坂の終わり)
_CUFF_DETENT_S = (0.45, 0.75, 0.95, 1.25)
# 装着した位置でのCの外側の端(帯の端に近い側)の、帯の端からの弧長。浅い段の
# すぐ内側に置き、外へ滑ると段に当たるようにする
_CUFF_END_OFFSET = 1.35
# 溝の両脇に残す帯の肉の最小値(mm、片側)
_CUFF_MIN_EDGE_WALL = 0.25
# 爪の先端と帯の肌側の面の間に残す距離の最小値(mm)
_CUFF_MIN_ARM_INSET = 0.1
# 浅い段を越えるとき、Cの背(下の腕=棒の付け根を固定端とする片持ち梁)の
# 付け根の曲げひずみの上限。PLAの降伏ひずみが2〜2.5%、PETGで4%前後なので、
# 繰り返しの着脱に耐える水準として3%(以前のエッジクリップと同じ)
_MAX_CUFF_STRAIN = 0.03
# 浅い段を越えるのに要る力(N)の範囲。下限より弱いと、顔に触れた程度で
# 滑って外れる。上限より強いと、手で外しにくい(ユーザー要望「付けたり
# 取り外ししやすい」)。印刷材のヤング率はPLAの値で見積もる
_PRINT_MODULUS = 3500.0  # MPa(=N/mm^2)
_MIN_CUFF_HOLD_FORCE = 1.5
_MAX_CUFF_HOLD_FORCE = 10.0
# Cと肌の間に残すすき間の最小値(mm)
_MIN_CUFF_SKIN_GAP = 0.1
# 帯の曲線が「まっすぐ」とみなせる、帯の端からの向きの変化の上限(度)
# (_straight_length)
_STRAIGHT_ANGLE_DEG = 2.0
# 連結部を帯に沿って曲げるときに、帯の下縁より下・上縁より上へ延ばす範囲(mm)
# (TabFrame.profiles。帯の範囲は_band_meshと同じ高さの断面を使う)
_JOINT_PROFILE_BELOW = 3.0
_JOINT_PROFILE_ABOVE = 1.5
# 帯(テープを貼る薄い板)の、印刷に耐える最小の厚み(mm)。FDMの
# 0.2mm積層で3層
_MIN_BRIDGE_THICKNESS = 0.6
# 両端の貼り代(医療用両面テープを貼る面)の面積の下限(mm^2、左右合計)。
# 片側5mm×4mm程度は欲しいという水準の暫定値。テープの実物で測って
# 見直す前提(_MAX_SKIN_PRESSUREも同じ)。貼り代の長さは、鼻の背面側へ
# 回り込む手前で打ち切られる(tape_pad_span)ため6mmより短くなることが
# 多く、48mm^2では探索範囲の6割を弾いてしまったので40mm^2にした。さらに
# 帯を一定の曲率の円弧にした時期に、肌に届くのが端の2〜3mmだけになった
# ため16mm^2(片側2mm×4mm)にした(いまは側面に沿うので貼り代は長い)。
# テープで足りるかどうかは、貼り代にかかる面圧(skin_pressure_margin)が
# 別に判定する
_MIN_TAPE_AREA = 16.0


@dataclass(frozen=True)
class FrameParams:
    """フレームの仮寸法パラメータ(単位: mm)。

    ブリーズライト型の平らなブリッジ+棒+鼻栓を差し込むレンズという
    プレースホルダーで、後から実際の造形(3Dプリント/粘土)に向けて調整・
    最適化する。
    """

    natural_radius: float = 20.0
    # 帯の端(連結部はその少し内側)を、断面の側面の輪郭の
    # どこに置くか(直線の辺の長さを1とした弧長。0=鼻の正面寄りの端、
    # 1=背面角の手前、1を超えるぶんはまっすぐ伸ばす。_bridge_profile)。以前は定数だったが、
    # メガネとの干渉・嵌め込みのしやすさ(joint_access_margin)と、
    # その外側に残るテープの貼り代の兼ね合いを最適化させるため変数にした
    tab_side_ratio: float = _DEFAULT_TAB_SIDE_EDGE_RATIO
    # 帯を鼻のどの高さに貼るか(y座標、mm)。以前は定数_BRIDGE_Yだったが、
    # 装着位置は拡張力(装着後の曲率半径・帯の経路長)・棒の長さ・目立ち方の
    # すべてを左右するのに最適化の対象外だったため、探索変数にした
    bridge_y: float = _DEFAULT_BRIDGE_Y
    bridge_width: float = 5.0
    bridge_thickness: float = 1.0
    leg_thickness: float = 3.2
    collar_length: float = 2.08
    # 帯を抱くCが、帯の端近くの浅い段を越えるときの締めしろ(mm、片側)。
    # 大きいほど抜けにくいが、着脱のときCが大きく開いて折れやすく、外す力も
    # 増える(cuff_retention_margin・cuff_strain_margin)
    cuff_detent: float = 0.08

    def __post_init__(self) -> None:
        for name in (
            "natural_radius",
            "tab_side_ratio",
            "bridge_y",
            "bridge_width",
            "bridge_thickness",
            "leg_thickness",
            "collar_length",
            "cuff_detent",
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
    """連結部を置く位置と、帯の面に沿った局所座標系。

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
    rod_half_width: float  # 棒の付け根の半幅(=leg_thickness/2)
    side: int  # 左右(-1/1)
    half_thickness: float  # 帯の厚みの半分(局所座標のn=0が帯の厚みの中央)
    inset: float  # 帯の端から連結部の中心までの、帯に沿った長さ
    # 高さごとの帯の曲線(_joint_to_worldが連結部を帯に沿って曲げるのに使う)
    profile_ys: np.ndarray
    profiles: tuple


@dataclass(frozen=True)
class RodPath:
    """棒の中心線の点列と、点ごとの半径(_rod_radii参照)。"""

    points: np.ndarray  # shape (N, 3)
    radii: np.ndarray  # shape (N,)


# ブリッジの点列・左右の棒・左右のレンズの寸法。build_pathsが返し、
# 各種*_margin・build_leg_piece・scripts/dilator/evaluation.pyの間で共通の
# 型として使う
FramePaths = tuple[
    list[np.ndarray],
    RodPath,
    RodPath,
    CollarGeometry,
    CollarGeometry,
    TabFrame,
    TabFrame,
]


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


def bridge_points(
    body: trimesh.Trimesh, params: NoseParams, bridge_y: float, tab_side_ratio: float
) -> list[np.ndarray]:
    """ブリッジ(鼻を左右に横断する帯)の、高さbridge_yでの肌側の面の点列を
    返す(points[0]が+x側の端、points[-1]が-x側の端)。

    帯の形(_bridge_profile)は鼻の断面と両端の位置(tab_side_ratio)
    だけで決まり、帯の厚み・幅には依存しない。bodyは
    ほかの経路関数と引数をそろえるために受け取る。
    """
    return list(_bridge_profile_points(params, bridge_y, tab_side_ratio))


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


def _side_outline(params: NoseParams, y: float) -> tuple[np.ndarray, np.ndarray]:
    """高さyの断面の+x側の輪郭を、内側(前面の丸め弧の端)から外側へ
    たどった点列(x, z)と、その累積弧長を返す。

    直線の辺(_side_edge_span)を通り、その先の背面角の丸め弧まで続く。
    帯をタブより外側へ伸ばす(_BRIDGE_TAPE_SPAN、テープの貼り代)とき、
    直線の辺の延長では鼻の表面から浮いてしまうため、実際の輪郭の点を
    そのままたどる。
    """
    half_width, depth_back, depth_front = surface_profile_at(params, y)
    ring_2d = rounded_triangle_ring(half_width, depth_back, depth_front)
    # 輪郭は[背面左角の弧, ブーメラン, 背面右角の弧, 前面角の弧]の順。
    # 前面角の弧の始点(直線の辺の内側の端)から、背面右角の弧を逆順に
    # たどると、内側→外側→背面へ回り込む向きになる
    outline = ring_2d[-POINTS_PER_CORNER : -3 * POINTS_PER_CORNER : -1]
    steps = np.linalg.norm(np.diff(outline, axis=0), axis=1)
    return outline, np.concatenate([[0.0], np.cumsum(steps)])


def _outline_at(outline: np.ndarray, arc: np.ndarray, span: float) -> np.ndarray:
    """_side_outlineの点列を弧長spanだけ進んだ位置の(x, z)を返す。"""
    span = float(np.clip(span, 0.0, arc[-1]))
    return np.array([np.interp(span, arc, outline[:, k]) for k in range(2)])


def _outline_ratio(params: NoseParams, y: float, point: np.ndarray) -> tuple[float, np.ndarray]:
    """点(x, z)にいちばん近い、高さyの断面の+x側の輪郭の位置を、
    tab_side_ratioと同じ比率(直線の辺の長さを1とした、輪郭に沿った弧長)と、その点の
    (x, z)で返す。"""
    outline, arc = _side_outline(params, y)
    line = LineString(outline)
    span = float(line.project(Point(point)))
    return span / float(arc[1]), _outline_at(outline, arc, span)


def _outline_normal_x(outline: np.ndarray) -> np.ndarray:
    """_side_outlineの各区間の外向き法線のx成分を返す(長さは点数-1)。

    1に近いほどその区間の面はまっすぐ外(+x、小鼻を開く向き)を向いており、
    0に近いほど鼻の背面側へ回り込んでいる。
    """
    segments = np.diff(outline, axis=0)
    normals = np.stack([segments[:, 1], -segments[:, 0]], axis=1)
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    return np.abs(normals[:, 0])


@dataclass(frozen=True)
class BridgeProfile:
    """高さyの断面での、帯の肌側の面の曲線(_bridge_profile)。

    pointsは+x側の端から-x側の端への点列(x, z)で、弧長で等間隔
    (_BRIDGE_PROFILE_SAMPLES点、奇数なので真ん中の点が鼻の稜線の上)。
    normalsは各点の外向きの単位法線、sは+x側の端からの弧長。
    """

    points: np.ndarray  # shape (K, 2)
    normals: np.ndarray  # shape (K, 2)
    s: np.ndarray  # shape (K,)

    @property
    def length(self) -> float:
        return float(self.s[-1])


def _curve_normals(points: np.ndarray) -> np.ndarray:
    """+x側から-x側へ鼻の前を回る曲線(x, z)の各点の外向きの単位法線。"""
    tangents = np.gradient(points, axis=0)
    tangents /= np.linalg.norm(tangents, axis=1, keepdims=True)
    # 前を右(+x)から左へ回る向きなので、接線を時計回りに90度回すと外向き
    return np.stack([tangents[:, 1], -tangents[:, 0]], axis=1)


@functools.lru_cache(maxsize=2)
def _profile_body(params: NoseParams) -> trimesh.Trimesh:
    """_bridge_profileが実際の鼻とのすき間を測るための鼻本体メッシュ
    (読み取り専用で共有する)。"""
    return build_nose_body(params)


@functools.lru_cache(maxsize=4096)
def _bridge_profile(params: NoseParams, y: float, tab_side_ratio: float) -> BridgeProfile:
    """高さyの断面で、帯の肌側の面がたどる曲線を返す。

    帯は鼻の前面の丸み(断面の前面角の丸め弧)と両側面(直線の辺)に沿う
    アーチで、表面からBRIDGE_OFFSETだけ浮かせる。両端は直線の辺の
    tab_side_ratioの位置(0=前面寄りの端、1=背面角の手前)で、1を超える
    ぶんは背面角の丸みに沿わせず、直線の辺の向きのまま「まっすぐ」伸ばす。

    経緯(ユーザー指摘への対応):
    - 以前は両端を背面角の丸みに沿って巻き込ませていたため、「両端の
      アーチ部分が丸みを帯びていて、人それぞれ鼻の形が違うのでうまく
      フィットしない」。
    - それを受けて帯全体を一定の曲率の円弧にしたところ、三角形に近い
      鼻の断面を円で跨ぐため側面から2mmほど浮き、端も後ろへ回せず、
      「アーチ状が平べったすぎる。前と同じくらいのアーチ状がいい」。
    - いまは、以前のアーチ(前面の丸み+側面)はそのままに、巻き込んでいた
      両端だけをまっすぐにしている。

    断面(surface_profile_at)は解析的な角丸三角形で、実際の鼻本体メッシュには
    小鼻の膨らみなどが加わっている(実測: y<15mmで側面・稜線が最大0.5mm外)。
    そのままだと帯や連結部の縁が肌に食い込むので、曲線とメッシュの
    すき間を測り、BRIDGE_OFFSETに足りないぶんだけ、その高さの曲線全体を
    外向きに持ち上げる(形は変えない)。同じ引数で何度も呼ばれるので
    キャッシュする(戻り値の配列は書き換えないこと)。
    """
    half_width, depth_back, depth_front = surface_profile_at(params, y)
    ring = rounded_triangle_ring(half_width, depth_back, depth_front)
    front_arc = ring[-POINTS_PER_CORNER:]
    inner, outer = _side_edge_span(params, y)
    edge = outer - inner
    end = inner + tab_side_ratio * edge
    # 右端→直線の辺→前面の丸め弧(+xから-xへ)→直線の辺→左端
    side = np.linspace(end, front_arc[0], 30)[:-1]
    mirror = np.array([-1.0, 1.0])
    curve = np.vstack([side, front_arc, (side * mirror)[::-1]])
    curve = curve[np.concatenate([[True], np.linalg.norm(np.diff(curve, axis=0), axis=1) > 1e-9])]
    curve = curve + _curve_normals(curve) * BRIDGE_OFFSET
    # 弧長で等間隔に取り直す
    arc = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(curve, axis=0), axis=1))])
    samples = np.linspace(0.0, arc[-1], _BRIDGE_PROFILE_SAMPLES)
    points = np.stack([np.interp(samples, arc, curve[:, k]) for k in range(2)], axis=1)
    # 左右対称にそろえる(補間の丸めで真ん中の点がx=0からずれないように)
    points = (points + (points * mirror)[::-1]) / 2
    normals = _curve_normals(points)
    body = _profile_body(params)
    world = np.stack([points[:, 0], np.full(len(points), y), points[:, 1]], axis=1)
    closest, _, triangle_id = trimesh.proximity.closest_point(body, world)
    gap = np.einsum("ij,ij->i", world - closest, body.face_normals[triangle_id])
    lift = max(0.0, BRIDGE_OFFSET - float(gap.min()))
    points = points + normals * lift
    return BridgeProfile(points=points, normals=normals, s=samples)


def _profile_at(profile: BridgeProfile, s: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """帯の曲線の、+x側の端から弧長sの位置の点(x, z)と外向きの単位法線を返す
    (sは配列可。戻り値の形は(len(s), 2))。"""
    s = np.atleast_1d(np.asarray(s, dtype=float))
    point = np.stack([np.interp(s, profile.s, profile.points[:, k]) for k in range(2)], axis=1)
    normal = np.stack([np.interp(s, profile.s, profile.normals[:, k]) for k in range(2)], axis=1)
    normal /= np.linalg.norm(normal, axis=1, keepdims=True)
    return point, normal


def _tape_pad(params: NoseParams, y: float, tab_side_ratio: float) -> tuple[float, float]:
    """高さyの断面で、帯の端の両面テープを貼れる長さ(mm)と、その面が
    平均してどれだけ外(+x)を向いているか(0〜1)を返す。

    帯の端から内側へたどり、肌側の面と肌のすき間がBRIDGE_OFFSET+
    _TAPE_MAX_GAP以内の範囲が続く長さを貼り代とする(最大_BRIDGE_TAPE_SPAN)。
    直線の辺の先へまっすぐ伸ばした端(tab_side_ratio>1)は背面角の丸みから
    浮くので、浮きすぎたぶんは貼り代にならない。
    """
    profile = _bridge_profile(params, y, tab_side_ratio)
    half_width, depth_back, depth_front = surface_profile_at(params, y)
    section = Polygon(rounded_triangle_ring(half_width, depth_back, depth_front))
    spans = np.linspace(0.0, _BRIDGE_TAPE_SPAN, 25)
    points, normals = _profile_at(profile, spans)
    length, outward = 0.0, []
    started = False
    for span, point, normal in zip(spans, points, normals):
        gap = section.exterior.distance(Point(point))
        if gap > BRIDGE_OFFSET + _TAPE_MAX_GAP:
            if started:
                break
            continue
        started = True
        length += float(spans[1] - spans[0]) if len(outward) else 0.0
        outward.append(abs(float(normal[0])))
    return length, float(np.mean(outward)) if outward else 0.0


def _bridge_profile_points(
    params: NoseParams, y: float, tab_side_ratio: float
) -> np.ndarray:
    """高さyの断面で、帯の肌側の面の点列(+x側の端から-x側の端へ、弧長で
    等間隔)を3次元の点で返す(_bridge_profile)。"""
    profile = _bridge_profile(params, y, tab_side_ratio)
    return np.stack(
        [profile.points[:, 0], np.full(len(profile.points), y), profile.points[:, 1]], axis=1
    )


def _bridge_grid(
    params: NoseParams, bridge_y: float, width: float, tab_side_ratio: float
) -> np.ndarray:
    """ブリッジを幅方向(y方向、bridge_y±width/2)にも鼻の表面に沿わせる
    ための格子点(オフセット前、鼻の表面上の生の点)を返す(shape:
    (_BRIDGE_WIDTH_SAMPLES, 13, 3))。

    以前はブリッジの中心の経路(bridge_points、高さbridge_yのみ)を
    グローバルなy軸方向に±width/2だけ平行移動して長方形の断面を作って
    いたが、鼻の断面(half_width・depth_back・depth_front)は高さyに
    よって変わる(commons.nose_model.surface_profile_at)ため、この平行
    移動では特にbridge_widthが大きいとき、実際の鼻の丸みから外れた
    (めり込む、または不自然に浮いた)形になってしまう(ユーザー指摘:
    「縦が長すぎる」「鼻にフィットする感じに調整して」)。_bridge_profile_
    pointsを複数の高さyで評価し、各高さの断面をそのまま並べる(ロフト)
    ことで、幅方向にも実際の鼻の丸みに沿う帯を作る。
    """
    ys = np.linspace(bridge_y - width / 2, bridge_y + width / 2, _BRIDGE_WIDTH_SAMPLES)
    return np.stack(
        [_bridge_profile_points(params, float(y), tab_side_ratio) for y in ys], axis=0
    )
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
    actual_radius = ((chord / 2) ** 2 + sagitta**2) / (2 * sagitta)
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
    """連結部の位置と局所座標系(TabFrame)を返す。

    帯の下縁(y=bridge_y-bridge_width/2)の曲線(_bridge_profile)の上で、帯の端から
    (棒の半幅+_CUFF_END_OFFSET)だけ内側に置く(スケッチの通り、
    棒はアーチの端近くにつく)。uは曲線の接線(帯の端へ向かう向き)、
    nは曲線の外向き、vは帯の下縁→上縁の向き(帯は高さごとに円弧が少し
    違うので、下縁と上縁の対応する点を結んで決める。三角形の法線などから
    決めると帯の面に対して傾き、平らな顎が帯に食い込んだ)。centerは
    帯の厚みの中央の点。まず+x側で計算してからsideで鏡映する。
    """
    y_edge = frame.bridge_y - frame.bridge_width / 2
    y_top = frame.bridge_y + frame.bridge_width / 2
    rod_half_width = frame.leg_thickness / 2
    # 帯を抱くCは棒と同じ幅なので、Cの外側の端が_CUFF_END_OFFSETに来る位置
    inset = rod_half_width + _CUFF_END_OFFSET
    middle = frame.bridge_thickness / 2

    def point_at(y: float) -> tuple[np.ndarray, np.ndarray]:
        profile = _bridge_profile(params, y, frame.tab_side_ratio)
        point, normal = _profile_at(profile, inset)
        mid = point[0] + normal[0] * middle
        return np.array([mid[0], y, mid[1]]), normal[0]

    center, normal = point_at(y_edge)
    top, _ = point_at(y_top)
    n0 = np.array([normal[0], 0.0, normal[1]])
    # 帯の端へ向かう接線(外向きの法線を時計回りに90度: 弧長sが減る向き)
    u0 = np.array([normal[1], 0.0, -normal[0]])
    n = np.cross(u0, top - center)
    n /= np.linalg.norm(n)
    if np.dot(n, n0) < 0:
        n = -n
    u = u0 - np.dot(u0, n) * n
    u /= np.linalg.norm(u)
    v = np.cross(n, u)
    if v[1] < 0:
        v = -v
    # 連結部の真下の肌の点は、帯の厚みの中央の点にいちばん近い輪郭の点に
    # する。帯の端をまっすぐ伸ばしたところでは、連結部のあたりが肌から浮く
    # (_bridge_profile)ため、同じxの輪郭上の点(以前の決め方)を使うと、棒の
    # 起点が連結部から2mm以上下にずれ、つなぎ目で棒が折れた(実測: 曲がりの
    # 半径1.55mmに対し棒の半径1.86mm)
    _, foot = _outline_ratio(params, y_edge, center[[0, 2]])
    anchor = np.array([foot[0], y_edge, foot[1]])
    # 連結部を帯に沿って曲げるための、高さごとの帯の曲線。帯の範囲では
    # _band_meshと同じ高さの断面を使い(帯の面と連結部の面が同じ折れ線で
    # 近似されるので、断面の間でずれない)、その外へ同じ間隔で延ばす
    step = frame.bridge_width / (_BRIDGE_WIDTH_SAMPLES - 1)
    below = int(np.ceil(_JOINT_PROFILE_BELOW / step))
    above = int(np.ceil(_JOINT_PROFILE_ABOVE / step))
    profile_ys = y_edge + step * np.arange(-below, _BRIDGE_WIDTH_SAMPLES + above)
    rows = [_bridge_profile(params, float(y), frame.tab_side_ratio) for y in profile_ys]
    return TabFrame(
        center=_mirror(center, side),
        anchor=_mirror(anchor, side),
        u=_mirror(u, side),
        v=_mirror(v, side),
        n=_mirror(n, side),
        rod_half_width=rod_half_width,
        side=side,
        half_thickness=middle,
        inset=inset,
        profile_ys=profile_ys,
        profiles=tuple(rows),
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
    start_ratio: float,
    y_start: float,
    offset: float,
    end_offset: float | None = None,
) -> np.ndarray:
    """連結部の下から_SIDE_FOLLOW_END_Yまで、鼻の側面を鼻翼の溝へ向かって
    降りる点列を返す(鼻の表面からoffsetだけ浮かせる)。

    始点は、断面の側面の輪郭のstart_ratioの位置(_outline_ratioの比率。
    =連結部の真下)。そこから降りるにつれて、断面の輪郭に沿って背面側の
    角(鼻の側面が顔へ回り込む、背面角の丸め弧の途中=_CREASE_FRACの位置)
    へ移っていく。実際の顔では、ここが小鼻と頬の境目の溝(鼻翼溝)にあたる。

    ユーザーが採用した案1-a。以前は直線の辺の同じ比率のまま真下へ降りて
    いたため、鼻がいちばん横へ張り出す鼻翼(y=0付近で断面の最大x=15.9mm、
    連結部の高さでは10.4mm)の内側を横切り、「鼻の上部から降りてくる異物」に
    見えていた。溝に沿わせると正面から隠れやすく、皮膚の谷にはまるので
    ずれにくい。
    """
    ys = np.linspace(y_start, _SIDE_FOLLOW_END_Y, _SIDE_FOLLOW_SAMPLES)
    raw = []
    for y in ys:
        outline, arc = _side_outline(params, float(y))
        joint_span = start_ratio * float(arc[1])
        back_arc = float(arc[POINTS_PER_CORNER] - arc[1])
        crease_span = float(arc[1]) + _CREASE_FRAC * back_arc
        weight = np.clip((y_start - y) / _CREASE_BLEND, 0.0, 1.0)
        weight = weight**2 * (3 - 2 * weight)
        x, z = _outline_at(outline, arc, (1 - weight) * joint_span + weight * crease_span)
        raw.append([x, y, z])
    offsets = np.linspace(offset, offset if end_offset is None else end_offset, len(ys))
    raw = np.array(raw)
    # 浮かせる向きは「最も近い三角形の法線」なので、どの面を拾うかで点ごとに
    # 向きが飛び、経路がギザつく。そのままだと曲がりの半径が棒の半径を
    # 下回る箇所ができて管が自分自身に食い込むため、法線の側を移動平均で
    # 均してから浮かせる(点自体を均すと、凸に曲がった経路が鼻の側へ
    # 寄って、めり込み(leg_clearance_margin)が出てしまう)
    raw_normals = _surface_normals(body, raw)
    raw_normals = raw_normals / np.linalg.norm(raw_normals, axis=1, keepdims=True)
    normals = raw_normals.copy()
    for _ in range(_SIDE_FOLLOW_SMOOTH_PASSES):
        normals[1:-1] = (normals[:-2] + 2 * normals[1:-1] + normals[2:]) / 4
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    # 均した向きは元の法線から少し傾くため、そのまま同じ長さだけ動かすと
    # 表面からの距離が足りなくなる(鼻へのめり込みになる)。傾いたぶんだけ
    # 長さを伸ばして、表面からの距離をoffsetに保つ
    tilt = np.clip(np.einsum("ij,ij->i", normals, raw_normals), 0.5, 1.0)
    return raw + normals * (offsets / tilt)[:, None]


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


def _turn_radii(points: np.ndarray) -> np.ndarray:
    """点列の各点における曲がりの半径(3点の外接円の半径)を返す
    (両端はinf)。直線なら大きな値になる。
    """
    radii = np.full(len(points), np.inf)
    before, here, after = points[:-2], points[1:-1], points[2:]
    area = np.linalg.norm(np.cross(before - here, after - here), axis=1)
    sides = (
        np.linalg.norm(before - here, axis=1)
        * np.linalg.norm(after - here, axis=1)
        * np.linalg.norm(before - after, axis=1)
    )
    radii[1:-1] = np.where(area > 1e-12, sides / np.maximum(2 * area, 1e-12), np.inf)
    return radii


def _rod_radii(
    frame: FrameParams, tab: TabFrame, collar: CollarGeometry, points: np.ndarray
) -> np.ndarray:
    """棒の点ごとの半径を返す。基本はleg_thickness/2で、次の範囲を
    越えないよう、なめらかに細くする。

    - 帯の近く: 制限しない。棒は連結部の脚側の形(帯の下縁より下)から生え、
      そこでは断面(平たいブレード)が帯の面と同じ向きに寝ているので、帯の
      ほうへは厚みを持たない(以前のタブ式は棒が帯の中から始まったため、
      帯の厚みの半分までに細める必要があった)。
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
    (GAの制約)が印刷に必要な寸法を下回らないか監視する。
    """
    y = points[:, 1]
    rho = np.hypot(points[:, 0] - collar.center_x, points[:, 2] - collar.center_z)
    radii = np.full(len(points), frame.leg_thickness / 2)
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
    # 幅の急な変化をならす。先に窓の中の最小値を取ってから平均するので、
    # どの点でも元の上限(レンズ・鼻栓・帯に収まる太さ)を超えず、いちばん
    # 細い所がさらに細くなることもない
    from scipy.ndimage import minimum_filter1d, uniform_filter1d

    window = max(int(round(_RADII_SMOOTH_WINDOW / _ROD_SAMPLE_SPACING)), 1)
    radii = uniform_filter1d(
        minimum_filter1d(radii, window, mode="nearest"), window, mode="nearest"
    )
    return np.maximum(radii, _ROD_MIN_RADIUS)


def _smooth_path(
    points: np.ndarray, tolerance: float, pinned_from: np.ndarray | None = None
) -> np.ndarray:
    """折れ線の経路を、平滑化スプラインで一本の滑らかな曲線にして返す
    (両端の位置と向きは保つ)。

    鼻の側面に沿う区間は8段の折れ線から、そのあとはエルミート曲線・
    四分円とつないでいるため、継ぎ目で経路が折れていた(実測: 0.2mmごとに
    最大15.8度、5度を超える折れが35か所)。平たいブレードは経路の向きに
    沿って断面を並べるので、この折れがそのまま板のよじれ・段差として
    見えていた(ユーザー指摘「うねる部分が不格好」「印刷も難しそう」)。
    元の経路からtolerance程度しか離れない範囲で、曲率が連続する(3次の)
    スプラインに置き換える。pinned_fromを渡すと、経路上でその点より後ろの
    区間はほぼ動かさない(リングの壁に溶け込む円弧を輪に沿わせたままにする)。
    """
    from scipy.interpolate import splev, splprep

    even = _resample(points, _PATH_SMOOTH_SPACING)
    if len(even) < 6:
        return points
    weights = np.ones(len(even))
    # 両端の数点は重くして、連結部の中の始点と終点の位置・向きを保つ
    weights[:3] = weights[-3:] = 50.0
    if pinned_from is not None:
        start_index = int(np.argmin(np.linalg.norm(even - pinned_from, axis=1)))
        weights[start_index:] = 50.0
    tck, _ = splprep(
        even.T, w=weights, s=len(even) * tolerance**2, k=3
    )
    samples = np.linspace(0.0, 1.0, max(len(even) * 2, 20))
    smooth = np.stack(splev(samples, tck), axis=1)
    smooth[0], smooth[-1] = points[0], points[-1]
    return smooth


def _keep_off_body(
    body: trimesh.Trimesh,
    points: np.ndarray,
    frame: FrameParams,
    collar: CollarGeometry,
) -> np.ndarray:
    """棒の経路のうち鼻に近すぎる点を、鼻の表面から離す。

    鼻の側面に沿う区間(_side_follow_points)は表面からの距離を決めて作るが、
    そこからレンズへ向かうエルミート曲線は両端の位置と向きだけで決まるため、
    途中で鼻の下面(鼻先の丸み)をかすめることがある。鼻の断面の丸め方を
    変えたときに、棒が許容量を超えて鼻へ食い込む状態(leg_clearance_margin
    違反)として実際に表面化した。

    各点について、必要な距離(線径の半分のうちめり込みを許さない分)に
    足りないぶんだけ表面の法線方向へ押し出し、押し出し量は移動平均で均して
    折れを作らないようにする。タブの中の始点と、レンズの高さまで降りた
    区間(鼻より下で、押し出すとレンズから外れる)は動かさない。
    """
    required = frame.leg_thickness / 2 * (1 - _EMBED_RATIO) + _ROD_BODY_GAP
    points = points.copy()
    for _ in range(_ROD_PUSH_ROUNDS):
        _, distance, triangle_id = trimesh.proximity.closest_point(body, points)
        signed = np.where(body.contains(points), -distance, distance)
        push = np.maximum(required - signed, 0.0)
        push[0] = 0.0
        # レンズへ入る手前では押し出しをなめらかに0へ落とす(ここで急に
        # 打ち切ると、その境界が折れになる: rod_kink_margin違反)
        taper = np.clip(
            (points[:, 1] - collar.y_end) / _ROD_PUSH_TAPER, 0.0, 1.0
        )
        push *= taper**2 * (3 - 2 * taper)
        if not np.any(push > 1e-6):
            break
        # 押し出し量を均してから適用する(点ごとに違う量を直接足すと、
        # そこが折れになって管が自分自身に食い込む: rod_kink_margin)
        for _ in range(_ROD_PUSH_SMOOTH_PASSES):
            push[1:-1] = (push[:-2] + 2 * push[1:-1] + push[2:]) / 4
        normals = body.face_normals[triangle_id]
        normals = normals / np.linalg.norm(normals, axis=1, keepdims=True)
        points = points + normals * push[:, None]
    return points


def _rod_path(
    frame: FrameParams,
    params: NoseParams,
    body: trimesh.Trimesh,
    tab: TabFrame,
    collar: CollarGeometry,
    side: Literal[-1, 1],
) -> RodPath:
    """棒の中心線と点ごとの半径を返す(モジュールdocstring「幾何」参照)。

    1. 連結部の脚側の形の中から始まる(_connector_rod_start)。
    2. 連結部の下から_SIDE_FOLLOW_END_Yまで、鼻の側面を鼻翼の溝へ
       向かって降りる(_side_follow_points)。
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
    canonical_v = _mirror(tab.v, side)
    canonical_n = _mirror(tab.n, side)
    # 棒は連結部の脚側の形の中から始まる(_connector_rod_start)
    start_v, start_n, follow_v = _connector_rod_start(frame)
    start = _mirror(tab.center, side) + canonical_v * start_v + canonical_n * start_n
    start_ratio, _ = _outline_ratio(params, float(canonical_anchor[1]), canonical_anchor[[0, 2]])
    # 起点は鼻の表面上の点(anchor)で、そこから同じオフセットで浮かせる
    # (TabFrameのdocstring参照。side_follow[0]はちょうどtab.centerになる)
    # 鼻の表面からの浮かせ量は、帯との継ぎ目では帯の厚みの中央(タブと
    # 段差なくつながる高さ)だが、そのままだと棒が帯より太いとき(leg_
    # thickness>bridge_thickness)に棒の下側が鼻へ食い込む(実測: 既定
    # 形状でleg_clearance_marginの余裕が0.004mmしか残らなかった)。
    # 降りるにつれて棒の半径ぶんの高さへなめらかに移す
    # 棒の起点は帯より外(連結部の脚側の形の中)にあるので、起点の浮かせ量は
    # 起点から肌までの距離にし、降りるにつれて肌へ寄せる
    float_height = float(np.linalg.norm((start - canonical_anchor)[[0, 2]]))
    side_follow = _side_follow_points(
        body,
        params,
        float(start_ratio),
        float(canonical_anchor[1]) + follow_v * float(canonical_v[1]),
        max(float_height, BRIDGE_OFFSET + frame.bridge_thickness / 2),
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
    # 降りてくる位置(start_angle)から輪に沿ってblendぶん先を接点にし、
    # そこからさらに_ROD_JOINT_ARC_DEGだけ(角度が減る向き=鼻の前面側から
    # 背面側へ)進む。接点を降りてくる位置そのものにすると、角を丸める
    # ぶん棒が輪に沿って手前(鼻の側)へ戻ることになり、鼻へめり込む
    blend = min(frame.leg_thickness * _ROD_CORNER_RADIUS_RATIO, r_arc / 2)
    contact_angle = start_angle - blend / r_arc
    angles = contact_angle - np.radians(np.linspace(0.0, _ROD_JOINT_ARC_DEG, _ROD_ARC_SAMPLES))
    arc = np.stack(
        [
            axis_x + r_arc * np.cos(angles),
            np.full(len(angles), y_mid),
            collar.center_z + r_arc * np.sin(angles),
        ],
        axis=1,
    )
    contact = arc[0]
    # 到達時の接線(その点での輪の接線、進む向き)。y成分がないため、棒は
    # レンズの面の中で輪に接して入る(ユーザーのスケッチ「6d」)
    contact_tangent = np.array([np.sin(contact_angle), 0.0, -np.cos(contact_angle)])
    # 接点の真上(レンズの上面より棒の半径ぶん上)を経由してから、外周面に
    # 沿ってまっすぐ降りて輪に入る。エルミート曲線で接点へ直接つなぐと、
    # 棒が輪の壁(内径〜外径の間)を斜めに横切り、その区間で壁の残り厚み
    # (rho-r_inner)しか太さを使えず極端に細くなっていた(実測: 直径0.4mm)。
    # レンズより上では棒はいくら太くてもよい(_rod_radii参照)ので、横移動は
    # すべて上で済ませる
    # 輪へは、接点の「真上かつ接線方向に手前」から四分円で入る。真上から
    # 降りてそのまま接線方向へ折れると、曲がりの半径が棒の半径を大きく
    # 下回って管が自分自身に食い込み(実測: 曲率半径0.14mmに対し棒の
    # 半径1.01mm)、そのメッシュはSTLへ書き出して座標で頂点を統合すると
    # 閉じた立体でなくなる。丸めの半径は棒の半径ぶん取る
    approach = np.array(
        [
            axis_x + r_arc * np.cos(start_angle),
            y_mid + blend,
            collar.center_z + r_arc * np.sin(start_angle),
        ]
    )
    direction = side_follow[-1] - side_follow[-2]
    direction /= np.linalg.norm(direction)
    span = float(np.linalg.norm(approach - stem_start))
    stem = _hermite(
        stem_start, direction * span, approach, np.array([0.0, -1.0, 0.0]) * span,
        _ROD_STEM_SAMPLES,
    )
    # 四分円に近いエルミート(接線の大きさは半径の約1.3倍)
    corner = _hermite(
        approach,
        np.array([0.0, -1.0, 0.0]) * blend * 1.3,
        contact,
        contact_tangent * blend * 1.3,
        _ROD_CORNER_SAMPLES,
    )
    stem = np.vstack([stem, corner[1:]])

    # リングの壁へ溶け込む円弧(arc)は輪に正確に沿わせたいので、その手前
    # までを一本の滑らかな曲線にしてから、円弧をそのままつなぐ
    # 平滑化と「鼻から離す補正」を交互にかける。平滑化は凸な膨らみを
    # わずかに削って鼻に寄せ、補正は押し出したところに曲がりを作るので、
    # 片方だけでは両立しない。リングの壁へ溶け込む円弧も含めて一本の曲線に
    # する(円弧だけ後からつなぐと、つなぎ目で向きが合わず折れた。実測11.7度)。
    # 円弧の部分は輪に正確に沿わせたいので、平滑化で動かないよう押さえる
    path = np.vstack([[start], side_follow, stem[1:], arc[1:]])
    for tolerance in _PATH_SMOOTH_TOLERANCES:
        path = _smooth_path(path, tolerance, pinned_from=contact)
        path = _keep_off_body(body, path, frame, collar)
    canonical = _resample(path, _ROD_SAMPLE_SPACING)
    points = canonical * np.array([side, 1.0, 1.0])
    return RodPath(points=points, radii=_rod_radii(frame, tab, collar, points))


def build_paths(
    frame: FrameParams,
    plug: PlugParams,
    params: NoseParams,
    body: trimesh.Trimesh,
) -> FramePaths:
    """ブリッジの点列・左右の棒・左右のレンズ・左右のタブを返す
    (メッシュ生成なし)。

    bodyは呼び出し側がbuild_nose_body(params)で構築済みのものを渡す
    (重複構築を避けるため)。
    """
    bridge = bridge_points(body, params, frame.bridge_y, frame.tab_side_ratio)
    rods = {}
    collars = {}
    tabs = {}
    for side in (-1, 1):
        tabs[side] = _tab_frame(frame, params, body, side)
        collars[side] = _collar_geometry(frame, plug, params, side)
        rods[side] = _rod_path(frame, params, body, tabs[side], collars[side], side)
    return bridge, rods[-1], rods[1], collars[-1], collars[1], tabs[-1], tabs[1]


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


def _joint_to_world(tab: TabFrame, local: np.ndarray) -> np.ndarray:
    """連結部の局所座標(u, v, n)の点を、帯の曲がりに沿って曲げた世界座標へ
    写す。

    帯は高さごとに形の違う曲線(_bridge_profile、_band_meshも各高さの
    曲線から外向きに厚みを付ける)なので、連結部も同じ曲線に沿わせる。
    vは高さy(=帯の下縁からtab.vに沿った距離のy成分)に、uはその高さの
    曲線に沿った長さ(帯の端へ向かう向きが正)に、nはその曲線の外向き
    (帯の厚みの中央から)に対応させ、隣り合う高さの間は線形に補間する。
    以前は連結部1点での曲率半径のまま全体を曲げていたため、帯の端に近い
    ところで帯と連結部の面がずれ、はめあいの隙間を越えて食い込んだ。
    左右で鏡映しているため、-x側はuを反転して面の向き(右手系)を保つ
    (連結部の脚側はuについて左右対称)。
    """
    y = tab.center[1] + local[:, 1] * tab.v[1]
    s = tab.inset - tab.side * local[:, 0]
    offset = tab.half_thickness + local[:, 2]
    position = np.interp(y, tab.profile_ys, np.arange(len(tab.profile_ys)))
    lower = np.clip(np.floor(position).astype(int), 0, len(tab.profile_ys) - 2)
    weight = (position - lower)[:, None]
    result = np.zeros((len(local), 2))
    for row in np.unique(lower):
        mask = lower == row
        blended = np.zeros((int(mask.sum()), 2))
        for index, row_weight in ((row, 1 - weight[mask]), (row + 1, weight[mask])):
            point, normal = _profile_at(tab.profiles[index], s[mask])
            blended += row_weight * (point + normal * offset[mask, None])
        result[mask] = blended
    return np.stack([tab.side * result[:, 0], y, result[:, 1]], axis=1)


# 局所座標(u, v, n)への並べ替え: CrossSectionの(x, y)=(v, n)を押し出した
# zをuにする(巡回置換なので面の向きは変わらない)
_VN_TO_LOCAL = np.array([[0.0, 0.0, 1.0, 0.0], [1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]])


# 連結部の断面の辺を分割する最大の長さ(mm)。連結部は帯の曲がりに沿って
# 曲げる(_joint_to_world)が、曲げるのは頂点だけなので、長い辺は弦のまま
# 残る。帯の外面は高さ方向にわずかにふくらむ(_bridge_profileの持ち上げ量が
# 高さで変わる)ため、帯の幅を1本で渡る辺が帯に食い込んだ(実測0.3mm^3)
_JOINT_EDGE_STEP = 0.25


def _ccw(polygon: np.ndarray) -> list:
    """多角形を、辺を_JOINT_EDGE_STEP以下に分割したうえで反時計回りにそろえる
    (CrossSectionは反時計回りだけを面にする)。"""
    polygon = np.asarray(polygon, dtype=float)
    if not Polygon(polygon).exterior.is_ccw:
        polygon = polygon[::-1]
    points = []
    for start, end in zip(polygon, np.roll(polygon, -1, axis=0)):
        count = max(int(np.ceil(np.linalg.norm(end - start) / _JOINT_EDGE_STEP)), 1)
        points.extend(start + (end - start) * t for t in np.arange(count) / count)
    return np.array(points).tolist()


def _extrude_vn(polygon: np.ndarray, u_range: tuple[float, float]) -> Manifold:
    """(v, n)の断面をuの範囲に押し出した立体を、局所座標で返す。"""
    body = CrossSection([_ccw(polygon)]).extrude(
        u_range[1] - u_range[0], n_divisions=_JOINT_BEND_DIVISIONS
    )
    return body.translate((0.0, 0.0, u_range[0])).transform(_VN_TO_LOCAL)


def _extrude_uv(polygon: np.ndarray, n_range: tuple[float, float]) -> Manifold:
    """(u, v)の輪郭をnの範囲に押し出した立体を、局所座標で返す。"""
    body = CrossSection([_ccw(polygon)]).extrude(n_range[1] - n_range[0])
    return body.translate((0.0, 0.0, n_range[0]))


def _band_top_v(tab: TabFrame, frame: FrameParams) -> float:
    """装着した形の帯の上縁の、連結部の局所座標でのv。

    _joint_to_worldは局所座標のvを高さy=帯の下縁+v*tab.v[1]に対応させるので、
    帯の上縁(高さ+bridge_width)はv=bridge_width/tab.v[1]にある(帯の面は
    鼻筋へ向かって少し傾いているので、bridge_widthより2〜3%大きい)。
    印刷形(build_bridge_print_piece)では局所座標をそのまま回すだけなので
    v=bridge_widthになる。
    """
    return frame.bridge_width / float(tab.v[1])


def _cuff_groove_local(frame: FrameParams, inset: float, top_v: float) -> Manifold:
    """帯を抱くCの帯側(上下の縁のV溝)を、+x側の局所座標で返す(引く立体)。

    溝は帯の端まで開けて(端から滑り込ませられる)、端の近く
    (_CUFF_DETENT_S)だけ浅くする。Cの爪はそこを少したわんで越え、
    カチッと止まる。内側の端(_CONNECTOR_S_END)は溝が行き止まりになって
    止まる。浅い段は、溝から「坂のある台形の山」を引いて作る。
    """
    half = _CUFF_GROOVE_HALF
    shallow = _CUFF_RIDGE_TIP - frame.cuff_detent
    s_a, s_b, s_c, s_d = _CUFF_DETENT_S
    grooves, bumps = [], []
    u_range = (inset - _CONNECTOR_S_END, inset + 0.5)
    for edge, sign in ((0.0, 1.0), (top_v, -1.0)):
        section = np.array(
            [(edge - sign * 0.05, -half), (edge + sign * _CUFF_GROOVE_DEPTH, 0.0), (edge - sign * 0.05, half)]
        )
        grooves.append(_extrude_vn(section, u_range))
        # 山: (u, v)の台形をnの向きに押し出す(溝の中だけ残す)
        deep = edge + sign * (_CUFF_GROOVE_DEPTH + 0.1)
        top = edge + sign * shallow
        outline = np.array(
            [(inset - s_a, deep), (inset - s_b, top), (inset - s_c, top), (inset - s_d, deep)]
        )
        bumps.append(_extrude_uv(outline, (-half - 0.1, half + 0.1)))
    groove = Manifold.batch_boolean(grooves, OpType.Add)
    return Manifold.batch_boolean([groove, *bumps], OpType.Subtract)


def _cuff_local(frame: FrameParams, top_v: float) -> Manifold:
    """帯を抱くCの脚側を、局所座標で返す(uについて左右対称)。

    断面は帯の外面側に背があり、上下の腕が帯の縁を回り込むC字(肌の側に
    開く)。腕の内側の面の中央に、縁のV溝に入る爪がある。腕の先端は帯の
    肌側の面より手前(_CUFF_ARM_REACH)で止め、肌と帯の間には入らない。
    """
    half_t = frame.bridge_thickness / 2
    width = top_v
    gap, arm = _CUFF_GAP, _CUFF_ARM
    n_in = half_t + gap
    n_out = n_in + _CUFF_BACK
    n_tip = _CUFF_ARM_REACH
    rh, tip = _CUFF_RIDGE_HALF, _CUFF_RIDGE_TIP
    vb0, vb1 = -(gap + arm), -gap
    vt0, vt1 = width + gap, width + gap + arm
    chamfer = 0.4
    section = np.array(
        [
            (vb0, n_tip),
            (vb0, n_out - chamfer),
            (vb0 + chamfer, n_out),
            (vt1 - chamfer, n_out),
            (vt1, n_out - chamfer),
            (vt1, n_tip),
            (vt0, n_tip),
            (vt0, -rh),
            (width - tip, 0.0),
            (vt0, rh),
            (vt0, n_in),
            (vb1, n_in),
            (vb1, rh),
            (tip, 0.0),
            (vb1, -rh),
            (vb1, n_tip),
        ]
    )
    half_width = frame.leg_thickness / 2
    return _extrude_vn(section, (-half_width, half_width))


def _leg_connector(tab: TabFrame, frame: FrameParams) -> Manifold:
    """脚の上端の帯を抱くCを、帯の曲がりに沿って曲げた世界座標で返す。"""
    local = _cuff_local(frame, _band_top_v(tab, frame))
    return local.warp_batch(lambda xyz: _joint_to_world(tab, np.asarray(xyz)))


def _connector_rod_start(frame: FrameParams) -> tuple[float, float, float]:
    """棒の起点を連結部の局所座標で返す(起点のv, 起点のn, 鼻の側面に沿って
    降り始める高さのv)。棒は帯を抱くCの下の腕の中から始まり、Cの背の外面と
    棒の外面がそろう高さ(n)に置く。"""
    blade_t = frame.leg_thickness / _BLADE_ASPECT
    n_out = frame.bridge_thickness / 2 + _CUFF_GAP + _CUFF_BACK
    v_mid = -(_CUFF_GAP + _CUFF_ARM / 2)
    return v_mid, n_out - blade_t / 2, -(_CUFF_GAP + _CUFF_ARM) - 0.3


# 棒(ブレード)を切り落とす高さ(連結部の局所座標v)。平たい断面の角が起点より
# 上へ出て帯の下縁に当たらないよう、帯の下縁より少し下で切る(切り口はCの
# 下の腕の中に収まる)
_BLADE_TRIM_V = -(_CUFF_GAP + 0.03)


def _to_manifold(mesh: trimesh.Trimesh) -> Manifold:
    """trimeshの閉じたメッシュをmanifold3dのManifoldに変換する。"""
    return Manifold(
        Mesh(
            vert_properties=np.asarray(mesh.vertices, dtype=np.float32),
            tri_verts=np.asarray(mesh.faces, dtype=np.uint32),
        )
    )


def _to_trimesh(manifold: Manifold) -> trimesh.Trimesh:
    """manifold3dのManifoldを、連結成分・退化面の後処理をしたtrimeshに変換する。

    同一座標の頂点の統合は、trimesh側(Trimesh(process=True)や
    merge_vertices())ではなくmanifold3d側(Mesh.merge())で行う。trimeshの
    統合は距離の閾値で機械的に潰すため、面同士が浅い角度で接する箇所では
    non-manifoldな縁を作ってしまい、閉じていたはずの立体が
    is_watertight=Falseになることが実測であった(探索範囲のランダム
    サンプルで1/60程度の頻度)。manifold3dの統合は、自身が保証する
    多様体性を壊さない範囲で行われる。
    """
    mesh = manifold.to_mesh()
    mesh.merge()
    result = trimesh.Trimesh(
        vertices=mesh.vert_properties[:, :3], faces=mesh.tri_verts, process=False
    )
    return _clean_boolean_result(_largest_component(result))


def _rod_manifold(rod: RodPath) -> Manifold:
    """棒を、経路上の各点に置いた球(半径は点ごと)の結合で作る。

    球の間隔(_ROD_SAMPLE_SPACING=0.2mm)は棒の半径(1mm前後)よりずっと
    小さいので、隣り合う球は必ず体積を持って重なり、触れるだけの関係が
    どこにも生じない。表面は球の連なりの分だけ波打つが、その深さは
    r-sqrt(r^2-(間隔/2)^2)で半径1mmなら0.005mmと、印刷の分解能よりはるかに
    細かい。

    以前は「隣り合う2点の球の凸包」を連ねていた。凸包どうしは共有する球の
    表面では接するだけで内部が重ならず、その接触面が出力に残ると、STLへ
    書き出して座標で頂点を統合し直したときに1本の辺を4面が共有する
    non-manifoldな縁ができ、閉じた立体でなくなる(実測: 探索範囲の
    ランダムサンプルで10〜20件に1件)。1つおきに半径を変える・球を半コマ
    回す・経路の角を丸めるといった対策でも完全には消えず、球だけの結合に
    変えて初めて全件で安定した。
    """
    spheres = [
        Manifold.sphere(float(radius), _ROD_SPHERE_SEGMENTS).translate(
            tuple(float(c) for c in point)
        )
        for point, radius in zip(rod.points, rod.radii)
    ]
    return Manifold.batch_boolean(spheres, OpType.Add)


def _blade_section(width: float, thickness: float) -> np.ndarray:
    """ブレードの断面(角丸長方形)の輪郭点列 (N, 2) を返す。"""
    half_w, half_t = width / 2, thickness / 2
    radius = min(half_w, half_t) * _BLADE_CORNER_RATIO
    corners = [
        (half_w - radius, half_t - radius),
        (-half_w + radius, half_t - radius),
        (-half_w + radius, -half_t + radius),
        (half_w - radius, -half_t + radius),
    ]
    per_corner = _BLADE_SECTION_POINTS // 4
    points = []
    for index, (corner_x, corner_y) in enumerate(corners):
        start = np.pi / 2 * index
        angles = np.linspace(start, start + np.pi / 2, per_corner)
        points.extend(
            [
                (corner_x + radius * np.cos(a), corner_y + radius * np.sin(a))
                for a in angles
            ]
        )
    return np.array(points)


def _blade_twist(
    points: np.ndarray, start_wide: np.ndarray, end_wide: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """経路に沿って運んだ回転最小化フレームと、始点の幅の向き(start_wide)を
    終点の幅の向き(end_wide)へ合わせるのに要るねじれ角(ラジアン)を返す。

    回転最小化フレームは、経路の曲がりだけに追従して、経路の向きのまわりには
    余計に回らない基準の向き(二重反射法、Wang et al. 2008)。これに対して
    ねじれを後から均等に配ることで、板の向きが曲がりの具合に引きずられて
    急に回ることがなくなる。
    """
    tangents = np.gradient(points, axis=0)
    tangents /= np.linalg.norm(tangents, axis=1, keepdims=True)
    reference = np.empty_like(points)
    first = start_wide - tangents[0] * np.dot(start_wide, tangents[0])
    reference[0] = first / np.linalg.norm(first)
    for i in range(len(points) - 1):
        step = points[i + 1] - points[i]
        c1 = float(np.dot(step, step))
        if c1 < 1e-18:
            reference[i + 1] = reference[i]
            continue
        r_left = reference[i] - (2 / c1) * np.dot(step, reference[i]) * step
        t_left = tangents[i] - (2 / c1) * np.dot(step, tangents[i]) * step
        v2 = tangents[i + 1] - t_left
        c2 = float(np.dot(v2, v2))
        reference[i + 1] = (
            r_left if c2 < 1e-18 else r_left - (2 / c2) * np.dot(v2, r_left) * v2
        )
    target = end_wide - tangents[-1] * np.dot(end_wide, tangents[-1])
    target /= np.linalg.norm(target)
    angle = float(
        np.arctan2(
            np.dot(np.cross(reference[-1], target), tangents[-1]),
            np.dot(reference[-1], target),
        )
    )
    # 断面は幅の向きについて対称なので、半回転ぶんは同じ形になる。回す量が
    # 小さいほうを選ぶ
    if angle > np.pi / 2:
        angle -= np.pi
    elif angle < -np.pi / 2:
        angle += np.pi
    return tangents, reference, np.cross(tangents, reference), angle


def _blade_frames(
    points: np.ndarray, start_wide: np.ndarray, end_wide: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """経路の各点での(接線, 幅方向, 厚み方向)を返す。

    幅方向は、始点(アーチの帯の面)から終点(リングの輪の面)へなめらかに
    ねじれる。制約から決まった経路(鼻の側面を降りて輪へ回り込む)を、
    そのまま意匠として読ませるための造形。

    以前は始点と終点の向きを直線的に混ぜてから経路の向きに直交させて
    いたため、経路が曲がるところで板の向きが急に回った(実測: 0.2mmの
    間に最大37.7度)。回転最小化フレーム(_blade_twist)を基準にして、
    必要なねじれを弧長に沿ってなめらか(両端で0になる形)に配る。
    """
    tangents, reference, binormal, angle = _blade_twist(points, start_wide, end_wide)
    steps = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))])
    ratio = steps / max(float(steps[-1]), 1e-9)
    phase = angle * (ratio**2 * (3 - 2 * ratio))
    wide = reference * np.cos(phase)[:, None] + binormal * np.sin(phase)[:, None]
    thick = np.cross(tangents, wide)
    return tangents, wide, thick


def blade_twist_rate(rod: RodPath, tab: TabFrame) -> float:
    """ブレードが1mmあたり何度ねじれるかを返す。

    アーチの面からリングの面へ向きを変えるのに要るねじれ角
    (回転最小化フレームに対して、_blade_twist)を、棒の長さで割ったもの。
    短い棒で急に回すと「ねじれた板」ではなく「ひねって折り曲げた板」に
    見えるため、evaluation側でこの密度に上限を課している
    (blade_twist_margin)。
    """
    length = float(np.sum(np.linalg.norm(np.diff(rod.points, axis=0), axis=1)))
    if length <= 0:
        return np.inf
    *_, angle = _blade_twist(
        rod.points, np.asarray(tab.u, dtype=float), np.array([0.0, 1.0, 0.0])
    )
    return abs(np.degrees(angle)) / length


def _blade_manifold(rod: RodPath, tab: TabFrame) -> Manifold:
    """棒を、ねじれながら進む平たいブレードとして作る。

    経路上に断面(角丸長方形)を並べ、隣り合う断面の対応する点どうしを
    四角形(三角形2枚)でつないだ1本の管(ロフト)にし、両端を断面の
    扇形でふさぐ。ブーリアン演算を使わずに、はじめから閉じた1つの立体に
    なる。曲がりの半径が棒の半幅を下回らない(rod_kink_margin)ので、
    曲がりの内側で隣の断面どうしが交差することもない。

    以前は1つ飛ばしの2断面(i と i+2)の凸包を重ねて結合していた。
    なめらかな区間では隣り合う凸包の側面がほとんど同じ平面になり、
    結合の結果に面積ほぼ0の細い三角形が残って、STLへ書き出すと1本の辺を
    4面が共有した(実測: 探索範囲のランダムサンプルで1/31)。さらに前は、
    断面に薄い厚みを与えた輪切りを積み重ねていたが、曲がるところで輪切りの
    角が段々に並び、見た目も印刷も粗かった(ユーザー指摘)。

    RodPath.radiiは断面の「半幅」として使い、厚みは幅/_BLADE_ASPECT。
    半幅はレンズ・帯に収まる上限として決めてあるので(_rod_radii)、
    平たくしたことで新たにはみ出すことはない(厚み方向はむしろ細くなる)。
    """
    points = _resample(rod.points, _BLADE_SLICE_SPACING)
    radii = np.interp(
        np.linspace(0.0, 1.0, len(points)),
        np.linspace(0.0, 1.0, len(rod.radii)),
        rod.radii,
    )
    _, wide, thick = _blade_frames(
        points, np.asarray(tab.u, dtype=float), np.array([0.0, 1.0, 0.0])
    )
    rings = []
    for point, radius, w_dir, t_dir in zip(points, radii, wide, thick):
        width = float(radius) * 2
        outline = _blade_section(width, width / _BLADE_ASPECT)
        # 角の丸めの半径が厚みの半分に等しいと、隣の角の弧の端点と重なる
        keep = np.linalg.norm(outline - np.roll(outline, 1, axis=0), axis=1) > 1e-9
        outline = outline[keep]
        rings.append(point + outline[:, :1] * w_dir + outline[:, 1:] * t_dir)
    count, per_ring = len(rings), len(rings[0])
    vertices = np.vstack(rings + [rings[0].mean(axis=0), rings[-1].mean(axis=0)])
    faces = []
    for i in range(count - 1):
        for k in range(per_ring):
            a, b = i * per_ring + k, i * per_ring + (k + 1) % per_ring
            c, d = b + per_ring, a + per_ring
            faces.extend([(a, b, c), (a, c, d)])
    start_cap, end_cap = count * per_ring, count * per_ring + 1
    last = (count - 1) * per_ring
    for k in range(per_ring):
        faces.append((start_cap, (k + 1) % per_ring, k))
        faces.append((end_cap, last + k, last + (k + 1) % per_ring))
    faces = np.array(faces)
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    # 断面の点の並び(時計回り/反時計回り)と経路の向きの組み合わせで、
    # 面が内向きになる場合は裏返す
    if mesh.volume < 0:
        mesh.invert()
    return _to_manifold(mesh)


def _open_ring_wedge(collar: CollarGeometry, side: Literal[-1, 1]) -> Manifold:
    """リングを鼻中隔側でC字に開くために抜く、扇形の角柱を返す。"""
    angle = np.radians(_OPEN_RING_GAP_DEG)
    reach = collar.r_outer * 3
    center_angle = np.pi if side > 0 else 0.0
    angles = np.linspace(center_angle - angle / 2, center_angle + angle / 2, 16)
    polygon = np.vstack(
        [[0.0, 0.0], np.stack([np.cos(angles), np.sin(angles)], axis=1) * reach]
    )
    height = (collar.y_end - collar.y_start) * 3
    mesh = trimesh.creation.extrude_polygon(Polygon(polygon), height)
    mesh.apply_translation([0.0, 0.0, -height / 2])
    mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    y_mid = (collar.y_start + collar.y_end) / 2
    mesh.apply_translation([collar.center_x, y_mid, collar.center_z])
    return _to_manifold(mesh)


# _clean_boolean_resultで同じ点とみなす頂点間の距離(mm)。float32の丸め
# (1e-6mm程度)より十分大きく、印刷の分解能よりはるかに小さい
_VERTEX_SNAP = 1e-5


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

    座標ベースの統合はmanifold3d側(_to_trimeshのMesh.merge())でも行うが、
    それは自身の多様体性を保つ範囲の統合なので、STLの読み手が行う「距離の
    閾値で機械的に潰す」統合とは結果が違う。書き出したものが読み直しても
    同じであるように、ここで後者と同じ統合をかけ、その結果に現れる退化面を
    取り除いてから返す(=書き出す形は既に統合済みで、読み直しても変化
    しない)。

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
    merged = _merge_and_drop_degenerate(mesh, snap=False)
    if merged.is_watertight:
        return merged
    # manifold3dの頂点はfloat32なので、本来同じ点が1ulp(座標13mm付近で
    # 約1e-6mm)だけずれて別々に残ることがある。座標が厳密に一致しないと
    # merge_vertices()では統合されず、その縁に細い隙間が残って閉じた立体で
    # なくなった(実測: 帯の穴の縁、探索範囲のランダムサンプルで1/16)。
    # そのときだけ_VERTEX_SNAPより近い頂点を同じ座標へ寄せてから統合する
    # (常に寄せると、細かい三角形の多い脚の部品で逆に閉じなくなった)
    snapped = _merge_and_drop_degenerate(mesh, snap=True)
    return snapped if snapped.is_watertight else merged


def _merge_and_drop_degenerate(mesh: trimesh.Trimesh, snap: bool) -> trimesh.Trimesh:
    """_clean_boolean_resultの本体(座標での頂点統合と、退化面の除去)。"""
    mesh = mesh.copy()
    if snap:
        vertices = mesh.vertices.copy()
        for a, b in sorted(cKDTree(vertices).query_pairs(_VERTEX_SNAP)):
            vertices[b] = vertices[a]
        mesh.vertices = vertices
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
    _band_meshがブリッジの格子点の各点の向きを決めるために使う。

    _offset_along_surface_normalと同じ最近接三角形の法線を求める処理だが、
    すでにオフセット済みの点(表面のごく近く)に対して法線だけを求め直す
    (点自体は動かさない)。
    """
    _, _, triangle_id = trimesh.proximity.closest_point(body, points)
    return body.face_normals[triangle_id]
def _band_mesh(
    body: trimesh.Trimesh, params: NoseParams, frame: FrameParams
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
    grid = _bridge_grid(
        params, frame.bridge_y, frame.bridge_width, frame.tab_side_ratio
    )
    rows, cols, _ = grid.shape
    # 格子点は帯の肌側の面そのもの(_bridge_profileの曲線。すでに鼻から
    # BRIDGE_OFFSET以上浮いている)。厚みはその曲線の外向きの法線(y成分なし)に
    # 取る。鼻の表面の法線を使うと、端をまっすぐ伸ばして鼻から浮いている
    # ところで帯の厚みの向きがずれる
    normals = np.zeros_like(grid)
    for row in range(rows):
        profile = _bridge_profile(params, float(grid[row, 0, 1]), frame.tab_side_ratio)
        normals[row][:, [0, 2]] = profile.normals
    flat = grid.reshape(-1, 3)
    normals = normals.reshape(-1, 3)
    thickness = frame.bridge_thickness
    bottom = flat
    top = flat + normals * thickness
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
    """ブリッジ(長方形断面の帯)の実際の頂点の鼻本体メッシュへの
    めり込み量が、厚みに比例した許容量(_EMBED_RATIO)を超えていないかを
    返す(正=超過量、0以下=許容範囲内)。earrings.frame_model.
    ring_clearance_marginと同じ考え方(ブリッジは鼻表面に沿わせて曲げる
    設計だが、押し込みは意図していないため、長方形断面が曲面と完全に
    一致しないことに由来する残留めり込みの水準までしか許容しない)。
    """
    radius = frame.bridge_thickness / 2
    allowed_embed = _EMBED_RATIO * radius
    band = _band_mesh(body, params, frame)
    signed_distance = _signed_distance_to_body(body, band.vertices)
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


def leg_clearance_margin(
    rods: list[RodPath], tabs: list[TabFrame], body: trimesh.Trimesh
) -> float:
    """棒(ブレード)の鼻本体メッシュへのめり込み量が、その点の断面の
    張り出しに比例した許容量(_EMBED_RATIO)を超えていないかを返す
    (正=超過量、0以下=許容範囲内。左右のうち厳しい方)。

    棒は平たいブレードで、断面の向きが経路に沿ってねじれる(_blade_frames)。
    肌の側への張り出しは、断面の半幅(RodPath.radii)と半厚み(半幅/
    _BLADE_ASPECT)を、その点の肌の法線へ射影した長さになる。以前は棒を
    球(半径=半幅)とみなしていたが、ブレードの付け根は薄い面を肌に向けて
    寝ているので、実際の張り出し(実測0.73mm)の2倍以上(1.60mm)で
    測ってしまい、問題のない形を違反と判定していた。

    符号(内外)は疑似法線ではなくtrimesh.Trimesh.containsで決める(棒は
    鼻の下端=メッシュが途切れる縁の近くを通り、疑似法線は誤判定するため。
    collar_clearance_marginと同じ)。
    """
    worst = -np.inf
    for rod, tab in zip(rods, tabs):
        # _blade_manifoldと同じ向きの計算(世界座標のまま)
        _, wide, thick = _blade_frames(
            rod.points, np.asarray(tab.u, dtype=float), np.array([0.0, 1.0, 0.0])
        )
        closest, distance, _ = trimesh.proximity.closest_point(body, rod.points)
        inside = body.contains(rod.points)
        signed = np.where(inside, -distance, distance)
        toward = rod.points - closest
        toward /= np.maximum(np.linalg.norm(toward, axis=1, keepdims=True), 1e-9)
        extent = rod.radii * np.abs(np.einsum("ij,ij->i", wide, toward)) + (
            rod.radii / _BLADE_ASPECT
        ) * np.abs(np.einsum("ij,ij->i", thick, toward))
        embed = extent - signed
        worst = max(worst, float((embed - _EMBED_RATIO * extent).max()))
    return worst


def validate_leg_clearance(
    rods: list[RodPath], tabs: list[TabFrame], body: trimesh.Trimesh
) -> None:
    """leg_clearance_marginが正(=違反)の場合に例外を送出する。"""
    margin = leg_clearance_margin(rods, tabs, body)
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


def rod_kink_margin(rods: list[RodPath]) -> float:
    """棒の曲がりの半径が、その場所の棒の半径に対して十分あるかを返す
    (正=不足、0以下=十分。左右のうち厳しい方)。

    曲がりの半径が棒の半幅を下回ると、板が折れ曲がったように見え(ユーザー
    指摘「うねる部分が不格好」)、そこは肉が急に厚くなる応力集中の角で、
    印刷の反りや折れの起点にもなる。
    3点ずつの外接円の半径で曲がりの半径を測り、棒の半径の
    _MIN_TURN_RADIUS_RATIO倍を下回らないことを要求する(実測: 経路の角を
    丸める前は曲率半径0.14mmに対し棒の半径1.01mmだった)。
    """
    worst = -np.inf
    for rod in rods:
        points, radii = rod.points, rod.radii
        before, here, after = points[:-2], points[1:-1], points[2:]
        cross = np.cross(before - here, after - here)
        area = np.linalg.norm(cross, axis=1)
        sides = (
            np.linalg.norm(before - here, axis=1)
            * np.linalg.norm(after - here, axis=1)
            * np.linalg.norm(before - after, axis=1)
        )
        turn_radius = np.where(area > 1e-12, sides / np.maximum(2 * area, 1e-12), np.inf)
        worst = max(worst, float((_MIN_TURN_RADIUS_RATIO * radii[1:-1] - turn_radius).max()))
    return worst


def validate_rod_kink(rods: list[RodPath]) -> None:
    """rod_kink_marginが正(=違反)の場合に例外を送出する。"""
    margin = rod_kink_margin(rods)
    if margin > _MARGIN_TOLERANCE:
        raise ValueError(
            f"棒の曲がりが急すぎて管が自分自身に食い込んでいる(不足{margin:.3f}mm)"
        )


def rod_thickness_margin(rods: list[RodPath]) -> float:
    """棒(ブレード)の最も細いところが、印刷に必要な寸法を下回っていないかを
    返す(正=不足量、0以下=十分。左右・幅/厚みのうち最も厳しい値)。

    ユーザー指摘(「レンズ部分とそれの棒の部分もう少し太くしてください。
    印刷時に上手く印刷できないので」)への対応。棒はレンズへ溶け込む区間で
    最も細くなり、その太さはレンズの壁の肉厚(_COLLAR_WALL_THICKNESS)と
    レンズの厚み(frame.collar_length)で決まる(_rod_radii参照)ため、
    collar_lengthが小さい個体をGAが避けるように誘導する。

    棒は平たいブレード(_blade_manifold)なので、幅(RodPath.radiiの2倍)と
    厚み(幅/_BLADE_ASPECT)を別々の下限で見る。
    """
    narrowest = min(float(rod.radii.min()) * 2 for rod in rods)
    return max(
        _MIN_ROD_WIDTH - narrowest,
        _MIN_ROD_THICKNESS - narrowest / _BLADE_ASPECT,
    )


def validate_rod_thickness(rods: list[RodPath]) -> None:
    """rod_thickness_marginが正(=違反)の場合に例外を送出する。"""
    margin = rod_thickness_margin(rods)
    if margin > _MARGIN_TOLERANCE:
        raise ValueError(
            f"棒の最も細いところが、印刷に必要な寸法(幅{_MIN_ROD_WIDTH}mm・"
            f"厚み{_MIN_ROD_THICKNESS}mm)に{margin:.3f}mm足りない。"
            "collar_lengthを大きくすること"
        )


def blade_twist_margin(rods: list[RodPath], tabs: list[TabFrame]) -> float:
    """ブレードのねじれの密度が上限(_MAX_BLADE_TWIST_RATE)を超えていないかを
    返す(正=超過、0以下=十分ゆるやか。左右のうち厳しい方)。

    棒をアーチと同じ板の断面にしたうえで、その板をアーチの面からリングの面へ
    ねじる造形にしている(_blade_manifold)。ねじりに使える長さが足りないと、
    連続した一本の線ではなく「ひねって折り曲げた板」に見え、造形としての
    意図が読めなくなる。長さは装着位置(bridge_y)が決めるので、この制約は
    実質「アーチを十分高い位置に置け」という要求として効く。
    """
    return max(blade_twist_rate(rod, tab) for rod, tab in zip(rods, tabs)) - (
        _MAX_BLADE_TWIST_RATE
    )


def validate_blade_twist(rods: list[RodPath], tabs: list[TabFrame]) -> None:
    """blade_twist_marginが正(=違反)の場合に例外を送出する。"""
    margin = blade_twist_margin(rods, tabs)
    if margin > _MARGIN_TOLERANCE:
        raise ValueError(
            f"ブレードのねじれが急すぎる(上限{_MAX_BLADE_TWIST_RATE}度/mmを"
            f"{margin:.2f}度/mm超過)。bridge_yを大きくして棒を長くすること"
        )


def _cuff_lever(frame: FrameParams) -> float:
    """帯を抱くCの背の、下の腕(棒の付け根)から上の腕までの長さ(mm)。"""
    return frame.bridge_width + 2 * _CUFF_GAP + _CUFF_ARM


def cuff_strain_margin(frame: FrameParams) -> float:
    """帯の端近くの浅い段を越えるとき、帯を抱くCが折れないかを返す
    (正=ひずみの超過量、0以下=十分)。

    段を越えるとき、上下の爪がそれぞれcuff_detentだけ押し広げられる。
    下の腕は棒につながっていて動かないので、Cの背を下の腕を固定端とする
    片持ち梁とみなし、上の腕が2*cuff_detent開いたときの付け根の曲げひずみ
    ε = 1.5·t·δ/L² が_MAX_CUFF_STRAINを超えないことを要求する(tは背の厚み、
    Lは_cuff_lever)。締めしろを大きくするほど抜けにくいが
    (cuff_retention_margin)、そのぶん大きく開くことになり、この制約と
    引っ張り合う。帯が広いほど背が長くなって、同じ締めしろでもしなりやすい。
    """
    lever = _cuff_lever(frame)
    strain = 1.5 * _CUFF_BACK * (2 * frame.cuff_detent) / lever**2
    return strain - _MAX_CUFF_STRAIN


def cuff_hold_force(frame: FrameParams) -> float:
    """帯を抱くCが浅い段を越えるのに要る力(N)の見積もり。

    cuff_strain_marginと同じ片持ち梁で、上の腕を2*cuff_detent開くのに要る
    力 F = 3EI·δ/L³(I=b·t³/12、bはCの長さ=棒の幅)。段の坂は45度なので、
    帯に沿って押す力もほぼ同じ大きさになる。
    """
    lever = _cuff_lever(frame)
    inertia = frame.leg_thickness * _CUFF_BACK**3 / 12
    return 3 * _PRINT_MODULUS * inertia * (2 * frame.cuff_detent) / lever**3


def cuff_retention_margin(frame: FrameParams) -> float:
    """帯を抱くCを外すのに要る力が、ちょうど良い範囲にあるかを返す
    (正=範囲外の量(N)、0以下=範囲内)。

    弱すぎる(_MIN_CUFF_HOLD_FORCE未満)と顔に触れた程度で滑って外れ、
    強すぎる(_MAX_CUFF_HOLD_FORCE超)と手で外しにくい(ユーザー要望
    「付けたり取り外ししやすい」)。
    """
    force = cuff_hold_force(frame)
    return max(_MIN_CUFF_HOLD_FORCE - force, force - _MAX_CUFF_HOLD_FORCE)


def _straight_length(profile: BridgeProfile) -> float:
    """帯の曲線の、+x側の端からまっすぐとみなせる長さ(mm)。端での向きから
    _STRAIGHT_ANGLE_DEGを超えて曲がるところまで。"""
    cos_limit = np.cos(np.radians(_STRAIGHT_ANGLE_DEG))
    bent = profile.normals @ profile.normals[0] < cos_limit
    return float(profile.s[np.argmax(bent)]) if bent.any() else profile.length


def cuff_fit_margin(frame: FrameParams, params: NoseParams) -> float:
    """帯を抱くCと縁の溝が帯に無理なく収まるかを返す(正=不足量、0以下=
    収まる。以下のうち最も厳しい値)。

    - 縁のV溝の両脇に帯の肉が残ること(_CUFF_MIN_EDGE_WALL)
    - Cの爪先(腕の先端)が帯の肌側の面より_CUFF_MIN_ARM_INSETだけ手前で
      止まること(肌と帯の間に入らない)
    - 溝の範囲(帯の端から_CONNECTOR_S_ENDまで)と、装着した位置のCが、帯の
      まっすぐな区間に収まること(Cは帯に沿って滑るので曲がりにかかると
      引っかかる。印刷形では溝をその位置の接線で回して置くだけなので、
      まっすぐでないとずれる)
    - 帯の厚みが印刷に耐える最小値(_MIN_BRIDGE_THICKNESS)以上であること
    """
    half_t = frame.bridge_thickness / 2
    edge_wall = _CUFF_MIN_EDGE_WALL - (half_t - _CUFF_GROOVE_HALF)
    arm = (-half_t + _CUFF_MIN_ARM_INSET) - _CUFF_ARM_REACH
    y_edge = frame.bridge_y - frame.bridge_width / 2
    straight = min(
        _straight_length(_bridge_profile(params, y, frame.tab_side_ratio))
        for y in (y_edge, y_edge + frame.bridge_width)
    )
    reach = max(_CONNECTOR_S_END, frame.leg_thickness + _CUFF_END_OFFSET)
    lateral = reach - straight
    thickness = _MIN_BRIDGE_THICKNESS - frame.bridge_thickness
    return max(edge_wall, arm, lateral, thickness)


def _cuff_sample_points(tab: TabFrame, frame: FrameParams) -> np.ndarray:
    """帯を抱くCの表面をおおまかに覆う点(世界座標)。断面の輪郭の点を
    帯に沿って何か所かに並べ、帯の曲がりに沿って曲げる。"""
    top_v = _band_top_v(tab, frame)
    half_t = frame.bridge_thickness / 2
    n_out = half_t + _CUFF_GAP + _CUFF_BACK
    vb0, vt1 = -(_CUFF_GAP + _CUFF_ARM), top_v + _CUFF_GAP + _CUFF_ARM
    outline = []
    for v in np.linspace(vb0, vt1, 12):
        outline.append((v, n_out))
    for n in np.linspace(_CUFF_ARM_REACH, n_out, 6):
        outline.extend([(vb0, n), (vt1, n)])
    outline.extend([(v, _CUFF_ARM_REACH) for v in (vb0, -_CUFF_GAP, top_v + _CUFF_GAP, vt1)])
    half_width = frame.leg_thickness / 2
    local = np.array(
        [(u, v, n) for u in np.linspace(-half_width, half_width, 5) for v, n in outline]
    )
    return _joint_to_world(tab, local)


def cuff_skin_margin(frame: FrameParams, tabs: list[TabFrame], body: trimesh.Trimesh) -> float:
    """帯を抱くCが肌に当たらないかを返す(正=すき間の不足量、0以下=十分。
    左右のうち厳しい方)。

    Cの腕は帯の下縁・上縁の外に出るので、鼻が下へ向かって横に張り出して
    いるところでは、腕の角が肌に近づく。Cの表面の点と鼻本体メッシュの
    符号付き距離(外が正)の最小値が_MIN_CUFF_SKIN_GAP以上であることを要求する。
    """
    worst = -np.inf
    for tab in tabs:
        points = _cuff_sample_points(tab, frame)
        closest, _, triangle_id = trimesh.proximity.closest_point(body, points)
        gap = np.einsum("ij,ij->i", points - closest, body.face_normals[triangle_id])
        worst = max(worst, _MIN_CUFF_SKIN_GAP - float(gap.min()))
    return worst


def cuff_frontal_area(tab: TabFrame, frame: FrameParams) -> float:
    """帯を抱くCを顔の正面(x-y平面)から見た影の面積(mm^2)。"""
    points = _cuff_sample_points(tab, frame)
    return float(MultiPoint([tuple(p) for p in points[:, :2]]).convex_hull.area)


def validate_cuff(
    frame: FrameParams, params: NoseParams, tabs: list[TabFrame], body: trimesh.Trimesh
) -> None:
    """帯を抱くCの4つの制約(cuff_fit/strain/retention/skin)のどれかが正
    (=違反)の場合に例外を送出する。"""
    checks = (
        ("帯を抱くCが帯に収まらない(cuff_fit)", cuff_fit_margin(frame, params)),
        ("帯を抱くCが着脱時に開きすぎる(cuff_strain)", cuff_strain_margin(frame)),
        ("帯を抱くCを外す力が範囲外(cuff_retention)", cuff_retention_margin(frame)),
        ("帯を抱くCが肌に近すぎる(cuff_skin)", cuff_skin_margin(frame, tabs, body)),
    )
    for message, margin in checks:
        if margin > _MARGIN_TOLERANCE:
            raise ValueError(f"{message}: 超過{margin:.3f}")


def joint_access_margin(
    frame: FrameParams, params: NoseParams, body: trimesh.Trimesh
) -> float:
    """連結部が鼻の側面に十分寄っているかを返す(正=不足、0以下=十分)。

    ユーザー指摘「アーチと棒の接続部分、もう少し外側にあってもいい。今だと
    鼻の正面に沿っていて、メガネをしていると付けづらそう」への対応。
    タブ中心のxが、その高さの断面の最大x(鼻のいちばん横に張り出す位置)の
    _MIN_JOINT_LATERAL_RATIO倍以上あることを要求する。

    正面寄りに置くほどメガネの鼻パッド・ブリッジと重なり、押し込むときに
    指も正面から入れることになる。一方で外側へ寄せるほど、その外側に残る
    テープの貼り代(tape_pad_area)が短くなるので、tab_side_ratioは
    この2つの釣り合いで決まる。
    """
    half_width, depth_back, depth_front = surface_profile_at(params, frame.bridge_y)
    ring_2d = rounded_triangle_ring(half_width, depth_back, depth_front)
    widest = float(ring_2d[:, 0].max())
    tab = _tab_frame(frame, params, body, 1)
    return _MIN_JOINT_LATERAL_RATIO - float(tab.center[0]) / widest


def validate_joint_access(
    frame: FrameParams, params: NoseParams, body: trimesh.Trimesh
) -> None:
    """joint_access_marginが正(=違反)の場合に例外を送出する。"""
    margin = joint_access_margin(frame, params, body)
    if margin > _MARGIN_TOLERANCE:
        raise ValueError(
            f"連結部が鼻の正面に寄りすぎている(不足{margin:.3f})。"
            "tab_side_ratioを大きくすること"
        )


def tape_pad_area(frame: FrameParams, params: NoseParams) -> float:
    """両端の貼り代(連結部より外側の帯)の面積の合計(mm^2)を返す。

    医療用の両面テープを貼る面で、ここに貼った分だけ帯の拡張力を小鼻へ
    伝えられる(ユーザーの用途: 「アーチの両端に両面テープを貼って
    ブリーズライトのように小鼻を広げる」)。帯の端で肌に届く長さ
    (_tape_pad)×帯の幅を左右2枚ぶん。
    """
    length, _ = _tape_pad(params, frame.bridge_y, frame.tab_side_ratio)
    return 2 * length * frame.bridge_width


def tape_outward_ratio(frame: FrameParams, params: NoseParams) -> float:
    """貼り代の面が、平均してどれだけ外(+x、小鼻を開く向き)を向いているかを
    0〜1で返す(_tape_pad)。

    帯が曲げ戻ろうとする力のうち、小鼻を実際に外へ開くのに使えるのは
    この向きの成分だけ(ユーザー指摘「ブリーズライトのような、鼻腔を
    広げる役割にならないといけない」)。拡張力(evaluation._extension_force)
    にそのまま掛ける。
    """
    _, outward = _tape_pad(params, frame.bridge_y, frame.tab_side_ratio)
    return outward


def tape_area_margin(frame: FrameParams, params: NoseParams) -> float:
    """貼り代の面積が_MIN_TAPE_AREAを下回っていないかを返す
    (正=不足量、0以下=十分)。
    """
    return _MIN_TAPE_AREA - tape_pad_area(frame, params)


def validate_tape_area(frame: FrameParams, params: NoseParams) -> None:
    """tape_area_marginが正(=違反)の場合に例外を送出する。"""
    margin = tape_area_margin(frame, params)
    if margin > _MARGIN_TOLERANCE:
        raise ValueError(
            f"両面テープの貼り代({tape_pad_area(frame, params):.1f}mm^2)が最小値"
            f"({_MIN_TAPE_AREA}mm^2)に{margin:.1f}mm^2足りない。bridge_widthを"
            "大きくするか、tab_side_ratioを小さくすること"
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
    """ブリッジ単体(平らな帯)を、左右の連結部の縁の溝(帯を抱くCの爪が入る。
    _cuff_groove_local)付きで構築する(着色済み)。+x側で作って帯に沿って
    曲げ、-x側はその鏡映。
    """
    body = build_nose_body(params)
    validate_joint_access(frame, params, body)
    validate_curvature(
        frame, bridge_points(body, params, frame.bridge_y, frame.tab_side_ratio)
    )
    validate_bridge_clearance(frame, params, body)

    band = _to_manifold(_band_mesh(body, params, frame))
    tab = _tab_frame(frame, params, body, 1)
    groove = _cuff_groove_local(frame, tab.inset, _band_top_v(tab, frame))
    groove = groove.warp_batch(lambda xyz: _joint_to_world(tab, np.asarray(xyz)))
    mesh = _to_trimesh(
        Manifold.batch_boolean([band, groove, groove.mirror((1.0, 0.0, 0.0))], OpType.Subtract)
    )
    mesh.visual.face_colors = _FRAME_COLOR
    return mesh


def _print_profile(frame: FrameParams, params: NoseParams) -> BridgeProfile:
    """印刷するときの帯の肌側の面の曲線を返す(build_bridge_print_piece)。

    装着した形(高さbridge_yの_bridge_profile)の曲がりを、場所ごとに
    一定の割合 actual_radius/natural_radius だけ弱めた曲線(弧長は同じ)。
    接線の向きを鼻の稜線(真ん中)からの角度で表し、その角度に割合を掛けて
    積分し直す。曲がりの分布(前面の丸みで強く、側面でまっすぐ)は装着した
    形のままなので、印刷した帯も同じアーチの形で、少し開いただけになる。
    評価関数の拡張力(evaluation._extension_force)の「たわみ
    1/actual_radius-1/natural_radius」は、ちょうどこの開いたぶんに当たる。
    """
    worn = _bridge_profile(params, frame.bridge_y, frame.tab_side_ratio)
    actual_radius, _ = bridge_curvature(list(_bridge_profile_points(params, frame.bridge_y, frame.tab_side_ratio)))
    ratio = min(actual_radius / frame.natural_radius, 1.0)
    steps = np.diff(worn.points, axis=0)
    angles = np.unwrap(np.arctan2(steps[:, 1], steps[:, 0]))
    middle = len(angles) // 2
    reference = (angles[middle - 1] + angles[middle]) / 2
    opened = reference + (angles - reference) * ratio
    lengths = np.linalg.norm(steps, axis=1)
    points = np.vstack(
        [[0.0, 0.0], np.cumsum(np.stack([np.cos(opened), np.sin(opened)], axis=1) * lengths[:, None], axis=0)]
    )
    # 真ん中の点を装着した形の真ん中の点にそろえる(左右対称に丸める)
    points += worn.points[len(points) // 2] - points[len(points) // 2]
    mirror = np.array([-1.0, 1.0])
    points = (points + (points * mirror)[::-1]) / 2
    return BridgeProfile(points=points, normals=_curve_normals(points), s=worn.s)


def build_bridge_print_piece(frame: FrameParams, params: NoseParams) -> trimesh.Trimesh:
    """印刷するときのブリッジ(自然な形の帯)を構築する(着色済み)。

    ブリーズライトは、平らな板ばねを鼻の上で曲げて両端を貼り、曲げ戻ろうと
    する力で小鼻を押し広げる。評価関数の拡張力(evaluation._extension_force)
    も「自然な形(曲率半径natural_radius)から、装着した形(build_bridge_piece)
    へ曲げたときの戻り」として計算している。以前は印刷用のSTLも装着した形
    そのもので出力していたため、実物は最初から鼻の形に曲がっていて
    予荷重がかからなかった。

    その後、帯を半径natural_radiusの円弧に伸ばした形にしたが、ほとんど
    平らな板になり「アーチ状が平べったすぎる。前と同じくらいのアーチ状が
    いい」(ユーザー指摘)。いまは装着した形と同じアーチを、曲がりだけ
    actual_radius/natural_radiusの割合に弱めた形にする(_print_profile)。

    幅・厚み・弧長は装着した形と同じで、連結部の帯側の仕掛け(帯を抱くCの
    縁の溝など)は、装着した形と同じく帯の端からの弧長の位置に付ける
    (曲げても肌側の面に沿った長さは変わらない)。
    """
    body = build_nose_body(params)
    y_edge = frame.bridge_y - frame.bridge_width / 2
    profile = _print_profile(frame, params)
    inner = profile.points
    outer = (profile.points + profile.normals * frame.bridge_thickness)[::-1]
    polygon = np.vstack([inner, outer])
    # 断面(x, z)をyへ押し出す。CrossSectionの(x, y)を(x, z)に、押し出しの
    # 向きをyに対応させる(反時計回りでなければ面にならない)
    if Polygon(polygon).exterior.is_ccw is False:
        polygon = polygon[::-1]
    strip = CrossSection([polygon.tolist()]).extrude(frame.bridge_width)
    strip = strip.transform(
        np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 0.0, 1.0, y_edge], [0.0, 1.0, 0.0, 0.0]])
    )
    # 連結部の帯側の仕掛けは、装着した形と同じく帯の端からの弧長の位置に付ける
    # (仕掛けは帯のまっすぐな区間に収まるので、その位置の接線・法線で
    # 回して置くだけでよい)。+x側で作り、-x側はその鏡映
    tab = _tab_frame(frame, params, body, 1)
    (point,), (normal,) = _profile_at(profile, tab.inset)
    axis_z = np.array([normal[0], 0.0, normal[1]])
    axis_x = np.array([normal[1], 0.0, -normal[0]])
    axis_y = np.cross(axis_z, axis_x)
    # 局所座標のn=0は帯の厚みの中央
    origin = np.array([point[0], y_edge, point[1]]) + axis_z * (frame.bridge_thickness / 2)
    matrix = np.column_stack([axis_x, axis_y, axis_z, origin])
    groove = _cuff_groove_local(frame, tab.inset, frame.bridge_width).transform(matrix)
    mesh = _to_trimesh(
        Manifold.batch_boolean([strip, groove, groove.mirror((1.0, 0.0, 0.0))], OpType.Subtract)
    )
    mesh.visual.face_colors = _FRAME_COLOR
    return mesh


def build_leg_piece(
    frame: FrameParams,
    plug: PlugParams,
    params: NoseParams,
    side: Literal[-1, 1],
) -> trimesh.Trimesh:
    """左右いずれか片側の、連結部+棒+リングを単一の部品として構築する
    (着色済み)。

    連結部の脚側(帯の上下の縁を抱く小さなC字。_leg_connector)
    から棒(_blade_manifold、ねじれる平たいブレード)が生え、鼻の側面を
    鼻翼の溝へ降りて、鼻中隔側を開いたC字のリングの外周へ溶け込む。3つは
    いずれも深く重なるため、触れるだけの関係にならない。
    """
    validate_target_reach(plug, params)
    validate_collar_no_overlap(plug, params)
    body = build_nose_body(params)
    validate_joint_access(frame, params, body)
    tab = _tab_frame(frame, params, body, side)
    collar = _collar_geometry(frame, plug, params, side)
    rod = _rod_path(frame, params, body, tab, collar, side)
    validate_leg_clearance([rod], [tab], body)
    validate_collar_clearance([collar], body)
    validate_collar_position(plug, params, collar, side)
    validate_lens_protrusion([rod], [collar])
    validate_rod_thickness([rod])
    validate_rod_kink([rod])
    validate_blade_twist([rod], [tab])
    validate_cuff(frame, params, [tab], body)

    lens = _to_manifold(_collar_mesh(collar))
    # 棒はCの下の腕の中から始まるが、平たい断面の角は起点より上へ出て帯の
    # 下縁に当たるので、帯の下縁より少し下の水平面で切り落とす
    # (_BLADE_TRIM_V。切り口はCの下の腕の中に収まる)
    blade = _blade_manifold(rod, tab).trim_by_plane(
        (0.0, -1.0, 0.0), -(float(tab.center[1]) + _BLADE_TRIM_V * float(tab.v[1]))
    )
    mesh = _to_trimesh(
        Manifold.batch_boolean(
            [
                blade,
                lens - _open_ring_wedge(collar, side),
                _leg_connector(tab, frame),
            ],
            OpType.Add,
        )
    )
    mesh.visual.face_colors = _FRAME_COLOR
    return mesh
