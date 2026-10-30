// Progressive enhancements. Every page still works without JavaScript.
(function () {
    'use strict';

    // Prevent double submissions
    document.querySelectorAll('form[data-once]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            if (e.defaultPrevented) return;
            form.querySelectorAll('button[type="submit"]').forEach(function (b) { b.disabled = true; });
        });
    });

    // Auto-submit filter dropdowns
    document.querySelectorAll('select[data-autosubmit]').forEach(function (sel) {
        sel.addEventListener('change', function () { sel.form.submit(); });
    });

    document.querySelectorAll('[data-print]').forEach(function (btn) {
        btn.addEventListener('click', function () { window.print(); });
    });

    // Copy the student address. The clipboard API needs HTTPS or localhost,
    // which a LAN address isn't, so fall back to selecting the text.
    document.querySelectorAll('[data-copy]').forEach(function (btn) {
        var target = document.getElementById(btn.dataset.copy);
        var label = btn.lastChild;
        btn.addEventListener('click', function () {
            var text = target.textContent.trim();
            var done = function () {
                label.textContent = ' Copied';
                setTimeout(function () { label.textContent = ' Copy'; }, 1600);
            };
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(text).then(done);
                return;
            }
            var range = document.createRange();
            range.selectNodeContents(target);
            var sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
            try { if (document.execCommand('copy')) done(); } catch (e) { /* text stays selected */ }
        });
    });

    // Uppercase token input as the student types
    var token = document.getElementById('token');
    if (token) {
        token.addEventListener('input', function () {
            var pos = token.selectionStart;
            token.value = token.value.toUpperCase().replace(/[\s-]/g, '');
            token.setSelectionRange(pos, pos);
        });
    }

    // Character counters
    document.querySelectorAll('textarea[data-counter]').forEach(function (ta) {
        var out = document.getElementById(ta.dataset.counter);
        var update = function () { out.textContent = ta.value.length + ' / ' + ta.maxLength; };
        ta.addEventListener('input', update);
        update();
    });

    // Feedback form: answered counter + jump to first unanswered question
    var form = document.getElementById('feedback-form');
    if (!form) return;
    var questions = Array.prototype.slice.call(form.querySelectorAll('fieldset.q'));
    var counter = form.querySelector('[data-answered]');

    function isAnswered(q) { return !!q.querySelector('input:checked'); }

    function refresh() {
        var n = questions.filter(isAnswered).length;
        counter.textContent = n;
        questions.forEach(function (q) { if (isAnswered(q)) q.classList.remove('missing'); });
    }

    form.addEventListener('change', refresh);
    refresh();

    form.addEventListener('submit', function (e) {
        var missing = questions.filter(function (q) { return !isAnswered(q); });
        if (!missing.length) return;
        e.preventDefault();
        missing.forEach(function (q) { q.classList.add('missing'); });
        missing[0].scrollIntoView({ behavior: 'smooth', block: 'start' });
        var first = missing[0].querySelector('input');
        if (first) first.focus({ preventScroll: true });
    });
})();
