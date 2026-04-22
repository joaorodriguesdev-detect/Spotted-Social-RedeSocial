(function () {
    var shell = document.querySelector('.direct-shell');
    if (!shell) {
        return;
    }

    // Ensure we have references to key DOM nodes before toggling state
    var composeBtn = document.getElementById('direct-new-message-trigger');
    var modal = document.getElementById('direct-new-modal');
    var closeBtn = document.getElementById('direct-new-modal-close');
    var backdrop = document.getElementById('direct-new-modal-backdrop');
    var groupModeToggle = document.getElementById('direct-create-group-toggle');
    var groupPanel = document.getElementById('direct-group-create-panel');
    var groupNameInput = document.getElementById('direct-group-name');
    var groupSelectedInfo = document.getElementById('direct-group-selected-info');
    var groupSelectedList = document.getElementById('direct-group-selected-list');
    var groupCreateSubmit = document.getElementById('direct-group-create-submit');
    var modalSearchInput = document.getElementById('direct-new-user-search');
    var modalModeHint = document.getElementById('direct-new-user-mode-hint');
    var resultsContainer = document.getElementById('direct-new-user-results');

    var searchForm = document.getElementById('direct-search-form');
    var inboxSearchInput = document.getElementById('direct-search-input');
    var filterInput = document.getElementById('direct-filter-input');
    var filterLinks = document.querySelectorAll('.direct-filters a[data-filter]');
    var listContainer = document.getElementById('direct-list');
    var conversationsCount = document.getElementById('direct-conversations-count');

    // If server disabled Direct, show a notice and disable compose actions early.
    if (typeof window.DIRECT_ENABLED !== 'undefined' && !window.DIRECT_ENABLED) {
        try {
            var notice = document.createElement('div');
            notice.className = 'dm-disabled-banner p-3 text-center text-sm text-secondary';
            notice.textContent = 'Direct desativado pelo sistema.';
            shell.insertBefore(notice, shell.firstChild);
            // Disable compose button if present
            if (composeBtn) try { composeBtn.disabled = true; } catch (e) {}
            if (listContainer) listContainer.innerHTML = '<div class="dm-empty-card rounded-2xl p-6 text-center text-secondary text-sm mx-2">Direct está desativado no momento.</div>';
        } catch (e) {
            // ignore DOM failures
        }
        return;
    }

    if (!composeBtn || !modal || !modalSearchInput || !resultsContainer) {
        return;
    }

    var composeDebounceTimer = null;
    var inboxDebounceTimer = null;
    var isFetchingInbox = false;
    var isGroupMode = false;
    var selectedGroupUsers = {};
    var lockedScrollY = 0;
    var touchStartY = null;

    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function escapeAttr(value) {
        return escapeHtml(value).replace(/`/g, '&#96;');
    }

    function lockPageScroll() {
        lockedScrollY = window.scrollY || window.pageYOffset || 0;
        document.documentElement.classList.add('direct-modal-open');
        document.body.classList.add('direct-modal-open');
        document.body.style.top = '-' + lockedScrollY + 'px';
    }

    function unlockPageScroll() {
        document.documentElement.classList.remove('direct-modal-open');
        document.body.classList.remove('direct-modal-open');
        document.body.style.top = '';
        window.scrollTo(0, lockedScrollY);
    }

    function getScrollableResultsTarget(target) {
        if (!(target instanceof HTMLElement) || !resultsContainer) {
            return null;
        }
        var scroller = target.closest('#direct-new-user-results');
        return scroller === resultsContainer ? resultsContainer : null;
    }

    function canScrollerMove(scroller, deltaY) {
        if (!scroller || scroller.scrollHeight <= scroller.clientHeight) {
            return false;
        }
        var atTop = scroller.scrollTop <= 0;
        var atBottom = scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 1;
        if (deltaY < 0 && atTop) {
            return false;
        }
        if (deltaY > 0 && atBottom) {
            return false;
        }
        return true;
    }

    function handleModalWheel(event) {
        var scroller = getScrollableResultsTarget(event.target);
        if (!scroller) {
            event.preventDefault();
            return;
        }
        if (!canScrollerMove(scroller, event.deltaY)) {
            event.preventDefault();
        }
    }

    function handleModalTouchStart(event) {
        if (!event.touches || !event.touches.length) {
            touchStartY = null;
            return;
        }
        touchStartY = event.touches[0].clientY;
    }

    function handleModalTouchMove(event) {
        var scroller = getScrollableResultsTarget(event.target);
        if (!scroller) {
            event.preventDefault();
            return;
        }
        if (!event.touches || !event.touches.length || touchStartY === null) {
            return;
        }
        var currentY = event.touches[0].clientY;
        var deltaY = touchStartY - currentY;
        if (!canScrollerMove(scroller, deltaY)) {
            event.preventDefault();
        }
    }

    function resetTouchState() {
        touchStartY = null;
    }

    function closeModal() {
        modal.classList.add('hidden');
        modal.setAttribute('aria-hidden', 'true');
        unlockPageScroll();
        modalSearchInput.value = '';
        resultsContainer.innerHTML = '';
        selectedGroupUsers = {};
        setGroupMode(false);
    }

    function openModal() {
        modal.classList.remove('hidden');
        modal.setAttribute('aria-hidden', 'false');
        lockPageScroll();
        modalSearchInput.focus();
        selectedGroupUsers = {};
        setGroupMode(false);
    }

    function updateGroupSelectedInfo() {
        if (!groupSelectedInfo) {
            return;
        }

        var usernames = Object.keys(selectedGroupUsers);
        if (!usernames.length) {
            groupSelectedInfo.textContent = 'Selecione participantes abaixo.';
            if (groupCreateSubmit) {
                groupCreateSubmit.disabled = isGroupMode;
            }
            return;
        }

        groupSelectedInfo.textContent = 'Selecionados (' + usernames.length + '): ' + usernames.map(function (u) {
            return '@' + u;
        }).join(', ');

        if (groupCreateSubmit) {
            groupCreateSubmit.disabled = false;
        }

        if (!groupSelectedList) {
            return;
        }

        if (!usernames.length) {
            groupSelectedList.innerHTML = '';
            return;
        }

        groupSelectedList.innerHTML = usernames.map(function (username) {
            var safeUsername = escapeHtml(username);
            return '<span class="direct-group-chip">@' + safeUsername + '<button type="button" data-remove-group-user="' + safeUsername + '" aria-label="Remover @' + safeUsername + '"><i class="fa-solid fa-xmark"></i></button></span>';
        }).join('');
    }

    function setGroupMode(enabled) {
        isGroupMode = !!enabled;
        if (!groupPanel || !groupModeToggle) {
            return;
        }

        if (isGroupMode) {
            groupPanel.classList.remove('hidden');
            groupModeToggle.classList.add('dm-pill-active');
            groupModeToggle.textContent = 'Cancelar grupo';
            modalSearchInput.placeholder = 'Buscar e selecionar integrantes por @username';
            if (modalModeHint) {
                modalModeHint.textContent = 'No modo grupo, clique no usuario para selecionar/remover integrante.';
            }
        } else {
            groupPanel.classList.add('hidden');
            groupModeToggle.classList.remove('dm-pill-active');
            groupModeToggle.textContent = 'Criar grupo';
            modalSearchInput.placeholder = 'Buscar usuario por @username';
            if (modalModeHint) {
                modalModeHint.textContent = 'Digite ao menos 2 caracteres para buscar e iniciar conversa.';
            }
            if (groupNameInput) {
                groupNameInput.value = '';
            }
            if (groupCreateSubmit) {
                groupCreateSubmit.disabled = false;
            }
        }

        updateGroupSelectedInfo();
    }

    function renderComposeMessage(message) {
        resultsContainer.innerHTML = '<p class="text-secondary text-sm px-3 py-4">' + escapeHtml(message) + '</p>';
    }

    function renderUsers(users) {
        if (!users || users.length === 0) {
            // When in group mode, clarify why results may be empty: only mutual followers
            renderComposeMessage(isGroupMode ? 'Nenhum usuário para selecionar. Apenas usuários que se seguem mutuamente aparecem aqui.' : 'Nenhum usuário encontrado.');
            return;
        }

        var html = '';
        for (var i = 0; i < users.length; i += 1) {
            var user = users[i] || {};
            var rawUsername = String(user.username || '').trim().toLowerCase();
            if (!rawUsername) {
                continue;
            }
            var username = escapeHtml(rawUsername);
            var name = escapeHtml(user.name || '');
            var profilePic = (user.profile_pic || '').trim();
            var safeProfilePic = profilePic ? escapeAttr(profilePic) : '';
            var avatarHtml = safeProfilePic
                ? '<img src="/static/uploads/' + safeProfilePic + '" alt="Avatar @' + username + '" class="w-full h-full object-cover">'
                : username.charAt(0).toUpperCase();

            var isSelected = Boolean(selectedGroupUsers[rawUsername]);
            var selectedClass = isSelected ? ' is-selected' : '';
            html += '<button type="button" class="direct-user-result-btn w-full text-left px-3 py-3' + selectedClass + '" data-username="' + username + '">';
            html += '<div class="flex items-center gap-2.5">';
            html += '<span class="direct-user-result-avatar">' + avatarHtml + '</span>';
            html += '<div class="flex-1 min-w-0">';
            html += '<p class="text-main font-semibold text-sm truncate">@' + username + '</p>';
            if (isGroupMode) {
                html += '<p class="text-secondary text-[11px] mt-0.5">' + (isSelected ? 'Selecionado para o grupo' : 'Clique para adicionar ao grupo') + '</p>';
            }
            if (name) {
                html += '<p class="text-secondary text-xs mt-0.5 truncate">' + name + '</p>';
            }
            html += '</div>';
            if (isSelected) {
                html += '<span class="direct-user-result-check" aria-hidden="true"><i class="fa-solid fa-check"></i></span>';
            }
            html += '</div>';
            html += '</button>';
        }

        resultsContainer.innerHTML = html;
    }

    function fetchUsers(rawQuery) {
        var query = (rawQuery || '').trim().replace(/^@+/, '');
        if (!isGroupMode && query.length < 2) {
            renderComposeMessage('Digite ao menos 2 caracteres para buscar.');
            return;
        }

        renderComposeMessage('Buscando...');
        fetch('/api/direct/users?q=' + encodeURIComponent(query), {
            credentials: 'same-origin'
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('Falha ao buscar usuarios');
                }
                return response.json();
            })
            .then(function (payload) {
                renderUsers(payload && payload.users ? payload.users : []);
            })
            .catch(function () {
                renderComposeMessage('Erro ao buscar usuarios. Tente novamente.');
            });
    }

    function openOrCreateConversation(username) {
        return fetch('/api/direct/conversations/start', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username: username })
        })
            .then(function (response) {
                return response.json().then(function (payload) {
                    return {
                        ok: response.ok,
                        payload: payload || {}
                    };
                });
            });
    }

    function createGroupConversation() {
        if (!groupNameInput || !groupCreateSubmit) {
            return;
        }

        var title = (groupNameInput.value || '').trim();
        if (!title) {
            renderComposeMessage('Informe um nome para o grupo.');
            return;
        }

        var usernames = Object.keys(selectedGroupUsers);
        if (!usernames.length) {
            renderComposeMessage('Selecione pelo menos 1 integrante para criar o grupo.');
            return;
        }
        groupCreateSubmit.disabled = true;
        fetch('/api/direct/groups', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                title: title,
                usernames: usernames
            })
        })
            .then(function (response) {
                return response.json().then(function (payload) {
                    return {
                        ok: response.ok,
                        payload: payload || {}
                    };
                });
            })
            .then(function (result) {
                // If server returned a structured error, show it to the user.
                if (!result.ok) {
                    var err = (result.payload && (result.payload.error || result.payload.message)) || 'Falha ao criar grupo';
                    renderComposeMessage(err);
                    return Promise.reject(new Error(err));
                }
                var url = result.payload && result.payload.url;
                if (!url) {
                    renderComposeMessage('Falha ao criar grupo. Resposta inesperada do servidor.');
                    return Promise.reject(new Error('no url'));
                }
                // Close modal and navigate to the newly created conversation
                try { closeModal(); } catch (e) {}
                window.location.href = url;
                return Promise.resolve();
            })
            .catch(function (err) {
                // If the promise was rejected earlier we already showed a message.
                if (typeof err === 'string') {
                    renderComposeMessage(err);
                }
                // Otherwise ensure there's a fallback message
                if (!resultsContainer.innerHTML || resultsContainer.innerHTML.indexOf('Falha') === -1) {
                    // only show generic when not already showing a specific error
                    renderComposeMessage('Nao foi possivel criar o grupo. Tente novamente.');
                }
            })
            .finally(function () {
                groupCreateSubmit.disabled = false;
            });
    }

    function applyFilterPillState(currentFilter) {
        for (var i = 0; i < filterLinks.length; i += 1) {
            var link = filterLinks[i];
            var isActive = link.getAttribute('data-filter') === currentFilter;
            if (isActive) {
                link.classList.add('dm-pill-active');
                link.classList.remove('text-main');
            } else {
                link.classList.remove('dm-pill-active');
                link.classList.add('text-main');
            }
        }
    }

    function formatRelativeTime(isoString) {
        if (!isoString) {
            return '';
        }

        var date = new Date(isoString);
        if (isNaN(date.getTime())) {
            return '';
        }

        var diffSeconds = Math.floor((Date.now() - date.getTime()) / 1000);
        if (diffSeconds < 0) {
            return 'agora';
        }
        if (diffSeconds < 60) {
            return 'agora';
        }
        if (diffSeconds < 3600) {
            return String(Math.floor(diffSeconds / 60)) + ' min';
        }
        if (diffSeconds < 86400) {
            return String(Math.floor(diffSeconds / 3600)) + ' h';
        }

        var diffDays = Math.floor(diffSeconds / 86400);
        if (diffDays < 30) {
            return String(diffDays) + ' d';
        }

        var day = String(date.getDate()).padStart(2, '0');
        var month = String(date.getMonth() + 1).padStart(2, '0');
        return day + '/' + month;
    }

    function buildDirectUrl(item) {
        var key = item.direct_key || item.slug || '';
        return '/direct/conversa/' + encodeURIComponent(key);
    }

    function renderConversationItem(item) {
        var title = escapeHtml(item.title || 'Conversa');
        var preview = escapeHtml(item.preview || 'Sem mensagens ainda.');
        var avatarText = escapeHtml((item.avatar_text || 'D').slice(0, 2));
        var avatarPic = item.avatar_pic ? escapeAttr(item.avatar_pic) : '';
        var timeLabel = escapeHtml(formatRelativeTime(item.time));
        var unreadCount = Number(item.unread_count || 0);
        var unreadBadge = '';

        if (unreadCount > 0) {
            unreadBadge = '<span class="dm-unread-badge">' + (unreadCount < 100 ? unreadCount : '99+') + '</span>';
        }

        var titlePrefix = item.is_group ? 'Grupo: ' : '';
        var avatarHtml = avatarPic
            ? '<img src="/static/uploads/' + avatarPic + '" class="w-full h-full object-cover" alt="Avatar da conversa ' + title + '">'
            : avatarText;

        return (
            '<a href="' + buildDirectUrl(item) + '" class="dm-row block no-underline px-4 py-3">' +
                '<div class="flex items-center gap-3">' +
                    '<div class="dm-avatar w-14 h-14 rounded-full bg-indigo-600/90 text-white flex items-center justify-center font-bold overflow-hidden">' +
                        avatarHtml +
                    '</div>' +
                    '<div class="flex-1 min-w-0">' +
                        '<div class="flex items-center justify-between gap-2">' +
                            '<p class="text-main font-bold text-[17px] truncate">' + titlePrefix + title + '</p>' +
                            '<span class="dm-row-time text-secondary text-xs">' + timeLabel + '</span>' +
                        '</div>' +
                        '<div class="flex items-center justify-between gap-2 mt-0.5">' +
                            '<p class="text-secondary text-[15px] leading-[1.2] truncate">' + preview + '</p>' +
                            unreadBadge +
                        '</div>' +
                    '</div>' +
                '</div>' +
            '</a>'
        );
    }

    function renderInbox(items) {
        if (!listContainer) {
            return;
        }

        if (!items || items.length === 0) {
            listContainer.innerHTML = (
                '<div class="dm-empty-card rounded-2xl p-6 text-center text-secondary text-sm mx-2">' +
                    'Nenhuma conversa ativa por enquanto.' +
                '</div>'
            );
        } else {
            var html = '';
            for (var i = 0; i < items.length; i += 1) {
                html += renderConversationItem(items[i] || {});
            }
            listContainer.innerHTML = html;
        }

        if (conversationsCount) {
            conversationsCount.textContent = String(items.length) + ' conversas';
        }
    }

    function updateUrlState(filter, query) {
        var url = new URL(window.location.href);
        url.searchParams.set('filter', filter || 'all');
        if (query) {
            url.searchParams.set('q', query);
        } else {
            url.searchParams.delete('q');
        }
        window.history.replaceState({}, '', url.toString());
    }

    function fetchInbox(options) {
        if (!searchForm || !inboxSearchInput || !filterInput || !listContainer) {
            return;
        }

        if (isFetchingInbox) {
            return;
        }

        var filter = (filterInput.value || 'all').toLowerCase();
        if (filter !== 'unread') {
            filter = 'all';
        }
        var query = (inboxSearchInput.value || '').trim().toLowerCase();

        isFetchingInbox = true;
        if (!options || !options.silent) {
            listContainer.innerHTML = '<p class="text-secondary text-sm px-3 py-4">Buscando...</p>';
        }

        var endpoint = '/api/direct/conversations?filter=' + encodeURIComponent(filter) + '&q=' + encodeURIComponent(query);
        fetch(endpoint, { credentials: 'same-origin' })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error('Falha ao carregar inbox');
                }
                return response.json();
            })
            .then(function (items) {
                var rows = Array.isArray(items) ? items : [];
                renderInbox(rows);
                applyFilterPillState(filter);
                updateUrlState(filter, query);
            })
            .catch(function () {
                if (!options || !options.silent) {
                    listContainer.innerHTML = '<p class="text-secondary text-sm px-3 py-4">Erro ao atualizar conversas. Tente novamente.</p>';
                }
            })
            .finally(function () {
                isFetchingInbox = false;
            });
    }

    composeBtn.addEventListener('click', openModal);

    if (closeBtn) {
        closeBtn.addEventListener('click', closeModal);
    }

    if (backdrop) {
        backdrop.addEventListener('click', closeModal);
    }

    modal.addEventListener('click', function (event) {
        var target = event.target;
        if (!(target instanceof HTMLElement)) {
            return;
        }

        var removeChipButton = target.closest('button[data-remove-group-user]');
        if (removeChipButton) {
            var removeUsername = removeChipButton.getAttribute('data-remove-group-user');
            if (removeUsername && selectedGroupUsers[removeUsername]) {
                delete selectedGroupUsers[removeUsername];
                updateGroupSelectedInfo();
                fetchUsers(modalSearchInput.value);
            }
            return;
        }

        var userButton = target.closest('button[data-username]');
        if (!userButton) {
            return;
        }

        var username = userButton.getAttribute('data-username');
        if (!username) {
            return;
        }

        if (isGroupMode) {
            if (selectedGroupUsers[username]) {
                delete selectedGroupUsers[username];
            } else {
                selectedGroupUsers[username] = true;
            }
            updateGroupSelectedInfo();
            fetchUsers(modalSearchInput.value);
            return;
        }

        openOrCreateConversation(username)
            .then(function (result) {
                if (!result.ok || !result.payload || !result.payload.url) {
                    throw new Error('Falha ao iniciar conversa');
                }
                window.location.href = result.payload.url;
            })
            .catch(function () {
                renderComposeMessage('Nao foi possivel iniciar a conversa. Tente novamente.');
            });
    });

    modal.addEventListener('wheel', handleModalWheel, { passive: false });
    modal.addEventListener('touchstart', handleModalTouchStart, { passive: true });
    modal.addEventListener('touchmove', handleModalTouchMove, { passive: false });
    modal.addEventListener('touchend', resetTouchState, { passive: true });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && !modal.classList.contains('hidden')) {
            closeModal();
        }
    });

    modalSearchInput.addEventListener('input', function () {
        if (composeDebounceTimer) {
            clearTimeout(composeDebounceTimer);
        }

        var value = modalSearchInput.value;
        composeDebounceTimer = setTimeout(function () {
            fetchUsers(value);
        }, 220);
    });

    if (searchForm && inboxSearchInput && filterInput && listContainer) {
        searchForm.addEventListener('submit', function (event) {
            event.preventDefault();
            fetchInbox();
        });

        inboxSearchInput.addEventListener('input', function () {
            if (inboxDebounceTimer) {
                clearTimeout(inboxDebounceTimer);
            }
            inboxDebounceTimer = setTimeout(function () {
                fetchInbox({ silent: true });
            }, 260);
        });

        for (var i = 0; i < filterLinks.length; i += 1) {
            filterLinks[i].addEventListener('click', function (event) {
                event.preventDefault();
                var selected = this.getAttribute('data-filter') || 'all';
                filterInput.value = selected === 'unread' ? 'unread' : 'all';
                fetchInbox();
            });
        }

        setInterval(function () {
            if (document.visibilityState === 'visible') {
                fetchInbox({ silent: true });
            }
        }, 15000);
    }

    if (groupModeToggle) {
        groupModeToggle.addEventListener('click', function () {
            setGroupMode(!isGroupMode);
            fetchUsers(modalSearchInput.value);
        });
    }

    if (groupCreateSubmit) {
        groupCreateSubmit.addEventListener('click', createGroupConversation);
    }
})();
