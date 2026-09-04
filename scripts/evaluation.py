"""フレームの評価関数(v3: 機能性・快適さ・意匠性の3目的+7制約)。
PROJECT.md の「評価関数」に対応。

frame_model.build_frame_pair が作るチューブメッシュを経由せず、経路の点列
(build_side_paths)と鼻本体メッシュだけを使って評価する。メッシュの生成
コストを払わずに済むため、遺伝的アルゴリズムが個体ごとに繰り返し
呼び出す用途でも軽量に計算できる。

## v2→v3: 「サブ項目の重み付け合成」をやめ、3目的+4制約に整理した

v2はfit_gap/smoothness/proportion_penaltyを「意匠性」という1軸のサブ項目
として並べ、合成方法(重み)を未定のまま残していた。しかし7項目のうち
本当に「トレードオフとして探索したい」ものは少なく、大半は「一定水準を
満たしていれば良い(わざと少し悪い値を選ぶ理由がない)」という合否に近い
性質だった。そこで以下のように再整理し、重みを発明する必要自体をなくした:

- **目的(3つ、NSGA-IIが探索するトレードオフ)**:
  - retention(機能性、最大化): grip_depthを増やせば保持力は上がるが
    painも増える、という本質的なトレードオフ
  - pain(快適さ、最小化): retentionと表裏一体
  - fit_gap(意匠性、最小化。旧fit_gap_mean): 素材の厚み・埋め込み具合との
    トレードオフとして探る価値がある3つ目の軸
- **制約(4つ、実行不可能個体を除外するための閾値判定。すべて0または
  一定値以下であるべき、わざと悪化させる理由がない値)**:
  - reach_gap: 保持部が鼻栓の露出端に届いているか(0であるべき)
  - fit_gap_max(旧fit_gap_maxのまま): 平均は良くても局所的に大きく
    浮いている点がないか
  - smoothness: 経路がジグザグしていないか
  - proportion_penalty: 太さが極端に細すぎ/太すぎないか
  - いずれも実際の閾値(reach_gap以外)はNSGA-II導入時の未決定事項
    (PROJECT.md参照)。現状のFrameScoreはこれらも生の値のまま返し、
    閾値判定(制約違反への変換)は呼び出し側(将来のGA連携層)に委ねる

## retentionにclip_angleを直接の乗数として含めない理由

サブエージェントによるレビューでは「clip_angleも保持力に寄与するはず」と
指摘されたが、実際のジオメトリ(frame_model.arm_points)を確認すると、
左右のアームは起点(x=0、clip_angleに依らず常に同じ点)から生えており、
clip_angleは起点から離れた後の開き方(左右への広がり方)にしか影響しない。
実物のバネ式クリップのように、起点そのものの角度が挟み込む力を生む
構造にはなっていないため、clip_angleをretentionの直接の乗数には含めない。

ただしこの判断は「clip_angleがretentionに一切影響してはいけない」という
意味ではない。後に、アームの実長(3D経路長)を接触面積の代理指標として使う
よう修正した(下記「retentionのarm_lengthを実際の経路長に置き換えた理由」
参照)ため、clip_angleを大きくして鼻翼側へ開くほど実長が伸び、間接的に
retentionへ寄与するようになった。これは「起点の角度が挟み込む力を生む」
という物理モデルとは別物で、「接触区間が長くなる」という接触面積の観点
からの寄与であり、上記の判断そのものとは矛盾しない。

## retentionのarm_thicknessをplug.diameterで頭打ちにする理由

別セッションのサブエージェントによるレビューで、retention(grip_depth×
arm_thickness)とproportion_penalty(太さ/長さ比の上限のみ)の組み合わせに
抜け穴が見つかった。当初proportion_penaltyの上限を緩く設定していたため、
grip_depthをほぼ0(=painもほぼ0)にしたままarm_thicknessだけ非現実的に
太くすると、意匠性側のコストをほぼ払わずにretentionだけ稼げてしまう
(v1で発覚した「体積を0に近づけて最適化目的と矛盾する」問題が、対象を
arm_thicknessに変えて再発した形)。

これに対し、retention自体にarm_thicknessの寄与の頭打ちを設け、
proportion_penaltyの上限も長さとの自己参照的な比率ではなく、シーン内に
実在する物理的な基準(鼻栓の直径)との比較に置き換えた。アームが鼻栓
本体よりも太くなる理由はなく、それを超えて太くしても保持力の向上には
寄与しない(=挟んでいる相手より太いクリップは、太さの分だけ無駄という
考え方)とみなす。

## retentionにarm_lengthを掛ける理由(アーチ型保持構造への変更)

NSGA-IIの実行結果をユーザーがレビューしたところ、パレート最適とされた
候補でアームが終始鼻表面から浮いており(実際に接触しているのは起点1点
だけ)、メガネのように鼻翼・鼻尖の少し上をアーチ状に挟むほうが実際には
落ちにくいはず、という指摘を受けた。

調査の結果、原因はmodels.frame_model.arm_pointsの幾何バグだった。起点
(x=0)だけは鼻表面へ正しくめり込ませていたが、それ以外の点はclip_angleで
外側(x≠0)へ開いていくにもかかわらず、x=0での前面最大値を安全マージンと
して使っていたため、実際の表面(xが0から離れるほど後退する)から乖離して
浮いていた(models.frame_model.arm_pointsのdocstring参照)。これを修正し、
アーム全体をgrip_depthで鼻表面へ沿わせるようにした。

アーム全体が接触区間になったことで、接触面積の代理指標としてretentionに
arm_length(接触区間の長さ)を掛けるようにした(メガネのアームが長く沿う
ほど落ちにくいのと同じ発想)。これにより、evaluate_frameがarm_lengthを
評価しないためGAの探索でarm_lengthが下限に張り付いていた既知の限界
(PROJECT.md参照)も同時に解消され、実際にNSGA-IIを動かすとarm_lengthが
トレードオフとして分布するようになったことを確認した。

## retentionのarm_lengthを実際の経路長に置き換えた理由(issue #1)

上記の修正でretentionはframe.arm_length(yの区間幅)に比例するようになった
が、これはclip_angleに依らず一定の値だった。実際にNSGA-IIを実行すると、
パレート最適候補のほとんどでclip_angleが1〜6度程度と小さいままで、
アームがほぼ鼻中隔の真上(x≈0)に留まり、鼻翼(nostril_gap/2〜tip_w/2付近)
まで横に開いていく候補をGAが選ばなかった。clip_angleを大きくしてもretention
が一切増えないため、GAにとって鼻翼側まで開く理由がなかったため。

「起点の角度自体は挟み込む力を生まない」という判断(上記「retentionに
clip_angleを直接の乗数として含めない理由」参照)は変えず、frame.arm_length
の代わりにarm_pointsの実際の3D経路長(x方向の広がりも含む点列のユークリッド
距離の合計)を使うよう修正した。clip_angleを大きくすると経路がx方向にも
伸びる分だけ実際の接触区間が長くなるため、この経路長を使えば「起点の角度」
という物理モデルを持ち出さずに、接触面積の観点から自然にclip_angleの寄与を
反映できる。_MAX_CLIP_ANGLE(60度)の範囲では経路長は最大でも
arm_length/cos(60°)=arm_length×2程度に収まるため、青天井に伸ばせる抜け穴には
ならない。

## holder_size_penaltyを廃止した理由(保持部の球の廃止)

ユーザーが実際の候補メッシュを見たところ、「複数の独立したパーツがはっきり
折れてつながっている」という指摘を受けた(issue #2)。原因を調査したところ、
smoothness制約(角度の数値評価)とは別に、frame_model側のメッシュ生成方法
(区間ごとに独立した円柱を生成して結合)自体が別部品の寄せ集めに見える
原因になっていた(frame_model.pyのモジュールdocstring参照)。

あわせて保持部(先端の球)の役割を調査したところ、評価関数のうち球の実在に
依存する項目はholder_size_penaltyだけで、これ自体「球が鼻栓より大きな
ドーム状になっていた」という球自身が生んだ問題を抑えるためだけに後から
追加された対症療法だったと判明した。reach_gap制約により、コネクタの終端
(path[-1])はすでに鼻栓の露出端にほぼ一致する位置まで到達しており、球は
その上にさらに乗せた別部品に過ぎなかった。ユーザーと相談し、球を独立した
部品としては廃止し(アーム+コネクタのチューブ自体の終端キャップが到達点を
兼ねる)、それに伴いholder_size_penalty制約も不要になったため削除した
(8制約→7制約)。
"""

from dataclasses import dataclass

import numpy as np
import trimesh

from models.frame_model import (
    FrameParams,
    SidePaths,
    arm_clearance_margin,
    build_side_paths,
    full_path_points,
    grip_depth_margin,
    grip_ring_margin,
    surface_following_points,
    validate_anchor_height,
    validate_target_reach,
)
from models.nose_model import NoseParams, build_nose_body
from models.plug_model import PlugParams, plug_outer_end

# プロポーション評価(下限)で許容する、太さ(arm_thickness)/全長 比の下限。
# 固定の「理想比率」を目標にすると設計者個人の美意識を客観指標と偽装する
# ことになるため、範囲内は罰則0とし、下回った分だけを罰則にする
# (毛髪のように細く見える、という明らかに破綻したケースだけを弾く緩い値。
# 現行のデフォルト値(比率約0.078)は範囲内に収まることを確認済み)
_MIN_THICKNESS_RATIO = 0.03
# retention・プロポーション評価(上限)で、arm_thicknessの寄与を頭打ちに
# する基準。plug.diameterに対する倍率(理由は上のモジュールdocstring参照)
_MAX_THICKNESS_TO_PLUG_DIAMETER = 1.0


def _path_length(points: list[np.ndarray]) -> float:
    """点列を順に結んだ折れ線の全長(隣接点間のユークリッド距離の合計)を返す。

    _retention(アームの実長)・_proportion_penalty(全長)の両方が、対象と
    なる点列が異なるだけで同じ計算をしていたため共通化した。
    """
    return sum(
        float(np.linalg.norm(points[i + 1] - points[i])) for i in range(len(points) - 1)
    )


def _retention(frame: FrameParams, plug: PlugParams, arm_points: list[np.ndarray]) -> float:
    """保持力(機能性、最大化)。grip_depth(めり込み量)×arm_thickness(剛性)×
    アームの実長(接触区間の3D経路長)。アーム全体がgrip_depthで鼻表面に沿う
    (models.frame_model.arm_points参照)ため、接触面積の代理指標として
    実長も乗じる(メガネのアームが長く沿うほど落ちにくいのと同じ発想)。
    arm_thicknessの寄与はplug.diameterで頭打ちにする(理由はモジュール
    docstring参照)。

    以前はframe.arm_length(yの区間幅)をそのまま使っていたが、これは
    clip_angleに依らず一定のため、実際にはclip_angleを大きくして鼻翼側へ
    開いてもretentionが一切増えず、GAがclip_angleを広げる理由がなかった
    (issue #1)。arm_points(x, y, z)の実際の3D経路長(x方向の広がりも含む)
    に置き換えることで、鼻翼側まで開くほど接触区間が実際に長くなる分を
    自然に反映するようにした。「起点自体の角度は挟み込む力を生まない」
    という判断(モジュールdocstring「retentionにclip_angleを直接の乗数として
    含めない理由」参照)は変えていない(依然としてclip_angleを直接の乗数には
    していない)。左右のアームはclip_angleによりxの符号が反転するだけで実長は
    等しいため、片側(呼び出し側が渡すarm_points)だけで十分。
    """
    effective_thickness = min(
        frame.arm_thickness, plug.diameter * _MAX_THICKNESS_TO_PLUG_DIAMETER
    )
    return frame.grip_depth * effective_thickness * _path_length(arm_points)


def _pain(frame: FrameParams) -> float:
    """痛み(快適さ、最小化)。retentionと表裏一体のgrip_depthそのもの。"""
    return frame.grip_depth


def _reach_gap(sides: list[SidePaths], targets: list[np.ndarray]) -> float:
    """到達性の制約チェック用の値(0であるべき)。

    connector_pointsの最終点がtarget(鼻栓の露出端)に届いていない距離
    (holder_offsetがdive_distにクランプされた場合の未到達量)。左右のうち
    より届いていない側(最大値)を返す。
    """
    return max(
        float(np.linalg.norm(target - path[-1]))
        for (_, path), target in zip(sides, targets)
    )


def _fit_gap(
    sides: list[SidePaths], body: trimesh.Trimesh, arm_thickness: float
) -> tuple[float, float]:
    """視覚的一体感。コネクタの表面沿い区間(非接触区間)の"円柱表面"から
    鼻本体表面までの距離の(平均, 最悪点)を返す。値が小さいほど顔に馴染んで
    見える。平均は目的(fit_gap)、最悪点は制約(fit_gap_max)として使う
    (FrameScore参照)。アーム(全区間がgrip_depthで意図的に鼻表面へ埋め込ま
    れる接触区間)は対象外(surface_following_pointsのdocstring参照)。

    表面沿い区間の点列(surface_points)はメッシュの中心線であり、実際に
    見える/触れるのは半径arm_thickness/2だけ太い円柱の表面。中心線からの
    距離をそのまま使うと、太いアームほど実際の見た目の隙間より過大な
    値になってしまう(frame_model.connector_pointsが中心線を
    arm_thickness/2の分だけ余分に浮かせているのと対になる補正)。
    curvature等により半径分を引いた値がわずかに負になりうるため0で
    クランプする。

    closest_point(rtreeによる空間索引を使う高速版)を使う。総当たりの
    closest_point_naiveより速く、結果は変わらない(frame_model.
    _signed_distance_to_bodyのdocstring参照)。
    """
    means, maxes = [], []
    for _, path in sides:
        surface_points = surface_following_points(path)
        _, distance, _ = trimesh.proximity.closest_point(body, surface_points)
        tube_distance = np.maximum(distance - arm_thickness / 2, 0.0)
        means.append(float(np.mean(tube_distance)))
        maxes.append(float(np.max(tube_distance)))
    return max(means), max(maxes)


def _smoothness(sides: list[SidePaths]) -> float:
    """経路全体の滑らかさ(制約)。経路上の連続する2区間がなす角度(度)の
    最悪値。0に近いほど直線的、180に近いほど鋭く折れ返っている。「急に
    折れ曲がる箇所がないか」という合否に近い性質のため、目的ではなく
    制約として扱う(FrameScore参照)。

    以前はコネクタの表面沿い区間からダイブ区間への遷移角(path末尾の1箇所)
    だけを見ていた(折れ線全体を見ると最適解が単純な直線に収束してしまう
    ことを懸念したため)。しかし実際にはアーム→コネクタの継ぎ目
    (points[-1]==path[0]の前後)がこの範囲外で最も急に折れ曲がっており
    (実測で約145度)、見逃していた(issue #2)。「基本的に滑らかに
    つながっていてほしい」という要望は経路全体に対するものであり、直線に
    寄っても悪化しない(smoothness=0が最良)ため、当初の懸念は却下し、
    アーム(points)とコネクタ(path)を1本の折れ線として結合した経路全体の
    各内部点を評価対象にする。

    points[-1]==path[0](arm_end)で連続しているため、frame_model.
    full_path_points(_proportion_penaltyの全長計算と共通)でアーム+コネクタ
    を1本の折れ線に結合する。

    holder_offset=0(バリデーション上は有効)でconnector_pointsの最終区間の
    長さが0になる場合や、_CONNECTOR_SAMPLESの分割・arm_end/targetのyが
    たまたま一致する等の縮退したジオメトリで、連続する2点が同じ座標になり
    区間ベクトルの長さが0になることがある。角度を定義できないため、その
    箇所は評価から除外する(0除算でNaNになることを避ける)。
    """
    angles = []
    for points, path in sides:
        full_path = full_path_points(points, path)
        for i in range(1, len(full_path) - 1):
            incoming = full_path[i] - full_path[i - 1]
            outgoing = full_path[i + 1] - full_path[i]
            incoming_norm = np.linalg.norm(incoming)
            outgoing_norm = np.linalg.norm(outgoing)
            if incoming_norm < 1e-9 or outgoing_norm < 1e-9:
                continue
            cos_angle = np.dot(incoming, outgoing) / (incoming_norm * outgoing_norm)
            angles.append(float(np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))))
    return max(angles) if angles else 0.0


def _proportion_penalty(
    sides: list[SidePaths], arm_thickness: float, max_thickness: float
) -> float:
    """プロポーションの破綻(制約)。下限は太さ/全長比が_MIN_THICKNESS_RATIOを
    下回った分(細すぎ)、上限はarm_thicknessがmax_thickness(plug.diameter
    基準の頭打ち値)を超えた分(太すぎ)を罰則にする(範囲内は0)。上限を
    plug.diameter基準にする理由はモジュールdocstring参照(retentionの
    頭打ちと同じ基準で、太さだけを稼ぐ抜け道を塞ぐ)。範囲内は0で、わざと
    少し破綻させたい理由がないため目的ではなく制約として扱う(FrameScore参照)。
    """
    penalties = []
    for points, path in sides:
        full_path = full_path_points(points, path)
        length = _path_length(full_path)
        ratio = arm_thickness / length
        too_thin = max(0.0, _MIN_THICKNESS_RATIO - ratio)
        too_thick = max(0.0, arm_thickness - max_thickness)
        penalties.append(too_thin + too_thick)
    return max(penalties)


@dataclass(frozen=True)
class FrameScore:
    """フレームの評価値(目的3つ+制約7つ。モジュールdocstring参照)。

    目的(retention/pain/fit_gap)はNSGA-IIが探索するトレードオフ。
    retentionのみ最大化、他は最小化。制約(reach_gap以下の7項目)は
    実行不可能個体を除外するための値で、いずれも0または一定値以下で
    あるべき(わざと悪化させて選ぶ理由がない)。実際の閾値判定は
    未実装で、生の値のまま返す(モジュールdocstring参照)。

    grip_depth_margin/arm_clearance_margin/grip_ring_marginは、
    frame_model.pyのvalidate_*(build_frame_pairが使う、例外を送出する版)
    と対になる制約値。frameの探索によって結果が変わる検証なので、
    evaluate_frameは例外で止めずこれらを制約として返す(モジュール
    docstring・frame_model.pyのモジュールdocstring参照)。
    """

    # 目的(3つ)
    retention: float  # 機能性(最大化)
    pain: float  # 快適さ(最小化)
    fit_gap: float  # 意匠性: 視覚的一体感・平均(最小化)
    # 制約(7つ。すべて0または一定値以下であるべき)
    reach_gap: float  # コネクタが鼻栓の露出端に届いているか(0であるべき)
    fit_gap_max: float  # 局所的な浮きの最悪点(閾値: _FIT_GAP_MAX_THRESHOLD)
    smoothness: float  # 経路の折れの急峻さ(閾値: _SMOOTHNESS_THRESHOLD_DEG)
    proportion_penalty: float  # 太さの破綻(0であるべき)
    grip_depth_margin: float  # 起点が鼻の厚みを超えていないか(0以下であるべき)
    arm_clearance_margin: float  # 表面沿い区間のめり込み量(0以下であるべき)
    grip_ring_margin: float  # 起点断面の側方への突き出し量(0以下であるべき)


# 制約の閾値。7項目のうち5項目(reach_gap/proportion_penalty/
# grip_depth_margin/arm_clearance_margin/grip_ring_margin)は0以下が
# 合格ラインになるよう既に設計されているため、constraint_values側で判断が
# 必要な実質的な閾値はfit_gap_max・smoothnessの2つだけ。いずれも仮置きで、
# NSGA-IIを実際に動かし、生成される候補フレームを見ながら見直す前提

# 0以下が合格ラインの制約に共通で使う、浮動小数点誤差を吸収するための
# ごく小さな余裕(mm、または比率)。境界ぎりぎりの計算結果が誤差でわずかに
# 正になっても誤って棄却しないようにする
_MARGIN_EPSILON = 1e-6

# fit_gap_maxの許容値(mm)。鼻栓自体の直径(plug.diameterの既定値6.0mm)を
# 「これ以上局所的に離れていたら明らかに顔から浮いて見える」の目安にする
# (フレームが挟んでいる相手=鼻栓より大きく浮くのは不自然、という考え方。
# retentionのarm_thickness頭打ちと同じ発想)。デフォルト設定の実測値
# (約3.19mm)はこの半分程度で収まる
_FIT_GAP_MAX_THRESHOLD = 6.0

# smoothnessの許容値(度)。180度(完全な折り返し)は明らかに破綻した形なので、
# その手前で「一続きの滑らかな形状」とみなせる範囲を120度とする(直角
# (90度)を超える曲がりもまだ意図的な形として許容し、それ以上を
# 「ジグザグ」とみなす)。デフォルト設定の実測値(約94度)はこの範囲に収まるが、
# 過去にパレート最適候補として出力されたclip_angle=5.74, arm_length=10.25等の
# 個体は約145度(アーム→コネクタの継ぎ目、issue #2)で明確に違反する。この
# 個体は今後の探索で除外される想定の値(GAを実際に動かし、生成される候補を
# 見ながら見直す前提の暫定値である点は他の閾値と同じ)
_SMOOTHNESS_THRESHOLD_DEG = 120.0


def constraint_values(score: FrameScore) -> tuple[float, ...]:
    """FrameScoreの7つの制約値を、NSGA-II(pymoo等)が使う規約(0以下=
    実行可能、正=違反量)に変換したタプルを返す。

    すでに0以下が合格ラインの5項目は_MARGIN_EPSILONを引くだけ(境界の
    誤差吸収)。fit_gap_max・smoothnessは実際の閾値を引く。
    """
    return (
        score.reach_gap - _MARGIN_EPSILON,
        score.fit_gap_max - _FIT_GAP_MAX_THRESHOLD,
        score.smoothness - _SMOOTHNESS_THRESHOLD_DEG,
        score.proportion_penalty - _MARGIN_EPSILON,
        score.grip_depth_margin - _MARGIN_EPSILON,
        score.arm_clearance_margin - _MARGIN_EPSILON,
        score.grip_ring_margin - _MARGIN_EPSILON,
    )


def evaluate_frame(
    frame: FrameParams, plug: PlugParams, params: NoseParams
) -> FrameScore:
    """FrameParams から機能性・快適さ・意匠性の評価値を計算する。

    frameに依存しない検証(validate_target_reach, validate_anchor_height。
    PlugParams/NoseParamsにしか依存せず、GAの探索中は結果が変わらない)は
    例外で即座に止める。frameに依存する検証(grip_depth_margin等)は
    例外で止めず、制約値としてFrameScoreに含める(frame_model.pyの
    モジュールdocstring参照)。
    """
    validate_target_reach(plug, params)
    validate_anchor_height(params)
    body = build_nose_body(params)
    sides: list[SidePaths] = [
        build_side_paths(frame, plug, params, side) for side in (-1, 1)
    ]

    targets = [
        plug_outer_end(plug, params.nostril_gap, params.tip_depth_front, side)
        for side in (-1, 1)
    ]
    max_thickness = plug.diameter * _MAX_THICKNESS_TO_PLUG_DIAMETER
    fit_gap, fit_gap_max = _fit_gap(sides, body, frame.arm_thickness)

    return FrameScore(
        retention=_retention(frame, plug, sides[0][0]),
        pain=_pain(frame),
        fit_gap=fit_gap,
        reach_gap=_reach_gap(sides, targets),
        fit_gap_max=fit_gap_max,
        smoothness=_smoothness(sides),
        proportion_penalty=_proportion_penalty(
            sides, frame.arm_thickness, max_thickness
        ),
        grip_depth_margin=grip_depth_margin(frame, params, sides),
        arm_clearance_margin=arm_clearance_margin(sides, body, frame.arm_thickness),
        grip_ring_margin=grip_ring_margin(frame, body, sides),
    )
