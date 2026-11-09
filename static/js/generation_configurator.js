/* Progressive enhancement of the existing, server-rendered Generation filters. */
(() => {
    if (!window.fetch || !window.AbortController || !window.DOMParser ||
        !document.getElementById("configurations")) return;

    const path = window.location.pathname;
    // Keep the live announcer mounted; replace only its sibling content.
    const panelIds = ["configuration-content"];
    let controller;
    let sequence = 0;
    let renderedSearch = window.location.search;

    function trimChoices(list) {
        return [...list.querySelectorAll("a[data-generation-filter]")]
            .map(link => link.getAttribute("href"));
    }

    function revealSelectedTrim(list) {
        const selected = list?.querySelector(".is-selected");
        if (!selected) return;
        const bounds = list.getBoundingClientRect();
        const item = selected.getBoundingClientRect();
        const style = window.getComputedStyle(list);
        const top = bounds.top + list.clientTop + parseFloat(style.paddingTop);
        const bottom = bounds.bottom - list.clientTop - parseFloat(style.paddingBottom);
        // Reveal only the obscured edge; never move the page or center a button.
        // Round outward to avoid clipping fractional pixels at zoomed font sizes.
        if (item.top < top) list.scrollTop += Math.floor(item.top - top);
        else if (item.bottom > bottom) list.scrollTop += Math.ceil(item.bottom - bottom);
    }

    function filterURL(value) {
        const url = new URL(value, window.location.href);
        return url.origin === window.location.origin && url.pathname === path ? url : null;
    }

    async function update(url, trigger, pushHistory = true) {
        const request = ++sequence;
        if (controller) controller.abort();
        controller = new AbortController();
        const panelId = "configurations";
        const focusId = trigger?.id;
        const focusHref = trigger?.getAttribute("href");
        const status = document.getElementById("generation-filter-status");
        status.textContent = "Updating configurations…";
        panelIds.forEach(id => document.getElementById(id).setAttribute("aria-busy", "true"));
        try {
            const requestURL = new URL(url);
            requestURL.hash = "";
            const response = await fetch(requestURL.href, {
                credentials: "same-origin",
                headers: { Accept: "text/html" },
                signal: controller.signal,
            });
            if (request !== sequence) return;
            if (!response.ok || !response.headers.get("content-type")?.includes("text/html") ||
                !filterURL(response.url)) throw new Error("Invalid filter response");
            const page = new DOMParser().parseFromString(await response.text(), "text/html");
            if (request !== sequence) return;
            const replacements = panelIds.map(id => page.getElementById(id));
            if (replacements.some(panel => !panel)) throw new Error("Missing filter panels");
            const top = document.getElementById(panelId).getBoundingClientRect().top;
            const oldTrims = document.getElementById("configuration-trims");
            const choices = oldTrims && trimChoices(oldTrims);
            // Read at replacement time: the user may scroll while fetching.
            const trimScrollTop = oldTrims?.scrollTop;
            panelIds.forEach((id, index) => document.getElementById(id).replaceWith(replacements[index]));
            const newTrims = document.getElementById("configuration-trims");
            if (newTrims && choices && JSON.stringify(choices) === JSON.stringify(trimChoices(newTrims))) {
                newTrims.scrollTop = trimScrollTop;
            }
            const newAnchor = document.getElementById(panelId);
            const focusTarget = (focusId && document.getElementById(focusId)) ||
                [...newAnchor.querySelectorAll("a[data-generation-filter]")]
                    .find(link => link.getAttribute("href") === focusHref) || newAnchor;
            focusTarget.focus({ preventScroll: true });
            revealSelectedTrim(newTrims);
            // Compensate any layout shift without scrolling to the section top.
            const delta = newAnchor.getBoundingClientRect().top - top;
            if (Math.abs(delta) > 1) {
                window.scrollTo({ top: window.scrollY + delta, left: window.scrollX, behavior: "instant" });
            }
            if (pushHistory && url.href !== window.location.href) {
                window.history.pushState(null, "", url.href);
            }
            renderedSearch = url.search;
            status.textContent = "Configurations updated.";
        } catch (error) {
            // Failed enhancement retains the ordinary server-rendered GET route.
            if (request === sequence && error.name !== "AbortError") window.location.assign(url.href);
        } finally {
            if (request === sequence) {
                panelIds.forEach(id => document.getElementById(id).removeAttribute("aria-busy"));
            }
        }
    }

    document.addEventListener("click", event => {
        if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey ||
            event.shiftKey || event.altKey) return;
        const link = event.target.closest("a[data-generation-filter]");
        if (!link || !link.closest("#configurations") || link.target ||
            link.hasAttribute("download")) return;
        const url = filterURL(link.href);
        if (!url) return;
        event.preventDefault();
        update(url, link);
    });

    window.addEventListener("popstate", () => {
        const url = filterURL(window.location.href);
        if (url && url.search !== renderedSearch) update(url, document.activeElement, false);
    });

    // Initial explicit trim/configuration deep links can select below the fold.
    revealSelectedTrim(document.getElementById("configuration-trims"));
})();
