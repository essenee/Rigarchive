'use strict';
{
    const $ = django.jQuery;
    $(function() {
        const generation = document.getElementById('id_generation');
        if (!generation) return;
        for (const id of ['id_engine', 'id_factory_body_configuration']) {
            const field = document.getElementById(id);
            if (!field) continue;
            const autocompleteUrl = field.getAttribute('data-ajax--url');
            if (!autocompleteUrl) continue;
            let pendingRequest;
            let previousGeneration = generation.value;
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
                $(field).select2('close');
                if (clear) $(field).val(null).trigger('change');
                field.disabled = !generation.value;
            }
            $(generation).on('change', function() {
                update(id === 'id_engine' || generation.value !== previousGeneration);
                previousGeneration = generation.value;
            });
            field.disabled = !generation.value;
        }
    });
}
