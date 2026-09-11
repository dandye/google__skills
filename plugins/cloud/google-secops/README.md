# Google SecOps Plugin

Agent plugin providing Security Operations capabilities for Google Security Operations (Chronicle SIEM and SOAR), packaged under the Agent Plugins 1.0.0 specification.

This plugin packages domain-specific agent skills, slash command shortcuts, environment configuration rules, and remote Model Context Protocol (MCP) server definitions connecting to Google SecOps.

---

## Overview

The Google SecOps plugin equips coding and operations agents with specialized workflows for security analytics:

* **Alert Triage:** Rapid evaluation, severity tuning, entity scoping, and closing recommendations.
* **Investigation:** UDM search, event extraction, asset/user timeline reconstruction, and lateral movement detection.
* **Threat Hunting:** Hypothesis-driven hunting, IoC sweeps, prevalence analysis, and outlier detection.
* **Case Management:** SOAR case tracking, task execution, comment documentation, and alert association.
* **Detection Engineering:** YARA-L 2.0 rule authoring, validation, test backtesting, deployment, and coverage evaluation.

---

## Prerequisites and Authentication

Before invoking Google SecOps skills or the Chronicle MCP server, ensure your local environment satisfies the following prerequisites:

### 1. Google Cloud Authentication

Authenticate with Application Default Credentials (ADC) and configure your quota project:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project ${PROJECT_ID}
```

### 2. Enable Chronicle MCP Service

The Chronicle MCP service must be enabled in your Google Cloud project:

```bash
gcloud beta services mcp enable chronicle.googleapis.com/mcp --project=${PROJECT_ID}
```

### 3. Web Console First-Login Requirement

You must log into the Google SecOps web interface (`https://<customer-subdomain>.chronicle.security`) at least once before making API or MCP calls. This initial login initializes tenant authorization profiles for your identity.

### 4. Required Environment Variables

Set the following environment variables in your active shell or agent profile:

```bash
export PROJECT_ID="your-gcp-project-id"
export CUSTOMER_ID="your-chronicle-customer-uuid"
export REGION="us" # or your Chronicle region (e.g. europe-west1)
export SERVER_URL="https://chronicle.us.rep.googleapis.com/mcp"
```

### 5. Preflight Verification

Agent runtimes register MCP tools once, at startup. If the connection fails, the session
simply has no SecOps tools; there is usually no error and no prompt. Verify before you
launch:

```bash
scripts/preflight_secops.sh
```

Two consequences follow from startup-only registration:

* Credentials are read from the process environment of the CLI **at launch**. If you rely
  on `direnv` or a `.env` file, enter the project directory before starting the CLI.
  Launching from elsewhere, or from a desktop launcher, silently falls back to whatever
  global ADC is present.
* A configuration change made mid-session takes effect only after a restart.

After launching, confirm the server actually connected:

```bash
ls -1 ~/.gemini/jetski/mcp/
```

A directory named for the server appears only once a session has connected and listed its
tools successfully. Its absence means the connection failed.

---

## Testing Plugin Installation

The plugin adheres to cross-harness packaging standards and can be installed and tested across different agent runtimes.

### Antigravity CLI (`agy`)

Install from a local clone for development testing:

```bash
agy plugin install ./plugins/cloud/google-secops
```

Or install directly from the remote repository branch:

```bash
agy plugin install https://github.com/dandye/google__skills/tree/feat-migrate-secops-adk-skill/plugins/cloud/google-secops
```

To uninstall or reinstall during development:

```bash
agy plugin uninstall google-secops
agy plugin install ./plugins/cloud/google-secops
```

### Gemini CLI

Install the extension from your local directory:

```bash
gemini extension install ./plugins/cloud/google-secops
```

Verify that Gemini CLI detects the extension:

```bash
gemini extension list
```

### Claude Code

Claude Code uses `.claude-plugin/plugin.json` and `mcp_config.json`. To test the MCP server connection directly in Claude Code:

```bash
claude mcp add chronicle https://chronicle.us.rep.googleapis.com/mcp
```

### OpenAI Codex

Codex utilizes `.codex-plugin/plugin.json` pointing to `./skills/` for skill discovery.

---

## Specialized Agents

The plugin bundles three specialized agents tailored for SOC operations and detection engineering. In Gemini CLI and Antigravity, invoke them directly using the `@` syntax or delegate tasks via subagent dispatch:

| Agent | Purpose | Primary Capabilities |
| :--- | :--- | :--- |
| `secops-triage-analyst` | Alert Triage | Evaluates detection metadata, scores entity risk, deduplicates alerts, calibrates severity, and dispatches dispositions. |
| `secops-investigator` | Incident Investigation | Conducts multi-hop entity pivoting, UDM graph exploration, parent-child process tree analysis, and timeline reconstruction. |
| `secops-detection-engineer` | Detection Engineering | Authors and validates YARA-L 2.0 detection rules, performs retrospective testing against historical UDM logs, and tunes alert filters. |

### Example Invocations

```bash
# Direct task to the triage analyst
@secops-triage-analyst Triage alert "alert-84920" and assess principal entity risk.

# Direct task to the incident investigator
@secops-investigator Reconstruct the process and network timeline for host "finance-srv-01".

# Direct task to the detection engineer
@secops-detection-engineer Validate and backtest the YARA-L rule for suspicious PowerShell execution.
```

---

## Verification and Smoke Testing

### 1. Verify Slash Commands

Because the command definition files are located in `commands/secops/*.toml`, Gemini CLI automatically namespaces them with a colon (`/secops:<command>`):

| Slash Command | Skill Bound | Function |
| :--- | :--- | :--- |
| `/secops:triage` | `skills/triage` | Triage alerts, assess risk, adjust severities |
| `/secops:investigate` | `skills/investigate` | UDM entity timelines, lateral movement checks |
| `/secops:hunt` | `skills/hunt` | Threat hunting hypotheses, IoC retroactive sweeps |
| `/secops:cases` | `skills/cases` | SOAR case creation, listing, comments, status |
| `/secops:detection-engineering` | `skills/detection-engineering` | YARA-L rule authoring, validation, test backtesting |

> [!NOTE]
> Gemini CLI compiles extension commands on startup. If you install or link the extension while a CLI session is already open, restart the session to register the slash commands.
>
> For instant project-level access without extension installation, symlink the commands directly:
> ```bash
> mkdir -p .gemini/commands
> ln -sfn $(pwd)/plugins/cloud/google-secops/commands/secops .gemini/commands/secops
> ```

### 2. Verify Remote MCP Connectivity

Run a quick query through your agent to verify communication with the Chronicle MCP server:

```text
/secops:cases list open cases
```

Or ask the agent:

```text
Check Google SecOps MCP connectivity by querying recent alerts in customer ${CUSTOMER_ID}.
```

Expected behavior:
* The agent loads the `google-secops` environment rules (`rules/secops-environment.md`).
* The agent issues an authenticated streamable-http POST to `${SERVER_URL}`.
* A structured response is returned from Google SecOps.

### 3. Run Automated Repository Tests

To verify manifest schemas, skill frontmatter validity, command references, and version consistency locally:

```bash
# Run unit and schema validation test suite
just test

# Run code style and format checks
just lint
```

---

## Plugin Directory Layout

```
plugins/cloud/google-secops/
├── README.md                      # Plugin installation and usage documentation
├── plugin.json                    # Agent Plugins 1.0.0 specification manifest
├── gemini-extension.json          # Gemini CLI extension descriptor and MCP settings
├── mcp.json                       # MCP server definition (streamable-http)
├── mcp_config.json                # Claude Code MCP configuration
├── .claude-plugin/
│   └── plugin.json                # Claude plugin manifest
├── .codex-plugin/
│   └── plugin.json                # Codex plugin manifest
├── rules/
│   └── secops-environment.md      # Environment parameters and ADC auth instructions
├── commands/
│   └── secops/                    # Slash command definitions
│       ├── cases.toml
│       ├── detection-engineering.toml
│       ├── hunt.toml
│       ├── investigate.toml
│       └── triage.toml
├── agents/                        # Specialized subagent definitions
│   ├── secops-detection-engineer.md
│   ├── secops-investigator.md
│   └── secops-triage-analyst.md
└── skills/                        # Packaged agent skills (with YAML frontmatter)
    ├── cases/
    │   └── SKILL.md
    ├── detection-engineering/
    │   └── SKILL.md
    ├── hunt/
    │   └── SKILL.md
    ├── investigate/
    │   └── SKILL.md
    └── triage/
        └── SKILL.md
```

---

## License

Apache-2.0
