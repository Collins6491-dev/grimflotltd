/* Shared progressive enhancement for password fields and server-rendered forms. */
(() => {
    const eye = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2.5 12s3.4-6 9.5-6 9.5 6 9.5 6-3.4 6-9.5 6-9.5-6-9.5-6Z"/><circle cx="12" cy="12" r="2.5"/></svg>';
    const eyeOff = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 3 18 18M10.6 6.2A10.8 10.8 0 0 1 12 6c6.1 0 9.5 6 9.5 6a17.7 17.7 0 0 1-3 3.7M6.1 6.1C3.8 8 2.5 12 2.5 12s3.4 6 9.5 6c1.3 0 2.5-.3 3.5-.7M9.9 9.9a3 3 0 0 0 4.2 4.2"/></svg>';

    document.querySelectorAll('input[type="password"]').forEach((input) => {
        if (input.dataset.passwordControl) return;
        input.dataset.passwordControl = 'true';
        const wrapper = document.createElement('span');
        wrapper.className = 'password-control';
        input.parentNode.insertBefore(wrapper, input);
        wrapper.append(input);
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'password-control__toggle';
        button.setAttribute('aria-label', 'Show password');
        button.setAttribute('aria-pressed', 'false');
        button.innerHTML = eye;
        button.addEventListener('click', () => {
            const reveal = input.type === 'password';
            const position = input.selectionStart;
            input.type = reveal ? 'text' : 'password';
            button.setAttribute('aria-label', reveal ? 'Hide password' : 'Show password');
            button.setAttribute('aria-pressed', String(reveal));
            button.innerHTML = reveal ? eyeOff : eye;
            input.focus();
            if (position !== null) input.setSelectionRange(position, position);
        });
        wrapper.append(button);
    });

    document.querySelectorAll('form[data-loading-form], form[method="post"]:not([data-no-loading])').forEach((form) => {
        if (form.dataset.loadingBound) return;
        form.dataset.loadingBound = 'true';

        form.addEventListener('submit', (event) => {
            if (!form.checkValidity()) return;
            const button = form.querySelector('button[type="submit"]');
            if (!button || button.disabled) return;
            button.disabled = true;
            button.classList.add('is-loading');
            button.setAttribute('aria-busy', 'true');
            const label = form.dataset.loadingLabel || 'Saving…';
            button.dataset.originalLabel = button.textContent.trim();
            button.innerHTML = '<span class="button-spinner" aria-hidden="true"></span><span>' + label + '</span>';
        });
    });
})();
