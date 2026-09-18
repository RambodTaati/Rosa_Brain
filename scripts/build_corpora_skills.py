# -*- coding: utf-8 -*-
from pathlib import Path
import json

ROOT = Path(r"D:\Rosa_Brain")
DATA = ROOT / "data"
CORPUS = DATA / "corpus"

def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")

write(CORPUS / "skills_postgres" / "01_core.txt", """
PostgreSQL is a relational database. Tables store rows and columns. Primary keys uniquely identify rows.
CREATE TABLE users (id BIGSERIAL PRIMARY KEY, email TEXT UNIQUE NOT NULL, created_at TIMESTAMPTZ DEFAULT now());
INSERT INTO users (email) VALUES ('rosa@example.com');
SELECT id, email FROM users WHERE email LIKE '%@example.com' ORDER BY id LIMIT 50;
UPDATE users SET email = 'new@example.com' WHERE id = 1;
DELETE FROM users WHERE id = 1;
Joins: SELECT u.email, o.total FROM users u JOIN orders o ON o.user_id = u.id;
Indexes speed lookups: CREATE INDEX ON orders (user_id);
Transactions: BEGIN; ... COMMIT; ROLLBACK undoes an open transaction.
FOREIGN KEY protects relations. Roles and GRANT set least privilege.
pg_dump is logical backup. EXPLAIN ANALYZE shows query plans.
Use parameterized queries to avoid SQL injection. Prefer migrations for schema changes.
""")
write(CORPUS / "skills_postgres" / "02_practice_qa.txt", """
Q: What does PRIMARY KEY do? A: Uniquely identifies each row and usually implies NOT NULL and an index.
Q: How do you prevent SQL injection in app code? A: Use parameterized queries, never concatenate user input into SQL.
Q: What is a transaction for? A: Keep multi-step writes atomic; commit or rollback together.
Q: When add an index? A: On columns used often in WHERE/JOIN with enough selectivity.
Q: What is pg_dump for? A: Logical backup of database objects and data.
""")

write(CORPUS / "skills_security_defensive" / "01_core.txt", """
Defensive security protects systems and users. Rosa_Brain learns defense only: no exploits, no attack playbooks, no PoCs.
Secure coding: validate input, encode output, least privilege, fail closed, keep secrets out of logs.
Defend OWASP-class issues: injection, broken auth, broken access control, misconfig, XSS/CSRF defenses, unsafe components, weak logging.
AuthN: strong credentials/passkeys, MFA when available, short-lived tokens.
AuthZ: check every request on the server; never trust client role flags.
Prefer TLS. Cookies: Secure, HttpOnly, SameSite as appropriate.
Hardening ideas for Windows and Ubuntu: least privilege, updates, firewall defaults, key-based SSH, separate service users.
Log auth failures and admin actions; never log passwords or tokens.
Incident mindset: contain, eradicate, recover, learn.
""")
write(CORPUS / "skills_security_defensive" / "02_practice_qa.txt", """
Q: What is least privilege? A: Grant only the minimum permissions needed for a task.
Q: How stop SQL injection defensively? A: Parameterized queries, validation, least DB privileges.
Q: Why check authorization on the server? A: Clients can be modified; server is the trust boundary.
Q: Should Rosa_Brain learn exploit code? A: No. Only defensive hardening and secure design.
Q: What must not be logged? A: Passwords, tokens, and other secrets.
""")

write(CORPUS / "skills_windows" / "01_core.txt", """
Windows professional use: NTFS permissions, services, Task Manager, Event Viewer concepts.
PowerShell: Get-ChildItem, Get-Content, Set-Content, Get-Service, Start-Service, Stop-Service, Get-Process.
Elevate only when required. Prefer reversible changes. Quote paths with spaces.
Firewall and updates matter. Scheduled Tasks automate recurring work.
As an agent: confirm destructive actions and log what changed.
""")
write(CORPUS / "skills_windows" / "02_practice_qa.txt", """
Q: List files in PowerShell? A: Get-ChildItem.
Q: Read a text file? A: Get-Content -Path file.
Q: When run elevated? A: Only for tasks that truly need admin rights.
""")

write(CORPUS / "skills_ubuntu" / "01_core.txt", """
Ubuntu professional use: bash, /etc /var /home, permissions, processes.
ls, cat, cp, mv; careful with rm. chmod/chown for permissions.
apt install with care. systemctl for services. journalctl for logs.
Prefer SSH keys. df -h, free -h, ss -lntp for ops checks.
As an agent: avoid destructive rm -rf, backup first, sparse sudo.
""")
write(CORPUS / "skills_ubuntu" / "02_practice_qa.txt", """
Q: Install a package? A: sudo apt update && sudo apt install name.
Q: Check a service? A: systemctl status service-name.
Q: Least privilege on Linux? A: Normal user by default; sudo only when needed.
""")

write(CORPUS / "skills_fullstack_agent" / "01_core.txt", """
Full-stack professional agent: clarify goal, inspect state, plan slices, implement, verify, report.
UI complete states; API authZ and safe errors; DB migrations and backups.
Designer care: hierarchy, contrast, RTL when needed.
Never send messages or spend money unasked; prefer drafts; confirm destructive ops.
""")
write(CORPUS / "skills_fullstack_agent" / "02_practice_qa.txt", """
Q: What is a vertical slice? A: One user-visible behavior end-to-end.
Q: Before dropping a table? A: Backup/confirm and check dependents.
Q: What does verify mean? A: Prove with a check that the change works.
""")

quizzes = []
def add(skill, q, a):
    quizzes.append({"skill": skill, "question": q, "answer": a, "text": f"SKILL {skill} Q: {q} A: {a}"})
add("postgres", "What does PRIMARY KEY do?", "Uniquely identifies each row.")
add("postgres", "How prevent SQL injection?", "Use parameterized queries.")
add("postgres", "What is BEGIN/COMMIT?", "Transaction boundaries for atomic writes.")
add("postgres", "What is pg_dump?", "Logical database backup tool.")
add("postgres", "Why use indexes?", "Speed selective lookups and joins.")
add("security_defensive", "What is least privilege?", "Minimum permissions needed only.")
add("security_defensive", "Where enforce authorization?", "Always on the server.")
add("security_defensive", "May we learn exploits?", "No. Defense and hardening only.")
add("security_defensive", "What not to log?", "Passwords, tokens, secrets.")
add("windows", "List files in PowerShell?", "Get-ChildItem")
add("windows", "When elevate?", "Only when admin rights are required.")
add("ubuntu", "Install package?", "sudo apt update && sudo apt install name")
add("ubuntu", "Check service?", "systemctl status name")
add("fullstack_agent", "What is verify?", "Prove the change works with a check.")
add("fullstack_agent", "Before destructive DB change?", "Backup and confirm impact.")

(DATA / "skills_quiz.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in quizzes) + "\n", encoding="utf-8", newline="\n")
write(CORPUS / "skills_quiz" / "01_all.txt", "\n".join(x["text"] for x in quizzes for _ in range(10)))
(DATA / "curriculum_skills.md").write_text(
    "# Rosa_Brain Skills Curriculum\n\n1. PostgreSQL\n2. Defensive security only (no exploits)\n3. Windows OS\n4. Ubuntu OS\n5. Full-stack professional agent\n",
    encoding="utf-8",
)
print("corpora_ok", len(quizzes))
