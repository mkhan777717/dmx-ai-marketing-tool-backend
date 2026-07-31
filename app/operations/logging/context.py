import contextvars
from typing import Optional

request_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)

correlation_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)

workspace_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "workspace_id", default=None
)

user_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "user_id", default=None
)

job_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "job_id", default=None
)

event_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "event_id", default=None
)


def set_context_var(
    ctx_var: contextvars.ContextVar, value: Optional[str]
) -> contextvars.Token:
    return ctx_var.set(value)


def reset_context_var(
    ctx_var: contextvars.ContextVar, token: contextvars.Token
) -> None:
    ctx_var.reset(token)


def get_context_dict() -> dict[str, str]:
    ctx = {}
    if req_id := request_id_ctx.get():
        ctx["request_id"] = req_id
    if corr_id := correlation_id_ctx.get():
        ctx["correlation_id"] = corr_id
    if ws_id := workspace_id_ctx.get():
        ctx["workspace_id"] = ws_id
    if usr_id := user_id_ctx.get():
        ctx["user_id"] = usr_id
    if j_id := job_id_ctx.get():
        ctx["job_id"] = j_id
    if e_id := event_id_ctx.get():
        ctx["event_id"] = e_id
    return ctx
