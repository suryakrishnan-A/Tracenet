/**
 * Error Serialization and Context Sanitization.
 */

const SENSITIVE_KEY_SUBSTRINGS = [
  "password",
  "secret",
  "token",
  "authorization",
  "api_key",
  "apikey",
  "cookie",
  "access_token",
  "private_key",
];

const MAX_MESSAGE_CHARS = 10000;
const MAX_STACK_CHARS = 100000;

export function formatError(error: unknown): { message: string; stackTrace?: string } {
  if (error instanceof Error) {
    const name = error.name || "Error";
    const msg = error.message ? `${name}: ${error.message}` : name;
    return {
      message: msg.slice(0, MAX_MESSAGE_CHARS),
      stackTrace: error.stack ? error.stack.slice(0, MAX_STACK_CHARS) : undefined,
    };
  }

  if (typeof error === "string") {
    return {
      message: error.slice(0, MAX_MESSAGE_CHARS),
    };
  }

  try {
    const stringified = JSON.stringify(error);
    return {
      message: `[Non-Error Object]: ${stringified}`.slice(0, MAX_MESSAGE_CHARS),
    };
  } catch {
    return {
      message: `[Unserializable Error]: ${String(error)}`.slice(0, MAX_MESSAGE_CHARS),
    };
  }
}

export function sanitizeMetadata(
  metadata?: Record<string, unknown>,
  maxBytes: number = 32768
): Record<string, unknown> {
  if (!metadata || typeof metadata !== "object") {
    return {};
  }

  const sanitized: Record<string, unknown> = {};

  for (const [key, val] of Object.entries(metadata)) {
    const lowerKey = key.toLowerCase();
    if (SENSITIVE_KEY_SUBSTRINGS.some((sub) => lowerKey.includes(sub))) {
      sanitized[key] = "[REDACTED]";
    } else {
      sanitized[key] = makeJsonSafe(val);
    }
  }

  try {
    const serialized = JSON.stringify(sanitized);
    if (new TextEncoder().encode(serialized).length > maxBytes) {
      return {
        _warning: `Metadata payload exceeded ${maxBytes} bytes and was pruned.`,
        keys: Object.keys(sanitized).slice(0, 10),
      };
    }
  } catch {
    return { _error: "Failed to serialize metadata" };
  }

  return sanitized;
}

function makeJsonSafe(value: unknown, depth = 0): unknown {
  if (depth > 5) return String(value);
  if (value === null || value === undefined) return value;
  if (typeof value === "boolean" || typeof value === "number" || typeof value === "string") {
    return value;
  }
  if (value instanceof Date) {
    return value.toISOString();
  }
  if (Array.isArray(value)) {
    return value.map((item) => makeJsonSafe(item, depth + 1));
  }
  if (typeof value === "object") {
    const obj: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value)) {
      obj[k] = makeJsonSafe(v, depth + 1);
    }
    return obj;
  }
  return String(value);
}
