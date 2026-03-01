"""Testes unitários — EnterprisePolicyEngine."""

import pytest
from pathlib import Path

from neopilot.security.enterprise_policy import (
    EnterprisePolicyEngine, PolicyRule,
)


@pytest.fixture
def policy(tmp_path):
    engine = EnterprisePolicyEngine(policy_path=tmp_path / "policy.yaml")
    return engine


def test_default_role_is_developer(policy):
    assert policy.get_current_role() == "developer"


def test_developer_can_do_anything(policy):
    policy.set_role("developer")
    assert policy.is_allowed("file.delete.important")
    assert policy.is_allowed("web.navigate", "https://anything.com")
    assert policy.is_allowed("system.shutdown")


def test_student_denied_file_delete(policy):
    policy.set_role("student")
    decision = policy.evaluate("file.delete.document.pdf")
    assert not decision.allowed
    assert "student" in decision.reason.lower() or "deny" in decision.reason.lower() or "nega" in decision.reason.lower()


def test_student_can_read(policy):
    policy.set_role("student")
    assert policy.is_allowed("read.documents.report")
    assert policy.is_allowed("libreoffice.calc")
    assert policy.is_allowed("web.navigate")


def test_teacher_can_use_dashboard(policy):
    policy.set_role("teacher")
    assert policy.is_allowed("dashboard.view")
    assert policy.is_allowed("write.documents.any")


def test_readonly_cannot_write(policy):
    policy.set_role("readonly")
    assert not policy.is_allowed("write.file.txt")
    assert not policy.is_allowed("delete.any")
    assert policy.is_allowed("read.anything")


def test_set_invalid_role(policy):
    result = policy.set_role("nonexistent_role")
    assert not result
    assert policy.get_current_role() == "developer"  # unchanged


def test_add_custom_rule(policy):
    policy.set_role("student")
    # Estudante não pode acessar redes sociais
    rule = PolicyRule(
        action="web.navigate",
        resource="https://facebook.com/*",
        allow=False,
        roles=["student"],
        audit=True,
    )
    policy.add_rule(rule)

    decision = policy.evaluate("web.navigate", "https://facebook.com/feed")
    assert not decision.allowed


def test_requires_approval_for_code_execution(policy):
    """Execução de código deve requerer aprovação quando regra explícita existe."""
    from neopilot.security.enterprise_policy import PolicyRule
    rule = PolicyRule(
        action="code.execute",
        resource="*",
        allow=True,
        requires_approval=True,
        audit=True,
    )
    policy.add_rule(rule)
    decision = policy.evaluate("code.execute", "script.py")
    assert decision.requires_approval


def test_list_roles(policy):
    roles = policy.list_roles()
    assert "student" in roles
    assert "teacher" in roles
    assert "developer" in roles
    assert "admin" in roles


def test_role_info(policy):
    info = policy.get_role_info("student")
    assert info is not None
    assert info.name == "student"
    assert len(info.permissions) > 0
    assert len(info.denied) > 0
