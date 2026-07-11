/**
 * Stats Controller
 * Handles statistics and chart functionality for the dashboard
 * Manages vulnerability statistics and data visualization
 */
class StatsController {
    constructor(userId, apiEndpoint) {
        this.userId = userId;
        this.apiEndpoint = apiEndpoint;
        this.chart = null;

        // UI elements
        this.ui = {
            totalVulns: document.getElementById('totalVulns'),
            statsSummary: document.getElementById('statsSummary'),
            vulnerabilityChart: document.getElementById('vulnerabilityChart')
        };

        // Initialize
        this.init();
    }

    /**
     * Initialize stats controller
     */
    async init() {
        console.log('📊 Initializing Stats Controller...');

        // Initialize chart
        this.initializeChart();

        // Load initial stats
        await this.loadStats();

        console.log('✅ Stats controller initialized');
    }

    /**
     * Load vulnerability statistics from API
     */
    async loadStats() {
        const requestUrl = `${this.apiEndpoint}/api/stats/vulnerabilities`;

        console.log('📊 Loading vulnerability stats:', {
            endpoint: requestUrl,
            userId: this.userId
        });

        try {
            const response = await fetch(
                requestUrl,
                {
                    headers: {
                        'X-User-ID': this.userId
                    }
                }
            );

            console.log('🟢 Vulnerability Stats API Response:', {
                status: response.status,
                ok: response.ok,
                statusText: response.statusText
            });

            if (response.ok) {
                const stats = await response.json();
                console.log('🟢 Vulnerability Stats Data:', stats);

                // Check if real data exists (total > 0)
                if (stats.total > 0) {
                    console.log('✅ Real data found, updating display');
                    this.updateVulnerabilityStats(stats);
                } else {
                    // No real data yet - show empty state
                    console.log('⚠️ No data found, showing empty state');
                    this.useEmptyVulnerabilityData();
                }
            } else {
                console.error(`Failed to load vulnerability stats: ${response.status}`);
                this.showStatsError();
            }
        } catch (error) {
            console.error('🔴 Failed to load vulnerability stats:', {
                message: error.message,
                stack: error.stack,
                endpoint: requestUrl
            });
            this.showStatsError();
        }
    }

    /**
     * Update vulnerability statistics
     */
    updateVulnerabilityStats(stats) {
        // Update chart data
        if (this.chart) {
            this.chart.data.datasets[0].data = [
                stats.injection,
                stats.cross_site_scripting,
                stats.authentication,
                stats.remote_code_execution,
                stats.memory_corruption,
                stats.csrf,
                stats.other
            ];
            this.chart.update();
        }

        // Update total count
        if (this.ui.totalVulns) {
            this.ui.totalVulns.textContent = stats.total || 0;
        }

        // Update stats summary
        this.updateStatsSummary(stats);
    }

    /**
     * Update stats summary display
     */
    updateStatsSummary(stats) {
        if (!this.ui.statsSummary) return;

        const categories = [
            { key: 'injection', label: 'Injection Attacks' },
            { key: 'cross_site_scripting', label: 'Cross-Site Scripting' },
            { key: 'authentication', label: 'Authentication' },
            { key: 'remote_code_execution', label: 'Remote Code Execution' }
        ];

        const summaryHTML = categories.map(cat => {
            const count = stats[cat.key] || 0;
            const percentage = stats.total > 0 ? ((count / stats.total) * 100).toFixed(1) : 0;
            return `
                <div class="flex items-center justify-between text-sm">
                    <span class="text-on-surface-variant">${cat.label}</span>
                    <span class="font-headline font-bold">${count} <span class="text-[10px] text-on-surface-variant">(${percentage}%)</span></span>
                </div>
            `;
        }).join('');

        // SECURE: Use safe innerHTML setter for summary content
        if (typeof CyberSecSanitizer !== 'undefined' && CyberSecSanitizer.safeSetInnerHTML) {
            CyberSecSanitizer.safeSetInnerHTML(this.ui.statsSummary, summaryHTML);
        } else {
            this.ui.statsSummary.innerHTML = summaryHTML; // Fallback
        }
    }

    /**
     * Use empty state when no vulnerability data available
     */
    useEmptyVulnerabilityData() {
        // Display empty state message - NO FAKE DATA
        const emptyStateHTML = `
            <div class="flex items-center justify-center h-full text-on-surface-variant">
                <div class="text-center">
                    <span class="material-symbols-outlined text-4xl text-outline-variant mb-2">bar_chart</span>
                    <p class="text-sm">No vulnerability data available yet</p>
                    <p class="text-xs text-outline mt-1">Start chatting to generate statistics</p>
                </div>
            </div>
        `;

        // Clear chart and show empty state
        if (this.chart) {
            this.chart.data.datasets[0].data = [0, 0, 0, 0, 0, 0, 0];
            this.chart.update();
        }

        // Update stats summary with empty state
        if (this.ui.statsSummary) {
            // SECURE: Use safe innerHTML setter
            if (typeof CyberSecSanitizer !== 'undefined' && CyberSecSanitizer.safeSetInnerHTML) {
                CyberSecSanitizer.safeSetInnerHTML(this.ui.statsSummary, emptyStateHTML);
            } else {
                this.ui.statsSummary.innerHTML = emptyStateHTML; // Fallback
            }
        }

        // Update total count
        if (this.ui.totalVulns) {
            this.ui.totalVulns.textContent = '0';
        }

        console.log('No vulnerability data - displaying empty state');
    }

    /**
     * Show stats error message
     */
    showStatsError() {
        if (!this.ui.statsSummary) return;

        const errorHTML = `
            <div class="flex items-center justify-center h-full text-error">
                <div class="text-center">
                    <span class="material-symbols-outlined text-4xl mb-2">error</span>
                    <p class="text-sm">Failed to load vulnerability statistics</p>
                    <p class="text-xs text-outline mt-1">Please check your connection and try again</p>
                </div>
            </div>
        `;

        // SECURE: Use safe innerHTML setter
        if (typeof CyberSecSanitizer !== 'undefined' && CyberSecSanitizer.safeSetInnerHTML) {
            CyberSecSanitizer.safeSetInnerHTML(this.ui.statsSummary, errorHTML);
        } else {
            this.ui.statsSummary.innerHTML = errorHTML; // Fallback
        }
    }

    /**
     * Initialize Chart.js doughnut chart
     */
    initializeChart() {
        if (!this.ui.vulnerabilityChart) {
            console.warn('Chart element not found');
            return;
        }

        const ctx = this.ui.vulnerabilityChart.getContext('2d');

        this.chart = new Chart(ctx, {
            type: 'doughnut',
            data: this.getChartData(),
            options: this.getChartOptions()
        });

        console.log('✅ Chart initialized');
    }

    /**
     * Get chart data structure
     */
    getChartData() {
        return {
            labels: ['Injection', 'Cross-Site Scripting', 'Authentication', 'Remote Code Execution', 'Memory Corruption', 'CSRF', 'Other'],
            datasets: [{
                data: [0, 0, 0, 0, 0, 0, 0],  // Start with zeros - real data or empty state
                backgroundColor: [
                    '#84fdad',  // Primary (Injection)
                    '#00caed',  // Tertiary (XSS)
                    '#76efa0',  // Primary-dim (Authentication)
                    '#ff716c',  // Error (RCE)
                    '#d7383b',  // Error-dim (Memory)
                    '#e4e2e4',  // Secondary (CSRF)
                    '#acaaae'   // Surface-variant (Other)
                ],
                hoverOffset: 4,
                hoverBackgroundColor: [
                    '#a8ffc3',
                    '#33e1ff',
                    '#96ffbd',
                    '#ff8e8a',
                    '#e9585a',
                    '#f0eff0',
                    '#c6c4ca'
                ]
            }]
        };
    }

    /**
     * Get chart options
     */
    getChartOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#fbf8fc',
                        font: {
                            family: 'Space Grotesk',
                            size: 12,
                            weight: '500'
                        },
                        padding: 15,
                        usePointStyle: true,
                        pointStyle: 'circle'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(30, 30, 34, 0.95)',
                    titleFont: {
                        family: 'Space Grotesk',
                        size: 14,
                        weight: '700'
                    },
                    bodyFont: {
                        family: 'Inter',
                        size: 12
                    },
                    padding: 12,
                    cornerRadius: 8,
                    borderColor: '#0F9D58',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                            return ` ${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            },
            elements: {
                arc: {
                    borderWidth: 2,
                    borderColor: '#0e0e11'
                }
            }
        };
    }

    /**
     * Refresh stats
     */
    async refreshStats() {
        await this.loadStats();
    }

    /**
     * Cleanup resources when controller is destroyed
     */
    cleanup() {
        // Cleanup chart if exists
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
            console.log('✅ Cleaned up chart');
        }

        console.log('✅ Stats controller cleaned up');
    }
}