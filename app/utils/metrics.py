from prometheus_client import Counter, Histogram

# Counters for tracking API calls
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP Requests", ["method", "endpoint", "status"]
)

# Histogram for request latency
REQUEST_LATENCY = Histogram(
    "http_request_latency_seconds", "Latency of HTTP requests in seconds", ["endpoint"]
)


def record_metrics(method: str, endpoint: str, status: str, latency: float):
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
    REQUEST_LATENCY.labels(endpoint=endpoint).observe(latency)
