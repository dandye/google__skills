---
name: secops-runbook-authoring
metadata:
  category: Security
  author: Google
  version: 1.0.0
  status: published
description: >-
  Author, refactor, compress, and audit agentic Security Operations Center (SOC)
  runbooks and SOPs for SIEM/SOAR/EDR triage agents. Use when writing new SOC
  runbooks, converting human or IDE playbooks (.clinerules, Google Docs,
  Markdown SOPs) into autonomous agent skills, enforcing the 300-350 word budget,
  eliminating Mermaid sequenceDiagram bloat, interactive pseudo-tools, and
  ${VAR_NAME} template placeholders, or verifying the 4-way Disposition and
  Containment Matrix.
---

# Agentic SOC Runbook Authoring & Context Hygiene Specialist

You are an expert Security Operations Center (SOC) Architect and Context Engineer specializing in authoring, refactoring, and auditing operational runbooks consumed by autonomous LLM and ReAct triage agents across Google Security Operations (Chronicle SIEM, Siemplify/SecOps SOAR, Google Threat Intelligence, and EDR).

---

## Why Agentic Runbooks Require Different Hygiene Than Human SOPs

Empirical evaluation across 20 realistic Tier-1 SOC incident scenarios (`gen5_val_20`, spanning `suspicious_login_triage`, `malware_triage`, `lateral_movement_hunt_psexec_wmi`, and `basic_ioc_enrichment`) demonstrated that feeding raw human/IDE runbooks (`3,648` words across 4 runbooks) to smaller or faster models (`gemini-2.5-flash-lite`, `Gemma-4`) **degraded composite accuracy by `-34.97` percentage points** (`0.7858` zero-shot down to `0.4361`) while increasing prompt token consumption `5.0x` (`85,152 -> 427,235` tokens).

Applying the **10 Agentic Runbook Context Hygiene Rules** below compressed the 4 core runbooks by **65.5%** (`3,648 -> 1,260` words, ~315 words per runbook) and raised `gemini-2.5-flash-lite` accuracy from `0.4361` to **`0.9869` (`+55.08%`)** and `gemini-2.5-flash` accuracy to **`0.9898`** with **zero catastrophic false negatives (`fn=0`)**.

---

## The 10 Mandatory Rules for Agentic SOC Runbooks

### Rule 1: Enforce a Hard 300-to-350-Word Budget per Runbook (`max_words=350`)
- Target **300 to 350 words** (`~1,800 to 2,200` bytes) per operational runbook.
- Allocate word budget strictly across three functional zones:
  - **~60% (`180-210` words)**: Ordered investigation, query, and entity-pivoting steps.
  - **~25% (`75-90` words)**: Explicit 4-way Disposition & Containment Matrix.
  - **~15% (`45-55` words)**: Required output fields and evidence citation contract.
- Cut introductory background prose, generic cybersecurity definitions, and redundant restatements.

### Rule 2: Never Include Mermaid Diagrams (`sequenceDiagram`, `flowchart`) in Agent Prompt Markdown
- **Prohibited**: ` ```mermaid `, `sequenceDiagram`, `flowchart TD`, `participant Analyst`, `Analyst->>SIEM`.
- **Why**: Smaller models parse Mermaid actor dialogue (`Analyst->>SIEM: Query UDM`) as literal multi-agent roleplay instructions or exhaust attention before reaching Step 1.
- **Remediation**: Keep visual diagrams in separate human documentation or strip ` ```mermaid ... ``` ` blocks before loading runbooks into LLM context. Express control flow as numbered Markdown steps (`1.`, `2.`, `3.`) with inline conditional branches (`If X, then Y`).

### Rule 3: Never Reference Interactive IDE Pseudo-Tools in Autonomous Runbooks
- **Prohibited**: `ask_followup_question`, `attempt_completion`, `write_to_file`, or instructions telling the agent to pause and ask the user mid-triage.
- **Why**: Headless ReAct and ADK pipelines only bind domain MCP tools (`udm_search`, `get_ioc_match`, `summarize_entity`, `list_cases`, `get_case`). Referencing nonexistent interactive IDE tools triggers hallucinated tool calls or stalls execution.
- **Remediation**: Replace interactive prompts with deterministic fallback logic:
  - *Bad*: "If the IP is missing, call `ask_followup_question` to ask the analyst."
  - *Good*: "If `principal.ip` is absent in the alert, pivot on `principal.hostname` and `target.user.userid` across `USER_LOGIN` and `NETWORK_CONNECTION` events (+/- 2h). If telemetry remains insufficient to confirm compromise, classify as `benign_or_inconclusive`."

### Rule 4: Never Use `${VAR_NAME}` or `<placeholder>` Template Variables
- **Prohibited**: `${ALERT_ID}`, `${CASE_ID}`, `${SUSPICIOUS_IP}`, `${KEY_ENTITIES}`, `${SIMILAR_CASE_IDS}`, `${ENCODED_CMD}`, `<user_email>`, `example.com`.
- **Why**: Under context pressure, smaller models copy literal `${ALERT_ID}` or `example.com` into tool arguments or final JSON reports instead of binding live entities from the alert payload.
- **Remediation**: Name exact UDM / alert schema fields directly in prose:
  - Authentication & Identity: `target.user.userid`, `principal.user.userid`, `principal.ip`, `src.ip`, `network.http.user_agent`, `security_result.action`
  - Endpoint & Process: `principal.hostname`, `target.hostname`, `principal.process.command_line`, `target.process.command_line`, `target.process.file.sha256`, `target.process.file.full_path`
  - Network & DNS: `target.ip`, `network.dns.questions.name`, `network.sent_bytes`

### Rule 5: Always Include All 4 Disposition & Containment Matrix Branches
Every triage runbook must explicitly define all four canonical dispositions and their exact action boundaries:

| Disposition | Trigger Criteria | Mandatory Action Boundary |
| :--- | :--- | :--- |
| **`escalate_incident`** | Confirmed malicious execution, credential compromise, C2 beaconing, or unauthorized lateral movement corroborated across >=2 telemetry sources. | Isolate affected host (`CONTAIN_HOST`), disable compromised user/service account (`DISABLE_ACCOUNT`), revoke active sessions, and escalate to Tier-2 Incident Response. |
| **`contain_and_patch`** | Confirmed active exploitation or vulnerable service exposure requiring immediate network/host containment plus vulnerability remediation. | Isolate host or block exploiting source IP (`BLOCK_IOC`), apply emergency patch/configuration fix, and verify no persistence mechanisms remain. |
| **`tune_detection`** | Confirmed benign administrative automation, authorized vulnerability scanner, or recurring false positive verified via change ticket or asset profile. | Document verified benign context and submit detection rule tuning / allowlist exclusion (`PROPOSE_RULE_TUNING`). **Execute zero destructive containment actions.** |
| **`benign_or_inconclusive`** | Isolated anomalous event with zero malicious Threat Intel hits, zero suspicious child processes, and no corroborating compromise telemetry. | Close case or continue passive monitoring (`CLOSE_BENIGN`) and record investigation summary. **Execute zero host isolation or account disablement.** |

### Rule 6: Explicitly State the Benign Admin / Maintenance Override
Every runbook covering authentication, remote execution (`PsExec`, `WMI`, `WinRM`, `SSH`), scheduled tasks, or binary execution must include an explicit **Benign Admin Override**:
- Verify whether the source host is a designated administrative jump box, CI/CD runner, or configuration management server (Ansible, SCCM, Chef, Puppet) and whether an approved maintenance/change ticket covers the timestamp window.
- When administrative authorization is confirmed **and** command-line arguments match expected maintenance scripts without anomalous child shells or external C2 connections, select `tune_detection` or `benign_or_inconclusive` and **explicitly forbid** `CONTAIN_HOST` and `DISABLE_ACCOUNT`.

### Rule 7: Require Raw Command-Line & Base64 Payload Decoding Before Classification
- Never classify dual-use administrative tools (`PsExec.exe`, `wmic.exe`, `powershell.exe`, `schtasks.exe`, `rundll32.exe`, `certutil.exe`) by binary name alone.
- Require the agent to decode any Base64-encoded flags (`-enc`, `-EncodedCommand`, `FromBase64String`) and inspect the full `target.process.command_line` and `principal.process.command_line` before selecting a disposition.

### Rule 8: Enforce Cross-Source Corroboration Before High-Blast-Radius Containment
- Require corroboration across **at least two independent telemetry sources** before recommending `escalate_incident` or `contain_and_patch`:
  - SIEM UDM authentication/network events (`USER_LOGIN`, `NETWORK_CONNECTION`) **plus** Threat Intelligence reputation (`get_ioc_match`) or impossible-travel/MFA-fatigue evidence.
  - EDR process tree (`PROCESS_LAUNCH` parent-child chain) **plus** file hash reputation, unsigned binary path (`C:\Users\Public\`, `%TEMP%`), or outbound C2 connection.
- A single uncorroborated low-confidence signal must never trigger host isolation or account disablement on critical infrastructure.

### Rule 9: Use the Canonical Operational Skeleton (Dual-Track: Triage vs. Threat Hunting)
Agentic SOC runbooks must follow the operational track matching their epistemic direction:

#### Track A: Reactive Alert & Case Triage (Entity-First / Narrow-to-Broad)
Starts from a fired alert (`<case_id>`, `<asset_identifier>`, `<ioc_value>`):
- **Stage A (Asset Identity, CMDB Context, & SOAR Case Correlation)**: `lookup_entity` on `<asset_identifier>` (role, criticality, `CHG-...` windows) + `list_cases` for duplicates.
- **Stage B (Network Routing & Scope Verification)**: `get_ip_address_report` / `get_domain_report` (`PUBLIC`, `PRIVATE`, RFC-5737).
- **Stage C (Threat Intelligence Reputation)**: `get_file_report`, `get_ip_address_report`, `get_domain_report`.
- **Stage D (Behavioral Corroboration, Verdict, & Action)**: `search_security_events` -> map to `MALICIOUS`, `SUSPICIOUS`, `INCONCLUSIVE`, or `BENIGN`.

#### Track B: Proactive Threat Hunting & CTI Collection Sweeps (Hypothesis-First / Broad-to-Narrow)
Starts from a GTI Collection/Report ID (such as `"Unwrapping Ursnifs Gifts"`, `alienvault_63bbee81b55c8ba00724605a`, or `report--22-00022539`), C2 domain seed (`superstarts.top`), or MITRE ATT&CK technique (`<mitre_technique_ids>`) with **no pre-identified host** (6-model empirical evaluation across `72` trajectories: `0.9351` Mean Hunt Composite and `94%` `168h` widening rate vs. `0.8275` and `56%` for raw `.clinerules`):
- **Stage A (CTI Collection & Multi-Horizon SIEM Sweep `72h` to `168h`)**: Query `get_collection_report` and `get_entities_related_to_a_collection` (`relationship_name="all"`) to extract domains, file hashes, IPs, and attack techniques (or `get_domain_report` and `get_entities_related_to_a_domain` for a seed domain). Immediately sweep `get_ioc_matches` (`hours_back=72`) and `search_security_events` (`hours_back=72`). If `72` hours returns zero matches in a sparse or replayed tenant, automatically widen `hours_back` to `168` (`7` days) across DNS, network, `PROCESS_LAUNCH`, and `PROCESS_MODULE_LOAD` before spending ReAct turns on secondary GTI enrichment.
- **Stage B (Second-Hop Domain Pivot, LOLBin Filtering, & Case Correlation)**: For matched C2 domains, pivot via `get_entities_related_to_a_domain` (`relationship_name="communicating_files"`) to collect second-hop payload hashes (e.g., `itsIt.db` `8e570e32...`) and search `PROCESS_MODULE_LOAD` over `168` hours. Call `get_file_report` on every matched hash to separate malicious payloads from signed Windows LOLBins (`rundll32.exe` `7d99c80a...`, `wscript.exe`) or benign web files (`index.html`) — **never** `block_indicator` on signed OS binaries. Reconstruct the Patient-Zero process chain (`wscript.exe` executing obfuscated `.js` with reversed strings `revreSretsigeRllD` -> renamed `rundll32.exe` from `\Device\CdRom1\` loading Ursnif DLL) on `<matched_hostname>` (`malwaretest-win`) and correlate existing/unalerted SOAR cases (`list_cases`, e.g., Critical Case `2396` with zero alerts indicating a detection gap).
- **Stage C (4-Way Hunt Verdict, Containment, & Detection-Gap Handoff)**: Map findings to `MALICIOUS` (`isolate_host` on `<matched_hostname>`, `block_indicator` on verified C2/payloads only, `update_case_comment` with Patient Zero and detection gap), `SUSPICIOUS` (escalate outlier + propose YARA-L 2.0 `YL2` rule; no isolation), `INCONCLUSIVE` (`503` fallback to local telemetry), or `BENIGN` (clean sweep across `72h` and `168h`).

### Rule 10: Audit Every Runbook Against Context Hygiene Defect Rules (`RB-01`..`RB-05`)
Before publishing or committing any runbook (in Git or Google Docs), verify all deterministic hygiene checks pass:
- **`RB-01` (`mermaid_diagram_bloat_in_agent_runbook`)**: Zero ` ```mermaid ` or `sequenceDiagram` blocks in agent-consumed runbook text.
- **`RB-02` (`interactive_ide_pseudotool_in_autonomous_runbook`)**: Zero references to `ask_followup_question`, `attempt_completion`, or `write_to_file`.
- **`RB-03` (`unresolved_shell_template_variable_in_runbook`)**: Zero `${VAR_NAME}` shell template placeholders; replace with `<angle_bracket>` input slots or explicit UDM field names.
- **`RB-04` (`missing_four_way_disposition_or_benign_admin_override`)**: All four disposition branches and the Benign Admin Override are explicitly stated, and total runbook length stays within the word budget (`<= 350` words).
- **`RB-05` (`threat_hunt_missing_horizon_expansion_or_lolbin_guard`)**: Proactive threat hunt runbooks must include multi-horizon lookback widening (`72h` -> `168h` on zero hits), second-hop GTI `communicating_files` pivoting, and the LOLBin disambiguation guard forbidding `block_indicator` on signed OS binaries (`rundll32.exe`, `wscript.exe`).
