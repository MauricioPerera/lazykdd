"""Motor de reglas declarativo (Contrato 17).

Evalua un record contra un rule-set declarativo (required/type/enums/bounds/refs/keyed)
y devuelve las violaciones, sin LLM ni red. Puro, determinista, stdlib.
"""

import re


def evaluate(ruleset: dict, record: dict, refs: dict) -> list:
    """Evalua `record` contra `ruleset` (familias declarativas), resolviendo las
    familias keyed contra `refs`. Devuelve una lista de violaciones legibles (vacia =
    valido), ordenada deterministamente; cada violacion empieza con '<field>: ...'
    (field puede ser punteado/anidado). Funcion pura: sin IO, sin red, determinista."""

    violations = []

    def get_value(obj, field_path):
        """Navega un campo punteado en un dict anidado. Retorna None si ausente."""
        parts = field_path.split('.')
        current = obj
        for part in parts:
            if not isinstance(current, dict):
                return None  # Intermedio no-dict -> ausente
            current = current.get(part)
        return current

    def is_empty(value):
        """Verifica si un valor se considera vacío (None o string vacío)."""
        return value is None or value == ""

    def format_violation(field, msg):
        """Formatea un mensaje de violación."""
        return "{}: {}".format(field, msg)

    def evaluate_v1_subset(ruleset_v1, record_elem, refs):
        """Evalua solo familias v1 (required/type/enums/bounds) sobre un elemento."""
        elem_violations = []

        # Procesar familia 'required'
        if "required" in ruleset_v1:
            for rule in ruleset_v1["required"]:
                field = rule["field"]
                value = get_value(record_elem, field)
                if is_empty(value):
                    elem_violations.append(format_violation(field, "required"))

        # Procesar familia 'type'
        if "type" in ruleset_v1:
            for rule in ruleset_v1["type"]:
                field = rule["field"]
                kind = rule["kind"]
                value = get_value(record_elem, field)

                if value is None:
                    continue

                if kind == "number":
                    if isinstance(value, bool) or not isinstance(value, (int, float)):
                        elem_violations.append(format_violation(field, "type must be number"))
                elif kind == "string":
                    if not isinstance(value, str):
                        elem_violations.append(format_violation(field, "type must be string"))
                elif kind == "dict":
                    if not isinstance(value, dict):
                        elem_violations.append(format_violation(field, "type must be dict"))

        # Procesar familia 'bounds'
        if "bounds" in ruleset_v1:
            for rule in ruleset_v1["bounds"]:
                field = rule["field"]
                value = get_value(record_elem, field)

                if value is None or not isinstance(value, (int, float)) or isinstance(value, bool):
                    continue

                if "gt" in rule and value <= rule["gt"]:
                    elem_violations.append(format_violation(field, "bounds violated"))
                elif "min" in rule and value < rule["min"]:
                    elem_violations.append(format_violation(field, "bounds violated"))
                elif "max" in rule and value > rule["max"]:
                    elem_violations.append(format_violation(field, "bounds violated"))
                elif rule.get("integer", False) and value != int(value):
                    elem_violations.append(format_violation(field, "bounds violated"))

        # Procesar familia 'enums'
        if "enums" in ruleset_v1:
            for rule in ruleset_v1["enums"]:
                field = rule["field"]
                value = get_value(record_elem, field)
                values = rule["values"]

                if value not in values:
                    elem_violations.append(format_violation(field, "not in enum"))

        # Procesar familia 'matches'
        if "matches" in ruleset_v1:
            for rule in ruleset_v1["matches"]:
                field = rule["field"]
                pattern = rule["pattern"]
                value = get_value(record_elem, field)

                # matches solo aplica si el valor es string (ausente/None se salta)
                if value is None or not isinstance(value, str):
                    continue

                if not re.search(pattern, value):
                    elem_violations.append(format_violation(field, "pattern mismatch"))

        return elem_violations

    # Procesar familia 'required'
    if "required" in ruleset:
        for rule in ruleset["required"]:
            field = rule["field"]
            value = get_value(record, field)
            if is_empty(value):
                violations.append(format_violation(field, "required"))

    # Procesar familia 'type'
    if "type" in ruleset:
        for rule in ruleset["type"]:
            field = rule["field"]
            kind = rule["kind"]
            value = get_value(record, field)

            # type no se evalua si ausente (eso es required)
            if value is None:
                continue

            if kind == "number":
                # number excluye bool
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    violations.append(format_violation(field, "type must be number"))
            elif kind == "string":
                if not isinstance(value, str):
                    violations.append(format_violation(field, "type must be string"))
            elif kind == "dict":
                if not isinstance(value, dict):
                    violations.append(format_violation(field, "type must be dict"))

    # Procesar familia 'bounds'
    if "bounds" in ruleset:
        for rule in ruleset["bounds"]:
            field = rule["field"]
            value = get_value(record, field)

            # bounds solo aplica a numbers
            if value is None or not isinstance(value, (int, float)) or isinstance(value, bool):
                continue

            if "gt" in rule and value <= rule["gt"]:
                violations.append(format_violation(field, "bounds violated"))
            elif "min" in rule and value < rule["min"]:
                violations.append(format_violation(field, "bounds violated"))
            elif "max" in rule and value > rule["max"]:
                violations.append(format_violation(field, "bounds violated"))
            elif rule.get("integer", False) and value != int(value):
                violations.append(format_violation(field, "bounds violated"))

    # Procesar familia 'enums'
    if "enums" in ruleset:
        for rule in ruleset["enums"]:
            field = rule["field"]
            value = get_value(record, field)
            values = rule["values"]

            # Igualdad de valor (in)
            if value not in values:
                violations.append(format_violation(field, "not in enum"))

    # Procesar familia 'matches'
    if "matches" in ruleset:
        for rule in ruleset["matches"]:
            field = rule["field"]
            pattern = rule["pattern"]
            value = get_value(record, field)

            # matches solo aplica si el valor es string (ausente/None se salta)
            if value is None or not isinstance(value, str):
                continue

            if not re.search(pattern, value):
                violations.append(format_violation(field, "pattern mismatch"))

    # Procesar familia 'refs'
    if "refs" in ruleset:
        for rule in ruleset["refs"]:
            field = rule["field"]
            collection = rule["collection"]
            value = get_value(record, field)

            # refs se evalua solo si presente
            if value is None:
                continue

            if collection not in refs or value not in refs[collection]:
                violations.append(format_violation(field, "ref not found"))

    # Procesar familia 'keyed_bounds'
    if "keyed_bounds" in ruleset:
        for rule in ruleset["keyed_bounds"]:
            field = rule["field"]
            key = rule["key"]
            table = rule["table"]
            max_path = rule["max_path"]

            value = get_value(record, field)

            # keyed_bounds solo aplica a numbers
            if value is None or not isinstance(value, (int, float)) or isinstance(value, bool):
                continue

            # Resolver la clave
            key_value = get_value(record, key)

            # Si la clave no resuelve en la tabla, saltamos (sin violacion)
            if table not in refs or key_value not in refs[table]:
                continue

            # Resolver el tope desde refs[table][key_value][max_path]
            max_limit = get_value(refs[table][key_value], max_path)

            # Si el tope no existe, saltamos
            if max_limit is None:
                continue

            if value > max_limit:
                violations.append(format_violation(field, "keyed bounds violated"))

    # Procesar familia 'keyed_enums'
    if "keyed_enums" in ruleset:
        for rule in ruleset["keyed_enums"]:
            field = rule["field"]
            key = rule["key"]
            table = rule["table"]
            values_path = rule["values_path"]

            value = get_value(record, field)

            # keyed_enums se evalua si presente
            if value is None:
                continue

            # Resolver la clave
            key_value = get_value(record, key)

            # Si la clave no resuelve en la tabla, saltamos (sin violacion)
            if table not in refs or key_value not in refs[table]:
                continue

            # Resolver el conjunto permitido desde refs[table][key_value][values_path]
            allowed_values = get_value(refs[table][key_value], values_path)

            # Si el conjunto no existe, saltamos
            if allowed_values is None:
                continue

            if value not in allowed_values:
                violations.append(format_violation(field, "keyed enum not allowed"))

    # Procesar familia 'each'
    if "each" in ruleset:
        for each_rule in ruleset["each"]:
            collection = each_rule.get("collection")
            where = each_rule.get("where")
            rules = each_rule.get("rules", {})

            # Obtener la coleccion desde el record
            items = get_value(record, collection)

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
                    item_where_value = get_value(item, where_field)
                    if item_where_value != where_value:
                        continue

                # La rule se aplica a este elemento. Si no es dict, es violacion
                if not isinstance(item, dict):
                    violations.append(format_violation(collection, "element at index {} is not a dict".format(idx)))
                    continue

                # Evaluar el subset v1 de reglas sobre este elemento
                elem_violations = evaluate_v1_subset(rules, item, refs)

                # Prefixar cada violacion con "collection: elemento <idx>."
                for elem_viol in elem_violations:
                    prefixed = "{}: elemento {}: {}".format(collection, idx, elem_viol)
                    violations.append(prefixed)

    # Ordenar deterministamente por campo (parte antes del ':')
    violations.sort(key=lambda v: v.split(":", 1)[0].strip())

    return violations
