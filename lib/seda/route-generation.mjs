import {
  isRetryableRouteError,
  routeRetryEvent,
} from "../bridge/client.mjs";
import {
  invalidBridgeError,
  resultToBridgeError,
  validateRoutePayload,
} from "./bridge-fail-closed.mjs";

const ROUTE_ATTEMPT_TIMEOUT_MS = 25_000;

export async function generateRouteWithRetry({
  callBridgeResult,
  concept,
  learnerGoal,
  launchAttempt,
  substrateAdequacy = "adequate",
  logRawLlm,
  events,
  section,
}) {
  const retryReasons = [];
  const maxAttempts = 2;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const result = await callBridgeResult(
      "generate-route",
      {
        concept,
        learner_goal: learnerGoal || null,
        launch_attempt: launchAttempt,
        substrate_adequacy: substrateAdequacy,
        log_raw_llm: logRawLlm,
        route_attempt: attempt,
        route_retry_reason: retryReasons.at(-1)?.message || null,
      },
      // Two route attempts must complete inside the 55 second HTTP proxy read
      // window, including process startup and response serialization.
      { timeoutMs: ROUTE_ATTEMPT_TIMEOUT_MS },
    );
    if (result.ok) {
      const invalid = validateRoutePayload(result.payload);
      if (invalid) {
        return {
          route: null,
          retryReasons,
          bridgeError: invalidBridgeError({
            action: "generate-route",
            phase: "route",
            reason: invalid,
          }),
        };
      }
      return {
        route: result.payload,
        retryReasons,
        bridgeError: null,
      };
    }
    if (!isRetryableRouteError(result) || attempt === maxAttempts) {
      if (isRetryableRouteError(result)) {
        retryReasons.push({
          attempt,
          error: result.error || "route_generation_failed",
          message: result.message || "",
        });
      }
      return {
        route: null,
        retryReasons,
        bridgeError: resultToBridgeError({
          result,
          action: "generate-route",
          phase: "route",
          retryable: isRetryableRouteError(result),
          attempts: attempt,
        }),
      };
    }
    const event = routeRetryEvent(result, attempt);
    retryReasons.push({
      attempt,
      error: event.error,
      message: event.message,
    });
    events.push(event);
    console.log(
      `${section("route", "Route Retry")} ${event.error}: ${event.message}`,
    );
  }
  return {
    route: null,
    retryReasons,
    bridgeError: resultToBridgeError({
      result: {
        error: "route-generation-failed",
        message: "route generation failed",
      },
      action: "generate-route",
      phase: "route",
      attempts: maxAttempts,
    }),
  };
}
