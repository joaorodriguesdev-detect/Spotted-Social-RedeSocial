(function () {
    const conversationShell = document.querySelector('.conversation-shell');
    const scrollArea = document.getElementById('conversation-scroll-area');
    if (!scrollArea) return;
    const conversationId = parseInt((conversationShell && conversationShell.getAttribute('data-conversation-id')) || '', 10) || null;
    const currentUserId = parseInt((conversationShell && conversationShell.getAttribute('data-current-user-id')) || '', 10) || null;
    const currentUsername = ((conversationShell && conversationShell.getAttribute('data-current-username')) || '').trim().toLowerCase();
    const pinnedContainer = document.getElementById('conversation-pinned');
    const pinnedText = document.getElementById('conversation-pinned-text');
    const pinnedActionButton = document.getElementById('conversation-pinned-action');
    let socket = null;
    const renderedMessageIds = new Set();
    const activeTypers = new Set();
    let pinnedMessageId = null;
    let typingEmitTimeout = null;
    let markReadTimer = null;
    // Track pending fetch controllers so we can abort long-running requests when
    // the user navigates away (prevents infinite loading in some browsers/hosts).
    const pendingFetchControllers = new Set();

    function dcFetch(url, options) {
        options = options || {};
        const controller = new AbortController();
        options.signal = controller.signal;
        pendingFetchControllers.add(controller);
        // Ensure the controller is removed when the fetch settles
        return fetch(url, options).finally(function () {
            pendingFetchControllers.delete(controller);
        });
    }

    // Abort any pending requests when the user is unloading/navigating away.
    window.addEventListener('beforeunload', function () {
        pendingFetchControllers.forEach(function (c) { try { c.abort(); } catch (e) {} });
        pendingFetchControllers.clear();
    });

    // If the user clicks a normal same-origin anchor, abort pending requests
    // immediately (capture phase) so the browser can navigate without waiting
    // for in-flight fetches to complete.
    document.addEventListener('click', function (ev) {
        try {
            const a = ev.target.closest && ev.target.closest('a');
            if (!a || !a.href) return;
            const url = new URL(a.href, window.location.href);
            if (url.origin !== window.location.origin) return;
            // allow links that use target=_blank to proceed without aborting
            if (a.target && a.target.toLowerCase() === '_blank') return;
            pendingFetchControllers.forEach(function (c) { try { c.abort(); } catch (e) {} });
            pendingFetchControllers.clear();
        } catch (e) {
            // ignore
        }
    }, true);

    // UI-only behavior: open conversation already positioned at latest message.
    scrollArea.scrollTop = scrollArea.scrollHeight;

    initActionsMenu();
    initMediaModal();
    initConversationSearch();
    initGroupNavbar();
    initGroupPanels();
    initDirectInfoPanel();
    initPinnedMessage();

    const myReactionByMessage = {};
    let activeReplyContext = null;
    const REACTION_STAGGER_STEP_MS = 26;

    initReactions();
    initComposer();
    initRealtime();

    function formatClockFromIso(isoValue) {
        if (!isoValue) return '';
        const date = new Date(isoValue);
        if (Number.isNaN(date.getTime())) return '';
        const hh = String(date.getHours()).padStart(2, '0');
        const mm = String(date.getMinutes()).padStart(2, '0');
        return hh + ':' + mm;
    }

    function createReactionPickerForRealtime(isOutBubble) {
        const picker = document.createElement('div');
        picker.className = 'conversation-emoji-picker' + (isOutBubble ? ' conversation-emoji-picker--out' : '') + ' hidden';
        picker.setAttribute('data-emoji-picker', 'true');
        ['❤️', '😂', '😮', '🔥', '👏'].forEach(function (emoji) {
            const button = document.createElement('button');
            button.type = 'button';
            button.setAttribute('data-emoji', emoji);
            button.textContent = emoji;
            picker.appendChild(button);
        });
        return picker;
    }

    function createReactionToolsForRealtime(isOutBubble) {
        const tools = document.createElement('div');
        tools.className = 'conversation-reaction-tools';

        const reactionList = document.createElement('div');
        reactionList.className = 'conversation-reactions';
        reactionList.setAttribute('data-reaction-list', 'true');

        const trigger = document.createElement('button');
        trigger.type = 'button';
        trigger.className = 'conversation-reaction-trigger' + (isOutBubble ? ' conversation-reaction-trigger--out' : '');
        trigger.setAttribute('data-reaction-trigger', 'true');
        trigger.setAttribute('aria-label', 'Reagir com emoji');
        const smileIcon = document.createElement('i');
        smileIcon.className = 'fa-regular fa-face-smile';
        trigger.appendChild(smileIcon);

        tools.appendChild(reactionList);
        tools.appendChild(trigger);
        tools.appendChild(createReactionPickerForRealtime(isOutBubble));
        return tools;
    }

    function createRealtimeMessageRow(message) {
        const hasSenderId = Boolean(message && typeof message.sender_id !== 'undefined' && message.sender_id !== null);
        const isMine = hasSenderId
            ? Number(message.sender_id) === Number(currentUserId)
            : Boolean(message && message.is_mine);
        const row = document.createElement('div');
        row.className = 'conversation-row mb-3 flex' + (isMine ? ' justify-end' : '');
        row.setAttribute('data-group-content', 'mensagem');

        const bubble = document.createElement('div');
        bubble.className = 'conversation-bubble ' + (isMine ? 'conversation-bubble-out text-white text-sm' : 'conversation-bubble-in text-main text-sm');
        bubble.setAttribute('data-message-id', String(message.id));
        bubble.setAttribute('data-author', isMine ? 'Voce' : ('@' + (message.sender_username || 'usuario')));
        bubble.setAttribute('data-reply-preview', message.content || '');

        if (!isMine && message.sender_username) {
            const sender = document.createElement('p');
            sender.className = 'conversation-sender-label';
            sender.textContent = '@' + message.sender_username;
            bubble.appendChild(sender);
        }

        bubble.appendChild(document.createTextNode(message.content || ''));

        const clock = formatClockFromIso(message.created_at);
        const meta = document.createElement('span');
        meta.className = (isMine ? 'conversation-status' : '') + ' block mt-1 text-[10px] ' + (isMine ? 'text-white/80' : 'text-secondary');
        meta.textContent = isMine ? (clock + ' • entregue') : clock;
        bubble.appendChild(meta);

        const replyButton = document.createElement('button');
        replyButton.type = 'button';
        replyButton.className = 'conversation-bubble-action' + (isMine ? ' conversation-bubble-action--out' : '');
        replyButton.setAttribute('data-reply-trigger', 'true');
        replyButton.textContent = 'Responder';
        bubble.appendChild(replyButton);

        const pinButton = document.createElement('button');
        pinButton.type = 'button';
        pinButton.className = 'conversation-bubble-pin' + (isMine ? ' conversation-bubble-pin--out' : '');
        pinButton.setAttribute('data-pin-trigger', 'true');
        pinButton.setAttribute('aria-label', 'Fixar mensagem');
        pinButton.innerHTML = '<i class="fa-solid fa-thumbtack"></i>';
        bubble.appendChild(pinButton);

        bubble.appendChild(createReactionToolsForRealtime(isMine));
        row.appendChild(bubble);
        return row;
    }

    function appendRealtimeMessage(message) {
        if (!message || typeof message.id === 'undefined' || message.id === null) return;
        const messageId = String(message.id);
        if (renderedMessageIds.has(messageId)) return;
        renderedMessageIds.add(messageId);

        const row = createRealtimeMessageRow(message);
        const typingRow = scrollArea.querySelector('.conversation-typing-row');
        if (typingRow && typingRow.parentNode === scrollArea) {
            scrollArea.insertBefore(row, typingRow);
        } else {
            scrollArea.appendChild(row);
        }
        scrollArea.scrollTop = scrollArea.scrollHeight;
        syncPinnedBubbleState();
    }

    function normalizeMessageId(rawValue) {
        const parsed = parseInt(String(rawValue || ''), 10);
        return Number.isNaN(parsed) ? null : parsed;
    }

    function getMessagePreviewText(message) {
        if (!message) return '';
        const content = (message.content || '').trim();
        if (!content) return 'Mensagem sem texto';
        return content.length > 120 ? content.slice(0, 117) + '...' : content;
    }

    function syncPinnedBubbleState() {
        scrollArea.querySelectorAll('.conversation-bubble').forEach(function (bubble) {
            const bubbleMessageId = normalizeMessageId(bubble.getAttribute('data-message-id'));
            const isPinned = Boolean(pinnedMessageId && bubbleMessageId && bubbleMessageId === pinnedMessageId);
            bubble.classList.toggle('conversation-bubble--pinned', isPinned);
        });
    }

    function applyPinnedMessageUI(message) {
        pinnedMessageId = message && normalizeMessageId(message.id) ? normalizeMessageId(message.id) : null;

        if (!pinnedContainer || !pinnedText || !pinnedActionButton) {
            syncPinnedBubbleState();
            return;
        }

        if (!pinnedMessageId) {
            pinnedContainer.classList.add('hidden');
            pinnedText.textContent = '';
            pinnedActionButton.textContent = 'Desafixar';
            syncPinnedBubbleState();
            return;
        }

        const hasSenderId = Boolean(message && typeof message.sender_id !== 'undefined' && message.sender_id !== null);
        const isMine = hasSenderId
            ? Number(message.sender_id) === Number(currentUserId)
            : Boolean(message && message.is_mine);
        const sender = isMine ? 'Voce' : ('@' + (message.sender_username || 'usuario'));
        pinnedText.textContent = sender + ': ' + getMessagePreviewText(message);
        pinnedActionButton.textContent = 'Desafixar';
        pinnedContainer.classList.remove('hidden');
        syncPinnedBubbleState();
    }

    function requestPinMessage(nextMessageId) {
        if (!conversationId) return Promise.resolve();
        return dcFetch('/api/direct/conversations/' + conversationId + '/pin', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message_id: nextMessageId })
        }).then(function (response) {
            return response.ok ? response.json() : null;
        }).then(function (payload) {
            if (!payload) return;
            applyPinnedMessageUI(payload.pinned_message || null);
        }).catch(function () {
            // Keep current UI unchanged on transient failures.
        });
    }

    function handlePinTriggerClick(pinTrigger) {
        const bubble = pinTrigger.closest('.conversation-bubble');
        if (!bubble) return;
        const messageId = normalizeMessageId(bubble.getAttribute('data-message-id'));
        if (!messageId) return;
        const nextMessageId = pinnedMessageId === messageId ? null : messageId;
        requestPinMessage(nextMessageId);
    }

    function initPinnedMessage() {
        if (!pinnedActionButton) return;
        pinnedActionButton.addEventListener('click', function () {
            if (!pinnedMessageId) return;
            requestPinMessage(null);
        });
        applyPinnedMessageUI(null);
    }

    function renderTypingState() {
        const typingRow = scrollArea.querySelector('.conversation-typing-row');
        const typingText = document.getElementById('conversation-typing-text');
        if (!typingRow || !typingText) return;

        if (!activeTypers.size) {
            typingRow.classList.add('hidden');
            typingText.textContent = '';
            return;
        }

        const names = Array.from(activeTypers);
        const label = names.length === 1 ? '@' + names[0] + ' está digitando...' : names.slice(0, 2).map(function (name) { return '@' + name; }).join(', ') + ' estão digitando...';
        typingText.textContent = label;
        typingRow.classList.remove('hidden');
    }

    function emitTyping(isTyping) {
        if (!socket || !socket.connected || !conversationId) return;
        socket.emit('direct:typing', { conversation_id: conversationId, is_typing: Boolean(isTyping) });
    }

    function scheduleMarkConversationRead() {
        if (!conversationId) return;
        if (markReadTimer) {
            window.clearTimeout(markReadTimer);
        }
        markReadTimer = window.setTimeout(function () {
            dcFetch('/api/direct/conversations/' + conversationId + '/read', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            }).catch(function () {
                // Ignore transient errors; next refresh/sync will retry.
            });
        }, 120);
    }

    function initRealtime() {
        // If the server has disabled Direct globally, skip realtime initialization.
        if (typeof window.DIRECT_ENABLED !== 'undefined' && !window.DIRECT_ENABLED) {
            // Disable realtime features: leave polling/Socket.IO inactive.
            console.info('Direct is disabled by server; realtime features are inactive.');
            return;
        }
        if (!conversationId) return;

        function loadLatestMessages() {
            return dcFetch('/api/direct/conversations/' + conversationId + '/messages')
                .then(function (response) { return response.ok ? response.json() : null; })
                .then(function (payload) {
                    if (!payload || !Array.isArray(payload.messages)) return;
                    scrollArea.querySelectorAll('.conversation-row[data-group-content="mensagem"]').forEach(function (row) {
                        row.remove();
                    });
                    payload.messages.forEach(appendRealtimeMessage);
                    applyPinnedMessageUI(payload.pinned_message || null);
                })
                .catch(function () {
                    // Keep fallback UI when realtime API is unavailable.
                });
        }

        loadLatestMessages();

        window.setInterval(function () {
            if (document.visibilityState !== 'visible') return;
            dcFetch('/api/direct/conversations/' + conversationId + '/messages')
                .then(function (response) { return response.ok ? response.json() : null; })
                .then(function (payload) {
                    if (!payload || !Array.isArray(payload.messages)) return;
                    payload.messages.forEach(appendRealtimeMessage);
                    applyPinnedMessageUI(payload.pinned_message || null);
                })
                .catch(function () {
                    // Ignore transient polling errors.
                });
        }, 5000);

        if (typeof window.io !== 'function') return;
        // On some hosting providers (eg. pythonanywhere) long-polling socket.io
        // clients can hold worker requests open and block other synchronous
        // requests (POSTs to send messages). To avoid this class of failure we
        // disable realtime socket initialization when running on those hosts
        // and fall back to our regular short-polling GET above.
        try {
            var host = window.location && window.location.hostname ? window.location.hostname : '';
            var shouldDisableRealtime = typeof host === 'string' && host.endsWith('pythonanywhere.com');
        } catch (e) {
            var shouldDisableRealtime = false;
        }

        if (!shouldDisableRealtime) {
            // Let socket.io pick the best transport (do not force polling).
            socket = window.io();
        } else {
            // Keep socket as null so the client will use the periodic dcFetch polling
            // already scheduled above. This avoids holding long-lived XHRs on
            // hosts that cannot safely handle them.
            socket = null;
        }
        socket.on('connect', function () {
            socket.emit('direct:join', { conversation_id: conversationId });
        });
        socket.on('direct:message', function (payload) {
            if (!payload || payload.conversation_id !== conversationId) return;
            // If this is a message we just sent optimistically, remove the optimistic placeholder
            try {
                const isMine = Number(payload.sender_id) === Number(currentUserId);
                if (isMine) {
                    // match placeholder by local content (best-effort)
                    const placeholder = scrollArea.querySelector('.conversation-bubble[data-local-content="' + (payload.content || '').replace(/"/g, '\\"') + '"]');
                    if (placeholder) {
                        const row = placeholder.closest('.conversation-row');
                        if (row) row.remove();
                        const tempId = placeholder.getAttribute('data-message-id');
                        if (tempId) renderedMessageIds.delete(String(tempId));
                    }
                }
            } catch (e) {
                // ignore matching errors
            }

            appendRealtimeMessage(payload);
            const isIncoming = Number(payload.sender_id) !== Number(currentUserId);
            if (isIncoming && document.visibilityState === 'visible') {
                scheduleMarkConversationRead();
            }
        });
        socket.on('direct:typing', function (payload) {
            if (!payload || payload.conversation_id !== conversationId || !payload.username) return;
            const sender = String(payload.username).toLowerCase();
            if (sender === currentUsername) return;
            if (payload.is_typing) {
                activeTypers.add(sender);
            } else {
                activeTypers.delete(sender);
            }
            renderTypingState();
        });
        socket.on('direct:members-updated', function (payload) {
            if (!payload || payload.conversation_id !== conversationId) return;
            document.dispatchEvent(new CustomEvent('direct:members-updated', { detail: payload }));
        });
        socket.on('direct:group-updated', function (payload) {
            if (!payload || payload.conversation_id !== conversationId) return;
            document.dispatchEvent(new CustomEvent('direct:group-updated', { detail: payload }));
        });
        socket.on('direct:pinned-updated', function (payload) {
            if (!payload || payload.conversation_id !== conversationId) return;
            applyPinnedMessageUI(payload.pinned_message || null);
        });
        socket.on('direct:reaction-updated', function (payload) {
            if (!payload || payload.conversation_id !== conversationId) return;
            var msgId = String(payload.message_id || '');
            var bubble = scrollArea.querySelector('.conversation-bubble[data-message-id="' + msgId + '"]');
            if (!bubble) return;
            var reactionList = bubble.querySelector('[data-reaction-list]');
            if (!reactionList) return;
            var reactors = payload.reactors || {};
            var reactions = payload.reactions || {};
            // Clear existing pills
            reactionList.innerHTML = '';
            Object.keys(reactions).forEach(function (emoji) {
                var count = Number(reactions[emoji] || 0) || 0;
                var isMine = Array.isArray(reactors[emoji]) && reactors[emoji].indexOf(currentUsername) >= 0;
                var isOutBubble = bubble.classList.contains('conversation-bubble-out');
                setReactionCount(reactionList, emoji, count, isOutBubble, isMine);
                if (isMine) {
                    myReactionByMessage[msgId] = emoji;
                }
            });
        });

        // When server determines that ALL members have read a specific message,
        // update the outgoing bubble status from 'entregue' to 'lido' in realtime.
        socket.on('direct:message-all-read', function (payload) {
            try {
                if (!payload || payload.conversation_id !== conversationId) return;
                var msgId = String(payload.message_id || '');
                if (!msgId) return;
                var bubble = scrollArea.querySelector('.conversation-bubble[data-message-id="' + msgId + '"]');
                if (!bubble) return;
                // Only update outgoing bubbles (messages sent by current user)
                if (!bubble.classList.contains('conversation-bubble-out')) return;
                var status = bubble.querySelector('.conversation-status');
                if (!status) return;
                // Preserve the time prefix if present, replace the suffix with 'lido'
                var text = (status.textContent || '').trim();
                var parts = text.split('•');
                var timePart = parts.length ? parts[0].trim() : '';
                if (!timePart) {
                    // fallback to current time
                    timePart = formatCurrentTime();
                }
                status.textContent = timePart + ' • lido';
            } catch (e) {
                // Non-fatal; keep UI stable on unexpected payloads
                console.error('Failed to apply message-all-read update', e);
            }
        });

        socket.on('notification:new', function (payload) {
            if (!payload) return;
            // Update bell badge in header if present
            var notifAnchor = document.querySelector('a[href="/notificacoes"]');
            if (!notifAnchor) return;
            var badge = notifAnchor.querySelector('.notification-unread-badge');
            var next = 1;
            if (badge) {
                var cur = parseInt(badge.textContent || '0', 10) || 0;
                next = cur + 1;
                badge.textContent = next < 100 ? String(next) : '99+';
            } else {
                badge = document.createElement('span');
                badge.className = 'absolute -top-1 -right-1 bg-indigo-500 text-white text-[9px] w-4 h-4 rounded-full flex items-center justify-center font-bold notification-unread-badge';
                badge.textContent = '1';
                notifAnchor.appendChild(badge);
            }
        });

        window.addEventListener('focus', function () {
            if (document.visibilityState === 'visible') {
                scheduleMarkConversationRead();
            }
        });
    }

    function initActionsMenu() {
        const actionsTrigger = document.getElementById('conversation-actions-trigger');
        const actionsMenu = document.getElementById('conversation-actions-menu');
        if (!actionsTrigger || !actionsMenu) return;

        function setActionsMenuState(isOpen) {
            actionsTrigger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
            if (conversationShell) {
                conversationShell.classList.toggle('conversation-actions-menu-open', isOpen);
            }
        }

        function closeMenu() {
            actionsMenu.classList.add('hidden');
            setActionsMenuState(false);
        }

        function getMenuItems() {
            return Array.from(actionsMenu.querySelectorAll('[role="menuitem"]'));
        }

        function handleActionsTriggerClick(event) {
            event.stopPropagation();
            const willOpen = actionsMenu.classList.contains('hidden');
            actionsMenu.classList.toggle('hidden');
            setActionsMenuState(willOpen);
            if (willOpen) {
                const items = getMenuItems();
                if (items.length) items[0].focus();
            }
        }

        function handleOutsideActionsMenuClick(event) {
            if (!actionsMenu.classList.contains('hidden') && !actionsMenu.contains(event.target)) {
                closeMenu();
            }
        }

        function handleActionsMenuKeydown(event) {
            if (event.key === 'Escape') {
                closeMenu();
                actionsTrigger.focus();
                return;
            }

            if (actionsMenu.classList.contains('hidden')) {
                return;
            }

            const items = getMenuItems();
            if (!items.length) return;
            const currentIndex = items.indexOf(document.activeElement);

            if (event.key === 'ArrowDown') {
                event.preventDefault();
                const nextIndex = currentIndex < 0 ? 0 : (currentIndex + 1) % items.length;
                items[nextIndex].focus();
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                const prevIndex = currentIndex <= 0 ? items.length - 1 : currentIndex - 1;
                items[prevIndex].focus();
            }
        }

        actionsTrigger.addEventListener('click', handleActionsTriggerClick);
        document.addEventListener('click', handleOutsideActionsMenuClick);
        document.addEventListener('keydown', handleActionsMenuKeydown);
    }

    function initMediaModal() {
        const mediaModal = document.getElementById('conversation-media-modal');
        const mediaImage = mediaModal ? mediaModal.querySelector('.conversation-media-full') : null;
        const mediaCloseButton = document.getElementById('conversation-media-close');
        const mediaPreviewTriggers = Array.from(document.querySelectorAll('[data-media-preview="true"]'));
        const summaryModal = document.getElementById('conversation-group-summary-modal');
        const settingsModal = document.getElementById('conversation-group-settings-modal');
        if (!mediaModal || !mediaImage || !mediaCloseButton || !mediaPreviewTriggers.length) return;

        function closeMediaModal() {
            mediaModal.classList.add('hidden');
        }

        function showMediaModal() {
            if (summaryModal) summaryModal.classList.add('hidden');
            if (settingsModal) settingsModal.classList.add('hidden');
            mediaModal.classList.remove('hidden');
        }

        function handleMediaOverlayClick(event) {
            if (event.target === mediaModal) {
                closeMediaModal();
            }
        }

        mediaPreviewTriggers.forEach(function (trigger) {
            trigger.addEventListener('click', function () {
                const fullSrc = trigger.getAttribute('data-media-full');
                const thumbImage = trigger.querySelector('img');
                if (fullSrc) {
                    mediaImage.src = fullSrc;
                } else if (thumbImage && thumbImage.src) {
                    mediaImage.src = thumbImage.src;
                }
                showMediaModal();
            });
        });
        mediaCloseButton.addEventListener('click', closeMediaModal);
        mediaModal.addEventListener('click', handleMediaOverlayClick);
    }

    function initReactions() {
        scrollArea.addEventListener('click', handleScrollAreaClick);
        document.addEventListener('keydown', handleEscapeForPickers);
    }

    function initConversationSearch() {
        const searchToggleButtons = Array.from(document.querySelectorAll('[data-conversation-search-toggle]'));
        const searchPanel = document.getElementById('conversation-search-panel');
        const searchInput = document.getElementById('conversation-search-input');
        const searchClearButton = document.getElementById('conversation-search-clear');
        const searchCount = document.getElementById('conversation-search-count');
        if (!searchToggleButtons.length || !searchPanel || !searchInput || !searchClearButton || !searchCount) return;

        function updateSearchCountLabel(value, matchCount) {
            if (!value) {
                searchCount.textContent = 'Digite para buscar nas mensagens.';
                return;
            }
            const label = matchCount === 1 ? 'resultado' : 'resultados';
            searchCount.textContent = String(matchCount) + ' ' + label + ' para "' + value + '".';
        }

        function applyConversationSearch() {
            const query = searchInput.value.trim().toLowerCase();
            let matchCount = 0;

            scrollArea.querySelectorAll('.conversation-row').forEach(function (row) {
                const bubble = row.querySelector('.conversation-bubble');
                if (!bubble || bubble.classList.contains('conversation-bubble-system')) return;

                const bubbleText = (bubble.getAttribute('data-reply-preview') || bubble.textContent || '').toLowerCase();
                const isMatch = !query || bubbleText.indexOf(query) >= 0;
                row.classList.toggle('conversation-row--search-hidden', !isMatch);
                bubble.classList.toggle('conversation-bubble--search-hit', Boolean(query && isMatch));
                if (isMatch && query) {
                    matchCount += 1;
                }
            });

            updateSearchCountLabel(query, matchCount);
        }

        function toggleSearchPanel() {
            const willOpen = searchPanel.classList.contains('hidden');
            searchPanel.classList.toggle('hidden');
            if (willOpen) {
                searchInput.focus();
                searchInput.select();
                return;
            }
            searchInput.value = '';
            applyConversationSearch();
        }

        function clearSearch() {
            searchInput.value = '';
            applyConversationSearch();
            searchInput.focus();
        }

        searchToggleButtons.forEach(function (button) {
            button.addEventListener('click', toggleSearchPanel);
        });
        searchClearButton.addEventListener('click', clearSearch);
        searchInput.addEventListener('input', applyConversationSearch);
    }

    function initGroupNavbar() {
        const navbar = document.querySelector('[data-group-navbar]');
        if (!navbar) return;

        const tabButtons = Array.from(navbar.querySelectorAll('[data-group-tab]'));
        if (!tabButtons.length) return;

        const messageRows = Array.from(scrollArea.querySelectorAll('[data-group-content="mensagem"]'));
        const membersRow = scrollArea.querySelector('[data-group-members-row]');
        const typingRow = scrollArea.querySelector('.conversation-typing-row');
        const dayDivider = scrollArea.querySelector('.conversation-day-divider');
        const newDivider = scrollArea.querySelector('.conversation-new-divider');

        function setRowVisibility(row, isVisible) {
            if (!row) return;
            row.classList.toggle('conversation-row--group-hidden', !isVisible);
        }

        function setActiveTab(activeTab) {
            tabButtons.forEach(function (button) {
                const isActive = button.getAttribute('data-group-tab') === activeTab;
                button.classList.toggle('conversation-group-nav-pill--active', isActive);
            });

            if (activeTab === 'membros') {
                messageRows.forEach(function (row) {
                    setRowVisibility(row, false);
                });
                if (membersRow) membersRow.classList.remove('hidden');
                if (typingRow) typingRow.classList.add('hidden');
                if (dayDivider) dayDivider.classList.add('hidden');
                if (newDivider) newDivider.classList.add('hidden');
            } else {
                messageRows.forEach(function (row) {
                    setRowVisibility(row, true);
                });
                if (membersRow) membersRow.classList.add('hidden');
                if (typingRow) typingRow.classList.remove('hidden');
                if (dayDivider) dayDivider.classList.remove('hidden');
                if (newDivider) newDivider.classList.remove('hidden');
            }
        }

        tabButtons.forEach(function (button) {
            button.addEventListener('click', function () {
                const tab = button.getAttribute('data-group-tab') || 'conversa';
                setActiveTab(tab);
                scrollArea.scrollTop = 0;
            });
        });

        setActiveTab('conversa');
    }

    function initGroupPanels() {
        const summaryModal = document.getElementById('conversation-group-summary-modal');
        const summaryOpenButton = document.getElementById('conversation-open-summary');
        const infoTriggerButton = document.getElementById('conversation-info-trigger');
        const summaryCloseButton = document.getElementById('conversation-group-summary-close');
        const settingsModal = document.getElementById('conversation-group-settings-modal');
        const settingsOpenButton = document.getElementById('conversation-open-settings');
        const settingsCloseButton = document.getElementById('conversation-group-settings-close');
        const settingsCancelButton = document.getElementById('conversation-group-settings-cancel');
        const settingsForm = document.getElementById('conversation-group-settings-form');
        const leaveGroupButton = document.getElementById('conversation-leave-group-btn');
        const mediaModal = document.getElementById('conversation-media-modal');

        const groupTitle = document.getElementById('conversation-group-title');
        const groupInitial = document.getElementById('conversation-group-initial');
        const groupCount = document.getElementById('conversation-group-count');
        const summaryTitle = document.getElementById('conversation-summary-title');
        const summaryCount = document.getElementById('conversation-summary-count');
        const groupSubtitle = document.querySelector('.conversation-group-subtitle');
        const participantsContainer = document.querySelector('.conversation-participants');
        const summaryMembers = document.getElementById('conversation-summary-members');
        const membersRowList = document.getElementById('conversation-members-tab-list');

        if (!summaryModal) return;

        const currentUsername = ((conversationShell && conversationShell.getAttribute('data-current-username')) || '').trim().toLowerCase();
        const isGroupAdmin = Boolean(conversationShell && conversationShell.getAttribute('data-is-group-admin') === 'true');
        const adminMembersList = document.getElementById('conversation-admin-members-list');
        const addMemberInput = document.getElementById('conversation-add-member-input');
        const addMemberButton = document.getElementById('conversation-add-member-btn');
        const groupNameInput = document.getElementById('conversation-group-name-input');
        const groupPhotoInput = document.getElementById('conversation-group-photo-input');
        const groupPhotoPreview = document.getElementById('conversation-group-photo-preview');

        const initialMemberCards = Array.from((summaryMembers || document).querySelectorAll('[data-member-name]'));
        const initialMembers = initialMemberCards
            .map(function (card) {
                return (card.getAttribute('data-member-name') || '').trim().toLowerCase();
            })
            .filter(Boolean);
        const memberPictures = {};
        initialMemberCards.forEach(function (card) {
            const username = (card.getAttribute('data-member-name') || '').trim().toLowerCase();
            const pic = (card.getAttribute('data-member-pic') || '').trim();
            if (username) {
                memberPictures[username] = pic;
            }
        });

        let members = initialMembers.length ? initialMembers.slice() : [];
        let adminMembers = new Set();
        if (currentUsername && members.indexOf(currentUsername) >= 0) {
            adminMembers.add(currentUsername);
        }
        if (!adminMembers.size && members.length) {
            adminMembers.add(members[0]);
        }

        function closeActionsMenuIfOpen() {
            const trigger = document.getElementById('conversation-actions-trigger');
            const menu = document.getElementById('conversation-actions-menu');
            if (!trigger || !menu || menu.classList.contains('hidden')) return;
            menu.classList.add('hidden');
            trigger.setAttribute('aria-expanded', 'false');
            if (conversationShell) {
                conversationShell.classList.remove('conversation-actions-menu-open');
            }
        }

        function openModal(modal) {
            if (!modal) return;
            closeActionsMenuIfOpen();
            if (mediaModal) {
                mediaModal.classList.add('hidden');
            }
            modal.classList.remove('hidden');
        }

        function closeModal(modal) {
            if (!modal) return;
            modal.classList.add('hidden');
        }

        function formatMemberLabel(username) {
            return '@' + username;
        }

        function profileUrlFor(username) {
            return '/perfil/' + username;
        }

        function buildMemberAvatar(picFilename, username) {
            if (picFilename) {
                const img = document.createElement('img');
                img.src = '/static/uploads/' + picFilename;
                img.alt = 'Foto de @' + username;
                img.className = 'w-full h-full object-cover';
                return img;
            }
            return document.createTextNode(username.charAt(0).toUpperCase());
        }

        function syncMemberCountUI() {
            const label = String(members.length) + ' participantes';
            if (groupCount) {
                groupCount.textContent = '';
                const dot = document.createElement('span');
                dot.className = 'conversation-presence-dot';
                dot.setAttribute('aria-hidden', 'true');
                groupCount.appendChild(dot);
                groupCount.appendChild(document.createTextNode(' ' + label));
            }
            if (summaryCount) {
                summaryCount.textContent = label;
            }
            if (groupSubtitle) {
                groupSubtitle.textContent = label + ' • conversa ativa';
            }
        }

        function renderParticipantChips() {
            if (!participantsContainer) return;
            participantsContainer.innerHTML = '';
            members.forEach(function (username) {
                const chip = document.createElement('span');
                chip.className = 'conversation-chip';
                chip.setAttribute('data-member-name', username);
                chip.textContent = formatMemberLabel(username);
                participantsContainer.appendChild(chip);
            });
        }

        function closeAllMemberMenus() {
            document.querySelectorAll('.conversation-member-menu').forEach(function (menu) {
                menu.classList.add('hidden');
                menu.style.top = '';
                menu.style.left = '';
            });
        }

        function placeMemberMenu(triggerButton, menu) {
            if (!triggerButton || !menu) return;

            const triggerRect = triggerButton.getBoundingClientRect();
            const menuRect = menu.getBoundingClientRect();
            const viewportPadding = 8;

            let left = triggerRect.left - menuRect.width - 8;
            if (left < viewportPadding) {
                left = triggerRect.right + 8;
            }
            if (left + menuRect.width > window.innerWidth - viewportPadding) {
                left = window.innerWidth - menuRect.width - viewportPadding;
            }

            let top = triggerRect.top + (triggerRect.height / 2) - (menuRect.height / 2);
            if (top < viewportPadding) {
                top = viewportPadding;
            }
            if (top + menuRect.height > window.innerHeight - viewportPadding) {
                top = window.innerHeight - menuRect.height - viewportPadding;
            }

            menu.style.left = String(Math.round(left)) + 'px';
            menu.style.top = String(Math.round(top)) + 'px';
        }

        function removeMemberFromGroup(username) {
            if (!conversationId) return;
            dcFetch('/api/direct/conversations/' + conversationId + '/members/' + encodeURIComponent(username), {
                method: 'DELETE'
            });
        }

        function leaveGroup() {
            if (!conversationId) return;
            dcFetch('/api/direct/conversations/' + conversationId + '/leave', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            }).then(function (response) {
                return response.ok ? response.json() : null;
            }).then(function (payload) {
                if (!payload || !payload.ok) return;
                window.location.href = payload.redirect_url || '/direct';
            });
        }

        function setGroupPhotoPreview(picValue, fallbackName) {
            if (!groupPhotoPreview) return;
            if (picValue) {
                groupPhotoPreview.textContent = '';
                const img = document.createElement('img');
                img.src = picValue;
                img.alt = 'Foto do grupo';
                img.className = 'w-full h-full object-cover';
                groupPhotoPreview.appendChild(img);
                return;
            }
            const safe = (fallbackName || 'grupo').trim();
            groupPhotoPreview.textContent = safe ? safe.charAt(0).toUpperCase() : 'G';
        }

        function applyMembersPayload(memberItems) {
            if (!Array.isArray(memberItems)) return;
            members = [];
            adminMembers = new Set();
            Object.keys(memberPictures).forEach(function (key) {
                delete memberPictures[key];
            });

            memberItems.forEach(function (item) {
                const username = normalizeUsername(item.username || '');
                if (!username) return;
                if (members.indexOf(username) < 0) {
                    members.push(username);
                }
                const pic = (item.profile_pic || '').trim();
                memberPictures[username] = pic;
                if (item.is_admin) {
                    adminMembers.add(username);
                }
            });

            ensureAtLeastOneAdmin();
            renderAdminMembersList();
            renderAllMemberLists();
            syncMemberCountUI();
        }

        function loadMembersFromApi() {
            if (!conversationId) return;
            dcFetch('/api/direct/conversations/' + conversationId + '/members')
                .then(function (response) { return response.ok ? response.json() : null; })
                .then(function (payload) {
                    if (!payload || !Array.isArray(payload.members)) return;
                    applyMembersPayload(payload.members);
                })
                .catch(function () {
                    // Keep template-provided members as fallback.
                });
        }

        function renderMemberCards(container) {
            if (!container) return;
            container.innerHTML = '';
            members.forEach(function (username) {
                const card = document.createElement('div');
                card.className = 'conversation-member-card';
                card.setAttribute('data-member-name', username);
                card.setAttribute('data-member-pic', memberPictures[username] || '');

                const main = document.createElement('div');
                main.className = 'conversation-member-main';

                const avatar = document.createElement('div');
                avatar.className = 'conversation-member-avatar';
                const avatarContent = buildMemberAvatar(memberPictures[username] || '', username);
                avatar.appendChild(avatarContent);

                const textBlock = document.createElement('div');
                const name = document.createElement('p');
                name.className = 'conversation-member-name';
                name.textContent = formatMemberLabel(username);

                const role = document.createElement('p');
                role.className = 'conversation-member-meta text-secondary text-[10px]';
                role.textContent = adminMembers.has(username) ? 'Administrador' : 'Membro';

                textBlock.appendChild(name);
                textBlock.appendChild(role);
                main.appendChild(avatar);
                main.appendChild(textBlock);
                card.appendChild(main);

                const menuTrigger = document.createElement('button');
                menuTrigger.type = 'button';
                menuTrigger.className = 'conversation-member-menu-trigger';
                menuTrigger.setAttribute('data-member-menu-trigger', 'true');
                menuTrigger.setAttribute('aria-label', 'Acoes do participante');
                const ellipsisIcon = document.createElement('i');
                ellipsisIcon.className = 'fa-solid fa-ellipsis';
                menuTrigger.appendChild(ellipsisIcon);

                const menu = document.createElement('div');
                menu.className = 'conversation-member-menu hidden';

                const profileLink = document.createElement('a');
                profileLink.href = profileUrlFor(username);
                profileLink.className = 'conversation-member-menu-link';
                profileLink.textContent = 'Ver perfil';
                menu.appendChild(profileLink);

                if (isGroupAdmin && username !== currentUsername) {
                    const removeButton = document.createElement('button');
                    removeButton.type = 'button';
                    removeButton.className = 'conversation-member-menu-item';
                    removeButton.textContent = 'Remover do grupo';
                    removeButton.addEventListener('click', function () {
                        removeMemberFromGroup(username);
                    });
                    menu.appendChild(removeButton);
                }

                menuTrigger.addEventListener('click', function (event) {
                    event.stopPropagation();
                    const isHidden = menu.classList.contains('hidden');
                    closeAllMemberMenus();
                    if (!isHidden) {
                        menu.classList.add('hidden');
                        return;
                    }
                    menu.classList.remove('hidden');
                    placeMemberMenu(menuTrigger, menu);
                });

                card.appendChild(menuTrigger);
                card.appendChild(menu);

                container.appendChild(card);
            });
        }

        function ensureAtLeastOneAdmin() {
            if (adminMembers.size || !members.length) return;
            adminMembers.add(members[0]);
        }

        function renderAdminMembersList() {
            if (!adminMembersList) return;
            adminMembersList.innerHTML = '';

            members.forEach(function (username) {
                const row = document.createElement('div');
                row.className = 'conversation-admin-member-row';

                const name = document.createElement('span');
                name.className = 'conversation-admin-member-name';
                name.textContent = formatMemberLabel(username);

                const actions = document.createElement('div');
                actions.className = 'conversation-admin-member-actions';

                const toggleAdmin = document.createElement('button');
                toggleAdmin.type = 'button';
                toggleAdmin.className = 'conversation-admin-toggle';
                const isAdmin = adminMembers.has(username);
                toggleAdmin.textContent = isAdmin ? 'Remover admin' : 'Tornar admin';
                toggleAdmin.addEventListener('click', function () {
                    if (!conversationId) return;
                    const nextIsAdmin = !adminMembers.has(username);
                    dcFetch('/api/direct/conversations/' + conversationId + '/members/' + encodeURIComponent(username) + '/admin', {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ is_admin: nextIsAdmin })
                    });
                });

                let removeMember = null;
                if (username !== currentUsername) {
                    removeMember = document.createElement('button');
                    removeMember.type = 'button';
                    removeMember.className = 'conversation-admin-remove';
                    removeMember.textContent = 'Remover';
                    removeMember.addEventListener('click', function () {
                        removeMemberFromGroup(username);
                    });
                }

                actions.appendChild(toggleAdmin);
                if (removeMember) {
                    actions.appendChild(removeMember);
                }
                row.appendChild(name);
                row.appendChild(actions);
                adminMembersList.appendChild(row);
            });
        }

        function renderAllMemberLists() {
            renderParticipantChips();
            renderMemberCards(summaryMembers);
            renderMemberCards(membersRowList);
        }

        function normalizeUsername(rawValue) {
            return (rawValue || '').trim().replace(/^@+/, '').toLowerCase();
        }

        function refreshGroupIdentityUI(nameValue) {
            const safeName = (nameValue || '').trim() || 'grupo';
            if (groupTitle) groupTitle.textContent = safeName;
            if (summaryTitle) summaryTitle.textContent = safeName;
            if (groupInitial) {
                groupInitial.textContent = safeName.charAt(0).toUpperCase();
            }
        }

        function handleAddMember() {
            if (!addMemberInput) return;
            const normalized = normalizeUsername(addMemberInput.value);
            if (!normalized) return;
            if (!conversationId) return;
            dcFetch('/api/direct/conversations/' + conversationId + '/members', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: normalized })
            });
            addMemberInput.value = '';
            addMemberInput.focus();
        }

        function handleSettingsSave() {
            const nextName = groupNameInput ? groupNameInput.value : '';
            if (!conversationId) return;

            dcFetch('/api/direct/conversations/' + conversationId + '/group', {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: nextName
                })
            }).then(function (response) {
                return response.ok ? response.json() : null;
            }).then(function (payload) {
                if (!payload) return;
                refreshGroupIdentityUI(payload.title || nextName);
                setGroupPhotoPreview(payload.group_photo || '', payload.title || nextName);
                syncMemberCountUI();
                closeModal(settingsModal);
            });
        }

        if (groupPhotoInput && groupPhotoPreview) {
            groupPhotoInput.addEventListener('change', function () {
                const file = groupPhotoInput.files && groupPhotoInput.files[0];
                if (!file) return;
                const url = window.URL.createObjectURL(file);
                groupPhotoPreview.textContent = '';
                const previewImg = document.createElement('img');
                previewImg.src = url;
                previewImg.alt = 'Preview da foto do grupo';
                previewImg.className = 'w-full h-full object-cover';
                groupPhotoPreview.appendChild(previewImg);
            });
        }

        if (summaryOpenButton) {
            summaryOpenButton.addEventListener('click', function () {
                openModal(summaryModal);
            });
        }

        if (infoTriggerButton) {
            infoTriggerButton.addEventListener('click', function () {
                openModal(summaryModal);
            });
        }

        if (summaryCloseButton) {
            summaryCloseButton.addEventListener('click', function () {
                closeModal(summaryModal);
            });
        }

        if (settingsOpenButton && settingsModal) {
            settingsOpenButton.addEventListener('click', function () {
                openModal(settingsModal);
            });
        }

        if (settingsCloseButton) {
            settingsCloseButton.addEventListener('click', function () {
                closeModal(settingsModal);
            });
        }

        if (settingsCancelButton) {
            settingsCancelButton.addEventListener('click', function () {
                closeModal(settingsModal);
            });
        }

        document.querySelectorAll('[data-open-summary]').forEach(function (button) {
            button.addEventListener('click', function () {
                openModal(summaryModal);
            });
        });

        document.querySelectorAll('[data-open-settings]').forEach(function (button) {
            button.addEventListener('click', function () {
                if (!settingsModal) return;
                openModal(settingsModal);
            });
        });

        if (addMemberButton) {
            addMemberButton.addEventListener('click', handleAddMember);
        }
        if (addMemberInput) {
            addMemberInput.addEventListener('keydown', function (event) {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    handleAddMember();
                }
            });
        }

        if (settingsForm) {
            settingsForm.addEventListener('submit', function (event) {
                event.preventDefault();
                handleSettingsSave();
            });
        }

        if (leaveGroupButton) {
            leaveGroupButton.addEventListener('click', leaveGroup);
        }

        [summaryModal, settingsModal].forEach(function (modal) {
            if (!modal) return;
            modal.addEventListener('click', function (event) {
                if (event.target === modal) {
                    closeModal(modal);
                }
            });
        });

        document.addEventListener('keydown', function (event) {
            if (event.key !== 'Escape') return;
            closeAllMemberMenus();
            closeModal(summaryModal);
            closeModal(settingsModal);
        });

        document.addEventListener('click', function () {
            closeAllMemberMenus();
        });

        document.addEventListener('direct:members-updated', function (event) {
            const detail = event.detail || {};
            if (!conversationId || detail.conversation_id !== conversationId) return;
            applyMembersPayload(detail.members || []);
        });

        document.addEventListener('direct:group-updated', function (event) {
            const detail = event.detail || {};
            if (!conversationId || detail.conversation_id !== conversationId) return;
            const nextTitle = detail.title || '';
            refreshGroupIdentityUI(nextTitle);
            setGroupPhotoPreview(detail.group_photo || '', nextTitle);
        });

        window.addEventListener('resize', closeAllMemberMenus);
        document.addEventListener('scroll', closeAllMemberMenus, true);

        renderAllMemberLists();
        renderAdminMembersList();
        syncMemberCountUI();
        loadMembersFromApi();
    }

    function initDirectInfoPanel() {
        const infoTriggerButton = document.getElementById('conversation-info-trigger');
        const directInfoModal = document.getElementById('conversation-direct-info-modal');
        const directInfoCloseButton = document.getElementById('conversation-direct-info-close');
        const muteToggleButton = document.getElementById('conversation-direct-mute-toggle');
        if (!infoTriggerButton || !directInfoModal || !directInfoCloseButton) return;

        function getMuteStorageKey() {
            const safeUserId = currentUserId ? String(currentUserId) : 'anon';
            return 'direct:muted-conversations:' + safeUserId;
        }

        function readMutedConversationIds() {
            try {
                const raw = window.localStorage.getItem(getMuteStorageKey());
                const parsed = raw ? JSON.parse(raw) : [];
                return Array.isArray(parsed) ? parsed.map(function (item) { return Number(item); }) : [];
            } catch (error) {
                return [];
            }
        }

        function writeMutedConversationIds(ids) {
            try {
                window.localStorage.setItem(getMuteStorageKey(), JSON.stringify(ids));
            } catch (error) {
                // Ignore storage write failures.
            }
        }

        function isConversationMuted() {
            return readMutedConversationIds().indexOf(Number(conversationId)) >= 0;
        }

        function setConversationMuted(nextMuted) {
            const muted = readMutedConversationIds();
            const currentId = Number(conversationId);
            const hasCurrent = muted.indexOf(currentId) >= 0;
            if (nextMuted && !hasCurrent) {
                muted.push(currentId);
            }
            if (!nextMuted && hasCurrent) {
                const next = muted.filter(function (item) { return item !== currentId; });
                writeMutedConversationIds(next);
                return;
            }
            writeMutedConversationIds(muted);
        }

        function refreshMuteButton() {
            if (!muteToggleButton) return;
            const muted = isConversationMuted();
            muteToggleButton.textContent = muted ? 'Conversa silenciada' : 'Silenciar conversa';
            muteToggleButton.classList.toggle('conversation-group-action-chip--primary', muted);
        }

        function openModal() {
            refreshMuteButton();
            directInfoModal.classList.remove('hidden');
        }

        function closeModal() {
            directInfoModal.classList.add('hidden');
        }

        infoTriggerButton.addEventListener('click', openModal);
        directInfoCloseButton.addEventListener('click', closeModal);

        if (muteToggleButton) {
            muteToggleButton.addEventListener('click', function () {
                const nextMuted = !isConversationMuted();
                setConversationMuted(nextMuted);
                refreshMuteButton();
            });
        }

        directInfoModal.addEventListener('click', function (event) {
            if (event.target === directInfoModal) {
                closeModal();
            }
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') {
                closeModal();
            }
        });
    }

    function initComposer() {
        const composerForm = document.getElementById('conversation-composer-form');
        const messageInput = document.getElementById('direct-message-input');
        const sendButton = document.getElementById('conversation-send-button');
        const replyPreview = document.getElementById('conversation-reply-preview');
        const replyAuthor = document.getElementById('conversation-reply-author');
        const replyText = document.getElementById('conversation-reply-text');
        const replyCancelButton = document.getElementById('conversation-reply-cancel');

        if (!composerForm || !messageInput || !sendButton || !replyPreview || !replyAuthor || !replyText || !replyCancelButton) {
            return;
        }

        // Apply server-controlled Direct enabled/disabled state to composer UI
        function applyDirectEnabledState() {
            try {
                if (typeof window.DIRECT_ENABLED !== 'undefined' && !window.DIRECT_ENABLED) {
                    messageInput.placeholder = 'Direct desativado.';
                    messageInput.disabled = true;
                    sendButton.disabled = true;
                    composerForm.classList.add('conversation-composer--disabled');
                    sendButton.setAttribute('aria-disabled', 'true');
                    return false;
                }
                // Ensure composer is enabled when server allows Direct
                messageInput.disabled = false;
                composerForm.classList.remove('conversation-composer--disabled');
                sendButton.removeAttribute('aria-disabled');
                // Send button enabled/disabled will be managed by setSendButtonState()
                return true;
            } catch (e) {
                // On unexpected failures, default to enabled to avoid locking UI
                try { messageInput.disabled = false; sendButton.removeAttribute('aria-disabled'); composerForm.classList.remove('conversation-composer--disabled'); } catch (ee) {}
                return true;
            }
        }

        var _directAvailable = applyDirectEnabledState();
        if (!_directAvailable) {
            // Direct is disabled on server — keep composer inactive.
            return;
        }

        function setSendButtonState() {
            sendButton.disabled = messageInput.value.trim().length === 0;

            if (messageInput.value.trim()) {
                emitTyping(true);
                if (typingEmitTimeout) {
                    window.clearTimeout(typingEmitTimeout);
                }
                typingEmitTimeout = window.setTimeout(function () {
                    emitTyping(false);
                }, 1500);
            } else {
                emitTyping(false);
            }
        }

        function clearReplyContext() {
            activeReplyContext = null;
            replyPreview.classList.add('hidden');
            replyAuthor.textContent = '';
            replyText.textContent = '';
        }

        function setReplyContext(replyContext) {
            if (!replyContext) {
                clearReplyContext();
                return;
            }

            activeReplyContext = replyContext;
            replyAuthor.textContent = 'Respondendo a ' + replyContext.author;
            replyText.textContent = replyContext.text;
            replyPreview.classList.remove('hidden');
        }

        function createReactionPicker(isOutBubble) {
            const picker = document.createElement('div');
            picker.className = 'conversation-emoji-picker' + (isOutBubble ? ' conversation-emoji-picker--out' : '') + ' hidden';
            picker.setAttribute('data-emoji-picker', 'true');

            ['❤️', '😂', '😮', '🔥', '👏'].forEach(function (emoji) {
                const button = document.createElement('button');
                button.type = 'button';
                button.setAttribute('data-emoji', emoji);
                button.textContent = emoji;
                picker.appendChild(button);
            });

            return picker;
        }

        function createReactionTools(isOutBubble) {
            const tools = document.createElement('div');
            tools.className = 'conversation-reaction-tools';

            const reactionList = document.createElement('div');
            reactionList.className = 'conversation-reactions';
            reactionList.setAttribute('data-reaction-list', 'true');

            const reactionTrigger = document.createElement('button');
            reactionTrigger.type = 'button';
            reactionTrigger.className = 'conversation-reaction-trigger' + (isOutBubble ? ' conversation-reaction-trigger--out' : '');
            reactionTrigger.setAttribute('data-reaction-trigger', 'true');
            reactionTrigger.setAttribute('aria-label', 'Reagir com emoji');

            const reactionIcon = document.createElement('i');
            reactionIcon.className = 'fa-regular fa-face-smile';
            reactionTrigger.appendChild(reactionIcon);

            tools.appendChild(reactionList);
            tools.appendChild(reactionTrigger);
            tools.appendChild(createReactionPicker(isOutBubble));
            return tools;
        }

        function insertMessageRow(row) {
            const typingRow = scrollArea.querySelector('.conversation-typing-row');
            if (typingRow && typingRow.parentNode === scrollArea) {
                scrollArea.insertBefore(row, typingRow);
                return;
            }
            scrollArea.appendChild(row);
        }

        function formatCurrentTime() {
            const now = new Date();
            const hh = String(now.getHours()).padStart(2, '0');
            const mm = String(now.getMinutes()).padStart(2, '0');
            return hh + ':' + mm;
        }

        function createOutgoingMessageRow(messageText, replyContext) {
            const row = document.createElement('div');
            row.className = 'conversation-row mb-3 flex justify-end';

            const bubble = document.createElement('div');
            const messageId = 'local-' + String(Date.now()) + '-' + String(Math.floor(Math.random() * 1000));
            bubble.className = 'conversation-bubble conversation-bubble-out text-white text-sm';
            bubble.setAttribute('data-message-id', messageId);
            bubble.setAttribute('data-author', 'Voce');
            bubble.setAttribute('data-reply-preview', messageText);

            if (replyContext) {
                const quote = document.createElement('div');
                quote.className = 'conversation-quote mb-2 text-[11px]';

                const quoteAuthor = document.createElement('p');
                quoteAuthor.className = 'conversation-quote-author';
                quoteAuthor.textContent = 'Respondendo a ' + replyContext.author;

                const quoteText = document.createElement('p');
                quoteText.className = 'conversation-quote-text';
                quoteText.textContent = replyContext.text;

                quote.appendChild(quoteAuthor);
                quote.appendChild(quoteText);
                bubble.appendChild(quote);
            }

            const messageNode = document.createTextNode(messageText);
            bubble.appendChild(messageNode);

            const status = document.createElement('span');
            status.className = 'conversation-status block mt-1 text-[10px] text-white/80';
            status.textContent = formatCurrentTime() + ' • enviando';
            bubble.appendChild(status);

            const replyButton = document.createElement('button');
            replyButton.type = 'button';
            replyButton.className = 'conversation-bubble-action conversation-bubble-action--out';
            replyButton.setAttribute('data-reply-trigger', 'true');
            replyButton.textContent = 'Responder';
            bubble.appendChild(replyButton);

            const pinButton = document.createElement('button');
            pinButton.type = 'button';
            pinButton.className = 'conversation-bubble-pin conversation-bubble-pin--out';
            pinButton.setAttribute('data-pin-trigger', 'true');
            pinButton.setAttribute('aria-label', 'Fixar mensagem');
            const pinIcon = document.createElement('i');
            pinIcon.className = 'fa-solid fa-thumbtack';
            pinButton.appendChild(pinIcon);
            bubble.appendChild(pinButton);

            bubble.appendChild(createReactionTools(true));
            row.appendChild(bubble);

            return { row: row, status: status };
        }

        // Mark an outgoing bubble as failed and attach a retry button
        function markOutgoingAsFailed(bubble) {
            if (!bubble) return;
            bubble.classList.add('conversation-bubble--error');
            const status = bubble.querySelector('.conversation-status');
            if (status) status.textContent = (status.textContent || '').replace('enviando', 'falha');

            // If retry button already exists, skip
            if (bubble.querySelector('.conversation-retry-btn')) return;

            const retry = document.createElement('button');
            retry.type = 'button';
            retry.className = 'conversation-retry-btn';
            retry.setAttribute('aria-label', 'Tentar novamente');
            retry.textContent = 'Reenviar';

            retry.addEventListener('click', function (ev) {
                ev.preventDefault();
                ev.stopPropagation();
                // disable button to avoid double clicks
                retry.disabled = true;
                const localContent = bubble.getAttribute('data-local-content') || bubble.getAttribute('data-reply-preview') || '';
                if (!localContent) return;
                // Attempt resend
                dcFetch('/api/direct/conversations/' + conversationId + '/messages', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content: localContent })
                }).then(function (response) {
                    return response.ok ? response.json() : null;
                }).then(function (data) {
                    // On success, remove the optimistic bubble and append confirmed message or let socket handle it
                    try {
                        const row = bubble.closest('.conversation-row');
                        if (row) row.remove();
                        const tempId = bubble.getAttribute('data-message-id');
                        if (tempId) renderedMessageIds.delete(String(tempId));
                    } catch (e) {
                        // ignore
                    }
                    if (data && data.message && !(socket && socket.connected)) {
                        appendRealtimeMessage(data.message);
                    }
                }).catch(function () {
                    // re-enable retry to allow further attempts
                    retry.disabled = false;
                });
            });

            // Place retry button next to status
            if (status && status.parentNode) {
                status.parentNode.appendChild(retry);
            } else {
                bubble.appendChild(retry);
            }
        }

        function scheduleStatusProgress(statusNode) {
            window.setTimeout(function () {
                statusNode.textContent = statusNode.textContent.replace('enviando', 'entregue');
            }, 900);
            window.setTimeout(function () {
                statusNode.textContent = statusNode.textContent.replace('entregue', 'lido');
            }, 2400);
        }

        function handleComposerSubmit(event) {
            event.preventDefault();
            const messageText = messageInput.value.trim();
            if (!messageText) return;

            // Optimistic UI: render outgoing row immediately so user sees instant feedback
            const outgoing = createOutgoingMessageRow(messageText, activeReplyContext);
            const outgoingRow = outgoing.row;
            const outgoingStatus = outgoing.status;
            const bubble = outgoingRow.querySelector('.conversation-bubble');
            const localId = bubble.getAttribute('data-message-id');
            // tag with local content so we can match and remove it when server confirms
            bubble.setAttribute('data-local-content', messageText);
            scrollArea.appendChild(outgoingRow);
            scrollArea.scrollTop = scrollArea.scrollHeight;
            scheduleStatusProgress(outgoingStatus);
            // prevent duplicate rendering by marking temporary id as rendered
            renderedMessageIds.add(String(localId));

            const payload = {
                content: messageText
            };
            dcFetch('/api/direct/conversations/' + conversationId + '/messages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            }).then(function (response) {
                return response.ok ? response.json() : null;
            }).then(function (data) {
                if (!data || !data.message) {
                    // treat as failure
                    try { markOutgoingAsFailed(bubble); } catch (e) { /* ignore */ }
                    return;
                }
                // If socket is not connected, append the confirmed message directly and remove optimistic placeholder
                const incoming = data.message;
                if (!socket || !socket.connected) {
                    // remove optimistic placeholder matching the content if still present
                    try {
                        const placeholder = scrollArea.querySelector('.conversation-bubble[data-local-content="' + incoming.content.replace(/"/g, '\\"') + '"]');
                        if (placeholder) {
                            const row = placeholder.closest('.conversation-row');
                            if (row) row.remove();
                            const tempId = placeholder.getAttribute('data-message-id');
                            if (tempId) renderedMessageIds.delete(String(tempId));
                        }
                    } catch (e) {
                        // ignore matching errors
                    }
                    appendRealtimeMessage(incoming);
                }
            }).catch(function () {
                // Mark the optimistic row as failed and show retry UI
                try { markOutgoingAsFailed(bubble); } catch (e) { /* ignore */ }
            });

            emitTyping(false);
            messageInput.value = '';
            clearReplyContext();
            setSendButtonState();
        }

        messageInput.addEventListener('input', setSendButtonState);
        composerForm.addEventListener('submit', handleComposerSubmit);
        replyCancelButton.addEventListener('click', clearReplyContext);
        setSendButtonState();

        // Expose minimal hooks for delegated click handlers.
        scrollArea.setReplyContext = setReplyContext;
        scrollArea.clearReplyContext = clearReplyContext;
        scrollArea.focusComposerInput = function () {
            messageInput.focus();
        };
    }

    function closeAllEmojiPickers() {
        scrollArea.querySelectorAll('[data-emoji-picker]').forEach(function (picker) {
            picker.classList.add('hidden');
        });
    }

    function updatePickerSelection(bubble, selectedEmoji) {
        if (!bubble) return;
        const picker = bubble.querySelector('[data-emoji-picker]');
        if (!picker) return;

        picker.querySelectorAll('[data-emoji]').forEach(function (btn) {
            const isSelected = Boolean(selectedEmoji && btn.getAttribute('data-emoji') === selectedEmoji);
            btn.classList.toggle('conversation-emoji-option--selected', isSelected);
        });
    }

    function renderReactionPill(reactionList, emoji, count, isOutBubble, isMine) {
        const pill = document.createElement('span');
        pill.className = 'conversation-reaction-pill' + (isOutBubble ? ' conversation-reaction-pill--out' : '') + (isMine ? ' conversation-reaction-pill--mine' : '');
        pill.setAttribute('data-emoji', emoji);
        pill.setAttribute('data-count', String(count));
        pill.textContent = emoji + ' ' + count;
        reactionList.appendChild(pill);
        return pill;
    }

    function sortReactionPills(reactionList) {
        const pills = Array.from(reactionList.querySelectorAll('.conversation-reaction-pill'));
        pills.sort(function (a, b) {
            const countA = parseInt(a.getAttribute('data-count') || '0', 10) || 0;
            const countB = parseInt(b.getAttribute('data-count') || '0', 10) || 0;
            if (countA !== countB) {
                return countB - countA;
            }
            const emojiA = a.getAttribute('data-emoji') || '';
            const emojiB = b.getAttribute('data-emoji') || '';
            return emojiA.localeCompare(emojiB);
        });

        pills.forEach(function (pill, index) {
            reactionList.appendChild(pill);
            pill.style.setProperty('--reaction-stagger', String(index * REACTION_STAGGER_STEP_MS) + 'ms');
            pill.classList.remove('conversation-reaction-pill--reorder');
            void pill.offsetWidth;
            pill.classList.add('conversation-reaction-pill--reorder');
        });
    }

    function playReactionPop(pill) {
        if (!pill) return;
        pill.classList.remove('conversation-reaction-pill--pop');
        // Force reflow to restart animation when user reacts repeatedly.
        void pill.offsetWidth;
        pill.classList.add('conversation-reaction-pill--pop');
    }

    function findReactionPill(reactionList, emoji) {
        return reactionList.querySelector('[data-emoji="' + emoji + '"]');
    }

    function setReactionCount(reactionList, emoji, newCount, isOutBubble, isMine) {
        let pill = findReactionPill(reactionList, emoji);
        const previousCount = pill ? (parseInt(pill.getAttribute('data-count') || '0', 10) || 0) : 0;
        if (newCount <= 0) {
            if (pill) pill.remove();
            sortReactionPills(reactionList);
            return;
        }

        if (!pill) {
            pill = renderReactionPill(reactionList, emoji, newCount, isOutBubble, isMine);
        }

        pill.setAttribute('data-count', String(newCount));
        pill.textContent = emoji + ' ' + newCount;
        pill.classList.toggle('conversation-reaction-pill--mine', Boolean(isMine));
        sortReactionPills(reactionList);
        if (newCount > previousCount) {
            playReactionPop(pill);
        }
    }

    function getReactionCount(reactionList, emoji) {
        const pill = findReactionPill(reactionList, emoji);
        if (!pill) return 0;
        const value = parseInt(pill.getAttribute('data-count') || '0', 10);
        return Number.isNaN(value) ? 0 : value;
    }

    function applyReactionSelection(bubble, selectedEmoji) {
        if (!bubble) return;

        const messageId = bubble.getAttribute('data-message-id') || '';
        if (!messageId) return;

        const reactionList = bubble.querySelector('[data-reaction-list]');
        if (!reactionList) return;

        const isOutBubble = bubble.classList.contains('conversation-bubble-out');
        const previousEmoji = myReactionByMessage[messageId];

        if (previousEmoji === selectedEmoji) {
            const currentCount = getReactionCount(reactionList, selectedEmoji);
            setReactionCount(reactionList, selectedEmoji, currentCount - 1, isOutBubble, false);
            delete myReactionByMessage[messageId];
            updatePickerSelection(bubble, null);
            // Emit removal to server
            if (socket && socket.connected) {
                socket.emit('direct:react', { conversation_id: conversationId, message_id: Number(messageId), reaction: selectedEmoji });
            }
            return;
        }

        if (previousEmoji) {
            const oldCount = getReactionCount(reactionList, previousEmoji);
            setReactionCount(reactionList, previousEmoji, oldCount - 1, isOutBubble, false);
        }

        const currentCount = getReactionCount(reactionList, selectedEmoji);
        setReactionCount(reactionList, selectedEmoji, currentCount + 1, isOutBubble, true);
        myReactionByMessage[messageId] = selectedEmoji;
        updatePickerSelection(bubble, selectedEmoji);
        // Emit new reaction to server
        if (socket && socket.connected) {
            socket.emit('direct:react', { conversation_id: conversationId, message_id: Number(messageId), reaction: selectedEmoji });
        }
    }

    function handleReactionTriggerClick(triggerBtn) {
        const bubble = triggerBtn.closest('.conversation-bubble');
        if (!bubble) return;

        const picker = bubble.querySelector('[data-emoji-picker]');
        if (!picker) return;

        const messageId = bubble.getAttribute('data-message-id') || '';
        const wasHidden = picker.classList.contains('hidden');
        closeAllEmojiPickers();
        if (wasHidden) {
            updatePickerSelection(bubble, myReactionByMessage[messageId] || null);
            picker.classList.remove('hidden');
        }
    }

    function handleReactionPillClick(reactionPill) {
        const bubble = reactionPill.closest('.conversation-bubble');
        const selectedEmoji = reactionPill.getAttribute('data-emoji');
        if (!bubble || !selectedEmoji) return;

        applyReactionSelection(bubble, selectedEmoji);
        closeAllEmojiPickers();
    }

    function handleEmojiOptionClick(emojiBtn) {
        const bubble = emojiBtn.closest('.conversation-bubble');
        if (!bubble) return;

        const selectedEmoji = emojiBtn.getAttribute('data-emoji');
        if (!selectedEmoji) return;

        applyReactionSelection(bubble, selectedEmoji);
        closeAllEmojiPickers();
    }

    function handleScrollAreaClick(event) {
        const pinTrigger = event.target.closest('[data-pin-trigger]');
        if (pinTrigger) {
            handlePinTriggerClick(pinTrigger);
            return;
        }

        const replyTrigger = event.target.closest('[data-reply-trigger]');
        if (replyTrigger) {
            handleReplyTriggerClick(replyTrigger);
            return;
        }

        const triggerBtn = event.target.closest('[data-reaction-trigger]');
        if (triggerBtn) {
            handleReactionTriggerClick(triggerBtn);
            return;
        }

        const reactionPill = event.target.closest('.conversation-reaction-pill');
        if (reactionPill) {
            handleReactionPillClick(reactionPill);
            return;
        }

        const emojiBtn = event.target.closest('[data-emoji]');
        if (emojiBtn && emojiBtn.closest('[data-emoji-picker]')) {
            handleEmojiOptionClick(emojiBtn);
            return;
        }

        if (!event.target.closest('[data-emoji-picker]')) {
            closeAllEmojiPickers();
        }
    }

    function handleEscapeForPickers(event) {
        if (event.key === 'Escape') {
            closeAllEmojiPickers();
        }
    }

    function handleReplyTriggerClick(replyTrigger) {
        const bubble = replyTrigger.closest('.conversation-bubble');
        if (!bubble) return;

        const previewText = bubble.getAttribute('data-reply-preview') || '';
        const author = bubble.getAttribute('data-author') || inferBubbleAuthor(bubble);
        const setReplyContext = scrollArea.setReplyContext;
        const focusComposerInput = scrollArea.focusComposerInput;
        if (typeof setReplyContext !== 'function' || typeof focusComposerInput !== 'function') return;

        setReplyContext({
            author: author,
            text: previewText
        });
        focusComposerInput();
    }

    function inferBubbleAuthor(bubble) {
        if (bubble.classList.contains('conversation-bubble-out')) {
            return 'Voce';
        }
        const fallbackName = (conversationShell && conversationShell.getAttribute('data-target-username')) || 'contato';
        return '@' + fallbackName;
    }