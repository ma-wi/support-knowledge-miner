import {
  cleanup,
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

  expect(await screen.findByText("fixture.csv")).toBeInTheDocument();
  expect(screen.getByText(/Total: 2; importiert: 1;/)).toBeInTheDocument();
  expect(screen.getByText(/Dataset-Version: dataset-1/)).toBeInTheDocument();
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
    within(runsRegion).getByText("Provider/Modell: vllm/local-embed"),
  ).toBeInTheDocument();
  expect(
    within(runsRegion).getByText(/Dataset-Version: dataset-1/),
  ).toBeInTheDocument();
  expect(within(runsRegion).getByText(/Diagnose: {}/)).toBeInTheDocument();
});
