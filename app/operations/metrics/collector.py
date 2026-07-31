import logging

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Abstract metric collection service. In production, this would use
    prometheus_client or opentelemetry to record real metrics.
    Currently stubbed out to log the metric internally.
    """

    @staticmethod
    def increment_counter(metric_name: str, labels: dict = None, value: int = 1):
        # Stub implementation
        logger.debug(
            f"[Metrics] Counter incremented: {metric_name} | value: {value} | labels: {labels}"
        )

    @staticmethod
    def record_histogram(metric_name: str, value: float, labels: dict = None):
        # Stub implementation
        logger.debug(
            f"[Metrics] Histogram recorded: {metric_name} | value: {value} | labels: {labels}"
        )


metrics_collector = MetricsCollector()
