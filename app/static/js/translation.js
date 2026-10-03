(function () {
    'use strict';

    const supportedLanguages = new Set(['en', 'hi', 'mr', 'kn']);
    const storageKey = 'bloodlink-language';
    const selector = document.getElementById('bloodlink-language-select');

    function readLanguage() {
        try {
            const stored = localStorage.getItem(storageKey);
            if (supportedLanguages.has(stored)) return stored;
        } catch (_) { /* Cookies still persist the preference when storage is unavailable. */ }
        const match = document.cookie.match(/(?:^|;\s*)googtrans=\/en\/(en|hi|mr|kn)(?:;|$)/);
        return match ? match[1] : 'en';
    }

    function saveLanguage(language) {
        if (!supportedLanguages.has(language)) return;
        try { localStorage.setItem(storageKey, language); } catch (_) { /* Cookie is the primary Google state. */ }
        const value = `/en/${language}`;
        document.cookie = `googtrans=${value}; path=/; SameSite=Lax`;
        if (location.hostname && location.hostname !== 'localhost') {
            document.cookie = `googtrans=${value}; path=/; domain=${location.hostname}; SameSite=Lax`;
        }
    }

    function applyLanguage(language) {
        saveLanguage(language);
        const combo = document.querySelector('.goog-te-combo');
        if (combo) {
            combo.value = language;
            combo.dispatchEvent(new Event('change'));
        }
    }

    function protectSensitiveValues() {
        const sensitiveValue = /^(?:[ABO]{1,2}[+-]|#?\d+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\+?[\d() .-]{7,})$/;
        document.querySelectorAll('body *').forEach(function (element) {
            if (element.children.length || element.getAttribute('translate') === 'no') return;
            if (sensitiveValue.test((element.textContent || '').trim())) element.setAttribute('translate', 'no');
        });
    }

    function restorePagePosition() {
        [document.documentElement, document.body].forEach(function (element) {
            if (!element) return;
            if (element.style.top && element.style.top !== '0px') element.style.top = '0px';
            if (element.style.marginTop && element.style.marginTop !== '0px') element.style.marginTop = '0px';
        });
    }

    window.googleTranslateElementInit = function () {
        new google.translate.TranslateElement({
            pageLanguage: 'en',
            includedLanguages: 'en,hi,mr,kn',
            autoDisplay: false
        }, 'google_translate_element');
        const language = readLanguage();
        if (selector) selector.value = language;
        restorePagePosition();
        if (language !== 'en') {
            const waitForWidget = window.setInterval(function () {
                if (document.querySelector('.goog-te-combo')) {
                    window.clearInterval(waitForWidget);
                    applyLanguage(language);
                }
            }, 100);
            window.setTimeout(function () { window.clearInterval(waitForWidget); }, 10000);
        }
    };

    if (selector) {
        const language = readLanguage();
        selector.value = language;
        selector.addEventListener('change', function () { applyLanguage(selector.value); });
    }

    document.addEventListener('click', async function (event) {
        const logoutButton = event.target.closest('[data-logout]');
        if (!logoutButton) return;
        logoutButton.disabled = true;
        try {
            await fetch('/api/logout', { method: 'POST' });
            window.location.href = '/';
        } catch (_) {
            logoutButton.disabled = false;
        }
    });

    const observer = new MutationObserver(function () {
        document.querySelectorAll('.goog-te-banner-frame, .goog-te-balloon-frame, #goog-gt-tt').forEach(function (node) {
            if (node.style.display !== 'none') node.style.display = 'none';
        });
        restorePagePosition();
        protectSensitiveValues();
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
    restorePagePosition();
    protectSensitiveValues();

    const positionObserver = new MutationObserver(restorePagePosition);
    positionObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class', 'style'] });
    positionObserver.observe(document.body, { attributes: true, attributeFilter: ['style'] });

    const script = document.createElement('script');
    script.src = 'https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';
    script.async = true;
    document.head.appendChild(script);
}());
