"""Sign up, sign in, sign out (FR-23, FR-24) and the two pages for them.

Wrong email and wrong password get the same message, so the sign-in form never tells
whether an email has an account.
"""

from pathlib import Path

from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row

from app import auth, db
from app.errors import ApiError
from app.schemas import ErrorOut, LoginIn, RegisterIn, UserOut

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")

USER_BY_EMAIL_SQL = "SELECT id, email, display_name, password_hash FROM users WHERE email = %(email)s"

INSERT_USER_SQL = """
INSERT INTO users (email, display_name, password_hash)
VALUES (%(email)s, %(display_name)s, %(password_hash)s)
RETURNING id, email, display_name
"""

DELETE_SESSION_SQL = "DELETE FROM sessions WHERE token_hash = %(token_hash)s"

WRONG_LOGIN = ApiError(401, "WRONG_LOGIN", "Email hoặc mật khẩu không đúng.")
TOO_MANY = ApiError(429, "TOO_MANY_ATTEMPTS", "Bạn nhập sai quá nhiều lần. Hãy thử lại sau 15 phút.")
EMAIL_TAKEN = ApiError(409, "EMAIL_TAKEN", "Email này đã có tài khoản. Hãy đăng nhập.")


def signed_in(user: dict, token: str, status_code: int = 200) -> Response:
    response = Response(UserOut(**user).model_dump_json(), status_code=status_code, media_type="application/json")
    auth.set_session_cookie(response, token)
    return response


@router.post("/api/auth/register", response_model=UserOut, status_code=201, responses={409: {"model": ErrorOut}})
def register(body: RegisterIn):
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        params = {"email": body.email, "display_name": body.display_name, "password_hash": auth.hash_password(body.password)}
        try:
            user = cur.execute(INSERT_USER_SQL, params).fetchone()
        except UniqueViolation as err:  # users.email is UNIQUE (BR-11)
            raise EMAIL_TAKEN from err
        token = auth.start_session(cur, user["id"])
    return signed_in(user, token, 201)


@router.post("/api/auth/login", response_model=UserOut, responses={401: {"model": ErrorOut}, 429: {"model": ErrorOut}})
def login(body: LoginIn):
    if auth.too_many_failures(body.email):
        raise TOO_MANY
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        user = cur.execute(USER_BY_EMAIL_SQL, {"email": body.email}).fetchone()
        if user is None or not auth.verify_password(body.password, user["password_hash"]):
            auth.record_failure(body.email)
            raise WRONG_LOGIN
        auth.clear_failures(body.email)
        token = auth.start_session(cur, user["id"])
    return signed_in(user, token)


@router.post("/api/auth/demo", response_model=UserOut)
def demo_login():
    """The "Dùng thử" button: sign in to the shared demo account (seed data), no password."""
    with db.pool.connection(timeout=5) as conn:
        cur = conn.cursor(row_factory=dict_row)
        user = cur.execute(USER_BY_EMAIL_SQL, {"email": auth.DEMO_EMAIL}).fetchone()
        if user is None:
            raise ApiError(404, "NO_DEMO", "Bản này chưa có tài khoản dùng thử.")
        token = auth.start_session(cur, user["id"])
    return signed_in(user, token)


@router.post("/api/auth/logout", status_code=204, response_class=Response)
def logout(request: Request):
    token = request.cookies.get(auth.COOKIE)
    if token:
        with db.pool.connection(timeout=5) as conn:
            conn.execute(DELETE_SESSION_SQL, {"token_hash": auth.token_hash(token)})
    response = Response(status_code=204)
    response.delete_cookie(auth.COOKIE, path="/")
    return response


@router.get("/api/auth/me", response_model=UserOut, responses={401: {"model": ErrorOut}})
def me(user: auth.CurrentUser):
    return user


def safe_next(next_url: str | None) -> str:
    """Only a path on this site: "//evil.com" or "https://..." would send the user away after signing in."""
    if next_url and next_url.startswith("/") and not next_url.startswith("//") and "\\" not in next_url:
        return next_url
    return "/"


@router.get("/dang-nhap", include_in_schema=False)
def login_page(request: Request, next: str | None = None):
    if auth.user_from_request(request):
        return RedirectResponse(safe_next(next), status_code=303)
    return templates.TemplateResponse(request, "login.html", {"next": safe_next(next)})


@router.get("/dang-ky", include_in_schema=False)
def register_page(request: Request, next: str | None = None):
    if auth.user_from_request(request):
        return RedirectResponse(safe_next(next), status_code=303)
    return templates.TemplateResponse(request, "register.html", {"next": safe_next(next)})
