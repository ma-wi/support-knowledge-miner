import { useEffect, useRef, useState } from "react";
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

const MAX_IMPORT_BYTES = 512 * 1024 * 1024;

type ApiProviderConfiguration = {
  provider: string;
  endpoint_url: string | null;
  manual_models: string[];
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
  apiKeySet: boolean;
  updatedAt: string;
};

type ConfigurableProvider = "openai" | "ollama" | "vllm";
type ProfileAlgorithm = "hdbscan" | "agglomerative";
type AgglomerativeCriterion = "n_clusters" | "distance_threshold";
type ProjectProfileLoadState = {
  projectId: string | null;
  status: "idle" | "loading" | "ready" | "error";
};
type AuthoritativeProjectContext = {
  projectId: string | null;
  generation: number;
  ready: boolean;
};
type ClusterGenerationRequest = {
  projectId: string;
  runId: string;
  generation: number;
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

type ApiCluster = {
  id: string;
  project_id: string;
  analysis_run_id: string;
  dataset_version_id: string;
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
};

type Cluster = {
  id: string;
  projectId: string;
  analysisRunId: string;
  datasetVersionId: string;
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

type ApiCandidate = {
  id: string;
  project_id: string;
  dataset_version_id: string;
  analysis_run_id: string | null;
  source_cluster_id: string | null;
  candidate_type: string;
  auto_status: string;
  manual_status: string | null;
  effective_status: string;
  language: string;
  auto_category_path: string | null;
  manual_category_path: string | null;
  effective_category_path: string | null;
  auto_title: string;
  manual_title: string | null;
  effective_title: string;
  auto_canonical_question: string;
  manual_canonical_question: string | null;
  effective_canonical_question: string;
  auto_canonical_answer: string;
  manual_canonical_answer: string | null;
  effective_canonical_answer: string;
  auto_alternative_questions: string[];
  manual_alternative_questions: string[] | null;
  effective_alternative_questions: string[];
  auto_parameters: Record<string, unknown>;
  manual_parameters: Record<string, unknown> | null;
  effective_parameters: Record<string, unknown>;
  auto_external_data_dependencies: string[];
  manual_external_data_dependencies: string[] | null;
  effective_external_data_dependencies: string[];
  quality_score: number;
  faq_suitability_score: number;
  dynamicity_score: number;
  contradiction_score: number;
  source_pair_count: number;
  source_cluster_ids: string[];
  notes: string | null;
  metadata: Record<string, unknown>;
};

type Candidate = {
  id: string;
  projectId: string;
  datasetVersionId: string;
  analysisRunId: string | null;
  sourceClusterId: string | null;
  candidateType: string;
  autoStatus: string;
  manualStatus: string | null;
  effectiveStatus: string;
  language: string;
  autoCategoryPath: string | null;
  manualCategoryPath: string | null;
  effectiveCategoryPath: string | null;
  autoTitle: string;
  manualTitle: string | null;
  effectiveTitle: string;
  autoCanonicalQuestion: string;
  manualCanonicalQuestion: string | null;
  effectiveCanonicalQuestion: string;
  autoCanonicalAnswer: string;
  manualCanonicalAnswer: string | null;
  effectiveCanonicalAnswer: string;
  autoAlternativeQuestions: string[];
  manualAlternativeQuestions: string[] | null;
  effectiveAlternativeQuestions: string[];
  autoParameters: Record<string, unknown>;
  manualParameters: Record<string, unknown> | null;
  effectiveParameters: Record<string, unknown>;
  autoExternalDataDependencies: string[];
  manualExternalDataDependencies: string[] | null;
  effectiveExternalDataDependencies: string[];
  qualityScore: number;
  faqSuitabilityScore: number;
  dynamicityScore: number;
  contradictionScore: number;
  sourcePairCount: number;
  sourceClusterIds: string[];
  notes: string | null;
  metadata: Record<string, unknown>;
};

type ApiCandidateSource = {
  candidate_id: string;
  cluster_id: string | null;
  message_pair_id: string;
  ticket_id: string;
  message_group_id: string;
  message: string;
  answer: string;
  message_segment_id: string | null;
  source_language: string;
  normalized_customer_message: string | null;
  normalized_support_answer: string | null;
  assignment_type: string;
  membership_score: number;
  is_multi_intent: boolean;
  intent_label: string | null;
  dataset_version_id: string;
  analysis_run_id: string | null;
};

type CandidateSource = {
  candidateId: string;
  clusterId: string | null;
  messagePairId: string;
  ticketId: string;
  messageGroupId: string;
  message: string;
  answer: string;
  messageSegmentId: string | null;
  sourceLanguage: string;
  normalizedCustomerMessage: string | null;
  normalizedSupportAnswer: string | null;
  assignmentType: string;
  membershipScore: number;
  isMultiIntent: boolean;
  intentLabel: string | null;
  datasetVersionId: string;
  analysisRunId: string | null;
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
type SettingsTab = "providers" | "users";
type ProjectTab =
  | "profiles"
  | "import"
  | "runs"
  | "clusters"
  | "candidates"
  | "exports"
  | "delete";

const API_BASE = import.meta.env.VITE_SKM_API_BASE_URL ?? "";
const INTERNAL_LAST_NAME_PLACEHOLDER = "-";
const SESSION_TOKEN_STORAGE_KEY = "skm.session-token";
const RUN_POLL_INTERVAL_MS = 2000;
const FEEDBACK_LABELS: Record<FeedbackKind, string> = {
  success: "Erfolg",
  info: "Hinweis",
  warning: "Warnung",
  error: "Fehler",
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

function toCluster(cluster: ApiCluster): Cluster {
  return {
    id: cluster.id,
    projectId: cluster.project_id,
    analysisRunId: cluster.analysis_run_id,
    datasetVersionId: cluster.dataset_version_id,
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

function toCandidate(candidate: ApiCandidate): Candidate {
  return {
    id: candidate.id,
    projectId: candidate.project_id,
    datasetVersionId: candidate.dataset_version_id,
    analysisRunId: candidate.analysis_run_id,
    sourceClusterId: candidate.source_cluster_id,
    candidateType: candidate.candidate_type,
    autoStatus: candidate.auto_status,
    manualStatus: candidate.manual_status,
    effectiveStatus: candidate.effective_status,
    language: candidate.language,
    autoCategoryPath: candidate.auto_category_path,
    manualCategoryPath: candidate.manual_category_path,
    effectiveCategoryPath: candidate.effective_category_path,
    autoTitle: candidate.auto_title,
    manualTitle: candidate.manual_title,
    effectiveTitle: candidate.effective_title,
    autoCanonicalQuestion: candidate.auto_canonical_question,
    manualCanonicalQuestion: candidate.manual_canonical_question,
    effectiveCanonicalQuestion: candidate.effective_canonical_question,
    autoCanonicalAnswer: candidate.auto_canonical_answer,
    manualCanonicalAnswer: candidate.manual_canonical_answer,
    effectiveCanonicalAnswer: candidate.effective_canonical_answer,
    autoAlternativeQuestions: candidate.auto_alternative_questions,
    manualAlternativeQuestions: candidate.manual_alternative_questions,
    effectiveAlternativeQuestions: candidate.effective_alternative_questions,
    autoParameters: candidate.auto_parameters,
    manualParameters: candidate.manual_parameters,
    effectiveParameters: candidate.effective_parameters,
    autoExternalDataDependencies: candidate.auto_external_data_dependencies,
    manualExternalDataDependencies: candidate.manual_external_data_dependencies,
    effectiveExternalDataDependencies:
      candidate.effective_external_data_dependencies,
    qualityScore: candidate.quality_score,
    faqSuitabilityScore: candidate.faq_suitability_score,
    dynamicityScore: candidate.dynamicity_score,
    contradictionScore: candidate.contradiction_score,
    sourcePairCount: candidate.source_pair_count,
    sourceClusterIds: candidate.source_cluster_ids,
    notes: candidate.notes,
    metadata: candidate.metadata,
  };
}

function toCandidateSource(source: ApiCandidateSource): CandidateSource {
  return {
    candidateId: source.candidate_id,
    clusterId: source.cluster_id,
    messagePairId: source.message_pair_id,
    ticketId: source.ticket_id,
    messageGroupId: source.message_group_id,
    message: source.message,
    answer: source.answer,
    messageSegmentId: source.message_segment_id,
    sourceLanguage: source.source_language,
    normalizedCustomerMessage: source.normalized_customer_message,
    normalizedSupportAnswer: source.normalized_support_answer,
    assignmentType: source.assignment_type,
    membershipScore: source.membership_score,
    isMultiIntent: source.is_multi_intent,
    intentLabel: source.intent_label,
    datasetVersionId: source.dataset_version_id,
    analysisRunId: source.analysis_run_id,
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

function suggestedAnalysisProfileName(
  profiles: Pick<AnalysisProfile, "name">[],
): string {
  const highestSequence = profiles.reduce((highest, profile) => {
    const match = /^analysis-(\d+)$/.exec(profile.name);
    if (match === null) {
      return highest;
    }
    return Math.max(highest, Number.parseInt(match[1], 10));
  }, 0);
  return `analysis-${highestSequence + 1}`;
}

function formatJsonObject(value: Record<string, unknown> | null): string {
  if (value === null || Object.keys(value).length === 0) {
    return "-";
  }
  return JSON.stringify(value);
}

class ApiRequestError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
  }
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
    try {
      const payload = (await response.json()) as { detail?: unknown };
      detail = typeof payload.detail === "string" ? payload.detail : null;
    } catch {
      detail = null;
    }
    throw new ApiRequestError(
      detail ?? `Anfrage fehlgeschlagen (HTTP ${response.status}).`,
      response.status,
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
  const [analysisProfiles, setAnalysisProfiles] = useState<AnalysisProfile[]>(
    [],
  );
  const [projectProfileLoadState, setProjectProfileLoadState] =
    useState<ProjectProfileLoadState>({
      projectId: null,
      status: "idle",
    });
  const [analysisRuns, setAnalysisRuns] = useState<AnalysisRun[]>([]);
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [clusterSources, setClusterSources] = useState<ClusterSource[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [candidateSources, setCandidateSources] = useState<CandidateSource[]>(
    [],
  );
  const [exportLogs, setExportLogs] = useState<ExportLog[]>([]);
  const [lastExportCsv, setLastExportCsv] = useState("");
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [clusterLoadRunId, setClusterLoadRunId] = useState<string | null>(null);
  const [clusterGenerationRequest, setClusterGenerationRequest] =
    useState<ClusterGenerationRequest | null>(null);
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
  const [profileName, setProfileName] = useState("analysis-1");
  const [profileProvider, setProfileProvider] =
    useState<ConfigurableProvider>("vllm");
  const [profileModel, setProfileModel] = useState("");
  const [profileAlgorithm, setProfileAlgorithm] =
    useState<ProfileAlgorithm>("hdbscan");
  const [agglomerativeCriterion, setAgglomerativeCriterion] =
    useState<AgglomerativeCriterion>("n_clusters");
  const [runAnalysisProfileId, setRunAnalysisProfileId] = useState("");
  const [cloudUseConfirmed, setCloudUseConfirmed] = useState(false);
  const projectOpenGeneration = useRef(0);
  const clusterGenerationRequestRef = useRef<ClusterGenerationRequest | null>(
    null,
  );
  const signOutRef = useRef<() => void>(() => undefined);
  const authoritativeProjectContext = useRef<AuthoritativeProjectContext>({
    projectId: null,
    generation: 0,
    ready: false,
  });

  function showFeedback(kind: FeedbackKind, text: string) {
    setFeedback({ kind, text });
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

  async function fetchAnalysisProfiles(token: string, projectId: string) {
    const apiProfiles = await apiRequest<ApiAnalysisProfile[]>(
      `/api/projects/${projectId}/analysis-profiles`,
      { token },
    );
    return apiProfiles.map(toAnalysisProfile);
  }

  async function fetchAnalysisRuns(
    token: string,
    projectId: string,
    signal?: AbortSignal,
  ) {
    const apiRuns = await apiRequest<ApiAnalysisRun[]>(
      `/api/projects/${projectId}/analysis-runs`,
      { token, signal },
    );
    return apiRuns.map(toAnalysisRun);
  }

  async function loadClusters(token: string, projectId: string, runId: string) {
    try {
      const apiClusters = await apiRequest<ApiCluster[]>(
        `/api/projects/${projectId}/analysis-runs/${runId}/clusters`,
        { token },
      );
      setClusters(apiClusters.map(toCluster));
      setClusterSources([]);
      setClusterLoadRunId(runId);
      showFeedback(
        apiClusters.length > 0 ? "success" : "info",
        apiClusters.length > 0
          ? "Cluster geladen."
          : "Für diesen abgeschlossenen Run wurden noch keine Cluster erzeugt.",
      );
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(error, "Cluster konnten nicht geladen werden."),
      );
    }
  }

  async function fetchCandidates(token: string, projectId: string) {
    const apiCandidates = await apiRequest<ApiCandidate[]>(
      `/api/projects/${projectId}/candidates`,
      { token },
    );
    return apiCandidates.map(toCandidate);
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
      setAnalysisProfiles([]);
      setProjectProfileLoadState({ projectId: null, status: "idle" });
      setAnalysisRuns([]);
      setClusters([]);
      setClusterLoadRunId(null);
      setClusterSources([]);
      setCandidates([]);
      setCandidateSources([]);
      setExportLogs([]);
      setLastExportCsv("");
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
    setAnalysisProfiles([]);
    setProjectProfileLoadState({ projectId: null, status: "idle" });
    setAnalysisRuns([]);
    setClusters([]);
    setClusterLoadRunId(null);
    setClusterSources([]);
    setCandidates([]);
    setCandidateSources([]);
    setExportLogs([]);
    setLastExportCsv("");
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
    setAnalysisProfiles([]);
    setProjectProfileLoadState({ projectId: null, status: "idle" });
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
    setAnalysisProfiles([]);
    setAnalysisRuns([]);
    setClusters([]);
    setClusterLoadRunId(null);
    setClusterSources([]);
    setCandidates([]);
    setCandidateSources([]);
    setExportLogs([]);
    setLastExportCsv("");
    setProjectProfileLoadState({
      projectId,
      status: "loading",
    });
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
      setProjectProfileLoadState({
        projectId: project.id,
        status: "loading",
      });
      setCurrentProject(project);
      setProjectTab("import");
      rememberProjectAccess(project.id);
      setActivePage("projects");

      const [logs, profiles, nextCandidates, exports] =
        await Promise.allSettled([
          fetchImportLogs(session.token, projectId),
          fetchAnalysisProfiles(session.token, projectId),
          fetchCandidates(session.token, projectId),
          fetchExports(session.token, projectId),
        ]);
      if (projectOpenGeneration.current !== generation) {
        return;
      }
      setImportLogs(logs.status === "fulfilled" ? logs.value : []);
      setCandidates(
        nextCandidates.status === "fulfilled" ? nextCandidates.value : [],
      );
      setExportLogs(exports.status === "fulfilled" ? exports.value : []);
      if (profiles.status === "fulfilled") {
        authoritativeProjectContext.current = {
          projectId: project.id,
          generation,
          ready: true,
        };
        setAnalysisProfiles(profiles.value);
        setProjectProfileLoadState({
          projectId: project.id,
          status: "ready",
        });
      } else {
        authoritativeProjectContext.current = {
          projectId: project.id,
          generation,
          ready: false,
        };
        setAnalysisProfiles([]);
        setProjectProfileLoadState({
          projectId: project.id,
          status: "error",
        });
      }
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
        setAnalysisProfiles([]);
        setProjectProfileLoadState({ projectId: null, status: "idle" });
        setAnalysisRuns([]);
        setClusters([]);
        setClusterLoadRunId(null);
        setClusterSources([]);
        setCandidates([]);
        setCandidateSources([]);
        setExportLogs([]);
        setLastExportCsv("");
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
    } else if (provider === "ollama") {
      payload.manual_models =
        providers.find((item) => item.provider === "ollama")?.manualModels ??
        [];
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

  async function createAnalysisProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const context = authoritativeProjectContext.current;
    if (
      session === null ||
      currentProject === null ||
      !context.ready ||
      context.projectId !== currentProject.id ||
      projectProfileLoadState.projectId !== currentProject.id ||
      projectProfileLoadState.status !== "ready"
    ) {
      showFeedback(
        "info",
        "Analyseprofile werden noch geladen und können noch nicht gespeichert werden.",
      );
      return;
    }
    const formElement = event.currentTarget;
    const originProjectId = currentProject.id;
    const generation = context.generation;
    const form = new FormData(formElement);
    const similarity = Number.parseFloat(String(form.get("similarity") ?? ""));
    const thresholds = Number.isFinite(similarity) ? { similarity } : {};
    const algorithmSettings: Record<string, number | string> = {
      algorithm: profileAlgorithm,
    };
    if (profileAlgorithm === "hdbscan") {
      algorithmSettings.min_cluster_size = Number.parseInt(
        String(form.get("minClusterSize") ?? ""),
        10,
      );
      const minSamples = String(form.get("minSamples") ?? "").trim();
      if (minSamples) {
        algorithmSettings.min_samples = Number.parseInt(minSamples, 10);
      }
      algorithmSettings.cluster_selection_epsilon = Number.parseFloat(
        String(form.get("clusterSelectionEpsilon") ?? ""),
      );
    } else {
      if (agglomerativeCriterion === "n_clusters") {
        algorithmSettings.n_clusters = Number.parseInt(
          String(form.get("nClusters") ?? ""),
          10,
        );
      } else {
        algorithmSettings.distance_threshold = Number.parseFloat(
          String(form.get("distanceThreshold") ?? ""),
        );
      }
      algorithmSettings.linkage = String(form.get("linkage") ?? "ward");
    }
    try {
      const created = await apiRequest<ApiAnalysisProfile>(
        `/api/projects/${originProjectId}/analysis-profiles`,
        {
          method: "POST",
          token: session.token,
          body: JSON.stringify({
            name: profileName.trim(),
            provider: profileProvider,
            model: profileModel,
            thresholds,
            algorithm_settings: algorithmSettings,
          }),
        },
      );
      if (!isAuthoritativeProjectContext(originProjectId, generation)) {
        return;
      }
      const nextProfiles = [toAnalysisProfile(created), ...analysisProfiles];
      setAnalysisProfiles(nextProfiles);
      setProfileName(suggestedAnalysisProfileName(nextProfiles));
      formElement.reset();
      showFeedback("success", "Analyseprofil gespeichert.");
    } catch (error: unknown) {
      if (isAuthoritativeProjectContext(originProjectId, generation)) {
        showFeedback(
          "error",
          actionErrorMessage(
            error,
            "Analyseprofil konnte nicht gespeichert werden. Provider und Modell prüfen.",
          ),
        );
      }
    }
  }

  async function startAnalysisRun(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const context = authoritativeProjectContext.current;
    if (
      session === null ||
      currentProject === null ||
      !context.ready ||
      context.projectId !== currentProject.id ||
      projectProfileLoadState.projectId !== currentProject.id ||
      projectProfileLoadState.status !== "ready"
    ) {
      showFeedback(
        "info",
        "Analyseprofile werden noch geladen; ein Run kann noch nicht gestartet werden.",
      );
      return;
    }
    const originProjectId = currentProject.id;
    const generation = context.generation;
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const datasetVersionId = String(form.get("datasetVersionId") ?? "");
    const selectedProfile = authoritativeAnalysisProfiles.find(
      (profile) => profile.id === runAnalysisProfileId,
    );
    if (selectedProfile === undefined) {
      showFeedback(
        "warning",
        "Bitte ein Profil des aktuellen Projekts auswählen.",
      );
      return;
    }
    if (selectedProfile?.isCloudProvider && !cloudUseConfirmed) {
      showFeedback(
        "warning",
        "OpenAI Cloud-Nutzung muss vor dem Analysestart bestätigt werden.",
      );
      return;
    }
    try {
      const created = await apiRequest<ApiAnalysisRun>(
        `/api/projects/${originProjectId}/analysis-runs`,
        {
          method: "POST",
          token: session.token,
          body: JSON.stringify({
            dataset_version_id: datasetVersionId,
            analysis_profile_id: runAnalysisProfileId,
            parameters: {
              ...(selectedProfile?.isCloudProvider
                ? { cloud_use_confirmed: true }
                : {}),
            },
          }),
        },
      );
      if (!isAuthoritativeProjectContext(originProjectId, generation)) {
        return;
      }
      setAnalysisRuns((existing) => [toAnalysisRun(created), ...existing]);
      formElement.reset();
      setCloudUseConfirmed(false);
      showFeedback(
        "success",
        `Analyse gestartet: ${created.status}, Fortschritt ${created.progress}%.`,
      );
    } catch (error: unknown) {
      if (isAuthoritativeProjectContext(originProjectId, generation)) {
        showFeedback(
          "error",
          actionErrorMessage(
            error,
            "Analyse konnte nicht gestartet werden. Dataset-Version und Profil prüfen.",
          ),
        );
      }
    }
  }

  async function generateClusters(runId: string) {
    if (
      session === null ||
      currentProject === null ||
      clusterGenerationRequestRef.current !== null
    ) {
      return;
    }
    const request: ClusterGenerationRequest = {
      projectId: currentProject.id,
      runId,
      generation: projectOpenGeneration.current,
    };
    clusterGenerationRequestRef.current = request;
    setClusterGenerationRequest(request);
    showFeedback("info", `Clustererzeugung für Run ${runId} läuft.`);
    try {
      const apiClusters = await apiRequest<ApiCluster[]>(
        `/api/projects/${request.projectId}/analysis-runs/${runId}/clusters/generate`,
        { method: "POST", token: session.token },
      );
      if (projectOpenGeneration.current !== request.generation) {
        return;
      }
      setClusters(apiClusters.map(toCluster));
      setClusterSources([]);
      setClusterLoadRunId(runId);
      showFeedback("success", "Cluster erzeugt und geladen.");
    } catch (error: unknown) {
      if (projectOpenGeneration.current === request.generation) {
        showFeedback(
          "error",
          actionErrorMessage(
            error,
            "Cluster konnten nicht erzeugt werden. Run-Status prüfen.",
          ),
        );
      }
    } finally {
      if (clusterGenerationRequestRef.current === request) {
        clusterGenerationRequestRef.current = null;
        setClusterGenerationRequest((activeRequest) =>
          activeRequest === request ? null : activeRequest,
        );
      }
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

  async function inspectClusterSources(clusterId: string) {
    if (session === null || currentProject === null) {
      return;
    }
    try {
      const apiSources = await apiRequest<ApiClusterSource[]>(
        `/api/projects/${currentProject.id}/clusters/${clusterId}/sources`,
        { token: session.token },
      );
      setClusterSources(apiSources.map(toClusterSource));
      showFeedback("success", "Quellen geladen.");
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(
          error,
          "Clusterquellen konnten nicht geladen werden.",
        ),
      );
    }
  }

  async function createCandidateFromCluster(clusterId: string) {
    if (session === null || currentProject === null) {
      return;
    }
    try {
      const apiCandidate = await apiRequest<ApiCandidate>(
        `/api/projects/${currentProject.id}/clusters/${clusterId}/candidates`,
        { method: "POST", token: session.token },
      );
      const candidate = toCandidate(apiCandidate);
      setCandidates((existing) => [
        candidate,
        ...existing.filter((item) => item.id !== candidate.id),
      ]);
      setCandidateSources([]);
      showFeedback("success", "Candidate aus Cluster erstellt.");
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(
          error,
          "Candidate konnte nicht aus Cluster erstellt werden.",
        ),
      );
    }
  }

  async function updateCandidate(
    event: FormEvent<HTMLFormElement>,
    candidate: Candidate,
  ) {
    event.preventDefault();
    if (session === null || currentProject === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    const listFromField = (name: string) =>
      String(form.get(name) ?? "")
        .split("\n")
        .map((item) => item.trim())
        .filter(Boolean);
    const listOverrideFromField = (
      name: string,
      currentManualValue: string[] | null,
    ) => {
      const values = listFromField(name);
      return currentManualValue === null && values.length === 0 ? null : values;
    };
    const objectOverrideFromField = (
      name: string,
      currentManualValue: Record<string, unknown> | null,
    ) => {
      const rawValue = String(form.get(name) ?? "").trim();
      if (rawValue === "") {
        return currentManualValue === null ? null : {};
      }
      const parsed = JSON.parse(rawValue) as unknown;
      if (
        parsed === null ||
        Array.isArray(parsed) ||
        typeof parsed !== "object"
      ) {
        throw new Error("manual parameters must be a JSON object");
      }
      return parsed as Record<string, unknown>;
    };
    try {
      const updated = await apiRequest<ApiCandidate>(
        `/api/projects/${currentProject.id}/candidates/${candidate.id}`,
        {
          method: "PATCH",
          token: session.token,
          body: JSON.stringify({
            candidate_type:
              String(form.get("candidateType") ?? "").trim() || null,
            manual_status:
              String(form.get("manualStatus") ?? "").trim() || null,
            manual_category_path:
              String(form.get("manualCategoryPath") ?? "").trim() || null,
            manual_title: String(form.get("manualTitle") ?? "").trim() || null,
            manual_canonical_question:
              String(form.get("manualCanonicalQuestion") ?? "").trim() || null,
            manual_canonical_answer:
              String(form.get("manualCanonicalAnswer") ?? "").trim() || null,
            manual_alternative_questions: listOverrideFromField(
              "manualAlternativeQuestions",
              candidate.manualAlternativeQuestions,
            ),
            manual_parameters: objectOverrideFromField(
              "manualParameters",
              candidate.manualParameters,
            ),
            manual_external_data_dependencies: listOverrideFromField(
              "manualExternalDataDependencies",
              candidate.manualExternalDataDependencies,
            ),
            notes: String(form.get("notes") ?? "").trim() || null,
          }),
        },
      );
      setCandidates((existing) =>
        existing.map((candidate) =>
          candidate.id === updated.id ? toCandidate(updated) : candidate,
        ),
      );
      showFeedback("success", "Candidate-Curation gespeichert.");
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(
          error,
          "Candidate konnte nicht aktualisiert werden.",
        ),
      );
    }
  }

  async function inspectCandidateSources(candidateId: string) {
    if (session === null || currentProject === null) {
      return;
    }
    try {
      const apiSources = await apiRequest<ApiCandidateSource[]>(
        `/api/projects/${currentProject.id}/candidates/${candidateId}/sources`,
        { token: session.token },
      );
      setCandidateSources(apiSources.map(toCandidateSource));
      showFeedback("success", "Candidate-Quellen geladen.");
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(
          error,
          "Candidate-Quellen konnten nicht geladen werden.",
        ),
      );
    }
  }

  async function createExport(
    event: FormEvent<HTMLFormElement>,
    exportType: "candidates" | "source-assignments",
  ) {
    event.preventDefault();
    if (session === null || currentProject === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    const includeOriginalText = form.get("includeOriginalText") === "on";
    try {
      const result = await apiRequest<{
        export: ApiExportLog;
        csv_content: string;
        warning: string | null;
      }>(`/api/projects/${currentProject.id}/exports/${exportType}`, {
        method: "POST",
        token: session.token,
        body: JSON.stringify({
          include_original_text: includeOriginalText,
        }),
      });
      setExportLogs((existing) => [
        toExportLog(result.export),
        ...existing.filter((item) => item.id !== result.export.id),
      ]);
      setLastExportCsv(result.csv_content);
      showFeedback(
        result.warning === null ? "success" : "warning",
        result.warning ??
          `Export erstellt: ${result.export.output_filename} (${result.export.row_count} Zeilen).`,
      );
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(error, "Export konnte nicht erstellt werden."),
      );
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
    (log) => log.datasetVersionId !== null,
  );
  const profileProviderConfiguration = providers.find(
    (provider) => provider.provider === profileProvider,
  );
  const profileProviderModels =
    profileProviderConfiguration?.manualModels ?? [];
  const currentProjectProfilesAreReady =
    currentProject !== null &&
    projectProfileLoadState.projectId === currentProject.id &&
    projectProfileLoadState.status === "ready";
  const authoritativeAnalysisProfiles = currentProjectProfilesAreReady
    ? analysisProfiles
    : [];
  const selectedRunProfile = authoritativeAnalysisProfiles.find(
    (profile) => profile.id === runAnalysisProfileId,
  );

  function rememberProjectAccess(projectId: string) {
    setRecentProjectIds((existing) =>
      [projectId, ...existing.filter((id) => id !== projectId)].slice(0, 10),
    );
  }

  useEffect(() => {
    setProfileName(
      suggestedAnalysisProfileName(
        currentProjectProfilesAreReady ? analysisProfiles : [],
      ),
    );
  }, [currentProject?.id, currentProjectProfilesAreReady, analysisProfiles]);

  useEffect(() => {
    const availableModels =
      providers.find((provider) => provider.provider === profileProvider)
        ?.manualModels ?? [];
    setProfileModel((currentModel) =>
      availableModels.includes(currentModel)
        ? currentModel
        : (availableModels[0] ?? ""),
    );
  }, [profileProvider, providers]);

  useEffect(() => {
    setRunAnalysisProfileId((currentProfileId) =>
      currentProjectProfilesAreReady &&
      analysisProfiles.some((profile) => profile.id === currentProfileId)
        ? currentProfileId
        : currentProjectProfilesAreReady
          ? (analysisProfiles[0]?.id ?? "")
          : "",
    );
    setCloudUseConfirmed(false);
  }, [currentProject?.id, currentProjectProfilesAreReady, analysisProfiles]);

  useEffect(() => {
    if (
      session === null ||
      currentProject === null ||
      activePage !== "projects" ||
      (projectTab !== "runs" && projectTab !== "clusters")
    ) {
      return undefined;
    }

    const shouldPoll = projectTab === "runs";
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
        void refreshRuns();
      }, delay);
    }

    async function refreshRuns() {
      if (activeRequest !== null || !isCurrentPollingContext(true)) {
        return;
      }
      const request = { controller: new AbortController() };
      activeRequest = request;
      try {
        const runs = await fetchAnalysisRuns(
          token,
          projectId,
          request.controller.signal,
        );
        if (activeRequest === request && isCurrentPollingContext(true)) {
          setAnalysisRuns(runs);
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
        void refreshRuns();
      }
    }

    document.addEventListener("visibilitychange", handleVisibilityChange);
    if (document.visibilityState === "visible") {
      void refreshRuns();
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
                    ["profiles", "Profile"],
                    ["runs", "Runs"],
                    ["clusters", "Cluster"],
                    ["candidates", "Kandidaten"],
                    ["exports", "Export"],
                    ["delete", "Projekt löschen"],
                  ] as const
                ).map(([tab, label]) => (
                  <button
                    type="button"
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
                  className={settingsTab === "providers" ? "selected" : ""}
                  onClick={() => setSettingsTab("providers")}
                >
                  Embedding-Provider
                </button>
                <button
                  type="button"
                  className={settingsTab === "users" ? "selected" : ""}
                  onClick={() => setSettingsTab("users")}
                >
                  Nutzer
                </button>
              </div>
            </>
          )}

          {activePage === "settings" && settingsTab === "providers" && (
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
                    Modelle werden über den gespeicherten oder neu eingegebenen
                    API-Key abgerufen und danach für Analysen freigegeben.
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
                    <span className="field-caption">Freigegebene Modelle</span>
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
                      defaultValue={vllmProvider?.manualModels.join(", ") ?? ""}
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
                    <span className="field-caption">Installierte Modelle</span>
                    <p className="hint">
                      {ollamaProvider?.manualModels.length
                        ? ollamaProvider.manualModels.join(", ")
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
                      <input name="pullModel" placeholder="nomic-embed-text" />
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
              {currentProject && projectTab === "profiles" && (
                <section id="profiles" className="panel-grid profile-grid">
                  {!currentProjectProfilesAreReady ? (
                    <section
                      className="panel stack"
                      role="status"
                      aria-label="Analyseprofile werden geladen"
                    >
                      <p className="eyebrow">Profile</p>
                      <h2>
                        {projectProfileLoadState.status === "error"
                          ? "Profile nicht verfügbar"
                          : "Analyseprofile werden geladen"}
                      </h2>
                      <p className="hint">
                        {projectProfileLoadState.status === "error"
                          ? "Die Profile dieses Projekts konnten nicht geladen werden. Wechseln Sie erneut in das Projekt, bevor Sie ein Profil anlegen."
                          : "Das Profilformular wird freigegeben, sobald die projektlokalen Profile vollständig geladen sind."}
                      </p>
                    </section>
                  ) : (
                    <>
                      <form
                        className="panel stack"
                        onSubmit={createAnalysisProfile}
                        aria-label="Analyseprofil erstellen"
                      >
                        <p className="eyebrow">Profile</p>
                        <h2>Analyseprofil erstellen</h2>
                        <label>
                          Profilname
                          <input
                            name="profileName"
                            value={profileName}
                            onChange={(event) =>
                              setProfileName(event.target.value)
                            }
                            required
                          />
                        </label>
                        <label>
                          Provider
                          <select
                            name="provider"
                            value={profileProvider}
                            onChange={(event) =>
                              setProfileProvider(
                                event.target.value as ConfigurableProvider,
                              )
                            }
                          >
                            <option value="vllm">vLLM lokal</option>
                            <option value="ollama">Ollama lokal</option>
                            <option value="openai">OpenAI Cloud</option>
                          </select>
                        </label>
                        <label>
                          Modell
                          <select
                            name="model"
                            value={profileModel}
                            onChange={(event) =>
                              setProfileModel(event.target.value)
                            }
                            aria-describedby="profile-model-status"
                            disabled={profileProviderModels.length === 0}
                            required
                          >
                            {profileProviderModels.length === 0 && (
                              <option value="">Keine Modelle verfügbar</option>
                            )}
                            {profileProviderModels.map((model) => (
                              <option key={model} value={model}>
                                {model}
                              </option>
                            ))}
                          </select>
                        </label>
                        <p
                          id="profile-model-status"
                          className={
                            profileProviderModels.length === 0
                              ? "status warning"
                              : "hint"
                          }
                          role="status"
                        >
                          {profileProviderModels.length === 0
                            ? "Für diesen Provider ist noch kein Modell konfiguriert. Bitte zuerst die Provider-Einstellungen ergänzen."
                            : `${profileProviderModels.length} Modell(e) für ${profileProvider} verfügbar.`}
                        </p>
                        <label>
                          Similarity Threshold
                          <input
                            name="similarity"
                            type="number"
                            min="0"
                            max="1"
                            step="any"
                            placeholder="0.78"
                          />
                        </label>
                        <label>
                          Algorithmus
                          <select
                            name="algorithm"
                            value={profileAlgorithm}
                            onChange={(event) =>
                              setProfileAlgorithm(
                                event.target.value as ProfileAlgorithm,
                              )
                            }
                          >
                            <option value="hdbscan">HDBSCAN</option>
                            <option value="agglomerative">Agglomerative</option>
                          </select>
                        </label>
                        <fieldset className="parameter-group">
                          <legend>
                            {profileAlgorithm === "hdbscan"
                              ? "HDBSCAN-Parameter"
                              : "Agglomerative-Parameter"}
                          </legend>
                          {profileAlgorithm === "hdbscan" ? (
                            <div className="stack">
                              <label>
                                Minimale Clustergröße
                                <input
                                  name="minClusterSize"
                                  type="number"
                                  min="2"
                                  max="100000"
                                  defaultValue="5"
                                  required
                                />
                              </label>
                              <label>
                                Minimale Samples (optional)
                                <input
                                  name="minSamples"
                                  type="number"
                                  min="1"
                                  max="100000"
                                />
                              </label>
                              <label>
                                Cluster-Auswahl-Epsilon
                                <input
                                  name="clusterSelectionEpsilon"
                                  type="number"
                                  min="0"
                                  step="any"
                                  defaultValue="0"
                                  required
                                />
                              </label>
                            </div>
                          ) : (
                            <div className="stack">
                              <label>
                                Abbruchkriterium
                                <select
                                  name="agglomerativeCriterion"
                                  value={agglomerativeCriterion}
                                  onChange={(event) =>
                                    setAgglomerativeCriterion(
                                      event.target
                                        .value as AgglomerativeCriterion,
                                    )
                                  }
                                >
                                  <option value="n_clusters">
                                    Anzahl Cluster
                                  </option>
                                  <option value="distance_threshold">
                                    Distanzschwelle
                                  </option>
                                </select>
                              </label>
                              {agglomerativeCriterion === "n_clusters" ? (
                                <label>
                                  Anzahl Cluster
                                  <input
                                    name="nClusters"
                                    type="number"
                                    min="1"
                                    defaultValue="2"
                                    required
                                  />
                                </label>
                              ) : (
                                <label>
                                  Distanzschwelle
                                  <input
                                    name="distanceThreshold"
                                    type="number"
                                    min="0"
                                    step="any"
                                    required
                                  />
                                </label>
                              )}
                              <label>
                                Linkage
                                <select name="linkage" defaultValue="ward">
                                  <option value="ward">Ward</option>
                                  <option value="complete">Complete</option>
                                  <option value="average">Average</option>
                                  <option value="single">Single</option>
                                </select>
                              </label>
                            </div>
                          )}
                        </fieldset>
                        <button
                          type="submit"
                          disabled={
                            !profileName.trim() ||
                            !profileProviderModels.includes(profileModel)
                          }
                        >
                          Profil speichern
                        </button>
                      </form>

                      <section className="panel" aria-label="Analyseprofile">
                        <h2>Analyseprofile</h2>
                        <div className="user-list">
                          {analysisProfiles.length === 0 && (
                            <p className="hint">
                              Noch keine Analyseprofile für dieses Projekt.
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
                                  Cloud-Nutzung: OpenAI Profil sendet spätere
                                  Analyseinhalte an den konfigurierten
                                  Cloud-Provider.
                                </p>
                              )}
                              <p className="hint">
                                Thresholds: {JSON.stringify(profile.thresholds)}
                              </p>
                              <p className="hint">
                                Algorithmus:{" "}
                                {JSON.stringify(profile.algorithmSettings)}
                              </p>
                            </article>
                          ))}
                        </div>
                      </section>
                    </>
                  )}
                </section>
              )}

              {projectTab === "exports" && (
                <section id="exports" className="panel-grid">
                  <form
                    className="panel stack"
                    onSubmit={(event) => createExport(event, "candidates")}
                    aria-label="Candidate CSV exportieren"
                  >
                    <p className="eyebrow">Export</p>
                    <h2>Candidate CSV exportieren</h2>
                    <p className="hint">
                      Export nutzt die akzeptierten Candidate-Baseline-Spalten
                      und persistiert Metadaten in der Projektdatenbank.
                    </p>
                    <label className="inline-check">
                      <input name="includeOriginalText" type="checkbox" />
                      Originaltext bewusst einschliessen
                    </label>
                    <p className="status warning">
                      Warnung: Candidate-Felder können aus Supporttexten
                      abgeleitet sein. Der Export wird dann auch ohne aktivierte
                      Checkbox als Originaltext-Export protokolliert.
                    </p>
                    <button type="submit">Candidate CSV exportieren</button>
                  </form>

                  <form
                    className="panel stack"
                    onSubmit={(event) =>
                      createExport(event, "source-assignments")
                    }
                    aria-label="Source Assignment CSV exportieren"
                  >
                    <p className="eyebrow">Traceability</p>
                    <h2>Source-Assignment CSV exportieren</h2>
                    <p className="hint">
                      Ohne Toggle bleiben die Originalfelder customer_message
                      und support_answer leer; Traceability-IDs und
                      normalisierte Felder bleiben enthalten.
                    </p>
                    <label className="inline-check">
                      <input name="includeOriginalText" type="checkbox" />
                      Originaltext in customer_message/support_answer
                      einschliessen
                    </label>
                    <p className="status warning">
                      Warnung: Originaltexte sind potentiell identifizierende
                      Inhalte und sollten nur bewusst exportiert werden.
                    </p>
                    <button type="submit">
                      Source Assignment CSV exportieren
                    </button>
                  </form>

                  <section className="panel" aria-label="Exporthistorie">
                    <h2>Exporthistorie</h2>
                    <div className="user-list">
                      {exportLogs.length === 0 && (
                        <p className="hint">
                          Noch keine Exporte für dieses Projekt.
                        </p>
                      )}
                      {exportLogs.map((log) => (
                        <article className="user-card" key={log.id}>
                          <div className="user-heading">
                            <strong>{log.outputFilename}</strong>
                            <span>{log.exportType}</span>
                          </div>
                          <p className="hint">
                            Zeilen: {log.rowCount}; Originaltext:{" "}
                            {log.includeOriginalText ? "ja" : "nein"}
                          </p>
                          <p className="hint">
                            Dataset-Version: {log.datasetVersionId ?? "-"}; Run:{" "}
                            {log.analysisRunId ?? "-"}
                          </p>
                          <p className="hint">Erstellt: {log.createdAt}</p>
                          {log.includeOriginalText && (
                            <p className="status warning">
                              Dieser Export wurde mit Originaltext erstellt.
                            </p>
                          )}
                        </article>
                      ))}
                    </div>
                    {lastExportCsv && (
                      <pre
                        className="log-detail"
                        aria-label="Letzter CSV Export"
                      >
                        {lastExportCsv}
                      </pre>
                    )}
                  </section>
                </section>
              )}

              {projectTab === "runs" && (
                <section id="runs" className="panel-grid">
                  <form
                    className="panel stack"
                    onSubmit={startAnalysisRun}
                    aria-label="Analyse starten"
                  >
                    <p className="eyebrow">Run Monitor</p>
                    <h2>Analyse starten</h2>
                    <p className="hint">
                      Lokale Fixture-Workflows können ohne OpenAI abgeschlossen
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
                      <select
                        name="analysisProfileId"
                        value={runAnalysisProfileId}
                        disabled={!currentProjectProfilesAreReady}
                        onChange={(event) => {
                          setRunAnalysisProfileId(event.target.value);
                          setCloudUseConfirmed(false);
                        }}
                      >
                        {!currentProjectProfilesAreReady && (
                          <option value="">Profile werden geladen</option>
                        )}
                        {authoritativeAnalysisProfiles.map((profile) => (
                          <option key={profile.id} value={profile.id}>
                            {profile.name} ({profile.provider}/{profile.model})
                          </option>
                        ))}
                      </select>
                    </label>
                    {selectedRunProfile?.isCloudProvider && (
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
                        für diesen Run an OpenAI übertragen werden.
                      </label>
                    )}
                    <button
                      type="submit"
                      disabled={
                        runnableDatasetLogs.length === 0 ||
                        !currentProjectProfilesAreReady ||
                        authoritativeAnalysisProfiles.length === 0 ||
                        (selectedRunProfile?.isCloudProvider === true &&
                          !cloudUseConfirmed)
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
                          Noch keine Analyse-Runs für dieses Projekt.
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
              )}

              {projectTab === "clusters" && (
                <section id="clusters" className="panel-grid">
                  <section className="panel" aria-label="Cluster Aktionen">
                    <p className="eyebrow">Cluster Explorer</p>
                    <h2>Cluster erzeugen</h2>
                    <p className="hint">
                      Abgeschlossene Runs können mit dem im Analyseprofil
                      gewählten HDBSCAN- oder Agglomerative-Verfahren geclustert
                      werden.
                    </p>
                    <div className="user-list">
                      {analysisRuns.length === 0 && (
                        <p className="hint">
                          Noch keine Runs für Cluster vorhanden.
                        </p>
                      )}
                      {analysisRuns.map((run) => (
                        <article
                          className="user-card"
                          key={`cluster-action-${run.id}`}
                        >
                          <div className="user-heading">
                            <strong>{run.status}</strong>
                            <span>{run.model}</span>
                          </div>
                          <p className="hint">Run: {run.id}</p>
                          <button
                            type="button"
                            className="secondary"
                            disabled={
                              run.status !== "completed" ||
                              clusterGenerationRequest !== null
                            }
                            onClick={() => generateClusters(run.id)}
                          >
                            {clusterGenerationRequest?.projectId ===
                              currentProject?.id &&
                            clusterGenerationRequest?.runId === run.id
                              ? "Cluster werden erzeugt"
                              : "Cluster erzeugen"}
                          </button>
                          {clusterGenerationRequest?.projectId ===
                            currentProject?.id &&
                            clusterGenerationRequest?.runId === run.id && (
                              <p className="status info" role="status">
                                Clustererzeugung läuft für Run {run.id}.
                              </p>
                            )}
                          <button
                            type="button"
                            className="secondary"
                            disabled={run.status !== "completed"}
                            onClick={() =>
                              session &&
                              currentProject &&
                              loadClusters(
                                session.token,
                                currentProject.id,
                                run.id,
                              )
                            }
                          >
                            Cluster laden
                          </button>
                        </article>
                      ))}
                    </div>
                  </section>

                  <section className="panel" aria-label="Cluster Explorer">
                    <h2>Cluster Explorer</h2>
                    <div className="user-list">
                      {clusters.length === 0 && (
                        <p className="hint">
                          {clusterLoadRunId === null
                            ? "Noch keine Cluster geladen."
                            : "Für den ausgewählten abgeschlossenen Run wurden noch keine Cluster erzeugt. Bitte zuerst „Cluster erzeugen“ ausführen."}
                        </p>
                      )}
                      {clusters.map((cluster) => (
                        <article className="user-card" key={cluster.id}>
                          <div className="user-heading">
                            <strong>{cluster.effectiveTitle}</strong>
                            <span>
                              {cluster.isOutlier ? "Outlier" : "Cluster"}
                            </span>
                          </div>
                          <p className="hint">
                            Auto: {cluster.autoTitle} / {cluster.autoCategory} /{" "}
                            {cluster.autoStatus}
                          </p>
                          <p className="hint">
                            Manual: {cluster.manualTitle ?? "-"} /{" "}
                            {cluster.manualCategory ?? "-"} /{" "}
                            {cluster.manualStatus ?? "-"}
                          </p>
                          <p className="hint">
                            Effective: {cluster.effectiveTitle} /{" "}
                            {cluster.effectiveCategory ?? "-"} /{" "}
                            {cluster.effectiveStatus}
                          </p>
                          <p className="hint">
                            Score: {cluster.score}; Quellen:{" "}
                            {cluster.memberCount}; Algorithmus:{" "}
                            {cluster.algorithm}
                          </p>
                          <form
                            className="stack"
                            onSubmit={(event) =>
                              updateCluster(event, cluster.id)
                            }
                          >
                            <label>
                              Manueller Titel
                              <input
                                name="manualTitle"
                                defaultValue={cluster.manualTitle ?? ""}
                              />
                            </label>
                            <label>
                              Manuelle Kategorie
                              <input
                                name="manualCategory"
                                defaultValue={cluster.manualCategory ?? ""}
                              />
                            </label>
                            <label>
                              Manueller Status
                              <select
                                name="manualStatus"
                                defaultValue={cluster.manualStatus ?? ""}
                              >
                                <option value="">Kein Override</option>
                                <option value="unreviewed">unreviewed</option>
                                <option value="in_progress">in_progress</option>
                                <option value="reviewed">reviewed</option>
                                <option value="rejected">rejected</option>
                                <option value="outlier">outlier</option>
                              </select>
                            </label>
                            <button type="submit">Overrides speichern</button>
                          </form>
                          <button
                            type="button"
                            className="secondary"
                            onClick={() => inspectClusterSources(cluster.id)}
                          >
                            Quellen anzeigen
                          </button>
                          <button
                            type="button"
                            className="secondary"
                            onClick={() =>
                              createCandidateFromCluster(cluster.id)
                            }
                          >
                            Candidate erstellen
                          </button>
                        </article>
                      ))}
                    </div>
                    {clusterSources.length > 0 && (
                      <section
                        className="log-detail"
                        aria-label="Cluster Quellen"
                      >
                        <h2>Quellen</h2>
                        {clusterSources.map((source) => (
                          <article
                            className="user-card"
                            key={source.messagePairId}
                          >
                            <strong>
                              {source.ticketId} / {source.messageGroupId}
                            </strong>
                            <p className="hint">Message: {source.message}</p>
                            <p className="hint">Answer: {source.answer}</p>
                            <p className="hint">
                              Score: {source.membershipScore}; Assignment:{" "}
                              {source.assignmentType}
                            </p>
                          </article>
                        ))}
                      </section>
                    )}
                  </section>
                </section>
              )}

              {projectTab === "candidates" && (
                <section
                  id="candidates"
                  className="panel"
                  aria-label="Candidate Editor"
                >
                  <p className="eyebrow">Candidate Curation</p>
                  <h2>Candidate Editor</h2>
                  <p className="hint">
                    Generierte Werte bleiben erhalten; manuelle Felder bestimmen
                    die effektiven Kurationswerte.
                  </p>
                  <div className="user-list">
                    {candidates.length === 0 && (
                      <p className="hint">
                        Noch keine Candidates für dieses Projekt.
                      </p>
                    )}
                    {candidates.map((candidate) => (
                      <article className="user-card" key={candidate.id}>
                        <div className="user-heading">
                          <strong>{candidate.effectiveTitle}</strong>
                          <span>
                            {candidate.candidateType} /{" "}
                            {candidate.effectiveStatus}
                          </span>
                        </div>
                        <p className="hint">
                          Auto: {candidate.autoTitle} /{" "}
                          {candidate.autoCategoryPath ?? "-"} /{" "}
                          {candidate.autoStatus}
                        </p>
                        <p className="hint">
                          Manual: {candidate.manualTitle ?? "-"} /{" "}
                          {candidate.manualCategoryPath ?? "-"} /{" "}
                          {candidate.manualStatus ?? "-"}
                        </p>
                        <p className="hint">
                          Effective: {candidate.effectiveTitle} /{" "}
                          {candidate.effectiveCategoryPath ?? "-"} /{" "}
                          {candidate.effectiveStatus}
                        </p>
                        <p className="hint">
                          Frage Auto: {candidate.autoCanonicalQuestion}
                        </p>
                        <p className="hint">
                          Frage Manual:{" "}
                          {candidate.manualCanonicalQuestion ?? "-"}
                        </p>
                        <p className="hint">
                          Frage Effective:{" "}
                          {candidate.effectiveCanonicalQuestion}
                        </p>
                        <p className="hint">
                          Antwort Auto: {candidate.autoCanonicalAnswer}
                        </p>
                        <p className="hint">
                          Antwort Manual:{" "}
                          {candidate.manualCanonicalAnswer ?? "-"}
                        </p>
                        <p className="hint">
                          Antwort Effective:{" "}
                          {candidate.effectiveCanonicalAnswer}
                        </p>
                        <p className="hint">
                          Alternative Fragen Auto:{" "}
                          {candidate.autoAlternativeQuestions.join("; ") || "-"}
                        </p>
                        <p className="hint">
                          Alternative Fragen Manual:{" "}
                          {candidate.manualAlternativeQuestions?.join("; ") ??
                            "-"}
                        </p>
                        <p className="hint">
                          Alternative Fragen Effective:{" "}
                          {candidate.effectiveAlternativeQuestions.join("; ") ||
                            "-"}
                        </p>
                        <p className="hint">
                          Parameter Auto:{" "}
                          {formatJsonObject(candidate.autoParameters)}
                        </p>
                        <p className="hint">
                          Parameter Manual:{" "}
                          {formatJsonObject(candidate.manualParameters)}
                        </p>
                        <p className="hint">
                          Parameter Effective:{" "}
                          {formatJsonObject(candidate.effectiveParameters)}
                        </p>
                        <p className="hint">
                          Externe Datenabhängigkeiten Auto:{" "}
                          {candidate.autoExternalDataDependencies.join("; ") ||
                            "-"}
                        </p>
                        <p className="hint">
                          Externe Datenabhängigkeiten Manual:{" "}
                          {candidate.manualExternalDataDependencies?.join(
                            "; ",
                          ) ?? "-"}
                        </p>
                        <p className="hint">
                          Externe Datenabhängigkeiten Effective:{" "}
                          {candidate.effectiveExternalDataDependencies.join(
                            "; ",
                          ) || "-"}
                        </p>
                        <p className="hint">
                          Quellen: {candidate.sourcePairCount}; Cluster:{" "}
                          {candidate.sourceClusterIds.join(", ") || "-"};
                          Sprache: {candidate.language}
                        </p>
                        <p className="hint">
                          Scores: quality {candidate.qualityScore}, FAQ{" "}
                          {candidate.faqSuitabilityScore}, dynamic{" "}
                          {candidate.dynamicityScore}, contradiction{" "}
                          {candidate.contradictionScore}
                        </p>
                        <form
                          className="stack"
                          onSubmit={(event) =>
                            updateCandidate(event, candidate)
                          }
                        >
                          <label>
                            Candidate Typ
                            <select
                              name="candidateType"
                              defaultValue={candidate.candidateType}
                            >
                              <option value="static_faq">static_faq</option>
                              <option value="parameterized_faq">
                                parameterized_faq
                              </option>
                              <option value="dynamic_case">dynamic_case</option>
                              <option value="text_block">text_block</option>
                              <option value="single_case">single_case</option>
                              <option value="not_usable">not_usable</option>
                            </select>
                          </label>
                          <label>
                            Manueller Status
                            <select
                              name="manualStatus"
                              defaultValue={candidate.manualStatus ?? ""}
                            >
                              <option value="">Kein Override</option>
                              <option value="unreviewed">unreviewed</option>
                              <option value="in_progress">in_progress</option>
                              <option value="reviewed">reviewed</option>
                              <option value="rejected">rejected</option>
                              <option value="export_ready">export_ready</option>
                            </select>
                          </label>
                          <label>
                            Manuelle Kategorie
                            <input
                              name="manualCategoryPath"
                              defaultValue={candidate.manualCategoryPath ?? ""}
                            />
                          </label>
                          <label>
                            Manueller Titel
                            <input
                              name="manualTitle"
                              defaultValue={candidate.manualTitle ?? ""}
                            />
                          </label>
                          <label>
                            Manuelle Frage
                            <textarea
                              name="manualCanonicalQuestion"
                              defaultValue={
                                candidate.manualCanonicalQuestion ?? ""
                              }
                            />
                          </label>
                          <label>
                            Manuelle Antwort
                            <textarea
                              name="manualCanonicalAnswer"
                              defaultValue={
                                candidate.manualCanonicalAnswer ?? ""
                              }
                            />
                          </label>
                          <label>
                            Alternative Fragen, eine pro Zeile
                            <textarea
                              name="manualAlternativeQuestions"
                              defaultValue={
                                candidate.manualAlternativeQuestions?.join(
                                  "\n",
                                ) ?? ""
                              }
                            />
                          </label>
                          <label>
                            Parameter JSON
                            <textarea
                              name="manualParameters"
                              defaultValue={
                                candidate.manualParameters === null
                                  ? ""
                                  : JSON.stringify(candidate.manualParameters)
                              }
                            />
                          </label>
                          <label>
                            Externe Datenabhängigkeiten, eine pro Zeile
                            <textarea
                              name="manualExternalDataDependencies"
                              defaultValue={
                                candidate.manualExternalDataDependencies?.join(
                                  "\n",
                                ) ?? ""
                              }
                            />
                          </label>
                          <label>
                            Notizen
                            <textarea
                              name="notes"
                              defaultValue={candidate.notes ?? ""}
                            />
                          </label>
                          <button type="submit">Candidate speichern</button>
                        </form>
                        <button
                          type="button"
                          className="secondary"
                          onClick={() => inspectCandidateSources(candidate.id)}
                        >
                          Candidate Quellen anzeigen
                        </button>
                      </article>
                    ))}
                  </div>
                  {candidateSources.length > 0 && (
                    <section
                      className="log-detail"
                      aria-label="Candidate Quellen"
                    >
                      <h2>Candidate Quellen</h2>
                      {candidateSources.map((source) => (
                        <article
                          className="user-card"
                          key={source.messagePairId}
                        >
                          <strong>
                            {source.ticketId} / {source.messageGroupId}
                          </strong>
                          <p className="hint">Message: {source.message}</p>
                          <p className="hint">Answer: {source.answer}</p>
                          <p className="hint">
                            Assignment: {source.assignmentType}; Score:{" "}
                            {source.membershipScore}; Cluster:{" "}
                            {source.clusterId ?? "-"}
                          </p>
                        </article>
                      ))}
                    </section>
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
