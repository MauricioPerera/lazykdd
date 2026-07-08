"""Target validate-article (Contrato 23).

Valida un articulo contra una tabla de estilo editorial.
Devuelve lista de violaciones (vacia = conforme); nunca lanza.
"""

import re


def validate_article(article: dict, style: dict) -> list:
    """Valida article contra style y devuelve violaciones (lista vacia = conforme).

    Acumula todas las violaciones; pura; determinista; nunca lanza.
    """
    violations = []

    # === TITLE ===
    try:
        title = article.get("title") if isinstance(article, dict) else None
        if not title:  # None o vacio
            violations.append("title: obligatorio")
        elif isinstance(title, str):
            title_max = style.get("title_max", float("inf"))
            if len(title) > title_max:
                violations.append("title: largo mayor a limite")
        else:
            violations.append("title: debe ser string")
    except Exception:
        violations.append("title: error en validacion")

    # === BODY ===
    try:
        body = article.get("body") if isinstance(article, dict) else None
        if body is None:
            violations.append("body: obligatoria")
        elif isinstance(body, str):
            # Contar palabras
            word_count = len(body.split())
            words_min = style.get("words_min", 0)
            words_max = style.get("words_max", float("inf"))
            if not (words_min <= word_count <= words_max):
                violations.append("body: palabras fuera de rango")

            # Verificar caracteres prohibidos
            forbidden_chars = style.get("forbidden_chars", [])
            if forbidden_chars:
                for char in forbidden_chars:
                    if char in body:
                        violations.append("body: contiene caracter prohibido")
                        break

            # Verificar frases prohibidas (case-insensitive)
            forbidden_phrases = style.get("forbidden_phrases", [])
            if forbidden_phrases:
                body_lower = body.lower()
                for phrase in forbidden_phrases:
                    if phrase.lower() in body_lower:
                        violations.append(f"body: contiene frase prohibida ({phrase})")
                        break

            # Verificar tablas markdown (linea cuyo primer caracter no-espacio es '|')
            for line in body.split('\n'):
                if line.lstrip().startswith('|'):
                    violations.append("body: contiene tabla markdown")
                    break

            # Verificar H1 y contar H2
            h1_found = False
            h2_count = 0
            for line in body.split('\n'):
                if line.startswith('# '):
                    h1_found = True
                    break
                elif line.startswith('## '):
                    h2_count += 1

            if h1_found:
                violations.append("body: contiene H1")

            h2_min = style.get("h2_min", 0)
            h2_max = style.get("h2_max", float("inf"))
            if not (h2_min <= h2_count <= h2_max):
                violations.append("body: H2 fuera de rango")

            # Verificar URLs crudas
            # URL cruda = http(s):// no precedida por ']('
            if re.search(r'(?<!\]\()https?://', body):
                violations.append("body: contiene URL cruda")

            # Verificar parrafos (bloques separados por '\n\n')
            # Los headers no cuentan como parrafo
            paragraph_words_max = style.get("paragraph_words_max", float("inf"))
            paragraphs = body.split('\n\n')
            for par in paragraphs:
                # Ignorar bloques que son solo headers
                if par.lstrip().startswith('#'):
                    continue
                # Contar palabras del parrafo
                par_word_count = len(par.split())
                if par_word_count > paragraph_words_max:
                    violations.append("body: parrafo excede limite de palabras")
                    break
        else:
            violations.append("body: debe ser string")
    except Exception:
        violations.append("body: error en validacion")

    # === SEO_DESCRIPTION ===
    try:
        seo = article.get("seo_description") if isinstance(article, dict) else None
        if seo is None or seo == "":
            violations.append("seo_description: obligatoria")
        elif isinstance(seo, str):
            seo_len = len(seo)
            seo_min = style.get("seo_min", 0)
            seo_max = style.get("seo_max", float("inf"))
            if not (seo_min <= seo_len <= seo_max):
                violations.append("seo_description: largo fuera de rango")
        else:
            violations.append("seo_description: debe ser string")
    except Exception:
        violations.append("seo_description: error en validacion")

    return violations
