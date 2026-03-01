"""
NeoPilot Enterprise Policy Engine
RBAC baseado em YAML: define permissões por papel/usuário/contexto.
"""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from neopilot.core.logger import get_logger

logger = get_logger("enterprise_policy")


@dataclass
class PolicyRule:
    """Regra individual de política."""
    action: str          # Glob pattern: "web.navigate", "file.delete.*"
    resource: str        # Glob pattern: "*.py", "http://*", "*"
    allow: bool
    requires_approval: bool = False
    audit: bool = True
    roles: list[str] = field(default_factory=list)  # [] = todos os papéis


@dataclass
class Role:
    name: str
    display_name: str
    permissions: list[str]  # Lista de ações permitidas (glob)
    denied: list[str] = field(default_factory=list)


@dataclass
class PolicyDecision:
    allowed: bool
    requires_approval: bool
    audit: bool
    reason: str


class EnterprisePolicyEngine:
    """
    Motor de políticas enterprise para NeoPilot.
    Carrega regras de YAML e avalia permissões em tempo real.
    """

    DEFAULT_POLICY_PATH = Path.home() / ".neopilot" / "enterprise_policy.yaml"

    # Papéis embutidos
    BUILTIN_ROLES = {
        "student": Role(
            name="student",
            display_name="Aluno",
            permissions=["read.*", "write.documents.*", "libreoffice.*", "web.*"],
            denied=["file.delete.*", "system.*", "security.*"],
        ),
        "teacher": Role(
            name="teacher",
            display_name="Professor",
            permissions=["read.*", "write.*", "libreoffice.*", "web.*", "dashboard.*"],
            denied=["system.*"],
        ),
        "developer": Role(
            name="developer",
            display_name="Desenvolvedor",
            permissions=["*"],
            denied=[],
        ),
        "admin": Role(
            name="admin",
            display_name="Administrador",
            permissions=["*"],
            denied=[],
        ),
        "readonly": Role(
            name="readonly",
            display_name="Somente Leitura",
            permissions=["read.*", "web.navigate.*"],
            denied=["write.*", "delete.*", "execute.*"],
        ),
    }

    def __init__(self, policy_path: Optional[Path] = None):
        self.policy_path = policy_path or self.DEFAULT_POLICY_PATH
        self._rules: list[PolicyRule] = []
        self._roles: dict[str, Role] = dict(self.BUILTIN_ROLES)
        self._current_role: str = "developer"  # Papel padrão
        self._current_user: Optional[str] = os.environ.get("USER")
        self._load()

    def _load(self) -> None:
        """Carrega políticas do arquivo YAML."""
        if not self.policy_path.exists():
            self._create_default_policy()
            return

        try:
            import yaml
            with open(self.policy_path) as f:
                data = yaml.safe_load(f)

            if not data:
                return

            # Carrega papéis customizados
            for role_data in data.get("roles", []):
                role = Role(
                    name=role_data["name"],
                    display_name=role_data.get("display_name", role_data["name"]),
                    permissions=role_data.get("permissions", []),
                    denied=role_data.get("denied", []),
                )
                self._roles[role.name] = role

            # Carrega regras
            for rule_data in data.get("rules", []):
                rule = PolicyRule(
                    action=rule_data["action"],
                    resource=rule_data.get("resource", "*"),
                    allow=rule_data.get("allow", True),
                    requires_approval=rule_data.get("requires_approval", False),
                    audit=rule_data.get("audit", True),
                    roles=rule_data.get("roles", []),
                )
                self._rules.append(rule)

            # Papel padrão
            if "default_role" in data:
                self._current_role = data["default_role"]

            logger.info(
                "Política enterprise carregada",
                rules=len(self._rules),
                roles=len(self._roles),
            )
        except Exception as e:
            logger.error("Falha ao carregar política", error=str(e))

    def _create_default_policy(self) -> None:
        """Cria arquivo de política padrão."""
        default_yaml = """# NeoPilot Enterprise Policy
# Define permissões por papel e ação

default_role: developer

roles:
  - name: student
    display_name: Aluno
    permissions:
      - "read.*"
      - "write.documents.*"
      - "libreoffice.*"
      - "web.navigate.*"
    denied:
      - "file.delete.*"
      - "system.*"

  - name: teacher
    display_name: Professor
    permissions:
      - "read.*"
      - "write.*"
      - "libreoffice.*"
      - "web.*"
      - "dashboard.*"
    denied:
      - "system.*"

rules:
  # Sempre requer aprovação para deletar arquivos
  - action: "file.delete.*"
    resource: "*"
    allow: true
    requires_approval: true
    audit: true

  # Bloqueia acesso a sites não-educacionais em modo aluno
  - action: "web.navigate"
    resource: "http://social-media.example.com/*"
    allow: false
    roles: ["student"]
    audit: true

  # Permite LibreOffice sem restrições
  - action: "libreoffice.*"
    resource: "*"
    allow: true
    requires_approval: false
    audit: true

  # Requer aprovação para executar código
  - action: "code.execute"
    resource: "*"
    allow: true
    requires_approval: true
    audit: true
"""
        self.policy_path.parent.mkdir(parents=True, exist_ok=True)
        self.policy_path.write_text(default_yaml)
        logger.info("Política padrão criada", path=str(self.policy_path))

    def set_role(self, role: str, user: Optional[str] = None) -> bool:
        """Define papel atual (ex: ao iniciar sessão de aluno)."""
        if role not in self._roles:
            logger.warning("Papel desconhecido", role=role)
            return False
        self._current_role = role
        if user:
            self._current_user = user
        logger.info("Papel definido", role=role, user=user)
        return True

    def evaluate(self, action: str, resource: str = "*") -> PolicyDecision:
        """
        Avalia se ação/recurso é permitido para papel atual.
        Ordem: regras explícitas → RBAC de papel → negação padrão para ações críticas.
        """
        role = self._roles.get(self._current_role)

        # Verifica regras explícitas (primeira que bater wins)
        for rule in self._rules:
            if not fnmatch.fnmatch(action, rule.action):
                continue
            if not fnmatch.fnmatch(resource, rule.resource):
                continue
            if rule.roles and self._current_role not in rule.roles:
                continue

            return PolicyDecision(
                allowed=rule.allow,
                requires_approval=rule.requires_approval,
                audit=rule.audit,
                reason=f"Regra explícita: {rule.action}/{rule.resource}",
            )

        # Verifica RBAC do papel
        if role:
            # Negações têm prioridade
            for denied in role.denied:
                if fnmatch.fnmatch(action, denied):
                    return PolicyDecision(
                        allowed=False,
                        requires_approval=False,
                        audit=True,
                        reason=f"Papel '{role.name}' nega: {denied}",
                    )

            # Permissões
            for perm in role.permissions:
                if fnmatch.fnmatch(action, perm):
                    return PolicyDecision(
                        allowed=True,
                        requires_approval=False,
                        audit=True,
                        reason=f"Papel '{role.name}' permite: {perm}",
                    )

        # Padrão: permite para desenvolvedor/admin, nega para outros
        default_allow = self._current_role in ("developer", "admin")
        return PolicyDecision(
            allowed=default_allow,
            requires_approval=False,
            audit=True,
            reason=f"Política padrão para papel '{self._current_role}'",
        )

    def is_allowed(self, action: str, resource: str = "*") -> bool:
        """Shorthand para evaluate().allowed."""
        return self.evaluate(action, resource).allowed

    def get_current_role(self) -> str:
        return self._current_role

    def get_role_info(self, role_name: Optional[str] = None) -> Optional[Role]:
        return self._roles.get(role_name or self._current_role)

    def list_roles(self) -> list[str]:
        return list(self._roles.keys())

    def add_rule(self, rule: PolicyRule) -> None:
        """Adiciona regra em runtime."""
        self._rules.insert(0, rule)  # Regras novas têm prioridade

    def audit_log(self, action: str, resource: str, decision: PolicyDecision) -> None:
        """Registra decisão de política no audit log."""
        if decision.audit:
            logger.info(
                "Decisão de política",
                action=action,
                resource=resource[:80],
                allowed=decision.allowed,
                role=self._current_role,
                user=self._current_user,
                reason=decision.reason,
            )
