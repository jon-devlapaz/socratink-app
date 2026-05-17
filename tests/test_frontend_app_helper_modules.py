"""Characterization tests for small app.js helper modules."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TEST_NODE_TIMEOUT_SECONDS = 30


def run_node_module(script: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["node", "--input-type=module", "-e", script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=TEST_NODE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(
            f"Node helper module test timed out after {TEST_NODE_TIMEOUT_SECONDS}s",
            pytrace=False,
        )


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_html_escape_helper_matches_app_contract() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { escHtml } from './public/js/html.js';

        assert.equal(
          escHtml(`<&>"'`),
          '&lt;&amp;&gt;&quot;&#39;'
        );
        assert.equal(escHtml(null), '');
        assert.equal(escHtml(42), '42');
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_hero_helpers_preserve_state_labels_and_actions() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          describeDoorSource,
          getHeroActionConfig,
          getHeroGuidance,
          getHeroStateLabel,
        } from './public/js/app-hero.js';

        assert.equal(getHeroStateLabel('actualized'), 'spaced evidence');
        assert.equal(getHeroStateLabel('missing'), 'no concepts yet');

        assert.deepEqual(
          getHeroActionConfig(null),
          { label: 'Begin', action: 'add', disabled: false }
        );
        assert.deepEqual(
          getHeroActionConfig({ state: 'growing', graphData: { nodes: [] } }),
          { label: 'Open Draft Path', action: 'open-map', disabled: false }
        );
        assert.deepEqual(
          getHeroActionConfig({ state: 'hibernating', graphData: null }),
          { label: 'Return Later', action: 'wait', disabled: true }
        );

        assert.equal(
          getHeroGuidance({ state: 'instantiated', graphData: null }),
          'Map this source into a concept. The map is not learner evidence.'
        );
        assert.equal(describeDoorSource({ type: 'text', text: 'abc' }), '3 chars pasted');
        assert.equal(describeDoorSource({ type: 'url', url: 'https://example.com' }), 'https://example.com');
        assert.equal(describeDoorSource(null), '');
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_app_timer_preserves_countdown_contract() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { createCountdownTimer, formatTimerSeconds } from './public/js/app-timer.js';

        assert.equal(formatTimerSeconds(24 * 60 * 60), '24:00:00');
        assert.equal(formatTimerSeconds(3661), '01:01:01');
        assert.equal(formatTimerSeconds(3), '00:00:03');

        let intervalCallback = null;
        const cleared = [];
        const completions = [];
        const timerDisplay = { textContent: '' };
        const timer = createCountdownTimer({
          timerDisplay,
          initialSeconds: 10,
          onComplete() {
            completions.push(timer.getTimeLeft());
          },
          setIntervalRef(callback, delay) {
            intervalCallback = callback;
            assert.equal(delay, 1000);
            return 'interval-1';
          },
          clearIntervalRef(intervalId) {
            cleared.push(intervalId);
          },
        });

        assert.equal(timer.getTimeLeft(), 10);
        timer.start(2);
        assert.equal(timerDisplay.textContent, '00:00:02');
        assert.deepEqual(cleared, [null]);
        assert.equal(timer.getTimeLeft(), 2);

        intervalCallback();
        assert.equal(timerDisplay.textContent, '00:00:01');
        assert.equal(timer.getTimeLeft(), 1);
        assert.deepEqual(completions, []);

        intervalCallback();
        assert.equal(timerDisplay.textContent, '00:00:00');
        assert.deepEqual(completions, [0]);
        assert.deepEqual(cleared, [null, 'interval-1']);

        timer.fastForward();
        assert.equal(timer.getTimeLeft(), 3);
        timer.updateDisplay();
        assert.equal(timerDisplay.textContent, '00:00:03');

        timer.fastForward(7);
        assert.equal(timer.getTimeLeft(), 7);

        const zeroCompletions = [];
        const zeroTimer = createCountdownTimer({
          timerDisplay: { textContent: '' },
          onComplete() {
            zeroCompletions.push('complete');
          },
          setIntervalRef() {
            throw new Error('zero-second timer should not schedule an interval');
          },
        });
        zeroTimer.start(0);
        assert.deepEqual(zeroCompletions, ['complete']);
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_phase_b_session_helpers_preserve_storage_contract() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          getDefaultPhaseBSessionState,
          getPhaseBSessionStorageKey,
          loadPhaseBSessionState,
          persistPhaseBResumeState,
          persistPhaseBSessionState,
          loadPhaseBResumeState,
        } from './public/js/phase-b-session.js';

        const backing = new Map();
        const storage = {
          getItem(key) { return backing.has(key) ? backing.get(key) : null; },
          setItem(key, value) { backing.set(key, String(value)); },
          removeItem(key) { backing.delete(key); },
        };

        assert.deepEqual(getDefaultPhaseBSessionState(), {
          startedAt: null,
          nodesDrilled: 0,
          visitedNodeIds: [],
          retriesByNode: {},
          events: [],
        });
        assert.equal(getPhaseBSessionStorageKey('concept-1'), 'learnops-phase-b-session:concept-1');

        persistPhaseBSessionState(
          {
            startedAt: '2026-05-13T10:00:00.000Z',
            nodesDrilled: 99,
            visitedNodeIds: ['a', '', 'b'],
            retriesByNode: { a: 1 },
            events: [{ type: 'study' }],
          },
          { conceptId: 'concept-1', storage }
        );
        assert.deepEqual(loadPhaseBSessionState({ conceptId: 'concept-1', storage }), {
          startedAt: '2026-05-13T10:00:00.000Z',
          nodesDrilled: 2,
          visitedNodeIds: ['a', 'b'],
          retriesByNode: { a: 1 },
          events: [{ type: 'study' }],
        });

        persistPhaseBResumeState({ conceptId: 'c', nodeId: 'n', mode: 'study' }, { storage });
        assert.deepEqual(loadPhaseBResumeState({ storage }), { conceptId: 'c', nodeId: 'n', mode: 'study' });
        persistPhaseBResumeState(null, { storage });
        assert.equal(loadPhaseBResumeState({ storage }), null);

        Object.defineProperty(globalThis, 'sessionStorage', {
          configurable: true,
          get() { throw new Error('storage denied'); },
        });
        assert.deepEqual(loadPhaseBSessionState(), getDefaultPhaseBSessionState());
        assert.equal(loadPhaseBResumeState(), null);
        assert.doesNotThrow(() => persistPhaseBSessionState({ visitedNodeIds: [] }));
        assert.doesNotThrow(() => persistPhaseBResumeState({ conceptId: 'c', nodeId: 'n', mode: 'study' }));
        delete globalThis.sessionStorage;
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_settings_view_template_preserves_required_dom_ids() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { SETTINGS_HTML } from './public/js/settings-view.js';

        for (const requiredId of [
          'settings-identity-row',
          'settings-avatar',
          'settings-identity-email',
          'settings-identity-meta',
          'settings-identity-action-host',
          'settings-motion-toggle',
          'settings-sound-toggle',
        ]) {
          assert.ok(SETTINGS_HTML.includes(`id="${requiredId}"`), requiredId);
        }
        assert.ok(SETTINGS_HTML.includes('data-theme-value="light"'));
        assert.ok(SETTINGS_HTML.includes('data-theme-value="dark"'));
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_library_view_helpers_preserve_card_metadata_and_empty_state() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          buildLibraryHtml,
          getLibraryConceptMeta,
        } from './public/js/library-view.js';

        const graph = {
          metadata: {
            core_thesis: 'This is the central claim.',
            architecture_type: 'cause_effect',
            difficulty: 'medium',
            source_title: 'Source Title',
          },
          clusters: [
            { subnodes: [{ id: 'a' }, { id: 'b' }] },
            { subnodes: [{ id: 'c' }] },
          ],
        };
        assert.deepEqual(
          getLibraryConceptMeta({ name: 'Concept', state: 'growing', graphData: graph }),
          {
            thesis: 'No learner reconstruction recorded yet.',
            summarySource: 'none',
            architecture: 'cause effect',
            difficulty: 'medium',
            clusterCount: 2,
            subnodeCount: 3,
            sourceLabel: 'Map: Source Title',
          }
        );
        assert.equal(
          getLibraryConceptMeta({
            contentType: 'pdf',
            graphData: JSON.stringify({ metadata: { thesis: 'x'.repeat(200) }, clusters: [] }),
          }).sourceLabel,
          'Source: PDF'
        );
        assert.ok(getLibraryConceptMeta({ graphData: '{' }).thesis.includes('No learner reconstruction'));

        const training = {
          node_records: {
            n1: {
              attempts: [
                {
                  id: 'a1',
                  at: '2026-05-15T10:00:00.000Z',
                  user_text: 'The vague first answer.',
                  classification: 'thin',
                },
                {
                  id: 'a2',
                  at: '2026-05-15T11:00:00.000Z',
                  user_text: 'The learner reconstructed the causal mechanism.',
                  classification: 'strong',
                },
              ],
            },
          },
        };
        assert.deepEqual(
          getLibraryConceptMeta({ name: 'Concept', state: 'growing', graphData: graph }, training),
          {
            thesis: 'The learner reconstructed the causal mechanism.',
            summarySource: 'learner_attempt',
            architecture: 'cause effect',
            difficulty: 'medium',
            clusterCount: 2,
            subnodeCount: 3,
            sourceLabel: 'Map: Source Title',
          }
        );

        const emptyHtml = buildLibraryHtml([]);
        assert.ok(emptyHtml.includes('Begin a reconstruction.'));
        assert.ok(emptyHtml.includes('App.showIgnition()'));
        assert.ok(!emptyHtml.includes('App.seedLocalQaConcept()'));

        const localQaEmptyHtml = buildLibraryHtml([], {}, { showLocalQaSeed: true });
        assert.ok(localQaEmptyHtml.includes('data-local-qa-seed'));
        assert.ok(localQaEmptyHtml.includes('App.seedLocalQaConcept()'));
        assert.ok(localQaEmptyHtml.includes('data-local-repair-qa-seed'));
        assert.ok(localQaEmptyHtml.includes('App.seedLocalRepairQaConcept()'));

        const cardHtml = buildLibraryHtml([
          { id: 'c-1', name: '<Unsafe>', state: 'growing', graphData: graph },
        ], { 'c-1': training });
        assert.ok(cardHtml.includes('data-concept-id="c-1"'));
        assert.ok(cardHtml.includes('onclick="App.openLibraryConcept(this.dataset.conceptId)"'));
        assert.ok(cardHtml.includes('&lt;Unsafe&gt;'));
        assert.ok(cardHtml.includes('The learner reconstructed the causal mechanism.'));
        assert.ok(!cardHtml.includes('This is the central claim.'));
        assert.ok(cardHtml.includes('2 sections'));
        assert.ok(cardHtml.includes('3 entries'));
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_source_input_helpers_preserve_blocking_and_text_contracts() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          SOURCE_INPUT_HTML,
          hasStudyEvidence,
          isBlockedVideoUrl,
          shortOnboardingText,
        } from './public/js/source-input-ui.js';

        for (const blocked of [
          'https://youtu.be/abc',
          'https://youtube.com/watch?v=abc',
          'https://www.youtube.com/watch?v=abc',
          'https://youtube-nocookie.com/embed/abc',
          'https://www.youtube-nocookie.com/embed/abc',
        ]) {
          assert.equal(isBlockedVideoUrl(blocked), true, blocked);
        }
        assert.equal(isBlockedVideoUrl('https://example.com/watch?v=abc'), false);
        assert.equal(isBlockedVideoUrl('not a url'), false);

        assert.equal(shortOnboardingText('  a   b\\n c  ', 20), 'a b c');
        assert.equal(shortOnboardingText('abcdefghij', 8), 'abcde...');
        assert.equal(shortOnboardingText(null), '');

        assert.equal(hasStudyEvidence({ drill_status: 'primed' }), true);
        assert.equal(hasStudyEvidence({ drill_status: 'solid' }), true);
        assert.equal(hasStudyEvidence({ gap_type: 'misread' }), true);
        assert.equal(hasStudyEvidence({ drill_status: 'new' }), false);

        assert.ok(SOURCE_INPUT_HTML(false).includes('data-tab="url"'));
        assert.ok(!SOURCE_INPUT_HTML(false).includes('paste-clipboard-btn'));
        assert.ok(SOURCE_INPUT_HTML(true).includes('paste-clipboard-btn'));
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_board_grid_helpers_preserve_tile_markup_and_events() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          EMPTY_TILE,
          TILE_PLATFORM,
          conceptPinSVG,
          playAnim,
          renderGrid,
        } from './public/js/board-grid.js';

        assert.ok(TILE_PLATFORM.includes('tile-top'));
        assert.ok(EMPTY_TILE.includes('tile-top-empty'));
        assert.ok(conceptPinSVG(2, 'growing').includes('concept-marker-anim-2'));
        assert.ok(conceptPinSVG(2, 'growing').includes('data-state="growing"'));

        const events = [];
        const makeTile = () => ({
          attrs: {},
          innerHTML: '',
          setAttribute(name, value) { this.attrs[name] = value; },
        });
        const tiles = [makeTile(), makeTile()];
        renderGrid({
          concepts: [{ id: 'c1', name: 'First', state: 'growing' }],
          tileEls: tiles,
          activeId: 'c1',
          bus: { emit(eventName) { events.push(eventName); } },
        });

        assert.equal(tiles[0].attrs.class, 'tile-group selected');
        assert.equal(tiles[0].attrs.role, 'button');
        assert.equal(tiles[0].attrs.tabindex, '0');
        assert.equal(tiles[0].attrs['aria-label'], 'Open First');
        assert.ok(tiles[0].innerHTML.includes('concept-pin-0'));
        assert.equal(tiles[1].attrs.class, 'tile-group empty');
        assert.equal(tiles[1].attrs['aria-label'], 'New concept');
        assert.ok(tiles[1].innerHTML.includes('tile-top-empty'));
        assert.deepEqual(events, ['grid:rendered']);

        const classes = new Set(['anim-crack']);
        const animationEvents = {};
        const el = {
          classList: {
            add(name) { classes.add(name); },
            remove(name) { classes.delete(name); },
          },
          addEventListener(name, fn) { animationEvents[name] = fn; },
          removeEventListener(name) { delete animationEvents[name]; },
        };
        playAnim('emerge', 3, {
          documentRef: { getElementById(id) { return id === 'concept-marker-anim-3' ? el : null; } },
        });
        assert.ok(classes.has('anim-emerge'));
        assert.ok(!classes.has('anim-crack'));
        animationEvents.animationend();
        assert.ok(!classes.has('anim-emerge'));
        playAnim('missing', 3, {
          documentRef: { getElementById() { throw new Error('should not query'); } },
        });
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_theme_preference_helpers_preserve_storage_dom_and_toggle_contracts() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          applyThemePreference,
          getStoredThemePreference,
          getToggledTheme,
          normalizeThemePreference,
          updateThemeToggleUi,
        } from './public/js/theme-preference.js';

        const storage = new Map();
        const storageLike = {
          getItem(key) { return storage.has(key) ? storage.get(key) : null; },
          setItem(key, value) { storage.set(key, String(value)); },
        };
        assert.equal(normalizeThemePreference('dark'), 'dark');
        assert.equal(normalizeThemePreference('blue'), 'light');
        assert.equal(getToggledTheme('dark'), 'light');
        assert.equal(getToggledTheme('light'), 'dark');
        assert.equal(getStoredThemePreference({ storage: storageLike }), 'light');
        storage.set('learnops-theme', 'dark');
        assert.equal(getStoredThemePreference({ storage: storageLike }), 'dark');
        assert.equal(getStoredThemePreference({
          storage: { getItem() { throw new Error('denied'); } },
          logger: { warn() {} },
        }), 'light');

        const calls = [];
        const toggle = {
          dataset: {},
          attrs: {},
          setAttribute(name, value) { this.attrs[name] = value; },
        };
        const bodyClasses = new Set();
        const documentRef = {
          body: {
            dataset: {},
            classList: {
              toggle(name, enabled) {
                if (enabled) bodyClasses.add(name);
                else bodyClasses.delete(name);
              },
            },
          },
          documentElement: { dataset: {} },
        };
        updateThemeToggleUi('dark', toggle);
        assert.equal(toggle.dataset.theme, 'dark');
        assert.equal(toggle.attrs['aria-pressed'], 'true');
        assert.equal(toggle.attrs.title, 'Switch to light mode');

        const appliedDark = applyThemePreference('dark', {
          documentRef,
          themeToggleEl: toggle,
          storage: storageLike,
          onRemount() { calls.push('remount'); },
        });
        assert.equal(appliedDark, 'dark');
        assert.ok(bodyClasses.has('night'));
        assert.equal(documentRef.body.dataset.theme, 'dark');
        assert.equal(documentRef.documentElement.dataset.theme, 'dark');
        assert.equal(storage.get('learnops-theme'), 'dark');
        assert.deepEqual(calls, ['remount']);

        const appliedLight = applyThemePreference('unknown', {
          documentRef,
          themeToggleEl: toggle,
          storage: storageLike,
          persist: false,
          onRemount() { calls.push('remount'); },
        });
        assert.equal(appliedLight, 'light');
        assert.ok(!bodyClasses.has('night'));
        assert.equal(storage.get('learnops-theme'), 'dark');
        applyThemePreference('dark', {
          documentRef,
          themeToggleEl: null,
          storage: { setItem() { throw new Error('denied'); } },
          logger: { warn() {} },
          onRemount() {},
        });
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_app_shell_ui_preserves_drawer_settings_and_concept_list_contracts() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          clearSettingsPanel,
          closeDrawer,
          conceptListItemHtml,
          openDrawer,
          renderConceptList,
          toggleDrawer,
        } from './public/js/app-shell-ui.js';

        const drawer = { dataset: {} };
        const drawerToggle = {
          attrs: {},
          setAttribute(name, value) { this.attrs[name] = value; },
        };
        const documentRef = {
          body: { dataset: {} },
        };
        openDrawer({ drawer, drawerToggle, documentRef });
        assert.equal(drawer.dataset.open, 'true');
        assert.equal(documentRef.body.dataset.drawerOpen, 'true');
        assert.equal(drawerToggle.attrs['aria-expanded'], 'true');
        closeDrawer({ drawer, drawerToggle, documentRef });
        assert.equal(drawer.dataset.open, 'false');
        assert.equal(documentRef.body.dataset.drawerOpen, 'false');
        assert.equal(drawerToggle.attrs['aria-expanded'], 'false');
        const sounds = [];
        toggleDrawer({ drawer, drawerToggle, documentRef, audio: { playDrawerToggle() { sounds.push('tap'); } } });
        assert.deepEqual(sounds, ['tap']);
        assert.equal(drawer.dataset.open, 'true');

        const settingsHost = { innerHTML: '', querySelector() { return {}; } };
        const settingsBtn = { dataset: { engaged: 'true' } };
        clearSettingsPanel({
          documentRef: {
            getElementById(id) {
              if (id === 'sidebar-settings-host') return settingsHost;
              if (id === 'nav-settings') return settingsBtn;
              return null;
            },
          },
        });
        assert.equal(settingsHost.innerHTML, '');
        assert.equal('engaged' in settingsBtn.dataset, false);

        const html = conceptListItemHtml({ id: 'c1', name: '<Unsafe>', state: 'growing' });
        assert.ok(html.includes('&lt;Unsafe&gt;'));
        assert.ok(html.includes('data-concept-id="c1"'));
        assert.ok(html.includes('App.deleteConcept(this.dataset.conceptId,this)'));

        class FakeElement {
          constructor() {
            this.className = '';
            this.innerHTML = '';
            this.listeners = {};
            this.children = [];
            this.dataset = {};
          }
          addEventListener(name, fn) { this.listeners[name] = fn; }
          appendChild(child) { this.children.push(child); }
          closest() { return null; }
        }
        const conceptListEl = new FakeElement();
        const clicked = [];
        renderConceptList({
          concepts: [
            { id: 'c1', name: 'First', state: 'growing', graphData: true },
            { id: 'c2', name: 'Second', state: 'hibernating' },
          ],
          activeId: 'c2',
          conceptListEl,
          documentRef: { createElement() { return new FakeElement(); } },
          elementCtor: FakeElement,
          onOpenConcept(concept) { clicked.push(concept.id); },
        });
        assert.equal(conceptListEl.innerHTML, '');
        assert.equal(conceptListEl.children.length, 2);
        assert.equal(conceptListEl.children[0].className, 'concept-item');
        assert.equal(conceptListEl.children[0].dataset.conceptId, 'c1');
        assert.equal(conceptListEl.children[1].className, 'concept-item active');
        assert.equal(conceptListEl.children[1].dataset.conceptId, 'c2');
        conceptListEl.children[0].listeners.click({ target: new FakeElement() });
        assert.deepEqual(clicked, ['c1']);
        const deleteTarget = new FakeElement();
        deleteTarget.closest = (selector) => selector === '.concept-delete' ? {} : null;
        conceptListEl.children[1].listeners.click({ target: deleteTarget });
        assert.deepEqual(clicked, ['c1']);
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_concept_page_view_renders_active_entry_html_contract() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          findConceptEntryById,
          getConceptEntryId,
          renderActiveEntryHtml,
          renderConceptStripHtml,
          selectInitialConceptEntry,
        } from './public/js/concept-page-view.js';

        const backbone = [
          { id: 'core', label: '<Core>', drill_status: 'drilled', purpose: 'First purpose' },
          { id: 'entry-2', label: 'Second & unsafe', drill_status: 'locked' },
          { id: 'entry-3', label: 'Third', drill_status: 'locked' },
        ];
        const training = {
          node_records: {
            core: {
              attempts: [{
                id: 'a1',
                kind: 'cold',
                at: '2026-05-15T10:00:00.000Z',
                user_text: 'Learner explained the core mechanism.',
                classification: 'strong',
                gaps: [],
                grader_version: 'qa',
              }],
              repairs: [],
            },
          },
        };

        assert.equal(getConceptEntryId(backbone[0], 0), 'core');
        assert.equal(getConceptEntryId({ label: 'No id' }, 2), 'entry-2');

        const legacyStatusCompat = selectInitialConceptEntry([
          { id: 'legacy-primed', label: 'Legacy primed', drill_status: 'solidified' },
          { id: 'next', label: 'Next', drill_status: 'locked' },
        ]);
        assert.equal(legacyStatusCompat.id, 'next');

        const legacyDrilledHtml = renderActiveEntryHtml(
          { id: 'legacy-drilled', label: 'Legacy drilled', drill_status: 'drilled' },
          0,
          [{ id: 'legacy-drilled', label: 'Legacy drilled', drill_status: 'drilled' }],
          {},
          { metadata: {} }
        );
        assert.ok(legacyDrilledHtml.includes('ready to reconstruct again entry 1 of 1'));

        const legacyStudyHtml = renderActiveEntryHtml(
          { id: 'legacy-study', label: 'Legacy study', drill_status: 'primed', drill_phase: 'study', study_note: 'Legacy study note.' },
          0,
          [{ id: 'legacy-study', label: 'Legacy study', drill_status: 'primed', drill_phase: 'study', study_note: 'Legacy study note.' }],
          {},
          { metadata: {} }
        );
        assert.ok(legacyStudyHtml.includes('study required entry 1 of 1'));
        assert.ok(legacyStudyHtml.includes('data-active-entry-action="study"'));
        const legacyStudyRevealedHtml = renderActiveEntryHtml(
          { id: 'legacy-study', label: 'Legacy study', drill_status: 'primed', drill_phase: 'study', study_note: 'Legacy study note.' },
          0,
          [{ id: 'legacy-study', label: 'Legacy study', drill_status: 'primed', drill_phase: 'study', study_note: 'Legacy study note.' }],
          {},
          { metadata: {} },
          { node_records: { 'legacy-study': { attempts: [], repairs: [], study_revealed_at: '2026-05-15T10:05:00.000Z' } } }
        );
        assert.ok(legacyStudyRevealedHtml.includes('Legacy study note.'));
        assert.ok(!legacyStudyRevealedHtml.includes('concept-page-b2__evidence'));

        const initial = selectInitialConceptEntry([
          { id: 'done', label: 'Done', drill_status: 'solidified' },
          { label: 'Next cold entry', drill_status: 'locked' },
        ], {
          node_records: {
            done: {
              attempts: [
                { id: 's1', at: '2026-05-14T10:00:00.000Z', user_text: 'first strong', classification: 'strong', gaps: [], grader_version: 'qa' },
                { id: 's2', at: '2026-05-15T10:00:00.000Z', user_text: 'second strong', classification: 'strong', gaps: [], grader_version: 'qa' },
              ],
            },
          },
        });
        assert.equal(initial.entry.label, 'Next cold entry');
        assert.equal(initial.index, 1);
        assert.equal(initial.id, 'entry-1');

        const allSolidified = selectInitialConceptEntry([
          { id: 'solid', label: 'Solid', drill_status: 'solidified' },
        ]);
        assert.equal(allSolidified.entry.label, 'Solid');
        assert.equal(allSolidified.index, 0);
        assert.equal(allSolidified.id, 'solid');
        const solidifiedHtml = renderActiveEntryHtml(
          { id: 'solid', label: 'Solid', drill_status: 'solidified' },
          0,
          [{ id: 'solid', label: 'Solid', drill_status: 'solidified' }],
          {},
          { metadata: {} }
        );
        assert.ok(solidifiedHtml.includes('solidified entry 1 of 1'));
        assert.ok(!solidifiedHtml.includes('concept-page-b2__entry-cta'));
        const legacySolidWithPartialTrainingHtml = renderActiveEntryHtml(
          { id: 'legacy-solid', label: 'Legacy solid', drill_status: 'solidified' },
          0,
          [{ id: 'legacy-solid', label: 'Legacy solid', drill_status: 'solidified' }],
          {},
          { metadata: {} },
          {
            node_records: {
              'legacy-solid': {
                attempts: [{
                  id: 'legacy-redrill',
                  at: '2026-05-15T10:00:00.000Z',
                  user_text: 'Strong legacy re-drill.',
                  classification: 'strong',
                  gaps: [],
                  grader_version: 'qa',
                }],
              },
            },
          }
        );
        assert.ok(legacySolidWithPartialTrainingHtml.includes('solidified entry 1 of 1'));
        assert.ok(!legacySolidWithPartialTrainingHtml.includes('study required entry 1 of 1'));
        assert.ok(!legacySolidWithPartialTrainingHtml.includes('concept-page-b2__entry-cta'));

        const emptyInitial = selectInitialConceptEntry([]);
        assert.equal(emptyInitial.entry.id, 'core-thesis');
        assert.equal(emptyInitial.index, 0);
        assert.equal(emptyInitial.id, 'core-thesis');

        const fallbackMatch = findConceptEntryById([{ label: 'No id' }], 'entry-0');
        assert.equal(fallbackMatch.entry.label, 'No id');
        assert.equal(fallbackMatch.index, 0);
        assert.equal(fallbackMatch.id, 'entry-0');
        assert.equal(findConceptEntryById(backbone, 'missing'), null);

        const blockedHtml = renderActiveEntryHtml(
          backbone[2],
          2,
          backbone,
          { startingMapContext: '<threshold & sketch>' },
          { metadata: { core_thesis: 'fallback thesis' } },
          training
        );
        assert.ok(blockedHtml.includes('&lt;threshold &amp; sketch&gt;'));
        assert.ok(blockedHtml.includes('locked entry 3 of 3'));
        assert.ok(blockedHtml.includes('aria-disabled="true"'));
        assert.ok(blockedHtml.includes('>Locked</button>'));
        assert.ok(blockedHtml.includes('&lt;Core&gt;'));
        assert.ok(blockedHtml.includes('Second &amp; unsafe'));
        assert.ok(blockedHtml.includes('READY TO RECONSTRUCT'));

        const readyHtml = renderActiveEntryHtml(
          backbone[1],
          1,
          backbone,
          { startingMapContext: '' },
          { metadata: { starting_map_context: 'metadata sketch' } },
          training
        );
        assert.ok(readyHtml.includes('metadata sketch'));
        assert.ok(readyHtml.includes('first reconstruction entry 2 of 3'));
        assert.ok(readyHtml.includes('data-active-entry-id="entry-2"'));
        assert.ok(readyHtml.includes('Write what you remember'));

        const readyAttemptHtml = renderActiveEntryHtml(
          backbone[1],
          1,
          backbone,
          { startingMapContext: '' },
          { metadata: { starting_map_context: 'metadata sketch' } },
          training,
          { attemptEntryId: 'entry-2' }
        );
        assert.ok(readyAttemptHtml.includes('concept-page-b2__attempt'));
        assert.ok(readyAttemptHtml.includes('data-attempt-entry-id="entry-2"'));
        assert.ok(readyAttemptHtml.includes('Write what you can reconstruct'));
        assert.ok(readyAttemptHtml.includes('Save what I wrote'));
        assert.ok(!readyAttemptHtml.includes('concept-page-b2__entry-cta'));

        const primedHtml = renderActiveEntryHtml(
          { id: 'primed', label: 'Primed', drill_status: 'primed' },
          0,
          [{ id: 'primed', label: 'Primed', drill_status: 'primed' }],
          {},
          { metadata: {} },
          {
            node_records: {
              primed: {
                attempts: [{
                  id: 'p1',
                  kind: 'cold',
                  at: '2026-05-15T10:00:00.000Z',
                  user_text: 'A strong first attempt.',
                  classification: 'strong',
                  gaps: [],
                  grader_version: 'qa',
                }],
                repairs: [],
              },
            },
          }
        );
        assert.ok(primedHtml.includes('concept-page-b2__threshold--empty'));
        assert.ok(primedHtml.includes('add sketch'));
        assert.ok(primedHtml.includes('study required entry 1 of 1'));
        assert.ok(primedHtml.includes('data-active-entry-action="study"'));
        assert.ok(primedHtml.includes('Reveal study note'));

        const studiedHtml = renderActiveEntryHtml(
          { id: 'studied', label: 'Studied', purpose: 'Study note for this entry.' },
          0,
          [{ id: 'studied', label: 'Studied', purpose: 'Study note for this entry.' }],
          {},
          { metadata: {} },
          {
            node_records: {
              studied: {
                attempts: [{
                  id: 'st1',
                  kind: 'cold',
                  at: '2026-05-15T10:00:00.000Z',
                  user_text: 'A strong first attempt.',
                  classification: 'strong',
                  gaps: [],
                  grader_version: 'qa',
                }],
                study_revealed_at: '2026-05-15T10:05:00.000Z',
                repairs: [],
              },
            },
          },
          { now: '2026-05-15T11:00:00.000Z' }
        );
        assert.ok(studiedHtml.includes('review pending entry 1 of 1'));
        assert.ok(studiedHtml.includes('concept-page-b2__evidence'));
        assert.ok(studiedHtml.includes('learner reconstruction'));
        assert.ok(studiedHtml.includes('A strong first attempt.'));
        assert.ok(studiedHtml.includes('No repair hinge recorded for this reconstruction.'));
        assert.ok(studiedHtml.includes('concept-page-b2__study-note'));
        assert.ok(studiedHtml.includes('Study note for this entry.'));
        assert.ok(!studiedHtml.includes('concept-page-b2__entry-cta'));

        const principleHtml = renderActiveEntryHtml(
          { id: 'principle', label: 'Principle', principle: 'Entry-specific generated principle.' },
          0,
          [{ id: 'principle', label: 'Principle', principle: 'Entry-specific generated principle.' }],
          { startingMapContext: 'Learner sketch.', contentPreview: 'Global source preview should not appear.' },
          { metadata: { core_thesis: 'Global core thesis should not appear.' } },
          {
            node_records: {
              principle: {
                attempts: [{
                  id: 'pr1',
                  kind: 'cold',
                  at: '2026-05-15T10:00:00.000Z',
                  user_text: 'A strong first attempt.',
                  classification: 'strong',
                  gaps: [],
                  grader_version: 'qa',
                }],
                study_revealed_at: '2026-05-15T10:05:00.000Z',
                repairs: [],
              },
            },
          },
          { now: '2026-05-15T11:00:00.000Z' }
        );
        assert.ok(principleHtml.includes('Entry-specific generated principle.'));
        assert.ok(!principleHtml.includes('Global core thesis should not appear.'));
        assert.ok(!principleHtml.includes('Global source preview should not appear.'));

        const studiedAttemptHtml = renderActiveEntryHtml(
          { id: 'studied', label: 'Studied', purpose: 'Study note for this entry.' },
          0,
          [{ id: 'studied', label: 'Studied', purpose: 'Study note for this entry.' }],
          {},
          { metadata: {} },
          {
            node_records: {
              studied: {
                attempts: [{
                  id: 'st1',
                  kind: 'cold',
                  at: '2026-05-15T10:00:00.000Z',
                  user_text: 'A strong first attempt.',
                  classification: 'strong',
                  gaps: [],
                  grader_version: 'qa',
                }],
                study_revealed_at: '2026-05-15T10:05:00.000Z',
                repairs: [],
              },
            },
          },
          { now: '2026-05-15T11:00:00.000Z', attemptEntryId: 'studied' }
        );
        assert.ok(!studiedAttemptHtml.includes('concept-page-b2__attempt'));
        assert.ok(studiedAttemptHtml.includes('concept-page-b2__study-note'));

        const repairHtml = renderActiveEntryHtml(
          { id: 'repair', label: 'Repair', study_note: 'Study the channel gate.' },
          0,
          [{ id: 'repair', label: 'Repair', study_note: 'Study the channel gate.' }],
          {},
          { metadata: {} },
          {
            node_records: {
              repair: {
                attempts: [{
                  id: 'rp1',
                  kind: 'cold',
                  at: '2026-05-15T10:00:00.000Z',
                  user_text: 'Sodium just rushes in.',
                  classification: 'thin',
                  gaps: [{
                    mechanism: 'channel gate',
                    correction: 'Name that voltage-gated sodium channels open at threshold.',
                  }],
                  grader_version: 'qa',
                }],
                study_revealed_at: '2026-05-15T10:05:00.000Z',
                repairs: [],
              },
            },
          }
        );
        assert.ok(repairHtml.includes('repair the gap entry 1 of 1'));
        assert.ok(repairHtml.includes('concept-page-b2__evidence'));
        assert.ok(repairHtml.includes('Sodium just rushes in.'));
        assert.ok(repairHtml.includes('Name that voltage-gated sodium channels open at threshold.'));
        assert.ok(repairHtml.includes('concept-page-b2__repair'));
        assert.ok(repairHtml.includes('channel gate'));
        assert.ok(repairHtml.includes('Name that voltage-gated sodium channels open at threshold.'));
        assert.ok(repairHtml.includes('data-repair-entry-id="repair"'));
        assert.ok(repairHtml.includes('Write the missing link'));
        assert.ok(repairHtml.includes('Save repair'));
        const fallbackRepairHtml = renderActiveEntryHtml(
          { label: 'Fallback repair', study_note: 'Study the unnamed entry.' },
          1,
          [{ id: 'done', label: 'Done', drill_status: 'solidified' }, { label: 'Fallback repair', study_note: 'Study the unnamed entry.' }],
          {},
          { metadata: {} },
          {
            node_records: {
              'entry-1': {
                attempts: [{
                  id: 'fr1',
                  kind: 'cold',
                  at: '2026-05-15T10:00:00.000Z',
                  user_text: 'Incomplete fallback answer.',
                  classification: 'thin',
                  gaps: [{ mechanism: 'fallback link', correction: 'Name the fallback mechanism.' }],
                  grader_version: 'qa',
                }],
                study_revealed_at: '2026-05-15T10:05:00.000Z',
                repairs: [],
              },
            },
          }
        );
        assert.ok(fallbackRepairHtml.includes('data-repair-entry-id="entry-1"'));
        assert.ok(!fallbackRepairHtml.includes('data-repair-entry-id="core-thesis"'));

        const repairedHtml = renderActiveEntryHtml(
          { id: 'repair', label: 'Repair' },
          0,
          [{ id: 'repair', label: 'Repair' }],
          {},
          { metadata: {} },
          {
            node_records: {
              repair: {
                attempts: [{
                  id: 'rp1',
                  kind: 'cold',
                  at: '2026-05-15T10:00:00.000Z',
                  user_text: 'Sodium just rushes in.',
                  classification: 'thin',
                  gaps: [{ mechanism: 'channel gate', correction: 'Name the gate.' }],
                  grader_version: 'qa',
                }],
                study_revealed_at: '2026-05-15T10:05:00.000Z',
                repairs: [{
                  id: 'rr1',
                  at: '2026-05-15T10:10:00.000Z',
                  text: 'Voltage-gated channels open at threshold.',
                }],
              },
            },
          }
        );
        assert.ok(repairedHtml.includes('ready to reconstruct again entry 1 of 1'));
        assert.ok(repairedHtml.includes('Write it again'));
        assert.ok(!repairedHtml.includes('concept-page-b2__repair'));

        const stripHtml = renderConceptStripHtml(backbone, backbone[1], 1, training);
        assert.ok(stripHtml.includes('class="concept-strip"'));
        assert.ok(stripHtml.includes('viewBox="0 0 600 110"'));
        assert.ok(stripHtml.includes('concept-strip__edge is-active'));
        assert.ok(stripHtml.includes('data-entry-id="core"'));
        assert.ok(stripHtml.includes('data-entry-id="entry-2"'));
        assert.ok(stripHtml.includes('data-entry-index="2"'));
        assert.ok(stripHtml.includes('concept-strip__node--primed'));
        assert.ok(stripHtml.includes('concept-strip__node--ready is-active'));
        assert.ok(stripHtml.includes('concept-strip__node--locked'));
        assert.ok(stripHtml.includes('r="9"'));
        assert.ok(stripHtml.includes('Second &amp; unsafe · 2 of 3'));
        assert.ok(stripHtml.includes('aria-label="Second &amp; unsafe, ready to reconstruct, current"'));

        const emptyStripHtml = renderConceptStripHtml([], { id: 'core-thesis', label: 'Core thesis' }, 0);
        assert.ok(emptyStripHtml.includes('data-entry-id="core-thesis"'));
        assert.ok(emptyStripHtml.includes('core thesis, ready to reconstruct, current'));
        assert.ok(emptyStripHtml.includes('<text x="60" y="80">core thesis</text>'));
        """
    )
    assert result.returncode == 0, result.stderr
