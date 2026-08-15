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
  ticket_url_template: string | null;
};

type Project = {
  id: string;
  name: string;
  lifecycleState: string;
  updatedAt: string;
  ticketUrlTemplate: string | null;
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
  skipped_detail_count?: number;
  dataset_version_id: string | null;
  dataset_display_name: string | null;
  dataset_deleted_at: string | null;
  started_at: string;
  completed_at: string;
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
  skippedDetailCount: number;
  datasetVersionId: string | null;
  datasetDisplayName: string | null;
  datasetDeletedAt: string | null;
  startedAt: string;
  completedAt: string;
};

const MAX_IMPORT_BYTES = 512 * 1024 * 1024;

type ApiProviderConfiguration = {
  id: string;
  provider: string;
  display_name: string;
  endpoint_url: string | null;
  available_models: string[];
  manual_models: string[];
  llm_models?: string[];
  api_key_set: boolean;
  updated_at: string;
};

type ApiProviderCheck = {
  id: string;
  provider: string;
  ok: boolean;
  models: string[];
  embedding_models: string[];
  llm_models: string[];
  message: string;
};

type ProviderConfiguration = {
  id: string;
  provider: string;
  displayName: string;
  endpointUrl: string | null;
  availableModels: string[];
  manualModels: string[];
  llmModels: string[];
  apiKeySet: boolean;
  updatedAt: string;
};

type ConfigurableProvider = "openai" | "ollama";
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
  provider_configuration_id: string | null;
  provider_display_name: string | null;
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
  providerConfigurationId: string | null;
  providerDisplayName: string | null;
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
  llm_provider_configuration_id: string | null;
  llm_provider_display_name: string | null;
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
  active_cluster_count?: number;
  active_message_pair_count?: number;
};

type ApiClusterSetBatchDeleteResponse = {
  deleted_cluster_set_ids: string[];
  cluster_sets: ApiClusterSet[];
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
  llmProviderConfigurationId: string | null;
  llmProviderDisplayName: string | null;
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
  activeClusterCount: number;
  activeMessagePairCount: number;
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
  created_at: string;
  updated_at: string;
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
  createdAt: string;
  updatedAt: string;
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
type SettingsTab = "providers" | "users";
type ProjectTab =
  "import" | "indexing" | "cluster-sets" | "explorer" | "settings";
type ExplorerExportFormat = "csv" | "json";
type ClusterSortKey =
  | "status"
  | "title"
  | "category"
  | "customerQuestions"
  | "supportAnswers"
  | "hintsScore";
type SortDirection = "asc" | "desc";
type ClusterSortState = {
  key: ClusterSortKey;
  direction: SortDirection;
} | null;
type ClusterSetRefinementSource = {
  id: string;
  title: string;
  label: string;
  isOutlier: boolean;
};
type ClusterSetRefinementDraft = {
  parentClusterSetId: string;
  parentClusterSetName: string;
  indexingRunId: string;
  sourceClusterIds: string[];
  sources: ClusterSetRefinementSource[];
  description: string;
};
type ClusterOrigin = {
  sourceParentClusterId: string;
  sourceParentClusterTitle: string;
  sourceParentClusterLabel: number | null;
  sourceParentClusterIsOutlier: boolean;
  batchGroupIndex: number;
  localClusterLabel: number;
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
  VALIDATION_FAILED:
    "Die Eingaben sind ungültig. Bitte prüfen und erneut versuchen.",
  PROJECT_NOT_FOUND:
    "Das Projekt wurde nicht gefunden. Bitte Projektliste neu laden.",
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
    "Die aktuelle Datenmenge, Dimension oder Zusammenfassung überschreitet das Clusterbudget. Bitte Datenmenge, Dimensionen oder Beispiele reduzieren.",
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
  CLUSTER_ALGORITHM_PARAMETERS_INVALID:
    "Die Cluster-Parameter passen nicht zum gewählten Algorithmus oder Verfeinerungsmodus.",
  CLUSTER_BATCH_REFINEMENT_EMPTY_GROUP:
    "Mindestens ein ausgewählter Parent-Cluster enthält keine nutzbaren Quellen.",
  CLUSTER_BATCH_REFINEMENT_GROUP_INVALID:
    "Eine Parent-Gruppe ist für die gewählten Cluster-Parameter zu klein oder ungültig.",
  CLUSTER_SEARCH_NO_RESULTS:
    "Keine Cluster entsprechen der aktuellen Textsuche oder dem Filter.",
  CLUSTER_OUTLIER_EMPTY_RESULT:
    "Die Ausreißer-Einstellung würde keine Zeilen übrig lassen. Bitte Schwellwert anpassen.",
  PROVIDER_MODEL_PULL_IN_PROGRESS:
    "Ein Ollama-Modell wird bereits geladen. Bitte Abschluss abwarten.",
  PROVIDER_DELETE_FAILED:
    "Provider konnte nicht entfernt werden. Bitte aktuellen Stand neu laden und erneut versuchen.",
  PROVIDER_DELETE_BLOCKED:
    "Provider wird noch von einer aktiven Berechnung verwendet. Bitte Abschluss abwarten oder den Job abbrechen.",
  CLUSTER_OUTLIER_RECALCULATION_FAILED:
    "Die Ausreißer-Neuberechnung konnte nicht abgeschlossen werden.",
  CLUSTER_REDUCTION_UNAVAILABLE:
    "Die gewählte Dimensionsreduzierung ist lokal nicht verfügbar. Bitte Parameter anpassen.",
  CLUSTER_ACCELERATOR_UNAVAILABLE:
    "cuML/RAPIDS ist in dieser lokalen Laufzeit nicht verfügbar. Bitte CPU-Backend wählen.",
  CLUSTER_SET_LINEAGE_UNAVAILABLE:
    "Die Analyse-Historie ist unvollständig. Bitte Liste neu laden.",
  CLUSTER_SET_DUPLICATE_UNAVAILABLE:
    "Das ausgewählte Cluster-Set ist nicht mehr für eine Duplikation verfügbar.",
  CLUSTER_SET_BATCH_DELETE_FAILED:
    "Die ausgewählten Cluster-Sets konnten nicht vollständig gelöscht werden.",
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
    ticketUrlTemplate: project.ticket_url_template ?? null,
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
    skippedDetailCount: log.skipped_detail_count ?? 0,
    datasetVersionId: log.dataset_version_id,
    datasetDisplayName: log.dataset_display_name,
    datasetDeletedAt: log.dataset_deleted_at,
    startedAt: log.started_at,
    completedAt: log.completed_at,
  };
}

function toProviderConfiguration(
  configuration: ApiProviderConfiguration,
): ProviderConfiguration {
  const manualModels =
    configuration.provider === "openai"
      ? configuration.manual_models.filter(isOpenAiEmbeddingModel)
      : configuration.manual_models;
  const llmModels =
    configuration.provider === "openai"
      ? (configuration.llm_models ?? []).filter(isOpenAiLlmModel)
      : (configuration.llm_models ?? []);
  const availableModels =
    (configuration.available_models ?? []).length > 0
      ? configuration.available_models
      : Array.from(new Set([...manualModels, ...llmModels]));
  return {
    id: configuration.id,
    provider: configuration.provider,
    displayName: configuration.display_name,
    endpointUrl: configuration.endpoint_url,
    availableModels,
    manualModels,
    llmModels,
    apiKeySet: configuration.api_key_set,
    updatedAt: configuration.updated_at,
  };
}

function uniqueModels(models: string[]): string[] {
  return Array.from(new Set(models));
}

function isOpenAiEmbeddingModel(model: string): boolean {
  return model.toLowerCase().startsWith("text-embedding-");
}

function isOpenAiLlmModel(model: string): boolean {
  const normalized = model.toLowerCase();
  if (normalized === "o4-mini") {
    return true;
  }
  if (normalized.startsWith("gpt-4.1") || normalized.startsWith("gpt-4o")) {
    return true;
  }
  const major = normalized.match(/^gpt-(\d+)(?:[.-].*)?$/);
  return major !== null && Number.parseInt(major[1], 10) >= 5;
}

function embeddingModelOptions(provider: ProviderConfiguration): string[] {
  if (provider.provider === "openai") {
    return provider.availableModels.filter(isOpenAiEmbeddingModel);
  }
  return provider.availableModels;
}

function llmModelOptions(provider: ProviderConfiguration): string[] {
  if (provider.provider === "openai") {
    return provider.availableModels.filter(isOpenAiLlmModel);
  }
  return provider.availableModels;
}

function reconcileDiscoveredProviderModels(
  provider: ProviderConfiguration,
  models: string[],
  result: ApiProviderCheck,
): ProviderConfiguration {
  const availableModels = uniqueModels(models);
  const nextProvider = {
    ...provider,
    availableModels,
  };
  const discoveredEmbeddingModels = result.embedding_models ?? [];
  const discoveredLlmModels = result.llm_models ?? [];
  const embeddingOptions =
    discoveredEmbeddingModels.length > 0
      ? discoveredEmbeddingModels
      : embeddingModelOptions(nextProvider);
  const llmOptions =
    discoveredLlmModels.length > 0
      ? discoveredLlmModels
      : llmModelOptions(nextProvider);
  const embeddingSet = new Set(embeddingOptions);
  const llmSet = new Set(llmOptions);
  return {
    ...nextProvider,
    manualModels: provider.manualModels.filter((model) =>
      embeddingSet.has(model),
    ),
    llmModels: provider.llmModels.filter((model) => llmSet.has(model)),
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
    providerConfigurationId: run.provider_configuration_id,
    providerDisplayName: run.provider_display_name,
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
    llmProviderConfigurationId: clusterSet.llm_provider_configuration_id,
    llmProviderDisplayName: clusterSet.llm_provider_display_name,
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
    activeClusterCount:
      clusterSet.active_cluster_count ?? clusterSet.cluster_count,
    activeMessagePairCount: clusterSet.active_message_pair_count ?? 0,
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
    createdAt: cluster.created_at,
    updatedAt: cluster.updated_at,
    autoSummaryQuestion: cluster.auto_summary_question ?? null,
    autoSummaryAnswer: cluster.auto_summary_answer ?? null,
  };
}

function sortClusterSetsByRecency(clusterSets: ClusterSet[]): ClusterSet[] {
  return clusterSets.slice().sort((left, right) => {
    const updatedComparison = right.updatedAt.localeCompare(left.updatedAt);
    if (updatedComparison !== 0) {
      return updatedComparison;
    }
    return right.createdAt.localeCompare(left.createdAt);
  });
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

function buildTicketUrl(
  ticketUrlTemplate: string | null,
  ticketId: string,
): string | null {
  if (ticketUrlTemplate === null || ticketUrlTemplate.trim() === "") {
    return null;
  }
  if (!ticketUrlTemplate.includes("<ticket_id>")) {
    return null;
  }
  try {
    const href = ticketUrlTemplate.replaceAll(
      "<ticket_id>",
      encodeURIComponent(ticketId),
    );
    const parsed = new URL(href);
    if (
      !["http:", "https:"].includes(parsed.protocol) ||
      parsed.username !== "" ||
      parsed.password !== ""
    ) {
      return null;
    }
    return parsed.toString();
  } catch {
    return null;
  }
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

function parsePositiveInteger(value: FormDataEntryValue | null): number | null {
  const cleaned = String(value ?? "").trim();
  if (!/^[1-9]\d*$/.test(cleaned)) {
    return null;
  }
  const parsed = Number(cleaned);
  return Number.isSafeInteger(parsed) ? parsed : null;
}

const CLUSTER_SET_PARAMETER_LABELS: Record<string, string> = {
  vector_basis: "Vektorbasis",
  message_weight: "Nachrichten-Gewicht",
  answer_weight: "Antwort-Gewicht",
  algorithm: "Algorithmus",
  min_cluster_size: "min_cluster_size",
  min_samples: "min_samples",
  cluster_selection_epsilon: "selection_epsilon",
  reduction_method: "Reduktion",
  reduction_dimensions: "Ziel-Dimensionen",
  execution_backend: "Backend",
  umap_n_neighbors: "UMAP n_neighbors",
  umap_min_dist: "UMAP min_dist",
  outlier_threshold: "Outlier-Schwelle",
  n_clusters: "n_clusters",
  linkage: "Linkage",
  distance_threshold: "distance_threshold",
  llm_provider: "LLM-Provider",
  llm_model: "LLM-Modell",
  llm_sample_strategy: "LLM-Strategie",
  llm_sample_requested: "LLM-Samples",
  llm_sample_seed: "LLM-Seed",
};

const CLUSTER_SET_PARAMETER_ORDER = [
  "vector_basis",
  "message_weight",
  "answer_weight",
  "algorithm",
  "min_cluster_size",
  "min_samples",
  "cluster_selection_epsilon",
  "reduction_method",
  "reduction_dimensions",
  "execution_backend",
  "umap_n_neighbors",
  "umap_min_dist",
  "outlier_threshold",
  "n_clusters",
  "linkage",
  "distance_threshold",
  "llm_provider",
  "llm_model",
  "llm_sample_strategy",
  "llm_sample_requested",
  "llm_sample_seed",
];

type ClusterSetParameterEntry = {
  key: string;
  label: string;
  value: string;
};

type ClusterStatusSummaryEntry = {
  status: string;
  label: string;
  clusterCount: number;
  messagePairCount: number;
};

type ExplorerClusterSetSummary = {
  totalClusters: number;
  totalMessagePairCount: number;
  activeClusters: number;
  activeMessagePairCount: number;
  rejectedClusters: number;
  rejectedMessagePairCount: number;
  statusEntries: ClusterStatusSummaryEntry[];
};

const CLUSTER_STATUS_ORDER = [
  "unreviewed",
  "in_progress",
  "reviewed",
  "rejected",
  "outlier",
];

const CLUSTER_STATUS_LABELS: Record<string, string> = {
  unreviewed: "unreviewed",
  in_progress: "in_progress",
  reviewed: "reviewed",
  rejected: "rejected",
  outlier: "outlier",
};

function formatClusterSetParameterValue(key: string, value: unknown): string {
  if (value === null || value === undefined) {
    if (key === "min_samples") {
      return "auto";
    }
    if (key === "outlier_threshold") {
      return "aus";
    }
    if (
      key === "reduction_dimensions" ||
      key === "umap_n_neighbors" ||
      key === "umap_min_dist" ||
      key === "distance_threshold"
    ) {
      return "nicht aktiv";
    }
    return "-";
  }
  if (typeof value === "number") {
    return Number.isInteger(value)
      ? String(value)
      : String(Number(value.toFixed(4)));
  }
  if (typeof value === "boolean") {
    return value ? "ja" : "nein";
  }
  if (typeof value === "string") {
    if (key === "llm_sample_requested" && value === "all") {
      return "alle Beispiele";
    }
    return value.trim() || "-";
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function clusterSetParameterEntries(
  clusterSet: ClusterSet,
): ClusterSetParameterEntry[] {
  const values: Record<string, unknown> = {
    vector_basis: clusterSet.vectorBasis,
    message_weight: clusterSet.messageWeight,
    answer_weight: clusterSet.answerWeight,
    algorithm: clusterSet.algorithm,
    ...clusterSet.parameters,
  };
  if (clusterSet.llmProvider !== null) {
    values.llm_provider =
      clusterSet.llmProviderDisplayName ?? clusterSet.llmProvider;
    values.llm_model = clusterSet.llmModel ?? "-";
    values.llm_sample_strategy =
      clusterSet.llmSampleStrategy.strategy ?? "random";
    values.llm_sample_requested = clusterSet.llmSampleStrategy.requested ?? "-";
    values.llm_sample_seed = clusterSet.llmSampleStrategy.seed ?? "-";
  }
  const keys = [
    ...CLUSTER_SET_PARAMETER_ORDER,
    ...Object.keys(values)
      .filter((key) => !CLUSTER_SET_PARAMETER_ORDER.includes(key))
      .sort((left, right) => left.localeCompare(right)),
  ];
  const seen = new Set<string>();
  return keys
    .filter((key) => {
      if (seen.has(key) || !(key in values)) {
        return false;
      }
      seen.add(key);
      return true;
    })
    .map((key) => ({
      key,
      label: CLUSTER_SET_PARAMETER_LABELS[key] ?? key,
      value: formatClusterSetParameterValue(key, values[key]),
    }));
}

function formatClusterStatusLabel(status: string): string {
  return CLUSTER_STATUS_LABELS[status] ?? status;
}

function formatClusterAndPairCount(
  clusterCount: number,
  messagePairCount: number,
): string {
  const clusterLabel = clusterCount === 1 ? "Cluster" : "Cluster";
  const pairLabel =
    messagePairCount === 1 ? "Nachrichtenpaar" : "Nachrichtenpaare";
  return `${clusterCount} ${clusterLabel} / ${messagePairCount} ${pairLabel}`;
}

function summarizeExplorerClusters(
  clusters: Cluster[],
): ExplorerClusterSetSummary {
  const byStatus = new Map<
    string,
    { clusterCount: number; messagePairCount: number }
  >();
  let totalMessagePairCount = 0;
  let activeClusters = 0;
  let activeMessagePairCount = 0;
  let rejectedClusters = 0;
  let rejectedMessagePairCount = 0;

  for (const cluster of clusters) {
    const status = cluster.effectiveStatus;
    const messagePairCount = cluster.memberCount;
    totalMessagePairCount += messagePairCount;
    const existing = byStatus.get(status) ?? {
      clusterCount: 0,
      messagePairCount: 0,
    };
    existing.clusterCount += 1;
    existing.messagePairCount += messagePairCount;
    byStatus.set(status, existing);
    if (status === "rejected") {
      rejectedClusters += 1;
      rejectedMessagePairCount += messagePairCount;
    } else {
      activeClusters += 1;
      activeMessagePairCount += messagePairCount;
    }
  }

  const statusEntries = Array.from(byStatus.entries())
    .sort(([left], [right]) => {
      const leftIndex = CLUSTER_STATUS_ORDER.indexOf(left);
      const rightIndex = CLUSTER_STATUS_ORDER.indexOf(right);
      if (leftIndex !== -1 || rightIndex !== -1) {
        return (
          (leftIndex === -1 ? Number.MAX_SAFE_INTEGER : leftIndex) -
          (rightIndex === -1 ? Number.MAX_SAFE_INTEGER : rightIndex)
        );
      }
      return left.localeCompare(right, "de");
    })
    .map(([status, counts]) => ({
      status,
      label: formatClusterStatusLabel(status),
      clusterCount: counts.clusterCount,
      messagePairCount: counts.messagePairCount,
    }));

  return {
    totalClusters: clusters.length,
    totalMessagePairCount,
    activeClusters,
    activeMessagePairCount,
    rejectedClusters,
    rejectedMessagePairCount,
    statusEntries,
  };
}

function metadataObject(value: unknown): Record<string, unknown> | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function clusterOrigin(cluster: Cluster): ClusterOrigin | null {
  const refinement = metadataObject(cluster.metadata.refinement);
  if (refinement === null || refinement.mode !== "per_parent") {
    return null;
  }
  const sourceParentClusterId = refinement.source_parent_cluster_id;
  const sourceParentClusterTitle = refinement.source_parent_cluster_title;
  const batchGroupIndex = refinement.batch_group_index;
  const localClusterLabel = refinement.local_cluster_label;
  if (
    typeof sourceParentClusterId !== "string" ||
    typeof sourceParentClusterTitle !== "string" ||
    typeof batchGroupIndex !== "number" ||
    !Number.isSafeInteger(batchGroupIndex) ||
    typeof localClusterLabel !== "number" ||
    !Number.isSafeInteger(localClusterLabel)
  ) {
    return null;
  }
  const sourceParentClusterLabel = refinement.source_parent_cluster_label;
  const sourceParentClusterIsOutlier =
    refinement.source_parent_cluster_is_outlier;
  return {
    sourceParentClusterId,
    sourceParentClusterTitle,
    sourceParentClusterLabel:
      typeof sourceParentClusterLabel === "number" &&
      Number.isSafeInteger(sourceParentClusterLabel)
        ? sourceParentClusterLabel
        : null,
    sourceParentClusterIsOutlier:
      typeof sourceParentClusterIsOutlier === "boolean"
        ? sourceParentClusterIsOutlier
        : false,
    batchGroupIndex,
    localClusterLabel,
  };
}

function clusterOriginGroupLabel(origin: ClusterOrigin | null): string {
  if (origin === null) {
    return "Parent: nicht gespeichert";
  }
  const label =
    origin.sourceParentClusterLabel === null
      ? ""
      : ` · Label ${origin.sourceParentClusterLabel}`;
  const outlier = origin.sourceParentClusterIsOutlier ? " · Ausreißer" : "";
  return `Parent: ${origin.sourceParentClusterTitle}${label}${outlier}`;
}

class ApiRequestError extends Error {
  readonly status: number;
  readonly code: string | null;
  readonly fieldErrors: Record<string, string>;

  constructor(
    message: string,
    status: number,
    code: string | null = null,
    fieldErrors: Record<string, string> = {},
  ) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = code;
    this.fieldErrors = fieldErrors;
  }
}

function normalizeApiError(payload: {
  title?: unknown;
  detail?: unknown;
  code?: unknown;
  fieldErrors?: unknown;
}): {
  message: string | null;
  code: string | null;
  fieldErrors: Record<string, string>;
} {
  const code = typeof payload.code === "string" ? payload.code : null;
  const fieldErrors: Record<string, string> = {};
  if (Array.isArray(payload.fieldErrors)) {
    for (const item of payload.fieldErrors) {
      if (
        typeof item === "object" &&
        item !== null &&
        "field" in item &&
        "message" in item &&
        typeof item.field === "string" &&
        typeof item.message === "string"
      ) {
        fieldErrors[item.field] = item.message;
      }
    }
  }
  if (code !== null && ERROR_MESSAGES_BY_CODE[code] !== undefined) {
    return { message: ERROR_MESSAGES_BY_CODE[code], code, fieldErrors };
  }
  if (code !== null) {
    return {
      message: ERROR_MESSAGES_BY_CODE.UNEXPECTED_ERROR,
      code,
      fieldErrors,
    };
  }
  if (typeof payload.detail === "string" && payload.detail.trim() !== "") {
    return { message: payload.detail, code, fieldErrors };
  }
  if (typeof payload.title === "string" && payload.title.trim() !== "") {
    return { message: payload.title, code, fieldErrors };
  }
  return { message: null, code, fieldErrors };
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
    let fieldErrors: Record<string, string> = {};
    try {
      const payload = (await response.json()) as {
        title?: unknown;
        detail?: unknown;
        code?: unknown;
        fieldErrors?: unknown;
      };
      const normalized = normalizeApiError(payload);
      detail = normalized.message;
      code = normalized.code;
      fieldErrors = normalized.fieldErrors;
    } catch {
      detail = null;
    }
    throw new ApiRequestError(
      detail ?? `Anfrage fehlgeschlagen (HTTP ${response.status}).`,
      response.status,
      code,
      fieldErrors ?? {},
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
  const [clusterSort, setClusterSort] = useState<ClusterSortState>(null);
  const [showExcludedClusters, setShowExcludedClusters] = useState(false);
  const [includeOutlierRows, setIncludeOutlierRows] = useState(true);
  const [outlierThreshold, setOutlierThreshold] = useState("0.5");
  const [explorerExportFormat, setExplorerExportFormat] =
    useState<ExplorerExportFormat>("csv");
  const [explorerExportError, setExplorerExportError] = useState<string | null>(
    null,
  );
  const [explorerRailCollapsed, setExplorerRailCollapsed] = useState(false);
  const [clusterSetRefinementDraft, setClusterSetRefinementDraft] =
    useState<ClusterSetRefinementDraft | null>(null);
  const [clusterSetGenerationRequest, setClusterSetGenerationRequest] =
    useState<ClusterSetGenerationRequest | null>(null);
  const [selectedClusterSetIds, setSelectedClusterSetIds] = useState<string[]>(
    [],
  );
  const [collapsedClusterSetMetadataIds, setCollapsedClusterSetMetadataIds] =
    useState<string[]>([]);
  const [clusterSetBatchDeleteInProgress, setClusterSetBatchDeleteInProgress] =
    useState(false);
  const [clusterSetDuplicateRequestId, setClusterSetDuplicateRequestId] =
    useState<string | null>(null);
  const [clusterSetDuplicateErrors, setClusterSetDuplicateErrors] = useState<
    Record<string, string>
  >({});
  const [clusterSetFocusId, setClusterSetFocusId] = useState<string | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(false);
  const [projectSettingsError, setProjectSettingsError] = useState<
    string | null
  >(null);
  const [projectSettingsFieldErrors, setProjectSettingsFieldErrors] = useState<
    Record<string, string>
  >({});
  const [projectDeleteError, setProjectDeleteError] = useState<string | null>(
    null,
  );
  const [isProjectSettingsSaving, setIsProjectSettingsSaving] = useState(false);
  const [activePage, setActivePage] = useState<ActivePage>("projects");
  const [settingsTab, setSettingsTab] = useState<SettingsTab>("providers");
  const [projectTab, setProjectTab] = useState<ProjectTab>("import");
  const [newProviderType, setNewProviderType] =
    useState<ConfigurableProvider>("openai");
  const [ollamaPullProviderId, setOllamaPullProviderId] = useState<
    string | null
  >(null);
  const [indexingProviderId, setIndexingProviderId] = useState("");
  const [indexingModel, setIndexingModel] = useState("");
  const [cloudUseConfirmed, setCloudUseConfirmed] = useState(false);
  const [removeIndexingLineBreaks, setRemoveIndexingLineBreaks] =
    useState(false);
  const [replaceIndexingLineBreaks, setReplaceIndexingLineBreaks] =
    useState(false);
  const [indexingLineBreakReplacement, setIndexingLineBreakReplacement] =
    useState(". ");
  const [lowercaseIndexingInput, setLowercaseIndexingInput] = useState(false);
  const [clusterSetVectorBasis, setClusterSetVectorBasis] = useState("message");
  const [clusterSetAlgorithm, setClusterSetAlgorithm] = useState("hdbscan");
  const [
    clusterSetAgglomerativeSplitRule,
    setClusterSetAgglomerativeSplitRule,
  ] = useState("n_clusters");
  const [clusterSetRefinementMode, setClusterSetRefinementMode] =
    useState("common");
  const [clusterSetReductionMethod, setClusterSetReductionMethod] =
    useState("none");
  const [clusterSetExecutionBackend, setClusterSetExecutionBackend] =
    useState("auto");
  const [clusterSetLlmProviderId, setClusterSetLlmProviderId] = useState("");
  const [clusterSetSummaryRequestId, setClusterSetSummaryRequestId] = useState<
    string | null
  >(null);
  const [summaryDialogClusterSet, setSummaryDialogClusterSet] =
    useState<ClusterSet | null>(null);
  const [summaryDialogError, setSummaryDialogError] = useState<string | null>(
    null,
  );
  const [summaryDialogProviderId, setSummaryDialogProviderId] = useState("");
  const [summaryDialogModel, setSummaryDialogModel] = useState("");
  const [summaryDialogSampleCount, setSummaryDialogSampleCount] = useState(10);
  const [summaryDialogSampleAll, setSummaryDialogSampleAll] = useState(false);
  const [summaryDialogCloudUseConfirmed, setSummaryDialogCloudUseConfirmed] =
    useState(false);
  const [explorerSummaryError, setExplorerSummaryError] = useState<
    string | null
  >(null);
  const [clusterSetLlmSampleAll, setClusterSetLlmSampleAll] = useState(false);
  const [clusterSetCloudUseConfirmed, setClusterSetCloudUseConfirmed] =
    useState(false);
  const [globalMenuOpen, setGlobalMenuOpen] = useState(false);
  const projectOpenGeneration = useRef(0);
  const clusterSetGenerationRequestRef =
    useRef<ClusterSetGenerationRequest | null>(null);
  const sourceDialogRef = useRef<HTMLElement | null>(null);
  const sourceDialogCloseRef = useRef<HTMLButtonElement | null>(null);
  const sourceDialogTriggerRef = useRef<HTMLElement | null>(null);
  const explorerTableWorkspaceRef = useRef<HTMLDivElement | null>(null);
  const clusterSetCardRefs = useRef(new Map<string, HTMLElement>());
  const summaryDialogRef = useRef<HTMLElement | null>(null);
  const summaryDialogCloseRef = useRef<HTMLButtonElement | null>(null);
  const summaryDialogTriggerRef = useRef<HTMLElement | null>(null);
  const globalMenuButtonRef = useRef<HTMLButtonElement | null>(null);
  const globalMenuRef = useRef<HTMLDivElement | null>(null);
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
    const firstEmbeddingProvider = nextProviders.find(
      (provider) => provider.manualModels.length > 0,
    );
    const firstLlmProvider = nextProviders.find(
      (provider) => provider.llmModels.length > 0,
    );
    setIndexingProviderId((current) =>
      current && nextProviders.some((provider) => provider.id === current)
        ? current
        : (firstEmbeddingProvider?.id ?? ""),
    );
    setClusterSetLlmProviderId((current) =>
      current && nextProviders.some((provider) => provider.id === current)
        ? current
        : (firstLlmProvider?.id ?? ""),
    );
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
      setExplorerSummaryError(null);
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
    setClusterSetSummaryRequestId(null);
    setSummaryDialogClusterSet(null);
    setSummaryDialogError(null);
    setSummaryDialogProviderId("");
    setSummaryDialogModel("");
    setSummaryDialogSampleCount(10);
    setSummaryDialogSampleAll(false);
    setSummaryDialogCloudUseConfirmed(false);
    setExplorerSummaryError(null);
    resetSourceDialogState();
    setExportLogs([]);
    setExplorerExportError(null);
    setLastExportContent("");
    setLastExportContentType("");
    setIndexingProviderId("");
    setClusterSetReductionMethod("none");
    setClusterSetExecutionBackend("auto");
    setClusterSetLlmProviderId("");
    setClusterSetSummaryRequestId(null);
    setSummaryDialogClusterSet(null);
    setSummaryDialogError(null);
    setSummaryDialogProviderId("");
    setSummaryDialogModel("");
    setSummaryDialogSampleCount(10);
    setSummaryDialogSampleAll(false);
    setSummaryDialogCloudUseConfirmed(false);
    setExplorerSummaryError(null);
    setActivePage("projects");
    setGlobalMenuOpen(false);
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
    setGlobalMenuOpen(false);
    setActivePage("settings");
    setSettingsTab("providers");
  }

  function openProjectListPage() {
    setGlobalMenuOpen(false);
    invalidateProjectContext();
    setActivePage("projects");
    setCurrentProject(null);
    setIndexingRuns([]);
    setClusterSets([]);
    setProjectTab("import");
    setProjectSettingsError(null);
    setProjectSettingsFieldErrors({});
    setProjectDeleteError(null);
    setFeedback(null);
    setExplorerSummaryError(null);
  }

  function navigateFromGlobalMenu(target: "projects" | "settings" | "signout") {
    if (target === "projects") {
      openProjectListPage();
      globalMenuButtonRef.current?.focus();
      return;
    }
    if (target === "settings") {
      openProvidersPage();
      globalMenuButtonRef.current?.focus();
      return;
    }
    setGlobalMenuOpen(false);
    signOut();
  }

  useEffect(() => {
    if (!globalMenuOpen) {
      return undefined;
    }
    function closeOnPointerDown(event: PointerEvent) {
      const target = event.target;
      if (!(target instanceof Node)) {
        return;
      }
      if (
        globalMenuRef.current?.contains(target) ||
        globalMenuButtonRef.current?.contains(target)
      ) {
        return;
      }
      setGlobalMenuOpen(false);
    }
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key !== "Escape") {
        return;
      }
      setGlobalMenuOpen(false);
      globalMenuButtonRef.current?.focus();
    }
    document.addEventListener("pointerdown", closeOnPointerDown);
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnPointerDown);
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [globalMenuOpen]);

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
      setProjectSettingsError(null);
      setProjectSettingsFieldErrors({});
      setProjectDeleteError(null);
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

  async function updateProjectSettings(
    event: FormEvent<HTMLFormElement>,
    projectId: string,
  ) {
    event.preventDefault();
    if (session === null) {
      return;
    }
    const form = new FormData(event.currentTarget);
    const name = String(form.get("projectName") ?? "");
    const ticketUrlTemplate = String(form.get("ticketUrlTemplate") ?? "");
    setFeedback(null);
    if (!name.trim()) {
      setProjectSettingsFieldErrors({
        projectName: "Projektname ist erforderlich.",
      });
      setProjectSettingsError(
        "Die Projekteinstellungen konnten nicht gespeichert werden.",
      );
      return;
    }
    setIsProjectSettingsSaving(true);
    setProjectSettingsError(null);
    setProjectSettingsFieldErrors({});
    try {
      const updated = await apiRequest<ApiProject>(
        `/api/projects/${projectId}`,
        {
          method: "PATCH",
          token: session.token,
          body: JSON.stringify({
            name,
            ticket_url_template:
              ticketUrlTemplate.trim() === "" ? null : ticketUrlTemplate,
          }),
        },
      );
      const project = toProject(updated);
      setProjects((existing) =>
        existing.map((item) => (item.id === projectId ? project : item)),
      );
      if (currentProject?.id === projectId) {
        setCurrentProject(project);
      }
      showFeedback("success", "Projekteinstellungen gespeichert.");
    } catch (error: unknown) {
      if (error instanceof ApiRequestError) {
        setProjectSettingsFieldErrors(error.fieldErrors);
        if (error.code === "VALIDATION_FAILED") {
          setProjectSettingsError(
            "Die Projekteinstellungen konnten nicht gespeichert werden. Bitte Eingaben prüfen.",
          );
        } else if (error.code === "PROJECT_NOT_FOUND") {
          setProjectSettingsError("Das Projekt wurde nicht gefunden.");
        } else {
          setProjectSettingsError(
            "Die Projekteinstellungen konnten nicht gespeichert werden.",
          );
        }
      } else {
        setProjectSettingsError(
          "Die Projekteinstellungen konnten nicht gespeichert werden.",
        );
      }
    } finally {
      setIsProjectSettingsSaving(false);
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
    setProjectDeleteError(null);
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
      setProjectDeleteError(
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
        selectedLog !== undefined &&
          selectedLog.skippedRecords > selectedLog.skippedDetailCount
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

  function upsertProviderState(updated: ApiProviderConfiguration) {
    const nextProvider = toProviderConfiguration(updated);
    setProviders((existing) =>
      existing.map((item) =>
        item.id === nextProvider.id ? nextProvider : item,
      ),
    );
  }

  async function addProvider() {
    if (session === null) {
      return;
    }
    try {
      const created = await apiRequest<ApiProviderConfiguration>(
        "/api/providers",
        {
          method: "POST",
          token: session.token,
          body: JSON.stringify({ provider: newProviderType }),
        },
      );
      const nextProvider = toProviderConfiguration(created);
      setProviders((existing) => [...existing, nextProvider]);
      showFeedback("success", `${nextProvider.displayName} wurde hinzugefügt.`);
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(error, "Provider konnte nicht hinzugefügt werden."),
      );
    }
  }

  async function deleteProvider(provider: ProviderConfiguration) {
    if (session === null) {
      return;
    }
    try {
      await apiRequest<void>(`/api/providers/${provider.id}`, {
        method: "DELETE",
        token: session.token,
      });
      setProviders((existing) =>
        existing.filter((item) => item.id !== provider.id),
      );
      if (indexingProviderId === provider.id) {
        setIndexingProviderId("");
        setIndexingModel("");
      }
      if (clusterSetLlmProviderId === provider.id) {
        setClusterSetLlmProviderId("");
      }
      showFeedback(
        "success",
        `${provider.displayName} wurde aus der aktiven Konfiguration entfernt.`,
      );
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(error, "Provider konnte nicht entfernt werden."),
      );
    }
  }

  async function configureProvider(
    event: FormEvent<HTMLFormElement>,
    provider: ProviderConfiguration,
  ) {
    event.preventDefault();
    if (session === null) {
      return;
    }
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const displayName = String(form.get("displayName") ?? "").trim();
    const endpointUrl = String(form.get("endpointUrl") ?? "").trim();
    const apiKey = String(form.get("apiKey") ?? "");
    const payload: Record<string, unknown> = {
      display_name: displayName || provider.displayName,
      provider: provider.provider,
      endpoint_url: provider.provider === "ollama" ? endpointUrl : null,
      available_models: provider.availableModels,
      manual_models: provider.manualModels,
      llm_models: provider.llmModels,
    };
    if (provider.provider === "openai") {
      payload.api_key = apiKey || null;
      payload.remove_api_key = form.get("removeApiKey") === "on";
    }
    try {
      const updated = await apiRequest<ApiProviderConfiguration>(
        `/api/providers/${provider.id}`,
        {
          method: "PUT",
          token: session.token,
          body: JSON.stringify(payload),
        },
      );
      upsertProviderState(updated);
      const apiKeyInput = formElement.elements.namedItem("apiKey");
      if (apiKeyInput instanceof HTMLInputElement) {
        apiKeyInput.value = "";
      }
      showFeedback(
        "success",
        `${displayName || provider.displayName} gespeichert.`,
      );
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

  async function testProviderConnection(provider: ProviderConfiguration) {
    if (session === null) {
      return;
    }
    try {
      const result = await apiRequest<ApiProviderCheck>(
        `/api/providers/${provider.id}/check`,
        {
          method: "POST",
          token: session.token,
        },
      );
      if (result.ok) {
        showFeedback(
          "success",
          `Verbindung zu ${provider.displayName} erfolgreich geprüft.`,
        );
      } else {
        showFeedback(
          "warning",
          result.message || "Verbindung konnte nicht geprüft werden.",
        );
      }
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(error, "Verbindung konnte nicht geprüft werden."),
      );
    }
  }

  async function discoverProviderModels(provider: ProviderConfiguration) {
    if (session === null) {
      return;
    }
    try {
      const result = await apiRequest<ApiProviderCheck>(
        `/api/providers/${provider.id}/check`,
        {
          method: "POST",
          token: session.token,
        },
      );
      const models = uniqueModels(result.models);
      if (result.ok) {
        setProviders((existing) =>
          existing.map((item) =>
            item.id === provider.id
              ? reconcileDiscoveredProviderModels(item, models, result)
              : item,
          ),
        );
      }
      if (result.ok && models.length > 0) {
        showFeedback(
          "success",
          `${models.length} Modell(e) für ${provider.displayName} abgerufen.`,
        );
      } else if (result.ok) {
        showFeedback("info", "Keine Modelle gefunden.");
      } else {
        showFeedback(
          "warning",
          result.message || "Modelle konnten nicht abgerufen werden.",
        );
      }
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(error, "Modelle konnten nicht abgerufen werden."),
      );
    }
  }

  function toggleProviderModel(
    providerId: string,
    purpose: "embedding" | "llm",
    model: string,
    checked: boolean,
  ) {
    setProviders((existing) =>
      existing.map((provider) => {
        if (provider.id !== providerId) {
          return provider;
        }
        const current =
          purpose === "embedding" ? provider.manualModels : provider.llmModels;
        const selected = new Set(
          checked
            ? [...current, model]
            : current.filter((item) => item !== model),
        );
        const options =
          purpose === "embedding"
            ? embeddingModelOptions(provider)
            : llmModelOptions(provider);
        const next = options.filter((item) => selected.has(item));
        return purpose === "embedding"
          ? { ...provider, manualModels: next }
          : { ...provider, llmModels: next };
      }),
    );
  }

  async function pullOllamaModel(
    provider: ProviderConfiguration,
    formElement: HTMLFormElement,
  ) {
    if (session === null) {
      return;
    }
    const form = new FormData(formElement);
    const model = String(form.get("pullModel") ?? "").trim();
    if (!model) {
      showFeedback("warning", "Ollama Modellname fehlt.");
      return;
    }
    setOllamaPullProviderId(provider.id);
    showFeedback("info", `Ollama Modell ${model} wird heruntergeladen.`);
    try {
      const updated = await apiRequest<ApiProviderConfiguration>(
        `/api/providers/${provider.id}/ollama/pull`,
        {
          method: "POST",
          token: session.token,
          body: JSON.stringify({ model }),
        },
      );
      upsertProviderState(updated);
      formElement.reset();
      showFeedback("success", `Ollama Modell ${model} wurde hinzugefügt.`);
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(error, "Ollama Modell konnte nicht geladen werden."),
      );
    } finally {
      setOllamaPullProviderId(null);
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

  function indexingNormalizationParameters(): Record<string, unknown> {
    const normalization: Record<string, unknown> = {};
    if (removeIndexingLineBreaks) {
      normalization.newline_mode = "remove";
    } else if (replaceIndexingLineBreaks) {
      normalization.newline_mode = "replace";
      normalization.newline_replacement = indexingLineBreakReplacement;
    } else if (lowercaseIndexingInput) {
      normalization.newline_mode = "preserve";
    }
    if (lowercaseIndexingInput) {
      normalization.lowercase = true;
    }
    if (Object.keys(normalization).length > 0) {
      return { embedding_input_normalization: normalization };
    }
    return {};
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
    if (!datasetVersionId || !indexingProviderId || !indexingModel) {
      showFeedback("warning", "Bitte Datensatz und Embedding-Modell wählen.");
      return;
    }
    const replacementHasLineBreak =
      indexingLineBreakReplacement.includes("\n") ||
      indexingLineBreakReplacement.includes("\r");
    if (
      replaceIndexingLineBreaks &&
      (indexingLineBreakReplacement.length === 0 || replacementHasLineBreak)
    ) {
      showFeedback(
        "warning",
        "Bitte ein Ersatzzeichen ohne Zeilenumbruch angeben.",
      );
      return;
    }
    if (
      indexingProviderConfiguration?.provider === "openai" &&
      !cloudUseConfirmed
    ) {
      showFeedback(
        "warning",
        "OpenAI Cloud-Nutzung muss vor dem Start bestätigt werden.",
      );
      return;
    }
    try {
      const parameters = indexingNormalizationParameters();
      const created = await apiRequest<ApiIndexingRun>(
        `/api/projects/${originProjectId}/indexing-runs`,
        {
          method: "POST",
          token: session.token,
          body: JSON.stringify({
            dataset_version_id: datasetVersionId,
            provider_id: indexingProviderId,
            model: indexingModel,
            cloud_use_confirmed:
              indexingProviderConfiguration?.provider === "openai"
                ? cloudUseConfirmed
                : undefined,
            parameters:
              Object.keys(parameters).length > 0 ? parameters : undefined,
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

  function touchClusterSetFromClusterUpdate(updatedCluster: Cluster) {
    const clusterSetId = updatedCluster.clusterSetId;
    if (clusterSetId === null) {
      return;
    }
    setClusterSets((existing) =>
      sortClusterSetsByRecency(
        existing.map((clusterSet) =>
          clusterSet.id === clusterSetId
            ? { ...clusterSet, updatedAt: updatedCluster.updatedAt }
            : clusterSet,
        ),
      ),
    );
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
    const nClusters = Number.parseInt(String(form.get("nClusters") ?? "2"), 10);
    const distanceThresholdRaw = String(
      form.get("distanceThreshold") ?? "",
    ).trim();
    const linkage = String(form.get("linkage") ?? "ward");
    const reductionMethod = String(form.get("reductionMethod") ?? "none");
    const executionBackend = String(form.get("executionBackend") ?? "auto");
    const reductionDimensions = Number.parseInt(
      String(form.get("reductionDimensions") ?? "10"),
      10,
    );
    const umapNeighbors = Number.parseInt(
      String(form.get("umapNeighbors") ?? "15"),
      10,
    );
    const umapMinDist = Number.parseFloat(
      String(form.get("umapMinDist") ?? "0"),
    );
    const outlierThresholdRaw = String(
      form.get("outlierThreshold") ?? "",
    ).trim();
    const llmProviderId = String(form.get("llmProviderId") ?? "");
    const llmModel = String(form.get("llmModel") ?? "").trim();
    const llmSampleCount = parsePositiveInteger(form.get("llmSampleCount"));
    if (
      llmProviderId !== "" &&
      !clusterSetLlmSampleAll &&
      llmSampleCount === null
    ) {
      showFeedback(
        "error",
        ERROR_MESSAGES_BY_CODE.CLUSTER_SUMMARY_SAMPLE_COUNT_INVALID,
      );
      return;
    }
    if (
      clusterSetAlgorithm === "agglomerative" &&
      clusterSetAgglomerativeSplitRule === "n_clusters" &&
      !Number.isFinite(nClusters)
    ) {
      showFeedback(
        "error",
        ERROR_MESSAGES_BY_CODE.CLUSTER_ALGORITHM_PARAMETERS_INVALID,
      );
      return;
    }
    const distanceThreshold = Number.parseFloat(distanceThresholdRaw);
    if (
      clusterSetAlgorithm === "agglomerative" &&
      clusterSetAgglomerativeSplitRule === "distance_threshold" &&
      !Number.isFinite(distanceThreshold)
    ) {
      showFeedback(
        "error",
        ERROR_MESSAGES_BY_CODE.CLUSTER_ALGORITHM_PARAMETERS_INVALID,
      );
      return;
    }
    const algorithmSettings =
      clusterSetAlgorithm === "agglomerative"
        ? {
            algorithm: "agglomerative",
            linkage,
            ...(clusterSetAgglomerativeSplitRule === "distance_threshold"
              ? { distance_threshold: distanceThreshold }
              : { n_clusters: Number.isFinite(nClusters) ? nClusters : 2 }),
          }
        : {
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
            reduction_method: reductionMethod,
            execution_backend: executionBackend,
            ...(reductionMethod !== "none"
              ? {
                  reduction_dimensions: Number.isFinite(reductionDimensions)
                    ? reductionDimensions
                    : 10,
                }
              : {}),
            ...(reductionMethod === "umap"
              ? {
                  umap_n_neighbors: Number.isFinite(umapNeighbors)
                    ? umapNeighbors
                    : 15,
                  umap_min_dist: Number.isFinite(umapMinDist) ? umapMinDist : 0,
                }
              : {}),
          };
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
            refinement_mode:
              clusterSetRefinementDraft === null
                ? "common"
                : clusterSetRefinementMode,
            vector_basis: clusterSetVectorBasis,
            message_weight:
              clusterSetVectorBasis === "combined"
                ? Number(form.get("messageWeight") ?? 0.5)
                : 1,
            answer_weight:
              clusterSetVectorBasis === "combined"
                ? Number(form.get("answerWeight") ?? 0.5)
                : 0,
            algorithm_settings: algorithmSettings,
            outlier_threshold: outlierThresholdRaw
              ? Number.parseFloat(outlierThresholdRaw)
              : null,
            source_cluster_ids:
              clusterSetRefinementDraft?.sourceClusterIds ?? [],
            llm_provider_id: llmProviderId || null,
            llm_model: llmProviderId ? llmModel || null : null,
            llm_sample_count:
              llmProviderId && !clusterSetLlmSampleAll ? llmSampleCount : null,
            llm_sample_all: clusterSetLlmSampleAll,
            llm_cloud_use_confirmed:
              clusterSetLlmProviderConfiguration?.provider === "openai" &&
              clusterSetCloudUseConfirmed,
          }),
        },
      );
      if (projectOpenGeneration.current !== request.generation) {
        return;
      }
      upsertClusterSet(toClusterSet(created));
      setClusterSetFocusId(created.id);
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

  function closeSummaryRegenerationDialog() {
    setSummaryDialogClusterSet(null);
    setSummaryDialogError(null);
    setSummaryDialogCloudUseConfirmed(false);
    summaryDialogTriggerRef.current?.focus();
    summaryDialogTriggerRef.current = null;
  }

  function openSummaryRegenerationDialog(
    clusterSet: ClusterSet,
    trigger?: HTMLElement,
  ) {
    const providerConfiguration =
      llmProviders.find(
        (provider) => provider.id === clusterSet.llmProviderConfigurationId,
      ) ?? llmProviders[0];
    const requested = clusterSet.llmSampleStrategy.requested;
    const nextSampleAll = requested === "all";
    const nextSampleCount =
      typeof requested === "number" &&
      Number.isSafeInteger(requested) &&
      requested > 0
        ? Math.min(requested, 50)
        : 10;
    summaryDialogTriggerRef.current = trigger ?? null;
    setSummaryDialogClusterSet(clusterSet);
    setSummaryDialogProviderId(providerConfiguration?.id ?? "");
    setSummaryDialogModel(
      clusterSet.llmModel !== null &&
        providerConfiguration?.llmModels.includes(clusterSet.llmModel)
        ? clusterSet.llmModel
        : (providerConfiguration?.llmModels[0] ?? clusterSet.llmModel ?? ""),
    );
    setSummaryDialogSampleCount(nextSampleCount);
    setSummaryDialogSampleAll(nextSampleAll);
    setSummaryDialogCloudUseConfirmed(false);
    setSummaryDialogError(null);
    setExplorerSummaryError(null);
  }

  async function regenerateClusterSetSummaries(
    clusterSet: ClusterSet,
    surface: "dialog" | "explorer",
  ) {
    const setSurfaceError =
      surface === "dialog" ? setSummaryDialogError : setExplorerSummaryError;
    setSurfaceError(null);
    const selectedProvider = llmProviders.find(
      (provider) => provider.id === summaryDialogProviderId,
    );
    const selectedModel = summaryDialogModel.trim();
    const safeSampleCount = Math.max(
      1,
      Math.min(50, Math.trunc(summaryDialogSampleCount)),
    );
    if (
      session === null ||
      currentProject === null ||
      selectedProvider === undefined ||
      selectedModel === ""
    ) {
      const message =
        "Für die Summary-Neuerstellung muss ein aktiver LLM-Provider mit Modell ausgewählt sein.";
      setSurfaceError(message);
      showFeedback("error", message);
      return;
    }
    if (
      selectedProvider.provider === "openai" &&
      !summaryDialogCloudUseConfirmed
    ) {
      const message =
        "Bitte bestätige die OpenAI-Übertragung für diese Summary-Neuerstellung.";
      setSurfaceError(message);
      showFeedback("error", message);
      return;
    }
    setClusterSetSummaryRequestId(clusterSet.id);
    showFeedback("info", "Summary-Neuerstellung wurde gestartet.");
    try {
      const updated = await apiRequest<ApiClusterSet>(
        `/api/projects/${currentProject.id}/cluster-sets/${clusterSet.id}/summaries`,
        {
          method: "POST",
          token: session.token,
          body: JSON.stringify({
            llm_provider_id: selectedProvider.id,
            llm_model: selectedModel,
            llm_sample_count: summaryDialogSampleAll ? null : safeSampleCount,
            llm_sample_all: summaryDialogSampleAll,
            llm_cloud_use_confirmed:
              selectedProvider.provider === "openai" &&
              summaryDialogCloudUseConfirmed,
          }),
        },
      );
      upsertClusterSet(toClusterSet(updated));
      setSurfaceError(null);
      if (surface === "dialog") {
        closeSummaryRegenerationDialog();
      }
      showFeedback(
        "success",
        "Summary-Neuerstellung gestartet. Status wird aktualisiert.",
      );
    } catch (error: unknown) {
      const message = actionErrorMessage(
        error,
        "Summary-Neuerstellung konnte nicht gestartet werden.",
      );
      setSurfaceError(message);
      showFeedback("error", message);
    } finally {
      setClusterSetSummaryRequestId((activeId) =>
        activeId === clusterSet.id ? null : activeId,
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

  function toggleClusterSetSelection(clusterSetId: string, checked: boolean) {
    setSelectedClusterSetIds((existing) =>
      checked
        ? [...existing.filter((id) => id !== clusterSetId), clusterSetId]
        : existing.filter((id) => id !== clusterSetId),
    );
  }

  async function duplicateClusterSet(clusterSetId: string) {
    if (session === null || currentProject === null) {
      return;
    }
    setClusterSetDuplicateRequestId(clusterSetId);
    setClusterSetDuplicateErrors((existing) => {
      const { [clusterSetId]: _removed, ...remaining } = existing;
      return remaining;
    });
    try {
      const duplicated = await apiRequest<ApiClusterSet>(
        `/api/projects/${currentProject.id}/cluster-sets/${clusterSetId}/duplicate`,
        { method: "POST", token: session.token },
      );
      const nextClusterSet = toClusterSet(duplicated);
      upsertClusterSet(nextClusterSet);
      setClusterSetFocusId(nextClusterSet.id);
      setClusterSetDuplicateErrors((existing) => {
        const { [clusterSetId]: _removed, ...remaining } = existing;
        return remaining;
      });
      showFeedback("success", "Cluster-Set dupliziert.");
    } catch (error: unknown) {
      const message = actionErrorMessage(
        error,
        "Cluster-Set konnte nicht dupliziert werden.",
      );
      setClusterSetDuplicateErrors((existing) => ({
        ...existing,
        [clusterSetId]: message,
      }));
      showFeedback("error", message);
    } finally {
      setClusterSetDuplicateRequestId((activeId) =>
        activeId === clusterSetId ? null : activeId,
      );
    }
  }

  async function batchDeleteClusterSets() {
    if (
      session === null ||
      currentProject === null ||
      selectedClusterSetIds.length === 0
    ) {
      return;
    }
    if (
      !window.confirm(
        `${selectedClusterSetIds.length} Cluster-Sets löschen? Die Aktion löscht nur, wenn alle ausgewählten Sets noch verfügbar sind.`,
      )
    ) {
      return;
    }
    setClusterSetBatchDeleteInProgress(true);
    try {
      const result = await apiRequest<ApiClusterSetBatchDeleteResponse>(
        `/api/projects/${currentProject.id}/cluster-sets/batch-delete`,
        {
          method: "POST",
          token: session.token,
          body: JSON.stringify({ cluster_set_ids: selectedClusterSetIds }),
        },
      );
      const deletedIds = new Set(result.deleted_cluster_set_ids);
      setClusterSets(result.cluster_sets.map(toClusterSet));
      setSelectedClusterSetIds((existing) =>
        existing.filter((id) => !deletedIds.has(id)),
      );
      if (clusterSetLoadId !== null && deletedIds.has(clusterSetLoadId)) {
        setClusters([]);
        resetSourceDialogState();
        setClusterSetLoadId(null);
      }
      showFeedback("success", "Ausgewählte Cluster-Sets gelöscht.");
    } catch (error: unknown) {
      showFeedback(
        "error",
        actionErrorMessage(
          error,
          "Cluster-Sets konnten nicht gelöscht werden.",
        ),
      );
    } finally {
      setClusterSetBatchDeleteInProgress(false);
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
      const updatedCluster = toCluster(updated);
      setClusters((existing) =>
        existing.map((cluster) =>
          cluster.id === clusterId ? updatedCluster : cluster,
        ),
      );
      touchClusterSetFromClusterUpdate(updatedCluster);
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
      const updatedCluster = toCluster(updated);
      setClusters((existing) =>
        existing.map((cluster) =>
          cluster.id === clusterId ? updatedCluster : cluster,
        ),
      );
      touchClusterSetFromClusterUpdate(updatedCluster);
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

  function scrollExplorerToTop() {
    explorerTableWorkspaceRef.current?.scrollTo({
      top: 0,
      behavior: "smooth",
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function createRefinementDraftFromVisibleClusters() {
    if (loadedClusterSet === null) {
      return;
    }
    const sourceClusters = visibleIncludedClusters.map((cluster) => ({
      id: cluster.id,
      title: cluster.effectiveTitle,
      label: clusterCategory(cluster),
      isOutlier: cluster.isOutlier,
    }));
    const sourceClusterIds = sourceClusters.map((cluster) => cluster.id);
    if (sourceClusterIds.length === 0) {
      showFeedback(
        "error",
        ERROR_MESSAGES_BY_CODE.CLUSTER_REFINEMENT_EMPTY_SOURCE,
      );
      return;
    }
    setClusterSetRefinementDraft({
      parentClusterSetId: loadedClusterSet.id,
      parentClusterSetName: loadedClusterSet.displayName,
      indexingRunId: loadedClusterSet.indexingRunId,
      sourceClusterIds,
      sources: sourceClusters,
      description: `${sourceClusterIds.length} sichtbare eingeschlossene Cluster aus ${loadedClusterSet.displayName}`,
    });
    setClusterSetRefinementMode("common");
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
      const sourceClusters = apiClusters
        .map(toCluster)
        .filter((cluster) => !clusterIsExcluded(cluster))
        .map((cluster) => ({
          id: cluster.id,
          title: cluster.effectiveTitle,
          label: clusterCategory(cluster),
          isOutlier: cluster.isOutlier,
        }));
      const sourceClusterIds = sourceClusters.map((cluster) => cluster.id);
      if (sourceClusterIds.length === 0) {
        showFeedback(
          "error",
          ERROR_MESSAGES_BY_CODE.CLUSTER_REFINEMENT_EMPTY_SOURCE,
        );
        return;
      }
      setClusterSetRefinementDraft({
        parentClusterSetId: clusterSet.id,
        parentClusterSetName: clusterSet.displayName,
        indexingRunId: clusterSet.indexingRunId,
        sourceClusterIds,
        sources: sourceClusters,
        description: `${sourceClusterIds.length} eingeschlossene Cluster aus ${clusterSet.displayName}`,
      });
      setClusterSetRefinementMode("common");
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
      "reduction_method",
      "reduction_dimensions",
      "umap_n_neighbors",
      "umap_min_dist",
      "execution_backend",
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

  const embeddingProviders = providers.filter(
    (provider) => provider.manualModels.length > 0,
  );
  const llmProviders = providers.filter(
    (provider) => provider.llmModels.length > 0,
  );
  const summaryDialogProvider =
    llmProviders.find((provider) => provider.id === summaryDialogProviderId) ??
    null;
  const summaryDialogModels = summaryDialogProvider?.llmModels ?? [];
  const summaryDialogModelKey = summaryDialogModels.join("\u0000");
  const summaryDialogUsesOpenAi = summaryDialogProvider?.provider === "openai";
  const runnableDatasetLogs = importLogs.filter(
    (log) => log.datasetVersionId !== null && log.datasetDeletedAt === null,
  );
  const indexingProviderConfiguration = providers.find(
    (provider) => provider.id === indexingProviderId,
  );
  const indexingProviderModels =
    indexingProviderConfiguration?.manualModels ?? [];
  const completedIndexingRuns = indexingRuns.filter(
    (run) => run.status === "completed",
  );
  const clusterSetLlmProviderConfiguration = providers.find(
    (provider) => provider.id === clusterSetLlmProviderId,
  );
  const clusterSetLlmProviderModels =
    clusterSetLlmProviderId === ""
      ? []
      : (clusterSetLlmProviderConfiguration?.llmModels ?? []);

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

  function compareClusterText(left: string | null, right: string | null) {
    return (left ?? "").localeCompare(right ?? "", "de", {
      sensitivity: "base",
      numeric: true,
    });
  }

  function compareClusterNumbers(left: number | null, right: number | null) {
    if (left === null && right === null) {
      return 0;
    }
    if (left === null) {
      return 1;
    }
    if (right === null) {
      return -1;
    }
    return left - right;
  }

  function clusterSortValue(cluster: Cluster, key: ClusterSortKey) {
    if (key === "status") {
      return cluster.effectiveStatus;
    }
    if (key === "title") {
      return cluster.effectiveTitle;
    }
    if (key === "category") {
      return clusterCategory(cluster);
    }
    if (key === "customerQuestions" || key === "supportAnswers") {
      return cluster.memberCount;
    }
    return cluster.score;
  }

  function sortClustersForDisplay(
    nextClusters: Cluster[],
    sortState: ClusterSortState,
  ) {
    if (sortState === null) {
      return nextClusters;
    }
    const baselineOrder = new Map(
      clusters.map((cluster, index) => [cluster.id, index]),
    );
    const directionMultiplier = sortState.direction === "asc" ? 1 : -1;
    return nextClusters.slice().sort((left, right) => {
      const leftValue = clusterSortValue(left, sortState.key);
      const rightValue = clusterSortValue(right, sortState.key);
      const primaryComparison =
        typeof leftValue === "number" || typeof rightValue === "number"
          ? compareClusterNumbers(
              typeof leftValue === "number" ? leftValue : null,
              typeof rightValue === "number" ? rightValue : null,
            )
          : compareClusterText(String(leftValue), String(rightValue));
      if (primaryComparison !== 0) {
        return primaryComparison * directionMultiplier;
      }
      return (
        (baselineOrder.get(left.id) ?? 0) - (baselineOrder.get(right.id) ?? 0)
      );
    });
  }

  function cycleClusterSort(key: ClusterSortKey) {
    setClusterSort((current) => {
      if (current === null || current.key !== key) {
        return { key, direction: "asc" };
      }
      if (current.direction === "asc") {
        return { key, direction: "desc" };
      }
      return null;
    });
  }

  function clusterHeaderSortLabel(key: ClusterSortKey, label: string) {
    if (clusterSort?.key !== key) {
      return `${label} sortieren, aktuell unsortiert`;
    }
    return `${label} sortieren, aktuell ${
      clusterSort.direction === "asc" ? "aufsteigend" : "absteigend"
    }`;
  }

  function clusterHeaderSortIndicator(key: ClusterSortKey) {
    if (clusterSort?.key !== key) {
      return "↕";
    }
    return clusterSort.direction === "asc" ? "↑" : "↓";
  }

  function clusterHeaderAriaSort(
    key: ClusterSortKey,
  ): "none" | "ascending" | "descending" {
    if (clusterSort?.key !== key) {
      return "none";
    }
    return clusterSort.direction === "asc" ? "ascending" : "descending";
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
  useEffect(() => {
    if (
      session === null ||
      currentProject === null ||
      projectTab !== "explorer" ||
      clusterSetLoadId !== null
    ) {
      return;
    }
    const latestCompleted = clusterSets.find(
      (clusterSet) =>
        clusterSet.status === "completed" && clusterSet.deletedAt === null,
    );
    if (latestCompleted !== undefined) {
      void loadClusterSetClusters(
        session.token,
        currentProject.id,
        latestCompleted.id,
      );
    }
  }, [clusterSetLoadId, clusterSets, currentProject, projectTab, session]);
  const clusterCategories = Array.from(
    new Set(clusters.map(clusterCategory)),
  ).sort((left, right) => left.localeCompare(right));
  const filteredClusters = clusters.filter(
    (cluster) =>
      (showExcludedClusters || !clusterIsExcluded(cluster)) &&
      (includeOutlierRows || !cluster.isOutlier) &&
      (clusterCategoryFilter === "" ||
        clusterCategory(cluster) === clusterCategoryFilter) &&
      clusterMatchesSearch(cluster, clusterSearchQuery),
  );
  const visibleClusters = sortClustersForDisplay(filteredClusters, clusterSort);
  const visibleIncludedClusters = visibleClusters.filter(
    (cluster) => !clusterIsExcluded(cluster),
  );
  const visibleExcludedClusters = visibleClusters.filter(clusterIsExcluded);
  const explorerClusterSummary = summarizeExplorerClusters(clusters);
  const hasPerParentOriginGrouping = visibleIncludedClusters.some(
    (cluster) => clusterOrigin(cluster) !== null,
  );
  const includedClusterGroups = hasPerParentOriginGrouping
    ? Array.from(
        visibleIncludedClusters
          .reduce((groups, cluster) => {
            const origin = clusterOrigin(cluster);
            const key =
              origin === null
                ? "origin-missing"
                : `origin-${origin.batchGroupIndex}-${origin.sourceParentClusterId}`;
            const existing = groups.get(key) ?? {
              key,
              label: clusterOriginGroupLabel(origin),
              sortIndex:
                origin === null
                  ? Number.MAX_SAFE_INTEGER
                  : origin.batchGroupIndex,
              clusters: [] as Cluster[],
            };
            existing.clusters.push(cluster);
            groups.set(key, existing);
            return groups;
          }, new Map<string, { key: string; label: string; sortIndex: number; clusters: Cluster[] }>())
          .values(),
      )
        .sort(
          (left, right) =>
            left.sortIndex - right.sortIndex ||
            left.label.localeCompare(right.label),
        )
        .map(({ key, label, clusters }) => ({ key, label, clusters }))
    : clusterGroupByCategory
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
  function clusterSetTreeOptions(
    clusterSet: ClusterSet,
    depth = 0,
  ): { clusterSet: ClusterSet; depth: number }[] {
    return [
      { clusterSet, depth },
      ...childClusterSets(clusterSet.id).flatMap((child) =>
        clusterSetTreeOptions(child, depth + 1),
      ),
    ];
  }
  const explorerClusterSetOptions = rootClusterSets
    .flatMap((root) => clusterSetTreeOptions(root))
    .filter(
      ({ clusterSet }) =>
        clusterSet.status === "completed" && clusterSet.deletedAt === null,
    );
  useEffect(() => {
    const visibleIds = new Set(clusterSets.map((clusterSet) => clusterSet.id));
    setSelectedClusterSetIds((existing) =>
      existing.filter((id) => visibleIds.has(id)),
    );
  }, [clusterSets]);
  useEffect(() => {
    if (clusterSetFocusId === null) {
      return;
    }
    const target = clusterSetCardRefs.current.get(clusterSetFocusId);
    if (target === undefined) {
      return;
    }
    target.scrollIntoView?.({ block: "center", behavior: "smooth" });
    target.focus({ preventScroll: true });
    setClusterSetFocusId(null);
  }, [clusterSetFocusId, clusterSets]);
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
  const activeSummaryDialogClusterSet =
    summaryDialogClusterSet === null
      ? null
      : (clusterSets.find((item) => item.id === summaryDialogClusterSet.id) ??
        summaryDialogClusterSet);
  const summaryDialogClusterSetId = summaryDialogClusterSet?.id ?? null;
  const summaryDialogCanStart =
    activeSummaryDialogClusterSet !== null &&
    summaryDialogProvider !== null &&
    summaryDialogModel.trim() !== "" &&
    (summaryDialogSampleAll ||
      (Number.isSafeInteger(summaryDialogSampleCount) &&
        summaryDialogSampleCount >= 1 &&
        summaryDialogSampleCount <= 50)) &&
    (!summaryDialogUsesOpenAi || summaryDialogCloudUseConfirmed) &&
    clusterSetSummaryRequestId !== activeSummaryDialogClusterSet.id;
  const canRegenerateLoadedClusterSetSummaries =
    loadedClusterSet !== null &&
    loadedClusterSet.status === "completed" &&
    loadedClusterSet.deletedAt === null &&
    loadedClusterSet.llmProviderConfigurationId !== null &&
    loadedClusterSet.llmModel !== null;

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
      providers.find((provider) => provider.id === indexingProviderId)
        ?.manualModels ?? [];
    setIndexingModel((currentModel) =>
      availableModels.includes(currentModel)
        ? currentModel
        : (availableModels[0] ?? ""),
    );
  }, [indexingProviderId, providers]);

  useEffect(() => {
    setCloudUseConfirmed(false);
  }, [currentProject?.id, indexingProviderId]);

  useEffect(() => {
    setClusterSetCloudUseConfirmed(false);
  }, [currentProject?.id, clusterSetLlmProviderId]);

  useEffect(() => {
    const availableModels =
      summaryDialogModelKey === "" ? [] : summaryDialogModelKey.split("\u0000");
    if (availableModels.length > 0) {
      setSummaryDialogModel((currentModel) =>
        availableModels.includes(currentModel)
          ? currentModel
          : (availableModels[0] ?? ""),
      );
    }
    setSummaryDialogCloudUseConfirmed(false);
  }, [summaryDialogModelKey, summaryDialogProviderId]);

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

  useEffect(() => {
    if (summaryDialogClusterSetId === null) {
      return undefined;
    }
    summaryDialogCloseRef.current?.focus();
    const handleDialogKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closeSummaryRegenerationDialog();
        return;
      }
      if (event.key !== "Tab" || summaryDialogRef.current === null) {
        return;
      }
      const focusable = Array.from(
        summaryDialogRef.current.querySelectorAll<HTMLElement>(
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
    return () => window.removeEventListener("keydown", handleDialogKeyDown);
  }, [summaryDialogClusterSetId]);

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
          <div className="cluster-actions-stack">
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
          </div>
        </td>
      </tr>
    );
  }

  function renderSourceTicketLabel(source: ClusterSource) {
    const ticketLabel = `Ticket ${source.ticketId}`;
    const ticketHref = buildTicketUrl(
      currentProject?.ticketUrlTemplate ?? null,
      source.ticketId,
    );
    return (
      <>
        {ticketHref === null ? (
          ticketLabel
        ) : (
          <a
            className="source-ticket-link"
            href={ticketHref}
            target="_blank"
            rel="noopener noreferrer"
          >
            {ticketLabel}
          </a>
        )}{" "}
        · Gruppe {source.messageGroupId}
      </>
    );
  }

  function renderSortableClusterHeader(key: ClusterSortKey, label: string) {
    return (
      <th aria-sort={clusterHeaderAriaSort(key)} scope="col">
        <button
          type="button"
          className="sort-header-button"
          aria-label={clusterHeaderSortLabel(key, label)}
          onClick={() => cycleClusterSort(key)}
        >
          <span>{label}</span>
          <span className="sort-indicator" aria-hidden="true">
            {clusterHeaderSortIndicator(key)}
          </span>
        </button>
      </th>
    );
  }

  function renderClusterSetCard(clusterSet: ClusterSet, depth = 0) {
    const children = childClusterSets(clusterSet.id);
    const hasChildren = children.length > 0;
    const isExpanded = !collapsedClusterSetIds.has(clusterSet.id);
    const childRegionId = `cluster-set-children-${clusterSet.id}`;
    const metadataRegionId = `cluster-set-metadata-${clusterSet.id}`;
    const isDeletedHistoryNode = clusterSet.deletedAt !== null;
    const parameterEntries = clusterSetParameterEntries(clusterSet);
    const isSelected = selectedClusterSetIds.includes(clusterSet.id);
    const isMetadataCollapsed = collapsedClusterSetMetadataIds.includes(
      clusterSet.id,
    );
    return (
      <article
        className={`user-card cluster-set-node ${isSelected ? "selected" : ""}`}
        key={clusterSet.id}
        ref={(element) => {
          if (element === null) {
            clusterSetCardRefs.current.delete(clusterSet.id);
            return;
          }
          clusterSetCardRefs.current.set(clusterSet.id, element);
        }}
        tabIndex={-1}
        style={{ marginLeft: depth === 0 ? 0 : "1rem" }}
      >
        <div className="user-heading cluster-set-heading">
          <div className="cluster-set-title">
            <label className="inline-checkbox">
              <input
                type="checkbox"
                checked={isSelected}
                disabled={isDeletedHistoryNode}
                onChange={(event) =>
                  toggleClusterSetSelection(clusterSet.id, event.target.checked)
                }
                aria-label={`${clusterSet.displayName} auswählen`}
              />
              <span className="sr-only">Auswählen</span>
            </label>
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
        <button
          type="button"
          className="secondary metadata-toggle"
          aria-expanded={!isMetadataCollapsed}
          aria-controls={metadataRegionId}
          onClick={() =>
            setCollapsedClusterSetMetadataIds((existing) =>
              existing.includes(clusterSet.id)
                ? existing.filter((id) => id !== clusterSet.id)
                : [...existing, clusterSet.id],
            )
          }
        >
          {isMetadataCollapsed ? "Metadaten anzeigen" : "Metadaten ausblenden"}
        </button>
        <div
          id={metadataRegionId}
          className="cluster-set-metadata"
          hidden={isMetadataCollapsed}
        >
          <p className="hint">
            Phase: {clusterSet.phase}; Basis: {clusterSet.vectorBasis};
            Algorithmus: {clusterSet.algorithm}; Cluster:{" "}
            {clusterSet.clusterCount}; aktiv: {clusterSet.activeClusterCount};
            aktive Nachrichtenpaare: {clusterSet.activeMessagePairCount}
          </p>
          <dl
            className="parameter-list parameter-list-compact"
            aria-label={`Parameter von ${clusterSet.displayName}`}
          >
            {parameterEntries.map((entry) => (
              <div key={entry.key}>
                <dt>{entry.label}</dt>
                <dd>{entry.value}</dd>
              </div>
            ))}
          </dl>
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
              ? `${clusterSet.llmProviderDisplayName ?? clusterSet.llmProvider}/${clusterSet.llmModel}`
              : "deaktiviert"}
          </p>
        </div>
        {clusterSet.errorCode !== null && (
          <p className="error" role="alert">
            {clusterSet.errorMessage ??
              ERROR_MESSAGES_BY_CODE[clusterSet.errorCode] ??
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
              clusterSet.status !== "completed" ||
              isDeletedHistoryNode ||
              clusterSetDuplicateRequestId === clusterSet.id
            }
            onClick={() => void duplicateClusterSet(clusterSet.id)}
          >
            {clusterSetDuplicateRequestId === clusterSet.id
              ? "Duplikat wird erstellt"
              : "Duplizieren"}
          </button>
          <button
            type="button"
            className="secondary"
            disabled={
              clusterSet.status !== "completed" ||
              isDeletedHistoryNode ||
              clusterSetSummaryRequestId === clusterSet.id
            }
            onClick={(event) => {
              openSummaryRegenerationDialog(clusterSet, event.currentTarget);
            }}
          >
            {clusterSetSummaryRequestId === clusterSet.id
              ? "Summaries werden gestartet"
              : "Summaries neu erstellen"}
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
        {clusterSetDuplicateErrors[clusterSet.id] !== undefined && (
          <p className="error" role="alert">
            {clusterSetDuplicateErrors[clusterSet.id]}
          </p>
        )}
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

  const feedbackOverlay =
    feedback === null ? null : (
      <div className="feedback-overlay">
        <p
          role={feedback.kind === "error" ? "alert" : "status"}
          className={`feedback ${feedback.kind}`}
        >
          <span className="feedback-text">
            <strong>{FEEDBACK_LABELS[feedback.kind]}:</strong> {feedback.text}
          </span>
          <button
            type="button"
            className="feedback-close"
            aria-label="Meldung schließen"
            onClick={() => setFeedback(null)}
          >
            ×
          </button>
        </p>
      </div>
    );

  const summaryRegenerationDialog =
    activeSummaryDialogClusterSet === null ? null : (
      <div className="dialog-backdrop">
        <section
          className="source-dialog summary-regeneration-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="summary-dialog-title"
          ref={summaryDialogRef}
        >
          <div className="panel-title">
            <div>
              <p className="eyebrow">Nur Summary-Job</p>
              <h2 id="summary-dialog-title">Summaries neu erstellen</h2>
            </div>
            <button
              type="button"
              className="secondary"
              aria-label="Dialog schließen"
              ref={summaryDialogCloseRef}
              onClick={closeSummaryRegenerationDialog}
            >
              ×
            </button>
          </div>
          <p>
            Cluster-Set:{" "}
            <strong>{activeSummaryDialogClusterSet.displayName}</strong>
          </p>
          <p className="status warning">
            Clusterzuordnung, Ausreißerstatus und manuelle Explorer-Änderungen
            bleiben unverändert. Es werden nur Titel, Kategorie, Frage- und
            Antwort-Summary neu geschrieben.
          </p>
          <div className="form-grid">
            <label>
              LLM-Provider
              <select
                value={summaryDialogProviderId}
                onChange={(event) =>
                  setSummaryDialogProviderId(event.currentTarget.value)
                }
              >
                {llmProviders.length === 0 && (
                  <option value="">Kein LLM-Provider verfügbar</option>
                )}
                {llmProviders.map((provider) => (
                  <option value={provider.id} key={provider.id}>
                    {provider.displayName}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Modell
              <select
                value={summaryDialogModel}
                onChange={(event) =>
                  setSummaryDialogModel(event.currentTarget.value)
                }
                disabled={summaryDialogModels.length === 0}
              >
                {summaryDialogModels.length === 0 && (
                  <option value="">Kein Modell verfügbar</option>
                )}
                {summaryDialogModels.map((model) => (
                  <option value={model} key={model}>
                    {model}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Beispiele je Cluster
              <input
                type="number"
                min="1"
                max="50"
                value={summaryDialogSampleCount}
                disabled={summaryDialogSampleAll}
                onChange={(event) =>
                  setSummaryDialogSampleCount(Number(event.currentTarget.value))
                }
              />
            </label>
            <label>
              Ergebnis
              <select value="replace" onChange={() => undefined}>
                <option value="replace">Aktuelle Summary ersetzen</option>
                <option value="version" disabled>
                  Zusätzlich als Version speichern (noch nicht verfügbar)
                </option>
              </select>
            </label>
          </div>
          <label className="inline-check">
            <input
              type="checkbox"
              checked={summaryDialogSampleAll}
              onChange={(event) =>
                setSummaryDialogSampleAll(event.currentTarget.checked)
              }
            />
            Alle verfügbaren Beispiele je Cluster verwenden.
          </label>
          {summaryDialogUsesOpenAi && (
            <label className="inline-check">
              <input
                type="checkbox"
                checked={summaryDialogCloudUseConfirmed}
                onChange={(event) =>
                  setSummaryDialogCloudUseConfirmed(event.currentTarget.checked)
                }
              />
              OpenAI-Übertragung für diese Aktion bestätigen.
            </label>
          )}
          {summaryDialogError !== null && (
            <div className="status error" role="alert">
              {summaryDialogError}
            </div>
          )}
          {summaryDialogProvider === null || summaryDialogModel === "" ? (
            <p className="status warning" role="status">
              Für die Summary-Neuerstellung ist kein aktiver LLM-Provider mit
              Modell verfügbar.
            </p>
          ) : null}
          <div className="form-actions">
            <button
              type="button"
              onClick={() =>
                void regenerateClusterSetSummaries(
                  activeSummaryDialogClusterSet,
                  "dialog",
                )
              }
              disabled={!summaryDialogCanStart}
            >
              {clusterSetSummaryRequestId === activeSummaryDialogClusterSet.id
                ? "Summaries werden gestartet"
                : "Summary-Job starten"}
            </button>
            <button
              type="button"
              className="secondary"
              onClick={closeSummaryRegenerationDialog}
            >
              Abbrechen
            </button>
          </div>
        </section>
      </div>
    );

  if (isSessionChecking) {
    return (
      <>
        {feedbackOverlay}
        <main className="auth-shell">
          <section className="auth-card" aria-label="Sitzungsprüfung">
            <p className="eyebrow">Support Knowledge Miner</p>
            <p role="status" className="intro">
              Gespeicherte Sitzung wird geprüft.
            </p>
          </section>
        </main>
      </>
    );
  }

  if (session === null) {
    return (
      <>
        {feedbackOverlay}
        <main className="auth-shell">
          <section className="auth-card" aria-labelledby="signin-title">
            <p className="eyebrow">Support Knowledge Miner</p>
            <h1 id="signin-title">Lokaler Zugriff</h1>
            <p className="intro">
              Geschützte Projekt-, Import- und Kurationsbereiche starten erst
              nach erfolgreicher Backend-Anmeldung. Fehler nennen nie, ob E-Mail
              oder Passwort falsch war.
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
          </section>
        </main>
      </>
    );
  }

  return (
    <>
      {feedbackOverlay}
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
            <div className="global-menu">
              <button
                type="button"
                className="icon-button global-menu-button"
                aria-label="Hauptmenü öffnen"
                aria-haspopup="menu"
                aria-expanded={globalMenuOpen}
                aria-controls="global-menu-overlay"
                ref={globalMenuButtonRef}
                onClick={() => setGlobalMenuOpen((open) => !open)}
              >
                <span aria-hidden="true">☰</span>
              </button>
              {globalMenuOpen && (
                <div
                  id="global-menu-overlay"
                  className="global-menu-overlay"
                  role="menu"
                  ref={globalMenuRef}
                >
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => navigateFromGlobalMenu("projects")}
                  >
                    Projekte
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => navigateFromGlobalMenu("settings")}
                  >
                    Einstellungen
                  </button>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => navigateFromGlobalMenu("signout")}
                  >
                    Abmelden
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        <div className="workspace">
          <section className="content">
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
                      ["settings", "Einstellungen"],
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
                    Provider
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

            {activePage === "settings" && settingsTab === "providers" && (
              <section id="providers" className="provider-settings">
                <section className="panel provider-add-row">
                  <div>
                    <p className="eyebrow">Provider</p>
                    <h2>Provider verwalten</h2>
                    <p className="hint">
                      Verbindung, API-Key und Modellfreigaben werden hier
                      zentral pro Provider-Instanz gepflegt.
                    </p>
                  </div>
                  <div className="inline-form">
                    <label>
                      Basistyp
                      <select
                        value={newProviderType}
                        onChange={(event) =>
                          setNewProviderType(
                            event.target.value as ConfigurableProvider,
                          )
                        }
                      >
                        <option value="openai">OpenAI</option>
                        <option value="ollama">Ollama</option>
                      </select>
                    </label>
                    <button type="button" onClick={() => void addProvider()}>
                      Provider hinzufügen
                    </button>
                  </div>
                </section>

                <section className="provider-grid">
                  {providers.length === 0 && (
                    <section className="panel provider-card stack">
                      <h2>Noch kein Provider eingerichtet</h2>
                      <p className="hint">
                        Füge OpenAI oder Ollama hinzu, um Modelle für
                        Indizierung und Cluster-Set-Summaries bereitzustellen.
                      </p>
                    </section>
                  )}
                  {providers.map((provider) => {
                    const embeddingModels = embeddingModelOptions(provider);
                    const llmModels = llmModelOptions(provider);
                    return (
                      <form
                        key={provider.id}
                        className="panel provider-card stack"
                        onSubmit={(event) => configureProvider(event, provider)}
                        aria-label={`${provider.displayName} Provider konfigurieren`}
                      >
                        <div className="panel-title">
                          <div>
                            <p className="eyebrow">
                              {provider.provider === "openai"
                                ? "Cloud"
                                : "Lokal"}{" "}
                              ·{" "}
                              {provider.provider === "openai"
                                ? "OpenAI"
                                : "Ollama"}
                            </p>
                            <h2>{provider.displayName}</h2>
                          </div>
                          <button
                            type="button"
                            className="danger"
                            onClick={() => void deleteProvider(provider)}
                          >
                            Entfernen
                          </button>
                        </div>
                        <label>
                          Anzeigename
                          <input
                            name="displayName"
                            defaultValue={provider.displayName}
                            required
                          />
                        </label>
                        {provider.provider === "openai" ? (
                          <>
                            <label className="provider-key-row">
                              OpenAI API-Key
                              <input
                                name="apiKey"
                                type="password"
                                autoComplete="off"
                                placeholder={
                                  provider.apiKeySet
                                    ? "•••••••• gespeichert"
                                    : "sk-..."
                                }
                              />
                            </label>
                            <label className="inline-check">
                              <input name="removeApiKey" type="checkbox" />
                              Gespeicherten API-Key entfernen
                            </label>
                          </>
                        ) : (
                          <label>
                            Endpoint URL
                            <input
                              name="endpointUrl"
                              defaultValue={provider.endpointUrl ?? ""}
                              placeholder="http://localhost:11434"
                            />
                          </label>
                        )}

                        <div className="model-selection">
                          <span className="field-caption">
                            Embedding-Modelle
                          </span>
                          {embeddingModels.length === 0 && (
                            <p className="hint">
                              Noch keine Modelle abgerufen.
                            </p>
                          )}
                          {embeddingModels.map((model) => (
                            <label
                              className="inline-check"
                              key={`${provider.id}:embedding:${model}`}
                            >
                              <input
                                type="checkbox"
                                checked={provider.manualModels.includes(model)}
                                onChange={(event) =>
                                  toggleProviderModel(
                                    provider.id,
                                    "embedding",
                                    model,
                                    event.target.checked,
                                  )
                                }
                              />
                              {model}
                            </label>
                          ))}
                        </div>

                        <div className="model-selection">
                          <span className="field-caption">LLM-Modelle</span>
                          {llmModels.length === 0 && (
                            <p className="hint">
                              Noch keine Modelle abgerufen.
                            </p>
                          )}
                          {llmModels.map((model) => (
                            <label
                              className="inline-check"
                              key={`${provider.id}:llm:${model}`}
                            >
                              <input
                                type="checkbox"
                                checked={provider.llmModels.includes(model)}
                                onChange={(event) =>
                                  toggleProviderModel(
                                    provider.id,
                                    "llm",
                                    model,
                                    event.target.checked,
                                  )
                                }
                              />
                              {model}
                            </label>
                          ))}
                        </div>

                        <div className="form-actions">
                          <button type="submit">Provider speichern</button>
                          <button
                            type="button"
                            className="secondary"
                            onClick={() =>
                              void testProviderConnection(provider)
                            }
                          >
                            Verbindung testen
                          </button>
                          <button
                            type="button"
                            className="secondary"
                            onClick={() =>
                              void discoverProviderModels(provider)
                            }
                          >
                            Modelle abrufen
                          </button>
                        </div>
                        <p className="hint">
                          Verbindungstest und Modellabruf nutzen die zuletzt
                          gespeicherte Provider-Konfiguration.
                        </p>

                        {provider.provider === "ollama" && (
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
                              disabled={ollamaPullProviderId !== null}
                              onClick={(event) => {
                                const form =
                                  event.currentTarget.closest("form");
                                if (form !== null) {
                                  void pullOllamaModel(provider, form);
                                }
                              }}
                            >
                              {ollamaPullProviderId === provider.id
                                ? "Download läuft ..."
                                : "Herunterladen und hinzufügen"}
                            </button>
                          </div>
                        )}
                      </form>
                    );
                  })}
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
                        Cluster-Parameter werden erst im nächsten Schritt
                        gewählt.
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
                          name="providerId"
                          value={indexingProviderId}
                          onChange={(event) => {
                            setIndexingProviderId(event.target.value);
                            setCloudUseConfirmed(false);
                          }}
                        >
                          {embeddingProviders.length === 0 && (
                            <option value="">Kein Provider verfügbar</option>
                          )}
                          {embeddingProviders.map((provider) => (
                            <option key={provider.id} value={provider.id}>
                              {provider.displayName} ·{" "}
                              {provider.provider === "openai"
                                ? "OpenAI"
                                : "Ollama"}
                            </option>
                          ))}
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
                          : `${indexingProviderModels.length} Modell(e) für ${indexingProviderConfiguration?.displayName ?? "Provider"} verfügbar.`}
                      </p>
                      <fieldset className="parameter-group">
                        <legend>Text-Normalisierung für Embeddings</legend>
                        <p className="hint">
                          Originaltexte bleiben unverändert. Die Normalisierung
                          gilt nur für den Text, der an den Embedding-Provider
                          gesendet wird.
                        </p>
                        <label className="inline-check">
                          <input
                            name="removeLineBreaks"
                            type="checkbox"
                            checked={removeIndexingLineBreaks}
                            onChange={(event) => {
                              setRemoveIndexingLineBreaks(event.target.checked);
                              if (event.target.checked) {
                                setReplaceIndexingLineBreaks(false);
                              }
                            }}
                          />
                          Zeilenumbrüche entfernen
                        </label>
                        <label className="inline-check">
                          <input
                            name="replaceLineBreaks"
                            type="checkbox"
                            checked={replaceIndexingLineBreaks}
                            onChange={(event) => {
                              setReplaceIndexingLineBreaks(
                                event.target.checked,
                              );
                              if (event.target.checked) {
                                setRemoveIndexingLineBreaks(false);
                              }
                            }}
                          />
                          Zeilenumbrüche ersetzen durch
                        </label>
                        <label>
                          Ersatzzeichen für Zeilenumbrüche
                          <input
                            name="lineBreakReplacement"
                            value={indexingLineBreakReplacement}
                            maxLength={16}
                            disabled={!replaceIndexingLineBreaks}
                            onChange={(event) =>
                              setIndexingLineBreakReplacement(
                                event.target.value,
                              )
                            }
                          />
                        </label>
                        <label className="inline-check">
                          <input
                            name="lowercaseEmbeddingInput"
                            type="checkbox"
                            checked={lowercaseIndexingInput}
                            onChange={(event) =>
                              setLowercaseIndexingInput(event.target.checked)
                            }
                          />
                          Text in Kleinschreibung umwandeln
                        </label>
                      </fieldset>
                      {indexingProviderConfiguration?.provider === "openai" && (
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
                          (indexingProviderConfiguration?.provider ===
                            "openai" &&
                            !cloudUseConfirmed)
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
                          <article
                            className="user-card indexing-card"
                            key={run.id}
                          >
                            <div className="user-heading">
                              <strong>{run.status}</strong>
                              <span>{run.progress}%</span>
                            </div>
                            <progress value={run.progress} max={100}>
                              {run.progress}%
                            </progress>
                            <p className="hint">Phase: {run.phase}</p>
                            <p className="hint">
                              Provider/Modell:{" "}
                              {run.providerDisplayName ?? run.provider}/
                              {run.model}
                            </p>
                            <p className="hint">
                              Datensatz: {run.datasetDisplayName ?? "-"};
                              Version: {run.datasetVersionId}
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
                            <p className="hint diagnostics-text">
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
                          <p>{clusterSetRefinementDraft.description}.</p>
                          <p>
                            <strong>Zu verfeinerndes Cluster-Set:</strong>{" "}
                            {clusterSetRefinementDraft.parentClusterSetName}
                          </p>
                          <p className="hint">
                            Parent-ID:{" "}
                            {clusterSetRefinementDraft.parentClusterSetId}
                          </p>
                          <p className="hint">Ausgewählte Cluster:</p>
                          <ul className="compact-list">
                            {clusterSetRefinementDraft.sources
                              .slice(0, 5)
                              .map((source) => (
                                <li key={source.id}>
                                  {source.title} · {source.label}
                                  {source.isOutlier ? " · Ausreißer" : ""}
                                </li>
                              ))}
                          </ul>
                          {clusterSetRefinementDraft.sources.length > 5 && (
                            <p className="hint">
                              +{clusterSetRefinementDraft.sources.length - 5}{" "}
                              weitere ausgewählte Parent-Cluster.
                            </p>
                          )}
                          <input
                            type="hidden"
                            name="indexingRunId"
                            value={clusterSetRefinementDraft.indexingRunId}
                          />
                          <label>
                            Verfeinerungsmodus
                            <select
                              name="refinementMode"
                              value={clusterSetRefinementMode}
                              onChange={(event) =>
                                setClusterSetRefinementMode(event.target.value)
                              }
                            >
                              <option value="common">
                                Gemeinsam neu clustern
                              </option>
                              <option value="per_parent">
                                Separat je Parent-Cluster
                              </option>
                            </select>
                          </label>
                          <button
                            type="button"
                            className="secondary"
                            onClick={() => {
                              setClusterSetRefinementDraft(null);
                              setClusterSetRefinementMode("common");
                            }}
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
                                {run.datasetDisplayName ?? run.datasetVersionId}{" "}
                                / {run.model}
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
                      <label>
                        Algorithmus
                        <select
                          name="clusterAlgorithm"
                          value={clusterSetAlgorithm}
                          onChange={(event) =>
                            setClusterSetAlgorithm(event.target.value)
                          }
                        >
                          <option value="hdbscan">HDBSCAN</option>
                          <option value="agglomerative">Agglomerative</option>
                        </select>
                      </label>
                      {clusterSetAlgorithm === "hdbscan" ? (
                        <>
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
                          <div className="inline-form">
                            <label>
                              Dimensionsreduzierung
                              <select
                                name="reductionMethod"
                                value={clusterSetReductionMethod}
                                onChange={(event) =>
                                  setClusterSetReductionMethod(
                                    event.target.value,
                                  )
                                }
                              >
                                <option value="none">Keine</option>
                                <option value="pca">PCA vor HDBSCAN</option>
                                <option value="umap">UMAP vor HDBSCAN</option>
                              </select>
                            </label>
                            <label>
                              Ziel-Dimensionen
                              <input
                                name="reductionDimensions"
                                type="number"
                                min="2"
                                max="512"
                                defaultValue="10"
                                disabled={clusterSetReductionMethod === "none"}
                              />
                            </label>
                            <label>
                              Backend
                              <select
                                name="executionBackend"
                                value={clusterSetExecutionBackend}
                                onChange={(event) =>
                                  setClusterSetExecutionBackend(
                                    event.target.value,
                                  )
                                }
                              >
                                <option value="auto">
                                  Auto (cuML wenn verfügbar)
                                </option>
                                <option value="cpu">CPU/sklearn</option>
                                <option value="cuml">GPU/cuML erzwingen</option>
                              </select>
                            </label>
                          </div>
                          {clusterSetReductionMethod === "umap" && (
                            <div className="inline-form">
                              <label>
                                UMAP n_neighbors
                                <input
                                  name="umapNeighbors"
                                  type="number"
                                  min="2"
                                  max="512"
                                  defaultValue="15"
                                />
                              </label>
                              <label>
                                UMAP min_dist
                                <input
                                  name="umapMinDist"
                                  type="number"
                                  min="0"
                                  max="0.99"
                                  step="0.01"
                                  defaultValue="0"
                                />
                              </label>
                            </div>
                          )}
                        </>
                      ) : (
                        <>
                          <div className="inline-form">
                            <label>
                              Agglomerative Schnittregel
                              <select
                                name="agglomerativeSplitRule"
                                value={clusterSetAgglomerativeSplitRule}
                                onChange={(event) =>
                                  setClusterSetAgglomerativeSplitRule(
                                    event.target.value,
                                  )
                                }
                              >
                                <option value="n_clusters">
                                  Feste Clusteranzahl
                                </option>
                                <option value="distance_threshold">
                                  Distanzschwelle
                                </option>
                              </select>
                            </label>
                            {clusterSetAgglomerativeSplitRule ===
                            "distance_threshold" ? (
                              <label>
                                distance_threshold
                                <input
                                  name="distanceThreshold"
                                  type="number"
                                  min="0"
                                  step="0.01"
                                  required
                                />
                              </label>
                            ) : (
                              <label>
                                n_clusters
                                <input
                                  name="nClusters"
                                  type="number"
                                  min="1"
                                  defaultValue="2"
                                  required
                                />
                              </label>
                            )}
                            <label>
                              Linkage
                              <select name="linkage" defaultValue="ward">
                                <option value="ward">ward</option>
                                <option value="complete">complete</option>
                                <option value="average">average</option>
                                <option value="single">single</option>
                              </select>
                            </label>
                          </div>
                        </>
                      )}
                      <label>
                        LLM-Zusammenfassung
                        <select
                          name="llmProviderId"
                          value={clusterSetLlmProviderId}
                          onChange={(event) =>
                            setClusterSetLlmProviderId(event.target.value)
                          }
                        >
                          <option value="">Keine Zusammenfassung</option>
                          {llmProviders.map((provider) => (
                            <option key={provider.id} value={provider.id}>
                              {provider.displayName} ·{" "}
                              {provider.provider === "openai"
                                ? "OpenAI"
                                : "Ollama"}
                            </option>
                          ))}
                        </select>
                      </label>
                      {clusterSetLlmProviderId !== "" && (
                        <>
                          <label>
                            LLM-Modell
                            <select
                              name="llmModel"
                              required
                              disabled={
                                clusterSetLlmProviderModels.length === 0
                              }
                            >
                              {clusterSetLlmProviderModels.length === 0 && (
                                <option value="">
                                  Keine Modelle verfügbar
                                </option>
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
                      {clusterSetLlmProviderConfiguration?.provider ===
                        "openai" && (
                        <label className="confirmation-field">
                          <input
                            name="llmCloudUseConfirmed"
                            type="checkbox"
                            checked={clusterSetCloudUseConfirmed}
                            onChange={(event) =>
                              setClusterSetCloudUseConfirmed(
                                event.target.checked,
                              )
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
                          (clusterSetLlmProviderId !== "" &&
                            clusterSetLlmProviderModels.length === 0) ||
                          (clusterSetLlmProviderConfiguration?.provider ===
                            "openai" &&
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
                      <div
                        className="batch-toolbar"
                        aria-label="Cluster-Set Batch-Aktionen"
                      >
                        <span>{selectedClusterSetIds.length} ausgewählt</span>
                        <label className="cluster-set-actions-select">
                          Aktionen
                          <select
                            aria-label="Aktionen"
                            value=""
                            disabled={
                              selectedClusterSetIds.length === 0 ||
                              clusterSetBatchDeleteInProgress
                            }
                            onChange={(event) => {
                              if (event.target.value === "delete") {
                                void batchDeleteClusterSets();
                              }
                            }}
                          >
                            <option value="">
                              {clusterSetBatchDeleteInProgress
                                ? "Löschen läuft"
                                : "Aktion wählen"}
                            </option>
                            <option value="delete">Löschen</option>
                          </select>
                        </label>
                      </div>
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
                      </div>

                      {loadedClusterSet === null ? (
                        <p className="hint">
                          Noch kein abgeschlossenes Cluster-Set geladen. Wähle
                          im Tab „Cluster-Sets“ einen fertigen Satz aus.
                        </p>
                      ) : (
                        <div
                          className={`explorer-workspace-grid ${
                            explorerRailCollapsed
                              ? "explorer-workspace-grid-collapsed"
                              : ""
                          }`}
                        >
                          <aside
                            className={`explorer-rail ${
                              explorerRailCollapsed
                                ? "explorer-rail-collapsed"
                                : ""
                            }`}
                            aria-label="Explorer Kontrollleiste"
                          >
                            <div className="explorer-rail-header">
                              {!explorerRailCollapsed && (
                                <strong>Kontrollleiste</strong>
                              )}
                              <button
                                type="button"
                                className="secondary icon-button explorer-rail-toggle"
                                aria-label={
                                  explorerRailCollapsed
                                    ? "Kontrollleiste ausklappen"
                                    : "Kontrollleiste einklappen"
                                }
                                title={
                                  explorerRailCollapsed
                                    ? "Kontrollleiste ausklappen"
                                    : "Kontrollleiste einklappen"
                                }
                                aria-expanded={!explorerRailCollapsed}
                                aria-controls="explorer-rail-content"
                                onClick={() =>
                                  setExplorerRailCollapsed(
                                    (collapsed) => !collapsed,
                                  )
                                }
                              >
                                <span aria-hidden="true">
                                  {explorerRailCollapsed ? "›" : "‹"}
                                </span>
                              </button>
                            </div>
                            <div
                              id="explorer-rail-content"
                              className="explorer-rail-content"
                              hidden={explorerRailCollapsed}
                            >
                              <section
                                className="rail-group"
                                aria-label="Cluster-Set Auswahl"
                              >
                                <h3>Cluster-Set</h3>
                                <label>
                                  Geladenes Set
                                  <select
                                    value={loadedClusterSet.id}
                                    onChange={(event) => {
                                      if (
                                        session === null ||
                                        currentProject === null
                                      ) {
                                        return;
                                      }
                                      void loadClusterSetClusters(
                                        session.token,
                                        currentProject.id,
                                        event.target.value,
                                      );
                                    }}
                                  >
                                    {explorerClusterSetOptions.map(
                                      ({ clusterSet, depth }) => (
                                        <option
                                          key={clusterSet.id}
                                          value={clusterSet.id}
                                        >
                                          {"— ".repeat(depth)}
                                          {clusterSet.displayName}
                                        </option>
                                      ),
                                    )}
                                  </select>
                                </label>
                                <button
                                  type="button"
                                  className="secondary"
                                  onClick={() => setProjectTab("cluster-sets")}
                                >
                                  Cluster-Sets verwalten
                                </button>
                              </section>

                              <section
                                className="rail-group"
                                aria-label="Explorer Filter"
                              >
                                <h3>Suche & Filter</h3>
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
                                      setClusterCategoryFilter(
                                        event.target.value,
                                      )
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
                                      setClusterGroupByCategory(
                                        event.target.checked,
                                      )
                                    }
                                  />
                                  Nach Kategorie gruppieren
                                </label>
                                <label className="inline-check">
                                  <input
                                    type="checkbox"
                                    checked={showExcludedClusters}
                                    onChange={(event) =>
                                      setShowExcludedClusters(
                                        event.target.checked,
                                      )
                                    }
                                  />
                                  Ausgeschlossene anzeigen
                                </label>
                                <label className="inline-check">
                                  <input
                                    type="checkbox"
                                    checked={includeOutlierRows}
                                    onChange={(event) =>
                                      setIncludeOutlierRows(
                                        event.target.checked,
                                      )
                                    }
                                  />
                                  Ausreißer in Tabelle anzeigen
                                </label>
                              </section>

                              <section
                                className="rail-group"
                                aria-label="Explorer Verfeinerung"
                              >
                                <h3>Verfeinerung</h3>
                                <p className="hint">
                                  Nutzt die aktuell sichtbaren eingeschlossenen
                                  Cluster als Quelle für ein neues
                                  Child-Cluster-Set.
                                </p>
                                <button
                                  type="button"
                                  onClick={
                                    createRefinementDraftFromVisibleClusters
                                  }
                                >
                                  Eingeschlossene Cluster verfeinern
                                </button>
                              </section>

                              <section
                                className="rail-group"
                                aria-label="Ausreißer ausschließen"
                              >
                                <h3>Ausreißer</h3>
                                <p className="hint">
                                  Erstellt ein neues Child-Cluster-Set.
                                </p>
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
                                  onClick={() =>
                                    void createOutlierExclusionSet()
                                  }
                                >
                                  Ausreißer berechnen
                                </button>
                              </section>

                              <section
                                className="rail-group"
                                aria-label="Explorer Summary"
                              >
                                <h3>Summary</h3>
                                <p className="hint">
                                  Ersetzt die aktuellen Summary-Felder dieses
                                  Cluster-Sets. Versions- und Kopie-Modi sind
                                  nicht aktiv.
                                </p>
                                {explorerSummaryError !== null && (
                                  <div className="status error" role="alert">
                                    {explorerSummaryError}
                                  </div>
                                )}
                                <button
                                  type="button"
                                  disabled={
                                    !canRegenerateLoadedClusterSetSummaries ||
                                    clusterSetSummaryRequestId ===
                                      loadedClusterSet.id
                                  }
                                  onClick={(event) =>
                                    openSummaryRegenerationDialog(
                                      loadedClusterSet,
                                      event.currentTarget,
                                    )
                                  }
                                >
                                  {clusterSetSummaryRequestId ===
                                  loadedClusterSet.id
                                    ? "Summaries werden gestartet"
                                    : "Summaries neu erstellen"}
                                </button>
                                {!canRegenerateLoadedClusterSetSummaries && (
                                  <p className="hint">
                                    Für dieses Cluster-Set ist kein aktiver
                                    LLM-Provider hinterlegt.
                                  </p>
                                )}
                              </section>

                              {clusters.length > 0 && (
                                <section
                                  className="rail-group"
                                  aria-label="Explorer Export"
                                >
                                  <h3>Export</h3>
                                  <p className="hint">
                                    Exportiert die aktuelle gefilterte
                                    Explorer-Tabelle ohne Originaltexte aus dem
                                    Quellen-Dialog.
                                  </p>
                                  {explorerExportError !== null && (
                                    <div
                                      className="status error stack"
                                      role="alert"
                                    >
                                      <strong>
                                        Explorer-Export fehlgeschlagen.
                                      </strong>
                                      <p>{explorerExportError}</p>
                                      <p className="hint">
                                        Filter und Format bleiben erhalten.
                                        Bitte Eingaben anpassen oder den Export
                                        erneut starten.
                                      </p>
                                    </div>
                                  )}
                                  <form
                                    className="stack"
                                    onSubmit={createExplorerExport}
                                  >
                                    <label>
                                      Format
                                      <select
                                        value={explorerExportFormat}
                                        onChange={(event) =>
                                          setExplorerExportFormat(
                                            event.target
                                              .value as ExplorerExportFormat,
                                          )
                                        }
                                      >
                                        <option value="csv">CSV</option>
                                        <option value="json">JSON</option>
                                      </select>
                                    </label>
                                    <button
                                      type="submit"
                                      disabled={visibleClusters.length === 0}
                                    >
                                      Aktuelle Tabelle exportieren
                                    </button>
                                  </form>
                                  <section aria-label="Exporthistorie">
                                    <h3>Exporthistorie</h3>
                                    <div className="user-list">
                                      {visibleExportLogs.length === 0 && (
                                        <p className="hint">
                                          Noch keine Explorer-Exporte für dieses
                                          Projekt.
                                        </p>
                                      )}
                                      {visibleExportLogs.map((log) => (
                                        <article
                                          className="user-card"
                                          key={log.id}
                                        >
                                          <div className="user-heading">
                                            <strong>
                                              {log.outputFilename}
                                            </strong>
                                            <span>{log.exportType}</span>
                                          </div>
                                          <p className="hint">
                                            Zeilen: {log.rowCount}; Cluster-Set:{" "}
                                            {log.clusterSetId ?? "-"}
                                          </p>
                                          <p className="hint">
                                            Erstellt: {log.createdAt}
                                          </p>
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
                              )}
                            </div>
                          </aside>

                          <div
                            className="explorer-table-workspace"
                            ref={explorerTableWorkspaceRef}
                          >
                            <div
                              className="metric-grid"
                              aria-label="Explorer Kennzahlen"
                            >
                              <div>
                                <span className="field-caption">
                                  Geladenes Set
                                </span>
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
                              className="cluster-set-parameter-card"
                              aria-label="Cluster-Set Parameter"
                            >
                              <span className="field-caption">
                                Cluster-Set Parameter
                              </span>
                              <dl className="parameter-list">
                                {clusterSetParameterEntries(
                                  loadedClusterSet,
                                ).map((entry) => (
                                  <div key={entry.key}>
                                    <dt>{entry.label}</dt>
                                    <dd>{entry.value}</dd>
                                  </div>
                                ))}
                              </dl>
                              <section
                                className="cluster-set-summary-block"
                                aria-label="Cluster-Set Statistik"
                              >
                                <span className="field-caption">
                                  Cluster-Set Statistik
                                </span>
                                <dl className="parameter-list parameter-list-compact">
                                  <div>
                                    <dt>Gesamt</dt>
                                    <dd>
                                      {formatClusterAndPairCount(
                                        explorerClusterSummary.totalClusters,
                                        explorerClusterSummary.totalMessagePairCount,
                                      )}
                                    </dd>
                                  </div>
                                  <div>
                                    <dt>Nicht rejected</dt>
                                    <dd>
                                      {formatClusterAndPairCount(
                                        explorerClusterSummary.activeClusters,
                                        explorerClusterSummary.activeMessagePairCount,
                                      )}
                                    </dd>
                                  </div>
                                  <div>
                                    <dt>Rejected</dt>
                                    <dd>
                                      {formatClusterAndPairCount(
                                        explorerClusterSummary.rejectedClusters,
                                        explorerClusterSummary.rejectedMessagePairCount,
                                      )}
                                    </dd>
                                  </div>
                                  {explorerClusterSummary.statusEntries.map(
                                    (entry) => (
                                      <div key={entry.status}>
                                        <dt>Status: {entry.label}</dt>
                                        <dd>
                                          {formatClusterAndPairCount(
                                            entry.clusterCount,
                                            entry.messagePairCount,
                                          )}
                                        </dd>
                                      </div>
                                    ),
                                  )}
                                </dl>
                                {explorerClusterSummary.statusEntries.length ===
                                  0 && (
                                  <p className="hint">
                                    Keine Statuswerte vorhanden.
                                  </p>
                                )}
                              </section>
                            </section>

                            {clusters.length > 0 &&
                              visibleClusters.length === 0 && (
                                <p className="status info" role="status">
                                  {
                                    ERROR_MESSAGES_BY_CODE.CLUSTER_SEARCH_NO_RESULTS
                                  }
                                </p>
                              )}

                            <div className="cluster-table-wrap" tabIndex={0}>
                              <table className="cluster-table">
                                <thead>
                                  <tr>
                                    {renderSortableClusterHeader(
                                      "status",
                                      "Status",
                                    )}
                                    {renderSortableClusterHeader(
                                      "title",
                                      "Titel",
                                    )}
                                    {renderSortableClusterHeader(
                                      "category",
                                      "Kategorie",
                                    )}
                                    <th>Frage</th>
                                    <th>Antwort</th>
                                    {renderSortableClusterHeader(
                                      "customerQuestions",
                                      "Kundenanfragen",
                                    )}
                                    {renderSortableClusterHeader(
                                      "supportAnswers",
                                      "Supportantworten",
                                    )}
                                    {renderSortableClusterHeader(
                                      "hintsScore",
                                      "Hinweise / Score",
                                    )}
                                    <th>Aktionen</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {includedClusterGroups.map((group) => (
                                    <Fragment key={group.key}>
                                      {(clusterGroupByCategory ||
                                        hasPerParentOriginGrouping) && (
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
                                  <div
                                    className="cluster-table-wrap"
                                    tabIndex={0}
                                  >
                                    <table className="cluster-table">
                                      <tbody>
                                        {visibleExcludedClusters.map(
                                          (cluster) =>
                                            renderClusterTableRow(cluster),
                                        )}
                                      </tbody>
                                    </table>
                                  </div>
                                )}
                              </section>
                            )}
                          </div>
                          <button
                            type="button"
                            className="icon-button scroll-to-top"
                            aria-label="Nach oben scrollen"
                            title="Nach oben scrollen"
                            onClick={scrollExplorerToTop}
                          >
                            <span aria-hidden="true">↑</span>
                          </button>
                        </div>
                      )}
                    </section>

                    {sourceDialogCluster !== null && (
                      <div
                        className="dialog-backdrop"
                        onClick={(event) => {
                          if (event.target === event.currentTarget) {
                            closeSourceDialog();
                          }
                        }}
                      >
                        <section
                          className="source-dialog"
                          role="dialog"
                          aria-modal="true"
                          aria-labelledby="source-dialog-title"
                          ref={sourceDialogRef}
                        >
                          <div className="panel-title source-dialog-header">
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
                                <div
                                  className="status error stack"
                                  role="alert"
                                >
                                  <strong>
                                    Weitere Quellen konnten nicht geladen
                                    werden.
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
                                      {renderSourceTicketLabel(source)}
                                    </strong>
                                    <p>Kundenfrage: {source.message}</p>
                                    <p>Supportantwort: {source.answer}</p>
                                    <p className="hint">
                                      Score:{" "}
                                      {formatScore(source.membershipScore)};
                                      Assignment: {source.assignmentType}
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
                                    onClick={() =>
                                      void loadMoreClusterSources()
                                    }
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
                              Importdatum:{" "}
                              {formatProjectUpdatedAt(log.startedAt)}
                            </p>
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
                            {log.skippedDetailCount > 0 ? (
                              <button
                                type="button"
                                className="secondary"
                                onClick={() => inspectImportLog(log.id)}
                              >
                                Logdetails anzeigen
                              </button>
                            ) : (
                              <p className="hint">
                                Keine Validierungsdetails vorhanden.
                              </p>
                            )}
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

                {currentProject && projectTab === "settings" && (
                  <section
                    className="panel-grid"
                    aria-label="Projekteinstellungen"
                  >
                    <form
                      key={`${currentProject.id}:${currentProject.name}:${currentProject.ticketUrlTemplate ?? ""}`}
                      className="panel project-settings-form stack"
                      onSubmit={(event) =>
                        void updateProjectSettings(event, currentProject.id)
                      }
                      aria-label="Projekteinstellungen speichern"
                    >
                      <div>
                        <p className="eyebrow">Einstellungen</p>
                        <h2>Projekt bearbeiten</h2>
                        <p className="hint">
                          Ändere den Projektnamen und optional die
                          Ticket-Link-Vorlage für Quellen im Explorer.
                        </p>
                      </div>
                      {projectSettingsError !== null && (
                        <div className="status error" role="alert">
                          {projectSettingsError}
                        </div>
                      )}
                      <label>
                        Projektname
                        <input
                          name="projectName"
                          defaultValue={currentProject.name}
                          aria-invalid={
                            projectSettingsFieldErrors.projectName !== undefined
                          }
                          aria-describedby={
                            projectSettingsFieldErrors.projectName !== undefined
                              ? "project-name-error"
                              : undefined
                          }
                          required
                        />
                      </label>
                      {projectSettingsFieldErrors.projectName !== undefined && (
                        <p
                          id="project-name-error"
                          className="field-error"
                          role="alert"
                        >
                          {projectSettingsFieldErrors.projectName}
                        </p>
                      )}
                      <label>
                        Ticket-Link-Vorlage
                        <input
                          name="ticketUrlTemplate"
                          defaultValue={currentProject.ticketUrlTemplate ?? ""}
                          placeholder="https://tickets.example.test/<ticket_id>"
                          aria-invalid={
                            projectSettingsFieldErrors.ticket_url_template !==
                            undefined
                          }
                          aria-describedby={
                            projectSettingsFieldErrors.ticket_url_template !==
                            undefined
                              ? "ticket-url-template-help ticket-url-template-error"
                              : "ticket-url-template-help"
                          }
                        />
                      </label>
                      <p id="ticket-url-template-help" className="hint">
                        Leer lassen, um Ticket-Links zu deaktivieren. Erlaubt
                        sind absolute http(s)-URLs mit genauem Platzhalter{" "}
                        <code>{"<ticket_id>"}</code>; die Anwendung prüft keine
                        Erreichbarkeit.
                      </p>
                      {projectSettingsFieldErrors.ticket_url_template !==
                        undefined && (
                        <p
                          id="ticket-url-template-error"
                          className="field-error"
                          role="alert"
                        >
                          {projectSettingsFieldErrors.ticket_url_template}
                        </p>
                      )}
                      <button
                        type="submit"
                        className="primary"
                        disabled={isProjectSettingsSaving}
                      >
                        {isProjectSettingsSaving
                          ? "Einstellungen werden gespeichert"
                          : "Einstellungen speichern"}
                      </button>
                    </form>

                    <form
                      className="panel stack danger-panel"
                      onSubmit={(event) =>
                        deleteProject(event, currentProject.id)
                      }
                      aria-label="Projekt löschen"
                    >
                      <div>
                        <p className="eyebrow">Gefahrenbereich</p>
                        <h2>Projekt löschen</h2>
                        <p className="hint">
                          Löscht das Projekt dauerhaft. Zur Bestätigung muss der
                          Projektname exakt eingegeben werden.
                        </p>
                      </div>
                      {projectDeleteError !== null && (
                        <div className="status error" role="alert">
                          {projectDeleteError}
                        </div>
                      )}
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

            {summaryRegenerationDialog}

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
    </>
  );
}

export default App;
