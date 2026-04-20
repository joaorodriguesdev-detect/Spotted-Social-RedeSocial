(function () {
    var prefersReducedMotion = false;
    try {
        prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch (err) {
        prefersReducedMotion = false;
    }

    if (prefersReducedMotion) {
        return;
    }

    function isModifiedClick(event) {
        return event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0;
    }

    document.addEventListener('click', function (event) {
        var link = event.target.closest && event.target.closest('a.js-page-transition');
        if (!link) {
            return;
        }

        if (isModifiedClick(event) || link.hasAttribute('download') || (link.target && link.target !== '_self')) {
            return;
        }

        var href = link.getAttribute('href') || '';
        if (!href || href.charAt(0) === '#') {
            return;
        }

        var targetUrl;
        try {
            targetUrl = new URL(href, window.location.origin);
        } catch (err) {
            return;
        }

        if (targetUrl.origin !== window.location.origin || targetUrl.pathname === window.location.pathname) {
            return;
        }

        var pageShell = document.querySelector('.app-page-shell');
        if (!pageShell) {
            return;
        }

        event.preventDefault();
        pageShell.classList.add('is-leaving');

        window.setTimeout(function () {
            window.location.href = targetUrl.href;
        }, 120);
    }, true);
})();

