---
name: google-cloud-recipe-gcp-juggling
metadata:
  version: "1.0.0"
  category: GettingStarted
description: >-
  Isolates Google Cloud CLI (gcloud) configurations, Application Default
  Credentials (ADC), service account impersonation, and Python virtual
  environments per directory using direnv and CLOUDSDK_CONFIG. Use when
  juggling multiple Google Cloud accounts, organizations, or projects on a
  single workstation, preventing global ADC overwrites during gcloud auth login
  --update-adc, or sandboxing multi-repo and git-worktree environments.
  Don't use for single-project workstations sharing one global identity, or for
  production compute workloads where credentials come from the metadata server
  (Compute Engine, Cloud Run, GKE Workload Identity).
---

# Google Cloud Recipe: Juggling Multiple GCP Accounts and Projects with direnv

This skill provides a deterministic workflow for isolating [Google Cloud CLI (`gcloud`)](https://docs.cloud.google.com/sdk/docs) configurations, [Application Default Credentials (ADC)](https://docs.cloud.google.com/docs/authentication/application-default-credentials), service account impersonation settings, and Python virtual environments (`uv` / `.venv`) on a per-directory basis using `direnv` and `CLOUDSDK_CONFIG="${PWD}/.gcloud"`.

> [!IMPORTANT]
> For autonomous agents executing this skill:
> 1. **Check-Before-Mutate Audits**: Always perform silent pre-execution audits (`which direnv`, `direnv status`, `echo "$CLOUDSDK_CONFIG"`, and checking `.gitignore`) before writing `.envrc` or running `gcloud auth` commands.
> 2. **Protect Global ADC**: Never run `gcloud auth login --update-adc` or `gcloud auth application-default login` until you have verified that `CLOUDSDK_CONFIG` resolves to the directory-local `${PWD}/.gcloud` path.
> 3. **Subshell Execution via `direnv exec`**: Non-interactive agent tool calls execute in subshells that do not source interactive `~/.bashrc` or `~/.zshrc` hooks. Always wrap directory-scoped commands in `direnv exec "$PROJECT_DIR" <command>` after running `direnv allow`.
> 4. **Single-Question Policy**: Ask the developer for one operational parameter or confirmation at a time when target values (`PROJECT_ID`, `ACCOUNT`) are unspecified.
> 5. **Non-Interactive Output**: Append `--quiet` and `--format="json"` to `gcloud` audit and configuration commands to prevent terminal hangs.

---

## Overview

Developers, solutions architects, and security engineers frequently juggle multiple Google Cloud identities on a single workstation:
- A primary corporate identity (`developer@company.com`) bound to an enterprise organization.
- Sandbox, demo, or testing organizations (`admin@sandbox.example.com`).
- Client or partner tenants (`contractor@client-org.com`).
- Personal Free Trial or hobby projects (`user@gmail.com`).

### Why `gcloud config configurations` Alone Is Not Enough

While `gcloud config configurations create` manages named CLI property profiles, it fails in multi-terminal, multi-worktree, and SDK-driven workflows for two structural reasons:

| Mechanism | Scope of Active State | Isolates `gcloud` CLI? | Isolates Application Default Credentials (ADC)? | Safe for Concurrent Terminals & Agents? |
| :--- | :--- | :--- | :--- | :--- |
| `gcloud config set project` | Global (`~/.config/gcloud/configurations/config_default`) | No (overwrites default) | No (`~/.config/gcloud/application_default_credentials.json` is shared) | No — switching project in Tab A silently mutates Tab B |
| `gcloud config configurations activate` | Global (`~/.config/gcloud/active_config`) | Partial (switches active profile globally) | **No** — ADC remains a single global file overwritten by every login | No — only one configuration can be active globally at a time |
| `CLOUDSDK_ACTIVE_CONFIG_NAME` via `direnv` | Directory-scoped shell env | Yes | **No** — all named configs still share `~/.config/gcloud/application_default_credentials.json` | Partial — Python/Go/Node client libraries still collide on ADC |
| **`CLOUDSDK_CONFIG="${PWD}/.gcloud"` via `direnv` (This Recipe)** | **Directory-scoped filesystem & shell env** | **Yes** (`./.gcloud/credentials.db`) | **Yes** (`./.gcloud/application_default_credentials.json`) | **Yes** — each repo or git worktree has a completely independent credential store |

### Architecture

```text
+-------------------------------------------------------------------------------+
|                              Developer Workstation                            |
|                                                                               |
|  Global Config: ~/.config/gcloud/                                             |
|  Global ADC:    ~/.config/gcloud/application_default_credentials.json         |
|                 (Bound to primary corporate identity — NEVER overwritten)     |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
|               Project Worktree: ~/Projects/my-project/                        |
|                                                                               |
|  [direnv hook triggers upon cd or direnv exec]                                |
|    1. uv venv & PATH_add .venv/bin            <-- Auto-provisions & activates |
|    2. CLOUDSDK_CONFIG="${PWD}/.gcloud"        <-- Isolated gcloud & ADC dir   |
|    3. CLOUDSDK_CORE_ACCOUNT="admin@sandbox.example.com"                       |
|    4. CLOUDSDK_CORE_PROJECT="my-sandbox-project-01"                           |
|    5. GOOGLE_APPLICATION_CREDENTIALS="${PWD}/.gcloud/application_default_...  |
|    6. Optional mTLS / service account impersonation overrides                 |
|                                                                               |
|  Local Directory State (Git-Ignored):                                         |
|    .venv/                                          (Local Python virtualenv)  |
|    .gcloud/credentials.db                          (Local CLI OAuth token)    |
|    .gcloud/application_default_credentials.json    (Local SDK ADC file)       |
+-------------------------------------------------------------------------------+
```

When you `cd` into the project directory, `direnv` redirects all `gcloud` CLI and `google-auth` SDK lookups to `./.gcloud/` and activates `.venv`. When you `cd` out, `direnv` unloads the environment variables and restores your global corporate configuration automatically.

---

## Clarifying Questions

If the developer has not already provided these parameters in their prompt, clarify:

1. **Target Directory (`PROJECT_DIR`)**: Which repository or git worktree directory should be isolated?
2. **Target Identity (`ACCOUNT`)**: Which email address (`user@domain.com`) should be active inside this directory?
3. **Target Project (`PROJECT_ID`)**: Which Google Cloud Project ID should be pinned (or should a new project be onboarded via `google-cloud-recipe-onboarding` after isolation is active)?
4. **Authentication Mode**: Will local code authenticate directly as the user via ADC (`gcloud auth login <ACCOUNT> --update-adc`), or should it impersonate a service account via `CLOUDSDK_AUTH_IMPERSONATE_SERVICE_ACCOUNT`?

---

## Prerequisites

- Google Cloud CLI (`gcloud`) installed on the host machine.
- Bash or Zsh shell environment (Linux or macOS).
- Optional: [`uv`](https://docs.astral.sh/uv/) installed if automatic Python `.venv` provisioning is desired.

---

## Steps

### Section 1: Audit Host Tooling and Install `direnv`

Before modifying any project files, silently check whether `direnv`, `gcloud`, and `uv` are installed:

```bash
which direnv gcloud uv
```

If `direnv` is missing (including on managed corporate workstations without passwordless `sudo`), install the standalone binary into user-space and register the shell hook:

```bash
# 1. Install direnv binary into user-local bin directories
INSTALL_BIN_DIR="$HOME/.local/bin"
FALLBACK_BIN_DIR="$HOME/bin"
mkdir -p "$INSTALL_BIN_DIR" "$FALLBACK_BIN_DIR"
curl -fsSL https://direnv.net/install.sh | bin_path="$INSTALL_BIN_DIR" bash
cp "$INSTALL_BIN_DIR/direnv" "$FALLBACK_BIN_DIR/direnv"
chmod +x "$INSTALL_BIN_DIR/direnv" "$FALLBACK_BIN_DIR/direnv"

# 2. Register direnv hook in ~/.bashrc (or ~/.zshrc)
SHELL_RC="$HOME/.bashrc"
if ! grep -q "direnv hook" "$SHELL_RC" 2>/dev/null; then
  cat << 'HOOK' >> "$SHELL_RC"

# Load direnv hook
export PATH="$HOME/.local/bin:$HOME/bin:$PATH"
if command -v direnv &> /dev/null; then
  eval "$(direnv hook bash)"
fi
HOOK
fi

# 3. Optional: Define reusable layout_uv helper in ~/.config/direnv/direnvrc
DIRENV_CONFIG_DIR="$HOME/.config/direnv"
mkdir -p "$DIRENV_CONFIG_DIR"
if ! grep -q "layout_uv()" "$DIRENV_CONFIG_DIR/direnvrc" 2>/dev/null; then
  cat << 'EOF' >> "$DIRENV_CONFIG_DIR/direnvrc"
layout_uv() {
  if ! has uv; then
    log_error "uv not found. Install from https://astral.sh/uv"
    return 1
  fi
  VIRTUAL_ENV="${PWD}/.venv"
  if [[ ! -d "${VIRTUAL_ENV}" ]]; then
    uv venv
  fi
  PATH_add "${VIRTUAL_ENV}/bin"
  export VIRTUAL_ENV
}
EOF
fi
```

---

### Section 2: Protect `.gitignore` Before Creating Credentials

To prevent accidental commits of local OAuth tokens, ADC JSON files, or environment scripts, always append `.gcloud/`, `.envrc`, and `.venv/` to the project's `.gitignore` **before** generating `.envrc` or authenticating:

```bash
PROJECT_DIR="/path/to/your/project"
GITIGNORE_FILE="${PROJECT_DIR}/.gitignore"

touch "$GITIGNORE_FILE"
for ENTRY in ".venv/" ".gcloud/" ".envrc"; do
  if ! grep -qxF "$ENTRY" "$GITIGNORE_FILE"; then
    echo "$ENTRY" >> "$GITIGNORE_FILE"
  fi
done
```

---

### Section 3: Generate `.envrc` in the Target Directory

Create `.envrc` at the root of the repository or git worktree. Define target identity and project variables first, then export the `CLOUDSDK_*` and `GOOGLE_*` environment variables referencing them:

```bash
PROJECT_DIR="/path/to/your/project"
PROJECT_ID="my-sandbox-project-01"
PROJECT_NUMBER="123456789012"
REGION="us-central1"
ACCOUNT="admin@sandbox.example.com"

cat << EOF > "${PROJECT_DIR}/.envrc"
# ============================================================================
# direnv configuration for Google Cloud account, ADC, and virtualenv isolation
# ============================================================================

# 1. Automatically provision and activate local Python virtualenv (.venv)
if has uv; then
  VIRTUAL_ENV="\${PWD}/.venv"
  if [ ! -d "\${VIRTUAL_ENV}" ]; then
    uv venv
  fi
  PATH_add "\${VIRTUAL_ENV}/bin"
  export VIRTUAL_ENV
elif [ -d ".venv/bin" ]; then
  PATH_add .venv/bin
  export VIRTUAL_ENV="\${PWD}/.venv"
fi

# 2. Load optional local overrides from .env if present
# Note: Always quote values containing spaces, parentheses, '#', or '=' in .env,
# otherwise direnv's strict dotenv parser rejects the line and drops the entire file.
dotenv_if_exists .env

# 3. Isolate gcloud configuration and ADC directory to this workspace
export CLOUDSDK_CONFIG="\${PWD}/.gcloud"

# 4. Pin target Google Cloud Project, Region, and Account
# Use ':-' so non-empty values from .env can override defaults while empty .env.example keys fall back.
export GCP_PROJECT_ID="\${GCP_PROJECT_ID:-${PROJECT_ID}}"
export GCP_PROJECT_NUMBER="\${GCP_PROJECT_NUMBER:-${PROJECT_NUMBER}}"
export GCP_LOCATION="\${GCP_LOCATION:-${REGION}}"
export CLOUDSDK_CORE_PROJECT="\${GCP_PROJECT_ID}"
export CLOUDSDK_COMPUTE_REGION="\${GCP_LOCATION}"
export CLOUDSDK_CORE_ACCOUNT="\${CLOUDSDK_CORE_ACCOUNT:-${ACCOUNT}}"

# 5. Pin GOOGLE_APPLICATION_CREDENTIALS when local ADC exists
if [ -f "\${PWD}/.gcloud/application_default_credentials.json" ]; then
  export GOOGLE_APPLICATION_CREDENTIALS="\${PWD}/.gcloud/application_default_credentials.json"
fi

# 6. Optional: Keyless Service Account Impersonation (recommended over JSON keys)
# SERVICE_ACCOUNT_EMAIL="workload-sa@\${GCP_PROJECT_ID}.iam.gserviceaccount.com"
# export CLOUDSDK_AUTH_IMPERSONATE_SERVICE_ACCOUNT="\${SERVICE_ACCOUNT_EMAIL}"

# 7. Enterprise Endpoint Verification / Context-Aware Access mTLS Bypass
# Prevents cert-provider subprocess crashes (exit code -11) when authenticating
# from an enterprise-managed workstation to an external or sandbox tenant.
export GOOGLE_API_USE_CLIENT_CERTIFICATE="false"
export GOOGLE_API_USE_MTLS_ENDPOINT="never"
export CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE="false"
export GOOGLE_GENAI_USE_VERTEXAI="TRUE"
EOF
```

---

### Section 4: Authorize `direnv` and Authenticate Inside the Sandbox

1. **Authorize the `.envrc` file:**

   ```bash
   PROJECT_DIR="/path/to/your/project"
   direnv allow "$PROJECT_DIR"
   ```

2. **Authenticate both `gcloud` CLI and Application Default Credentials (ADC) in a single step:**
   Always prefer `gcloud auth login <ACCOUNT> --update-adc` over separate `gcloud auth application-default login` invocations so that CLI credentials (`credentials.db`) and client library ADC (`application_default_credentials.json`) never drift apart.

   > [!CAUTION]
   > **Avoid the `PROMPT_COMMAND` One-Liner Trap**:
   > `direnv`'s bash hook executes via `PROMPT_COMMAND`, which only fires when an interactive prompt is rendered. If a user copy-pastes `cd "$PROJECT_DIR" && gcloud auth login "$ACCOUNT" --update-adc` as a single compound line, bash runs both commands back-to-back with no prompt in between—meaning `.envrc` has **not** loaded yet and `--update-adc` will overwrite the global `~/.config/gcloud/application_default_credentials.json`!
   > Always include `direnv exec .` in copy-pasteable one-liners so `CLOUDSDK_CONFIG` is guaranteed to load before `gcloud` executes:

   ```bash
   PROJECT_DIR="/path/to/your/project"
   ACCOUNT="admin@sandbox.example.com"

   cd "$PROJECT_DIR" && direnv allow . && direnv exec . gcloud auth login "$ACCOUNT" --update-adc
   ```

   Because `direnv exec .` explicitly loads `${PROJECT_DIR}/.envrc` before launching `gcloud`:
   - CLI tokens are written to `${PROJECT_DIR}/.gcloud/credentials.db`.
   - ADC is written to `${PROJECT_DIR}/.gcloud/application_default_credentials.json`.
   - Re-entering the directory (or running `direnv reload`) automatically exports `GOOGLE_APPLICATION_CREDENTIALS="${PWD}/.gcloud/application_default_credentials.json"`.
   - **The global `~/.config/gcloud/application_default_credentials.json` file remains untouched.**

---

### Section 5: Add a Fail-Closed Guard for Deployment Scripts and Agents

Automated build scripts (`deploy.sh`, `Makefile`, `justfile`) and AI agent tool invocations execute in non-interactive subshells where `~/.bashrc` shell hooks do not run. Furthermore, if `.envrc` is unallowed, `direnv exec .` fails **open**—printing a warning and executing the command against the ambient host environment.

Therefore, always combine `direnv exec` with an explicit in-script assertion of both `CLOUDSDK_CONFIG` and the resolved `PROJECT_ID`:

1. **Wrap non-interactive commands in `direnv exec`:**

   ```bash
   PROJECT_DIR="/path/to/your/project"
   direnv exec "$PROJECT_DIR" gcloud auth list --format="json"
   ```

2. **Add a fail-closed project and config guard before mutating resources (`scripts/require_project.sh`):**

   ```bash
   EXPECTED_PROJECT_ID="my-sandbox-project-01"
   RESOLVED_PROJECT_ID="$(gcloud config get-value project --quiet 2>/dev/null)"

   if [ "${CLOUDSDK_CONFIG:-}" != "${PWD}/.gcloud" ] || [ "$RESOLVED_PROJECT_ID" != "$EXPECTED_PROJECT_ID" ]; then
     echo "ERROR: Isolated environment not active (CLOUDSDK_CONFIG='${CLOUDSDK_CONFIG:-unset}', project='$RESOLVED_PROJECT_ID', expected='$EXPECTED_PROJECT_ID')." >&2
     echo "Run: direnv allow . && direnv exec . <command>" >&2
     exit 1
   fi
   ```

---

### Section 6: Skill Chaining

Once directory isolation is active, chain to downstream Google Cloud skills inside the isolated workspace:

1. **First-Time Project Creation & Billing Setup (`google-cloud-recipe-onboarding`)**:
   If `$PROJECT_ID` does not exist yet or needs billing attached, run [`google-cloud-recipe-onboarding`](../google-cloud-recipe-onboarding/SKILL.md) **after** completing Sections 1–4 of this skill. Because `CLOUDSDK_CONFIG="${PWD}/.gcloud"` is already active, `gcloud projects create`, `gcloud config set project`, and `gcloud billing projects link` will execute cleanly inside `${PWD}/.gcloud` without mutating `~/.config/gcloud`.
2. **Production & Workload Identity Architecture (`google-cloud-recipe-auth`)**:
   When transitioning local code to Cloud Run, GKE, or Compute Engine, chain to [`google-cloud-recipe-auth`](../google-cloud-recipe-auth/SKILL.md) to attach dedicated service accounts rather than deploying local `.gcloud` credentials.
3. **Workload Deployment (`cloud-run-basics`, `bigquery-basics`, `agent-platform-deploy`)**:
   Execute all downstream `gcloud` and SDK commands via `direnv exec "$PROJECT_DIR" <command>`.

---

## Validation Logic

Run these non-interactive checks via `direnv exec` to verify that isolation is active and global credentials are unharmed:

| Check | Verification Command (`direnv exec "$PROJECT_DIR" ...`) | Expected Result |
| :--- | :--- | :--- |
| **1. `direnv` Authorization** | `direnv status` | `Found RC allowed true` / `Found RC allowed 0` |
| **2. Isolated Config Path** | `direnv exec "$PROJECT_DIR" bash -c 'echo "$CLOUDSDK_CONFIG"'` | `${PROJECT_DIR}/.gcloud` |
| **3. Active `gcloud` Account** | `direnv exec "$PROJECT_DIR" gcloud config get-value account --quiet` | Matches target `$ACCOUNT` |
| **4. Active `gcloud` Project** | `direnv exec "$PROJECT_DIR" gcloud config get-value project --quiet` | Matches target `$PROJECT_ID` |
| **5. Local Python `.venv`** | `direnv exec "$PROJECT_DIR" which python` | `${PROJECT_DIR}/.venv/bin/python` |
| **6. Python SDK Config Path** | `direnv exec "$PROJECT_DIR" python3 -c "import google.auth._cloud_sdk; print(google.auth._cloud_sdk.get_config_path())"` | `${PROJECT_DIR}/.gcloud` |
| **7. Global Config Intact** | `env -u CLOUDSDK_CONFIG -u CLOUDSDK_CORE_PROJECT -u CLOUDSDK_CORE_ACCOUNT gcloud config get-value project --quiet` | Returns host's original global project (unchanged) |

---

## Common Gotchas & Troubleshooting

### 1. Enterprise mTLS Crash: `Cert provider command returns non-zero status code -11`
- **Symptom**: Python Google Cloud SDKs (`google-cloud-aiplatform`, `google-genai`, `google-auth`) crash with `Cert provider command returns non-zero status code -11` when calling APIs in an external or sandbox project from an enterprise workstation.
- **Cause**: Enterprise Endpoint Verification configures a client-certificate helper binary that fails or exits `-11` when probing endpoints outside the corporate organization.
- **Fix**: Ensure the three mTLS bypass variables in Section 3 (`GOOGLE_API_USE_CLIENT_CERTIFICATE="false"`, `GOOGLE_API_USE_MTLS_ENDPOINT="never"`, `CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE="false"`) are exported in `.envrc`.

### 2. Global `GOOGLE_APPLICATION_CREDENTIALS` Overriding Local User ADC
- **Symptom**: Even after running `gcloud auth login "$ACCOUNT" --update-adc`, Python libraries authenticate as an unrelated service account and fail with `403 PERMISSION_DENIED`.
- **Cause**: ADC lookup order checks `$GOOGLE_APPLICATION_CREDENTIALS` **before** `$CLOUDSDK_CONFIG/application_default_credentials.json`. If the parent shell exported `GOOGLE_APPLICATION_CREDENTIALS` pointing to a global JSON key file, it wins.
- **Fix**: Keep Step 5 in `.envrc` so `GOOGLE_APPLICATION_CREDENTIALS` explicitly points to `${PWD}/.gcloud/application_default_credentials.json` whenever that file exists, or `unset GOOGLE_APPLICATION_CREDENTIALS` at the top of `.envrc`.

### 3. Non-Interactive Agent Reauthentication Failure
- **Symptom**: `gcloud` or ADC calls fail with `Reauthentication failed. cannot prompt during non-interactive execution.`
- **Cause**: Human user credentials (`type == "authorized_user"`) require periodic interactive OAuth/WebAuthn renewal, which headless agent tools cannot complete without a TTY.
- **Fix**: Prompt the developer with the ready-to-paste interactive command:
  ```bash
  PROJECT_DIR="/path/to/your/project"
  ACCOUNT="admin@sandbox.example.com"
  cd "$PROJECT_DIR" && gcloud auth login "$ACCOUNT" --update-adc
  ```

---

## References

- [Google Cloud CLI Configurations Guide](https://docs.cloud.google.com/sdk/docs/configurations)
- [How Application Default Credentials Work](https://docs.cloud.google.com/docs/authentication/application-default-credentials)
- [Service Account Impersonation](https://docs.cloud.google.com/docs/authentication/use-service-account-impersonation)
- [Authorizing the gcloud CLI](https://docs.cloud.google.com/sdk/docs/authorizing)
