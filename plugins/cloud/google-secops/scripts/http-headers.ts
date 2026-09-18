/** Emit runtime ADC headers for the Codex and Claude Streamable HTTP clients. */
function fail(message: string): never {
  console.error(`google-secops: ${message}`);
  process.exit(1);
}

function gcloud(args: string[], advice: string): string {
  try {
    const result = Bun.spawnSync(["gcloud", ...args], {
      stdin: "ignore",
      stdout: "pipe",
      stderr: "pipe",
    });
    // Do not forward stdout/stderr on failure: they may contain credentials.
    if (result.exitCode !== 0) fail(advice);
    return result.stdout.toString().trim();
  } catch {
    fail("could not run gcloud; install the Google Cloud CLI and check PATH");
  }
}

const token = gcloud(
  ["auth", "application-default", "print-access-token"],
  "ADC token command failed; run: gcloud auth application-default login",
);
if (!token) fail("no ADC token; run: gcloud auth application-default login");
if (!/^[A-Za-z0-9._~+\/-]+=*$/.test(token)) fail("ADC command returned an invalid bearer token");

const projectAdvice = "no valid quota project; set PROJECT_ID or run: gcloud config set project PROJECT_ID";
const project = process.env.PROJECT_ID || gcloud(["config", "get-value", "project"], projectAdvice);
if (!/^[a-zA-Z0-9:.-]+$/.test(project)) fail(projectAdvice);

// JSON serialization keeps stdout a single header object. Never persist tokens.
console.log(JSON.stringify({
  Authorization: `Bearer ${token}`,
  "x-goog-user-project": project,
}));
