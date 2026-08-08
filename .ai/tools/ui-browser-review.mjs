#!/usr/bin/env node

import { spawn, spawnSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import {
  lstat,
  mkdir,
  readFile,
  realpath,
  rename,
  writeFile,
} from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const TOOL_PATH = fileURLToPath(import.meta.url);
const REPOSITORY_ROOT = path.resolve(path.dirname(TOOL_PATH), "../..");
const FRONTEND_ROOT = path.join(REPOSITORY_ROOT, "frontend");
const WORK_ROOT = path.join(REPOSITORY_ROOT, ".ai", "work");
const CURRENT_PLAN = path.join(REPOSITORY_ROOT, ".ai", "CURRENT_PLAN.md");
const BASELINE_ROOT = path.join(FRONTEND_ROOT, "ui-baselines");
const VITE_EXECUTABLE = path.join(
  FRONTEND_ROOT,
  "node_modules",
  "vite",
  "bin",
  "vite.js",
);
const VITE_CONFIG = path.join(
  REPOSITORY_ROOT,
  ".ai",
  "tools",
  "ui-vite.config.mjs",
);
const SERVER_START_TIMEOUT_MS = 30_000;
const SERVER_STOP_TIMEOUT_MS = 5_000;
const MAX_SERVER_LOG_BYTES = 64 * 1024;
const MAX_JSON_BYTES = 5 * 1024 * 1024;
const MAX_IMAGE_BYTES = 25 * 1024 * 1024;
const PIXEL_CHANNEL_THRESHOLD = 16;
const MAX_DIFFERENT_PIXEL_RATIO = 0.001;
const WORK_DIRECTORY_PATTERN =
  /^\.ai\/work\/([A-Za-z0-9][A-Za-z0-9._-]{0,63})\/?$/;
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"];
const SYNTHETIC_USER = {
  id: "local-owner",
  first_name: "Local",
  last_name: "Owner",
  email: "owner@example.test",
};
const SYNTHETIC_PROJECT = {
  id: "project-alpha",
  name: "Alpha",
  lifecycle_state: "active",
  created_at: "2026-07-22T00:00:00Z",
  updated_at: "2026-07-22T00:00:00Z",
  ticket_url_template: null,
};
const SYNTHETIC_PROJECT_WITH_TICKET_TEMPLATE = {
  ...SYNTHETIC_PROJECT,
  ticket_url_template: "https://tickets.example.test/T-<ticket_id>",
  updated_at: "2026-07-22T00:01:00Z",
};
const SYNTHETIC_EMPTY_PROJECT = {
  id: "project-empty",
  name: "Leeres Projekt",
  lifecycle_state: "active",
  created_at: "2026-07-22T00:00:00Z",
  updated_at: "2026-07-22T00:00:00Z",
  ticket_url_template: null,
};
const SYNTHETIC_IMPORT_LOG = {
  id: "import-log-1",
  source_type: "csv",
  source_name: "fixture.csv",
  status: "completed",
  failure_reason: null,
  total_records: 4,
  valid_records: 4,
  skipped_records: 0,
  dataset_version_id: "dataset-1",
  dataset_display_name: "Fixture dataset",
  dataset_deleted_at: null,
};
const SYNTHETIC_PROVIDER = {
  id: "provider-ollama",
  provider: "ollama",
  display_name: "Lokales Ollama",
  endpoint_url: "http://localhost:11434",
  available_models: ["local-embed", "llama3.1"],
  manual_models: ["local-embed"],
  llm_models: ["llama3.1"],
  api_key_set: false,
  updated_at: "2026-07-22T00:00:00Z",
};
const SYNTHETIC_INDEXING_RUN = {
  id: "run-completed",
  project_id: "project-alpha",
  dataset_version_id: "dataset-1",
  dataset_display_name: "Fixture dataset",
  dataset_deleted_at: null,
  status: "completed",
  progress: 100,
  phase: "completed",
  provider: "vllm",
  model: "local-embed",
  parameters: {},
  error_code: null,
  error_message: null,
  diagnostics: { embeddings_written: 8 },
  started_at: "2026-07-22T00:00:00Z",
  completed_at: "2026-07-22T00:00:01Z",
  cancel_requested_at: null,
  deleted_at: null,
  created_at: "2026-07-22T00:00:00Z",
  updated_at: "2026-07-22T00:00:01Z",
};
const SYNTHETIC_CLUSTER_SET = {
  id: "cluster-set-1",
  project_id: "project-alpha",
  indexing_run_id: "run-completed",
  dataset_version_id: "dataset-1",
  dataset_display_name: "Fixture dataset",
  indexing_deleted_at: null,
  parent_cluster_set_id: null,
  display_name: "Antworten fein",
  status: "completed",
  progress: 100,
  phase: "completed",
  derivation_type: "root",
  vector_basis: "combined",
  message_weight: 0.4,
  answer_weight: 0.6,
  algorithm: "hdbscan",
  parameters: { min_cluster_size: 2, outlier_threshold: 0.72 },
  source_snapshot: { type: "all_dataset_pairs", source_pair_count: 4 },
  llm_provider: "ollama",
  llm_model: "llama3.1",
  llm_parameters: { enabled: true },
  llm_sample_strategy: { strategy: "random", requested: 2, seed: 7 },
  error_code: null,
  error_message: null,
  diagnostics: {},
  started_at: "2026-07-22T00:00:00Z",
  completed_at: "2026-07-22T00:00:03Z",
  cancel_requested_at: null,
  deleted_at: null,
  created_at: "2026-07-22T00:00:00Z",
  updated_at: "2026-07-22T00:00:03Z",
  cluster_count: 3,
};
const SYNTHETIC_CHILD_CLUSTER_SET = {
  ...SYNTHETIC_CLUSTER_SET,
  id: "cluster-set-child-1",
  parent_cluster_set_id: "cluster-set-1",
  display_name: "Antworten fein — Retouren",
  derivation_type: "refinement",
  vector_basis: "answer",
  cluster_count: 1,
  created_at: "2026-07-22T00:05:00Z",
  updated_at: "2026-07-22T00:05:03Z",
};
const SYNTHETIC_CLUSTERS = [
  {
    id: "cluster-1",
    project_id: "project-alpha",
    analysis_run_id: "run-completed",
    dataset_version_id: "dataset-1",
    cluster_set_id: "cluster-set-1",
    auto_title: "Passwort zurücksetzen",
    manual_title: null,
    effective_title: "Passwort zurücksetzen",
    auto_category: "Konto",
    manual_category: null,
    effective_category: "Konto",
    auto_status: "unreviewed",
    manual_status: null,
    effective_status: "unreviewed",
    score: 0.91,
    is_outlier: false,
    algorithm: "hdbscan",
    member_count: 2,
    metadata: { qa_mismatch: { average: 0.12, maximum: 0.44 } },
    auto_summary_question: "Wie können Kunden ihr Passwort zurücksetzen?",
    auto_summary_answer: "Sende den Link zum Zurücksetzen und erkläre die Frist.",
  },
  {
    id: "cluster-2",
    project_id: "project-alpha",
    analysis_run_id: "run-completed",
    dataset_version_id: "dataset-1",
    cluster_set_id: "cluster-set-1",
    auto_title: "Veraltete Abrechnung",
    manual_title: null,
    effective_title: "Veraltete Abrechnung",
    auto_category: "Abrechnung",
    manual_category: null,
    effective_category: "Abrechnung",
    auto_status: "unreviewed",
    manual_status: "rejected",
    effective_status: "rejected",
    score: 0.61,
    is_outlier: false,
    algorithm: "hdbscan",
    member_count: 1,
    metadata: {},
    auto_summary_question: "Warum wurde eine alte Rechnung belastet?",
    auto_summary_answer: "Prüfe Rechnungsdatum und Erstattungspfad.",
  },
  {
    id: "cluster-3",
    project_id: "project-alpha",
    analysis_run_id: "run-completed",
    dataset_version_id: "dataset-1",
    cluster_set_id: "cluster-set-1",
    auto_title: "Einzelne Retourenfrage",
    manual_title: null,
    effective_title: "Einzelne Retourenfrage",
    auto_category: "Retoure",
    manual_category: null,
    effective_category: "Retoure",
    auto_status: "outlier",
    manual_status: null,
    effective_status: "outlier",
    score: 0.22,
    is_outlier: true,
    algorithm: "hdbscan",
    member_count: 1,
    metadata: { qa_mismatch: { maximum: 0.78 } },
    auto_summary_question: "Wie wird ein Zubehörteil retourniert?",
    auto_summary_answer: "Erzeuge ein Retourenlabel für Zubehör.",
  },
];
const SYNTHETIC_CLUSTER_SOURCES = [
  {
    cluster_id: "cluster-1",
    message_pair_id: "pair-1",
    ticket_id: "T-1",
    message_group_id: "G-1",
    message: "Ich habe mein Passwort vergessen. Was kann ich tun?",
    answer: "Nutze den Link zum Zurücksetzen. Der Link ist 30 Minuten gültig.",
    membership_score: 0.91,
    is_outlier: false,
    assignment_type: "automatic",
  },
  {
    cluster_id: "cluster-1",
    message_pair_id: "pair-2",
    ticket_id: "T-2",
    message_group_id: "G-2",
    message: "Der Reset-Link ist abgelaufen.",
    answer: "Fordere einen neuen Reset-Link an und prüfe den Spam-Ordner.",
    membership_score: 0.86,
    is_outlier: false,
    assignment_type: "automatic",
  },
];
const SYNTHETIC_EXPORT_LOG = {
  id: "export-explorer-1",
  project_id: "project-alpha",
  export_type: "explorer_csv",
  include_original_text: false,
  filters: {},
  selection: {},
  dataset_version_id: "dataset-1",
  analysis_run_id: "run-completed",
  cluster_set_id: "cluster-set-1",
  output_filename: "explorer_csv-cluster-set-1.csv",
  output_path: null,
  row_count: 2,
  created_at: "2026-07-23T00:00:00Z",
};

function fail(message) {
  throw new Error(message);
}

function isBelow(candidate, boundary) {
  const relative = path.relative(boundary, candidate);
  return (
    relative !== "" &&
    relative !== ".." &&
    !relative.startsWith(`..${path.sep}`) &&
    !path.isAbsolute(relative)
  );
}

export function parseActiveWorkDirectory(currentPlanText) {
  if (/^No active requirement\.\s*$/m.test(currentPlanText)) {
    fail("UI browser automation requires an active work item");
  }
  const match = currentPlanText.match(
    /^- Work directory:\s*`?([^`\n]+)`?\s*$/m,
  );
  if (match === null) {
    fail("CURRENT_PLAN.md does not declare an active work directory");
  }
  const value = match[1].trim();
  const validated = value.match(WORK_DIRECTORY_PATTERN);
  if (validated === null) {
    fail("active work directory must be one direct child below .ai/work");
  }
  return { relative: value.replace(/\/$/, ""), changeId: validated[1] };
}

export function validateBaseUrl(value) {
  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    fail("browser review base_url must be a valid URL");
  }
  if (
    parsed.protocol !== "http:" ||
    parsed.hostname !== "127.0.0.1" ||
    parsed.username ||
    parsed.password ||
    parsed.search ||
    parsed.hash ||
    parsed.pathname !== "/" ||
    !parsed.port
  ) {
    fail(
      "browser review base_url must be an explicit http://127.0.0.1:<port> loopback root",
    );
  }
  const port = Number(parsed.port);
  if (!Number.isInteger(port) || port < 1024 || port > 65_535) {
    fail("browser review port must be between 1024 and 65535");
  }
  return parsed;
}

export function isAllowedBrowserRequest(requestUrl, baseUrl) {
  let request;
  try {
    request = new URL(requestUrl);
  } catch {
    return false;
  }
  return request.protocol === "http:" && request.origin === baseUrl.origin;
}

export function isAllowedBrowserSocket(requestUrl, baseUrl) {
  let request;
  try {
    request = new URL(requestUrl);
  } catch {
    return false;
  }
  return (
    request.protocol === "ws:" &&
    request.hostname === baseUrl.hostname &&
    request.port === baseUrl.port &&
    !request.username &&
    !request.password
  );
}

export function safeBrowserRequestLabel(requestUrl) {
  try {
    const request = new URL(requestUrl);
    return `${request.protocol}//${request.host}${request.pathname}`.slice(
      0,
      512,
    );
  } catch {
    return "<invalid URL>";
  }
}

export function comparePixelArrays(
  expected,
  actual,
  channelThreshold = PIXEL_CHANNEL_THRESHOLD,
) {
  if (expected.length !== actual.length || expected.length % 4 !== 0) {
    fail("visual comparison requires equally sized RGBA pixel arrays");
  }
  let differentPixels = 0;
  for (let offset = 0; offset < expected.length; offset += 4) {
    let different = false;
    for (let channel = 0; channel < 4; channel += 1) {
      if (
        Math.abs(expected[offset + channel] - actual[offset + channel]) >
        channelThreshold
      ) {
        different = true;
        break;
      }
    }
    if (different) {
      differentPixels += 1;
    }
  }
  const totalPixels = expected.length / 4;
  return {
    differentPixels,
    totalPixels,
    ratio: totalPixels === 0 ? 0 : differentPixels / totalPixels,
  };
}

async function exists(candidate) {
  try {
    await lstat(candidate);
    return true;
  } catch (error) {
    if (error?.code === "ENOENT") {
      return false;
    }
    throw error;
  }
}

async function ensureDirectoryWithoutSymlinks(root, segments) {
  let current = root;
  for (const segment of segments) {
    current = path.join(current, segment);
    if (await exists(current)) {
      const metadata = await lstat(current);
      if (metadata.isSymbolicLink() || !metadata.isDirectory()) {
        fail(`UI evidence path is not a real directory: ${current}`);
      }
    } else {
      await mkdir(current, { mode: 0o700 });
    }
  }
  return current;
}

async function resolveActiveWork() {
  const currentPlanText = await readFile(CURRENT_PLAN, "utf8");
  const declared = parseActiveWorkDirectory(currentPlanText);
  const lexical = path.resolve(REPOSITORY_ROOT, declared.relative);
  const realWorkRoot = await realpath(WORK_ROOT);
  const realWork = await realpath(lexical);
  if (realWork !== lexical || !isBelow(realWork, realWorkRoot)) {
    fail("active work directory must be symlink-free and below .ai/work");
  }
  const evidence = await ensureDirectoryWithoutSymlinks(realWork, ["evidence"]);
  const ui = await ensureDirectoryWithoutSymlinks(evidence, ["ui"]);
  await ensureDirectoryWithoutSymlinks(ui, ["desktop"]);
  await ensureDirectoryWithoutSymlinks(ui, ["mobile"]);
  await ensureDirectoryWithoutSymlinks(ui, ["accessibility"]);
  await ensureDirectoryWithoutSymlinks(ui, ["reports"]);
  return { ...declared, workDirectory: realWork, evidenceDirectory: ui };
}

function loadProjectConfiguration() {
  const query = `
import json
import pathlib
import sys
root = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(root / ".ai" / "tools"))
from _common import get, load_yaml_subset
data = load_yaml_subset(root / ".ai" / "project.yaml")
print(json.dumps({
    "browserCommand": get(data, "ui_quality", "browser_review", "command", default=""),
    "baseUrl": get(data, "ui_quality", "browser_review", "base_url", default=""),
    "viewports": get(data, "ui_quality", "browser_review", "viewports", default={}),
    "accessibilityCommand": get(data, "ui_quality", "accessibility", "command", default=""),
    "visualRegressionCommand": get(data, "ui_quality", "visual_regression", "command", default=""),
}))
`;
  const result = spawnSync("python3", ["-c", query, REPOSITORY_ROOT], {
    cwd: REPOSITORY_ROOT,
    encoding: "utf8",
    maxBuffer: 64 * 1024,
  });
  if (result.status !== 0) {
    fail(`could not read UI quality configuration: ${result.stderr.trim()}`);
  }
  const parsed = JSON.parse(result.stdout);
  if (
    typeof parsed.browserCommand !== "string" ||
    typeof parsed.accessibilityCommand !== "string" ||
    typeof parsed.visualRegressionCommand !== "string"
  ) {
    fail("UI quality commands must be strings");
  }
  const baseUrlValue = parsed.baseUrl;
  const baseUrl = validateBaseUrl(baseUrlValue);
  const viewports = [];
  for (const name of ["desktop", "mobile"]) {
    const viewport = parsed.viewports?.[name];
    if (
      typeof viewport?.width !== "number" ||
      !Number.isInteger(viewport.width) ||
      viewport.width <= 0 ||
      typeof viewport?.height !== "number" ||
      !Number.isInteger(viewport.height) ||
      viewport.height <= 0
    ) {
      fail(`browser review viewport ${name} is missing or invalid`);
    }
    viewports.push({ name, width: viewport.width, height: viewport.height });
  }
  return { ...parsed, baseUrl, baseUrlValue, viewports };
}

function loadBrowserDependencies() {
  const requireFromFrontend = createRequire(
    pathToFileURL(path.join(FRONTEND_ROOT, "package.json")),
  );
  let browserPackage;
  let axePackage;
  try {
    browserPackage = requireFromFrontend("playwright-core");
    axePackage = requireFromFrontend("@axe-core/playwright");
  } catch (error) {
    fail(`UI browser dependencies are not installed: ${error.message}`);
  }
  const AxeBuilder = axePackage.default ?? axePackage;
  if (
    typeof browserPackage.chromium?.launch !== "function" ||
    typeof AxeBuilder !== "function"
  ) {
    fail("installed UI browser dependencies expose an unexpected API");
  }
  return { chromium: browserPackage.chromium, AxeBuilder };
}

async function atomicWrite(target, content, mode = 0o600) {
  const parent = path.dirname(target);
  const metadata = await lstat(parent);
  if (metadata.isSymbolicLink() || !metadata.isDirectory()) {
    fail(`output parent is not a real directory: ${parent}`);
  }
  const temporary = path.join(
    parent,
    `.${path.basename(target)}.${process.pid}.${randomUUID()}.tmp`,
  );
  await writeFile(temporary, content, { flag: "wx", mode });
  await rename(temporary, target);
}

async function writeJson(target, value) {
  const encoded = `${JSON.stringify(value, null, 2)}\n`;
  if (Buffer.byteLength(encoded) > MAX_JSON_BYTES) {
    fail(`JSON evidence exceeds ${MAX_JSON_BYTES} bytes`);
  }
  await atomicWrite(target, encoded);
}

function appendBoundedLog(current, chunk) {
  const combined = `${current}${chunk.toString("utf8")}`;
  return combined.slice(-MAX_SERVER_LOG_BYTES);
}

async function waitForServer(child, baseUrl, getLog, getSpawnError) {
  const deadline = Date.now() + SERVER_START_TIMEOUT_MS;
  while (Date.now() < deadline) {
    if (getSpawnError() !== undefined) {
      fail(`could not start Vite server: ${getSpawnError().message}`);
    }
    if (child.exitCode !== null) {
      fail(`Vite server exited before readiness: ${getLog().trim()}`);
    }
    const serverLog = getLog();
    if (/Port \d+ is already in use/i.test(serverLog)) {
      fail(`configured Vite port is already in use: ${serverLog.trim()}`);
    }
    try {
      const response = await fetch(baseUrl, {
        signal: AbortSignal.timeout(1_000),
        redirect: "error",
      });
      const content = await response.text();
      if (
        response.ok &&
        serverLog.includes("Local:") &&
        content.includes('src="/src/main.tsx"')
      ) {
        await new Promise((resolve) => setTimeout(resolve, 100));
        if (child.exitCode !== null) {
          fail(
            `Vite server could not bind the configured port: ${getLog().trim()}`,
          );
        }
        return;
      }
    } catch {
      // The fixed local port is not ready yet.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  fail(`Vite server did not become ready within ${SERVER_START_TIMEOUT_MS} ms`);
}

async function waitForExit(child, timeoutMs) {
  if (child.exitCode !== null) {
    return true;
  }
  return await new Promise((resolve) => {
    const timeout = setTimeout(() => {
      child.off("exit", onExit);
      resolve(false);
    }, timeoutMs);
    const onExit = () => {
      clearTimeout(timeout);
      resolve(true);
    };
    child.once("exit", onExit);
  });
}

async function stopServer(child) {
  if (child.exitCode !== null || child.pid === undefined) {
    return;
  }
  try {
    if (process.platform === "win32") {
      child.kill("SIGTERM");
    } else {
      process.kill(-child.pid, "SIGTERM");
    }
  } catch (error) {
    if (error?.code === "ESRCH") {
      return;
    }
    throw error;
  }
  if (await waitForExit(child, SERVER_STOP_TIMEOUT_MS)) {
    return;
  }
  try {
    if (process.platform === "win32") {
      child.kill("SIGKILL");
    } else {
      process.kill(-child.pid, "SIGKILL");
    }
  } catch (error) {
    if (error?.code === "ESRCH") {
      return;
    }
    throw error;
  }
  await waitForExit(child, SERVER_STOP_TIMEOUT_MS);
}

async function startServer(baseUrl) {
  let spawnError;
  const child = spawn(
    process.execPath,
    [
      VITE_EXECUTABLE,
      "--config",
      VITE_CONFIG,
      "--host",
      "127.0.0.1",
      "--port",
      baseUrl.port,
      "--strictPort",
    ],
    {
      cwd: FRONTEND_ROOT,
      detached: process.platform !== "win32",
      env: {
        ...process.env,
        BROWSER: "none",
        NO_UPDATE_NOTIFIER: "1",
      },
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  child.once("error", (error) => {
    spawnError = error;
  });
  let serverLog = "";
  child.stdout.on("data", (chunk) => {
    serverLog = appendBoundedLog(serverLog, chunk);
  });
  child.stderr.on("data", (chunk) => {
    serverLog = appendBoundedLog(serverLog, chunk);
  });
  try {
    await waitForServer(
      child,
      baseUrl.href,
      () => serverLog,
      () => spawnError,
    );
  } catch (error) {
    await stopServer(child);
    throw error;
  }
  return child;
}

async function withBrowser(configuration, callback) {
  const dependencies = loadBrowserDependencies();
  const server = await startServer(configuration.baseUrl);
  let browser;
  try {
    browser = await dependencies.chromium.launch({ headless: true });
    return await callback({ browser, AxeBuilder: dependencies.AxeBuilder });
  } finally {
    if (browser !== undefined) {
      await browser.close();
    }
    await stopServer(server);
  }
}

function apiJson(route, body, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

function requestJson(route) {
  try {
    return JSON.parse(route.request().postData() ?? "{}");
  } catch {
    return {};
  }
}

async function fulfillSyntheticApi(route, requestUrl, method, apiMode) {
  const path = requestUrl.pathname;
  const pathWithQuery = `${requestUrl.pathname}${requestUrl.search}`;
  if (path === "/api/auth/sign-in" && method === "POST") {
    if (apiMode === "signed-in") {
      await apiJson(route, {
        access_token: "synthetic-local-token",
        user: SYNTHETIC_USER,
      });
      return true;
    }
    await apiJson(route, { detail: "Anmeldung fehlgeschlagen." }, 401);
    return true;
  }
  if (apiMode !== "signed-in") {
    await apiJson(route, {
      detail: "Nicht in diesem UI-Testzustand verfügbar.",
    }, 404);
    return true;
  }
  if (path === "/api/auth/sign-out" && method === "POST") {
    await route.fulfill({ status: 204, body: "" });
    return true;
  }
  if (path === "/api/users" && method === "GET") {
    await apiJson(route, [SYNTHETIC_USER]);
    return true;
  }
  if (path === "/api/projects" && method === "GET") {
    await apiJson(route, [SYNTHETIC_PROJECT, SYNTHETIC_EMPTY_PROJECT]);
    return true;
  }
  if (path === "/api/providers" && method === "GET") {
    await apiJson(route, [SYNTHETIC_PROVIDER]);
    return true;
  }
  if (path === "/api/projects/project-alpha" && method === "GET") {
    await apiJson(route, SYNTHETIC_PROJECT);
    return true;
  }
  if (path === "/api/projects/project-alpha" && method === "PATCH") {
    const payload = requestJson(route);
    if (
      typeof payload.ticket_url_template === "string" &&
      payload.ticket_url_template.startsWith("ftp:")
    ) {
      await apiJson(
        route,
        {
          type: "urn:skm:error:VALIDATION_FAILED",
          title: "Projekteinstellungen sind ungültig.",
          status: 422,
          detail:
            "Die Projekteinstellungen konnten mit diesen Eingaben nicht gespeichert werden.",
          code: "VALIDATION_FAILED",
          correlationId: null,
          retryable: true,
          suggestedAction: "correct-input",
          fieldErrors: [
            {
              field: "ticket_url_template",
              message:
                "Die Ticket-Link-Vorlage muss eine http(s)-URL mit <ticket_id> sein.",
            },
          ],
        },
        422,
      );
      return true;
    }
    await apiJson(route, {
      ...SYNTHETIC_PROJECT_WITH_TICKET_TEMPLATE,
      name:
        typeof payload.name === "string" && payload.name.trim()
          ? payload.name
          : SYNTHETIC_PROJECT_WITH_TICKET_TEMPLATE.name,
      ticket_url_template:
        payload.ticket_url_template === undefined
          ? SYNTHETIC_PROJECT_WITH_TICKET_TEMPLATE.ticket_url_template
          : payload.ticket_url_template,
    });
    return true;
  }
  if (path === "/api/projects/project-empty" && method === "GET") {
    await apiJson(route, SYNTHETIC_EMPTY_PROJECT);
    return true;
  }
  if (path === "/api/projects/project-alpha/imports" && method === "GET") {
    await apiJson(route, [SYNTHETIC_IMPORT_LOG]);
    return true;
  }
  if (path === "/api/projects/project-empty/imports" && method === "GET") {
    await apiJson(route, []);
    return true;
  }
  if (path === "/api/projects/project-alpha/indexing-runs" && method === "GET") {
    await apiJson(route, [SYNTHETIC_INDEXING_RUN]);
    return true;
  }
  if (
    path === "/api/projects/project-empty/indexing-runs" &&
    method === "GET"
  ) {
    await apiJson(route, []);
    return true;
  }
  if (path === "/api/projects/project-alpha/cluster-sets" && method === "GET") {
    await apiJson(route, [SYNTHETIC_CLUSTER_SET, SYNTHETIC_CHILD_CLUSTER_SET]);
    return true;
  }
  if (path === "/api/projects/project-empty/cluster-sets" && method === "GET") {
    await apiJson(route, []);
    return true;
  }
  if (
    path === "/api/projects/project-alpha/cluster-sets/cluster-set-1/clusters" &&
    method === "GET"
  ) {
    await apiJson(route, SYNTHETIC_CLUSTERS);
    return true;
  }
  if (
    pathWithQuery ===
      "/api/projects/project-alpha/clusters/cluster-1/sources?limit=50&offset=0" &&
    method === "GET"
  ) {
    await apiJson(route, {
      sources: SYNTHETIC_CLUSTER_SOURCES,
      limit: 50,
      offset: 0,
      next_offset: null,
      has_more: false,
    });
    return true;
  }
  if (path === "/api/projects/project-alpha/exports" && method === "GET") {
    await apiJson(route, []);
    return true;
  }
  if (path === "/api/projects/project-empty/exports" && method === "GET") {
    await apiJson(route, []);
    return true;
  }
  if (
    path === "/api/projects/project-alpha/exports/explorer" &&
    method === "POST"
  ) {
    await apiJson(
      route,
      {
        export: SYNTHETIC_EXPORT_LOG,
        content:
          "cluster_id,status,title,category,summary_question,summary_answer\ncluster-1,unreviewed,Passwort zurücksetzen,Konto,Wie können Kunden ihr Passwort zurücksetzen?,Sende den Link zum Zurücksetzen.\n",
        content_type: "text/csv",
        warning: null,
      },
      201,
    );
    return true;
  }
  return false;
}

async function configureScenarioPage(
  browser,
  configuration,
  viewport,
  apiMode = "signed-out",
) {
  const context = await browser.newContext({
    viewport: { width: viewport.width, height: viewport.height },
    locale: "de-DE",
    timezoneId: "Europe/Berlin",
    colorScheme: "light",
    reducedMotion: "reduce",
    serviceWorkers: "block",
  });
  const blockedRequests = [];
  await context.addInitScript(() => {
    window.sessionStorage.clear();
    window.localStorage.clear();
  });
  await context.route("**/*", async (route) => {
    const request = route.request();
    if (!isAllowedBrowserRequest(request.url(), configuration.baseUrl)) {
      blockedRequests.push(safeBrowserRequestLabel(request.url()));
      await route.abort("blockedbyclient");
      return;
    }
    const requestUrl = new URL(request.url());
    if (requestUrl.pathname.startsWith("/api/")) {
      if (
        await fulfillSyntheticApi(route, requestUrl, request.method(), apiMode)
      ) {
        return;
      }
      await apiJson(
        route,
        {
          detail: "Nicht in diesem UI-Testzustand verfügbar.",
        },
        404,
      );
      return;
    }
    await route.continue();
  });
  await context.routeWebSocket(/.*/, async (socket) => {
    if (!isAllowedBrowserSocket(socket.url(), configuration.baseUrl)) {
      blockedRequests.push(safeBrowserRequestLabel(socket.url()));
      await socket.close({
        code: 1008,
        reason: "External sockets are blocked",
      });
      return;
    }
    socket.connectToServer();
  });
  const page = await context.newPage();
  await page.goto(configuration.baseUrl.href, {
    waitUntil: "domcontentloaded",
    timeout: 15_000,
  });
  await page.getByRole("heading", { name: "Lokaler Zugriff" }).waitFor({
    state: "visible",
    timeout: 10_000,
  });
  await page.addStyleTag({
    content:
      "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}",
  });
  await page.evaluate(async () => {
    await document.fonts.ready;
  });
  return { context, page, blockedRequests };
}

async function enterInvalidCredentials(page) {
  await page.getByLabel("E-Mail").fill("browser-review@example.test");
  await page.getByLabel("Passwort").fill("synthetic-test-password");
  await page.getByRole("button", { name: "Anmelden" }).click();
  await page.getByRole("alert").waitFor({ state: "visible", timeout: 10_000 });
}

async function signInToSyntheticApp(page) {
  await page.getByLabel("E-Mail").fill("owner@example.test");
  await page.getByLabel("Passwort").fill("synthetic-test-password");
  await page.getByRole("button", { name: "Anmelden" }).click();
  await page
    .getByRole("heading", { name: "Projekte & Analysen" })
    .waitFor({ state: "visible", timeout: 10_000 });
}

async function openProjectList(page) {
  await page.getByRole("button", { name: "Hauptmenü öffnen" }).click();
  await page.getByRole("menuitem", { name: "Projekte" }).click();
  await page
    .getByRole("region", { name: "Bestehende Projekte" })
    .waitFor({ state: "visible", timeout: 10_000 });
}

async function openSyntheticProject(page, projectName = "Alpha") {
  await page
    .getByRole("region", { name: "Bestehende Projekte" })
    .waitFor({ state: "visible", timeout: 10_000 });
  const escaped = projectName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  await page
    .getByRole("region", { name: "Bestehende Projekte" })
    .getByRole("button", {
      name: new RegExp(`${escaped}, zuletzt aktualisiert`),
    })
    .click();
  await page
    .getByRole("tab", { name: "Cluster-Sets", exact: true })
    .waitFor({ state: "visible", timeout: 10_000 });
}

async function captureState(
  captures,
  page,
  viewport,
  outputRoot,
  state,
  id,
  onState = null,
) {
  const image = await captureScreenshot(page);
  const relative = screenshotRelativePath(viewport, state, id);
  if (outputRoot !== null) {
    await atomicWrite(path.join(outputRoot, relative), image);
  }
  const capture = {
    id,
    state,
    viewport: {
      width: viewport.width,
      height: viewport.height,
    },
    viewportName: viewport.name,
    file: relative,
    image,
  };
  captures.push(capture);
  if (onState !== null) {
    await onState({ ...capture, page });
  }
}

async function assertSourceDialogKeyboardBehavior(page) {
  await page
    .getByText("Angezeigt: 2 Quellen.")
    .waitFor({ state: "visible", timeout: 10_000 });
  const closeButton = page.getByRole("button", {
    name: "Schließen",
    exact: true,
  });
  await closeButton.waitFor({ state: "visible", timeout: 10_000 });
  const focusedBeforeTab = await page.evaluate(
    () => document.activeElement?.textContent?.trim() ?? "",
  );
  if (focusedBeforeTab !== "Schließen") {
    fail("source dialog did not move focus to the close button");
  }
  await page.keyboard.press("Tab");
  const focusedAfterTab = await page.evaluate(
    () => document.activeElement?.textContent?.trim() ?? "",
  );
  if (focusedAfterTab !== "Schließen") {
    fail("source dialog did not trap focus on Tab");
  }
}

async function assertClusterSetTreeDisclosure(page) {
  const collapseButton = page.getByRole("button", {
    name: "Ast einklappen",
    exact: true,
  });
  await collapseButton.waitFor({ state: "visible", timeout: 10_000 });
  const expandedBefore = await collapseButton.getAttribute("aria-expanded");
  if (expandedBefore !== "true") {
    fail("cluster-set tree branch did not expose expanded state");
  }
  await page.getByText("Antworten fein — Retouren").waitFor({
    state: "visible",
    timeout: 10_000,
  });
  await collapseButton.click();
  await page.getByText("Antworten fein — Retouren").waitFor({
    state: "hidden",
    timeout: 10_000,
  });
  const expandButton = page.getByRole("button", {
    name: "Ast ausklappen",
    exact: true,
  });
  const expandedAfterCollapse = await expandButton.getAttribute("aria-expanded");
  if (expandedAfterCollapse !== "false") {
    fail("cluster-set tree branch did not expose collapsed state");
  }
  await expandButton.click();
  await page.getByText("Antworten fein — Retouren").waitFor({
    state: "visible",
    timeout: 10_000,
  });
}

async function closeSourceDialogAndVerifyFocusReturn(page) {
  await page.keyboard.press("Escape");
  await page
    .getByRole("dialog", { name: "Passwort zurücksetzen" })
    .waitFor({ state: "hidden", timeout: 10_000 });
  const focusedAfterEscape = await page.evaluate(
    () => document.activeElement?.textContent?.trim() ?? "",
  );
  if (focusedAfterEscape !== "Quellen anzeigen") {
    fail("source dialog did not return focus to its opener");
  }
}

async function assertTicketLinkVisible(page) {
  const ticketLink = page.getByRole("link", { name: "Ticket T-1" });
  await ticketLink.waitFor({ state: "visible", timeout: 10_000 });
  const href = await ticketLink.getAttribute("href");
  if (href !== "https://tickets.example.test/T-T-1") {
    fail("source dialog ticket link did not use the configured template");
  }
  const target = await ticketLink.getAttribute("target");
  const rel = await ticketLink.getAttribute("rel");
  if (target !== "_blank" || rel !== "noopener noreferrer") {
    fail("source dialog ticket link is missing safe external-link attributes");
  }
}

async function captureProjectSettingsStates(
  captures,
  page,
  viewport,
  outputRoot,
  onState,
) {
  await page.getByRole("tab", { name: "Einstellungen", exact: true }).click();
  await page
    .getByRole("heading", { name: "Projekt bearbeiten" })
    .waitFor({ state: "visible", timeout: 10_000 });
  await page
    .getByRole("form", { name: "Projekt löschen" })
    .waitFor({ state: "visible", timeout: 10_000 });
  await captureState(
    captures,
    page,
    viewport,
    outputRoot,
    "project-settings-default",
    "project",
    onState,
  );

  const settingsForm = page.getByRole("form", {
    name: "Projekteinstellungen speichern",
  });
  await settingsForm.getByLabel("Ticket-Link-Vorlage").fill(
    "ftp://tickets.example.test/<ticket_id>",
  );
  await settingsForm
    .getByRole("button", { name: "Einstellungen speichern" })
    .click();
  await settingsForm
    .getByText(
      "Die Ticket-Link-Vorlage muss eine http(s)-URL mit <ticket_id> sein.",
    )
    .waitFor({ state: "visible", timeout: 10_000 });
  await captureState(
    captures,
    page,
    viewport,
    outputRoot,
    "project-settings-validation-error",
    "project",
    onState,
  );

  const deleteForm = page.getByRole("form", { name: "Projekt löschen" });
  await deleteForm.getByLabel("Projektname bestätigen").fill("Alpha");
  await captureState(
    captures,
    page,
    viewport,
    outputRoot,
    "project-settings-delete-confirmation",
    "project",
    onState,
  );

  await settingsForm
    .getByLabel("Ticket-Link-Vorlage")
    .fill("https://tickets.example.test/T-<ticket_id>");
  await settingsForm
    .getByRole("button", { name: "Einstellungen speichern" })
    .click();
  await page
    .getByText("Projekteinstellungen gespeichert.")
    .waitFor({ state: "visible", timeout: 10_000 });
}

async function captureExplorerInteractionStates(
  captures,
  page,
  viewport,
  outputRoot,
  onState,
) {
  const sortButton = page.getByRole("button", {
    name: /Hinweise \/ Score sortieren/,
  });
  await sortButton.click();
  await page
    .locator("th", { has: sortButton })
    .evaluate((cell) => {
      if (cell.getAttribute("aria-sort") !== "ascending") {
        throw new Error("score sort did not expose ascending state");
      }
    });
  await captureState(
    captures,
    page,
    viewport,
    outputRoot,
    "explorer-sort-score-ascending",
    "project",
    onState,
  );

  await sortButton.click();
  await page
    .locator("th", { has: sortButton })
    .evaluate((cell) => {
      if (cell.getAttribute("aria-sort") !== "descending") {
        throw new Error("score sort did not expose descending state");
      }
    });
  await captureState(
    captures,
    page,
    viewport,
    outputRoot,
    "explorer-sort-score-descending",
    "project",
    onState,
  );

  await sortButton.click();
  await page
    .locator("th", { has: sortButton })
    .evaluate((cell) => {
      if (cell.getAttribute("aria-sort") !== "none") {
        throw new Error("score sort did not return to unsorted state");
      }
    });
  await captureState(
    captures,
    page,
    viewport,
    outputRoot,
    "explorer-sort-score-unsorted",
    "project",
    onState,
  );

  await page
    .getByRole("button", { name: "Kontrollleiste einklappen" })
    .click();
  await page
    .getByRole("button", { name: "Kontrollleiste ausklappen" })
    .waitFor({ state: "visible", timeout: 10_000 });
  await captureState(
    captures,
    page,
    viewport,
    outputRoot,
    "explorer-collapsed-rail",
    "project",
    onState,
  );
  await page
    .getByRole("button", { name: "Kontrollleiste ausklappen" })
    .click();
  await page
    .getByRole("button", { name: "Kontrollleiste einklappen" })
    .waitFor({ state: "visible", timeout: 10_000 });

  const workspace = page.locator(".explorer-table-workspace").first();
  await workspace.evaluate((element) => {
    element.scrollTop = element.scrollHeight;
  });
  await page.getByRole("button", { name: "Nach oben scrollen" }).click();
  await page.waitForFunction(
    () =>
      (document.querySelector(".explorer-table-workspace")?.scrollTop ?? 0) ===
      0,
  );
  await captureState(
    captures,
    page,
    viewport,
    outputRoot,
    "explorer-after-scroll-to-top",
    "project",
    onState,
  );
}

async function captureScreenshot(page) {
  const image = await page.screenshot({
    type: "png",
    fullPage: true,
    animations: "disabled",
    caret: "hide",
    timeout: 10_000,
  });
  if (image.length === 0 || image.length > MAX_IMAGE_BYTES) {
    fail("captured screenshot is empty or exceeds the evidence size limit");
  }
  return image;
}

function screenshotRelativePath(viewport, state, prefix = "signed-out") {
  const safeState = state.replaceAll("/", "-");
  return `${viewport.name}/${prefix}-${safeState}.png`;
}

async function captureScenarios(
  browser,
  configuration,
  outputRoot,
  prefix,
  onState = null,
) {
  const captures = [];
  for (const viewport of configuration.viewports) {
    const configured = await configureScenarioPage(
      browser,
      configuration,
      viewport,
    );
    try {
      for (const state of ["default", "invalid-credentials", "error/failure"]) {
        if (state === "invalid-credentials") {
          await enterInvalidCredentials(configured.page);
        }
        const image = await captureScreenshot(configured.page);
        const relative = screenshotRelativePath(viewport, state, prefix);
        if (outputRoot !== null) {
          await atomicWrite(path.join(outputRoot, relative), image);
        }
        const capture = {
          id: "signed-out",
          state,
          viewport: {
            width: viewport.width,
            height: viewport.height,
          },
          viewportName: viewport.name,
          file: relative,
          image,
        };
        captures.push(capture);
        if (onState !== null) {
          await onState({ ...capture, page: configured.page });
        }
      }
      if (configured.blockedRequests.length > 0) {
        fail(
          `browser attempted external request(s): ${configured.blockedRequests.join(", ")}`,
        );
      }
    } finally {
      await configured.context.close();
    }
  }
  return captures;
}

async function captureProjectScenarios(
  browser,
  configuration,
  outputRoot,
  onState = null,
) {
  const captures = [];
  for (const viewport of configuration.viewports) {
    const configured = await configureScenarioPage(
      browser,
      configuration,
      viewport,
      "signed-in",
    );
    try {
      const { page } = configured;
      await signInToSyntheticApp(page);
      await openSyntheticProject(page, "Leeres Projekt");
      await page
        .getByRole("tab", { name: "Explorer", exact: true })
        .click();
      await page
        .getByText(/Noch kein abgeschlossenes Cluster-Set geladen/)
        .waitFor({ state: "visible", timeout: 10_000 });
      await captureState(
        captures,
        page,
        viewport,
        outputRoot,
        "explorer-empty",
        "project",
        onState,
      );

      await openProjectList(page);
      await openSyntheticProject(page);

      await page
        .getByRole("tab", { name: "Cluster-Sets", exact: true })
        .click();
      await page
        .getByRole("button", { name: "Im Explorer laden" })
        .first()
        .waitFor({ state: "visible", timeout: 10_000 });
      await captureState(
        captures,
        page,
        viewport,
        outputRoot,
        "cluster-sets-tree",
        "project",
        onState,
      );
      await assertClusterSetTreeDisclosure(page);

      await page
        .getByRole("button", { name: "Cluster verfeinern" })
        .first()
        .click();
      await page
        .getByText("Verfeinerung vorausgefüllt")
        .waitFor({ state: "visible", timeout: 10_000 });
      await captureState(
        captures,
        page,
        viewport,
        outputRoot,
        "cluster-set-refinement-draft",
        "project",
        onState,
      );
      await page
        .getByRole("button", { name: "Verfeinerung zurücksetzen" })
        .click();

      await page
        .getByRole("tab", { name: "Explorer", exact: true })
        .click();
      await page.getByRole("button", { name: "Cluster-Set auswählen" }).click();
      await page
        .getByRole("button", { name: "Im Explorer laden" })
        .first()
        .click();
      await page
        .getByRole("heading", { name: "Cluster Explorer" })
        .waitFor({ state: "visible", timeout: 10_000 });
      await page
        .getByRole("row", { name: /Passwort zurücksetzen/ })
        .first()
        .waitFor({ state: "visible", timeout: 10_000 });
      await captureState(
        captures,
        page,
        viewport,
        outputRoot,
        "explorer-loaded-table",
        "project",
        onState,
      );
      await captureExplorerInteractionStates(
        captures,
        page,
        viewport,
        outputRoot,
        onState,
      );

      await page
        .getByPlaceholder("Titel, Kategorie, Summary oder Status")
        .fill("keine Treffer");
      await page
        .getByText("Keine Cluster entsprechen der aktuellen Textsuche oder dem Filter.")
        .waitFor({ state: "visible", timeout: 10_000 });
      await captureState(
        captures,
        page,
        viewport,
        outputRoot,
        "explorer-no-results",
        "project",
        onState,
      );
      await page
        .getByPlaceholder("Titel, Kategorie, Summary oder Status")
        .fill("");

      await page.getByLabel("Ausgeschlossene anzeigen").check();
      await page
        .getByRole("region", { name: "Ausgeschlossene Cluster" })
        .waitFor({ state: "visible", timeout: 10_000 });
      await captureState(
        captures,
        page,
        viewport,
        outputRoot,
        "explorer-excluded-rows",
        "project",
        onState,
      );

      const sourceOpener = page
        .getByRole("row", { name: /Passwort zurücksetzen/ })
        .getByRole("button", { name: "Quellen anzeigen" });
      await sourceOpener.click();
      await page
        .getByRole("dialog", { name: "Passwort zurücksetzen" })
        .waitFor({ state: "visible", timeout: 10_000 });
      await assertSourceDialogKeyboardBehavior(page);
      await captureState(
        captures,
        page,
        viewport,
        outputRoot,
        "explorer-source-dialog",
        "project",
        onState,
      );
      await closeSourceDialogAndVerifyFocusReturn(page);

      await captureProjectSettingsStates(
        captures,
        page,
        viewport,
        outputRoot,
        onState,
      );
      await page
        .getByRole("tab", { name: "Explorer", exact: true })
        .click();
      await page
        .getByRole("row", { name: /Passwort zurücksetzen/ })
        .first()
        .waitFor({ state: "visible", timeout: 10_000 });
      await page
        .getByRole("row", { name: /Passwort zurücksetzen/ })
        .getByRole("button", { name: "Quellen anzeigen" })
        .click();
      await page
        .getByRole("dialog", { name: "Passwort zurücksetzen" })
        .waitFor({ state: "visible", timeout: 10_000 });
      await assertTicketLinkVisible(page);
      await captureState(
        captures,
        page,
        viewport,
        outputRoot,
        "explorer-source-dialog-ticket-link",
        "project",
        onState,
      );
      await closeSourceDialogAndVerifyFocusReturn(page);

      await page
        .getByRole("button", { name: "Aktuelle Tabelle exportieren" })
        .click();
      await page
        .getByText(/Explorer-Export erstellt/)
        .waitFor({ state: "visible", timeout: 10_000 });
      await captureState(
        captures,
        page,
        viewport,
        outputRoot,
        "explorer-export-output",
        "project",
        onState,
      );

      await page
        .getByRole("button", { name: "Eingeschlossene Cluster verfeinern" })
        .click();
      await page
        .getByText("Verfeinerung vorausgefüllt")
        .waitFor({ state: "visible", timeout: 10_000 });
      await captureState(
        captures,
        page,
        viewport,
        outputRoot,
        "explorer-refinement-draft",
        "project",
        onState,
      );

      if (configured.blockedRequests.length > 0) {
        fail(
          `browser attempted external request(s): ${configured.blockedRequests.join(", ")}`,
        );
      }
    } finally {
      await configured.context.close();
    }
  }
  return captures;
}

async function captureAllScenarios(browser, configuration, outputRoot) {
  return [
    ...(await captureScenarios(
      browser,
      configuration,
      outputRoot,
      "signed-out",
    )),
    ...(await captureProjectScenarios(browser, configuration, outputRoot)),
  ];
}

function gitOutput(...arguments_) {
  const result = spawnSync("git", arguments_, {
    cwd: REPOSITORY_ROOT,
    encoding: "utf8",
    maxBuffer: 1024 * 1024,
  });
  if (result.status !== 0) {
    fail(`git ${arguments_.join(" ")} failed: ${result.stderr.trim()}`);
  }
  return result.stdout.trim();
}

function workingTreeFingerprint() {
  const result = spawnSync(
    path.join(REPOSITORY_ROOT, ".ai", "tools", "check-ui-quality.py"),
    ["--fingerprint"],
    {
      cwd: REPOSITORY_ROOT,
      encoding: "utf8",
      maxBuffer: 1024 * 1024,
    },
  );
  if (result.status !== 0 || !/^[a-f0-9]{64}$/.test(result.stdout.trim())) {
    fail(`could not compute UI evidence fingerprint: ${result.stderr.trim()}`);
  }
  return result.stdout.trim();
}

async function runBrowserReview(configuration, activeWork) {
  if (!configuration.browserCommand.trim()) {
    fail("browser review command is not configured");
  }
  await withBrowser(configuration, async ({ browser }) => {
    const captures = await captureAllScenarios(
      browser,
      configuration,
      activeWork.evidenceDirectory,
    );
    const manifest = {
      change_id: activeWork.changeId,
      generated_at: new Date().toISOString(),
      application_revision: gitOutput("rev-parse", "HEAD"),
      working_tree_fingerprint: workingTreeFingerprint(),
      browser: `Chromium ${browser.version()}`,
      base_url: configuration.baseUrlValue,
      execution_mode: "automated",
      performed_by: "trusted-host-automation",
      browser_command: configuration.browserCommand,
      command_result: "pass",
      interaction_check: "passed",
      screens: captures.map(
        ({ image: _image, viewportName: _name, ...capture }) => capture,
      ),
    };
    await writeJson(
      path.join(activeWork.evidenceDirectory, "manifest.json"),
      manifest,
    );
  });
}

function minimizedViolation(violation) {
  return {
    id: violation.id,
    impact: violation.impact,
    help: violation.help,
    helpUrl: violation.helpUrl,
    tags: violation.tags,
    nodes: violation.nodes.slice(0, 20).map((node) => ({
      target: node.target,
      html: node.html.slice(0, 1_000),
      failureSummary: node.failureSummary?.slice(0, 2_000) ?? "",
    })),
  };
}

async function analyzeAccessibilityState(
  AxeBuilder,
  audits,
  { id, state, viewportName, page },
) {
  const result = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  audits.push({
    screen: id,
    state,
    viewport: viewportName,
    violations: result.violations.map(minimizedViolation),
  });
}

async function runAccessibility(configuration, activeWork) {
  if (!configuration.accessibilityCommand.trim()) {
    fail("accessibility command is not configured");
  }
  await withBrowser(configuration, async ({ browser, AxeBuilder }) => {
    const audits = [];
    const onState = async (capture) =>
      analyzeAccessibilityState(AxeBuilder, audits, capture);
    await captureScenarios(
      browser,
      configuration,
      null,
      "signed-out",
      onState,
    );
    await captureProjectScenarios(browser, configuration, null, onState);
    const violations = audits.flatMap((audit) =>
      audit.violations.map((violation) => ({
        ...violation,
        audit: {
          screen: audit.screen,
          state: audit.state,
          viewport: audit.viewport,
        },
      })),
    );
    const report = {
      generated_at: new Date().toISOString(),
      command: configuration.accessibilityCommand,
      wcag_tags: WCAG_TAGS,
      result: violations.length === 0 ? "pass" : "fail",
      audits,
    };
    await writeJson(
      path.join(
        activeWork.evidenceDirectory,
        "accessibility",
        "axe-report.json",
      ),
      report,
    );
    if (violations.length > 0) {
      const identifiers = [...new Set(violations.map((item) => item.id))].join(
        ", ",
      );
      fail(`accessibility violations detected: ${identifiers}`);
    }
  });
}

async function comparePngBuffers(page, expected, actual) {
  if (
    expected.length === 0 ||
    actual.length === 0 ||
    expected.length > MAX_IMAGE_BYTES ||
    actual.length > MAX_IMAGE_BYTES
  ) {
    fail("visual comparison image is empty or exceeds the size limit");
  }
  return await page.evaluate(
    async ({ expectedBase64, actualBase64, channelThreshold }) => {
      const decode = async (base64) => {
        const response = await fetch(`data:image/png;base64,${base64}`);
        return await createImageBitmap(await response.blob());
      };
      const [expectedImage, actualImage] = await Promise.all([
        decode(expectedBase64),
        decode(actualBase64),
      ]);
      if (
        expectedImage.width !== actualImage.width ||
        expectedImage.height !== actualImage.height
      ) {
        return {
          differentPixels: actualImage.width * actualImage.height,
          totalPixels: actualImage.width * actualImage.height,
          ratio: 1,
          dimensionMismatch: true,
          diffPngBase64: null,
        };
      }
      const width = actualImage.width;
      const height = actualImage.height;
      const expectedCanvas = document.createElement("canvas");
      const actualCanvas = document.createElement("canvas");
      const diffCanvas = document.createElement("canvas");
      for (const canvas of [expectedCanvas, actualCanvas, diffCanvas]) {
        canvas.width = width;
        canvas.height = height;
      }
      const expectedContext = expectedCanvas.getContext("2d");
      const actualContext = actualCanvas.getContext("2d");
      const diffContext = diffCanvas.getContext("2d");
      expectedContext.drawImage(expectedImage, 0, 0);
      actualContext.drawImage(actualImage, 0, 0);
      const expectedPixels = expectedContext.getImageData(0, 0, width, height);
      const actualPixels = actualContext.getImageData(0, 0, width, height);
      const diffPixels = diffContext.createImageData(width, height);
      let differentPixels = 0;
      for (let offset = 0; offset < expectedPixels.data.length; offset += 4) {
        let different = false;
        for (let channel = 0; channel < 4; channel += 1) {
          if (
            Math.abs(
              expectedPixels.data[offset + channel] -
                actualPixels.data[offset + channel],
            ) > channelThreshold
          ) {
            different = true;
            break;
          }
        }
        if (different) {
          differentPixels += 1;
          diffPixels.data[offset] = 255;
          diffPixels.data[offset + 1] = 0;
          diffPixels.data[offset + 2] = 255;
          diffPixels.data[offset + 3] = 255;
        } else {
          const shade = Math.round(
            (actualPixels.data[offset] +
              actualPixels.data[offset + 1] +
              actualPixels.data[offset + 2]) /
              6,
          );
          diffPixels.data[offset] = shade;
          diffPixels.data[offset + 1] = shade;
          diffPixels.data[offset + 2] = shade;
          diffPixels.data[offset + 3] = 96;
        }
      }
      diffContext.putImageData(diffPixels, 0, 0);
      const totalPixels = width * height;
      return {
        differentPixels,
        totalPixels,
        ratio: totalPixels === 0 ? 0 : differentPixels / totalPixels,
        dimensionMismatch: false,
        diffPngBase64:
          differentPixels === 0
            ? null
            : diffCanvas.toDataURL("image/png").split(",", 2)[1],
      };
    },
    {
      expectedBase64: expected.toString("base64"),
      actualBase64: actual.toString("base64"),
      channelThreshold: PIXEL_CHANNEL_THRESHOLD,
    },
  );
}

export async function validateBaselineFile(candidate) {
  const metadata = await lstat(candidate);
  if (
    metadata.isSymbolicLink() ||
    !metadata.isFile() ||
    metadata.size === 0 ||
    metadata.size > MAX_IMAGE_BYTES
  ) {
    fail(
      `visual baseline must be a non-empty bounded regular file: ${candidate}`,
    );
  }
  const content = await readFile(candidate);
  const pngSignature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  if (!content.subarray(0, 8).equals(pngSignature)) {
    fail(`visual baseline is not a PNG: ${candidate}`);
  }
  return content;
}

async function runVisualRegression(configuration, activeWork, updateBaselines) {
  if (!updateBaselines && !configuration.visualRegressionCommand.trim()) {
    fail("visual regression command is not configured");
  }
  await withBrowser(configuration, async ({ browser }) => {
    const captures = await captureAllScenarios(
      browser,
      configuration,
      activeWork.evidenceDirectory,
    );
    if (updateBaselines) {
      if (!(await exists(BASELINE_ROOT))) {
        await mkdir(BASELINE_ROOT, { mode: 0o755 });
      }
      const baselineMetadata = await lstat(BASELINE_ROOT);
      if (
        baselineMetadata.isSymbolicLink() ||
        !baselineMetadata.isDirectory()
      ) {
        fail("visual baseline root must be a real directory");
      }
      for (const capture of captures) {
        const baselineName = capture.file.replaceAll("/", "-");
        await atomicWrite(
          path.join(BASELINE_ROOT, baselineName),
          capture.image,
          0o644,
        );
      }
      return;
    }

    const comparisonPage = await browser.newPage();
    const comparisons = [];
    try {
      for (const capture of captures) {
        const baselineName = capture.file.replaceAll("/", "-");
        const baseline = await validateBaselineFile(
          path.join(BASELINE_ROOT, baselineName),
        );
        const comparison = await comparePngBuffers(
          comparisonPage,
          baseline,
          capture.image,
        );
        const passed =
          !comparison.dimensionMismatch &&
          comparison.ratio <= MAX_DIFFERENT_PIXEL_RATIO;
        let diffFile = null;
        if (!passed && comparison.diffPngBase64 !== null) {
          diffFile = `reports/diff-${baselineName}`;
          await atomicWrite(
            path.join(activeWork.evidenceDirectory, diffFile),
            Buffer.from(comparison.diffPngBase64, "base64"),
          );
        }
        comparisons.push({
          screen: capture.id,
          state: capture.state,
          viewport: capture.viewportName,
          baseline: `frontend/ui-baselines/${baselineName}`,
          actual: capture.file,
          diff: diffFile,
          different_pixels: comparison.differentPixels,
          total_pixels: comparison.totalPixels,
          difference_ratio: comparison.ratio,
          allowed_ratio: MAX_DIFFERENT_PIXEL_RATIO,
          result: passed ? "pass" : "fail",
        });
      }
    } finally {
      await comparisonPage.close();
    }
    const failed = comparisons.filter(
      (comparison) => comparison.result === "fail",
    );
    await writeJson(
      path.join(
        activeWork.evidenceDirectory,
        "reports",
        "visual-regression.json",
      ),
      {
        generated_at: new Date().toISOString(),
        command: configuration.visualRegressionCommand,
        result: failed.length === 0 ? "pass" : "fail",
        pixel_channel_threshold: PIXEL_CHANNEL_THRESHOLD,
        maximum_difference_ratio: MAX_DIFFERENT_PIXEL_RATIO,
        comparisons,
      },
    );
    if (failed.length > 0) {
      fail(
        `visual regression detected in ${failed
          .map((item) => `${item.viewport}/${item.state}`)
          .join(", ")}`,
      );
    }
  });
}

async function main() {
  const mode = process.argv[2];
  const modes = [
    "browser",
    "accessibility",
    "visual-regression",
    "update-baselines",
  ];
  if (!modes.includes(mode)) {
    console.error(
      "Usage: ui-browser-review.mjs browser|accessibility|visual-regression|update-baselines",
    );
    return 2;
  }
  const configuration = loadProjectConfiguration();
  const activeWork = await resolveActiveWork();
  if (mode === "browser") {
    await runBrowserReview(configuration, activeWork);
  } else if (mode === "accessibility") {
    await runAccessibility(configuration, activeWork);
  } else {
    await runVisualRegression(
      configuration,
      activeWork,
      mode === "update-baselines",
    );
  }
  console.log(`[ui-browser-review] ${mode}: PASS`);
  return 0;
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  main()
    .then((status) => {
      process.exitCode = status;
    })
    .catch((error) => {
      console.error(`[ui-browser-review] FAIL: ${error.message}`);
      process.exitCode = 1;
    });
}
