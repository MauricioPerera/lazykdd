#!/usr/bin/env python3
"""Gate deterministico de diagramas Mermaid 'flowchart' (Contrato: diagram-gate).

Parser minimo en Python puro (regex) para el subconjunto mas comun de la
sintaxis 'flowchart'/'graph' de Mermaid: definicion de nodos con shape
([ ], { }, ( )) y edges (-->, -->|label|, ---, -.->). NO usa el parser real
de mermaid: eso exigiria Node.js via subprocess, prohibido por 'forbids' en
los gates Nivel 1 de este repo (ver knowledge/contracts/ux-page-gate.md).
Cobertura deliberadamente parcial (solo flowchart) — ver
knowledge/diagram-contract-spec.md para el subconjunto exacto soportado y
la comparacion con el proyecto hermano mermaid-gate (Node, parser real de
mermaid, 20 tipos de diagrama, sin la restriccion de dependencias de este
repo).
"""

import json
import os
import re
import sys


_SHAPE = r'(\[[^\]]*\]|\{[^{}]*\}|\([^()]*\))?'
NODE_DEF = re.compile(r'^\s*(\w+)\s*' + _SHAPE + r'\s*$')
EDGE_LINE = re.compile(
    r'(\w+)\s*' + _SHAPE +
    r'\s*(?:-{1,3}|-\.-?)>?\s*(?:\|([^|]*)\|\s*)?' +
    r'(\w+)\s*' + _SHAPE
)


def _strip_shape(token):
    """Extrae el label de '[label]'/'{label}'/'(label)'; None si no hay shape."""
    if not token:
        return None
    return token[1:-1].strip()


def get_diagram_type(text):
    """Primer token no vacio/no-comentario del texto ('flowchart' o 'graph')."""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('%%'):
            continue
        return stripped.split()[0]
    return None


def parse_flowchart(text):
    """Devuelve {'nodes': [{'id','label'}], 'edges': [{'from','to','label'}]}.

    Heuristica linea por linea: cada linea (salvo el header) se prueba primero
    como edge, despues como definicion de nodo suelta. No maneja subgraphs,
    estilos, ni edges multi-linea — ver knowledge/diagram-contract-spec.md.
    """
    nodes = {}
    edges = []

    def register(node_id, shape_token):
        label = _strip_shape(shape_token)
        if label is not None:
            nodes[node_id] = label
        elif node_id not in nodes:
            nodes[node_id] = node_id

    lines = text.splitlines()
    for raw_line in lines[1:]:
        line = raw_line.strip()
        if not line or line.startswith('%%'):
            continue

        edge_match = EDGE_LINE.search(line)
        if edge_match:
            from_id, from_shape, label, to_id, to_shape = edge_match.groups()
            register(from_id, from_shape)
            register(to_id, to_shape)
            edges.append({
                'from': from_id,
                'to': to_id,
                'label': label.strip() if label else None,
            })
            continue

        node_match = NODE_DEF.match(line)
        if node_match:
            node_id, shape = node_match.groups()
            register(node_id, shape)

    return {
        'nodes': [{'id': nid, 'label': label} for nid, label in nodes.items()],
        'edges': edges,
    }


def validate_diagram(mmd_path, contract_path):
    """Valida un .mmd contra su .diagram-contract.json. Retorna lista de findings."""
    file_label = mmd_path.replace('\\', '/')

    try:
        with open(mmd_path, 'r', encoding='utf-8') as fh:
            text = fh.read()
    except OSError as e:
        return [{'file': file_label, 'level': 'ERROR', 'rule': 'FILE_ERROR', 'msg': str(e)}]

    try:
        with open(contract_path, 'r', encoding='utf-8') as fh:
            contract = json.load(fh)
    except (OSError, ValueError) as e:
        return [{
            'file': contract_path.replace('\\', '/'),
            'level': 'ERROR',
            'rule': 'CONTRACT_INVALID',
            'msg': str(e),
        }]

    diagram_type = get_diagram_type(text)
    normalized = 'flowchart' if diagram_type in ('flowchart', 'graph') else diagram_type

    expected_type = contract.get('diagram_type')
    if expected_type and expected_type != 'flowchart':
        return [{
            'file': file_label,
            'level': 'ERROR',
            'rule': 'DIAGRAM_TYPE_UNSUPPORTED',
            'msg': (
                "este gate pure-Python solo soporta diagram_type 'flowchart' "
                "(para '{}' usar el proyecto hermano mermaid-gate)".format(expected_type)
            ),
        }]

    if normalized != 'flowchart':
        return [{
            'file': file_label,
            'level': 'ERROR',
            'rule': 'DIAGRAM_TYPE_MISMATCH',
            'msg': "diagram_type esperado 'flowchart', encontrado '{}'".format(diagram_type),
        }]

    findings = []
    parsed = parse_flowchart(text)
    nodes_by_id = {n['id']: n for n in parsed['nodes']}

    min_nodes = contract.get('min_nodes')
    if isinstance(min_nodes, int) and len(parsed['nodes']) < min_nodes:
        findings.append({
            'file': file_label, 'level': 'ERROR', 'rule': 'MIN_NODES',
            'msg': 'min_nodes {}, encontrado {}'.format(min_nodes, len(parsed['nodes'])),
        })

    max_nodes = contract.get('max_nodes')
    if isinstance(max_nodes, int) and len(parsed['nodes']) > max_nodes:
        findings.append({
            'file': file_label, 'level': 'ERROR', 'rule': 'MAX_NODES',
            'msg': 'max_nodes {}, encontrado {}'.format(max_nodes, len(parsed['nodes'])),
        })

    for req in contract.get('required_nodes', []):
        found = nodes_by_id.get(req.get('id'))
        if not found:
            findings.append({
                'file': file_label, 'level': 'ERROR', 'rule': 'MISSING_NODE',
                'msg': "falta nodo requerido '{}'".format(req.get('id')),
            })
            continue
        if req.get('label') and found.get('label') != req.get('label'):
            findings.append({
                'file': file_label, 'level': 'ERROR', 'rule': 'NODE_LABEL_MISMATCH',
                'msg': "nodo '{}' esperaba label '{}', encontrado '{}'".format(
                    req.get('id'), req.get('label'), found.get('label')),
            })

    for req in contract.get('required_edges', []):
        match = None
        for e in parsed['edges']:
            if e['from'] != req.get('from') or e['to'] != req.get('to'):
                continue
            if req.get('label') and e.get('label') != req.get('label'):
                continue
            match = e
            break
        if not match:
            label_part = " con label '{}'".format(req['label']) if req.get('label') else ''
            findings.append({
                'file': file_label, 'level': 'ERROR', 'rule': 'MISSING_EDGE',
                'msg': "falta edge requerido '{}' -> '{}'{}".format(
                    req.get('from'), req.get('to'), label_part),
            })

    findings.sort(key=lambda f: (f['rule'], f['msg']))
    return findings


def main(argv):
    """Escanea paths por pares .mmd + .diagram-contract.json. Exit 1 si hay ERROR."""
    if not argv:
        argv = ['examples/diagrams']

    all_findings = []
    pairs_checked = 0
    paths_to_scan = []

    for path in argv:
        if not os.path.exists(path):
            all_findings.append({
                'file': path, 'level': 'INFO', 'rule': 'PATH_MISSING',
                'msg': 'path no existe: {}'.format(path),
            })
            continue

        if os.path.isdir(path):
            found_mmd = False
            for root, dirs, files in os.walk(path):
                for f in sorted(files):
                    if f.lower().endswith('.mmd'):
                        found_mmd = True
                        paths_to_scan.append(os.path.join(root, f))
            if not found_mmd:
                all_findings.append({
                    'file': path, 'level': 'INFO', 'rule': 'PATH_MISSING',
                    'msg': 'no hay archivos .mmd en: {}'.format(path),
                })
        else:
            paths_to_scan.append(path)

    for mmd_path in paths_to_scan:
        base, _ = os.path.splitext(mmd_path)
        contract_path = base + '.diagram-contract.json'
        if not os.path.exists(contract_path):
            all_findings.append({
                'file': mmd_path.replace('\\', '/'), 'level': 'WARNING', 'rule': 'CONTRACT_MISSING',
                'msg': 'falta el contrato: {}'.format(contract_path.replace('\\', '/')),
            })
            continue
        pairs_checked += 1
        all_findings.extend(validate_diagram(mmd_path, contract_path))

    for f in all_findings:
        print('{} [{}] {}: {}'.format(f['level'], f['rule'], f['file'], f['msg']))

    error_count = sum(1 for f in all_findings if f['level'] == 'ERROR')
    warning_count = sum(1 for f in all_findings if f['level'] == 'WARNING')

    print()
    print('Resumen: {} error(es), {} warning(s), {} diagrama(s) verificados'.format(
        error_count, warning_count, pairs_checked
    ))

    return 1 if error_count > 0 else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
