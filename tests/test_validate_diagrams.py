"""Oraculo congelado del gate de diagramas Mermaid 'flowchart' (Contrato: diagram-gate).

Fija el comportamiento de ``scripts/validate_diagrams.py``. Parser propio en
Python puro (sin subprocess/red/LLM, por 'forbids' de este repo) para el
subconjunto 'flowchart' de Mermaid — NO el parser real de mermaid.

  API: ``parse_flowchart(text) -> {'nodes': [...], 'edges': [...]}`` y
  ``validate_diagram(mmd_path, contract_path) -> list`` — findings
  ``{'file','level','rule','msg'}`` ordenados por (rule, msg).

  Checks y severidad EXACTA:
    FILE_ERROR (ERROR)               el .mmd no se pudo leer.
    CONTRACT_INVALID (ERROR)         el .diagram-contract.json no existe o
                                      no es JSON valido.
    DIAGRAM_TYPE_UNSUPPORTED (ERROR) el contrato pide un diagram_type
                                      distinto de 'flowchart' (este gate solo
                                      soporta flowchart).
    DIAGRAM_TYPE_MISMATCH (ERROR)    el .mmd no arranca con 'flowchart' o
                                      'graph'.
    MIN_NODES / MAX_NODES (ERROR)    cantidad de nodos fuera del rango
                                      declarado en el contrato.
    MISSING_NODE (ERROR)             un id de required_nodes no aparece en
                                      el diagrama.
    NODE_LABEL_MISMATCH (ERROR)      el nodo existe pero su label no
                                      coincide con el declarado.
    MISSING_EDGE (ERROR)             un edge (from/to[/label]) de
                                      required_edges no aparece.

  CLI (``main(argv)``): uno o mas paths (archivo .mmd o directorio);
  default ``['examples/diagrams']``. Directorio se escanea recursivamente
  por ``*.mmd``; cada .mmd espera un ``<mismo-nombre>.diagram-contract.json``
  al lado. Path inexistente o sin .mmd -> INFO ``PATH_MISSING`` (no bloquea).
  .mmd sin contrato -> WARNING ``CONTRACT_MISSING`` (no bloquea: capa
  opt-in, un diagrama puede existir sin contrato). Exit 1 solo si hay >=1
  ERROR. Resumen: ``Resumen: N error(es), M warning(s), K diagrama(s)
  verificados`` (K = pares .mmd+contrato efectivamente validados).

Este archivo es un ORACULO CONGELADO (tests_sha256): el implementador no lo
modifica. Ver knowledge/contracts/diagram-gate.md.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import validate_diagrams as vd  # noqa: E402


FLOWCHART_OK = (
    "flowchart TD\n"
    "    A[Inicio] --> B{Condicion}\n"
    "    B -->|Si| C[Accion 1]\n"
    "    B -->|No| D[Accion 2]\n"
)


class _Fixture(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="diag_")
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)

    def _write(self, name, content):
        p = os.path.join(self.base, name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(content)
        return p

    def _write_json(self, name, obj):
        return self._write(name, json.dumps(obj))

    def _pair(self, mmd_content, contract_obj, base_name="d"):
        mmd = self._write(base_name + ".mmd", mmd_content)
        self._write_json(base_name + ".diagram-contract.json", contract_obj)
        return mmd, mmd[:-4] + ".diagram-contract.json"

    def _rules(self, findings, level=None):
        if level is None:
            return sorted(f["rule"] for f in findings)
        return sorted(f["rule"] for f in findings if f["level"] == level)


class TestParseFlowchart(unittest.TestCase):
    def test_nodos_y_edges_basicos(self):
        parsed = vd.parse_flowchart(FLOWCHART_OK)
        nodes_by_id = {n["id"]: n["label"] for n in parsed["nodes"]}
        self.assertEqual(nodes_by_id, {
            "A": "Inicio", "B": "Condicion", "C": "Accion 1", "D": "Accion 2",
        })
        edges = [(e["from"], e["to"], e["label"]) for e in parsed["edges"]]
        self.assertEqual(edges, [
            ("A", "B", None), ("B", "C", "Si"), ("B", "D", "No"),
        ])

    def test_nodo_sin_shape_usa_id_como_label(self):
        parsed = vd.parse_flowchart("flowchart TD\n    X --> Y\n")
        nodes_by_id = {n["id"]: n["label"] for n in parsed["nodes"]}
        self.assertEqual(nodes_by_id, {"X": "X", "Y": "Y"})

    def test_diagram_type_flowchart_y_graph(self):
        self.assertEqual(vd.get_diagram_type("flowchart TD\nA-->B"), "flowchart")
        self.assertEqual(vd.get_diagram_type("graph LR\nA-->B"), "graph")

    def test_comentarios_y_lineas_vacias_se_ignoran(self):
        text = "flowchart TD\n\n    %% comentario\n    A --> B\n"
        parsed = vd.parse_flowchart(text)
        self.assertEqual(len(parsed["edges"]), 1)


class TestValidateDiagramEstructura(_Fixture):
    def test_diagrama_valido_sin_findings(self):
        mmd, contract = self._pair(FLOWCHART_OK, {
            "diagram_type": "flowchart",
            "min_nodes": 3, "max_nodes": 10,
            "required_nodes": [{"id": "A", "label": "Inicio"}, {"id": "B"}],
            "required_edges": [{"from": "A", "to": "B"}, {"from": "B", "to": "C", "label": "Si"}],
        })
        self.assertEqual(vd.validate_diagram(mmd, contract), [])

    def test_falta_nodo_requerido(self):
        mmd, contract = self._pair(FLOWCHART_OK, {
            "diagram_type": "flowchart",
            "required_nodes": [{"id": "Z"}],
        })
        findings = vd.validate_diagram(mmd, contract)
        self.assertIn("MISSING_NODE", self._rules(findings))
        self.assertTrue(any("'Z'" in f["msg"] for f in findings))

    def test_label_de_nodo_no_coincide(self):
        mmd, contract = self._pair(FLOWCHART_OK, {
            "diagram_type": "flowchart",
            "required_nodes": [{"id": "A", "label": "Otro"}],
        })
        findings = vd.validate_diagram(mmd, contract)
        self.assertIn("NODE_LABEL_MISMATCH", self._rules(findings))

    def test_falta_edge_requerido(self):
        mmd, contract = self._pair(FLOWCHART_OK, {
            "diagram_type": "flowchart",
            "required_edges": [{"from": "C", "to": "A"}],
        })
        findings = vd.validate_diagram(mmd, contract)
        self.assertIn("MISSING_EDGE", self._rules(findings))

    def test_min_nodes_y_max_nodes(self):
        mmd, contract = self._pair(FLOWCHART_OK, {"diagram_type": "flowchart", "min_nodes": 10})
        self.assertIn("MIN_NODES", self._rules(vd.validate_diagram(mmd, contract)))

        mmd2, contract2 = self._pair(FLOWCHART_OK, {"diagram_type": "flowchart", "max_nodes": 1}, "d2")
        self.assertIn("MAX_NODES", self._rules(vd.validate_diagram(mmd2, contract2)))

    def test_diagram_type_mismatch(self):
        mmd, contract = self._pair("graph TD\n    A --> B\n", {"diagram_type": "flowchart"}, "d3")
        # graph es alias valido de flowchart: no debe dar mismatch
        self.assertEqual(vd.validate_diagram(mmd, contract), [])

    def test_diagram_type_unsupported_en_contrato(self):
        mmd, contract = self._pair(FLOWCHART_OK, {"diagram_type": "sequenceDiagram"})
        findings = vd.validate_diagram(mmd, contract)
        self.assertEqual(self._rules(findings), ["DIAGRAM_TYPE_UNSUPPORTED"])

    def test_contrato_invalido(self):
        mmd = self._write("bad.mmd", FLOWCHART_OK)
        contract = self._write("bad.diagram-contract.json", "{no es json valido")
        findings = vd.validate_diagram(mmd, contract)
        self.assertEqual(self._rules(findings), ["CONTRACT_INVALID"])

    def test_archivo_mmd_inexistente(self):
        contract = self._write_json("x.diagram-contract.json", {"diagram_type": "flowchart"})
        findings = vd.validate_diagram(os.path.join(self.base, "no-existe.mmd"), contract)
        self.assertEqual(self._rules(findings), ["FILE_ERROR"])


class TestMain(_Fixture):
    def _run_main(self, argv):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exit_code = vd.main(argv)
        return exit_code, buf.getvalue()

    def test_path_inexistente_da_info_y_exit_0(self):
        exit_code, out = self._run_main([os.path.join(self.base, "no-existe")])
        self.assertEqual(exit_code, 0)
        self.assertIn("PATH_MISSING", out)

    def test_mmd_sin_contrato_da_warning_no_bloquea(self):
        mmd = self._write("solo.mmd", FLOWCHART_OK)
        exit_code, out = self._run_main([mmd])
        self.assertEqual(exit_code, 0)
        self.assertIn("CONTRACT_MISSING", out)

    def test_par_valido_exit_0(self):
        mmd, _ = self._pair(FLOWCHART_OK, {"diagram_type": "flowchart", "required_nodes": [{"id": "A"}]})
        exit_code, out = self._run_main([mmd])
        self.assertEqual(exit_code, 0)
        self.assertIn("Resumen: 0 error(es), 0 warning(s), 1 diagrama(s) verificados", out)

    def test_par_invalido_exit_1(self):
        mmd, _ = self._pair(FLOWCHART_OK, {"diagram_type": "flowchart", "required_nodes": [{"id": "Z"}]})
        exit_code, out = self._run_main([mmd])
        self.assertEqual(exit_code, 1)

    def test_directorio_recursivo(self):
        sub = os.path.join(self.base, "sub")
        os.makedirs(sub)
        with open(os.path.join(sub, "e.mmd"), "w", encoding="utf-8") as fh:
            fh.write(FLOWCHART_OK)
        with open(os.path.join(sub, "e.diagram-contract.json"), "w", encoding="utf-8") as fh:
            json.dump({"diagram_type": "flowchart"}, fh)
        exit_code, out = self._run_main([self.base])
        self.assertEqual(exit_code, 0)
        self.assertIn("1 diagrama(s) verificados", out)


if __name__ == "__main__":
    unittest.main()
