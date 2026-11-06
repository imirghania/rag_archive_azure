import time

import jwt
import pytest

from docai.security.access import Principal
from docai.security.auth import AuthError, DevIdentity, principal_from_claims

K = "k" * 32
P = Principal("oid-1", "Layla", ["DocAI.Reader"], ["g1"])


def test_a_valid_token_gives_the_principal_back():
    d = DevIdentity(K)
    got = d.validate(d.issue(P))
    assert (got.oid, got.name, got.roles, got.groups) == ("oid-1", "Layla", ["DocAI.Reader"], ["g1"])


@pytest.mark.parametrize("mutate", ["expired", "wrong_key", "wrong_audience", "no_role", "garbage"])
def test_bad_tokens_are_refused(mutate):
    d = DevIdentity(K)
    tok = {
        "expired": lambda: d.issue(P, ttl=-10),
        "wrong_key": lambda: DevIdentity("o" * 32).issue(P),
        "wrong_audience": lambda: jwt.encode({"aud": "api://other", "iss": "docai-dev", "oid": "x", "roles": ["DocAI.Reader"], "exp": time.time() + 99}, K, algorithm="HS256"),
        "no_role": lambda: d.issue(Principal("o", "n", ["Some.Other.Role"], [])),
        "garbage": lambda: "not.a.token",
    }[mutate]()
    with pytest.raises(AuthError):
        d.validate(tok)


def test_a_groups_overage_pointer_is_an_error_not_an_empty_scope():
    with pytest.raises(AuthError, match="too many groups"):
        principal_from_claims({"oid": "o", "roles": ["DocAI.Reader"], "_claim_names": {"groups": "src1"}})
