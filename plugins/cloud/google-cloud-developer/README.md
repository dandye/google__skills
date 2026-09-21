# google-cloud-developer plugin

The `google-cloud-developer` plugin equips AI coding agents with foundational
skills, safety guardrails, and live documentation grounding for building on
Google Cloud.

Built on the open [Agent Plugins specification](https://agent-plugins.org/),
this plugin bundles curated Agent Skills, routing rules, and configuration for
the **Developer Knowledge MCP server** into a single portable package.

---

## Installation

### Antigravity CLI

Install the plugin directly via the CLI using its path in the Google Agent
Skills repository:

```bash
agy plugin install https://github.com/google/skills/plugins/cloud/google-cloud-developer
```

### Claude Code

Add the Google plugins marketplace, then install the plugin:

```bash
claude plugin marketplace add google/skills
claude plugin install google-cloud-developer@google-plugins
```

### Codex CLI

Add the Google plugins marketplace, then install the plugin:

```bash
codex plugin marketplace add google/skills
codex plugin add google-cloud-developer@google-plugins
```

---

## What's Included

### Bundled Skills

-   **[gcloud](./skills/gcloud)**: Safety-critical validation, best practices,
    and execution guardrails for `gcloud` CLI commands.
-   **[google-cloud-recipe-auth](./skills/google-cloud-recipe-auth)**:
    Authentication workflows, credential selection, and service identity best
    practices.
-   **[google-cloud-recipe-gcp-juggling](./skills/google-cloud-recipe-gcp-juggling)**:
    Per-directory isolation of `gcloud` configurations, Application Default
    Credentials (ADC), service account impersonation, and Python virtual
    environments using `direnv`.
-   **[google-cloud-recipe-onboarding](./skills/google-cloud-recipe-onboarding)**:
    First-project onboarding, account setup, and billing configuration.
-   **[finding-google-skills](./skills/finding-google-skills)**: Discovery and
    on-demand installation of specialized skills from the Google Agent Skills
    repo.
-   **[retrieving-developer-knowledge](./skills/retrieving-developer-knowledge)**:
    Grounded retrieval of official Google documentation.

### MCP Server

-   **[Developer Knowledge MCP server](https://developers.google.com/knowledge/mcp)**:
    Provides AI agents with up-to-date grounding in official Google developer
    documentation over streamable HTTP.

### Routing Rules

-   **[google-cloud-discovery.md](./rules/google-cloud-discovery.md)**:
    Always-on routing map that guides the agent to discover and suggest deeper
    product-specific skills (such as `gke-*`, `agent-platform-*`,
    `google-cloud-waf-*`, and `<product>-basics`) when a task requires
    specialized domain knowledge beyond the foundational bundle.

---

## Plugin in Action

To see how this plugin works, consider a situation where you're bootstrapping a
new project as part of working on a script. With the `google-cloud-developer`
plugin installed, you can prompt your agent:

> *I'm brand new to this platform, and I need to get an account and a first
> project with billing set up. Then, I need my local machine authenticated so a
> script that I'm writing can call the APIs as a service identity instead of as
> me.*

1.  **Environment awareness**: The agent silently runs background checks against
    your live environment for prerequisites like CLI availability and potential
    existing projects or organizations.

2.  **Review**: The agent considers IAM best practices to avoid risks that might
    be assumed as part of the prompt, like accidental key leaks or git commits.

3.  **Interaction with guardrails**: The agent outlines a workflow roadmap and
    offers to act on those steps before modifying any resources.
