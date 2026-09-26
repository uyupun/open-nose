"""インタラクティブビューア(trimeshのSceneViewer)向けの、設計に依らない補助。

半透明メッシュの描画順の並べ直し(order_for_viewer)と、カメラ位置の調整
(show_scene)を提供する。各設計のview_nose.pyから使う。
"""

import trimesh

# ビューアでの描画順を決める、ジオメトリ名の接頭辞の優先順位(先頭ほど
# 先に描く=内側の部品)。trimeshのビューアは半透明メッシュを登録順に、
# 深度書き込みを有効にしたまま描くため、外側の部品(鼻本体)を先に描くと
# その奥にある部品(鼻孔の中を通るフレーム等)は深度テストで描画自体が
# スキップされ、alphaをいくら下げても見えない(実機で確認)。内側→外側の
# 順に描けば、後から描かれる皮膚・鼻栓が手前でブレンドされ、透けて見える。
# 各設計のscene.pyはこの順で登録するが、glTF(.glb)から読み戻すとtrimeshの
# ローダーがノード順を保持しない(実測: body, plug_*, frame_*の順に戻る)
# ため、読み込んだシーンはorder_for_viewerで並べ直す必要がある
DRAW_ORDER_PREFIXES = ("frame", "plug", "body")

# カメラを既定位置より少し下にずらす(上側の余白を減らすため)量を、シーンの
# y方向の大きさに対する比率で指定する。以前は固定値(-8.0mm。鼻全体、
# y方向約59mmに合わせた値)だったが、フレーム単体のSTL(約8.5mm)のように
# 小さいシーンでは対象がほぼ画面外に出てしまった(実機で確認)ため、
# 大きさに比例させる(鼻全体では従来と同じ約-8mmになる)
CAMERA_Y_OFFSET_RATIO = -8.0 / 59.0


def order_for_viewer(scene: trimesh.Scene) -> trimesh.Scene:
    """sceneのジオメトリをDRAW_ORDER_PREFIXESの優先順位(内側→外側)で
    登録し直した新しいSceneを返す。

    どの接頭辞にも当てはまらない名前(任意のOBJ/STL/glTF等)は最後に、元の
    順序のまま並べる(安定ソート)。各ノードの変換行列はそのまま引き継ぐ。
    """

    def priority(geom_name: str) -> int:
        for i, prefix in enumerate(DRAW_ORDER_PREFIXES):
            if geom_name.startswith(prefix):
                return i
        return len(DRAW_ORDER_PREFIXES)

    entries = []
    for node in scene.graph.nodes_geometry:
        transform, geom_name = scene.graph.get(node)
        entries.append((priority(geom_name), node, geom_name, transform))
    entries.sort(key=lambda e: e[0])

    ordered = trimesh.Scene()
    for _, node, geom_name, transform in entries:
        ordered.add_geometry(
            scene.geometry[geom_name],
            node_name=node,
            geom_name=geom_name,
            transform=transform,
        )
    return ordered


def load_for_viewer(path) -> trimesh.Scene:
    """ファイル(OBJ/STL/glTF等)をビューア表示用のSceneとして読み込む。

    force="scene": 単一ジオメトリのファイルでもSceneとして読み込む
    (Trimeshにはcamera_transformがなく、show_sceneのカメラ調整が使えない
    ため)。読み込み後にorder_for_viewerで描画順を並べ直す。
    """
    return order_for_viewer(trimesh.load(path, force="scene"))


# ビューアのウィンドウを画面のどれだけの大きさで開くか(短い方の辺に対する
# 比率)。trimeshの既定は1800x1350pxで、これは実際の画面(実測1512x982px)
# より大きく、はみ出した状態で開いてしまう
WINDOW_SCREEN_RATIO = 0.8
# ウィンドウの大きさ(px)。画面の大きさが取れなかったときに使う
FALLBACK_RESOLUTION = (1000, 800)


def _window_resolution() -> tuple[int, int]:
    """画面に収まるウィンドウの大きさ(px)を返す。"""
    try:
        import pyglet

        screen = pyglet.canvas.get_display().get_default_screen()
        side = int(min(screen.width, screen.height) * WINDOW_SCREEN_RATIO)
        return (int(side * 4 / 3), side)
    except Exception:
        return FALLBACK_RESOLUTION


def _viewer_class():
    """マウスのドラッグで確実に回転するSceneViewerのサブクラスを返す。

    trimeshのビューアは、押した瞬間(on_mouse_press)にトラックボールの起点を
    登録し、ドラッグ中はその起点からの差分で回転させる。起点が登録されて
    いないと、trimesh.viewer.trackball.Tragball.dragは差分を0として扱い、
    ドラッグが完全に無効になる(trimesh側のコメントにも「down eventが何らかの
    理由で発火しなかった場合はno-opにする」とある)。実機(macOS 26 +
    pyglet 1.5.31)では実際にこの状態で、ホイールのズーム(押下を必要と
    しない)だけが効き、上下左右の回転がまったくできなかった。

    pygletはドラッグのイベントで移動量(dx, dy)も渡してくれるので、
    1回のドラッグを「直前の位置から今の位置への小さなドラッグ」として
    その場で組み立て直す。押下イベントが届くかどうかに依存しなくなる。
    """
    import numpy as np
    import pyglet
    from trimesh.viewer.trackball import Trackball
    from trimesh.viewer.windowed import SceneViewer

    class DragFixSceneViewer(SceneViewer):
        def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
            ball = self.view["ball"]
            ball.set_state(Trackball.STATE_ROTATE)
            if buttons == pyglet.window.mouse.LEFT:
                ctrl = modifiers & pyglet.window.key.MOD_CTRL
                shift = modifiers & pyglet.window.key.MOD_SHIFT
                if ctrl and shift:
                    ball.set_state(Trackball.STATE_ZOOM)
                elif shift:
                    ball.set_state(Trackball.STATE_ROLL)
                elif ctrl:
                    ball.set_state(Trackball.STATE_PAN)
            elif buttons == pyglet.window.mouse.MIDDLE:
                ball.set_state(Trackball.STATE_PAN)
            elif buttons == pyglet.window.mouse.RIGHT:
                ball.set_state(Trackball.STATE_ZOOM)
            ball.down(np.array([x - dx, y - dy]))
            ball.drag(np.array([x, y]))
            self.scene.camera_transform = ball.pose

    return DragFixSceneViewer


def show_scene(scene: trimesh.Scene) -> None:
    """カメラ位置とウィンドウの大きさを調整してインタラクティブビューアを開く。

    操作: ドラッグで回転 / ホイールでズーム / ctrl+ドラッグで平行移動 /
    shift+ドラッグでロール。キーは z=視点リセット、w=ワイヤーフレーム、
    a=座標軸、g=グリッド、f=フルスクリーン、q=終了。
    """
    camera_transform = scene.camera_transform.copy()
    camera_transform[1, 3] += CAMERA_Y_OFFSET_RATIO * scene.extents[1]
    scene.camera_transform = camera_transform
    resolution = _window_resolution()
    scene.camera.resolution = resolution
    _viewer_class()(scene, resolution=resolution)
