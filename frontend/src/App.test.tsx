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

type ApiActiveJobs = {
  indexing_active: boolean;
  cluster_set_active: boolean;
};

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
  skipped_detail_count: 1,
  dataset_version_id: "dataset-1",
  dataset_display_name: "Fixture dataset",
  dataset_deleted_at: null,
  started_at: "2026-07-22T00:00:00Z",
  completed_at: "2026-07-22T00:00:00Z",
};
const openAiProvider = {
  id: "provider-openai",
  provider: "openai",
  display_name: "OpenAI",
  endpoint_url: null,
  available_models: ["text-embedding-3-small", "gpt-4.1-mini"],
  manual_models: ["text-embedding-3-small"],
  llm_models: ["gpt-4.1-mini"],
  api_key_set: true,
  updated_at: "2026-07-22T00:00:00Z",
};
const localOllamaProvider = {
  id: "provider-local-ollama",
  provider: "ollama",
  display_name: "Lokales Ollama",
  endpoint_url: "http://localhost:11434",
  available_models: ["local-embed"],
  manual_models: ["local-embed"],
  llm_models: [],
  api_key_set: false,
  updated_at: "2026-07-22T00:00:00Z",
};
const ollamaProvider = {
  id: "provider-ollama",
  provider: "ollama",
  display_name: "Ollama",
  endpoint_url: "http://localhost:11434",
  available_models: ["nomic-embed-text", "llama3.1"],
  manual_models: ["nomic-embed-text"],
  llm_models: ["llama3.1"],
  api_key_set: false,
  updated_at: "2026-07-22T00:00:00Z",
};
const analysisRun = {
  id: "run-1",
  project_id: "project-alpha",
  dataset_version_id: "dataset-1",
  dataset_display_name: "Fixture dataset",
  dataset_deleted_at: null,
  status: "queued",
  progress: 0,
  phase: "queued",
  provider: "ollama",
  provider_configuration_id: "provider-local-ollama",
  provider_display_name: "Lokales Ollama",
  model: "local-embed",
  parameters: {},
  error_code: null,
  error_message: null,
  diagnostics: {},
  started_at: null,
  completed_at: null,
  cancel_requested_at: null,
  deleted_at: null,
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
  cluster_set_id: "cluster-set-1",
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
  metadata: { non_quadratic: true, qa_mismatch: { maximum: 0.44 } },
  auto_summary_question: "How do I reset it?",
  auto_summary_answer: "Use the reset link.",
  created_at: "2026-07-22T00:00:00Z",
  updated_at: "2026-07-22T00:00:00Z",
};
const clusterSet = {
  id: "cluster-set-1",
  project_id: "project-alpha",
  indexing_run_id: "run-completed",
  dataset_version_id: "dataset-1",
  dataset_display_name: "Fixture dataset",
  indexing_deleted_at: null,
  parent_cluster_set_id: null,
  display_name: "Antworten fein",
  status: "queued",
  progress: 0,
  phase: "queued",
  derivation_type: "root",
  vector_basis: "combined",
  message_weight: 0.4,
  answer_weight: 0.6,
  algorithm: "hdbscan",
  parameters: {
    min_cluster_size: 2,
    min_samples: 12,
    cluster_selection_epsilon: 0.1,
    reduction_method: "pca",
    reduction_dimensions: 100,
    execution_backend: "auto",
    umap_n_neighbors: null,
    umap_min_dist: null,
    outlier_threshold: 0.72,
  },
  source_snapshot: { type: "all_dataset_pairs", source_pair_count: 1 },
  llm_provider: "ollama",
  llm_provider_configuration_id: "provider-ollama",
  llm_provider_display_name: "Ollama",
  llm_model: "llama3.1",
  llm_parameters: { enabled: true },
  llm_sample_strategy: { strategy: "random", requested: 2, seed: 7 },
  error_code: null,
  error_message: null,
  diagnostics: {},
  started_at: null,
  completed_at: null,
  cancel_requested_at: null,
  deleted_at: null,
  created_at: "2026-07-22T00:00:00Z",
  updated_at: "2026-07-22T00:00:00Z",
  cluster_count: 0,
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
const explorerExportLog = {
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
  row_count: 1,
  created_at: "2026-07-23T00:00:00Z",
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
  activeJobStatus: ApiActiveJobs = {
    indexing_active: false,
    cluster_set_active: false,
  },
) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? "GET";
      if (path === "/api/jobs/active" && method === "GET") {
        return jsonResponse(activeJobStatus);
      }
      return handler(input, init);
    });
}

function mockProjectFetch(
  override: (
    path: string,
    method: string,
    init?: RequestInit,
  ) => Response | Promise<Response> | undefined,
  activeJobStatus?: ApiActiveJobs,
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
      return jsonResponse([localOllamaProvider]);
    }
    if (path === "/api/jobs/active" && method === "GET") {
      return jsonResponse({
        indexing_active: false,
        cluster_set_active: false,
      });
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
    if (path.endsWith("/exports") && method === "GET") {
      return jsonResponse([]);
    }
    throw new Error(`unexpected request ${method} ${path}`);
  }, activeJobStatus);
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

async function openGlobalMenu(user: ReturnType<typeof userEvent.setup>) {
  const menuButton = screen.getByRole("button", {
    name: "Hauptmenü öffnen",
  });
  await user.click(menuButton);
  expect(menuButton).toHaveAttribute("aria-haspopup", "menu");
  expect(menuButton).toHaveAttribute("aria-expanded", "true");
  return {
    menuButton,
    menu: await screen.findByRole("menu"),
  };
}

async function signOutThroughGlobalMenu(
  user: ReturnType<typeof userEvent.setup>,
) {
  const { menu } = await openGlobalMenu(user);
  await user.click(within(menu).getByRole("menuitem", { name: "Abmelden" }));
}

async function openProjectsPage(user: ReturnType<typeof userEvent.setup>) {
  const { menu } = await openGlobalMenu(user);
  await user.click(within(menu).getByRole("menuitem", { name: "Projekte" }));
}

async function openSettingsTab(
  user: ReturnType<typeof userEvent.setup>,
  tabName: "Provider" | "Nutzer",
) {
  const { menu } = await openGlobalMenu(user);
  await user.click(
    within(menu).getByRole("menuitem", { name: "Einstellungen" }),
  );
  await user.click(await screen.findByRole("tab", { name: tabName }));
}

async function openProjectTab(
  user: ReturnType<typeof userEvent.setup>,
  tabName:
    "Import" | "Indizieren" | "Cluster-Sets" | "Explorer" | "Projekt löschen",
) {
  await user.click(await screen.findByRole("tab", { name: tabName }));
}

function getProjectRow(projectList: HTMLElement, projectName: string) {
  const escapedProjectName = projectName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return within(projectList).getByRole("button", {
    name: new RegExp(`^${escapedProjectName}`),
  });
}

async function expectErrorFeedback(text: string, rawText?: string) {
  await waitFor(() => {
    const alert = screen
      .getAllByRole("alert")
      .find((candidate) => candidate.textContent?.includes(`Fehler: ${text}`));
    expect(alert).toBeDefined();
    if (alert === undefined) {
      throw new Error("error feedback alert missing");
    }
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
    if (path === "/api/jobs/active" && method === "GET") {
      return jsonResponse({
        indexing_active: false,
        cluster_set_active: false,
      });
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

  await signOutThroughGlobalMenu(user);

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

  await signOutThroughGlobalMenu(user);

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

test("uses only the topbar global menu after sign-in", async () => {
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

  expect(
    screen.queryByRole("navigation", { name: "Hauptnavigation" }),
  ).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Projektliste")).not.toBeInTheDocument();
  const { menu, menuButton } = await openGlobalMenu(user);
  expect(
    within(menu).getByRole("menuitem", { name: "Projekte" }),
  ).toBeInTheDocument();
  expect(
    within(menu).getByRole("menuitem", { name: "Einstellungen" }),
  ).toBeInTheDocument();
  expect(
    within(menu).getByRole("menuitem", { name: "Abmelden" }),
  ).toBeInTheDocument();
  fireEvent.keyDown(window, { key: "Escape" });
  await waitFor(() =>
    expect(screen.queryByRole("menu")).not.toBeInTheDocument(),
  );
  expect(menuButton).toHaveFocus();
  expect(menuButton).toHaveAttribute("aria-expanded", "false");

  await openSettingsTab(user, "Provider");
  expect(screen.getByRole("tab", { name: "Provider" })).toHaveClass("selected");
  expect(
    screen.queryByRole("tab", { name: "LLM-Provider" }),
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole("tab", { name: "Nutzer" }));
  expect(screen.getByRole("tab", { name: "Nutzer" })).toHaveClass("selected");
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
    if (path === "/api/providers/provider-openai/check" && method === "POST") {
      openAiCheckCount += 1;
      expect(new Headers(init?.headers).get("Authorization")).toBe(
        "Bearer api-token",
      );
      return jsonResponse({
        id: "provider-openai",
        provider: "openai",
        ok: true,
        models: ["text-embedding-3-large", "gpt-4.1-mini"],
        embedding_models: ["text-embedding-3-large"],
        llm_models: ["gpt-4.1-mini"],
        message: "live calls are not required",
      });
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
  render(<App />);

  await signIn(user);
  await openSettingsTab(user, "Provider");

  const openAiForm = await screen.findByRole("form", {
    name: "OpenAI Provider konfigurieren",
  });
  await user.click(
    within(openAiForm).getByRole("button", { name: "Modelle abrufen" }),
  );

  const discoveredEmbeddingInput = await within(openAiForm).findByLabelText(
    "text-embedding-3-large",
  );
  expect(discoveredEmbeddingInput).toBeInstanceOf(HTMLInputElement);
  expect((discoveredEmbeddingInput as HTMLInputElement).checked).toBe(false);
  expect(within(openAiForm).getByLabelText("gpt-4.1-mini")).toBeChecked();
  expect(
    await screen.findByText("2 Modell(e) für OpenAI abgerufen."),
  ).toBeInTheDocument();
  expect(
    screen.queryByText("live calls are not required"),
  ).not.toBeInTheDocument();
  expect(openAiCheckCount).toBeGreaterThanOrEqual(1);
});

test("tests provider connections without changing model selections", async () => {
  const user = userEvent.setup();
  let checkCount = 0;
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
    if (path === "/api/providers/provider-openai/check" && method === "POST") {
      checkCount += 1;
      return jsonResponse({
        id: "provider-openai",
        provider: "openai",
        ok: true,
        models: ["text-embedding-3-large"],
        embedding_models: ["text-embedding-3-large"],
        llm_models: [],
        message: "provider reachable",
      });
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
  render(<App />);

  await signIn(user);
  await openSettingsTab(user, "Provider");
  const openAiForm = await screen.findByRole("form", {
    name: "OpenAI Provider konfigurieren",
  });

  await user.click(
    within(openAiForm).getByRole("button", { name: "Verbindung testen" }),
  );

  expect(
    await screen.findByText("Verbindung zu OpenAI erfolgreich geprüft."),
  ).toBeInTheDocument();
  expect(checkCount).toBe(1);
  expect(
    within(openAiForm).queryByLabelText("text-embedding-3-large"),
  ).not.toBeInTheDocument();
  expect(
    within(openAiForm).getByLabelText("text-embedding-3-small"),
  ).toBeChecked();
  expect(within(openAiForm).getByLabelText("gpt-4.1-mini")).toBeChecked();
});

test("keeps unchecked provider models visible and in their original order", async () => {
  const user = userEvent.setup();
  const orderedProvider = {
    ...ollamaProvider,
    available_models: ["embed-a", "shared-model", "embed-b"],
    manual_models: ["embed-a", "shared-model", "embed-b"],
    llm_models: ["embed-a", "shared-model", "embed-b"],
  };
  let savedBody: Record<string, unknown> | null = null;
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
      return jsonResponse([orderedProvider]);
    }
    if (path === "/api/providers/provider-ollama" && method === "PUT") {
      savedBody = JSON.parse(String(init?.body));
      return jsonResponse({
        ...orderedProvider,
        available_models: savedBody?.available_models,
        manual_models: savedBody?.manual_models,
        llm_models: savedBody?.llm_models,
      });
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
  render(<App />);

  await signIn(user);
  await openSettingsTab(user, "Provider");
  const ollamaForm = await screen.findByRole("form", {
    name: "Ollama Provider konfigurieren",
  });
  const modelSections = ollamaForm.querySelectorAll(".model-selection");
  const embeddingSection = modelSections[0] as HTMLElement;
  const llmSection = modelSections[1] as HTMLElement;
  const sectionLabels = (section: HTMLElement) =>
    Array.from(section.querySelectorAll("label")).map((label) =>
      label.textContent?.trim(),
    );

  expect(sectionLabels(embeddingSection)).toEqual([
    "embed-a",
    "shared-model",
    "embed-b",
  ]);
  const sharedInputs = within(ollamaForm).getAllByLabelText("shared-model");
  await user.click(sharedInputs[0]);
  await user.click(sharedInputs[1]);

  expect(sectionLabels(embeddingSection)).toEqual([
    "embed-a",
    "shared-model",
    "embed-b",
  ]);
  expect(sectionLabels(llmSection)).toEqual([
    "embed-a",
    "shared-model",
    "embed-b",
  ]);
  const uncheckedSharedInputs =
    within(ollamaForm).getAllByLabelText("shared-model");
  expect(uncheckedSharedInputs).toHaveLength(2);
  expect(uncheckedSharedInputs[0]).not.toBeChecked();
  expect(uncheckedSharedInputs[1]).not.toBeChecked();

  await user.click(
    within(ollamaForm).getByRole("button", { name: "Provider speichern" }),
  );

  await waitFor(() => {
    expect(savedBody).toMatchObject({
      available_models: ["embed-a", "shared-model", "embed-b"],
      manual_models: ["embed-a", "embed-b"],
      llm_models: ["embed-a", "embed-b"],
    });
  });
});

test("removes unavailable models after successful provider discovery", async () => {
  const user = userEvent.setup();
  const staleProvider = {
    ...ollamaProvider,
    available_models: ["nomic-embed-text", "removed-model"],
    manual_models: ["nomic-embed-text", "removed-model"],
    llm_models: ["removed-model"],
  };
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
      return jsonResponse([staleProvider]);
    }
    if (path === "/api/providers/provider-ollama/check" && method === "POST") {
      return jsonResponse({
        id: "provider-ollama",
        provider: "ollama",
        ok: true,
        models: ["nomic-embed-text"],
        embedding_models: ["nomic-embed-text"],
        llm_models: ["nomic-embed-text"],
        message: "Ollama models discovered",
      });
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
  render(<App />);

  await signIn(user);
  await openSettingsTab(user, "Provider");
  const ollamaForm = await screen.findByRole("form", {
    name: "Ollama Provider konfigurieren",
  });
  expect(within(ollamaForm).getAllByLabelText("removed-model")).toHaveLength(2);

  await user.click(
    within(ollamaForm).getByRole("button", { name: "Modelle abrufen" }),
  );

  await waitFor(() =>
    expect(
      within(ollamaForm).queryByLabelText("removed-model"),
    ).not.toBeInTheDocument(),
  );
  expect(within(ollamaForm).getAllByLabelText("nomic-embed-text")).toHaveLength(
    2,
  );
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
      return jsonResponse([
        {
          ...ollamaProvider,
          available_models: [],
          manual_models: [],
          llm_models: [],
        },
      ]);
    }
    if (path === "/api/providers/provider-ollama" && method === "PUT") {
      ollamaSaveCount += 1;
      const body = JSON.parse(String(init?.body));
      expect(body.endpoint_url).toBe("http://localhost:11434");
      expect(body.available_models).toEqual(
        ollamaSaveCount === 1 ? [] : ["nomic-embed-text", "mxbai-embed-large"],
      );
      expect(body.manual_models).toEqual(
        ollamaSaveCount === 1 ? [] : ["nomic-embed-text", "mxbai-embed-large"],
      );
      return jsonResponse({
        ...ollamaProvider,
        available_models: body.available_models,
        manual_models: body.manual_models,
        llm_models: body.llm_models,
      });
    }
    if (path === "/api/providers/provider-ollama/check" && method === "POST") {
      return jsonResponse({
        id: "provider-ollama",
        provider: "ollama",
        ok: true,
        models: ["nomic-embed-text", "mxbai-embed-large"],
        embedding_models: ["nomic-embed-text", "mxbai-embed-large"],
        llm_models: ["nomic-embed-text", "mxbai-embed-large"],
        message: "Ollama models discovered",
      });
    }
    if (
      path === "/api/providers/provider-ollama/ollama/pull" &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      expect(body.model).toBe("embeddinggemma");
      return jsonResponse({
        ...ollamaProvider,
        available_models: [
          "nomic-embed-text",
          "mxbai-embed-large",
          "embeddinggemma",
        ],
        manual_models: ["nomic-embed-text", "mxbai-embed-large"],
        llm_models: [],
      });
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
  render(<App />);

  await signIn(user);
  await openSettingsTab(user, "Provider");

  const ollamaForm = await screen.findByRole("form", {
    name: "Ollama Provider konfigurieren",
  });
  expect(within(ollamaForm).getByLabelText("Endpoint URL")).toHaveValue(
    "http://localhost:11434",
  );
  expect(within(ollamaForm).queryByLabelText("Ollama Modelle")).toBeNull();
  await user.click(
    within(ollamaForm).getByRole("button", { name: "Provider speichern" }),
  );

  expect(await screen.findByText("Ollama gespeichert.")).toBeInTheDocument();
  await user.click(
    within(ollamaForm).getByRole("button", { name: "Modelle abrufen" }),
  );
  await waitFor(() => {
    expect(
      within(ollamaForm).getAllByLabelText("nomic-embed-text").length,
    ).toBeGreaterThan(0);
    expect(
      within(ollamaForm).getAllByLabelText("mxbai-embed-large").length,
    ).toBeGreaterThan(0);
  });
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
  await waitFor(() => {
    expect(
      within(ollamaForm).getAllByLabelText("embeddinggemma").length,
    ).toBeGreaterThan(0);
  });
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
      path === "/api/projects/project-alpha/indexing-runs" &&
      method === "GET"
    ) {
      return jsonResponse([]);
    }
    if (path === "/api/projects/project-beta/imports" && method === "GET") {
      return jsonResponse([]);
    }
    if (
      path === "/api/projects/project-beta/indexing-runs" &&
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
      .getAllByRole("tab")
      .map((tab) => tab.textContent),
  ).toEqual([
    "Import",
    "Indizieren",
    "Cluster-Sets",
    "Explorer",
    "Projekt löschen",
  ]);

  await openProjectsPage(user);
  const switchProjectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(switchProjectList, "Alpha"));
  expect(
    await screen.findByRole("heading", { name: "Alpha" }),
  ).toBeInTheDocument();
  expect(
    within(
      screen.getByRole("form", { name: "Projekt umbenennen" }),
    ).getByLabelText("Projektname"),
  ).toHaveValue("Alpha");

  await openProjectsPage(user);
  const updatedProjectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(updatedProjectList, "Beta"));
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

  await openProjectsPage(user);
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
      path === "/api/projects/project-alpha/indexing-runs" &&
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

test("hides import log details when no persisted detail rows exist", async () => {
  const user = userEvent.setup();
  mockProjectFetch((path, method) => {
    if (path === "/api/projects/project-alpha/imports" && method === "GET") {
      return jsonResponse([
        {
          ...importLog,
          skipped_records: 1,
          skipped_detail_count: 0,
        },
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

  const importLogsRegion = await screen.findByRole("region", {
    name: "Importprotokolle",
  });
  expect(
    within(importLogsRegion).queryByRole("button", {
      name: "Logdetails anzeigen",
    }),
  ).not.toBeInTheDocument();
  expect(
    within(importLogsRegion).getByText("Keine Validierungsdetails vorhanden."),
  ).toBeInTheDocument();
});

test("configures providers and starts a project indexing run", async () => {
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
      return jsonResponse([
        localOllamaProvider,
        {
          ...openAiProvider,
          manual_models: ["text-embedding-3-small", "gpt-4.1-mini"],
        },
      ]);
    }
    if (path === "/api/providers/provider-openai" && method === "PUT") {
      openAiSaveCount += 1;
      expect(new Headers(init?.headers).get("Authorization")).toBe(
        "Bearer api-token",
      );
      const body = JSON.parse(String(init?.body));
      if (openAiSaveCount === 1) {
        expect(body.api_key).toBe("sk-test-secret");
        expect(body.available_models).toEqual([
          "text-embedding-3-small",
          "gpt-4.1-mini",
        ]);
        expect(body.manual_models).toEqual(["text-embedding-3-small"]);
        expect(body.llm_models).toEqual(["gpt-4.1-mini"]);
        return jsonResponse(openAiProvider);
      }
      expect(body.api_key).toBeUndefined();
      expect(body.manual_models).toEqual(["text-embedding-3-small"]);
      return jsonResponse({
        ...openAiProvider,
        manual_models: ["text-embedding-3-small"],
      });
    }
    if (path === "/api/providers/provider-openai/check" && method === "POST") {
      return jsonResponse({
        id: "provider-openai",
        provider: "openai",
        ok: true,
        models: ["text-embedding-3-small"],
        embedding_models: ["text-embedding-3-small"],
        llm_models: [],
        message: "OpenAI embedding models discovered",
      });
    }
    if (path === "/api/projects/project-alpha" && method === "GET") {
      return jsonResponse(alphaProject);
    }
    if (path === "/api/projects/project-alpha/imports" && method === "GET") {
      return jsonResponse([importLog]);
    }
    if (
      path === "/api/projects/project-alpha/indexing-runs" &&
      method === "GET"
    ) {
      return jsonResponse([completedAnalysisRun]);
    }
    if (path === "/api/projects/project-alpha/exports" && method === "GET") {
      return jsonResponse([]);
    }
    if (
      path === "/api/projects/project-alpha/indexing-runs" &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      expect(body).toMatchObject({
        dataset_version_id: "dataset-1",
        provider_id: "provider-local-ollama",
        model: "local-embed",
      });
      expect(body.analysis_profile_id).toBeUndefined();
      return jsonResponse(analysisRun, { status: 201 });
    }
    if (
      path === "/api/projects/project-alpha/cluster-sets" &&
      method === "GET"
    ) {
      return jsonResponse([
        {
          ...clusterSet,
          status: "completed",
          progress: 100,
          phase: "completed",
        },
      ]);
    }
    if (
      path ===
        "/api/projects/project-alpha/cluster-sets/cluster-set-1/clusters" &&
      method === "GET"
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
      path ===
        "/api/projects/project-alpha/clusters/cluster-1/sources?limit=50&offset=0" &&
      method === "GET"
    ) {
      return jsonResponse({
        sources: [
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
        ],
        limit: 50,
        offset: 0,
        next_offset: 1,
        has_more: true,
      });
    }
    if (
      path ===
        "/api/projects/project-alpha/clusters/cluster-1/sources?limit=50&offset=1" &&
      method === "GET"
    ) {
      return jsonResponse({
        sources: [
          {
            cluster_id: "cluster-1",
            message_pair_id: "pair-2",
            ticket_id: "T-2",
            message_group_id: "G-2",
            message: "Can I change the email?",
            answer: "Open account settings.",
            membership_score: 0.82,
            is_outlier: false,
            assignment_type: "automatic",
          },
        ],
        limit: 50,
        offset: 1,
        next_offset: null,
        has_more: false,
      });
    }
    if (
      path === "/api/projects/project-alpha/exports/explorer" &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      expect(body).toMatchObject({
        cluster_set_id: "cluster-set-1",
        export_format: "csv",
        search_query: null,
        category: null,
        include_excluded: false,
        include_outliers: true,
        cluster_ids: ["cluster-1"],
      });
      return jsonResponse(
        {
          export: explorerExportLog,
          content:
            "cluster_id,status,title,category,summary_question,summary_answer\ncluster-1,reviewed,Reset workflow,Account,How do I reset it?,Use the reset link.\n",
          content_type: "text/csv",
          warning: null,
        },
        { status: 201 },
      );
    }
    throw new Error(`unexpected request ${method} ${path}`);
  });
  render(<App />);

  await signIn(user);
  await openSettingsTab(user, "Provider");

  const openAiForm = await screen.findByRole("form", {
    name: "OpenAI Provider konfigurieren",
  });
  await user.type(
    within(openAiForm).getByLabelText("OpenAI API-Key"),
    "sk-test-secret",
  );
  await user.click(
    within(openAiForm).getByRole("button", { name: "Provider speichern" }),
  );

  expect(await screen.findByText("OpenAI gespeichert.")).toBeInTheDocument();
  const savedOpenAiInputs =
    within(openAiForm).getAllByLabelText("gpt-4.1-mini");
  expect(
    savedOpenAiInputs.every(
      (input) => input instanceof HTMLInputElement && input.checked,
    ),
  ).toBe(true);
  expect(screen.queryByText("sk-test-secret")).not.toBeInTheDocument();

  await openProjectsPage(user);

  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));
  expect(
    screen.queryByRole("button", { name: "Profile" }),
  ).not.toBeInTheDocument();

  await openProjectTab(user, "Indizieren");
  const runForm = await screen.findByRole("form", {
    name: "Indizierung starten",
  });
  expect(
    within(runForm).queryByLabelText("Analyseprofil"),
  ).not.toBeInTheDocument();
  expect(within(runForm).getByLabelText("Embedding-Provider")).toHaveValue(
    "provider-local-ollama",
  );
  expect(within(runForm).getByLabelText("Embedding-Modell")).toHaveValue(
    "local-embed",
  );
  await user.click(
    within(runForm).getByRole("button", { name: "Indizierung starten" }),
  );

  const runsRegion = await screen.findByRole("region", {
    name: "Indizierungen",
  });
  expect(await within(runsRegion).findByText("queued")).toBeInTheDocument();
  expect(within(runsRegion).getAllByText("0%").length).toBeGreaterThan(0);
  expect(
    within(runsRegion).getAllByText(
      "Provider/Modell: Lokales Ollama/local-embed",
    ).length,
  ).toBeGreaterThan(0);
  expect(
    within(runsRegion).getAllByText(/Version: dataset-1/).length,
  ).toBeGreaterThan(0);
  expect(within(runsRegion).getByText(/Diagnose: {}/)).toBeInTheDocument();

  await openProjectTab(user, "Cluster-Sets");
  expect(
    screen.queryByRole("region", { name: "Cluster Aktionen" }),
  ).not.toBeInTheDocument();
  const clusterSets = await screen.findByRole("region", {
    name: "Cluster-Sets",
  });
  expect(
    within(clusterSets).getByRole("button", { name: "Im Explorer laden" }),
  ).toBeEnabled();
  expect(
    within(clusterSets).getByRole("button", { name: "Cluster verfeinern" }),
  ).toBeEnabled();
  expect(within(clusterSets).getByText("min_samples")).toBeInTheDocument();
  expect(within(clusterSets).getByText("Ziel-Dimensionen")).toBeInTheDocument();
  expect(within(clusterSets).getByText("100")).toBeInTheDocument();
  expect(within(clusterSets).getByText("UMAP n_neighbors")).toBeInTheDocument();
  expect(
    within(clusterSets).getAllByText("nicht aktiv").length,
  ).toBeGreaterThan(0);
  await user.click(
    within(clusterSets).getByRole("button", { name: "Cluster verfeinern" }),
  );
  const directRefinementForm = await screen.findByRole("form", {
    name: "Cluster-Set erstellen",
  });
  expect(
    within(directRefinementForm).getByText("Verfeinerung vorausgefüllt"),
  ).toBeInTheDocument();
  expect(
    within(directRefinementForm).getByText(/1 eingeschlossene Cluster/),
  ).toBeInTheDocument();
  await user.click(
    within(directRefinementForm).getByRole("button", {
      name: "Verfeinerung zurücksetzen",
    }),
  );
  await user.click(
    within(clusterSets).getByRole("button", { name: "Im Explorer laden" }),
  );

  const clusterExplorer = await screen.findByRole("region", {
    name: "Cluster Explorer",
  });
  expect(
    await within(clusterExplorer).findByText("Cluster H"),
  ).toBeInTheDocument();
  expect(within(clusterExplorer).getByText(/Auto: Cluster H/)).toBeVisible();
  expect(within(clusterExplorer).getByText("How do I reset it?")).toBeVisible();
  expect(
    within(clusterExplorer).getByText("Use the reset link."),
  ).toBeVisible();
  expect(within(clusterExplorer).getByText(/Q\/A-Mismatch 0.44/)).toBeVisible();
  const explorerParameters = within(clusterExplorer).getByRole("region", {
    name: "Cluster-Set Parameter",
  });
  expect(within(explorerParameters).getByText("min_samples")).toBeVisible();
  expect(within(explorerParameters).getByText("12")).toBeVisible();
  expect(
    within(explorerParameters).getByText("Ziel-Dimensionen"),
  ).toBeVisible();
  expect(within(explorerParameters).getByText("100")).toBeVisible();

  const searchInput = within(clusterExplorer).getByPlaceholderText(
    "Titel, Kategorie, Summary oder Status",
  );
  await user.type(searchInput, "nicht vorhanden");
  expect(
    within(clusterExplorer).getByText(
      "Keine Cluster entsprechen der aktuellen Textsuche oder dem Filter.",
    ),
  ).toBeInTheDocument();
  await user.clear(searchInput);

  const clusterRow = within(clusterExplorer)
    .getByText("Cluster H")
    .closest("tr");
  if (clusterRow === null) {
    throw new Error("cluster row missing");
  }
  await user.type(
    within(clusterRow).getByLabelText("Titel für Cluster H"),
    "Reset workflow",
  );
  await user.type(
    within(clusterRow).getByLabelText("Kategorie für Cluster H"),
    "Account",
  );
  await user.selectOptions(
    within(clusterRow).getByLabelText("Status für Cluster H"),
    "reviewed",
  );
  await user.click(
    within(clusterRow).getByRole("button", { name: "Speichern" }),
  );
  expect(
    await within(clusterExplorer).findByText("Reset workflow"),
  ).toBeInTheDocument();
  expect(
    within(clusterExplorer).getAllByText("reviewed").length,
  ).toBeGreaterThan(0);

  const updatedClusterRow = within(clusterExplorer)
    .getByText("Reset workflow")
    .closest("tr");
  if (updatedClusterRow === null) {
    throw new Error("updated cluster row missing");
  }
  const sourceTrigger = within(updatedClusterRow).getByRole("button", {
    name: "Quellen anzeigen",
  });
  await user.click(sourceTrigger);
  const sources = await screen.findByRole("dialog", {
    name: "Reset workflow",
  });
  const closeSources = within(sources).getByRole("button", {
    name: "Schließen",
  });
  expect(closeSources).toHaveFocus();
  fireEvent.keyDown(window, { key: "Tab" });
  expect(closeSources).toHaveFocus();
  expect(
    within(sources).getByText("Ticket T-1 · Gruppe G-1"),
  ).toBeInTheDocument();
  expect(
    within(sources).getByText("Kundenfrage: How do I reset it?"),
  ).toBeInTheDocument();
  expect(
    within(sources).getByText("Supportantwort: Use the reset link."),
  ).toBeInTheDocument();
  await user.click(
    within(sources).getByRole("button", { name: "Weitere Quellen laden" }),
  );
  expect(
    await within(sources).findByText("Ticket T-2 · Gruppe G-2"),
  ).toBeInTheDocument();
  expect(
    within(sources).getByText("Angezeigt: 2 Quellen."),
  ).toBeInTheDocument();
  fireEvent.keyDown(window, { key: "Escape" });
  await waitFor(() => {
    expect(
      screen.queryByRole("dialog", { name: "Reset workflow" }),
    ).not.toBeInTheDocument();
  });
  expect(sourceTrigger).toHaveFocus();

  const explorerExport = await screen.findByRole("region", {
    name: "Explorer Export",
  });
  await user.click(
    within(explorerExport).getByRole("button", {
      name: "Aktuelle Tabelle exportieren",
    }),
  );
  expect(
    await screen.findByText(/Explorer-Export erstellt/),
  ).toBeInTheDocument();
  const exportHistory = within(explorerExport).getByRole("region", {
    name: "Exporthistorie",
  });
  expect(
    within(exportHistory).getByText("explorer_csv-cluster-set-1.csv"),
  ).toBeInTheDocument();
  expect(
    within(exportHistory).getByText(/Cluster-Set: cluster-set-1/),
  ).toBeInTheDocument();
  expect(
    within(explorerExport).getByLabelText("Letzter Explorer Export"),
  ).toBeInTheDocument();

  const explorerRail = within(clusterExplorer).getByRole("complementary", {
    name: "Explorer Kontrollleiste",
  });
  const refinementGroup = within(explorerRail).getByRole("region", {
    name: "Explorer Verfeinerung",
  });
  await user.click(
    within(refinementGroup).getByRole("button", {
      name: "Eingeschlossene Cluster verfeinern",
    }),
  );
  const refinementForm = await screen.findByRole("form", {
    name: "Cluster-Set erstellen",
  });
  expect(
    within(refinementForm).getByText("Verfeinerung vorausgefüllt"),
  ).toBeInTheDocument();
  expect(
    within(refinementForm).getByText(/1 sichtbare eingeschlossene Cluster/),
  ).toBeInTheDocument();
});

test("hides run-bound clustering and gates Cluster-Set loading until completion", async () => {
  const user = userEvent.setup();
  mockProjectFetch((path, method) => {
    if (
      path === "/api/projects/project-alpha/indexing-runs" &&
      method === "GET"
    ) {
      return jsonResponse([analysisRun, completedAnalysisRun]);
    }
    if (
      path === "/api/projects/project-alpha/cluster-sets" &&
      method === "GET"
    ) {
      return jsonResponse([
        {
          ...clusterSet,
          status: "running",
          progress: 40,
          phase: "clustering",
        },
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
  await openProjectTab(user, "Cluster-Sets");

  expect(
    screen.queryByRole("region", { name: "Cluster Aktionen" }),
  ).not.toBeInTheDocument();
  const clusterSets = await screen.findByRole("region", {
    name: "Cluster-Sets",
  });
  expect(within(clusterSets).getByText(/running · 40%/)).toBeInTheDocument();
  expect(
    within(clusterSets).getByRole("button", { name: "Im Explorer laden" }),
  ).toBeDisabled();
  expect(
    within(clusterSets).getByRole("button", { name: "Cluster verfeinern" }),
  ).toBeDisabled();
  await openProjectTab(user, "Explorer");
  expect(
    screen.getByText(/Noch kein abgeschlossenes Cluster-Set geladen/),
  ).toBeInTheDocument();
});

test("regenerates summaries through the summary-only Cluster-Set endpoint", async () => {
  const user = userEvent.setup();
  let summaryPostCount = 0;
  let createPostCount = 0;
  mockProjectFetch((path, method, init) => {
    if (path === "/api/providers" && method === "GET") {
      return jsonResponse([ollamaProvider]);
    }
    if (
      path === "/api/projects/project-alpha/indexing-runs" &&
      method === "GET"
    ) {
      return jsonResponse([completedAnalysisRun]);
    }
    if (
      path === "/api/projects/project-alpha/cluster-sets" &&
      method === "GET"
    ) {
      return jsonResponse([
        {
          ...clusterSet,
          status: "completed",
          progress: 100,
          phase: "completed",
        },
      ]);
    }
    if (
      path ===
        "/api/projects/project-alpha/cluster-sets/cluster-set-1/summaries" &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      expect(body).toMatchObject({
        llm_provider_id: "provider-ollama",
        llm_model: "llama3.1",
        llm_sample_count: 2,
        llm_sample_all: false,
        llm_cloud_use_confirmed: false,
      });
      summaryPostCount += 1;
      return jsonResponse(
        {
          ...clusterSet,
          status: "queued",
          progress: 85,
          phase: "queued_summary",
        },
        { status: 202 },
      );
    }
    if (
      path === "/api/projects/project-alpha/cluster-sets" &&
      method === "POST"
    ) {
      createPostCount += 1;
      return jsonResponse(clusterSet, { status: 201 });
    }
    return undefined;
  });
  render(<App />);

  await signIn(user);
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));
  await openProjectTab(user, "Cluster-Sets");

  const clusterSets = await screen.findByRole("region", {
    name: "Cluster-Sets",
  });
  await user.click(
    within(clusterSets).getByRole("button", {
      name: "Summaries neu erstellen",
    }),
  );
  const summaryDialog = await screen.findByRole("dialog", {
    name: "Summaries neu erstellen",
  });
  expect(
    within(summaryDialog).getByText(/Clusterzuordnung.*bleiben unverändert/),
  ).toBeInTheDocument();
  expect(within(summaryDialog).getByLabelText("LLM-Provider")).toHaveValue(
    "provider-ollama",
  );
  expect(within(summaryDialog).getByLabelText("Modell")).toHaveValue(
    "llama3.1",
  );
  expect(
    within(summaryDialog).getByLabelText("Beispiele je Cluster"),
  ).toHaveValue(2);
  expect(within(summaryDialog).getByLabelText("Ergebnis")).toHaveValue(
    "replace",
  );
  expect(summaryPostCount).toBe(0);
  await user.click(
    within(summaryDialog).getByRole("button", { name: "Summary-Job starten" }),
  );

  await waitFor(() => expect(summaryPostCount).toBe(1));
  expect(createPostCount).toBe(0);
  expect(
    await screen.findByText(
      "Summary-Neuerstellung gestartet. Status wird aktualisiert.",
    ),
  ).toBeInTheDocument();
});

test("regenerates summaries from the Explorer rail without full reclustering", async () => {
  const user = userEvent.setup();
  let summaryPostCount = 0;
  let createPostCount = 0;
  mockProjectFetch((path, method, init) => {
    if (path === "/api/providers" && method === "GET") {
      return jsonResponse([ollamaProvider]);
    }
    if (
      path === "/api/projects/project-alpha/indexing-runs" &&
      method === "GET"
    ) {
      return jsonResponse([completedAnalysisRun]);
    }
    if (
      path === "/api/projects/project-alpha/cluster-sets" &&
      method === "GET"
    ) {
      return jsonResponse([
        {
          ...clusterSet,
          status: "completed",
          progress: 100,
          phase: "completed",
        },
      ]);
    }
    if (
      path ===
        "/api/projects/project-alpha/cluster-sets/cluster-set-1/clusters" &&
      method === "GET"
    ) {
      return jsonResponse([cluster]);
    }
    if (
      path ===
        "/api/projects/project-alpha/cluster-sets/cluster-set-1/summaries" &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      expect(body).toMatchObject({
        llm_provider_id: "provider-ollama",
        llm_model: "llama3.1",
        llm_sample_count: 2,
        llm_sample_all: false,
        llm_cloud_use_confirmed: false,
      });
      summaryPostCount += 1;
      return jsonResponse(
        {
          ...clusterSet,
          status: "queued",
          progress: 85,
          phase: "queued_summary",
        },
        { status: 202 },
      );
    }
    if (
      path === "/api/projects/project-alpha/cluster-sets" &&
      method === "POST"
    ) {
      createPostCount += 1;
      return jsonResponse(clusterSet, { status: 201 });
    }
    return undefined;
  });
  render(<App />);

  await signIn(user);
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));
  await openProjectTab(user, "Explorer");

  const clusterExplorer = await screen.findByRole("region", {
    name: "Cluster Explorer",
  });
  await within(clusterExplorer).findByText("Cluster H");
  const explorerRail = within(clusterExplorer).getByRole("complementary", {
    name: "Explorer Kontrollleiste",
  });
  const summaryGroup = within(explorerRail).getByRole("region", {
    name: "Explorer Summary",
  });
  expect(
    within(summaryGroup).getByText(/Summary-Felder dieses Cluster-Sets/),
  ).toBeInTheDocument();
  await user.click(
    within(summaryGroup).getByRole("button", {
      name: "Summaries neu erstellen",
    }),
  );
  const summaryDialog = await screen.findByRole("dialog", {
    name: "Summaries neu erstellen",
  });
  expect(within(summaryDialog).getByLabelText("LLM-Provider")).toHaveValue(
    "provider-ollama",
  );
  await user.click(
    within(summaryDialog).getByRole("button", { name: "Summary-Job starten" }),
  );

  await waitFor(() => expect(summaryPostCount).toBe(1));
  expect(createPostCount).toBe(0);
  expect(
    await screen.findByText(
      "Summary-Neuerstellung gestartet. Status wird aktualisiert.",
    ),
  ).toBeInTheDocument();
});

test("allows Explorer outlier recalculation while another Cluster-Set job is active", async () => {
  const user = userEvent.setup();
  let outlierPostCount = 0;
  mockProjectFetch((path, method) => {
    if (
      path === "/api/projects/project-alpha/indexing-runs" &&
      method === "GET"
    ) {
      return jsonResponse([completedAnalysisRun]);
    }
    if (
      path === "/api/projects/project-alpha/cluster-sets" &&
      method === "GET"
    ) {
      return jsonResponse([
        {
          ...clusterSet,
          status: "completed",
          progress: 100,
          phase: "completed",
        },
      ]);
    }
    if (
      path ===
        "/api/projects/project-alpha/cluster-sets/cluster-set-1/clusters" &&
      method === "GET"
    ) {
      return jsonResponse([cluster]);
    }
    if (
      path === "/api/projects/project-alpha/cluster-sets" &&
      method === "POST"
    ) {
      outlierPostCount += 1;
      return jsonResponse(
        {
          ...clusterSet,
          id: "cluster-set-outliers",
          parent_cluster_set_id: "cluster-set-1",
          derivation_type: "outlier_exclusion",
          display_name: "Antworten fein ohne Ausreißer",
          status: "queued",
          progress: 0,
          phase: "queued",
        },
        { status: 201 },
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
  await openProjectTab(user, "Explorer");

  const clusterExplorer = await screen.findByRole("region", {
    name: "Cluster Explorer",
  });
  const outlierButton = within(clusterExplorer).getByRole("button", {
    name: "Ausreißer berechnen",
  });
  expect(outlierButton).toBeEnabled();
  await user.click(outlierButton);
  await waitFor(() => expect(outlierPostCount).toBe(1));
  expect(
    await screen.findByText(
      "Ausreißer-Neuberechnung als Child-Cluster-Set gestartet.",
    ),
  ).toBeInTheDocument();
});

test("lets analysts collapse and reopen Cluster-Set tree branches", async () => {
  const user = userEvent.setup();
  mockProjectFetch((path, method) => {
    if (
      path === "/api/projects/project-alpha/indexing-runs" &&
      method === "GET"
    ) {
      return jsonResponse([completedAnalysisRun]);
    }
    if (
      path === "/api/projects/project-alpha/cluster-sets" &&
      method === "GET"
    ) {
      return jsonResponse([
        {
          ...clusterSet,
          status: "completed",
          progress: 100,
          phase: "completed",
          cluster_count: 2,
        },
        {
          ...clusterSet,
          id: "cluster-set-child-1",
          parent_cluster_set_id: "cluster-set-1",
          display_name: "Antworten fein — Retouren",
          derivation_type: "refinement",
          vector_basis: "answer",
          cluster_count: 1,
        },
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
  await openProjectTab(user, "Cluster-Sets");

  const clusterSets = await screen.findByRole("region", {
    name: "Cluster-Sets",
  });
  const toggle = within(clusterSets).getByRole("button", {
    name: "Ast einklappen",
  });
  expect(toggle).toHaveAttribute("aria-expanded", "true");
  expect(
    within(clusterSets).getByText("Antworten fein — Retouren"),
  ).toBeVisible();

  await user.click(toggle);
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  expect(
    within(clusterSets).queryByText("Antworten fein — Retouren"),
  ).not.toBeInTheDocument();

  await user.click(
    within(clusterSets).getByRole("button", { name: "Ast ausklappen" }),
  );
  expect(
    within(clusterSets).getByText("Antworten fein — Retouren"),
  ).toBeVisible();
});

test("shows and guards Cluster-Set creation while the request is pending", async () => {
  const user = userEvent.setup();
  let createRequests = 0;
  let resolveCreation: (response: Response) => void = () => undefined;
  const pendingCreation = new Promise<Response>((resolve) => {
    resolveCreation = resolve;
  });
  mockProjectFetch((path, method) => {
    if (
      path === "/api/projects/project-alpha/indexing-runs" &&
      method === "GET"
    ) {
      return jsonResponse([completedAnalysisRun]);
    }
    if (
      path === "/api/projects/project-alpha/cluster-sets" &&
      method === "GET"
    ) {
      return jsonResponse([]);
    }
    if (
      path === "/api/projects/project-alpha/cluster-sets" &&
      method === "POST"
    ) {
      createRequests += 1;
      return pendingCreation;
    }
    return undefined;
  });
  render(<App />);

  await signIn(user);
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));
  await openProjectTab(user, "Cluster-Sets");

  const form = await screen.findByRole("form", {
    name: "Cluster-Set erstellen",
  });
  await user.type(within(form).getByLabelText("Anzeigename"), "Pending Set");
  await user.click(
    within(form).getByRole("button", { name: "Cluster-Set erstellen" }),
  );

  const pendingButton = within(form).getByRole("button", {
    name: "Cluster-Set wird erstellt",
  });
  expect(pendingButton).toBeDisabled();
  fireEvent.click(pendingButton);
  expect(createRequests).toBe(1);

  await act(async () => {
    resolveCreation(jsonResponse(clusterSet, { status: 201 }));
    await pendingCreation;
  });

  expect(
    await screen.findByText("Cluster-Set angelegt. Status wird aktualisiert."),
  ).toBeInTheDocument();
  expect(
    within(form).getByRole("button", { name: "Cluster-Set erstellen" }),
  ).toBeEnabled();
});

test("creates a Cluster-Set with vector basis and bounded LLM sampling", async () => {
  const user = userEvent.setup();
  let receivedBody: Record<string, unknown> | null = null;
  mockProjectFetch((path, method, init) => {
    if (path === "/api/providers" && method === "GET") {
      return jsonResponse([
        localOllamaProvider,
        { ...ollamaProvider, llm_models: ["llama3.1"] },
      ]);
    }
    if (
      path === "/api/projects/project-alpha/indexing-runs" &&
      method === "GET"
    ) {
      return jsonResponse([completedAnalysisRun]);
    }
    if (
      path === "/api/projects/project-alpha/cluster-sets" &&
      method === "GET"
    ) {
      return jsonResponse([]);
    }
    if (
      path === "/api/projects/project-alpha/cluster-sets" &&
      method === "POST"
    ) {
      receivedBody = JSON.parse(String(init?.body));
      return jsonResponse(clusterSet, { status: 201 });
    }
    return undefined;
  });
  render(<App />);

  await signIn(user);
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));
  await openProjectTab(user, "Cluster-Sets");

  const form = await screen.findByRole("form", {
    name: "Cluster-Set erstellen",
  });
  await user.type(within(form).getByLabelText("Anzeigename"), "Antworten fein");
  await user.selectOptions(
    within(form).getByLabelText("Vektor-Basis"),
    "combined",
  );
  await user.clear(within(form).getByLabelText("Antwort-Gewicht"));
  await user.type(within(form).getByLabelText("Antwort-Gewicht"), "0.6");
  await user.clear(within(form).getByLabelText("Nachricht-Gewicht"));
  await user.type(within(form).getByLabelText("Nachricht-Gewicht"), "0.4");
  await user.type(
    within(form).getByLabelText("Outlier-Schwelle optional"),
    "0.72",
  );
  await user.selectOptions(
    within(form).getByLabelText("LLM-Zusammenfassung"),
    "provider-ollama",
  );
  await user.clear(within(form).getByLabelText("Beispiele pro Cluster"));
  await user.type(within(form).getByLabelText("Beispiele pro Cluster"), "2");
  await user.click(
    within(form).getByRole("button", { name: "Cluster-Set erstellen" }),
  );

  await screen.findByText("Antworten fein");
  expect(receivedBody).toMatchObject({
    indexing_run_id: "run-completed",
    display_name: "Antworten fein",
    vector_basis: "combined",
    message_weight: 0.4,
    answer_weight: 0.6,
    outlier_threshold: 0.72,
    llm_provider_id: "provider-ollama",
    llm_model: "llama3.1",
    llm_sample_count: 2,
  });
  const clusterSetsRegion = screen.getByRole("region", {
    name: "Cluster-Sets",
  });
  expect(
    within(clusterSetsRegion).getByText(/queued · 0%/),
  ).toBeInTheDocument();
  expect(
    within(clusterSetsRegion).getByText(/Ollama\/llama3.1/),
  ).toBeInTheDocument();
  expect(
    within(clusterSetsRegion).getByText("Outlier-Schwelle"),
  ).toBeInTheDocument();
  expect(within(clusterSetsRegion).getByText("0.72")).toBeInTheDocument();
});

test("rejects non-integer Cluster-Set LLM sample counts before submitting", async () => {
  const user = userEvent.setup();
  let postCount = 0;
  mockProjectFetch((path, method) => {
    if (path === "/api/providers" && method === "GET") {
      return jsonResponse([
        localOllamaProvider,
        { ...ollamaProvider, llm_models: ["llama3.1"] },
      ]);
    }
    if (
      path === "/api/projects/project-alpha/indexing-runs" &&
      method === "GET"
    ) {
      return jsonResponse([completedAnalysisRun]);
    }
    if (
      path === "/api/projects/project-alpha/cluster-sets" &&
      method === "GET"
    ) {
      return jsonResponse([]);
    }
    if (
      path === "/api/projects/project-alpha/cluster-sets" &&
      method === "POST"
    ) {
      postCount += 1;
      return jsonResponse(clusterSet, { status: 201 });
    }
    return undefined;
  });
  render(<App />);

  await signIn(user);
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));
  await openProjectTab(user, "Cluster-Sets");

  const form = await screen.findByRole("form", {
    name: "Cluster-Set erstellen",
  });
  await user.selectOptions(
    within(form).getByLabelText("LLM-Zusammenfassung"),
    "provider-ollama",
  );
  await user.clear(within(form).getByLabelText("Beispiele pro Cluster"));
  await user.type(within(form).getByLabelText("Beispiele pro Cluster"), "1.5");
  await user.click(
    within(form).getByRole("button", { name: "Cluster-Set erstellen" }),
  );

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Die Beispielanzahl für Zusammenfassungen ist ungültig.",
  );
  expect(postCount).toBe(0);
});

test("ignores delayed Cluster-Set creation after switching projects", async () => {
  const user = userEvent.setup();
  const betaRun = {
    ...completedAnalysisRun,
    id: "run-beta",
    project_id: "project-beta",
  };
  let resolveCreation: (response: Response) => void = () => undefined;
  const pendingCreation = new Promise<Response>((resolve) => {
    resolveCreation = resolve;
  });
  mockProjectFetch((path, method) => {
    if (
      path === "/api/projects/project-alpha/indexing-runs" &&
      method === "GET"
    ) {
      return jsonResponse([completedAnalysisRun]);
    }
    if (
      path === "/api/projects/project-beta/indexing-runs" &&
      method === "GET"
    ) {
      return jsonResponse([betaRun]);
    }
    if (
      path === "/api/projects/project-alpha/cluster-sets" &&
      method === "POST"
    ) {
      return pendingCreation;
    }
    if (
      /^\/api\/projects\/project-(alpha|beta)\/cluster-sets$/.test(path) &&
      method === "GET"
    ) {
      return jsonResponse([]);
    }
    return undefined;
  });
  render(<App />);

  await signIn(user);
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));
  await openProjectTab(user, "Cluster-Sets");
  const form = await screen.findByRole("form", {
    name: "Cluster-Set erstellen",
  });
  await user.type(within(form).getByLabelText("Anzeigename"), "Alpha Set");
  await user.click(
    within(form).getByRole("button", { name: "Cluster-Set erstellen" }),
  );

  await openProjectsPage(user);
  const switchProjectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(switchProjectList, "Beta"));
  await waitFor(() =>
    expect(screen.getByLabelText("Projektname")).toHaveValue("Beta"),
  );
  expect(screen.getByText("Projekt geöffnet.")).toBeInTheDocument();

  await act(async () => {
    resolveCreation(jsonResponse(clusterSet, { status: 201 }));
    await pendingCreation;
  });

  expect(screen.getByText("Projekt geöffnet.")).toBeInTheDocument();
  expect(
    screen.queryByText("Cluster-Set angelegt. Status wird aktualisiert."),
  ).not.toBeInTheDocument();
  await openProjectTab(user, "Cluster-Sets");
  const betaClusterSets = await screen.findByRole("region", {
    name: "Cluster-Sets",
  });
  expect(
    within(betaClusterSets).queryByText("Cluster H"),
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

test("renders safe error feedback for user, provider, import, indexing, explorer, and export actions", async () => {
  const user = userEvent.setup();
  let indexingRejections = 0;
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
      return jsonResponse([localOllamaProvider]);
    }
    if (path === "/api/providers/provider-local-ollama" && method === "PUT") {
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
      path === "/api/projects/project-alpha/indexing-runs" &&
      method === "GET"
    ) {
      return jsonResponse([completedAnalysisRun]);
    }
    if (
      path === "/api/projects/project-alpha/indexing-runs" &&
      method === "POST"
    ) {
      indexingRejections += 1;
      if (indexingRejections === 1) {
        return jsonResponse(
          {
            title: "Indizierung abgelehnt",
            detail: "raw indexing model diagnostic",
            code: "INDEXING_MODEL_UNAVAILABLE",
          },
          { status: 422 },
        );
      }
      return jsonResponse(
        {
          title: "Indizierung abgelehnt",
          detail: "indexing run cannot be started",
          code: "IDX-START-REJECTED",
        },
        { status: 409 },
      );
    }
    if (
      path === "/api/projects/project-alpha/cluster-sets" &&
      method === "GET"
    ) {
      return jsonResponse([
        {
          ...clusterSet,
          status: "completed",
          progress: 100,
          phase: "completed",
        },
      ]);
    }
    if (path === "/api/projects/project-alpha/exports" && method === "GET") {
      return jsonResponse([]);
    }
    if (
      path ===
        "/api/projects/project-alpha/cluster-sets/cluster-set-1/clusters" &&
      method === "GET"
    ) {
      return jsonResponse([cluster]);
    }
    if (
      path === "/api/projects/project-alpha/clusters/cluster-1" &&
      method === "PATCH"
    ) {
      return jsonResponse(
        {
          detail: "raw cluster update diagnostic",
          code: "CLUSTER_MANUAL_UPDATE_INVALID",
        },
        { status: 422 },
      );
    }
    if (
      path ===
        "/api/projects/project-alpha/clusters/cluster-1/sources?limit=50&offset=0" &&
      method === "GET"
    ) {
      return jsonResponse(
        {
          detail: "raw source lookup diagnostic",
          code: "CLUSTER_SOURCE_NOT_FOUND",
        },
        { status: 404 },
      );
    }
    if (
      path === "/api/projects/project-alpha/exports/explorer" &&
      method === "POST"
    ) {
      return jsonResponse(
        {
          detail: "raw explorer export diagnostic",
          code: "EXPLORER_EXPORT_FAILED",
        },
        { status: 500 },
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

  await openSettingsTab(user, "Provider");
  const providerForm = await screen.findByRole("form", {
    name: "Lokales Ollama Provider konfigurieren",
  });
  await user.click(
    within(providerForm).getByRole("button", { name: "Provider speichern" }),
  );
  await expectErrorFeedback(
    "provider endpoint is not reachable",
    "raw exception",
  );

  await openProjectsPage(user);
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

  await openProjectTab(user, "Indizieren");
  const runForm = await screen.findByRole("form", {
    name: "Indizierung starten",
  });
  await user.click(
    within(runForm).getByRole("button", { name: "Indizierung starten" }),
  );
  await expectErrorFeedback(
    "Das gewählte Embedding-Modell ist nicht verfügbar. Bitte Provider-Einstellungen prüfen oder ein anderes Modell wählen.",
    "raw indexing model diagnostic",
  );
  await user.click(
    within(runForm).getByRole("button", { name: "Indizierung starten" }),
  );
  await expectErrorFeedback(
    "Die Aktion konnte nicht abgeschlossen werden. Bitte erneut versuchen oder den aktuellen Stand neu laden.",
    "indexing run cannot be started",
  );

  await openProjectTab(user, "Cluster-Sets");
  const clusterSets = await screen.findByRole("region", {
    name: "Cluster-Sets",
  });
  await user.click(
    within(clusterSets).getByRole("button", { name: "Im Explorer laden" }),
  );
  const clusterExplorer = await screen.findByRole("region", {
    name: "Cluster Explorer",
  });
  const clusterRow = (
    await within(clusterExplorer).findByText("Cluster H")
  ).closest("tr");
  if (clusterRow === null) {
    throw new Error("cluster row missing");
  }
  await user.click(
    within(clusterRow).getByRole("button", { name: "Ausschließen" }),
  );
  await expectErrorFeedback(
    "Die Cluster-Änderung ist ungültig und wurde nicht gespeichert.",
    "raw cluster update diagnostic",
  );

  await user.click(
    within(clusterRow).getByRole("button", { name: "Quellen anzeigen" }),
  );
  await expectErrorFeedback(
    "Die Quellen dieses Clusters konnten nicht geladen werden. Bitte Cluster-Set neu laden.",
    "raw source lookup diagnostic",
  );
  const failedSourceDialog = await screen.findByRole("dialog", {
    name: "Cluster H",
  });
  const sourceAlert = within(failedSourceDialog).getByRole("alert");
  expect(
    within(sourceAlert).getByText(
      "Die Quellen dieses Clusters konnten nicht geladen werden. Bitte Cluster-Set neu laden.",
    ),
  ).toBeInTheDocument();
  expect(
    within(failedSourceDialog).queryByText(
      "Keine Quellen für diesen Cluster vorhanden.",
    ),
  ).not.toBeInTheDocument();
  expect(
    within(failedSourceDialog).getByRole("button", {
      name: "Quellen erneut laden",
    }),
  ).toBeInTheDocument();
  await user.click(
    within(failedSourceDialog).getByRole("button", { name: "Schließen" }),
  );

  const explorerExport = await screen.findByRole("region", {
    name: "Explorer Export",
  });
  await user.click(
    within(explorerExport).getByRole("button", {
      name: "Aktuelle Tabelle exportieren",
    }),
  );
  await expectErrorFeedback(
    "Der Export konnte nicht erstellt werden. Bitte erneut versuchen oder das Format wechseln.",
    "raw explorer export diagnostic",
  );
  const exportAlert = within(explorerExport).getByRole("alert");
  expect(
    within(exportAlert).getByText(
      "Der Export konnte nicht erstellt werden. Bitte erneut versuchen oder das Format wechseln.",
    ),
  ).toBeInTheDocument();
  expect(
    within(exportAlert).getByText(/Filter und Format bleiben erhalten/),
  ).toBeInTheDocument();
  expect(
    within(explorerExport).queryByLabelText("Letzter Explorer Export"),
  ).not.toBeInTheDocument();
});

test("keeps indexing requests project-local and sends only selected provider and model fields", async () => {
  const user = userEvent.setup();
  const indexingBodies: Record<string, unknown>[] = [];
  let resolveBetaProject: (response: Response) => void = () => undefined;
  const pendingBetaProject = new Promise<Response>((resolve) => {
    resolveBetaProject = resolve;
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
        { ...localOllamaProvider, manual_models: [] },
        {
          ...ollamaProvider,
          available_models: ["embed-a", "embed-b", "llama3.1"],
          manual_models: ["embed-a", "embed-b"],
        },
        openAiProvider,
      ]);
    }
    if (path === "/api/projects/project-alpha" && method === "GET") {
      return jsonResponse(alphaProject);
    }
    if (path === "/api/projects/project-beta" && method === "GET") {
      return pendingBetaProject;
    }
    if (path === "/api/projects/project-alpha/imports" && method === "GET") {
      return jsonResponse([importLog]);
    }
    if (path === "/api/projects/project-beta/imports" && method === "GET") {
      return jsonResponse([]);
    }
    if (
      path === "/api/projects/project-alpha/indexing-runs" &&
      method === "POST"
    ) {
      const body = JSON.parse(String(init?.body));
      indexingBodies.push(body);
      return jsonResponse(
        {
          ...analysisRun,
          provider: "ollama",
          provider_configuration_id: body.provider_id,
          provider_display_name: "Ollama",
          model: body.model,
          parameters: {},
        },
        { status: 201 },
      );
    }
    if (
      /^\/api\/projects\/project-(alpha|beta)\/indexing-runs$/.test(path) &&
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

  await openProjectTab(user, "Indizieren");
  const indexingForm = await screen.findByRole("form", {
    name: "Indizierung starten",
  });
  expect(within(indexingForm).getByLabelText("Embedding-Provider")).toHaveValue(
    "provider-ollama",
  );
  expect(screen.queryByText(/historical-legacy/)).not.toBeInTheDocument();

  const modelSelect = within(indexingForm).getByLabelText("Embedding-Modell");
  await waitFor(() => expect(modelSelect).toHaveValue("embed-a"));
  expect(
    within(modelSelect)
      .getAllByRole("option")
      .map((option) => option.textContent),
  ).toEqual(["embed-a", "embed-b"]);
  await user.click(
    within(indexingForm).getByRole("button", {
      name: "Indizierung starten",
    }),
  );

  expect(indexingBodies).toHaveLength(1);
  expect(indexingBodies[0]).toMatchObject({
    dataset_version_id: "dataset-1",
    provider_id: "provider-ollama",
    model: "embed-a",
  });
  expect(indexingBodies[0].analysis_profile_id).toBeUndefined();
  expect(indexingBodies[0].algorithm_settings).toBeUndefined();
  expect(indexingBodies[0].parameters).toBeUndefined();

  await openProjectsPage(user);
  const switchProjectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(switchProjectList, "Beta"));
  expect(
    screen.queryByRole("region", { name: "Aktuelles Projekt" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("form", { name: "Indizierung starten" }),
  ).not.toBeInTheDocument();
  fireEvent.submit(indexingForm);
  expect(indexingBodies).toHaveLength(1);

  resolveBetaProject(jsonResponse(betaProject));
  await waitFor(() =>
    expect(screen.getByLabelText("Projektname")).toHaveValue("Beta"),
  );
  await openProjectTab(user, "Indizieren");
  const betaIndexingForm = await screen.findByRole("form", {
    name: "Indizierung starten",
  });
  expect(
    within(betaIndexingForm).getByRole("button", {
      name: "Indizierung starten",
    }),
  ).toBeDisabled();
  expect(
    within(betaIndexingForm).queryByText(/dataset-1/),
  ).not.toBeInTheDocument();

  await openProjectsPage(user);
  const alphaProjectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(alphaProjectList, "Alpha"));
  await waitFor(() =>
    expect(screen.getByLabelText("Projektname")).toHaveValue("Alpha"),
  );
  await openProjectTab(user, "Indizieren");
  const runForm = await screen.findByRole("form", {
    name: "Indizierung starten",
  });
  await user.selectOptions(
    within(runForm).getByLabelText("Embedding-Provider"),
    "provider-ollama",
  );
  await user.click(
    within(runForm).getByRole("button", { name: "Indizierung starten" }),
  );
  await waitFor(() => expect(indexingBodies).toHaveLength(2));
  expect(indexingBodies[1]).toMatchObject({
    dataset_version_id: "dataset-1",
    provider_id: "provider-ollama",
    model: "embed-a",
  });
});

test("sends selected line-break normalization parameters for indexing", async () => {
  const user = userEvent.setup();
  let indexingBody: Record<string, unknown> | null = null;

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
      return jsonResponse([localOllamaProvider]);
    }
    if (path === "/api/projects/project-alpha" && method === "GET") {
      return jsonResponse(alphaProject);
    }
    if (path === "/api/projects/project-alpha/imports" && method === "GET") {
      return jsonResponse([importLog]);
    }
    if (
      path === "/api/projects/project-alpha/indexing-runs" &&
      method === "GET"
    ) {
      return jsonResponse([]);
    }
    if (path === "/api/projects/project-alpha/exports" && method === "GET") {
      return jsonResponse([]);
    }
    if (
      path === "/api/projects/project-alpha/indexing-runs" &&
      method === "POST"
    ) {
      indexingBody = JSON.parse(String(init?.body));
      return jsonResponse(
        {
          ...analysisRun,
          parameters: indexingBody?.parameters ?? {},
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
  await openProjectTab(user, "Indizieren");
  const indexingForm = await screen.findByRole("form", {
    name: "Indizierung starten",
  });

  await user.click(
    within(indexingForm).getByLabelText("Zeilenumbrüche ersetzen durch"),
  );
  const replacementInput = within(indexingForm).getByLabelText(
    "Ersatzzeichen für Zeilenumbrüche",
  );
  await user.clear(replacementInput);
  await user.type(replacementInput, "|");
  await user.click(
    within(indexingForm).getByLabelText("Text in Kleinschreibung umwandeln"),
  );
  await user.click(
    within(indexingForm).getByRole("button", {
      name: "Indizierung starten",
    }),
  );

  await waitFor(() => expect(indexingBody).not.toBeNull());
  expect(indexingBody).toMatchObject({
    dataset_version_id: "dataset-1",
    provider_id: "provider-local-ollama",
    model: "local-embed",
    parameters: {
      embedding_input_normalization: {
        newline_mode: "replace",
        newline_replacement: "|",
        lowercase: true,
      },
    },
  });
});

test("requires explicit OpenAI confirmation immediately before starting an indexing run", async () => {
  const user = userEvent.setup();
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
      return jsonResponse([localOllamaProvider, openAiProvider]);
    }
    if (path === "/api/projects/project-alpha" && method === "GET") {
      return jsonResponse(alphaProject);
    }
    if (path === "/api/projects/project-alpha/imports" && method === "GET") {
      return jsonResponse([importLog]);
    }
    if (
      path === "/api/projects/project-alpha/indexing-runs" &&
      method === "GET"
    ) {
      return jsonResponse([]);
    }
    if (path === "/api/projects/project-alpha/exports" && method === "GET") {
      return jsonResponse([]);
    }
    if (
      path === "/api/projects/project-alpha/indexing-runs" &&
      method === "POST"
    ) {
      runRequests += 1;
      const body = JSON.parse(String(init?.body));
      expect(body).toMatchObject({
        dataset_version_id: "dataset-1",
        provider_id: "provider-openai",
        model: "text-embedding-3-small",
        cloud_use_confirmed: true,
      });
      expect(body.analysis_profile_id).toBeUndefined();
      expect(body.parameters).toBeUndefined();
      return jsonResponse(
        {
          ...analysisRun,
          provider: "openai",
          provider_configuration_id: "provider-openai",
          provider_display_name: "OpenAI",
          model: "text-embedding-3-small",
          parameters: {},
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
  await openProjectTab(user, "Indizieren");

  const runForm = await screen.findByRole("form", {
    name: "Indizierung starten",
  });
  expect(
    within(runForm).queryByLabelText(/Ich bestätige/),
  ).not.toBeInTheDocument();
  await user.selectOptions(
    within(runForm).getByLabelText("Embedding-Provider"),
    "provider-openai",
  );
  expect(within(runForm).getByLabelText("Embedding-Modell")).toHaveValue(
    "text-embedding-3-small",
  );
  expect(
    within(within(runForm).getByLabelText("Embedding-Modell"))
      .getAllByRole("option")
      .map((option) => option.textContent),
  ).toEqual(["text-embedding-3-small"]);
  const confirmation = within(runForm).getByLabelText(/Ich bestätige/);
  const startButton = within(runForm).getByRole("button", {
    name: "Indizierung starten",
  });
  expect(startButton).toBeDisabled();
  expect(runRequests).toBe(0);

  await user.click(confirmation);
  expect(startButton).toBeEnabled();
  await user.click(startButton);

  await waitFor(() => expect(runRequests).toBe(1));
  await waitFor(() => expect(confirmation).not.toBeChecked());
});

test("requires confirmation before deleting dataset versions and indexing runs", async () => {
  const user = userEvent.setup();
  const confirm = vi.spyOn(window, "confirm");
  let datasetDeleteRequests = 0;
  let indexingDeleteRequests = 0;

  mockProjectFetch((path, method) => {
    if (
      path === "/api/projects/project-alpha/indexing-runs" &&
      method === "GET"
    ) {
      return jsonResponse([analysisRun]);
    }
    if (
      path === "/api/projects/project-alpha/dataset-versions/dataset-1" &&
      method === "DELETE"
    ) {
      datasetDeleteRequests += 1;
      return jsonResponse({
        id: "dataset-1",
        display_name: "Fixture dataset",
        deleted_at: "2026-07-22T00:00:02Z",
      });
    }
    if (
      path === "/api/projects/project-alpha/indexing-runs/run-1" &&
      method === "DELETE"
    ) {
      indexingDeleteRequests += 1;
      return new Response(null, { status: 204 });
    }
    return undefined;
  });
  render(<App />);

  await signIn(user);
  const projectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(projectList, "Alpha"));

  confirm.mockReturnValueOnce(false);
  await user.click(
    await screen.findByRole("button", { name: "Datensatz löschen" }),
  );
  expect(datasetDeleteRequests).toBe(0);

  confirm.mockReturnValueOnce(true);
  await user.click(screen.getByRole("button", { name: "Datensatz löschen" }));
  await waitFor(() => expect(datasetDeleteRequests).toBe(1));

  await openProjectTab(user, "Indizieren");
  const runsRegion = await screen.findByRole("region", {
    name: "Indizierungen",
  });
  expect(await within(runsRegion).findByText("queued")).toBeInTheDocument();

  confirm.mockReturnValueOnce(false);
  await user.click(within(runsRegion).getByRole("button", { name: "Löschen" }));
  expect(indexingDeleteRequests).toBe(0);

  confirm.mockReturnValueOnce(true);
  await user.click(within(runsRegion).getByRole("button", { name: "Löschen" }));
  await waitFor(() => expect(indexingDeleteRequests).toBe(1));
});

test("opens a project without an eager indexing request and gives the Indizieren view sole request ownership", async () => {
  const user = userEvent.setup();
  let runRequests = 0;
  let activeRequests = 0;
  let maximumActiveRequests = 0;
  let completeRequest: (response: Response) => void = () => undefined;
  mockProjectFetch((path, method, init) => {
    if (
      path === "/api/projects/project-alpha/indexing-runs" &&
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

  await openProjectTab(user, "Indizieren");
  await waitFor(() => expect(runRequests).toBe(1));
  expect(activeRequests).toBe(1);
  expect(maximumActiveRequests).toBe(1);

  completeRequest(jsonResponse([completedAnalysisRun]));
  const runsRegion = await screen.findByRole("region", {
    name: "Indizierungen",
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
      path === "/api/projects/project-alpha/indexing-runs" &&
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
  await openProjectTab(user, "Indizieren");
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
    name: "Indizierungen",
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
      path === "/api/projects/project-alpha/indexing-runs" &&
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
  await openProjectTab(user, "Indizieren");

  const runsRegion = await screen.findByRole("region", {
    name: "Indizierungen",
  });
  expect(await within(runsRegion).findByText("running")).toBeInTheDocument();
  expect(within(runsRegion).getAllByText("40%").length).toBeGreaterThan(0);
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

  await waitFor(
    () =>
      expect(within(runsRegion).getAllByText("70%").length).toBeGreaterThan(0),
    { timeout: 3000 },
  );
  expect(
    await within(runsRegion).findByText("completed", undefined, {
      timeout: 3000,
    }),
  ).toBeInTheDocument();
  expect(within(runsRegion).getAllByText("100%").length).toBeGreaterThan(0);
  expect(
    within(runsRegion).getByText(
      'Diagnose: {"embeddings_written":2,"clusters_written":1}',
    ),
  ).toBeInTheDocument();
  expect(runRequests).toBe(4);
}, 15000);

test("pauses indexing polling while hidden or outside the Indizieren tab and refreshes immediately when visible", async () => {
  const user = userEvent.setup();
  let visibilityState: DocumentVisibilityState = "visible";
  vi.spyOn(document, "visibilityState", "get").mockImplementation(
    () => visibilityState,
  );
  let runRequests = 0;
  mockProjectFetch((path, method) => {
    if (
      path === "/api/projects/project-alpha/indexing-runs" &&
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
  await openProjectTab(user, "Indizieren");
  const runsRegion = await screen.findByRole("region", {
    name: "Indizierungen",
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

  await openProjectTab(user, "Import");
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
      path === "/api/projects/project-alpha/indexing-runs" &&
      method === "GET"
    ) {
      alphaRunRequests += 1;
      return pendingAlphaPoll;
    }
    if (
      path === "/api/projects/project-beta/indexing-runs" &&
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
  await openProjectTab(user, "Indizieren");
  await waitFor(() => expect(alphaRunRequests).toBe(1));

  await openProjectsPage(user);
  const switchProjectList = await screen.findByRole("region", {
    name: "Bestehende Projekte",
  });
  await user.click(getProjectRow(switchProjectList, "Beta"));
  await waitFor(() =>
    expect(screen.getByLabelText("Projektname")).toHaveValue("Beta"),
  );
  resolveAlphaPoll(
    jsonResponse([
      { ...analysisRun, status: "failed", error_message: "stale" },
    ]),
  );
  await pendingAlphaPoll;
  await openProjectTab(user, "Indizieren");

  const runsRegion = await screen.findByRole("region", {
    name: "Indizierungen",
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
      path === "/api/projects/project-alpha/indexing-runs" &&
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
  await openProjectTab(user, "Indizieren");
  await waitFor(() => expect(runRequests).toBe(1));

  await signOutThroughGlobalMenu(user);
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
      path === "/api/projects/project-alpha/indexing-runs" &&
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
  await openProjectTab(user, "Indizieren");
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
      path === "/api/projects/project-alpha/indexing-runs" &&
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
  await openProjectTab(user, "Indizieren");

  expect(
    await screen.findByRole("heading", { name: "Lokaler Zugriff" }),
  ).toBeInTheDocument();
  expect(window.sessionStorage.getItem(sessionTokenStorageKey)).toBeNull();
  expect(runRequests).toBe(1);
});
