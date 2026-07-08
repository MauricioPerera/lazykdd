#!/usr/bin/env python3
"""Gate de UX/accesibilidad de paginas HTML (Contrato 30).

Valida propiedades mecanicas de HTML: balance de tags, i18n, contraste WCAG,
reduced-motion, IDs referenciados. Severidad calibrada contra google-labs-code/design.md:
referencias rotas=error, accesibilidad recomendada=warning.
"""

import html.parser
import json
import os
import re
import sys


VOID_ELEMENTS = {
    "meta", "link", "img", "br", "hr", "input", "area", "base", "col",
    "embed", "source", "track", "wbr"
}


def _check_tag_balance(html_content):
    """Retorna lista de findings para HTML_UNCLOSED."""
    findings = []
    stack = []

    class BalanceParser(html.parser.HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag.lower() not in VOID_ELEMENTS:
                stack.append(tag.lower())

        def handle_endtag(self, tag):
            tag = tag.lower()
            if not stack:
                findings.append({
                    "rule": "HTML_UNCLOSED",
                    "level": "ERROR",
                    "msg": f"cierre sin apertura: </{tag}>"
                })
            elif stack[-1] == tag:
                stack.pop()
            else:
                # Desapilamos hasta encontrarlo o vaciar
                expected = stack[-1]
                while stack and stack[-1] != tag:
                    stack.pop()
                if stack:
                    stack.pop()  # Sacamos el tag encontrado
                findings.append({
                    "rule": "HTML_UNCLOSED",
                    "level": "ERROR",
                    "msg": f"cierre desordenado: </{tag}> pero el tope era <{expected}>"
                })

    parser = BalanceParser()
    try:
        parser.feed(html_content)
    except Exception:
        # Si hay error de parsing, no es nuestro problema en este check
        pass

    if stack:
        tags_str = ", ".join(stack)
        findings.append({
            "rule": "HTML_UNCLOSED",
            "level": "ERROR",
            "msg": f"tag(s) sin cerrar al final: {tags_str}"
        })

    return findings


def _check_i18n(html_content):
    """Retorna lista de findings para I18N_*."""
    findings = []

    # Extraer valores de data-i18n y data-i18n-html
    data_i18n_pattern = r'data-i18n(?:-html)?="([^"]*)"'
    keys_used = set()
    for match in re.finditer(data_i18n_pattern, html_content):
        keys_used.add(match.group(1))

    if not keys_used:
        return findings

    # Buscar bloque i18n-data
    script_pattern = r'<script[^>]*id="i18n-data"[^>]*type="application/json"[^>]*>(.+?)</script>'
    script_match = re.search(script_pattern, html_content, re.S | re.I)
    if not script_match:
        script_pattern = r'<script[^>]*type="application/json"[^>]*id="i18n-data"[^>]*>(.+?)</script>'
        script_match = re.search(script_pattern, html_content, re.S | re.I)

    if not script_match:
        findings.append({
            "rule": "I18N_DATA_MISSING",
            "level": "ERROR",
            "msg": 'hay atributos data-i18n pero no existe el bloque <script id="i18n-data">'
        })
        return findings

    json_content = script_match.group(1).strip()
    try:
        i18n_data = json.loads(json_content)
    except json.JSONDecodeError:
        findings.append({
            "rule": "I18N_DATA_INVALID",
            "level": "ERROR",
            "msg": "el bloque #i18n-data no es JSON valido"
        })
        return findings

    if not isinstance(i18n_data, dict) or not i18n_data:
        findings.append({
            "rule": "I18N_DATA_INVALID",
            "level": "ERROR",
            "msg": "el bloque #i18n-data no es un objeto no vacio"
        })
        return findings

    # Verificar que cada clave existe en cada idioma
    for key in keys_used:
        for lang in i18n_data.keys():
            if not isinstance(i18n_data[lang], dict) or key not in i18n_data[lang]:
                findings.append({
                    "rule": "I18N_MISSING",
                    "level": "ERROR",
                    "msg": f"clave '{key}' ausente en el idioma '{lang}'"
                })

    return findings


def _check_ids(html_content):
    """Retorna lista de findings para ID_UNRESOLVED."""
    findings = []

    # Extraer IDs reales
    id_pattern = r'id="([^"]*)"'
    real_ids = set()
    for match in re.finditer(id_pattern, html_content):
        real_ids.add(match.group(1))

    # Extraer IDs referenciados por JavaScript
    referenced_ids = set()

    # getElementById('x') o getElementById("x")
    getelementbyid_pattern = r"getElementById\(['\"]([^'\"]+)['\"]\)"
    for match in re.finditer(getelementbyid_pattern, html_content):
        referenced_ids.add(match.group(1))

    # querySelector('#x') o querySelector("#x")
    queryselector_pattern = r"querySelector\(['\"]#([^'\"]+)['\"]\)"
    for match in re.finditer(queryselector_pattern, html_content):
        referenced_ids.add(match.group(1))

    # Verificar que todos los IDs referenciados existan
    for ref_id in referenced_ids:
        if ref_id not in real_ids:
            findings.append({
                "rule": "ID_UNRESOLVED",
                "level": "ERROR",
                "msg": f"id referenciado no existe: {ref_id}"
            })

    return findings


def _hex_to_rgb(hex_color):
    """Convierte hex a RGB. Soporta #rgb y #rrggbb."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    if len(hex_color) != 6:
        return None
    try:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _relative_luminance(rgb):
    """Calcula luminancia relativa WCAG con corrección gamma sRGB."""
    r, g, b = [x / 255.0 for x in rgb]

    def correct(s):
        if s <= 0.03928:
            return s / 12.92
        return ((s + 0.055) / 1.055) ** 2.4

    r = correct(r)
    g = correct(g)
    b = correct(b)

    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(rgb1, rgb2):
    """Calcula ratio de contraste WCAG."""
    l1 = _relative_luminance(rgb1)
    l2 = _relative_luminance(rgb2)

    l_max = max(l1, l2)
    l_min = min(l1, l2)

    return (l_max + 0.05) / (l_min + 0.05)


def _check_contrast(html_content):
    """Retorna lista de findings para CONTRAST_*."""
    findings = []

    # Buscar bloque ux-contrast-pairs
    script_pattern = r'<script[^>]*id="ux-contrast-pairs"[^>]*type="application/json"[^>]*>(.+?)</script>'
    script_match = re.search(script_pattern, html_content, re.S | re.I)
    if not script_match:
        script_pattern = r'<script[^>]*type="application/json"[^>]*id="ux-contrast-pairs"[^>]*>(.+?)</script>'
        script_match = re.search(script_pattern, html_content, re.S | re.I)

    if not script_match:
        # No existe el bloque, no hay nada que chequear (opt-in)
        return findings

    json_content = script_match.group(1).strip()
    try:
        pairs = json.loads(json_content)
    except json.JSONDecodeError:
        findings.append({
            "rule": "CONTRAST_DATA_INVALID",
            "level": "ERROR",
            "msg": "el bloque #ux-contrast-pairs no es JSON valido"
        })
        return findings

    if not isinstance(pairs, list):
        findings.append({
            "rule": "CONTRAST_DATA_INVALID",
            "level": "ERROR",
            "msg": "el bloque #ux-contrast-pairs no es una lista"
        })
        return findings

    hex_pattern = r'^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$'

    for i, entry in enumerate(pairs):
        if not isinstance(entry, dict):
            scope = entry.get("scope", f"entrada {i}") if isinstance(entry, dict) else f"entrada {i}"
            findings.append({
                "rule": "CONTRAST_DATA_INVALID",
                "level": "ERROR",
                "msg": f"entrada {scope} no es un objeto"
            })
            continue

        text_hex = entry.get("text")
        bg_hex = entry.get("bg")
        scope = entry.get("scope", f"entrada {i}")

        if not text_hex or not bg_hex:
            findings.append({
                "rule": "CONTRAST_DATA_INVALID",
                "level": "ERROR",
                "msg": f"entrada {scope}: falta 'text' o 'bg'"
            })
            continue

        if not isinstance(text_hex, str) or not isinstance(bg_hex, str):
            findings.append({
                "rule": "CONTRAST_DATA_INVALID",
                "level": "ERROR",
                "msg": f"entrada {scope}: 'text' o 'bg' no son strings"
            })
            continue

        if not re.match(hex_pattern, text_hex) or not re.match(hex_pattern, bg_hex):
            findings.append({
                "rule": "CONTRAST_DATA_INVALID",
                "level": "ERROR",
                "msg": f"entrada {scope}: hex invalido"
            })
            continue

        rgb_text = _hex_to_rgb(text_hex)
        rgb_bg = _hex_to_rgb(bg_hex)

        if rgb_text is None or rgb_bg is None:
            findings.append({
                "rule": "CONTRAST_DATA_INVALID",
                "level": "ERROR",
                "msg": f"entrada {scope}: no se pudo parsear hex"
            })
            continue

        ratio = _contrast_ratio(rgb_text, rgb_bg)
        if ratio < 4.5:
            findings.append({
                "rule": "CONTRAST_LOW",
                "level": "WARNING",
                "msg": f"contraste bajo en {scope}: ratio {ratio:.2f}:1 entre {text_hex} y {bg_hex}"
            })

    return findings


def _check_motion(html_content):
    """Retorna lista de findings para MOTION_UNGUARDED."""
    findings = []

    # Extraer todos los <style>...</style>
    style_pattern = r'<style[^>]*>(.+?)</style>'
    css_content = ""
    for match in re.finditer(style_pattern, html_content, re.S | re.I):
        css_content += match.group(1) + "\n"

    if not css_content:
        return findings

    # Buscar @keyframes, animation: o transition:
    has_animation = bool(re.search(r'@keyframes', css_content, re.I))
    has_animation = has_animation or bool(re.search(r'animation\s*:', css_content, re.I))
    has_animation = has_animation or bool(re.search(r'transition\s*:', css_content, re.I))

    if not has_animation:
        return findings

    # Buscar guarda @media (prefers-reduced-motion: reduce)
    has_guard = bool(re.search(r'@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)', css_content, re.I))

    if not has_guard:
        findings.append({
            "rule": "MOTION_UNGUARDED",
            "level": "WARNING",
            "msg": "CSS contiene animacion sin guarda @media (prefers-reduced-motion: reduce)"
        })

    return findings


def validate_ux_page(html_path):
    """Valida una pagina HTML y retorna lista de findings ordenados."""
    findings = []

    # Intentar leer el archivo
    try:
        with open(html_path, 'r', encoding='utf-8') as fh:
            html_content = fh.read()
    except OSError as e:
        return [{
            "file": html_path.replace('\\', '/'),
            "level": "ERROR",
            "rule": "FILE_ERROR",
            "msg": str(e)
        }]

    # Correr los checks
    findings.extend(_check_tag_balance(html_content))
    findings.extend(_check_i18n(html_content))
    findings.extend(_check_ids(html_content))
    findings.extend(_check_contrast(html_content))
    findings.extend(_check_motion(html_content))

    # Agregar la clave 'file' a cada finding
    for f in findings:
        f['file'] = html_path.replace('\\', '/')

    # Ordenar por (rule, msg)
    findings.sort(key=lambda f: (f['rule'], f['msg']))

    return findings


def main(argv):
    """Escanea paths y reporta findings. Exit 1 si hay ERRORs, 0 si no."""
    if not argv:
        argv = ['examples/ux-page']

    all_findings = []
    html_count = 0
    paths_to_scan = []

    # Recopilar todos los paths a escanear
    for path in argv:
        if not os.path.exists(path):
            all_findings.append({
                "file": path,
                "level": "INFO",
                "rule": "PATH_MISSING",
                "msg": f"path no existe: {path}"
            })
            continue

        if os.path.isdir(path):
            # Escanear recursivamente
            found_html = False
            for root, dirs, files in os.walk(path):
                html_files = sorted([f for f in files if f.lower().endswith('.html')])
                for html_file in html_files:
                    found_html = True
                    full_path = os.path.join(root, html_file)
                    paths_to_scan.append(full_path)

            if not found_html:
                all_findings.append({
                    "file": path,
                    "level": "INFO",
                    "rule": "PATH_MISSING",
                    "msg": f"no hay archivos .html en: {path}"
                })
        else:
            paths_to_scan.append(path)

    # Validar cada archivo
    for html_path in paths_to_scan:
        findings = validate_ux_page(html_path)
        all_findings.extend(findings)
        html_count += 1

    # Imprimir todos los findings
    for f in all_findings:
        print("{} [{}] {}: {}".format(f['level'], f['rule'], f['file'], f['msg']))

    # Contar errores y warnings
    error_count = sum(1 for f in all_findings if f['level'] == 'ERROR')
    warning_count = sum(1 for f in all_findings if f['level'] == 'WARNING')

    print()
    print("Resumen: {} error(es), {} warning(s), {} archivo(s) HTML escaneados".format(
        error_count, warning_count, html_count
    ))

    return 1 if error_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
