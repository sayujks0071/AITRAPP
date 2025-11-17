"""Metrics wrapper for Prometheus-style metric recording"""
from typing import Any, Dict, Optional
from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry

from packages.core.metrics import REGISTRY


class MetricsWrapper:
    """
    Wrapper around Prometheus metrics that provides a simple interface:
    
    metrics.gauge("name", labels).set(value)
    metrics.counter("name", labels).inc(value)
    metrics.histogram("name", labels).observe(value)
    """
    
    def __init__(self, registry: CollectorRegistry = REGISTRY):
        self.registry = registry
        self._gauges: Dict[str, Gauge] = {}
        self._counters: Dict[str, Counter] = {}
        self._histograms: Dict[str, Histogram] = {}
    
    def gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> "GaugeWrapper":
        """Get or create a gauge metric"""
        if name not in self._gauges:
            label_names = list(labels.keys()) if labels else []
            self._gauges[name] = Gauge(
                name,
                f"Gauge metric: {name}",
                label_names,
                registry=self.registry
            )
        return GaugeWrapper(self._gauges[name], labels or {})
    
    def counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> "CounterWrapper":
        """Get or create a counter metric"""
        if name not in self._counters:
            label_names = list(labels.keys()) if labels else []
            self._counters[name] = Counter(
                name,
                f"Counter metric: {name}",
                label_names,
                registry=self.registry
            )
        return CounterWrapper(self._counters[name], labels or {})
    
    def histogram(self, name: str, labels: Optional[Dict[str, str]] = None, buckets: Optional[list] = None) -> "HistogramWrapper":
        """Get or create a histogram metric"""
        if name not in self._histograms:
            label_names = list(labels.keys()) if labels else []
            self._histograms[name] = Histogram(
                name,
                f"Histogram metric: {name}",
                label_names,
                buckets=buckets,
                registry=self.registry
            )
        return HistogramWrapper(self._histograms[name], labels or {})


class GaugeWrapper:
    """Wrapper for Gauge metric with labels"""
    def __init__(self, gauge: Gauge, labels: Dict[str, str]):
        self.gauge = gauge
        self.labels = labels
    
    def set(self, value: float) -> None:
        """Set gauge value"""
        if self.labels:
            self.gauge.labels(**self.labels).set(value)
        else:
            self.gauge.set(value)


class CounterWrapper:
    """Wrapper for Counter metric with labels"""
    def __init__(self, counter: Counter, labels: Dict[str, str]):
        self.counter = counter
        self.labels = labels
    
    def inc(self, value: float = 1.0) -> None:
        """Increment counter"""
        if self.labels:
            self.counter.labels(**self.labels).inc(value)
        else:
            self.counter.inc(value)


class HistogramWrapper:
    """Wrapper for Histogram metric with labels"""
    def __init__(self, histogram: Histogram, labels: Dict[str, str]):
        self.histogram = histogram
        self.labels = labels
    
    def observe(self, value: float) -> None:
        """Observe a value"""
        if self.labels:
            self.histogram.labels(**self.labels).observe(value)
        else:
            self.histogram.observe(value)


