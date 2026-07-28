import { createHash } from "node:crypto";

export const SOURCE_NORMALIZATION_VERSION = "source-text-v1";

export class SourceRevisionStoreError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "SourceRevisionStoreError";
    this.code = code;
  }
}

export function normalizeExtractedSourceText(value) {
  return String(value ?? "")
    .replace(/\r\n?/g, "\n")
    // eslint-disable-next-line no-control-regex -- source normalization removes unsafe controls.
    .replace(/[\x00-\x08\x0b-\x0c\x0e-\x1f]/g, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function sourceTextSha256(text) {
  return createHash("sha256").update(text, "utf8").digest("hex");
}

export function createSupabaseSourceRevisionStore({
  supabaseUrl = process.env.SUPABASE_URL,
  publishableKey = process.env.SUPABASE_PUBLISHABLE_KEY,
  accessToken,
  fetchImpl = globalThis.fetch,
} = {}) {
  const baseUrl = validatedSupabaseUrl(supabaseUrl);
  const apiKey = String(publishableKey || "").trim();
  const userToken = String(accessToken || "").trim();
  if (!apiKey) {
    throw new SourceRevisionStoreError(
      "SourceStoreConfigurationError",
      "source storage requires a Supabase publishable key",
    );
  }
  if (!userToken) {
    throw new SourceRevisionStoreError(
      "SourceAuthenticationRequired",
      "source storage requires an authenticated user token",
    );
  }
  if (isServiceRoleKey(apiKey)) {
    throw new SourceRevisionStoreError(
      "SourceStoreConfigurationError",
      "source storage must use a Supabase publishable key",
    );
  }
  if (typeof fetchImpl !== "function") {
    throw new SourceRevisionStoreError(
      "SourceStoreConfigurationError",
      "source storage requires fetch",
    );
  }

  async function request(path, options = {}) {
    let response;
    try {
      response = await fetchImpl(`${baseUrl}/rest/v1${path}`, {
        ...options,
        signal: options.signal || AbortSignal.timeout(10_000),
        headers: {
          apikey: apiKey,
          authorization: `Bearer ${userToken}`,
          "content-type": "application/json",
          ...(options.headers || {}),
        },
      });
    } catch {
      throw new SourceRevisionStoreError(
        "SourceStoreUnavailable",
        "source storage is unavailable",
      );
    }

    let text;
    try {
      text = await response.text();
    } catch {
      throw new SourceRevisionStoreError(
        "SourceStoreUnavailable",
        "source storage response failed",
      );
    }
    const body = text ? safeJson(text) : null;
    if (response.ok) return body;
    if (response.status === 401 || response.status === 403) {
      throw new SourceRevisionStoreError(
        "SourceAuthenticationRequired",
        "source storage rejected the user session",
      );
    }
    if (response.status === 409) {
      throw new SourceRevisionStoreError(
        "SourceIdempotencyConflict",
        "idempotency key was already used for different source content",
      );
    }
    throw new SourceRevisionStoreError(
      "SourceStoreUnavailable",
      "source storage request failed",
    );
  }

  async function intake(input) {
    const payload = normalizeIntake(input);
    const checksum = sourceTextSha256(payload.normalizedText);
    const result = await request("/rpc/intake_source_revision", {
      method: "POST",
      body: JSON.stringify({
        p_idempotency_key: payload.idempotencyKey,
        p_normalized_text: payload.normalizedText,
        p_checksum_sha256: checksum,
        p_normalization_version: payload.normalizationVersion,
        p_extraction_version: payload.extractionVersion,
        p_parser_version: payload.parserVersion,
        p_source_kind: payload.sourceKind,
        p_provenance: payload.provenance,
      }),
    });
    return normalizeReference(result);
  }

  async function read(revisionId) {
    const id = requiredUuid(revisionId, "revisionId");
    const query = new URLSearchParams({
      select:
        "source_id,revision_id,normalized_text,checksum_sha256,normalization_version,extraction_version,parser_version,source_kind,provenance,erased_at",
      revision_id: `eq.${id}`,
      limit: "1",
    });
    const rows = await request(`/source_revisions?${query}`);
    const row = Array.isArray(rows) ? rows[0] : null;
    if (!row?.normalized_text || row.erased_at) {
      throw new SourceRevisionStoreError(
        "SourceUnavailable",
        "source revision is unavailable",
      );
    }
    const reference = normalizeReference({
      sourceId: row.source_id,
      revisionId: row.revision_id,
      checksumSha256: row.checksum_sha256,
      normalizationVersion: row.normalization_version,
      extractionVersion: row.extraction_version,
      parserVersion: row.parser_version,
      sourceKind: row.source_kind,
      provenance: row.provenance,
    });
    if (sourceTextSha256(row.normalized_text) !== reference.checksumSha256) {
      throw new SourceRevisionStoreError(
        "SourceUnavailable",
        "source revision integrity check failed",
      );
    }
    return { ...reference, normalizedText: row.normalized_text };
  }

  async function erase(revisionId) {
    const result = await request("/rpc/erase_source_revision", {
      method: "POST",
      body: JSON.stringify({
        p_revision_id: requiredUuid(revisionId, "revisionId"),
      }),
    });
    return { erased: result?.erased === true };
  }

  return { intake, read, erase };
}

function normalizeIntake(input) {
  if (!input || typeof input !== "object") {
    throw new SourceRevisionStoreError(
      "InvalidSourceIntake",
      "source intake payload is required",
    );
  }
  const normalizedText = normalizeExtractedSourceText(input.normalizedText);
  if (!normalizedText) {
    throw new SourceRevisionStoreError(
      "InvalidSourceIntake",
      "normalized source text is required",
    );
  }
  if (Buffer.byteLength(normalizedText, "utf8") > 65_536) {
    throw new SourceRevisionStoreError(
      "SourceTooLarge",
      "normalized source text is too large",
    );
  }
  const sourceKind = String(input.sourceKind || "");
  if (!["paste", "txt", "md", "pdf"].includes(sourceKind)) {
    throw new SourceRevisionStoreError(
      "InvalidSourceIntake",
      "source kind is invalid",
    );
  }
  const provenance = input.provenance;
  if (!provenance || typeof provenance !== "object" || Array.isArray(provenance)) {
    throw new SourceRevisionStoreError(
      "InvalidSourceIntake",
      "source provenance object is required",
    );
  }
  const expectedProvenance = {
    intake_surface: "promoted-alpha-file-intake",
    input_method: sourceKind === "paste" ? "paste" : "file",
  };
  if (
    Object.keys(provenance).length !== 2
    || provenance.intake_surface !== expectedProvenance.intake_surface
    || provenance.input_method !== expectedProvenance.input_method
  ) {
    throw new SourceRevisionStoreError(
      "InvalidSourceIntake",
      "source provenance is invalid",
    );
  }
  const requestedNormalizationVersion = String(input.normalizationVersion || "");
  if (requestedNormalizationVersion !== SOURCE_NORMALIZATION_VERSION) {
    throw new SourceRevisionStoreError(
      "InvalidSourceIntake",
      "source normalization version is invalid",
    );
  }
  return {
    idempotencyKey: requiredUuid(input.idempotencyKey, "idempotencyKey"),
    normalizedText,
    normalizationVersion: SOURCE_NORMALIZATION_VERSION,
    extractionVersion:
      requiredString(input.extractionVersion, "extractionVersion"),
    parserVersion: requiredString(input.parserVersion, "parserVersion"),
    sourceKind,
    provenance: expectedProvenance,
  };
}

function normalizeReference(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new SourceRevisionStoreError(
      "SourceStoreUnavailable",
      "source storage returned invalid reference data",
    );
  }
  const checksumSha256 = String(value.checksumSha256 || "");
  if (!/^[0-9a-f]{64}$/.test(checksumSha256)) {
    throw new SourceRevisionStoreError(
      "SourceStoreUnavailable",
      "source storage returned an invalid checksum",
    );
  }
  return {
    sourceId: requiredUuid(value.sourceId, "sourceId"),
    revisionId: requiredUuid(value.revisionId, "revisionId"),
    checksumSha256,
    normalizationVersion:
      requiredString(value.normalizationVersion, "normalizationVersion"),
    extractionVersion:
      requiredString(value.extractionVersion, "extractionVersion"),
    parserVersion: requiredString(value.parserVersion, "parserVersion"),
    sourceKind: requiredString(value.sourceKind, "sourceKind"),
    provenance: value.provenance || {},
    replayed: value.replayed === true,
    deduplicated: value.deduplicated === true,
  };
}

function validatedSupabaseUrl(value) {
  const raw = String(value || "").trim().replace(/\/+$/, "");
  let parsed;
  try {
    parsed = new URL(raw);
  } catch {
    throw new SourceRevisionStoreError(
      "SourceStoreConfigurationError",
      "source storage requires a valid Supabase URL",
    );
  }
  if (parsed.protocol !== "https:" || parsed.pathname !== "/") {
    throw new SourceRevisionStoreError(
      "SourceStoreConfigurationError",
      "source storage requires a Supabase HTTPS origin",
    );
  }
  return parsed.origin;
}

function requiredUuid(value, field) {
  const text = String(value || "").trim();
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(text)) {
    throw new SourceRevisionStoreError(
      "InvalidSourceIntake",
      `${field} must be a UUID`,
    );
  }
  return text;
}

function requiredString(value, field) {
  const text = String(value || "").trim();
  if (!text) {
    throw new SourceRevisionStoreError(
      "InvalidSourceIntake",
      `${field} is required`,
    );
  }
  return text;
}

function safeJson(text) {
  try {
    return JSON.parse(text);
  } catch {
    throw new SourceRevisionStoreError(
      "SourceStoreUnavailable",
      "source storage returned an invalid response",
    );
  }
}

function isServiceRoleKey(key) {
  if (key.startsWith("sb_secret_")) return true;
  const parts = key.split(".");
  if (parts.length !== 3) return false;
  try {
    const payload = JSON.parse(Buffer.from(parts[1], "base64url").toString("utf8"));
    return payload?.role === "service_role";
  } catch {
    return false;
  }
}
