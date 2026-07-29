import {
  act,
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
  first_name: "Local",
  last_name: "Owner",
  email: "owner@example.test",
};
const sessionTokenStorageKey = "skm.session-token";
const curator = {
  id: "local-curator",
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
const ollamaProvider = {
  provider: "ollama",
  endpoint_url: "http://localhost:11434",
  manual_models: ["nomic-embed-text"],
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
  parameters: {},
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
  auto_category: "hdbscan",
  manual_category: null,
  effective_category: "hdbscan",
  auto_status: "unreviewed",
  manual_status: null,
  effective_status: "unreviewed",
  score: 0.91,
  is_outlier: false,
  algorithm: "hdbscan",
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
  auto_category_path: "hdbscan",
  manual_category_path: null,
  effective_category_path: "hdbscan",
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
  vi.useRealTimers();
  window.sessionStorage.clear();
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

function mockProjectFetch(
  override: (
    path: string,
    method: string,
    init?: RequestInit,
  ) => Response | Promise<Response> | undefined,
) {
  return mockFetch((input, init) => {
    const path = String(input);
    const method = init?.method ?? "GET";
    const overridden = override(path, method, init);
    if (overridden !== undefined) {
      return overridden;
    }
    if (path === "/api/auth/sign-in" && method === "POST") {
      return jsonResponse({ access_token: "api-token", user: owner });
    }
    if (path === "/api/auth/sign-out" && method === "POST") {
      return new Response(null, { status: 204 });
    }
    if (path === "/api/users" && method === "GET") {
      return jsonResponse([owner]);
    }
    if (path === "/api/projects" && method === "GET") {
      return jsonResponse([alphaProject, betaProject]);
    }
    if (path === "/api/providers" && method === "GET") {
      return jsonResponse([vllmProvider]);
    }
    if (path === "/api/projects/project-alpha" && method === "GET") {
      return jsonResponse(alphaProject);
    }
    if (path === "/api/projects/project-beta" && method === "GET") {
      return jsonResponse(betaProject);
    }
    if (path.endsWith("/imports") && method === "GET") {
      return jsonResponse(path.includes("project-alpha") ? [importLog] : []);
    }
    if (path.endsWith("/analysis-profiles") && method === "GET") {
      return jsonResponse(
        path.includes("project-alpha") ? [analysisProfile] : [],
      );
    }
    if (
      (path.endsWith("/candidates") || path.endsWith("/exports")) &&
      method === "GET"
    ) {
      return jsonResponse([]);
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
}

async function signIn(user: ReturnType<typeof userEvent.setup>) {
  const signInForm = screen
    .getByRole("button", { name: "Anmelden" })
    .closest("form");
  if (signInForm === null) {
    throw new Error("sign-in form missing");
  }
  await user.type(
    within(signInForm).getByLabelText("E-Mail"),
    "owner@example.test",
  );
  await user.type(
    within(signInForm).getByLabelText("Passwort"),
    "owner-password",
  );
  await user.click(
    within(signInForm).getByRole("button", { name: "Anmelden" }),
  );
}

async function openSettingsTab(
  user: ReturnType<typeof userEvent.setup>,
  tabName: "Embedding-Provider" | "Nutzer",
) {
  await user.click(screen.getByRole("button", { name: "Einstellungen" }));
  await user.click(await screen.findByRole("button", { name: tabName }));
}

async function openProjectTab(
  user: ReturnType<typeof userEvent.setup>,
  tabName:
    | "Profile"
    | "Import"
    | "Runs"
    | "Cluster"
    | "Kandidaten"
    | "Export"
    | "Projekt löschen",
) {
  await user.click(await screen.findByRole("button", { name: tabName }));
}

function getProjectRow(projectList: HTMLElement, projectName: string) {
  const escapedProjectName = projectName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return within(projectList).getByRole("button", {
    name: new RegExp(`^${escapedProjectName}`),
  });
}

async function expectErrorFeedback(text: string, rawText?: string) {
  await waitFor(() => {
    const alert = screen.getByRole("alert");
    expect(alert).toHaveClass("error");
    expect(alert).toHaveTextContent(`Fehler: ${text}`);
    if (rawText !== undefined) {
      expect(alert).not.toHaveTextContent(rawText);
    }
  });
}

test("prevents protected user management before sign-in", () => {
  render(<App />);

  expect(
    screen.getByRole("heading", { name: "Lokaler Zugriff" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("heading", { name: "Projekte & Analysen" }),
  ).not.toBeInTheDocument();
});

test("restores a tab session only after the stored token is validated by the server", async () => {
  window.sessionStorage.setItem(sessionTokenStorageKey, "stored-token");
  const fetchMock = mockFetch((input, init) => {
    const path = String(input);
    const method = init?.method ?? "GET";
    if (path === "/api/auth/me" && method === "GET") {
      expect(new Headers(init?.headers).get("Authorization")).toBe(
        "Bearer stored-token",
      );
      return jsonResponse(owner);
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

  expect(screen.getByRole("status")).toHaveTextContent(
    "Gespeicherte Sitzung wird geprüft.",
  );
  expect(
    screen.queryByRole("heading", { name: "Projekte & Analysen" }),
  ).not.toBeInTheDocument();
  expect(
    await screen.findByRole("heading", { name: "Projekte & Analysen" }),
  ).toBeInTheDocument();
  expect(screen.getByText("Local Owner")).toBeInTheDocument();
  expect(
    screen.queryByRole("heading", { name: "Lokaler Zugriff" }),
  ).not.toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/auth/me",
    expect.objectContaining({ headers: expect.any(Headers) }),
  );
});

test("clears a stored token when server validation rejects the session", async () => {
  window.sessionStorage.setItem(sessionTokenStorageKey, "expired-token");
  mockFetch((input, init) => {
    const path = String(input);
    const method = init?.method ?? "GET";
    if (path === "/api/auth/me" && method === "GET") {
      return jsonResponse(
        { detail: "authentication required" },
        { status: 401 },
      );
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });

  render(<App />);

  expect(
    await screen.findByRole("heading", { name: "Lokaler Zugriff" }),
  ).toBeInTheDocument();
  expect(window.sessionStorage.getItem(sessionTokenStorageKey)).toBeNull();
  expect(
    screen.queryByRole("heading", { name: "Projekte & Analysen" }),
  ).not.toBeInTheDocument();
});

test("preserves a stored token after a transient validation failure and restores it on retry", async () => {
  window.sessionStorage.setItem(sessionTokenStorageKey, "stored-token");
  let validationAttempts = 0;
  mockFetch((input, init) => {
    const path = String(input);
    const method = init?.method ?? "GET";
    if (path === "/api/auth/me" && method === "GET") {
      validationAttempts += 1;
      if (validationAttempts === 1) {
        return Promise.reject(new Error("backend unavailable"));
      }
      return jsonResponse(owner);
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

  const firstRender = render(<App />);

  expect(
    await screen.findByRole("heading", { name: "Lokaler Zugriff" }),
  ).toBeInTheDocument();
  expect(window.sessionStorage.getItem(sessionTokenStorageKey)).toBe(
    "stored-token",
  );

  firstRender.unmount();
  render(<App />);

  expect(
    await screen.findByRole("heading", { name: "Projekte & Analysen" }),
  ).toBeInTheDocument();
  expect(window.sessionStorage.getItem(sessionTokenStorageKey)).toBe(
    "stored-token",
  );
});

test("does not clear stored session state when a stale bootstrap rejects after unmount", async () => {
  window.sessionStorage.setItem(sessionTokenStorageKey, "stored-token");
  let rejectValidation: (reason?: unknown) => void = () => undefined;
  const pendingValidation = new Promise<Response>((_resolve, reject) => {
    rejectValidation = reject;
  });
  const fetchMock = mockFetch((input, init) => {
    const path = String(input);
    const method = init?.method ?? "GET";
    if (path === "/api/auth/me" && method === "GET") {
      return pendingValidation;
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });

  const rendered = render(<App />);
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  rendered.unmount();
  rejectValidation(new Error("stale validation failure"));
  await pendingValidation.catch(() => undefined);
  await new Promise((resolve) => window.setTimeout(resolve, 0));

  expect(window.sessionStorage.getItem(sessionTokenStorageKey)).toBe(
    "stored-token",
  );
});

test("stores only the bearer token after sign-in", async () => {
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

  await screen.findByRole("heading", { name: "Projekte & Analysen" });
  expect(window.sessionStorage).toHaveLength(1);
  expect(window.sessionStorage.getItem(sessionTokenStorageKey)).toBe(
    "api-token",
  );
  expect(JSON.stringify(window.sessionStorage)).not.toContain(
    "owner@example.test",
  );
  expect(JSON.stringify(window.sessionStorage)).not.toContain("owner-password");
});

test("clears local session state even when server sign-out is unavailable", async () => {
  const user = userEvent.setup();
  const fetchMock = mockFetch((input, init) => {
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
    if (path === "/api/auth/sign-out" && method === "POST") {
      expect(new Headers(init?.headers).get("Authorization")).toBe(
        "Bearer api-token",
      );
      return Promise.reject(new Error("backend unavailable"));
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
  render(<App />);
  await signIn(user);
  await screen.findByRole("heading", { name: "Projekte & Analysen" });

  await user.click(screen.getByRole("button", { name: "Abmelden" }));

  expect(
    await screen.findByRole("heading", { name: "Lokaler Zugriff" }),
  ).toBeInTheDocument();
  expect(window.sessionStorage.getItem(sessionTokenStorageKey)).toBeNull();
  await waitFor(() =>
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/sign-out",
      expect.objectContaining({ method: "POST" }),
    ),
  );
  await expectErrorFeedback(
    "Lokale Abmeldung abgeschlossen, aber die Serversitzung konnte nicht widerrufen werden.",
    "backend unavailable",
  );
});

test("shows a sanitized API detail when server-side sign-out revocation fails", async () => {
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
    if (path === "/api/auth/sign-out" && method === "POST") {
      return jsonResponse(
        { detail: "server session could not be revoked" },
        { status: 503 },
      );
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
  render(<App />);
  await signIn(user);
  await screen.findByRole("heading", { name: "Projekte & Analysen" });

  await user.click(screen.getByRole("button", { name: "Abmelden" }));

  expect(
    await screen.findByRole("heading", { name: "Lokaler Zugriff" }),
  ).toBeInTheDocument();
  expect(window.sessionStorage.getItem(sessionTokenStorageKey)).toBeNull();
  await expectErrorFeedback("server session could not be revoked");
});

test("keeps protected UI closed when backend rejects credentials", async () => {
  const user = userEvent.setup();
  mockFetch(() =>
    jsonResponse({ detail: "invalid credentials" }, { status: 401 }),
  );
  render(<App />);

  await signIn(user);

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Fehler: invalid credentials",
  );
  expect(
    screen.queryByRole("heading", { name: "Projekte & Analysen" }),
  ).not.toBeInTheDocument();
});

test("keeps protected UI closed when backend is unavailable", async () => {
  const user = userEvent.setup();
  mockFetch(() => Promise.reject(new Error("backend unavailable")));
  render(<App />);

  await signIn(user);

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent(
    "Anmeldung fehlgeschlagen oder Backend nicht erreichbar.",
  );
  expect(alert).not.toHaveTextContent("backend unavailable");
  expect(
    screen.queryByRole("heading", { name: "Projekte & Analysen" }),
  ).not.toBeInTheDocument();
});

test.each([
  {
    name: "sanitized API detail",
    providerResponse: () =>
      jsonResponse(
        { detail: "provider list temporarily unavailable" },
        { status: 503 },
      ),
    expected: "provider list temporarily unavailable",
    rawText: "raw provider failure",
  },
  {
    name: "safe network fallback",
    providerResponse: () =>
      Promise.reject(new Error("raw provider transport failure")),
    expected:
      "Angemeldet, aber Provider-Konfigurationen konnten nicht geladen werden.",
    rawText: "raw provider transport failure",
  },
])(
  "keeps the session and shows $name when provider loading after sign-in fails",
  async ({ providerResponse, expected, rawText }) => {
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
        return providerResponse();
      }
      throw new Error(`unexpected request ${method} ${path}`);
    });
    render(<App />);

    await signIn(user);

    expect(
      await screen.findByRole("heading", { name: "Projekte & Analysen" }),
    ).toBeInTheDocument();
    expect(window.sessionStorage.getItem(sessionTokenStorageKey)).toBe(
      "api-token",
    );
    await expectErrorFeedback(expected, rawText);
    expect(
      screen.queryByText("Angemeldet. Geschützte Workflows sind verfügbar."),
    ).not.toBeInTheDocument();
  },
);

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
    await screen.findByRole("heading", { name: "Projekte & Analysen" }),
  ).toBeInTheDocument();
  await openSettingsTab(user, "Nutzer");
  expect(
    await screen.findByRole("heading", { name: "Nutzer anlegen" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Selbstlöschung gesperrt" }),
  ).toBeDisabled();

  const createForm = screen.getByRole("form", { name: "User anlegen" });
  await user.type(within(createForm).getByLabelText("Name"), "Support Curator");
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

  expect(
    await screen.findByDisplayValue("curator@example.test"),
  ).toBeInTheDocument();
  const success = screen.getByRole("status");
  expect(success).toHaveClass("feedback", "success");
  expect(success).toHaveTextContent(
    "Erfolg: User angelegt. Passwortwert bleibt write-only.",
  );
  await user.click(screen.getByRole("button", { name: "User löschen" }));
  await waitFor(() =>
    expect(
      screen.queryByDisplayValue("curator@example.test"),
    ).not.toBeInTheDocument(),
  );
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/auth/sign-in",
    expect.objectContaining({ method: "POST" }),
  );
});

test("shows sidebar navigation and settings tabs after sign-in", async () => {
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
    name: "Hauptnavigation",
  });
  expect(
    within(navigation).getByRole("button", { name: "Projekte" }),
  ).toBeInTheDocument();
  expect(
    within(navigation).getByRole("button", { name: "Einstellungen" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Abmelden" })).toBeInTheDocument();

  await openSettingsTab(user, "Embedding-Provider");
  expect(
    screen.getByRole("button", { name: "Embedding-Provider" }),
  ).toHaveClass("selected");
  await user.click(screen.getByRole("button", { name: "Nutzer" }));
  expect(screen.getByRole("button", { name: "Nutzer" })).toHaveClass(
    "selected",
  );
  expect(
    screen.queryByRole("region", { name: "Gemeinsame Zustände" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("heading", { name: "Einstellungen" }),
  ).toBeInTheDocument();
});

test("refreshes OpenAI models for an already stored API key", async () => {
  const user = userEvent.setup();
  let openAiCheckCount = 0;
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
      return jsonResponse([openAiProvider]);
    }
    if (path === "/api/providers/openai/check" && method === "POST") {
      openAiCheckCount += 1;
      expect(new Headers(init?.headers).get("Authorization")).toBe(
        "Bearer api-token",
      );
      return jsonResponse({
        provider: "openai",
        ok: true,
        models: ["text-embedding-3-large"],
        message: "live calls are not required",
      });
    }
    if (path === "/api/providers/openai" && method === "PUT") {
      const body = JSON.parse(String(init?.body));
      expect(body.api_key).toBeUndefined();
      expect(body.manual_models).toEqual(["text-embedding-3-large"]);
      return jsonResponse({
        ...openAiProvider,
        manual_models: ["text-embedding-3-large"],
      });
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
  render(<App />);

  await signIn(user);
  await openSettingsTab(user, "Embedding-Provider");

  const openAiForm = await screen.findByRole("form", {
    name: "OpenAI Provider konfigurieren",
  });
  await user.click(
    within(openAiForm).getByRole("button", { name: "Modelle abrufen" }),
  );

  expect(
    await within(openAiForm).findByLabelText("text-embedding-3-large"),
  ).toBeChecked();
  expect(
    await screen.findByText("1 OpenAI Modell(e) abgerufen."),
  ).toBeInTheDocument();
  expect(
    screen.queryByText("live calls are not required"),
  ).not.toBeInTheDocument();
  expect(openAiCheckCount).toBeGreaterThanOrEqual(1);
});

test("configures Ollama and refreshes local models", async () => {
  const user = userEvent.setup();
  let ollamaSaveCount = 0;
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
    if (path === "/api/providers/ollama" && method === "PUT") {
      ollamaSaveCount += 1;
      const body = JSON.parse(String(init?.body));
      expect(body.endpoint_url).toBe("http://localhost:11434");
      expect(body.manual_models).toEqual(
        ollamaSaveCount === 1 ? [] : ["nomic-embed-text", "mxbai-embed-large"],
      );
      return jsonResponse({
        ...ollamaProvider,
        manual_models: body.manual_models,
      });
    }
    if (path === "/api/providers/ollama/check" && method === "POST") {
      return jsonResponse({
        provider: "ollama",
        ok: true,
        models: ["nomic-embed-text", "mxbai-embed-large"],
        message: "Ollama models discovered",
      });
    }
    if (path === "/api/providers/ollama/pull" && method === "POST") {
      const body = JSON.parse(String(init?.body));
      expect(body.model).toBe("embeddinggemma");
      return jsonResponse({
        ...ollamaProvider,
        manual_models: [
          "nomic-embed-text",
          "mxbai-embed-large",
          "embeddinggemma",
        ],
      });
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
  render(<App />);

  await signIn(user);
  await openSettingsTab(user, "Embedding-Provider");

  const ollamaForm = await screen.findByRole("form", {
    name: "Ollama Provider konfigurieren",
  });
  await user.type(
    within(ollamaForm).getByLabelText("Endpoint URL"),
    "http://localhost:11434",
  );
  expect(within(ollamaForm).queryByLabelText("Ollama Modelle")).toBeNull();
  await user.click(
    within(ollamaForm).getByRole("button", { name: "Ollama speichern" }),
  );

  expect(
    await screen.findByText("Ollama Provider gespeichert."),
  ).toBeInTheDocument();
  await user.click(
    within(ollamaForm).getByRole("button", { name: "Modelle abrufen" }),
  );
  expect(
    await screen.findByText(/nomic-embed-text, mxbai-embed-large/),
  ).toBeInTheDocument();
  await user.type(
    within(ollamaForm).getByLabelText("Neues Ollama Modell"),
    "embeddinggemma",
  );
  await user.click(
    within(ollamaForm).getByRole("button", {
      name: "Herunterladen und hinzufügen",
    }),
  );
  expect(
    await screen.findByText("Ollama Modell embeddinggemma wurde hinzugefügt."),
  ).toBeInTheDocument();
  expect(
    await screen.findByText(
      /nomic-embed-text, mxbai-embed-large, embeddinggemma/,
    ),
  ).toBeInTheDocument();
});

test("allows signed-in users to create open rename and delete projects with confirmation", async () => {
  const user = userEvent.setup();
  let currentBetaProject = betaProject;
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
      return jsonResponse(currentBetaProject);
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
      currentBetaProject = { ...betaProject, name: "Beta renamed" };
      return jsonResponse(currentBetaProject);
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
  expect(
    screen.queryByRole("form", { name: "Import starten" }),
  ).not.toBeInTheDocument();
  await waitFor(() =>
    expect(within(projectList).getByText("Beta")).toBeInTheDocument(),
  );

  const formattedUpdatedAt = new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(betaProject.updated_at));
  const betaRow = getProjectRow(projectList, "Beta");
  expect(betaRow).toHaveTextContent(formattedUpdatedAt);
  expect(within(projectList).queryByRole("textbox")).not.toBeInTheDocument();
  expect(
    within(projectList).queryByRole("button", { name: "Projekt öffnen" }),
  ).not.toBeInTheDocument();

  await user.click(betaRow);
  expect(
    await screen.findByRole("form", { name: "Import starten" }),
  ).toBeInTheDocument();
  const projectTabs = screen.getByRole("tablist", {
    name: "Projektbereiche",
  });
  expect(
    within(projectTabs)
      .getAllByRole("button")
      .map((button) => button.textContent),
  ).toEqual([
    "Import",
    "Profile",
    "Runs",
    "Cluster",
    "Kandidaten",
    "Export",
    "Projekt löschen",
  ]);

  const sidebarProjectList = screen.getByLabelText("Projektliste");
  await user.click(
    within(sidebarProjectList).getByRole("button", { name: "Alpha" }),
  );
  expect(
    await screen.findByRole("heading", { name: "Alpha" }),
  ).toBeInTheDocument();
  expect(
    within(
      screen.getByRole("form", { name: "Projekt umbenennen" }),
    ).getByLabelText("Projektname"),
  ).toHaveValue("Alpha");

  await user.click(
    within(sidebarProjectList).getByRole("button", { name: "Beta" }),
  );
  expect(
    await screen.findByRole("heading", { name: "Beta" }),
  ).toBeInTheDocument();
  const renameForm = screen.getByRole("form", {
    name: "Projekt umbenennen",
  });
  const nameInput = within(renameForm).getByLabelText("Projektname");
  expect(nameInput).toHaveValue("Beta");
  await user.clear(nameInput);
  await user.type(nameInput, "Beta renamed");
  await user.click(
    within(renameForm).getByRole("button", { name: "Umbenennen" }),
  );
  expect(
    await screen.findByRole("heading", { name: "Beta renamed" }),
  ).toBeInTheDocument();
  expect(
    screen.getByText(
      `Status: active; zuletzt aktualisiert: ${formattedUpdatedAt}`,
    ),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("region", { name: "Bestehende Projekte" }),
  ).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Projekte" }));
  const reopenedProjectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  const reopenedBetaRow = getProjectRow(reopenedProjectList, "Beta renamed");
  reopenedBetaRow.focus();
  await user.keyboard(" ");
  expect(
    await screen.findByRole("heading", { name: "Beta renamed" }),
  ).toBeInTheDocument();
  await openProjectTab(user, "Projekt löschen");
  const deleteForm = screen.getByRole("form", { name: "Projekt löschen" });
  await user.type(
    within(deleteForm).getByLabelText("Projektname bestätigen"),
    "Beta renamed",
  );
  await user.click(
    within(deleteForm).getByRole("button", { name: "Projekt löschen" }),
  );
  await waitFor(() =>
    expect(screen.queryByText("Beta renamed")).not.toBeInTheDocument(),
  );
});

test("imports a selected CSV file and shows persisted log details", async () => {
  const user = userEvent.setup();
  let importPostCount = 0;
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
      importPostCount += 1;
      expect(new Headers(init?.headers).get("Authorization")).toBe(
        "Bearer api-token",
      );
      expect(new Headers(init?.headers).get("Content-Type")).toBe("text/csv");
      expect(new Headers(init?.headers).get("Content-Disposition")).toBe(
        "attachment; filename*=UTF-8''fixture.csv",
      );
      expect(init?.body).toBeInstanceOf(File);
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
              context: { ticket_id: "T-2" },
            },
          ],
          skipped_entries_truncated: false,
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
          context: { ticket_id: "T-2" },
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
  await user.click(getProjectRow(projectList, "Alpha"));

  const importForm = await screen.findByRole("form", {
    name: "Import starten",
  });
  expect(
    within(importForm).getByText(/Maximale Dateigröße: 512 MiB/),
  ).toBeVisible();
  const file = new window.File(
    ["ticket_id,message_group_id,message,answer\nT-1,G-1,Hi,A\n"],
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

  const oversizedFile = new window.File(["x"], "oversized.csv", {
    type: "text/csv",
  });
  Object.defineProperty(oversizedFile, "size", {
    value: 512 * 1024 * 1024 + 1,
  });
  await user.upload(
    within(importForm).getByLabelText("Importdatei"),
    oversizedFile,
  );
  await user.click(
    within(importForm).getByRole("button", { name: "Import starten" }),
  );
  expect(await screen.findByText(/Datei ist zu groß/)).toBeInTheDocument();
  expect(importPostCount).toBe(1);
});

test("configures providers and creates a project analysis profile", async () => {
  const user = userEvent.setup();
  let openAiSaveCount = 0;
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
      openAiSaveCount += 1;
      expect(new Headers(init?.headers).get("Authorization")).toBe(
        "Bearer api-token",
      );
      const body = JSON.parse(String(init?.body));
      if (openAiSaveCount === 1) {
        expect(body.api_key).toBe("sk-test-secret");
        expect(body.manual_models).toEqual([]);
        return jsonResponse(openAiProvider);
      }
      expect(body.api_key).toBeUndefined();
      expect(body.manual_models).toEqual(["text-embedding-3-small"]);
      return jsonResponse({
        ...openAiProvider,
        manual_models: ["text-embedding-3-small"],
      });
    }
    if (path === "/api/providers/openai/check" && method === "POST") {
      return jsonResponse({
        provider: "openai",
        ok: true,
        models: ["text-embedding-3-small"],
        message: "OpenAI embedding models discovered",
      });
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
      const body = JSON.parse(String(init?.body));
      expect(body).toMatchObject({
        name: "Local profile",
        provider: "vllm",
        model: "local-embed",
        thresholds: { similarity: 0.78 },
        algorithm_settings: {
          algorithm: "hdbscan",
          min_cluster_size: 5,
          cluster_selection_epsilon: 0,
        },
      });
      expect(body.prompt_identifier).toBeUndefined();
      expect(body.algorithm_settings.min_samples).toBeUndefined();
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
          ticket_id: "T-1",
          message_group_id: "G-1",
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
          ticket_id: "T-1",
          message_group_id: "G-1",
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
            "Export enthält Originaltext und damit potentiell identifizierende Inhalte.",
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
  await openSettingsTab(user, "Embedding-Provider");

  const openAiForm = await screen.findByRole("form", {
    name: "OpenAI Provider konfigurieren",
  });
  await user.type(
    within(openAiForm).getByLabelText("Neuer OpenAI API-Key"),
    "sk-test-secret",
  );
  await user.click(
    within(openAiForm).getByRole("button", { name: "OpenAI speichern" }),
  );

  expect(await screen.findByText("API-Key gesetzt")).toBeInTheDocument();
  expect(
    await within(openAiForm).findByLabelText("text-embedding-3-small"),
  ).toBeChecked();
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

  await user.click(screen.getByRole("button", { name: "Projekte" }));

  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));
  await openProjectTab(user, "Profile");

  const profileForm = await screen.findByRole("form", {
    name: "Analyseprofil erstellen",
  });
  expect(within(profileForm).getByLabelText("Profilname")).toHaveValue(
    "analysis-1",
  );
  await user.clear(within(profileForm).getByLabelText("Profilname"));
  await user.type(
    within(profileForm).getByLabelText("Profilname"),
    "Local profile",
  );
  expect(within(profileForm).getByLabelText("Modell")).toHaveValue(
    "local-embed",
  );
  await user.type(
    within(profileForm).getByLabelText("Similarity Threshold"),
    "0.78",
  );
  expect(within(profileForm).getByLabelText("Algorithmus")).toHaveValue(
    "hdbscan",
  );
  expect(
    within(profileForm).queryByLabelText("Prompt-ID"),
  ).not.toBeInTheDocument();
  await user.click(
    within(profileForm).getByRole("button", { name: "Profil speichern" }),
  );

  expect(await screen.findByText("Local profile")).toBeInTheDocument();
  expect(screen.getByText("vllm/local-embed")).toBeInTheDocument();
  expect(screen.getByText(/"similarity":0.78/)).toBeInTheDocument();

  await openProjectTab(user, "Runs");
  const runForm = await screen.findByRole("form", {
    name: "Analyse starten",
  });
  expect(within(runForm).queryByLabelText("Run-Modus")).not.toBeInTheDocument();
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

  await openProjectTab(user, "Cluster");
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
    within(clusterExplorer).getByText(/Auto: Cluster H \/ hdbscan/),
  ).toBeInTheDocument();
  expect(
    within(clusterExplorer).getByText(/Manual: - \/ - \/ -/),
  ).toBeInTheDocument();
  expect(
    within(clusterExplorer).getByText(/Effective: Cluster H \/ hdbscan/),
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
  await openProjectTab(user, "Kandidaten");

  const candidateEditor = await screen.findByRole("region", {
    name: "Candidate Editor",
  });
  expect(
    await within(candidateEditor).findByText("Cluster H"),
  ).toBeInTheDocument();
  expect(
    within(candidateEditor).getByText(
      /Auto: Cluster H \/ hdbscan \/ unreviewed/,
    ),
  ).toBeInTheDocument();
  expect(
    within(candidateEditor).getByText(/Manual: - \/ - \/ -/),
  ).toBeInTheDocument();
  expect(
    within(candidateEditor).getByText(
      /Effective: Cluster H \/ hdbscan \/ unreviewed/,
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
      "Externe Datenabhängigkeiten, eine pro Zeile",
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

  await openProjectTab(user, "Export");
  const candidateExportForm = await screen.findByRole("form", {
    name: "Candidate CSV exportieren",
  });
  await user.click(
    within(candidateExportForm).getByRole("button", {
      name: "Candidate CSV exportieren",
    }),
  );
  expect(
    await screen.findByText(/Export enthält Originaltext/),
  ).toBeInTheDocument();
  const warning = screen.getByRole("status");
  expect(warning).toHaveClass("feedback", "warning");
  expect(warning).toHaveTextContent("Warnung: Export enthält Originaltext");

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

test("disables meaningless cluster loads, explains empty results, and preserves safe API errors", async () => {
  const user = userEvent.setup();
  const safeBudgetDetail =
    "clustering working set estimate 749211264 bytes for 1000 records with 900 dimensions exceeds the 536870912-byte (512 MiB) limit; reduce the dataset size or embedding dimensions, or select HDBSCAN";
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
    if (path === "/api/projects/project-alpha/candidates" && method === "GET") {
      return jsonResponse([]);
    }
    if (path === "/api/projects/project-alpha/exports" && method === "GET") {
      return jsonResponse([]);
    }
    if (
      path === "/api/projects/project-alpha/analysis-runs" &&
      method === "GET"
    ) {
      return jsonResponse([analysisRun, completedAnalysisRun]);
    }
    if (
      path ===
        "/api/projects/project-alpha/analysis-runs/run-completed/clusters" &&
      method === "GET"
    ) {
      return jsonResponse([]);
    }
    if (
      path ===
        "/api/projects/project-alpha/analysis-runs/run-completed/clusters/generate" &&
      method === "POST"
    ) {
      return jsonResponse({ detail: safeBudgetDetail }, { status: 400 });
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
  render(<App />);

  await signIn(user);
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));
  await openProjectTab(user, "Cluster");

  const clusterActions = await screen.findByRole("region", {
    name: "Cluster Aktionen",
  });
  const queuedCard = within(clusterActions)
    .getByText("Run: run-1")
    .closest("article");
  const completedCard = within(clusterActions)
    .getByText("Run: run-completed")
    .closest("article");
  if (queuedCard === null || completedCard === null) {
    throw new Error("cluster action cards missing");
  }
  expect(
    within(queuedCard).getByRole("button", { name: "Cluster laden" }),
  ).toBeDisabled();
  const loadCompleted = within(completedCard).getByRole("button", {
    name: "Cluster laden",
  });
  expect(loadCompleted).toBeEnabled();

  await user.click(loadCompleted);

  const info = await screen.findByRole("status");
  expect(info).toHaveClass("feedback", "info");
  expect(info).toHaveTextContent(
    "Hinweis: Für diesen abgeschlossenen Run wurden noch keine Cluster erzeugt.",
  );
  expect(
    screen.getByText(
      "Für den ausgewählten abgeschlossenen Run wurden noch keine Cluster erzeugt. Bitte zuerst „Cluster erzeugen“ ausführen.",
    ),
  ).toBeInTheDocument();

  await user.click(
    within(completedCard).getByRole("button", {
      name: "Cluster erzeugen",
    }),
  );

  const error = await screen.findByRole("alert");
  expect(error).toHaveClass("feedback", "error");
  expect(error).toHaveTextContent(`Fehler: ${safeBudgetDetail}`);
  expect(
    within(completedCard).getByRole("button", {
      name: "Cluster erzeugen",
    }),
  ).toBeEnabled();
});

test("shows and guards cluster generation while the request is pending", async () => {
  const user = userEvent.setup();
  let generateRequests = 0;
  let resolveGeneration: (response: Response) => void = () => undefined;
  const pendingGeneration = new Promise<Response>((resolve) => {
    resolveGeneration = resolve;
  });
  mockProjectFetch((path, method) => {
    if (
      path === "/api/projects/project-alpha/analysis-runs" &&
      method === "GET"
    ) {
      return jsonResponse([completedAnalysisRun]);
    }
    if (
      path ===
        "/api/projects/project-alpha/analysis-runs/run-completed/clusters/generate" &&
      method === "POST"
    ) {
      generateRequests += 1;
      return pendingGeneration;
    }
    return undefined;
  });
  render(<App />);

  await signIn(user);
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));
  await openProjectTab(user, "Cluster");

  const clusterActions = await screen.findByRole("region", {
    name: "Cluster Aktionen",
  });
  const completedCard = within(clusterActions)
    .getByText("Run: run-completed")
    .closest("article");
  if (completedCard === null) {
    throw new Error("completed cluster action card missing");
  }

  await user.click(
    within(completedCard).getByRole("button", {
      name: "Cluster erzeugen",
    }),
  );

  const pendingButton = within(completedCard).getByRole("button", {
    name: "Cluster werden erzeugt",
  });
  expect(pendingButton).toBeDisabled();
  expect(within(completedCard).getByRole("status")).toHaveTextContent(
    "Clustererzeugung läuft für Run run-completed.",
  );
  expect(
    screen.getByText("Clustererzeugung für Run run-completed läuft."),
  ).toBeInTheDocument();
  fireEvent.click(pendingButton);
  expect(generateRequests).toBe(1);

  await act(async () => {
    resolveGeneration(jsonResponse([cluster]));
    await pendingGeneration;
  });

  expect(
    await screen.findByText("Cluster erzeugt und geladen."),
  ).toBeInTheDocument();
  expect(
    within(completedCard).getByRole("button", {
      name: "Cluster erzeugen",
    }),
  ).toBeEnabled();
  const clusterExplorer = screen.getByRole("region", {
    name: "Cluster Explorer",
  });
  expect(within(clusterExplorer).getByText("Cluster H")).toBeInTheDocument();
});

test("ignores delayed cluster generation after switching projects", async () => {
  const user = userEvent.setup();
  const betaRun = {
    ...completedAnalysisRun,
    id: "run-beta",
    project_id: "project-beta",
  };
  let resolveGeneration: (response: Response) => void = () => undefined;
  const pendingGeneration = new Promise<Response>((resolve) => {
    resolveGeneration = resolve;
  });
  mockProjectFetch((path, method) => {
    if (
      path === "/api/projects/project-alpha/analysis-runs" &&
      method === "GET"
    ) {
      return jsonResponse([completedAnalysisRun]);
    }
    if (
      path === "/api/projects/project-beta/analysis-runs" &&
      method === "GET"
    ) {
      return jsonResponse([betaRun]);
    }
    if (
      path ===
        "/api/projects/project-alpha/analysis-runs/run-completed/clusters/generate" &&
      method === "POST"
    ) {
      return pendingGeneration;
    }
    return undefined;
  });
  render(<App />);

  await signIn(user);
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));
  await openProjectTab(user, "Cluster");
  const clusterActions = await screen.findByRole("region", {
    name: "Cluster Aktionen",
  });
  await user.click(
    within(clusterActions).getByRole("button", {
      name: "Cluster erzeugen",
    }),
  );

  const navigation = screen.getByRole("navigation", {
    name: "Hauptnavigation",
  });
  await user.click(within(navigation).getByRole("button", { name: "Beta" }));
  await waitFor(() =>
    expect(screen.getByLabelText("Projektname")).toHaveValue("Beta"),
  );
  expect(screen.getByText("Projekt geöffnet.")).toBeInTheDocument();

  await act(async () => {
    resolveGeneration(jsonResponse([cluster]));
    await pendingGeneration;
  });

  expect(screen.getByText("Projekt geöffnet.")).toBeInTheDocument();
  expect(
    screen.queryByText("Cluster erzeugt und geladen."),
  ).not.toBeInTheDocument();
  await openProjectTab(user, "Cluster");
  const betaClusterExplorer = await screen.findByRole("region", {
    name: "Cluster Explorer",
  });
  expect(
    within(betaClusterExplorer).queryByText("Cluster H"),
  ).not.toBeInTheDocument();
});

test("restarts the feedback timeout when the same project error occurs again", async () => {
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
    if (path === "/api/projects" && method === "POST") {
      return jsonResponse(
        { detail: "project name already exists" },
        { status: 409 },
      );
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
  render(<App />);
  await signIn(user);
  await screen.findByRole("heading", { name: "Projekte & Analysen" });

  const createForm = screen.getByRole("form", { name: "Projekt erstellen" });
  await user.type(within(createForm).getByLabelText("Projektname"), "Alpha");
  const createButton = within(createForm).getByRole("button", {
    name: "Projekt erstellen",
  });
  vi.useFakeTimers();
  await act(async () => {
    fireEvent.click(createButton);
  });
  const firstAlert = screen.getByRole("alert");
  expect(firstAlert).toHaveClass("feedback", "error");
  expect(firstAlert).toHaveTextContent("Fehler: project name already exists");
  expect(firstAlert).not.toHaveTextContent("raw exception");

  await act(async () => {
    vi.advanceTimersByTime(3000);
  });
  await act(async () => {
    fireEvent.click(createButton);
  });
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Fehler: project name already exists",
  );

  await act(async () => {
    vi.advanceTimersByTime(600);
  });
  expect(screen.getByRole("alert")).toHaveTextContent(
    "project name already exists",
  );

  await act(async () => {
    vi.advanceTimersByTime(2899);
  });
  expect(screen.getByRole("alert")).toBeInTheDocument();

  await act(async () => {
    vi.advanceTimersByTime(1);
  });
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

test("renders safe error feedback for user, provider, import, profile, run, candidate, and export actions", async () => {
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
    if (path === "/api/users" && method === "POST") {
      return jsonResponse(
        { detail: "user email is already registered" },
        { status: 409 },
      );
    }
    if (path === "/api/projects" && method === "GET") {
      return jsonResponse([alphaProject]);
    }
    if (path === "/api/providers" && method === "GET") {
      return jsonResponse([vllmProvider]);
    }
    if (path === "/api/providers/vllm" && method === "PUT") {
      return jsonResponse(
        { detail: "provider endpoint is not reachable" },
        { status: 400 },
      );
    }
    if (path === "/api/projects/project-alpha" && method === "GET") {
      return jsonResponse(alphaProject);
    }
    if (path === "/api/projects/project-alpha/imports" && method === "GET") {
      return jsonResponse([importLog]);
    }
    if (path === "/api/projects/project-alpha/imports" && method === "POST") {
      return Promise.reject(new Error("raw import transport exception"));
    }
    if (
      path === "/api/projects/project-alpha/analysis-profiles" &&
      method === "GET"
    ) {
      return jsonResponse([analysisProfile]);
    }
    if (
      path === "/api/projects/project-alpha/analysis-profiles" &&
      method === "POST"
    ) {
      return jsonResponse(
        { detail: "analysis profile is invalid" },
        { status: 400 },
      );
    }
    if (
      path === "/api/projects/project-alpha/analysis-runs" &&
      method === "GET"
    ) {
      return jsonResponse([completedAnalysisRun]);
    }
    if (
      path === "/api/projects/project-alpha/analysis-runs" &&
      method === "POST"
    ) {
      return jsonResponse(
        { detail: "analysis run cannot be started" },
        { status: 409 },
      );
    }
    if (path === "/api/projects/project-alpha/candidates" && method === "GET") {
      return jsonResponse([candidate]);
    }
    if (
      path === "/api/projects/project-alpha/candidates/candidate-1" &&
      method === "PATCH"
    ) {
      return jsonResponse(
        { detail: "candidate update conflicts with current state" },
        { status: 409 },
      );
    }
    if (path === "/api/projects/project-alpha/exports" && method === "GET") {
      return jsonResponse([]);
    }
    if (
      path === "/api/projects/project-alpha/exports/candidates" &&
      method === "POST"
    ) {
      return jsonResponse(
        { detail: "candidate export cannot be created" },
        { status: 400 },
      );
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
  render(<App />);
  await signIn(user);

  await openSettingsTab(user, "Nutzer");
  const userForm = await screen.findByRole("form", { name: "User anlegen" });
  await user.type(within(userForm).getByLabelText("Name"), "Support Curator");
  await user.type(
    within(userForm).getByLabelText("E-Mail"),
    "curator@example.test",
  );
  await user.type(
    within(userForm).getByLabelText("Initiales Passwort"),
    "curator-password",
  );
  await user.click(
    within(userForm).getByRole("button", { name: "User erstellen" }),
  );
  await expectErrorFeedback(
    "user email is already registered",
    "raw exception",
  );

  await openSettingsTab(user, "Embedding-Provider");
  const providerForm = await screen.findByRole("form", {
    name: "vLLM Provider konfigurieren",
  });
  await user.click(
    within(providerForm).getByRole("button", { name: "vLLM speichern" }),
  );
  await expectErrorFeedback(
    "provider endpoint is not reachable",
    "raw exception",
  );

  await user.click(screen.getByRole("button", { name: "Projekte" }));
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));

  const importForm = await screen.findByRole("form", {
    name: "Import starten",
  });
  const file = new window.File(
    ["ticket_id,message_group_id,message,answer\nT-1,G-1,Hi,A\n"],
    "fixture.csv",
    { type: "text/csv" },
  );
  await user.upload(within(importForm).getByLabelText("Importdatei"), file);
  await user.click(
    within(importForm).getByRole("button", { name: "Import starten" }),
  );
  await expectErrorFeedback(
    "Import konnte nicht durchgeführt werden.",
    "raw import transport exception",
  );

  await openProjectTab(user, "Profile");
  const profileForm = await screen.findByRole("form", {
    name: "Analyseprofil erstellen",
  });
  await user.click(
    within(profileForm).getByRole("button", { name: "Profil speichern" }),
  );
  await expectErrorFeedback("analysis profile is invalid", "raw exception");

  await openProjectTab(user, "Runs");
  const runForm = await screen.findByRole("form", {
    name: "Analyse starten",
  });
  await user.click(
    within(runForm).getByRole("button", { name: "Analyse starten" }),
  );
  await expectErrorFeedback("analysis run cannot be started", "raw exception");

  await openProjectTab(user, "Kandidaten");
  const candidateEditor = await screen.findByRole("region", {
    name: "Candidate Editor",
  });
  await user.click(
    within(candidateEditor).getByRole("button", {
      name: "Candidate speichern",
    }),
  );
  await expectErrorFeedback(
    "candidate update conflicts with current state",
    "raw exception",
  );

  await openProjectTab(user, "Export");
  const exportForm = await screen.findByRole("form", {
    name: "Candidate CSV exportieren",
  });
  await user.click(
    within(exportForm).getByRole("button", {
      name: "Candidate CSV exportieren",
    }),
  );
  await expectErrorFeedback(
    "candidate export cannot be created",
    "raw exception",
  );
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
  await user.click(getProjectRow(projectList, "Alpha"));
  await openProjectTab(user, "Kandidaten");

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
      /Externe Datenabhängigkeiten Auto: identity-service/,
    ),
  ).toBeInTheDocument();
  expect(
    within(candidateEditor).getByText(/Externe Datenabhängigkeiten Manual: -/),
  ).toBeInTheDocument();
  expect(
    within(candidateEditor).getByText(
      /Externe Datenabhängigkeiten Effective: identity-service/,
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

test("suggests project-local profile names and sends only selected model and algorithm fields", async () => {
  const user = userEvent.setup();
  const alphaProfiles = [
    { ...analysisProfile, id: "profile-analysis-1", name: "analysis-1" },
    { ...analysisProfile, id: "profile-analysis-7", name: "analysis-7" },
    {
      ...analysisProfile,
      id: "profile-historical",
      name: "manuell",
      algorithm_settings: { algorithm: "historical-legacy" },
    },
  ];
  const betaProfiles = [
    {
      ...analysisProfile,
      id: "profile-beta-2",
      project_id: "project-beta",
      name: "analysis-2",
    },
  ];
  let createdBody: Record<string, unknown> | null = null;
  let profileRequests = 0;
  const runProfileIds: string[] = [];
  let resolveBetaProject: (response: Response) => void = () => undefined;
  const pendingBetaProject = new Promise<Response>((resolve) => {
    resolveBetaProject = resolve;
  });
  let resolveBetaProfiles: (response: Response) => void = () => undefined;
  const pendingBetaProfiles = new Promise<Response>((resolve) => {
    resolveBetaProfiles = resolve;
  });

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
      return jsonResponse([alphaProject, betaProject]);
    }
    if (path === "/api/providers" && method === "GET") {
      return jsonResponse([
        { ...vllmProvider, manual_models: [] },
        { ...ollamaProvider, manual_models: ["embed-a", "embed-b"] },
        openAiProvider,
      ]);
    }
    if (path === "/api/projects/project-alpha" && method === "GET") {
      return jsonResponse(alphaProject);
    }
    if (path === "/api/projects/project-beta" && method === "GET") {
      return pendingBetaProject;
    }
    if (
      path === "/api/projects/project-alpha/analysis-profiles" &&
      method === "GET"
    ) {
      return jsonResponse(alphaProfiles);
    }
    if (
      path === "/api/projects/project-beta/analysis-profiles" &&
      method === "GET"
    ) {
      return pendingBetaProfiles;
    }
    if (
      path === "/api/projects/project-alpha/analysis-profiles" &&
      method === "POST"
    ) {
      profileRequests += 1;
      createdBody = JSON.parse(String(init?.body));
      return jsonResponse(
        {
          ...analysisProfile,
          id: "profile-analysis-8",
          name: "analysis-8",
          provider: "ollama",
          model: "embed-a",
          algorithm_settings: {
            algorithm: "agglomerative",
            distance_threshold: 0.4,
            linkage: "average",
          },
        },
        { status: 201 },
      );
    }
    if (path === "/api/projects/project-alpha/imports" && method === "GET") {
      return jsonResponse([importLog]);
    }
    if (path === "/api/projects/project-beta/imports" && method === "GET") {
      return jsonResponse([]);
    }
    if (
      path === "/api/projects/project-alpha/analysis-runs" &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      runProfileIds.push(String(body.analysis_profile_id));
      return jsonResponse(
        {
          ...analysisRun,
          analysis_profile_id: body.analysis_profile_id,
          parameters: body.parameters,
        },
        { status: 201 },
      );
    }
    if (
      /^\/api\/projects\/project-(alpha|beta)\/analysis-runs$/.test(path) &&
      method === "GET"
    ) {
      return jsonResponse([]);
    }
    if (
      /^\/api\/projects\/project-(alpha|beta)\/candidates$/.test(path) &&
      method === "GET"
    ) {
      return jsonResponse([]);
    }
    if (
      /^\/api\/projects\/project-(alpha|beta)\/exports$/.test(path) &&
      method === "GET"
    ) {
      return jsonResponse([]);
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
  render(<App />);

  await signIn(user);
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));
  await openProjectTab(user, "Profile");

  const profileForm = await screen.findByRole("form", {
    name: "Analyseprofil erstellen",
  });
  await waitFor(() =>
    expect(within(profileForm).getByLabelText("Profilname")).toHaveValue(
      "analysis-8",
    ),
  );
  expect(
    within(profileForm).getByText(/noch kein Modell konfiguriert/i),
  ).toBeInTheDocument();
  expect(
    within(profileForm).getByRole("button", { name: "Profil speichern" }),
  ).toBeDisabled();
  expect(screen.getByText(/historical-legacy/)).toBeInTheDocument();

  await user.selectOptions(
    within(profileForm).getByLabelText("Provider"),
    "ollama",
  );
  const modelSelect = within(profileForm).getByLabelText("Modell");
  await waitFor(() => expect(modelSelect).toHaveValue("embed-a"));
  expect(
    within(modelSelect)
      .getAllByRole("option")
      .map((option) => option.textContent),
  ).toEqual(["embed-a", "embed-b"]);
  expect(
    within(profileForm).getByLabelText("Minimale Clustergröße"),
  ).toBeInTheDocument();
  expect(
    within(profileForm).queryByLabelText("Anzahl Cluster"),
  ).not.toBeInTheDocument();

  await user.selectOptions(
    within(profileForm).getByLabelText("Algorithmus"),
    "agglomerative",
  );
  expect(
    within(profileForm).queryByLabelText("Minimale Clustergröße"),
  ).not.toBeInTheDocument();
  expect(
    within(profileForm).getByLabelText("Anzahl Cluster"),
  ).toBeInTheDocument();
  await user.selectOptions(
    within(profileForm).getByLabelText("Abbruchkriterium"),
    "distance_threshold",
  );
  await user.type(within(profileForm).getByLabelText("Distanzschwelle"), "0.4");
  await user.selectOptions(
    within(profileForm).getByLabelText("Linkage"),
    "average",
  );
  await user.click(
    within(profileForm).getByRole("button", { name: "Profil speichern" }),
  );

  expect(createdBody).toMatchObject({
    name: "analysis-8",
    provider: "ollama",
    model: "embed-a",
    algorithm_settings: {
      algorithm: "agglomerative",
      distance_threshold: 0.4,
      linkage: "average",
    },
  });
  const submittedAlgorithmSettings = (
    createdBody as unknown as {
      algorithm_settings: Record<string, unknown>;
    }
  ).algorithm_settings;
  expect(submittedAlgorithmSettings.n_clusters).toBeUndefined();
  expect(submittedAlgorithmSettings.min_cluster_size).toBeUndefined();
  await waitFor(() =>
    expect(within(profileForm).getByLabelText("Profilname")).toHaveValue(
      "analysis-9",
    ),
  );

  await openProjectTab(user, "Runs");
  const formerAlphaRunForm = await screen.findByRole("form", {
    name: "Analyse starten",
  });
  await openProjectTab(user, "Profile");
  const formerAlphaProfileForm = await screen.findByRole("form", {
    name: "Analyseprofil erstellen",
  });
  const navigation = screen.getByRole("navigation", {
    name: "Hauptnavigation",
  });
  await user.click(
    within(navigation).getByRole("button", {
      name: "Beta",
    }),
  );
  expect(
    screen.queryByRole("region", { name: "Aktuelles Projekt" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("form", { name: "Analyseprofil erstellen" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("form", { name: "Analyse starten" }),
  ).not.toBeInTheDocument();
  fireEvent.submit(formerAlphaProfileForm);
  fireEvent.submit(formerAlphaRunForm);
  expect(profileRequests).toBe(1);
  expect(runProfileIds).toEqual([]);

  resolveBetaProject(jsonResponse(betaProject));
  await waitFor(() =>
    expect(screen.getByLabelText("Projektname")).toHaveValue("Beta"),
  );
  await openProjectTab(user, "Profile");
  expect(
    await screen.findByRole("status", {
      name: "Analyseprofile werden geladen",
    }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("form", { name: "Analyseprofil erstellen" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByDisplayValue("analysis-9")).not.toBeInTheDocument();
  expect(screen.queryByText(/historical-legacy/)).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Profil speichern" }),
  ).not.toBeInTheDocument();

  await user.click(
    within(navigation).getByRole("button", {
      name: "Alpha",
    }),
  );
  await waitFor(() =>
    expect(screen.getByLabelText("Projektname")).toHaveValue("Alpha"),
  );
  await openProjectTab(user, "Profile");
  const alphaProfileForm = await screen.findByRole("form", {
    name: "Analyseprofil erstellen",
  });
  await waitFor(() =>
    expect(within(alphaProfileForm).getByLabelText("Profilname")).toHaveValue(
      "analysis-8",
    ),
  );

  resolveBetaProfiles(jsonResponse(betaProfiles));
  await waitFor(() => {
    expect(screen.getByLabelText("Projektname")).toHaveValue("Alpha");
    expect(screen.queryByText("analysis-2")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("status", {
        name: "Analyseprofile werden geladen",
      }),
    ).not.toBeInTheDocument();
  });

  await openProjectTab(user, "Runs");
  const runForm = await screen.findByRole("form", {
    name: "Analyse starten",
  });
  const runProfileSelect = within(runForm).getByLabelText("Analyseprofil");
  expect(
    within(runProfileSelect).queryByRole("option", {
      name: /analysis-2/,
    }),
  ).not.toBeInTheDocument();
  expect(runProfileSelect).toHaveValue("profile-analysis-1");
  await user.click(
    within(runForm).getByRole("button", { name: "Analyse starten" }),
  );
  await waitFor(() => expect(runProfileIds).toEqual(["profile-analysis-1"]));
});

test("requires explicit OpenAI confirmation immediately before starting a run", async () => {
  const user = userEvent.setup();
  const localProfile = {
    ...analysisProfile,
    id: "profile-local",
    name: "Local",
  };
  const cloudProfile = {
    ...analysisProfile,
    id: "profile-cloud",
    name: "Cloud",
    provider: "openai",
    model: "gpt-4.1-mini",
    is_cloud_provider: true,
  };
  let runRequests = 0;

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
      return jsonResponse([vllmProvider, openAiProvider]);
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
      return jsonResponse([localProfile, cloudProfile]);
    }
    if (
      path === "/api/projects/project-alpha/analysis-runs" &&
      method === "GET"
    ) {
      return jsonResponse([]);
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
      runRequests += 1;
      const body = JSON.parse(String(init?.body));
      expect(body.analysis_profile_id).toBe("profile-cloud");
      expect(body.parameters.cloud_use_confirmed).toBe(true);
      return jsonResponse(
        {
          ...analysisRun,
          analysis_profile_id: "profile-cloud",
          profile_snapshot: {
            name: "Cloud",
            provider: "openai",
            model: "gpt-4.1-mini",
          },
          provider: "openai",
          model: "gpt-4.1-mini",
          parameters: body.parameters,
        },
        { status: 201 },
      );
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
  render(<App />);

  await signIn(user);
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));
  await openProjectTab(user, "Runs");

  const runForm = await screen.findByRole("form", {
    name: "Analyse starten",
  });
  const profileSelect = within(runForm).getByLabelText("Analyseprofil");
  expect(
    within(runForm).queryByLabelText(/Ich bestätige/),
  ).not.toBeInTheDocument();
  await user.selectOptions(profileSelect, "profile-cloud");
  const confirmation = within(runForm).getByLabelText(/Ich bestätige/);
  const startButton = within(runForm).getByRole("button", {
    name: "Analyse starten",
  });
  expect(startButton).toBeDisabled();
  expect(runRequests).toBe(0);

  await user.click(confirmation);
  expect(startButton).toBeEnabled();
  await user.click(startButton);

  await waitFor(() => expect(runRequests).toBe(1));
  expect(confirmation).not.toBeChecked();
});

test("opens a project without an eager run request and gives the Runs view sole request ownership", async () => {
  const user = userEvent.setup();
  let runRequests = 0;
  let activeRequests = 0;
  let maximumActiveRequests = 0;
  let completeRequest: (response: Response) => void = () => undefined;
  mockProjectFetch((path, method, init) => {
    if (
      path === "/api/projects/project-alpha/analysis-runs" &&
      method === "GET"
    ) {
      runRequests += 1;
      activeRequests += 1;
      maximumActiveRequests = Math.max(maximumActiveRequests, activeRequests);
      const signal = init?.signal;
      expect(signal).toBeInstanceOf(AbortSignal);
      return new Promise<Response>((resolve, reject) => {
        let settled = false;
        signal?.addEventListener(
          "abort",
          () => {
            if (!settled) {
              settled = true;
              activeRequests -= 1;
              reject(new DOMException("Aborted", "AbortError"));
            }
          },
          { once: true },
        );
        completeRequest = (response) => {
          if (!settled) {
            settled = true;
            activeRequests -= 1;
            resolve(response);
          }
        };
      });
    }
    return undefined;
  });
  render(<App />);

  await signIn(user);
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));
  await waitFor(() =>
    expect(screen.getByLabelText("Projektname")).toHaveValue("Alpha"),
  );
  expect(runRequests).toBe(0);

  await openProjectTab(user, "Runs");
  await waitFor(() => expect(runRequests).toBe(1));
  expect(activeRequests).toBe(1);
  expect(maximumActiveRequests).toBe(1);

  completeRequest(jsonResponse([completedAnalysisRun]));
  const runsRegion = await screen.findByRole("region", {
    name: "Analyse Runs",
  });
  expect(await within(runsRegion).findByText("completed")).toBeInTheDocument();
  expect(activeRequests).toBe(0);
});

test("aborts a hidden in-flight poll before refreshing immediately on return", async () => {
  const user = userEvent.setup();
  let visibilityState: DocumentVisibilityState = "visible";
  vi.spyOn(document, "visibilityState", "get").mockImplementation(
    () => visibilityState,
  );
  let runRequests = 0;
  let activeRequests = 0;
  let maximumActiveRequests = 0;
  const completeRequests: Array<(response: Response) => void> = [];
  mockProjectFetch((path, method, init) => {
    if (
      path === "/api/projects/project-alpha/analysis-runs" &&
      method === "GET"
    ) {
      runRequests += 1;
      activeRequests += 1;
      maximumActiveRequests = Math.max(maximumActiveRequests, activeRequests);
      const signal = init?.signal;
      expect(signal).toBeInstanceOf(AbortSignal);
      return new Promise<Response>((resolve, reject) => {
        let settled = false;
        signal?.addEventListener(
          "abort",
          () => {
            if (!settled) {
              settled = true;
              activeRequests -= 1;
              reject(new DOMException("Aborted", "AbortError"));
            }
          },
          { once: true },
        );
        completeRequests.push((response) => {
          if (!settled) {
            settled = true;
            activeRequests -= 1;
            resolve(response);
          }
        });
      });
    }
    return undefined;
  });
  render(<App />);

  await signIn(user);
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));
  expect(runRequests).toBe(0);
  await openProjectTab(user, "Runs");
  await waitFor(() => expect(runRequests).toBe(1));
  expect(activeRequests).toBe(1);

  visibilityState = "hidden";
  document.dispatchEvent(new Event("visibilitychange"));
  await waitFor(() => expect(activeRequests).toBe(0));

  visibilityState = "visible";
  document.dispatchEvent(new Event("visibilitychange"));
  await waitFor(() => expect(runRequests).toBe(2));
  expect(activeRequests).toBe(1);
  expect(maximumActiveRequests).toBe(1);

  completeRequests[1]?.(jsonResponse([completedAnalysisRun]));
  const runsRegion = await screen.findByRole("region", {
    name: "Analyse Runs",
  });
  expect(await within(runsRegion).findByText("completed")).toBeInTheDocument();
  expect(activeRequests).toBe(0);
});

test("polls visible runs immediately and every two seconds without overlap and recovers after failure", async () => {
  const user = userEvent.setup();
  const runningRun = {
    ...analysisRun,
    status: "running",
    progress: 40,
    diagnostics: { embedded_messages: 4 },
    started_at: "2026-07-22T00:00:02Z",
    updated_at: "2026-07-22T00:00:03Z",
  };
  const completedRun = {
    ...completedAnalysisRun,
    error_message: null,
    diagnostics: { embeddings_written: 2, clusters_written: 1 },
    updated_at: "2026-07-22T00:00:06Z",
  };
  const laterRunningRun = {
    ...runningRun,
    progress: 70,
    diagnostics: { embedded_messages: 8 },
    updated_at: "2026-07-22T00:00:05Z",
  };
  let runRequests = 0;
  let rejectPendingPoll: (reason?: unknown) => void = () => undefined;
  const pendingPoll = new Promise<Response>((_resolve, reject) => {
    rejectPendingPoll = reject;
  });
  mockProjectFetch((path, method) => {
    if (
      path === "/api/projects/project-alpha/analysis-runs" &&
      method === "GET"
    ) {
      runRequests += 1;
      if (runRequests === 1) {
        return jsonResponse([runningRun]);
      }
      if (runRequests === 2) {
        return pendingPoll;
      }
      if (runRequests === 3) {
        return jsonResponse([laterRunningRun]);
      }
      return jsonResponse([completedRun]);
    }
    return undefined;
  });
  render(<App />);

  await signIn(user);
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));
  await openProjectTab(user, "Runs");

  const runsRegion = await screen.findByRole("region", {
    name: "Analyse Runs",
  });
  expect(await within(runsRegion).findByText("running")).toBeInTheDocument();
  expect(within(runsRegion).getByText("40%")).toBeInTheDocument();
  expect(
    within(runsRegion).getByText('Diagnose: {"embedded_messages":4}'),
  ).toBeInTheDocument();
  expect(runRequests).toBe(1);

  await waitFor(() => expect(runRequests).toBe(2), { timeout: 3000 });
  await new Promise((resolve) => window.setTimeout(resolve, 2100));
  expect(runRequests).toBe(2);
  expect(within(runsRegion).getByText("running")).toBeInTheDocument();

  rejectPendingPoll(new Error("temporary backend failure"));
  await pendingPoll.catch(() => undefined);

  expect(
    await within(runsRegion).findByText("70%", undefined, {
      timeout: 3000,
    }),
  ).toBeInTheDocument();
  expect(
    await within(runsRegion).findByText("completed", undefined, {
      timeout: 3000,
    }),
  ).toBeInTheDocument();
  expect(within(runsRegion).getByText("100%")).toBeInTheDocument();
  expect(
    within(runsRegion).getByText(
      'Diagnose: {"embeddings_written":2,"clusters_written":1}',
    ),
  ).toBeInTheDocument();
  expect(runRequests).toBe(4);
}, 15000);

test("pauses run polling while hidden or outside the Runs tab and refreshes immediately when visible", async () => {
  const user = userEvent.setup();
  let visibilityState: DocumentVisibilityState = "visible";
  vi.spyOn(document, "visibilityState", "get").mockImplementation(
    () => visibilityState,
  );
  let runRequests = 0;
  mockProjectFetch((path, method) => {
    if (
      path === "/api/projects/project-alpha/analysis-runs" &&
      method === "GET"
    ) {
      runRequests += 1;
      return jsonResponse([
        runRequests < 2
          ? { ...analysisRun, status: "running", progress: 20 }
          : completedAnalysisRun,
      ]);
    }
    return undefined;
  });
  render(<App />);

  await signIn(user);
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));
  await openProjectTab(user, "Runs");
  const runsRegion = await screen.findByRole("region", {
    name: "Analyse Runs",
  });
  expect(await within(runsRegion).findByText("running")).toBeInTheDocument();
  expect(runRequests).toBe(1);

  visibilityState = "hidden";
  document.dispatchEvent(new Event("visibilitychange"));
  await new Promise((resolve) => window.setTimeout(resolve, 2100));
  expect(runRequests).toBe(1);

  visibilityState = "visible";
  document.dispatchEvent(new Event("visibilitychange"));
  expect(await within(runsRegion).findByText("completed")).toBeInTheDocument();
  expect(runRequests).toBe(2);

  await openProjectTab(user, "Profile");
  await new Promise((resolve) => window.setTimeout(resolve, 2100));
  expect(runRequests).toBe(2);
}, 10000);

test("ignores a delayed poll from a previously opened project", async () => {
  const user = userEvent.setup();
  const betaRun = {
    ...completedAnalysisRun,
    id: "run-beta",
    project_id: "project-beta",
    diagnostics: { project: "beta" },
  };
  let alphaRunRequests = 0;
  let resolveAlphaPoll: (response: Response) => void = () => undefined;
  const pendingAlphaPoll = new Promise<Response>((resolve) => {
    resolveAlphaPoll = resolve;
  });
  mockProjectFetch((path, method) => {
    if (
      path === "/api/projects/project-alpha/analysis-runs" &&
      method === "GET"
    ) {
      alphaRunRequests += 1;
      return pendingAlphaPoll;
    }
    if (
      path === "/api/projects/project-beta/analysis-runs" &&
      method === "GET"
    ) {
      return jsonResponse([betaRun]);
    }
    return undefined;
  });
  render(<App />);

  await signIn(user);
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));
  await openProjectTab(user, "Runs");
  await waitFor(() => expect(alphaRunRequests).toBe(1));

  const navigation = screen.getByRole("navigation", {
    name: "Hauptnavigation",
  });
  await user.click(within(navigation).getByRole("button", { name: "Beta" }));
  await waitFor(() =>
    expect(screen.getByLabelText("Projektname")).toHaveValue("Beta"),
  );
  resolveAlphaPoll(
    jsonResponse([
      { ...analysisRun, status: "failed", error_message: "stale" },
    ]),
  );
  await pendingAlphaPoll;
  await openProjectTab(user, "Runs");

  const runsRegion = await screen.findByRole("region", {
    name: "Analyse Runs",
  });
  expect(await within(runsRegion).findByText("completed")).toBeInTheDocument();
  expect(within(runsRegion).getByText(/"project":"beta"/)).toBeInTheDocument();
  expect(within(runsRegion).queryByText("failed")).not.toBeInTheDocument();
  expect(within(runsRegion).queryByText("stale")).not.toBeInTheDocument();
});

test("ignores a delayed poll after logout", async () => {
  const user = userEvent.setup();
  let runRequests = 0;
  let resolvePoll: (response: Response) => void = () => undefined;
  const pendingPoll = new Promise<Response>((resolve) => {
    resolvePoll = resolve;
  });
  mockProjectFetch((path, method) => {
    if (
      path === "/api/projects/project-alpha/analysis-runs" &&
      method === "GET"
    ) {
      runRequests += 1;
      return pendingPoll;
    }
    return undefined;
  });
  render(<App />);

  await signIn(user);
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));
  await openProjectTab(user, "Runs");
  await waitFor(() => expect(runRequests).toBe(1));

  await user.click(screen.getByRole("button", { name: "Abmelden" }));
  resolvePoll(
    jsonResponse([
      { ...analysisRun, status: "failed", error_message: "stale" },
    ]),
  );
  await pendingPoll;

  expect(
    await screen.findByRole("heading", { name: "Lokaler Zugriff" }),
  ).toBeInTheDocument();
  expect(screen.queryByText("failed")).not.toBeInTheDocument();
  expect(screen.queryByText("stale")).not.toBeInTheDocument();
});

test("stops polling and ignores an in-flight response after unmount", async () => {
  const user = userEvent.setup();
  let runRequests = 0;
  let resolvePoll: (response: Response) => void = () => undefined;
  const pendingPoll = new Promise<Response>((resolve) => {
    resolvePoll = resolve;
  });
  mockProjectFetch((path, method) => {
    if (
      path === "/api/projects/project-alpha/analysis-runs" &&
      method === "GET"
    ) {
      runRequests += 1;
      return pendingPoll;
    }
    return undefined;
  });
  const rendered = render(<App />);

  await signIn(user);
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));
  await openProjectTab(user, "Runs");
  await waitFor(() => expect(runRequests).toBe(1));

  rendered.unmount();
  vi.useFakeTimers();
  resolvePoll(jsonResponse([completedAnalysisRun]));
  await pendingPoll;
  await vi.advanceTimersByTimeAsync(3000);

  expect(runRequests).toBe(1);
});

test("returns to signed-out state when run polling establishes an invalid session", async () => {
  const user = userEvent.setup();
  let runRequests = 0;
  mockProjectFetch((path, method) => {
    if (
      path === "/api/projects/project-alpha/analysis-runs" &&
      method === "GET"
    ) {
      runRequests += 1;
      return jsonResponse(
        { detail: "authentication required" },
        { status: 401 },
      );
    }
    return undefined;
  });
  render(<App />);

  await signIn(user);
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));
  await openProjectTab(user, "Runs");

  expect(
    await screen.findByRole("heading", { name: "Lokaler Zugriff" }),
  ).toBeInTheDocument();
  expect(window.sessionStorage.getItem(sessionTokenStorageKey)).toBeNull();
  expect(runRequests).toBe(1);
});
