import pytest

from docai.security.access import Principal, access_scope, departments_with, is_admin, require, scope_hash
from docai.contracts.enums import Capability as C

R = {"g-fin-r": ("FIN", "reader"), "g-fin-e": ("FIN", "expert"), "g-fin-s": ("FIN", "steward"), "g-fin-t": ("FIN", "restricted"),
     "g-hr-r": ("HR", "reader")}


def test_unregistered_groups_never_grant_access():
    assert access_scope(R, ["g-fin-r", "random-group", "g-hr-r"]) == ["g-fin-r", "g-hr-r"]
    assert scope_hash(["b", "a"]) == scope_hash(["a", "b"])


def test_the_spec_case_expert_in_finance_reader_only_in_hr_cannot_settle_an_hr_task():
    layla = Principal("1", "Layla", ["DocAI.Reader", "DocAI.Expert"], ["g-fin-r", "g-fin-e", "g-hr-r"])
    assert departments_with(R, layla, C.review) == ["FIN"]
    assert departments_with(R, layla, C.ask) == ["FIN", "HR"]
    with pytest.raises(PermissionError):
        require(R, layla, C.review, "HR")


def test_the_role_alone_grants_nothing_and_the_group_alone_grants_nothing():
    assert departments_with(R, Principal("1", "x", ["DocAI.Expert"], []), C.review) == []
    assert departments_with(R, Principal("1", "x", ["DocAI.Reader"], ["g-fin-e"]), C.review) == []


def test_the_four_mvp_users_get_exactly_their_capabilities():
    layla = Principal("1", "Layla", ["DocAI.Reader"], ["g-fin-r"])
    sara = Principal("2", "Sara", ["DocAI.Expert"], ["g-fin-r", "g-fin-e", "g-fin-t"])
    rana = Principal("3", "Rana", ["DocAI.Steward"], ["g-fin-r", "g-fin-s"])
    yousef = Principal("4", "Yousef", ["DocAI.Admin"], [])
    caps = lambda p: {c: departments_with(R, p, c) for c in C}  # noqa: E731
    assert caps(layla) == {C.ask: ["FIN"], C.review: [], C.approve: [], C.upload: []}
    assert caps(sara) == {C.ask: ["FIN"], C.review: ["FIN"], C.approve: [], C.upload: ["FIN"]}
    assert caps(rana) == {C.ask: ["FIN"], C.review: ["FIN"], C.approve: ["FIN"], C.upload: []}
    assert caps(yousef) == {C.ask: [], C.review: [], C.approve: [], C.upload: []} and is_admin(yousef)


def test_a_department_with_an_uploader_group_needs_the_uploader_role_and_group():
    reg = {**R, "g-fin-u": ("FIN", "uploader")}
    sara = Principal("2", "Sara", ["DocAI.Expert"], ["g-fin-r", "g-fin-e"])
    clerk = Principal("5", "Clerk", ["DocAI.Uploader", "DocAI.Reader"], ["g-fin-r", "g-fin-u"])
    assert departments_with(reg, sara, C.upload) == []
    assert departments_with(reg, clerk, C.upload) == ["FIN"]
