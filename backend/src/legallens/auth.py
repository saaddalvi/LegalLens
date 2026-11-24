"""Sign-in: turning a Clerk session token into a Clerk user id."""

from __future__ import annotations

import logging
import os
import ssl
from typing import Protocol

import certifi
import jwt
from jwt import PyJWKClient


class InvalidToken(Exception):
    """The token is missing a claim, expired, or not one Clerk issued for this app."""


class TokenVerifier(Protocol):
    def verify(self, token: str) -> str:
        """The Clerk user id the token was issued to; raises InvalidToken otherwise."""
        ...


class ClerkVerifier:
    """Checks a Clerk session token's signature against the instance's JWKS, its expiry
    and not-before time, its issuer, and its authorised party (`azp`: the frontend that
    asked Clerk for it)."""

    def __init__(
        self,
        issuer: str,
        authorized_parties: list[str],
        keys: PyJWKClient | None = None,
    ):
        self.issuer = issuer.rstrip("/")
        self.authorized_parties = authorized_parties
        # PyJWKClient caches the fetched keys, so the JWKS is not fetched per request.
        # certifi's CA bundle, because a Python without system certificates (a python.org
        # build on macOS) cannot otherwise fetch the JWKS, and every token would be refused.
        self._keys = keys or PyJWKClient(
            f"{self.issuer}/.well-known/jwks.json",
            ssl_context=ssl.create_default_context(cafile=certifi.where()),
        )

    @classmethod
    def from_env(cls) -> ClerkVerifier | None:
        """Reads CLERK_ISSUER (the Frontend API URL) and CLERK_AUTHORIZED_PARTIES
        (comma-separated frontend origins). None when CLERK_ISSUER is not set."""
        issuer = os.environ.get("CLERK_ISSUER", "").strip()
        if not issuer:
            logging.getLogger(__name__).warning(
                "CLERK_ISSUER is not set; /ask and /ask/stream will refuse every request"
            )
            return None
        parties = [
            p.strip()
            for p in os.environ.get(
                "CLERK_AUTHORIZED_PARTIES", "http://localhost:3000"
            ).split(",")
            if p.strip()
        ]
        return cls(issuer, parties)

    def verify(self, token: str) -> str:
        try:
            key = self._keys.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=self.issuer,
                options={"require": ["exp", "iss", "sub"]},
            )
        except (jwt.PyJWTError, ValueError) as exc:
            raise InvalidToken(str(exc)) from exc
        if claims.get("azp") not in self.authorized_parties:
            raise InvalidToken("token was not issued to an authorised party")
        sub = claims["sub"]
        if not isinstance(sub, str) or not sub:
            raise InvalidToken("token has no user id")
        return sub
