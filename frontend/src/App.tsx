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
      setMessage("Angemeldet. Geschuetzte Workflows sind verfuegbar.");
    } catch {
      setSession(null);
      setUsers([]);
      setProjects([]);
      setCurrentProject(null);
      setImportLogs([]);
      setImportLogEntries([]);
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

      {currentProject && (
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
                <p className="hint">Noch keine Imports fuer dieses Projekt.</p>
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
