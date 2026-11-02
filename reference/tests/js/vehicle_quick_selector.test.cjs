const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../../../static/js/vehicle_quick_selector.js'), 'utf8');

function harness(count = 2) {
    const document = { activeElement: null, handlers: {}, addEventListener(name, fn) { this.handlers[name] = fn; } };
    function node(attrs = {}) {
        return { attrs, hidden: true, handlers: {},
            addEventListener(name, fn) { this.handlers[name] = fn; },
            setAttribute(name, value) { this.attrs[name] = value; },
            getAttribute(name) { return this.attrs[name]; },
            focus() { document.activeElement = this; },
        };
    }
    const toggle = node({ 'aria-expanded': 'false' });
    const groups = Array.from({ length: count }, () => node());
    const buttons = groups.map((_, i) => node({ 'aria-controls': String(i), 'aria-pressed': 'false' }));
    const prompt = node(); prompt.hidden = false;
    const footer = node(); const modelLink = node();
    const panel = node();
    panel.contains = target => [prompt, footer, modelLink, ...buttons].includes(target);
    panel.querySelectorAll = () => buttons;
    panel.querySelector = selector => selector === 'a' ? footer : prompt;
    const root = node();
    root.querySelector = selector => selector === '.vehicle-quick-toggle' ? toggle : panel;
    root.contains = target => target === toggle || target === panel || panel.contains(target);
    document.querySelector = () => root;
    document.getElementById = id => groups[Number(id)];
    vm.runInNewContext(source, { document });
    return { document, toggle, panel, groups, buttons, prompt, footer, modelLink, root,
        click(target) { target.handlers.click?.(); document.handlers.click({ target }); },
        escape() { const event = { key: 'Escape', preventDefault() { this.prevented = true; } }; document.handlers.keydown(event); return event; },
    };
}

test('enhancement reveals toggle, opens on click and focuses manufacturer', () => {
    const h = harness();
    assert.equal(h.toggle.hidden, false);
    assert.equal(h.panel.hidden, true);
    h.click(h.toggle);
    assert.equal(h.panel.hidden, false);
    assert.equal(h.toggle.attrs['aria-expanded'], 'true');
    assert.equal(h.document.activeElement, h.buttons[0]);
    h.click(h.toggle);
    assert.equal(h.panel.hidden, true);
    assert.equal(h.document.activeElement, h.toggle);
});
test('manufacturer selection switches model groups without moving focus or navigating', () => {
    const h = harness(); h.click(h.toggle);
    h.buttons[0].focus(); h.click(h.buttons[0]);
    assert.deepEqual(h.groups.map(g => g.hidden), [false, true]);
    assert.equal(h.prompt.hidden, true);
    h.buttons[1].focus(); h.click(h.buttons[1]);
    assert.deepEqual(h.groups.map(g => g.hidden), [true, false]);
    assert.deepEqual(h.buttons.map(b => b.attrs['aria-pressed']), ['false', 'true']);
    assert.equal(h.document.activeElement, h.buttons[1]);
    h.escape(); h.click(h.toggle);
    assert.equal(h.document.activeElement, h.buttons[1]);
    assert.equal(h.modelLink.handlers.click, undefined);
});
test('Escape closes and restores focus, only consuming Escape while open', () => {
    const h = harness(); assert.equal(h.escape().prevented, undefined);
    h.click(h.toggle); assert.equal(h.escape().prevented, true);
    assert.equal(h.panel.hidden, true);
    assert.equal(h.toggle.attrs['aria-expanded'], 'false');
    assert.equal(h.document.activeElement, h.toggle);
});
test('outside click closes; keyboard exit closes without stealing destination focus', () => {
    const h = harness(); h.click(h.toggle);
    h.document.handlers.click({ target: {} });
    assert.equal(h.panel.hidden, true);
    assert.equal(h.document.activeElement, h.toggle);
    h.click(h.toggle);
    const outside = {}; h.document.activeElement = outside;
    h.root.handlers.focusout({ relatedTarget: outside });
    assert.equal(h.panel.hidden, true);
    assert.equal(h.document.activeElement, outside);
});
test('internal focus stays open and empty catalogue focuses Browse all link', () => {
    const h = harness(0); h.click(h.toggle);
    assert.equal(h.document.activeElement, h.footer);
    h.root.handlers.focusout({ relatedTarget: h.footer });
    assert.equal(h.panel.hidden, false);
});
test('pages without header are harmless', () => {
    vm.runInNewContext(source, { document: { querySelector: () => null } });
});
