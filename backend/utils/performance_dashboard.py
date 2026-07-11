"""
Performance monitoring dashboard utilities.

Provides tools for visualizing and analyzing performance metrics
collected from the performance middleware and profilers.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict


class PerformanceDashboard:
    """Performance monitoring dashboard data aggregator."""

    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or Path(".benchmarks")
        self.metrics_cache = {}
        self.load_metrics()

    def load_metrics(self):
        """Load performance metrics from storage."""
        # Load latest baseline
        baseline_file = self.data_path / "baseline_latest.json"
        if baseline_file.exists():
            with open(baseline_file, encoding='utf-8') as f:
                self.metrics_cache['baseline'] = json.load(f)

        # Load latest comparison
        comparison_files = list(self.data_path.glob("comparison_*.json"))
        if comparison_files:
            latest_comparison = max(comparison_files, key=lambda f: f.stat().st_mtime)
            with open(latest_comparison, encoding='utf-8') as f:
                self.metrics_cache['comparison'] = json.load(f)

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "overall_health": "unknown",
            "critical_issues": [],
            "warnings": [],
            "improvements": [],
            "metrics": {}
        }

        # Analyze baseline if available
        if 'baseline' in self.metrics_cache:
            baseline_data = self.metrics_cache['baseline']
            analysis = baseline_data.get('analysis', {})

            # Overall health assessment
            concerning = len(analysis.get('performance_categories', {}).get('concerning', []))
            excellent = len(analysis.get('performance_categories', {}).get('excellent', []))
            total = analysis.get('total_benchmarks', 1)

            if concerning > total * 0.2:  # More than 20% concerning
                summary["overall_health"] = "critical"
                summary["critical_issues"].append(f"High number of slow tests: {concerning}/{total}")
            elif excellent > total * 0.7:  # More than 70% excellent
                summary["overall_health"] = "excellent"
                summary["improvements"].append(f"Excellent performance: {excellent}/{total} tests fast")
            else:
                summary["overall_health"] = "good"

            summary["metrics"]["total_benchmarks"] = total
            summary["metrics"]["avg_execution_time"] = analysis.get('summary', {}).get('average', 0)

        # Analyze comparison if available
        if 'comparison' in self.metrics_cache:
            comparison_data = self.metrics_cache['comparison']
            regressions = len(comparison_data.get('regressions', []))
            improvements = len(comparison_data.get('improvements', []))

            if regressions > 0:
                summary["overall_health"] = "critical"
                summary["critical_issues"].append(f"Performance regressions detected: {regressions} tests")

            if improvements > 0:
                summary["improvements"].append(f"Performance gains: {improvements} tests improved")

        return summary

    def get_endpoint_performance(self) -> Dict[str, Any]:
        """Get endpoint-specific performance data."""
        endpoints = {}

        # Get from comparison data if available
        if 'comparison' in self.metrics_cache:
            comparison_data = self.metrics_cache['comparison']

            # Combine all performance data
            for category in ['regressions', 'improvements', 'stable']:
                for item in comparison_data.get(category, []):
                    test_name = item['test']
                    if test_name not in endpoints:
                        endpoints[test_name] = {
                            'current': item.get('current', 0),
                            'baseline': item.get('baseline', 0),
                            'change_percentage': item.get('change_percentage', 0),
                            'status': 'unknown'
                        }

                    # Determine status
                    if category == 'regressions':
                        endpoints[test_name]['status'] = 'regression'
                    elif category == 'improvements':
                        endpoints[test_name]['status'] = 'improvement'
                    else:
                        endpoints[test_name]['status'] = 'stable'

        return endpoints

    def get_performance_trends(self, days: int = 7) -> Dict[str, Any]:
        """Get performance trends over time."""
        trends = {
            'period_days': days,
            'data_points': [],
            'overall_trend': 'stable',
            'significant_changes': []
        }

        # Load comparison files for the period
        cutoff_date = datetime.now() - timedelta(days=days)
        comparison_files = []

        for file in self.data_path.glob("comparison_*.json"):
            file_date = datetime.fromtimestamp(file.stat().st_mtime)
            if file_date > cutoff_date:
                with open(file, encoding='utf-8') as f:
                    data = json.load(f)
                    comparison_files.append({
                        'file': file,
                        'date': file_date,
                        'data': data
                    })

        # Sort by date
        comparison_files.sort(key=lambda x: x['date'])

        # Extract trend data
        for comp in comparison_files:
            summary = comp['data'].get('summary', {})
            trends['data_points'].append({
                'date': comp['date'].isoformat(),
                'regressions': summary.get('regressions', 0),
                'improvements': summary.get('improvements', 0),
                'stable': summary.get('stable', 0)
            })

        # Determine overall trend
        if len(trends['data_points']) >= 2:
            first = trends['data_points'][0]
            last = trends['data_points'][-1]

            if last['regressions'] > first['regressions']:
                trends['overall_trend'] = 'degrading'
            elif last['improvements'] > first['improvements']:
                trends['overall_trend'] = 'improving'

        return trends

    def generate_html_dashboard(self) -> str:
        """Generate HTML dashboard for performance visualization."""
        summary = self.get_performance_summary()
        endpoints = self.get_endpoint_performance()
        trends = self.get_performance_trends()

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Performance Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .dashboard {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .health-excellent {{ background: #d4edda; color: #155724; }}
        .health-good {{ background: #cce5ff; color: #004085; }}
        .health-critical {{ background: #f8d7da; color: #721c24; }}
        .section {{ background: #fff; border: 1px solid #ddd; padding: 20px; margin-bottom: 20px; border-radius: 5px; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #f9f9f9; border-radius: 3px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        .regression {{ color: #dc3545; font-weight: bold; }}
        .improvement {{ color: #28a745; font-weight: bold; }}
        .stable {{ color: #6c757d; }}
        .timestamp {{ font-size: 0.9em; color: #666; }}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header health-{summary['overall_health']}">
            <h1>🔍 Performance Dashboard</h1>
            <p>Overall Health: {summary['overall_health'].upper()}</p>
            <p class="timestamp">Generated: {summary['timestamp']}</p>
        </div>

        <div class="section">
            <h2>📊 Summary</h2>
            <div class="metric">Total Benchmarks: {summary['metrics'].get('total_benchmarks', 'N/A')}</div>
            <div class="metric">Avg Execution Time: {summary['metrics'].get('avg_execution_time', 0):.4f}s</div>
        </div>

        <div class="section">
            <h2>🚨 Critical Issues</h2>
            <ul>
                {"".join(f"<li>{issue}</li>" for issue in summary['critical_issues'])}
            </ul>
        </div>

        <div class="section">
            <h2>✅ Improvements</h2>
            <ul>
                {"".join(f"<li>{imp}</li>" for imp in summary['improvements'])}
            </ul>
        </div>

        <div class="section">
            <h2>🔗 Endpoint Performance</h2>
            <table>
                <tr>
                    <th>Test Name</th>
                    <th>Current</th>
                    <th>Baseline</th>
                    <th>Change</th>
                    <th>Status</th>
                </tr>
                {"".join(f"""
                <tr>
                    <td>{test_name}</td>
                    <td>{data['current']:.4f}s</td>
                    <td>{data['baseline']:.4f}s</td>
                    <td>{data['change_percentage']:+.2f}%</td>
                    <td class="{data['status']}">{data['status']}</td>
                </tr>
                """ for test_name, data in endpoints.items())}
            </table>
        </div>

        <div class="section">
            <h2>📈 Performance Trends (Last {trends['period_days']} Days)</h2>
            <p>Overall Trend: {trends['overall_trend']}</p>
            <table>
                <tr>
                    <th>Date</th>
                    <th>Regressions</th>
                    <th>Improvements</th>
                    <th>Stable</th>
                </tr>
                {"".join(f"""
                <tr>
                    <td>{point['date']}</td>
                    <td>{point['regressions']}</td>
                    <td>{point['improvements']}</td>
                    <td>{point['stable']}</td>
                </tr>
                """ for point in trends['data_points'])}
            </table>
        </div>
    </div>
</body>
</html>
        """

        return html

    def save_dashboard(self, output_path: Optional[Path] = None):
        """Save HTML dashboard to file."""
        output_path = output_path or self.data_path / "dashboard.html"

        html = self.generate_html_dashboard()
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        return output_path


class PerformanceAlertManager:
    """Manage performance alerts and notifications."""

    def __init__(self):
        self.alerts = []
        self.thresholds = {
            'critical': 5.0,      # 5 seconds
            'warning': 1.0,       # 1 second
            'regression': 20.0   # 20% degradation
        }

    def check_performance_alerts(self, comparison_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for performance alerts based on comparison data."""
        alerts = []

        # Check for regressions
        regressions = comparison_data.get('regressions', [])
        if len(regressions) > self.thresholds['regression'] / 100:
            alerts.append({
                'severity': 'critical',
                'message': f"High number of performance regressions: {len(regressions)}",
                'details': regressions
            })

        # Check individual test times
        for regression in regressions:
            if regression['current'] > self.thresholds['critical']:
                alerts.append({
                    'severity': 'critical',
                    'message': f"Test exceeds critical threshold: {regression['test']}",
                    'details': regression
                })
            elif regression['current'] > self.thresholds['warning']:
                alerts.append({
                    'severity': 'warning',
                    'message': f"Test exceeds warning threshold: {regression['test']}",
                    'details': regression
                })

        self.alerts = alerts
        return alerts

    def generate_alert_report(self) -> str:
        """Generate alert report."""
        if not self.alerts:
            return "✅ No performance alerts"

        report = ["🚨 Performance Alert Report", "=" * 50]

        for alert in self.alerts:
            severity = alert['severity'].upper()
            report.append(f"\n[{severity}] {alert['message']}")

        return "\n".join(report)


# Utility functions for quick performance checks
def quick_performance_check() -> Dict[str, Any]:
    """Perform quick performance health check."""
    dashboard = PerformanceDashboard()
    return dashboard.get_performance_summary()


def generate_performance_dashboard() -> Path:
    """Generate and save performance dashboard."""
    dashboard = PerformanceDashboard()
    return dashboard.save_dashboard()


if __name__ == "__main__":
    # Generate dashboard when run directly
    print("🔍 Generating performance dashboard...")
    dashboard_path = generate_performance_dashboard()
    print(f"✅ Dashboard generated: {dashboard_path}")

    # Perform quick check
    summary = quick_performance_check()
    print(f"\n📊 Performance Health: {summary['overall_health'].upper()}")
    print(f"📈 Total Benchmarks: {summary['metrics'].get('total_benchmarks', 'N/A')}")