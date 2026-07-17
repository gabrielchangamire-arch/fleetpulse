"""Bounded-cardinality Prometheus metrics."""

from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS = Counter(
    "fleetpulse_http_requests_total", "HTTP requests", ["method", "route", "status"]
)
HTTP_LATENCY = Histogram(
    "fleetpulse_http_request_duration_seconds", "HTTP request duration", ["method", "route"]
)
INGESTION = Counter("fleetpulse_ingestion_batches_total", "Ingestion outcomes", ["status"])
WORKER_EVENTS = Counter("fleetpulse_worker_events_total", "Worker event outcomes", ["status"])
OUTBOX_PUBLISHED = Counter("fleetpulse_outbox_published_total", "Published outbox events")
QUEUE_PENDING = Gauge("fleetpulse_queue_pending", "Pending Redis Stream events")
CACHE_REQUESTS = Counter("fleetpulse_cache_requests_total", "Fleet cache outcomes", ["status"])
