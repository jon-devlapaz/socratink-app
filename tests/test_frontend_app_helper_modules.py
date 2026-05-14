"""Characterization tests for small app.js helper modules."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def run_node_module(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
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
            thesis: 'This is the central claim.',
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
        assert.ok(getLibraryConceptMeta({ graphData: '{' }).thesis.includes('No summary'));

        const emptyHtml = buildLibraryHtml([]);
        assert.ok(emptyHtml.includes('Begin a reconstruction.'));
        assert.ok(emptyHtml.includes('App.showIgnition()'));

        const cardHtml = buildLibraryHtml([
          { id: 'c-1', name: '<Unsafe>', state: 'growing', graphData: graph },
        ]);
        assert.ok(cardHtml.includes('onclick="App.openLibraryConcept(\\'c-1\\')"'));
        assert.ok(cardHtml.includes('&lt;Unsafe&gt;'));
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
        assert.ok(html.includes('App.deleteConcept(\\'c1\\',this)'));

        class FakeElement {
          constructor() {
            this.className = '';
            this.innerHTML = '';
            this.listeners = {};
            this.children = [];
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
        assert.equal(conceptListEl.children[1].className, 'concept-item active');
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
          renderActiveEntryHtml,
          renderConceptStripHtml,
        } from './public/js/concept-page-view.js';

        const backbone = [
          { id: 'core', label: '<Core>', drill_status: 'drilled', purpose: 'First purpose' },
          { id: 'entry-2', label: 'Second & unsafe', drill_status: 'locked' },
          { id: 'entry-3', label: 'Third', drill_status: 'locked' },
        ];

        const blockedHtml = renderActiveEntryHtml(
          backbone[2],
          2,
          backbone,
          { startingMapContext: '<threshold & sketch>' },
          { metadata: { core_thesis: 'fallback thesis' } }
        );
        assert.ok(blockedHtml.includes('&lt;threshold &amp; sketch&gt;'));
        assert.ok(blockedHtml.includes('locked entry 3 of 3'));
        assert.ok(blockedHtml.includes('aria-disabled="true"'));
        assert.ok(blockedHtml.includes('>Locked</button>'));
        assert.ok(blockedHtml.includes('&lt;Core&gt;'));
        assert.ok(blockedHtml.includes('Second &amp; unsafe'));
        assert.ok(blockedHtml.includes('LOCKED'));

        const readyHtml = renderActiveEntryHtml(
          backbone[1],
          1,
          backbone,
          { startingMapContext: '' },
          { metadata: { starting_map_context: 'metadata sketch' } }
        );
        assert.ok(readyHtml.includes('metadata sketch'));
        assert.ok(readyHtml.includes('first cold attempt entry 2 of 3'));
        assert.ok(readyHtml.includes('data-active-entry-id="entry-2"'));
        assert.ok(readyHtml.includes('Try from memory'));

        const primedHtml = renderActiveEntryHtml(
          { id: 'primed', label: 'Primed', drill_status: 'primed' },
          0,
          [{ id: 'primed', label: 'Primed', drill_status: 'primed' }],
          {},
          { metadata: {} }
        );
        assert.ok(primedHtml.includes('concept-page-b2__threshold--empty'));
        assert.ok(primedHtml.includes('add sketch'));
        assert.ok(primedHtml.includes('re-drill ready entry 1 of 1'));
        assert.ok(primedHtml.includes('Re-drill from memory'));

        const stripHtml = renderConceptStripHtml(backbone, backbone[1], 1);
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
        assert.ok(stripHtml.includes('aria-label="Second &amp; unsafe, ready for first attempt, current"'));

        const emptyStripHtml = renderConceptStripHtml([], { id: 'core-thesis', label: 'Core thesis' }, 0);
        assert.ok(emptyStripHtml.includes('data-entry-id="core-thesis"'));
        assert.ok(emptyStripHtml.includes('core thesis, ready for first attempt, current'));
        assert.ok(emptyStripHtml.includes('<text x="60" y="80">core thesis</text>'));
        """
    )
    assert result.returncode == 0, result.stderr
