"""Lightweight, thread-safe Prometheus metrics instrumentation engine.

Implements standard Prometheus exposition format (0.0.4) with zero external network dependencies:
- Counter: Monotonically increasing metric with multidimensional labels.
- Gauge: Instantaneous value metric supporting set, inc, and dec.
- Histogram: Configurable bucketed distribution tracking latencies with sum and count.
- MetricsRegistry: Central registry exporting formatted metrics to Prometheus scrapers.
"""

from collections import defaultdict
import threading
import time
from typing import Dict, List, Tuple, Optional, Any


class Metric:
    """Base class for Prometheus metrics with label dimensions."""

    def __init__(self, name: str, description: str, label_names: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self.label_names = tuple(label_names or [])
        self._lock = threading.Lock()

    def _format_labels(self, labels: Dict[str, str]) -> str:
        """Format dictionary labels to Prometheus key-value string: {k1="v1",k2="v2"}."""
        if not labels:
            return ""
        pairs = [f'{k}="{v}"' for k, v in sorted(labels.items())]
        return "{" + ",".join(pairs) + "}"


class Counter(Metric):
    """Cumulative metric that represents a single monotonically increasing counter."""

    def __init__(self, name: str, description: str, label_names: Optional[List[str]] = None):
        super().__init__(name, description, label_names)
        self._values: Dict[Tuple[Tuple[str, str], ...], float] = defaultdict(float)

    def labels(self, **kwargs) -> "Counter":
        """Bind label key-values."""
        return _BoundCounter(self, kwargs)

    def inc(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment counter by non-negative amount."""
        if amount < 0:
            raise ValueError("Counters can only be incremented by non-negative values.")
        key = tuple(sorted((k, str(v)) for k, v in (labels or {}).items()))
        with self._lock:
            self._values[key] += amount

    def get_value(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Retrieve current value for specific label combination."""
        key = tuple(sorted((k, str(v)) for k, v in (labels or {}).items()))
        with self._lock:
            return self._values[key]

    def render(self) -> List[str]:
        """Render counter to Prometheus exposition format lines."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} counter",
        ]
        with self._lock:
            if not self._values and not self.label_names:
                lines.append(f"{self.name} 0.0")
            else:
                for label_tuples, val in sorted(self._values.items()):
                    lbl_str = self._format_labels(dict(label_tuples))
                    lines.append(f"{self.name}{lbl_str} {val}")
        return lines


class _BoundCounter:
    """Helper proxy for Counter with pre-bound labels."""

    def __init__(self, parent: Counter, labels: Dict[str, str]):
        self.parent = parent
        self.labels = labels

    def inc(self, amount: float = 1.0) -> None:
        self.parent.inc(amount, labels=self.labels)


class Gauge(Metric):
    """Metric that represents a single numerical value that can arbitrarily go up and down."""

    def __init__(self, name: str, description: str, label_names: Optional[List[str]] = None):
        super().__init__(name, description, label_names)
        self._values: Dict[Tuple[Tuple[str, str], ...], float] = defaultdict(float)

    def labels(self, **kwargs) -> "Gauge":
        """Bind label key-values."""
        return _BoundGauge(self, kwargs)

    def set(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set gauge to exact value."""
        key = tuple(sorted((k, str(v)) for k, v in (labels or {}).items()))
        with self._lock:
            self._values[key] = float(value)

    def inc(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment gauge."""
        key = tuple(sorted((k, str(v)) for k, v in (labels or {}).items()))
        with self._lock:
            self._values[key] += float(amount)

    def dec(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Decrement gauge."""
        key = tuple(sorted((k, str(v)) for k, v in (labels or {}).items()))
        with self._lock:
            self._values[key] -= float(amount)

    def get_value(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Retrieve current gauge value."""
        key = tuple(sorted((k, str(v)) for k, v in (labels or {}).items()))
        with self._lock:
            return self._values[key]

    def render(self) -> List[str]:
        """Render gauge to Prometheus exposition format lines."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} gauge",
        ]
        with self._lock:
            if not self._values and not self.label_names:
                lines.append(f"{self.name} 0.0")
            else:
                for label_tuples, val in sorted(self._values.items()):
                    lbl_str = self._format_labels(dict(label_tuples))
                    lines.append(f"{self.name}{lbl_str} {val}")
        return lines


class _BoundGauge:
    """Helper proxy for Gauge with pre-bound labels."""

    def __init__(self, parent: Gauge, labels: Dict[str, str]):
        self.parent = parent
        self.labels = labels

    def set(self, value: float) -> None:
        self.parent.set(value, labels=self.labels)

    def inc(self, amount: float = 1.0) -> None:
        self.parent.inc(amount, labels=self.labels)

    def dec(self, amount: float = 1.0) -> None:
        self.parent.dec(amount, labels=self.labels)


DEFAULT_HISTOGRAM_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


class Histogram(Metric):
    """Cumulative metric that samples observations into configurable buckets."""

    def __init__(
        self,
        name: str,
        description: str,
        label_names: Optional[List[str]] = None,
        buckets: Optional[Tuple[float, ...]] = None,
    ):
        super().__init__(name, description, label_names)
        self.buckets = sorted(buckets or DEFAULT_HISTOGRAM_BUCKETS)
        self._counts: Dict[Tuple[Tuple[str, str], ...], int] = defaultdict(int)
        self._sums: Dict[Tuple[Tuple[str, str], ...], float] = defaultdict(float)
        self._bucket_counts: Dict[Tuple[Tuple[str, str], ...], Dict[float, int]] = defaultdict(
            lambda: {b: 0 for b in self.buckets}
        )

    def labels(self, **kwargs) -> "Histogram":
        """Bind label key-values."""
        return _BoundHistogram(self, kwargs)

    def observe(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Sample a value observation into the histogram."""
        key = tuple(sorted((k, str(v)) for k, v in (labels or {}).items()))
        with self._lock:
            self._counts[key] += 1
            self._sums[key] += float(value)
            b_dict = self._bucket_counts[key]
            for b in self.buckets:
                if value <= b:
                    b_dict[b] += 1

    def render(self) -> List[str]:
        """Render histogram into Prometheus exposition format."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} histogram",
        ]
        with self._lock:
            for label_tuples in sorted(set(list(self._counts.keys()) or [()])):
                lbl_dict = dict(label_tuples)
                b_dict = self._bucket_counts[label_tuples]
                count = self._counts[label_tuples]
                sum_val = self._sums[label_tuples]

                # Bucket lines
                for b in self.buckets:
                    b_lbls = dict(lbl_dict)
                    b_lbls["le"] = str(b)
                    lines.append(f"{self.name}_bucket{self._format_labels(b_lbls)} {b_dict[b]}")

                # +Inf bucket line
                inf_lbls = dict(lbl_dict)
                inf_lbls["le"] = "+Inf"
                lines.append(f"{self.name}_bucket{self._format_labels(inf_lbls)} {count}")

                # Sum and count lines
                base_lbl_str = self._format_labels(lbl_dict)
                lines.append(f"{self.name}_sum{base_lbl_str} {sum_val}")
                lines.append(f"{self.name}_count{base_lbl_str} {count}")

        return lines


class _BoundHistogram:
    """Helper proxy for Histogram with pre-bound labels."""

    def __init__(self, parent: Histogram, labels: Dict[str, str]):
        self.parent = parent
        self.labels = labels

    def observe(self, value: float) -> None:
        self.parent.observe(value, labels=self.labels)


class MetricsRegistry:
    """Registry maintaining collection of application metrics."""

    def __init__(self):
        self._metrics: Dict[str, Metric] = {}
        self._lock = threading.Lock()

    def register(self, metric: Metric) -> Metric:
        """Register a metric in the registry."""
        with self._lock:
            self._metrics[metric.name] = metric
            return metric

    def get_metric(self, name: str) -> Optional[Metric]:
        """Fetch metric by name."""
        with self._lock:
            return self._metrics.get(name)

    def render(self) -> str:
        """Export all registered metrics into Prometheus 0.0.4 plain-text format."""
        lines = []
        with self._lock:
            for _, metric in sorted(self._metrics.items()):
                lines.extend(metric.render())
                lines.append("")
        return "\n".join(lines)


# Global Application Registry
registry = MetricsRegistry()

# Standard Customer Voice AI Core Metrics
HTTP_REQUESTS_TOTAL: Counter = registry.register(
    Counter(
        "cva_http_requests_total",
        "Total number of HTTP requests processed by endpoint and status code.",
        ["method", "endpoint", "status"],
    )
)

HTTP_REQUEST_DURATION_SECONDS: Histogram = registry.register(
    Histogram(
        "cva_http_request_duration_seconds",
        "HTTP request latency in seconds.",
        ["method", "endpoint"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    )
)

REVIEWS_INGESTED_TOTAL: Counter = registry.register(
    Counter(
        "cva_reviews_ingested_total",
        "Total customer reviews ingested across products and channels.",
        ["product_id", "source_id"],
    )
)

CLUSTERS_FORMED_TOTAL: Counter = registry.register(
    Counter(
        "cva_clusters_formed_total",
        "Total issue clusters discovered by DBSCAN semantic clustering.",
        ["product_id"],
    )
)

KAFKA_EVENTS_TOTAL: Counter = registry.register(
    Counter(
        "cva_kafka_events_published_total",
        "Total events published to Kafka topics with delivery status.",
        ["topic", "status"],
    )
)

INVESTIGATIONS_TOTAL: Counter = registry.register(
    Counter(
        "cva_investigations_total",
        "Total LangGraph multi-agent investigations executed.",
        ["status", "team_id"],
    )
)

ACTIVE_CLUSTERS_GAUGE: Gauge = registry.register(
    Gauge(
        "cva_active_clusters_gauge",
        "Current number of active unresolved issue clusters.",
        ["product_id"],
    )
)

DB_PING_LATENCY_SECONDS: Gauge = registry.register(
    Gauge(
        "cva_db_ping_latency_seconds",
        "Response latency of database connectivity probe in seconds.",
    )
)
