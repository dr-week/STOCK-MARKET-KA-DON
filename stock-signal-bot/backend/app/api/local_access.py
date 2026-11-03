"""Shared access guard for private local-only API resources."""

import ipaddress

from fastapi import HTTPException, Request


def require_loopback_client(request: Request) -> None:
    client = request.client
    try:
        is_loopback = client is not None and ipaddress.ip_address(client.host).is_loopback
    except ValueError:
        is_loopback = False
    if not is_loopback:
        raise HTTPException(status_code=403, detail="Private local data access is restricted to this PC.")
