#!/usr/bin/env python3
"""Gate de perimetro (Contrato 28).

Validador determinista: dado un task contract (clave `touch_only`) y la lista
de archivos cambiados, falla si algo cayo fuera del perimetro. Parser mini-YAML
copiado identico de validate_contracts.py para garantizar coherencia.

Sin red, sin subprocess. Solo stdlib.
"""

import fnmatch
import os
import sys


# ---------------------------------------------------------------------------
# Parser YAML minimal (identico a validate_contracts.py)
# ---------------------------------------------------------------------------

def _split_inline_list(inner):
    """Parte el contenido entre [ ] respetando comillas simples/dobles."""
    items = []
    buf = []
    quote = None
    for ch in inner:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            buf.append(ch)
        elif ch == ',':
            items.append(''.join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    last = ''.join(buf).strip()
    if last:
        items.append(last)
    return items


def _parse_scalar(value):
    value = value.strip()
    if value.startswith('[') and value.endswith(']'):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item) for item in _split_inline_list(inner)]
    if len(value) >= 2 and value[0] in ("'", '"') and value[-1] == value[0]:
        return value[1:-1]
    return value


def _parse_block(lines, start, indent):
    """Parsea un bloque dict a partir de la linea `start` con indent `indent`.

    Devuelve (dict, indice_siguiente).
    """
    result = {}
    i = start
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        cur_indent = len(line) - len(line.lstrip(' '))
        if cur_indent < indent:
            break
        if cur_indent > indent:
            i += 1
            continue
        stripped = line.strip()
        if ':' not in stripped:
            i += 1
            continue
        key, _, value = stripped.partition(':')
        key = key.strip()
        value = value.strip()
        if value == '':
            j = i + 1
            child_indent = None
            while j < n:
                l = lines[j]
                if not l.strip():
                    j += 1
                    continue
                ci = len(l) - len(l.lstrip(' '))
                if ci <= indent:
                    break
                child_indent = ci
                break
            if child_indent is not None:
                child, j = _parse_block(lines, i + 1, child_indent)
                result[key] = child
                i = j
            else:
                result[key] = ''
                i += 1
        else:
            result[key] = _parse_scalar(value)
            i += 1
    return result, i


def parse_frontmatter(text):
    """Devuelve (dict, body_str) o (None, body) si no hay frontmatter valido."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        idx = 0
        while idx < len(lines) and not lines[idx].strip():
            idx += 1
        if idx >= len(lines) or lines[idx].strip() != '---':
            return None, text
        start = idx
    else:
        start = 0
    end = None
    for k in range(start + 1, len(lines)):
        if lines[k].strip() == '---':
            end = k
            break
    if end is None:
        return None, text
    fm_lines = lines[start + 1:end]
    body_lines = lines[end + 1:]
    data, _ = _parse_block(fm_lines, 0, 0)
    return data, '\n'.join(body_lines)


# ---------------------------------------------------------------------------
# Validacion del perimetro
# ---------------------------------------------------------------------------

def _normalize_path(p):
    """Normaliza ruta: backslashes a '/', quita './' al inicio, limpia lineas."""
    p = p.strip()
    if not p:
        return None
    p = p.replace('\\', '/')
    if p.startswith('./'):
        p = p[2:]
    return p if p else None


def _normalize_changed_files(changed_files):
    """Normaliza lista de cambiados: elimina vacios, duplicados, ordena."""
    normalized = []
    for cf in changed_files:
        norm = _normalize_path(cf)
        if norm:
            normalized.append(norm)
    return sorted(list(set(normalized)))


def _is_valid_touch_only(touch_only):
    """Verifica si touch_only es lista no vacia de strings no vacios."""
    if not isinstance(touch_only, list):
        return False
    if len(touch_only) == 0:
        return False
    for item in touch_only:
        if not isinstance(item, str) or len(item) == 0:
            return False
    return True


def _matches_any_pattern(path, patterns):
    """Devuelve True si path matchea alguno de los patrones (fnmatch posix)."""
    for pattern in patterns:
        if fnmatch.fnmatch(path, pattern):
            return True
    return False


def _finding(file_rel, rule, msg, level='ERROR'):
    """Construye un finding dict (mismo patron que validate_skills.py)."""
    return {'file': file_rel, 'level': level, 'rule': rule, 'msg': msg}


def _load_and_validate_touch_only(contract_path, file_rel):
    """Lee y parsea el contrato, valida touch_only. Devuelve (data, error_findings):
    `error_findings` es None si todo OK (y `data` es el frontmatter parseado), o la
    lista de EXACTAMENTE 1 finding a devolver de inmediato si hay un error (archivo
    no legible / frontmatter invalido / touch_only invalido) -- en ese caso `data` es
    None."""
    # Leer contrato
    try:
        with open(contract_path, 'r', encoding='utf-8') as fh:
            text = fh.read()
    except OSError:
        return None, [_finding(file_rel, 'FM_PARSE',
                               'contrato inexistente o no legible')]

    # Parsear frontmatter
    data, _body = parse_frontmatter(text)
    if data is None:
        return None, [_finding(
            file_rel, 'FM_PARSE',
            "frontmatter YAML no encontrado o no delimitado por '---'")]

    # Validar touch_only
    touch_only = data.get('touch_only')
    if not _is_valid_touch_only(touch_only):
        return None, [_finding(
            file_rel, 'TOUCH_ONLY_MISSING',
            'touch_only ausente, no-lista, vacia o con items no-string/vacios')]

    return data, None


def _check_changed_files(normalized, tests_path, target_path, touch_only,
                          file_rel):
    """Valida cada archivo cambiado: TESTS_TOUCHED (si es el oraculo Y tests !=
    target) o OUT_OF_PERIMETER (si no matchea ningun patron de touch_only). Logica
    identica al loop original, incluido el `continue` que evita doble-reporte del
    mismo archivo (TESTS_TOUCHED excluye OUT_OF_PERIMETER para ESE archivo)."""
    findings = []
    for changed in normalized:
        # Regla: TESTS_TOUCHED
        if changed == tests_path and tests_path != target_path:
            findings.append(_finding(
                file_rel, 'TESTS_TOUCHED',
                'el archivo {} (oraculo congelado) no debe cambiar '
                '(tests != target)'.format(changed)))
            continue  # No emitir OUT_OF_PERIMETER para este archivo

        # Regla: OUT_OF_PERIMETER
        if not _matches_any_pattern(changed, touch_only):
            findings.append(_finding(
                file_rel, 'OUT_OF_PERIMETER',
                'archivo {} fuera del perimetro touch_only'.format(changed)))
    return findings


def validate_perimeter(contract_path, changed_files):
    """Valida que los archivos cambiados estan dentro del perimetro touch_only.

    Args:
        contract_path: ruta al archivo .md del contrato
        changed_files: lista de rutas (normalizadas o no) que cambiaron

    Returns:
        lista de findings {'file','level','rule','msg'} ordenados por
        (file, rule, msg). 'file' es la ruta posix del contrato (relativa,
        tal como se la pasa).
    """
    file_rel = contract_path.replace('\\', '/')

    # Fase 1: leer contrato, parsear frontmatter y validar touch_only
    data, err = _load_and_validate_touch_only(contract_path, file_rel)
    if err is not None:
        return err

    # Fase 2: normalizar cambiados y validar cada uno contra el perimetro
    normalized = _normalize_changed_files(changed_files)
    if not normalized:
        return []

    touch_only = data.get('touch_only')
    tests_path = data.get('tests', '')
    target_path = data.get('target', '')
    findings = _check_changed_files(normalized, tests_path, target_path,
                                    touch_only, file_rel)

    # Ordenar por (file, rule, msg)
    findings.sort(key=lambda f: (f['file'], f['rule'], f['msg']))
    return findings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv):
    """CLI: python scripts/validate_perimeter.py <contract.md> [--changed f1 f2 ...]

    Sin --changed, lee los paths de stdin (uno por linea).
    Imprime findings y resumen. Exit 0 sin ERRORs, 1 con >=1.
    """
    if len(argv) < 1:
        print("Uso: python scripts/validate_perimeter.py <contract.md> [--changed f1 f2 ...]")
        return 1

    contract_path = argv[0]
    changed_files = []

    # Parsear argumentos
    if len(argv) > 1 and argv[1] == '--changed':
        changed_files = argv[2:]
    else:
        # Leer de stdin
        try:
            for line in sys.stdin:
                changed_files.append(line.rstrip('\n\r'))
        except EOFError:
            pass

    # Validar
    findings = validate_perimeter(contract_path, changed_files)

    # Imprimir findings
    errors = [f for f in findings if f['level'] == 'ERROR']
    for f in findings:
        print("{} [{}] {}: {}".format(f['level'], f['rule'], f['file'], f['msg']))

    # Imprimir resumen
    normalized_changed = _normalize_changed_files(changed_files)
    n_changed = len(normalized_changed)
    n_errors = len(errors)
    print("Resumen: {} error(es), {} archivo(s) cambiados".format(n_errors, n_changed))

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
