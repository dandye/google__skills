# Google SecOps Plugin

Agent plugin providing Security Operations capabilities for Google Security Operations (Chronicle SIEM and SOAR).

This plugin packages domain-specific agent skills, environment configuration rules, and remote Model Context Protocol (MCP) server definitions connecting to Google SecOps.

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

### 5. Codex: automatic ADC headers

Codex loads the native `.codex-plugin/plugin.json` manifest, which bundles
`http_headers_helper` for the Streamable HTTP server. The helper runs
`gcloud auth application-default print-access-token` and returns an
`Authorization: Bearer …` header plus `x-goog-user-project`. It uses
`PROJECT_ID` when present in the helper process, otherwise the active gcloud
project. No manual `mcp_servers.secops` entry is needed.

Codex 0.154.0 starts header helpers with a restricted environment. Arbitrary
variables such as `PROJECT_ID`, `CLOUDSDK_CONFIG`, and
`GOOGLE_APPLICATION_CREDENTIALS` are not forwarded, so exporting them before
launching Codex is not sufficient for this version. Use the default gcloud
configuration and ADC available under the inherited home directory, and select
the intended quota project there:

```bash
gcloud config set project YOUR_QUOTA_PROJECT_ID
gcloud auth application-default login
gcloud auth application-default set-quota-project YOUR_QUOTA_PROJECT_ID
```

Ensure `gcloud` is on the PATH inherited by Codex. This runtime limitation is
tracked in [openai/codex#46244](https://github.com/openai/codex/issues/46244)
and is visible in the [0.154.0 helper implementation](https://github.com/openai/codex/blob/rust-v0.154.0/codex-rs/rmcp-client/src/http_headers.rs#L411-L437).

The root `plugin.json` intentionally omits the Agent Plugins `$schema` marker.
With that marker, Codex prioritizes the portable manifest and reads `mcp.json`,
whose schema cannot express this helper. Keep authentication in the native
Codex manifest; adding the marker back bypasses it. Other clients retain their
existing manifests and ADC configuration.

Codex caches helper headers per connection and can refresh them after an
authentication failure. See the [Codex MCP documentation](https://developers.openai.com/codex/mcp).

### 6. Preflight Verification

Agent runtimes register MCP tools once, at startup. If the connection fails, the session
simply has no SecOps tools; there is usually no error and no prompt. Ensure all environment
variables above are set before launching the agent runtime.

Two consequences follow from startup-only registration:

* Environment-dependent client configuration must be available **at launch**. If you
  rely on `direnv` or a `.env` file, enter the project directory before starting the CLI.
  Codex 0.154.0 header helpers have the additional environment restriction described
  above; they use the default gcloud configuration even if custom credential-location
  variables were exported in the parent shell.
* A configuration change made mid-session takes effect only after a restart.

After launching, confirm the server actually connected. The command differs per harness:

| Harness | Verify connection |
| :--- | :--- |
| Codex | Start a fresh session, then use `/mcp` and invoke a read-only SecOps tool |
| Claude Code | `claude mcp list` |
| Gemini CLI | `gemini mcp list` |
| Antigravity (`agy`) | `ls -1 ~/.gemini/jetski/mcp/` |

A server that failed to connect will be absent, or listed without its tools. Do not rely on
a configuration listing: most harnesses show what is *configured*, not what is *connected*.

---

## Testing Plugin Installation

The plugin ships client-specific manifests and can be installed and tested across different agent runtimes.

### Antigravity CLI (`agy`)

Install from a local clone for development testing:

```bash
agy plugin install ./plugins/cloud/google-secops
```

Or install directly from the remote repository branch:

```bash
agy plugin install https://github.com/google/skills/tree/main/plugins/cloud/google-secops
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

Add the Google plugins marketplace, then install the plugin:

```bash
claude plugin marketplace add google/skills
claude plugin install google-secops@google-plugins
```

### OpenAI Codex

Add the Google plugins marketplace, then install the plugin:

```bash
codex plugin marketplace add google/skills
codex plugin add google-secops@google-plugins
```

To test changes from this checkout, run these commands from the repository root:

```bash
codex plugin marketplace add .
codex plugin add google-secops@google-plugins
bun test plugins/cloud/google-secops/tests/codex-auth.test.ts
```

The local marketplace replaces the configured `google-plugins` source. To switch
back after publishing, run `codex plugin marketplace add google/skills` again.
Restart Codex after reinstalling, open `/mcp`, and confirm the `secops` server
connects. A successful install or MCP handshake alone does not prove access:
invoke a read-only SecOps tool against your configured customer as well.

If startup reports that the HTTP headers helper exited, check ADC with
`gcloud auth application-default print-access-token > /dev/null`. A
reauthentication error requires `gcloud auth application-default login` before
retrying. Remove a manually configured duplicate `mcp_servers.secops` entry if
you previously used the workaround, so the test exercises the plugin server.

---

## Verification and Smoke Testing

### Verify Remote MCP Connectivity and Skill Discovery

Run a quick query through your agent to verify communication with the Chronicle MCP server:

```text
Check Google SecOps MCP connectivity by querying recent alerts in customer ${CUSTOMER_ID}.
```

Expected behavior:
* The agent loads the `google-secops` environment rules (`rules/secops-environment.md`).
* The agent identifies and executes the relevant skill workflow (e.g. `secops-triage`).
* The agent issues an authenticated streamable-http POST to `${SERVER_URL}`.
* A structured response is returned from Google SecOps.


---

## Plugin Directory Layout

```
plugins/cloud/google-secops/
├── README.md                      # Plugin installation and usage documentation
├── plugin.json                    # Plugin metadata for agy
├── gemini-extension.json          # Gemini CLI extension descriptor and MCP settings
├── mcp.json                       # Portable MCP server definition
├── mcp_config.json                # MCP server definition (read by agy / Jetski)
├── .claude-plugin/
│   └── plugin.json                # Claude plugin manifest, incl. its MCP server and ADC helper
├── .codex-plugin/
│   └── plugin.json                # Native Codex manifest with ADC header helper
├── rules/
│   └── secops-environment.md      # Environment parameters and ADC auth instructions
└── skills/                        # Packaged agent skills (with YAML frontmatter)
    ├── secops-cases/
    │   └── SKILL.md
    ├── secops-detection-engineering/
    │   └── SKILL.md
    ├── secops-hunt/
    │   └── SKILL.md
    ├── secops-investigate/
    │   └── SKILL.md
    └── secops-triage/
        └── SKILL.md
```

---

## License

Apache-2.0
