// UI helpers
const UI_TEXT = {
    commentRequired: 'Digite um comentario antes de enviar.',
    searchUsersHint: 'Busque por usuarios para encontrar perfis.',
    searchEventsHint: 'Busque por eventos usando titulo, local ou descricao.',
    searchUsersResults: (queryText) => `Resultados em usuarios para "${queryText}"`,
    searchEventsResults: (queryText) => `Resultados em eventos para "${queryText}"`
};

function setInlineError(inputEl, errorEl, message) {
    if (!inputEl || !errorEl) return;
    if (message) {
        errorEl.textContent = message;
        errorEl.classList.remove('hidden');
        inputEl.setAttribute('aria-invalid', 'true');
    } else {
        errorEl.textContent = '';
        errorEl.classList.add('hidden');
        inputEl.removeAttribute('aria-invalid');
    }
}

function togglePostDesc(postId, btn) {
    const p = document.getElementById('post-desc-' + postId);
    if (!p) return;
    const expanded = p.classList.toggle('desc-expanded');
    btn.innerText = expanded ? 'Ver menos' : 'Ver mais';
}

function initFeedEventDescriptionToggles(scope) {
    const root = scope || document;
    const buttons = root.querySelectorAll('[data-feed-desc-toggle]');
    buttons.forEach((btn) => {
        const postId = btn.getAttribute('data-feed-desc-toggle');
        const block = document.getElementById('post-desc-' + postId);
        if (!block) return;

        if (block.scrollHeight > block.clientHeight + 4) {
            btn.classList.remove('hidden');
            if (!block.classList.contains('desc-expanded')) {
                btn.innerText = 'Ver mais';
            }
        } else {
            btn.classList.add('hidden');
        }
    });
}

function showComments(postId, btn) {
    const extra = document.getElementById('extra-comments-' + postId);
    if (!extra) return;
    extra.classList.remove('hidden');
    btn.remove();
}

function ajaxLike(event, element) {
    event.preventDefault();
    // Mark request as AJAX to get JSON response from the server
    fetch(element.href, { headers: { 'X-Requested-With': 'XMLHttpRequest' } }).then((response) => {
        if (!response.ok) return;
        return response.json();
    }).then((data) => {
        if (!data) return;
        const span = element.querySelector('.like-count');
        if (typeof data.likes === 'number' && span) {
            span.innerText = String(data.likes);
        }

        const icon = element.querySelector('i');
        if (!icon) return;

        if (data.liked) {
            element.classList.add('text-red-500');
            icon.classList.remove('fa-regular');
            icon.classList.add('fa-solid');
        } else {
            element.classList.remove('text-red-500');
            icon.classList.remove('fa-solid');
            icon.classList.add('fa-regular');
        }
    }).catch((err) => {
        // network or parse error - ignore silently for now
        console.error('Like failed', err);
    });
}

function ajaxComment(event, form, postId) {
    event.preventDefault();
    const formData = new FormData(form);
    const input = form.querySelector('input[name="comment_content"]');
    const errorEl = form.parentElement ? form.parentElement.querySelector('[data-comment-error]') : null;
    const content = (input ? input.value : '').trim();

    if (!content) {
        setInlineError(input, errorEl, UI_TEXT.commentRequired);
        if (input) input.focus();
        return;
    }
    formData.set('comment_content', content);
    setInlineError(input, errorEl, '');

    // Disable submit button while processing
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.disabled = true;

    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    }).then((response) => {
        if (!response.ok) {
            console.error('Comment submission failed with status:', response.status);
            setInlineError(input, errorEl, 'Erro ao enviar comentário. Tente novamente.');
            if (submitBtn) submitBtn.disabled = false;
            return;
        }

        const container = document.getElementById('comments-container-' + postId);
        if (!container) {
            console.error('Comments container not found for post:', postId);
            setInlineError(input, errorEl, 'Erro ao atualizar comentários.');
            if (submitBtn) submitBtn.disabled = false;
            return;
        }

        const newComment = document.createElement('div');
        newComment.className = 'text-[13px] mb-1';
        const username = (window.__INDEX_PAGE__ && window.__INDEX_PAGE__.username) || '';
        const isAdmin = Boolean(window.__INDEX_PAGE__ && window.__INDEX_PAGE__.is_admin);
        const verifiedBadge = isAdmin
            ? '<i class="fa-solid fa-circle-check text-blue-500 text-[11px] ml-1" title="Conta verificada"></i>'
            : '';

        newComment.innerHTML = `
            <a href="/perfil/${username}" class="hover:underline">
                <span class="font-bold text-main">${username}</span>
            </a>
            ${verifiedBadge}
            <span class="text-main ml-1">${content}</span>
            <span class="text-secondary text-[11px] ml-1">&middot; agora</span>
        `;

        container.appendChild(newComment);
        input.value = '';
        setInlineError(input, errorEl, '');
        // Update visible comment count on the post if present
        try {
            const countSpan = document.querySelector(`#post-${postId} .comment-count`);
            if (countSpan) {
                const current = parseInt(countSpan.innerText || '0', 10) || 0;
                countSpan.innerText = String(current + 1);
            }
        } catch (e) {
            // ignore DOM update failures
            console.error('Failed to update comment count', e);
        }
        if (submitBtn) submitBtn.disabled = false;
    }).catch((error) => {
        console.error('Erro ao enviar comentário:', error);
        setInlineError(input, errorEl, 'Erro de conexão. Tente novamente.');
        if (submitBtn) submitBtn.disabled = false;
    });
}

// Search block
function createSearchController(dom) {
    const state = {
        liveSearchTimer: null,
        activeSearchRequest: null,
        currentCategory: dom.searchCategoryInput ? dom.searchCategoryInput.value : 'usuarios',
        expandedSearchEventIds: new Set()
    };

    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function setCategoryButtonStyles(selectedCategory) {
        dom.categoryButtons.forEach((button) => {
            const isActive = button.getAttribute('data-search-category') === selectedCategory;
            button.classList.toggle('bg-indigo-500', isActive);
            button.classList.toggle('text-white', isActive);
            button.classList.toggle('border-indigo-500', isActive);
            button.classList.toggle('text-main', !isActive);
        });
    }

    function setSearchHeading(category, queryText) {
        if (!dom.searchHeading) return;
        if (!queryText) {
            dom.searchHeading.textContent = category === 'eventos'
                ? UI_TEXT.searchEventsHint
                : UI_TEXT.searchUsersHint;
            return;
        }
        dom.searchHeading.textContent = category === 'eventos'
            ? UI_TEXT.searchEventsResults(queryText)
            : UI_TEXT.searchUsersResults(queryText);
    }

    function renderUserResults(users, queryText) {
        setSearchHeading('usuarios', queryText);
        if (!queryText) {
            dom.searchResultsRoot.innerHTML = '';
            return;
        }
        if (!users.length) {
            dom.searchResultsRoot.innerHTML = '<p class="text-center text-secondary text-sm">Nada encontrado.</p>';
            return;
        }

        dom.searchResultsRoot.innerHTML = `
            <div class="grid gap-3">
                ${users.map((user) => `
                    <div class="search-user-card p-3 rounded-xl border twitter-border flex items-center justify-between shadow-sm">
                        <div>
                            <p class="text-[14px] text-main font-bold">${escapeHtml(user.name || '')}</p>
                            <p class="text-[12px] text-secondary">@${escapeHtml(user.username || '')}</p>
                        </div>
                        <a href="/perfil/${encodeURIComponent(user.username || '')}" class="bg-indigo-600 text-white px-4 py-1.5 rounded-full text-xs font-bold hover:bg-indigo-700 transition">Ver</a>
                    </div>
                `).join('')}
            </div>
        `;
    }

    function renderSearchSkeleton(category) {
        if (category === 'eventos') {
            dom.searchResultsRoot.innerHTML = `
                <div class="grid gap-4">
                    <div class="event-card search-event-card overflow-hidden p-4">
                        <div class="search-skeleton h-5 w-3/5 mb-3"></div>
                        <div class="search-skeleton h-4 w-2/5 mb-4"></div>
                        <div class="search-skeleton h-3 w-full mb-2"></div>
                        <div class="search-skeleton h-3 w-11/12 mb-2"></div>
                        <div class="search-skeleton h-3 w-2/3 mb-4"></div>
                        <div class="search-skeleton h-8 w-40"></div>
                    </div>
                </div>
            `;
            return;
        }

        dom.searchResultsRoot.innerHTML = `
            <div class="grid gap-3">
                <div class="search-user-card p-3 rounded-xl border twitter-border shadow-sm">
                    <div class="search-skeleton h-4 w-2/5 mb-2"></div>
                    <div class="search-skeleton h-3 w-1/3"></div>
                </div>
                <div class="search-user-card p-3 rounded-xl border twitter-border shadow-sm">
                    <div class="search-skeleton h-4 w-1/2 mb-2"></div>
                    <div class="search-skeleton h-3 w-1/4"></div>
                </div>
            </div>
        `;
    }

    function toggleSearchEventDesc(eventId, buttonEl) {
        const desc = document.getElementById(`search-event-desc-${eventId}`);
        if (!desc || !buttonEl) return;
        const expanded = desc.classList.toggle('desc-expanded');
        if (expanded) {
            state.expandedSearchEventIds.add(String(eventId));
        } else {
            state.expandedSearchEventIds.delete(String(eventId));
        }
        buttonEl.textContent = expanded ? 'Ver menos' : 'Ver mais';
    }

    function initSearchEventDescriptionToggles(scope) {
        const root = scope || document;
        const buttons = root.querySelectorAll('[data-search-event-desc-toggle]');
        buttons.forEach((buttonEl) => {
            const eventId = buttonEl.getAttribute('data-search-event-desc-toggle');
            const desc = document.getElementById(`search-event-desc-${eventId}`);
            if (!desc) return;

            if (state.expandedSearchEventIds.has(String(eventId))) {
                desc.classList.add('desc-expanded');
                buttonEl.textContent = 'Ver menos';
            }

            if (desc.scrollHeight > desc.clientHeight + 4) {
                buttonEl.classList.remove('hidden');
                if (!desc.classList.contains('desc-expanded')) {
                    buttonEl.textContent = 'Ver mais';
                }
            } else {
                buttonEl.classList.add('hidden');
                state.expandedSearchEventIds.delete(String(eventId));
            }
        });
    }

    function renderEventResults(events, queryText) {
        setSearchHeading('eventos', queryText);
        if (!queryText) {
            dom.searchResultsRoot.innerHTML = '';
            return;
        }
        if (!events.length) {
            dom.searchResultsRoot.innerHTML = '<p class="text-center text-secondary text-sm">Nenhum evento encontrado.</p>';
            return;
        }

        dom.searchResultsRoot.innerHTML = `
            <div class="grid gap-4">
                ${events.map((event) => {
                    const mediaBlock = event.media_url
                        ? `<img src="/static/uploads/${encodeURIComponent(event.media_url)}" alt="Capa do evento ${escapeHtml(event.title || '')}" class="event-media h-40">`
                        : '';

                    return `
                        <article class="event-card search-event-card overflow-hidden">
                            ${mediaBlock}
                            <div class="p-4">
                                <div class="flex items-start justify-between gap-3 mb-3">
                                    <h3 class="event-title text-indigo-500 leading-tight">${escapeHtml(event.title || '')}</h3>
                                    <span class="event-meta-chip shrink-0"><i class="fa-regular fa-calendar-check text-[11px]"></i>${escapeHtml(event.event_date_label || '')}</span>
                                </div>
                                <p id="search-event-desc-${event.id}" class="event-description whitespace-pre-line mb-1 desc-container search-event-desc-fade">${escapeHtml(event.description || '')}</p>
                                <button type="button" data-search-event-desc-toggle="${event.id}" class="event-toggle-btn hidden text-indigo-500 mb-3 hover:underline focus:outline-none">Ver mais</button>
                                <div class="flex flex-wrap items-center gap-2 mb-3">
                                    <span class="event-meta-chip"><i class="fa-solid fa-location-dot text-[11px]"></i>${escapeHtml(event.location || '')}</span>
                                    <a href="/perfil/${encodeURIComponent(event.creator_username || '')}" class="event-author-link inline-flex items-center"><i class="fa-regular fa-circle-user mr-1"></i>@${escapeHtml(event.creator_username || '')}</a>
                                </div>
                                <div class="pt-3 border-t twitter-border flex items-center justify-end">
                                    <a href="/eventos" class="interactive-control text-xs font-bold text-indigo-500 hover:text-indigo-400 transition">Abrir em eventos</a>
                                </div>
                            </div>
                        </article>
                    `;
                }).join('')}
            </div>
        `;

        initSearchEventDescriptionToggles(dom.searchResultsRoot);
    }

    async function performLiveSearch() {
        const queryText = (dom.searchInput.value || '').trim();

        if (state.activeSearchRequest) {
            state.activeSearchRequest.abort();
        }
        state.activeSearchRequest = new AbortController();

        if (!queryText) {
            if (dom.searchLoading) dom.searchLoading.classList.add('hidden');
            if (state.currentCategory === 'eventos') {
                renderEventResults([], '');
            } else {
                renderUserResults([], '');
            }
            const params = new URLSearchParams();
            params.set('category', state.currentCategory);
            window.history.replaceState({}, '', '/search?' + params.toString());
            return;
        }

        try {
            if (dom.searchLoading) dom.searchLoading.classList.remove('hidden');
            renderSearchSkeleton(state.currentCategory);

            const params = new URLSearchParams();
            params.set('query', queryText);
            params.set('category', state.currentCategory);
            const response = await fetch('/api/search?' + params.toString(), {
                signal: state.activeSearchRequest.signal,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });
            if (!response.ok) return;

            const payload = await response.json();
            if (payload.category === 'eventos') {
                renderEventResults(payload.events || [], queryText);
            } else {
                renderUserResults(payload.users || [], queryText);
            }

            window.history.replaceState({}, '', '/search?' + params.toString());
        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error(error);
            }
        } finally {
            if (dom.searchLoading) dom.searchLoading.classList.add('hidden');
        }
    }

    function scheduleLiveSearch() {
        if (state.liveSearchTimer) clearTimeout(state.liveSearchTimer);
        state.liveSearchTimer = setTimeout(performLiveSearch, 240);
    }

    function init() {
        setCategoryButtonStyles(state.currentCategory);
        initSearchEventDescriptionToggles(document);

        dom.searchResultsRoot.addEventListener('click', (event) => {
            const toggleButton = event.target.closest('[data-search-event-desc-toggle]');
            if (!toggleButton) return;
            const eventId = toggleButton.getAttribute('data-search-event-desc-toggle');
            toggleSearchEventDesc(eventId, toggleButton);
        });

        dom.searchInput.addEventListener('input', scheduleLiveSearch);
        dom.searchInput.addEventListener('keydown', (event) => {
            if (event.key !== 'Enter') return;
            event.preventDefault();
            performLiveSearch();
        });

        if (dom.searchForm) {
            dom.searchForm.addEventListener('submit', (event) => {
                event.preventDefault();
                performLiveSearch();
            });
        }

        dom.categoryButtons.forEach((button) => {
            button.addEventListener('click', () => {
                state.currentCategory = button.getAttribute('data-search-category') || 'usuarios';
                dom.searchCategoryInput.value = state.currentCategory;
                setCategoryButtonStyles(state.currentCategory);
                performLiveSearch();
            });
        });
    }

    return { init };
}

// Feed block
function createFeedController(dom, pageCtx) {
    const state = {
        hasMore: Boolean(pageCtx.has_more),
        nextCursorTs: pageCtx.next_cursor_ts || null,
        nextCursorId: pageCtx.next_cursor_id || null,
        isLoading: false,
        feedObserver: null,
        debounceTimer: null,
        lastLoadTriggerAt: 0
    };
    const LOAD_DEBOUNCE_MS = 120;
    const LOAD_THROTTLE_MS = 350;

    async function loadMoreFeed() {
        if (state.isLoading || !state.hasMore || !dom.feedContainer) return;
        state.isLoading = true;
        if (dom.feedLoading) dom.feedLoading.classList.remove('hidden');

        try {
            const params = new URLSearchParams();
            if (state.nextCursorTs) params.set('cursor_ts', state.nextCursorTs);
            if (state.nextCursorId) params.set('cursor_id', String(state.nextCursorId));
            const response = await fetch('/feed/more?' + params.toString());
            if (!response.ok) return;

            const data = await response.json();
            if (data.html) {
                dom.feedContainer.insertAdjacentHTML('beforeend', data.html);
                initFeedEventDescriptionToggles(dom.feedContainer);
            }

            state.hasMore = Boolean(data.has_more);
            state.nextCursorTs = data.next_cursor_ts;
            state.nextCursorId = data.next_cursor_id;

            if (!state.hasMore && state.feedObserver) {
                state.feedObserver.disconnect();
            }
        } catch (error) {
            console.error(error);
        } finally {
            state.isLoading = false;
            if (dom.feedLoading) dom.feedLoading.classList.add('hidden');
        }
    }

    function scheduleLoadMoreFeed() {
        if (state.isLoading || !state.hasMore || !dom.feedContainer) return;
        const now = Date.now();
        if (now - state.lastLoadTriggerAt < LOAD_THROTTLE_MS) return;
        state.lastLoadTriggerAt = now;
        if (state.debounceTimer) clearTimeout(state.debounceTimer);
        state.debounceTimer = setTimeout(loadMoreFeed, LOAD_DEBOUNCE_MS);
    }

    function isNearPageBottom() {
        const threshold = 420;
        const doc = document.documentElement;
        return window.innerHeight + window.scrollY >= doc.scrollHeight - threshold;
    }

    function init() {
        if (!dom.feedSentinel) return;
        initFeedEventDescriptionToggles(document);

        state.feedObserver = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) scheduleLoadMoreFeed();
        }, { rootMargin: '300px 0px' });
        state.feedObserver.observe(dom.feedSentinel);

        window.addEventListener('scroll', () => {
            if (isNearPageBottom()) scheduleLoadMoreFeed();
        }, { passive: true });

        window.addEventListener('load', () => {
            if (isNearPageBottom()) scheduleLoadMoreFeed();
        });
    }

    return { init };
}

(function initIndexPage() {
    const pageCtx = window.__INDEX_PAGE__ || {};
    const isSearching = Boolean(pageCtx.searching);

    const dom = {
        feedPostForm: document.getElementById('feed-post-form'),
        feedPostContent: document.getElementById('feed-post-content'),
        feedPostError: document.getElementById('feed-post-error'),
        fileInput: document.getElementById('file-input'),
        imgPreview: document.getElementById('image-preview'),
        feedContainer: document.getElementById('feed-posts-container'),
        feedLoading: document.getElementById('feed-loading'),
        feedSentinel: document.getElementById('feed-sentinel'),
        searchCategoryInput: document.getElementById('search-category-input'),
        categoryButtons: document.querySelectorAll('[data-search-category]'),
        searchInput: document.getElementById('search-input'),
        searchHeading: document.getElementById('search-heading'),
        searchResultsRoot: document.getElementById('search-results-root'),
        searchForm: document.getElementById('search-form'),
        searchLoading: document.getElementById('search-loading')
    };

    if (dom.feedPostForm && dom.feedPostContent && dom.feedPostError) {
        dom.feedPostForm.addEventListener('submit', (event) => {
            if (!dom.feedPostContent.value.trim()) {
                event.preventDefault();
                setInlineError(dom.feedPostContent, dom.feedPostError, 'Digite algo para postar.');
                dom.feedPostContent.focus();
                return;
            }
            setInlineError(dom.feedPostContent, dom.feedPostError, '');
        });

        dom.feedPostContent.addEventListener('input', () => {
            if (dom.feedPostContent.value.trim()) {
                setInlineError(dom.feedPostContent, dom.feedPostError, '');
            }
        });
    }

    if (dom.fileInput && dom.imgPreview) {
        dom.fileInput.addEventListener('change', function () {
            const file = this.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = (e) => {
                dom.imgPreview.src = e.target.result;
                dom.imgPreview.style.display = 'block';
            };
            reader.readAsDataURL(file);
        });
    }

    const searchPageActive = Boolean(
        isSearching &&
        dom.searchInput &&
        dom.searchCategoryInput &&
        dom.searchHeading &&
        dom.searchResultsRoot
    );

    if (!isSearching) {
        createFeedController(dom, pageCtx).init();

        // If the page was opened with a fragment like #post-123 and the
        // element is not present in the initial chunk, progressively load
        // more feed chunks until the element appears (or no more chunks).
        (function ensureHashAnchorLoaded() {
            try {
                const hash = (location.hash || '').trim();
                if (!hash || !hash.startsWith('#post-')) return;
                const targetId = hash.slice(1);
                if (document.getElementById(targetId)) {
                    document.getElementById(targetId).scrollIntoView({ behavior: 'smooth', block: 'center' });
                    return;
                }

                // Use pageCtx's cursors to fetch additional chunks
                let nextCursorTs = pageCtx.next_cursor_ts || null;
                let nextCursorId = pageCtx.next_cursor_id || null;
                let hasMore = Boolean(pageCtx.has_more);
                const container = dom.feedContainer;
                if (!container || !hasMore) return;

                const fetchMoreUntilFound = async () => {
                    while (hasMore && !document.getElementById(targetId)) {
                        const params = new URLSearchParams();
                        if (nextCursorTs) params.set('cursor_ts', nextCursorTs);
                        if (nextCursorId) params.set('cursor_id', String(nextCursorId));
                        try {
                            const resp = await fetch('/feed/more?' + params.toString(), { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                            if (!resp.ok) break;
                            const data = await resp.json();
                            if (data.html) {
                                container.insertAdjacentHTML('beforeend', data.html);
                                initFeedEventDescriptionToggles(container);
                            }
                            hasMore = Boolean(data.has_more);
                            nextCursorTs = data.next_cursor_ts;
                            nextCursorId = data.next_cursor_id;
                            if (document.getElementById(targetId)) {
                                document.getElementById(targetId).scrollIntoView({ behavior: 'smooth', block: 'center' });
                                break;
                            }
                            // small delay between fetches
                            await new Promise(r => setTimeout(r, 120));
                        } catch (e) {
                            console.error('Failed to fetch feed/more for anchor resolution', e);
                            break;
                        }
                    }
                };

                fetchMoreUntilFound();
            } catch (err) {
                console.error('Anchor resolution failed', err);
            }
        })();
    }
    if (searchPageActive) {
        createSearchController(dom).init();
    }
})();


