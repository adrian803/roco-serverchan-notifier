from __future__ import annotations

import os
from contextlib import asynccontextmanager
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import quote

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import web_auth, web_services
from .config_store import ConfigStore
from .provider_specs import public_provider_types
from .scheduler import SchedulerService


SESSION_COOKIE_NAME = web_auth.SESSION_COOKIE_NAME
PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "static"
TEMPLATE_DIR = PACKAGE_DIR / "templates"
store = ConfigStore()
scheduler = SchedulerService(store)
static_files = StaticFiles(directory=str(STATIC_DIR))


async def static_asset(path: str, request: Request):
    return await static_files.get_response(path, request.scope)


def _request_store(request: Request | None = None) -> ConfigStore:
    if request is not None:
        app = getattr(request, "app", None)
        if app is not None and hasattr(app.state, "store"):
            return app.state.store
    return store


def _request_scheduler(request: Request | None = None) -> SchedulerService:
    if request is not None:
        app = getattr(request, "app", None)
        if app is not None and hasattr(app.state, "scheduler"):
            return app.state.scheduler
    return scheduler


def _require_auth(request: Request) -> None:
    if not web_auth.is_authenticated(_request_store(request), request):
        raise HTTPException(status_code=401, detail="请先登录控制台")


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse | RedirectResponse:
    if exc.status_code == 401 and not request.url.path.startswith("/api/"):
        next_path = request.url.path
        if request.url.query:
            next_path = f"{next_path}?{request.url.query}"
        return RedirectResponse(f"/login?next={quote(next_path, safe='/?:=&')}", status_code=303)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)


async def login_page(request: Request):
    request_store = _request_store(request)
    if not web_auth.auth_enabled(request_store) or web_auth.is_authenticated(request_store, request):
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(render_login_html())


async def api_login(request: Request) -> JSONResponse:
    request_store = _request_store(request)
    if not web_auth.auth_enabled(request_store):
        if web_auth.allow_empty_password():
            return JSONResponse({"ok": True, "message": "未启用控制台认证"})

    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="登录参数格式错误") from exc

    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    if not web_auth.credentials_are_valid(request_store, username, password):
        raise HTTPException(status_code=401, detail="用户名或密码不正确")

    response = JSONResponse({"ok": True, "message": "登录成功"})
    response.set_cookie(
        SESSION_COOKIE_NAME,
        web_auth.make_session_cookie(request_store, username),
        max_age=web_auth.session_ttl(),
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )
    return response


async def api_logout() -> JSONResponse:
    response = JSONResponse({"ok": True, "message": "已退出登录"})
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


async def index() -> str:
    return render_index_html()


async def api_provider_types() -> dict[str, Any]:
    return {"provider_types": public_provider_types()}


async def api_state(request: Request) -> dict[str, Any]:
    return web_services.build_state_payload(_request_store(request), _request_scheduler(request))


async def api_save_config(request: Request) -> JSONResponse:
    payload = await request.json()
    try:
        settings = web_services.save_config_payload(_request_store(request), _request_scheduler(request), payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"配置保存失败: {exc}") from exc
    return JSONResponse({"ok": True, "config": settings.public_dict()})


async def api_run_now(request: Request) -> JSONResponse:
    started = await _request_scheduler(request).run_now()
    if not started:
        return JSONResponse({"ok": False, "message": "已有任务正在执行"})
    return JSONResponse({"ok": True, "message": "已开始执行"})


async def api_test_push(request: Request) -> JSONResponse:
    payload = await request.json()
    try:
        return JSONResponse(await web_services.send_test_push(_request_store(request), payload))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def create_app(
    store: ConfigStore | None = None,
    scheduler: SchedulerService | None = None,
) -> FastAPI:
    app_store = store or globals()["store"]
    app_scheduler = scheduler or SchedulerService(app_store)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        web_auth.log_console_password_once(app_store)
        app_scheduler.start()
        try:
            yield
        finally:
            await app_scheduler.stop()

    app = FastAPI(title="Roco Push Console", lifespan=lifespan)
    app.state.store = app_store
    app.state.scheduler = app_scheduler
    app.add_api_route("/static/{path:path}", static_asset, include_in_schema=False, methods=["GET"])
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_api_route("/login", login_page, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/api/login", api_login, methods=["POST"])
    app.add_api_route("/api/logout", api_logout, methods=["POST"])
    app.add_api_route("/", index, methods=["GET"], response_class=HTMLResponse, dependencies=[Depends(_require_auth)])
    app.add_api_route("/api/provider-types", api_provider_types, methods=["GET"], dependencies=[Depends(_require_auth)])
    app.add_api_route("/api/state", api_state, methods=["GET"], dependencies=[Depends(_require_auth)])
    app.add_api_route("/api/config", api_save_config, methods=["POST"], dependencies=[Depends(_require_auth)])
    app.add_api_route("/api/run-now", api_run_now, methods=["POST"], dependencies=[Depends(_require_auth)])
    app.add_api_route("/api/test-push", api_test_push, methods=["POST"], dependencies=[Depends(_require_auth)])
    return app


app = create_app()


def cli() -> None:
    host = os.environ.get("WEB_HOST", "0.0.0.0")
    try:
        port = int(os.environ.get("WEB_PORT", "19892"))
    except ValueError:
        port = 19892
    uvicorn.run("roco_serverchan_notifier.web:app", host=host, port=port)


def _read_template(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


def render_login_html() -> str:
    username = escape(web_auth.auth_username(), quote=True)
    return _read_template("login.html").replace("__USERNAME__", username)


def render_index_html() -> str:
    return _read_template("index.html")


if __name__ == "__main__":
    cli()
