# Rosa_Brain

Independent **from-scratch** local cognitive agent in PyTorch.

**Goals:** self-contained learning brain · no cloud LLM dependency · defensive security only · open collaboration.

## What this is

- Tiny byte-level neural net trained **locally** (CUDA when available)
- FastAPI app + Vue 3 UI (chat, training dashboard, Skills, MCP registries)
- Skills curriculum (PostgreSQL → defensive security → OS → pro programmer → web languages topics)
- Sandboxed tools (workspace filesystem + allowlisted shell)
- **No** Ollama / cloud model APIs / pretrained base LLMs as the brain

## Quick start (Windows)

```powershell
cd Rosa_Brain
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt
pip install -e .
.\run.bat
```

Open http://127.0.0.1:8765/

## Layout

```
rosa_brain/     # API, brain, model, tools, memory, learning status
frontend/       # Vue 3 + Vite + TypeScript UI
scripts/        # auto learners, keep_alive, exams
data/           # corpora, registries, learning state (no secrets)
checkpoints/    # local weights (gitignored *.pt)
workspace/      # sandboxed tool root
```

## Contributing

We want help from other programmers to make Rosa_Brain stronger in its trained domains while staying **fully local**.

1. Fork → branch → PR
2. Keep **no cloud LLM** as the core brain
3. Security content must stay **defensive only** (no exploit/PoC/attack guides)
4. Prefer reproducible local training scripts + tests
5. Do not commit `.venv`, weights (`*.pt`), or secrets

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).

## Status

Active research / engineering project. Training dashboards and agent tooling evolve quickly; PRs welcome.
