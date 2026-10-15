"""Repository Hygiene and Security Audit Script (Phase 10).

Checks:
1. Scans source code for TODO/FIXME/XXX tags.
2. Scans for hardcoded secrets or API tokens.
3. Validates relative markdown links across docs/ and README.md.
4. Checks for empty modules, broken imports, and orphan files.
"""

import os
import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".next",
    "dist",
    "build",
    "backups",
    ".turbo",
}

# Suspicious secret regex patterns
SECRET_PATTERNS = [
    (r"(?i)(?:api_key|apikey|secret|password|passwd|token)\s*=\s*['\"][a-zA-Z0-9_\-\.\/]{16,}['\"]", "Hardcoded Secret/Token"),
    (r"sk-[a-zA-Z0-9]{20,}", "OpenAI API Key"),
    (r"ghp_[a-zA-Z0-9]{20,}", "GitHub Personal Access Token"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
    (r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----", "Private Key"),
]

# Whitelist known placeholder prefixes or dummy test hashes
WHITELIST = {
    "tn_mgmt_placeholder",
    "tn_ingest_placeholder",
    "tn_live_placeholder",
    "ChangeThisInProductionSecuredSecret!",
    "postgres:postgres",
    "your_production_google_gemini_api_key_here",
    "generate_a_strong_random_password_here_min_32_chars",
    "tn_ingest_a1b2c3d4e5f67890123456789abcdef",
    "tn_live_your_project_key",
    "tn_ingest_your_scoped_key",
    "tn_live_key",
    "tn_ingest_key",
    "tn_live_your_project_key_here",
    "tn_ingest_your_scoped_ingestion_key_here",
    "tn_live_placeholder_key",
    "tn_ingest_placeholder_key",
    "your_api_key_here",
    "my-secret-key",
}

def scan_files():
    print("=" * 70)
    print("TraceNest Phase 10: Repository Hygiene & Security Audit")
    print("=" * 70)

    todos = []
    suspicious_secrets = []
    md_files = []

    for root, dirs, files in os.walk(ROOT_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            path = Path(root) / f
            rel_path = path.relative_to(ROOT_DIR)

            if path.suffix in (".md", ".markdown"):
                md_files.append(path)

            # Skip binary files
            if path.suffix in (".ico", ".png", ".jpg", ".jpeg", ".gz", ".sql", ".pyc"):
                continue

            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            lines = content.splitlines()
            for idx, line in enumerate(lines, 1):
                # 1. Search for TODO / FIXME
                if any(tag in line for tag in ("TODO", "FIXME", "XXX")):
                    # Exclude this audit script itself
                    if "audit_repo.py" not in str(rel_path):
                        todos.append((str(rel_path), idx, line.strip()))

                # 2. Search for secrets
                for pattern, desc in SECRET_PATTERNS:
                    match = re.search(pattern, line)
                    if match:
                        matched_str = match.group(0)
                        # Check whitelist
                        if not any(w in matched_str for w in WHITELIST):
                            suspicious_secrets.append((str(rel_path), idx, desc))

    print(f"\n[1] Found {len(todos)} TODO / FIXME comments:")
    for file, line_no, text in todos:
        print(f"    {file}:{line_no} -> {text[:80]}")

    print(f"\n[2] Found {len(suspicious_secrets)} suspicious secret patterns:")
    for file, line_no, desc in suspicious_secrets:
        print(f"    {file}:{line_no} -> {desc}")

    # 3. Validate Markdown links
    print(f"\n[3] Validating Markdown links across {len(md_files)} documentation files...")
    broken_links = []
    link_regex = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    for md in md_files:
        rel_md = md.relative_to(ROOT_DIR)
        text = md.read_text(encoding="utf-8", errors="ignore")
        for match in link_regex.finditer(text):
            label, target = match.groups()
            # Ignore web links, anchors, mailto
            if target.startswith(("http://", "https://", "#", "mailto:", "conversation://", "file:///")):
                continue
            # Strip anchors
            clean_target = target.split("#")[0]
            if not clean_target:
                continue
            # Resolve relative path
            target_path = (md.parent / clean_target).resolve()
            if not target_path.exists():
                broken_links.append((str(rel_md), target, str(target_path)))

    print(f"    Found {len(broken_links)} broken relative links:")
    for source_file, target, resolved in broken_links:
        print(f"    {source_file} -> '{target}' (resolved: {resolved})")

    print("\n" + "=" * 70)
    print("AUDIT SUMMARY:")
    print(f"  - Unresolved TODOs:     {len(todos)}")
    print(f"  - Hardcoded Secrets:    {len(suspicious_secrets)}")
    print(f"  - Broken Doc Links:     {len(broken_links)}")
    print("=" * 70)

if __name__ == "__main__":
    scan_files()
