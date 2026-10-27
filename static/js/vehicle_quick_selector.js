(() => {
    const root = document.querySelector('[data-vehicle-quick]');
    if (!root) return;
    const toggle = root.querySelector('.vehicle-quick-toggle');
    const panel = root.querySelector('.vehicle-quick-panel');
    const manufacturers = Array.from(panel.querySelectorAll('.vehicle-quick-manufacturer'));
    const prompt = panel.querySelector('[data-quick-prompt]');
    function close(restoreFocus = false) {
        panel.hidden = true;
        toggle.setAttribute('aria-expanded', 'false');
        if (restoreFocus) toggle.focus();
    }
    toggle.addEventListener('click', () => {
        if (!panel.hidden) {
            close(true);
            return;
        }
        panel.hidden = false;
        toggle.setAttribute('aria-expanded', 'true');
        (manufacturers.find(button => button.getAttribute('aria-pressed') === 'true')
            || manufacturers[0] || panel.querySelector('a')).focus();
    });
    manufacturers.forEach(button => button.addEventListener('click', () => {
        manufacturers.forEach(other => {
            const selected = other === button;
            other.setAttribute('aria-pressed', String(selected));
            document.getElementById(other.getAttribute('aria-controls')).hidden = !selected;
        });
        prompt.hidden = true;
        // Keep focus on the native button; the model links follow in Tab order.
    }));
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && !panel.hidden) {
            event.preventDefault();
            close(true);
        }
    });
    document.addEventListener('click', event => {
        if (!root.contains(event.target)) close(panel.contains(document.activeElement));
    });
    root.addEventListener('focusout', event => {
        if (!root.contains(event.relatedTarget)) close();
    });
    toggle.hidden = false;
})();
