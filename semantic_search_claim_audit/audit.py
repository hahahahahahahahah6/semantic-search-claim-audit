"""Deterministic documentation and Python source inspection."""
import argparse
import ast
import json
import sys
from pathlib import Path
from .phrases import SEMANTICSEARCH, NOSEMANTICSEARCH

GENERIC_NAMES = ('semantic_search', 'search_semantic', 'vector_search', 'search_vectors', 'embedding_search', 'search_embeddings', 'similarity_search', 'search_similar', 'find_similar', 'similar_documents', 'retrieve_semantic', 'semantic_retrieve', 'embed_query', 'embed_and_search', 'search_by_embedding', 'semantic_lookup', 'lookup_semantic', 'rank_by_similarity', 'nearest_neighbors', 'find_semantic', 'semantic_match', 'match_semantic', 'vector_retrieve', 'retrieve_vectors')
FAISS_CLASSES = ('IndexFlatL2', 'IndexFlatIP', 'IndexHNSWFlat', 'IndexIVFFlat', 'IndexIDMap', 'IndexFlat')
VECTOR_DATABASE_CLASSES = ('chromadb.Client', 'chromadb.PersistentClient', 'pinecone.Index', 'qdrant_client.QdrantClient', 'pymilvus.Collection', 'pymilvus.MilvusClient', 'weaviate.Client')
SIMILARITY_NAMES = ('cos_sim', 'pytorch_cos_sim', 'semantic_search', 'cosine_similarity', 'cosine_sim')

def prose(text):
    result = []
    fenced = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced:
            result.append(line.replace("`", ""))
    return "\n".join(result).lower()


def consume(text, phrases):
    found = []
    for phrase in sorted(phrases, key=len, reverse=True):
        start = text.find(phrase)
        while start >= 0:
            found.append(phrase)
            text = text[:start] + " " * len(phrase) + text[start + len(phrase):]
            start = text.find(phrase)
    return text, found


def claims(text):
    rest, denials = consume(prose(text), NOSEMANTICSEARCH)
    return consume(rest, SEMANTICSEARCH)[1], denials


def evidence(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    aliases = {}
    shadowed = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                aliases[item.asname or item.name.split('.')[0]] = item.name if item.asname else item.name.split('.')[0]
        elif isinstance(node, ast.ImportFrom):
            for item in node.names:
                aliases[item.asname or item.name] = (node.module or '') + '.' + item.name
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            shadowed.add(node.name)
    def name(node):
        if isinstance(node, ast.Name):
            if node.id in shadowed:
                return ''
            return aliases.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            base = name(node.value)
            if node.attr in shadowed or not base:
                return ''
            return base + '.' + node.attr
        if isinstance(node, ast.Call):
            return name(node.func)
        return '<expression>'
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    def tail(n):
        return name(n.func).split('.')[-1]
    for call in calls:
        if tail(call) in GENERIC_NAMES:
            if isinstance(call.func, ast.Attribute) or (isinstance(call.func, ast.Name) and call.func.id in aliases):
                return True
    similar = any(tail(n) in SIMILARITY_NAMES for n in calls)
    assigned = {}
    def kind(node):
        if isinstance(node, ast.Name):
            return assigned.get(node.id)
        if isinstance(node, ast.Call):
            resolved = name(node.func)
            last = resolved.split('.')[-1]
            if last == 'SentenceTransformer':
                return ('embedding', id(node))
            if last in FAISS_CLASSES:
                return ('faiss', id(node))
            if resolved in VECTOR_DATABASE_CLASSES or ('.' not in resolved and resolved in [s.split('.')[-1] for s in VECTOR_DATABASE_CLASSES]):
                return ('database', id(node))
            if isinstance(node.func, ast.Attribute):
                return kind(node.func.value)
        return None
    # Resolve aliases of constructed instances, including forward traversal order.
    for unused in range(len(calls) + 1):
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = kind(node.value)
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name) and value:
                        assigned[target.id] = value
    operations = {}
    for call in calls:
        if isinstance(call.func, ast.Attribute):
            route = kind(call.func.value)
            if route:
                operations.setdefault(route, set()).add(call.func.attr)
        resolved = name(call.func)
        if similar and (resolved.endswith('.embeddings.create') or resolved.endswith('.Embedding.create') or resolved in ('embeddings.create', 'Embedding.create')):
            return True
    return any((route[0] == 'embedding' and similar and 'encode' in methods) or (route[0] == 'faiss' and {'add', 'search'} <= methods) or (route[0] == 'database' and 'query' in methods) for route, methods in operations.items())


EXCLUDED = {'.git', '__pycache__', '.venv', 'venv', 'env', '.env'}


def audit(repo, ignore=(), verbose=False):
    repo = Path(repo)
    if not repo.is_dir():
        raise OSError('Repository is not a directory: ' + str(repo))
    paths = []
    decisions = []
    for path in sorted(repo.rglob('*')):
        rel = path.relative_to(repo).as_posix()
        if any(part in EXCLUDED for part in path.relative_to(repo).parts) or any((parent / 'pyvenv.cfg').is_file() for parent in path.parents if parent != repo and repo in parent.parents) or any(rel.startswith(p) for p in ignore):
            continue
        if path.is_file():
            paths.append(path)
    present = any(evidence(p.read_text(encoding='utf-8')) for p in paths if p.suffix == '.py')
    findings = []
    for path in paths:
        rel = path.relative_to(repo).as_posix()
        test = 'tests' in path.relative_to(repo).parts[:-1]
        doc = rel == 'README.md' or (rel.startswith('docs/') and path.suffix == '.md')
        if not (doc or test):
            continue
        positive, negative = claims(path.read_text(encoding='utf-8'))
        decisions.append(rel + ': ' + str(len(positive)) + ' positive, ' + str(len(negative)) + ' negative matches')
        if positive and not present:
            findings.append(dict(verdict='documented-semantic-search-claim-false', severity='HIGH' if doc else 'MEDIUM', path=rel, message='Documented capability has no recognized Python evidence.'))
        if negative and present and doc:
            findings.append(dict(verdict='documented-no-semantic-search-claim-false', severity='HIGH', path=rel, message='Documented denial contradicts recognized Python evidence.'))
    if verbose:
        print('Scope: README.md, docs/**/*.md, tests/ fixtures; Python modules', file=sys.stderr)
        for decision in decisions:
            print(decision, file=sys.stderr)
    return findings


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(1, message + '\n')


def main(argv=None):
    parser = Parser()
    parser.add_argument('--version', action='version', version='0.1.0')
    sub = parser.add_subparsers(dest='command', required=True)
    command = sub.add_parser('audit')
    command.add_argument('repo', nargs='?', default='.')
    command.add_argument('--json', action='store_true')
    command.add_argument('--verbose', action='store_true')
    command.add_argument('--ignore', action='append', default=[])
    command.add_argument('--fail-on', choices=['high', 'medium'], default='high')
    args = parser.parse_args(argv)
    try:
        findings = audit(args.repo, args.ignore, args.verbose)
    except (OSError, UnicodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(findings))
    elif findings:
        for finding in findings:
            print('{severity} {verdict} {path}: {message}'.format(**finding))
    else:
        print('PASS')
    return 2 if any(f['severity'] == 'HIGH' or args.fail_on == 'medium' for f in findings) else 0
