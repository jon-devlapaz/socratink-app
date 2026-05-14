from __future__ import annotations

import os
import re
from urllib.parse import urljoin

from playwright.sync_api import Page, expect


def _enter_app_shell_as_guest(page: Page, base_url: str) -> None:
    if os.getenv("SOCRATINK_E2E_LOCAL_GUEST"):
        page.goto(urljoin(base_url + "/", "auth/e2e/guest?return_to=%2F"))
    else:
        page.goto(base_url)
        if "/login" in page.url:
            target_pattern = re.compile(r"^" + re.escape(base_url.rstrip("/")) + r"/?$")
            with page.expect_navigation(url=target_pattern, timeout=15_000):
                page.locator("#guest-continue-link").click()
    page.wait_for_load_state("load")
    expect(page.locator("#concept-list")).to_be_attached()


def test_app_helper_modules_preserve_browser_contracts(clean_page: Page, base_url: str) -> None:
    _enter_app_shell_as_guest(clean_page, base_url)

    clean_page.locator("#hero-source-attach").click()
    expect(clean_page.locator("#hero-source-panel .overlay-textarea")).to_be_visible()
    clean_page.locator("#hero-source-panel .overlay-textarea").fill("source text")
    clean_page.locator("#hero-source-panel .creation-source-panel-attach").click()
    expect(clean_page.locator("#hero-source-value")).to_have_text("11 chars pasted")
    expect(clean_page.locator("#hero-source-attach")).to_have_text("remove")

    clean_page.evaluate("window.App.showSettings()")
    expect(clean_page.locator("#settings-content")).to_be_visible()
    expect(clean_page.locator("#settings-identity-email")).to_have_text("Guest")
    clean_page.locator('.settings-pill[data-theme-value="dark"]').click()
    expect(clean_page.locator('.settings-pill[data-theme-value="dark"]')).to_have_attribute("aria-checked", "true")
    expect(clean_page.locator("html")).to_have_attribute("data-theme", "dark")
    clean_page.locator("#theme-toggle").click()
    expect(clean_page.locator('.settings-pill[data-theme-value="light"]')).to_have_attribute("aria-checked", "true")
    clean_page.locator("#settings-motion-toggle").click()
    expect(clean_page.locator("#settings-motion-toggle")).to_have_attribute("aria-checked", "true")
    expect(clean_page.locator("html")).to_have_attribute("data-motion", "reduced")
    clean_page.locator("#settings-sound-toggle").click()
    expect(clean_page.locator("#settings-sound-toggle")).to_have_attribute("aria-checked", "false")

    result = clean_page.evaluate(
        """async () => {
            const assert = (condition, message) => {
              if (!condition) throw new Error(message);
            };
            const same = (actual, expected, message) => {
              const a = JSON.stringify(actual);
              const e = JSON.stringify(expected);
              if (a !== e) throw new Error(`${message}: ${a} !== ${e}`);
            };

            const html = await import('/js/html.js');
            assert(html.escHtml(`<&>"'`) === '&lt;&amp;&gt;&quot;&#39;', 'html escaping');
            assert(html.escHtml(null) === '', 'null escaping');

            const hero = await import('/js/app-hero.js');
            for (const [state, label] of [
              ['instantiated', 'source captured'],
              ['growing', 'concept'],
              ['fractured', 'worth revisiting'],
              ['hibernating', 'spacing'],
              ['actualized', 'spaced evidence'],
              ['missing', 'no concepts yet'],
            ]) {
              assert(hero.getHeroStateLabel(state) === label, `label ${state}`);
            }
            assert(hero.getHeroGuidance(null).includes('Pick a tile'), 'empty guidance');
            assert(hero.getHeroGuidance({ state: 'instantiated', graphData: {} }).includes('hypothesis'), 'instantiated graph guidance');
            assert(hero.getHeroGuidance({ state: 'instantiated', graphData: null }).includes('not learner evidence'), 'instantiated draft guidance');
            assert(hero.getHeroGuidance({ state: 'growing', graphData: {} }).includes('cold attempt'), 'growing graph guidance');
            assert(hero.getHeroGuidance({ state: 'growing', graphData: null }).includes('Continue'), 'growing draft guidance');
            assert(hero.getHeroGuidance({ state: 'fractured' }).includes('gap'), 'fractured guidance');
            assert(hero.getHeroGuidance({ state: 'hibernating' }).includes('spacing'), 'hibernating guidance');
            assert(hero.getHeroGuidance({ state: 'actualized' }).includes('Spaced evidence'), 'actualized guidance');
            assert(hero.getHeroGuidance({ state: 'unknown' }).includes('Pick a tile'), 'fallback guidance');
            same(hero.getHeroActionConfig(null), { label: 'Begin', action: 'add', disabled: false }, 'empty action');
            same(hero.getHeroActionConfig({ state: 'instantiated', graphData: {} }), { label: 'Open Draft Path', action: 'open-map', disabled: false }, 'instantiated graph action');
            same(hero.getHeroActionConfig({ state: 'instantiated', graphData: null }), { label: 'Draft Map', action: 'extract', disabled: false }, 'instantiated draft action');
            same(hero.getHeroActionConfig({ state: 'growing', graphData: {} }), { label: 'Open Draft Path', action: 'open-map', disabled: false }, 'growing graph action');
            same(hero.getHeroActionConfig({ state: 'growing', graphData: null }), { label: 'Draft Map', action: 'extract', disabled: false }, 'growing draft action');
            same(hero.getHeroActionConfig({ state: 'fractured' }), { label: 'Repair Gap', action: 'drill', disabled: false }, 'fractured action');
            same(hero.getHeroActionConfig({ state: 'hibernating', graphData: {} }), { label: 'Open Evidence Map', action: 'open-map', disabled: false }, 'hibernating graph action');
            same(hero.getHeroActionConfig({ state: 'hibernating', graphData: null }), { label: 'Return Later', action: 'wait', disabled: true }, 'hibernating wait action');
            same(hero.getHeroActionConfig({ state: 'actualized', graphData: {} }), { label: 'Open Evidence Map', action: 'open-map', disabled: false }, 'actualized graph action');
            same(hero.getHeroActionConfig({ state: 'actualized', graphData: null }), { label: 'Open Desk', action: 'wait', disabled: true }, 'actualized wait action');
            same(hero.getHeroActionConfig({ state: 'unknown' }), { label: 'Begin', action: 'add', disabled: false }, 'fallback action');
            assert(hero.describeDoorSource(null) === '', 'empty source label');
            assert(hero.describeDoorSource({ type: 'text', text: 'abc' }) === '3 chars pasted', 'text source label');
            assert(hero.describeDoorSource({ type: 'url', url: 'https://example.com' }) === 'https://example.com', 'url source label');
            assert(hero.describeDoorSource({ type: 'url' }) === 'URL', 'url fallback source label');
            assert(hero.describeDoorSource({ type: 'file', filename: 'notes.md', text: 'abcd' }).includes('4 chars'), 'file source label');
            assert(hero.describeDoorSource({ type: 'custom' }) === 'custom', 'custom source label');

            const phase = await import('/js/phase-b-session.js');
            const backing = new Map();
            const storage = {
              getItem(key) { return backing.has(key) ? backing.get(key) : null; },
              setItem(key, value) { backing.set(key, String(value)); },
              removeItem(key) { backing.delete(key); },
            };
            same(phase.getDefaultPhaseBSessionState(), {
              startedAt: null,
              nodesDrilled: 0,
              visitedNodeIds: [],
              retriesByNode: {},
              events: [],
            }, 'default phase state');
            assert(phase.getPhaseBSessionStorageKey('c1') === 'learnops-phase-b-session:c1', 'phase key');
            assert(phase.getPhaseBSessionStorageKey() === 'learnops-phase-b-session', 'phase fallback key');
            same(phase.loadPhaseBSessionState({ conceptId: 'missing', storage }), phase.getDefaultPhaseBSessionState(), 'missing session');
            phase.persistPhaseBSessionState({
              startedAt: '2026-05-13T10:00:00.000Z',
              nodesDrilled: 99,
              visitedNodeIds: ['a', '', 'b'],
              retriesByNode: { a: 1 },
              events: [{ type: 'study' }],
            }, { conceptId: 'c1', storage });
            same(phase.loadPhaseBSessionState({ conceptId: 'c1', storage }), {
              startedAt: '2026-05-13T10:00:00.000Z',
              nodesDrilled: 2,
              visitedNodeIds: ['a', 'b'],
              retriesByNode: { a: 1 },
              events: [{ type: 'study' }],
            }, 'loaded session');
            backing.set('learnops-phase-b-session:bad', '{');
            same(phase.loadPhaseBSessionState({ conceptId: 'bad', storage, logger: { warn() {} } }), phase.getDefaultPhaseBSessionState(), 'bad session');
            phase.persistPhaseBSessionState({}, { storage: { setItem() { throw new Error('denied'); } }, logger: { warn() {} } });
            phase.persistPhaseBResumeState({ conceptId: 'c1', nodeId: 'n1', mode: 'study' }, { storage });
            same(phase.loadPhaseBResumeState({ storage }), { conceptId: 'c1', nodeId: 'n1', mode: 'study' }, 'resume state');
            phase.persistPhaseBResumeState(null, { storage });
            assert(phase.loadPhaseBResumeState({ storage }) === null, 'cleared resume');
            backing.set('learnops-phase-b-resume', JSON.stringify({ conceptId: 'c1', nodeId: 'n1', mode: 'read' }));
            assert(phase.loadPhaseBResumeState({ storage }) === null, 'invalid resume mode');
            backing.set('learnops-phase-b-resume', '{');
            assert(phase.loadPhaseBResumeState({ storage, logger: { warn() {} } }) === null, 'bad resume');
            phase.persistPhaseBResumeState({ conceptId: 'c1', nodeId: 'n1', mode: 'study' }, { storage: { setItem() { throw new Error('denied'); } }, logger: { warn() {} } });
            const originalSessionStorage = Object.getOwnPropertyDescriptor(window, 'sessionStorage');
            Object.defineProperty(window, 'sessionStorage', {
              configurable: true,
              get() { throw new Error('storage denied'); },
            });
            same(phase.loadPhaseBSessionState(), phase.getDefaultPhaseBSessionState(), 'denied session storage');
            assert(phase.loadPhaseBResumeState() === null, 'denied resume storage');
            phase.persistPhaseBSessionState({});
            phase.persistPhaseBResumeState({ conceptId: 'c1', nodeId: 'n1', mode: 'study' });
            Object.defineProperty(window, 'sessionStorage', originalSessionStorage);
            Object.defineProperty(window, 'sessionStorage', { configurable: true, value: undefined });
            same(phase.loadPhaseBSessionState(), phase.getDefaultPhaseBSessionState(), 'missing session storage');
            Object.defineProperty(window, 'sessionStorage', originalSessionStorage);

            const settings = await import('/js/settings-view.js');
            const existingMount = document.getElementById('settings-content');
            if (existingMount) existingMount.remove();
            await settings.renderSettingsView({ documentRef: document });
            const mount = document.createElement('div');
            mount.id = 'settings-content';
            document.body.append(mount);
            const themeButton = document.createElement('button');
            themeButton.id = 'theme-toggle';
            document.body.append(themeButton);
            let theme = 'light';
            const audioCalls = [];
            const deps = {
              documentRef: document,
              fetchAuthSession: async () => ({ guest_mode: true, auth_enabled: true }),
              isGuestSession: (session) => Boolean(session?.guest_mode),
              isIdentifiedUserSession: (session) => Boolean(session?.user?.email),
              buildLoginHref: () => '/login?return_to=%2F',
              logout: async () => {},
              redirectToLogin: () => {},
              getStoredThemePreference: () => theme,
              setTheme: (next) => { theme = next === 'dark' ? 'dark' : 'light'; },
              AudioFX: {
                enabled: false,
                setEnabled(next) { this.enabled = next; audioCalls.push(`enabled:${next}`); },
                playFocusTap() { audioCalls.push('tap'); },
              },
            };
            localStorage.setItem('socratink.motion', 'reduced');
            await settings.renderSettingsView(deps);
            assert(mount.querySelector('#settings-identity-email').textContent === 'Guest', 'guest identity');
            mount.querySelector('[data-theme-value="dark"]').click();
            assert(theme === 'dark', 'settings theme click');
            themeButton.click();
            await new Promise((resolve) => setTimeout(resolve, 0));
            assert(mount.querySelector('[data-theme-value="dark"]').getAttribute('aria-checked') === 'true', 'corner theme sync');
            const motion = mount.querySelector('#settings-motion-toggle');
            assert(motion.getAttribute('aria-checked') === 'true', 'stored reduced motion');
            motion.click();
            assert(!document.documentElement.dataset.motion, 'motion cleared');
            motion.click();
            assert(document.documentElement.dataset.motion === 'reduced', 'motion restored');
            const sound = mount.querySelector('#settings-sound-toggle');
            sound.click();
            assert(audioCalls.includes('enabled:true') && audioCalls.includes('tap'), 'sound enabled cue');
            const originalLocalStorage = Object.getOwnPropertyDescriptor(window, 'localStorage');
            Object.defineProperty(window, 'localStorage', {
              configurable: true,
              get() { throw new Error('local storage denied'); },
            });
            await settings.renderSettingsView(deps);
            assert(mount.querySelector('#settings-motion-toggle').getAttribute('aria-checked') === 'false', 'motion storage fallback');
            Object.defineProperty(window, 'localStorage', originalLocalStorage);
            deps.fetchAuthSession = async () => ({ user: { email: 'learner@example.com' } });
            deps.logout = async () => { throw new Error('logout failed'); };
            await settings.renderSettingsView(deps);
            assert(mount.querySelector('#settings-identity-email').textContent === 'learner@example.com', 'identified identity');
            const failedLogoutButton = mount.querySelector('.settings-identity-action');
            failedLogoutButton.click();
            await new Promise((resolve) => setTimeout(resolve, 20));
            assert(failedLogoutButton.disabled === false, 'failed logout re-enables button');
            deps.logout = async () => {};
            deps.redirectToLogin = (path) => { window.__settingsRedirect = path; };
            await settings.renderSettingsView(deps);
            mount.querySelector('.settings-identity-action').click();
            await new Promise((resolve) => setTimeout(resolve, 0));
            assert(window.__settingsRedirect === '/', 'logout redirect');
            deps.fetchAuthSession = async () => ({ auth_enabled: false });
            await settings.renderSettingsView(deps);
            assert(mount.querySelector('#settings-identity-row').hidden, 'auth disabled hidden');
            deps.fetchAuthSession = async () => ({});
            await settings.renderSettingsView(deps);
            assert(mount.querySelector('#settings-identity-row').hidden, 'unknown hidden');
            deps.fetchAuthSession = async () => { throw new Error('api unavailable'); };
            await settings.renderSettingsView(deps);
            assert(mount.querySelector('#settings-identity-row').hidden, 'fetch failure hidden');

            const library = await import('/js/library-view.js');
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
            same(library.getLibraryConceptMeta({ name: 'Concept', state: 'growing', graphData: graph }), {
              thesis: 'This is the central claim.',
              architecture: 'cause effect',
              difficulty: 'medium',
              clusterCount: 2,
              subnodeCount: 3,
              sourceLabel: 'Map: Source Title',
            }, 'library metadata');
            assert(library.getLibraryConceptMeta({
              contentFilename: 'notes.md',
              graphData: JSON.stringify({ metadata: { core_thesis: 'From file' }, clusters: [] }),
            }).sourceLabel === 'Source: notes.md', 'library filename source');
            assert(library.getLibraryConceptMeta({ graphData: '{' }).thesis.includes('No summary'), 'library malformed fallback');
            assert(library.buildLibraryHtml([]).includes('Begin a reconstruction.'), 'library empty state');
            const libraryHtml = library.buildLibraryHtml([
              { id: 'c-1', name: '<Unsafe>', state: 'growing', graphData: graph },
            ]);
            assert(libraryHtml.includes('App.openLibraryConcept(\\'c-1\\')'), 'library card onclick');
            assert(libraryHtml.includes('&lt;Unsafe&gt;'), 'library escaped name');
            assert(libraryHtml.includes('2 sections'), 'library section count');
            assert(libraryHtml.includes('3 entries'), 'library entry count');
            window.App.showLibrary();
            assert(document.getElementById('library-view').classList.contains('visible'), 'library view visible');
            assert(document.getElementById('library-content').textContent.includes('Begin a reconstruction.'), 'library app path');

            const sourceInput = await import('/js/source-input-ui.js');
            assert(sourceInput.isBlockedVideoUrl('https://youtu.be/abc'), 'blocked short youtube url');
            assert(sourceInput.isBlockedVideoUrl('https://www.youtube-nocookie.com/embed/abc'), 'blocked nocookie url');
            assert(!sourceInput.isBlockedVideoUrl('https://example.com/article'), 'allowed url');
            assert(!sourceInput.isBlockedVideoUrl('not a url'), 'invalid url allowed');
            assert(sourceInput.shortOnboardingText('  a   b\\n c  ', 20) === 'a b c', 'short text normalizes whitespace');
            assert(sourceInput.shortOnboardingText('abcdefghij', 8) === 'abcde...', 'short text truncates');
            assert(sourceInput.shortOnboardingText(null) === '', 'short text null fallback');
            assert(sourceInput.hasStudyEvidence({ drill_status: 'primed' }), 'primed evidence');
            assert(sourceInput.hasStudyEvidence({ drill_status: 'drilled' }), 'drilled evidence');
            assert(sourceInput.hasStudyEvidence({ drill_status: 'solidified' }), 'solidified evidence');
            assert(sourceInput.hasStudyEvidence({ drill_status: 'solid' }), 'solid evidence');
            assert(sourceInput.hasStudyEvidence({ gap_type: 'misread' }), 'gap evidence');
            assert(!sourceInput.hasStudyEvidence({ drill_status: 'new' }), 'no evidence fallback');
            assert(sourceInput.SOURCE_INPUT_HTML(true).includes('paste-clipboard-btn'), 'clipboard template');
            assert(!sourceInput.SOURCE_INPUT_HTML(false).includes('paste-clipboard-btn'), 'no clipboard template');

            const sourceMount = document.createElement('div');
            document.body.append(sourceMount);
            const sourceSubmits = [];
            const sourceUi = sourceInput.buildContentInputUI(sourceMount, {
              showClipboard: true,
              readFile(file, onSuccess, onError) {
                if (file.name === 'bad.txt') {
                  onError('bad file', '', file.name);
                  return;
                }
                onSuccess('uploaded text', file.name);
              },
              onSubmit(payload) { sourceSubmits.push(payload); },
              onCancel() { window.__sourceInputCancelled = true; },
            });
            assert(sourceMount.querySelector('.overlay-extract').disabled, 'initial submit disabled');
            Object.defineProperty(navigator, 'clipboard', {
              configurable: true,
              value: { readText: async () => 'clipboard text' },
            });
            sourceMount.querySelector('.paste-clipboard-btn').click();
            await new Promise((resolve) => setTimeout(resolve, 0));
            assert(sourceMount.querySelector('.overlay-textarea').value === 'clipboard text', 'clipboard paste');
            sourceMount.querySelector('.overlay-extract').dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
            same(sourceSubmits.pop(), { text: 'clipboard text', type: 'text', filename: null, url: null }, 'paste submit');
            Object.defineProperty(navigator, 'clipboard', {
              configurable: true,
              value: { readText: async () => { throw new Error('denied'); } },
            });
            const originalExecCommand = document.execCommand;
            document.execCommand = (command) => {
              window.__sourceInputPasteFallback = command;
              return true;
            };
            sourceMount.querySelector('.paste-clipboard-btn').click();
            await new Promise((resolve) => setTimeout(resolve, 0));
            assert(window.__sourceInputPasteFallback === 'paste', 'clipboard fallback paste command');
            document.execCommand = originalExecCommand;

            sourceMount.querySelector('[data-tab="url"]').click();
            const urlInput = sourceMount.querySelector('.overlay-url-input');
            urlInput.value = 'https://www.youtube.com/watch?v=abc';
            urlInput.dispatchEvent(new Event('input', { bubbles: true }));
            assert(sourceMount.querySelector('.overlay-extract').disabled, 'blocked url disabled');
            assert(sourceMount.querySelector('.overlay-url-feedback').textContent.includes('Video links'), 'blocked url feedback');
            urlInput.value = 'https://example.com/article';
            urlInput.dispatchEvent(new Event('input', { bubbles: true }));
            urlInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true }));
            same(sourceSubmits.pop(), {
              text: 'https://example.com/article',
              type: 'url',
              filename: null,
              url: 'https://example.com/article',
            }, 'url submit');

            sourceMount.querySelector('[data-tab="upload"]').click();
            const goodDrop = new Event('drop', { bubbles: true, cancelable: true });
            Object.defineProperty(goodDrop, 'dataTransfer', { value: { files: [new File(['ok'], 'ok.txt')] } });
            sourceMount.querySelector('.overlay-dropzone').dispatchEvent(goodDrop);
            const uploadFeedback = () => sourceMount.querySelector('[data-panel="upload"] .overlay-dropfeedback');
            assert(uploadFeedback().textContent.includes('ok.txt'), 'upload feedback');
            sourceMount.querySelector('.overlay-extract').dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
            same(sourceSubmits.pop(), { text: 'uploaded text', type: 'file', filename: 'ok.txt', url: null }, 'file submit');
            const badDrop = new Event('drop', { bubbles: true, cancelable: true });
            Object.defineProperty(badDrop, 'dataTransfer', { value: { files: [new File(['bad'], 'bad.txt')] } });
            sourceMount.querySelector('.overlay-dropzone').dispatchEvent(badDrop);
            assert(uploadFeedback().textContent === 'bad file', 'upload error');
            const fileInput = sourceMount.querySelector('input[type="file"]');
            Object.defineProperty(fileInput, 'files', { configurable: true, value: [new File(['changed'], 'changed.txt')] });
            fileInput.dispatchEvent(new Event('change', { bubbles: true }));
            assert(uploadFeedback().textContent.includes('changed.txt'), 'file input change upload');
            sourceMount.querySelector('.overlay-cancel').click();
            assert(window.__sourceInputCancelled, 'source cancel');
            sourceUi.destroy();
            assert(sourceMount.innerHTML === '', 'source destroy');

            const board = await import('/js/board-grid.js');
            assert(board.TILE_PLATFORM.includes('tile-top'), 'tile platform markup');
            assert(board.EMPTY_TILE.includes('tile-top-empty'), 'empty tile markup');
            assert(board.conceptPinSVG(4, 'actualized').includes('concept-marker-anim-4'), 'pin animation id');
            const boardEvents = [];
            const tileA = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            const tileB = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            board.renderGrid({
              concepts: [{ id: 'c1', name: 'First', state: 'growing' }],
              tileEls: [tileA, tileB],
              activeId: 'c1',
              bus: { emit(eventName) { boardEvents.push(eventName); } },
            });
            assert(tileA.getAttribute('class') === 'tile-group selected', 'selected tile class');
            assert(tileA.getAttribute('role') === 'button', 'tile role');
            assert(tileA.getAttribute('tabindex') === '0', 'tile tabindex');
            assert(tileA.getAttribute('aria-label') === 'Open First', 'tile label');
            assert(tileA.innerHTML.includes('concept-pin-0'), 'tile pin');
            assert(tileB.getAttribute('class') === 'tile-group empty', 'empty tile class');
            assert(tileB.getAttribute('aria-label') === 'New concept', 'empty tile label');
            same(boardEvents, ['grid:rendered'], 'board event');
            const animEl = document.createElement('div');
            animEl.id = 'concept-marker-anim-7';
            animEl.classList.add('anim-crack');
            document.body.append(animEl);
            board.playAnim('emerge', 7);
            assert(animEl.classList.contains('anim-emerge'), 'animation class added');
            assert(!animEl.classList.contains('anim-crack'), 'old animation removed');
            animEl.dispatchEvent(new Event('animationend'));
            assert(!animEl.classList.contains('anim-emerge'), 'animation class cleaned');
            board.playAnim('missing', 7);

            const themeModule = await import('/js/theme-preference.js');
            assert(themeModule.THEME_STORAGE_KEY === 'learnops-theme', 'theme key');
            assert(themeModule.normalizeThemePreference('dark') === 'dark', 'dark normalize');
            assert(themeModule.normalizeThemePreference('sepia') === 'light', 'fallback normalize');
            assert(themeModule.getToggledTheme('dark') === 'light', 'toggle dark');
            assert(themeModule.getToggledTheme('light') === 'dark', 'toggle light');
            const themeStorage = new Map();
            const themeStorageLike = {
              getItem(key) { return themeStorage.has(key) ? themeStorage.get(key) : null; },
              setItem(key, value) { themeStorage.set(key, String(value)); },
            };
            assert(themeModule.getStoredThemePreference({ storage: themeStorageLike }) === 'light', 'missing theme defaults light');
            themeStorage.set('learnops-theme', 'dark');
            assert(themeModule.getStoredThemePreference({ storage: themeStorageLike }) === 'dark', 'stored dark');
            assert(themeModule.getStoredThemePreference({
              storage: { getItem() { throw new Error('denied'); } },
              logger: { warn() {} },
            }) === 'light', 'stored theme read fallback');
            const themeToggle = document.createElement('button');
            themeModule.updateThemeToggleUi('dark', themeToggle);
            assert(themeToggle.dataset.theme === 'dark', 'toggle dataset');
            assert(themeToggle.getAttribute('aria-pressed') === 'true', 'toggle pressed');
            assert(themeToggle.getAttribute('title') === 'Switch to light mode', 'toggle title');
            const remounts = [];
            const resolvedDark = themeModule.applyThemePreference('dark', {
              themeToggleEl: themeToggle,
              storage: themeStorageLike,
              onRemount() { remounts.push('remount'); },
            });
            assert(resolvedDark === 'dark', 'apply dark return');
            assert(document.body.classList.contains('night'), 'body night');
            assert(document.body.dataset.theme === 'dark', 'body theme');
            assert(document.documentElement.dataset.theme === 'dark', 'html theme');
            same(remounts, ['remount'], 'theme remount');
            const resolvedLight = themeModule.applyThemePreference('unknown', {
              themeToggleEl: null,
              storage: themeStorageLike,
              persist: false,
              onRemount() { remounts.push('remount'); },
            });
            assert(resolvedLight === 'light', 'apply fallback return');
            assert(!document.body.classList.contains('night'), 'body light');
            assert(themeStorage.get('learnops-theme') === 'dark', 'persist false skips write');
            themeModule.applyThemePreference('dark', {
              themeToggleEl: null,
              storage: { setItem() { throw new Error('denied'); } },
              logger: { warn() {} },
              onRemount() {},
            });
            window.App.setTheme('light');
            assert(document.documentElement.dataset.theme === 'light', 'app setTheme light');
            window.App.toggleTheme();
            assert(document.documentElement.dataset.theme === 'dark', 'app toggle theme');

            return true;
        }"""
    )
    assert result is True
