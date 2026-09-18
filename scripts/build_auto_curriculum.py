# -*- coding: utf-8 -*-
"""Build English-first curriculum + auto learner."""
from __future__ import annotations

from pathlib import Path
import textwrap

ROOT = Path(r"D:\Rosa_Brain")
CORPUS = ROOT / "data" / "corpus"
EN = CORPUS / "english"
FA = CORPUS / "persian"
EN.mkdir(parents=True, exist_ok=True)
FA.mkdir(parents=True, exist_ok=True)
(ROOT / "scripts").mkdir(parents=True, exist_ok=True)

# --- English: foundational + conversational + meaning ---

(EN / "01_alphabet_sounds.txt").write_text(
    textwrap.dedent(
        """\
        The English alphabet has 26 letters.
        a b c d e f g h i j k l m n o p q r s t u v w x y z
        A B C D E F G H I J K L M N O P Q R S T U V W X Y Z
        Vowels are a e i o u, and sometimes y.
        Consonants are the other letters.
        Common sounds: th as in the, sh as in she, ch as in chair, ng as in singing.
        Numbers: zero one two three four five six seven eight nine ten twenty thirty hundred thousand.
        0 1 2 3 4 5 6 7 8 9 10 20 50 100 1000.
        """
    ),
    encoding="utf-8",
)

(EN / "02_core_vocabulary.txt").write_text(
    textwrap.dedent(
        """\
        People: I you he she we they person man woman child friend family teacher student.
        Time: now today yesterday tomorrow morning afternoon evening night week month year.
        Place: here there home school work city street room kitchen office online.
        Actions: be have do go come see say know think want need make take give find use learn teach help.
        Feelings: happy sad angry tired calm confused sure unsure curious grateful.
        Objects: book phone computer table chair water food money key door window.
        Descriptors: big small new old good bad fast slow easy hard true false important.
        Connectors: and or but because so if then when while although however therefore.
        Politeness: please thank you thanks sorry excuse me you are welcome.
        """
    ),
    encoding="utf-8",
)

(EN / "03_grammar_patterns.txt").write_text(
    textwrap.dedent(
        """\
        Present simple: I work. She works. They work. I do not work. Does he work?
        Present continuous: I am learning. She is reading. Are you listening?
        Past simple: I went home. She said hello. Did you see it? I did not know.
        Future: I will help you. We are going to start. What will happen next?
        Questions: What is this? Where are you? Who said that? Why did it fail? How does it work? Which one is better?
        Negation: I do not understand yet. That is not ready. Never give up.
        Modals: I can help. You should rest. We must be careful. It might work. Could you explain?
        Conditionals: If it rains, stay inside. If you practice, you improve. If I knew, I would tell you.
        Pronouns: I me my mine / you your yours / he him his / she her hers / we us our / they them their.
        Articles: a book, an idea, the brain, the English language.
        """
    ),
    encoding="utf-8",
)

dialogues = []
pairs = [
    ("Hi", "Hello. How can I help you today?"),
    ("How are you?", "I am doing well, thank you. How about you?"),
    ("What is your name?", "My name is Rosa Brain."),
    ("What do you do?", "I learn from experience and help Rosa through an API."),
    ("Can you explain that simply?", "Yes. I will use short clear sentences."),
    ("I do not understand.", "No problem. I will say it another way."),
    ("What does meaning mean?", "Meaning is the idea a sentence is trying to communicate."),
    ("Are you sure?", "I am reasonably sure based on what I have learned so far."),
    ("Thanks", "You are welcome."),
    ("Goodbye", "Goodbye. Talk to you soon."),
    ("What time is it conceptually?", "Time tells us when something happens: now, before, or later."),
    ("I am frustrated.", "I hear you. Let's slow down and solve one piece at a time."),
    ("Can we chat casually?", "Sure. We can talk in everyday conversational English."),
    ("What is the point?", "The point is the main idea you should remember."),
    ("Tell me in plain English.", "Okay. Here is the plain version."),
]
for u, a in pairs:
    dialogues.append(f"User: {u}\nBrain: {a}\n")
(EN / "04_conversation.txt").write_text("\n".join(dialogues), encoding="utf-8")

qa = []
facts = [
    ("The cat is on the sofa.", "Where is the cat?", "On the sofa."),
    ("Rosa trains the brain every evening.", "When does Rosa train the brain?", "Every evening."),
    ("English is learned before Persian in this curriculum.", "Which language comes first?", "English."),
    ("A question asks for information.", "What does a question do?", "It asks for information."),
    ("Understanding means grasping the intended meaning.", "What is understanding?", "Grasping the intended meaning."),
    ("Conversation uses everyday spoken language.", "What is conversation?", "Everyday spoken language between people."),
    ("If someone says they are starving, they are very hungry.", "What does starving mean here?", "Very hungry."),
    ("Break a leg means good luck, not real injury.", "What does break a leg mean?", "Good luck."),
    ("The store is closed, so we cannot buy milk now.", "Can we buy milk now?", "No."),
    ("She left because she was tired.", "Why did she leave?", "Because she was tired."),
]
for text, q, a in facts:
    qa.append(f"Text: {text}\nQuestion: {q}\nAnswer: {a}\nMeaning: The answer comes from the text.\n")
(EN / "05_comprehension_meaning.txt").write_text("\n".join(qa), encoding="utf-8")

(EN / "06_spoken_english.txt").write_text(
    textwrap.dedent(
        """\
        Spoken English often shortens words: I'm, you're, don't, can't, won't, it's, that's.
        Fillers exist but meaning matters more: well, you know, I mean, kind of, basically.
        Soft requests: Could you help me for a second? Would you mind explaining that?
        Agreement: Yeah. Exactly. That makes sense. I see what you mean.
        Disagreement politely: I see your point, but I think about it differently.
        Clarifying: Sorry, what do you mean by that? Do you mean X or Y?
        Summarizing: So basically, we need to finish English first, then Persian.
        Emotions in talk: I'm excited. I'm worried. I'm curious. I'm relieved.
        Turn-taking: Go ahead. Your turn. Let me finish this thought.
        Repair: Wait, I misspoke. What I meant was...
        """
    ),
    encoding="utf-8",
)

(EN / "07_concepts.txt").write_text(
    textwrap.dedent(
        """\
        Concept: cause and effect. Rain causes wet streets. Practice causes improvement.
        Concept: intent. The speaker wants the listener to understand a request or idea.
        Concept: context. The same word can mean different things in different situations.
        Concept: literal vs figurative. Cold can mean low temperature or unfriendly behavior.
        Concept: paraphrase. Saying the same meaning with different words.
        Concept: entailment. If all dogs are animals and Rex is a dog, then Rex is an animal.
        Concept: contradiction. It cannot be both open and closed at the same time.
        Concept: topic. Stay on the main subject unless the user changes it.
        Goal for Rosa Brain: understand conversational English meaning, then learn Persian.
        """
    ),
    encoding="utf-8",
)

# Expand English by repeating patterns with substitutions for volume
extra = []
subjects = ["I", "You", "We", "They", "Rosa", "The student", "The teacher", "My friend"]
verbs = [
    ("learn English", "learned English", "will learn English"),
    ("understand the meaning", "understood the meaning", "will understand the meaning"),
    ("ask a question", "asked a question", "will ask a question"),
    ("give a clear answer", "gave a clear answer", "will give a clear answer"),
    ("practice every day", "practiced every day", "will practice every day"),
]
for s in subjects:
    for base, past, fut in verbs:
        extra.append(f"{s} {base}.")
        extra.append(f"{s} {past}.")
        extra.append(f"{s} {fut}.")
        extra.append(f"Does {s if s not in ('I','You','We','They') else 'this person'} {base}? Yes.")
        extra.append(f"What does {s} do? {s} {base}.")
(EN / "08_pattern_drill.txt").write_text("\n".join(extra), encoding="utf-8")

# --- Persian (phase 2; created now, trained later) ---
(FA / "01_core.txt").write_text(
    textwrap.dedent(
        """\
        من رزا برین هستم. اول انگلیسی یاد گرفتم، حالا فارسی یاد می‌گیرم.
        سلام. حال شما چطور است؟ ممنون، خوبم.
        لطفاً واضح بگو. متوجه نشدم. یعنی چه؟
        معنی یعنی مفهومی که جمله می‌خواهد برساند.
        پرسش می‌پرسد. پاسخ جواب می‌دهد. گفتگو زبان روزمره است.
        """
    ),
    encoding="utf-8",
)

(FA / "02_conversation.txt").write_text(
    textwrap.dedent(
        """\
        کاربر: سلام
        مغز: سلام. چطور می‌توانم کمک کنم؟
        کاربر: انگلیسی بلدی؟
        مغز: بله، اول انگلیسی را تمرین کردم.
        کاربر: فارسی بلدی؟
        مغز: دارم فارسی محاوره‌ای را یاد می‌گیرم.
        کاربر: منظورت چیست؟
        مغز: منظورم همان مفهوم اصلی حرف تو است.
        """
    ),
    encoding="utf-8",
)

# Auto learner
(ROOT / "scripts" / "auto_learn.py").write_text(
    r'''# -*- coding: utf-8 -*-
"""Automatic curriculum learner: English first, then Persian."""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from rosa_brain.config import settings
from rosa_brain.model import ModelManager

PHASES = {
    "english": {
        "glob": "english/*.txt",
        "min_steps": int(os.environ.get("ROSA_EN_STEPS", "8000")),
        "target_loss": float(os.environ.get("ROSA_EN_TARGET_LOSS", "0.45")),
        "min_bytes": 50_000,
    },
    "persian": {
        "glob": "persian/*.txt",
        "min_steps": int(os.environ.get("ROSA_FA_STEPS", "5000")),
        "target_loss": float(os.environ.get("ROSA_FA_TARGET_LOSS", "0.50")),
        "min_bytes": 20_000,
    },
}


def load_corpus(glob_pat: str, min_bytes: int) -> str:
    corpus = settings.data_dir / "corpus"
    parts = []
    for p in sorted(corpus.glob(glob_pat)):
        parts.append(p.read_text(encoding="utf-8", errors="replace"))
    if not parts:
        raise SystemExit(f"No corpus for pattern {glob_pat}")
    text = "\n\n".join(parts)
    while len(text.encode("utf-8")) < min_bytes:
        text = text + "\n\n" + text
    return text


def state_path() -> Path:
    return settings.data_dir / "auto_learn_state.json"


def load_state() -> dict:
    p = state_path()
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"phase": "english", "phase_steps": 0, "history": []}


def save_state(st: dict) -> None:
    state_path().write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def train_phase(mgr: ModelManager, phase: str, st: dict, chunk: int = 25) -> dict:
    cfg = PHASES[phase]
    text = load_corpus(cfg["glob"], cfg["min_bytes"])
    print(json.dumps({
        "event": "phase_start",
        "phase": phase,
        "device": mgr.device,
        "params": sum(p.numel() for p in mgr.net.parameters()),
        "bytes": len(text.encode("utf-8")),
        "min_steps": cfg["min_steps"],
        "target_loss": cfg["target_loss"],
        "phase_steps_done": st.get("phase_steps", 0),
    }, ensure_ascii=False), flush=True)

    recent = []
    while True:
        result = mgr.train_on_text(text, steps=chunk)
        st["phase_steps"] = int(st.get("phase_steps", 0)) + chunk
        st["total_steps"] = int(result["train_steps_total"])
        recent.append(result["avg_loss"])
        if len(recent) > 20:
            recent = recent[-20:]
        avg_recent = sum(recent) / len(recent)
        row = {
            "event": "progress",
            "phase": phase,
            "phase_steps": st["phase_steps"],
            "total_steps": st["total_steps"],
            "chunk_loss": result["avg_loss"],
            "recent_avg_loss": avg_recent,
            "device": result["device"],
        }
        print(json.dumps(row, ensure_ascii=False), flush=True)
        st.setdefault("history", []).append(row)
        # keep history bounded
        st["history"] = st["history"][-500:]
        save_state(st)

        enough_steps = st["phase_steps"] >= cfg["min_steps"]
        good_loss = avg_recent <= cfg["target_loss"] and len(recent) >= 8
        if enough_steps and good_loss:
            done = {"event": "phase_done", "phase": phase, "phase_steps": st["phase_steps"], "recent_avg_loss": avg_recent}
            print(json.dumps(done, ensure_ascii=False), flush=True)
            return done


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once-phase", choices=["english", "persian", "all"], default="all")
    ap.add_argument("--chunk", type=int, default=25)
    args = ap.parse_args()

    mgr = ModelManager()
    mgr.load_if_exists()
    st = load_state()
    order = ["english", "persian"] if args.once_phase == "all" else [args.once_phase]

    # resume phase from state when running all
    if args.once_phase == "all" and st.get("phase") in PHASES:
        # continue from saved phase onward
        start = order.index(st["phase"]) if st["phase"] in order else 0
        order = order[start:]

    for phase in order:
        st["phase"] = phase
        if st.get("active_phase") != phase:
            st["active_phase"] = phase
            st["phase_steps"] = 0
            save_state(st)
        train_phase(mgr, phase, st, chunk=args.chunk)
        # move to next
        if phase == "english":
            st["phase"] = "persian"
            st["phase_steps"] = 0
            st["english_completed_at"] = time.time()
        elif phase == "persian":
            st["phase"] = "done"
            st["persian_completed_at"] = time.time()
        save_state(st)

    print(json.dumps({"event": "curriculum_done", "state": st["phase"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
''',
    encoding="utf-8",
)

# Update curriculum markdown
(ROOT / "data" / "curriculum.md").write_text(
    """# Rosa_Brain Automatic Curriculum

Order demanded by Rosa:
1. English first (full conversational understanding / meaning)
2. Then Persian
3. Then other languages later

## Auto start
- `auto_learn.bat` — runs continuous learner
- `run.bat` starts API and also launches auto-learn in background

## Train command
```
.venv\\Scripts\\python.exe scripts\\auto_learn.py --once-phase all
```

State file: `data/auto_learn_state.json`
""",
    encoding="utf-8",
)

# auto_learn.bat
(ROOT / "auto_learn.bat").write_text(
    """@echo off
setlocal
cd /d "%~dp0"
set "ROSA_BRAIN_ROOT=%~dp0"
if "%ROSA_BRAIN_ROOT:~-1%"=="\\" set "ROSA_BRAIN_ROOT=%ROSA_BRAIN_ROOT:~0,-1%"
set "PY=%~dp0.venv\\Scripts\\python.exe"
if not exist "%PY%" (
  echo [Rosa_Brain] venv missing
  pause
  exit /b 1
)
echo [Rosa_Brain] auto-learn starting: English first, then Persian
"%PY%" "%~dp0scripts\\auto_learn.py" --once-phase all
echo [Rosa_Brain] auto-learn finished
pause
""",
    encoding="ascii",
)

# Patch run.bat to start learner in background
run_bat = ROOT / "run.bat"
run_bat.write_text(
    """@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "ROSA_BRAIN_ROOT=%~dp0"
if "%ROSA_BRAIN_ROOT:~-1%"=="\\" set "ROSA_BRAIN_ROOT=%ROSA_BRAIN_ROOT:~0,-1%"
set "PY=%~dp0.venv\\Scripts\\python.exe"
set "HOST=127.0.0.1"
set "PORT=8765"

if not exist "%PY%" (
  echo [Rosa_Brain] venv not found. Run Setup-Windows.ps1 first.
  pause
  exit /b 1
)

REM Start auto-learn in background (English then Persian) if not already running.
for /f "tokens=2 delims=," %%P in ('tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH ^| find /I "auto_learn.py"') do set LEARN_UP=1
if not defined LEARN_UP (
  echo [Rosa_Brain] starting auto-learn in background...
  start "Rosa_Brain_AutoLearn" /MIN "%PY%" "%~dp0scripts\\auto_learn.py" --once-phase all
) else (
  echo [Rosa_Brain] auto-learn already running
)

"%PY%" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=2).read(); print('OK')" 1>nul 2>nul
if not errorlevel 1 (
  echo [Rosa_Brain] already running at http://127.0.0.1:8765
  echo Auto-learn is active in background.
  pause
  exit /b 0
)

for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8765 .*LISTENING"') do (
  echo [Rosa_Brain] freeing PID %%P on port 8765
  taskkill /F /PID %%P >nul 2>&1
)
timeout /t 1 /nobreak >nul

echo [Rosa_Brain] starting API at http://%HOST%:%PORT%
"%PY%" -m rosa_brain
echo.
echo [Rosa_Brain] server stopped.
pause
""",
    encoding="ascii",
)

en_files = list(EN.glob("*.txt"))
print("english_files", len(en_files), "bytes", sum(f.stat().st_size for f in en_files))
print("persian_files", len(list(FA.glob("*.txt"))))
print("READY")