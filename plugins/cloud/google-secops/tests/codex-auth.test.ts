import { describe, expect, test } from "bun:test";
import { mkdtemp, chmod, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const root = new URL("../", import.meta.url);
const manifest = await Bun.file(new URL(".codex-plugin/plugin.json", root)).json();
const helper = manifest.mcpServers.secops.http_headers_helper;

async function runHelper(options: { token?: string; tokenStatus?: number; project?: string; override?: string }) {
  const dir = await mkdtemp(join(tmpdir(), "secops-auth-"));
  try {
    const gcloud = join(dir, "gcloud");
    await Bun.write(gcloud, `#!/bin/sh
case "$*" in
  'auth application-default print-access-token') printf '%s' "$TEST_TOKEN"; exit "$TEST_TOKEN_STATUS";;
  'config get-value project') printf '%s' "$TEST_PROJECT";;
  *) exit 99;;
esac
`);
    await chmod(gcloud, 0o755);
    const result = Bun.spawnSync(["/bin/sh", "-c", helper], {
      env: { PATH: dir, TEST_TOKEN: options.token ?? "test-token", TEST_TOKEN_STATUS: String(options.tokenStatus ?? 0), TEST_PROJECT: options.project ?? "test-project", PROJECT_ID: options.override ?? "" },
    });
    return { status: result.exitCode, stdout: result.stdout.toString(), stderr: result.stderr.toString() };
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}

describe("Codex SecOps ADC helper", () => {
  test("native manifest remains selectable over portable metadata", async () => {
    const metadata = await Bun.file(new URL("plugin.json", root)).json();
    expect(metadata.$schema).toBeUndefined();
    expect(manifest.name).toBe(metadata.name);
    expect(manifest.version).toBe(metadata.version);
    expect(manifest.mcpServers.secops.url).toBe("https://chronicle.us.rep.googleapis.com/mcp");
  });

  test("uses ADC bearer token and active gcloud project", async () => {
    const result = await runHelper({});
    expect(result.status).toBe(0);
    expect(JSON.parse(result.stdout)).toEqual({ Authorization: "Bearer test-token", "x-goog-user-project": "test-project" });
  });

  test("PROJECT_ID overrides the active project", async () => {
    const result = await runHelper({ override: "quota-project" });
    expect(result.status).toBe(0);
    expect(JSON.parse(result.stdout)["x-goog-user-project"]).toBe("quota-project");
  });

  test("failed token command emits no credentials even if it prints a token", async () => {
    const result = await runHelper({ tokenStatus: 1 });
    expect(result.status).not.toBe(0);
    expect(result.stdout).toBe("");
  });

  test("empty token fails with actionable advice", async () => {
    const result = await runHelper({ token: "" });
    expect(result.status).not.toBe(0);
    expect(result.stdout).toBe("");
    expect(result.stderr).toContain("application-default login");
  });

  for (const project of ["", "(unset)", 'invalid"project', "project\nheader"]) {
    test(`rejects invalid quota project ${JSON.stringify(project)}`, async () => {
      const result = await runHelper({ project });
      expect(result.status).not.toBe(0);
      expect(result.stdout).toBe("");
      expect(result.stderr).toContain("PROJECT_ID");
    });
  }
});
