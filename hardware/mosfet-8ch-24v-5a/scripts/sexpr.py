"""Minimal S-expression reader/writer for KiCad files."""
import re

class Sym(str):
    """Unquoted atom."""

_TOK = re.compile(r'\s*(\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+)')

def parse(text):
    pos, stack, cur = 0, [], None
    root = None
    for m in _TOK.finditer(text):
        t = m.group(1)
        if t == '(':
            new = []
            if cur is not None:
                cur.append(new)
                stack.append(cur)
            cur = new
        elif t == ')':
            if stack:
                cur = stack.pop()
            else:
                root = cur
        elif t.startswith('"'):
            cur.append(re.sub(r'\\(.)', lambda m: '\n' if m.group(1) == 'n' else m.group(1), t[1:-1]))
        else:
            cur.append(Sym(t))
    return root

def dump(node, indent=0):
    if isinstance(node, list):
        simple = all(not isinstance(c, list) for c in node)
        if simple:
            return '(' + ' '.join(dump(c) for c in node) + ')'
        out = '(' + dump(node[0])
        for c in node[1:]:
            if isinstance(c, list):
                out += '\n' + '  ' * (indent + 1) + dump(c, indent + 1)
            else:
                out += ' ' + dump(c)
        return out + '\n' + '  ' * indent + ')'
    if isinstance(node, Sym):
        return str(node)
    if isinstance(node, str):
        return '"' + node.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'
    return str(node)

def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]
