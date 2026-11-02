const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../../static/js/generation_configurator.js'), 'utf8');
const base = 'https://archive.example/vehicles/toyota/4runner/fourth-generation/';
const tick = () => new Promise(resolve => setImmediate(resolve));

// Execute the production script with an instrumented DOM/Fetch boundary.
// These tests cover asynchronous interaction behavior, not browser rendering.
function harness(enhanced = true) {
    const h = { requests: [], navigations: [], history: [], scrolls: [], pages: new Map() };
    let current = new URL(base);
    const handlers = {};
    const windowHandlers = {};
    const document = {
        panels: {}, activeElement: null,
        addEventListener: (name, callback) => { handlers[name] = callback; },
        getElementById(id) {
            return this.panels[id] || Object.values(this.panels).flatMap(p => p.children || []).find(n => n.id === id);
        },
    };
    function node(id, panel, attrs = {}) {
        return {
            id, attrs, panel, target: '',
            get href() { return new URL(attrs.href, current).href; },
            getAttribute: name => attrs[name] ?? null,
            hasAttribute: name => Object.hasOwn(attrs, name),
            closest(selector) {
                if (selector === 'a[data-generation-filter]') return Object.hasOwn(attrs, 'data-generation-filter') ? this : null;
                return this.panel;
            },
            focus(options) { document.activeElement = this; h.focusOptions = options; },
        };
    }
    function panel(id, layoutTop) {
        return {
            id, layoutTop, children: [], attrs: {},
            getBoundingClientRect() { return { top: this.layoutTop - window.scrollY }; },
            setAttribute(name, value) { this.attrs[name] = value; },
            removeAttribute(name) { delete this.attrs[name]; },
            replaceWith(replacement) {
                document.panels[id] = replacement;
                if (id === 'configuration-content') {
                    document.panels.configurations.layoutTop = replacement.layoutTop;
                    document.panels.configurations.children = replacement.children;
                }
            },
            querySelectorAll() { return this.children.filter(n => Object.hasOwn(n.attrs, 'data-generation-filter')); },
            focus(options) { document.activeElement = this; h.focusOptions = options; },
        };
    }
    h.link = (href, owner = document.panels.configurations, enhanced = true) => {
        const link = node('', owner, { href, ...(enhanced ? { 'data-generation-filter': '' } : {}) });
        owner.children.push(link);
        return link;
    };
    const location = {
        get href() { return current.href; }, get origin() { return current.origin; },
        get pathname() { return current.pathname; }, get search() { return current.search; },
        assign: url => h.navigations.push(url),
    };
    const fetch = (url, options) => new Promise((resolve, reject) => h.requests.push({ url, options, resolve, reject }));
    const window = {
        location, fetch: enhanced ? fetch : undefined, AbortController, DOMParser: true, scrollY: 600, scrollX: 0,
        addEventListener: (name, callback) => { windowHandlers[name] = callback; },
        history: { pushState: (_state, _title, url) => { h.history.push(url); current = new URL(url); } },
        scrollTo(options) { h.scrolls.push(options); this.scrollY = options.top; },
    };
    document.panels.configurations = panel('configurations', 1000);
    document.panels['configuration-content'] = panel('configuration-content', 1000);
    document.panels['generation-filter-status'] = { textContent: '' };
    // Exclude the status node from generic child lookups.
    document.panels['generation-filter-status'].children = [];
    class DOMParser { parseFromString(key) { return { getElementById: id => h.pages.get(key)?.[id] }; } }
    h.respond = (index, { shift = 0, missing = false, ok = true } = {}) => {
        const request = h.requests[index];
        const key = String(index);
        const configurations = panel('configuration-content', 1000 + shift);
        h.link(new URL(request.url).search + '#configurations', configurations);
        h.pages.set(key, !missing ? { 'configuration-content': configurations } : {});
        request.resolve({ ok, url: request.url, headers: { get: () => 'text/html; charset=utf-8' }, text: async () => key });
    };
    h.dispatch = (name, target, extra = {}) => {
        const event = { target, button: 0, preventDefault() { this.defaultPrevented = true; }, ...extra };
        document.activeElement = target;
        handlers[name]?.(event);
        return event;
    };
    h.pop = search => { current = new URL(base + search); windowHandlers.popstate(); };
    Object.assign(h, { window, document, handlers });
    vm.runInNewContext(source, { window, document, fetch, URL, URLSearchParams, AbortController, DOMParser });
    return h;
}

test('selection fetches panels without navigation and compensates layout shift at commit time', async () => {
    const h = harness();
    const event = h.dispatch('click', h.link('?year=2003#configurations'));
    assert.equal(event.defaultPrevented, true);
    assert.equal(h.requests[0].url, base + '?year=2003');
    h.window.scrollY += 50; // User scrolls while the response is in flight.
    h.respond(0, { shift: 80 });
    await tick();
    assert.equal(h.window.scrollY, 730);
    assert.equal(h.navigations.length, 0);
    assert.equal(h.history[0], base + '?year=2003#configurations');
    assert.equal(h.focusOptions.preventScroll, true);
    assert.equal(h.document.getElementById('generation-filter-status').textContent, 'Configurations updated.');
    assert.equal(h.document.getElementById('configuration-content').attrs['aria-busy'], undefined);
});

test('canonical Specs, unmarked links, modified clicks and external URLs retain native navigation', () => {
    const h = harness();
    for (const [link, extra] of [
        [h.link('#configurations', undefined, false), {}],
        [h.link(base + 'exact-record/', undefined, false), {}],
        [h.link('?year=2003'), { ctrlKey: true }],
        [h.link('https://elsewhere.example/?year=2003'), {}],
    ]) assert.equal(h.dispatch('click', link, extra).defaultPrevented, undefined);
    assert.equal(h.requests.length, 0);
});

test('year, unnamed-trim and exact-selection links use their complete GET state', async () => {
    const h = harness();
    const searches = ['?year=2003', '?year=2003&trim=', '?year=2003&configuration=exact-record'];
    for (const [index, search] of searches.entries()) {
        assert.equal(h.dispatch('click', h.link(search + '#configurations')).defaultPrevented, true);
        assert.equal(h.requests[index].url, base + search);
        h.respond(index);
        await tick();
    }
    assert.equal(h.history.length, 3);
    assert.equal(h.navigations.length, 0);
});

test('late responses cannot overwrite a newer selection', async () => {
    const h = harness();
    h.dispatch('click', h.link('?year=2003#configurations'));
    h.dispatch('click', h.link('?year=2007#configurations'));
    h.respond(1);
    await tick();
    h.respond(0);
    await tick();
    assert.equal(h.history.length, 1);
    assert.equal(h.history[0], base + '?year=2007#configurations');
    assert.equal(h.navigations.length, 0);
});

test('network failure falls back to the original server-rendered GET URL', async () => {
    const h = harness();
    h.dispatch('click', h.link('?year=2003#configurations'));
    h.requests[0].reject(new Error('offline'));
    await tick();
    assert.equal(h.navigations[0], base + '?year=2003#configurations');
});

test('invalid HTML does not partially replace panels and uses native fallback', async () => {
    const h = harness();
    const original = h.document.panels['configuration-content'];
    h.dispatch('click', h.link('?year=2003#configurations'));
    h.respond(0, { missing: true });
    await tick();
    assert.equal(h.document.panels['configuration-content'], original);
    assert.equal(h.navigations.length, 1);
});

test('back/forward refreshes filter panels without adding history entries', async () => {
    const h = harness();
    h.dispatch('click', h.link('?year=2003#configurations'));
    h.respond(0);
    await tick();
    h.pop('');
    h.respond(1);
    await tick();
    assert.equal(h.history.length, 1);
    assert.equal(h.requests[1].url, base);
    assert.equal(h.navigations.length, 0);
});


test('unsupported enhancement leaves server-rendered GET links untouched', () => {
    const h = harness(false);
    assert.equal(h.dispatch('click', h.link('?year=2003#configurations')).defaultPrevented, undefined);
    assert.equal(h.requests.length, 0);
});

test('subsequent selections use the replaced panels without a reload or top scroll', async () => {
    const h = harness();
    h.dispatch('click', h.link('?year=2003#configurations'));
    h.respond(0);
    await tick();
    const currentPanel = h.document.panels.configurations;
    h.dispatch('click', h.link('?year=2003&trim=SR5#configurations', currentPanel));
    h.respond(1);
    await tick();
    assert.equal(h.requests.length, 2);
    assert.equal(h.history.length, 2);
    assert.equal(h.navigations.length, 0);
    assert.equal(h.scrolls.length, 0); // No layout shift: preserve the exact viewport.
    assert.equal(h.window.scrollY, 600);
});

test('HTTP failures retain the native configurator reset destination', async () => {
    const h = harness();
    h.dispatch('click', h.link(base + '#configurations'));
    h.respond(0, { ok: false });
    await tick();
    assert.equal(new URL(h.navigations[0]).hash, '#configurations');
    assert.equal(h.history.length, 0);
});


test('live announcer remains mounted during repeated updates and focus stays accessible', async () => {
    const h = harness();
    const announcer = h.document.getElementById('generation-filter-status');
    const root = h.document.panels.configurations;
    for (let index = 0; index < 2; index++) {
        const link = h.link('?year=' + (2003 + index) + '#configurations');
        h.dispatch('click', link);
        assert.equal(announcer.textContent, 'Updating configurations…');
        h.respond(index);
        await tick();
        assert.equal(h.document.getElementById('generation-filter-status'), announcer);
        assert.equal(h.document.panels.configurations, root);
        assert.equal(announcer.textContent, 'Configurations updated.');
        assert.equal(h.focusOptions.preventScroll, true);
    }
    assert.equal(h.navigations.length, 0);
});
