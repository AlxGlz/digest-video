"""Conservative inline-link checks, followed by Pandoc's real parser at build time."""
import json
import re
from common import execute

LINK = re.compile(r'(!?\[[^\]\n]*\])\((<[^>\n]+>|[^\s)]+)(\s+"[^"\n]*")?\)')
MARKER = re.compile(r'<!--\s*block:([a-zA-Z0-9_-]+)\s*-->')


def visible(text):
    """Mask code while retaining offsets. Actual link semantics are checked with Pandoc."""
    chars = list(text)
    fence = None
    offset = 0
    for line in text.splitlines(keepends=True):
        m = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        masked = fence is not None or m is not None or line.startswith(('    ', '\t'))
        if m:
            if fence is None:
                fence = m.group(1)
            elif m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
                fence = None
        if masked:
            chars[offset:offset+len(line)] = ['\n' if c == '\n' else ' ' for c in line]
        offset += len(line)
    result = ''.join(chars)
    for match in re.finditer(r'(`+)([\s\S]*?)(?<!`)\1(?!`)', result):
        chars[match.start():match.end()] = ['\n' if c == '\n' else ' ' for c in match.group()]
    result = ''.join(chars)
    for match in re.finditer(r'<!--.*?-->', result, re.S):
        if not MARKER.fullmatch(match.group()):
            chars[match.start():match.end()] = [' ']*len(match.group())
    return ''.join(chars)


def links(text):
    for match in LINK.finditer(visible(text)):
        # Escaped link labels are literal text, including an odd run of backslashes.
        before = text[:match.start()]
        if (len(before)-len(before.rstrip('\\'))) % 2 == 0:
            yield match


def replace_links(text, transform):
    for match in reversed(list(links(text))):
        text = text[:match.start()] + transform(match) + text[match.end():]
    return text


def block_links(text):
    markers = list(MARKER.finditer(visible(text)))
    result = {}
    for i, marker in enumerate(markers):
        stop = markers[i+1].start() if i+1 < len(markers) else len(text)
        result[marker.group(1)] = [m.group(2).strip('<>') for m in links(text[marker.end():stop])
                                  if not m.group(1).startswith('!')]
    return result


def parsed_links(path, pandoc, log):
    """Parse with the same Markdown reader used for PDF, excluding code and image targets."""
    stdout, _ = execute([pandoc, str(path), '-f', 'markdown', '-t', 'json'], log)
    ast = json.loads(stdout)
    result, blocks, current = [], {}, None
    def walk(node):
        nonlocal current
        if isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, dict):
            if node.get('t') in ('RawBlock', 'RawInline'):
                for ident in MARKER.findall(node['c'][1]):
                    current = ident
                    blocks.setdefault(ident, [])
            if node.get('t') == 'Link':
                target = node['c'][-1][0]
                result.append(target)
                if current is not None:
                    blocks[current].append(target)
            walk(node.get('c', []))
    walk(ast['blocks'])
    return result, blocks
