"""Motor de reglas declarativo (Contrato 17).

Evalua un record contra un rule-set declarativo (required/type/enums/bounds/refs/keyed)
y devuelve las violaciones, sin LLM ni red. Puro, determinista, stdlib.

Estructura: `evaluate` es un dispatcher delgado que reparte cada familia
declarativa a una funcion module-level `_check_<familia>`. Las familias que
NO usan `refs` (required/type/bounds/enums/matches) se aplican tanto al record
top-level como, dentro de `each`, a cada elemento de una coleccion (por eso
reciben un `obj` generico); las keyed y `each` si necesitan `refs`.
"""

import re


def _get_value(obj, field_path):
    """Navega un campo punteado en un dict anidado. Retorna None si ausente."""
    parts = field_path.split('.')
    current = obj
    for part in parts:
        if not isinstance(current, dict):
            return None  # Intermedio no-dict -> ausente
        current = current.get(part)
    return current


def _is_empty(value):
    """Verifica si un valor se considera vacio (None o string vacio)."""
    return value is None or value == ""


def _format_violation(field, msg):
    """Formatea un mensaje de violacion."""
    return "{}: {}".format(field, msg)


def _check_required(rules, obj):
    """Familia 'required': ausente/None/"" -> violacion."""
    violations = []
    for rule in rules:
        field = rule["field"]
        value = _get_value(obj, field)
        if _is_empty(value):
            violations.append(_format_violation(field, "required"))
    return violations


def _check_type(rules, obj):
    """Familia 'type': number|string|dict; number excluye bool; solo si presente."""
    violations = []
    for rule in rules:
        field = rule["field"]
        kind = rule["kind"]
        value = _get_value(obj, field)

        # type no se evalua si ausente (eso es required)
        if value is None:
            continue

        if kind == "number":
            # number excluye bool
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                violations.append(_format_violation(field, "type must be number"))
        elif kind == "string":
            if not isinstance(value, str):
                violations.append(_format_violation(field, "type must be string"))
        elif kind == "dict":
            if not isinstance(value, dict):
                violations.append(_format_violation(field, "type must be dict"))
    return violations


def _check_bounds(rules, obj):
    """Familia 'bounds': gt/min/max/integer; solo sobre numbers; una violacion por regla."""
    violations = []
    for rule in rules:
        field = rule["field"]
        value = _get_value(obj, field)

        # bounds solo aplica a numbers
        if value is None or not isinstance(value, (int, float)) or isinstance(value, bool):
            continue

        if "gt" in rule and value <= rule["gt"]:
            violations.append(_format_violation(field, "bounds violated"))
        elif "min" in rule and value < rule["min"]:
            violations.append(_format_violation(field, "bounds violated"))
        elif "max" in rule and value > rule["max"]:
            violations.append(_format_violation(field, "bounds violated"))
        elif rule.get("integer", False) and value != int(value):
            violations.append(_format_violation(field, "bounds violated"))
    return violations


def _check_enums(rules, obj):
    """Familia 'enums': igualdad de valor (in)."""
    violations = []
    for rule in rules:
        field = rule["field"]
        value = _get_value(obj, field)
        values = rule["values"]

        if value not in values:
            violations.append(_format_violation(field, "not in enum"))
    return violations


def _check_matches(rules, obj):
    """Familia 'matches': {field, pattern}; viola si string y re.search no matchea."""
    violations = []
    for rule in rules:
        field = rule["field"]
        pattern = rule["pattern"]
        value = _get_value(obj, field)

        # matches solo aplica si el valor es string (ausente/None se salta)
        if value is None or not isinstance(value, str):
            continue

        if not re.search(pattern, value):
            violations.append(_format_violation(field, "pattern mismatch"))
    return violations


def _check_refs(rules, record, refs):
    """Familia 'refs': el valor debe ser clave en refs[collection]; solo si presente."""
    violations = []
    for rule in rules:
        field = rule["field"]
        collection = rule["collection"]
        value = _get_value(record, field)

        # refs se evalua solo si presente
        if value is None:
            continue

        if collection not in refs or value not in refs[collection]:
            violations.append(_format_violation(field, "ref not found"))
    return violations


def _check_keyed_bounds(rules, record, refs):
    """Familia 'keyed_bounds': tope = refs[table][record[key]][max_path]; > max -> violacion."""
    violations = []
    for rule in rules:
        field = rule["field"]
        key = rule["key"]
        table = rule["table"]
        max_path = rule["max_path"]

        value = _get_value(record, field)

        # keyed_bounds solo aplica a numbers
        if value is None or not isinstance(value, (int, float)) or isinstance(value, bool):
            continue

        # Resolver la clave
        key_value = _get_value(record, key)

        # Si la clave no resuelve en la tabla, saltamos (sin violacion)
        if table not in refs or key_value not in refs[table]:
            continue

        # Resolver el tope desde refs[table][key_value][max_path]
        max_limit = _get_value(refs[table][key_value], max_path)

        # Si el tope no existe, saltamos
        if max_limit is None:
            continue

        if value > max_limit:
            violations.append(_format_violation(field, "keyed bounds violated"))
    return violations


def _check_keyed_enums(rules, record, refs):
    """Familia 'keyed_enums': allowed = refs[table][record[key]][values_path]; no in -> violacion."""
    violations = []
    for rule in rules:
        field = rule["field"]
        key = rule["key"]
        table = rule["table"]
        values_path = rule["values_path"]

        value = _get_value(record, field)

        # keyed_enums se evalua si presente
        if value is None:
            continue

        # Resolver la clave
        key_value = _get_value(record, key)

        # Si la clave no resuelve en la tabla, saltamos (sin violacion)
        if table not in refs or key_value not in refs[table]:
            continue

        # Resolver el conjunto permitido desde refs[table][key_value][values_path]
        allowed_values = _get_value(refs[table][key_value], values_path)

        # Si el conjunto no existe, saltamos
        if allowed_values is None:
            continue

        if value not in allowed_values:
            violations.append(_format_violation(field, "keyed enum not allowed"))
    return violations


def _check_each(rules, record, refs):
    """Familia 'each': cuantificacion sobre colecciones del subset v1 por elemento."""
    violations = []
    for each_rule in rules:
        collection = each_rule.get("collection")
        where = each_rule.get("where")
        sub_rules = each_rule.get("rules", {})

        # Obtener la coleccion desde el record
        items = _get_value(record, collection)

        # Si no existe o no es lista, se salta
        if not isinstance(items, list):
            continue

        # Procesar cada elemento de la coleccion
        for idx, item in enumerate(items):
            # Si hay filtro where, verificar que el elemento lo cumpla
            # Si no cumple, esta rule no se aplica a este elemento
            if where:
                where_field = where.get("field")
                where_value = where.get("equals")
                item_where_value = _get_value(item, where_field)
                if item_where_value != where_value:
                    continue

            # La rule se aplica a este elemento. Si no es dict, es violacion
            if not isinstance(item, dict):
                violations.append(_format_violation(collection, "element at index {} is not a dict".format(idx)))
                continue

            # Evaluar el subset v1 de reglas sobre este elemento (reusa los
            # mismos helpers del nivel top, eliminando la duplicacion previa).
            elem_violations = []
            if "required" in sub_rules:
                elem_violations += _check_required(sub_rules["required"], item)
            if "type" in sub_rules:
                elem_violations += _check_type(sub_rules["type"], item)
            if "bounds" in sub_rules:
                elem_violations += _check_bounds(sub_rules["bounds"], item)
            if "enums" in sub_rules:
                elem_violations += _check_enums(sub_rules["enums"], item)
            if "matches" in sub_rules:
                elem_violations += _check_matches(sub_rules["matches"], item)

            # Prefixar cada violacion con "collection: elemento <idx>: <viol>"
            for elem_viol in elem_violations:
                prefixed = "{}: elemento {}: {}".format(collection, idx, elem_viol)
                violations.append(prefixed)
    return violations


def evaluate(ruleset: dict, record: dict, refs: dict) -> list:
    """Evalua `record` contra `ruleset` (familias declarativas), resolviendo las
    familias keyed contra `refs`. Devuelve una lista de violaciones legibles (vacia =
    valido), ordenada deterministamente; cada violacion empieza con '<field>: ...'
    (field puede ser punteado/anidado). Funcion pura: sin IO, sin red, determinista.

    Dispatcher delgado: reparte cada familia a su helper module-level y combina
    las violaciones. El orden de procesamiento sigue el canon del contrato
    (required, type, bounds, enums, matches, refs, keyed_bounds, keyed_enums, each);
    el sort final determinista (por campo) hace que el orden no afecte el resultado.
    """
    violations = []
    if "required" in ruleset:
        violations += _check_required(ruleset["required"], record)
    if "type" in ruleset:
        violations += _check_type(ruleset["type"], record)
    if "bounds" in ruleset:
        violations += _check_bounds(ruleset["bounds"], record)
    if "enums" in ruleset:
        violations += _check_enums(ruleset["enums"], record)
    if "matches" in ruleset:
        violations += _check_matches(ruleset["matches"], record)
    if "refs" in ruleset:
        violations += _check_refs(ruleset["refs"], record, refs)
    if "keyed_bounds" in ruleset:
        violations += _check_keyed_bounds(ruleset["keyed_bounds"], record, refs)
    if "keyed_enums" in ruleset:
        violations += _check_keyed_enums(ruleset["keyed_enums"], record, refs)
    if "each" in ruleset:
        violations += _check_each(ruleset["each"], record, refs)
    # Ordenar deterministamente por campo (parte antes del ':')
    violations.sort(key=lambda v: v.split(":", 1)[0].strip())
    return violations