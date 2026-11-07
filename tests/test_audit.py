import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from semantic_search_claim_audit import audit as a
from semantic_search_claim_audit.phrases import SEMANTICSEARCH, NOSEMANTICSEARCH

class AuditTests(unittest.TestCase):
    def test_semanticsearch(self):
        self.assertEqual(SEMANTICSEARCH, ('semantic search', 'semantic-search', 'semanticsearch', 'semantic search engine', 'semantic search engines', 'semantic search system', 'semantic search systems', 'semantic search feature', 'semantic search capability', 'semantic search support', 'supports semantic search', 'semantic search tool', 'semantic search api', 'semantic search model', 'semantic search models', 'semantic search pipeline', 'semantic search algorithm', 'semantic search library', 'semantic search framework', 'semantic search service', 'semantic search function', 'semantic retrieval', 'semantic retriever', 'semantic document search', 'semantic query', 'semantic queries', 'search semantically', 'searches semantically', 'semantically search', 'vector search', 'vector-search', 'vectorsearch', 'vector search engine', 'vector search engines', 'vector search system', 'vector search feature', 'vector search capability', 'supports vector search', 'vector search api', 'vector search tool', 'vector similarity search', 'similarity search', 'similarity-search', 'similarity search engine', 'embedding search', 'embedding-based search', 'embedding based search', 'search by meaning', 'search by semantic similarity', 'meaning-based search'))
    def test_nosemanticsearch(self):
        self.assertEqual(NOSEMANTICSEARCH, ('does not support semantic search', 'do not support semantic search', "doesn't support semantic search", "don't support semantic search", 'no semantic search', 'without semantic search', 'never performs semantic search', 'does not perform semantic search', 'semantic search not supported', 'semantic search unsupported', 'no semantic search support', 'lacks semantic search', 'missing semantic search', 'semantic search disabled', 'no semantic search capability', 'without semantic search support', 'does not provide semantic search', 'no semantic search model', 'semantic search not available', 'does not use semantic search', 'no vector search', 'without vector search', 'does not support vector search', 'no similarity search'))
    def test_generic_names(self):
        self.assertEqual(a.GENERIC_NAMES, ('semantic_search', 'search_semantic', 'vector_search', 'search_vectors', 'embedding_search', 'search_embeddings', 'similarity_search', 'search_similar', 'find_similar', 'similar_documents', 'retrieve_semantic', 'semantic_retrieve', 'embed_query', 'embed_and_search', 'search_by_embedding', 'semantic_lookup', 'lookup_semantic', 'rank_by_similarity', 'nearest_neighbors', 'find_semantic', 'semantic_match', 'match_semantic', 'vector_retrieve', 'retrieve_vectors'))
    def test_faiss_classes(self):
        self.assertEqual(a.FAISS_CLASSES, ('IndexFlatL2', 'IndexFlatIP', 'IndexHNSWFlat', 'IndexIVFFlat', 'IndexIDMap', 'IndexFlat'))
    def test_vector_database_classes(self):
        self.assertEqual(a.VECTOR_DATABASE_CLASSES, ('chromadb.Client', 'chromadb.PersistentClient', 'pinecone.Index', 'qdrant_client.QdrantClient', 'pymilvus.Collection', 'pymilvus.MilvusClient', 'weaviate.Client'))
    def test_similarity_names(self):
        self.assertEqual(a.SIMILARITY_NAMES, ('cos_sim', 'pytorch_cos_sim', 'semantic_search', 'cosine_similarity', 'cosine_sim'))

    def test_positive_routes(self):
        cases = [
            "m=SentenceTransformer('x'); m.encode(x); cos_sim(x,y)",
            "SentenceTransformer('x').encode(x); cosine_sim(x,y)",
            "import sentence_transformers as st; m=st.SentenceTransformer('x'); m.encode(x); cos_sim(x,y)",
            "from sentence_transformers import SentenceTransformer as S; S('x').encode(x); cos_sim(x,y)",
            "client.embeddings.create(x); cos_sim(x,y)",
            "embeddings.create(x); pytorch_cos_sim(x,y)",
            "Embedding.create(x); cosine_similarity(x,y)",
            "from openai import Embedding as E; E.create(x); cos_sim(x,y)",
            "from whatever import semantic_search as s; s(x)",
            "objects[0].semantic_search(x)",
            "factory().vector_search(x)",
            "(1).find_similar(x)",
        ]
        for name in a.SIMILARITY_NAMES:
            cases.append("SentenceTransformer('x').encode(x); " + name + '(x,y)')
            cases.append(f"from lib import {name} as compare; SentenceTransformer('x').encode(x); compare(x,y)")
        for name in a.FAISS_CLASSES:
            cases.extend([f'i=faiss.{name}(3); i.add(x); i.search(x)', f'faiss.{name}(3).add(x).search(x)', f'from faiss import {name} as I; i=I(3); i.add(x); i.search(x)'])
        for name in a.VECTOR_DATABASE_CLASSES:
            module, cls = name.split('.')
            cases.extend([f'd={name}(); d.query(x)', f'{name}().query(x)', f'from {module} import {cls} as C; C().query(x)'])
        for name in a.GENERIC_NAMES:
            cases.extend([f'x.{name}(x)', f'from anything import {name} as f; f(x)'])
        for source in cases:
            with self.subTest(source=source):
                self.assertTrue(a.evidence(source))

    def test_rejections(self):
        cases = [
            'import sentence_transformers, faiss, chromadb, pinecone, qdrant_client, pymilvus, weaviate, openai, torch, sklearn',
            'Elasticsearch().search(x)', 'Whoosh().search(x)', "cursor.execute('SELECT * FROM t WHERE x LIKE ?')", "cursor.execute('SELECT * FROM t WHERE t MATCH ?')", 're.search(x,y)',
            'BM25Okapi(x).get_scores(y)', 'TfidfVectorizer().fit_transform(x); cosine_similarity(x,y)',
            'SentenceTransformer(x)', 'SentenceTransformer(x).encode(x)', 'client.embeddings.create(x)', 'm.encode(x)', 'cos_sim(x,y)', 'cosine_similarity(x,y)',
            'faiss.IndexFlatL2(3)', 'i.add(x)', 'i.search(x)', 'i=faiss.IndexFlatL2(3); i.add(x)', 'i=faiss.IndexFlatL2(3); i.search(x)',
            'chromadb.Client()', 'd.query(x)', 'a=faiss.IndexFlatL2(3); b=faiss.IndexFlatL2(3); a.add(x); b.search(x)', 'chromadb.Client(); other.query(x)', "'semantic search vector search'", '# semantic search', '"""vector search"""', 'x.semantic_search', 'semantic_search',
            'subprocess.run(["semantic-search", "x"])',
            'def semantic_search(x): pass\nsemantic_search(x)',
            'from lib import semantic_search\ndef semantic_search(x): pass\nsemantic_search(x)',
            'class SentenceTransformer: pass\nSentenceTransformer(x).encode(x); cos_sim(x,y)',
            'import faiss as f\nclass f: pass\ni=f.IndexFlatL2(3); i.add(x); i.search(x)',
            'from lib import cosine_similarity\ndef cosine_similarity(x,y): pass\nSentenceTransformer(x).encode(x); cosine_similarity(x,y)',
            'from chromadb import Client\nclass Client: pass\nClient().query(x)',
        ]
        for source in cases:
            with self.subTest(source=source):
                self.assertFalse(a.evidence(source))

    def test_all_route_shadowing(self):
        cases = [
            'from openai import Embedding\nclass Embedding: pass\nEmbedding.create(x); cos_sim(x,y)',
            'def embeddings(): pass\nembeddings.create(x); cos_sim(x,y)',
        ]
        for name in a.GENERIC_NAMES:
            cases.append(f'from lib import {name}\ndef {name}(x): pass\n{name}(x)')
        for name in a.FAISS_CLASSES:
            cases.append(f'from faiss import {name}\nclass {name}: pass\ni={name}(3); i.add(x); i.search(x)')
        for name in a.VECTOR_DATABASE_CLASSES:
            module, cls = name.split('.')
            cases.append(f'from {module} import {cls}\nclass {cls}: pass\n{cls}().query(x)')
        for source in cases:
            with self.subTest(source=source):
                self.assertFalse(a.evidence(source))

    def test_matching(self):
        self.assertEqual(a.claims('does not support semantic search'), ([], ['does not support semantic search']))
        for phrase in ('semantic search engine', 'vector search engine'):
            self.assertEqual(a.claims(phrase), ([phrase], []))
        self.assertEqual(a.claims('SEMANTIC SEARCH'), (['semantic search'], []))
        self.assertEqual(a.claims('vector search over image embeddings'), (['vector search'], []))
        self.assertEqual(a.claims('```py\nsemantic search\n```'), ([], []))
        self.assertEqual(a.claims('`semantic search`'), (['semantic search'], []))
        self.assertEqual(a.claims('semantic--search'), ([], []))
        self.assertEqual(a.claims('no semantic search support; semantic search engines'), (['semantic search engines'], ['no semantic search support']))

    def run_cli(self, root, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = a.main(['audit', str(root), *args])
        return code, output.getvalue()

    def test_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            readme = root/'README.md'
            readme.write_text('semantic search')
            code, out = self.run_cli(root)
            self.assertEqual(code, 2)
            self.assertIn('HIGH documented-semantic-search-claim-false', out)
            code, out = self.run_cli(root, '--json')
            self.assertIn('verdict', json.loads(out)[0])
            self.assertIn('message', json.loads(out)[0])
            self.assertEqual(self.run_cli(root, '--ignore', 'README')[0], 0)
            (root/'main.py').write_text('x.vector_search(q)')
            self.assertEqual(self.run_cli(root), (0, 'PASS\n'))
            readme.write_text('no semantic search')
            code, out = self.run_cli(root)
            self.assertEqual(code, 2)
            self.assertIn('HIGH documented-no-semantic-search-claim-false', out)
            (root/'main.py').unlink()
            self.assertEqual(self.run_cli(root)[0], 0)
            readme.write_text('Plain documentation')
            self.assertEqual(self.run_cli(root), (0, 'PASS\n'))
            (root/'tests').mkdir()
            (root/'tests/fixture.txt').write_text('semantic search')
            self.assertEqual(self.run_cli(root)[0], 0)
            self.assertIn('MEDIUM', self.run_cli(root)[1])
            self.assertEqual(self.run_cli(root, '--fail-on', 'medium')[0], 2)
            self.assertEqual(self.run_cli(root, '--ignore', 'tests', '--fail-on', 'medium')[0], 0)

    def test_module_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'README.md').write_text('SEMANTIC SEARCH')
            (root/'one.py').write_text('SentenceTransformer(x).encode(x)')
            (root/'two.py').write_text('cos_sim(x,y)')
            self.assertEqual(self.run_cli(root)[0], 2)

    def test_scope_and_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'docs/deep').mkdir(parents=True)
            (root/'docs/deep/guide.md').write_text('semantic search')
            (root/'other.md').write_text('semantic search')
            self.assertEqual(self.run_cli(root)[0], 2)
            self.assertEqual(self.run_cli(root, '--ignore', 'docs/')[0], 0)
            (root/'.venv').mkdir()
            (root/'.venv/evidence.py').write_text('x.vector_search(q)')
            self.assertEqual(self.run_cli(root)[0], 2)
            output = io.StringIO()
            with contextlib.redirect_stderr(output):
                self.assertEqual(self.run_cli(root, '--verbose')[0], 2)
            self.assertIn('docs/deep/guide.md', output.getvalue())
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(self.run_cli(root/'missing')[0], 1)
                with self.assertRaises(SystemExit) as error:
                    a.main(['audit', '--bad'])
            self.assertEqual(error.exception.code, 1)

    def test_ignore_before_repo(self):
        # Regression: --ignore used to take nargs='+', so it swallowed a
        # following repo path and the audit silently scanned '.' instead.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'README.md').write_text('Plain documentation')
            (root/'tests').mkdir()
            (root/'tests/fixture.txt').write_text('semantic search')
            (root/'main.py').write_text('x = 1\n')
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = a.main(['audit', '--ignore', 'tests', str(root)])
            self.assertEqual(code, 0)
            self.assertEqual(out.getvalue(), 'PASS\n')

    def test_version(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as error:
            a.main(['--version'])
        self.assertEqual(error.exception.code, 0)
        self.assertEqual(out.getvalue(), '0.1.0\n')

    def test_self_readme(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(a.claims((root/'README.md').read_text()), ([], []))
        self.assertEqual(self.run_cli(root)[0], 0)
        # Also inspect only shipped documentation.
        self.assertEqual(self.run_cli(root, '--ignore', 'tests')[0], 0)

if __name__ == '__main__':
    unittest.main()
