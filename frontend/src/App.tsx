import { useState } from "react";
import type { FormEvent } from "react";
import "./App.css";

type ApiUser = {
  id: string;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
};

type User = {
  id: string;
  username: string;
  firstName: string;
  lastName: string;
  email: string;
};

type ApiProject = {
  id: string;
  name: string;
  lifecycle_state: string;
  created_at: string;
  updated_at: string;
};

type Project = {
  id: string;
  name: string;
  lifecycleState: string;
  updatedAt: string;
};

type ApiImportLog = {
  id: string;
  source_type: string;
  source_name: string;
  status: string;
  failure_reason: string | null;
  total_records: number;
  valid_records: number;
  skipped_records: number;
  dataset_version_id: string | null;
};

type ApiImportLogEntry = {
  source_location: string;
  reason: string;
  context: Record<string, unknown>;
};

type ImportLog = {
  id: string;
  sourceType: string;
  sourceName: string;
  status: string;
  failureReason: string | null;
  totalRecords: number;
  validRecords: number;
  skippedRecords: number;
  datasetVersionId: string | null;
};

type ApiProviderConfiguration = {
  provider: string;
  endpoint_url: string | null;
  manual_models: string[];
  api_key_set: boolean;
  updated_at: string;
};

type ProviderConfiguration = {
  provider: string;
  endpointUrl: string | null;
  manualModels: string[];
  apiKeySet: boolean;
  updatedAt: string;
};

type ApiAnalysisProfile = {
  id: string;
  project_id: string;
  name: string;
  provider: string;
  model: string;
  is_cloud_provider: boolean;
  thresholds: Record<string, unknown>;
  algorithm_settings: Record<string, unknown>;
  prompt_identifier: string | null;
  prompt_template: string | null;
};

type AnalysisProfile = {
  id: string;
  projectId: string;
  name: string;
  provider: string;
  model: string;
  isCloudProvider: boolean;
  thresholds: Record<string, unknown>;
  algorithmSettings: Record<string, unknown>;
  promptIdentifier: string | null;
  promptTemplate: string | null;
};

type ApiAnalysisRun = {
  id: string;
  project_id: string;
  dataset_version_id: string;
  analysis_profile_id: string;
  status: string;
  progress: number;
  profile_snapshot: Record<string, unknown>;
  provider: string;
  model: string;
  parameters: Record<string, unknown>;
  error_message: string | null;
  diagnostics: Record<string, unknown>;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

type AnalysisRun = {
  id: string;
  projectId: string;
  datasetVersionId: string;
  analysisProfileId: string;
  status: string;
  progress: number;
  profileSnapshot: Record<string, unknown>;
  provider: string;
  model: string;
  parameters: Record<string, unknown>;
  errorMessage: string | null;
  diagnostics: Record<string, unknown>;
  startedAt: string | null;
  completedAt: string | null;
  createdAt: string;
  updatedAt: string;
};

type Session = {
  token: string;
  user: User;
};

const API_BASE = import.meta.env.VITE_SKM_API_BASE_URL ?? "";

function toUser(user: ApiUser): User {
  return {
    id: user.id,
    username: user.username,
    firstName: user.first_name,
    lastName: user.last_name,
    email: user.email,
  };
}

function toProject(project: ApiProject): Project {
  return {
    id: project.id,
    name: project.name,
    lifecycleState: project.lifecycle_state,
    updatedAt: project.updated_at,
  };
}

function toImportLog(log: ApiImportLog): ImportLog {
  return {
    id: log.id,
    sourceType: log.source_type,
    sourceName: log.source_name,
    status: log.status,
    failureReason: log.failure_reason,
    totalRecords: log.total_records,
    validRecords: log.valid_records,
    skippedRecords: log.skipped_records,
    datasetVersionId: log.dataset_version_id,
  };
}

function toProviderConfiguration(
  configuration: ApiProviderConfiguration,
): ProviderConfiguration {
  return {
    provider: configuration.provider,
    endpointUrl: configuration.endpoint_url,
    manualModels: configuration.manual_models,
    apiKeySet: configuration.api_key_set,
    updatedAt: configuration.updated_at,
  };
}

function toAnalysisProfile(profile: ApiAnalysisProfile): AnalysisProfile {
  return {
    id: profile.id,
    projectId: profile.project_id,
    name: profile.name,
    provider: profile.provider,
    model: profile.model,
    isCloudProvider: profile.is_cloud_provider,
    thresholds: profile.thresholds,
    algorithmSettings: profile.algorithm_settings,
    promptIdentifier: profile.prompt_identifier,
    promptTemplate: profile.prompt_template,
  };
}

function toAnalysisRun(run: ApiAnalysisRun): AnalysisRun {
  return {
    id: run.id,
    projectId: run.project_id,
    datasetVersionId: run.dataset_version_id,
    analysisProfileId: run.analysis_profile_id,
    status: run.status,
    progress: run.progress,
    profileSnapshot: run.profile_snapshot,
    provider: run.provider,
    model: run.model,
    parameters: run.parameters,
    errorMessage: run.error_message,
    diagnostics: run.diagnostics,
    startedAt: run.started_at,
    completedAt: run.completed_at,
    createdAt: run.created_at,
    updatedAt: run.updated_at,
  };
}

function parseModels(value: FormDataEntryValue | null): string[] {
  return String(value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

async function apiRequest<T>(
  path: string,
  options: RequestInit & { token?: string } = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    throw new Error(`request failed with status ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

function readFileAsText(file: File): Promise<string> {
  if (typeof file.text === "function") {
    return file.text();
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => resolve(String(reader.result ?? "")));
    reader.addEventListener("error", () => reject(reader.error));
    reader.readAsText(file);
  });
}

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [importLogs, setImportLogs] = useState<ImportLog[]>([]);
  const [importLogEntries, setImportLogEntries] = useState<ApiImportLogEntry[]>(
    [],
  );
  const [providers, setProviders] = useState<ProviderConfiguration[]>([]);
  const [analysisProfiles, setAnalysisProfiles] = useState<AnalysisProfile[]>(
    [],
  );
  const [analysisRuns, setAnalysisRuns] = useState<AnalysisRun[]>([]);
  const [message, setMessage] = useState("");
  const [passwordNotice, setPasswordNotice] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function loadUsers(token: string) {
    const apiUsers = await apiRequest<ApiUser[]>("/api/users", { token });
    setUsers(apiUsers.map(toUser));
  }

  async function loadProjects(token: string) {
    const apiProjects = await apiRequest<ApiProject[]>("/api/projects", {
      token,
    });
    setProjects(apiProjects.map(toProject));
  }

  async function loadImportLogs(token: string, projectId: string) {
    const apiLogs = await apiRequest<ApiImportLog[]>(
      `/api/projects/${projectId}/imports`,
      { token },
    );
    setImportLogs(apiLogs.map(toImportLog));
  }

  async function loadProviders(token: string) {
    const apiProviders = await apiRequest<ApiProviderConfiguration[]>(
      "/api/providers",
      { token },
    );
    setProviders(apiProviders.map(toProviderConfiguration));
  }

  async function loadAnalysisProfiles(token: string, projectId: string) {
    const apiProfiles = await apiRequest<ApiAnalysisProfile[]>(
      `/api/projects/${projectId}/analysis-profiles`,
      { token },
    );
    setAnalysisProfiles(apiProfiles.map(toAnalysisProfile));
  }

  async function loadAnalysisRuns(token: string, projectId: string) {
    const apiRuns = await apiRequest<ApiAnalysisRun[]>(
      `/api/projects/${projectId}/analysis-runs`,
      { token },
    );
    setAnalysisRuns(apiRuns.map(toAnalysisRun));
  }

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const username = String(form.get("username") ?? "").trim();
    const password = String(form.get("password") ?? "");
    try {
      const response = await apiRequest<{
        access_token: string;
        user: ApiUser;
      }>("/api/auth/sign-in", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      const nextSession = {
        token: response.access_token,
        user: toUser(response.user),
      };
      setSession(nextSession);
      await Promise.all([
        loadUsers(nextSession.token),
        loadProjects(nextSession.token),
      ]);
      await loadProviders(nextSession.token).catch(() => setProviders([]));
      setMessage("Angemeldet. Geschuetzte Workflows sind verfuegbar.");
    } catch {
      setSession(null);
      setUsers([]);
      setProjects([]);
      setCurrentProject(null);
      setImportLogs([]);
      setImportLogEntries([]);
      setProviders([]);
      setAnalysisProfiles([]);
      setAnalysisRuns([]);
      setMessage(
        "Anmeldung fehlgeschlagen oder Backend nicht erreichbar. Bitte Zugangsdaten und lokalen Dienst pruefen.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function createProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (session === null) {
      return;
    }
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const name = String(form.get("projectName") ?? "").trim();
    setIsLoading(true);
    try {
      const created = await apiRequest<ApiProject>("/api/projects", {
        method: "POST",
        token: session.token,
        body: JSON.stringify({ name }),
      });
      const project = toProject(created);
      setProjects((existing) => [project, ...existing]);
      setCurrentProject(project);
      setImportLogs([]);
      setImportLogEntries([]);
      setAnalysisProfiles([]);
      setAnalysisRuns([]);
      formElement.reset();
      setMessage("Projekt erstellt und geoeffnet.");
    } catch {
      setMessage(
        "Projekt konnte nicht erstellt werden. Bitte Namen und Backend pruefen.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function openProject(projectId: string) {
    if (session === null) {
      return;
    }
    try {
      const opened = await apiRequest<ApiProject>(
        `/api/projects/${projectId}`,
        {
          token: session.token,
        },
      );
      setCurrentProject(toProject(opened));
      await loadImportLogs(session.token, projectId);
      await loadAnalysisProfiles(session.token, projectId).catch(() =>
        setAnalysisProfiles([]),
      );
      await loadAnalysisRuns(session.token, projectId).catch(() =>
        setAnalysisRuns([]),
      );
      setImportLogEntries([]);
      setMessage("Projekt geoeffnet.");
    } catch {
      setMessage("Projekt konnte nicht geoeffnet werden.");
    }
  }

  async function renameProject(projectId: string, name: string) {
    if (session === null || !name.trim()) {
      return;
    }
    try {
      const renamed = await apiRequest<ApiProject>(
        `/api/projects/${projectId}`,
        {
          method: "PATCH",
          token: session.token,
          body: JSON.stringify({ name }),
        },
      );
      const project = toProject(renamed);
      setProjects((existing) =>
        existing.map((item) => (item.id === projectId ? project : item)),
      );
      if (currentProject?.id === projectId) {
        setCurrentProject(project);
      }
      setMessage("Projekt umbenannt.");
    } catch {
      setMessage("Projekt konnte nicht umbenannt werden.");
    }
  }

  async function deleteProject(
    event: FormEvent<HTMLFormElement>,
    projectId: string,
  ) {
    event.preventDefault();
    if (session === null) {
      return;
    }
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const confirmationName = String(form.get("confirmationName") ?? "");
    try {
      await apiRequest<void>(`/api/projects/${projectId}`, {
        method: "DELETE",
        token: session.token,
        body: JSON.stringify({ confirmation_name: confirmationName }),
      });
      setProjects((existing) =>
        existing.filter((project) => project.id !== projectId),
      );
      if (currentProject?.id === projectId) {
        setCurrentProject(null);
        setImportLogs([]);
        setImportLogEntries([]);
        setAnalysisProfiles([]);
        setAnalysisRuns([]);
      }
      setMessage("Projekt geloescht.");
    } catch {
      setMessage(
        "Projekt konnte nicht geloescht werden. Namensbestaetigung pruefen.",
      );
    }
  }

  async function createUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (session === null) {
      return;
    }
    setIsLoading(true);
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const username = String(form.get("username") ?? "").trim();
    const firstName = String(form.get("firstName") ?? "").trim();
    const lastName = String(form.get("lastName") ?? "").trim();
    const email = String(form.get("email") ?? "").trim();
    const password = String(form.get("password") ?? "");
    try {
      const created = await apiRequest<ApiUser>("/api/users", {
        method: "POST",
        token: session.token,
        body: JSON.stringify({
          username,
          first_name: firstName,
          last_name: lastName,
          email,
          password,
        }),
      });
      setUsers((existing) => [...existing, toUser(created)]);
      formElement.reset();
      setMessage("User angelegt. Passwortwert bleibt write-only.");
    } catch {
      setMessage(
        "User konnte nicht angelegt werden. Bitte Eingaben und Backend pruefen.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function updateUser(
    userId: string,
    field: keyof Omit<User, "id">,
    value: string,
  ) {
    if (session === null) {
      return;
    }
    const previous = users;
    const nextUsers = users.map((user) =>
      user.id === userId ? { ...user, [field]: value } : user,
    );
    setUsers(nextUsers);
    const updated = nextUsers.find((user) => user.id === userId);
    if (updated === undefined) {
      return;
    }
    try {
      const saved = await apiRequest<ApiUser>(`/api/users/${userId}`, {
        method: "PATCH",
        token: session.token,
        body: JSON.stringify({
          username: updated.username,
          first_name: updated.firstName,
          last_name: updated.lastName,
          email: updated.email,
        }),
      });
      setUsers((existing) =>
        existing.map((user) => (user.id === userId ? toUser(saved) : user)),
      );
      setMessage("Userdaten aktualisiert.");
    } catch {
      setUsers(previous);
      setMessage("Userdaten konnten nicht gespeichert werden.");
    }
  }

  async function setPassword(userId: string, password: string) {
    if (session === null || !password) {
      return;
    }
    try {
      await apiRequest<void>(`/api/users/${userId}/password`, {
        method: "POST",
        token: session.token,
        body: JSON.stringify({ password }),
      });
      setPasswordNotice(
        "Passwortwert bleibt write-only und wurde gespeichert.",
      );
    } catch {
      setPasswordNotice("Passwort konnte nicht gespeichert werden.");
    }
  }

  async function deleteUser(userId: string) {
    if (session === null) {
      return;
    }
    if (session.user.id === userId) {
      setMessage(
        "Self-Delete ist gesperrt, damit kein lokaler Lockout entsteht.",
      );
      return;
    }
    try {
      await apiRequest<void>(`/api/users/${userId}`, {
        method: "DELETE",
        token: session.token,
      });
      setUsers((existing) => existing.filter((user) => user.id !== userId));
      setMessage("User geloescht.");
    } catch {
      setMessage("User konnte nicht geloescht werden.");
    }
  }

  async function importFile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (session === null || currentProject === null) {
      return;
    }
    const formElement = event.currentTarget;
    const input = formElement.elements.namedItem("importFile");
    const file =
      input instanceof HTMLInputElement
        ? (input.files?.[0] ?? null)
        : new FormData(formElement).get("importFile");
    if (!(file instanceof File)) {
      setMessage("Bitte CSV- oder JSON-Datei auswaehlen.");
      return;
    }
    const sourceType = file.name.toLowerCase().endsWith(".json")
      ? "json"
      : "csv";
    setIsLoading(true);
    try {
      const content = await readFileAsText(file);
      const result = await apiRequest<{
        log: ApiImportLog;
        skipped_entries: ApiImportLogEntry[];
      }>(`/api/projects/${currentProject.id}/imports`, {
        method: "POST",
        token: session.token,
        body: JSON.stringify({
          source_type: sourceType,
          source_name: file.name,
          content,
        }),
      });
      setImportLogs((existing) => [toImportLog(result.log), ...existing]);
      setImportLogEntries(result.skipped_entries);
      setMessage(
        `Import abgeschlossen: ${result.log.valid_records} importiert, ${result.log.skipped_records} uebersprungen, ${result.log.total_records} gelesen.`,
      );
      formElement.reset();
    } catch {
      setMessage(
        "Import fehlgeschlagen. Logeintrag und Validierungsdetails pruefen.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function inspectImportLog(logId: string) {
    if (session === null || currentProject === null) {
      return;
    }
    try {
      const entries = await apiRequest<ApiImportLogEntry[]>(
        `/api/projects/${currentProject.id}/imports/${logId}/entries`,
        { token: session.token },
      );
      setImportLogEntries(entries);
      setMessage("Import-Log geladen.");
    } catch {
      setMessage("Import-Log konnte nicht geladen werden.");
    }
  }

  async function configureProvider(
    event: FormEvent<HTMLFormElement>,
    provider: "openai" | "vllm",
  ) {
    event.preventDefault();
    if (session === null) {
      return;
    }
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const payload: Record<string, unknown> = {
      manual_models: parseModels(form.get("manualModels")),
    };
    if (provider === "openai") {
      const apiKey = String(form.get("apiKey") ?? "");
      payload.api_key = apiKey || null;
      payload.remove_api_key = form.get("removeApiKey") === "on";
    } else {
      payload.endpoint_url = String(form.get("endpointUrl") ?? "").trim();
    }
    try {
      const updated = await apiRequest<ApiProviderConfiguration>(
        `/api/providers/${provider}`,
        {
          method: "PUT",
          token: session.token,
          body: JSON.stringify(payload),
        },
      );
      setProviders((existing) => [
        toProviderConfiguration(updated),
        ...existing.filter((item) => item.provider !== provider),
      ]);
      formElement.reset();
      setMessage(
        provider === "openai"
          ? "OpenAI Provider gespeichert. API-Key bleibt write-only."
          : "vLLM Provider gespeichert.",
      );
    } catch {
      setMessage("Provider-Konfiguration konnte nicht gespeichert werden.");
    }
  }

  async function createAnalysisProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (session === null || currentProject === null) {
      return;
    }
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const similarity = Number.parseFloat(String(form.get("similarity") ?? ""));
    const thresholds = Number.isFinite(similarity) ? { similarity } : {};
    try {
      const created = await apiRequest<ApiAnalysisProfile>(
        `/api/projects/${currentProject.id}/analysis-profiles`,
        {
          method: "POST",
          token: session.token,
          body: JSON.stringify({
            name: String(form.get("profileName") ?? "").trim(),
            provider: String(form.get("provider") ?? ""),
            model: String(form.get("model") ?? "").trim(),
            thresholds,
            algorithm_settings: {
              algorithm:
                String(form.get("algorithm") ?? "").trim() || "default",
            },
            prompt_identifier:
              String(form.get("promptIdentifier") ?? "").trim() || null,
          }),
        },
      );
      setAnalysisProfiles((existing) => [
        toAnalysisProfile(created),
        ...existing,
      ]);
      formElement.reset();
      setMessage("Analyseprofil gespeichert.");
    } catch {
      setMessage(
        "Analyseprofil konnte nicht gespeichert werden. Provider und Modell pruefen.",
      );
    }
  }

  async function startAnalysisRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (session === null || currentProject === null) {
      return;
    }
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const datasetVersionId = String(form.get("datasetVersionId") ?? "");
    const analysisProfileId = String(form.get("analysisProfileId") ?? "");
    const mode = String(form.get("runMode") ?? "").trim() || "fixture";
    try {
      const created = await apiRequest<ApiAnalysisRun>(
        `/api/projects/${currentProject.id}/analysis-runs`,
        {
          method: "POST",
          token: session.token,
          body: JSON.stringify({
            dataset_version_id: datasetVersionId,
            analysis_profile_id: analysisProfileId,
            parameters: { mode },
          }),
        },
      );
      setAnalysisRuns((existing) => [toAnalysisRun(created), ...existing]);
      formElement.reset();
      setMessage(
        `Analyse gestartet: ${created.status}, Fortschritt ${created.progress}%.`,
      );
    } catch {
      setMessage(
        "Analyse konnte nicht gestartet werden. Dataset-Version und Profil pruefen.",
      );
    }
  }

  const configuredModelHint =
    providers
      .flatMap((provider) =>
        provider.manualModels.map((model) => `${provider.provider}:${model}`),
      )
      .join(", ") || "Noch keine Modelle konfiguriert.";
  const runnableDatasetLogs = importLogs.filter(
    (log) => log.datasetVersionId !== null,
  );

  if (session === null) {
    return (
      <main className="auth-shell">
        <section className="auth-card" aria-labelledby="signin-title">
          <p className="eyebrow">Support Knowledge Miner</p>
          <h1 id="signin-title">Lokaler Zugriff</h1>
          <p className="intro">
            Geschuetzte Projekt-, Import- und Kurationsbereiche starten erst
            nach erfolgreicher Backend-Anmeldung. Fehler nennen nie, ob
            Benutzername oder Passwort falsch war.
          </p>
          <form className="stack" onSubmit={signIn}>
            <label>
              Benutzername
              <input name="username" autoComplete="username" />
            </label>
            <label>
              Passwort
              <input
                name="password"
                type="password"
                autoComplete="current-password"
              />
            </label>
            <button type="submit" disabled={isLoading}>
              {isLoading ? "Pruefe Anmeldung" : "Anmelden"}
            </button>
          </form>
          {message && (
            <p role="alert" className="status error">
              {message}
            </p>
          )}
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">T003 Project Home</p>
          <h1>Projektverwaltung</h1>
        </div>
        <button
          type="button"
          className="secondary"
          onClick={() => setSession(null)}
        >
          Abmelden
        </button>
      </header>

      {message && (
        <p role="status" className="status">
          {message}
        </p>
      )}

      <section className="panel project-summary" aria-label="Aktuelles Projekt">
        <p className="eyebrow">Aktuelles Projekt</p>
        {currentProject ? (
          <div>
            <h2>{currentProject.name}</h2>
            <p className="hint">
              Status: {currentProject.lifecycleState}; zuletzt aktualisiert:{" "}
              {currentProject.updatedAt}
            </p>
          </div>
        ) : (
          <p className="hint">Noch kein Projekt geoeffnet.</p>
        )}
      </section>

      <section className="panel-grid">
        <form
          className="panel stack"
          onSubmit={(event) => configureProvider(event, "openai")}
          aria-label="OpenAI Provider konfigurieren"
        >
          <p className="eyebrow">T005 Provider</p>
          <h2>OpenAI konfigurieren</h2>
          <p className="hint">
            API-Key wird nur geschrieben oder geloescht und nie angezeigt.
            OpenAI-Profile sind als Cloud-Nutzung markiert.
          </p>
          <label>
            Neuer OpenAI API-Key
            <input
              name="apiKey"
              type="password"
              autoComplete="off"
              placeholder="sk-..."
            />
          </label>
          <label>
            OpenAI Modelle
            <input
              name="manualModels"
              placeholder="text-embedding-3-small, gpt-4.1-mini"
            />
          </label>
          <label className="inline-check">
            <input name="removeApiKey" type="checkbox" />
            Gespeicherten API-Key entfernen
          </label>
          <button type="submit">OpenAI speichern</button>
        </form>

        <form
          className="panel stack"
          onSubmit={(event) => configureProvider(event, "vllm")}
          aria-label="vLLM Provider konfigurieren"
        >
          <p className="eyebrow">Lokal</p>
          <h2>vLLM konfigurieren</h2>
          <p className="hint">
            Lokale vLLM-Endpoints bleiben explizit und koennen mehrere Modelle
            bereitstellen.
          </p>
          <label>
            Endpoint URL
            <input name="endpointUrl" placeholder="http://localhost:8000" />
          </label>
          <label>
            vLLM Modelle
            <input name="manualModels" placeholder="local-embed, local-chat" />
          </label>
          <button type="submit">vLLM speichern</button>
        </form>

        <section className="panel" aria-label="Provider Konfigurationen">
          <h2>Provider Konfigurationen</h2>
          <div className="user-list">
            {providers.length === 0 && (
              <p className="hint">Noch keine Provider konfiguriert.</p>
            )}
            {providers.map((provider) => (
              <article className="user-card" key={provider.provider}>
                <div className="user-heading">
                  <strong>{provider.provider}</strong>
                  {provider.provider === "openai" && (
                    <span>
                      {provider.apiKeySet ? "API-Key gesetzt" : "Kein API-Key"}
                    </span>
                  )}
                </div>
                {provider.endpointUrl && (
                  <p className="hint">Endpoint: {provider.endpointUrl}</p>
                )}
                <p className="hint">
                  Modelle:{" "}
                  {provider.manualModels.length
                    ? provider.manualModels.join(", ")
                    : "keine"}
                </p>
              </article>
            ))}
          </div>
        </section>
      </section>

      {currentProject && (
        <>
          <section className="panel-grid">
            <form
              className="panel stack"
              onSubmit={createAnalysisProfile}
              aria-label="Analyseprofil erstellen"
            >
              <p className="eyebrow">T005 Profile</p>
              <h2>Analyseprofil erstellen</h2>
              <p className="hint">
                Konfigurierte Modelle: {configuredModelHint}
              </p>
              <label>
                Profilname
                <input name="profileName" />
              </label>
              <label>
                Provider
                <select name="provider" defaultValue="vllm">
                  <option value="vllm">vLLM lokal</option>
                  <option value="openai">OpenAI Cloud</option>
                </select>
              </label>
              <label>
                Modell
                <input name="model" placeholder="local-embed" />
              </label>
              <label>
                Similarity Threshold
                <input name="similarity" placeholder="0.78" />
              </label>
              <label>
                Algorithmus
                <input name="algorithm" placeholder="hdbscan" />
              </label>
              <label>
                Prompt-ID
                <input name="promptIdentifier" placeholder="faq-v1" />
              </label>
              <button type="submit">Profil speichern</button>
            </form>

            <section className="panel" aria-label="Analyseprofile">
              <h2>Analyseprofile</h2>
              <div className="user-list">
                {analysisProfiles.length === 0 && (
                  <p className="hint">
                    Noch keine Analyseprofile fuer dieses Projekt.
                  </p>
                )}
                {analysisProfiles.map((profile) => (
                  <article className="user-card" key={profile.id}>
                    <div className="user-heading">
                      <strong>{profile.name}</strong>
                      <span>
                        {profile.provider}/{profile.model}
                      </span>
                    </div>
                    {profile.isCloudProvider && (
                      <p className="status warning">
                        Cloud-Nutzung: OpenAI Profil sendet spaetere
                        Analyseinhalte an den konfigurierten Cloud-Provider.
                      </p>
                    )}
                    <p className="hint">
                      Thresholds: {JSON.stringify(profile.thresholds)}
                    </p>
                    <p className="hint">
                      Algorithmus: {JSON.stringify(profile.algorithmSettings)}
                    </p>
                    {profile.promptIdentifier && (
                      <p className="hint">Prompt: {profile.promptIdentifier}</p>
                    )}
                  </article>
                ))}
              </div>
            </section>
          </section>

          <section className="panel-grid">
            <form
              className="panel stack"
              onSubmit={startAnalysisRun}
              aria-label="Analyse starten"
            >
              <p className="eyebrow">T006 Run Monitor</p>
              <h2>Analyse starten</h2>
              <p className="hint">
                Lokale Fixture-Workflows koennen ohne OpenAI abgeschlossen
                werden. OpenAI-Profile bleiben als Cloud-Nutzung sichtbar.
              </p>
              <label>
                Dataset-Version
                <select name="datasetVersionId">
                  {runnableDatasetLogs.map((log) => (
                    <option
                      key={log.datasetVersionId ?? log.id}
                      value={log.datasetVersionId ?? ""}
                    >
                      {log.sourceName} / {log.datasetVersionId}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Analyseprofil
                <select name="analysisProfileId">
                  {analysisProfiles.map((profile) => (
                    <option key={profile.id} value={profile.id}>
                      {profile.name} ({profile.provider}/{profile.model})
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Run-Modus
                <input name="runMode" placeholder="fixture" />
              </label>
              <button
                type="submit"
                disabled={
                  runnableDatasetLogs.length === 0 ||
                  analysisProfiles.length === 0
                }
              >
                Analyse starten
              </button>
            </form>

            <section className="panel" aria-label="Analyse Runs">
              <h2>Analyse Runs</h2>
              <div className="user-list">
                {analysisRuns.length === 0 && (
                  <p className="hint">
                    Noch keine Analyse-Runs fuer dieses Projekt.
                  </p>
                )}
                {analysisRuns.map((run) => (
                  <article className="user-card" key={run.id}>
                    <div className="user-heading">
                      <strong>{run.status}</strong>
                      <span>{run.progress}%</span>
                    </div>
                    <p className="hint">
                      Provider/Modell: {run.provider}/{run.model}
                    </p>
                    <p className="hint">
                      Dataset-Version: {run.datasetVersionId}
                    </p>
                    <p className="hint">
                      Profil-Snapshot:{" "}
                      {String(
                        run.profileSnapshot.name ?? run.analysisProfileId,
                      )}
                    </p>
                    <p className="hint">
                      Erstellt: {run.createdAt}; gestartet:{" "}
                      {run.startedAt ?? "noch nicht"}; abgeschlossen:{" "}
                      {run.completedAt ?? "noch nicht"}
                    </p>
                    {run.errorMessage && (
                      <p className="error">{run.errorMessage}</p>
                    )}
                    <p className="hint">
                      Diagnose: {JSON.stringify(run.diagnostics)}
                    </p>
                  </article>
                ))}
              </div>
            </section>
          </section>

          <section className="panel-grid">
            <form
              className="panel stack"
              onSubmit={importFile}
              aria-label="Import starten"
            >
              <p className="eyebrow">T004 Import</p>
              <h2>CSV/JSON importieren</h2>
              <p className="hint">
                Erwartete Felder: ticketid, messagegroupid, message, answer.
                Ungueltige Datensaetze werden uebersprungen und protokolliert.
              </p>
              <label>
                Importdatei
                <input name="importFile" type="file" accept=".csv,.json" />
              </label>
              <button type="submit" disabled={isLoading}>
                Import starten
              </button>
            </form>

            <section className="panel" aria-label="Importprotokolle">
              <h2>Importprotokolle</h2>
              <div className="user-list">
                {importLogs.length === 0 && (
                  <p className="hint">
                    Noch keine Imports fuer dieses Projekt.
                  </p>
                )}
                {importLogs.map((log) => (
                  <article className="user-card" key={log.id}>
                    <div className="user-heading">
                      <strong>{log.sourceName}</strong>
                      <span>{log.status}</span>
                    </div>
                    <p className="hint">
                      Total: {log.totalRecords}; importiert: {log.validRecords};
                      uebersprungen: {log.skippedRecords}
                    </p>
                    {log.failureReason && (
                      <p className="error">{log.failureReason}</p>
                    )}
                    {log.datasetVersionId && (
                      <p className="hint">
                        Dataset-Version: {log.datasetVersionId}
                      </p>
                    )}
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => inspectImportLog(log.id)}
                    >
                      Logdetails anzeigen
                    </button>
                  </article>
                ))}
              </div>
              {importLogEntries.length > 0 && (
                <div className="log-detail" aria-label="Import Logdetails">
                  <h2>Validierungsdetails</h2>
                  {importLogEntries.map((entry) => (
                    <p
                      className="hint"
                      key={`${entry.source_location}-${entry.reason}`}
                    >
                      {entry.source_location}: {entry.reason}
                    </p>
                  ))}
                </div>
              )}
            </section>
          </section>
        </>
      )}

      <section className="panel-grid">
        <form
          className="panel stack"
          onSubmit={createProject}
          aria-label="Projekt erstellen"
        >
          <h2>Projekt erstellen</h2>
          <label>
            Projektname
            <input name="projectName" />
          </label>
          <button type="submit" disabled={isLoading}>
            Projekt erstellen
          </button>
        </form>

        <section className="panel" aria-label="Bestehende Projekte">
          <h2>Bestehende Projekte</h2>
          <div className="user-list">
            {projects.length === 0 && (
              <p className="hint">Noch keine Projekte vorhanden.</p>
            )}
            {projects.map((project) => (
              <article className="user-card" key={project.id}>
                <div className="user-heading">
                  <strong>{project.name}</strong>
                  {currentProject?.id === project.id && <span>Geoeffnet</span>}
                </div>
                <label>
                  Projektname
                  <input
                    defaultValue={project.name}
                    onBlur={(event) =>
                      renameProject(project.id, event.target.value)
                    }
                  />
                </label>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => openProject(project.id)}
                >
                  Projekt oeffnen
                </button>
                <form
                  className="stack"
                  onSubmit={(event) => deleteProject(event, project.id)}
                >
                  <label>
                    Projektname bestaetigen
                    <input name="confirmationName" />
                  </label>
                  <button type="submit" className="danger">
                    Projekt loeschen
                  </button>
                </form>
              </article>
            ))}
          </div>
        </section>
      </section>

      <section className="panel-grid">
        <form
          className="panel stack"
          onSubmit={createUser}
          aria-label="User anlegen"
        >
          <h2>User anlegen</h2>
          <label>
            Benutzername
            <input name="username" />
          </label>
          <label>
            Vorname
            <input name="firstName" />
          </label>
          <label>
            Nachname
            <input name="lastName" />
          </label>
          <label>
            E-Mail
            <input name="email" type="email" />
          </label>
          <label>
            Initiales Passwort
            <input
              name="password"
              type="password"
              autoComplete="new-password"
            />
          </label>
          <button type="submit" disabled={isLoading}>
            User erstellen
          </button>
        </form>

        <section className="panel" aria-label="Bestehende User">
          <h2>Bestehende User</h2>
          <div className="user-list">
            {users.map((user) => {
              const isSelf = user.id === session.user.id;
              return (
                <article className="user-card" key={user.id}>
                  <div className="user-heading">
                    <strong>{user.username}</strong>
                    {isSelf && <span>Aktueller User</span>}
                  </div>
                  <label>
                    Benutzername
                    <input
                      value={user.username}
                      onChange={(event) =>
                        updateUser(user.id, "username", event.target.value)
                      }
                    />
                  </label>
                  <label>
                    Vorname
                    <input
                      value={user.firstName}
                      onChange={(event) =>
                        updateUser(user.id, "firstName", event.target.value)
                      }
                    />
                  </label>
                  <label>
                    Nachname
                    <input
                      value={user.lastName}
                      onChange={(event) =>
                        updateUser(user.id, "lastName", event.target.value)
                      }
                    />
                  </label>
                  <label>
                    E-Mail
                    <input
                      value={user.email}
                      onChange={(event) =>
                        updateUser(user.id, "email", event.target.value)
                      }
                    />
                  </label>
                  <label>
                    Neues Passwort fuer diesen User
                    <input
                      type="password"
                      autoComplete="new-password"
                      onBlur={(event) =>
                        setPassword(user.id, event.target.value)
                      }
                    />
                  </label>
                  {passwordNotice && <p className="hint">{passwordNotice}</p>}
                  <button
                    type="button"
                    className="danger"
                    disabled={isSelf}
                    onClick={() => deleteUser(user.id)}
                  >
                    {isSelf ? "Self-Delete gesperrt" : "User loeschen"}
                  </button>
                  {isSelf && (
                    <p className="hint">
                      Ein User kann sich nicht selbst loeschen. Das Backend
                      erzwingt dieselbe Regel.
                    </p>
                  )}
                </article>
              );
            })}
          </div>
        </section>
      </section>
    </main>
  );
}

export default App;
