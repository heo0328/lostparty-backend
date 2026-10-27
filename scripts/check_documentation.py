#!/usr/bin/env python3
"""Read-only documentation, traceability and frozen-artifact checks. Run at repo root."""
import ast
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r'!?\[[^\]\n]*\]\(([^\s)]+)(?:\s+"[^"\n]*")?\)')


def heading_anchors(text):
    anchors = set(re.findall(r'<(?:a|span)\s+(?:id|name)=["\']([^"\']+)["\']', text))
    counts = Counter()
    fence = None
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(('```', '~~~')):
            marker = stripped[:3]
            fence = None if fence == marker else marker if fence is None else fence
            continue
        if fence or not re.match(r'^#{1,6}\s', line):
            continue
        heading = re.sub(r'^#{1,6}\s+', '', line).strip().rstrip('#').strip()
        heading = re.sub(r'<[^>]*>', '', heading).lower()
        # GitHub-style heading slugs retain Unicode letters, underscores and hyphens.
        slug = re.sub(r'[^\w\- ]', '', heading).replace(' ', '-')
        count = counts[slug]
        counts[slug] += 1
        anchors.add(slug + (f'-{count}' if count else ''))
    return anchors


def check_target(source, target, anchor_cache):
    if re.match(r'[a-zA-Z][\w+.-]*:', target) or target.startswith('/'):
        return
    path, _, fragment = target.partition('#')
    destination = (source.parent / unquote(path.split('?')[0])).resolve() if path else source.resolve()
    assert destination.exists(), f'{source.relative_to(ROOT)}: missing {target}'
    if fragment and destination.suffix == '.md':
        if destination not in anchor_cache:
            anchor_cache[destination] = heading_anchors(destination.read_text())
        assert unquote(fragment) in anchor_cache[destination], f'{source.relative_to(ROOT)}: missing anchor {target}'


def main():
    tracked = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
    markdown = {ROOT / p for p in tracked if p.endswith('.md') and (ROOT / p).is_file()}
    markdown.update((ROOT / 'docs').rglob('*.md'))
    anchors = {}
    links = 0
    external_links = 0
    for source in sorted(markdown):
        for target in LINK.findall(source.read_text()):
            if re.match(r'[a-zA-Z][\w+.-]*:', target) or target.startswith('/'):
                external_links += 1
                continue
            check_target(source, target, anchors)
            links += 1

    docs = ROOT / 'docs'
    for path in docs.rglob('*.json'):
        json.loads(path.read_text())
    python_files = list(docs.rglob('*.py')) + list((ROOT / 'tests').glob('*.py')) + [Path(__file__).resolve()]
    for path in python_files:
        content = path.read_text()
        ast.parse(content, filename=str(path))
        for literal in re.findall(r'''Path\(['"](docs/[^'"]+)['"]\)''', content):
            assert (ROOT / literal).exists(), f'{path.relative_to(ROOT)}: missing {literal}'

    source_map = json.loads((docs / 'engineering/documentation/source-map.json').read_text())
    entries = source_map['entries']
    assert len(entries) == source_map['source_count'] == len({e['source'] for e in entries})
    baseline = source_map['baseline_commit']
    expected_sources = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', baseline, '--', 'docs'], cwd=ROOT, text=True).splitlines()
    assert {e['source'] for e in entries} == set(expected_sources), 'Source inventory must cover the complete baseline'
    immutable_json = 0
    archived_bodies = 0
    for entry in entries:
        preserved = ROOT / entry['preserved_at']
        assert preserved.is_file(), entry['preserved_at']
        original = subprocess.check_output(['git', 'show', baseline + ':' + entry['source']], cwd=ROOT)
        assert hashlib.sha256(original).hexdigest() == entry['source_sha256'], entry['source']
        if preserved.suffix == '.json':
            assert preserved.read_bytes() == original, f'Frozen JSON changed: {preserved}'
            immutable_json += 1
        if entry['treatment'] == '본문 통합·원문 보관':
            text = preserved.read_text().split('\n\n', 1)[1]
            # Only the relocation banner and link destinations may differ.
            def without_targets(value):
                return LINK.sub(lambda m: m[0][:m.start(1)-m.start()] + '<target>' + m[0][m.end(1)-m.start():], value)
            assert without_targets(text) == without_targets(original.decode()), f'Original body changed: {preserved}'
            archived_bodies += 1
        for target in entry['current_documents']:
            check_target(docs / 'source.md', '../' + target, anchors)
        for section in entry['sections']:
            for target in section['destinations'] + section.get('current_reference', []):
                check_target(docs / 'source.md', '../' + target, anchors)
        for dependency in entry['dependent_files']:
            assert (ROOT / dependency).exists(), dependency

    contract = json.loads((ROOT / 'openapi/two-cycle.openapi.yaml').read_text())
    expected = {(method.upper(), path, operation['operationId']) for path, methods in contract['paths'].items()
                for method, operation in methods.items() if method in {'get', 'post', 'put', 'patch', 'delete', 'head', 'options'}}
    api_map = json.loads((docs / 'engineering/documentation/api-map.json').read_text())['operations']
    actual = {(row['method'], row['path'], row['operation_id']) for row in api_map}
    assert len(api_map) == len(actual) and actual == expected, 'API classification is incomplete or stale'
    for row in api_map:
        destination = docs / (row['topic'] if row['topic'].startswith('engineering/') else 'features/' + row['topic']) / 'README.md'
        assert destination.is_file(), row['topic']
        assert row['path'] in destination.read_text(), f'Unlisted operation: {row}'

    for line in (ROOT / 'Dockerfile.test').read_text().splitlines():
        if line.startswith('COPY docs/'):
            _, source, destination = line.split()
            assert (ROOT / source).is_file(), source
            assert destination.removeprefix('./') == source, destination
    print(json.dumps({'markdown_files': len(markdown), 'relative_links_and_anchors_checked': links, 'external_links_not_fetched': external_links,
                      'baseline_sources': len(entries), 'source_headings': sum(len(e['sections']) for e in entries),
                      'archived_bodies_preserved': archived_bodies, 'frozen_json_bytes_preserved': immutable_json,
                      'api_operations_classified': len(api_map), 'json_python_paths_docker': 'PASS',
                      'runtime_api_db_tests_executed': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
