/**
 * CyberSec Password Checker Controller
 * Manages password strength analysis functionality
 */
class PasswordCheckerController {
    constructor() {
        this.apiEndpoint = window.config.get('apiEndpoint');
        this.passwordStrengthEndpoint = window.config.get('passwordStrengthEndpoint');
        this.init();
    }

    init() {
        this.setupEventListeners();
        console.log('Password checker controller initialized');
    }

    setupEventListeners() {
        const passwordInput = document.getElementById('passwordInput');
        const visibilityButton = document.getElementById('visibilityButton');

        if (visibilityButton && passwordInput) {
            visibilityButton.addEventListener('click', () => this.togglePasswordVisibility(passwordInput, visibilityButton));
        }

        if (passwordInput) {
            // Add debounce to prevent API calls on every keystroke
            const debounceFn = window.debounce || (typeof debounce !== 'undefined' ? debounce : null);
            if (debounceFn) {
                const debouncedCheck = debounceFn((value) => {
                    this.checkPasswordStrength(value);
                }, 500); // Wait 500ms after user stops typing

                passwordInput.addEventListener('input', (e) => {
                    debouncedCheck(e.target.value);
                });
                console.log('✅ Password input listener with debounce added');
            } else {
                console.warn('⚠️ debounce function is not defined, adding listener without debounce');
                passwordInput.addEventListener('input', (e) => {
                    this.checkPasswordStrength(e.target.value);
                });
            }
        }
    }

    togglePasswordVisibility(passwordInput, button) {
        const icon = button.querySelector('.material-symbols-outlined');
        if (passwordInput.type === 'password') {
            passwordInput.type = 'text';
            icon.textContent = 'visibility_off';
        } else {
            passwordInput.type = 'password';
            icon.textContent = 'visibility';
        }
    }

    async checkPasswordStrength(password) {
        console.log('🔐 checkPasswordStrength called:', {
            passwordLength: password?.length,
            endpoint: this.passwordStrengthEndpoint
        });

        if (!password.trim()) {
            console.warn('⚠️ Empty password, showing empty state');
            this.showPasswordEmptyState();
            return;
        }

        console.log('🔵 Sending password strength API request:', {
            endpoint: this.passwordStrengthEndpoint,
            method: 'POST',
            passwordLength: password.length
        });

        try {
            const response = await fetch(this.passwordStrengthEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                    // Note: Authorization and X-User-ID headers are auto-injected by auth.js fetch interceptor
                },
                body: JSON.stringify({ password: password })
            });

            console.log('🟢 Password Strength API Response:', {
                status: response.status,
                ok: response.ok,
                statusText: response.statusText
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            console.log('🟢 Password Strength Response Data:', result);
            this.updatePasswordDisplay(result);

        } catch (error) {
            console.error('🔴 Password Strength API Error:', {
                message: error.message,
                stack: error.stack,
                endpoint: this.passwordStrengthEndpoint
            });
            this.showPasswordError(error.message);
        }
    }

    showPasswordEmptyState() {
        const strengthBars = document.querySelectorAll('.h-2');
        const strengthText = document.getElementById('passwordStrength');

        if (strengthBars.length) {
            strengthBars.forEach(bar => {
                bar.className = 'h-2 flex-1 rounded-full bg-surface-container-highest';
            });
        }

        if (strengthText) {
            strengthText.textContent = 'Độ mạnh: Chưa kiểm tra';
            strengthText.className = 'text-primary font-headline';
        }
    }

    showPasswordError(errorMessage) {
        const strengthBars = document.querySelectorAll('.h-2');
        const strengthText = document.getElementById('passwordStrength');

        if (strengthBars.length) {
            strengthBars.forEach(bar => {
                bar.className = 'h-2 flex-1 rounded-full bg-error';
            });
        }

        if (strengthText) {
            strengthText.textContent = 'Lỗi kiểm tra';
            strengthText.className = 'text-error font-headline';
        }

        console.error('Password check error:', errorMessage);
    }

    updatePasswordDisplay(result) {
        console.log('📊 Updating password display with result:', result);

        const strengthBars = document.querySelectorAll('.h-2');
        const strengthText = document.getElementById('passwordStrength');
        const crackTimeText = document.getElementById('passwordCrackTime');

        if (!strengthBars.length) {
            console.error('❌ No strength bars found in DOM');
            return;
        }
        if (!strengthText) {
            console.error('❌ No strength text element found');
            return;
        }
        if (!crackTimeText) {
            console.warn('⚠️ No crack time text element found (optional)');
        }

        console.log('✅ DOM elements found, updating display');

        // Update strength bars based on score
        const activeBars = Math.ceil(result.strength_score / 20);
        strengthBars.forEach((bar, index) => {
            if (index < activeBars) {
                bar.className = `h-2 flex-1 rounded-full ${this.getStrengthColor(result.strength_color)}`;
            } else {
                bar.className = 'h-2 flex-1 rounded-full bg-surface-container-highest';
            }
        });

        // Update text displays
        strengthText.textContent = `Độ mạnh: ${result.strength}`;
        if (crackTimeText) {
            crackTimeText.textContent = this.getEstimatedCrackTime(result.strength_score);
        }

        // Update audit parameters
        this.updateAuditParameters(result);

        console.log('✅ Password display updated successfully');
    }

    updateAuditParameters(result) {
        console.log('📋 Updating audit parameters');

        const auditList = document.querySelector('ul.space-y-4');
        if (!auditList) {
            console.error('❌ No audit list found in DOM');
            return;
        }

        console.log('✅ Found audit list, creating parameters');

        const parameters = [
            { label: 'Độ dài', value: `${result.password_length} ký tự`, status: result.password_length >= 12 ? 'Passed' : 'Warning' },
            { label: 'Chữ hoa', value: result.has_upper ? 'Đạt' : 'Thiếu', status: result.has_upper ? 'Passed' : 'Warning' },
            { label: 'Chữ thường', value: result.has_lower ? 'Đạt' : 'Thiếu', status: result.has_lower ? 'Passed' : 'Warning' },
            { label: 'Chữ số', value: result.has_digit ? 'Đạt' : 'Thiếu', status: result.has_digit ? 'Passed' : 'Warning' },
            { label: 'Ký tự đặc biệt', value: result.has_special ? 'Đạt' : 'Thiếu', status: result.has_special ? 'Passed' : 'Warning' },
        ];

        auditList.innerHTML = parameters.map(param => `
            <li class="flex items-center justify-between text-sm">
                <span class="text-on-surface-variant">${param.label}</span>
                <span class="${param.status === 'Passed' ? 'text-primary' : 'text-error'} font-mono">${param.value}</span>
            </li>
        `).join('');

        console.log('✅ Audit parameters updated');
    }

    getStrengthColor(strengthColor) {
        const colors = {
            'green': 'bg-primary',
            'blue': 'bg-blue-500',
            'yellow': 'bg-yellow-500',
            'red': 'bg-error'
        };
        return colors[strengthColor] || 'bg-surface-container-highest';
    }

    getEstimatedCrackTime(score) {
        if (score >= 80) return 'Hàng trăm năm';
        if (score >= 60) return 'Vài năm';
        if (score >= 40) return 'Vài tháng';
        if (score >= 20) return 'Vài ngày';
        return 'Ngay lập tức';
    }

    resetPasswordDisplay() {
        const strengthBars = document.querySelectorAll('.h-2');
        const strengthText = document.getElementById('passwordStrength');
        const crackTimeText = document.getElementById('passwordCrackTime');

        if (strengthBars.length) {
            strengthBars.forEach(bar => {
                bar.className = 'h-2 flex-1 rounded-full bg-surface-container-highest';
            });
        }

        if (strengthText) strengthText.textContent = 'Độ mạnh: Chưa kiểm tra';
        if (crackTimeText) crackTimeText.textContent = 'Thời gian crack: Không xác định';
    }
}

// Initialize when DOM is ready and config is available
document.addEventListener('DOMContentLoaded', () => {
    // Prevent double initialization
    if (window.passwordCheckerControllerInitialized) {
        console.warn('⚠️ Password checker controller already initialized, skipping duplicate initialization');
        return;
    }

    try {
        if (window.config) {
            console.log('✅ Config loaded, initializing password checker controller');
            const passwordChecker = new PasswordCheckerController();
            window.passwordCheckerControllerInitialized = true;
        } else {
            console.warn('⚠️ Config not loaded, waiting...');
            setTimeout(() => {
                if (window.config && !window.passwordCheckerControllerInitialized) {
                    console.log('✅ Config loaded after delay, initializing password checker');
                    const passwordChecker = new PasswordCheckerController();
                    window.passwordCheckerControllerInitialized = true;
                } else {
                    console.error('❌ Config failed to load, password checker cannot initialize');
                }
            }, 100);
        }
    } catch (error) {
        console.error('❌ Failed to initialize password checker:', error);
    }
});