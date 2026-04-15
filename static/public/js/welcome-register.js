// JS for welcome/register modal: autocomplete, validation, modal open/close
(function(){
    const universities = ["UFPR","UTFPR","PUCPR","UP","UTP","UniCuritiba","FAE","Outra"];

    const openBtn = document.getElementById('open-reg-modal');
    const modal = document.getElementById('modal-registro');
    const closeBtn = document.getElementById('close-reg-modal');

    const nameEl = document.getElementById('reg-name');
    const usernameEl = document.getElementById('reg-username');
    const uniEl = document.getElementById('reg-university');
    const uniList = document.getElementById('uni-list');
    const passEl = document.getElementById('reg-password');
    const submitBtn = document.getElementById('registro-submit');
    const otherWrapper = document.getElementById('other-uni-wrapper');
    const otherInput = document.getElementById('reg-university-other');
    const otherErr = document.getElementById('err-university-other');

    const errName = document.getElementById('err-name');
    const errUser = document.getElementById('err-username');
    const errUni = document.getElementById('err-university');
    const errPass = document.getElementById('err-password');

    let _focusHandler = null;
    let _previousActive = null;

    function openModal(){
        _previousActive = document.activeElement;
        modal.classList.remove('hidden');
        document.body.classList.add('modal-open');
        // set focus to first input shortly after open
        setTimeout(()=> { nameEl && nameEl.focus(); }, 120);
        // install focus trap
        installFocusTrap();
    }

    function closeModal(){
        modal.classList.add('hidden');
        document.body.classList.remove('modal-open');
        removeFocusTrap();
        if(uniPortal){ uniPortal.classList.add('hidden'); }
        setActiveIndex(-1);
        // return focus to opener
        try{ openBtn && openBtn.focus(); }catch(e){}
        // restore previous active if any
        try{ _previousActive && _previousActive.focus(); }catch(e){}
    }

    if(openBtn) openBtn.addEventListener('click', openModal);
    if(closeBtn) closeBtn.addEventListener('click', closeModal);

    // Close when clicking outside modal content
    modal.addEventListener('click', function(e){
        if(e.target === modal) closeModal();
    });
    // Close on ESC
    document.addEventListener('keydown', function(e){ if(e.key === 'Escape') closeModal(); });

    function installFocusTrap(){
        const focusableSelector = 'a[href], area[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), iframe, object, embed, [tabindex]:not([tabindex="-1"]), [contenteditable]';
        const container = modal.querySelector('.welcome-card') || modal;
        const focusables = Array.prototype.slice.call(container.querySelectorAll(focusableSelector));
        if(!focusables.length) return;
        const first = focusables[0];
        const last = focusables[focusables.length-1];
        _focusHandler = function(e){
            if(e.key !== 'Tab') return;
            if(e.shiftKey){
                if(document.activeElement === first){ e.preventDefault(); last.focus(); }
            } else {
                if(document.activeElement === last){ e.preventDefault(); first.focus(); }
            }
        };
        container.addEventListener('keydown', _focusHandler);
    }

    function removeFocusTrap(){
        const container = modal.querySelector('.welcome-card') || modal;
        if(_focusHandler){ container.removeEventListener('keydown', _focusHandler); _focusHandler = null; }
    }

    // Portal element for autocomplete dropdown (appended to body)
    let uniPortal = null;
    function ensurePortal(){
        if(uniPortal && document.body.contains(uniPortal)) return;
        uniPortal = document.createElement('div');
        uniPortal.id = 'uni-list-portal';
        uniPortal.className = 'autocomplete-list-portal hidden';
        document.body.appendChild(uniPortal);
    }

    // ensure Feather replaces any static icons already in the DOM
    if(window.feather) {
        try{ feather.replace(); }catch(e){}
    }
    // also run on DOMContentLoaded to be safe when script ordering varies
    document.addEventListener('DOMContentLoaded', function(){
        if(window.feather){ try{ feather.replace(); }catch(e){} }
    });

    function showList(filtered){
        ensurePortal();
        uniPortal.innerHTML = '';
        if(!filtered.length){ uniPortal.classList.add('hidden'); return; }
        filtered.forEach(u => {
            const div = document.createElement('div');
            div.className = 'autocomplete-item';
            div.textContent = u;
            div.tabIndex = 0;
            div.addEventListener('click', () => selectUniversity(u));
            div.addEventListener('keydown', (e)=> { if(e.key === 'Enter') selectUniversity(u); });
            div.addEventListener('mouseover', ()=> setActiveIndexFromNode(div));
            // if this item is currently selected, add a check icon
            if( (uniEl.value || '').toLowerCase() === u.toLowerCase() ){
                const chk = document.createElement('span');
                chk.className = 'item-check';
                chk.setAttribute('data-feather','check');
                div.appendChild(chk);
            }
            uniPortal.appendChild(div);
        });
        // position portal under input
        const rect = uniEl.getBoundingClientRect();
        uniPortal.style.minWidth = rect.width + 'px';
        uniPortal.style.left = Math.max(8, rect.left + window.scrollX) + 'px';
        uniPortal.style.top = (rect.bottom + window.scrollY + 6) + 'px';
        // animate open
        uniPortal.classList.remove('hidden','closing');
        // force reflow then add open
        void uniPortal.offsetWidth;
        uniPortal.classList.add('open');
        // render feather icons inside portal
        if(window.feather) try{ feather.replace(); }catch(e){}
    }

    // create a compact chip to show selected university and allow edit
    function showSelectedChip(val){
        const wrapper = document.getElementById('uni-chip-wrapper');
        if(!wrapper) return;
        wrapper.innerHTML = '';
        const chip = document.createElement('div');
        chip.className = 'selected-chip';
        chip.textContent = val;
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.title = 'Editar universidade';
        const ico = document.createElement('i');
        ico.setAttribute('data-feather','edit-2');
        ico.className = 'chip-edit-icon';
        btn.appendChild(ico);
        btn.addEventListener('click', ()=>{
            // remove chip and re-enable input for editing
            wrapper.classList.add('hidden');
            uniEl.readOnly = false;
            uniEl.value = '';
            uniEl.focus();
            uniEl.setAttribute('name','university');
            if(otherInput) otherInput.removeAttribute('name');
        });
        chip.appendChild(btn);
        wrapper.appendChild(chip);
        wrapper.classList.remove('hidden');
        // animate chip in
        setTimeout(()=> { chip.classList.add('visible'); if(window.feather) try{ feather.replace(); }catch(e){} }, 20);
        // make input readonly to indicate locked selection
        uniEl.readOnly = true;
    }

    // keyboard navigation state
    let _activeIndex = -1;
    function setActiveIndex(idx){
        const container = (uniPortal && document.body.contains(uniPortal)) ? uniPortal : uniList;
        const items = Array.from(container.querySelectorAll('.autocomplete-item'));
        items.forEach((it,i)=> it.classList.toggle('active', i === idx));
        _activeIndex = idx;
    }
    function setActiveIndexFromNode(node){
        const container = (uniPortal && document.body.contains(uniPortal)) ? uniPortal : uniList;
        const items = Array.from(container.querySelectorAll('.autocomplete-item'));
        const idx = items.indexOf(node);
        if(idx >= 0) setActiveIndex(idx);
    }

    function selectUniversity(val){
        // If user selects 'Outra', reveal the free input
        // hide both inline list and portal (portal used when appended to body)
        if(uniPortal){
            uniPortal.classList.remove('open');
            uniPortal.classList.add('closing');
            setTimeout(()=> uniPortal.classList.add('hidden'), 180);
        }
        if(uniList) uniList.classList.add('hidden');
        if(String(val).toLowerCase() === 'outra'){
            uniEl.value = 'Outra';
            // remove name from visible field so backend doesn't get 'Outra'
            uniEl.removeAttribute('name');
            otherInput.setAttribute('name','university');
            otherInput.value = '';
            otherWrapper.classList.remove('hidden');
            otherInput.focus();
        } else {
            // normal selection
            uniEl.value = val;
            // ensure uniEl has the proper name
            uniEl.setAttribute('name','university');
            if(otherInput){ otherInput.removeAttribute('name'); otherWrapper.classList.add('hidden'); }
        }
        // reset active index and hide list
        setActiveIndex(-1);
        // create a chip and mark input readonly for compact display
        if(String(val).toLowerCase() !== 'outra'){
            try{ showSelectedChip(val); } catch(e){}
            // move focus to next logical field (password)
            setTimeout(()=> { passEl && passEl.focus(); }, 80);
        }
        validateField(uniEl);
        validateAll();
    }

    uniEl.addEventListener('input', (e)=>{
        const v = e.target.value.trim();
        if(!v){ if(uniPortal) { uniPortal.classList.add('hidden'); } validateField(uniEl); validateAll(); return; }
        const filtered = universities.filter(u => u.toLowerCase().includes(v.toLowerCase()));
        // debounce showList to avoid rapid DOM updates
        debounceShowList(filtered);
        // If user typed 'outra' explicitly, show other input
        if(v.toLowerCase() === 'outra'){
            uniEl.removeAttribute('name');
            otherInput.setAttribute('name','university');
            otherWrapper.classList.remove('hidden');
            otherInput.focus();
        } else {
            // ensure other input hidden
            otherWrapper.classList.add('hidden');
            if(otherInput) otherInput.removeAttribute('name');
            uniEl.setAttribute('name','university');
        }
        validateField(uniEl);
        validateAll();
    });

    // debounce helper
    let _debounceTimer = null;
    function debounceShowList(filtered){
        if(_debounceTimer) clearTimeout(_debounceTimer);
        _debounceTimer = setTimeout(()=> { showList(filtered); _debounceTimer = null; }, 150);
    }

    // keyboard support for the autocomplete field
    uniEl.addEventListener('keydown', function(e){
        const container = (uniPortal && document.body.contains(uniPortal)) ? uniPortal : uniList;
        const items = Array.from(container.querySelectorAll('.autocomplete-item'));
        if(e.key === 'ArrowDown'){
            e.preventDefault();
            if(container.classList.contains('hidden')){
                const filtered = universities.filter(u => u.toLowerCase().includes((uniEl.value||'').toLowerCase()));
                showList(filtered);
            }
            const next = (Math.max(_activeIndex, -1) + 1) % Math.max(items.length,1);
            setActiveIndex(next);
            items[next] && items[next].focus();
        } else if(e.key === 'ArrowUp'){
            e.preventDefault();
            const prev = (_activeIndex <= 0) ? items.length - 1 : _activeIndex - 1;
            setActiveIndex(prev);
            items[prev] && items[prev].focus();
        } else if(e.key === 'Enter'){
            if(_activeIndex >= 0 && items[_activeIndex]){
                e.preventDefault();
                selectUniversity(items[_activeIndex].textContent);
            }
        } else if(e.key === 'Escape'){
            if(uniPortal) uniPortal.classList.add('hidden'); else uniList.classList.add('hidden');
            setActiveIndex(-1);
        }
    });

    document.addEventListener('click', (e)=>{
        if(e.target.closest('#uni-list-portal')) return; // clicks inside portal
        if(!e.target.closest('.autocomplete')) {
            if(uniPortal) uniPortal.classList.add('hidden');
            if(uniList) uniList.classList.add('hidden');
        }
    });

    // Normalize username to lowercase as user types
    usernameEl.addEventListener('input', ()=>{
        const pos = usernameEl.selectionStart;
        usernameEl.value = usernameEl.value.toLowerCase();
        usernameEl.setSelectionRange(pos, pos);
        validateField(usernameEl); validateAll();
    });

    nameEl.addEventListener('input', ()=> { validateField(nameEl); validateAll(); });
    passEl.addEventListener('input', ()=> { validateField(passEl); validateAll(); });

    function validateField(el){
        if(el === nameEl){
            const ok = el.value.trim().length >= 3;
            errName.classList.toggle('hidden', ok);
            return ok;
        }
        if(el === usernameEl){
            const v = el.value.trim();
            const ok = /^[a-z0-9_]+$/.test(v) && v.length >= 3;
            errUser.classList.toggle('hidden', ok);
            return ok;
        }
        if(el === uniEl){
            const v = (el.value || '').trim();
            // If visible field has value 'Outra', validation depends on otherInput
            if(v.toLowerCase() === 'outra'){
                const okOther = otherInput && otherInput.value.trim().length >= 2;
                otherErr && otherErr.classList.toggle('hidden', okOther);
                errUni.textContent = okOther ? 'Preencha sua universidade.' : 'Escolha uma universidade da lista.';
                // hide main err if other is okay
                errUni.classList.toggle('hidden', okOther);
                return okOther;
            }
            // Force selection: must exactly match one known university (case-insensitive)
            const ok = universities.some(u => u.toLowerCase() === v.toLowerCase());
            errUni.textContent = ok ? 'Preencha sua universidade.' : 'Escolha uma universidade da lista.';
            errUni.classList.toggle('hidden', ok);
            return ok;
        }
        if(el === otherInput){
            const ok = el.value.trim().length >= 2;
            otherErr && otherErr.classList.toggle('hidden', ok);
            return ok;
        }
        if(el === passEl){
            const ok = el.value.length >= 6;
            errPass.classList.toggle('hidden', ok);
            return ok;
        }
        return false;
    }

    function validateAll(){
        const uniValid = validateField(uniEl) || (otherInput && validateField(otherInput));
        const all = validateField(nameEl) && validateField(usernameEl) && uniValid && validateField(passEl);
        submitBtn.disabled = !all;
    }

    // run on changes
    [nameEl, usernameEl, uniEl, passEl, otherInput].forEach(i => i && i.addEventListener('input', validateAll));

    // initial run
    validateAll();

    // prevent form submission when disabled (extra safety)
    const form = document.getElementById('registro-form');
    form && form.addEventListener('submit', function(e){ if(submitBtn.disabled){ e.preventDefault(); } });

})();

