"""Characterization tests for small app.js helper modules."""

from __future__ import annotations

import shutil
from html.parser import HTMLParser
from pathlib import Path

import pytest

from tests._helpers.node_runner import run_node_module

REPO_ROOT = Path(__file__).resolve().parent.parent


class ButtonTypeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.missing_type: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "button":
            return
        attr_names = {name.lower() for name, _value in attrs}
        if "type" not in attr_names:
            self.missing_type.append(self.get_starttag_text() or "<button>")

@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_drill_chamber_noops_when_required_nodes_are_missing() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';

        const nodes = new Map();

        function makeNode(id) {
          return {
            id,
            hidden: true,
            disabled: false,
            value: '',
            textContent: '',
            innerHTML: '',
            placeholder: '',
            listeners: {},
            classList: {
              add() {},
              remove() {},
            },
            appendChild(child) {
              this.appended = this.appended || [];
              this.appended.push(child);
              this.lastChild = child;
            },
            addEventListener(type, handler) {
              this.listeners[type] = handler;
            },
            click() {
              this.listeners.click?.({});
            },
            focus() {
              this.focused = true;
            },
            insertAdjacentHTML(_position, html) {
              this.insertedHtml = html;
            },
            querySelectorAll() {
              return [];
            },
            removeAttribute(name) {
              delete this[name];
            },
            scrollIntoView() {
              this.scrolled = true;
            },
            setAttribute(name, value) {
              this[name] = value;
            },
          };
        }

        globalThis.window = {};
        globalThis.document = {
          body: {
            classList: {
              add() {},
              remove() {},
            },
          },
          createElement(tagName) {
            return makeNode(tagName);
          },
          getElementById(id) {
            return nodes.get(id) || null;
          },
        };
        globalThis.requestAnimationFrame = (callback) => callback();
        const scheduledTimers = [];
        globalThis.setTimeout = (callback, delay = 0) => {
          if (delay === 1200) {
            const timer = { callback, delay, cleared: false };
            scheduledTimers.push(timer);
            return timer;
          }
          callback();
          return 0;
        };
        globalThis.clearTimeout = (timer) => { if (timer) timer.cleared = true; };

        await import('./public/js/drill-chamber.js');

        for (const id of [
          'drill-chamber-view',
          'chamber-concept-name',
          'chamber-entry-name',
          'chamber-question',
          'chamber-composer',
          'chamber-send',
          'chamber-exit',
          'chamber-chat-log',
        ]) {
          nodes.set(id, makeNode(id));
        }

        assert.doesNotThrow(() => window.DrillChamber.show({
          conceptName: 'Concept',
          entryName: 'Entry',
          question: 'Question?',
        }));
        assert.doesNotThrow(() => window.DrillChamber.setComposerEnabled(true));
        assert.doesNotThrow(() => window.DrillChamber.clearComposer());
        assert.doesNotThrow(() => window.DrillChamber.swapQuestion('Next?'));
        assert.doesNotThrow(() => window.DrillChamber.appendHistoryTurn('ai', 'Hello'));
        assert.doesNotThrow(() => window.DrillChamber.appendCreed());
        assert.equal(window.DrillChamber.getComposerValue(), '');

        nodes.set('chamber-active', makeNode('chamber-active'));
        window.DrillChamber.show({
          conceptName: 'Concept',
          entryName: 'Entry',
          question: 'Question?',
        });
        assert.equal(nodes.get('drill-chamber-view').hidden, false);
        assert.equal(nodes.get('chamber-question').textContent, 'Question?');

        const sent = [];
        window.DrillChamber.onSend((text) => sent.push(text));
        nodes.get('chamber-composer').value = '  learner answer  ';
        nodes.get('chamber-send').click();
        assert.deepEqual(sent, ['learner answer']);
        assert.equal(nodes.get('chamber-composer').disabled, true);
        assert.equal(nodes.get('chamber-send').disabled, true);

        nodes.set('chamber-hint', makeNode('chamber-hint'));
        nodes.set('chamber-verdict', makeNode('chamber-verdict'));
        window.DrillChamber.show({
          conceptName: 'Concept',
          entryName: 'Entry',
          question: 'Question?',
        });
        window.DrillChamber.setLoading(true);
        assert.equal(nodes.get('chamber-hint').textContent, 'A sentence is enough.');
        window.DrillChamber.setLoading(true, { checkingAnswer: true });
        assert.equal(nodes.get('chamber-hint').textContent, 'Checking your answer…');
        const pendingTimer = scheduledTimers.at(-1);
        assert.equal(pendingTimer.delay <= 1500, true);
        pendingTimer.callback();
        assert.equal(nodes.get('chamber-verdict').hidden, false);
        assert.deepEqual(
          nodes.get('chamber-verdict').appended.slice(-3).map((node) => node.textContent),
          ['Answer received', '•', 'Checking the link you wrote.']
        );
        assert.equal(
          nodes.get('chamber-verdict').lastChild.textContent,
          'Checking the link you wrote.'
        );
        window.DrillChamber.setLoading(false);
        assert.equal(nodes.get('chamber-hint').textContent, 'A sentence is enough.');
        assert.equal(nodes.get('chamber-verdict').hidden, true);
        window.DrillChamber.setLoading(true, { checkingAnswer: true });
        scheduledTimers.at(-1).callback();
        window.DrillChamber.appendVerdict('Checked • Partly there');
        assert.equal(nodes.get('chamber-verdict').lastChild.textContent, 'Partly there');
        assert.equal(nodes.get('chamber-verdict').hidden, false);
        window.DrillChamber.setLoading(true, { checkingAnswer: true });
        const exitTimer = scheduledTimers.at(-1);
        assert.equal(nodes.get('chamber-active')['data-loading'], 'true');
        window.DrillChamber.hide();
        assert.equal(exitTimer.cleared, true);
        assert.equal(nodes.get('chamber-active')['data-loading'], undefined);
        nodes.get('chamber-composer').value = '   ';
        nodes.get('chamber-send').click();
        assert.deepEqual(sent, ['learner answer']);
        assert.equal(nodes.get('chamber-hint').textContent, 'Write a sentence before checking.');
        assert.equal(nodes.get('chamber-composer').focused, true);
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_drill_verdict_helpers_keep_seda_transitions_specific() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          nextSedaPromptAfterVerdict,
          verdictCopy,
        } from './public/js/drill-verdict.js';

        const duplicateFallback = nextSedaPromptAfterVerdict(
          'Same question?',
          'Same question?',
          'I guessed with my own words.'
        );
        assert.equal(
          duplicateFallback,
          'You wrote: «I guessed with my own words.». Now: name the missing link in one sentence.'
        );
        assert.notEqual(duplicateFallback, 'Same question?');
        assert.equal(
          nextSedaPromptAfterVerdict('Explain the mechanism.', 'Same question?', 'My rough answer.'),
          'You wrote: «My rough answer.». Now: Explain the mechanism.'
        );
        const partialVerdict = verdictCopy({
          classification: 'partial',
          userText: 'The query compares with keys.',
        });
        assert.match(partialVerdict, /Checked • Partly there •/);
        assert.match(partialVerdict, /The query compares with keys\\./);
        assert.doesNotMatch(partialVerdict, /partial/i);
        assert.match(partialVerdict, /Your line: “The query compares with keys\\.”/);
        assert.match(partialVerdict, /Study will target the missing link\\./);
        const unsafeFeedback = verdictCopy({
          classification: 'partial',
          userText: 'A rough answer.',
          specificFeedback: 'Classification: shallow. Score 2.',
        });
        assert.doesNotMatch(unsafeFeedback, /Classification|shallow|Score 2/i);
        assert.match(unsafeFeedback, /Study will target the missing link\\./);
        for (const classification of ['deep', 'thin', 'shallow']) {
          const copy = verdictCopy({ classification, userText: 'A rough causal link.' });
          assert.match(copy, /Checked • Partly there •/);
          assert.doesNotMatch(copy, new RegExp(classification, 'i'));
        }
        const wrongDirection = verdictCopy({
          classification: 'wrong_direction',
          userText: 'I started from the output.',
        });
        assert.match(wrongDirection, /Study will show a different starting point\\./);
        assert.doesNotMatch(wrongDirection, /wrong_direction/i);
        assert.equal(
          verdictCopy({ userText: 'The query compares with keys.', sedaComplete: true }),
          'Checked • Recorded • Your attempt is on record. • Study is ready.'
        );
        const supportTurn = verdictCopy({
          userText: 'I need one more cue.',
          recordable: false,
        });
        assert.equal(
          supportTurn,
          'Response received • Keep going • Your line: “I need one more cue.” • Use the next question to add one cause-and-effect link.'
        );
        assert.doesNotMatch(supportTurn, /Checked|Gap found|Study|Partly there|Wrong angle/);
        """
    )
    assert result.returncode == 0, result.stderr


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
        assert.equal(getHeroStateLabel('missing'), 'no sessions yet');

        assert.deepEqual(
          getHeroActionConfig(null),
          { label: 'Begin', action: 'add', disabled: false }
        );
        assert.deepEqual(
          getHeroActionConfig({ state: 'growing', graphData: { nodes: [] } }),
          { label: 'Resume session', action: 'open-map', disabled: false }
        );
        assert.deepEqual(
          getHeroActionConfig({ state: 'hibernating', graphData: null }),
          { label: 'Return Later', action: 'wait', disabled: true }
        );

        assert.equal(
          getHeroGuidance({ state: 'instantiated', graphData: null }),
          'Turn the material into a learning session. The map is not learner evidence.'
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
def test_launch_pad_normalizes_goal_shaped_door_input() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { buildPendingShellFromDoorInput } from './public/js/launch-pad.js';

        const goalShell = buildPendingShellFromDoorInput(
          ' I want to understand why sodium rushing into a neuron starts an electrical signal. '
        );
        assert.equal(
          goalShell.name,
          'sodium rushing into a neuron starts an electrical signal'
        );
        assert.equal(
          goalShell.goal,
          'I want to understand why sodium rushing into a neuron starts an electrical signal.'
        );

        const topicShell = buildPendingShellFromDoorInput(
          'How sodium channels create an action potential'
        );
        assert.equal(topicShell.name, 'How sodium channels create an action potential');
        assert.equal(topicShell.goal, '');
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_submit_concept_create_sends_learner_goal() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { submitConceptCreate } from './public/js/ai_service.js';

        let capturedBody = null;
        globalThis.fetch = async (_url, options) => {
          capturedBody = JSON.parse(options.body);
          return new Response(JSON.stringify({ provisional_map: {} }), {
            status: 200,
            headers: { 'content-type': 'application/json' },
          });
        };

        await submitConceptCreate({
          name: 'Sodium channels',
          learnerGoal: 'I want to explain why sodium starts the signal.',
          startingSketch: 'sodium moves into the neuron and starts a signal somehow',
          source: null,
        });

        assert.equal(capturedBody.name, 'Sodium channels');
        assert.equal(capturedBody.learner_goal, 'I want to explain why sodium starts the signal.');
        assert.equal(capturedBody.starting_sketch, 'sodium moves into the neuron and starts a signal somehow');
        assert.equal(capturedBody.source, null);
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_launch_pad_action_sends_shell_goal_to_extract() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { runLaunchPadAction } from './public/js/launch-pad.js';

        const storage = new Map();
        globalThis.sessionStorage = {
          getItem(key) { return storage.has(key) ? storage.get(key) : null; },
          setItem(key, value) { storage.set(key, String(value)); },
          removeItem(key) { storage.delete(key); },
        };
        globalThis.localStorage = {
          getItem(key) {
            return key === 'gemini_key' ? 'stale-browser-key' : null;
          },
        };

        const elements = {
          'launch-pad-input': {
            value: 'Sodium moves into the neuron through channels and that movement starts an electrical signal somehow.',
          },
          'launch-pad-submit': {
            disabled: false,
            textContent: 'Save first model',
          },
          'launch-pad-validation': {
            textContent: '',
          },
          'launch-pad-form': {
            dataset: {},
            setAttribute(name, value) { this[name] = value; },
            removeAttribute(name) { delete this[name]; },
          },
        };
        globalThis.document = {
          getElementById(id) { return elements[id] || null; },
        };

        let capturedBody = null;
        globalThis.fetch = async (_url, options) => {
          capturedBody = JSON.parse(options.body);
          return new Response(JSON.stringify({
            provisional_map: {
              metadata: {},
              backbone: [{ id: 'b1', principle: 'Signal start', dependent_clusters: ['c1'] }],
              clusters: [{
                id: 'c1',
                label: 'Signal start',
                description: 'Explain the initial movement.',
                subnodes: [{ id: 'c1_s1', label: 'Signal start', mechanism: 'Sodium influx depolarizes the neuron.' }],
              }],
              relationships: { domain_mechanics: [], learning_prerequisites: [] },
              frameworks: [],
            },
          }), {
            status: 200,
            headers: { 'content-type': 'application/json' },
          });
        };

        storage.set('socratink:pendingShell', JSON.stringify({
          name: 'Sodium channels',
          goal: 'I want to explain why sodium starts the signal.',
          ts: Date.now(),
        }));

        const calls = [];
        const App = {
          persistCreatedConceptFromLaunchPad(map, shell, threshold) {
            calls.push({ map, shell, threshold });
          },
          navigateToGraphViewFromLaunchPad(options) {
            calls.push({ options });
          },
        };

        const resultValue = await runLaunchPadAction({ preventDefault() {} }, App);

        assert.equal(resultValue, false);
        assert.equal(capturedBody.name, 'Sodium channels');
        assert.equal(capturedBody.learner_goal, 'I want to explain why sodium starts the signal.');
        assert.equal(capturedBody.starting_sketch, elements['launch-pad-input'].value);
        assert.equal(capturedBody.route_owner, 'seda');
        assert.equal(Object.hasOwn(capturedBody, 'api_key'), false);
        assert.equal(calls.length, 2);
        assert.equal(storage.has('socratink:pendingShell'), false);
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_launch_pad_persistence_failure_emits_retry_telemetry() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { Bus } from './public/js/bus.js';
        import { runLaunchPadAction } from './public/js/launch-pad.js';

        const storage = new Map();
        globalThis.sessionStorage = {
          getItem(key) { return storage.has(key) ? storage.get(key) : null; },
          setItem(key, value) { storage.set(key, String(value)); },
          removeItem(key) { storage.delete(key); },
        };
        globalThis.localStorage = {
          getItem() { return null; },
        };

        const elements = {
          'launch-pad-input': { value: 'My rough first model.' },
          'launch-pad-submit': {
            disabled: false,
            textContent: 'Save first model',
          },
          'launch-pad-validation': { textContent: '' },
          'launch-pad-form': {
            dataset: {},
            setAttribute(name, value) { this[name] = value; },
            removeAttribute(name) { delete this[name]; },
          },
        };
        globalThis.document = {
          getElementById(id) { return elements[id] || null; },
        };
        globalThis.fetch = async () => new Response(JSON.stringify({
          provisional_map: {
            metadata: {},
            backbone: [{ id: 'b1', principle: 'First model', dependent_clusters: [] }],
            clusters: [],
            relationships: { domain_mechanics: [], learning_prerequisites: [] },
            frameworks: [],
          },
        }), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        });

        storage.set('socratink:pendingShell', JSON.stringify({
          name: 'Persistence failure',
          goal: '',
          ts: Date.now(),
        }));

        const telemetry = [];
        Bus.on('telemetry', (payload) => telemetry.push(payload));

        const err = new Error('board full');
        err.code = 'board_at_capacity';
        const resultValue = await runLaunchPadAction({ preventDefault() {} }, {
          persistCreatedConceptFromLaunchPad() { throw err; },
          navigateToGraphViewFromLaunchPad() {
            throw new Error('should not navigate after persistence failure');
          },
        });

        assert.equal(resultValue, false);
        assert.equal(storage.has('socratink:pendingShell'), true);
        assert.equal(elements['launch-pad-submit'].disabled, false);
        assert.equal(
          elements['launch-pad-validation'].textContent,
          'The board holds nine concepts. Retire one in your library to start another.'
        );
        assert.deepEqual(
          telemetry.find((payload) => payload.event === 'concept_create.launch_pad.persist_failed'),
          {
            event: 'concept_create.launch_pad.persist_failed',
            reason: 'board_at_capacity',
          }
        );
        """
    )
    assert result.returncode == 0, result.stderr


def test_frontend_ai_calls_do_not_forward_browser_gemini_key() -> None:
    for rel_path in [
        "public/js/ai_service.js",
        "public/js/app.js",
        "public/js/launch-pad.js",
    ]:
        text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert "gemini_key" not in text, rel_path


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
          'settings-mic-toggle',
          'settings-tutor-voice-toggle',
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
            thesis: 'Your first reconstruction will appear here.',
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
        assert.ok(getLibraryConceptMeta({ graphData: '{' }).thesis.includes('first reconstruction'));

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
        assert.ok(emptyHtml.includes('Start a learning session.'));
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
        assert.ok(cardHtml.includes('role="button"'));
        assert.ok(cardHtml.includes('tabindex="0"'));
        assert.ok(cardHtml.includes('aria-label="Open concept &lt;Unsafe&gt;"'));
        assert.ok(cardHtml.includes('onclick="App.openLibraryConcept(this.dataset.conceptId)"'));
        assert.ok(cardHtml.includes("event.key==='Enter'||event.key===' '"));
        assert.ok(cardHtml.includes('&lt;Unsafe&gt;'));
        assert.ok(cardHtml.includes('The learner reconstructed the causal mechanism.'));
        assert.ok(!cardHtml.includes('This is the central claim.'));
        assert.ok(cardHtml.includes('2 sections'));
        assert.ok(cardHtml.includes('3 entries'));

        const noEvidenceHtml = buildLibraryHtml([
          { id: 'legacy-solid', name: 'Legacy Solid', state: 'actualized', graphData: graph },
        ], {});
        assert.ok(noEvidenceHtml.includes('data-state=""'));
        assert.ok(!noEvidenceHtml.includes('actualized'));

        const legacyPrimedGraph = JSON.stringify({
          metadata: {},
          backbone: [{ id: 'legacy-primed', drill_status: 'primed' }],
          clusters: [],
        });
        const legacyPrimedHtml = buildLibraryHtml([
          { id: 'legacy-primed', name: 'Legacy Primed', state: 'growing', graphData: legacyPrimedGraph },
        ], {});
        assert.ok(legacyPrimedHtml.includes('data-state="primed"'));
        assert.ok(legacyPrimedHtml.includes('>draft saved<'));

        const legacyNeedsRepairGraph = JSON.stringify({
          metadata: {},
          backbone: [{ id: 'legacy-drilled', drill_status: 'drilled' }],
          clusters: [],
        });
        const legacyNeedsRepairHtml = buildLibraryHtml([
          { id: 'legacy-drilled', name: 'Legacy Drilled', state: 'growing', graphData: legacyNeedsRepairGraph },
        ], {});
        assert.ok(legacyNeedsRepairHtml.includes('data-state="needs repair"'));
        assert.ok(legacyNeedsRepairHtml.includes('>needs repair<'));

        const legacySolidGraph = JSON.stringify({
          metadata: { drill_status: 'solidified' },
          backbone: [{ id: 'legacy-solid-node', drill_status: 'solidified' }],
          clusters: [],
        });
        const legacySolidHtml = buildLibraryHtml([
          { id: 'legacy-solid-node', name: 'Legacy Solid Node', state: 'growing', graphData: legacySolidGraph },
        ], {});
        assert.ok(legacySolidHtml.includes('data-state="solidified"'));
        assert.ok(legacySolidHtml.includes('>solid spaced reconstruction<'));

        const needsRepairTraining = {
          node_records: {
            a: {
              attempts: [
                {
                  id: 'thin-1',
                  at: '2026-05-15T10:00:00.000Z',
                  user_text: 'Too vague.',
                  classification: 'thin',
                  gaps: ['causal trigger missing'],
                },
                {
                  id: 'thin-2',
                  at: '2026-05-15T11:00:00.000Z',
                  user_text: 'Still too vague.',
                  classification: 'thin',
                  gaps: ['causal trigger missing'],
                },
              ],
            },
          },
        };
        const derivedHtml = buildLibraryHtml([
          { id: 'c-derived', name: 'Derived', state: 'actualized', graphData: graph },
        ], { 'c-derived': needsRepairTraining });
        assert.ok(derivedHtml.includes('data-state="needs repair"'));
        assert.ok(derivedHtml.includes('>needs repair<'));
        assert.ok(!derivedHtml.includes('actualized'));
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_source_panel_preserves_blocking_and_tab_contracts() -> None:
    source_panel_js = (REPO_ROOT / "public" / "js" / "source-panel.js").read_text(encoding="utf-8")
    assert 'data-tab="paste"' in source_panel_js
    assert 'data-tab="url"' in source_panel_js
    assert 'data-tab="upload"' in source_panel_js
    assert "creation-source-panel-cancel" in source_panel_js
    assert "creation-source-panel-attach" in source_panel_js

    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { isBlockedVideoUrl } from './public/js/source-panel.js';

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
          removeAttribute(name) { delete this.attrs[name]; },
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
        assert.equal(tiles[0].attrs['aria-label'], 'Resume First');
        assert.ok(tiles[0].innerHTML.includes('concept-pin-0'));
        assert.equal(tiles[1].attrs.class, 'tile-group empty');
        assert.equal(tiles[1].attrs['aria-label'], 'Start learning');
        assert.ok(tiles[1].innerHTML.includes('tile-top-empty'));
        assert.deepEqual(events, ['grid:rendered']);

        renderGrid({
          concepts: [{ id: 'c1', name: 'First', state: 'growing' }],
          tileEls: tiles,
          activeId: 'c1',
          bus: { emit(eventName) { events.push(eventName); } },
          dueConceptIds: new Set(['c1']),
          readyFilterActive: true,
        });
        assert.equal(tiles[0].attrs.class, 'tile-group selected is-due');
        assert.equal(tiles[0].attrs['data-due'], '');
        assert.equal(tiles[0].attrs.tabindex, '0');
        assert.equal(tiles[0].attrs['aria-label'], 'Resume First, due for spaced reconstruction');
        assert.equal(tiles[1].attrs.class, 'tile-group empty is-filtered-out');
        assert.equal(tiles[1].attrs.tabindex, '-1');
        assert.equal(tiles[1].attrs['aria-disabled'], 'true');
        assert.equal(tiles[1].attrs['data-ready-filtered'], 'out');
        assert.ok(tiles[0].innerHTML.includes('concept-pin-due-ring'));

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

        const shellGraph = {
          clusters: [
            { subnodes: [{ id: 'n1' }] },
          ],
        };
        const html = conceptListItemHtml({ id: 'c1', name: '<Unsafe>', state: 'growing' });
        assert.ok(html.includes('&lt;Unsafe&gt;'));
        assert.ok(html.includes('data-concept-id="c1"'));
        assert.ok(html.includes('class="concept-actions"'));
        assert.ok(html.includes('aria-haspopup="menu"'));
        assert.ok(html.includes('more_vert'));
        assert.ok(html.includes('class="concept-action-menu"'));
        assert.ok(html.includes('hidden'));
        assert.ok(html.includes('class="concept-delete concept-action-menu-item"'));
        assert.ok(html.includes('Delete session'));
        assert.ok(html.includes('App.deleteConcept(this.dataset.conceptId,this)'));
        assert.ok(html.includes('data-state=""'));
        assert.ok(!html.includes('data-state="growing"'));

        const primedTraining = {
          node_records: {
            n1: {
              attempts: [
                {
                  id: 'a1',
                  at: '2026-05-15T10:00:00.000Z',
                  user_text: 'A substantive first reconstruction.',
                  classification: 'strong',
                  gaps: [],
                },
              ],
            },
          },
        };
        const primedHtml = conceptListItemHtml(
          { id: 'c1', name: 'Primed', state: 'actualized', graphData: shellGraph },
          primedTraining
        );
        assert.ok(primedHtml.includes('data-state="primed"'));
        assert.ok(!primedHtml.includes('actualized'));

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
            { id: 'c1', name: 'First', state: 'growing', graphData: shellGraph },
            { id: 'c2', name: 'Second', state: 'hibernating' },
          ],
          activeId: 'c2',
          trainingByConceptId: {
            c1: primedTraining,
          },
          conceptListEl,
          documentRef: { createElement() { return new FakeElement(); } },
          elementCtor: FakeElement,
          onOpenConcept(concept) { clicked.push(concept.id); },
        });
        assert.equal(conceptListEl.innerHTML, '');
        assert.equal(conceptListEl.children.length, 2);
        assert.equal(conceptListEl.children[0].className, 'concept-item');
        assert.equal(conceptListEl.children[0].dataset.conceptId, 'c1');
        assert.ok(conceptListEl.children[0].innerHTML.includes('data-state="primed"'));
        assert.equal(conceptListEl.children[1].className, 'concept-item active');
        assert.equal(conceptListEl.children[1].dataset.conceptId, 'c2');
        assert.ok(conceptListEl.children[1].innerHTML.includes('data-state=""'));
        conceptListEl.children[0].listeners.click({ target: new FakeElement() });
        assert.deepEqual(clicked, ['c1']);
        const menuTarget = new FakeElement();
        menuTarget.closest = (selector) => selector.includes('.concept-actions') ? {} : null;
        conceptListEl.children[1].listeners.click({ target: menuTarget });
        assert.deepEqual(clicked, ['c1']);
        """
    )
    assert result.returncode == 0, result.stderr


def test_new_concept_field_has_unique_accessible_label() -> None:
    index_html = (REPO_ROOT / "public" / "index.html").read_text()

    assert '<h1 class="ig-title" id="ignition-title" tabindex="-1">' in index_html
    assert "What are you trying to explain?" in index_html
    assert "Write what you remember first. We'll show what to study" in index_html
    assert "You'll write first. Answers come after." in index_html
    assert 'id="ignition-boundary"' in index_html
    assert 'class="ig-eyebrow">New session</p>' in index_html
    assert "socratink will ask for your first model" not in index_html
    assert 'id="hero-single-input-field"' in index_html
    assert 'id="hero-cold-guess-field"' in index_html
    assert 'aria-label="Learning goal"' in index_html
    assert 'aria-label="What do you already think?"' in index_html
    assert '>Start session</button>' in index_html
    assert 'aria-label="What do you want to explain?"' not in index_html


def test_feedback_modal_copy_and_button_contract() -> None:
    index_html = (REPO_ROOT / "public" / "index.html").read_text()

    assert 'role="dialog"' in index_html
    assert 'aria-modal="true"' in index_html
    assert 'aria-labelledby="feedback-title"' in index_html
    assert 'aria-describedby="feedback-desc"' in index_html
    assert '<h2 class="modal-title" id="feedback-title">Feedback</h2>' in index_html
    assert "my local TODO list" not in index_html
    assert 'id="feedback-desc"' in index_html
    assert "A 9 or 10 means the UX feels ready for a new customer." in index_html
    assert '<select id="feedback-ux-rating" class="feedback-rating-input">' in index_html
    assert '<option value="9">9 / 10</option>' in index_html
    assert 'placeholder="Optional: what made it feel that way?"' in index_html
    feedback_textarea = index_html[index_html.index('id="feedback-message"'):index_html.index("</textarea>", index_html.index('id="feedback-message"'))]
    assert "required" not in feedback_textarea
    assert "minlength" not in feedback_textarea
    assert 'id="feedback-status" class="modal-status" role="status" aria-live="polite"' in index_html
    assert '<button class="modal-close" type="button" onclick="Feedback.hide()" aria-label="Close feedback">' in index_html


def test_static_buttons_declare_type() -> None:
    index_html = (REPO_ROOT / "public" / "index.html").read_text()
    parser = ButtonTypeParser()
    parser.feed(index_html)

    assert parser.missing_type == []


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_concept_entry_view_state_derives_route_progression_contract() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          deriveConceptEntryViewState,
          deriveConceptEntries,
        } from './public/js/concept-page-view.js';

        const data = {
          clusters: [{
            id: 'c1',
            label: 'Mechanism cluster',
            subnodes: [
              { id: 'gate', label: 'Sodium gate' },
              { id: 'spread', label: 'Signal spread' },
            ],
          }],
        };

        const entries = deriveConceptEntries(data);
        assert.equal(entries.length, 2);
        assert.equal(entries[0].id, 'gate');
        assert.equal(entries[1].id, 'spread');
        assert.deepEqual(deriveConceptEntryViewState(entries, 0, null), {
          id: 'gate',
          attempted: false,
          state: 'ready to reconstruct',
          nextAction: 'cold_attempt',
        });
        assert.deepEqual(deriveConceptEntryViewState(entries, 1, null), {
          id: 'spread',
          attempted: false,
          state: 'locked',
          nextAction: null,
        });
        assert.equal(
          deriveConceptEntryViewState(entries, 0, {
            node_records: {
              gate: {
                attempts: [{ at: '2026-05-21T00:00:00Z', classification: 'partial' }],
              },
            },
          }).state,
          'primed'
        );
        assert.deepEqual(deriveConceptEntryViewState(null, 0, null), {
          id: 'entry-0',
          attempted: false,
          state: 'locked',
          nextAction: null,
        });
        assert.deepEqual(deriveConceptEntryViewState([], 1, null), {
          id: 'entry-1',
          attempted: false,
          state: 'locked',
          nextAction: null,
        });
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_concept_constellation_renderer_redacts_locked_source_content() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { renderConceptConstellationHtml } from './public/js/concept-constellation-view.js';

        const data = {
          metadata: {
            source_title: 'How sodium channels create an action potential',
            core_thesis: 'Sodium channels open at threshold and sodium enters.',
          },
          clusters: [{
            id: 'gate-cluster',
            title: 'SOURCE TITLE SHOULD NOT APPEAR',
            description: 'SOURCE PREVIEW SHOULD NOT APPEAR',
            subnodes: [
              {
                id: 'gate',
                label: 'Sodium gate',
                mechanism: 'Sodium channels open at threshold.',
                learner_scaffold: { task_label: 'Sodium gate' },
              },
              {
                id: 'spread',
                label: 'Signal spread',
                detail: 'SOURCE DETAIL SHOULD NOT APPEAR',
                mechanism: 'The depolarization propagates.',
                learner_scaffold: { task_label: 'Signal spread' },
              },
              {
                id: 'reset',
                label: 'Reset phase',
                study_note: 'Potassium channels reset the membrane.',
                learner_scaffold: { task_label: 'Reset phase' },
              },
              {
                id: 'legacy',
                label: 'Legacy fallback label',
                drill_status: 'primed',
              },
            ],
          }],
        };

        const activeHtml = renderConceptConstellationHtml(data, {
          activeEntryId: 'gate',
          training: {
            node_records: {
              gate: {
                attempts: [{ at: '2026-05-21T00:00:00Z', classification: 'partial' }],
              },
            },
          },
        });
        assert.match(activeHtml, /concept-constellation__svg/);
        assert.match(activeHtml, /concept-constellation__shell/);
        assert.match(activeHtml, /concept-constellation__edge/);
        assert.doesNotMatch(activeHtml, /concept-constellation__edge[^"]*is-lit/);
        assert.match(activeHtml, /concept-constellation__selected/);
        assert.match(activeHtml, /Draft structure only\\./);
        assert.match(activeHtml, /Overview first\\./);
        assert.match(activeHtml, /concept-constellation__return/);
        assert.doesNotMatch(activeHtml, /role="img"/);
        assert.match(activeHtml, /class="concept-constellation__node[^"]*"\\s+data-entry-id="gate"/);
        assert.match(activeHtml, /class="concept-constellation__node is-active"/);
        assert.match(activeHtml, /data-state="primed"/);
        assert.match(activeHtml, /role="button"/);
        assert.match(activeHtml, /tabindex="0"/);
        assert.match(activeHtml, /data-constellation-selected-name>Sodium gate/);
        assert.match(activeHtml, /data-constellation-selected-purpose>Write the first useful reconstruction before study appears\\./);
        assert.match(activeHtml, /Sodium gate/);
        assert.match(activeHtml, /Entry 02/);
        assert.match(activeHtml, /Legacy fallback label/);
        assert.doesNotMatch(activeHtml, /Signal spread/);
        assert.doesNotMatch(activeHtml, /Reset phase/);
        assert.match(activeHtml, /data-entry-id="legacy"[\\s\\S]*data-state="primed"/);

        const attemptedHtml = renderConceptConstellationHtml(data, {
          activeEntryId: 'reset',
          training: {
            node_records: {
              gate: {
                attempts: [{ at: '2026-05-21T00:00:00Z', classification: 'partial' }],
              },
              spread: {
                attempts: [{ at: '2026-05-21T00:05:00Z', classification: 'partial' }],
              },
            },
          },
        });
        assert.match(attemptedHtml, /Signal spread/);
        assert.match(attemptedHtml, /Reset phase/);
        assert.match(attemptedHtml, /concept-constellation__edge[^"]*is-lit/);

        const coldHtml = renderConceptConstellationHtml(data, {
          activeEntryId: 'gate',
          training: null,
        });
        assert.match(coldHtml, /data-entry-id="gate"[\\s\\S]*data-state="ready"/);
        assert.match(coldHtml, /Entry 02/);
        assert.doesNotMatch(coldHtml, /Signal spread/);
        assert.match(coldHtml, /data-entry-id="legacy"[\\s\\S]*data-state="primed"/);

        for (const forbidden of [
          /Sodium channels open at threshold/,
          /SOURCE TITLE SHOULD NOT APPEAR/,
          /SOURCE PREVIEW SHOULD NOT APPEAR/,
          /SOURCE DETAIL SHOULD NOT APPEAR/,
          /The depolarization propagates/,
          /Potassium channels reset the membrane/,
          /How sodium channels create an action potential/,
          /core_thesis/,
          /mechanism/,
          /study_note/,
          /description/,
          /detail/,
          /title=/,
        ]) {
          assert.doesNotMatch(activeHtml, forbidden);
          assert.doesNotMatch(attemptedHtml, forbidden);
          assert.doesNotMatch(coldHtml, forbidden);
        }
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_comparison_acknowledgement_is_ui_only_and_reset_scoped() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          clearComparisonAcknowledgement,
          clearComparisonAcknowledgementsForConcept,
          hasComparisonAcknowledgement,
          markComparisonAcknowledged,
        } from './public/js/comparison-acknowledgement.js';

        const backing = new Map();
        const storage = {
          getItem(key) {
            return backing.has(key) ? backing.get(key) : null;
          },
          setItem(key, value) {
            backing.set(key, String(value));
          },
          removeItem(key) {
            backing.delete(key);
          },
          key(index) {
            return Array.from(backing.keys())[index] || null;
          },
          get length() {
            return backing.size;
          },
        };

        assert.equal(hasComparisonAcknowledgement('concept-1', 'entry-1', storage), false);
        markComparisonAcknowledged('concept-1', 'entry-1', storage);
        assert.equal(hasComparisonAcknowledgement('concept-1', 'entry-1', storage), true);
        assert.equal(hasComparisonAcknowledgement('concept-1', 'entry-2', storage), false);
        assert.equal(hasComparisonAcknowledgement('concept-2', 'entry-1', storage), false);

        // Later repairs or spaced re-drills change attempts, but the UI-only
        // acknowledgement remains scoped to the entry, not the latest attempt id.
        markComparisonAcknowledged('concept-1', 'entry-1', storage);
        assert.equal(hasComparisonAcknowledgement('concept-1', 'entry-1', storage), true);

        clearComparisonAcknowledgement('concept-1', 'entry-1', storage);
        assert.equal(hasComparisonAcknowledgement('concept-1', 'entry-1', storage), false);

        markComparisonAcknowledged('concept-1', 'entry-1', storage);
        markComparisonAcknowledged('concept-1', 'entry-2', storage);
        markComparisonAcknowledged('concept-2', 'entry-1', storage);
        clearComparisonAcknowledgementsForConcept('concept-1', storage);
        assert.equal(hasComparisonAcknowledgement('concept-1', 'entry-1', storage), false);
        assert.equal(hasComparisonAcknowledgement('concept-1', 'entry-2', storage), false);
        assert.equal(hasComparisonAcknowledgement('concept-2', 'entry-1', storage), true);

        const throwingStorage = {
          getItem() {
            throw new Error('get blocked');
          },
          setItem() {
            throw new Error('set blocked');
          },
          removeItem() {
            throw new Error('remove blocked');
          },
          key() {
            throw new Error('key blocked');
          },
          get length() {
            throw new Error('length blocked');
          },
        };
        assert.equal(hasComparisonAcknowledgement('concept-1', 'entry-1', throwingStorage), false);
        assert.doesNotThrow(() => markComparisonAcknowledged('concept-1', 'entry-1', throwingStorage));
        assert.doesNotThrow(() => clearComparisonAcknowledgement('concept-1', 'entry-1', throwingStorage));
        assert.doesNotThrow(() => clearComparisonAcknowledgementsForConcept('concept-1', throwingStorage));

        const partiallyFailingStorage = {
          removed: [],
          get length() {
            return 3;
          },
          key(index) {
            if (index === 0) throw new Error('slot blocked');
            if (index === 1) return 'socratink:comparison_ack:v1:concept-1:entry-3';
            return 'socratink:comparison_ack:v1:concept-2:entry-1';
          },
          removeItem(key) {
            this.removed.push(key);
          },
        };
        clearComparisonAcknowledgementsForConcept('concept-1', partiallyFailingStorage);
        assert.deepEqual(partiallyFailingStorage.removed, ['socratink:comparison_ack:v1:concept-1:entry-3']);
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_source_less_gestalt_hybrid_stage_contracts() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          deriveConceptEntries,
          renderActiveEntryHtml,
        } from './public/js/concept-page-view.js';

        const graphData = {
          metadata: {
            core_thesis: 'AI-generated answer structure must stay hidden.',
            learner_goal: 'explain sodium channel gating',
            source_title: 'Learner launch sketch',
          },
          clusters: [{
            id: 'c1',
            label: 'Generated cluster label should not be a pre-attempt marker',
            description: 'Generated cluster description should stay hidden.',
            subnodes: [
              {
                id: 'gate',
                label: 'Voltage threshold opens sodium channels',
                mechanism: 'Sodium channels open when membrane voltage reaches threshold.',
                study_note: 'Voltage-gated sodium channels open at threshold, letting sodium rush in.',
                learner_scaffold: {
                  learner_move: 'Say it',
                  task_label: 'Sodium gate',
                  task_cue: 'Name the trigger without reading the note.',
                  entry_prompt: 'What do you think makes the sodium channel open?',
                  expected_shape: 'Write one sentence. Name the trigger, even if you are guessing.',
                  blank_hint: 'Use voltage, signal, or trigger if one of those feels useful.',
                },
              },
              {
                id: 'spread',
                label: 'Sodium influx causes depolarization',
                mechanism: 'Sodium influx depolarizes the next membrane segment.',
                study_note: 'Hidden future study note.',
                learner_scaffold: {
                  learner_move: 'Explain how',
                  task_label: 'Signal spread',
                  task_cue: 'Connect one step to the next.',
                  entry_prompt: 'How do you think the signal moves?',
                },
              },
            ],
          }],
        };
        const entries = deriveConceptEntries(graphData);
        const concept = {
          id: 'sample-customer-sketch',
          name: 'action potentials',
          contentType: null,
          sourceUrl: null,
          startingMapContext: 'I think nerves send electricity by opening little gates, but I am fuzzy on what starts it.',
        };

        const coldHtml = renderActiveEntryHtml(
          entries[0],
          0,
          entries,
          concept,
          graphData,
          { source_mode: 'source_less', node_records: {} },
          { viewMode: 'cold-surface' }
        );
        assert.ok(coldHtml.includes('Context'));
        assert.ok(coldHtml.includes('I think nerves send electricity'));
        assert.ok(!coldHtml.includes('Write first. Compare after.'));
        assert.ok(coldHtml.includes('aria-label="Concept context"'));
        assert.ok(coldHtml.includes('Study stays hidden until you save a draft. This is not a grade.'));
        assert.ok(coldHtml.includes('What do you think makes the sodium channel open?'));
        assert.ok(coldHtml.includes('Sodium gate'));
        assert.ok(coldHtml.includes('Save draft'));
        assert.ok(!coldHtml.includes('Shaped by your sketch'));
        assert.ok(!coldHtml.includes('Shaped from your launch attempt, not verified against a source.'));
        assert.ok(!coldHtml.includes('AI-generated answer structure must stay hidden.'));
        assert.ok(!coldHtml.includes('Voltage threshold opens sodium channels'));
        assert.ok(!coldHtml.includes('Sodium influx causes depolarization'));
        assert.ok(!coldHtml.includes('concept-page-b2__route-item'));
        assert.ok(!coldHtml.includes('concept-page-b2__route-marker-item'));
        assert.ok(!coldHtml.includes('data-entry-id="spread"'));
        assert.ok(!coldHtml.includes('concept-page-b2__nearby'));

        const coldWithoutTrainingHtml = renderActiveEntryHtml(
          entries[0],
          0,
          entries,
          concept,
          graphData,
          null
        );
        assert.ok(coldWithoutTrainingHtml.includes('aria-label="Concept context"'));
        assert.ok(!coldWithoutTrainingHtml.includes('Shaped from your launch attempt, not verified against a source.'));
        assert.ok(coldWithoutTrainingHtml.includes('What do you think makes the sodium channel open?'));
        assert.ok(!coldWithoutTrainingHtml.includes('concept-page-b2__route-item'));
        assert.ok(!coldWithoutTrainingHtml.includes('concept-page-b2__route-marker-item'));
        assert.ok(!coldWithoutTrainingHtml.includes('data-entry-id="spread"'));
        assert.ok(!coldWithoutTrainingHtml.includes('concept-page-b2__nearby'));

        const savedDraftTraining = {
          source_mode: 'source_less',
          node_records: {
            gate: {
              attempts: [{
                id: 'cold-1',
                kind: 'cold',
                at: '2026-05-21T10:00:00.000Z',
                user_text: 'The gate probably opens when the voltage gets high enough.',
                classification: 'partial',
                gaps: [{ mechanism: 'threshold', correction: 'Name threshold as the opening condition.' }],
                grader_version: 'qa',
              }],
              repairs: [],
            },
          },
        };
        const savedHtml = renderActiveEntryHtml(
          entries[0],
          0,
          entries,
          concept,
          graphData,
          savedDraftTraining,
          { viewMode: 'saved-draft-study-gate' }
        );
        assert.ok(savedHtml.includes('concept-page-b2__evidence--study-gate'));
        assert.ok(!savedHtml.includes('Draft recorded. Having your own words fresh in mind makes it easier to notice the differences when you read the notes.'));
        assert.ok(savedHtml.includes('The gate probably opens when the voltage gets high enough.'));
        assert.ok(savedHtml.includes('Reveal notes and compare'));
        assert.ok(!savedHtml.includes('Missing piece'));
        assert.ok(!savedHtml.includes('threshold as the opening condition'));
        assert.ok(!savedHtml.includes('concept-page-b2__route'));
        assert.ok(savedHtml.includes('concept-page-b2__gestalt--single-column'));
        assert.ok(!savedHtml.includes('concept-page-b2__nearby'));

        const cleanRevealedTraining = {
          source_mode: 'source_less',
          node_records: {
            gate: {
              attempts: [{
                id: 'cold-2',
                kind: 'cold',
                at: '2026-05-21T10:00:00.000Z',
                user_text: 'The channel opens when voltage reaches threshold.',
                classification: 'strong',
                gaps: [],
                grader_version: 'qa',
              }],
              study_revealed_at: '2026-05-21T10:05:00.000Z',
              repairs: [],
            },
          },
        };
        const compareHtml = renderActiveEntryHtml(
          entries[0],
          0,
          entries,
          concept,
          graphData,
          cleanRevealedTraining,
          { viewMode: 'post-reveal-comparison', now: '2026-05-21T11:00:00.000Z' }
        );
        assert.ok(compareHtml.includes('Compare notes'));
        assert.ok(compareHtml.includes('The channel opens when voltage reaches threshold.'));
        assert.ok(compareHtml.includes('Voltage-gated sodium channels open at threshold'));
        assert.ok(compareHtml.includes('Continue'));
        assert.ok(compareHtml.includes('data-active-entry-action="next-entry"'));
        assert.ok(compareHtml.includes('data-active-entry-id="spread"'));
        assert.ok(compareHtml.includes('Rate this moment'));
        assert.ok(compareHtml.includes('data-feedback-rating'));
        assert.ok(compareHtml.includes('data-feedback-moment="compare notes"'));
        assert.ok(!compareHtml.includes('No missing piece recorded for this draft.'));
        assert.ok(!compareHtml.includes('concept-page-b2__route-item'));
        assert.ok(compareHtml.includes('concept-page-b2__gestalt--single-column'));
        assert.ok(!compareHtml.includes('data-entry-id="spread"'));
        assert.ok(!compareHtml.includes('concept-page-b2__nearby'));

        const autoCompareHtml = renderActiveEntryHtml(
          entries[0],
          0,
          entries,
          concept,
          graphData,
          cleanRevealedTraining,
          { comparisonAcknowledged: false, now: '2026-05-21T11:00:00.000Z' }
        );
        assert.ok(autoCompareHtml.includes('Compare notes'));
        assert.ok(autoCompareHtml.includes('Continue'));
        assert.ok(autoCompareHtml.includes('data-active-entry-action="next-entry"'));
        assert.ok(autoCompareHtml.includes('data-active-entry-id="spread"'));
        assert.ok(autoCompareHtml.includes('Rate this moment'));
        assert.ok(autoCompareHtml.includes('data-feedback-rating'));
        assert.ok(autoCompareHtml.includes('data-feedback-moment="compare notes"'));
        assert.ok(autoCompareHtml.includes('concept-page-b2__gestalt--single-column'));
        assert.ok(!autoCompareHtml.includes('concept-page-b2__nearby'));
        assert.ok(!autoCompareHtml.includes('concept-page-b2__route-item'));

        const expandedHtml = renderActiveEntryHtml(
          entries[0],
          0,
          entries,
          concept,
          graphData,
          cleanRevealedTraining,
          { viewMode: 'expanded-workspace', now: '2026-05-21T11:00:00.000Z' }
        );
        assert.ok(!expandedHtml.includes('concept-page-b2__route-item'));
        assert.ok(!expandedHtml.includes('concept-page-b2__route-marker-item'));
        assert.ok(!expandedHtml.includes('data-entry-id="spread"'));
        assert.ok(!expandedHtml.includes('data-active-entry-action="keep-working"'));
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_concept_page_inline_drill_mount_preserves_context() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          deriveConceptEntries,
          renderActiveEntryHtml,
        } from './public/js/concept-page-view.js';

        const graphData = {
          metadata: {
            starting_map_context: 'I think voltage opens a gate, then sodium moves.',
          },
          clusters: [{
            id: 'c1',
            subnodes: [
              { id: 'gate', label: 'Sodium gate', purpose: 'Name the trigger.' },
              { id: 'spread', label: 'Signal spread', purpose: 'Connect the next step.' },
            ],
          }],
        };
        const entries = deriveConceptEntries(graphData);
        const html = renderActiveEntryHtml(
          entries[0],
          0,
          entries,
          { id: 'concept-1', name: 'Action potentials' },
          graphData,
          { node_records: {} },
          { isDrilling: true }
        );

        assert.match(html, /node-strip/);
        assert.match(html, /node-strip-item/);
        assert.match(html, /concept-page-b2__route-item/);
        assert.match(html, /vd-sketch-wrapper/);
        assert.match(html, /data-action="toggle-sketch"/);
        assert.match(html, /I think voltage opens a gate/);
        assert.match(html, /concept-page-b2__active-entry--drilling/);
        assert.match(html, /id="drill-chamber-view"/);
        assert.match(html, /id="chamber-chat-log"/);
        assert.doesNotMatch(html, /id="chamber-history-toggle"/);
        assert.doesNotMatch(html, /data-active-entry-action="drill"/);
      """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_source_less_view_mode_derivation_preserves_comparison_seams() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import { deriveSourceLessViewMode } from './public/js/concept-page-view.js';

        assert.equal(deriveSourceLessViewMode({
          attempted: false,
          record: null,
          next_action: 'cold_attempt',
        }), 'cold-surface');

        assert.equal(deriveSourceLessViewMode({
          attempted: true,
          next_action: 'study',
          record: {
            attempts: [{ id: 'a1', at: '2026-05-21T10:00:00.000Z' }],
            repairs: [],
          },
        }), 'saved-draft-study-gate');

        assert.equal(deriveSourceLessViewMode({
          attempted: true,
          next_action: 'repair',
          record: {
            attempts: [{ id: 'a1', at: '2026-05-21T10:00:00.000Z' }],
            study_revealed_at: '2026-05-21T10:05:00.000Z',
            repairs: [],
          },
        }, { comparisonAcknowledged: false }), 'post-reveal-comparison');

        assert.equal(deriveSourceLessViewMode({
          attempted: true,
          next_action: 'review',
          record: {
            attempts: [{ id: 'a1', at: '2026-05-21T10:00:00.000Z' }],
            study_revealed_at: '2026-05-21T10:05:00.000Z',
            repairs: [],
          },
        }, { comparisonAcknowledged: false }), 'post-reveal-comparison');

        assert.equal(deriveSourceLessViewMode({
          attempted: true,
          next_action: 'repair',
          record: {
            attempts: [{ id: 'a1', at: '2026-05-21T10:00:00.000Z' }],
            study_revealed_at: '2026-05-21T10:05:00.000Z',
            repairs: [],
          },
        }, { comparisonAcknowledged: true }), 'expanded-workspace');

        assert.equal(deriveSourceLessViewMode({
          attempted: true,
          next_action: 'spaced_attempt',
          record: {
            attempts: [{ id: 'legacy-after-study', at: '2026-05-21T10:10:00.000Z' }],
            study_revealed_at: '2026-05-21T10:05:00.000Z',
            repairs: [],
          },
        }, { comparisonAcknowledged: false }), 'expanded-workspace');
        """
    )
    assert result.returncode == 0, result.stderr


def test_audio_surfaces_share_versioned_audio_module_instance() -> None:
    app_js = (REPO_ROOT / "public" / "js" / "app.js").read_text(encoding="utf-8")
    launch_pad_js = (REPO_ROOT / "public" / "js" / "launch-pad.js").read_text(encoding="utf-8")
    source_panel_js = (REPO_ROOT / "public" / "js" / "source-panel.js").read_text(encoding="utf-8")

    assert "from './audio.js?v=4'" in app_js
    assert "from './audio.js?v=4'" in launch_pad_js
    assert 'from "./audio.js?v=4"' in source_panel_js
    assert "from './audio.js';" not in launch_pad_js
    assert 'from "./audio.js";' not in source_panel_js


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_concept_page_view_renders_active_entry_html_contract() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';
        import {
          deriveConceptEntries,
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
        assert.ok(legacyDrilledHtml.includes('Ready to reconstruct again'));
        assert.ok(!legacyDrilledHtml.includes('ready to reconstruct again entry 1 of 1'));

        const legacyStudyHtml = renderActiveEntryHtml(
          { id: 'legacy-study', label: 'Legacy study', drill_status: 'primed', drill_phase: 'study', study_note: 'Legacy study note.' },
          0,
          [{ id: 'legacy-study', label: 'Legacy study', drill_status: 'primed', drill_phase: 'study', study_note: 'Legacy study note.' }],
          {},
          { metadata: {} }
        );
        assert.ok(legacyStudyHtml.includes('Draft saved'));
        assert.ok(!legacyStudyHtml.includes('study required entry 1 of 1'));
        assert.ok(legacyStudyHtml.includes('data-active-entry-action="study"'));
        assert.ok(legacyStudyHtml.includes('Reveal notes and compare'));
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
        const legacyPrimedWaitingHtml = renderActiveEntryHtml(
          {
            id: 'legacy-waiting',
            label: 'Legacy waiting',
            drill_status: 'primed',
            re_drill_eligible_after: '2026-05-16T04:00:00.000Z',
          },
          0,
          [{
            id: 'legacy-waiting',
            label: 'Legacy waiting',
            drill_status: 'primed',
            re_drill_eligible_after: '2026-05-16T04:00:00.000Z',
          }],
          {},
          { metadata: {} },
          null,
          { now: '2026-05-15T20:00:00.000Z' }
        );
        assert.ok(legacyPrimedWaitingHtml.includes('Review later'));
        assert.ok(!legacyPrimedWaitingHtml.includes('Review later entry 1 of 1'));
        assert.ok(!legacyPrimedWaitingHtml.includes('concept-page-b2__entry-cta'));
        const legacyPrimedReadyHtml = renderActiveEntryHtml(
          {
            id: 'legacy-ready',
            label: 'Legacy ready',
            drill_status: 'primed',
            re_drill_eligible_after: '2026-05-16T04:00:00.000Z',
          },
          0,
          [{
            id: 'legacy-ready',
            label: 'Legacy ready',
            drill_status: 'primed',
            re_drill_eligible_after: '2026-05-16T04:00:00.000Z',
          }],
          {},
          { metadata: {} },
          null,
          { now: '2026-05-16T05:00:00.000Z' }
        );
        assert.ok(legacyPrimedReadyHtml.includes('Ready to reconstruct again'));
        assert.ok(!legacyPrimedReadyHtml.includes('spaced reconstruction ready entry 1 of 1'));
        assert.ok(legacyPrimedReadyHtml.includes('concept-page-b2__entry-cta'));

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
        assert.ok(solidifiedHtml.includes('solidified'));
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
        assert.ok(legacySolidWithPartialTrainingHtml.includes('solidified'));
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
        assert.ok(blockedHtml.includes('locked'));
        assert.ok(blockedHtml.includes('aria-disabled="true"'));
        assert.ok(blockedHtml.includes('>Locked</button>'));
        assert.ok(blockedHtml.includes('&lt;Core&gt;'));
        assert.ok(blockedHtml.includes('Second &amp; unsafe'));
        assert.ok(blockedHtml.includes('ready to reconstruct'));

        const readyHtml = renderActiveEntryHtml(
          backbone[1],
          1,
          backbone,
          { startingMapContext: '' },
          { metadata: { starting_map_context: 'metadata sketch' } },
          training
        );
        assert.ok(readyHtml.includes('metadata sketch'));
        assert.ok(readyHtml.includes('concept-page-b2__gestalt'));
        assert.ok(readyHtml.includes('concept-page-b2__route'));
        assert.ok(!readyHtml.includes('Write first. Compare after.'));
        assert.ok(readyHtml.includes('Start from memory'));
        assert.ok(!readyHtml.includes('first reconstruction entry 2 of 3'));
        assert.ok(readyHtml.includes('Save draft'));
        assert.ok(readyHtml.includes('Need a cue?'));
        assert.ok(readyHtml.includes('data-blank-start'));
        assert.ok(readyHtml.includes('data-blank-start-hint'));
        assert.ok(!readyHtml.includes('The mechanism stays hidden.'));
        assert.ok(readyHtml.includes('concept-page-b2__attempt'));
        assert.ok(!readyHtml.includes('concept-page-b2__entry-cta'));

        const sourceLessHtml = renderActiveEntryHtml(
          backbone[1],
          1,
          backbone,
          { startingMapContext: '' },
          { metadata: { starting_map_context: 'metadata sketch' } },
          {
            source_mode: 'source_less',
            node_records: training.node_records,
          }
        );
        assert.ok(sourceLessHtml.includes('aria-label="Concept context"'));
        assert.ok(!sourceLessHtml.includes('Shaped from your launch attempt, not verified against a source.'));
        const sourceAttachedHtml = renderActiveEntryHtml(
          backbone[1],
          1,
          backbone,
          { startingMapContext: '' },
          { metadata: { starting_map_context: 'metadata sketch' } },
          {
            source_mode: 'source_attached',
            node_records: training.node_records,
          }
        );
        assert.ok(sourceAttachedHtml.includes('aria-label="Concept context"'));

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
        assert.ok(readyAttemptHtml.includes('Write what you can explain now'));
        assert.ok(readyAttemptHtml.includes('Save draft'));
        assert.ok(!readyAttemptHtml.includes('concept-page-b2__entry-cta'));

        const scaffoldedMap = {
          metadata: {
            starting_map_context: 'Hermes Agent is a self-improving autonomous agent.',
            core_thesis: 'Hermes Agent composes durable agent capabilities into one working system.',
            learner_goal: 'build a reliable agent system',
          },
          backbone: [{ id: 'b1', principle: 'Starting model', dependent_clusters: ['c1'] }],
          clusters: [{
            id: 'c1',
            label: 'Starting model',
            description: 'State the system in your own words.',
            subnodes: [{
              id: 'c1_s1',
              label: 'Starting model',
              mechanism: 'Hermes works by composing persistent memory, reusable skills, executable tools, provider routing, deployment environments, and safety boundaries.',
              learner_scaffold: {
                bloom_level: 'understand',
                learner_move: 'Say it',
                task_label: 'Starting model',
                task_cue: 'Put the system in your words.',
                tailoring_anchor: 'You mentioned a self-improving agent, so this starts by naming what parts are working together.',
                entry_prompt: 'How would you explain Hermes Agent to a classmate right now?',
                expected_shape: 'Write 1-2 sentences. Name what it does and one fuzzy part.',
                sentence_starter: 'My current guess is that Hermes Agent works by...',
                blank_hint: 'Pick one phrase from your sketch and say what role it plays.',
                evidence_goal: 'Learner states an initial model without reading source content.',
              },
            }],
          }],
        };
        const scaffoldEntries = deriveConceptEntries(scaffoldedMap);
        assert.equal(scaffoldEntries.length, 1);
        assert.equal(scaffoldEntries[0].id, 'c1_s1');
        assert.equal(scaffoldEntries[0].learner_scaffold.task_label, 'Starting model');
        const scaffoldHtml = renderActiveEntryHtml(
          scaffoldEntries[0],
          0,
          scaffoldEntries,
          { startingMapContext: '' },
          scaffoldedMap,
          { source_mode: 'source_less', node_records: {} },
          { attemptEntryId: 'c1_s1' }
        );
        assert.ok(scaffoldHtml.includes('Starting model'));
        assert.ok(!scaffoldHtml.includes('Put the system in your words.'));
        assert.ok(!scaffoldHtml.includes('Shaped by your sketch'));
        assert.ok(!scaffoldHtml.includes('State the system in your own words.'));
        assert.ok(scaffoldHtml.includes('How would you explain Hermes Agent to a classmate right now?'));
        assert.ok(scaffoldHtml.includes('Goal: build a reliable agent system. First make a starting guess for Starting model.'));
        assert.ok(scaffoldHtml.includes('Write 1-2 sentences. Name what it does and one fuzzy part.'));
        assert.ok(scaffoldHtml.includes('My current guess is that Hermes Agent works by...'));
        assert.ok(scaffoldHtml.includes('Pick one phrase from your sketch and say what role it plays.'));
        assert.ok(!scaffoldHtml.includes('Draft your starting guess: what it does, what it connects to, or why it matters.'));
        assert.ok(!scaffoldHtml.includes('Not sure yet? Type what you think it might do, or list a few terms you recognize.'));
        assert.ok(scaffoldHtml.includes('Save draft'));
        assert.ok(!scaffoldHtml.includes('Bloom'));
        assert.ok(!scaffoldHtml.includes('bloom_level'));
        assert.ok(!scaffoldHtml.includes('provider routing, deployment environments'));

        const moveOnlyEntries = deriveConceptEntries({
          backbone: [],
          clusters: [{
            id: 'c1',
            label: 'Move-only label',
            description: 'Move-only cue.',
            subnodes: [{
              id: 'c1_s1',
              label: 'Move-only label',
              mechanism: 'Hidden answer.',
              learner_scaffold: {
                bloom_level: 'understand',
                learner_move: 'Use it',
                task_label: '',
                task_cue: '',
                tailoring_anchor: '',
                entry_prompt: 'What is your current model?',
                expected_shape: 'Write one sentence.',
                sentence_starter: 'My current model is...',
                blank_hint: 'Use one word from your sketch.',
                evidence_goal: 'Learner states a current model.',
              },
            }],
          }],
        });
        const moveOnlyHtml = renderActiveEntryHtml(
          moveOnlyEntries[0],
          0,
          moveOnlyEntries,
          {},
          { metadata: {} },
          { source_mode: 'source_less', node_records: {} }
        );
        assert.ok(moveOnlyHtml.includes('Use it'));
        assert.ok(moveOnlyHtml.includes('My current model is...'));
        assert.ok(moveOnlyHtml.includes('Use one word from your sketch.'));
        assert.ok(!moveOnlyHtml.includes('Draft your starting guess: what it does, what it connects to, or why it matters.'));
        assert.ok(!moveOnlyHtml.includes('Not sure yet? Type what you think it might do, or list a few terms you recognize.'));
        assert.ok(!moveOnlyHtml.includes('Say it'));
        assert.ok(!moveOnlyHtml.includes('Core Logic'));

        const fallbackScaffoldEntries = deriveConceptEntries({
          clusters: [{
            id: 'c1',
            subnodes: [{
              id: 'c1_s1',
              label: 'Fallback label',
              learner_scaffold: {
                bloom_level: 'understand',
                learner_move: 'Say it',
                task_label: 'Fallback label',
                task_cue: 'Name the working relationship.',
                tailoring_anchor: '',
                entry_prompt: 'What relationship do you think matters here?',
                expected_shape: 'Write one relationship you suspect.',
                sentence_starter: '',
                blank_hint: '',
                evidence_goal: 'Learner states a suspected relationship.',
              },
            }],
          }],
        });
        const fallbackScaffoldHtml = renderActiveEntryHtml(
          fallbackScaffoldEntries[0],
          0,
          fallbackScaffoldEntries,
          {},
          { metadata: {} },
          { source_mode: 'source_less', node_records: {} }
        );
        assert.ok(fallbackScaffoldHtml.includes('Write one relationship you suspect.'));
        assert.ok(fallbackScaffoldHtml.includes('placeholder="Write what you can explain right now."'));
        assert.ok(!fallbackScaffoldHtml.includes('placeholder="Write one relationship you suspect."'));
        assert.ok(fallbackScaffoldHtml.includes('Type one relationship you suspect, even if it feels incomplete.'));

        const primedHtml = renderActiveEntryHtml(
          { id: 'primed', label: 'Primed', drill_status: 'primed', study_note: 'Hidden reference note.' },
          0,
          [{ id: 'primed', label: 'Primed', drill_status: 'primed', study_note: 'Hidden reference note.' }],
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
        assert.ok(primedHtml.includes('add context'));
        assert.ok(primedHtml.includes('Draft saved'));
        assert.ok(!primedHtml.includes('study required entry 1 of 1'));
        assert.ok(primedHtml.includes('Your memory draft'));
        assert.ok(primedHtml.includes('concept-page-b2__evidence--study-gate'));
        assert.ok(!primedHtml.includes('Draft recorded. Having your own words fresh in mind makes it easier to notice the differences when you read the notes.'));
        assert.ok(primedHtml.includes('Draft saved'));
        assert.ok(primedHtml.includes('A strong first attempt.'));
        assert.ok(!primedHtml.includes('Missing piece'));
        assert.ok(!primedHtml.includes('Hidden reference note.'));
        assert.ok(primedHtml.includes('data-active-entry-action="study"'));
        assert.ok(primedHtml.includes('Reveal notes and compare'));

        const legacyRedrillWithTrainingHtml = renderActiveEntryHtml(
          {
            id: 'legacy-redrill-training',
            label: 'Legacy re-drill with training',
            drill_status: 'drilled',
            last_drilled: '2026-05-15T10:05:00.000Z',
          },
          0,
          [{
            id: 'legacy-redrill-training',
            label: 'Legacy re-drill with training',
            drill_status: 'drilled',
            last_drilled: '2026-05-15T10:05:00.000Z',
          }],
          {},
          { metadata: {} },
          {
            node_records: {
              'legacy-redrill-training': {
                attempts: [{
                  id: 'legacy-r1',
                  kind: 'cold',
                  at: '2026-05-15T10:00:00.000Z',
                  user_text: 'A thin migrated attempt.',
                  classification: 'thin',
                  gaps: [{ type: 'mechanism', description: 'Missing causal link.' }],
                  grader_version: 'qa',
                }],
                repairs: [],
              },
            },
          }
        );
        assert.ok(legacyRedrillWithTrainingHtml.includes('Needs repair'));
        assert.ok(!legacyRedrillWithTrainingHtml.includes('repair the gap entry 1 of 1'));
        assert.ok(legacyRedrillWithTrainingHtml.includes('A thin migrated attempt.'));
        assert.ok(!legacyRedrillWithTrainingHtml.includes('study required entry 1 of 1'));

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
        assert.ok(studiedHtml.includes('Review later'));
        assert.ok(!studiedHtml.includes('Review later entry 1 of 1'));
        assert.ok(studiedHtml.includes('concept-page-b2__evidence'));
        assert.ok(studiedHtml.includes('Your draft'));
        assert.ok(!studiedHtml.includes('learner reconstruction'));
        assert.ok(studiedHtml.includes('A strong first attempt.'));
        assert.ok(!studiedHtml.includes('No missing piece recorded for this draft.'));
        assert.ok(studiedHtml.includes('concept-page-b2__study-note'));
        assert.ok(studiedHtml.includes('Study note for this entry.'));
        assert.ok(!studiedHtml.includes('concept-page-b2__entry-cta'));

        const studiedRouteHtml = renderActiveEntryHtml(
          { id: 'studied', label: 'Studied', purpose: 'Study note for this entry.' },
          0,
          [
            { id: 'studied', label: 'Studied', purpose: 'Study note for this entry.' },
            { id: 'next-entry', label: 'Next entry', purpose: 'Write the next link from memory.' },
          ],
          { contentType: 'text' },
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
        assert.ok(studiedRouteHtml.includes('Review later'));
        assert.ok(studiedRouteHtml.includes('Continue route'));
        assert.ok(studiedRouteHtml.includes('data-active-entry-id="next-entry"'));
        assert.ok(studiedRouteHtml.includes('data-active-entry-action="next-entry"'));

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
                    correction: 'The learner correctly identifies sodium flow but does not name the voltage-gated channel opening.',
                  }],
                  grader_version: 'qa',
                }],
                study_revealed_at: '2026-05-15T10:05:00.000Z',
                repairs: [],
              },
            },
          }
        );
        assert.ok(repairHtml.includes('Needs repair'));
        assert.ok(!repairHtml.includes('repair the gap entry 1 of 1'));
        assert.ok(!repairHtml.includes('nearby entries  all locked until first reconstruction'));
        assert.ok(repairHtml.includes('Nearby entries'));
        assert.ok(repairHtml.includes('concept-page-b2__evidence'));
        assert.ok(repairHtml.includes('Your draft'));
        assert.ok(repairHtml.includes('concept-page-b2__evidence--compact'));
        assert.ok(!repairHtml.includes('Missing piece'));
        assert.ok(!repairHtml.includes('repair hinge'));
        assert.ok(repairHtml.includes('Sodium just rushes in.'));
        assert.ok(repairHtml.includes('Your draft names sodium flow but does not name the voltage-gated channel opening.'));
        assert.ok(!repairHtml.includes('The learner correctly identifies'));
        assert.ok(repairHtml.includes('concept-page-b2__repair'));
        assert.ok(repairHtml.includes('Repair'));
        assert.ok(repairHtml.includes('Missing link'));
        assert.ok(repairHtml.includes('Your draft names sodium flow but does not name the voltage-gated channel opening.'));
        assert.ok(repairHtml.includes('data-repair-entry-id="repair"'));
        assert.ok(!repairHtml.includes('Put it in your words'));
        assert.ok(!repairHtml.includes('1 missing link to repair'));
        assert.ok(!repairHtml.includes('Save this repair before you try from memory again.'));
        assert.ok(repairHtml.includes('Write the missing link.'));
        assert.ok(repairHtml.includes('Use your words. One or two sentences is enough.'));
        assert.ok(repairHtml.includes('Save repair'));
        assert.ok(repairHtml.includes('Study note stays hidden while you repair.'));
        assert.ok(repairHtml.includes('Show study note'));
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
        assert.ok(repairedHtml.includes('Needs repair'));
        assert.ok(!repairedHtml.includes('repair the gap entry 1 of 1'));
        assert.ok(!repairedHtml.includes('Write it again'));
        assert.ok(repairedHtml.includes('Repair saved'));
        assert.ok(repairedHtml.includes('Pressure-check the repaired link.'));
        assert.ok(repairedHtml.includes('concept-page-b2__repair'));
        assert.ok(repairedHtml.includes('Pressure-check this link'));
        assert.ok(repairedHtml.includes('data-active-entry-action="drill-gap"'));
        assert.ok(!repairedHtml.includes('concept-page-b2__repair-input'));
        assert.ok(!repairedHtml.includes('concept-page-b2__repair-save'));
        assert.ok(!repairedHtml.includes('Save this repair before you try from memory again.'));

        const checkedRepairHtml = renderActiveEntryHtml(
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
          },
          { repairCheckedThisSession: true }
        );
        assert.ok(checkedRepairHtml.includes('Repair checked'));
        assert.ok(checkedRepairHtml.includes('Repair checked for now.'));
        assert.ok(checkedRepairHtml.includes('Study note stays hidden for later reconstruction.'));
        assert.ok(checkedRepairHtml.includes('Rate this moment'));
        assert.ok(checkedRepairHtml.includes('data-feedback-rating'));
        assert.ok(checkedRepairHtml.includes('data-feedback-moment="repair checked"'));
        assert.ok(!checkedRepairHtml.includes('Pressure-check this link'));
        assert.ok(!checkedRepairHtml.includes('Study note stays hidden while you repair.'));

        const checkedRepairWithNextHtml = renderActiveEntryHtml(
          { id: 'repair', label: 'Repair' },
          0,
          [{ id: 'repair', label: 'Repair' }, { id: 'next-entry', label: 'Next entry' }],
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
          },
          { repairCheckedThisSession: true }
        );
        assert.ok(checkedRepairWithNextHtml.includes('Continue route'));
        assert.ok(checkedRepairWithNextHtml.includes('data-active-entry-id="next-entry"'));
        assert.ok(checkedRepairWithNextHtml.includes('data-active-entry-action="next-entry"'));
        assert.ok(!checkedRepairWithNextHtml.includes('Nearby entries'));

        const checkedNearbyHtml = renderActiveEntryHtml(
          { id: 'next-entry', label: 'Next entry' },
          1,
          [{ id: 'repair', label: 'Repair' }, { id: 'next-entry', label: 'Next entry' }],
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
              'next-entry': {
                attempts: [{
                  id: 'np1',
                  kind: 'cold',
                  at: '2026-05-15T10:20:00.000Z',
                  user_text: 'Next draft.',
                  classification: 'thin',
                  gaps: [{ mechanism: 'next gap', correction: 'Repair next.' }],
                  grader_version: 'qa',
                }],
                study_revealed_at: '2026-05-15T10:25:00.000Z',
              },
            },
          },
          { repairCheckedEntryIds: ['repair'] }
        );
        assert.ok(checkedNearbyHtml.includes('Nearby entries'));
        const checkedNearbyCompactHtml = checkedNearbyHtml.split(/\\s+/).join(' ');
        assert.ok(checkedNearbyCompactHtml.includes('<span>Repair</span> <span class="concept-page-b2__nearby-status">repair checked</span>'));
        assert.ok(!checkedNearbyCompactHtml.includes('<span>Repair</span> <span class="concept-page-b2__nearby-status">needs repair</span>'));

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

        const statefulStripHtml = renderConceptStripHtml(
          [
            { id: 'repair-node', label: 'Repair node' },
            { id: 'solid-node', label: 'Solid node' },
            { id: 'ready-node' },
          ],
          { id: 'ready-node' },
          2,
          {
            node_records: {
              'repair-node': {
                attempts: [{
                  id: 'thin-1',
                  at: '2026-05-15T10:00:00.000Z',
                  user_text: 'Thin answer.',
                  classification: 'thin',
                  gaps: [{ mechanism: 'missing link', correction: 'Name the missing link.' }],
                  grader_version: 'qa',
                }],
                repairs: [],
              },
              'solid-node': {
                attempts: [
                  { id: 'solid-1', at: '2026-05-14T10:00:00.000Z', user_text: 'first strong', classification: 'strong', gaps: [], grader_version: 'qa' },
                  { id: 'solid-2', at: '2026-05-15T10:30:00.000Z', user_text: 'second strong', classification: 'strong', gaps: [], grader_version: 'qa' },
                ],
                study_revealed_at: '2026-05-14T10:05:00.000Z',
                repairs: [],
              },
            },
          }
        );
        assert.ok(statefulStripHtml.includes('concept-strip__node--needs-repair'));
        assert.ok(statefulStripHtml.includes('concept-strip__node--solidified'));
        assert.ok(statefulStripHtml.includes('Third entry · 3 of 3'));
        assert.ok(statefulStripHtml.includes('aria-label="Third entry, ready to reconstruct, current"'));

        const fourthFallbackStripHtml = renderConceptStripHtml(
          [
            { id: 'first-node' },
            { id: 'second-node' },
            { id: 'third-node' },
            { id: 'fourth-node' },
          ],
          { id: 'fourth-node' },
          3,
          {}
        );
        assert.ok(fourthFallbackStripHtml.includes('Entry 4 · 4 of 4'));
        assert.ok(fourthFallbackStripHtml.includes('aria-label="Entry 4, locked, current"'));

        const emptyStripHtml = renderConceptStripHtml([], { id: 'core-thesis', label: 'Core thesis' }, 0);
        assert.ok(emptyStripHtml.includes('data-entry-id="core-thesis"'));
        assert.ok(emptyStripHtml.includes('core thesis, ready to reconstruct, current'));
        assert.ok(emptyStripHtml.includes('<text x="60" y="80">core thesis</text>'));
        """
    )
    assert result.returncode == 0, result.stderr
