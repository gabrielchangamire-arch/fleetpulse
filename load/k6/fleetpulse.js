import http from "k6/http";
import { check } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";

const mode = __ENV.MODE || "read";
const rate = Number.parseInt(__ENV.RATE || "20", 10);
const duration = __ENV.DURATION || "10s";
const baseUrl = __ENV.BASE_URL || "https://localhost:8443";
const token = __ENV.TOKEN;
const runId = __ENV.RUN_ID || "manual";

if (!token) {
  throw new Error("TOKEN is required");
}
if (!["read", "ingest"].includes(mode)) {
  throw new Error(`unsupported MODE: ${mode}`);
}

const endpointLatency = new Trend("fleetpulse_endpoint_latency", true);
const endpointErrors = new Rate("fleetpulse_endpoint_errors");
const endpointRequests = new Counter("fleetpulse_endpoint_requests");
const cacheHits = new Counter("fleetpulse_cache_hits");

export const options = {
  insecureSkipTLSVerify: true,
  scenarios: {
    fleetpulse: {
      executor: "constant-arrival-rate",
      rate,
      timeUnit: "1s",
      duration,
      preAllocatedVUs: Math.max(10, Math.ceil(rate / 2)),
      maxVUs: Math.max(50, rate * 2),
    },
  },
  summaryTrendStats: ["avg", "min", "med", "max", "p(90)", "p(95)", "p(99)"],
};

function uuidV4() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (character) => {
    const random = Math.floor(Math.random() * 16);
    const value = character === "x" ? random : (random & 0x3) | 0x8;
    return value.toString(16);
  });
}

function telemetryBatch() {
  const sequence = `${__VU}-${__ITER}`;
  return {
    schema_version: 1,
    batch_id: uuidV4(),
    agent_id: `k6-agent-${runId}-${__VU}`.slice(0, 128),
    hostname: `k6-host-${sequence}`.slice(0, 255),
    samples: [
      {
        observed_at: new Date().toISOString(),
        cpu_percent: 42,
        load_1m: 0.4,
        load_5m: 0.3,
        load_15m: 0.2,
        memory: {
          total_bytes: 1073741824,
          available_bytes: 536870912,
          used_bytes: 536870912,
          used_percent: 50,
        },
        disks: [
          {
            mount: "/",
            total_bytes: 1073741824,
            used_bytes: 536870912,
            free_bytes: 536870912,
            used_percent: 50,
          },
        ],
        network: {
          bytes_sent: 1000,
          bytes_received: 2000,
          packets_sent: 10,
          packets_received: 20,
          errors_in: 0,
          errors_out: 0,
          drops_in: 0,
          drops_out: 0,
          tcp_established: 2,
          tcp_listening: 1,
          tcp_other: 0,
          udp_sockets: 1,
        },
        process_count: 10,
        top_processes: [],
      },
    ],
  };
}

export default function () {
  const headers = {
    Authorization: `Bearer ${token}`,
    "X-Request-ID": `k6-${runId}-${__VU}-${__ITER}`,
  };
  const response =
    mode === "read"
      ? http.get(`${baseUrl}/v1/fleet/state`, { headers, tags: { endpoint: "fleet_state" } })
      : http.post(`${baseUrl}/v1/telemetry/batches`, JSON.stringify(telemetryBatch()), {
          headers: { ...headers, "Content-Type": "application/json" },
          tags: { endpoint: "telemetry_ingest" },
        });

  const expectedStatus = mode === "read" ? 200 : 202;
  const valid = check(response, {
    "expected HTTP status": (result) => result.status === expectedStatus,
    "correlation ID returned": (result) => Boolean(result.headers["X-Request-Id"]),
  });
  endpointLatency.add(response.timings.duration, { mode });
  endpointErrors.add(!valid, { mode });
  endpointRequests.add(1, { mode });
  if (mode === "read" && response.headers["X-Cache"] === "HIT") {
    cacheHits.add(1);
  }
}
