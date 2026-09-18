# Contributing to Rosa_Brain

Thank you for helping make this local agent stronger.

## Principles

- **Local-first:** core intelligence must run without cloud LLMs.
- **Defensive security only:** OWASP-style hardening/secure coding OK; no offensive exploits.
- **No secrets in git:** tokens, passwords, private keys never committed.
- **Reproducible:** scripts + docs for Windows CUDA setups preferred.

## Dev setup

1. Fork and clone
2. Create venv, install `requirements.txt` and editable package
3. Run API with `run.bat` or `uvicorn rosa_brain.api:app --host 127.0.0.1 --port 8765`
4. Frontend: `cd frontend && npm install && npm run build` (builds into `rosa_brain/static/app`)

## Good first contributions

- Expand original skill corpora (not scraped copyrighted tutorials verbatim)
- Improve agent tool loop / sandboxed tools
- Tests for API and learning status
- UI/UX polish (Vue 3, RTL Persian)
- keep_alive / learner stability on Windows
- Documentation and examples

## PR checklist

- [ ] No `.venv` / `*.pt` / secrets
- [ ] Defensive-only security content
- [ ] Notes how to test locally
- [ ] UI text UTF-8 OK for Persian if touched
