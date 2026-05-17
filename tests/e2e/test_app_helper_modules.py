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
            const rejects = async (fn, pattern, message) => {
              let rejected = false;
              try {
                await fn();
              } catch (err) {
                rejected = true;
                assert(pattern.test(String(err?.message || err)), message);
              }
              assert(rejected, `${message}: did not reject`);
            };

            const html = await import('/js/html.js');
            assert(html.escHtml(`<&>"'`) === '&lt;&amp;&gt;&quot;&#39;', 'html escaping');
            assert(html.escHtml(null) === '', 'null escaping');

            const timerModule = await import('/js/app-timer.js');
            assert(timerModule.formatTimerSeconds(24 * 60 * 60) === '24:00:00', 'timer 24h formatting');
            assert(timerModule.formatTimerSeconds(3661) === '01:01:01', 'timer hour minute second formatting');
            let intervalCallback = null;
            const clearedIntervals = [];
            const timerDisplay = { textContent: '' };
            const completions = [];
            const timer = timerModule.createCountdownTimer({
              timerDisplay,
              initialSeconds: 10,
              onComplete() {
                completions.push(timer.getTimeLeft());
              },
              setIntervalRef(callback, delay) {
                intervalCallback = callback;
                assert(delay === 1000, 'timer interval delay');
                return 'browser-interval';
              },
              clearIntervalRef(intervalId) {
                clearedIntervals.push(intervalId);
              },
            });
            assert(timer.getTimeLeft() === 10, 'timer initial seconds');
            timer.start(2);
            assert(timerDisplay.textContent === '00:00:02', 'timer writes initial display on start');
            assert(clearedIntervals.length === 1 && clearedIntervals[0] === null, 'timer clears before start');
            intervalCallback();
            assert(timerDisplay.textContent === '00:00:01', 'timer decrements display');
            intervalCallback();
            assert(timerDisplay.textContent === '00:00:00', 'timer writes zero display');
            same(completions, [0], 'timer completion at zero');
            same(clearedIntervals, [null, 'browser-interval'], 'timer stop clears active interval');
            timer.fastForward();
            assert(timer.getTimeLeft() === 3, 'timer default fast-forward');
            timer.updateDisplay();
            assert(timerDisplay.textContent === '00:00:03', 'timer displays fast-forwarded value');
            timer.fastForward(7);
            assert(timer.getTimeLeft() === 7, 'timer custom fast-forward');
            const zeroCompletions = [];
            const zeroTimer = timerModule.createCountdownTimer({
              timerDisplay: { textContent: '' },
              onComplete() {
                zeroCompletions.push('complete');
              },
              setIntervalRef() {
                throw new Error('zero-second timer should not schedule an interval');
              },
            });
            zeroTimer.start(0);
            same(zeroCompletions, ['complete'], 'timer completes immediately at zero');
            const previousConceptsForTimer = localStorage.getItem('learnops_concepts');
            const previousActiveForTimer = localStorage.getItem('learnops_active');
            const timerFixture = {
              id: 'timer-fixture',
              name: 'Timer fixture',
              state: 'hibernating',
              timerStart: Date.now(),
              createdAt: Date.now(),
              graphData: JSON.stringify({
                metadata: { core_thesis: 'Timer fixture thesis.' },
                backbone: [],
                clusters: [],
              }),
            };
            localStorage.setItem('learnops_concepts', JSON.stringify([timerFixture]));
            localStorage.setItem('learnops_active', 'timer-fixture');
            window.App.selectConcept('timer-fixture');
            assert(document.getElementById('timer-display').style.display === 'block', 'app timer display visible for hibernating concept');
            assert(document.getElementById('timer-display').textContent === '24:00:00', 'app timer starts from remaining hibernation seconds');
            window.App.fastForward();
            timerFixture.state = 'growing';
            localStorage.setItem('learnops_concepts', JSON.stringify([timerFixture]));
            window.App.selectConcept('timer-fixture');
            if (previousConceptsForTimer === null) localStorage.removeItem('learnops_concepts');
            else localStorage.setItem('learnops_concepts', previousConceptsForTimer);
            if (previousActiveForTimer === null) localStorage.removeItem('learnops_active');
            else localStorage.setItem('learnops_active', previousActiveForTimer);

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
              thesis: 'No learner reconstruction recorded yet.',
              summarySource: 'none',
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
            const training = {
              node_records: {
                n1: {
                  attempts: [
                    {
                      id: 'a1',
                      at: '2026-05-15T10:00:00.000Z',
                      user_text: 'Thin first reconstruction.',
                      classification: 'thin',
                    },
                    {
                      id: 'a2',
                      at: '2026-05-15T11:00:00.000Z',
                      user_text: 'Learner-owned reconstruction.',
                      classification: 'strong',
                    },
                  ],
                },
              },
            };
            assert(library.getLibraryConceptMeta({ graphData: '{' }).thesis.includes('No learner reconstruction'), 'library malformed fallback');
            assert(library.getLibraryConceptMeta({ graphData: graph }, training).thesis === 'Learner-owned reconstruction.', 'library learner evidence');
            assert(library.buildLibraryHtml([]).includes('Begin a reconstruction.'), 'library empty state');
            const libraryHtml = library.buildLibraryHtml([
              { id: 'c-1', name: '<Unsafe>', state: 'growing', graphData: graph },
            ], { 'c-1': training });
            assert(libraryHtml.includes('data-concept-id="c-1"'), 'library card id data attr');
            assert(libraryHtml.includes('App.openLibraryConcept(this.dataset.conceptId)'), 'library card onclick');
            assert(libraryHtml.includes('&lt;Unsafe&gt;'), 'library escaped name');
            assert(libraryHtml.includes('Learner-owned reconstruction.'), 'library card learner evidence');
            assert(!libraryHtml.includes('This is the central claim.'), 'library card no AI thesis fallback');
            assert(libraryHtml.includes('2 sections'), 'library section count');
            assert(libraryHtml.includes('3 entries'), 'library entry count');
            window.App.showLibrary();
            assert(document.getElementById('library-view').classList.contains('visible'), 'library view visible');
            assert(document.getElementById('library-content').textContent.includes('Begin a reconstruction.'), 'library app path');

            const trainingStoreModule = await import('/js/training-store.js');
            assert(trainingStoreModule.TRAINING_SCHEMA_VERSION === 1, 'training schema version');
            const writes = new Map();
            const memoryStorage = {
              getItem(key) { return writes.has(key) ? writes.get(key) : null; },
              setItem(key, value) { writes.set(key, value); },
              removeItem(key) { writes.delete(key); },
            };
            const trainingStore = trainingStoreModule.createTrainingStore({ storage: memoryStorage });
            assert(await trainingStore.loadTraining('concept-training') === null, 'training initially empty');
            await trainingStore.saveTraining({ concept_id: 'saved-training', node_records: null });
            assert(JSON.parse(writes.get('socratink:training:v1:saved-training')).schema_version === 1, 'training save normalizes schema');
            await rejects(() => trainingStore.saveTraining({}), /concept-id-required/, 'training save requires concept id');
            await trainingStore.deleteTraining('saved-training');
            assert(await trainingStore.loadTraining('saved-training') === null, 'training delete clears concept evidence');
            await trainingStore.setProvenance('concept-training', {
              source_mode: 'source_less',
              grounding: 'learner_sketch',
              source_ref: null,
            });
            await trainingStore.setSketch('concept-training', {
              text: '  rough learner sketch  ',
              at: '2026-05-15T09:00:00.000Z',
            });
            await rejects(() => trainingStore.setSketch('concept-training', { text: 1, at: 'x' }), /sketch-text-required/, 'training rejects bad sketch text');
            await rejects(() => trainingStore.setSketch('concept-training', { text: 'x' }), /sketch-at-required/, 'training rejects missing sketch at');
            await rejects(() => trainingStore.setProvenance('concept-training', { source_mode: 'bad', grounding: 'source' }), /source-mode-invalid/, 'training rejects bad source mode');
            await rejects(() => trainingStore.setProvenance('concept-training', { source_mode: 'source_less', grounding: 'bad' }), /grounding-invalid/, 'training rejects bad grounding');
            await rejects(() => trainingStore.setProvenance('concept-training', { source_mode: 'source_less', grounding: 'source', source_ref: 'bad' }), /source-ref-invalid/, 'training rejects bad source ref');
            await rejects(() => trainingStore.appendAttempt('concept-training', '', {
              id: 'attempt-bad-node',
              at: '2026-05-15T10:00:00.000Z',
              user_text: 'attempt',
              classification: 'thin',
              gaps: [],
              grader_version: 'qa',
            }), /node-id-required/, 'training rejects missing node');
            await rejects(() => trainingStore.appendAttempt('concept-training', 'n1', {
              at: '2026-05-15T10:00:00.000Z',
              user_text: 'attempt',
              classification: 'thin',
              gaps: [],
              grader_version: 'qa',
            }), /attempt-id-required/, 'training rejects missing attempt id');
            await rejects(() => trainingStore.appendAttempt('concept-training', 'n1', {
              id: 'attempt-missing-at',
              user_text: 'attempt',
              classification: 'thin',
              gaps: [],
              grader_version: 'qa',
            }), /attempt-at-required/, 'training rejects missing attempt at');
            await rejects(() => trainingStore.appendAttempt('concept-training', 'n1', {
              id: 'attempt-empty',
              at: '2026-05-15T10:00:00.000Z',
              user_text: '   ',
              classification: 'thin',
              gaps: [],
              grader_version: 'qa',
            }), /user-text-required/, 'training rejects empty attempt');
            await rejects(() => trainingStore.appendAttempt('concept-training', 'n1', {
              id: 'attempt-bad-classification',
              at: '2026-05-15T10:00:00.000Z',
              user_text: 'attempt',
              classification: 'solid',
              gaps: [],
              grader_version: 'qa',
            }), /classification-invalid/, 'training rejects bad classification');
            await rejects(() => trainingStore.appendAttempt('concept-training', 'n1', {
              id: 'attempt-missing-grader',
              at: '2026-05-15T10:00:00.000Z',
              user_text: 'attempt',
              classification: 'thin',
              gaps: [],
            }), /grader-version-required/, 'training rejects missing grader');
            await rejects(() => trainingStore.appendAttempt('concept-training', 'n1', {
              id: 'attempt-missing-gaps',
              at: '2026-05-15T10:00:00.000Z',
              user_text: 'attempt',
              classification: 'thin',
              grader_version: 'qa',
            }), /gaps-required/, 'training rejects missing gaps');
            await trainingStore.appendAttempt('concept-training', 'n1', {
              id: 'attempt-1',
              kind: 'spaced',
              at: '2026-05-15T10:00:00.000Z',
              user_text: '  first learner answer  ',
              classification: 'thin',
              gaps: [{ mechanism: 'cause', correction: 'name cause' }],
              grader_version: 'qa',
            });
            await trainingStore.appendAttempt('concept-training', 'n1', {
              id: 'attempt-2',
              kind: 'cold',
              at: '2026-05-16T10:00:00.000Z',
              user_text: 'second learner answer',
              classification: 'strong',
              gaps: [],
              grader_version: 'qa',
            });
            await rejects(() => trainingStore.setStudyRevealed('concept-training-2', 'n1', '2026-05-15T10:05:00.000Z'), /attempt-required/, 'training study requires attempt');
            await rejects(() => trainingStore.setStudyRevealed('concept-training', 'n1', ''), /study-at-required/, 'training study requires time');
            await trainingStore.setStudyRevealed('concept-training', 'n1', '2026-05-15T10:05:00.000Z');
            await rejects(() => trainingStore.appendRepair('concept-training-2', 'n1', {
              id: 'repair-before-study',
              at: '2026-05-15T10:10:00.000Z',
              text: 'repair',
            }), /study-required/, 'training repair requires study');
            await rejects(() => trainingStore.appendRepair('concept-training', 'n1', {
              at: '2026-05-15T10:10:00.000Z',
              text: 'repair',
            }), /repair-id-required/, 'training rejects missing repair id');
            await rejects(() => trainingStore.appendRepair('concept-training', 'n1', {
              id: 'repair-missing-at',
              text: 'repair',
            }), /repair-at-required/, 'training rejects missing repair at');
            await rejects(() => trainingStore.appendRepair('concept-training', 'n1', {
              id: 'repair-empty',
              at: '2026-05-15T10:10:00.000Z',
              text: '  ',
            }), /repair-text-required/, 'training rejects empty repair');
            await trainingStore.appendRepair('concept-training', 'n1', {
              id: 'repair-1',
              at: '2026-05-15T10:10:00.000Z',
              text: 'repair text',
            });
            const storedTraining = await trainingStore.loadTraining('concept-training');
            assert(storedTraining.node_records.n1.attempts[0].kind === 'cold', 'training derives first attempt kind');
            assert(storedTraining.node_records.n1.attempts[1].kind === 'spaced', 'training derives spaced attempt kind');
            assert(storedTraining.node_records.n1.attempts[0].user_text === '  first learner answer  ', 'training preserves verbatim text');
            assert(storedTraining.node_records.n1.repairs[0].text === 'repair text', 'training appends repair');
            await trainingStore.saveTraining({
              concept_id: 'corrupt-node-record',
              node_records: { n1: { attempts: null, repairs: null } },
            });
            await trainingStore.appendAttempt('corrupt-node-record', 'n1', {
              id: 'attempt-corrupt-record',
              at: '2026-05-15T10:00:00.000Z',
              user_text: 'attempt after corrupt record',
              classification: 'thin',
              gaps: [],
              grader_version: 'qa',
            });
            const normalizedCorruptRecord = await trainingStore.loadTraining('corrupt-node-record');
            assert(Array.isArray(normalizedCorruptRecord.node_records.n1.attempts), 'training normalizes corrupt attempts array');
            assert(Array.isArray(normalizedCorruptRecord.node_records.n1.repairs), 'training normalizes corrupt repairs array');
            memoryStorage.setItem('socratink:training:v1:malformed-shape', JSON.stringify({ node_records: null }));
            assert((await trainingStore.loadTraining('malformed-shape')).node_records, 'training load normalizes node records');
            memoryStorage.setItem('socratink:training:v1:null-shape', 'null');
            assert(await trainingStore.loadTraining('null-shape') === null, 'training ignores null record');
            memoryStorage.setItem('socratink:training:v1:null-node-records-on-mutate', JSON.stringify({
              concept_id: 'null-node-records-on-mutate',
              node_records: null,
            }));
            await trainingStore.appendAttempt('null-node-records-on-mutate', 'n1', {
              id: 'attempt-null-records',
              at: '2026-05-15T10:00:00.000Z',
              user_text: 'attempt after null node records',
              classification: 'thin',
              gaps: [],
              grader_version: 'qa',
            });
            assert((await trainingStore.loadTraining('null-node-records-on-mutate')).node_records.n1, 'training recreates null node records on mutate');
            const noStorageStore = trainingStoreModule.createTrainingStore({ storage: null });
            assert(await noStorageStore.loadTraining('missing') === null, 'training no storage load');
            await noStorageStore.saveTraining({ concept_id: 'missing' });
            assert(await noStorageStore.appendAttempt('missing', 'n1', {
              id: 'attempt-no-storage',
              at: '2026-05-15T10:00:00.000Z',
              user_text: 'attempt',
              classification: 'thin',
              gaps: [],
              grader_version: 'qa',
            }) === null, 'training no storage mutation');

            localStorage.setItem('learnops_concepts', '[]');
            localStorage.removeItem('learnops_active');
            window.App.persistCreatedConceptFromLaunchPad(
              {
                metadata: {},
                backbone: [{ id: 'lp-node', label: 'Launch-pad node' }],
                clusters: [],
              },
              { name: 'Launch Pad Provenance' },
              'rough learner threshold'
            );
            await new Promise((resolve) => setTimeout(resolve, 0));
            const savedLaunchPadConcept = JSON.parse(localStorage.getItem('learnops_concepts'))[0];
            const savedLaunchPadTraining = JSON.parse(localStorage.getItem(`socratink:training:v1:${savedLaunchPadConcept.id}`));
            assert(savedLaunchPadTraining.source_mode === 'source_less', 'launch pad writes source-less provenance');
            assert(savedLaunchPadTraining.grounding === 'learner_sketch', 'launch pad writes learner sketch grounding');
            assert(savedLaunchPadTraining.sketch.text === 'rough learner threshold', 'launch pad writes sketch text');

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
            sourceMount.querySelector('.overlay-extract').click();
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
            sourceMount.querySelector('.overlay-extract').click();
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

            const shell = await import('/js/app-shell-ui.js');
            const shellDrawer = document.createElement('aside');
            const shellToggle = document.createElement('button');
            const shellSounds = [];
            shell.openDrawer({ drawer: shellDrawer, drawerToggle: shellToggle, documentRef: document });
            assert(shellDrawer.dataset.open === 'true', 'shell open drawer');
            assert(document.body.dataset.drawerOpen === 'true', 'shell body drawer open');
            assert(shellToggle.getAttribute('aria-expanded') === 'true', 'shell toggle open');
            shell.closeDrawer({ drawer: shellDrawer, drawerToggle: shellToggle, documentRef: document });
            assert(shellDrawer.dataset.open === 'false', 'shell close drawer');
            assert(document.body.dataset.drawerOpen === 'false', 'shell body drawer closed');
            shell.toggleDrawer({
              drawer: shellDrawer,
              drawerToggle: shellToggle,
              documentRef: document,
              audio: { playDrawerToggle() { shellSounds.push('tap'); } },
            });
            same(shellSounds, ['tap'], 'shell drawer sound');
            assert(shellDrawer.dataset.open === 'true', 'shell toggle opens');
            const shellHost = document.getElementById('sidebar-settings-host') || document.createElement('div');
            if (!shellHost.parentNode) {
              shellHost.id = 'sidebar-settings-host';
              document.body.append(shellHost);
            }
            shellHost.innerHTML = '<div class="settings-panel"></div>';
            const shellSettingsButton = document.getElementById('nav-settings') || document.createElement('button');
            if (!shellSettingsButton.parentNode) {
              shellSettingsButton.id = 'nav-settings';
              document.body.append(shellSettingsButton);
            }
            shellSettingsButton.dataset.engaged = 'true';
            shell.clearSettingsPanel({ documentRef: document });
            assert(shellHost.innerHTML === '', 'shell settings cleared');
            assert(!shellSettingsButton.dataset.engaged, 'shell settings engagement cleared');
            const shellItemHtml = shell.conceptListItemHtml({ id: 'c-shell', name: '<Unsafe>', state: 'growing' });
            assert(shellItemHtml.includes('&lt;Unsafe&gt;'), 'shell concept html escapes');
            assert(shellItemHtml.includes('data-concept-id="c-shell"'), 'shell concept id data attr');
            assert(shellItemHtml.includes('App.deleteConcept(this.dataset.conceptId,this)'), 'shell delete bridge');
            const shellConceptList = document.createElement('div');
            const shellOpened = [];
            shell.renderConceptList({
              concepts: [
                { id: 'c1', name: 'First', state: 'growing', graphData: true },
                { id: 'c2', name: 'Second', state: 'hibernating' },
              ],
              activeId: 'c2',
              conceptListEl: shellConceptList,
              documentRef: document,
              onOpenConcept(concept) { shellOpened.push(concept.id); },
            });
            assert(shellConceptList.children.length === 2, 'shell concept list count');
            assert(shellConceptList.children[1].classList.contains('active'), 'shell active concept');
            shellConceptList.children[0].dispatchEvent(new MouseEvent('click', { bubbles: true }));
            same(shellOpened, ['c1'], 'shell concept click');
            shellConceptList.querySelector('.concept-delete').dispatchEvent(new MouseEvent('click', { bubbles: true }));
            same(shellOpened, ['c1'], 'shell delete click ignored');

            // Coverage for app.js wrapper line changed in this branch.
            try { window.App.toggleDrawer(); } catch (e) { throw new Error('toggleDrawer error: ' + e); }
            const previousActiveConcept = localStorage.getItem('learnops_active');
            try {
              localStorage.removeItem('learnops_active');
              window.App.extract();
            } catch (e) {
              throw new Error('extract without active concept error: ' + e.message + ' \\n' + e.stack);
            } finally {
              if (previousActiveConcept === null) localStorage.removeItem('learnops_active');
              else localStorage.setItem('learnops_active', previousActiveConcept);
            }

            const conceptPage = await import('/js/concept-page-view.js');
            const trainingDerive = await import('/js/training-derive.js');
            const attempt = (id, at, classification) => ({
              id,
              kind: id === 'a1' ? 'cold' : 'spaced',
              at,
              user_text: `${classification} explanation`,
              classification,
              gaps: classification === 'strong' ? [] : [{ description: 'missing link' }],
              grader_version: 'qa',
            });
            same(trainingDerive.deriveNodeTraining(null).next_action, 'cold_attempt', 'training derive cold action');
            same(
              trainingDerive.deriveNodeTraining({
                attempts: [attempt('a1', '2026-05-15T10:00:00.000Z', 'partial')],
                study_revealed_at: '2026-05-15T10:01:00.000Z',
              }).next_action,
              'repair',
              'partial after study needs repair',
            );
            same(
              trainingDerive.deriveNodeTraining({
                attempts: [attempt('a1', '2026-05-15T10:00:00.000Z', 'thin')],
                study_revealed_at: '2026-05-15T10:01:00.000Z',
                repairs: [{ id: 'r1', at: '2026-05-15T10:02:00.000Z', text: 'repair' }],
              }).next_action,
              'spaced_attempt',
              'needs-repair node can move to spaced attempt after repair',
            );
            const reviewState = trainingDerive.deriveNodeTraining({
              attempts: [attempt('a1', '2026-05-15T10:00:00.000Z', 'strong')],
              study_revealed_at: '2026-05-15T10:01:00.000Z',
            }, { now: '2026-05-15T11:00:00.000Z' });
            same(reviewState.next_action, 'review', 'strong attempt before spacing reviews');
            assert(reviewState.solidify_unlocks_at === '2026-05-16T04:00:00.000Z', 'solidify unlock time derived');
            same(
              trainingDerive.deriveNodeTraining({
                attempts: [attempt('a1', 'bad-time', 'strong')],
                study_revealed_at: '2026-05-15T10:01:00.000Z',
              }, { now: 'bad-now' }).next_action,
              'review',
              'invalid spacing timestamps remain review',
            );
            same(
              trainingDerive.deriveNodeTraining({
                attempts: [attempt('a1', '2026-05-15T10:00:00.000Z', 'strong')],
                study_revealed_at: '2026-05-15T10:01:00.000Z',
              }, { now: '2026-05-16T05:00:00.000Z' }).next_action,
              'spaced_attempt',
              'spacing interval unlocks spaced attempt',
            );
            same(
              trainingDerive.deriveNodeTraining({
                attempts: [
                  attempt('a1', '2026-05-15T10:00:00.000Z', 'strong'),
                  attempt('a2', '2026-05-16T05:00:00.000Z', 'strong'),
                ],
                study_revealed_at: '2026-05-15T10:01:00.000Z',
              }).state,
              'solidified',
              'two spaced strong attempts solidify',
            );
            same(
              trainingDerive.deriveConceptStatus({
                node_records: {
                  p: { attempts: [attempt('p1', '2026-05-15T10:00:00.000Z', 'partial')] },
                  n: { attempts: [attempt('n1', '2026-05-15T10:00:00.000Z', 'wrong_direction')] },
                  s: {
                    attempts: [
                      attempt('s1', '2026-05-15T10:00:00.000Z', 'strong'),
                      attempt('s2', '2026-05-16T05:00:00.000Z', 'strong'),
                    ],
                  },
                },
              }, ['u', 'p', 'n', 's']).badge,
              'needs repair',
              'concept status prioritizes repair',
            );
            same(
              trainingDerive.deriveConceptStatus({
                node_records: {
                  p: { attempts: [attempt('p1', '2026-05-15T10:00:00.000Z', 'partial')] },
                },
              }, ['p']).badge,
              'primed',
              'concept status reports primed when no repair remains',
            );
            same(
              trainingDerive.deriveConceptStatus({
                node_records: {
                  s: {
                    attempts: [
                      attempt('s1', '2026-05-15T10:00:00.000Z', 'strong'),
                      attempt('s2', '2026-05-16T05:00:00.000Z', 'strong'),
                    ],
                  },
                },
              }, ['s']).badge,
              'solidified',
              'concept status reports solidified when all tested nodes solidify',
            );
            same(
              trainingDerive.deriveConceptStatus(null, 'not-array').composition.total,
              0,
              'concept status tolerates non-array node ids',
            );
            const conceptBackbone = [
              { id: 'core', label: '<Core>', drill_status: 'drilled', purpose: 'First purpose' },
              { id: 'entry-2', label: 'Second & unsafe', drill_status: 'locked' },
              { id: 'entry-3', label: 'Third', drill_status: 'locked' },
            ];
            const conceptTraining = {
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
            assert(conceptPage.getConceptEntryId(conceptBackbone[0], 0) === 'core', 'concept entry id uses explicit id');
            assert(conceptPage.getConceptEntryId({ label: 'No id' }, 2) === 'entry-2', 'concept entry id falls back to index');
            const legacyStatusCompatEntry = conceptPage.selectInitialConceptEntry([
              { id: 'legacy-primed', label: 'Legacy primed', drill_status: 'solidified' },
              { id: 'next', label: 'Next', drill_status: 'locked' },
            ]);
            assert(legacyStatusCompatEntry.id === 'next', 'concept page honors legacy solidified status when no training record exists');
            const legacyDrilledHtml = conceptPage.renderActiveEntryHtml(
              { id: 'legacy-drilled', label: 'Legacy drilled', drill_status: 'drilled' },
              0,
              [{ id: 'legacy-drilled', label: 'Legacy drilled', drill_status: 'drilled' }],
              {},
              { metadata: {} },
            );
            assert(legacyDrilledHtml.includes('ready to reconstruct again entry 1 of 1'), 'concept page honors legacy drilled status when no training record exists');
            const legacyStudyHtml = conceptPage.renderActiveEntryHtml(
              { id: 'legacy-study', label: 'Legacy study', drill_status: 'primed', drill_phase: 'study', study_note: 'Legacy study note.' },
              0,
              [{ id: 'legacy-study', label: 'Legacy study', drill_status: 'primed', drill_phase: 'study', study_note: 'Legacy study note.' }],
              {},
              { metadata: {} },
            );
            assert(legacyStudyHtml.includes('study required entry 1 of 1'), 'legacy primed study stays in study phase');
            assert(legacyStudyHtml.includes('data-active-entry-action="study"'), 'legacy primed study reveals study before redrill');
            const legacyStudyRevealedHtml = conceptPage.renderActiveEntryHtml(
              { id: 'legacy-study', label: 'Legacy study', drill_status: 'primed', drill_phase: 'study', study_note: 'Legacy study note.' },
              0,
              [{ id: 'legacy-study', label: 'Legacy study', drill_status: 'primed', drill_phase: 'study', study_note: 'Legacy study note.' }],
              {},
              { metadata: {} },
              { node_records: { 'legacy-study': { attempts: [], repairs: [], study_revealed_at: '2026-05-15T10:05:00.000Z' } } },
            );
            assert(legacyStudyRevealedHtml.includes('Legacy study note.'), 'legacy study reveal shows note without fabricating an attempt');
            assert(!legacyStudyRevealedHtml.includes('concept-page-b2__evidence'), 'legacy study reveal does not invent learner evidence');
            const initialEntry = conceptPage.selectInitialConceptEntry([
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
            assert(initialEntry.entry.label === 'Next cold entry', 'initial entry selects first non-solidified node');
            assert(initialEntry.index === 1, 'initial entry reports selected index');
            assert(initialEntry.id === 'entry-1', 'initial entry reports fallback id');
            const allSolidifiedEntry = conceptPage.selectInitialConceptEntry([
              { id: 'solid', label: 'Solid', drill_status: 'solidified' },
            ]);
            assert(allSolidifiedEntry.entry.label === 'Solid', 'initial entry falls back to first node');
            assert(allSolidifiedEntry.index === 0, 'initial fallback reports first index');
            assert(allSolidifiedEntry.id === 'solid', 'initial fallback reports first id');
            const emptyInitialEntry = conceptPage.selectInitialConceptEntry([]);
            assert(emptyInitialEntry.entry.id === 'core-thesis', 'initial entry falls back to synthetic core thesis');
            assert(emptyInitialEntry.index === 0, 'synthetic initial entry reports zero index');
            assert(emptyInitialEntry.id === 'core-thesis', 'synthetic initial entry reports core thesis id');
            const fallbackEntryMatch = conceptPage.findConceptEntryById([{ label: 'No id' }], 'entry-0');
            assert(fallbackEntryMatch.entry.label === 'No id', 'find entry supports fallback id');
            assert(fallbackEntryMatch.index === 0, 'find entry reports fallback index');
            assert(fallbackEntryMatch.id === 'entry-0', 'find entry reports fallback id');
            assert(conceptPage.findConceptEntryById(conceptBackbone, 'missing') === null, 'find entry returns null for missing id');
            const conceptPageHtml = conceptPage.renderActiveEntryHtml(
              conceptBackbone[2],
              2,
              conceptBackbone,
              { startingMapContext: '<threshold & sketch>' },
              { metadata: { core_thesis: 'fallback thesis' } },
              conceptTraining
            );
            assert(conceptPageHtml.includes('&lt;threshold &amp; sketch&gt;'), 'concept page threshold escapes');
            assert(conceptPageHtml.includes('locked entry 3 of 3'), 'concept page blocked eyebrow');
            assert(conceptPageHtml.includes('aria-disabled="true"'), 'concept page blocked cta');
            assert(conceptPageHtml.includes('Second &amp; unsafe'), 'concept page nearby escapes');
            assert(conceptPageHtml.includes('READY TO RECONSTRUCT'), 'concept page derives nearby readiness from training');
            const conceptPageAttemptHtml = conceptPage.renderActiveEntryHtml(
              conceptBackbone[1],
              1,
              conceptBackbone,
              {},
              { metadata: { starting_map_context: 'metadata sketch' } },
              conceptTraining,
              { attemptEntryId: 'entry-2' },
            );
            assert(conceptPageAttemptHtml.includes('concept-page-b2__attempt'), 'concept page inline attempt form');
            assert(conceptPageAttemptHtml.includes('data-attempt-entry-id="entry-2"'), 'concept page inline attempt target');
            assert(conceptPageAttemptHtml.includes('Save what I wrote'), 'concept page inline attempt save');
            const conceptPagePrimedHtml = conceptPage.renderActiveEntryHtml(
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
            assert(conceptPagePrimedHtml.includes('concept-page-b2__threshold--empty'), 'concept page empty threshold');
            assert(conceptPagePrimedHtml.includes('study required entry 1 of 1'), 'concept page primed study-required eyebrow');
            assert(conceptPagePrimedHtml.includes('data-active-entry-action="study"'), 'concept page primed study action');
            assert(conceptPagePrimedHtml.includes('Reveal study note'), 'concept page primed study cta');
            const conceptPageStudiedHtml = conceptPage.renderActiveEntryHtml(
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
              { now: '2026-05-15T11:00:00.000Z' },
            );
            assert(conceptPageStudiedHtml.includes('review pending entry 1 of 1'), 'concept page studied review eyebrow');
            assert(conceptPageStudiedHtml.includes('concept-page-b2__evidence'), 'concept page studied evidence artifact renders');
            assert(conceptPageStudiedHtml.includes('learner reconstruction'), 'concept page studied evidence label');
            assert(conceptPageStudiedHtml.includes('A strong first attempt.'), 'concept page studied preserves learner words');
            assert(conceptPageStudiedHtml.includes('concept-page-b2__study-note'), 'concept page studied note renders');
            assert(conceptPageStudiedHtml.includes('Study note for this entry.'), 'concept page studied note uses entry purpose');
            assert(conceptPageStudiedHtml.includes('Reconstruct from memory'), 'concept page studied re-drill cta');
            const conceptPagePrincipleHtml = conceptPage.renderActiveEntryHtml(
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
              { now: '2026-05-15T11:00:00.000Z' },
            );
            assert(conceptPagePrincipleHtml.includes('Entry-specific generated principle.'), 'concept page study note uses entry principle before global fallback');
            assert(!conceptPagePrincipleHtml.includes('Global core thesis should not appear.'), 'concept page principle avoids global core thesis fallback');
            assert(!conceptPagePrincipleHtml.includes('Global source preview should not appear.'), 'concept page principle avoids source preview fallback');
            const conceptPageRepairHtml = conceptPage.renderActiveEntryHtml(
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
              },
            );
            assert(conceptPageRepairHtml.includes('repair the gap entry 1 of 1'), 'concept page repair eyebrow');
            assert(conceptPageRepairHtml.includes('concept-page-b2__evidence'), 'concept page repair evidence artifact renders');
            assert(conceptPageRepairHtml.includes('Sodium just rushes in.'), 'concept page repair preserves learner words');
            assert(conceptPageRepairHtml.includes('Name that voltage-gated sodium channels open at threshold.'), 'concept page repair surfaces hinge');
            assert(conceptPageRepairHtml.includes('concept-page-b2__repair'), 'concept page repair panel');
            assert(conceptPageRepairHtml.includes('data-repair-entry-id="repair"'), 'concept page repair save target');
            assert(conceptPageRepairHtml.includes('Save repair'), 'concept page repair save');
            const conceptPageReviewHtml = conceptPage.renderActiveEntryHtml(
              { id: 'review', label: 'Review' },
              0,
              [{ id: 'review', label: 'Review' }],
              {},
              { metadata: {} },
              {
                node_records: {
                  review: {
                    attempts: [attempt('rv1', '2026-05-15T10:00:00.000Z', 'strong')],
                    study_revealed_at: '2026-05-15T10:01:00.000Z',
                  },
                },
              },
              { now: '2026-05-15T11:00:00.000Z' },
            );
            assert(conceptPageReviewHtml.includes('review pending entry 1 of 1'), 'concept page review pending eyebrow');
            assert(conceptPageReviewHtml.includes('Reconstruct from memory'), 'concept page review cta');
            const conceptPageSpacedHtml = conceptPage.renderActiveEntryHtml(
              { id: 'spaced', label: 'Spaced' },
              0,
              [{ id: 'spaced', label: 'Spaced' }],
              {},
              { metadata: {} },
              {
                node_records: {
                  spaced: {
                    attempts: [attempt('sp1', '2026-05-15T10:00:00.000Z', 'strong')],
                    study_revealed_at: '2026-05-15T10:01:00.000Z',
                  },
                },
              },
              { now: '2026-05-16T05:00:00.000Z' },
            );
            assert(conceptPageSpacedHtml.includes('spaced reconstruction ready entry 1 of 1'), 'concept page spaced eyebrow');
            const conceptPageDefensiveHtml = conceptPage.renderActiveEntryHtml(
              { id: 'defensive', label: 'Defensive' },
              0,
              [{ id: 'defensive', label: 'Defensive' }],
              {},
              { metadata: {} },
              {
                node_records: {
                  defensive: {
                    attempts: [attempt('df1', '2026-05-15T10:00:00.000Z', 'unknown')],
                    study_revealed_at: '2026-05-15T10:01:00.000Z',
                  },
                },
              },
            );
            assert(conceptPageDefensiveHtml.includes('re-drill ready entry 1 of 1'), 'concept page has defensive attempted fallback');
            const conceptStripHtml = conceptPage.renderConceptStripHtml(conceptBackbone, conceptBackbone[1], 1, conceptTraining);
            assert(conceptStripHtml.includes('class="concept-strip"'), 'concept strip wrapper');
            assert(conceptStripHtml.includes('concept-strip__edge is-active'), 'concept strip active edge');
            assert(conceptStripHtml.includes('concept-strip__node--primed'), 'concept strip primed node');
            assert(conceptStripHtml.includes('concept-strip__node--ready is-active'), 'concept strip ready active node');
            assert(conceptStripHtml.includes('concept-strip__node--locked'), 'concept strip locked node');
            assert(conceptStripHtml.includes('Second &amp; unsafe · 2 of 3'), 'concept strip active label escapes');
            assert(conceptStripHtml.includes('aria-label="Second &amp; unsafe, ready to reconstruct, current"'), 'concept strip aria escapes');
            const emptyConceptStripHtml = conceptPage.renderConceptStripHtml([], { id: 'core-thesis', label: 'Core thesis' }, 0);
            assert(emptyConceptStripHtml.includes('data-entry-id="core-thesis"'), 'concept strip empty synthetic node');
            assert(emptyConceptStripHtml.includes('<text x="60" y="80">core thesis</text>'), 'concept strip empty label');

            const launchPadEvents = [];
            sessionStorage.removeItem('socratink:pendingShell');
            const launchPadResult = await window.App.runLaunchPadAction({
              preventDefault() { launchPadEvents.push('prevented'); },
            });
            assert(launchPadResult === false, 'launch pad wrapper returns false without shell');
            same(launchPadEvents, ['prevented'], 'launch pad wrapper prevents submit default');

            return true;
        }"""
    )
    assert result is True
