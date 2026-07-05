"""Tests unitarios del ensamblador de contexto CCDD Nivel 2 (KDD).

Cubren lo que lista la seccion Tests del task contract
``knowledge/contracts/assemble-context.md``: presupuesto respetado,
prioridades, truncado, min_tokens, firma estable, determinismo 2x,
retriever por mencion/tags/fallback, regex_deny aborta, reference_check
detecta y pasa, exit codes del CLI.

Los tests PUEDEN usar subprocess para probar el CLI (patron estandar); el
target ``scripts/assemble_context.py`` NO usa subprocess (forbids del task
contract).
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import assemble_context as ac  # noqa: E402


def _write(d, name, content):
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(content)
    return p


def _node(name, tags, body):
    fm = "---\ntype: 'Concept'\ntitle: '{}'\ndescription: 'x'\ntags: {}\n---\n" \
        .format(name, tags)
    return fm + "# " + name + "\n\n" + body


# ---------------------------------------------------------------------------
# Funcion assemble()
# ---------------------------------------------------------------------------

class TestBudgetAndPriorities(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        os.makedirs(os.path.join(self.d, "knowledge"))
        # aaa (prio 0) cabe holgado; bbb (prio 10) es enorme y con none no recorta
        _write(self.d, "knowledge/aaa.md", _node("aaa", "['x']",
                "x" * 1000))  # ~250 tokens
        _write(self.d, "knowledge/bbb.md", _node("bbb", "['y']",
                "y" * 60000))  # ~15000 tokens, excede el remanente

    def tearDown(self):
        self.tmp.cleanup()

    def _contract(self):
        return {
            "budget": {"max_tokens": 2000, "output_reserve": 0},
            "slots": [
                {"id": "big", "source": "static", "path": "knowledge/aaa.md",
                 "compaction": "none", "max_tokens": 1800, "priority": 0},
                {"id": "small", "source": "static", "path": "knowledge/bbb.md",
                 "compaction": "none", "priority": 10},
            ],
        }

    def test_presupuesto_respetado(self):
        r = ac.assemble(self._contract(), "tarea", self.d)
        self.assertLessEqual(r["used"], r["available"])

    def test_prioridades_orden_y_omision(self):
        # prio 0 (big/aaa, none, max 1800): ~250 tokens < 1800 -> incluido.
        # prio 10 (small/bbb, none): remanente ~1750, contenido ~15000 tokens
        # -> con none no recorta y excede -> omitido. Confirma orden: el de
        # prioridad mas baja se lleva el presupuesto primero.
        r = ac.assemble(self._contract(), "tarea", self.d)
        by_id = {s["id"]: s for s in r["slots"]}
        self.assertEqual(by_id["big"]["status"], "included")
        self.assertEqual(by_id["small"]["status"], "omitted")
        self.assertLessEqual(r["used"], r["available"])


class TestTruncateAndMinTokens(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        os.makedirs(os.path.join(self.d, "knowledge"))
        _write(self.d, "knowledge/big.md", _node("big", "['t']",
                "abcdefghij " * 5000))  # ~60000 chars ~15000 tokens

    def tearDown(self):
        self.tmp.cleanup()

    def test_truncate_recorta_y_marca(self):
        contract = {
            "budget": {"max_tokens": 400, "output_reserve": 0},
            "slots": [
                {"id": "s", "source": "static", "path": "knowledge/big.md",
                 "compaction": "truncate", "max_tokens": 100, "priority": 0},
            ],
        }
        r = ac.assemble(contract, "tarea", self.d)
        s = r["slots"][0]
        self.assertEqual(s["status"], "included")
        self.assertLessEqual(s["tokens"], 100)  # respeta el tope
        self.assertIn(ac._TRUNC_MARKER, r["context"])

    def test_min_tokens_piso_omite(self):
        # cap = 100, min_tokens = 200 -> omitido pese a compaction truncate
        contract = {
            "budget": {"max_tokens": 100, "output_reserve": 0},
            "slots": [
                {"id": "s", "source": "static", "path": "knowledge/big.md",
                 "compaction": "truncate", "max_tokens": 100,
                 "min_tokens": 200, "priority": 0},
            ],
        }
        r = ac.assemble(contract, "tarea", self.d)
        self.assertEqual(r["slots"][0]["status"], "omitted")
        self.assertEqual(r["slots"][0]["tokens"], 0)


class TestSignAndDeterminism(unittest.TestCase):
    def test_firma_estable_y_sha12(self):
        contract = {
            "budget": {"max_tokens": 100000, "output_reserve": 0},
            "slots": [
                {"id": "spec", "source": "static",
                 "path": "knowledge/OKF-SPEC.md", "compaction": "none",
                 "sign": True, "priority": 0},
            ],
        }
        r1 = ac.assemble(contract, "t", ROOT)
        r2 = ac.assemble(contract, "t", ROOT)
        sign1 = r1["slots"][0]["sign"]
        sign2 = r2["slots"][0]["sign"]
        self.assertEqual(sign1, sign2)
        # sha256[:12] del contenido incluido
        import hashlib
        expected = hashlib.sha256(
            r1["context"].split("### slot: spec\n", 1)[1].encode("utf-8")
        ).hexdigest()[:12]
        self.assertEqual(sign1, expected)

    @unittest.skipUnless(
        os.path.isfile(os.path.join(ROOT, "knowledge", "data_models",
                                    "users_table.md")),
        "ejemplo removido por init: knowledge/data_models/users_table.md")
    def test_determinismo_dos_corridas(self):
        # Skip-guard preventivo (acoplamiento autorizado por C06): corre el
        # retriever sobre la KB real con la tarea "documentar la tabla users"
        # (nodo de ejemplo users_table). Post-init users_table se elimina,
        # pero el fallback del retriever preserva el determinismo; el guard es
        # preventivo (post-init nada falla aca) y se saltea limpio.
        contract = {
            "budget": {"max_tokens": 16000, "output_reserve": 3000},
            "slots": [
                {"id": "okf_spec", "source": "static",
                 "path": "knowledge/OKF-SPEC.md", "compaction": "none",
                 "sign": True, "priority": 0},
                {"id": "okf_index", "source": "dynamic",
                 "provider": "okf_index", "compaction": "none", "priority": 10},
                {"id": "okf_nodes", "source": "dynamic",
                 "provider": "okf_nodes", "compaction": "summarize",
                 "max_tokens": 6000, "priority": 20},
                {"id": "user_task", "source": "runtime",
                 "compaction": "truncate", "priority": 30},
            ],
            "guardrails": {
                "regex_deny": {"patterns": ["api_key="], "on_fail": "abort"},
                "reference_check": {"on_fail": "report"},
            },
        }
        r1 = ac.assemble(contract, "documentar la tabla users", ROOT)
        r2 = ac.assemble(contract, "documentar la tabla users", ROOT)
        a = json.dumps(r1, sort_keys=True)
        b = json.dumps(r2, sort_keys=True)
        self.assertEqual(a, b)
        self.assertEqual(r1["context"], r2["context"])


class TestRetriever(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        os.makedirs(os.path.join(self.d, "knowledge"))
        os.makedirs(os.path.join(self.d, "knowledge", "data_models"))
        _write(self.d, "knowledge/data_models/users_table.md",
               _node("users_table", "['data-model','users','example']",
                     "campos de users"))
        _write(self.d, "knowledge/architecture_overview.md",
               _node("architecture_overview", "['architecture','overview']",
                     "vista general"))
        _write(self.d, "knowledge/concept_zzz.md",
               _node("concept_zzz", "['zzztag']", "sin relacion"))
        _write(self.d, "knowledge/index.md",
               "# Index\n\n- [users](data_models/users_table.md)\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _nodes(self, task):
        contract = {
            "budget": {"max_tokens": 100000, "output_reserve": 0},
            "slots": [
                {"id": "n", "source": "dynamic", "provider": "okf_nodes",
                 "compaction": "summarize", "priority": 0},
            ],
        }
        r = ac.assemble(contract, task, self.d)
        return r["slots"][0]["selected"]

    def test_match_por_tag(self):
        # "users" es un tag de users_table -> match por tag
        sel = self._nodes("documentar la tabla users")
        self.assertIn("users_table", sel)

    def test_match_por_mencion(self):
        # nombre de archivo "architecture_overview" mencionado en la tarea
        sel = self._nodes("explicar architecture_overview del sistema")
        self.assertIn("architecture_overview", sel)
        self.assertNotIn("users_table", sel)

    def test_fallback_todos(self):
        sel = self._nodes("tarea sin relacion con nodos")
        # todos los .md de knowledge/ en orden alfabetico
        self.assertEqual(sel, sorted(sel))
        self.assertIn("users_table", sel)
        self.assertIn("architecture_overview", sel)
        self.assertIn("concept_zzz", sel)
        self.assertIn("index", sel)


class TestGuardrails(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        os.makedirs(os.path.join(self.d, "knowledge"))
        _write(self.d, "knowledge/index.md", "# Index\n")
        _write(self.d, "knowledge/real.md", _node("real", "['t']", "ok"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_regex_deny_aborta(self):
        contract = {
            "budget": {"max_tokens": 10000, "output_reserve": 0},
            "slots": [
                {"id": "task", "source": "runtime", "compaction": "none",
                 "priority": 0},
            ],
            "guardrails": {
                "regex_deny": {"patterns": ["api_key="], "on_fail": "abort"},
            },
        }
        with self.assertRaises(ac.GuardrailAbort):
            ac.assemble(contract, "mi api_key=secret123", self.d)

    def test_reference_check_detecta_inexistente(self):
        contract = {
            "budget": {"max_tokens": 10000, "output_reserve": 0},
            "slots": [
                {"id": "task", "source": "runtime", "compaction": "none",
                 "priority": 0},
            ],
            "guardrails": {"reference_check": {"on_fail": "report"}},
        }
        r = ac.assemble(contract, "revisar knowledge/no-existe.md", self.d)
        self.assertFalse(r["guardrails"]["ok"])
        joined = " ".join(r["guardrails"]["findings"])
        self.assertIn("knowledge/no-existe.md", joined)
        self.assertIn("reference_check", joined)

    def test_reference_check_pasa_con_existentes(self):
        contract = {
            "budget": {"max_tokens": 10000, "output_reserve": 0},
            "slots": [
                {"id": "task", "source": "runtime", "compaction": "none",
                 "priority": 0},
            ],
            "guardrails": {"reference_check": {"on_fail": "report"}},
        }
        r = ac.assemble(contract, "revisar knowledge/real.md", self.d)
        self.assertTrue(r["guardrails"]["ok"])
        self.assertEqual(r["guardrails"]["findings"], [])


class TestContractValidation(unittest.TestCase):
    def test_budget_ausente_lanza_valueerror(self):
        with self.assertRaises(ValueError):
            ac.assemble({"slots": []}, "t", ROOT)

    def test_max_tokens_no_positivo(self):
        with self.assertRaises(ValueError):
            ac.assemble({"budget": {"max_tokens": 0, "output_reserve": 0},
                         "slots": [{"id": "a", "source": "runtime",
                                    "priority": 0}]}, "t", ROOT)

    def test_slots_vacio(self):
        with self.assertRaises(ValueError):
            ac.assemble({"budget": {"max_tokens": 10, "output_reserve": 0},
                         "slots": []}, "t", ROOT)

    def test_static_sin_path(self):
        with self.assertRaises(ValueError):
            ac.assemble({"budget": {"max_tokens": 10, "output_reserve": 0},
                         "slots": [{"id": "a", "source": "static",
                                    "priority": 0}]}, "t", ROOT)


# ---------------------------------------------------------------------------
# CLI via subprocess (exit codes)
# ---------------------------------------------------------------------------

def _run_cli(args, cwd=ROOT):
    return subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "assemble_context.py")]
        + args,
        cwd=cwd, capture_output=True, text=True, encoding="utf-8",
    )


class TestCLIExitCodes(unittest.TestCase):
    def test_exit_0_ok(self):
        r = _run_cli(["ccdd/context.json", "documentar la tabla users"])
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        self.assertIn("guardrails: ok", r.stdout)

    def test_exit_2_contrato_invalido(self):
        with tempfile.TemporaryDirectory() as d:
            bad = _write(d, "bad.json",
                         json.dumps({"budget": {"max_tokens": 0,
                                                 "output_reserve": 0}}))
            r = _run_cli([bad, "t"], cwd=d)
        self.assertEqual(r.returncode, 2, msg=r.stdout + r.stderr)

    def test_exit_2_guardrail_abort(self):
        r = _run_cli(["ccdd/context.json", "mi api_key=secret123"])
        self.assertEqual(r.returncode, 2, msg=r.stdout + r.stderr)
        self.assertIn("ABORT", r.stderr)

    def test_exit_1_io_contrato_inexistente(self):
        r = _run_cli(["ccdd/no-existe.json", "t"])
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)

    def test_cli_determinismo_stdout(self):
        r1 = _run_cli(["ccdd/context.json", "documentar la tabla users"])
        r2 = _run_cli(["ccdd/context.json", "documentar la tabla users"])
        self.assertEqual(r1.stdout, r2.stdout)


if __name__ == "__main__":
    unittest.main()