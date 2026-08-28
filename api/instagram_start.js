"use strict";

const crypto = require("crypto");

const LOGIN_PATH = "/Login";
const MAX_FORM_BODY_BYTES = 2048;
const FORM_CONTENT_TYPE = "application/x-www-form-urlencoded";
const REQUIRED_CONSENT_FIELDS = new Set([
  "age_confirmed",
  "terms_accepted",
  "privacy_accepted",
  "instagram_permissions_accepted",
]);
const CONSENT_BINDING_COOKIE_NAME = "cl_consent_binding";
const CONSENT_BINDING_MAX_AGE_SECONDS = 600;
const CONSENT_BINDING_VERSION = 1;
const STATE_TTL_SECONDS = 600;
const STATE_VERSION = 1;
const TERMS_VERSION = "influencer-v1.2-2026-08-26";
const PRIVACY_VERSION = "privacy-2026-08-26-v3";
const INSTAGRAM_PERMISSIONS_VERSION = "instagram-permissions-2026-08-26";
const INSTAGRAM_AUTH_URL = "https://www.instagram.com";
const INSTAGRAM_SCOPE =
  "instagram_business_basic,instagram_business_manage_insights";

function handler(req, res) {
  handleRequest(req)
    .then((result) => sendResponse(res, result))
    .catch(() =>
      sendResponse(res, redirect(loginErrorLocation("configuration_error"))),
    );
}

async function handleRequest(req) {
  const method = String(req.method || "").toUpperCase();
  const headers = normalizeHeaders(req.headers || {});

  if (method !== "POST") {
    return {
      statusCode: 405,
      headers: {
        allow: "POST",
        "content-type": "text/plain; charset=utf-8",
      },
      body: "Method Not Allowed",
    };
  }

  if (
    hasDuplicateHeader(req.rawHeaders || [], "content-length") ||
    !validContentLength(headers["content-length"])
  ) {
    return redirect(loginErrorLocation("invalid_request"));
  }
  if (!hasFormContentType(headers["content-type"] || "")) {
    return redirect(loginErrorLocation("invalid_request"));
  }
  if (!sameOriginRequest(headers, "https")) {
    return redirect(loginErrorLocation("invalid_request"));
  }

  const body = await readBoundedBody(req, MAX_FORM_BODY_BYTES);
  if (body === null || !validConsentForm(body)) {
    return redirect(loginErrorLocation("invalid_request"));
  }

  if (validateRuntime().length) {
    return redirect(loginErrorLocation("configuration_error"));
  }

  const binding = createBindingToken(process.env.SESSION_COOKIE_SECRET);
  const consent = acceptedNow();
  const oauthUrl = getOAuthUrl(consent, binding.bindingId);
  return redirect(oauthUrl, {
    "set-cookie": buildBindingCookie(binding.token),
  });
}

function sendResponse(res, result) {
  const headers = result.headers || {};
  if (typeof res.status === "function") {
    res.status(result.statusCode);
  } else {
    res.statusCode = result.statusCode;
  }
  for (const [key, value] of Object.entries(headers)) {
    if (typeof res.setHeader === "function") {
      res.setHeader(key, value);
    }
  }
  if (typeof res.end === "function") {
    res.end(result.body || "");
  }
}

function redirect(location, extraHeaders = {}) {
  return {
    statusCode: 303,
    headers: {
      location,
      "cache-control": "no-store",
      "referrer-policy": "no-referrer",
      ...extraHeaders,
    },
    body: "",
  };
}

function loginErrorLocation(code) {
  return `${LOGIN_PATH}?step=consent&auth_error=${code}`;
}

function normalizeHeaders(headers) {
  const normalized = {};
  for (const [key, value] of Object.entries(headers)) {
    normalized[String(key).toLowerCase()] = Array.isArray(value)
      ? value.join(",")
      : String(value);
  }
  return normalized;
}

function hasDuplicateHeader(rawHeaders, headerName) {
  let count = 0;
  for (let index = 0; index < rawHeaders.length; index += 2) {
    if (String(rawHeaders[index]).toLowerCase() === headerName) {
      count += 1;
    }
  }
  return count > 1;
}

function validContentLength(value) {
  if (value === undefined || value === "") {
    return true;
  }
  if (!/^(0|[1-9][0-9]*)$/.test(value)) {
    return false;
  }
  return Number(value) <= MAX_FORM_BODY_BYTES;
}

function hasFormContentType(contentType) {
  return contentType.split(";", 1)[0].trim().toLowerCase() === FORM_CONTENT_TYPE;
}

function sameOriginRequest(headers, scheme) {
  const host = headers.host || "";
  if (!host) {
    return false;
  }

  const expectedOrigin = `${scheme}://${host}`;
  if ((headers["sec-fetch-site"] || "") === "cross-site") {
    return false;
  }

  const origin = headers.origin || "";
  if (origin) {
    return origin === expectedOrigin;
  }

  return urlOrigin(headers.referer || "") === expectedOrigin;
}

function urlOrigin(value) {
  try {
    const parsed = new URL(value);
    if (!["http:", "https:"].includes(parsed.protocol) || !parsed.host) {
      return null;
    }
    return `${parsed.protocol}//${parsed.host}`;
  } catch {
    return null;
  }
}

function readBoundedBody(req, maxBytes) {
  if (Buffer.isBuffer(req.body)) {
    return Promise.resolve(req.body.length <= maxBytes ? req.body : null);
  }
  if (typeof req.body === "string") {
    const body = Buffer.from(req.body, "utf8");
    return Promise.resolve(body.length <= maxBytes ? body : null);
  }
  if (req.body && typeof req.body === "object") {
    const body = bodyFromParsedForm(req.body);
    return Promise.resolve(body && body.length <= maxBytes ? body : null);
  }

  return new Promise((resolve, reject) => {
    const chunks = [];
    let total = 0;
    let overflowed = false;
    req.on("data", (chunk) => {
      const buffer = Buffer.from(chunk);
      total += buffer.length;
      if (total > maxBytes) {
        overflowed = true;
        return;
      }
      chunks.push(buffer);
    });
    req.on("end", () => resolve(overflowed ? null : Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

function bodyFromParsedForm(body) {
  const keys = Object.keys(body);
  if (keys.length !== REQUIRED_CONSENT_FIELDS.size) {
    return null;
  }

  const pairs = [];
  for (const key of keys.sort()) {
    const value = body[key];
    if (
      !REQUIRED_CONSENT_FIELDS.has(key) ||
      Array.isArray(value) ||
      value !== "true"
    ) {
      return null;
    }
    pairs.push(`${encodeURIComponent(key)}=${encodeURIComponent(value)}`);
  }
  return Buffer.from(pairs.join("&"), "ascii");
}

function validConsentForm(body) {
  if (!body || body.length > MAX_FORM_BODY_BYTES || !isAscii(body)) {
    return false;
  }
  const raw = body.toString("ascii");
  const pairs = raw.split("&");
  if (pairs.length !== REQUIRED_CONSENT_FIELDS.size) {
    return false;
  }

  const seen = new Set();
  for (const pair of pairs) {
    const separatorIndex = pair.indexOf("=");
    if (separatorIndex <= 0) {
      return false;
    }
    const key = decodeFormComponent(pair.slice(0, separatorIndex));
    const value = decodeFormComponent(pair.slice(separatorIndex + 1));
    if (
      key === null ||
      value === null ||
      seen.has(key) ||
      !REQUIRED_CONSENT_FIELDS.has(key) ||
      value !== "true"
    ) {
      return false;
    }
    seen.add(key);
  }
  return seen.size === REQUIRED_CONSENT_FIELDS.size;
}

function isAscii(buffer) {
  for (const byte of buffer.values()) {
    if (byte > 0x7f) {
      return false;
    }
  }
  return true;
}

function decodeFormComponent(value) {
  try {
    return decodeURIComponent(value.replace(/\+/g, " "));
  } catch {
    return null;
  }
}

function validateRuntime() {
  const errors = [];
  for (const key of [
    "INSTAGRAM_APP_ID",
    "INSTAGRAM_APP_SECRET",
    "OAUTH_REDIRECT_URI",
    "CONTACT_EMAIL",
    "SUPABASE_URL",
    "SUPABASE_KEY",
  ]) {
    if (!process.env[key]) {
      errors.push(key);
    }
  }

  if (!envFlag("VERCEL")) {
    return errors;
  }
  if (Buffer.byteLength(process.env.SESSION_COOKIE_SECRET || "", "utf8") < 32) {
    errors.push("SESSION_COOKIE_SECRET (minimum 32 bytes)");
  }
  if (vercelOAuthRedirectError(process.env.OAUTH_REDIRECT_URI || "")) {
    errors.push("OAUTH_REDIRECT_URI (Vercel must be https://<host>/auth/callback)");
  }
  if (!["secret", "service_role"].includes(supabaseKeyKind(process.env.SUPABASE_KEY || ""))) {
    errors.push("SUPABASE_KEY (secret/service_role required)");
  }
  if ((process.env.VERCEL_ENV || "").toLowerCase() === "preview") {
    errors.push(...validatePreviewSupabaseProject());
  }
  return errors;
}

function envFlag(name) {
  const value = process.env[name];
  return value !== undefined && ["1", "true", "yes", "on"].includes(value.trim().toLowerCase());
}

function vercelOAuthRedirectError(uri) {
  try {
    const parsed = new URL(uri);
    return !(
      parsed.protocol === "https:" &&
      parsed.host &&
      parsed.pathname === "/auth/callback" &&
      !parsed.search &&
      !parsed.hash
    );
  } catch {
    return true;
  }
}

function validatePreviewSupabaseProject() {
  if (envFlag("ALLOW_SHARED_SUPABASE_IN_PREVIEW")) {
    return supabaseProjectUrlError(process.env.SUPABASE_URL || "")
      ? ["SUPABASE_URL (must be https://<project-ref>.supabase.co)"]
      : [];
  }

  const errors = [];
  const previewRef = (process.env.SUPABASE_PREVIEW_PROJECT_REF || "").trim();
  const productionRef = (process.env.SUPABASE_PRODUCTION_PROJECT_REF || "").trim();
  if (!previewRef) {
    errors.push("SUPABASE_PREVIEW_PROJECT_REF");
  }
  if (!productionRef) {
    errors.push("SUPABASE_PRODUCTION_PROJECT_REF");
  }
  if (previewRef && productionRef && previewRef === productionRef) {
    errors.push("SUPABASE_PREVIEW_PROJECT_REF (must differ from production)");
  }
  if (previewRef && process.env.SUPABASE_URL) {
    try {
      const host = new URL(process.env.SUPABASE_URL).hostname || "";
      if (host !== `${previewRef}.supabase.co`) {
        errors.push("SUPABASE_URL (Vercel Preview must use preview Supabase project)");
      }
    } catch {
      errors.push("SUPABASE_URL (Vercel Preview must use preview Supabase project)");
    }
  }
  return errors;
}

function supabaseProjectUrlError(uri) {
  try {
    const parsed = new URL(uri);
    const host = parsed.hostname || "";
    const projectRef = host.endsWith(".supabase.co")
      ? host.slice(0, -".supabase.co".length)
      : "";
    return !(
      parsed.protocol === "https:" &&
      parsed.host &&
      ["", "/"].includes(parsed.pathname) &&
      !parsed.search &&
      !parsed.hash &&
      !parsed.port &&
      !parsed.username &&
      !parsed.password &&
      host.endsWith(".supabase.co") &&
      projectRef &&
      !projectRef.includes(".")
    );
  } catch {
    return true;
  }
}

function supabaseKeyKind(key) {
  if (key.startsWith("sb_secret_")) {
    return "secret";
  }
  if (key.startsWith("sb_publishable_")) {
    return "publishable";
  }

  const parts = key.split(".");
  if (parts.length !== 3) {
    return "unknown";
  }
  try {
    const payload = JSON.parse(base64urlDecode(parts[1]).toString("utf8"));
    return typeof payload.role === "string" ? payload.role : "unknown";
  } catch {
    return "unknown";
  }
}

function createBindingToken(secret) {
  const issuedAt = Math.floor(Date.now() / 1000);
  const bindingId = randomBase64Url(24);
  const payload = {
    bid: bindingId,
    exp: issuedAt + CONSENT_BINDING_MAX_AGE_SECONDS,
    iat: issuedAt,
    v: CONSENT_BINDING_VERSION,
  };
  const payloadPart = base64urlEncode(Buffer.from(stableJson(payload), "utf8"));
  const signaturePart = base64urlEncode(sign(Buffer.from(payloadPart, "ascii"), secret));
  return {
    bindingId,
    token: `${payloadPart}.${signaturePart}`,
  };
}

function buildBindingCookie(token) {
  return (
    `${CONSENT_BINDING_COOKIE_NAME}=${token}; ` +
    `Max-Age=${CONSENT_BINDING_MAX_AGE_SECONDS}; Path=/; ` +
    "SameSite=Lax; Secure; HttpOnly"
  );
}

function acceptedNow() {
  return {
    accepted_at: new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00"),
    age_confirmed: true,
    instagram_permissions_accepted: true,
    instagram_permissions_version: INSTAGRAM_PERMISSIONS_VERSION,
    privacy_accepted: true,
    privacy_version: PRIVACY_VERSION,
    terms_accepted: true,
    terms_version: TERMS_VERSION,
  };
}

function getOAuthUrl(consent, bindingId) {
  const state = generateState(consent, bindingId);
  const params = new URLSearchParams({
    client_id: process.env.INSTAGRAM_APP_ID || "",
    redirect_uri: process.env.OAUTH_REDIRECT_URI || "",
    state,
    scope: INSTAGRAM_SCOPE,
    response_type: "code",
  });
  return `${INSTAGRAM_AUTH_URL}/oauth/authorize?${params.toString()}`;
}

function generateState(consent, bindingId) {
  const now = Math.floor(Date.now() / 1000);
  const payload = {
    accepted_at: consent.accepted_at,
    age_confirmed: true,
    binding_id: bindingId,
    iat: now,
    instagram_permissions_accepted: true,
    instagram_permissions_version: INSTAGRAM_PERMISSIONS_VERSION,
    nonce: randomBase64Url(16),
    privacy_accepted: true,
    privacy_version: PRIVACY_VERSION,
    terms_accepted: true,
    terms_version: TERMS_VERSION,
    v: STATE_VERSION,
  };
  payload.bundle_hash = consentBundleHash(payload);
  const payloadBytes = Buffer.from(stableJson(payload), "utf8");
  return `${base64urlEncode(payloadBytes)}.${base64urlEncode(sign(payloadBytes, process.env.INSTAGRAM_APP_SECRET))}`;
}

function consentBundleHash(payload) {
  const consentItems = {};
  for (const key of Object.keys(payload)) {
    if (!["iat", "nonce", "binding_id", "bundle_hash"].includes(key)) {
      consentItems[key] = payload[key];
    }
  }
  return crypto
    .createHash("sha256")
    .update(stableJson(consentItems), "utf8")
    .digest("hex");
}

function sign(message, secret) {
  if (Buffer.byteLength(secret || "", "utf8") < 32) {
    throw new Error("secret must be at least 32 bytes");
  }
  return crypto.createHmac("sha256", Buffer.from(secret, "utf8")).update(message).digest();
}

function randomBase64Url(byteLength) {
  return base64urlEncode(crypto.randomBytes(byteLength));
}

function base64urlEncode(buffer) {
  return Buffer.from(buffer)
    .toString("base64")
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");
}

function base64urlDecode(value) {
  const padding = "=".repeat((4 - (value.length % 4)) % 4);
  return Buffer.from(`${value}${padding}`.replace(/-/g, "+").replace(/_/g, "/"), "base64");
}

function stableJson(value) {
  if (Array.isArray(value)) {
    return `[${value.map(stableJson).join(",")}]`;
  }
  if (value && typeof value === "object") {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${stableJson(value[key])}`)
      .join(",")}}`;
  }
  return JSON.stringify(value);
}

module.exports = handler;
module.exports._private = {
  MAX_FORM_BODY_BYTES,
  bodyFromParsedForm,
  handleRequest,
  stableJson,
  validConsentForm,
  validateRuntime,
};
