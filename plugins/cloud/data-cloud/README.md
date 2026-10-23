# Data Cloud Plugins

This directory vendors the [Google Data Cloud](https://cloud.google.com/data-cloud) plugins as **git
submodules**, so they can be discovered and installed through the central `google/skills` repository. Each
submodule pins to a specific release tag of its upstream plugin repository, which remains the **source of
truth** for that plugin's skills and MCP server definition.

These plugins package product-specific **Skills** and (where applicable) **MCP servers** for their product's
common user journeys. The set mirrors the layout used by
[`GoogleCloudPlatform/data-cloud-plugins`](https://github.com/GoogleCloudPlatform/data-cloud-plugins).

## Installation

### Antigravity CLI (`agy`)

Antigravity CLI installs plugins directly from a repository path. Point `agy` at the plugin you want:

```bash
agy plugin install https://github.com/google/skills/plugins/cloud/data-cloud/alloydb
agy plugin install https://github.com/google/skills/plugins/cloud/data-cloud/spanner
```

> [!NOTE]
> Submodules are used here because Antigravity CLI does not yet support a marketplace manifest (as Claude Code
> and Codex do). Once marketplace support lands for `agy`, these submodules can be retired in favor of the
> shared manifest.

For Claude Code and Codex, install via the marketplace manifest at the root of this repository instead.

## Included Plugins

Each plugin is pinned to the release tag shown. To update the working tree to the pinned versions, run
`git submodule update --init` from the repo root.

| Product | Repository | Version | Description |
| :--- | :--- | :--- | :--- |
| **AlloyDB for PostgreSQL** | [alloydb-plugin](https://github.com/GoogleCloudPlatform/alloydb-plugin) | `0.2.0` | Create, connect, and interact with an AlloyDB for PostgreSQL database and data. |
| **AlloyDB Omni** | [alloydb-omni-plugin](https://github.com/GoogleCloudPlatform/alloydb-omni-plugin) | `0.2.2` | Create, connect, and interact with an AlloyDB Omni database and data. |
| **BigQuery Data Analytics** | [bigquery-data-analytics-plugin](https://github.com/GoogleCloudPlatform/bigquery-data-analytics-plugin) | `0.2.5` | Connect, query, and generate data insights for BigQuery datasets and data. |
| **Cloud SQL for MySQL** | [cloud-sql-mysql-plugin](https://github.com/GoogleCloudPlatform/cloud-sql-mysql-plugin) | `0.2.0` | Connect and interact with a Cloud SQL for MySQL database and data. |
| **Cloud SQL for PostgreSQL** | [cloud-sql-postgresql-plugin](https://github.com/GoogleCloudPlatform/cloud-sql-postgresql-plugin) | `0.4.0` | Create, connect, and interact with a Cloud SQL for PostgreSQL database and data. |
| **Cloud SQL for SQL Server** | [cloud-sql-sqlserver-plugin](https://github.com/GoogleCloudPlatform/cloud-sql-sqlserver-plugin) | `0.2.0` | Connect to and interact with a Cloud SQL for SQL Server database. |
| **Data Agent Kit** | [data-agent-kit-plugin](https://github.com/GoogleCloudPlatform/data-agent-kit-plugin) | `1.0.0` | A specialized suite of skills for data engineers and database practitioners on Google Cloud — architect data pipelines, transform data with dbt, write Spark/BigQuery notebooks, and orchestrate end-to-end workflows. |
| **Dataproc** | [dataproc-plugin](https://github.com/GoogleCloudPlatform/dataproc-plugin) | `0.1.0` | Manage Dataproc clusters and jobs. |
| **DB Context Engineering Agent** | [db-context-enrichment](https://github.com/GoogleCloudPlatform/db-context-enrichment) | `v0.7.2` | Author and maintain QueryData / Conversational Analytics API context sets that teach the NL→SQL planner your schema vocabulary and golden query shapes. |
| **Firestore** | [firestore-native-plugin](https://github.com/GoogleCloudPlatform/firestore-native-plugin) | `0.3.4` | Connect and interact with Cloud Firestore. |
| **Google Cloud Storage** | [google-cloud-storage-plugin](https://github.com/GoogleCloudPlatform/google-cloud-storage-plugin) | `3.0.1` | Vetted Google Cloud Storage skills for your coding agent. |
| **Knowledge Catalog** | [knowledge-catalog-plugin](https://github.com/GoogleCloudPlatform/knowledge-catalog-plugin) | `0.5.4` | Connect to Knowledge Catalog (formerly Dataplex) to discover, manage, monitor, and govern data and AI artifacts across your data platform. |
| **Looker** | [looker-plugin](https://github.com/GoogleCloudPlatform/looker-plugin) | `0.3.11` | Connect to Looker and interact with your data using LookML. |
| **Oracle Database** | [oracledb-plugin](https://github.com/GoogleCloudPlatform/oracledb-plugin) | `0.2.7` | Connect, query, and interact with Oracle Databases and their data. |
| **Spanner** | [spanner-plugin](https://github.com/GoogleCloudPlatform/spanner-plugin) | `0.3.6` | Connect and interact with Spanner data using natural language. |

## Updating a pinned version

Each submodule's tracked tag is recorded in the top-level `.gitmodules` (`branch = <version>`). To advance a
plugin to a newer release, update its submodule to the new tag and commit the pointer change:

```bash
cd plugins/cloud/data-cloud/<plugin>
git fetch --tags
git checkout <new-version>
cd -
git config -f .gitmodules submodule.<plugin>.branch <new-version>
git add .gitmodules plugins/cloud/data-cloud/<plugin>
git commit -m "feat(<plugin>): bump to <new-version>"
```
