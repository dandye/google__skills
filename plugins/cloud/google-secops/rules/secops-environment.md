---
name: secops-environment
description: Google SecOps environment configuration and authentication parameters including Customer ID, Project ID, Region, and Server URL.
---

# Google SecOps Environment Context

When executing tools, custom commands, or skills that interact with Google SecOps (including detection engineering, alert triage, threat hunting, and case management), always adhere to the following authentication and environment configuration requirements:

## Authentication & Prerequisites

1. **Google Cloud Authentication**:
   Ensure you are authenticated with Google Cloud using Application Default Credentials (ADC) and have set your quota project:
   ```bash
   gcloud auth application-default login
   gcloud auth application-default set-quota-project ${PROJECT_ID}
   ```

2. **Enable MCP Service**:
   The Chronicle MCP service must be enabled in your Google Cloud project:
   ```bash
   gcloud beta services mcp enable chronicle.googleapis.com/mcp --project=${PROJECT_ID}
   ```

3. **GUI Login Requirement**:
   Users must log into the Google SecOps web interface at least once prior to invoking the SecOps MCP server or API endpoints.

## Required Environment Variables

Always use the following configured environment parameters for SecOps operations:

* **Google Cloud Project ID (`PROJECT_ID`)**: `${PROJECT_ID}`
* **Chronicle Customer ID (`CUSTOMER_ID`)**: `${CUSTOMER_ID}`
* **Chronicle Region (`REGION`)**: `${REGION}`
* **Server URL (`SERVER_URL`)**: `${SERVER_URL}` (default: `https://chronicle.us.rep.googleapis.com/mcp`)

Whenever a SecOps MCP tool or workflow (such as `generate_threat_detection_opportunity`, `generate_synthetic_events`, `evaluate_rule_coverage`, `get_rule`, `generate_rules`, `create_rule`, `list_cases`, `udm_search`, etc.) requires a customer ID, project ID, region, or server URL parameter, always supply these exact configured values unless explicitly overridden by the user.
