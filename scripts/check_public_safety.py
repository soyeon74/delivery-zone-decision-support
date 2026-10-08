from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    "data/raw", "data/private", "data/operational", "data/internal", "data/gis_private"
}

PATTERNS = {
    "resident_id_like": re.compile(r"\b\d{6}-\d{7}\b"),
    "korean_mobile_like": re.compile(r"\b01[016789]-?\d{3,4}-?\d{4}\b"),
    "long_numeric_id": re.compile(r"\b\d{12,14}\b"),
    "api_key_literal": re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{16,}"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}

TEXT_EXTS = {
    ".py",".md",".txt",".json",".yaml",".yml",".toml",".ini",".cfg",".csv",
    ".html",".css",".js",".ts",".tsx",".jsx",".env",".example"
}

def is_excluded(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    if rel.startswith(".git/"):
        return True
    return any(rel == d or rel.startswith(d + "/") for d in EXCLUDED_DIRS)

findings = []
for path in ROOT.rglob("*"):
    if not path.is_file() or is_excluded(path):
        continue
    if path.name == ".env.example":
        # example-only keys are allowed if they do not contain real secrets
        pass
    if path.suffix.lower() not in TEXT_EXTS and path.name not in {".gitignore",".env.example"}:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            text = path.read_text(encoding="utf-8-sig")
        except Exception:
            continue
    for name, pattern in PATTERNS.items():
        for m in pattern.finditer(text):
            value = m.group(0)
            # Synthetic IDs intentionally start with SYN- and are not numeric-only.
            findings.append((path.relative_to(ROOT).as_posix(), name, value[:80]))

if findings:
    print("FAIL: 공개 전 확인이 필요한 패턴이 발견되었습니다.")
    for file, kind, value in findings:
        print(f"- {file} | {kind} | {value}")
    sys.exit(1)

print("PASS: 기본 공개 안전패턴 검사에서 의심 항목이 발견되지 않았습니다.")
print("주의: PASS는 기관의 공식 보안/반출 승인과 동일한 의미가 아닙니다.")
