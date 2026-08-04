import { Fragment, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import "./App.css";

type ApiUser = {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
};

type User = {
  id: string;
  name: string;
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
  dataset_display_name: string | null;
  dataset_deleted_at: string | null;
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
  datasetDisplayName: string | null;
  datasetDeletedAt: string | null;
};

const MAX_IMPORT_BYTES = 512 * 1024 * 1024;

type ApiProviderConfiguration = {
  provider: string;
  endpoint_url: string | null;
  manual_models: string[];
  llm_models?: string[];
  api_key_set: boolean;
  updated_at: string;
};

type ApiProviderCheck = {
  provider: string;
  ok: boolean;
  models: string[];
  message: string;
};

type ProviderConfiguration = {
  provider: string;
  endpointUrl: string | null;
  manualModels: string[];
  llmModels: string[];
  apiKeySet: boolean;
  updatedAt: string;
};

type ConfigurableProvider = "openai" | "ollama" | "vllm";
type AuthoritativeProjectContext = {
  projectId: string | null;
  generation: number;
  ready: boolean;
};
type ClusterSetGenerationRequest = {
  projectId: string;
  indexingRunId: string;
  generation: number;
};

type ApiIndexingRun = {
  id: string;
  project_id: string;
  dataset_version_id: string;
  dataset_display_name: string | null;
  dataset_deleted_at: string | null;
  status: string;
  progress: number;
  phase: string;
  provider: string;
  model: string;
  parameters: Record<string, unknown>;
  error_code: string | null;
  error_message: string | null;
  diagnostics: Record<string, unknown>;
  started_at: string | null;
  completed_at: string | null;
  cancel_requested_at: string | null;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
};

type IndexingRun = {
  id: string;
  projectId: string;
  datasetVersionId: string;
  datasetDisplayName: string | null;
  datasetDeletedAt: string | null;
  status: string;
  progress: number;
  phase: string;
  provider: string;
  model: string;
  parameters: Record<string, unknown>;
  errorCode: string | null;
  errorMessage: string | null;
  diagnostics: Record<string, unknown>;
  startedAt: string | null;
  completedAt: string | null;
  cancelRequestedAt: string | null;
  deletedAt: string | null;
  createdAt: string;
  updatedAt: string;
};

type ApiClusterSet = {
  id: string;
  project_id: string;
  indexing_run_id: string;
  dataset_version_id: string;
  dataset_display_name: string | null;
  indexing_deleted_at: string | null;
  parent_cluster_set_id: string | null;
  display_name: string;
  status: string;
  progress: number;
  phase: string;
  derivation_type: string;
  vector_basis: string;
  message_weight: number;
  answer_weight: number;
  algorithm: string;
  parameters: Record<string, unknown>;
  source_snapshot: Record<string, unknown>;
  llm_provider: string | null;
  llm_model: string | null;
  llm_parameters: Record<string, unknown>;
  llm_sample_strategy: Record<string, unknown>;
  error_code: string | null;
  error_message: string | null;
  diagnostics: Record<string, unknown>;
  started_at: string | null;
  completed_at: string | null;
  cancel_requested_at: string | null;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
  cluster_count: number;
};

type ClusterSet = {
  id: string;
  projectId: string;
  indexingRunId: string;
  datasetVersionId: string;
  datasetDisplayName: string | null;
  indexingDeletedAt: string | null;
  parentClusterSetId: string | null;
  displayName: string;
  status: string;
  progress: number;
  phase: string;
  derivationType: string;
  vectorBasis: string;
  messageWeight: number;
  answerWeight: number;
  algorithm: string;
  parameters: Record<string, unknown>;
  sourceSnapshot: Record<string, unknown>;
  llmProvider: string | null;
  llmModel: string | null;
  llmParameters: Record<string, unknown>;
  llmSampleStrategy: Record<string, unknown>;
  errorCode: string | null;
  errorMessage: string | null;
  diagnostics: Record<string, unknown>;
  startedAt: string | null;
  completedAt: string | null;
  cancelRequestedAt: string | null;
  deletedAt: string | null;
  createdAt: string;
  updatedAt: string;
  clusterCount: number;
};

type ApiCluster = {
  id: string;
  project_id: string;
  analysis_run_id: string;
  dataset_version_id: string;
  cluster_set_id?: string | null;
  auto_title: string;
  manual_title: string | null;
  effective_title: string;
  auto_category: string | null;
  manual_category: string | null;
  effective_category: string | null;
  auto_status: string;
  manual_status: string | null;
  effective_status: string;
  score: number;
  is_outlier: boolean;
  algorithm: string;
  member_count: number;
  metadata: Record<string, unknown>;
  auto_summary_question?: string | null;
  auto_summary_answer?: string | null;
};

type Cluster = {
  id: string;
  projectId: string;
  analysisRunId: string;
  datasetVersionId: string;
  clusterSetId: string | null;
  autoTitle: string;
  manualTitle: string | null;
  effectiveTitle: string;
  autoCategory: string | null;
  manualCategory: string | null;
  effectiveCategory: string | null;
  autoStatus: string;
  manualStatus: string | null;
  effectiveStatus: string;
  score: number;
  isOutlier: boolean;
  algorithm: string;
  memberCount: number;
  metadata: Record<string, unknown>;
  autoSummaryQuestion: string | null;
  autoSummaryAnswer: string | null;
};

type ApiClusterSource = {
  cluster_id: string;
  message_pair_id: string;
  ticket_id: string;
  message_group_id: string;
  message: string;
  answer: string;
  membership_score: number;
  is_outlier: boolean;
  assignment_type: string;
};

type ApiClusterSourcePage = {
  sources: ApiClusterSource[];
  limit: number;
  offset: number;
  next_offset: number | null;
  has_more: boolean;
};

type ClusterSource = {
  clusterId: string;
  messagePairId: string;
  ticketId: string;
  messageGroupId: string;
  message: string;
  answer: string;
  membershipScore: number;
  isOutlier: boolean;
  assignmentType: string;
};

type ApiExportLog = {
  id: string;
  project_id: string;
  export_type: string;
  include_original_text: boolean;
  filters: Record<string, unknown>;
  selection: Record<string, unknown>;
  dataset_version_id: string | null;
  analysis_run_id: string | null;
  cluster_set_id: string | null;
  output_filename: string;
  output_path: string | null;
  row_count: number;
  created_at: string;
};

type ExportLog = {
  id: string;
  projectId: string;
  exportType: string;
  includeOriginalText: boolean;
  filters: Record<string, unknown>;
  selection: Record<string, unknown>;
  datasetVersionId: string | null;
  analysisRunId: string | null;
  clusterSetId: string | null;
  outputFilename: string;
  outputPath: string | null;
  rowCount: number;
  createdAt: string;
};

type Session = {
  token: string;
  user: User;
};

type FeedbackKind = "success" | "info" | "warning" | "error";

type Feedback = {
  kind: FeedbackKind;
  text: string;
};

type ActivePage = "projects" | "settings";
type SettingsTab = "providers" | "llm-providers" | "users";
type ProjectTab =
  "import" | "indexing" | "cluster-sets" | "explorer" | "delete";
type LlmProviderSelection = "" | "openai" | "ollama";
type ExplorerExportFormat = "csv" | "json";
type ClusterSetRefinementDraft = {
  parentClusterSetId: string;
  indexingRunId: string;
  sourceClusterIds: string[];
  description: string;
};

const API_BASE = import.meta.env.VITE_SKM_API_BASE_URL ?? "";
const INTERNAL_LAST_NAME_PLACEHOLDER = "-";
const SESSION_TOKEN_STORAGE_KEY = "skm.session-token";
const RUN_POLL_INTERVAL_MS = 2000;
const CLUSTER_SOURCE_PAGE_SIZE = 50;
const FEEDBACK_LABELS: Record<FeedbackKind, string> = {
  success: "Erfolg",
  info: "Hinweis",
  warning: "Warnung",
  error: "Fehler",
};
const ERROR_MESSAGES_BY_CODE: Record<string, string> = {
  UNEXPECTED_ERROR:
    "Die Aktion konnte nicht abgeschlossen werden. Bitte erneut versuchen oder den aktuellen Stand neu laden.",
  INDEXING_MODEL_UNAVAILABLE:
    "Das gewählte Embedding-Modell ist nicht verfügbar. Bitte Provider-Einstellungen prüfen oder ein anderes Modell wählen.",
  INDEXING_CLOUD_CONFIRMATION_REQUIRED:
    "Diese Indizierung würde Originaltexte an OpenAI senden. Bitte Cloud-Nutzung bewusst bestätigen oder ein lokales Modell wählen.",
  INDEXING_CANCEL_NOT_AVAILABLE:
    "Diese Indizierung kann nicht mehr abgebrochen werden. Bitte Liste aktualisieren.",
  INDEXING_NOT_COMPLETE:
    "Diese Indizierung ist noch nicht abgeschlossen. Bitte Abschluss abwarten oder eine fertige Indizierung wählen.",
  CLUSTER_VECTOR_BASIS_UNAVAILABLE:
    "Für diese Vektor-Basis fehlen Embeddings oder die Gewichtung ist ungültig. Bitte eine andere Basis wählen.",
  CLUSTER_SUMMARY_SAMPLE_COUNT_INVALID:
    "Die Beispielanzahl für Zusammenfassungen ist ungültig. Bitte einen Wert ab 1 wählen.",
  CLUSTER_BUDGET_EXCEEDED:
    "Die Zusammenfassung überschreitet das erlaubte Text- oder Aufruflimit. Bitte weniger Beispiele wählen.",
  LLM_CLOUD_CONFIRMATION_REQUIRED:
    "Diese Zusammenfassung würde Originaltexte an OpenAI senden. Bitte Cloud-Nutzung bewusst bestätigen.",
  LLM_PROVIDER_UNAVAILABLE:
    "Der LLM-Provider ist nicht verfügbar. Bitte Provider-Einstellungen prüfen oder Summaries deaktivieren.",
  CLUSTER_SUMMARY_FAILED:
    "Die Clusterbildung ist abgeschlossen, aber die Zusammenfassung konnte nicht erstellt werden.",
  CLUSTER_SET_CANCEL_NOT_AVAILABLE:
    "Dieses Cluster-Set kann nicht mehr abgebrochen werden. Bitte Liste aktualisieren.",
  CLUSTER_SET_NOT_FOUND:
    "Das Cluster-Set wurde nicht gefunden oder ist nicht mehr verfügbar. Bitte Liste neu laden.",
  CLUSTER_SET_NOT_COMPLETE:
    "Dieses Cluster-Set kann erst nach Abschluss geladen werden. Bitte Status aktualisieren und warten.",
  CLUSTER_SOURCE_NOT_FOUND:
    "Die Quellen dieses Clusters konnten nicht geladen werden. Bitte Cluster-Set neu laden.",
  CLUSTER_SOURCE_PAGE_INVALID:
    "Die Quellen konnten wegen ungültiger Seitenparameter nicht geladen werden. Bitte erneut öffnen.",
  CLUSTER_MANUAL_UPDATE_INVALID:
    "Die Cluster-Änderung ist ungültig und wurde nicht gespeichert.",
  CLUSTER_REFINEMENT_EMPTY_SOURCE:
    "Die gewählte Quelle enthält keine nutzbaren Zeilen für eine Verfeinerung.",
  CLUSTER_SEARCH_NO_RESULTS:
    "Keine Cluster entsprechen der aktuellen Textsuche oder dem Filter.",
  CLUSTER_OUTLIER_EMPTY_RESULT:
    "Die Ausreißer-Einstellung würde keine Zeilen übrig lassen. Bitte Schwellwert anpassen.",
  CLUSTER_OUTLIER_RECALCULATION_FAILED:
    "Die Ausreißer-Neuberechnung konnte nicht abgeschlossen werden.",
  CLUSTER_SET_LINEAGE_UNAVAILABLE:
    "Die Analyse-Historie ist unvollständig. Bitte Liste neu laden.",
  EXPLORER_EXPORT_EMPTY:
    "Im aktuellen Filterstand gibt es keine exportierbaren Zeilen.",
  EXPLORER_EXPORT_FORMAT_INVALID:
    "Das Exportformat ist ungültig. Bitte CSV oder JSON wählen.",
  EXPLORER_EXPORT_SELECTION_TOO_LARGE:
    "Die aktuelle Explorer-Auswahl ist zu groß. Bitte Filter oder Auswahl verkleinern.",
  EXPLORER_EXPORT_FAILED:
    "Der Export konnte nicht erstellt werden. Bitte erneut versuchen oder das Format wechseln.",
};

function readStoredSessionToken(): string | null {
  try {
    return window.sessionStorage.getItem(SESSION_TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

function storeSessionToken(token: string): void {
  window.sessionStorage.setItem(SESSION_TOKEN_STORAGE_KEY, token);
}

function clearStoredSessionToken(expectedToken?: string): void {
  try {
    if (
      expectedToken === undefined ||
      window.sessionStorage.getItem(SESSION_TOKEN_STORAGE_KEY) === expectedToken
    ) {
      window.sessionStorage.removeItem(SESSION_TOKEN_STORAGE_KEY);
    }
  } catch {
    // The in-memory session is still cleared when browser storage is unavailable.
  }
}

function userNameFromApi(user: ApiUser): string {
  return [user.first_name, user.last_name]
    .filter((part) => part.trim() !== INTERNAL_LAST_NAME_PLACEHOLDER)
    .join(" ")
    .trim();
}

function splitUserName(name: string): {
  first_name: string;
  last_name: string;
} {
  const cleaned = name.trim();
  const [firstName = "", ...remainingName] = cleaned.split(/\s+/);
  const lastName = remainingName.join(" ").trim();
  return {
    first_name: firstName || cleaned,
    last_name: lastName || INTERNAL_LAST_NAME_PLACEHOLDER,
  };
}

function toUser(user: ApiUser): User {
  return {
    id: user.id,
    name: userNameFromApi(user),
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

function formatProjectUpdatedAt(updatedAt: string): string {
  const date = new Date(updatedAt);
  if (Number.isNaN(date.getTime())) {
    return updatedAt;
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
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
    datasetDisplayName: log.dataset_display_name,
    datasetDeletedAt: log.dataset_deleted_at,
  };
}

function toProviderConfiguration(
  configuration: ApiProviderConfiguration,
): ProviderConfiguration {
  return {
    provider: configuration.provider,
    endpointUrl: configuration.endpoint_url,
    manualModels: configuration.manual_models,
    llmModels: configuration.llm_models ?? [],
    apiKeySet: configuration.api_key_set,
    updatedAt: configuration.updated_at,
  };
}

function toIndexingRun(run: ApiIndexingRun): IndexingRun {
  return {
    id: run.id,
    projectId: run.project_id,
    datasetVersionId: run.dataset_version_id,
    datasetDisplayName: run.dataset_display_name,
    datasetDeletedAt: run.dataset_deleted_at,
    status: run.status,
    progress: run.progress,
    phase: run.phase,
    provider: run.provider,
    model: run.model,
    parameters: run.parameters,
    errorCode: run.error_code,
    errorMessage: run.error_message,
    diagnostics: run.diagnostics,
    startedAt: run.started_at,
    completedAt: run.completed_at,
    cancelRequestedAt: run.cancel_requested_at,
    deletedAt: run.deleted_at,
    createdAt: run.created_at,
    updatedAt: run.updated_at,
  };
}

function toClusterSet(clusterSet: ApiClusterSet): ClusterSet {
  return {
    id: clusterSet.id,
    projectId: clusterSet.project_id,
    indexingRunId: clusterSet.indexing_run_id,
    datasetVersionId: clusterSet.dataset_version_id,
    datasetDisplayName: clusterSet.dataset_display_name,
    indexingDeletedAt: clusterSet.indexing_deleted_at,
    parentClusterSetId: clusterSet.parent_cluster_set_id,
    displayName: clusterSet.display_name,
    status: clusterSet.status,
    progress: clusterSet.progress,
    phase: clusterSet.phase,
    derivationType: clusterSet.derivation_type,
    vectorBasis: clusterSet.vector_basis,
    messageWeight: clusterSet.message_weight,
    answerWeight: clusterSet.answer_weight,
    algorithm: clusterSet.algorithm,
    parameters: clusterSet.parameters,
    sourceSnapshot: clusterSet.source_snapshot,
    llmProvider: clusterSet.llm_provider,
    llmModel: clusterSet.llm_model,
    llmParameters: clusterSet.llm_parameters,
    llmSampleStrategy: clusterSet.llm_sample_strategy,
    errorCode: clusterSet.error_code,
    errorMessage: clusterSet.error_message,
    diagnostics: clusterSet.diagnostics,
    startedAt: clusterSet.started_at,
    completedAt: clusterSet.completed_at,
    cancelRequestedAt: clusterSet.cancel_requested_at,
    deletedAt: clusterSet.deleted_at,
    createdAt: clusterSet.created_at,
    updatedAt: clusterSet.updated_at,
    clusterCount: clusterSet.cluster_count,
  };
}

function toCluster(cluster: ApiCluster): Cluster {
  return {
    id: cluster.id,
    projectId: cluster.project_id,
    analysisRunId: cluster.analysis_run_id,
    datasetVersionId: cluster.dataset_version_id,
    clusterSetId: cluster.cluster_set_id ?? null,
    autoTitle: cluster.auto_title,
    manualTitle: cluster.manual_title,
    effectiveTitle: cluster.effective_title,
    autoCategory: cluster.auto_category,
    manualCategory: cluster.manual_category,
    effectiveCategory: cluster.effective_category,
    autoStatus: cluster.auto_status,
    manualStatus: cluster.manual_status,
    effectiveStatus: cluster.effective_status,
    score: cluster.score,
    isOutlier: cluster.is_outlier,
    algorithm: cluster.algorithm,
    memberCount: cluster.member_count,
    metadata: cluster.metadata,
    autoSummaryQuestion: cluster.auto_summary_question ?? null,
    autoSummaryAnswer: cluster.auto_summary_answer ?? null,
  };
}

function toClusterSource(source: ApiClusterSource): ClusterSource {
  return {
    clusterId: source.cluster_id,
    messagePairId: source.message_pair_id,
    ticketId: source.ticket_id,
    messageGroupId: source.message_group_id,
    message: source.message,
    answer: source.answer,
    membershipScore: source.membership_score,
    isOutlier: source.is_outlier,
    assignmentType: source.assignment_type,
  };
}

function toExportLog(log: ApiExportLog): ExportLog {
  return {
    id: log.id,
    projectId: log.project_id,
    exportType: log.export_type,
    includeOriginalText: log.include_original_text,
    filters: log.filters,
    selection: log.selection,
    datasetVersionId: log.dataset_version_id,
    analysisRunId: log.analysis_run_id,
    clusterSetId: log.cluster_set_id,
    outputFilename: log.output_filename,
    outputPath: log.output_path,
    rowCount: log.row_count,
    createdAt: log.created_at,
  };
}

function parseModels(value: FormDataEntryValue | null): string[] {
  return String(value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function parsePositiveInteger(value: FormDataEntryValue | null): number | null {
  const cleaned = String(value ?? "").trim();
  if (!/^[1-9]\d*$/.test(cleaned)) {
    return null;
  }
  const parsed = Number(cleaned);
  return Number.isSafeInteger(parsed) ? parsed : null;
}

class ApiRequestError extends Error {
  readonly status: number;
  readonly code: string | null;

  constructor(message: string, status: number, code: string | null = null) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = code;
  }
}

function normalizeApiError(payload: {
  title?: unknown;
  detail?: unknown;
  code?: unknown;
}): { message: string | null; code: string | null } {
  const code = typeof payload.code === "string" ? payload.code : null;
  if (code !== null && ERROR_MESSAGES_BY_CODE[code] !== undefined) {
    return { message: ERROR_MESSAGES_BY_CODE[code], code };
  }
  if (code !== null) {
    return { message: ERROR_MESSAGES_BY_CODE.UNEXPECTED_ERROR, code };
  }
  if (typeof payload.detail === "string" && payload.detail.trim() !== "") {
    return { message: payload.detail, code };
  }
  if (typeof payload.title === "string" && payload.title.trim() !== "") {
    return { message: payload.title, code };
  }
  return { message: null, code };
}

function actionErrorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiRequestError ? error.message : fallback;
}

async function apiRequest<T>(
  path: string,
  options: RequestInit & { token?: string } = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    let detail: string | null = null;
    let code: string | null = null;
    try {
      const payload = (await response.json()) as {
        title?: unknown;
        detail?: unknown;
        code?: unknown;
      };
      const normalized = normalizeApiError(payload);
      detail = normalized.message;
      code = normalized.code;
    } catch {
      detail = null;
    }
    throw new ApiRequestError(
      detail ?? `Anfrage fehlgeschlagen (HTTP ${response.status}).`,
      response.status,
      code,
    );
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

function encodeRfc5987Filename(filename: string): string {
  return encodeURIComponent(filename).replace(
    /['()*]/g,
    (character) => `%${character.charCodeAt(0).toString(16).toUpperCase()}`,
  );
}

function App() {
  const [bootstrapToken] = useState(readStoredSessionToken);
  const [isSessionChecking, setIsSessionChecking] = useState(
    bootstrapToken !== null,
  );
  const [session, setSession] = useState<Session | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [importLogs, setImportLogs] = useState<ImportLog[]>([]);
  const [importLogEntries, setImportLogEntries] = useState<ApiImportLogEntry[]>(
    [],
  );
  const [providers, setProviders] = useState<ProviderConfiguration[]>([]);
  const [indexingRuns, setIndexingRuns] = useState<IndexingRun[]>([]);
  const [clusterSets, setClusterSets] = useState<ClusterSet[]>([]);
  const [collapsedClusterSetIds, setCollapsedClusterSetIds] = useState<
    Set<string>
  >(new Set());
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [clusterSources, setClusterSources] = useState<ClusterSource[]>([]);
  const [exportLogs, setExportLogs] = useState<ExportLog[]>([]);
  const [lastExportContent, setLastExportContent] = useState("");
  const [lastExportContentType, setLastExportContentType] = useState("");
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [clusterSetLoadId, setClusterSetLoadId] = useState<string | null>(null);
  const [sourceDialogCluster, setSourceDialogCluster] =
    useState<Cluster | null>(null);
  const [sourceDialogLoaded, setSourceDialogLoaded] = useState(false);
  const [sourceDialogError, setSourceDialogError] = useState<string | null>(
    null,
  );
  const [sourceDialogNextOffset, setSourceDialogNextOffset] = useState<
    number | null
  >(null);
  const [sourceDialogLoadingMore, setSourceDialogLoadingMore] = useState(false);
  const [clusterSearchQuery, setClusterSearchQuery] = useState("");
  const [clusterCategoryFilter, setClusterCategoryFilter] = useState("");
  const [clusterGroupByCategory, setClusterGroupByCategory] = useState(false);
  const [showExcludedClusters, setShowExcludedClusters] = useState(false);
  const [includeOutlierRows, setIncludeOutlierRows] = useState(true);
  const [outlierThreshold, setOutlierThreshold] = useState("0.5");
  const [explorerExportFormat, setExplorerExportFormat] =
    useState<ExplorerExportFormat>("csv");
  const [explorerExportError, setExplorerExportError] = useState<string | null>(
    null,
  );
  const [clusterSetRefinementDraft, setClusterSetRefinementDraft] =
    useState<ClusterSetRefinementDraft | null>(null);
  const [clusterSetGenerationRequest, setClusterSetGenerationRequest] =
    useState<ClusterSetGenerationRequest | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activePage, setActivePage] = useState<ActivePage>("projects");
  const [settingsTab, setSettingsTab] = useState<SettingsTab>("providers");
  const [projectTab, setProjectTab] = useState<ProjectTab>("import");
  const [recentProjectIds, setRecentProjectIds] = useState<string[]>([]);
  const [openAiDiscoveredModels, setOpenAiDiscoveredModels] = useState<
    string[]
  >([]);
  const [openAiSelectedModels, setOpenAiSelectedModels] = useState<string[]>(
    [],
  );
  const [indexingProvider, setIndexingProvider] =
    useState<ConfigurableProvider>("vllm");
  const [indexingModel, setIndexingModel] = useState("");
  const [cloudUseConfirmed, setCloudUseConfirmed] = useState(false);
  const [clusterSetVectorBasis, setClusterSetVectorBasis] = useState("message");
  const [clusterSetLlmProvider, setClusterSetLlmProvider] =
    useState<LlmProviderSelection>("");
  const [clusterSetLlmSampleAll, setClusterSetLlmSampleAll] = useState(false);
  const [clusterSetCloudUseConfirmed, setClusterSetCloudUseConfirmed] =
    useState(false);
  const projectOpenGeneration = useRef(0);
  const clusterSetGenerationRequestRef =
    useRef<ClusterSetGenerationRequest | null>(null);
  const sourceDialogRef = useRef<HTMLElement | null>(null);
  const sourceDialogCloseRef = useRef<HTMLButtonElement | null>(null);
  const sourceDialogTriggerRef = useRef<HTMLElement | null>(null);
  const signOutRef = useRef<() => void>(() => undefined);
  const authoritativeProjectContext = useRef<AuthoritativeProjectContext>({
    projectId: null,
    generation: 0,
    ready: false,
  });

  function showFeedback(kind: FeedbackKind, text: string) {
    setFeedback({ kind, text });
  }

  function resetSourceDialogState() {
    setClusterSources([]);
    setSourceDialogCluster(null);
    setSourceDialogLoaded(false);
    setSourceDialogError(null);
    setSourceDialogNextOffset(null);
    setSourceDialogLoadingMore(false);
  }

  function invalidateProjectContext() {
    const generation = projectOpenGeneration.current + 1;
    projectOpenGeneration.current = generation;
    authoritativeProjectContext.current = {
      projectId: null,
      generation,
      ready: false,
    };
    return generation;
  }

  function isAuthoritativeProjectContext(
    projectId: string,
    generation: number,
  ) {
    const context = authoritativeProjectContext.current;
    return (
      context.ready &&
      context.projectId === projectId &&
      context.generation === generation
    );
  }

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

  async function fetchImportLogs(token: string, projectId: string) {
    const apiLogs = await apiRequest<ApiImportLog[]>(
      `/api/projects/${projectId}/imports`,
      { token },
    );
    return apiLogs.map(toImportLog);
  }

  async function loadProviders(token: string) {
    const apiProviders = await apiRequest<ApiProviderConfiguration[]>(
      "/api/providers",
      { token },
    );
    const nextProviders = apiProviders.map(toProviderConfiguration);
    setProviders(nextProviders);
    const openAi = nextProviders.find(
      (provider) => provider.provider === "openai",
    );
    if (openAi !== undefined) {
      setOpenAiSelectedModels(openAi.manualModels);
    }
  }

  async function fetchIndexingRuns(
    token: string,
    projectId: string,
    signal?: AbortSignal,
  ) {
    const apiRuns = await apiRequest<ApiIndexingRun[]>(
      `/api/projects/${projectId}/indexing-runs`,
      { token, signal },
    );
    return apiRuns.map(toIndexingRun);
  }

  async function fetchClusterSets(
    token: string,
    projectId: string,
    signal?: AbortSignal,
  ) {
    const apiClusterSets = await apiRequest<ApiClusterSet[]>(
      `/api/projects/${projectId}/cluster-sets`,
      { token, signal },
    );
    return apiClusterSets.map(toClusterSet);
  }

  async function loadClusterSetClusters(
    token: string,
    projectId: string,
    clusterSetId: string,
  ) {
    try {
      const apiClusters = await apiRequest<ApiCluster[]>(
        `/api/projects/${projectId}/cluster-sets/${clusterSetId}/clusters`,
        { token },
      );
      setClusters(apiClusters.map(toCluster));
      resetSourceDialogState();
      setClusterSetLoadId(clusterSetId);
      setExplorerExportError(null);
      setLastExportContent("");
      setLastExportContentType("");
      setProjectTab("explorer");
      showFeedback(
        apiClusters.length > 0 ? "success" : "info",
        apiClusters.length > 0
          ? "Cluster-Set geladen."
          : "Dieses Cluster-Set enthält noch keine Cluster.",
      );
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(error, "Cluster-Set konnte nicht geladen werden."),
      );
    }
  }

  async function fetchExports(token: string, projectId: string) {
    const apiExports = await apiRequest<ApiExportLog[]>(
      `/api/projects/${projectId}/exports`,
      { token },
    );
    return apiExports.map(toExportLog);
  }

  useEffect(() => {
    if (bootstrapToken === null) {
      return undefined;
    }

    let cancelled = false;
    void apiRequest<ApiUser>("/api/auth/me", { token: bootstrapToken })
      .then((apiUser) => {
        if (cancelled) {
          return;
        }
        setSession({
          token: bootstrapToken,
          user: toUser(apiUser),
        });
        setIsSessionChecking(false);
        void loadUsers(bootstrapToken).catch(() => setUsers([]));
        void loadProjects(bootstrapToken).catch(() => setProjects([]));
        void loadProviders(bootstrapToken).catch(() => setProviders([]));
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }
        if (error instanceof ApiRequestError && error.status === 401) {
          clearStoredSessionToken(bootstrapToken);
          setFeedback(null);
        } else {
          showFeedback(
            "error",
            actionErrorMessage(
              error,
              "Sitzungsprüfung fehlgeschlagen oder Backend nicht erreichbar. Das gespeicherte Token bleibt für einen späteren Versuch erhalten.",
            ),
          );
        }
        setSession(null);
        setIsSessionChecking(false);
      });

    return () => {
      cancelled = true;
    };
  }, [bootstrapToken]);

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const email = String(form.get("email") ?? "").trim();
    const password = String(form.get("password") ?? "");
    let issuedToken: string | null = null;
    try {
      const response = await apiRequest<{
        access_token: string;
        user: ApiUser;
      }>("/api/auth/sign-in", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      issuedToken = response.access_token;
      const nextSession = {
        token: response.access_token,
        user: toUser(response.user),
      };
      storeSessionToken(nextSession.token);
      setSession(nextSession);
      await Promise.all([
        loadUsers(nextSession.token),
        loadProjects(nextSession.token),
      ]);
      let providerLoadError: unknown = null;
      try {
        await loadProviders(nextSession.token);
      } catch (error: unknown) {
        setProviders([]);
        providerLoadError = error;
      }
      setActivePage("projects");
      if (providerLoadError === null) {
        showFeedback(
          "success",
          "Angemeldet. Geschützte Workflows sind verfügbar.",
        );
      } else {
        showFeedback(
          "error",
          actionErrorMessage(
            providerLoadError,
            "Angemeldet, aber Provider-Konfigurationen konnten nicht geladen werden.",
          ),
        );
      }
    } catch (error: unknown) {
      if (issuedToken !== null) {
        clearStoredSessionToken(issuedToken);
      }
      invalidateProjectContext();
      setSession(null);
      setUsers([]);
      setProjects([]);
      setCurrentProject(null);
      setImportLogs([]);
      setImportLogEntries([]);
      setProviders([]);
      setIndexingRuns([]);
      setClusterSets([]);
      setClusters([]);
      setClusterSetLoadId(null);
      resetSourceDialogState();
      setExportLogs([]);
      setExplorerExportError(null);
      setLastExportContent("");
      setLastExportContentType("");
      showFeedback(
        "error",
        actionErrorMessage(
          error,
          "Anmeldung fehlgeschlagen oder Backend nicht erreichbar. Bitte Zugangsdaten und lokalen Dienst prüfen.",
        ),
      );
    } finally {
      setIsLoading(false);
    }
  }

  function signOut() {
    const token = session?.token;
    clearStoredSessionToken(token);
    invalidateProjectContext();
    setSession(null);
    setUsers([]);
    setProjects([]);
    setCurrentProject(null);
    setImportLogs([]);
    setImportLogEntries([]);
    setProviders([]);
    setIndexingRuns([]);
    setClusterSets([]);
    setClusters([]);
    setClusterSetLoadId(null);
    resetSourceDialogState();
    setExportLogs([]);
    setExplorerExportError(null);
    setLastExportContent("");
    setLastExportContentType("");
    setOpenAiDiscoveredModels([]);
    setOpenAiSelectedModels([]);
    setRecentProjectIds([]);
    setActivePage("projects");
    setFeedback(null);
    if (token !== undefined) {
      void apiRequest<void>("/api/auth/sign-out", {
        method: "POST",
        token,
      }).catch((error: unknown) => {
        showFeedback(
          "error",
          actionErrorMessage(
            error,
            "Lokale Abmeldung abgeschlossen, aber die Serversitzung konnte nicht widerrufen werden.",
          ),
        );
      });
    }
  }
  signOutRef.current = signOut;

  function openProvidersPage() {
    setActivePage("settings");
    setSettingsTab("providers");
    const openAi = providers.find((provider) => provider.provider === "openai");
    if (
      session !== null &&
      openAi?.apiKeySet &&
      openAiDiscoveredModels.length === 0
    ) {
      void discoverOpenAiModels(openAi.manualModels, false);
    }
  }

  function openProjectListPage() {
    invalidateProjectContext();
    setActivePage("projects");
    setCurrentProject(null);
    setIndexingRuns([]);
    setClusterSets([]);
    setProjectTab("import");
    setFeedback(null);
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
      invalidateProjectContext();
      setProjects((existing) => [project, ...existing]);
      setCurrentProject(null);
      setActivePage("projects");
      formElement.reset();
      showFeedback("success", "Projekt erstellt.");
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(
          error,
          "Projekt konnte nicht erstellt werden. Bitte Namen und Backend prüfen.",
        ),
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function openProject(projectId: string) {
    if (session === null) {
      return;
    }
    const generation = invalidateProjectContext();
    setCurrentProject(null);
    setImportLogs([]);
    setImportLogEntries([]);
    setIndexingRuns([]);
    setClusterSets([]);
    setClusters([]);
    setClusterSetLoadId(null);
    resetSourceDialogState();
    setExportLogs([]);
    setExplorerExportError(null);
    setLastExportContent("");
    setLastExportContentType("");
    setProjectTab("import");
    setActivePage("projects");
    try {
      const opened = await apiRequest<ApiProject>(
        `/api/projects/${projectId}`,
        {
          token: session.token,
        },
      );
      if (projectOpenGeneration.current !== generation) {
        return;
      }
      const project = toProject(opened);
      setCurrentProject(project);
      setProjectTab("import");
      rememberProjectAccess(project.id);
      setActivePage("projects");

      const [logs, nextClusterSets, exports] = await Promise.allSettled([
        fetchImportLogs(session.token, projectId),
        fetchClusterSets(session.token, projectId),
        fetchExports(session.token, projectId),
      ]);
      if (projectOpenGeneration.current !== generation) {
        return;
      }
      setImportLogs(logs.status === "fulfilled" ? logs.value : []);
      setClusterSets(
        nextClusterSets.status === "fulfilled" ? nextClusterSets.value : [],
      );
      setExportLogs(exports.status === "fulfilled" ? exports.value : []);
      authoritativeProjectContext.current = {
        projectId: project.id,
        generation,
        ready: true,
      };
      showFeedback("success", "Projekt geöffnet.");
    } catch (error: unknown) {
      if (projectOpenGeneration.current === generation) {
        showFeedback(
          "error",
          actionErrorMessage(error, "Projekt konnte nicht geöffnet werden."),
        );
      }
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
      showFeedback("success", "Projekt umbenannt.");
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(error, "Projekt konnte nicht umbenannt werden."),
      );
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
        invalidateProjectContext();
        setCurrentProject(null);
        setProjectTab("import");
        setImportLogs([]);
        setImportLogEntries([]);
        setIndexingRuns([]);
        setClusterSets([]);
        setClusters([]);
        setClusterSetLoadId(null);
        resetSourceDialogState();
        setExportLogs([]);
        setExplorerExportError(null);
        setLastExportContent("");
        setLastExportContentType("");
      }
      showFeedback("success", "Projekt gelöscht.");
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(
          error,
          "Projekt konnte nicht gelöscht werden. Namensbestätigung prüfen.",
        ),
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
    const name = String(form.get("name") ?? "").trim();
    const email = String(form.get("email") ?? "").trim();
    const password = String(form.get("password") ?? "");
    const splitName = splitUserName(name);
    try {
      const created = await apiRequest<ApiUser>("/api/users", {
        method: "POST",
        token: session.token,
        body: JSON.stringify({
          first_name: splitName.first_name,
          last_name: splitName.last_name,
          email,
          password,
        }),
      });
      setUsers((existing) => [...existing, toUser(created)]);
      formElement.reset();
      showFeedback("success", "User angelegt. Passwortwert bleibt write-only.");
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(
          error,
          "User konnte nicht angelegt werden. Bitte Eingaben und Backend prüfen.",
        ),
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
          ...splitUserName(updated.name),
          email: updated.email,
        }),
      });
      setUsers((existing) =>
        existing.map((user) => (user.id === userId ? toUser(saved) : user)),
      );
      showFeedback("success", "Userdaten aktualisiert.");
    } catch (error: unknown) {
      setUsers(previous);
      showFeedback(
        "error",
        actionErrorMessage(
          error,
          "Userdaten konnten nicht gespeichert werden.",
        ),
      );
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
      showFeedback(
        "success",
        "Passwortwert bleibt write-only und wurde gespeichert.",
      );
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(error, "Passwort konnte nicht gespeichert werden."),
      );
    }
  }

  async function deleteUser(userId: string) {
    if (session === null) {
      return;
    }
    if (session.user.id === userId) {
      showFeedback(
        "warning",
        "Selbstlöschung ist gesperrt, damit kein lokaler Lockout entsteht.",
      );
      return;
    }
    try {
      await apiRequest<void>(`/api/users/${userId}`, {
        method: "DELETE",
        token: session.token,
      });
      setUsers((existing) => existing.filter((user) => user.id !== userId));
      showFeedback("success", "User gelöscht.");
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(error, "User konnte nicht gelöscht werden."),
      );
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
      showFeedback("warning", "Bitte CSV- oder JSON-Datei auswählen.");
      return;
    }
    const lowerName = file.name.toLowerCase();
    if (!lowerName.endsWith(".csv") && !lowerName.endsWith(".json")) {
      showFeedback(
        "warning",
        "Nicht unterstützter Dateityp. Bitte CSV oder JSON auswählen.",
      );
      return;
    }
    if (file.size > MAX_IMPORT_BYTES) {
      showFeedback(
        "warning",
        `Datei ist zu groß (${file.size} Byte). Maximal erlaubt sind 536870912 Byte (512 MiB).`,
      );
      return;
    }
    const sourceType = lowerName.endsWith(".json") ? "json" : "csv";
    const contentType = sourceType === "json" ? "application/json" : "text/csv";
    setIsLoading(true);
    try {
      const result = await apiRequest<{
        log: ApiImportLog;
        skipped_entries: ApiImportLogEntry[];
        skipped_entries_truncated: boolean;
      }>(`/api/projects/${currentProject.id}/imports`, {
        method: "POST",
        token: session.token,
        headers: {
          "Content-Type": contentType,
          "Content-Disposition": `attachment; filename*=UTF-8''${encodeRfc5987Filename(file.name)}`,
        },
        body: file,
      });
      setImportLogs((existing) => [toImportLog(result.log), ...existing]);
      setImportLogEntries(result.skipped_entries);
      if (result.log.status === "failed") {
        showFeedback(
          "error",
          `Import fehlgeschlagen: ${result.log.failure_reason ?? "Unbekannter Validierungsfehler."}`,
        );
      } else {
        const truncationNotice = result.skipped_entries_truncated
          ? " Angezeigt werden nur die ersten 100 Fehlerdetails."
          : "";
        showFeedback(
          "success",
          `Import abgeschlossen: ${result.log.valid_records} importiert, ${result.log.skipped_records} übersprungen, ${result.log.total_records} gelesen.${truncationNotice}`,
        );
      }
      formElement.reset();
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(error, "Import konnte nicht durchgeführt werden."),
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
      const selectedLog = importLogs.find((log) => log.id === logId);
      showFeedback(
        "info",
        selectedLog !== undefined && selectedLog.skippedRecords > entries.length
          ? "Import-Log geladen. Angezeigt werden nur die ersten 100 Fehlerdetails."
          : "Import-Log geladen.",
      );
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(error, "Import-Log konnte nicht geladen werden."),
      );
    }
  }

  async function configureProvider(
    event: FormEvent<HTMLFormElement>,
    provider: ConfigurableProvider,
  ) {
    event.preventDefault();
    if (session === null) {
      return;
    }
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const payload: Record<string, unknown> = {};
    if (provider === "openai") {
      const apiKey = String(form.get("apiKey") ?? "");
      payload.api_key = apiKey || null;
      payload.remove_api_key = form.get("removeApiKey") === "on";
      payload.manual_models = openAiSelectedModels.length
        ? openAiSelectedModels
        : parseModels(form.get("manualModels"));
      payload.llm_models = parseModels(form.get("llmModels"));
    } else if (provider === "ollama") {
      payload.manual_models =
        providers.find((item) => item.provider === "ollama")?.manualModels ??
        [];
      payload.llm_models = parseModels(form.get("llmModels"));
      payload.endpoint_url = String(form.get("endpointUrl") ?? "").trim();
    } else {
      payload.manual_models = parseModels(form.get("manualModels"));
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
      if (provider === "openai") {
        const nextOpenAi = toProviderConfiguration(updated);
        setOpenAiSelectedModels(nextOpenAi.manualModels);
        formElement.reset();
        if (nextOpenAi.apiKeySet) {
          await discoverOpenAiModels(nextOpenAi.manualModels, true);
        } else {
          showFeedback("success", "OpenAI Provider gespeichert.");
        }
      } else {
        formElement.reset();
        showFeedback(
          "success",
          provider === "ollama"
            ? "Ollama Provider gespeichert."
            : "vLLM Provider gespeichert.",
        );
      }
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(
          error,
          "Provider-Konfiguration konnte nicht gespeichert werden.",
        ),
      );
    }
  }

  async function persistOpenAiModels(models: string[]) {
    if (session === null) {
      return;
    }
    const updated = await apiRequest<ApiProviderConfiguration>(
      "/api/providers/openai",
      {
        method: "PUT",
        token: session.token,
        body: JSON.stringify({ manual_models: models }),
      },
    );
    setProviders((existing) => [
      toProviderConfiguration(updated),
      ...existing.filter((item) => item.provider !== "openai"),
    ]);
  }

  async function persistProviderModels(
    provider: "ollama" | "vllm",
    models: string[],
  ) {
    if (session === null) {
      return;
    }
    const updated = await apiRequest<ApiProviderConfiguration>(
      `/api/providers/${provider}`,
      {
        method: "PUT",
        token: session.token,
        body: JSON.stringify({
          endpoint_url:
            providers.find((item) => item.provider === provider)?.endpointUrl ??
            null,
          manual_models: models,
          llm_models: providers.find((item) => item.provider === provider)
            ?.llmModels,
        }),
      },
    );
    setProviders((existing) => [
      toProviderConfiguration(updated),
      ...existing.filter((item) => item.provider !== provider),
    ]);
  }

  async function discoverOpenAiModels(
    fallbackModels = openAiSelectedModels,
    persistDiscovered = false,
  ) {
    if (session === null) {
      return;
    }
    try {
      const result = await apiRequest<ApiProviderCheck>(
        "/api/providers/openai/check",
        {
          method: "POST",
          token: session.token,
        },
      );
      const models = result.models.length ? result.models : fallbackModels;
      setOpenAiDiscoveredModels(models);
      setOpenAiSelectedModels((existing) =>
        persistDiscovered || existing.length === 0 ? models : existing,
      );
      if (persistDiscovered && models.length > 0) {
        await persistOpenAiModels(models);
      }
      if (result.ok && models.length > 0) {
        showFeedback("success", `${models.length} OpenAI Modell(e) abgerufen.`);
      } else if (result.ok) {
        showFeedback("info", "Keine OpenAI Modelle gefunden.");
      } else {
        showFeedback(
          "warning",
          result.message || "OpenAI Modelle konnten nicht abgerufen werden.",
        );
      }
    } catch (error: unknown) {
      setOpenAiDiscoveredModels(fallbackModels);
      showFeedback(
        "error",
        actionErrorMessage(
          error,
          "OpenAI Modelle konnten nicht abgerufen werden.",
        ),
      );
    }
  }

  function toggleOpenAiModel(model: string, checked: boolean) {
    setOpenAiSelectedModels((existing) =>
      checked
        ? Array.from(new Set([...existing, model]))
        : existing.filter((item) => item !== model),
    );
  }

  async function discoverProviderModels(provider: "ollama" | "vllm") {
    if (session === null) {
      return;
    }
    const configured = providers.find((item) => item.provider === provider);
    const fallbackModels = configured?.manualModels ?? [];
    try {
      const result = await apiRequest<ApiProviderCheck>(
        `/api/providers/${provider}/check`,
        {
          method: "POST",
          token: session.token,
        },
      );
      const models = result.models.length ? result.models : fallbackModels;
      if (models.length > 0) {
        await persistProviderModels(provider, models);
      }
      if (result.ok && models.length > 0) {
        showFeedback(
          "success",
          `${models.length} ${provider} Modell(e) abgerufen.`,
        );
      } else {
        showFeedback(
          "warning",
          result.message || `${provider} Modelle nicht gefunden.`,
        );
      }
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(
          error,
          `${provider} Modelle konnten nicht abgerufen werden.`,
        ),
      );
    }
  }

  async function pullOllamaModel(formElement: HTMLFormElement) {
    if (session === null) {
      return;
    }
    const form = new FormData(formElement);
    const model = String(form.get("pullModel") ?? "").trim();
    if (!model) {
      showFeedback("warning", "Ollama Modellname fehlt.");
      return;
    }
    setIsLoading(true);
    showFeedback("info", `Ollama Modell ${model} wird heruntergeladen.`);
    try {
      const updated = await apiRequest<ApiProviderConfiguration>(
        "/api/providers/ollama/pull",
        {
          method: "POST",
          token: session.token,
          body: JSON.stringify({ model }),
        },
      );
      setProviders((existing) => [
        toProviderConfiguration(updated),
        ...existing.filter((item) => item.provider !== "ollama"),
      ]);
      formElement.reset();
      showFeedback("success", `Ollama Modell ${model} wurde hinzugefügt.`);
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(error, "Ollama Modell konnte nicht geladen werden."),
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function renameDatasetVersion(
    datasetVersionId: string,
    displayName: string,
  ) {
    if (session === null || currentProject === null || !displayName.trim()) {
      return;
    }
    try {
      const updated = await apiRequest<{
        id: string;
        display_name: string | null;
        deleted_at: string | null;
      }>(
        `/api/projects/${currentProject.id}/dataset-versions/${datasetVersionId}`,
        {
          method: "PATCH",
          token: session.token,
          body: JSON.stringify({ display_name: displayName.trim() }),
        },
      );
      setImportLogs((existing) =>
        existing.map((log) =>
          log.datasetVersionId === datasetVersionId
            ? {
                ...log,
                datasetDisplayName: updated.display_name,
                datasetDeletedAt: updated.deleted_at,
              }
            : log,
        ),
      );
      setIndexingRuns((existing) =>
        existing.map((run) =>
          run.datasetVersionId === datasetVersionId
            ? {
                ...run,
                datasetDisplayName: updated.display_name,
                datasetDeletedAt: updated.deleted_at,
              }
            : run,
        ),
      );
      showFeedback("success", "Datensatz umbenannt.");
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(error, "Datensatz konnte nicht umbenannt werden."),
      );
    }
  }

  async function deleteDatasetVersion(datasetVersionId: string) {
    if (session === null || currentProject === null) {
      return;
    }
    if (
      !window.confirm(
        "Datensatz wirklich löschen? Bestehende Indizierungen bleiben sichtbar, der Datensatz kann aber nicht erneut ausgewählt werden.",
      )
    ) {
      return;
    }
    try {
      const updated = await apiRequest<{
        id: string;
        display_name: string | null;
        deleted_at: string | null;
      }>(
        `/api/projects/${currentProject.id}/dataset-versions/${datasetVersionId}`,
        {
          method: "DELETE",
          token: session.token,
        },
      );
      setImportLogs((existing) =>
        existing.map((log) =>
          log.datasetVersionId === datasetVersionId
            ? {
                ...log,
                datasetDisplayName: updated.display_name,
                datasetDeletedAt: updated.deleted_at,
              }
            : log,
        ),
      );
      setIndexingRuns((existing) =>
        existing.map((run) =>
          run.datasetVersionId === datasetVersionId
            ? {
                ...run,
                datasetDisplayName: updated.display_name,
                datasetDeletedAt: updated.deleted_at,
              }
            : run,
        ),
      );
      showFeedback("success", "Datensatz gelöscht.");
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(error, "Datensatz konnte nicht gelöscht werden."),
      );
    }
  }

  async function startIndexingRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const context = authoritativeProjectContext.current;
    if (
      session === null ||
      currentProject === null ||
      !context.ready ||
      context.projectId !== currentProject.id
    ) {
      showFeedback(
        "info",
        "Projekt wird noch geladen; die Indizierung kann noch nicht gestartet werden.",
      );
      return;
    }
    const originProjectId = currentProject.id;
    const generation = context.generation;
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const datasetVersionId = String(form.get("datasetVersionId") ?? "");
    if (!datasetVersionId || !indexingModel) {
      showFeedback("warning", "Bitte Datensatz und Embedding-Modell wählen.");
      return;
    }
    if (indexingProvider === "openai" && !cloudUseConfirmed) {
      showFeedback(
        "warning",
        "OpenAI Cloud-Nutzung muss vor dem Start bestätigt werden.",
      );
      return;
    }
    try {
      const created = await apiRequest<ApiIndexingRun>(
        `/api/projects/${originProjectId}/indexing-runs`,
        {
          method: "POST",
          token: session.token,
          body: JSON.stringify({
            dataset_version_id: datasetVersionId,
            provider: indexingProvider,
            model: indexingModel,
            cloud_use_confirmed:
              indexingProvider === "openai" ? cloudUseConfirmed : undefined,
          }),
        },
      );
      if (!isAuthoritativeProjectContext(originProjectId, generation)) {
        return;
      }
      setIndexingRuns((existing) => [toIndexingRun(created), ...existing]);
      formElement.reset();
      setCloudUseConfirmed(false);
      showFeedback(
        "success",
        `Indizierung gestartet: ${created.status}, Fortschritt ${created.progress}%.`,
      );
    } catch (error: unknown) {
      if (isAuthoritativeProjectContext(originProjectId, generation)) {
        showFeedback(
          "error",
          actionErrorMessage(
            error,
            "Indizierung konnte nicht gestartet werden. Datensatz, Provider und Modell prüfen.",
          ),
        );
      }
    }
  }

  async function cancelIndexingRun(runId: string) {
    if (session === null || currentProject === null) {
      return;
    }
    try {
      const updated = await apiRequest<ApiIndexingRun>(
        `/api/projects/${currentProject.id}/indexing-runs/${runId}/cancel`,
        {
          method: "POST",
          token: session.token,
        },
      );
      setIndexingRuns((existing) =>
        existing.map((run) =>
          run.id === runId ? toIndexingRun(updated) : run,
        ),
      );
      showFeedback("success", "Indizierung wird abgebrochen.");
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(
          error,
          "Indizierung konnte nicht abgebrochen werden.",
        ),
      );
    }
  }

  async function deleteIndexingRun(runId: string) {
    if (session === null || currentProject === null) {
      return;
    }
    if (
      !window.confirm(
        "Indizierung wirklich löschen? Sie wird aus der Liste entfernt und laufende Arbeit wird abgebrochen.",
      )
    ) {
      return;
    }
    try {
      await apiRequest<void>(
        `/api/projects/${currentProject.id}/indexing-runs/${runId}`,
        {
          method: "DELETE",
          token: session.token,
        },
      );
      setIndexingRuns((existing) => existing.filter((run) => run.id !== runId));
      showFeedback("success", "Indizierung gelöscht.");
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(error, "Indizierung konnte nicht gelöscht werden."),
      );
    }
  }

  function upsertClusterSet(clusterSet: ClusterSet) {
    setClusterSets((existing) => {
      const index = existing.findIndex((item) => item.id === clusterSet.id);
      if (index === -1) {
        return [clusterSet, ...existing];
      }
      return existing.map((item) =>
        item.id === clusterSet.id ? clusterSet : item,
      );
    });
    const parentClusterSetId = clusterSet.parentClusterSetId;
    if (parentClusterSetId !== null) {
      setCollapsedClusterSetIds((existing) => {
        if (!existing.has(parentClusterSetId)) {
          return existing;
        }
        const next = new Set(existing);
        next.delete(parentClusterSetId);
        return next;
      });
    }
  }

  function toggleClusterSetBranch(clusterSetId: string) {
    setCollapsedClusterSetIds((existing) => {
      const next = new Set(existing);
      if (next.has(clusterSetId)) {
        next.delete(clusterSetId);
      } else {
        next.add(clusterSetId);
      }
      return next;
    });
  }

  async function createClusterSet(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      session === null ||
      currentProject === null ||
      clusterSetGenerationRequestRef.current !== null
    ) {
      return;
    }
    const form = new FormData(event.currentTarget);
    const indexingRunId = String(form.get("indexingRunId") ?? "");
    if (!indexingRunId) {
      showFeedback("error", "Bitte eine abgeschlossene Indizierung wählen.");
      return;
    }
    const minClusterSize = Number.parseInt(
      String(form.get("minClusterSize") ?? "2"),
      10,
    );
    const minSamplesRaw = String(form.get("minSamples") ?? "").trim();
    const epsilonRaw = String(
      form.get("clusterSelectionEpsilon") ?? "0",
    ).trim();
    const outlierThresholdRaw = String(
      form.get("outlierThreshold") ?? "",
    ).trim();
    const llmProvider = String(form.get("llmProvider") ?? "") as
      "" | "openai" | "ollama";
    const llmModel = String(form.get("llmModel") ?? "").trim();
    const llmSampleCount = parsePositiveInteger(form.get("llmSampleCount"));
    if (
      llmProvider !== "" &&
      !clusterSetLlmSampleAll &&
      llmSampleCount === null
    ) {
      showFeedback(
        "error",
        ERROR_MESSAGES_BY_CODE.CLUSTER_SUMMARY_SAMPLE_COUNT_INVALID,
      );
      return;
    }
    const request: ClusterSetGenerationRequest = {
      projectId: currentProject.id,
      indexingRunId,
      generation: projectOpenGeneration.current,
    };
    clusterSetGenerationRequestRef.current = request;
    setClusterSetGenerationRequest(request);
    showFeedback("info", "Cluster-Set-Erzeugung wurde gestartet.");
    try {
      const created = await apiRequest<ApiClusterSet>(
        `/api/projects/${currentProject.id}/cluster-sets`,
        {
          method: "POST",
          token: session.token,
          body: JSON.stringify({
            indexing_run_id: indexingRunId,
            display_name: String(form.get("displayName") ?? "").trim() || null,
            parent_cluster_set_id:
              clusterSetRefinementDraft?.parentClusterSetId ?? null,
            derivation_type:
              clusterSetRefinementDraft === null ? "root" : "refinement",
            vector_basis: clusterSetVectorBasis,
            message_weight:
              clusterSetVectorBasis === "combined"
                ? Number(form.get("messageWeight") ?? 0.5)
                : 1,
            answer_weight:
              clusterSetVectorBasis === "combined"
                ? Number(form.get("answerWeight") ?? 0.5)
                : 0,
            algorithm_settings: {
              algorithm: "hdbscan",
              min_cluster_size: Number.isFinite(minClusterSize)
                ? minClusterSize
                : 2,
              ...(minSamplesRaw
                ? { min_samples: Number.parseInt(minSamplesRaw, 10) }
                : {}),
              cluster_selection_epsilon: epsilonRaw
                ? Number.parseFloat(epsilonRaw)
                : 0,
            },
            outlier_threshold: outlierThresholdRaw
              ? Number.parseFloat(outlierThresholdRaw)
              : null,
            source_cluster_ids:
              clusterSetRefinementDraft?.sourceClusterIds ?? [],
            llm_provider: llmProvider || null,
            llm_model: llmProvider ? llmModel || null : null,
            llm_sample_count:
              llmProvider && !clusterSetLlmSampleAll ? llmSampleCount : null,
            llm_sample_all: clusterSetLlmSampleAll,
            llm_cloud_use_confirmed:
              llmProvider === "openai" && clusterSetCloudUseConfirmed,
          }),
        },
      );
      if (projectOpenGeneration.current !== request.generation) {
        return;
      }
      upsertClusterSet(toClusterSet(created));
      setClusterSetRefinementDraft(null);
      showFeedback(
        "success",
        "Cluster-Set angelegt. Status wird aktualisiert.",
      );
    } catch (error: unknown) {
      if (projectOpenGeneration.current === request.generation) {
        showFeedback(
          "error",
          actionErrorMessage(
            error,
            "Cluster-Set konnte nicht erstellt werden.",
          ),
        );
      }
    } finally {
      if (clusterSetGenerationRequestRef.current === request) {
        clusterSetGenerationRequestRef.current = null;
        setClusterSetGenerationRequest((activeRequest) =>
          activeRequest === request ? null : activeRequest,
        );
      }
    }
  }

  async function cancelClusterSet(clusterSetId: string) {
    if (session === null || currentProject === null) {
      return;
    }
    try {
      const cancelled = await apiRequest<ApiClusterSet>(
        `/api/projects/${currentProject.id}/cluster-sets/${clusterSetId}/cancel`,
        { method: "POST", token: session.token },
      );
      upsertClusterSet(toClusterSet(cancelled));
      showFeedback("success", "Cluster-Set abgebrochen.");
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(
          error,
          "Cluster-Set konnte nicht abgebrochen werden.",
        ),
      );
    }
  }

  async function deleteClusterSet(clusterSetId: string) {
    if (session === null || currentProject === null) {
      return;
    }
    if (
      !window.confirm(
        "Cluster-Set wirklich löschen? Es wird aus der Übersicht entfernt; abgeleitete Historie kann weiterhin auf gelöschte Knoten verweisen.",
      )
    ) {
      return;
    }
    try {
      await apiRequest<void>(
        `/api/projects/${currentProject.id}/cluster-sets/${clusterSetId}`,
        { method: "DELETE", token: session.token },
      );
      setClusterSets((existing) =>
        existing.filter((clusterSet) => clusterSet.id !== clusterSetId),
      );
      if (clusterSetLoadId === clusterSetId) {
        setClusters([]);
        resetSourceDialogState();
        setClusterSetLoadId(null);
      }
      showFeedback("success", "Cluster-Set gelöscht.");
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(error, "Cluster-Set konnte nicht gelöscht werden."),
      );
    }
  }

  async function updateCluster(
    event: FormEvent<HTMLFormElement>,
    clusterId: string,
  ) {
    event.preventDefault();
    if (session === null || currentProject === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    try {
      const updated = await apiRequest<ApiCluster>(
        `/api/projects/${currentProject.id}/clusters/${clusterId}`,
        {
          method: "PATCH",
          token: session.token,
          body: JSON.stringify({
            manual_title: String(form.get("manualTitle") ?? "").trim() || null,
            manual_category:
              String(form.get("manualCategory") ?? "").trim() || null,
            manual_status:
              String(form.get("manualStatus") ?? "").trim() || null,
          }),
        },
      );
      setClusters((existing) =>
        existing.map((cluster) =>
          cluster.id === clusterId ? toCluster(updated) : cluster,
        ),
      );
      showFeedback("success", "Manuelle Clusterwerte gespeichert.");
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(error, "Cluster konnte nicht aktualisiert werden."),
      );
    }
  }

  async function setClusterManualStatus(
    clusterId: string,
    manualStatus: string | null,
  ) {
    if (session === null || currentProject === null) {
      return;
    }
    try {
      const updated = await apiRequest<ApiCluster>(
        `/api/projects/${currentProject.id}/clusters/${clusterId}`,
        {
          method: "PATCH",
          token: session.token,
          body: JSON.stringify({ manual_status: manualStatus }),
        },
      );
      setClusters((existing) =>
        existing.map((cluster) =>
          cluster.id === clusterId ? toCluster(updated) : cluster,
        ),
      );
      showFeedback(
        "success",
        manualStatus === "rejected"
          ? "Cluster ausgeschlossen."
          : "Cluster wieder eingeschlossen.",
      );
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(
          error,
          "Clusterstatus konnte nicht aktualisiert werden.",
        ),
      );
    }
  }

  async function inspectClusterSources(cluster: Cluster) {
    if (session === null || currentProject === null) {
      return;
    }
    sourceDialogTriggerRef.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    setSourceDialogCluster(cluster);
    await loadClusterSourcePage(cluster, 0, { append: false });
  }

  async function loadClusterSourcePage(
    cluster: Cluster,
    offset: number,
    options: { append: boolean },
  ) {
    if (session === null || currentProject === null) {
      return;
    }
    if (options.append) {
      setSourceDialogLoadingMore(true);
    } else {
      setSourceDialogLoaded(false);
      setClusterSources([]);
      setSourceDialogNextOffset(null);
    }
    setSourceDialogError(null);
    try {
      const apiPage = await apiRequest<ApiClusterSourcePage>(
        `/api/projects/${currentProject.id}/clusters/${cluster.id}/sources?limit=${CLUSTER_SOURCE_PAGE_SIZE}&offset=${offset}`,
        { token: session.token },
      );
      const pageSources = apiPage.sources.map(toClusterSource);
      setClusterSources((existing) =>
        options.append ? [...existing, ...pageSources] : pageSources,
      );
      setSourceDialogNextOffset(apiPage.next_offset);
      setSourceDialogLoaded(true);
      if (!options.append) {
        showFeedback("success", "Quellen geladen.");
      }
    } catch (error: unknown) {
      const message = actionErrorMessage(
        error,
        "Clusterquellen konnten nicht geladen werden.",
      );
      setSourceDialogError(message);
      setSourceDialogLoaded(true);
      if (!options.append) {
        setClusterSources([]);
        setSourceDialogNextOffset(null);
      }
      showFeedback("error", message);
    } finally {
      if (options.append) {
        setSourceDialogLoadingMore(false);
      }
    }
  }

  async function loadMoreClusterSources() {
    if (sourceDialogCluster === null || sourceDialogNextOffset === null) {
      return;
    }
    await loadClusterSourcePage(sourceDialogCluster, sourceDialogNextOffset, {
      append: true,
    });
  }

  function closeSourceDialog() {
    resetSourceDialogState();
  }

  function createRefinementDraftFromVisibleClusters() {
    if (loadedClusterSet === null) {
      return;
    }
    const sourceClusterIds = visibleIncludedClusters.map(
      (cluster) => cluster.id,
    );
    if (sourceClusterIds.length === 0) {
      showFeedback(
        "error",
        ERROR_MESSAGES_BY_CODE.CLUSTER_REFINEMENT_EMPTY_SOURCE,
      );
      return;
    }
    setClusterSetRefinementDraft({
      parentClusterSetId: loadedClusterSet.id,
      indexingRunId: loadedClusterSet.indexingRunId,
      sourceClusterIds,
      description: `${sourceClusterIds.length} sichtbare eingeschlossene Cluster aus ${loadedClusterSet.displayName}`,
    });
    setProjectTab("cluster-sets");
    showFeedback(
      "info",
      "Verfeinerung ist in der Cluster-Set-Erzeugung vorausgefüllt.",
    );
  }

  async function createRefinementDraftFromClusterSet(clusterSet: ClusterSet) {
    if (session === null || currentProject === null) {
      return;
    }
    try {
      const apiClusters = await apiRequest<ApiCluster[]>(
        `/api/projects/${currentProject.id}/cluster-sets/${clusterSet.id}/clusters`,
        { token: session.token },
      );
      const sourceClusterIds = apiClusters
        .map(toCluster)
        .filter((cluster) => !clusterIsExcluded(cluster))
        .map((cluster) => cluster.id);
      if (sourceClusterIds.length === 0) {
        showFeedback(
          "error",
          ERROR_MESSAGES_BY_CODE.CLUSTER_REFINEMENT_EMPTY_SOURCE,
        );
        return;
      }
      setClusterSetRefinementDraft({
        parentClusterSetId: clusterSet.id,
        indexingRunId: clusterSet.indexingRunId,
        sourceClusterIds,
        description: `${sourceClusterIds.length} eingeschlossene Cluster aus ${clusterSet.displayName}`,
      });
      setProjectTab("cluster-sets");
      showFeedback(
        "info",
        "Verfeinerung ist in der Cluster-Set-Erzeugung vorausgefüllt.",
      );
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(
          error,
          "Verfeinerung konnte nicht vorbereitet werden.",
        ),
      );
    }
  }

  function algorithmSettingsFromClusterSet(
    clusterSet: ClusterSet,
  ): Record<string, unknown> {
    const allowedKeys = [
      "min_cluster_size",
      "min_samples",
      "cluster_selection_epsilon",
      "n_clusters",
      "linkage",
      "distance_threshold",
    ];
    return {
      algorithm: clusterSet.algorithm,
      ...Object.fromEntries(
        allowedKeys
          .filter((key) => clusterSet.parameters[key] !== undefined)
          .map((key) => [key, clusterSet.parameters[key]]),
      ),
    };
  }

  async function createOutlierExclusionSet() {
    if (
      session === null ||
      currentProject === null ||
      loadedClusterSet === null
    ) {
      return;
    }
    const threshold = Number.parseFloat(outlierThreshold);
    if (!Number.isFinite(threshold) || threshold < 0 || threshold > 1) {
      showFeedback(
        "error",
        ERROR_MESSAGES_BY_CODE.CLUSTER_OUTLIER_EMPTY_RESULT,
      );
      return;
    }
    const sourceClusterIds = visibleIncludedClusters.map(
      (cluster) => cluster.id,
    );
    if (sourceClusterIds.length === 0) {
      showFeedback(
        "error",
        ERROR_MESSAGES_BY_CODE.CLUSTER_REFINEMENT_EMPTY_SOURCE,
      );
      return;
    }
    try {
      const created = await apiRequest<ApiClusterSet>(
        `/api/projects/${currentProject.id}/cluster-sets`,
        {
          method: "POST",
          token: session.token,
          body: JSON.stringify({
            indexing_run_id: loadedClusterSet.indexingRunId,
            display_name: `${loadedClusterSet.displayName} ohne Ausreißer`,
            parent_cluster_set_id: loadedClusterSet.id,
            derivation_type: "outlier_exclusion",
            vector_basis: loadedClusterSet.vectorBasis,
            message_weight: loadedClusterSet.messageWeight,
            answer_weight: loadedClusterSet.answerWeight,
            algorithm_settings:
              algorithmSettingsFromClusterSet(loadedClusterSet),
            source_cluster_ids: sourceClusterIds,
            outlier_threshold: threshold,
            llm_provider: null,
            llm_model: null,
            llm_sample_count: null,
            llm_sample_all: false,
            llm_cloud_use_confirmed: false,
          }),
        },
      );
      upsertClusterSet(toClusterSet(created));
      setProjectTab("cluster-sets");
      showFeedback(
        "success",
        "Ausreißer-Neuberechnung als Child-Cluster-Set gestartet.",
      );
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(
          error,
          "Ausreißer-Neuberechnung konnte nicht gestartet werden.",
        ),
      );
    }
  }

  async function createExplorerExport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      session === null ||
      currentProject === null ||
      loadedClusterSet === null
    ) {
      return;
    }
    setExplorerExportError(null);
    if (visibleClusters.length === 0) {
      const message = ERROR_MESSAGES_BY_CODE.EXPLORER_EXPORT_EMPTY;
      setExplorerExportError(message);
      showFeedback("error", message);
      return;
    }
    try {
      const result = await apiRequest<{
        export: ApiExportLog;
        content: string;
        content_type: string;
        warning: string | null;
      }>(`/api/projects/${currentProject.id}/exports/explorer`, {
        method: "POST",
        token: session.token,
        body: JSON.stringify({
          cluster_set_id: loadedClusterSet.id,
          export_format: explorerExportFormat,
          search_query: clusterSearchQuery.trim() || null,
          category: clusterCategoryFilter || null,
          include_excluded: showExcludedClusters,
          include_outliers: includeOutlierRows,
          cluster_ids: visibleClusters.map((cluster) => cluster.id),
        }),
      });
      setExportLogs((existing) => [
        toExportLog(result.export),
        ...existing.filter((item) => item.id !== result.export.id),
      ]);
      setLastExportContent(result.content);
      setLastExportContentType(result.content_type);
      setExplorerExportError(null);
      showFeedback(
        result.warning === null ? "success" : "warning",
        result.warning ??
          `Explorer-Export erstellt: ${result.export.output_filename} (${result.export.row_count} Zeilen).`,
      );
    } catch (error: unknown) {
      const message = actionErrorMessage(
        error,
        "Export konnte nicht erstellt werden.",
      );
      setExplorerExportError(message);
      showFeedback("error", message);
    }
  }

  const openAiProvider = providers.find(
    (provider) => provider.provider === "openai",
  );
  const vllmProvider = providers.find(
    (provider) => provider.provider === "vllm",
  );
  const ollamaProvider = providers.find(
    (provider) => provider.provider === "ollama",
  );
  const sidebarProjects = projects
    .slice()
    .sort((left, right) => {
      const leftRecentIndex = recentProjectIds.indexOf(left.id);
      const rightRecentIndex = recentProjectIds.indexOf(right.id);
      if (leftRecentIndex !== -1 || rightRecentIndex !== -1) {
        if (leftRecentIndex === -1) {
          return 1;
        }
        if (rightRecentIndex === -1) {
          return -1;
        }
        return leftRecentIndex - rightRecentIndex;
      }
      return right.updatedAt.localeCompare(left.updatedAt);
    })
    .slice(0, 10);
  const runnableDatasetLogs = importLogs.filter(
    (log) => log.datasetVersionId !== null && log.datasetDeletedAt === null,
  );
  const indexingProviderConfiguration = providers.find(
    (provider) => provider.provider === indexingProvider,
  );
  const indexingProviderModels =
    indexingProviderConfiguration?.manualModels ?? [];
  const completedIndexingRuns = indexingRuns.filter(
    (run) => run.status === "completed",
  );
  const clusterSetLlmProviderModels =
    clusterSetLlmProvider === ""
      ? []
      : (providers.find(
          (provider) => provider.provider === clusterSetLlmProvider,
        )?.llmModels ?? []);

  function clusterIsExcluded(cluster: Cluster): boolean {
    return cluster.effectiveStatus === "rejected";
  }

  function clusterCategory(cluster: Cluster): string {
    return cluster.effectiveCategory?.trim() || "Ohne Kategorie";
  }

  function clusterMatchesSearch(
    cluster: Cluster,
    searchQuery: string,
  ): boolean {
    const query = searchQuery.trim().toLowerCase();
    if (query === "") {
      return true;
    }
    return [
      cluster.effectiveTitle,
      cluster.effectiveCategory ?? "",
      cluster.effectiveStatus,
      cluster.autoSummaryQuestion ?? "",
      cluster.autoSummaryAnswer ?? "",
    ]
      .join("\n")
      .toLowerCase()
      .includes(query);
  }

  function mismatchMetric(cluster: Cluster, key: "average" | "maximum") {
    const mismatch = cluster.metadata.qa_mismatch;
    if (
      mismatch === null ||
      Array.isArray(mismatch) ||
      typeof mismatch !== "object"
    ) {
      return null;
    }
    const value = (mismatch as Record<string, unknown>)[key];
    return typeof value === "number" ? value : null;
  }

  function formatScore(value: number | null): string {
    return value === null ? "-" : value.toFixed(2);
  }

  function formatClusterSetType(value: string): string {
    return (
      {
        root: "Root",
        refinement: "Verfeinerung",
        outlier_exclusion: "Ausreißer-Ausschluss",
        manual_edit: "Manuelle Änderung",
      }[value] ?? value
    );
  }

  const loadedClusterSet =
    clusterSets.find((clusterSet) => clusterSet.id === clusterSetLoadId) ??
    null;
  const clusterCategories = Array.from(
    new Set(clusters.map(clusterCategory)),
  ).sort((left, right) => left.localeCompare(right));
  const visibleClusters = clusters.filter(
    (cluster) =>
      (showExcludedClusters || !clusterIsExcluded(cluster)) &&
      (includeOutlierRows || !cluster.isOutlier) &&
      (clusterCategoryFilter === "" ||
        clusterCategory(cluster) === clusterCategoryFilter) &&
      clusterMatchesSearch(cluster, clusterSearchQuery),
  );
  const visibleIncludedClusters = visibleClusters.filter(
    (cluster) => !clusterIsExcluded(cluster),
  );
  const visibleExcludedClusters = visibleClusters.filter(clusterIsExcluded);
  const includedClusterGroups = clusterGroupByCategory
    ? Array.from(
        visibleIncludedClusters.reduce((groups, cluster) => {
          const category = clusterCategory(cluster);
          groups.set(category, [...(groups.get(category) ?? []), cluster]);
          return groups;
        }, new Map<string, Cluster[]>()),
      )
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([category, groupClusters]) => ({
          key: category,
          label: category,
          clusters: groupClusters,
        }))
    : [
        {
          key: "all",
          label: "Eingeschlossene Cluster",
          clusters: visibleIncludedClusters,
        },
      ];
  const rootClusterSets = clusterSets.filter(
    (clusterSet) => clusterSet.parentClusterSetId === null,
  );
  const childClusterSets = (parentId: string) =>
    clusterSets.filter(
      (clusterSet) => clusterSet.parentClusterSetId === parentId,
    );
  function clusterSetPath(clusterSet: ClusterSet): ClusterSet[] {
    const byId = new Map(clusterSets.map((item) => [item.id, item]));
    const path = [clusterSet];
    const visited = new Set([clusterSet.id]);
    let parentId = clusterSet.parentClusterSetId;
    while (parentId !== null) {
      const parent = byId.get(parentId);
      if (parent === undefined || visited.has(parent.id)) {
        break;
      }
      path.unshift(parent);
      visited.add(parent.id);
      parentId = parent.parentClusterSetId;
    }
    return path;
  }
  const loadedAnalysisPath =
    loadedClusterSet === null ? [] : clusterSetPath(loadedClusterSet);
  const visibleExportLogs =
    loadedClusterSet === null
      ? exportLogs
      : exportLogs.filter(
          (log) =>
            log.clusterSetId === null ||
            log.clusterSetId === loadedClusterSet.id,
        );

  function rememberProjectAccess(projectId: string) {
    setRecentProjectIds((existing) =>
      [projectId, ...existing.filter((id) => id !== projectId)].slice(0, 10),
    );
  }

  function datasetLabel(
    log: Pick<
      ImportLog,
      "sourceName" | "datasetVersionId" | "datasetDisplayName"
    >,
  ) {
    return (
      log.datasetDisplayName ?? log.sourceName ?? log.datasetVersionId ?? "-"
    );
  }

  useEffect(() => {
    const availableModels =
      providers.find((provider) => provider.provider === indexingProvider)
        ?.manualModels ?? [];
    setIndexingModel((currentModel) =>
      availableModels.includes(currentModel)
        ? currentModel
        : (availableModels[0] ?? ""),
    );
  }, [indexingProvider, providers]);

  useEffect(() => {
    setCloudUseConfirmed(false);
  }, [currentProject?.id, indexingProvider]);

  useEffect(() => {
    setClusterSetCloudUseConfirmed(false);
  }, [currentProject?.id, clusterSetLlmProvider]);

  useEffect(() => {
    if (
      session === null ||
      currentProject === null ||
      activePage !== "projects" ||
      (projectTab !== "indexing" &&
        projectTab !== "cluster-sets" &&
        projectTab !== "explorer")
    ) {
      return undefined;
    }

    const shouldPoll =
      projectTab === "indexing" ||
      projectTab === "cluster-sets" ||
      projectTab === "explorer";
    const token = session.token;
    const projectId = currentProject.id;
    const projectGeneration = projectOpenGeneration.current;
    let cancelled = false;
    let timer: number | null = null;
    let activeRequest: { controller: AbortController } | null = null;

    function clearScheduledPoll() {
      if (timer !== null) {
        window.clearTimeout(timer);
        timer = null;
      }
    }

    function isCurrentPollingContext(requireVisible: boolean) {
      return (
        !cancelled &&
        projectOpenGeneration.current === projectGeneration &&
        (!requireVisible || document.visibilityState === "visible")
      );
    }

    function cancelActiveRequest() {
      const request = activeRequest;
      activeRequest = null;
      request?.controller.abort();
    }

    function scheduleNextPoll(delay: number) {
      if (!shouldPoll || !isCurrentPollingContext(true)) {
        return;
      }
      clearScheduledPoll();
      timer = window.setTimeout(() => {
        timer = null;
        void refreshIndexingRuns();
      }, delay);
    }

    async function refreshIndexingRuns() {
      if (activeRequest !== null || !isCurrentPollingContext(true)) {
        return;
      }
      const request = { controller: new AbortController() };
      activeRequest = request;
      try {
        const [runsResult, clusterSetsResult] = await Promise.allSettled([
          fetchIndexingRuns(token, projectId, request.controller.signal),
          projectTab === "cluster-sets" || projectTab === "explorer"
            ? fetchClusterSets(token, projectId, request.controller.signal)
            : Promise.resolve<ClusterSet[] | null>(null),
        ]);
        for (const result of [runsResult, clusterSetsResult]) {
          if (
            result.status === "rejected" &&
            result.reason instanceof ApiRequestError &&
            result.reason.status === 401
          ) {
            throw result.reason;
          }
        }
        if (activeRequest === request && isCurrentPollingContext(true)) {
          if (runsResult.status === "fulfilled") {
            setIndexingRuns(runsResult.value);
          }
          if (
            clusterSetsResult.status === "fulfilled" &&
            clusterSetsResult.value !== null
          ) {
            setClusterSets(clusterSetsResult.value);
          }
        }
      } catch (error: unknown) {
        if (
          activeRequest === request &&
          isCurrentPollingContext(false) &&
          error instanceof ApiRequestError &&
          error.status === 401
        ) {
          signOutRef.current();
        }
      } finally {
        if (activeRequest === request) {
          activeRequest = null;
          scheduleNextPoll(RUN_POLL_INTERVAL_MS);
        }
      }
    }

    function handleVisibilityChange() {
      clearScheduledPoll();
      cancelActiveRequest();
      if (document.visibilityState === "visible") {
        void refreshIndexingRuns();
      }
    }

    document.addEventListener("visibilitychange", handleVisibilityChange);
    if (document.visibilityState === "visible") {
      void refreshIndexingRuns();
    }

    return () => {
      cancelled = true;
      clearScheduledPoll();
      cancelActiveRequest();
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [activePage, currentProject, projectTab, session]);

  useEffect(() => {
    if (feedback === null) {
      return undefined;
    }
    const timeout = window.setTimeout(() => setFeedback(null), 3500);
    return () => window.clearTimeout(timeout);
  }, [feedback]);

  useEffect(() => {
    if (sourceDialogCluster === null) {
      return undefined;
    }
    sourceDialogCloseRef.current?.focus();
    const handleDialogKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closeSourceDialog();
        return;
      }
      if (event.key !== "Tab" || sourceDialogRef.current === null) {
        return;
      }
      const focusable = Array.from(
        sourceDialogRef.current.querySelectorAll<HTMLElement>(
          [
            "a[href]",
            "button:not([disabled])",
            "input:not([disabled])",
            "select:not([disabled])",
            "textarea:not([disabled])",
            "[tabindex]:not([tabindex='-1'])",
          ].join(","),
        ),
      ).filter(
        (element) =>
          !element.hasAttribute("hidden") &&
          element.getAttribute("aria-hidden") !== "true",
      );
      if (focusable.length === 0) {
        event.preventDefault();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", handleDialogKeyDown);
    return () => {
      window.removeEventListener("keydown", handleDialogKeyDown);
      const trigger = sourceDialogTriggerRef.current;
      sourceDialogTriggerRef.current = null;
      if (trigger !== null && document.contains(trigger)) {
        trigger.focus();
      }
    };
  }, [sourceDialogCluster]);

  function renderClusterTableRow(cluster: Cluster) {
    const isExcluded = clusterIsExcluded(cluster);
    const mismatchMaximum = mismatchMetric(cluster, "maximum");
    return (
      <tr className={isExcluded ? "excluded-row" : ""} key={cluster.id}>
        <td className="cluster-status-cell">
          <span className={`status-chip ${isExcluded ? "warning" : "active"}`}>
            {isExcluded ? "ausgeschlossen" : cluster.effectiveStatus}
          </span>
          {cluster.isOutlier && (
            <span className="status-chip warning">Ausreißer</span>
          )}
        </td>
        <td className="cluster-title-cell">
          <strong>{cluster.effectiveTitle}</strong>
          <p className="hint">Auto: {cluster.autoTitle}</p>
        </td>
        <td className="cluster-short-cell">{clusterCategory(cluster)}</td>
        <td className="cluster-text-cell">
          {cluster.autoSummaryQuestion ?? "-"}
        </td>
        <td className="cluster-text-cell">
          {cluster.autoSummaryAnswer ?? "-"}
        </td>
        <td className="cluster-count-cell">{cluster.memberCount}</td>
        <td className="cluster-count-cell">{cluster.memberCount}</td>
        <td className="cluster-hints-cell">
          Score {formatScore(cluster.score)}
          {mismatchMaximum !== null && mismatchMaximum >= 0.35 && (
            <p className="status warning">
              Q/A-Mismatch {formatScore(mismatchMaximum)}
            </p>
          )}
        </td>
        <td className="cluster-actions-cell">
          <form
            className="table-edit-form"
            onSubmit={(event) => updateCluster(event, cluster.id)}
          >
            <label>
              Titel
              <input
                name="manualTitle"
                defaultValue={cluster.manualTitle ?? ""}
                aria-label={`Titel für ${cluster.effectiveTitle}`}
              />
            </label>
            <label>
              Kategorie
              <input
                name="manualCategory"
                defaultValue={cluster.manualCategory ?? ""}
                aria-label={`Kategorie für ${cluster.effectiveTitle}`}
              />
            </label>
            <label>
              Status
              <select
                name="manualStatus"
                defaultValue={cluster.manualStatus ?? ""}
                aria-label={`Status für ${cluster.effectiveTitle}`}
              >
                <option value="">Kein Override</option>
                <option value="unreviewed">unreviewed</option>
                <option value="in_progress">in_progress</option>
                <option value="reviewed">reviewed</option>
                <option value="rejected">rejected</option>
                <option value="outlier">outlier</option>
              </select>
            </label>
            <button type="submit" className="secondary">
              Speichern
            </button>
          </form>
          <div className="form-actions">
            <button
              type="button"
              className="secondary"
              onClick={() => void inspectClusterSources(cluster)}
            >
              Quellen anzeigen
            </button>
            <button
              type="button"
              className="secondary"
              onClick={() =>
                void setClusterManualStatus(
                  cluster.id,
                  isExcluded ? "unreviewed" : "rejected",
                )
              }
            >
              {isExcluded ? "Wieder einschließen" : "Ausschließen"}
            </button>
          </div>
        </td>
      </tr>
    );
  }

  function renderClusterSetCard(clusterSet: ClusterSet, depth = 0) {
    const children = childClusterSets(clusterSet.id);
    const hasChildren = children.length > 0;
    const isExpanded = !collapsedClusterSetIds.has(clusterSet.id);
    const childRegionId = `cluster-set-children-${clusterSet.id}`;
    const isDeletedHistoryNode = clusterSet.deletedAt !== null;
    return (
      <article
        className="user-card cluster-set-node"
        key={clusterSet.id}
        style={{ marginLeft: depth === 0 ? 0 : "1rem" }}
      >
        <div className="user-heading cluster-set-heading">
          <div className="cluster-set-title">
            {hasChildren ? (
              <button
                type="button"
                className="tree-toggle"
                aria-expanded={isExpanded}
                aria-controls={childRegionId}
                onClick={() => toggleClusterSetBranch(clusterSet.id)}
              >
                <span aria-hidden="true">{isExpanded ? "▾" : "▸"}</span>
                {isExpanded ? "Ast einklappen" : "Ast ausklappen"}
              </button>
            ) : (
              <span className="tree-toggle-placeholder" aria-hidden="true" />
            )}
            <strong>{clusterSet.displayName}</strong>
          </div>
          <span>
            {formatClusterSetType(clusterSet.derivationType)} ·{" "}
            {clusterSet.status} · {clusterSet.progress}%
          </span>
        </div>
        <progress value={clusterSet.progress} max={100}>
          {clusterSet.progress}%
        </progress>
        <p className="hint">
          Phase: {clusterSet.phase}; Basis: {clusterSet.vectorBasis};
          Algorithmus: {clusterSet.algorithm}; Cluster:{" "}
          {clusterSet.clusterCount}
        </p>
        <p className="hint">
          Parameter: min_cluster_size{" "}
          {String(clusterSet.parameters.min_cluster_size ?? "-")};
          Outlier-Schwelle:{" "}
          {typeof clusterSet.parameters.outlier_threshold === "number"
            ? String(clusterSet.parameters.outlier_threshold)
            : "aus"}
        </p>
        <p className="hint">
          Indizierung: {clusterSet.indexingRunId}; Datensatz:{" "}
          {clusterSet.datasetDisplayName ?? "-"}
        </p>
        {clusterSet.parentClusterSetId !== null && (
          <p className="hint">Parent: {clusterSet.parentClusterSetId}</p>
        )}
        {isDeletedHistoryNode && (
          <p className="status warning" role="status">
            Gelöschter Historienknoten. Nicht ladbar, bleibt aber als Parent
            sichtbar.
          </p>
        )}
        {clusterSet.indexingDeletedAt !== null && (
          <p className="status warning">
            Basis-Indizierung gelöscht: {clusterSet.indexingDeletedAt}
          </p>
        )}
        <p className="hint">
          LLM:{" "}
          {clusterSet.llmProvider
            ? `${clusterSet.llmProvider}/${clusterSet.llmModel}`
            : "deaktiviert"}
        </p>
        {clusterSet.errorCode !== null && (
          <p className="error" role="alert">
            {ERROR_MESSAGES_BY_CODE[clusterSet.errorCode] ??
              ERROR_MESSAGES_BY_CODE.UNEXPECTED_ERROR}
          </p>
        )}
        <div className="form-actions">
          <button
            type="button"
            className="secondary"
            disabled={clusterSet.status !== "completed" || isDeletedHistoryNode}
            onClick={() =>
              session &&
              currentProject &&
              loadClusterSetClusters(
                session.token,
                currentProject.id,
                clusterSet.id,
              )
            }
          >
            Im Explorer laden
          </button>
          <button
            type="button"
            className="secondary"
            disabled={clusterSet.status !== "completed" || isDeletedHistoryNode}
            onClick={() => void createRefinementDraftFromClusterSet(clusterSet)}
          >
            Cluster verfeinern
          </button>
          <button
            type="button"
            className="secondary"
            disabled={
              isDeletedHistoryNode ||
              (clusterSet.status !== "queued" &&
                clusterSet.status !== "running")
            }
            onClick={() => void cancelClusterSet(clusterSet.id)}
          >
            Abbrechen
          </button>
          <button
            type="button"
            className="secondary"
            disabled={isDeletedHistoryNode}
            onClick={() => void deleteClusterSet(clusterSet.id)}
          >
            Löschen
          </button>
        </div>
        {hasChildren && isExpanded && (
          <div
            id={childRegionId}
            className="cluster-set-children"
            aria-label={`Child Cluster-Sets von ${clusterSet.displayName}`}
          >
            {children.map((child) => renderClusterSetCard(child, depth + 1))}
          </div>
        )}
      </article>
    );
  }

  if (isSessionChecking) {
    return (
      <main className="auth-shell">
        <section className="auth-card" aria-label="Sitzungsprüfung">
          <p className="eyebrow">Support Knowledge Miner</p>
          <p role="status" className="intro">
            Gespeicherte Sitzung wird geprüft.
          </p>
        </section>
      </main>
    );
  }

  if (session === null) {
    return (
      <main className="auth-shell">
        <section className="auth-card" aria-labelledby="signin-title">
          <p className="eyebrow">Support Knowledge Miner</p>
          <h1 id="signin-title">Lokaler Zugriff</h1>
          <p className="intro">
            Geschützte Projekt-, Import- und Kurationsbereiche starten erst nach
            erfolgreicher Backend-Anmeldung. Fehler nennen nie, ob E-Mail oder
            Passwort falsch war.
          </p>
          <form className="stack" onSubmit={signIn}>
            <label>
              E-Mail
              <input name="email" type="email" autoComplete="username" />
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
              {isLoading ? "Prüfe Anmeldung" : "Anmelden"}
            </button>
          </form>
          {feedback !== null && (
            <p
              role={feedback.kind === "error" ? "alert" : "status"}
              className={`status ${feedback.kind}`}
            >
              <strong>{FEEDBACK_LABELS[feedback.kind]}:</strong> {feedback.text}
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
          <p className="eyebrow">Support Knowledge Miner</p>
          <h1>
            {activePage === "projects"
              ? "Projekte & Analysen"
              : "Einstellungen"}
          </h1>
        </div>
        <div className="topbar-actions">
          <span>{session.user.name}</span>
          <button type="button" className="icon-button" onClick={signOut}>
            Abmelden
          </button>
        </div>
      </header>

      <div className="workspace">
        <aside className="sidebar">
          <nav aria-label="Hauptnavigation">
            <button
              type="button"
              className={`nav-item ${
                activePage === "projects" && currentProject === null
                  ? "active"
                  : ""
              }`}
              onClick={openProjectListPage}
            >
              Projekte
            </button>
            <div className="sidebar-submenu" aria-label="Projektliste">
              {sidebarProjects.map((project) => (
                <button
                  type="button"
                  className={`nav-subitem ${
                    activePage === "projects" &&
                    currentProject?.id === project.id
                      ? "active"
                      : ""
                  }`}
                  key={project.id}
                  onClick={() => void openProject(project.id)}
                >
                  {project.name}
                </button>
              ))}
            </div>
            <button
              type="button"
              className={`nav-item ${activePage === "settings" ? "active" : ""}`}
              onClick={openProvidersPage}
            >
              Einstellungen
            </button>
          </nav>
        </aside>

        <section className="content">
          {feedback !== null && (
            <p
              role={feedback.kind === "error" ? "alert" : "status"}
              className={`feedback ${feedback.kind}`}
            >
              <strong>{FEEDBACK_LABELS[feedback.kind]}:</strong> {feedback.text}
            </p>
          )}

          {activePage === "projects" && currentProject && (
            <>
              <section
                id="project-home"
                className="panel project-summary"
                aria-label="Aktuelles Projekt"
              >
                <p className="eyebrow">Aktuelles Projekt</p>
                <div className="project-summary-content">
                  <div>
                    <h2>{currentProject.name}</h2>
                    <p className="hint">
                      Status: {currentProject.lifecycleState}; zuletzt
                      aktualisiert:{" "}
                      {formatProjectUpdatedAt(currentProject.updatedAt)}
                    </p>
                  </div>
                  <form
                    key={`${currentProject.id}:${currentProject.name}`}
                    className="project-rename-form"
                    aria-label="Projekt umbenennen"
                    onSubmit={(event) => {
                      event.preventDefault();
                      const form = new FormData(event.currentTarget);
                      void renameProject(
                        currentProject.id,
                        String(form.get("projectName") ?? ""),
                      );
                    }}
                  >
                    <label>
                      Projektname
                      <input
                        name="projectName"
                        defaultValue={currentProject.name}
                        required
                      />
                    </label>
                    <button type="submit" className="secondary">
                      Umbenennen
                    </button>
                  </form>
                </div>
              </section>

              <div
                className="page-tabs"
                role="tablist"
                aria-label="Projektbereiche"
              >
                {(
                  [
                    ["import", "Import"],
                    ["indexing", "Indizieren"],
                    ["cluster-sets", "Cluster-Sets"],
                    ["explorer", "Explorer"],
                    ["delete", "Projekt löschen"],
                  ] as const
                ).map(([tab, label]) => (
                  <button
                    type="button"
                    role="tab"
                    aria-selected={projectTab === tab}
                    className={projectTab === tab ? "selected" : ""}
                    key={tab}
                    onClick={() => setProjectTab(tab)}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </>
          )}

          {activePage === "settings" && (
            <>
              <div
                className="page-tabs"
                role="tablist"
                aria-label="Einstellungen"
              >
                <button
                  type="button"
                  role="tab"
                  aria-selected={settingsTab === "providers"}
                  className={settingsTab === "providers" ? "selected" : ""}
                  onClick={() => setSettingsTab("providers")}
                >
                  Embedding-Provider
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={settingsTab === "llm-providers"}
                  className={settingsTab === "llm-providers" ? "selected" : ""}
                  onClick={() => setSettingsTab("llm-providers")}
                >
                  LLM-Provider
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={settingsTab === "users"}
                  className={settingsTab === "users" ? "selected" : ""}
                  onClick={() => setSettingsTab("users")}
                >
                  Nutzer
                </button>
              </div>
            </>
          )}

          {activePage === "settings" &&
            (settingsTab === "providers" ||
              settingsTab === "llm-providers") && (
              <section id="providers" className="provider-settings">
                <section className="provider-grid">
                  <form
                    className="panel provider-card stack"
                    onSubmit={(event) => configureProvider(event, "openai")}
                    aria-label="OpenAI Provider konfigurieren"
                  >
                    <div className="panel-title">
                      <div>
                        <p className="eyebrow">Cloud</p>
                        <h2>OpenAI</h2>
                      </div>
                      <span
                        className={`provider-status ${
                          openAiProvider?.apiKeySet ? "active" : "idle"
                        }`}
                      >
                        {openAiProvider?.apiKeySet
                          ? "API-Key gesetzt"
                          : "Nicht eingerichtet"}
                      </span>
                    </div>
                    <p className="hint">
                      Modelle werden über den gespeicherten oder neu
                      eingegebenen API-Key abgerufen und danach für Analysen
                      freigegeben.
                    </p>
                    <label className="provider-key-row">
                      Neuer OpenAI API-Key
                      <input
                        name="apiKey"
                        type="password"
                        autoComplete="off"
                        placeholder={
                          openAiProvider?.apiKeySet
                            ? "Neuen API-Key eintragen"
                            : "sk-..."
                        }
                      />
                    </label>
                    <div className="form-actions">
                      <button type="submit">OpenAI speichern</button>
                      <button
                        type="button"
                        className="secondary"
                        onClick={() =>
                          discoverOpenAiModels(openAiSelectedModels, true)
                        }
                      >
                        Modelle abrufen
                      </button>
                    </div>
                    <div
                      className="model-selection"
                      aria-label="OpenAI Modell-Auswahl"
                    >
                      <span className="field-caption">
                        Freigegebene Modelle
                      </span>
                      {(openAiDiscoveredModels.length
                        ? openAiDiscoveredModels
                        : openAiSelectedModels
                      ).map((model) => (
                        <label className="inline-check" key={model}>
                          <input
                            type="checkbox"
                            checked={openAiSelectedModels.includes(model)}
                            onChange={(event) =>
                              toggleOpenAiModel(model, event.target.checked)
                            }
                          />
                          {model}
                        </label>
                      ))}
                      {openAiDiscoveredModels.length === 0 &&
                        openAiSelectedModels.length === 0 && (
                          <p className="hint">Noch keine Modelle abgerufen.</p>
                        )}
                    </div>
                    <label>
                      OpenAI LLM-Modelle
                      <input
                        name="llmModels"
                        defaultValue={
                          openAiProvider?.llmModels.join(", ") ?? ""
                        }
                        placeholder="gpt-4.1-mini"
                      />
                    </label>
                    <label className="inline-check">
                      <input name="removeApiKey" type="checkbox" />
                      Gespeicherten API-Key entfernen
                    </label>
                  </form>

                  <form
                    className="panel provider-card stack"
                    onSubmit={(event) => configureProvider(event, "vllm")}
                    aria-label="vLLM Provider konfigurieren"
                  >
                    <div className="panel-title">
                      <div>
                        <p className="eyebrow">Lokal</p>
                        <h2>vLLM</h2>
                      </div>
                      <span
                        className={`provider-status ${vllmProvider ? "active" : "idle"}`}
                      >
                        {vllmProvider ? "Konfiguriert" : "Nicht eingerichtet"}
                      </span>
                    </div>
                    <p className="hint">
                      vLLM bleibt für dedizierte, bereits gestartete lokale
                      Endpoints mit expliziter Modellliste vorgesehen.
                    </p>
                    <label>
                      Endpoint URL
                      <input
                        name="endpointUrl"
                        defaultValue={vllmProvider?.endpointUrl ?? ""}
                        placeholder="http://localhost:8000"
                      />
                    </label>
                    <label>
                      vLLM Modelle
                      <input
                        name="manualModels"
                        defaultValue={
                          vllmProvider?.manualModels.join(", ") ?? ""
                        }
                        placeholder="local-embed, local-chat"
                      />
                    </label>
                    <div className="provider-meta">
                      <span className="field-caption">Aktuelle Modelle</span>
                      <p className="hint">
                        {vllmProvider?.manualModels.length
                          ? vllmProvider.manualModels.join(", ")
                          : "keine"}
                      </p>
                    </div>
                    <div className="form-actions">
                      <button type="submit">vLLM speichern</button>
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => discoverProviderModels("vllm")}
                      >
                        Modelle abrufen
                      </button>
                    </div>
                  </form>

                  <form
                    className="panel provider-card stack"
                    onSubmit={(event) => configureProvider(event, "ollama")}
                    aria-label="Ollama Provider konfigurieren"
                  >
                    <div className="panel-title">
                      <div>
                        <p className="eyebrow">Lokal</p>
                        <h2>Ollama</h2>
                      </div>
                      <span
                        className={`provider-status ${ollamaProvider ? "active" : "idle"}`}
                      >
                        {ollamaProvider ? "Konfiguriert" : "Nicht eingerichtet"}
                      </span>
                    </div>
                    <p className="hint">
                      Ollama verwaltet lokale Modelle. Neue Modelle können hier
                      heruntergeladen und danach direkt für Analysen verwendet
                      werden.
                    </p>
                    <label>
                      Endpoint URL
                      <input
                        name="endpointUrl"
                        defaultValue={ollamaProvider?.endpointUrl ?? ""}
                        placeholder="http://localhost:11434"
                      />
                    </label>
                    <div className="provider-meta">
                      <span className="field-caption">
                        Installierte Modelle
                      </span>
                      <p className="hint">
                        {ollamaProvider?.manualModels.length
                          ? ollamaProvider.manualModels.join(", ")
                          : "keine"}
                      </p>
                    </div>
                    <label>
                      Ollama LLM-Modelle
                      <input
                        name="llmModels"
                        defaultValue={
                          ollamaProvider?.llmModels.join(", ") ?? ""
                        }
                        placeholder="llama3.1"
                      />
                    </label>
                    <div className="provider-meta">
                      <span className="field-caption">
                        Aktuelle LLM-Modelle
                      </span>
                      <p className="hint">
                        {ollamaProvider?.llmModels.length
                          ? ollamaProvider.llmModels.join(", ")
                          : "keine"}
                      </p>
                    </div>
                    <div className="form-actions">
                      <button type="submit">Ollama speichern</button>
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => discoverProviderModels("ollama")}
                      >
                        Modelle abrufen
                      </button>
                    </div>
                    <div className="inline-form provider-pull-row">
                      <label>
                        Neues Ollama Modell
                        <input
                          name="pullModel"
                          placeholder="nomic-embed-text"
                        />
                      </label>
                      <button
                        type="button"
                        className="secondary"
                        onClick={(event) => {
                          const form = event.currentTarget.closest("form");
                          if (form !== null) {
                            void pullOllamaModel(form);
                          }
                        }}
                      >
                        Herunterladen und hinzufügen
                      </button>
                    </div>
                  </form>
                </section>
              </section>
            )}

          {activePage === "projects" && (
            <>
              {projectTab === "indexing" && (
                <section id="indexing" className="panel-grid">
                  <form
                    className="panel stack"
                    onSubmit={startIndexingRun}
                    aria-label="Indizierung starten"
                  >
                    <p className="eyebrow">Indizierung</p>
                    <h2>Datensatz indizieren</h2>
                    <p className="hint">
                      Embeddings werden direkt für einen Datensatz erzeugt.
                      Cluster-Parameter werden erst im nächsten Schritt gewählt.
                    </p>
                    <label>
                      Datensatz
                      <select name="datasetVersionId">
                        {runnableDatasetLogs.length === 0 && (
                          <option value="">Kein aktiver Datensatz</option>
                        )}
                        {runnableDatasetLogs.map((log) => (
                          <option
                            key={log.datasetVersionId ?? log.id}
                            value={log.datasetVersionId ?? ""}
                          >
                            {datasetLabel(log)} / {log.datasetVersionId}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Embedding-Provider
                      <select
                        name="provider"
                        value={indexingProvider}
                        onChange={(event) => {
                          setIndexingProvider(
                            event.target.value as ConfigurableProvider,
                          );
                          setCloudUseConfirmed(false);
                        }}
                      >
                        <option value="vllm">vLLM lokal</option>
                        <option value="ollama">Ollama lokal</option>
                        <option value="openai">OpenAI Cloud</option>
                      </select>
                    </label>
                    <label>
                      Embedding-Modell
                      <select
                        name="model"
                        value={indexingModel}
                        disabled={indexingProviderModels.length === 0}
                        onChange={(event) =>
                          setIndexingModel(event.target.value)
                        }
                        required
                      >
                        {indexingProviderModels.length === 0 && (
                          <option value="">Keine Modelle verfügbar</option>
                        )}
                        {indexingProviderModels.map((model) => (
                          <option key={model} value={model}>
                            {model}
                          </option>
                        ))}
                      </select>
                    </label>
                    <p
                      className={
                        indexingProviderModels.length === 0
                          ? "status warning"
                          : "hint"
                      }
                      role="status"
                    >
                      {indexingProviderModels.length === 0
                        ? "Für diesen Provider ist noch kein Modell konfiguriert. Bitte zuerst die Provider-Einstellungen ergänzen."
                        : `${indexingProviderModels.length} Modell(e) für ${indexingProvider} verfügbar.`}
                    </p>
                    {indexingProvider === "openai" && (
                      <label className="confirmation-field">
                        <input
                          name="cloudUseConfirmed"
                          type="checkbox"
                          checked={cloudUseConfirmed}
                          onChange={(event) =>
                            setCloudUseConfirmed(event.target.checked)
                          }
                        />
                        Ich bestätige, dass die importierten Nachrichtentexte
                        für diese Indizierung an OpenAI übertragen werden.
                      </label>
                    )}
                    <button
                      type="submit"
                      disabled={
                        runnableDatasetLogs.length === 0 ||
                        !indexingProviderModels.includes(indexingModel) ||
                        (indexingProvider === "openai" && !cloudUseConfirmed)
                      }
                    >
                      Indizierung starten
                    </button>
                  </form>

                  <section className="panel" aria-label="Indizierungen">
                    <h2>Indizierungen</h2>
                    <div className="user-list">
                      {indexingRuns.length === 0 && (
                        <p className="hint">
                          Noch keine Indizierungen für dieses Projekt.
                        </p>
                      )}
                      {indexingRuns.map((run) => (
                        <article className="user-card" key={run.id}>
                          <div className="user-heading">
                            <strong>{run.status}</strong>
                            <span>{run.progress}%</span>
                          </div>
                          <progress value={run.progress} max={100}>
                            {run.progress}%
                          </progress>
                          <p className="hint">Phase: {run.phase}</p>
                          <p className="hint">
                            Provider/Modell: {run.provider}/{run.model}
                          </p>
                          <p className="hint">
                            Datensatz: {run.datasetDisplayName ?? "-"}; Version:{" "}
                            {run.datasetVersionId}
                          </p>
                          {run.datasetDeletedAt !== null && (
                            <p className="status warning">
                              Datensatz gelöscht: {run.datasetDeletedAt}
                            </p>
                          )}
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
                          <div className="form-actions">
                            <button
                              type="button"
                              className="secondary"
                              disabled={
                                run.status !== "queued" &&
                                run.status !== "running"
                              }
                              onClick={() => void cancelIndexingRun(run.id)}
                            >
                              Abbrechen
                            </button>
                            <button
                              type="button"
                              className="secondary"
                              onClick={() => void deleteIndexingRun(run.id)}
                            >
                              Löschen
                            </button>
                          </div>
                        </article>
                      ))}
                    </div>
                  </section>
                </section>
              )}

              {projectTab === "cluster-sets" && (
                <section id="cluster-sets" className="panel-grid">
                  <form
                    className="panel stack"
                    onSubmit={createClusterSet}
                    aria-label="Cluster-Set erstellen"
                  >
                    <p className="eyebrow">Cluster-Sets</p>
                    <h2>Cluster-Set erstellen</h2>
                    <p className="hint">
                      Cluster-Sets speichern Analyseparameter, Vektor-Basis,
                      Quelle und optional LLM-Zusammenfassungen.
                    </p>
                    {clusterSetRefinementDraft !== null ? (
                      <section className="status info" role="status">
                        <strong>Verfeinerung vorausgefüllt</strong>
                        <p>
                          {clusterSetRefinementDraft.description}. Parent:{" "}
                          {clusterSetRefinementDraft.parentClusterSetId}
                        </p>
                        <input
                          type="hidden"
                          name="indexingRunId"
                          value={clusterSetRefinementDraft.indexingRunId}
                        />
                        <button
                          type="button"
                          className="secondary"
                          onClick={() => setClusterSetRefinementDraft(null)}
                        >
                          Verfeinerung zurücksetzen
                        </button>
                      </section>
                    ) : (
                      <label>
                        Indizierung
                        <select name="indexingRunId" required>
                          {completedIndexingRuns.length === 0 && (
                            <option value="">
                              Keine abgeschlossene Indizierung
                            </option>
                          )}
                          {completedIndexingRuns.map((run) => (
                            <option key={run.id} value={run.id}>
                              {run.datasetDisplayName ?? run.datasetVersionId} /{" "}
                              {run.model}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                    <label>
                      Anzeigename
                      <input
                        name="displayName"
                        placeholder="z. B. Antworten grob"
                      />
                    </label>
                    <label>
                      Vektor-Basis
                      <select
                        name="vectorBasis"
                        value={clusterSetVectorBasis}
                        onChange={(event) =>
                          setClusterSetVectorBasis(event.target.value)
                        }
                      >
                        <option value="message">Nachricht</option>
                        <option value="answer">Antwort</option>
                        <option value="combined">Q/A kombiniert</option>
                      </select>
                    </label>
                    {clusterSetVectorBasis === "combined" && (
                      <div className="inline-form">
                        <label>
                          Nachricht-Gewicht
                          <input
                            name="messageWeight"
                            type="number"
                            min="0"
                            step="0.1"
                            defaultValue="0.5"
                          />
                        </label>
                        <label>
                          Antwort-Gewicht
                          <input
                            name="answerWeight"
                            type="number"
                            min="0"
                            step="0.1"
                            defaultValue="0.5"
                          />
                        </label>
                      </div>
                    )}
                    <div className="inline-form">
                      <label>
                        HDBSCAN min_cluster_size
                        <input
                          name="minClusterSize"
                          type="number"
                          min="2"
                          defaultValue="2"
                        />
                      </label>
                      <label>
                        min_samples optional
                        <input name="minSamples" type="number" min="1" />
                      </label>
                      <label>
                        selection_epsilon
                        <input
                          name="clusterSelectionEpsilon"
                          type="number"
                          min="0"
                          step="0.01"
                          defaultValue="0"
                        />
                      </label>
                      <label>
                        Outlier-Schwelle optional
                        <input
                          name="outlierThreshold"
                          type="number"
                          min="0"
                          max="1"
                          step="0.01"
                        />
                      </label>
                    </div>
                    <label>
                      LLM-Zusammenfassung
                      <select
                        name="llmProvider"
                        value={clusterSetLlmProvider}
                        onChange={(event) =>
                          setClusterSetLlmProvider(
                            event.target.value as LlmProviderSelection,
                          )
                        }
                      >
                        <option value="">Keine Zusammenfassung</option>
                        <option value="ollama">Ollama lokal</option>
                        <option value="openai">OpenAI Cloud</option>
                      </select>
                    </label>
                    {clusterSetLlmProvider !== "" && (
                      <>
                        <label>
                          LLM-Modell
                          <select
                            name="llmModel"
                            required
                            disabled={clusterSetLlmProviderModels.length === 0}
                          >
                            {clusterSetLlmProviderModels.length === 0 && (
                              <option value="">Keine Modelle verfügbar</option>
                            )}
                            {clusterSetLlmProviderModels.map((model) => (
                              <option key={model} value={model}>
                                {model}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label>
                          Beispiele pro Cluster
                          <input
                            name="llmSampleCount"
                            type="number"
                            min="1"
                            step="any"
                            defaultValue="10"
                            disabled={clusterSetLlmSampleAll}
                          />
                        </label>
                        <label className="inline-check">
                          <input
                            name="llmSampleAll"
                            type="checkbox"
                            checked={clusterSetLlmSampleAll}
                            onChange={(event) =>
                              setClusterSetLlmSampleAll(event.target.checked)
                            }
                          />
                          Alle Beispiele je Cluster verwenden
                        </label>
                      </>
                    )}
                    {clusterSetLlmProvider === "openai" && (
                      <label className="confirmation-field">
                        <input
                          name="llmCloudUseConfirmed"
                          type="checkbox"
                          checked={clusterSetCloudUseConfirmed}
                          onChange={(event) =>
                            setClusterSetCloudUseConfirmed(event.target.checked)
                          }
                        />
                        Ich bestätige, dass Beispieltexte für
                        Cluster-Zusammenfassungen an OpenAI übertragen werden.
                      </label>
                    )}
                    <button
                      type="submit"
                      disabled={
                        (clusterSetRefinementDraft === null &&
                          completedIndexingRuns.length === 0) ||
                        clusterSetGenerationRequest !== null ||
                        (clusterSetLlmProvider !== "" &&
                          clusterSetLlmProviderModels.length === 0) ||
                        (clusterSetLlmProvider === "openai" &&
                          !clusterSetCloudUseConfirmed)
                      }
                    >
                      {clusterSetGenerationRequest === null
                        ? clusterSetRefinementDraft === null
                          ? "Cluster-Set erstellen"
                          : "Verfeinerung erstellen"
                        : "Cluster-Set wird erstellt"}
                    </button>
                  </form>

                  <section className="panel" aria-label="Cluster-Sets">
                    <h2>Gespeicherte Cluster-Sets</h2>
                    <div className="user-list">
                      {clusterSets.length === 0 && (
                        <p className="hint">
                          Noch keine Cluster-Sets für dieses Projekt.
                        </p>
                      )}
                      {rootClusterSets.map((clusterSet) =>
                        renderClusterSetCard(clusterSet),
                      )}
                    </div>
                  </section>
                </section>
              )}

              {projectTab === "explorer" && (
                <section id="explorer" className="explorer-layout">
                  <section
                    className="panel cluster-explorer"
                    aria-label="Cluster Explorer"
                  >
                    <div className="panel-title">
                      <div>
                        <p className="eyebrow">Explorer</p>
                        <h2>Cluster Explorer</h2>
                      </div>
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => setProjectTab("cluster-sets")}
                      >
                        Cluster-Set auswählen
                      </button>
                    </div>

                    {loadedClusterSet === null ? (
                      <p className="hint">
                        Noch kein abgeschlossenes Cluster-Set geladen. Wähle im
                        Tab „Cluster-Sets“ einen fertigen Satz aus.
                      </p>
                    ) : (
                      <>
                        <div
                          className="metric-grid"
                          aria-label="Explorer Kennzahlen"
                        >
                          <div>
                            <span className="field-caption">Geladenes Set</span>
                            <strong>{loadedClusterSet.displayName}</strong>
                          </div>
                          <div>
                            <span className="field-caption">Cluster</span>
                            <strong>{clusters.length}</strong>
                          </div>
                          <div>
                            <span className="field-caption">Sichtbar</span>
                            <strong>{visibleClusters.length}</strong>
                          </div>
                          <div>
                            <span className="field-caption">
                              Ausgeschlossen
                            </span>
                            <strong>
                              {clusters.filter(clusterIsExcluded).length}
                            </strong>
                          </div>
                        </div>

                        <section
                          className="analysis-path"
                          aria-label="Analysepfad"
                        >
                          <span className="field-caption">Analysepfad</span>
                          <ol>
                            <li>
                              Import:{" "}
                              {loadedClusterSet.datasetDisplayName ?? "-"}
                            </li>
                            <li>
                              Indizierung: {loadedClusterSet.indexingRunId}
                            </li>
                            {loadedAnalysisPath.map((clusterSet) => (
                              <li key={clusterSet.id}>
                                {formatClusterSetType(
                                  clusterSet.derivationType,
                                )}
                                : {clusterSet.displayName}
                                {clusterSet.deletedAt !== null
                                  ? " (gelöscht)"
                                  : ""}
                              </li>
                            ))}
                          </ol>
                        </section>

                        <section
                          className="explorer-controls"
                          aria-label="Explorer Filter"
                        >
                          <label>
                            Textsuche
                            <input
                              value={clusterSearchQuery}
                              onChange={(event) =>
                                setClusterSearchQuery(event.target.value)
                              }
                              placeholder="Titel, Kategorie, Summary oder Status"
                            />
                          </label>
                          <label>
                            Kategorie
                            <select
                              value={clusterCategoryFilter}
                              onChange={(event) =>
                                setClusterCategoryFilter(event.target.value)
                              }
                            >
                              <option value="">Alle Kategorien</option>
                              {clusterCategories.map((category) => (
                                <option key={category} value={category}>
                                  {category}
                                </option>
                              ))}
                            </select>
                          </label>
                          <label className="inline-check">
                            <input
                              type="checkbox"
                              checked={clusterGroupByCategory}
                              onChange={(event) =>
                                setClusterGroupByCategory(event.target.checked)
                              }
                            />
                            Nach Kategorie gruppieren
                          </label>
                          <label className="inline-check">
                            <input
                              type="checkbox"
                              checked={showExcludedClusters}
                              onChange={(event) =>
                                setShowExcludedClusters(event.target.checked)
                              }
                            />
                            Ausgeschlossene anzeigen
                          </label>
                          <label className="inline-check">
                            <input
                              type="checkbox"
                              checked={includeOutlierRows}
                              onChange={(event) =>
                                setIncludeOutlierRows(event.target.checked)
                              }
                            />
                            Ausreißer in Tabelle anzeigen
                          </label>
                        </section>

                        <section
                          className="outlier-box"
                          aria-label="Ausreißer ausschließen"
                        >
                          <h2>Ausreißer ausschließen</h2>
                          <p className="hint">
                            Diese Aktion verändert das Analyseergebnis und
                            erstellt deshalb ein neues Child-Cluster-Set.
                          </p>
                          <div className="inline-form">
                            <label>
                              Threshold
                              <input
                                type="number"
                                min="0"
                                max="1"
                                step="0.01"
                                value={outlierThreshold}
                                onChange={(event) =>
                                  setOutlierThreshold(event.target.value)
                                }
                              />
                            </label>
                            <button
                              type="button"
                              onClick={() => void createOutlierExclusionSet()}
                            >
                              Ausreißer berechnen
                            </button>
                          </div>
                        </section>

                        {clusters.length > 0 &&
                          visibleClusters.length === 0 && (
                            <p className="status info" role="status">
                              {ERROR_MESSAGES_BY_CODE.CLUSTER_SEARCH_NO_RESULTS}
                            </p>
                          )}

                        <div className="cluster-table-wrap" tabIndex={0}>
                          <table className="cluster-table">
                            <thead>
                              <tr>
                                <th>Status</th>
                                <th>Titel</th>
                                <th>Kategorie</th>
                                <th>Frage</th>
                                <th>Antwort</th>
                                <th>Kundenanfragen</th>
                                <th>Supportantworten</th>
                                <th>Hinweise</th>
                                <th>Aktionen</th>
                              </tr>
                            </thead>
                            <tbody>
                              {includedClusterGroups.map((group) => (
                                <Fragment key={group.key}>
                                  {clusterGroupByCategory && (
                                    <tr className="group-row">
                                      <td colSpan={9}>{group.label}</td>
                                    </tr>
                                  )}
                                  {group.clusters.map((cluster) =>
                                    renderClusterTableRow(cluster),
                                  )}
                                </Fragment>
                              ))}
                            </tbody>
                          </table>
                        </div>

                        {showExcludedClusters && (
                          <section
                            className="excluded-section"
                            aria-label="Ausgeschlossene Cluster"
                          >
                            <h2>Ausgeschlossene Cluster</h2>
                            {visibleExcludedClusters.length === 0 ? (
                              <p className="hint">
                                Keine ausgeschlossenen Cluster sichtbar.
                              </p>
                            ) : (
                              <div className="cluster-table-wrap" tabIndex={0}>
                                <table className="cluster-table">
                                  <tbody>
                                    {visibleExcludedClusters.map((cluster) =>
                                      renderClusterTableRow(cluster),
                                    )}
                                  </tbody>
                                </table>
                              </div>
                            )}
                          </section>
                        )}

                        <div className="form-actions">
                          <button
                            type="button"
                            onClick={createRefinementDraftFromVisibleClusters}
                          >
                            Eingeschlossene Cluster verfeinern
                          </button>
                        </div>
                      </>
                    )}
                  </section>

                  <section className="panel stack" aria-label="Explorer Export">
                    <p className="eyebrow">Export</p>
                    <h2>Explorer exportieren</h2>
                    <p className="hint">
                      Exportiert die aktuelle gefilterte Explorer-Tabelle ohne
                      Originaltexte aus dem Quellen-Dialog.
                    </p>
                    {explorerExportError !== null && (
                      <div className="status error stack" role="alert">
                        <strong>Explorer-Export fehlgeschlagen.</strong>
                        <p>{explorerExportError}</p>
                        <p className="hint">
                          Filter und Format bleiben erhalten. Bitte Eingaben
                          anpassen oder den Export erneut starten.
                        </p>
                      </div>
                    )}
                    <form className="stack" onSubmit={createExplorerExport}>
                      <label>
                        Format
                        <select
                          value={explorerExportFormat}
                          onChange={(event) =>
                            setExplorerExportFormat(
                              event.target.value as ExplorerExportFormat,
                            )
                          }
                        >
                          <option value="csv">CSV</option>
                          <option value="json">JSON</option>
                        </select>
                      </label>
                      <button
                        type="submit"
                        disabled={
                          loadedClusterSet === null ||
                          visibleClusters.length === 0
                        }
                      >
                        Aktuelle Tabelle exportieren
                      </button>
                    </form>
                    <section aria-label="Exporthistorie">
                      <h2>Exporthistorie</h2>
                      <div className="user-list">
                        {visibleExportLogs.length === 0 && (
                          <p className="hint">
                            Noch keine Explorer-Exporte für dieses Projekt.
                          </p>
                        )}
                        {visibleExportLogs.map((log) => (
                          <article className="user-card" key={log.id}>
                            <div className="user-heading">
                              <strong>{log.outputFilename}</strong>
                              <span>{log.exportType}</span>
                            </div>
                            <p className="hint">
                              Zeilen: {log.rowCount}; Cluster-Set:{" "}
                              {log.clusterSetId ?? "-"}
                            </p>
                            <p className="hint">Erstellt: {log.createdAt}</p>
                          </article>
                        ))}
                      </div>
                    </section>
                    {lastExportContent && (
                      <pre
                        className="log-detail"
                        aria-label="Letzter Explorer Export"
                        tabIndex={0}
                      >
                        {lastExportContentType}:{"\n"}
                        {lastExportContent}
                      </pre>
                    )}
                  </section>

                  {sourceDialogCluster !== null && (
                    <div className="dialog-backdrop">
                      <section
                        className="source-dialog"
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="source-dialog-title"
                        ref={sourceDialogRef}
                      >
                        <div className="panel-title">
                          <div>
                            <p className="eyebrow">Quellen</p>
                            <h2 id="source-dialog-title">
                              {sourceDialogCluster.effectiveTitle}
                            </h2>
                          </div>
                          <button
                            type="button"
                            className="secondary"
                            ref={sourceDialogCloseRef}
                            onClick={closeSourceDialog}
                          >
                            Schließen
                          </button>
                        </div>
                        {!sourceDialogLoaded ? (
                          <p className="hint" role="status">
                            Quellen werden geladen.
                          </p>
                        ) : sourceDialogError !== null &&
                          clusterSources.length === 0 ? (
                          <div className="status error stack" role="alert">
                            <strong>
                              Quellen konnten nicht geladen werden.
                            </strong>
                            <p>{sourceDialogError}</p>
                            <button
                              type="button"
                              className="secondary"
                              onClick={() =>
                                void loadClusterSourcePage(
                                  sourceDialogCluster,
                                  0,
                                  { append: false },
                                )
                              }
                            >
                              Quellen erneut laden
                            </button>
                          </div>
                        ) : clusterSources.length === 0 ? (
                          <p className="hint">
                            Keine Quellen für diesen Cluster vorhanden.
                          </p>
                        ) : (
                          <>
                            {sourceDialogError !== null && (
                              <div className="status error stack" role="alert">
                                <strong>
                                  Weitere Quellen konnten nicht geladen werden.
                                </strong>
                                <p>{sourceDialogError}</p>
                              </div>
                            )}
                            <div className="source-list">
                              {clusterSources.map((source) => (
                                <article
                                  className="user-card"
                                  key={source.messagePairId}
                                >
                                  <strong>
                                    Ticket {source.ticketId} · Gruppe{" "}
                                    {source.messageGroupId}
                                  </strong>
                                  <p>Kundenfrage: {source.message}</p>
                                  <p>Supportantwort: {source.answer}</p>
                                  <p className="hint">
                                    Score: {formatScore(source.membershipScore)}
                                    ; Assignment: {source.assignmentType}
                                    {source.isOutlier ? "; Ausreißer" : ""}
                                  </p>
                                </article>
                              ))}
                            </div>
                            <div className="source-dialog-footer">
                              {sourceDialogNextOffset !== null && (
                                <button
                                  type="button"
                                  className="secondary"
                                  disabled={sourceDialogLoadingMore}
                                  onClick={() => void loadMoreClusterSources()}
                                >
                                  {sourceDialogLoadingMore
                                    ? "Weitere Quellen werden geladen"
                                    : "Weitere Quellen laden"}
                                </button>
                              )}
                              <p className="hint">
                                Angezeigt: {clusterSources.length} Quelle
                                {clusterSources.length === 1 ? "" : "n"}.
                              </p>
                            </div>
                          </>
                        )}
                      </section>
                    </div>
                  )}
                </section>
              )}

              {currentProject && projectTab === "import" && (
                <section id="imports" className="panel-grid">
                  <form
                    className="panel stack"
                    onSubmit={importFile}
                    aria-label="Import starten"
                  >
                    <p className="eyebrow">Import</p>
                    <h2>CSV/JSON importieren</h2>
                    <p className="hint">
                      Erwartete Felder: ticket_id, message_group_id, message,
                      answer. Ungültige Datensätze werden übersprungen und
                      protokolliert. Maximale Dateigröße: 512 MiB.
                    </p>
                    <label>
                      Importdatei
                      <input
                        name="importFile"
                        type="file"
                        accept=".csv,.json"
                      />
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
                          Noch keine Imports für dieses Projekt.
                        </p>
                      )}
                      {importLogs.map((log) => (
                        <article className="user-card" key={log.id}>
                          <div className="user-heading">
                            <strong>{log.sourceName}</strong>
                            <span>{log.status}</span>
                          </div>
                          <p className="hint">
                            Total: {log.totalRecords}; importiert:{" "}
                            {log.validRecords}; übersprungen:{" "}
                            {log.skippedRecords}
                          </p>
                          {log.failureReason && (
                            <p className="error">{log.failureReason}</p>
                          )}
                          {log.datasetVersionId && (
                            <div className="stack">
                              <p className="hint">
                                Dataset-Version: {log.datasetVersionId}
                              </p>
                              <label>
                                Datensatzname
                                <input
                                  defaultValue={datasetLabel(log)}
                                  disabled={log.datasetDeletedAt !== null}
                                  onBlur={(event) => {
                                    if (
                                      event.target.value.trim() !==
                                      datasetLabel(log)
                                    ) {
                                      void renameDatasetVersion(
                                        log.datasetVersionId ?? "",
                                        event.target.value,
                                      );
                                    }
                                  }}
                                />
                              </label>
                              {log.datasetDeletedAt === null ? (
                                <button
                                  type="button"
                                  className="secondary"
                                  onClick={() =>
                                    void deleteDatasetVersion(
                                      log.datasetVersionId ?? "",
                                    )
                                  }
                                >
                                  Datensatz löschen
                                </button>
                              ) : (
                                <p className="status warning">
                                  Datensatz gelöscht: {log.datasetDeletedAt}
                                </p>
                              )}
                            </div>
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
                      <div
                        className="log-detail"
                        aria-label="Import Logdetails"
                      >
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
              {activePage === "projects" && currentProject === null && (
                <section
                  className="project-home"
                  aria-label="Project Home Aktionen"
                >
                  <form
                    className="panel project-create-form"
                    onSubmit={createProject}
                    aria-label="Projekt erstellen"
                  >
                    <h2>Projekt erstellen</h2>
                    <label>
                      Projektname
                      <input name="projectName" required />
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
                        <button
                          type="button"
                          className="project-row"
                          key={project.id}
                          aria-label={`${project.name}, zuletzt aktualisiert ${formatProjectUpdatedAt(project.updatedAt)}`}
                          onClick={() => void openProject(project.id)}
                        >
                          <strong>{project.name}</strong>
                          <span>
                            {formatProjectUpdatedAt(project.updatedAt)}
                          </span>
                        </button>
                      ))}
                    </div>
                  </section>
                </section>
              )}

              {currentProject && projectTab === "delete" && (
                <section className="panel-grid" aria-label="Projekt löschen">
                  <section className="panel stack">
                    <p className="eyebrow">Gefahrenbereich</p>
                    <h2>Projekt löschen</h2>
                    <p className="hint">
                      Löscht das Projekt dauerhaft. Zur Bestätigung muss der
                      Projektname exakt eingegeben werden.
                    </p>
                  </section>
                  <form
                    className="panel stack"
                    onSubmit={(event) =>
                      deleteProject(event, currentProject.id)
                    }
                    aria-label="Projekt löschen"
                  >
                    <label>
                      Projektname bestätigen
                      <input name="confirmationName" />
                    </label>
                    <button type="submit" className="danger">
                      Projekt löschen
                    </button>
                  </form>
                </section>
              )}
            </>
          )}

          {activePage === "settings" && settingsTab === "users" && (
            <section id="users" className="admin-grid">
              <form
                className="panel user-form stack"
                onSubmit={createUser}
                aria-label="User anlegen"
              >
                <div className="panel-title">
                  <div>
                    <p className="eyebrow">Nutzerverwaltung</p>
                    <h2>Nutzer anlegen</h2>
                  </div>
                </div>
                <label>
                  Name
                  <input name="name" autoComplete="name" />
                </label>
                <label>
                  E-Mail
                  <input name="email" type="email" autoComplete="email" />
                </label>
                <label>
                  Initiales Passwort
                  <input
                    name="password"
                    type="password"
                    autoComplete="new-password"
                  />
                </label>
                <div className="form-actions">
                  <button type="submit" disabled={isLoading}>
                    User erstellen
                  </button>
                </div>
              </form>

              <section
                className="panel users-panel"
                aria-label="Bestehende User"
              >
                <div className="panel-title">
                  <div>
                    <p className="eyebrow">Konten</p>
                    <h2>Aktive Nutzer</h2>
                  </div>
                </div>
                <div
                  className="users-table"
                  role="table"
                  aria-label="Aktive Nutzer"
                >
                  <div className="table-row table-head" role="row">
                    <span role="columnheader">Name</span>
                    <span role="columnheader">E-Mail</span>
                    <span role="columnheader">Passwort</span>
                    <span role="columnheader">Aktionen</span>
                  </div>
                  {users.map((user) => {
                    const isSelf = user.id === session.user.id;
                    return (
                      <div
                        className="table-row user-row"
                        role="row"
                        key={user.id}
                      >
                        <span role="cell">
                          <input
                            aria-label={`Name für ${user.email}`}
                            value={user.name}
                            onChange={(event) =>
                              updateUser(user.id, "name", event.target.value)
                            }
                          />
                        </span>
                        <span role="cell">
                          <input
                            aria-label={`E-Mail für ${user.email}`}
                            value={user.email}
                            onChange={(event) =>
                              updateUser(user.id, "email", event.target.value)
                            }
                          />
                        </span>
                        <span role="cell">
                          <input
                            aria-label={`Neues Passwort für ${user.email}`}
                            type="password"
                            autoComplete="new-password"
                            onBlur={(event) =>
                              setPassword(user.id, event.target.value)
                            }
                          />
                        </span>
                        <span className="row-actions" role="cell">
                          {isSelf && (
                            <span className="self-badge">Aktuell</span>
                          )}
                          <button
                            type="button"
                            className="danger"
                            disabled={isSelf}
                            onClick={() => deleteUser(user.id)}
                            aria-label={
                              isSelf
                                ? "Selbstlöschung gesperrt"
                                : "User löschen"
                            }
                            title={
                              isSelf
                                ? "Selbstlöschung gesperrt"
                                : "User löschen"
                            }
                          >
                            <svg
                              aria-hidden="true"
                              className="button-icon-svg"
                              viewBox="0 0 24 24"
                            >
                              <path d="M9 3h6l1 2h4v2H4V5h4l1-2Z" />
                              <path d="M6 9h12l-1 11H7L6 9Zm4 2v7h2v-7h-2Zm4 0v7h2v-7h-2Z" />
                            </svg>
                          </button>
                        </span>
                      </div>
                    );
                  })}
                </div>
              </section>
            </section>
          )}
        </section>
      </div>
    </main>
  );
}

export default App;
