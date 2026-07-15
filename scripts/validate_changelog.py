#!/usr/bin/env python3
"""Gate de coherencia CHANGELOG<->reportes (Contrato 27).

Valida que todo contrato con reporte en docs/reports tiene su entrada en
CHANGELOG.md (y viceversa, con link y sin duplicados). Nacido del incidente
real de v1.2.0: tres entradas perdidas por un replace silencioso.
"""

import os
import re
import sys


# ---------------------------------------------------------------------------
# Core validation logic
# ---------------------------------------------------------------------------

def validate_changelog(changelog_path, reports_dir):
    """Valida coherencia entre CHANGELOG.md y reportes de contratos.

    Devuelve lista de findings [{'file','level','rule','msg'}] ordenados por
    (file, rule, msg), con rutas en estilo posix ('/').

    Capa opcional: si changelog o reports_dir no existen/están vacíos,
    retorna findings INFO sin evaluar reglas ERROR.
    """
    # Capa opcional: changelog ausente
    if not os.path.isfile(changelog_path):
        return [_finding(_to_posix(changelog_path), 'CHANGELOG_MISSING',
                        'archivo no existe', level='INFO')]

    # Capa opcional: reports_dir ausente o sin reportes CONTRACT-*
    if not os.path.isdir(reports_dir):
        return [_finding(_to_posix(reports_dir), 'REPORTS_MISSING',
                        'directorio no existe', level='INFO')]

    # Extraer reportes válidos: patrón CONTRACT-<dígitos>-REPORT.md
    reports = _extract_reports(reports_dir)
    if not reports:
        return [_finding(_to_posix(reports_dir), 'REPORTS_MISSING',
                        'sin reportes CONTRACT-*', level='INFO')]

    # Extraer entradas del changelog: líneas que EMPIEZAN con **Contract <dígitos>
    entry_nns = dict(_extract_entries(changelog_path))  # nn -> [line_numbers]
    report_nns = set(reports.keys())

    # ENTRY_MISSING (reportes sin entrada) + REPORT_MISSING/LINK_MISSING/ENTRY_DUP
    findings = _check_entry_missing(report_nns, entry_nns, changelog_path,
                                    reports)
    findings += _check_entries(entry_nns, report_nns, changelog_path)

    # Ordenar por (file, rule, msg)
    findings.sort(key=lambda f: (f['file'], f['rule'], f['msg']))

    return findings


def _check_entry_missing(report_nns, entry_nns, changelog_path, reports):
    """Findings ENTRY_MISSING: reportes cuyo NN no tiene entrada
    correspondiente en el changelog. Mismo formato de mensaje que hoy
    (incluye la ruta relativa del reporte, con '/' como separador)."""
    findings = []
    for nn in sorted(report_nns):
        if nn not in entry_nns:
            report_file = os.path.relpath(reports[nn],
                                         os.path.dirname(changelog_path))
            report_file = report_file.replace(os.sep, '/')
            findings.append(_finding(
                _to_posix(changelog_path),
                'ENTRY_MISSING',
                'reporte {} sin entrada; archivo: {}'.format(nn, report_file)
            ))
    return findings


def _check_entries(entry_nns, report_nns, changelog_path):
    """Findings REPORT_MISSING (entrada sin reporte), LINK_MISSING
    (hay reporte pero la primera linea de la entrada no linkea), y
    ENTRY_DUP (un finding por ocurrencia EXTRA de un NN repetido --
    la primera ocurrencia NO genera finding). Logica identica a hoy,
    incluida la lectura de _read_entry_line/_has_link sobre
    line_nums[0]."""
    findings = []
    for nn in sorted(entry_nns.keys()):
        line_nums = entry_nns[nn]

        if nn not in report_nns:
            # REPORT_MISSING: entrada sin reporte
            findings.append(_finding(
                _to_posix(changelog_path),
                'REPORT_MISSING',
                'entrada sin reporte: {}'.format(nn)
            ))
        else:
            # Hay reporte correspondiente: chequear link en primera línea
            first_line = _read_entry_line(changelog_path, line_nums[0])
            if not _has_link(first_line, nn):
                findings.append(_finding(
                    _to_posix(changelog_path),
                    'LINK_MISSING',
                    'entrada sin link al reporte: {}'.format(nn)
                ))

        # ENTRY_DUP: más de una entrada para el mismo NN
        # Un finding por ocurrencia extra
        if len(line_nums) > 1:
            for _ in range(len(line_nums) - 1):
                findings.append(_finding(
                    _to_posix(changelog_path),
                    'ENTRY_DUP',
                    'entrada duplicada: {}'.format(nn)
                ))
    return findings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _finding(file, rule, msg, level='ERROR'):
    """Crea un finding."""
    return {'file': file, 'level': level, 'rule': rule, 'msg': msg}


def _to_posix(path):
    """Convierte ruta a posix."""
    return path.replace(os.sep, '/')


def _extract_reports(reports_dir):
    """Extrae reportes válidos: CONTRACT-<dígitos>-REPORT.md.

    Devuelve dict {nn: filepath}.
    """
    reports = {}
    pattern = re.compile(r'^CONTRACT-(\d+)-REPORT\.md$')

    try:
        entries = os.listdir(reports_dir)
    except OSError:
        return {}

    for entry in sorted(entries):
        m = pattern.match(entry)
        if m:
            nn = m.group(1)
            filepath = os.path.join(reports_dir, entry)
            reports[nn] = filepath

    return reports


def _extract_entries(changelog_path):
    """Extrae entradas: líneas que EMPIEZAN con '**Contract <dígitos>'.

    Devuelve dict {nn: [line_numbers]}.
    """
    entries = {}
    pattern = re.compile(r'^\*\*Contract\s+(\d+)')

    try:
        with open(changelog_path, 'r', encoding='utf-8') as fh:
            lines = fh.readlines()
    except OSError:
        return {}

    for i, line in enumerate(lines):
        m = pattern.match(line)
        if m:
            nn = m.group(1)
            if nn not in entries:
                entries[nn] = []
            entries[nn].append(i)

    return entries


def _read_entry_line(changelog_path, line_num):
    """Lee una línea específica del changelog."""
    try:
        with open(changelog_path, 'r', encoding='utf-8') as fh:
            lines = fh.readlines()
        if 0 <= line_num < len(lines):
            return lines[line_num]
    except OSError:
        pass
    return ''


def _has_link(line, nn):
    """Chequea si la línea contiene '(docs/reports/CONTRACT-NN-REPORT.md)'."""
    expected = '(docs/reports/CONTRACT-{}-REPORT.md)'.format(nn)
    return expected in line


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv):
    """CLI: imprime findings y resumen; exit 0 sin ERRORs, 1 con >=1."""
    # Parsear argumentos con defaults
    if len(argv) >= 2:
        changelog_path = argv[0]
        reports_dir = argv[1]
    elif len(argv) == 1:
        changelog_path = argv[0]
        reports_dir = 'docs/reports'
    else:
        changelog_path = 'CHANGELOG.md'
        reports_dir = 'docs/reports'

    # Validar
    findings = validate_changelog(changelog_path, reports_dir)

    # Separar errores
    errors = [f for f in findings if f['level'] == 'ERROR']

    # Imprimir findings
    if findings:
        for f in findings:
            print("{} [{}] {}: {}".format(f['level'], f['rule'],
                                        f['file'], f['msg']))

    # Contar NN distintos escaneados (lo ESCANEADO, nunca derivado de findings)
    scanned_nns = set()

    # Desde reportes
    if os.path.isdir(reports_dir):
        reports = _extract_reports(reports_dir)
        scanned_nns.update(reports.keys())

    # Desde entradas
    if os.path.isfile(changelog_path):
        entries = _extract_entries(changelog_path)
        scanned_nns.update(entries.keys())

    # Imprimir resumen
    print()
    print("Resumen: {} error(es), {} contrato(s) verificados".format(
        len(errors), len(scanned_nns)))

    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
