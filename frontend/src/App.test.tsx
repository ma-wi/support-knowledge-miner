import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import userEvent from "@testing-library/user-event";
import App from "./App";

const owner = {
  id: "local-owner",
  username: "owner",
  first_name: "Local",
  last_name: "Owner",
  email: "owner@example.test",
};
const curator = {
  id: "local-curator",
  username: "curator",
  first_name: "Support",
  last_name: "Curator",
  email: "curator@example.test",
};
const alphaProject = {
  id: "project-alpha",
  name: "Alpha",
  lifecycle_state: "active",
  created_at: "2026-07-22T00:00:00Z",
  updated_at: "2026-07-22T00:00:00Z",
};
const betaProject = {
  id: "project-beta",
  name: "Beta",
  lifecycle_state: "active",
  created_at: "2026-07-22T00:00:00Z",
  updated_at: "2026-07-22T00:00:00Z",
};
const importLog = {
  id: "import-log-1",
  project_id: "project-alpha",
  source_type: "csv",
  source_name: "fixture.csv",
  status: "completed",
  failure_reason: null,
  total_records: 2,
  valid_records: 1,
  skipped_records: 1,
  dataset_version_id: "dataset-1",
  started_at: "2026-07-22T00:00:00Z",
  completed_at: "2026-07-22T00:00:00Z",
};
const openAiProvider = {
  provider: "openai",
  endpoint_url: null,
  manual_models: ["gpt-4.1-mini"],
  api_key_set: true,
  updated_at: "2026-07-22T00:00:00Z",
};
const vllmProvider = {
  provider: "vllm",
  endpoint_url: "http://localhost:8000",
  manual_models: ["local-embed"],
  api_key_set: false,
  updated_at: "2026-07-22T00:00:00Z",
};
const analysisProfile = {
  id: "profile-1",
  project_id: "project-alpha",
  name: "Local profile",
  provider: "vllm",
  model: "local-embed",
  is_cloud_provider: false,
  thresholds: { similarity: 0.78 },
  algorithm_settings: { algorithm: "hdbscan" },
  prompt_identifier: "faq-v1",
  prompt_template: null,
  created_at: "2026-07-22T00:00:00Z",
  updated_at: "2026-07-22T00:00:00Z",
};
const analysisRun = {
  id: "run-1",
  project_id: "project-alpha",
  dataset_version_id: "dataset-1",
  analysis_profile_id: "profile-1",
  status: "queued",
  progress: 0,
  profile_snapshot: {
    name: "Local profile",
    provider: "vllm",
    model: "local-embed",
  },
  provider: "vllm",
  model: "local-embed",
  parameters: { mode: "fixture" },
  error_message: null,
  diagnostics: {},
  started_at: null,
  completed_at: null,
  created_at: "2026-07-22T00:00:00Z",
  updated_at: "2026-07-22T00:00:01Z",
};
const completedAnalysisRun = {
  ...analysisRun,
  id: "run-completed",
  status: "completed",
  progress: 100,
  diagnostics: { embeddings_written: 2 },
  started_at: "2026-07-22T00:00:00Z",
  completed_at: "2026-07-22T00:00:01Z",
};
const cluster = {
  id: "cluster-1",
  project_id: "project-alpha",
  analysis_run_id: "run-completed",
  dataset_version_id: "dataset-1",
  auto_title: "Cluster H",
  manual_title: null,
  effective_title: "Cluster H",
  auto_category: "deterministic-key",
  manual_category: null,
  effective_category: "deterministic-key",
  auto_status: "unreviewed",
  manual_status: null,
  effective_status: "unreviewed",
  score: 0.91,
  is_outlier: false,
  algorithm: "linear-prefix-scaffold",
  member_count: 2,
  metadata: { non_quadratic: true },
  created_at: "2026-07-22T00:00:00Z",
  updated_at: "2026-07-22T00:00:00Z",
};
const updatedCluster = {
  ...cluster,
  manual_title: "Reset workflow",
  effective_title: "Reset workflow",
  manual_category: "Account",
  effective_category: "Account",
  manual_status: "reviewed",
  effective_status: "reviewed",
};
const candidate = {
  id: "candidate-1",
  project_id: "project-alpha",
  dataset_version_id: "dataset-1",
  analysis_run_id: "run-completed",
  source_cluster_id: "cluster-1",
  candidate_type: "static_faq",
  auto_status: "unreviewed",
  manual_status: null,
  effective_status: "unreviewed",
  language: "de",
  auto_category_path: "deterministic-key",
  manual_category_path: null,
  effective_category_path: "deterministic-key",
  auto_title: "Cluster H",
  manual_title: null,
  effective_title: "Cluster H",
  auto_canonical_question: "How do I reset it?",
  manual_canonical_question: null,
  effective_canonical_question: "How do I reset it?",
  auto_canonical_answer: "Use the reset link.",
  manual_canonical_answer: null,
  effective_canonical_answer: "Use the reset link.",
  auto_alternative_questions: ["Password reset failed"],
  manual_alternative_questions: null,
  effective_alternative_questions: ["Password reset failed"],
  auto_parameters: {},
  manual_parameters: null,
  effective_parameters: {},
  auto_external_data_dependencies: [],
  manual_external_data_dependencies: null,
  effective_external_data_dependencies: [],
  quality_score: 0.91,
  faq_suitability_score: 0.91,
  dynamicity_score: 0,
  contradiction_score: 0,
  source_pair_count: 1,
  source_cluster_ids: ["cluster-1"],
  notes: null,
  metadata: { generated_from: "cluster" },
  created_at: "2026-07-22T00:00:00Z",
  updated_at: "2026-07-22T00:00:00Z",
};
const updatedCandidate = {
  ...candidate,
  candidate_type: "parameterized_faq",
  manual_status: "export_ready",
  effective_status: "export_ready",
  manual_category_path: "Account",
  effective_category_path: "Account",
  manual_title: "Reset FAQ",
  effective_title: "Reset FAQ",
  manual_canonical_question: "How can customers reset passwords?",
  effective_canonical_question: "How can customers reset passwords?",
  manual_canonical_answer: "Send a reset link.",
  effective_canonical_answer: "Send a reset link.",
  manual_alternative_questions: ["Password reset does not work"],
  effective_alternative_questions: ["Password reset does not work"],
  manual_parameters: { account_id: "required" },
  effective_parameters: { account_id: "required" },
  manual_external_data_dependencies: ["identity-service"],
  effective_external_data_dependencies: ["identity-service"],
  notes: "Reviewed candidate.",
};
const candidateExportLog = {
  id: "export-candidates-1",
  project_id: "project-alpha",
  export_type: "candidate_csv",
  include_original_text: true,
  filters: {},
  selection: {},
  dataset_version_id: "dataset-1",
  analysis_run_id: "run-completed",
  output_filename: "candidate_csv-export-candidates-1.csv",
  output_path: null,
  row_count: 1,
  created_at: "2026-07-23T00:00:00Z",
};
const sourceAssignmentExportLog = {
  id: "export-sources-1",
  project_id: "project-alpha",
  export_type: "source_assignment_csv",
  include_original_text: false,
  filters: {},
  selection: {},
  dataset_version_id: "dataset-1",
  analysis_run_id: "run-completed",
  output_filename: "source_assignment_csv-export-sources-1.csv",
  output_path: null,
  row_count: 1,
  created_at: "2026-07-23T00:00:01Z",
};
const generatedMultiValueCandidate = {
  ...candidate,
  auto_alternative_questions: ["Password reset failed", "Reset mail missing"],
  effective_alternative_questions: [
    "Password reset failed",
    "Reset mail missing",
  ],
  auto_parameters: { account_id: "optional" },
  effective_parameters: { account_id: "optional" },
  auto_external_data_dependencies: ["identity-service"],
  effective_external_data_dependencies: ["identity-service"],
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

function mockFetch(
  handler: (
    input: RequestInfo | URL,
    init?: RequestInit,
  ) => Response | Promise<Response>,
) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input, init) => handler(input, init));
}

async function signIn(user: ReturnType<typeof userEvent.setup>) {
  const signInForm = screen
    .getByRole("button", { name: "Anmelden" })
    .closest("form");
  if (signInForm === null) {
    throw new Error("sign-in form missing");
  }
  await user.type(within(signInForm).getByLabelText("Benutzername"), "owner");
  await user.type(
    within(signInForm).getByLabelText("Passwort"),
    "owner-password",
  );
  await user.click(
    within(signInForm).getByRole("button", { name: "Anmelden" }),
  );
}

test("prevents protected user management before sign-in", () => {
  render(<App />);

  expect(
    screen.getByRole("heading", { name: "Lokaler Zugriff" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("heading", { name: "Projektverwaltung" }),
  ).not.toBeInTheDocument();
});

test("keeps protected UI closed when backend rejects credentials", async () => {
  const user = userEvent.setup();
  mockFetch(() =>
    jsonResponse({ detail: "invalid credentials" }, { status: 401 }),
  );
  render(<App />);

  await signIn(user);

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Anmeldung fehlgeschlagen oder Backend nicht erreichbar.",
  );
  expect(
    screen.queryByRole("heading", { name: "Projektverwaltung" }),
  ).not.toBeInTheDocument();
});

test("keeps protected UI closed when backend is unavailable", async () => {
  const user = userEvent.setup();
  mockFetch(() => Promise.reject(new Error("backend unavailable")));
  render(<App />);

  await signIn(user);

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Backend nicht erreichbar",
  );
  expect(
    screen.queryByRole("heading", { name: "Projektverwaltung" }),
  ).not.toBeInTheDocument();
});

test("opens user management only after API sign-in and uses bearer token for user actions", async () => {
  const user = userEvent.setup();
  const fetchMock = mockFetch((input, init) => {
    const path = String(input);
    const method = init?.method ?? "GET";
    if (path === "/api/auth/sign-in" && method === "POST") {
      return jsonResponse({ access_token: "api-token", user: owner });
    }
    if (path === "/api/users" && method === "GET") {
      expect(new Headers(init?.headers).get("Authorization")).toBe(
        "Bearer api-token",
      );
      return jsonResponse([owner]);
    }
    if (path === "/api/projects" && method === "GET") {
      expect(new Headers(init?.headers).get("Authorization")).toBe(
        "Bearer api-token",
      );
      return jsonResponse([alphaProject]);
    }
    if (path === "/api/users" && method === "POST") {
      expect(new Headers(init?.headers).get("Authorization")).toBe(
        "Bearer api-token",
      );
      expect(String(init?.body)).toContain("curator-password");
      return jsonResponse(curator, { status: 201 });
    }
    if (path === "/api/users/local-curator" && method === "DELETE") {
      expect(new Headers(init?.headers).get("Authorization")).toBe(
        "Bearer api-token",
      );
      return new Response(null, { status: 204 });
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
  render(<App />);

  await signIn(user);

  expect(
    await screen.findByRole("heading", { name: "Projektverwaltung" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Self-Delete gesperrt" }),
  ).toBeDisabled();

  const createForm = screen.getByRole("form", { name: "User anlegen" });
  await user.type(within(createForm).getByLabelText("Benutzername"), "curator");
  await user.type(within(createForm).getByLabelText("Vorname"), "Support");
  await user.type(within(createForm).getByLabelText("Nachname"), "Curator");
  await user.type(
    within(createForm).getByLabelText("E-Mail"),
    "curator@example.test",
  );
  await user.type(
    within(createForm).getByLabelText("Initiales Passwort"),
    "curator-password",
  );
  await user.click(
    within(createForm).getByRole("button", { name: "User erstellen" }),
  );

  expect(await screen.findByText("curator")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "User loeschen" }));
  await waitFor(() =>
    expect(screen.queryByText("curator")).not.toBeInTheDocument(),
  );
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/auth/sign-in",
    expect.objectContaining({ method: "POST" }),
  );
});

test("shows MVP shell navigation and shared empty states after sign-in", async () => {
  const user = userEvent.setup();
  mockFetch((input, init) => {
    const path = String(input);
    const method = init?.method ?? "GET";
    if (path === "/api/auth/sign-in" && method === "POST") {
      return jsonResponse({ access_token: "api-token", user: owner });
    }
    if (path === "/api/users" && method === "GET") {
      return jsonResponse([owner]);
    }
    if (path === "/api/projects" && method === "GET") {
      return jsonResponse([]);
    }
    if (path === "/api/providers" && method === "GET") {
      return jsonResponse([]);
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
  render(<App />);

  await signIn(user);

  const navigation = await screen.findByRole("navigation", {
    name: "MVP Navigation",
  });
  for (const name of [
    "Projekt Home",
    "User",
    "Provider",
    "Profile",
    "Import",
    "Runs",
    "Cluster",
    "Candidates",
    "Export",
  ]) {
    expect(within(navigation).getByRole("link", { name })).toBeInTheDocument();
  }

  const sharedStates = screen.getByRole("region", {
    name: "Gemeinsame Zustaende",
  });
  expect(within(sharedStates).getByText("Loading: bereit")).toBeInTheDocument();
  expect(
    within(sharedStates).getByText("Empty: keine Projekte"),
  ).toBeInTheDocument();
  expect(
    within(sharedStates).getByText(/Provider: noch nicht konfiguriert/),
  ).toBeInTheDocument();
  expect(
    within(sharedStates).getByText(/Projektkontext: kein Projekt geoeffnet/),
  ).toBeInTheDocument();
  expect(
    within(sharedStates).getByText(/lokale Session aktiv/),
  ).toBeInTheDocument();
});

test("allows signed-in users to create open rename and delete projects with confirmation", async () => {
  const user = userEvent.setup();
  mockFetch((input, init) => {
    const path = String(input);
    const method = init?.method ?? "GET";
    if (path === "/api/auth/sign-in" && method === "POST") {
      return jsonResponse({ access_token: "api-token", user: owner });
    }
    if (path === "/api/users" && method === "GET") {
      return jsonResponse([owner]);
    }
    if (path === "/api/projects" && method === "GET") {
      return jsonResponse([alphaProject]);
    }
    if (path === "/api/projects" && method === "POST") {
      expect(new Headers(init?.headers).get("Authorization")).toBe(
        "Bearer api-token",
      );
      expect(String(init?.body)).toContain("Beta");
      return jsonResponse(betaProject, { status: 201 });
    }
    if (path === "/api/projects/project-beta" && method === "GET") {
      return jsonResponse(betaProject);
    }
    if (path === "/api/projects/project-beta/imports" && method === "GET") {
      return jsonResponse([]);
    }
    if (
      path === "/api/projects/project-beta/analysis-runs" &&
      method === "GET"
    ) {
      return jsonResponse([]);
    }
    if (path === "/api/projects/project-beta" && method === "PATCH") {
      expect(String(init?.body)).toContain("Beta renamed");
      return jsonResponse({ ...betaProject, name: "Beta renamed" });
    }
    if (path === "/api/projects/project-beta" && method === "DELETE") {
      expect(String(init?.body)).toContain("Beta renamed");
      return new Response(null, { status: 204 });
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
  render(<App />);

  await signIn(user);

  const createForm = await screen.findByRole("form", {
    name: "Projekt erstellen",
  });
  await user.type(within(createForm).getByLabelText("Projektname"), "Beta");
  await user.click(
    within(createForm).getByRole("button", { name: "Projekt erstellen" }),
  );
  const projectList = screen.getByRole("region", {
    name: "Bestehende Projekte",
  });
  await waitFor(() =>
    expect(within(projectList).getByText("Beta")).toBeInTheDocument(),
  );

  let betaCard = within(projectList).getByText("Beta").closest("article");
  if (betaCard === null) {
    throw new Error("project card missing");
  }
  await user.click(
    within(betaCard).getByRole("button", { name: "Projekt oeffnen" }),
  );
  expect(
    await screen.findByText(
      "Status: active; zuletzt aktualisiert: 2026-07-22T00:00:00Z",
    ),
  ).toBeInTheDocument();

  betaCard = within(projectList).getByText("Beta").closest("article");
  if (betaCard === null) {
    throw new Error("project card missing");
  }
  const nameInput = within(betaCard).getByLabelText("Projektname");
  await user.clear(nameInput);
  await user.type(nameInput, "Beta renamed");
  await user.tab();
  await waitFor(() =>
    expect(within(projectList).getByText("Beta renamed")).toBeInTheDocument(),
  );

  betaCard = within(projectList).getByText("Beta renamed").closest("article");
  if (betaCard === null) {
    throw new Error("renamed project card missing");
  }
  const deleteForm = within(betaCard)
    .getByRole("button", { name: "Projekt loeschen" })
    .closest("form");
  if (deleteForm === null) {
    throw new Error("delete form missing");
  }
  await user.type(
    within(deleteForm).getByLabelText("Projektname bestaetigen"),
    "Beta renamed",
  );
  await user.click(
    within(deleteForm).getByRole("button", { name: "Projekt loeschen" }),
  );
  await waitFor(() =>
    expect(screen.queryByText("Beta renamed")).not.toBeInTheDocument(),
  );
});

test("imports a selected CSV file and shows persisted log details", async () => {
  const user = userEvent.setup();
  mockFetch((input, init) => {
    const path = String(input);
    const method = init?.method ?? "GET";
    if (path === "/api/auth/sign-in" && method === "POST") {
      return jsonResponse({ access_token: "api-token", user: owner });
    }
    if (path === "/api/users" && method === "GET") {
      return jsonResponse([owner]);
    }
    if (path === "/api/projects" && method === "GET") {
      return jsonResponse([alphaProject]);
    }
    if (path === "/api/projects/project-alpha" && method === "GET") {
      return jsonResponse(alphaProject);
    }
    if (path === "/api/projects/project-alpha/imports" && method === "GET") {
      return jsonResponse([]);
    }
    if (
      path === "/api/projects/project-alpha/analysis-runs" &&
      method === "GET"
    ) {
      return jsonResponse([]);
    }
    if (path === "/api/projects/project-alpha/imports" && method === "POST") {
      expect(new Headers(init?.headers).get("Authorization")).toBe(
        "Bearer api-token",
      );
      expect(String(init?.body)).toContain("ticketid");
      return jsonResponse(
        {
          log: importLog,
          dataset_version: {
            id: "dataset-1",
            project_id: "project-alpha",
            version_number: 1,
            import_log_id: "import-log-1",
            record_count: 1,
            source_type: "csv",
            source_name: "fixture.csv",
            created_at: "2026-07-22T00:00:00Z",
          },
          skipped_entries: [
            {
              source_location: "row 3",
              reason: "message must not be empty",
              context: { ticketid: "T-2" },
            },
          ],
        },
        { status: 201 },
      );
    }
    if (
      path === "/api/projects/project-alpha/imports/import-log-1/entries" &&
      method === "GET"
    ) {
      return jsonResponse([
        {
          source_location: "row 3",
          reason: "message must not be empty",
          context: { ticketid: "T-2" },
        },
      ]);
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
  render(<App />);

  await signIn(user);
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  const alphaCard = within(projectList).getByText("Alpha").closest("article");
  if (alphaCard === null) {
    throw new Error("alpha project card missing");
  }
  await user.click(
    within(alphaCard).getByRole("button", { name: "Projekt oeffnen" }),
  );

  const importForm = await screen.findByRole("form", {
    name: "Import starten",
  });
  const file = new window.File(
    ["ticketid,messagegroupid,message,answer\nT-1,G-1,Hi,A\n"],
    "fixture.csv",
    { type: "text/csv" },
  );
  await user.upload(within(importForm).getByLabelText("Importdatei"), file);
  await user.click(
    within(importForm).getByRole("button", { name: "Import starten" }),
  );

  const importLogsRegion = await screen.findByRole("region", {
    name: "Importprotokolle",
  });
  expect(
    await within(importLogsRegion).findByText("fixture.csv"),
  ).toBeInTheDocument();
  expect(
    within(importLogsRegion).getByText(/Total: 2; importiert: 1;/),
  ).toBeInTheDocument();
  expect(
    within(importLogsRegion).getByText(/Dataset-Version: dataset-1/),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/row 3: message must not be empty/),
  ).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Logdetails anzeigen" }));
  expect(await screen.findByText("Import-Log geladen.")).toBeInTheDocument();
});

test("configures providers and creates a project analysis profile", async () => {
  const user = userEvent.setup();
  mockFetch((input, init) => {
    const path = String(input);
    const method = init?.method ?? "GET";
    if (path === "/api/auth/sign-in" && method === "POST") {
      return jsonResponse({ access_token: "api-token", user: owner });
    }
    if (path === "/api/users" && method === "GET") {
      return jsonResponse([owner]);
    }
    if (path === "/api/projects" && method === "GET") {
      return jsonResponse([alphaProject]);
    }
    if (path === "/api/providers" && method === "GET") {
      return jsonResponse([]);
    }
    if (path === "/api/providers/openai" && method === "PUT") {
      expect(new Headers(init?.headers).get("Authorization")).toBe(
        "Bearer api-token",
      );
      expect(String(init?.body)).toContain("sk-test-secret");
      return jsonResponse(openAiProvider);
    }
    if (path === "/api/providers/vllm" && method === "PUT") {
      expect(String(init?.body)).toContain("http://localhost:8000");
      return jsonResponse(vllmProvider);
    }
    if (path === "/api/projects/project-alpha" && method === "GET") {
      return jsonResponse(alphaProject);
    }
    if (path === "/api/projects/project-alpha/imports" && method === "GET") {
      return jsonResponse([importLog]);
    }
    if (
      path === "/api/projects/project-alpha/analysis-profiles" &&
      method === "GET"
    ) {
      return jsonResponse([]);
    }
    if (
      path === "/api/projects/project-alpha/analysis-profiles" &&
      method === "POST"
    ) {
      expect(String(init?.body)).toContain("local-embed");
      return jsonResponse(analysisProfile, { status: 201 });
    }
    if (
      path === "/api/projects/project-alpha/analysis-runs" &&
      method === "GET"
    ) {
      return jsonResponse([completedAnalysisRun]);
    }
    if (path === "/api/projects/project-alpha/candidates" && method === "GET") {
      return jsonResponse([]);
    }
    if (path === "/api/projects/project-alpha/exports" && method === "GET") {
      return jsonResponse([]);
    }
    if (
      path === "/api/projects/project-alpha/analysis-runs" &&
      method === "POST"
    ) {
      expect(String(init?.body)).toContain("dataset-1");
      expect(String(init?.body)).toContain("profile-1");
      return jsonResponse(analysisRun, { status: 201 });
    }
    if (
      path ===
        "/api/projects/project-alpha/analysis-runs/run-completed/clusters/generate" &&
      method === "POST"
    ) {
      return jsonResponse([cluster]);
    }
    if (
      path === "/api/projects/project-alpha/clusters/cluster-1" &&
      method === "PATCH"
    ) {
      expect(String(init?.body)).toContain("Reset workflow");
      return jsonResponse(updatedCluster);
    }
    if (
      path === "/api/projects/project-alpha/clusters/cluster-1/sources" &&
      method === "GET"
    ) {
      return jsonResponse([
        {
          cluster_id: "cluster-1",
          message_pair_id: "pair-1",
          ticketid: "T-1",
          messagegroupid: "G-1",
          message: "How do I reset it?",
          answer: "Use the reset link.",
          membership_score: 0.91,
          is_outlier: false,
          assignment_type: "automatic",
        },
      ]);
    }
    if (
      path === "/api/projects/project-alpha/clusters/cluster-1/candidates" &&
      method === "POST"
    ) {
      return jsonResponse(candidate, { status: 201 });
    }
    if (
      path === "/api/projects/project-alpha/candidates/candidate-1" &&
      method === "PATCH"
    ) {
      const body = JSON.parse(String(init?.body));
      expect(body.manual_title).toBe("Reset FAQ");
      expect(body.manual_status).toBe("export_ready");
      expect(body.manual_alternative_questions).toEqual([
        "Password reset does not work",
      ]);
      expect(body.manual_parameters).toEqual({ account_id: "required" });
      expect(body.manual_external_data_dependencies).toEqual([
        "identity-service",
      ]);
      return jsonResponse(updatedCandidate);
    }
    if (
      path === "/api/projects/project-alpha/candidates/candidate-1/sources" &&
      method === "GET"
    ) {
      return jsonResponse([
        {
          candidate_id: "candidate-1",
          cluster_id: "cluster-1",
          message_pair_id: "pair-1",
          ticketid: "T-1",
          messagegroupid: "G-1",
          message: "How do I reset it?",
          answer: "Use the reset link.",
          message_segment_id: null,
          source_language: "unknown",
          normalized_customer_message: "how do i reset it?",
          normalized_support_answer: "use the reset link.",
          assignment_type: "automatic",
          membership_score: 0.91,
          is_multi_intent: false,
          intent_label: null,
          dataset_version_id: "dataset-1",
          analysis_run_id: "run-completed",
        },
      ]);
    }
    if (
      path === "/api/projects/project-alpha/exports/candidates" &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      expect(body.include_original_text).toBe(false);
      return jsonResponse(
        {
          export: candidateExportLog,
          csv_content:
            "candidate_id,candidate_type,status\\ncandidate-1,parameterized_faq,export_ready\\n",
          warning:
            "Export enthaelt Originaltext und damit potentiell identifizierende Inhalte.",
        },
        { status: 201 },
      );
    }
    if (
      path === "/api/projects/project-alpha/exports/source-assignments" &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      expect(body.include_original_text).toBe(false);
      return jsonResponse(
        {
          export: sourceAssignmentExportLog,
          csv_content:
            "candidate_id,cluster_id,pair_id,customer_message,support_answer\\ncandidate-1,cluster-1,pair-1,,\\n",
          warning: null,
        },
        { status: 201 },
      );
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
  render(<App />);

  await signIn(user);

  const openAiForm = await screen.findByRole("form", {
    name: "OpenAI Provider konfigurieren",
  });
  await user.type(
    within(openAiForm).getByLabelText("Neuer OpenAI API-Key"),
    "sk-test-secret",
  );
  await user.type(
    within(openAiForm).getByLabelText("OpenAI Modelle"),
    "gpt-4.1-mini",
  );
  await user.click(
    within(openAiForm).getByRole("button", { name: "OpenAI speichern" }),
  );

  expect(await screen.findByText("API-Key gesetzt")).toBeInTheDocument();
  expect(screen.queryByText("sk-test-secret")).not.toBeInTheDocument();

  const vllmForm = screen.getByRole("form", {
    name: "vLLM Provider konfigurieren",
  });
  await user.type(
    within(vllmForm).getByLabelText("Endpoint URL"),
    "http://localhost:8000",
  );
  await user.type(
    within(vllmForm).getByLabelText("vLLM Modelle"),
    "local-embed",
  );
  await user.click(
    within(vllmForm).getByRole("button", { name: "vLLM speichern" }),
  );

  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  const alphaCard = within(projectList).getByText("Alpha").closest("article");
  if (alphaCard === null) {
    throw new Error("alpha project card missing");
  }
  await user.click(
    within(alphaCard).getByRole("button", { name: "Projekt oeffnen" }),
  );

  const profileForm = await screen.findByRole("form", {
    name: "Analyseprofil erstellen",
  });
  await user.type(
    within(profileForm).getByLabelText("Profilname"),
    "Local profile",
  );
  await user.type(within(profileForm).getByLabelText("Modell"), "local-embed");
  await user.type(
    within(profileForm).getByLabelText("Similarity Threshold"),
    "0.78",
  );
  await user.type(within(profileForm).getByLabelText("Algorithmus"), "hdbscan");
  await user.type(within(profileForm).getByLabelText("Prompt-ID"), "faq-v1");
  await user.click(
    within(profileForm).getByRole("button", { name: "Profil speichern" }),
  );

  expect(await screen.findByText("Local profile")).toBeInTheDocument();
  expect(screen.getByText("vllm/local-embed")).toBeInTheDocument();
  expect(screen.getByText(/"similarity":0.78/)).toBeInTheDocument();

  const runForm = await screen.findByRole("form", {
    name: "Analyse starten",
  });
  await user.type(within(runForm).getByLabelText("Run-Modus"), "fixture");
  await user.click(
    within(runForm).getByRole("button", { name: "Analyse starten" }),
  );

  const runsRegion = await screen.findByRole("region", {
    name: "Analyse Runs",
  });
  expect(await within(runsRegion).findByText("queued")).toBeInTheDocument();
  expect(within(runsRegion).getByText("0%")).toBeInTheDocument();
  expect(
    within(runsRegion).getAllByText("Provider/Modell: vllm/local-embed").length,
  ).toBeGreaterThan(0);
  expect(
    within(runsRegion).getAllByText(/Dataset-Version: dataset-1/).length,
  ).toBeGreaterThan(0);
  expect(within(runsRegion).getByText(/Diagnose: {}/)).toBeInTheDocument();

  const clusterActions = await screen.findByRole("region", {
    name: "Cluster Aktionen",
  });
  const generateButtons = within(clusterActions).getAllByRole("button", {
    name: "Cluster erzeugen",
  });
  const enabledGenerate = generateButtons.find(
    (button) => !button.hasAttribute("disabled"),
  );
  if (enabledGenerate === undefined) {
    throw new Error("enabled cluster generation button missing");
  }
  await user.click(enabledGenerate);

  const clusterExplorer = await screen.findByRole("region", {
    name: "Cluster Explorer",
  });
  expect(
    await within(clusterExplorer).findByText("Cluster H"),
  ).toBeInTheDocument();
  expect(
    within(clusterExplorer).getByText(/Auto: Cluster H \/ deterministic-key/),
  ).toBeInTheDocument();
  expect(
    within(clusterExplorer).getByText(/Manual: - \/ - \/ -/),
  ).toBeInTheDocument();
  expect(
    within(clusterExplorer).getByText(
      /Effective: Cluster H \/ deterministic-key/,
    ),
  ).toBeInTheDocument();

  const clusterCard = within(clusterExplorer)
    .getByText("Cluster H")
    .closest("article");
  if (clusterCard === null) {
    throw new Error("cluster card missing");
  }
  await user.type(
    within(clusterCard).getByLabelText("Manueller Titel"),
    "Reset workflow",
  );
  await user.type(
    within(clusterCard).getByLabelText("Manuelle Kategorie"),
    "Account",
  );
  await user.selectOptions(
    within(clusterCard).getByLabelText("Manueller Status"),
    "reviewed",
  );
  await user.click(
    within(clusterCard).getByRole("button", { name: "Overrides speichern" }),
  );
  expect(
    await within(clusterExplorer).findByText("Reset workflow"),
  ).toBeInTheDocument();
  expect(
    within(clusterExplorer).getByText(
      /Effective: Reset workflow \/ Account \/ reviewed/,
    ),
  ).toBeInTheDocument();

  await user.click(
    within(clusterCard).getByRole("button", { name: "Quellen anzeigen" }),
  );
  const sources = await screen.findByRole("region", {
    name: "Cluster Quellen",
  });
  expect(within(sources).getByText("T-1 / G-1")).toBeInTheDocument();
  expect(
    within(sources).getByText("Message: How do I reset it?"),
  ).toBeInTheDocument();
  expect(
    within(sources).getByText("Answer: Use the reset link."),
  ).toBeInTheDocument();

  const updatedClusterCard = within(clusterExplorer)
    .getByText("Reset workflow")
    .closest("article");
  if (updatedClusterCard === null) {
    throw new Error("updated cluster card missing");
  }
  await user.click(
    within(updatedClusterCard).getByRole("button", {
      name: "Candidate erstellen",
    }),
  );

  const candidateEditor = await screen.findByRole("region", {
    name: "Candidate Editor",
  });
  expect(
    await within(candidateEditor).findByText("Cluster H"),
  ).toBeInTheDocument();
  expect(
    within(candidateEditor).getByText(
      /Auto: Cluster H \/ deterministic-key \/ unreviewed/,
    ),
  ).toBeInTheDocument();
  expect(
    within(candidateEditor).getByText(/Manual: - \/ - \/ -/),
  ).toBeInTheDocument();
  expect(
    within(candidateEditor).getByText(
      /Effective: Cluster H \/ deterministic-key \/ unreviewed/,
    ),
  ).toBeInTheDocument();
  expect(
    within(candidateEditor).getByText("Frage Effective: How do I reset it?"),
  ).toBeInTheDocument();
  expect(
    within(candidateEditor).getByText("Antwort Effective: Use the reset link."),
  ).toBeInTheDocument();

  const candidateCard = within(candidateEditor)
    .getByText("Cluster H")
    .closest("article");
  if (candidateCard === null) {
    throw new Error("candidate card missing");
  }
  await user.selectOptions(
    within(candidateCard).getByLabelText("Candidate Typ"),
    "parameterized_faq",
  );
  await user.selectOptions(
    within(candidateCard).getByLabelText("Manueller Status"),
    "export_ready",
  );
  await user.type(
    within(candidateCard).getByLabelText("Manuelle Kategorie"),
    "Account",
  );
  await user.type(
    within(candidateCard).getByLabelText("Manueller Titel"),
    "Reset FAQ",
  );
  await user.type(
    within(candidateCard).getByLabelText("Manuelle Frage"),
    "How can customers reset passwords?",
  );
  await user.type(
    within(candidateCard).getByLabelText("Manuelle Antwort"),
    "Send a reset link.",
  );
  await user.type(
    within(candidateCard).getByLabelText("Alternative Fragen, eine pro Zeile"),
    "Password reset does not work",
  );
  fireEvent.change(within(candidateCard).getByLabelText("Parameter JSON"), {
    target: { value: '{"account_id":"required"}' },
  });
  await user.type(
    within(candidateCard).getByLabelText(
      "Externe Datenabhaengigkeiten, eine pro Zeile",
    ),
    "identity-service",
  );
  await user.type(
    within(candidateCard).getByLabelText("Notizen"),
    "Reviewed candidate.",
  );
  await user.click(
    within(candidateCard).getByRole("button", {
      name: "Candidate speichern",
    }),
  );
  expect(
    await within(candidateEditor).findByText("Reset FAQ"),
  ).toBeInTheDocument();
  expect(
    within(candidateEditor).getByText(
      /Effective: Reset FAQ \/ Account \/ export_ready/,
    ),
  ).toBeInTheDocument();
  expect(
    within(candidateEditor).getByText(
      "Frage Effective: How can customers reset passwords?",
    ),
  ).toBeInTheDocument();
  expect(
    within(candidateEditor).getByText("Antwort Effective: Send a reset link."),
  ).toBeInTheDocument();
  expect(
    within(candidateEditor).getByText(
      'Parameter Effective: {"account_id":"required"}',
    ),
  ).toBeInTheDocument();

  await user.click(
    within(candidateEditor).getByRole("button", {
      name: "Candidate Quellen anzeigen",
    }),
  );
  const candidateSources = await screen.findByRole("region", {
    name: "Candidate Quellen",
  });
  expect(within(candidateSources).getByText("T-1 / G-1")).toBeInTheDocument();
  expect(
    within(candidateSources).getByText("Message: How do I reset it?"),
  ).toBeInTheDocument();
  expect(
    within(candidateSources).getByText("Answer: Use the reset link."),
  ).toBeInTheDocument();

  const candidateExportForm = await screen.findByRole("form", {
    name: "Candidate CSV exportieren",
  });
  await user.click(
    within(candidateExportForm).getByRole("button", {
      name: "Candidate CSV exportieren",
    }),
  );
  expect(
    await screen.findByText(/Export enthaelt Originaltext/),
  ).toBeInTheDocument();

  const sourceExportForm = screen.getByRole("form", {
    name: "Source Assignment CSV exportieren",
  });
  await user.click(
    within(sourceExportForm).getByRole("button", {
      name: "Source Assignment CSV exportieren",
    }),
  );
  const exportHistory = await screen.findByRole("region", {
    name: "Exporthistorie",
  });
  expect(
    within(exportHistory).getByText("candidate_csv-export-candidates-1.csv"),
  ).toBeInTheDocument();
  expect(
    within(exportHistory).getByText(
      "source_assignment_csv-export-sources-1.csv",
    ),
  ).toBeInTheDocument();
  expect(
    within(exportHistory).getByText(/Originaltext: ja/),
  ).toBeInTheDocument();
  expect(
    within(exportHistory).getByText(/Originaltext: nein/),
  ).toBeInTheDocument();
});

test("does not save untouched generated candidate multi-value fields as empty manual overrides", async () => {
  const user = userEvent.setup();
  const patchBodies: unknown[] = [];
  mockFetch((input, init) => {
    const path = String(input);
    const method = init?.method ?? "GET";
    if (path === "/api/auth/sign-in" && method === "POST") {
      return jsonResponse({ access_token: "api-token", user: owner });
    }
    if (path === "/api/users" && method === "GET") {
      return jsonResponse([owner]);
    }
    if (path === "/api/projects" && method === "GET") {
      return jsonResponse([alphaProject]);
    }
    if (path === "/api/providers" && method === "GET") {
      return jsonResponse([]);
    }
    if (path === "/api/projects/project-alpha" && method === "GET") {
      return jsonResponse(alphaProject);
    }
    if (path === "/api/projects/project-alpha/imports" && method === "GET") {
      return jsonResponse([]);
    }
    if (
      path === "/api/projects/project-alpha/analysis-profiles" &&
      method === "GET"
    ) {
      return jsonResponse([]);
    }
    if (
      path === "/api/projects/project-alpha/analysis-runs" &&
      method === "GET"
    ) {
      return jsonResponse([]);
    }
    if (path === "/api/projects/project-alpha/candidates" && method === "GET") {
      return jsonResponse([generatedMultiValueCandidate]);
    }
    if (
      path === "/api/projects/project-alpha/candidates/candidate-1" &&
      method === "PATCH"
    ) {
      const body = JSON.parse(String(init?.body));
      patchBodies.push(body);
      return jsonResponse({
        ...generatedMultiValueCandidate,
        notes: body.notes,
      });
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
  render(<App />);

  await signIn(user);
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  const alphaCard = within(projectList).getByText("Alpha").closest("article");
  if (alphaCard === null) {
    throw new Error("alpha project card missing");
  }
  await user.click(
    within(alphaCard).getByRole("button", { name: "Projekt oeffnen" }),
  );

  const candidateEditor = await screen.findByRole("region", {
    name: "Candidate Editor",
  });
  expect(
    within(candidateEditor).getByText(
      /Alternative Fragen Auto: Password reset failed; Reset mail missing/,
    ),
  ).toBeInTheDocument();
  expect(
    within(candidateEditor).getByText(/Alternative Fragen Manual: -/),
  ).toBeInTheDocument();
  expect(
    within(candidateEditor).getByText(
      /Alternative Fragen Effective: Password reset failed; Reset mail missing/,
    ),
  ).toBeInTheDocument();
  expect(
    within(candidateEditor).getByText(
      'Parameter Auto: {"account_id":"optional"}',
    ),
  ).toBeInTheDocument();
  expect(
    within(candidateEditor).getByText(/Parameter Manual: -/),
  ).toBeInTheDocument();
  expect(
    within(candidateEditor).getByText(
      'Parameter Effective: {"account_id":"optional"}',
    ),
  ).toBeInTheDocument();
  expect(
    within(candidateEditor).getByText(
      /Externe Datenabhaengigkeiten Auto: identity-service/,
    ),
  ).toBeInTheDocument();
  expect(
    within(candidateEditor).getByText(/Externe Datenabhaengigkeiten Manual: -/),
  ).toBeInTheDocument();
  expect(
    within(candidateEditor).getByText(
      /Externe Datenabhaengigkeiten Effective: identity-service/,
    ),
  ).toBeInTheDocument();
  const candidateCard = within(candidateEditor)
    .getByText("Cluster H")
    .closest("article");
  if (candidateCard === null) {
    throw new Error("candidate card missing");
  }
  await user.type(
    within(candidateCard).getByLabelText("Notizen"),
    "Reviewed without multi-value edits.",
  );
  await user.click(
    within(candidateCard).getByRole("button", {
      name: "Candidate speichern",
    }),
  );

  expect(patchBodies).toHaveLength(1);
  expect(patchBodies[0]).toMatchObject({
    manual_alternative_questions: null,
    manual_parameters: null,
    manual_external_data_dependencies: null,
    notes: "Reviewed without multi-value edits.",
  });
});
