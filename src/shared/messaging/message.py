from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, DefaultDict, Optional, Self

if TYPE_CHECKING:
    from ..network import Connection


@dataclass(slots=True)
class Message:
    message: str
    data: Optional[Any] = None

    def as_json(self, encoding: str = "utf-8") -> bytes:
        message = asdict(self)
        return json.dumps(message).encode(encoding)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Message:
        return Message(message=data["message"], data=data.get("data"))


MsgHandlerFunc = Callable[["Connection", Message], None]


class MessageRouter:
    def __init__(self, prefix: str = ""):
        self.prefix = prefix
        self.routes: dict[str, list[MsgHandlerFunc]] = DefaultDict(list)

    def serve(self, ctx: Connection, message: Message):
        routes = self.routes.get(message.message)
        if not routes:
            ctx.send(Message("unregistered message"))
            return

        for handler in routes:
            handler(ctx, message)

    def register(self, message: str) -> Callable[[MsgHandlerFunc], MsgHandlerFunc]:
        def decorator(fn: MsgHandlerFunc) -> MsgHandlerFunc:
            self.routes[self.prefix + message].append(fn)

            @wraps(fn)
            def wrapper(ctx: Connection, msg: Message):
                fn(ctx, msg)

            return wrapper

        return decorator

    def include_router(self, sub_router: MessageRouter) -> Self:
        for k, v in sub_router.routes.items():
            self.routes[k].extend(v)

        return self
