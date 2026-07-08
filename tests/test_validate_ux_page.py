"""Oraculo congelado del gate de UX/accesibilidad de paginas HTML (Contrato 30).

Fija el comportamiento de ``scripts/validate_ux_page.py``. Diseno calibrado
contra un tercero real de produccion (google-labs-code/design.md, 25k stars):
formula WCAG independientemente verificada contra la suya; severidad
(contrast/motion = WARNING, referencias rotas = ERROR) calibrada contra su
precedente real (solo `broken-ref` es error en su linter).

  API: ``def validate_ux_page(html_path) -> list`` — findings
  ``{'file','level','rule','msg'}`` ordenados por (rule, msg); ``file`` es
  ``html_path`` normalizado a posix ('/').

  Checks y severidad EXACTA:
    HTML_UNCLOSED (ERROR)         balance/anidamiento de tags (html.parser;
                                  elementos void auto-cerrados no cuentan).
    I18N_DATA_MISSING (ERROR)     hay atributos data-i18n/data-i18n-html en
                                  el HTML pero no existe
                                  <script id="i18n-data" type="application/json">.
    I18N_DATA_INVALID (ERROR)     el bloque #i18n-data existe pero no es JSON
                                  valido, o no es un objeto {idioma: {...}}
                                  no vacio.
    I18N_MISSING (ERROR)          una clave data-i18n usada en el HTML no
                                  existe en uno o mas de los idiomas
                                  declarados en #i18n-data.
    ID_UNRESOLVED (ERROR)         un id referenciado por
                                  getElementById('x') o querySelector('#x')
                                  (extraccion best-effort por regex) no
                                  existe como id="x" en el HTML.
                                  querySelector con selector de clase/tag
                                  (sin '#') se ignora.
    CONTRAST_DATA_INVALID (ERROR) el bloque opcional
                                  <script id="ux-contrast-pairs"> existe pero
                                  no es JSON valido, no es una lista, o una
                                  entrada no tiene 'text'/'bg' como hex
                                  validos (#rgb o #rrggbb). Ausencia total del
                                  bloque NO es error (capa opt-in): sin el
                                  bloque, el check de contraste no produce
                                  ningun finding.
    CONTRAST_LOW (WARNING)        un par valido del bloque anterior tiene
                                  ratio WCAG < 4.5:1 (formula: luminancia
                                  relativa con correccion gamma sRGB,
                                  (L_claro+0.05)/(L_oscuro+0.05)). El msg
                                  incluye el 'scope', el ratio con 2
                                  decimales, y los dos hex.
    MOTION_UNGUARDED (WARNING)    el CSS dentro de <style> declara
                                  @keyframes, `animation:` o `transition:`
                                  sin una guarda
                                  @media (prefers-reduced-motion: reduce).
                                  Sin <style>, o sin animacion alguna en el
                                  CSS: sin finding.
    FILE_ERROR (ERROR)            el archivo no se pudo leer; unico caso
                                  donde las demas reglas se omiten.

  Exit code (main): 1 si hay >=1 finding ERROR; WARNING nunca bloquea (mismo
  precedente que FM_KEY_forbids en validate_contracts.py desde el C10).

  CLI: ``main(argv) -> int``. ``argv`` es una lista de paths (archivo o
  directorio); default ``['examples/ux-page']`` si argv esta vacio. Un
  directorio se escanea recursivamente por ``*.html`` (case-insensitive).
  Path inexistente, o directorio sin ningun .html -> finding INFO
  ``PATH_MISSING`` (capa opcional, no cuenta para el exit code). Imprime cada
  finding y termina con
  ``Resumen: N error(es), M warning(s), K archivo(s) HTML escaneados``
  (K = archivos HTML efectivamente encontrados y analizados).

Este archivo es un ORACULO CONGELADO (tests_sha256): el implementador no lo
modifica. Ver knowledge/contracts/ux-page-gate.md.
"""

import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import validate_ux_page as uxp  # noqa: E402


I18N_OK = (
    '<script type="application/json" id="i18n-data">'
    '{"en": {"hello": "Hello"}, "es": {"hello": "Hola"}}'
    "</script>"
)


def _wrap(body, extra_head=""):
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\">" + extra_head +
        "</head><body>" + body + "</body></html>"
    )


class _Fixture(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="c30_")
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)

    def _write(self, name, content):
        p = os.path.join(self.base, name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(content)
        return p

    def _rules(self, findings, level=None):
        if level is None:
            return sorted(f["rule"] for f in findings)
        return sorted(f["rule"] for f in findings if f["level"] == level)


class TestTagBalance(_Fixture):
    def test_html_valido_sin_findings(self):
        p = self._write("ok.html", _wrap("<div><span>x</span></div>"))
        self.assertEqual(uxp.validate_ux_page(p), [])

    def test_void_elements_no_disparan(self):
        p = self._write(
            "void.html",
            _wrap('<div><img src="x.png"><br><hr></div>'),
        )
        self.assertEqual(uxp.validate_ux_page(p), [])

    def test_tag_sin_cerrar_al_final(self):
        p = self._write("unclosed.html", _wrap("<div><span>x</div>"))
        findings = uxp.validate_ux_page(p)
        rules = self._rules(findings)
        self.assertIn("HTML_UNCLOSED", rules)
        self.assertTrue(any("span" in f["msg"] for f in findings))

    def test_cierre_desordenado(self):
        p = self._write(
            "disorder.html",
            _wrap("<div><a><b>x</b></a></div><p></span>"),
        )
        findings = uxp.validate_ux_page(p)
        self.assertIn("HTML_UNCLOSED", self._rules(findings))


class TestI18n(_Fixture):
    def test_sin_data_i18n_sin_findings(self):
        p = self._write("plain.html", _wrap("<p>hola</p>"))
        self.assertEqual(uxp.validate_ux_page(p), [])

    def test_completo_sin_findings(self):
        p = self._write(
            "i18n_ok.html",
            _wrap('<p data-i18n="hello">Hello</p>', I18N_OK),
        )
        self.assertEqual(uxp.validate_ux_page(p), [])

    def test_data_i18n_html_tambien_cuenta(self):
        p = self._write(
            "i18n_html.html",
            _wrap('<p data-i18n-html="hello">Hello</p>', I18N_OK),
        )
        self.assertEqual(uxp.validate_ux_page(p), [])

    def test_falta_bloque_i18n_data(self):
        p = self._write("i18n_missing.html", _wrap('<p data-i18n="hello">Hello</p>'))
        findings = uxp.validate_ux_page(p)
        self.assertEqual(self._rules(findings), ["I18N_DATA_MISSING"])
        self.assertEqual(findings[0]["level"], "ERROR")

    def test_bloque_i18n_data_json_invalido(self):
        p = self._write(
            "i18n_bad.html",
            _wrap(
                '<p data-i18n="hello">Hello</p>',
                '<script type="application/json" id="i18n-data">{not json}</script>',
            ),
        )
        findings = uxp.validate_ux_page(p)
        self.assertEqual(self._rules(findings), ["I18N_DATA_INVALID"])

    def test_bloque_i18n_data_no_es_objeto(self):
        p = self._write(
            "i18n_list.html",
            _wrap(
                '<p data-i18n="hello">Hello</p>',
                '<script type="application/json" id="i18n-data">[]</script>',
            ),
        )
        findings = uxp.validate_ux_page(p)
        self.assertEqual(self._rules(findings), ["I18N_DATA_INVALID"])

    def test_clave_ausente_en_un_idioma(self):
        p = self._write(
            "i18n_gap.html",
            _wrap(
                '<p data-i18n="hello">Hi</p><p data-i18n="bye">Bye</p>',
                '<script type="application/json" id="i18n-data">'
                '{"en": {"hello": "Hi", "bye": "Bye"}, "es": {"hello": "Hola"}}'
                "</script>",
            ),
        )
        findings = uxp.validate_ux_page(p)
        errs = [f for f in findings if f["level"] == "ERROR"]
        self.assertEqual(len(errs), 1, errs)
        self.assertEqual(errs[0]["rule"], "I18N_MISSING")
        self.assertIn("bye", errs[0]["msg"])
        self.assertIn("es", errs[0]["msg"])


class TestIds(_Fixture):
    def test_get_element_by_id_resuelve(self):
        body = '<div id="target"></div><script>document.getElementById("target");</script>'
        p = self._write("id_ok.html", _wrap(body))
        self.assertEqual(uxp.validate_ux_page(p), [])

    def test_get_element_by_id_no_resuelve(self):
        body = '<script>document.getElementById("ghost");</script>'
        p = self._write("id_ghost.html", _wrap(body))
        findings = uxp.validate_ux_page(p)
        self.assertEqual(self._rules(findings), ["ID_UNRESOLVED"])
        self.assertIn("ghost", findings[0]["msg"])

    def test_query_selector_id_resuelve(self):
        body = '<div id="panel"></div><script>document.querySelector("#panel");</script>'
        p = self._write("qs_ok.html", _wrap(body))
        self.assertEqual(uxp.validate_ux_page(p), [])

    def test_query_selector_id_no_resuelve(self):
        body = '<script>document.querySelector("#missing");</script>'
        p = self._write("qs_ghost.html", _wrap(body))
        findings = uxp.validate_ux_page(p)
        self.assertEqual(self._rules(findings), ["ID_UNRESOLVED"])
        self.assertIn("missing", findings[0]["msg"])

    def test_query_selector_de_clase_se_ignora(self):
        body = '<script>document.querySelector(".card"); document.querySelector("div");</script>'
        p = self._write("qs_class.html", _wrap(body))
        self.assertEqual(uxp.validate_ux_page(p), [])


class TestContrast(_Fixture):
    def _page(self, pairs_json):
        return _wrap(
            "<p>x</p>",
            '<script type="application/json" id="ux-contrast-pairs">'
            + pairs_json + "</script>",
        )

    def test_sin_bloque_sin_findings(self):
        p = self._write("no_pairs.html", _wrap("<p>x</p>"))
        self.assertEqual(uxp.validate_ux_page(p), [])

    def test_par_valido_alto_contraste(self):
        p = self._write(
            "high.html",
            self._page('[{"scope": "root", "text": "#000000", "bg": "#ffffff"}]'),
        )
        self.assertEqual(uxp.validate_ux_page(p), [])

    def test_par_identico_bajo_contraste(self):
        p = self._write(
            "low.html",
            self._page('[{"scope": "dark", "text": "#808080", "bg": "#808080"}]'),
        )
        findings = uxp.validate_ux_page(p)
        self.assertEqual(len(findings), 1, findings)
        f = findings[0]
        self.assertEqual(f["rule"], "CONTRAST_LOW")
        self.assertEqual(f["level"], "WARNING")
        self.assertIn("dark", f["msg"])
        self.assertIn("1.00", f["msg"])

    def test_json_invalido(self):
        p = self._write("bad_json.html", self._page("{not json"))
        findings = uxp.validate_ux_page(p)
        self.assertEqual(self._rules(findings), ["CONTRAST_DATA_INVALID"])
        self.assertEqual(findings[0]["level"], "ERROR")

    def test_no_es_lista(self):
        p = self._write("not_list.html", self._page('{"scope": "root"}'))
        findings = uxp.validate_ux_page(p)
        self.assertEqual(self._rules(findings), ["CONTRAST_DATA_INVALID"])

    def test_entrada_sin_hex_valido(self):
        p = self._write(
            "bad_hex.html",
            self._page('[{"scope": "root", "text": "notacolor", "bg": "#ffffff"}]'),
        )
        findings = uxp.validate_ux_page(p)
        self.assertEqual(self._rules(findings), ["CONTRAST_DATA_INVALID"])

    def test_multiples_pares_mezcla_ok_y_low(self):
        p = self._write(
            "mixed.html",
            self._page(
                '[{"scope": "root", "text": "#000000", "bg": "#ffffff"},'
                ' {"scope": "dark", "text": "#111111", "bg": "#151515"}]'
            ),
        )
        findings = uxp.validate_ux_page(p)
        self.assertEqual(self._rules(findings, "WARNING"), ["CONTRAST_LOW"])
        self.assertEqual(len(findings), 1)


class TestMotion(_Fixture):
    def test_sin_style_sin_findings(self):
        p = self._write("no_style.html", _wrap("<p>x</p>"))
        self.assertEqual(uxp.validate_ux_page(p), [])

    def test_style_sin_animacion_sin_findings(self):
        p = self._write(
            "static.html",
            "<html><head><style>p{color:red;}</style></head><body>x</body></html>",
        )
        self.assertEqual(uxp.validate_ux_page(p), [])

    def test_keyframes_sin_guarda(self):
        html = (
            "<html><head><style>"
            "@keyframes spin{from{opacity:0}to{opacity:1}}"
            "</style></head><body>x</body></html>"
        )
        p = self._write("anim_unguarded.html", html)
        findings = uxp.validate_ux_page(p)
        self.assertEqual(self._rules(findings), ["MOTION_UNGUARDED"])
        self.assertEqual(findings[0]["level"], "WARNING")

    def test_transition_sin_guarda(self):
        html = (
            "<html><head><style>.a{transition: all .2s ease;}</style>"
            "</head><body>x</body></html>"
        )
        p = self._write("trans_unguarded.html", html)
        self.assertEqual(self._rules(uxp.validate_ux_page(p)), ["MOTION_UNGUARDED"])

    def test_animacion_con_guarda_sin_findings(self):
        html = (
            "<html><head><style>"
            "@keyframes spin{from{opacity:0}to{opacity:1}}"
            ".a{animation: spin 1s;}"
            "@media (prefers-reduced-motion: reduce){.a{animation-duration:.001s}}"
            "</style></head><body>x</body></html>"
        )
        p = self._write("anim_guarded.html", html)
        self.assertEqual(uxp.validate_ux_page(p), [])


class TestAggregationAndFile(_Fixture):
    def test_file_key_posix_normalizado(self):
        p = self._write("sub.html", _wrap("<p>x</p>"))
        p_bad = self._write("bad.html", _wrap("<div>"))
        findings = uxp.validate_ux_page(p_bad)
        self.assertTrue(all("\\" not in f["file"] for f in findings))

    def test_archivo_inexistente_file_error(self):
        findings = uxp.validate_ux_page(os.path.join(self.base, "no-existe.html"))
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "FILE_ERROR")
        self.assertEqual(findings[0]["level"], "ERROR")

    def test_ordenado_por_rule_y_msg(self):
        html = (
            "<html><head><style>@keyframes k{}</style></head>"
            '<body><div><script>document.getElementById("a");'
            'document.getElementById("b");</script></body></html>'
        )
        p = self._write("multi.html", html)
        findings = uxp.validate_ux_page(p)
        keys = [(f["rule"], f["msg"]) for f in findings]
        self.assertEqual(keys, sorted(keys))

    def test_determinismo(self):
        p = self._write("det.html", _wrap("<div>"))
        self.assertEqual(uxp.validate_ux_page(p), uxp.validate_ux_page(p))


class TestCli(_Fixture):
    def test_directorio_limpio_exit_0(self):
        d = os.path.join(self.base, "site")
        os.makedirs(d)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(_wrap("<p>ok</p>"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = uxp.main([d])
        self.assertEqual(code, 0)
        self.assertIn("0 error(es)", out.getvalue())
        self.assertIn("1 archivo(s)", out.getvalue())

    def test_solo_warning_no_bloquea_exit_code(self):
        d = os.path.join(self.base, "warnonly")
        os.makedirs(d)
        html = (
            "<html><head><style>@keyframes k{from{opacity:0}to{opacity:1}}"
            ".a{animation:k 1s}</style></head><body>x</body></html>"
        )
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(html)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = uxp.main([d])
        self.assertEqual(code, 0)
        self.assertIn("MOTION_UNGUARDED", out.getvalue())
        self.assertIn("1 warning(s)", out.getvalue())

    def test_error_bloquea_exit_1(self):
        d = os.path.join(self.base, "broken")
        os.makedirs(d)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(_wrap("<div>"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = uxp.main([d])
        self.assertEqual(code, 1)
        self.assertIn("HTML_UNCLOSED", out.getvalue())

    def test_path_inexistente_info_exit_0(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = uxp.main([os.path.join(self.base, "no-existe")])
        self.assertEqual(code, 0)
        self.assertIn("PATH_MISSING", out.getvalue())

    def test_directorio_sin_html_info_exit_0(self):
        d = os.path.join(self.base, "empty")
        os.makedirs(d)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = uxp.main([d])
        self.assertEqual(code, 0)
        self.assertIn("PATH_MISSING", out.getvalue())

    def test_default_argv_usa_examples_ux_page(self):
        old_cwd = os.getcwd()
        os.chdir(self.base)
        try:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = uxp.main([])
            self.assertEqual(code, 0)
            self.assertIn("examples/ux-page", out.getvalue().replace("\\", "/"))
        finally:
            os.chdir(old_cwd)


class TestRepoReal(unittest.TestCase):
    """El gate custodia el ejemplo REAL: pasa limpio (0 errores)."""

    def test_ejemplo_real_sin_errores(self):
        d = os.path.join(ROOT, "examples", "ux-page")
        if not os.path.isdir(d):
            self.skipTest("examples/ux-page aun no existe (capa opcional)")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = uxp.main([d])
        self.assertEqual(code, 0, out.getvalue())


if __name__ == "__main__":
    unittest.main()
