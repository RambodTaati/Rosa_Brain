# Rosa_Brain Automatic Curriculum

Order demanded by Rosa:
1. English first (full conversational understanding / meaning)
2. Then Persian
3. Then other languages later

## Auto start
- `auto_learn.bat` — runs continuous learner
- `run.bat` starts API and also launches auto-learn in background

## Train command
```
.venv\Scripts\python.exe scripts\auto_learn.py --once-phase all
```

State file: `data/auto_learn_state.json`
