import { describe, expect, test } from "bun:test";
import { mkdtemp, chmod, mkdir, rm, symlink } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const root = new URL("../", import.meta.url);
const codex = await Bun.file(new URL(".codex-plugin/plugin.json", root)).json();
const claude = await Bun.file(new URL(".claude-plugin/plugin.json", root)).json();
const script = await Bun.file(new URL("scripts/http-headers.ts", root)).text();
const launchers = [
  { name: "Codex", command: codex.mcpServers.secops.http_headers_helper },
  { name: "Claude", command: claude.mcpServers.secops.headersHelper },
];

type Options = {
  token?: string;
  tokenStatus?: number;
  project?: string;
  projectStatus?: number;
  override?: string;
  missingScript?: boolean;
  missingGcloud?: boolean;
};

async function runHelper(command: string, options: Options = {}) {
  const dir = await mkdtemp(join(tmpdir(), "secops auth "));
  try {
    const home = join(dir, "home with spaces");
    const installed = join(home, ".codex/plugins/cache/google-plugins/google-secops", codex.version);
    const cwd = join(dir, "unrelated project");
    const bin = join(dir, "bin");
    await Promise.all([mkdir(cwd, { recursive: true }), mkdir(bin, { recursive: true })]);
    if (!options.missingScript) await Bun.write(join(installed, "scripts/http-headers.ts"), script);
    await symlink(process.execPath, join(bin, "bun"));
    if (!options.missingGcloud) {
      const gcloud = join(bin, "gcloud");
      await Bun.write(gcloud, `#!/bin/sh
case "$*" in
  'auth application-default print-access-token') printf '%s' "$TEST_TOKEN"; printf '%s' 'private diagnostic' >&2; exit "$TEST_TOKEN_STATUS";;
  'config get-value project') printf '%s' "$TEST_PROJECT"; exit "$TEST_PROJECT_STATUS";;
  *) exit 99;;
esac
`);
      await chmod(gcloud, 0o755);
    }
    const result = Bun.spawnSync(["/bin/sh", "-c", command], {
      cwd,
      env: {
        PATH: bin,
        HOME: home,
        CLAUDE_PLUGIN_ROOT: installed,
        TEST_TOKEN: options.token ?? "test-token",
        TEST_TOKEN_STATUS: String(options.tokenStatus ?? 0),
        TEST_PROJECT: options.project ?? "test-project",
        TEST_PROJECT_STATUS: String(options.projectStatus ?? 0),
        PROJECT_ID: options.override ?? "",
      },
    });
    return { status: result.exitCode, stdout: result.stdout.toString(), stderr: result.stderr.toString() };
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}

test("native Codex manifest is selectable and versioned launchers use the shared script", async () => {
  const metadata = await Bun.file(new URL("plugin.json", root)).json();
  expect(metadata.$schema).toBeUndefined();
  expect(codex.name).toBe(metadata.name);
  expect(codex.version).toBe(metadata.version);
  expect(claude.version).toBe(codex.version);
  expect(codex.mcpServers.secops.url).toBe("https://chronicle.us.rep.googleapis.com/mcp");
  expect(claude.mcpServers.secops.url).toBe(codex.mcpServers.secops.url);
  expect(codex.mcpServers.secops.http_headers_helper).toBe(
    'bun "${HOME}/.codex/plugins/cache/google-plugins/google-secops/' + codex.version + '/scripts/http-headers.ts"',
  );
  expect(claude.mcpServers.secops.headersHelper).toBe('bun "${CLAUDE_PLUGIN_ROOT}/scripts/http-headers.ts"');
});

for (const { name, command } of launchers) {
  describe(`${name} bundled ADC helper`, () => {
    test("runs the installed script from unrelated cwd and paths containing spaces", async () => {
      const result = await runHelper(command);
      expect(result.status).toBe(0);
      expect(JSON.parse(result.stdout)).toEqual({ Authorization: "Bearer test-token", "x-goog-user-project": "test-project" });
      expect(result.stderr).toBe("");
    });

    test("PROJECT_ID overrides gcloud project lookup when inherited", async () => {
      const result = await runHelper(command, { override: "quota-project", projectStatus: 1 });
      expect(result.status).toBe(0);
      expect(JSON.parse(result.stdout)["x-goog-user-project"]).toBe("quota-project");
    });

    test("failed token command does not expose token output or diagnostics", async () => {
      const result = await runHelper(command, { tokenStatus: 1 });
      expect(result.status).not.toBe(0);
      expect(result.stdout).toBe("");
      expect(result.stderr).toContain("application-default login");
      expect(result.stderr).not.toContain("test-token");
      expect(result.stderr).not.toContain("private diagnostic");
    });

    test("empty token fails with actionable advice", async () => {
      const result = await runHelper(command, { token: "" });
      expect(result.status).not.toBe(0);
      expect(result.stdout).toBe("");
      expect(result.stderr).toContain("application-default login");
    });

    for (const token of ['invalid"token', "token\nheader"]) {
      test(`rejects malformed token ${JSON.stringify(token)}`, async () => {
        const result = await runHelper(command, { token });
        expect(result.status).not.toBe(0);
        expect(result.stdout).toBe("");
        expect(result.stderr).not.toContain(token);
      });
    }

    for (const project of ["", "(unset)", 'invalid"project', "project\nheader"]) {
      test(`rejects invalid quota project ${JSON.stringify(project)}`, async () => {
        const result = await runHelper(command, { project });
        expect(result.status).not.toBe(0);
        expect(result.stdout).toBe("");
        expect(result.stderr).toContain("PROJECT_ID");
      });
    }

    test("failed project command cannot emit headers even if it prints a project", async () => {
      const result = await runHelper(command, { projectStatus: 1 });
      expect(result.status).not.toBe(0);
      expect(result.stdout).toBe("");
      expect(result.stderr).toContain("PROJECT_ID");
    });

    test("missing gcloud fails without emitting credentials", async () => {
      const result = await runHelper(command, { missingGcloud: true });
      expect(result.status).not.toBe(0);
      expect(result.stdout).toBe("");
      expect(result.stderr).toContain("gcloud");
    });

    test("missing installed script fails without falling back to another helper", async () => {
      const result = await runHelper(command, { missingScript: true });
      expect(result.status).not.toBe(0);
      expect(result.stdout).toBe("");
    });
  });
}
