---
trigger: always_on
description: Google SecOps environment configuration and authentication parameters including Customer ID, Project ID, Region, and Server URL.
---

# Google SecOps Environment Context

When executing tools, custom commands, or skills that interact with Google Security Operations (Google SecOps, including detection engineering, alert triage, threat hunting, and case management), always adhere to the following authentication and environment configuration requirements:

## Authentication & Prerequisites

1. **Google Cloud SDK & Installation**:
   Ensure `gcloud` CLI is installed on your workstation. See [Google Cloud SDK Installation](https://cloud.google.com/sdk/docs/install).

2. **Google Cloud Authentication & Project Setup**:
   Ensure you are authenticated with Google Cloud using Application Default Credentials (ADC), have an active billing account linked to the project, and have set your quota project:
   ```bash
   PROJECT_ID="your-gcp-project-id"
   gcloud auth application-default login
   gcloud auth application-default set-quota-project "$PROJECT_ID"
   ```

3. **Required IAM Permissions**:
   Verify that your authenticated user or service account has been granted the appropriate Chronicle IAM roles:
   * `roles/chronicle.admin`: Full administrative access to rules, feeds, cases, and settings.
   * `roles/chronicle.editor`: Edit and run detection rules, run UDM queries, and update cases.
   * `roles/chronicle.viewer`: Read-only access to UDM events, alerts, entities, and cases.
   * `roles/serviceusage.serviceUsageConsumer`: Required to consume GCP APIs and invoke remote MCP services.

4. **Enable MCP Service**:
   The Chronicle MCP service must be enabled in your Google Cloud project:
   ```bash
   PROJECT_ID="your-gcp-project-id"
   gcloud beta services mcp enable chronicle.googleapis.com/mcp --project="$PROJECT_ID"
   ```

5. **Web Console First-Login Requirement**:
   Users must log into the Google SecOps web interface (`https://<customer-subdomain>.chronicle.security`) at least once prior to invoking the Google SecOps MCP server or API endpoints. This initial web login initializes authorization profiles for the user identity.

## Required Environment Variables

Always use the following configured environment parameters for Google SecOps operations:

* **Google Cloud Project ID (`PROJECT_ID`)**: `$PROJECT_ID`
* **Google SecOps Customer ID (`CUSTOMER_ID`)**: `$CUSTOMER_ID`
* **Google SecOps Region (`REGION`)**: `$REGION`
* **Server URL (`SERVER_URL`)**: `$SERVER_URL` (default: `https://chronicle.us.rep.googleapis.com/mcp`)

Whenever a Google SecOps MCP tool or workflow (such as `generate_threat_detection_opportunity`, `generate_synthetic_events`, `evaluate_rule_coverage_long_running`, `get_rule`, `generate_rules`, `create_rule`, `list_cases`, `udm_search`, etc.) requires a customer ID, project ID, region, or server URL parameter, always supply these exact configured values unless explicitly overridden by the user.
