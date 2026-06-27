from cadquery import Workplane, Assembly, Sketch, Vector, Location
from cadquery.func import box
from cadquery.vis import vtkAxesActor, ctrlPts
from cadquery.fig import Figure, show, clear, fit, wait

from asyncio import run
from unittest.mock import AsyncMock, Mock

from pytest import fixture, mark, raises

from sys import platform


@fixture(scope="module")
def fig():
    return Figure()


@fixture(scope="module")
def showables():

    # showables
    s = box(1, 1, 1)
    wp = Workplane().box(1, 1, 1)
    assy = Assembly().add(box(1, 1, 1))
    sk = Sketch().rect(1, 1)
    ctrl_pts = ctrlPts(sk.val().toNURBS())
    v = Vector()
    loc = Location()
    act = vtkAxesActor()

    return (s, s.copy(), wp, assy, sk, ctrl_pts, v, loc, act)


def test_fig_wait():

    fig = object.__new__(Figure)
    server_future = Mock()
    fig._server_future = server_future
    shutdown_coro = object()
    fig._shutdown = Mock(return_value=shutdown_coro)
    shutdown_future = Mock()
    fig._run = Mock(return_value=shutdown_future)
    fig._stop_loop = Mock()

    assert fig.wait() is fig
    server_future.result.assert_called_once_with()
    fig._run.assert_called_once_with(shutdown_coro)
    shutdown_future.result.assert_called_once_with()
    fig._stop_loop.assert_called_once_with()
    assert fig._server_future is None


def test_fig_wait_stops_server_on_keyboard_interrupt():

    fig = object.__new__(Figure)
    fig._server_future = Mock()
    fig._server_future.result.side_effect = KeyboardInterrupt
    shutdown_coro = object()
    fig._shutdown = Mock(return_value=shutdown_coro)
    shutdown_future = Mock()
    fig._run = Mock(return_value=shutdown_future)
    fig._stop_loop = Mock()

    assert fig.wait() is fig
    fig._run.assert_called_once_with(shutdown_coro)
    shutdown_future.result.assert_called_once_with()
    fig._stop_loop.assert_called_once_with()


def test_fig_wait_cleans_up_on_server_error():

    fig = object.__new__(Figure)
    fig._server_future = Mock()
    fig._server_future.result.side_effect = RuntimeError("server failed")
    shutdown_coro = object()
    fig._shutdown = Mock(return_value=shutdown_coro)
    shutdown_future = Mock()
    fig._run = Mock(return_value=shutdown_future)
    fig._stop_loop = Mock()

    with raises(RuntimeError, match="server failed"):
        fig.wait()

    fig._run.assert_called_once_with(shutdown_coro)
    shutdown_future.result.assert_called_once_with()
    fig._stop_loop.assert_called_once_with()
    assert fig._server_future is None


def test_fig_shutdown_releases_vtk_resources():

    fig = object.__new__(Figure)
    fig.server = Mock()
    fig.server.stop = AsyncMock()
    fig.view = Mock()
    fig.win = Mock()

    run(fig._shutdown())

    fig.server.stop.assert_awaited_once_with()
    fig.view.release_resources.assert_called_once_with()
    fig.win.Finalize.assert_called_once_with()


def test_fig_stop_loop():

    fig = object.__new__(Figure)
    fig.loop = Mock()
    fig.thread = Mock()
    fig._closed = False

    fig._stop_loop()

    fig.loop.call_soon_threadsafe.assert_called_once_with(fig.loop.stop)
    fig.thread.join.assert_called_once_with()
    fig.loop.close.assert_called_once_with()
    assert fig._closed


def test_fig_run_rejects_closed_figure():

    fig = object.__new__(Figure)
    fig._closed = True

    async def noop():
        pass

    coro = noop()

    with raises(RuntimeError, match="Figure has been shut down"):
        fig._run(coro)

    assert coro.cr_frame is None


def test_fig_wait_free_func(monkeypatch):

    fig = Mock()
    monkeypatch.setattr(Figure, "_instance", fig)
    monkeypatch.setattr(Figure, "_initialized", True)

    wait()

    fig.wait.assert_called_once_with()


@mark.gui
@mark.skipif(platform != "win32", reason="CI with UI only works on win for now")
def test_fig(fig, showables):

    (s, s1, wp, assy, sk, ctrl_pts, v, loc, act) = showables

    # individual showables
    fig.show(*showables)

    # fit
    fig.fit()

    # views
    fig.iso()
    fig.up()
    fig.front()
    fig.side()

    # clear
    fig.clear()

    # clear with an arg
    for showable in showables:
        fig.show(showable)

    for el in (s, wp, assy, sk, ctrl_pts):
        fig.clear(el)

    # show multiple showables at once
    fig.clear()
    fig.show(*showables)

    # more than one Solid showable -> more than 2 actors
    assert len(list(fig.actors.values())[-1]) > 2

    # lists of showables
    fig.show(s.Edges()).show([Vector(), Vector(0, 1)])

    # displaying nonsense does not throw
    fig.show("a").show(["a", 1234])

    # pop
    for el in showables:
        fig.show(el, color="red")
        fig.pop()

    # test singleton behavior of fig
    fig2 = Figure()
    assert fig is fig2

    # test onSelection
    fig.onVisibility(fig.state.actors[0])

    # test onVisbility
    fig.onSelection([fig.state.actors[0]])


@mark.gui
@mark.skipif(platform != "win32", reason="CI with UI only works on win for now")
def test_fig_free_func(showables):

    clear()
    fig = Figure()
    assert len(fig.state.actors) == 0

    for el in showables:
        show(el)

    fit()

    assert len(fig.state.actors) == len(showables)
