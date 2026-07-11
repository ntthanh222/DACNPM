import asyncio

from backend.utils import performance_profiler


def test_metrics_query_profiler_and_function_decorators():
    metrics = performance_profiler.PerformanceMetrics()
    metrics.execution_time = 0.2
    assert metrics.to_dict()["execution_time"] == 0.2
    queries = performance_profiler.DatabaseQueryProfiler()
    queries.record_query("select 1", 0.5)
    assert queries.get_stats()["total_queries"] == 1

    @performance_profiler.profile_function
    def value(): return "ok"
    assert value() == "ok"


def test_monitor_records_slow_operations_and_async_decorator():
    monitor = performance_profiler.PerformanceMonitor()
    monitor.operation_history = []
    metrics = performance_profiler.PerformanceMetrics(); metrics.execution_time = 2
    monitor.record_operation("slow", metrics)
    assert monitor.get_slow_operations()[-1]["name"] == "slow"

    @performance_profiler.profile_async_function
    async def value(): return "ok"
    assert asyncio.run(value()) == "ok"
