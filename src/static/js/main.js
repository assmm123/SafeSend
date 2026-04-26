/**
 * SafeSend - Main JavaScript Application
 * SafeSend - تطبيق JavaScript الرئيسي
 * 
 * Handles WebSocket, PWA, chat, theme, language, and all UI interactions.
 * يدير WebSocket، PWA، المحادثة، السمة، اللغة، وجميع تفاعلات الواجهة.
 */

// ============================================================
// 🏗️ Main Application
// ============================================================

class SafeSendApp {
    constructor() {
        this.ws = null;
        this.user = null;
        this.token = null;
        this.init();
    }

    async init() {
        console.log('🛡️ SafeSend starting...');
        this.token = localStorage.getItem('safesend_token');
        
        ThemeManager.init();
        LanguageManager.init();
        
        if (this.token) {
            await this.loadUser();
            WebSocketManager.connect(this.token);
        }
        
        PWAManager.init();
        this.setupEventListeners();
        console.log('✅ SafeSend ready');
    }

    async loadUser() {
        try {
            const res = await fetch('/api/v1/auth/me', {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });
            if (res.ok) {
                const data = await res.json();
                this.user = data.user;
                console.log('👤 User loaded:', this.user.username);
            }
        } catch (e) {
            console.error('Failed to load user:', e);
        }
    }

    setupEventListeners() {
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-logout]')) {
                this.logout();
            }
            if (e.target.matches('[data-toggle-theme]')) {
                ThemeManager.toggle();
            }
            if (e.target.matches('[data-toggle-lang]')) {
                LanguageManager.toggle();
            }
        });
    }

    logout() {
        localStorage.removeItem('safesend_token');
        WebSocketManager.disconnect();
        window.location.href = '/login';
    }
}

// ============================================================
// 🔌 WebSocket Manager
// ============================================================

const WebSocketManager = {
    socket: null,
    reconnectTimer: null,
    listeners: {},

    connect(token) {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${location.host}/ws?token=${token}`;
        
        this.socket = new WebSocket(url);
        
        this.socket.onopen = () => {
            console.log('🔗 WebSocket connected');
            document.querySelectorAll('.connection-status')
                .forEach(el => { el.className = 'connection-status connected'; 
                    el.innerHTML = '<span class="status-dot status-dot-green"></span> متصل'; });
        };

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.emit(data.type, data);
        };

        this.socket.onclose = () => {
            console.log('🔌 WebSocket disconnected');
            document.querySelectorAll('.connection-status')
                .forEach(el => { el.className = 'connection-status disconnected';
                    el.innerHTML = '<span class="status-dot status-dot-red"></span> غير متصل'; });
            this.reconnect(token);
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    },

    reconnect(token) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = setTimeout(() => {
            console.log('🔄 Reconnecting...');
            this.connect(token);
        }, 5000);
    },

    disconnect() {
        clearTimeout(this.reconnectTimer);
        if (this.socket) this.socket.close();
    },

    send(type, data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({ type, ...data }));
        }
    },

    on(event, callback) {
        if (!this.listeners[event]) this.listeners[event] = [];
        this.listeners[event].push(callback);
    },

    emit(event, data) {
        if (this.listeners[event]) {
            this.listeners[event].forEach(cb => cb(data));
        }
    }
};

// ============================================================
// 📱 PWA Manager
// ============================================================

const PWAManager = {
    deferredPrompt: null,

    init() {
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/sw.js')
                    .then(reg => console.log('📲 SW registered:', reg.scope))
                    .catch(err => console.error('SW failed:', err));
            });
        }

        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.deferredPrompt = e;
            this.showInstallBanner();
        });

        window.addEventListener('online', () => this.updateStatus(true));
        window.addEventListener('offline', () => this.updateStatus(false));
    },

    showInstallBanner() {
        const banner = document.getElementById('install-banner');
        if (banner) {
            banner.style.display = 'flex';
            banner.querySelector('[data-install]').onclick = () => {
                this.deferredPrompt.prompt();
                this.deferredPrompt.userChoice.then(() => {
                    banner.style.display = 'none';
                });
            };
        }
    },

    updateStatus(online) {
        document.querySelectorAll('.connection-status').forEach(el => {
            if (online) {
                el.className = 'connection-status connected';
                el.innerHTML = '<span class="status-dot status-dot-green"></span> متصل';
            } else {
                el.className = 'connection-status disconnected';
                el.innerHTML = '<span class="status-dot status-dot-red"></span> غير متصل';
            }
        });
    }
};

// ============================================================
// 🎨 Theme Manager
// ============================================================

const ThemeManager = {
    init() {
        const saved = localStorage.getItem('safesend_theme') || 'light';
        this.set(saved);
    },

    set(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('safesend_theme', theme);
    },

    toggle() {
        const current = document.documentElement.getAttribute('data-theme');
        this.set(current === 'dark' ? 'light' : 'dark');
    }
};

// ============================================================
// 🌐 Language Manager
// ============================================================

const LanguageManager = {
    current: 'ar',

    init() {
        const saved = localStorage.getItem('safesend_lang') || 'ar';
        this.set(saved);
    },

    set(lang) {
        this.current = lang;
        document.documentElement.setAttribute('dir', lang === 'ar' ? 'rtl' : 'ltr');
        document.documentElement.setAttribute('lang', lang);
        localStorage.setItem('safesend_lang', lang);
        
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (this.translations[key]) {
                el.textContent = this.translations[key][lang];
            }
        });
    },

    toggle() {
        this.set(this.current === 'ar' ? 'en' : 'ar');
    },

    translations: {
        'app.name': { ar: 'SafeSend', en: 'SafeSend' },
        'nav.home': { ar: 'الرئيسية', en: 'Home' },
        'nav.chat': { ar: 'محادثات', en: 'Chat' },
        'nav.new': { ar: 'جديد', en: 'New' },
        'nav.alerts': { ar: 'تنبيهات', en: 'Alerts' },
        'nav.profile': { ar: 'حسابي', en: 'Profile' },
        'btn.login': { ar: 'تسجيل الدخول', en: 'Login' },
        'btn.register': { ar: 'إنشاء حساب', en: 'Register' },
        'btn.logout': { ar: 'تسجيل الخروج', en: 'Logout' },
        'btn.save': { ar: 'حفظ', en: 'Save' },
        'btn.cancel': { ar: 'إلغاء', en: 'Cancel' },
    }
};

// ============================================================
// 📦 Cache Manager
// ============================================================

const CacheManager = {
    store: new Map(),

    get(key) {
        const item = this.store.get(key);
        if (!item) return null;
        if (Date.now() > item.expiry) {
            this.store.delete(key);
            return null;
        }
        return item.data;
    },

    set(key, data, ttl = 300000) {
        this.store.set(key, {
            data,
            expiry: Date.now() + ttl
        });
    },

    clear() {
        this.store.clear();
    }
};

// ============================================================
// 📊 Performance Monitor
// ============================================================

const PerformanceMonitor = {
    metrics: {},

    start(label) {
        this.metrics[label] = performance.now();
    },

    end(label) {
        if (this.metrics[label]) {
            const duration = performance.now() - this.metrics[label];
            console.log(`⏱️ ${label}: ${duration.toFixed(2)}ms`);
            delete this.metrics[label];
            return duration;
        }
    }
};

// ============================================================
// ⚠️ Error Boundary
// ============================================================

window.addEventListener('error', (event) => {
    console.error('🚨 Unhandled error:', event.error);
    // Send to server for logging
    if (navigator.sendBeacon) {
        navigator.sendBeacon('/api/v1/logs/error', JSON.stringify({
            message: event.error?.message,
            stack: event.error?.stack?.substring(0, 500),
            url: location.href,
            timestamp: new Date().toISOString()
        }));
    }
});

// ============================================================
// 🚀 Initialize
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    window.safeSend = new SafeSendApp();
});
