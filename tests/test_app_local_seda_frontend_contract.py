"""Frontend contracts for app-local SEDA entry and session APIs."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from tests._helpers.node_runner import run_node_module


REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_seda_visible_prompt_strips_context_labels() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { visibleSedaPromptFromResponse } from './public/js/seda-visible-prompt.js';

        const prompt = visibleSedaPromptFromResponse({
          awaiting: { key: 'cold_attempt' },
          learnerTranscript: [
            {
              text: 'Concept: vaccines create immune memory Try your first explanation. Messy is fine.',
            },
            {
              text: 'Concept: vaccines create immune memory Learner goal: I want to explain why vaccines create immune memory. In your own words, why does a safe preview make the later response faster?',
            },
          ],
        });

        assert.equal(
          prompt,
          'Try your first explanation. Messy is fine.\\nIn your own words, why does a safe preview make the later response faster?'
        );
        assert.equal(prompt.includes('Concept:'), false);
        assert.equal(prompt.includes('Learner goal:'), false);
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_seda_visible_prompt_drops_setup_log_lines() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { visibleSedaPromptFromResponse } from './public/js/seda-visible-prompt.js';

        const prompt = visibleSedaPromptFromResponse({
          awaiting: {
            key: 'cold_attempt',
            ctaText: 'In your own words, why does a safe preview make the later response faster?',
          },
          learnerTranscript: [
            { level: 'log', text: 'Concept: vaccines create immune memory' },
            { level: 'log', text: 'Learner goal: I want to explain why vaccines create immune memory.' },
          ],
        });

        assert.equal(
          prompt,
          'In your own words, why does a safe preview make the later response faster?'
        );
        assert.equal(prompt.includes('Concept:'), false);
        assert.equal(prompt.includes('Learner goal:'), false);
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_auth_entry_session_redirect_contract() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { requireAppEntrySession } from './public/js/auth.js';

        const warnings = [];
        console.warn = (...args) => warnings.push(args);

        const redirects = [];
        const redirected = await requireAppEntrySession({
          fetchSession: async () => null,
          redirect: () => redirects.push('login'),
          waitAfterRedirect: false,
        });
        assert.equal(redirected, false);
        assert.deepEqual(redirects, ['login']);

        redirects.length = 0;
        const blocked = requireAppEntrySession({
          fetchSession: async () => null,
          redirect: () => redirects.push('login'),
        });
        await Promise.resolve();
        assert.deepEqual(redirects, ['login']);
        blocked.then(
          () => assert.fail('default redirect path should stay blocked'),
          () => assert.fail('default redirect path should not reject')
        );

        redirects.length = 0;
        const afterFailure = await requireAppEntrySession({
          fetchSession: async () => { throw new Error('session failed'); },
          redirect: () => redirects.push('login'),
          waitAfterRedirect: false,
        });
        assert.equal(afterFailure, false);
        assert.equal(warnings.length, 1);
        assert.deepEqual(redirects, ['login']);
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_seda_session_client_uses_app_boundary() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { createSedaSession, getSedaSession, sendSedaTurn } from './public/js/ai_service.js';

        const calls = [];
        globalThis.fetch = async (url, options = {}) => {
          calls.push({ url, options });
          return new Response(JSON.stringify({ sessionId: 'session-1' }), {
            status: 200,
            headers: { 'content-type': 'application/json' },
          });
        };

        await createSedaSession();
        await getSedaSession('session/1');
        await sendSedaTurn('session/1', 'first attempt');

        assert.equal(calls[0].url, '/api/session');
        assert.equal(calls[0].options.method, 'POST');
        assert.equal(calls[1].url, '/api/session/session%2F1');
        assert.equal(calls[1].options.method, 'GET');
        assert.equal(calls[2].url, '/api/session/session%2F1/turn');
        assert.equal(calls[2].options.method, 'POST');
        assert.deepEqual(JSON.parse(calls[2].options.body), { text: 'first attempt' });
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_auth_bootstrap_keeps_loop_out_of_primary_navigation() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';

        const nodes = new Map([
          ['auth-controls', { hidden: true }],
          ['auth-login-link', { hidden: true, href: '', textContent: '' }],
          ['auth-logout-btn', {
            hidden: true,
            disabled: false,
            textContent: '',
            dataset: {},
            addEventListener(type, handler) { this[type] = handler; },
          }],
          ['auth-status', { hidden: true, textContent: '' }],
        ]);
        globalThis.window = {
          location: { pathname: '/', search: '', hash: '', assign() {} },
        };
        globalThis.document = {
          getElementById(id) { return nodes.get(id) || null; },
        };

        const auth = await import('./public/js/auth.js');
        let redirectedToLogin = false;
        assert.equal(
          await auth.requireAppEntrySession({
            fetchSession: async () => ({ authenticated: false, guest_mode: false }),
            redirect: () => { redirectedToLogin = true; },
            waitAfterRedirect: false,
          }),
          false,
        );
        assert.equal(redirectedToLogin, true);
        assert.equal(
          await auth.requireAppEntrySession({
            fetchSession: async () => ({ authenticated: true, guest_mode: true }),
            redirect: () => { throw new Error('guest should not redirect'); },
            waitAfterRedirect: false,
          }),
          true,
        );
        globalThis.fetch = async () => ({
          ok: true,
          json: async () => ({ guest_mode: true, auth_enabled: true, loop_available: false }),
        });
        await auth.bootstrapAuthUi();
        assert.equal(nodes.has('nav-loop'), false);

        auth.invalidateAuthSession();
        globalThis.fetch = async () => ({
          ok: true,
          json: async () => ({ guest_mode: true, auth_enabled: true, loop_available: true }),
        });
        await auth.bootstrapAuthUi();
        assert.equal(nodes.has('nav-loop'), false);
        """
    )
    assert result.returncode == 0, result.stderr
