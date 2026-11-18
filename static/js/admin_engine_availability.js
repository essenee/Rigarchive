'use strict';
{
    const $ = django.jQuery;
    $(function() {
        const generation = document.getElementById('id_generation');
        const engine = document.getElementById('id_engine');
        if (!generation || !engine) return;
        const autocompleteUrl = engine.getAttribute('data-ajax--url');
        if (!autocompleteUrl) return;
        let pendingRequest;
        // Keep Django's existing Select2 transport, search and pagination behavior.
        $.ajaxPrefilter(function(options, original, request) {
            if (options.url.split('?')[0] === autocompleteUrl.split('?')[0]) {
                pendingRequest = request;
                options.data = (options.data ? options.data + '&' : '') +
                    'generation=' + encodeURIComponent(generation.value);
            }
        });
        function update(clear) {
            if (pendingRequest) pendingRequest.abort();
            $(engine).select2('close');
            if (clear) $(engine).val(null).trigger('change');
            engine.disabled = !generation.value;
        }
        $(generation).on('change', function() { update(true); });
        engine.disabled = !generation.value;
    });
}
