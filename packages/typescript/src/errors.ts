/**
 * Custom Error Hierarchies for TraceNest SDK.
 */

export class TraceNestError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "TraceNestError";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class TraceNestConfigError extends TraceNestError {
  constructor(message: string) {
    super(message);
    this.name = "TraceNestConfigError";
  }
}

export class TraceNestDeliveryError extends TraceNestError {
  public readonly statusCode?: number;
  public readonly responseBody?: string;
  public readonly retryAfter?: number;

  constructor(
    message: string,
    options?: { statusCode?: number; responseBody?: string; retryAfter?: number }
  ) {
    super(message);
    this.name = "TraceNestDeliveryError";
    this.statusCode = options?.statusCode;
    this.responseBody = options?.responseBody;
    this.retryAfter = options?.retryAfter;
  }
}

export class TraceNestRateLimitError extends TraceNestDeliveryError {
  constructor(message: string, retryAfter: number, responseBody?: string) {
    super(message, { statusCode: 429, responseBody, retryAfter });
    this.name = "TraceNestRateLimitError";
  }
}
