"""Cases for the optional AI agent / MCP rules in catalog/gitleaks/.gitleaks.toml.

Every case is written to its own folder, then one real `gitleaks dir` run scans them all
with the catalog config. Each test checks what our rule found in its own folder.

Needs a `gitleaks` binary on PATH (CI installs the pinned version with `go install`).
Without one the tests skip, unless REQUIRE_GITLEAKS=1 is set, in which case they fail.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import CATALOG

CONFIG = CATALOG / "gitleaks" / ".gitleaks.toml"
SECRET = "mcp-config-secret"
AUTH = "mcp-config-auth-header"

# realistic-looking but fake value with enough entropy to pass the rule's 3.0 floor
FAKE = "q7Ft2LmZp9Xc4Rv8Kd1Wn6Hs3Jb5Ye0A"  # gitleaks:allow (synthetic)


def env_line(key, value):
    return json.dumps({key: value})


CASES = []  # (case id, file path, file text, rule id, expected secrets)


def case(path, text, rule, expected):
    CASES.append((f"c{len(CASES):03d}", path, text, rule, expected))
    return CASES[-1][0]


SECRET_KEYS = [
    "API_KEY", "BRAVE_API_KEY", "GITHUB_PERSONAL_ACCESS_TOKEN", "GITHUB_PAT", "SLACK_BOT_TOKEN",
    "client_secret", "client-secret", "DB_PASSWORD", "token", "PAT", "apiKey", "githubToken",
    "ApiKey", "clientSecret", "apikey", "accesstoken", "AUTHTOKEN", "credentials", "GOOGLE_CREDENTIALS",
    "npm.token",
    # compound lowercase names and plurals
    "githubtoken", "openaikey", "dbpassword", "API_KEYS", "tokens", "keys", "clientsecrets", "sshkey",
]
NON_SECRET_KEYS = [
    "PATH", "path", "Path", "PYTHONPATH", "TOKEN_FILE", "KEY_ID", "monkey", "keyboard", "TOKENIZER",
    "SECRET_NAME", "PASSWORD_FILE", "patch", "pattern", "compat", "tokens_url", "spatial", "turkey",
    "hockey", "githubpatch", "KEYS_URL",
]
ALLOWED_VALUES = [
    ("PATH", "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"),
    ("TOKEN_FILE", "~/secrets/mytoken.txt"),
    # path-like values under secret-looking keys are references, not secrets
    ("GITHUB_TOKEN", "~/secrets/mytoken.txt"),
    ("API_KEY", "/run/secrets/api_key"),
    ("SERVICE_ACCOUNT_CREDENTIALS", "./config/sa-key.json"),
    ("SERVICE_ACCOUNT_CREDENTIALS", "sa-prod-key.json"),
    ("CLIENT_SECRET", "C:\\Users\\dev\\secrets\\client.txt"),
    ("CLIENT_SECRET", "%USERPROFILE%\\secrets\\client.txt"),
    # env references and placeholders
    ("API_KEY", "${BRAVE_API_KEY}"),
    ("API_KEY", "your-api-key-here"),
    ("API_KEY", "<paste key>"),
    ("API_KEY", "changeme"),
]
# a value that merely starts with "/" but is a token (contains + and =) is not a path
SLASH_TOKEN = "/q7Ft2L+mZp9Xc4Rv8Kd1Wn6Hs3Jb5Ye0A=="  # gitleaks:allow (synthetic)
PATHS = [
    (".mcp.json", True),
    ("tools/.cursor/mcp.json", True),
    (".claude/settings.local.json", True),
    ("claude_desktop_config.json", True),
    ("package.json", False),
    ("docs/mcp.json.md", False),
]
AUTH_VALUES = [
    ("Bearer " + FAKE, True),
    ("token " + FAKE, True),
    ("Bearer ${GITHUB_TOKEN}", False),
    ("Bearer short", False),
]
FULL_CONFIG = json.dumps(
    {
        "mcpServers": {
            "github": {
                "command": "docker",
                "env": {
                    "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin",
                    "TOKEN_FILE": "~/secrets/mytoken.txt",
                    "GITHUB_PERSONAL_ACCESS_TOKEN": FAKE,
                    "LOG_LEVEL": "debugverbose",
                },
            }
        }
    },
    indent=2,
)

SECRET_KEY_CASES = [(k, case(".mcp.json", env_line(k, FAKE), SECRET, [FAKE])) for k in SECRET_KEYS]
NON_SECRET_KEY_CASES = [(k, case(".mcp.json", env_line(k, FAKE), SECRET, [])) for k in NON_SECRET_KEYS]
ALLOWED_CASES = [(k, v, case(".mcp.json", env_line(k, v), SECRET, [])) for k, v in ALLOWED_VALUES]
SLASH_TOKEN_CASE = case(".mcp.json", env_line("API_KEY", SLASH_TOKEN), SECRET, [SLASH_TOKEN])
PATH_CASES = [(p, hit, case(p, env_line("API_KEY", FAKE), SECRET, [FAKE] if hit else [])) for p, hit in PATHS]
FULL_CASE = case(".mcp.json", FULL_CONFIG, SECRET, [FAKE])
AUTH_CASES = [
    (v, hit, case(".vscode/mcp.json", json.dumps({"Authorization": v}), AUTH, [FAKE] if hit else []))
    for v, hit in AUTH_VALUES
]
BY_ID = {c[0]: c for c in CASES}


@pytest.fixture(scope="session")
def found(tmp_path_factory):
    """Run gitleaks once over every case; return {(case id, rule id): [secrets]}."""
    gitleaks = shutil.which("gitleaks")
    if not gitleaks:
        if os.environ.get("REQUIRE_GITLEAKS") == "1":
            pytest.fail("gitleaks not on PATH and REQUIRE_GITLEAKS=1")
        pytest.skip("gitleaks not on PATH")
    tmp = tmp_path_factory.mktemp("gitleaks")
    src = tmp / "src"
    for cid, path, text, _, _ in CASES:
        f = src / cid / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
    report = tmp / "report.json"
    proc = subprocess.run(
        [gitleaks, "dir", str(src), "--config", str(CONFIG), "--no-banner",
         "--report-format", "json", "--report-path", str(report), "--exit-code", "0"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = {}
    for f in json.loads(report.read_text(encoding="utf-8")):
        cid = Path(f["File"]).relative_to(src).parts[0]
        out.setdefault((cid, f["RuleID"]), []).append(f["Secret"])
    return out


def check(found, cid):
    _, _, _, rule, expected = BY_ID[cid]
    assert found.get((cid, rule), []) == expected


@pytest.mark.parametrize("key,cid", SECRET_KEY_CASES)
def test_secret_keys_are_flagged(found, key, cid):
    check(found, cid)


@pytest.mark.parametrize("key,cid", NON_SECRET_KEY_CASES)
def test_non_secret_keys_are_not_flagged(found, key, cid):
    check(found, cid)


@pytest.mark.parametrize("key,value,cid", ALLOWED_CASES)
def test_paths_references_and_placeholders_are_allowed(found, key, value, cid):
    check(found, cid)


def test_real_secret_in_a_path_like_value_still_flags(found):
    check(found, SLASH_TOKEN_CASE)


@pytest.mark.parametrize("path,hit,cid", PATH_CASES)
def test_rule_only_applies_to_agent_configs(found, path, hit, cid):
    check(found, cid)


def test_full_mcp_config_flags_only_the_secret(found):
    check(found, FULL_CASE)


@pytest.mark.parametrize("value,hit,cid", AUTH_CASES)
def test_authorization_header(found, value, hit, cid):
    check(found, cid)
