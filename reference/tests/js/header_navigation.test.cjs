const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../../../static/js/header_navigation.js'), 'utf8');
function harness(narrow = true, phoneWidth = true) {
    const document = { handlers: {}, activeElement: null, documentElement: { style: { setProperty(k, v) { this[k] = v; } } }, addEventListener(k, f) { this.handlers[k] = f; } };
    const node = () => ({ handlers: {}, attrs: {}, hidden: false, addEventListener(k, f) { this.handlers[k] = f; }, setAttribute(k, v) { this.attrs[k] = v; }, focus() { document.activeElement = this; }, matches() { return false; }, getBoundingClientRect() { return { top: 0, bottom: 171, height: 171 }; } });
    const toggle = node(), panel = node(), link = node(), nav = node(), search = node(), actions = node();
    const children = [nav, search, actions];
    const parent = { insertBefore(a, b) { children.splice(children.indexOf(a), 1); children.splice(children.indexOf(b), 0, a); }, appendChild(a) { children.splice(children.indexOf(a), 1); children.push(a); } };
    for (const e of children) { e.parentNode = parent; Object.defineProperty(e, 'nextElementSibling', { get() { return children[children.indexOf(e) + 1]; } }); }
    panel.contains = e => e === link;
    panel.querySelector = () => link;
    const root = node(); root.querySelector = s => s === 'button' ? toggle : panel;
    root.contains = e => [toggle, panel, link].includes(e);
    const header = node(); header.classList = { add() {} };
    header.contains = e => [root, toggle, panel, link, search, actions].includes(e);
    header.querySelector = s => s === '.site-nav' ? nav : s === '.header-search' ? search : actions;
    const compact = { matches: narrow, addEventListener(k, f) { this.change = f; } };
    const phone = { matches: phoneWidth, addEventListener(k, f) { this.change = f; } };
    document.querySelector = s => s === '.site-header' ? header : root;
    const window = { matchMedia: s => s.includes('1024') ? compact : phone, addEventListener() {} };
    vm.runInNewContext(source, { document, window });
    return { document, toggle, panel, link, root, compact, phone, children, nav, search, actions,
        click() { toggle.handlers.click(); },
        escape() { const e = { key: 'Escape', preventDefault() { this.prevented = true; } }; document.handlers.keydown(e); return e; }
    };
}
test('compact enhancement preserves visible fallback markup and orders phone search last', () => {
    const h = harness();
    assert.equal(h.toggle.hidden, false); assert.equal(h.panel.hidden, true);
    assert.deepEqual(h.children, [h.nav, h.actions, h.search]);
    assert.equal(h.document.documentElement.style['--site-header-height'], '171px');
});
test('secondary disclosure opens, focuses its first link, and Escape restores toggle', () => {
    const h = harness(); h.click();
    assert.equal(h.panel.hidden, false); assert.equal(h.toggle.attrs['aria-expanded'], 'true');
    assert.equal(h.document.activeElement, h.link);
    assert.equal(h.escape().prevented, true); assert.equal(h.panel.hidden, true);
    assert.equal(h.document.activeElement, h.toggle); assert.equal(h.escape().prevented, undefined);
});
test('toggle close restores focus and ordinary links have no navigation interception', () => {
    const h = harness(); h.click(); h.click();
    assert.equal(h.panel.hidden, true); assert.equal(h.document.activeElement, h.toggle);
    assert.equal(h.link.handlers.click, undefined);
});
test('outside click and focus exit close without stealing a new destination focus', () => {
    const h = harness(); h.click(); h.document.handlers.click({ target: {} });
    assert.equal(h.panel.hidden, true); assert.equal(h.document.activeElement, h.toggle);
    h.click(); const other = {}; h.document.activeElement = other;
    h.root.handlers.focusout({ relatedTarget: other });
    assert.equal(h.panel.hidden, true); assert.equal(h.document.activeElement, other);
});
test('desktop resize exposes all destinations and does not strand focus on hidden toggle', () => {
    const h = harness(); h.toggle.focus(); h.compact.matches = false; h.phone.matches = false; h.compact.change();
    assert.equal(h.toggle.hidden, true); assert.equal(h.panel.hidden, false);
    assert.equal(h.document.activeElement, h.link); assert.deepEqual(h.children, [h.nav, h.search, h.actions]);
    h.compact.matches = true; h.compact.change();
    assert.equal(h.document.activeElement, h.toggle); assert.equal(h.panel.hidden, true);
});
test('sticky focus correction only scrolls obscured content outside the header', () => {
    const h = harness(); let calls = 0;
    const target = { matches() { return false; }, getBoundingClientRect() { return { top: 30 }; }, scrollIntoView(opts) { assert.equal(opts.block, 'start'); calls++; } };
    h.document.handlers.focusin({ target }); assert.equal(calls, 1);
    target.matches = () => true; h.document.handlers.focusin({ target }); assert.equal(calls, 1);
});
test('missing header is harmless', () => { vm.runInNewContext(source, { document: { querySelector: () => null } }); });

test('tablet DOM order follows branding/Garage then navigation/search rows', () => {
    const h = harness(true, false);
    assert.deepEqual(h.children, [h.actions, h.nav, h.search]);
    h.phone.matches = true; h.phone.change();
    assert.deepEqual(h.children, [h.nav, h.actions, h.search]);
});
