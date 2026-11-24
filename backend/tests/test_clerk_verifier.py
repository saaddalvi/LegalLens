"""ClerkVerifier checks a Clerk session token's signature (against the JWKS), expiry, issuer
and authorised party, and returns the Clerk user id."""

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from legallens.auth import ClerkVerifier, InvalidToken

ISSUER = "https://clerk.example.test"
ORIGIN = "http://localhost:3000"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class FakeKeys:
    """Stands in for the JWKS fetch: always yields KEY's public half."""

    def get_signing_key_from_jwt(self, token):
        class Signing:
            key = KEY.public_key()

        return Signing()


def token(*, key=KEY, **claims):
    payload = {
        "sub": "user_123",
        "iss": ISSUER,
        "azp": ORIGIN,
        "exp": time.time() + 60,
        "nbf": time.time() - 5,
        **claims,
    }
    return jwt.encode(payload, key, algorithm="RS256", headers={"kid": "k1"})


@pytest.fixture
def verifier():
    return ClerkVerifier(ISSUER, [ORIGIN], keys=FakeKeys())


def test_a_valid_token_gives_the_user_id(verifier):
    assert verifier.verify(token()) == "user_123"


@pytest.mark.parametrize(
    "bad",
    [
        lambda: token(exp=time.time() - 10),
        lambda: token(iss="https://evil.example"),
        lambda: token(azp="https://evil.example"),
        lambda: token(key=OTHER_KEY),
        lambda: "not.a.jwt",
        lambda: jwt.encode({"sub": "user_123", "iss": ISSUER}, "x", algorithm="HS256"),
    ],
    ids=["expired", "wrong-issuer", "wrong-party", "bad-signature", "garbage", "hs256"],
)
def test_a_bad_token_is_invalid(verifier, bad):
    with pytest.raises(InvalidToken):
        verifier.verify(bad())


def test_a_token_without_a_party_or_subject_is_invalid(verifier):
    no_azp = jwt.encode(
        {"sub": "u", "iss": ISSUER, "exp": time.time() + 60}, KEY, algorithm="RS256"
    )
    with pytest.raises(InvalidToken):
        verifier.verify(no_azp)
    no_sub = jwt.encode(
        {"iss": ISSUER, "azp": ORIGIN, "exp": time.time() + 60}, KEY, algorithm="RS256"
    )
    with pytest.raises(InvalidToken):
        verifier.verify(no_sub)


def test_from_env_needs_an_issuer_and_authorised_parties(monkeypatch):
    monkeypatch.delenv("CLERK_ISSUER", raising=False)
    assert ClerkVerifier.from_env() is None
    monkeypatch.setenv("CLERK_ISSUER", ISSUER + "/")
    monkeypatch.setenv("CLERK_AUTHORIZED_PARTIES", f"{ORIGIN}, https://app.example")
    v = ClerkVerifier.from_env()
    assert v.issuer == ISSUER  # trailing slash dropped
    assert v.authorized_parties == [ORIGIN, "https://app.example"]
