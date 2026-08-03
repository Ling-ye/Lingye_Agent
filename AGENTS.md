# AGENTS.md

These instructions apply to the entire repository.

## Working rules

- Prefer WSL/Linux when it is available and the repository toolchain works there. Keep one environment for Git, tests, builds, paths, and hashes during a release workflow.
- Preserve unrelated behavior and user changes. Do not rewrite working code while making documentation or release-only changes.
- Do not design compatibility layers for unrequested legacy data or APIs.
- After code, packaging, or release-contract changes, update this file and the relevant README or guide.
- Keep code and directories professional, explicit, and narrowly scoped.
- Keep source, configuration, and documentation files on LF line endings as defined by .gitattributes.

## Git and releases

- The user owns every Git commit. Agents must not run git commit, amend, rebase, or force-push.
- Do not stage files unless the user explicitly asks.
- Pushes, PR creation, tags, and GitHub Releases are separate external writes and require the requested authorization.
- Use short Chinese commit-message suggestions.
- Never move a published tag or silently replace a published release asset.

## Runtime data and secrets

- Never track .env files, API keys, SQLite runtime databases, knowledge-base contents, model weights, or generated indexes.
- memory_data, knowledge_base, and data_science_kb are runtime directories.
- Configuration committed to the repository must contain placeholders or local non-secret defaults only.

## Validation

Blocking quick release checks:

~~~bash
python -m pytest -q tests/test_release_contract.py tests/test_function_call_agent_unit.py tests/test_simple_calculator.py::test_calculator_tool
python -m build
python -m twine check dist/*
python scripts/verify_release_artifact.py dist/lingye_agent-0.1.0-py3-none-any.whl
~~~

Run the complete suite when practical:

~~~bash
python -m pytest
~~~

The complete suite currently contains slow and external-service scenarios. Report its exact result or timeout; do not claim it passed without a completed run.
