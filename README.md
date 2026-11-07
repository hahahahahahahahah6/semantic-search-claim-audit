# Documentation claim auditor

An offline, deterministic auditor for documentation about retrieval by meaning.
It uses only the standard library, makes no network or model calls, collects no
telemetry, and writes no files during an audit. Python 3.9 or newer is required.

## Usage

```sh
python3 -m pip install .
semantic-search-claim-audit audit .
semantic-search-claim-audit audit . --json --verbose
semantic-search-claim-audit audit . --ignore tests/ vendor/ --fail-on medium
python3 -m semantic_search_claim_audit --version
```

The repository defaults to the current directory. Root README.md and Markdown
files beneath docs are checked. Triple-backtick fenced blocks are excluded;
inline code counts as prose. Python files throughout the repository provide
evidence, excluding Git metadata, caches, and virtual environments. Repeated
ignore options skip paths by repository-relative prefix, including source files.
Test-directory fixtures can produce medium findings. High findings fail by
default; the medium threshold also fails for medium findings. Exit codes are
0 for passing the threshold, 2 for failing it, and 1 for usage or IO errors.
Verbose decisions go to standard error. JSON output is a list of findings,
each with verdict, message, severity, and path fields.

```text
documented-semantic-search-claim-false HIGH
documented-no-semantic-search-claim-false HIGH
```

A positive claim without recognized evidence is flagged. A denial contradicted
by recognized evidence is flagged. A denial without evidence passes. With no
claims, the audit passes.

## Differentiation

The following neighboring tools address different behaviors, in order:
matching words, suggesting items, producing answers, and writing text.
This auditor checks retrieval by meaning and document retrieval instead.

```text
search-claim-audit
recommendation-claim-audit
question-answering-claim-audit
text-generation-claim-audit
```

## Limitations

This is static pattern matching, not semantic judgement or runtime verification.
Exact substrings are recognized, not restatements. Matching is case insensitive,
with no stemming or hyphen normalization. Longest-first span blanking counts
each occurrence once under its longest phrase. Denial spans are removed first.
All parts of a source evidence route must appear in one module. Imports are
resolved, and locally defined functions or classes shadow route names.

The model route requires construction, encoding on that instance, and a
recognized comparison call. Hosted embedding creation requires a comparison
call. An index requires construction, addition, and a retrieval call. A database
requires construction and a query on the instance. Recognized generic method
calls also count. Imports, strings, comments, subprocess invocations, and
unbound references alone do not count.

An index triple counts even when its vectors represent images. A database
construction and query counts even if its collection holds non-text vectors.
A generic call on an unrelated object counts because its method name is shared.
The exact examples below can describe non-text retrieval: the first two can
refer to images, and the third to stored embeddings of any modality.

```text
FAISS
semantic_search(
vector search over image embeddings
similarity search across product photos
embedding search over audio clips
```

A TF-IDF ranker paired with a comparison call is deliberately excluded: ranking
shared words does not establish retrieval by meaning. Keyword indexes, BM25,
SQL matching, regular expressions, recommendation, answer production, and text
creation alone also do not establish the checked capability. Recognized source
patterns neither prove correctness nor establish what data is retrieved.

## Development

```sh
python3 -m unittest discover
python3 -m build
```

Released under the MIT license.
