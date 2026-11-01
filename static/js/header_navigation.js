/* Progressive enhancement: existing destinations remain visible without JS. */
(() => {
    const header = document.querySelector('.site-header');
    const root = document.querySelector('[data-secondary-navigation]');
    if (!header || !root || !window.matchMedia) return;
    const toggle = root.querySelector('button');
    const panel = root.querySelector('.secondary-navigation-panel');
    const nav = header.querySelector('.site-nav');
    const search = header.querySelector('.header-search');
    const actions = header.querySelector('.header-actions');
    const compact = window.matchMedia('(max-width: 1024px)');
    const phone = window.matchMedia('(max-width: 600px)');
    function close(restore = false) {
        panel.hidden = compact.matches;
        toggle.setAttribute('aria-expanded', 'false');
        if (restore) toggle.focus();
    }
    function measure() {
        document.documentElement.style.setProperty('--site-header-height', `${header.getBoundingClientRect().height}px`);
    }
    function layout() {
        const focused = document.activeElement;
        // Match keyboard order to the visible rows at each breakpoint.
        const parent = search.parentNode;
        if (phone.matches && actions.nextElementSibling !== search) parent.insertBefore(actions, search);
        else if (compact.matches && !phone.matches && actions.nextElementSibling !== nav) parent.insertBefore(actions, nav);
        else if (!compact.matches && search.nextElementSibling !== actions) parent.appendChild(actions);
        toggle.hidden = !compact.matches;
        close();
        if (focused === toggle && !compact.matches) panel.querySelector('a')?.focus();
        else if (compact.matches && panel.contains(focused)) toggle.focus();
        else if (focused && header.contains(focused) && focused !== document.activeElement) focused.focus({ preventScroll: true });
        measure();
    }
    toggle.addEventListener('click', () => {
        if (!compact.matches) return;
        if (!panel.hidden) { close(true); return; }
        panel.hidden = false;
        toggle.setAttribute('aria-expanded', 'true');
        panel.querySelector('a')?.focus();
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && compact.matches && !panel.hidden) {
            event.preventDefault();
            close(true);
        }
    });
    document.addEventListener('click', event => {
        if (!root.contains(event.target)) close(compact.matches && panel.contains(document.activeElement));
    });
    root.addEventListener('focusout', event => {
        if (!root.contains(event.relatedTarget)) close();
    });
    document.addEventListener('focusin', event => {
        const target = event.target;
        if (header.contains(target) || target.matches('.skip-link') || !target.scrollIntoView) return;
        if (target.getBoundingClientRect().top < header.getBoundingClientRect().bottom) {
            target.scrollIntoView({ block: 'start', behavior: 'instant' });
        }
    });
    compact.addEventListener('change', layout);
    phone.addEventListener('change', layout);
    header.classList.add('header-enhanced');
    layout();
    if (window.ResizeObserver) new ResizeObserver(measure).observe(header);
    else window.addEventListener('resize', measure);
})();
