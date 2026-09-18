# Rosa_Brain

**Independent from-scratch local cognitive agent** built with PyTorch.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org/)
[![Vue 3](https://img.shields.io/badge/UI-Vue%203-42b883.svg)](https://vuejs.org/)

> **EN:** A self-contained learning brain that trains on *your* GPU — no cloud LLM, no Ollama, no pretrained base model as the mind.  
> **FA:** یک مغز یادگیری مستقل که روی GPU خودت آموزش می‌بیند — بدون LLM ابری، بدون Ollama، بدون مدل پایه ازپیش‌آموزش‌دیده به‌عنوان هسته.

**Public repo:** https://github.com/RambodTaati/Rosa_Brain

---

## Why Rosa_Brain exists

Most “AI agents” wrap a remote model API. Rosa_Brain takes the opposite path:

1. **Own the weights** — a small byte-level neural net is initialized randomly and trained locally.
2. **Own the loop** — think → act (sandboxed tools) → reflect (experience memory).
3. **Own the curriculum** — language understanding, PostgreSQL, defensive security, OS skills, professional programming, web-language topics.
4. **Stay open** — MIT license; collaboration welcome to make trained domains stronger.

It will not match a frontier cloud model on open-ended chat. It *is* designed to become excellent in the domains it trains on, with full local control.

---

## Features

| Area | What you get |
|------|----------------|
| **Local brain** | PyTorch TinyBrainNet + meaning/classify head; CUDA when available (e.g. RTX 5090) |
| **API** | FastAPI on `http://127.0.0.1:8765` — chat, learning status, resources, projects, skills, MCP registries |
| **UI** | Vue 3 + TypeScript + Vite — Chat/Projects, Training dashboard, Skills, MCP |
| **Tools** | Sandboxed workspace FS + allowlisted shell (`/ls`, `/read`, `/write`, shell) |
| **Memory** | Semantic memory + experience lessons |
| **Training** | Auto curriculum scripts + `keep_alive` watchdog |
| **Skills / MCP** | Local registries (prepare/enable); extend without cloud brain lock-in |
| **Policy** | Defensive security only — no exploit/PoC content |

---

## Architecture (short)

```
Browser UI (Vue) ──► FastAPI (rosa_brain.api)
                         │
                         ├─ Brain (think / act / reflect)
                         ├─ ModelManager (train / classify / checkpoint)
                         ├─ SandboxTools + WebLearner + Memory
                         └─ data/ (corpora, state, registries)
scripts/ ── auto_skills / auto_web_languages / exams / keep_alive.ps1
```

---

## Requirements

- Windows 10/11 recommended (scripts include `.bat` / `.ps1`)
- Python 3.12+
- Optional but recommended: NVIDIA GPU + CUDA PyTorch wheel
- Node.js 18+ only if you rebuild the frontend

---

## Quick start

```powershell
git clone https://github.com/RambodTaati/Rosa_Brain.git
cd Rosa_Brain
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt
pip install -e .
.\run.bat
```

Open **http://127.0.0.1:8765/**

Optional keep-alive (API + learner watchdog):

```powershell
.\keep_alive.bat
```

### Rebuild UI

```powershell
cd frontend
npm install
npm run build
```

Output goes to `rosa_brain/static/app/`.

---

## Training overview

Curriculum order (high level):

1. English / Persian language mastery & meaning detection  
2. Skills path: PostgreSQL → defensive security → Windows/Ubuntu → fullstack agent → **Pro programmer**  
3. Web languages topics (original local corpus covering HTML/CSS/JS/TS/Python/SQL/… — not scraped copyrighted tutorial dumps)

Useful scripts:

| Script | Role |
|--------|------|
| `scripts/auto_skills.py` | Skills / Pro programmer rounds |
| `scripts/auto_web_languages.py` | Web languages path (dedicated state) |
| `scripts/pro_exam.py` | Held-out professional exam |
| `scripts/web_languages_exam.py` | Web languages held-out exam |
| `scripts/keep_alive.ps1` | Restart API / correct learner mode |

Checkpoints (`*.pt`) are **gitignored** — train locally or share weights separately if you choose.

Dashboard: **http://127.0.0.1:8765/training**

---

## API highlights

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health + resource summary |
| GET | `/v1/resources` | CPU/RAM/GPU guidance |
| GET | `/v1/learning` | Live training status |
| POST | `/v1/chat` | Agent chat |
| POST | `/v1/classify` | Meaning / label classify |
| GET/POST | `/v1/projects` | Projects CRUD |
| GET/POST | `/v1/skills` | Skills registry |
| GET/POST | `/v1/mcp` | MCP registry |

---

## Project layout

```
rosa_brain/     # Python package: api, brain, model, tools, memory, registries
frontend/       # Vue 3 source
scripts/        # learners, exams, keep_alive
data/           # corpora, quizzes, learning state, registries (no secrets)
checkpoints/    # local weights (ignored)
workspace/      # sandboxed tool root
tests/          # slice tests
```

---

## Security & independence rules

- **No cloud LLM** as the core brain (no Ollama / hosted model API substitution).
- **Defensive-only** security education (OWASP-style hardening, secure coding).  
  **Forbidden:** exploit writeups, attack PoCs, offensive hacking guides.
- Do not commit secrets, tokens, or private keys.
- Tool shell is allowlisted; treat it as a sandbox, not full admin automation.

---

## Contributing

We want help from other programmers to deepen trained domains and harden the local agent loop.

1. Fork → branch → PR  
2. Read [CONTRIBUTING.md](CONTRIBUTING.md)  
3. Prefer tests + short notes on how you verified on Windows/CUDA  

Good first areas: corpora quality, agent tools, UI/RTL, learner stability, docs, exams.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Disclaimer

Rosa_Brain is an experimental local research/engineering system. Training quality depends on your hardware, corpus, and run length. Curriculum “100%” means gates for a defined path — not unlimited human-level intelligence.

---

## Links

- Repository: https://github.com/RambodTaati/Rosa_Brain  
- Issues: https://github.com/RambodTaati/Rosa_Brain/issues  
- Discussions: use Issues/PRs for collaboration for now  

**Built for local ownership. Improved together in the open.**
