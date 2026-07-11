/**
 * CyberSec News Controller
 * Manages dynamic news loading using shared news service
 */
class NewsController {
    constructor() {
        this.newsContainer = document.getElementById('newsStream');
        this.btnAllNews = document.getElementById('btnAllNews');
        this.btnCriticalNews = document.getElementById('btnCriticalNews');

        this.allNews = [];
        this.currentFilter = 'all'; // 'all' or 'critical'

        this.init();
    }

    async init() {
        if (!this.newsContainer) return;
        this.setupEventListeners();
        await this.loadNews();
        // Load statistics
        await this.loadCVECounts();
        await this.loadVulnerabilityStats();
    }

    setupEventListeners() {
        if (this.btnAllNews) {
            this.btnAllNews.addEventListener('click', () => this.setFilter('all'));
        }
        if (this.btnCriticalNews) {
            this.btnCriticalNews.addEventListener('click', () => this.setFilter('critical'));
        }
    }

    async loadNews() {
        if (!window.newsService) {
            console.error('News service not available');
            this.renderErrorState();
            return;
        }

        // Show loading state
        this.newsContainer.innerHTML = `
            <div class="text-center py-8">
                <p class="text-on-surface-variant">Đang tải tin tức...</p>
            </div>
        `;

        try {
            // Load latest news items (up to 50 items)
            this.allNews = await window.newsService.loadLatestNews(50);
            this.filterAndDisplayNews();
            console.log('✅ News loaded successfully:', this.allNews);
        } catch (e) {
            console.error('Failed to load news:', e);
            this.renderErrorState();
        }
    }

    async loadCVECounts() {
        try {
            const apiEndpoint = window.config?.get('apiEndpoint') || 'http://localhost:8000';
            const response = await fetch(`${apiEndpoint}/api/cve/stats`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const stats = await response.json();

            // Update CVE count displays
            const cveCountIndex = document.getElementById('cveCountIndex');
            const cveCountDetail = document.getElementById('cveCountDetail');

            if (cveCountIndex && stats.total_entries) {
                cveCountIndex.textContent = stats.total_entries.toLocaleString();
            }

            if (cveCountDetail && stats.total_entries) {
                cveCountDetail.textContent = stats.total_entries.toLocaleString();
            }

            console.log('✅ CVE counts loaded:', stats);
        } catch (error) {
            console.error('Failed to load CVE counts:', error);
            // Keep default "-" on error
        }
    }

    async loadVulnerabilityStats() {
        try {
            const apiEndpoint = window.config?.get('apiEndpoint') || 'http://localhost:8000';
            const response = await fetch(`${apiEndpoint}/api/stats/vulnerabilities`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const stats = await response.json();

            const total = stats.total || 1;
            const categories = [
                { name: 'Injection', value: stats.injection || 0, color: 'primary' },
                { name: 'Memory Corruption', value: stats.memory_corruption || 0, color: 'surface-variant' },
                { name: 'XSS', value: stats.cross_site_scripting || 0, color: 'tertiary' },
                { name: 'Auth Bypass', value: stats.authentication || 0, color: 'error' }
            ];

            // Update progress bars for index.html
            const progressContainer = document.getElementById('vulnerabilityProgressBars');
            if (progressContainer) {
                progressContainer.innerHTML = categories.map(cat => {
                    const percentage = total > 0 ? ((cat.value / total) * 100).toFixed(0) : 0;
                    return `
                        <div class="vulnerability-progress mb-6">
                            <div class="flex justify-between mb-2">
                                <span class="text-sm font-headline">${cat.name}</span>
                                <span class="text-sm font-mono text-${cat.color}">${percentage}%</span>
                            </div>
                            <div class="h-2 bg-surface-container-high rounded-full overflow-hidden">
                                <div class="h-full bg-${cat.color} rounded-full transition-all duration-500" style="width: ${percentage}%"></div>
                            </div>
                        </div>
                    `;
                }).join('');
            }

            // Update doughnut chart for detail.html
            const doughnutContainer = document.getElementById('vulnerabilityDoughnutChart');
            if (doughnutContainer) {
                this.updateDoughnutChart(categories, total);
            }

            console.log('✅ Vulnerability stats loaded:', stats);
        } catch (error) {
            console.error('Failed to load vulnerability stats:', error);
            // Keep default values on error
        }
    }

    updateDoughnutChart(categories, total) {
        const doughnutContainer = document.getElementById('vulnerabilityDoughnutChart');
        if (!doughnutContainer) return;

        // Calculate percentages and stroke-dashoffset values for SVG
        const circumference = 2 * Math.PI * 40; // r=40
        let accumulatedPercentage = 0;

        const chartSegments = categories.map(cat => {
            const percentage = total > 0 ? (cat.value / total) : 0;
            const dashOffset = circumference * (1 - accumulatedPercentage);
            accumulatedPercentage += percentage;

            return `
                <circle class="text-${cat.color}" cx="50" cy="50" fill="transparent" r="40"
                    stroke="currentColor" stroke-dasharray="${circumference}" stroke-dashoffset="${dashOffset}"
                    stroke-width="12" transform="rotate(-90 50 50)"></circle>
            `;
        }).join('');

        doughnutContainer.innerHTML = `
            <svg width="100" height="100" viewBox="0 0 100 100">
                ${chartSegments}
            </svg>
        `;

        // Update legend if exists
        const legendContainer = document.getElementById('vulnerabilityLegend');
        if (legendContainer) {
            legendContainer.innerHTML = categories.map(cat => {
                const percentage = total > 0 ? ((cat.value / total) * 100).toFixed(0) : 0;
                return `
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <div class="w-3 h-3 rounded-full bg-${cat.color}"></div>
                            <span class="text-xs font-headline">${cat.name}</span>
                        </div>
                        <span class="text-sm font-headline font-bold text-on-surface">${percentage}%</span>
                    </div>
                `;
            }).join('');
        }
    }

    setFilter(filterType) {
        if (this.currentFilter === filterType) return;
        this.currentFilter = filterType;

        // Update active class styling
        if (filterType === 'all') {
            this.btnAllNews?.classList.remove('bg-transparent', 'text-on-surface-variant');
            this.btnAllNews?.classList.add('bg-surface-container-high', 'border', 'border-outline-variant/30', 'text-primary');

            this.btnCriticalNews?.classList.remove('bg-surface-container-high', 'border', 'border-outline-variant/30', 'text-primary');
            this.btnCriticalNews?.classList.add('bg-transparent', 'text-on-surface-variant');
        } else {
            this.btnCriticalNews?.classList.remove('bg-transparent', 'text-on-surface-variant');
            this.btnCriticalNews?.classList.add('bg-surface-container-high', 'border', 'border-outline-variant/30', 'text-primary');

            this.btnAllNews?.classList.remove('bg-surface-container-high', 'border', 'border-outline-variant/30', 'text-primary');
            this.btnAllNews?.classList.add('bg-transparent', 'text-on-surface-variant');
        }

        this.filterAndDisplayNews();
    }

    filterAndDisplayNews() {
        if (!this.newsContainer) return;

        let filtered = this.allNews;
        if (this.currentFilter === 'critical') {
            filtered = this.allNews.filter(item => {
                const titleLower = (item.title || '').toLowerCase();
                const summaryLower = (item.summary || '').toLowerCase();
                // Check for critical threat indicators
                return titleLower.includes('critical') ||
                       titleLower.includes('severe') ||
                       titleLower.includes('zero-day') ||
                       titleLower.includes('rce') ||
                       titleLower.includes('exploit') ||
                       titleLower.includes('apt') ||
                       titleLower.includes('vulnerability') ||
                       titleLower.includes('nghiêm trọng') ||
                       summaryLower.includes('critical') ||
                       summaryLower.includes('severe') ||
                       summaryLower.includes('zero-day') ||
                       summaryLower.includes('rce') ||
                       summaryLower.includes('exploit') ||
                       summaryLower.includes('apt') ||
                       summaryLower.includes('vulnerability') ||
                       summaryLower.includes('nghiêm trọng');
            });
        }

        if (filtered.length === 0) {
            this.renderEmptyState();
        } else {
            // Render detailed view cards
            const html = window.newsService.generateNewsCards(filtered, true);
            this.newsContainer.innerHTML = html;
        }
    }

    renderEmptyState() {
        this.newsContainer.innerHTML = `
            <div class="text-center text-on-surface-variant py-12">
                <p>Không có tin tức nào thuộc danh mục này.</p>
            </div>
        `;
    }

    renderErrorState() {
        this.newsContainer.innerHTML = `
            <div class="text-center text-error py-12">
                <p>Không thể tải tin tức. Vui lòng thử lại sau.</p>
            </div>
        `;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Prevent double initialization
    if (window.newsControllerInitialized) {
        console.warn('⚠️ News controller already initialized, skipping duplicate initialization');
        return;
    }

    if (window.config) {
        new NewsController();
        window.newsControllerInitialized = true;
    } else {
        setTimeout(() => {
            if (window.config && !window.newsControllerInitialized) {
                new NewsController();
                window.newsControllerInitialized = true;
            }
        }, 100);
    }
});
