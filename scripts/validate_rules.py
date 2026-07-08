#!/usr/bin/env python3
"""Validador determinista de rule contracts (Contrato 18).

Sin LLM, sin red, sin subprocess. Solo stdlib. Escanea *.rules.json en un directorio
y valida estructura (familias conocidas), golden (presente, archivo existe, sha256),
reproduccion del golden por el motor declarativo, y code_only (reason no vacia).

  exit 0 sin ERRORs, 1 con >=1 ERROR.

Uso:
    python scripts/validate_rules.py [rules_dir]
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rule_engine


# Claves top-level permitidas en un rule-set
_VALID_KEYS = {
    "_comment", "required", "type", "enums", "bounds", "refs",
    "keyed_bounds", "keyed_enums", "code_only", "golden"
}


def _normalize_newlines(data):
    """Normaliza newlines a LF: \\r\\n -> \\n y \\r suelto -> \\n."""
    return data.replace('\r\n', '\n').replace('\r', '\n')


def _seal(path):
    """Calcula SHA256 del archivo con newlines normalizados a LF."""
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            content = fh.read()
        normalized = _normalize_newlines(content)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    except (OSError, UnicodeDecodeError):
        return None


def _validate_json(filepath):
    """Intenta parsear JSON. Devuelve (dict, error_msg) o (None, error_msg)."""
    try:
        with open(filepath, 'r', encoding='utf-8') as fh:
            return json.load(fh), None
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
        return None, str(e)


def _validate_familia(ruleset):
    """Valida que todas las claves top-level sean conocidas.
    Devuelve lista de (rule_name, msg) para cada error, vacia si ok."""
    errors = []
    for key in ruleset.keys():
        if key not in _VALID_KEYS:
            errors.append(("FAMILIA", "unknown key: {}".format(key)))
    return errors


def _validate_golden_presence(ruleset):
    """Valida que la clave golden este presente con path y sha256.
    Devuelve lista de (rule_name, msg) para cada error, vacia si ok."""
    errors = []
    if "golden" not in ruleset:
        errors.append(("GOLDEN", "golden key missing"))
        return errors

    golden_def = ruleset["golden"]
    if not isinstance(golden_def, dict):
        errors.append(("GOLDEN", "golden must be a dict"))
        return errors

    if "path" not in golden_def:
        errors.append(("GOLDEN", "golden.path missing"))
    if "sha256" not in golden_def:
        errors.append(("GOLDEN", "golden.sha256 missing"))

    return errors


def _validate_golden_file(ruleset, ruleset_dir):
    """Valida que el archivo golden exista y sea parseable.
    Devuelve lista de (rule_name, msg) para cada error, vacia si ok."""
    errors = []
    golden_def = ruleset.get("golden", {})
    path = golden_def.get("path")
    if not path:
        return errors  # Ya fue validado en _validate_golden_presence

    golden_path = os.path.join(ruleset_dir, path)
    if not os.path.isfile(golden_path):
        errors.append(("GOLDEN", "golden file not found: {}".format(path)))
        return errors

    golden_obj, err = _validate_json(golden_path)
    if golden_obj is None:
        errors.append(("GOLDEN", "golden not parseable: {}".format(err)))

    return errors


def _validate_golden_frozen(ruleset, ruleset_dir):
    """Valida que el sha256 del golden coincida (LF-normalizado).
    Devuelve lista de (rule_name, msg) para cada error, vacia si ok."""
    errors = []
    golden_def = ruleset.get("golden", {})
    path = golden_def.get("path")
    sha256_declared = golden_def.get("sha256")

    if not path or not sha256_declared:
        return errors  # Ya fue validado

    golden_path = os.path.join(ruleset_dir, path)
    if not os.path.isfile(golden_path):
        return errors  # Ya fue reportado en _validate_golden_file

    actual_hash = _seal(golden_path)
    if actual_hash is None:
        errors.append(("GOLDEN_FROZEN", "cannot read golden: {}".format(path)))
    elif actual_hash != sha256_declared:
        msg = "golden hash mismatch; expected={}, actual={}; reseal with: python scripts/validate_contracts.py --hash {}".format(
            sha256_declared, actual_hash, path)
        errors.append(("GOLDEN_FROZEN", msg))

    return errors


def _validate_golden_forma(ruleset, ruleset_dir):
    """Valida que el golden tenga forma correcta (refs dict, cases lista, cada caso bien formado).
    Devuelve lista de (rule_name, msg) para cada error, vacia si ok."""
    errors = []
    golden_def = ruleset.get("golden", {})
    path = golden_def.get("path")

    if not path:
        return errors

    golden_path = os.path.join(ruleset_dir, path)
    if not os.path.isfile(golden_path):
        return errors

    golden_obj, err = _validate_json(golden_path)
    if golden_obj is None:
        return errors  # Ya fue reportado

    if not isinstance(golden_obj, dict):
        errors.append(("GOLDEN_FORMA", "golden must be a dict"))
        return errors

    if "refs" not in golden_obj or not isinstance(golden_obj["refs"], dict):
        errors.append(("GOLDEN_FORMA", "golden.refs must be a dict"))

    if "cases" not in golden_obj or not isinstance(golden_obj["cases"], list):
        errors.append(("GOLDEN_FORMA", "golden.cases must be a list"))
        return errors  # No puede continuar sin cases

    if not golden_obj["cases"]:
        errors.append(("GOLDEN_FORMA", "golden.cases must not be empty"))
        return errors

    # Validar cada caso
    for case in golden_obj["cases"]:
        if not isinstance(case, dict):
            errors.append(("GOLDEN_FORMA", "case must be a dict"))
            continue

        if "name" not in case:
            errors.append(("GOLDEN_FORMA", "case missing name"))
        if "record" not in case or not isinstance(case.get("record"), dict):
            errors.append(("GOLDEN_FORMA", "case.record must be a dict"))
        if "violations" not in case or not isinstance(case.get("violations"), list):
            errors.append(("GOLDEN_FORMA", "case.violations must be a list"))
        if "code_only_miss" not in case or not isinstance(case.get("code_only_miss"), list):
            errors.append(("GOLDEN_FORMA", "case.code_only_miss must be a list"))

        # code_only_miss debe ser subconjunto de violations
        violations_set = set(case.get("violations", []))
        code_only_miss_set = set(case.get("code_only_miss", []))
        if not code_only_miss_set.issubset(violations_set):
            errors.append(("GOLDEN_FORMA", "code_only_miss must be subset of violations"))

    return errors


def _validate_code_only(ruleset):
    """Valida que todas las entradas de code_only tengan reason no vacia.
    Devuelve lista de (rule_name, msg) para cada error, vacia si ok."""
    errors = []
    code_only = ruleset.get("code_only", [])
    if not isinstance(code_only, list):
        return errors  # Sera reportado como FAMILIA o similar

    for entry in code_only:
        if not isinstance(entry, dict):
            continue
        reason = entry.get("reason", "")
        if not reason or not reason.strip():
            errors.append(("CODE_ONLY", "code_only entry missing reason"))

    return errors


def _validate_repro(ruleset, ruleset_dir):
    """Valida que el motor reproduce las violaciones del golden para cada caso.
    Devuelve lista de (rule_name, msg) para cada error, vacia si ok."""
    errors = []
    golden_def = ruleset.get("golden", {})
    path = golden_def.get("path")

    if not path:
        return errors

    golden_path = os.path.join(ruleset_dir, path)
    if not os.path.isfile(golden_path):
        return errors

    golden_obj, err = _validate_json(golden_path)
    if golden_obj is None:
        return errors

    refs = golden_obj.get("refs", {})
    cases = golden_obj.get("cases", [])

    for case in cases:
        if not isinstance(case, dict):
            continue

        case_name = case.get("name", "?")
        record = case.get("record", {})
        expected_violations = set(case.get("violations", []))
        code_only_miss = set(case.get("code_only_miss", []))

        # Motor reproduce: violations - code_only_miss
        actual_violations = rule_engine.evaluate(ruleset, record, refs)

        # Extraer campos top-level de las violaciones (formato "field: reason")
        # Campo top-level es la parte antes del primer punto o antes de ":"
        actual_fields = set()
        for violation in actual_violations:
            if ':' in violation:
                field = violation.split(':', 1)[0].strip()
                # Extraer solo el campo top-level (antes del primer punto)
                top_level = field.split('.')[0] if '.' in field else field
                actual_fields.add(top_level)

        expected_fields = expected_violations - code_only_miss

        if actual_fields != expected_fields:
            msg = "REPRO divergence for case '{}': expected={}, actual={}".format(
                case_name, sorted(expected_fields), sorted(actual_fields))
            errors.append(("REPRO", msg))

    return errors


def _scan_rule_files(rules_dir):
    """Escanea rules_dir y devuelve la lista ordenada de *.rules.json.
    Lista vacia si el directorio no existe o no tiene rule-sets (capa opcional)."""
    if not os.path.isdir(rules_dir):
        return []
    try:
        entries = os.listdir(rules_dir)
    except OSError:
        return []
    return sorted(e for e in entries if e.endswith(".rules.json"))


def validate_rules(rules_dir: str) -> list:
    """Valida todos los *.rules.json bajo rules_dir. Devuelve findings
    [{'file','level','rule','msg'}] ordenados (archivo, regla); vacia si todo es
    conforme O si el directorio no existe / no tiene rule-sets (capa opcional).
    No lanza ante rule-sets invalidos (reporta)."""

    findings = []

    # Capa opcional: dir ausente o sin rule-sets
    rule_files = _scan_rule_files(rules_dir)
    if not rule_files:
        return findings

    # Procesar cada rule-set
    for filename in rule_files:
        filepath = os.path.join(rules_dir, filename)

        # JSON parseable
        ruleset, err = _validate_json(filepath)
        if ruleset is None:
            findings.append({
                "file": filename,
                "level": "ERROR",
                "rule": "JSON",
                "msg": "not parseable: {}".format(err)
            })
            continue

        if not isinstance(ruleset, dict):
            findings.append({
                "file": filename,
                "level": "ERROR",
                "rule": "JSON",
                "msg": "must be a dict"
            })
            continue

        # FAMILIA
        for rule, msg in _validate_familia(ruleset):
            findings.append({
                "file": filename,
                "level": "ERROR",
                "rule": rule,
                "msg": msg
            })

        # GOLDEN (presencia)
        for rule, msg in _validate_golden_presence(ruleset):
            findings.append({
                "file": filename,
                "level": "ERROR",
                "rule": rule,
                "msg": msg
            })

        # GOLDEN (archivo existe y parseable)
        for rule, msg in _validate_golden_file(ruleset, rules_dir):
            findings.append({
                "file": filename,
                "level": "ERROR",
                "rule": rule,
                "msg": msg
            })

        # GOLDEN_FROZEN (hash)
        for rule, msg in _validate_golden_frozen(ruleset, rules_dir):
            findings.append({
                "file": filename,
                "level": "ERROR",
                "rule": rule,
                "msg": msg
            })

        # GOLDEN_FORMA
        for rule, msg in _validate_golden_forma(ruleset, rules_dir):
            findings.append({
                "file": filename,
                "level": "ERROR",
                "rule": rule,
                "msg": msg
            })

        # CODE_ONLY
        for rule, msg in _validate_code_only(ruleset):
            findings.append({
                "file": filename,
                "level": "ERROR",
                "rule": rule,
                "msg": msg
            })

        # REPRO (motor)
        for rule, msg in _validate_repro(ruleset, rules_dir):
            findings.append({
                "file": filename,
                "level": "ERROR",
                "rule": rule,
                "msg": msg
            })

    # Ordenar por (file, rule) para determinismo
    findings.sort(key=lambda f: (f["file"], f["rule"]))

    return findings


def main():
    """CLI: imprime findings y resumen; exit 0 sin ERRORs, 1 con >=1 ERROR.
    Sin *.rules.json (o dir ausente) -> INFO + exit 0 (capa opcional)."""
    rules_dir = sys.argv[1] if len(sys.argv) > 1 else "examples/rules"

    rule_files = _scan_rule_files(rules_dir)
    if not rule_files:
        print("INFO: {} no existe o no tiene *.rules.json (capa opcional)".format(rules_dir))
        return 0

    findings = validate_rules(rules_dir)

    error_count = 0
    for f in findings:
        if f["level"] == "ERROR":
            error_count += 1
        print("{} [{}] {}: {}".format(f["level"], f["rule"], f["file"], f["msg"]))

    if error_count == 0:
        print("OK: todos los rule contracts son conformes")

    print()
    print("Resumen: {} error(es) en {} archivo(s)".format(error_count, len(rule_files)))

    return 1 if error_count else 0


if __name__ == "__main__":
    sys.exit(main())
