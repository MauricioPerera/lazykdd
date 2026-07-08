"""Checker de integridad referencial del cableado de agentes (Contrato 26).

Valida SOLO integridad referencial (frontera code_only del dominio agent-wiring):
  - agent_skills[i].agent declarado en agents, .skill en skills_registry
  - agent_mcp[i].agent declarado en agents, .server en mcp_registry

Oraculo congelado: tests/test_check_wiring.py
Task contract: knowledge/contracts/check-agent-wiring.md
"""


def check_agent_wiring(record) -> list:
    """Validar integridad referencial del cableado agente-skills-MCP.

    Args:
        record (dict): contiene agents, skills_registry, mcp_registry,
                       agent_skills, agent_mcp

    Returns:
        list: violaciones canónicas ordenadas (vacía si íntegro)
    """
    if not isinstance(record, dict):
        return []

    # Extraer componentes con defensas contra tipos raros
    agents = record.get("agents", [])
    if not isinstance(agents, list):
        agents = []

    skills_registry = record.get("skills_registry", [])
    if not isinstance(skills_registry, list):
        skills_registry = []

    mcp_registry = record.get("mcp_registry", [])
    if not isinstance(mcp_registry, list):
        mcp_registry = []

    agent_skills = record.get("agent_skills", [])
    if not isinstance(agent_skills, list):
        agent_skills = []

    agent_mcp = record.get("agent_mcp", [])
    if not isinstance(agent_mcp, list):
        agent_mcp = []

    # Construir sets de nombres válidos
    agent_names = set()
    for agent in agents:
        if isinstance(agent, dict) and "name" in agent:
            name_val = agent["name"]
            if name_val is not None:
                agent_names.add(name_val)

    skills_set = set(skills_registry)
    mcp_set = set(mcp_registry)

    # Recolectar violaciones (orden: agent_mcp primero, luego agent_skills)
    violations = []

    # Procesar agent_mcp (alfabético primero)
    for i, entry in enumerate(agent_mcp):
        if not isinstance(entry, dict):
            continue

        agent_val = entry.get("agent")
        server_val = entry.get("server")

        # Saltamos si ambos campos son None/ausentes
        if agent_val is None and server_val is None:
            continue

        # Validar agente primero (si presente y no None)
        if agent_val is not None and agent_val not in agent_names:
            violations.append(
                f"agent_mcp: entrada {i}: agente '{agent_val}' no declarado"
            )

        # Validar server (si presente y no None)
        if server_val is not None and server_val not in mcp_set:
            violations.append(
                f"agent_mcp: entrada {i}: server '{server_val}' no registrado"
            )

    # Procesar agent_skills
    for i, entry in enumerate(agent_skills):
        if not isinstance(entry, dict):
            continue

        agent_val = entry.get("agent")
        skill_val = entry.get("skill")

        # Saltamos si ambos campos son None/ausentes
        if agent_val is None and skill_val is None:
            continue

        # Validar agente primero (si presente y no None)
        if agent_val is not None and agent_val not in agent_names:
            violations.append(
                f"agent_skills: entrada {i}: agente '{agent_val}' no declarado"
            )

        # Validar skill (si presente y no None)
        if skill_val is not None and skill_val not in skills_set:
            violations.append(
                f"agent_skills: entrada {i}: skill '{skill_val}' no registrada"
            )

    return violations
