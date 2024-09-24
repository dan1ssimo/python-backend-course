from typing import Any, Awaitable, Callable
import uvicorn
import math
from pprint import pprint
import json


def get_factorial(n):
    if n < 0:
        return None
    return math.factorial(n)


def get_fibonacci(n):
    if n < 0:
        return None
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def get_mean(data: list[float]):
    if len(data) == 0:
        return None
    return sum(data) / len(data)


async def app(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:

    path = scope["path"]
    method = scope["method"]
    path_params = path[1:].split("/")

    if not path_params:
        return await send_response(send, 422, json.dumps({"error": "Invalid path"}))

    if method == "GET":
        if path_params[0] == "factorial":

            try:
                n = int(scope["query_string"].decode().split("=")[1])
            except:
                return await send_response(
                    send,
                    422,
                    json.dumps({"error": "Invalid value for n, must be non-negative"}),
                )

            result = get_factorial(n)

            if result == None:
                return await send_response(
                    send,
                    400,
                    json.dumps({"error": "Invalid value for n, must be non-negative"}),
                )

            return await send_response(send, 200, json.dumps({"result": result}))

        if path_params[0] == "fibonacci":
            if len(path_params) < 2:
                return await send_response(
                    send, 422, json.dumps({"error": "Invalid param"})
                )

            try:
                n = int(path_params[1])
            except:
                return await send_response(
                    send,
                    422,
                    json.dumps({"error": "Inval"}),
                )

            result = get_fibonacci(n)

            if result == None:
                return await send_response(
                    send,
                    400,
                    json.dumps({"error": "Invalid value for n, must be non-negative"}),
                )

            return await send_response(send, 200, json.dumps({"result": result}))

        if path_params[0] == "mean":

            body = await receive_body(receive)

            try:
                ar = json.loads(body.decode())
            except:
                return await send_response(
                    send,
                    422,
                    json.dumps({"error": "Non json"}),
                )

            try:
                ar = [float(x) for x in ar]
            except:
                return await send_response(
                    send,
                    422,
                    json.dumps({"error": "Invalid value for n, must be non-negative"}),
                )

            result = get_mean(ar)

            if result == None:
                return await send_response(
                    send,
                    400,
                    json.dumps({"error": "Invalid value for n, must be non-negative"}),
                )

            return await send_response(send, 200, json.dumps({"result": result}))

    return await send_response(send, 404, json.dumps({"error": "Method not found"}))


async def receive_body(receive):
    body = b""
    more_body = True
    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)
    return body


async def send_response(send, status: int, body: str):
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                [b"content-type", b"application/json"],
            ],
        }
    )
    await send({"type": "http.response.body", "body": body.encode()})


if __name__ == "__main__":
    config = uvicorn.Config("homework_1:app", port=8000, log_level="info")
    server = uvicorn.Server(config)
    server.run()
