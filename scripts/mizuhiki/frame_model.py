"""水引型: 丸めたティッシュ(鼻栓)に着けて、小鼻に水引の結びを添える器具。

## 経緯

鼻栓を「隠すもの」から「装うもの」に変える(恥を、礼に変える)ために、
丸めたティッシュに着ける小さな器具を、ティッシュを受ける器・C字・二枚貝・
線の形・結び以外の10案・横顔で見せる7案と作り比べ、ユーザーが水引を選んだ。
決め手は次の2つ(ユーザーの言葉)。

- 鼻の下だけの輪(キャップ)は人の目に留まりにくく、世間の目は変わらない。
  小鼻(尾翼)に沿い、横顔や斜めから見て美しいものがいい
- 水引は慶事の贈り物を飾る結びで、性別を問わず使われている

## 形

3本の紐(直径0.9mm)を平らに並べた帯が、ティッシュのまわりを1周して輪に
なり(スカーフリングのように、ティッシュを輪に通して留める)、小鼻の外側を
上がって、あわじ結びに見立てた三つ輪の結びになる。結びの下からは端が
垂れる。帯は1本の紐を2回巻いた形から始めたが、らせんがばねに見えたので
3本を並べた帯にした。

- 輪の内径は9.0mm(ユーザー指摘「穴が小さい」で7.8mmから広げた)
- 輪・帯・結びは鼻の肌から_SKIN_GAP(0.3mm)離す
- 左右は同じ形(-x側は+x側の鏡映)

## FDM(0.4mmノズル)で刷るための補強

並べた紐は重なりがわずかで、紐と紐のつなぎ目の厚みが0.3mm前後しかなく、
輪を下にして刷るとつなぎ目の高さの層が線1本分にも満たなかった。そこで
紐の肌の側(輪では内側)を、紐の中心から_WEB_TOPの高さまでの板でつなぐ
(外から見える紐の溝の深さは変えない)。また輪の底は丸い紐で、ベッドに
着く面が細い環しかなかったので、底を_FLATだけ平らに削る。刷る向きは、
輪の底面をベッドに置き、着けたときの上を上にする向き(print_orientation)。
6方向を比べて、この向きがサポートの要る面が最も少なかった。

## 座標

鼻モデルと同じ(x=左右、y=鼻先(0)→鼻筋、z=前後(前面が+))。小鼻の外側の
面は、鼻の断面(角丸三角形)の背面側の角の丸みで、_back_arc_pointの比率f
で位置を指定する(0=顔との境目(z=-2.2付近)、1=側面のまっすぐな辺の
始まり)。
"""

from dataclasses import dataclass

import numpy as np
import trimesh
from manifold3d import Manifold, Mesh, OpType
from scipy.interpolate import splev, splprep

from commons.nose_model import (
    NoseParams,
    build_nose_body,
    nostril_depth_z,
    surface_profile_at,
    tip_cap_min_y,
)
from commons.plug_model import PlugParams
from commons.rounded_triangle import POINTS_PER_CORNER, rounded_triangle_ring

# ティッシュを通す輪の内半径(mm)
GRIP_RADIUS = 4.5
# 輪・帯・結びと鼻の肌のすき間(mm)
SKIN_GAP = 0.3
# 帯に並べる紐の本数
STRANDS = 3
# 隣り合う紐の中心の間隔(紐の直径に対する比)。1未満にして少し重ね、
# 並べた紐が一体の帯になるようにする
_STRAND_SPACING = 0.9
# 紐の肌の側をつなぐ板の上端(紐の中心からの高さ、mm)
_WEB_TOP = 0.2
# 輪の底を平らに削る深さ(mm)
_FLAT = 0.2
# 結びの端が垂れる向き(結びの面の横・上の成分)
_TAIL_DIRECTION = (0.5, -1.0)
# 鼻栓の外側の端の上端と鼻の底面のすき間、鼻の中に入っている長さ(mm)
_PLUG_TOP_GAP = 0.2
_PLUG_INSIDE = 8.8
# 器具の色(黒に近い灰色)
_COLOR = [52, 52, 60, 255]


@dataclass(frozen=True)
class MizuhikiParams:
    """水引型の設計変数(mm)。optimize._SEARCH_SPACEが探索する。

    - knot_scale: 三つ輪の結びの大きさ(三つ葉の曲線の倍率。1.7で結びの
      差し渡しが約10mm)
    - knot_y: 結びの中心の高さ(鼻先の底面の少し上が-3付近、小鼻の上端が
      7.5付近)
    - knot_f: 結びの中心の、小鼻の外側の面の上の位置(0=顔との境目、
      1=鼻の側面のまっすぐな辺の始まり)
    - cord_radius: 紐の半径。帯の幅・輪の高さ・目立ち方が決まる
    - tail_length: 結びの下から垂れる端の長さ
    """

    knot_scale: float = 1.7
    knot_y: float = 2.8
    knot_f: float = 0.6
    cord_radius: float = 0.45
    tail_length: float = 2.5

    def __post_init__(self) -> None:
        for name in ("knot_scale", "cord_radius", "tail_length"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name}は正の値である必要があります: {getattr(self, name)}")
        if not 0.0 <= self.knot_f <= 1.0:
            raise ValueError(f"knot_fは0〜1である必要があります: {self.knot_f}")


@dataclass(frozen=True)
class MizuhikiPaths:
    """器具(+x側)の紐の中心線。形状(build_manifold)と評価(evaluation)の
    両方が使う。"""

    path: np.ndarray  # 帯の中心線(輪→渡り→結び→端)
    band: np.ndarray  # 紐を並べる向き(単位ベクトル)
    reference: np.ndarray  # 帯の面の法線(輪では外向き、ほかでは肌の法線)
    strands: tuple[np.ndarray, ...]  # 紐ごとの中心線
    ring: slice  # pathのうち輪の区間
    entry: slice  # 輪から結びへ上がる区間
    knot: slice  # 結びの区間
    tail: slice  # 端の区間
    y_ring: float  # 輪(帯の中心)の高さ
    band_half: float  # 両端の紐の中心の間隔の半分
    knot_on_skin: float  # 結び・端のうち、肌に沿わせられた点の割合


# ---- 鼻の形 ----


def _back_arc_point(params: NoseParams, y: float, f: float) -> np.ndarray:
    """高さyの断面の、+x側の背面側の角の丸み(小鼻の外側の面)の上で、
    比率f(0=顔との境目、1=側面のまっすぐな辺の始まり)の点(x, y, z)。"""
    half_width, depth_back, depth_front = surface_profile_at(params, y)
    ring = rounded_triangle_ring(half_width, depth_back, depth_front)
    arc = ring[-2 * POINTS_PER_CORNER : -POINTS_PER_CORNER]
    step = np.linalg.norm(np.diff(arc, axis=0), axis=1)
    length = np.concatenate([[0.0], np.cumsum(step)])
    target = f * length[-1]
    return np.array([np.interp(target, length, arc[:, 0]), y, np.interp(target, length, arc[:, 1])])


def surface_frame(body: trimesh.Trimesh, points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """各点にいちばん近い鼻の表面の点と、そこでの外向きの法線。"""
    closest, _, triangle = trimesh.proximity.closest_point(body, points)
    return closest, body.face_normals[triangle]


def _keep_off(body: trimesh.Trimesh, points: np.ndarray, distance: float) -> np.ndarray:
    """鼻の表面からdistanceより近い点を、法線の向きへdistanceまで押し出す。"""
    points = points.copy()
    for _ in range(3):
        closest, normals = surface_frame(body, points)
        signed = np.einsum("ij,ij->i", points - closest, normals)
        near = signed < distance
        points[near] = closest[near] + normals[near] * distance
    return points


def _drape(
    body: trimesh.Trimesh, points: np.ndarray, direction: np.ndarray, distance: float
) -> tuple[np.ndarray, np.ndarray]:
    """平らな図形の点を、共通の向きdirection(肌から外向き)に沿って動かし、
    鼻の表面からdistanceの位置へ寄せる(布を掛けるように、曲面に沿わせる)。
    戻り値は(寄せた点、肌に当たった点か)。

    各点をいちばん近い表面の点へ寄せると、粗いメッシュの角の近くで多くの点が
    同じ頂点に寄って重なった(経路の向きが決まらなくなる)。平行な光線で
    表面に当てれば、点の並びは崩れない。
    """
    direction = direction / np.linalg.norm(direction)
    origins = points + direction * 20.0
    hits, rays, _ = body.ray.intersects_location(
        origins, np.tile(-direction, (len(points), 1)), multiple_hits=False
    )
    result = points.copy()
    on_skin = np.zeros(len(points), dtype=bool)
    # 1本も当たらない(図形がまるごと小鼻の外にある)と、hitsが(0,)の形で返る
    if len(rays):
        result[rays] = hits + direction * distance
        on_skin[rays] = True
    return result, on_skin


def _smooth_curve(points: np.ndarray, count: int, smoothing: float) -> np.ndarray:
    """点列をなめらかな曲線(スプライン)で近似し、弧長でほぼ等間隔にcount点取り直す。"""
    keep = np.concatenate([[True], np.linalg.norm(np.diff(points, axis=0), axis=1) > 1e-6])
    points = points[keep]
    tck, _ = splprep(points.T, s=smoothing, k=3)
    fine = np.array(splev(np.linspace(0, 1, count * 8), tck)).T
    arc = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(fine, axis=0), axis=1))])
    targets = np.linspace(0, arc[-1], count)
    return np.stack([np.interp(targets, arc, fine[:, k]) for k in range(3)], axis=1)


def nostril_center(params: NoseParams) -> np.ndarray:
    """+x側の鼻の穴の中心(x, z)。"""
    return np.array([params.nostril_gap / 2, nostril_depth_z(params.tip_depth_front)])


def ring_top(params: NoseParams) -> float:
    """輪の上端のy(鼻の底面からSKIN_GAPだけ下)。"""
    return tip_cap_min_y(params) - SKIN_GAP


def band_height(frame: MizuhikiParams) -> float:
    """帯(並べた紐)の高さ(底を削る前)。"""
    return 2 * frame.cord_radius * (1 + _STRAND_SPACING * (STRANDS - 1))


def ring_height(frame: MizuhikiParams) -> float:
    """輪の高さ(底を平らに削った後)。ティッシュをつかむ長さ。"""
    return band_height(frame) - _FLAT


def grip_bottom(frame: MizuhikiParams, params: NoseParams) -> float:
    """輪の下端のy(鼻栓の外側の端をここにそろえる)。"""
    return ring_top(params) - ring_height(frame)


def neck_thickness(frame: MizuhikiParams) -> float:
    """隣り合う紐のつなぎ目の、帯の面に垂直な厚み(肌の側の板を含む)。
    2つの円が交わる高さは中心から√(r²-(間隔/2)²)。板はそこより上まで
    埋めるので、厚みは紐の肌の側の縁から、板の上端と交わる高さの高い方まで。"""
    r = frame.cord_radius
    crossing = np.sqrt(max(r * r - (r * _STRAND_SPACING) ** 2, 0.0))
    return r + max(_WEB_TOP, crossing)


def bed_contact_width(frame: MizuhikiParams) -> float:
    """刷る向きで、輪の底(いちばん下の紐を_FLATだけ削った面)の幅。"""
    r = frame.cord_radius
    return 2 * np.sqrt(r * r - (r - _FLAT) ** 2)


# ---- 紐の中心線 ----


def _trefoil(scale: float) -> np.ndarray:
    """あわじ結びに見立てた三つ輪(三つ葉の結び目の投影)の2次元の閉じた曲線。
    上に1つ、左下・右下に1つずつの輪。右下の輪のいちばん下から始まる。"""
    t = np.linspace(0, 2 * np.pi, 400)
    x = -(np.sin(t) + 2 * np.sin(2 * t))
    y = -(np.cos(t) - 2 * np.cos(2 * t))
    right = x > 0.5
    start = np.flatnonzero(right)[np.argmin(y[right])]
    order = np.roll(np.arange(len(t) - 1), -start)
    curve = np.stack([x[order], y[order]], axis=1)
    return np.vstack([curve, curve[:1]]) * scale


def build_paths(frame: MizuhikiParams, params: NoseParams, body: trimesh.Trimesh) -> MizuhikiPaths:
    """帯(STRANDS本の紐を平らに並べる)がティッシュを1周し、小鼻の外側を
    上がって三つ輪の結びになり、端が垂れて終わる、紐の中心線。"""
    center, y_top = nostril_center(params), ring_top(params)
    r = frame.cord_radius
    gap = 2 * r * _STRAND_SPACING
    band_half = gap * (STRANDS - 1) / 2
    # ティッシュに1周巻く輪(帯の中心の高さ)。外側(+x)から始まって外側に戻る
    y_ring = y_top - r - band_half
    ring_radius = GRIP_RADIUS + r
    angles = np.linspace(0, 2 * np.pi, 72)
    ring = np.stack(
        [
            center[0] + ring_radius * np.cos(angles),
            np.full(len(angles), y_ring),
            center[1] + ring_radius * np.sin(angles),
        ],
        axis=1,
    )
    # 結び: 小鼻の外側の面の接平面に描き、平行な光線で肌に沿わせる
    knot_center = _back_arc_point(params, frame.knot_y, frame.knot_f)
    closest, normal = surface_frame(body, knot_center[None, :])
    normal = normal[0]
    up = np.array([0.0, 1.0, 0.0]) - normal[1] * normal
    up /= np.linalg.norm(up)
    side = np.cross(up, normal)
    anchor = closest[0] + normal * (SKIN_GAP + r)
    curve = _trefoil(frame.knot_scale)
    knot = anchor + np.outer(curve[:, 0], side) + np.outer(curve[:, 1], up)
    knot, knot_hit = _drape(body, knot, normal, SKIN_GAP + r)
    # 輪から結びへ上がる帯(結びの最初の点へ下から入る)と、結びから垂れる端
    entry = _smooth_curve(
        np.vstack([ring[-1], ring[-1] + np.array([1.6, 0.4, -0.4]), knot[0] - up * 1.6 + side * 0.9, knot[0]]),
        24,
        smoothing=0.0,
    )
    entry = _keep_off(body, entry, SKIN_GAP + r + band_half)
    direction = side * _TAIL_DIRECTION[0] + up * _TAIL_DIRECTION[1]
    direction /= np.linalg.norm(direction)
    tail = np.array([knot[-1] + direction * t for t in np.linspace(0, frame.tail_length, 12)])
    tail, tail_hit = _drape(body, tail, normal, SKIN_GAP + r)
    path = np.vstack([ring, entry[1:], knot[1:], tail[1:]])
    n_ring, n_entry, n_knot = len(ring), len(entry) - 1, len(knot) - 1
    # 帯の向き: 紐を並べる向きは、経路の接線と「基準の法線」の外積。輪では
    # 基準の法線を輪の外向きにして紐を上下に並べ、それ以外では肌の法線に
    # して、紐を肌に沿って並べる(帯が肌に寝る)
    reference = np.empty_like(path)
    radial = path[:n_ring, [0, 2]] - center
    reference[:n_ring] = np.column_stack([radial[:, 0], np.zeros(n_ring), radial[:, 1]])
    _, reference[n_ring:] = surface_frame(body, path[n_ring:])
    reference /= np.linalg.norm(reference, axis=1, keepdims=True)
    for _ in range(6):
        reference[1:-1] = (reference[:-2] + 2 * reference[1:-1] + reference[2:]) / 4
    reference /= np.linalg.norm(reference, axis=1, keepdims=True)
    tangent = np.gradient(path, axis=0)
    band = np.cross(tangent, reference)
    norms = np.linalg.norm(band, axis=1)
    if not np.all(norms > 1e-9):
        bad = np.flatnonzero(~(norms > 1e-9))
        raise RuntimeError(f"帯の向きが決まらない点: {bad[:10]} / {len(path)}")
    band /= norms[:, None]
    # 輪の部分は、上下の向きをそろえる(外積の向きが輪の途中で反転しないように)
    band[:n_ring] *= np.sign(band[:n_ring, 1:2] + 1e-9)
    # 帯を肌に沿わせて並べると、曲がるところで肌の側の紐が肌に近づくので、
    # 紐ごとに肌から離す
    strands = tuple(
        _keep_off(body, path + band * ((k - (STRANDS - 1) / 2) * gap), SKIN_GAP + r) for k in range(STRANDS)
    )
    on_skin = np.concatenate([knot_hit[1:], tail_hit[1:]])
    return MizuhikiPaths(
        path=path,
        band=band,
        reference=reference,
        strands=strands,
        ring=slice(0, n_ring),
        entry=slice(n_ring, n_ring + n_entry),
        knot=slice(n_ring + n_entry, n_ring + n_entry + n_knot),
        tail=slice(n_ring + n_entry + n_knot, len(path)),
        y_ring=y_ring,
        band_half=band_half,
        knot_on_skin=float(on_skin.mean()),
    )


# ---- 立体 ----


def _cord(points: np.ndarray, radius: float) -> Manifold:
    """経路に沿った丸い紐(隣り合う2点の球の凸包をつなぐ。交差してもよい)。"""
    sphere = Manifold.sphere(radius, 16)
    pieces = [
        Manifold.batch_hull([sphere.translate(tuple(a)), sphere.translate(tuple(b))])
        for a, b in zip(points[:-1], points[1:])
    ]
    return Manifold.batch_boolean(pieces, OpType.Add)


def build_manifold(frame: MizuhikiParams, paths: MizuhikiPaths, body: trimesh.Trimesh) -> Manifold:
    """+x側の器具の立体(紐・紐をつなぐ板、輪の底を平らに削る)。"""
    r = frame.cord_radius
    pieces = [_cord(strand, r) for strand in paths.strands]
    # 紐と紐のあいだ: 両端の紐の中心のあいだを、紐の肌の側の縁から_WEB_TOP
    # までの板で埋める(隣り合う断面の凸包をつなぐ。帯は結びで交差するので、
    # 1枚の帯の面にはしない)
    corners = [
        _keep_off(body, paths.path + paths.band * (sign * paths.band_half) + paths.reference * height, SKIN_GAP)
        for sign in (-1.0, 1.0)
        for height in (-r, _WEB_TOP)
    ]
    sections = np.stack(corners, axis=1)
    pieces += [Manifold.hull_points(np.vstack([a, b])) for a, b in zip(sections[:-1], sections[1:])]
    solid = Manifold.batch_boolean(pieces, OpType.Add)
    solid = solid.trim_by_plane((0.0, 1.0, 0.0), paths.y_ring - paths.band_half - r + _FLAT)
    parts = [part for part in solid.decompose() if abs(part.volume()) > 0.01]
    return parts[0] if len(parts) == 1 else Manifold.batch_boolean(parts, OpType.Add)


def _to_trimesh(manifold: Manifold) -> trimesh.Trimesh:
    """Manifoldを、STLに書き出して読み直しても閉じた立体のままのtrimeshにする。

    STLの読み手は座標で頂点を統合するので、ここでも統合しておき、そのとき
    2頂点が重なって潰れた三角形を取り除く(dilator.frame_model.
    _clean_boolean_resultと同じ処理)。統合で逆に閉じなくなるときは統合前の
    形を返す。
    """
    mesh = manifold.to_mesh()
    mesh.merge()
    raw = trimesh.Trimesh(vertices=mesh.vert_properties[:, :3], faces=mesh.tri_verts, process=False)
    result = raw.copy()
    result.merge_vertices()
    faces = result.faces
    collapsed = (faces[:, 0] == faces[:, 1]) | (faces[:, 1] == faces[:, 2]) | (faces[:, 0] == faces[:, 2])
    result.update_faces(~collapsed)
    result.remove_unreferenced_vertices()
    return result if result.is_watertight or not raw.is_watertight else raw


def build_piece(
    frame: MizuhikiParams, params: NoseParams, side: int, body: trimesh.Trimesh | None = None
) -> trimesh.Trimesh:
    """左右いずれかの器具を、鼻に着けた位置で構築する(着色済み)。"""
    body = body if body is not None else build_nose_body(params)
    solid = build_manifold(frame, build_paths(frame, params, body), body)
    if side == -1:
        solid = solid.mirror((1.0, 0.0, 0.0))
    mesh = _to_trimesh(solid)
    mesh.visual.face_colors = _COLOR
    return mesh


def print_orientation(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """鼻に着けた向きの器具を、刷る向きに置き直す: 着けたときの上(+y)を+Zに
    して(x軸まわりに+90度)、いちばん下(輪の底面)をZ=0、XYの中心を原点に
    置く。"""
    upright = mesh.copy()
    upright.apply_transform(np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]]))
    low, high = upright.bounds
    upright.apply_translation([-(low[0] + high[0]) / 2, -(low[1] + high[1]) / 2, -low[2]])
    return upright


def plug_params(frame: MizuhikiParams, params: NoseParams) -> PlugParams:
    """輪に通した鼻栓(丸めたティッシュ)の位置・寸法。

    太さは輪の内径に合わせ(丸めたティッシュは押し縮められるので、鼻の穴の
    中でも輪の中でもこの太さに収まる想定)、外側の端を輪の下端にそろえる。
    鼻の中に入っている長さは_PLUG_INSIDEに固定する。
    """
    top = tip_cap_min_y(params) - _PLUG_TOP_GAP
    outer_end = grip_bottom(frame, params)
    length = (top + _PLUG_INSIDE) - outer_end
    return PlugParams(diameter=2 * GRIP_RADIUS, length=length, y_offset=outer_end + length / 2)
