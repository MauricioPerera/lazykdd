"""Oraculo congelado del checker de cableado de agentes (Contrato 26).

Fija el comportamiento de ``src/check_agent_wiring.py``:

  API: ``def check_agent_wiring(record) -> list``

  El record (dict) trae:
    agents:          [{"name": str, ...}]           agentes declarados
    skills_registry: [str, ...]                      skills registradas
    mcp_registry:    [str, ...]                      servidores MCP registrados
    agent_skills:    [{"agent": str, "skill": str}]  cableado agente->skill
    agent_mcp:       [{"agent": str, "server": str}] cableado agente->MCP

  El checker valida SOLO integridad referencial (la frontera code_only del
  dominio agent-wiring; la presencia de campos es trabajo de las reglas
  declarativas):
    - agent_skills[i].agent debe estar declarado en agents (por name).
    - agent_skills[i].skill debe existir en skills_registry.
    - agent_mcp[i].agent   debe estar declarado en agents (por name).
    - agent_mcp[i].server  debe existir en mcp_registry.

  Violaciones canonicas (ASCII, indice y nombre exactos):
    "agent_skills: entrada <i>: agente '<x>' no declarado"
    "agent_skills: entrada <i>: skill '<x>' no registrada"
    "agent_mcp: entrada <i>: agente '<x>' no declarado"
    "agent_mcp: entrada <i>: server '<x>' no registrado"

  Semantica:
    - Lista vacia = cableado integro.
    - Entradas con el campo relevante ausente/None se SALTAN (required
      declarativo las cubre); una entrada puede emitir hasta 2 violaciones
      (agente Y referencia).
    - Colecciones ausentes o no-lista se saltan; elementos no-dict se saltan.
    - Orden determinista: agent_mcp/agent_skills agrupadas por coleccion en
      orden alfabetico de coleccion y, dentro, por indice ascendente.
    - Nunca lanza con records raros.

Este archivo es un ORACULO CONGELADO (tests_sha256): el implementador no lo
modifica. Ver knowledge/contracts/check-agent-wiring.md.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "src")))

from check_agent_wiring import check_agent_wiring


def _rec(**overrides):
    base = {
        "agents": [{"name": "pm-nativo", "model": "fable"},
                   {"name": "dev-efimero", "model": "haiku"}],
        "skills_registry": ["pm-native-ccdd", "delegar-glm-ccdd"],
        "mcp_registry": ["ccdd-complexity", "pocketbase"],
        "agent_skills": [{"agent": "pm-nativo", "skill": "pm-native-ccdd"}],
        "agent_mcp": [{"agent": "pm-nativo", "server": "ccdd-complexity"}],
    }
    base.update(overrides)
    return base


class TestIntegro(unittest.TestCase):
    def test_cableado_valido_vacio(self):
        self.assertEqual(check_agent_wiring(_rec()), [])

    def test_colecciones_de_cableado_vacias(self):
        self.assertEqual(
            check_agent_wiring(_rec(agent_skills=[], agent_mcp=[])), [])


class TestSkillFantasma(unittest.TestCase):
    def test_skill_no_registrada(self):
        r = _rec(agent_skills=[{"agent": "pm-nativo", "skill": "fantasma"}])
        v = check_agent_wiring(r)
        self.assertEqual(
            v, ["agent_skills: entrada 0: skill 'fantasma' no registrada"])

    def test_server_no_registrado(self):
        r = _rec(agent_mcp=[{"agent": "dev-efimero", "server": "nadie"}])
        v = check_agent_wiring(r)
        self.assertEqual(
            v, ["agent_mcp: entrada 0: server 'nadie' no registrado"])

    def test_agente_no_declarado_en_ambas(self):
        r = _rec(
            agent_skills=[{"agent": "otro", "skill": "pm-native-ccdd"}],
            agent_mcp=[{"agent": "otro", "server": "pocketbase"}])
        v = check_agent_wiring(r)
        self.assertEqual(v, [
            "agent_mcp: entrada 0: agente 'otro' no declarado",
            "agent_skills: entrada 0: agente 'otro' no declarado",
        ])

    def test_entrada_doble_violacion(self):
        r = _rec(agent_skills=[{"agent": "nadie", "skill": "fantasma"}])
        v = check_agent_wiring(r)
        self.assertEqual(v, [
            "agent_skills: entrada 0: agente 'nadie' no declarado",
            "agent_skills: entrada 0: skill 'fantasma' no registrada",
        ])


class TestSaltos(unittest.TestCase):
    def test_campo_ausente_se_salta(self):
        # required declarativo cubre presencia; el checker no la duplica.
        r = _rec(agent_skills=[{"agent": "pm-nativo"},
                               {"skill": "pm-native-ccdd"},
                               {"agent": None, "skill": None}])
        self.assertEqual(check_agent_wiring(r), [])

    def test_colecciones_ausentes_o_no_lista(self):
        self.assertEqual(check_agent_wiring({}), [])
        self.assertEqual(
            check_agent_wiring(_rec(agent_skills="raro", agent_mcp=None)), [])

    def test_elemento_no_dict_se_salta(self):
        r = _rec(agent_skills=["texto", 42,
                               {"agent": "pm-nativo",
                                "skill": "pm-native-ccdd"}])
        self.assertEqual(check_agent_wiring(r), [])

    def test_registros_vacios_todo_es_fantasma(self):
        r = _rec(agents=[], skills_registry=[], mcp_registry=[])
        v = check_agent_wiring(r)
        self.assertEqual(len(v), 4, v)  # 2 por entrada (agente + referencia)


class TestOrdenYRobustez(unittest.TestCase):
    def test_orden_deterministico_multi(self):
        r = _rec(
            agent_skills=[
                {"agent": "pm-nativo", "skill": "f1"},
                {"agent": "pm-nativo", "skill": "f2"},
            ],
            agent_mcp=[{"agent": "pm-nativo", "server": "m1"}])
        v1 = check_agent_wiring(r)
        v2 = check_agent_wiring(r)
        self.assertEqual(v1, v2)
        self.assertEqual(v1, [
            "agent_mcp: entrada 0: server 'm1' no registrado",
            "agent_skills: entrada 0: skill 'f1' no registrada",
            "agent_skills: entrada 1: skill 'f2' no registrada",
        ])

    def test_nunca_lanza_con_record_raro(self):
        for rec in ({"agents": "x"}, {"agents": [{"sin_name": 1}]},
                    {"agent_skills": [{}]}, {"skills_registry": 7}):
            out = check_agent_wiring(rec)
            self.assertIsInstance(out, list)


if __name__ == "__main__":
    unittest.main()
