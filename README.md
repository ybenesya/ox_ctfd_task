## OX CTFd Task

Home assignment for OX Security - CTFd insights tool.

AI assistance used: OpenAI Codex (Codex CLI, GPT-5).

### Requirements covered
- Latest 3 releases for `CTFd/CTFd`.
- Repo stats: forks, stars, contributors, pull requests.
- Contributors ranked by PR count (descending).
- Commit graph for a merged branch written to `.dot` (Graphviz + pydot).
- Logging to stdout or file with optional debug mode.
- Packaged as an installable Python package.

### Prerequisites
- Python 3.10+
- Git
- Graphviz (for generating the `.dot` commit graph)

### Install
```bash
python -m pip install -e .
```

### Usage
```bash
ox-ctfd-task --token <TOKEN>
```

Example (log to file):
```bash
ox-ctfd-task --token <TOKEN> --log-dest file --log-file-path logs.txt
```

Example (build commit graph):
```bash
ox-ctfd-task --token <TOKEN> --branch <MERGED_BRANCH>
```

### Flags
| Flag | Description | Required/Optional | Default |
| --- | --- | --- | --- |
| `--token` | GitHub Personal Access Token. | Required | None |
| `--owner` | GitHub repository owner/org. | Optional | `ybenesya` |
| `--repo` | GitHub repository name. | Optional | `CTFd` |
| `--branch` | Branch name (merged to main) to build a commit graph for. | Optional | `ybenesya-patch-2` |
| `--log-dest` | Where to write logs: `stdout` or `file`. | Optional | `stdout` |
| `--log-file-path` | Log file path (required when `--log-dest=file`). | Optional | None |
| `--debug` | Enable debug logging. | Optional | `false` |
| `--dot-out-path` | Output path for `.dot` graph file. | Optional | `graph.dot` |
| `--exclude-bot-users` | Exclude bot users in contributors list. | Optional | `false` |

### Tests
```bash
pip install -e .[dev]
pytest
```
