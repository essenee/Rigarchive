const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { decode, quietAnnotations } = require('../../../docs/design/homepage-paper-assets.cjs');
const root = path.resolve(__dirname, '../../..');
const asset = name => decode(path.join(root, 'static/images/homepage', name));

test('approved diagram retains every source RGB pixel, including drawings and labels', () => {
    const source = decode(path.join(root, 'docs/design/wireframes/homepage_hero_diagram_&background_approved.png'));
    const diagram = asset('4runner-diagram-approved-paper.png');
    assert.deepEqual([diagram.w, diagram.h], [502, 514]);
    for (let y = 0; y < diagram.h; y++) {
        for (let x = 0; x < diagram.w; x++) {
            const target = (y * diagram.w + x) * 4;
            const origin = ((y + 146) * source.w + x + 950) * 4;
            assert.deepEqual(diagram.pixels.subarray(target, target + 3), source.pixels.subarray(origin, origin + 3));
        }
    }
});

test('paper PNG surfaces have transparent outer corners and opaque interior paper', () => {
    for (const name of ['4runner-diagram-approved-paper.png', 'hero-photo-paper.png']) {
        const image = asset(name);
        assert.equal(image.pixels[3], 0);
        const center = (Math.floor(image.h / 2) * image.w + Math.floor(image.w / 2)) * 4;
        assert.equal(image.pixels[center + 3], 255);
    }
});

test('transparent contour ink crosses tile edges as continuously as neighboring pixels', () => {
    const image = asset('topographic-approved-neutral.png');
    for (const vertical of [true, false]) {
        function compositeDifference(a, b) {
            let delta = 0;
            for (let i = 0; i < image.w; i++) {
                const start = vertical ? (a * image.w + i) * 4 : (i * image.w + a) * 4;
                const end = vertical ? (b * image.w + i) * 4 : (i * image.w + b) * 4;
                delta += Math.abs(image.pixels[start + 3] - image.pixels[end + 3]) * (247 - 124) / 255;
            }
            return delta / image.w;
        }
        const edge = image.w - 1;
        const seam = compositeDifference(0, edge);
        const neighboring = (compositeDifference(0, 1) + compositeDifference(edge, edge - 1)) / 2;
        // Pixel centers across a tile boundary are one pixel apart, just like neighbors.
        // Compare continuity independently of the chosen ink contrast/contour density.
        assert.ok(seam <= neighboring * 1.25 + .5, 'tile boundary introduces a visible contrast jump');
    }
});

test('contour artwork leaves the CSS paper palette visible and keeps ink subdued', () => {
    const image = asset('topographic-approved-neutral.png');
    let clear = 0, maxAlpha = 0;
    for (let i = 0; i < image.pixels.length; i += 4) {
        const alpha = image.pixels[i + 3];
        if (!alpha) clear++;
        maxAlpha = Math.max(maxAlpha, alpha);
        assert.equal(image.pixels[i], image.pixels[i + 1]);
        assert.equal(image.pixels[i], image.pixels[i + 2]);
    }
    assert.ok(clear / (image.w * image.h) > .7);
    assert.ok(maxAlpha > 40 && maxAlpha <= 145);
});


test('quiet map retains the earlier contour pixels outside its small annotation areas', () => {
    const fs = require('node:fs'), crypto = require('node:crypto');
    const originalPath = path.join(root, 'static/images/homepage/topographic-subtle-original.png');
    assert.equal(crypto.createHash('sha256').update(fs.readFileSync(originalPath)).digest('hex'), '9d725fed69af69301d22d5a8b9606445573fc7130e10c22c75ff801b2b74f74e');
    const original = decode(originalPath), quiet = asset('topographic-approved-neutral.png');
    let changed = 0;
    for (let i = 0; i < quiet.pixels.length; i += 4) {
        const expected = Math.min(100, Math.round(Math.max(0, 248 - original.pixels[i] - 1) * 255 / 124));
        if (quiet.pixels[i + 3] !== expected) changed++;
    }
    assert.ok(changed > 0 && changed < 2000, 'new ink must be limited to labels and three faint dotted arcs');
});

test('both elevation labels run parallel to the actual local contour tangent', () => {
    const plan = quietAnnotations();
    assert.deepEqual(plan.labels.map(l => l.text), ['6800', '7200']);
    assert.equal(plan.dots.length, 3);
    for (const label of plan.labels) {
        const [a, b] = label.tangent, dx = b[0] - a[0], dy = b[1] - a[1];
        const cross = Math.cos(label.angle) * dy - Math.sin(label.angle) * dx;
        assert.ok(Math.abs(cross) / Math.hypot(dx, dy) < 1e-8);
    }
});

test('reusable frame has straight opaque paper edges and a fully transparent interior', () => {
    const frame = asset('hero-photo-frame.png');
    assert.deepEqual([frame.w, frame.h], [256, 256]);
    for (let y = 0; y < frame.h; y++) {
        for (let x = 0; x < frame.w; x++) {
            const i = (y * frame.w + x) * 4;
            const border = Math.min(x, y, 255 - x, 255 - y) < 32;
            assert.equal(frame.pixels[i + 3], border ? 255 : 0);
            if (border) {
                assert.ok(frame.pixels[i] >= 246 && frame.pixels[i] <= 254);
                assert.equal(frame.pixels[i], frame.pixels[i + 1]);
                assert.equal(frame.pixels[i] - frame.pixels[i + 2], 1);
            }
        }
    }
});

test('existing dotted arcs contain perceptible, spaced ink at full resolution', () => {
    const image = asset('topographic-approved-neutral.png');
    const original = asset('topographic-subtle-original.png');
    for (const arc of quietAnnotations().dots) {
        let perceptible = 0;
        for (const [x, y] of arc) {
            let added = 0;
            for (let yy = Math.floor(y) - 1; yy <= y + 1; yy++) {
                for (let xx = Math.floor(x) - 1; xx <= x + 1; xx++) {
                    const i = (yy * image.w + xx) * 4;
                    const baseline = Math.min(100, Math.round(Math.max(0, 248 - original.pixels[i] - 1) * 255 / 124));
                    added = Math.max(added, image.pixels[i + 3] - baseline);
                }
            }
            if (added >= 15) perceptible++;
        }
        assert.ok(perceptible >= 8, 'each arc needs several discernible dots without adding contour paths');
    }
});

test('length correction is localized and aligns its short witness with the rear bumper', () => {
    const original = asset('4runner-diagram-approved-paper.png');
    const corrected = asset('4runner-diagram-approved-paper-length-corrected.png');
    assert.deepEqual([corrected.w, corrected.h], [original.w, original.h]);
    let changes = 0;
    for (let y = 0; y < original.h; y++) {
        for (let x = 0; x < original.w; x++) {
            const i = (y * original.w + x) * 4;
            assert.equal(corrected.pixels[i + 3], original.pixels[i + 3]);
            if (x < 191 || x >= 454 || y < 23 || y >= 66) {
                assert.deepEqual(corrected.pixels.subarray(i, i + 4), original.pixels.subarray(i, i + 4));
            } else if (!corrected.pixels.subarray(i, i + 4).equals(original.pixels.subarray(i, i + 4))) changes++;
        }
    }
    // The erased ink's local paper repair is included; under 1% of the sheet changes.
    assert.ok(changes > 0 && changes < original.w * original.h * .01);
    const red = (x, y) => corrected.pixels[(y * corrected.w + x) * 4];
    let bumper = 0;
    for (let y = 155; y < 189; y++) for (let x = 397; x < 425; x++) if (red(x, y) < 180) bumper = Math.max(bumper, x);
    assert.equal(bumper, 414);
    assert.ok(red(bumper, 39) < 190, 'corrected witness aligns above the outer bumper');
    for (let y = 49; y < 66; y++) {
        assert.ok(red(414, y) > 225, 'short witness must not extend toward the vehicle');
        assert.ok(red(450, y) > 225, 'old witness tail must be removed');
    }
    assert.ok(red(450, 39) > 225, 'old arrow endpoint must be removed');
    const labelX = [];
    for (let y = 24; y < 48; y++) for (let x = 198; x < 259; x++) if (red(x, y) < 210) labelX.push(x);
    assert.ok(Math.abs((Math.min(...labelX) + Math.max(...labelX)) / 2 - 226) <= 1, 'handwritten label stays centered between endpoints');
    for (let y = 32; y < 46; y++) for (let x = 439; x < 450; x++) {
        if (original.pixels[(y * original.w + x) * 4] < 100) assert.ok(red(x - 36, y) < 135, 'native arrowhead ink must retain its shape');
    }
});
