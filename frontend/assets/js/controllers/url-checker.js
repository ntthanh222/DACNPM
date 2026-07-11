/**
 * CyberSec URL Checker Controller
 * Manages URL analysis functionality
 */
class URLCheckerController {
    constructor() {
        this.apiEndpoint = window.config.get('apiEndpoint');
        this.phishingCheckEndpoint = window.config.get('phishingCheckEndpoint');
        this.init();
    }

    init() {
        this.setupEventListeners();
        console.log('URL checker controller initialized');
        this.checkQueryParameters();
    }

    checkQueryParameters() {
        const urlParams = new URLSearchParams(window.location.search);
        const urlToCheck = urlParams.get('url');
        if (urlToCheck) {
            console.log('📬 Initial URL found in query parameters:', urlToCheck);
            const urlInput = document.getElementById('urlInput');
            if (urlInput) {
                urlInput.value = urlToCheck;
                setTimeout(() => {
                    this.checkURL(urlToCheck);
                    const cleanUrl = window.location.protocol + "//" + window.location.host + window.location.pathname;
                    window.history.replaceState({ path: cleanUrl }, '', cleanUrl);
                }, 300);
            }
        }
    }

    setupEventListeners() {
        const executeButton = document.getElementById('executeButton');
        const urlInput = document.getElementById('urlInput');

        if (executeButton && urlInput) {
            executeButton.addEventListener('click', () => this.checkURL(urlInput.value));
            urlInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.checkURL(urlInput.value);
                }
            });

            // Add manual paste handler to guarantee pasting works under all browser/OS conditions
            urlInput.addEventListener('paste', (e) => {
                const clipboardData = e.clipboardData || window.clipboardData;
                if (clipboardData) {
                    const pastedData = clipboardData.getData('Text') || clipboardData.getData('text/plain');
                    if (pastedData) {
                        e.preventDefault();
                        const startPos = urlInput.selectionStart;
                        const endPos = urlInput.selectionEnd;
                        const text = urlInput.value;
                        urlInput.value = text.substring(0, startPos) + pastedData + text.substring(endPos);
                        urlInput.selectionStart = urlInput.selectionEnd = startPos + pastedData.length;
                        console.log('✅ Manually pasted text via event handler:', pastedData);
                    }
                }
            });
        }
    }

    async checkURL(url) {
        console.log('🔗 checkURL called:', { url, endpoint: this.phishingCheckEndpoint });

        if (!url.trim()) {
            console.warn('⚠️ Empty URL, showing alert');
            alert('Vui lòng nhập URL cần kiểm tra');
            return;
        }

        const executeButton = document.getElementById('executeButton');

        if (executeButton) {
            executeButton.disabled = true;
            executeButton.innerHTML = '<span class="material-symbols-outlined animate-spin">refresh</span><span>Đang kiểm tra...</span>';
        }

        console.log('🔵 Sending phishing check API request:', {
            endpoint: this.phishingCheckEndpoint,
            method: 'POST',
            url: url
        });

        try {
            const response = await fetch(this.phishingCheckEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                    // Note: Authorization and X-User-ID headers are auto-injected by auth.js fetch interceptor
                },
                body: JSON.stringify({ url: url })
            });

            console.log('🟢 Phishing Check API Response:', {
                status: response.status,
                ok: response.ok,
                statusText: response.statusText
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            console.log('🟢 Phishing Check Response Data:', result);
            this.displayResults(result);

        } catch (error) {
            console.error('🔴 Phishing Check API Error:', {
                message: error.message,
                stack: error.stack,
                endpoint: this.phishingCheckEndpoint,
                url: url
            });

            // Clear previous results before showing error
            this.clearPreviousResults();

            // Show user-friendly error message
            const errorHTML = `
                <div class="col-span-12 bg-[#19191d] rounded-2xl p-6 border-l-2 border-error">
                    <div class="flex items-center gap-3 mb-4">
                        <span class="material-symbols-outlined text-error">error</span>
                        <h3 class="text-xl font-headline font-semibold">Lỗi kiểm tra URL</h3>
                    </div>
                    <div class="bg-surface-container-low p-4 rounded-xl">
                        <p class="text-sm text-on-surface-variant">
                            Không thể kiểm tra URL hiện tại. Vui lòng thử lại sau.
                        </p>
                        <p class="text-xs text-outline mt-2">
                            Chi tiết lỗi: ${this.escapeHtml(error.message)}
                        </p>
                    </div>
                </div>
            `;

            const resultsSection = document.createElement('div');
            resultsSection.innerHTML = errorHTML;

            // Insert after existing content
            const container = document.querySelector('.col-span-12');
            if (container && container.parentNode) {
                container.parentNode.insertBefore(resultsSection, container.nextSibling);
            }
        } finally {
            if (executeButton) {
                executeButton.disabled = false;
                executeButton.innerHTML = '<span class="material-symbols-outlined" aria-hidden="true">security_update_good</span>Thực hiện phân tích';
            }
        }
    }

    /**
     * Clear previous URL check results
     */
    clearPreviousResults() {
        // Find and remove previous results sections
        const previousResults = document.querySelectorAll('.col-span-12.bg-\\[\\#19191d\\].rounded-2xl.p-6.border-l-2');
        previousResults.forEach(section => {
            section.remove();
            console.log('🗑️ Removed previous results section');
        });
    }

    displayResults(result) {
        console.log('📊 Displaying URL check results:', result);

        // Clear previous results before displaying new ones
        this.clearPreviousResults();

        const resultsSection = document.createElement('div');
        resultsSection.className = 'col-span-12 bg-[#19191d] rounded-2xl p-6 border-l-2';

        // VALIDATE: Ensure risk_level is one of the expected values
        const validRiskLevels = ['LOW', 'MEDIUM', 'HIGH'];
        const riskLevel = validRiskLevels.includes(result.risk_level) ? result.risk_level : 'LOW';

        const riskLevelColors = {
            'LOW': 'border-primary',
            'MEDIUM': 'border-yellow-500',
            'HIGH': 'border-error'
        };

        const riskLevelTexts = {
            'LOW': 'text-primary',
            'MEDIUM': 'text-yellow-500',
            'HIGH': 'text-error'
        };

        resultsSection.classList.add(riskLevelColors[riskLevel] || 'border-primary');

        // SANITIZE: Validate and sanitize numeric values
        const riskScore = this.sanitizeNumber(result.risk_score);

        // SAFE: Create header using DOM manipulation
        const headerDiv = document.createElement('div');
        headerDiv.className = 'flex items-center justify-between mb-4';

        const titleH3 = document.createElement('h3');
        titleH3.className = 'text-xl font-headline font-semibold';
        titleH3.textContent = 'Kết quả phân tích';

        const riskSpan = document.createElement('span');
        riskSpan.className = `text-lg font-headline font-bold ${riskLevelTexts[riskLevel] || 'text-primary'}`;
        riskSpan.textContent = riskLevel; // SAFE: validated value

        headerDiv.appendChild(titleH3);
        headerDiv.appendChild(riskSpan);
        resultsSection.appendChild(headerDiv);

        // Create grid for risk score and URL
        const gridDiv = document.createElement('div');
        gridDiv.className = 'grid grid-cols-2 gap-4 mb-4';

        // Risk score card
        const scoreCard = document.createElement('div');
        scoreCard.className = 'bg-surface-container-low p-4 rounded-xl';
        scoreCard.innerHTML = `
            <p class="text-[10px] text-on-surface-variant font-headline mb-1 uppercase tracking-tighter">Điểm rủi ro</p>
            <p class="text-2xl font-headline font-bold">${riskScore}/100</p>
        `;

        // URL card - SAFE: Use textContent for URL
        const urlCard = document.createElement('div');
        urlCard.className = 'bg-surface-container-low p-4 rounded-xl';
        urlCard.innerHTML = `
            <p class="text-[10px] text-on-surface-variant font-headline mb-1 uppercase tracking-tighter">URL được kiểm tra</p>
            <p class="text-sm font-mono truncate">${this.escapeHtml(result.url)}</p>
        `;

        gridDiv.appendChild(scoreCard);
        gridDiv.appendChild(urlCard);
        resultsSection.appendChild(gridDiv);

        // Add fallback warning if needed
        if (result.fallback) {
            const fallbackDiv = document.createElement('div');
            fallbackDiv.className = 'mb-4 bg-yellow-500/10 border border-yellow-500/20 text-yellow-500 rounded-xl p-3 text-xs flex items-center gap-2';
            fallbackDiv.innerHTML = '<span class="material-symbols-outlined text-sm">info</span><span>Đang chạy ở chế độ dự phòng đối khớp mẫu (Không có kết nối VirusTotal API).</span>';
            resultsSection.appendChild(fallbackDiv);
        }

        // Reasons section
        const reasonsDiv = document.createElement('div');
        reasonsDiv.className = 'mb-4';

        const reasonsTitle = document.createElement('p');
        reasonsTitle.className = 'text-sm text-on-surface-variant mb-2';
        reasonsTitle.textContent = riskLevel === 'LOW' ? 'Chi tiết đánh giá:' : 'Các dấu hiệu đáng ngờ:';
        reasonsDiv.appendChild(reasonsTitle);

        const reasonsList = document.createElement('ul');
        reasonsList.className = 'space-y-2';

        if (result.reasons && result.reasons.length > 0) {
            result.reasons.forEach(reason => {
                const isSafe = reason.includes('0 công cụ') || reason.includes('Được quét bởi');
                const icon = isSafe ? 'check_circle' : 'warning';
                const colorClass = isSafe ? 'text-primary' : 'text-error';

                const reasonItem = document.createElement('li');
                reasonItem.className = 'flex items-center gap-2 text-sm';
                reasonItem.innerHTML = `
                    <span class="material-symbols-outlined ${colorClass} text-sm">${icon}</span>
                    <span>${this.escapeHtml(reason)}</span>
                `;
                reasonsList.appendChild(reasonItem);
            });
        } else {
            const defaultItem = document.createElement('li');
            defaultItem.className = 'flex items-center gap-2 text-sm';
            defaultItem.innerHTML = '<span class="material-symbols-outlined text-primary text-sm">check_circle</span><span>Không phát hiện dấu hiệu hoặc mẫu lừa đảo nào đáng ngờ.</span>';
            reasonsList.appendChild(defaultItem);
        }

        reasonsDiv.appendChild(reasonsList);
        resultsSection.appendChild(reasonsDiv);

        // Recommendation section
        const recommendationDiv = document.createElement('div');
        recommendationDiv.className = 'bg-surface-container-low p-4 rounded-xl';

        const recommendationTitle = document.createElement('p');
        recommendationTitle.className = 'text-sm font-semibold mb-2';
        recommendationTitle.textContent = 'Khuyến nghị:';

        const recommendationText = document.createElement('p');
        recommendationText.className = 'text-sm text-on-surface-variant';
        recommendationText.textContent = result.recommendation || 'Không có khuyến nghị.'; // SAFE: textContent prevents XSS

        recommendationDiv.appendChild(recommendationTitle);
        recommendationDiv.appendChild(recommendationText);
        resultsSection.appendChild(recommendationDiv);

        // Add results after the URL analysis section
        console.log('📍 Inserting results into DOM');

        // Try multiple selectors to find the URL section
        const urlSection = document.querySelector('section.col-span-12.lg\\:col-span-7') ||
                             document.querySelector('section[class*="col-span-7"]') ||
                             document.querySelector('.grid.grid-cols-12');

        if (urlSection && urlSection.parentNode) {
            console.log('✅ Found URL section, inserting results');
            urlSection.parentNode.insertBefore(resultsSection, urlSection.nextSibling);
        } else {
            console.error('❌ Could not find URL section container');
            // Fallback: append to the grid container
            const gridContainer = document.querySelector('.grid.grid-cols-12');
            if (gridContainer) {
                console.log('📌 Using fallback: appending to grid container');
                gridContainer.appendChild(resultsSection);
            }
        }

        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        console.log('✅ Results displayed and scrolled');

        this.addToScanHistory(result);
    }

    addToScanHistory(result) {
        const historyContainer = document.getElementById('scan-history');
        if (!historyContainer) return;

        const isEmptyState = historyContainer.querySelector('.text-center');
        if (isEmptyState) isEmptyState.remove();

        // VALIDATE: Ensure risk_level is valid
        const validRiskLevels = ['LOW', 'MEDIUM', 'HIGH'];
        const riskLevel = validRiskLevels.includes(result.risk_level) ? result.risk_level : 'LOW';

        const isSafe = riskLevel === 'LOW';
        const riskIcon = isSafe ? 'check_circle' : 'dangerous';
        const riskColor = isSafe ? 'text-primary' : 'text-error';
        const riskBg = isSafe ? 'bg-primary/10' : 'bg-error/10';
        const riskLabel = isSafe ? 'AN TOÀN' : 'PHÁT HIỆN MỐI ĐE DỌA';

        const now = new Date();
        const timeStr = now.toLocaleString('vi-VN');

        const entry = document.createElement('div');
        entry.className = 'bg-[#19191d] border border-white/[0.05] hover:bg-surface-container-high p-4 rounded-xl flex items-center justify-between transition-colors cursor-pointer';

        // SAFE: Use DOM manipulation for user-controlled content
        const leftDiv = document.createElement('div');
        leftDiv.className = 'flex items-center gap-4';

        const iconSpan = document.createElement('span');
        iconSpan.className = `material-symbols-outlined ${riskIcon} ${riskColor}`;
        iconSpan.setAttribute('aria-hidden', 'true');
        iconSpan.textContent = riskIcon;

        const textDiv = document.createElement('div');

        const urlParagraph = document.createElement('p');
        urlParagraph.className = 'font-headline font-bold';
        urlParagraph.textContent = result.url; // SAFE: textContent prevents XSS

        const timeParagraph = document.createElement('p');
        timeParagraph.className = 'text-xs text-on-surface-variant';
        timeParagraph.textContent = 'Đã quét vừa xong';

        textDiv.appendChild(urlParagraph);
        textDiv.appendChild(timeParagraph);
        leftDiv.appendChild(iconSpan);
        leftDiv.appendChild(textDiv);

        const riskBadge = document.createElement('span');
        riskBadge.className = `${riskColor} font-mono text-sm font-bold ${riskBg} px-3 py-1 rounded`;
        riskBadge.textContent = riskLabel;

        entry.appendChild(leftDiv);
        entry.appendChild(riskBadge);

        historyContainer.prepend(entry);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Sanitize numeric values to prevent XSS and injection attacks
     * @param {number|string} num - Value to sanitize
     * @returns {number} Sanitized number or 0 if invalid
     */
    sanitizeNumber(num) {
        const sanitized = parseFloat(num);
        return isNaN(sanitized) ? 0 : Math.max(0, Math.min(100, sanitized));
    }
}

// Initialize when DOM is ready and config is available
document.addEventListener('DOMContentLoaded', () => {
    // Prevent double initialization
    if (window.urlCheckerControllerInitialized) {
        console.warn('⚠️ URL checker controller already initialized, skipping duplicate initialization');
        return;
    }

    try {
        if (window.config) {
            console.log('✅ Config loaded, initializing URL checker controller');
            const urlChecker = new URLCheckerController();
            window.urlCheckerControllerInitialized = true;
        } else {
            console.warn('⚠️ Config not loaded, waiting...');
            setTimeout(() => {
                if (window.config && !window.urlCheckerControllerInitialized) {
                    console.log('✅ Config loaded after delay, initializing URL checker');
                    const urlChecker = new URLCheckerController();
                    window.urlCheckerControllerInitialized = true;
                } else {
                    console.error('❌ Config failed to load, URL checker cannot initialize');
                }
            }, 100);
        }
    } catch (error) {
        console.error('❌ Failed to initialize URL checker:', error);
    }
});
