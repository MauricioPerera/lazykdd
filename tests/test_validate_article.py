"""Oraculo congelado del contrato validate-article (Contrato 23).

Autorado por el orquestador ANTES de la delegacion. El implementador de
src/validate_article.py NO escribe ni modifica este archivo. Dominio:
knowledge/data_models/editorial_style.md.

Contrato:
    validate_article(article: dict, style: dict) -> list
article = {"title": str, "body": str, "seo_description": str}.
style = {"title_max": int, "words_min": int, "words_max": int,
         "h2_min": int, "h2_max": int, "seo_min": int, "seo_max": int,
         "paragraph_words_max": int,
         "forbidden_chars": [str], "forbidden_phrases": [str]}.
Devuelve violaciones legibles (vacia = conforme), cada una nombrando el campo
(title/body/seo_description). Acumula todas; pura; nunca lanza.

Definiciones exactas (congeladas aca):
- palabras = len(texto.split()).
- parrafo = bloque separado por linea en blanco; los headers (lineas que
  empiezan con '#') no cuentan como parrafo.
- H2 = linea que empieza con '## ' (H1 = linea que empieza con '# ').
- tabla markdown = alguna linea cuyo primer caracter no-espacio es '|'.
- frase prohibida: substring case-insensitive sobre el body.
- URL cruda: 'http://' o 'https://' que NO este inmediatamente precedido por
  '](' (la forma markdown [texto](url) es valida).
- seo_description: obligatoria; su largo en caracteres dentro de [seo_min, seo_max].
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from validate_article import validate_article


STYLE = {
    "title_max": 60,
    "words_min": 100, "words_max": 300,      # rangos chicos para fixtures manejables
    "h2_min": 2, "h2_max": 4,
    "seo_min": 20, "seo_max": 40,
    "paragraph_words_max": 80,
    "forbidden_chars": ["—"],            # em-dash
    "forbidden_phrases": ["robusto", "sinergias", "en el dinamico mundo de"],
}


def _body(words_per_par=40, pars=3, h2=2, extra=""):
    par = " ".join(["palabra"] * words_per_par)
    blocks = []
    for i in range(h2):
        blocks.append("## Seccion {}".format(i + 1))
        if i < pars:
            blocks.append(par)
    for i in range(h2, pars):
        blocks.append(par)
    if extra:
        blocks.append(extra)
    return "\n\n".join(blocks)


def _article(**overrides):
    a = {
        "title": "Un titulo claro y corto",
        "body": _body(),
        "seo_description": "Resumen claro para buscadores.",
    }
    a.update(overrides)
    return a


def _fields(violations):
    return {v.split(":", 1)[0].strip() for v in violations}


class TestConforme(unittest.TestCase):
    def test_articulo_conforme(self):
        self.assertEqual(validate_article(_article(), STYLE), [])

    def test_link_markdown_no_es_url_cruda(self):
        a = _article(body=_body(extra="Ver [el repo](https://github.com/x/y) para mas."))
        self.assertEqual(validate_article(a, STYLE), [])


class TestTitulo(unittest.TestCase):
    def test_titulo_ausente_o_vacio(self):
        for t in (None, ""):
            v = validate_article(_article(title=t), STYLE)
            self.assertIn("title", _fields(v))

    def test_titulo_sobre_el_tope(self):
        v = validate_article(_article(title="x" * 61), STYLE)
        self.assertEqual(_fields(v), {"title"})

    def test_titulo_en_el_tope_exacto_ok(self):
        self.assertEqual(validate_article(_article(title="x" * 60), STYLE), [])


class TestCuerpo(unittest.TestCase):
    def test_pocas_palabras(self):
        v = validate_article(_article(body=_body(words_per_par=10, pars=2)), STYLE)
        self.assertIn("body", _fields(v))

    def test_demasiadas_palabras(self):
        v = validate_article(_article(body=_body(words_per_par=79, pars=5, h2=3)), STYLE)
        self.assertIn("body", _fields(v))

    def test_em_dash_prohibido(self):
        a = _article(body=_body(extra="una pausa — dramatica"))
        v = validate_article(a, STYLE)
        self.assertIn("body", _fields(v))

    def test_frase_prohibida_case_insensitive(self):
        a = _article(body=_body(extra="un sistema Robusto y confiable"))
        v = validate_article(a, STYLE)
        self.assertIn("body", _fields(v))
        self.assertTrue(any("robusto" in x.lower() for x in v), v)

    def test_tabla_markdown_prohibida(self):
        a = _article(body=_body(extra="| a | b |\n|---|---|\n| 1 | 2 |"))
        v = validate_article(a, STYLE)
        self.assertIn("body", _fields(v))

    def test_h1_en_el_cuerpo_prohibido(self):
        a = _article(body="# Titulazo\n\n" + _body())
        v = validate_article(a, STYLE)
        self.assertIn("body", _fields(v))

    def test_h2_fuera_de_rango(self):
        v1 = validate_article(_article(body=_body(h2=1)), STYLE)
        self.assertIn("body", _fields(v1))
        v2 = validate_article(_article(body=_body(h2=5, pars=5)), STYLE)
        self.assertIn("body", _fields(v2))

    def test_url_cruda_prohibida(self):
        a = _article(body=_body(extra="mira https://example.com/x directo"))
        v = validate_article(a, STYLE)
        self.assertIn("body", _fields(v))

    def test_parrafo_sobre_el_tope_de_palabras(self):
        a = _article(body=_body(words_per_par=81, pars=2))
        v = validate_article(a, STYLE)
        self.assertIn("body", _fields(v))


class TestSeo(unittest.TestCase):
    def test_seo_ausente(self):
        v = validate_article(_article(seo_description=None), STYLE)
        self.assertIn("seo_description", _fields(v))

    def test_seo_fuera_de_rango(self):
        v1 = validate_article(_article(seo_description="corta"), STYLE)
        self.assertIn("seo_description", _fields(v1))
        v2 = validate_article(_article(seo_description="x" * 41), STYLE)
        self.assertIn("seo_description", _fields(v2))


class TestAcumulacionYRobustez(unittest.TestCase):
    def test_acumula_multiples(self):
        a = _article(title="x" * 61,
                     body=_body(extra="algo — robusto en https://x.com crudo"),
                     seo_description="corta")
        v = validate_article(a, STYLE)
        self.assertEqual(_fields(v), {"title", "body", "seo_description"})
        self.assertGreaterEqual(len(v), 4)

    def test_nunca_lanza_con_tipos_raros(self):
        for a in ({}, {"title": 5, "body": ["x"], "seo_description": {}},
                  {"title": "t", "body": None}):
            out = validate_article(a, STYLE)  # no debe lanzar
            self.assertIsInstance(out, list)
            self.assertGreaterEqual(len(out), 1)

    def test_determinista(self):
        a = _article(body=_body(extra="algo — robusto"))
        self.assertEqual(validate_article(a, STYLE), validate_article(a, STYLE))


if __name__ == "__main__":
    unittest.main()
