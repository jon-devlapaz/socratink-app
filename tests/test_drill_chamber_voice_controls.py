"""Drill chamber voice-control tests."""

from __future__ import annotations

import shutil

import pytest

from tests._helpers.node_runner import run_node_module


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_drill_chamber_voice_controls_use_loop_style_browser_apis() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';

        const nodes = new Map();
        const storage = new Map([
          ['socratink.loop.micInput', '1'],
          ['socratink.loop.tutorVoice', '1'],
        ]);
        let lastRecognition = null;
        const spoken = [];

        function makeNode(id) {
          const classes = new Set();
          return {
            id,
            hidden: true,
            disabled: false,
            value: '',
            textContent: '',
            innerHTML: '',
            placeholder: '',
            dataset: {},
            listeners: {},
            isConnected: true,
            parentNode: null,
            classList: {
              add(name) { classes.add(name); },
              remove(name) { classes.delete(name); },
              toggle(name, enabled) { enabled ? classes.add(name) : classes.delete(name); },
              contains(name) { return classes.has(name); },
            },
            appendChild(child) {
              child.parentNode = this;
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
            contains(node) {
              return node === this;
            },
            insertAdjacentHTML(_position, html) {
              this.insertedHtml = html;
            },
            querySelectorAll() {
              return [];
            },
            remove() {
              this.removed = true;
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

        class FakeRecognition {
          constructor() {
            this.listeners = {};
            this.startCalls = 0;
            this.stopCalls = 0;
            this.throwOnStart = false;
            lastRecognition = this;
          }
          addEventListener(type, handler) {
            this.listeners[type] = handler;
          }
          start() {
            this.startCalls += 1;
            if (this.throwOnStart) throw new Error('already started');
            this.listeners.start?.({});
          }
          stop() {
            this.stopCalls += 1;
            this.listeners.end?.({});
          }
          dispatch(type, event) {
            this.listeners[type]?.(event);
          }
        }

        globalThis.localStorage = {
          getItem(key) { return storage.has(key) ? storage.get(key) : null; },
          setItem(key, value) { storage.set(key, value); },
        };
        Object.defineProperty(globalThis, 'navigator', {
          value: { language: 'en-US' },
          configurable: true,
        });
        globalThis.window = {
          SpeechRecognition: FakeRecognition,
          speechSynthesis: {
            cancel() { spoken.push('cancel'); },
            speak(utterance) { spoken.push(utterance.text); },
          },
          SpeechSynthesisUtterance: class {
            constructor(text) { this.text = text; }
          },
        };
        globalThis.document = {
          body: {
            classList: {
              add() {},
              remove() {},
            },
          },
          documentElement: {},
          activeElement: null,
          createElement(tagName) {
            return makeNode(tagName);
          },
          getElementById(id) {
            return nodes.get(id) || null;
          },
        };
        globalThis.requestAnimationFrame = (callback) => callback();
        globalThis.setTimeout = (callback) => {
          callback();
          return 0;
        };

        for (const id of [
          'drill-chamber-view',
          'chamber-concept-name',
          'chamber-entry-name',
          'chamber-question',
          'chamber-active',
          'chamber-composer',
          'chamber-send',
          'chamber-mic',
          'chamber-tutor-voice',
          'chamber-voice-status',
          'chamber-exit',
          'chamber-chat-log',
        ]) {
          nodes.set(id, makeNode(id));
        }

        await import('./public/js/drill-chamber.js');

        window.DrillChamber.show({
          conceptName: 'Concept',
          entryName: 'Entry',
          question: 'What must happen first?',
        });

        assert.equal(nodes.get('chamber-mic').hidden, false);
        assert.equal(nodes.get('chamber-tutor-voice').hidden, false);
        assert.deepEqual(spoken, ['cancel', 'What must happen first?']);

        nodes.get('chamber-composer').value = 'base';
        nodes.get('chamber-mic').click();
        assert.equal(lastRecognition.startCalls, 1);
        assert.equal(nodes.get('chamber-mic')['aria-pressed'], 'true');
        assert.equal(nodes.get('chamber-mic')['aria-label'], 'Stop dictating answer');
        assert.equal(nodes.get('chamber-voice-status').textContent, 'listening');
        lastRecognition.dispatch('result', {
          results: [
            [{ transcript: ' ions cross' }],
            [{ transcript: ' the membrane' }],
          ],
        });
        assert.equal(nodes.get('chamber-composer').value, 'base ions cross the membrane');

        nodes.get('chamber-mic').click();
        assert.equal(lastRecognition.stopCalls, 1);
        assert.equal(nodes.get('chamber-mic')['aria-pressed'], 'false');
        assert.equal(nodes.get('chamber-mic')['aria-label'], 'Dictate answer');
        assert.equal(nodes.get('chamber-voice-status').textContent, '');
        assert.equal(nodes.get('chamber-composer').focused, true);

        nodes.get('chamber-mic').click();
        lastRecognition.dispatch('error', { error: 'no-speech' });
        assert.equal(nodes.get('chamber-mic')['aria-pressed'], 'false');
        assert.equal(nodes.get('chamber-voice-status').textContent, 'voice input: no-speech');

        nodes.get('chamber-mic').disabled = true;
        nodes.get('chamber-mic').click();
        assert.equal(lastRecognition.startCalls, 2);
        nodes.get('chamber-mic').disabled = false;
        lastRecognition.throwOnStart = true;
        nodes.get('chamber-mic').click();
        assert.equal(nodes.get('chamber-mic')['aria-pressed'], 'false');

        nodes.get('chamber-tutor-voice').click();
        assert.equal(storage.get('socratink.loop.tutorVoice'), '0');
        assert.equal(nodes.get('chamber-tutor-voice')['aria-pressed'], 'false');
        nodes.get('chamber-tutor-voice').click();
        assert.equal(storage.get('socratink.loop.tutorVoice'), '1');
        assert.equal(nodes.get('chamber-tutor-voice')['aria-label'], 'Tutor voice on');
        assert.ok(spoken.includes('What must happen first?'));
        """
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_drill_chamber_voice_controls_hide_when_browser_apis_missing() -> None:
    result = run_node_module(
        """
        import assert from 'node:assert/strict';

        const nodes = new Map();

        function makeNode(id) {
          const classes = new Set();
          return {
            id,
            hidden: true,
            disabled: false,
            value: '',
            textContent: '',
            innerHTML: '',
            placeholder: '',
            dataset: {},
            listeners: {},
            isConnected: true,
            classList: {
              add(name) { classes.add(name); },
              remove(name) { classes.delete(name); },
              toggle(name, enabled) { enabled ? classes.add(name) : classes.delete(name); },
              contains(name) { return classes.has(name); },
            },
            appendChild(child) { this.lastChild = child; },
            addEventListener(type, handler) { this.listeners[type] = handler; },
            focus() { this.focused = true; },
            insertAdjacentHTML(_position, html) { this.insertedHtml = html; },
            querySelectorAll() { return []; },
            remove() { this.removed = true; },
            removeAttribute(name) { delete this[name]; },
            scrollIntoView() { this.scrolled = true; },
            setAttribute(name, value) { this[name] = value; },
          };
        }

        globalThis.localStorage = {
          getItem() { throw new Error('storage denied'); },
          setItem() { throw new Error('storage denied'); },
        };
        Object.defineProperty(globalThis, 'navigator', {
          value: { language: '' },
          configurable: true,
        });
        globalThis.window = {};
        globalThis.document = {
          body: {
            classList: {
              add() {},
              remove() {},
            },
          },
          documentElement: {},
          activeElement: null,
          createElement(tagName) { return makeNode(tagName); },
          getElementById(id) { return nodes.get(id) || null; },
        };
        globalThis.requestAnimationFrame = (callback) => callback();
        globalThis.setTimeout = (callback) => {
          callback();
          return 0;
        };

        for (const id of [
          'drill-chamber-view',
          'chamber-concept-name',
          'chamber-entry-name',
          'chamber-question',
          'chamber-active',
          'chamber-composer',
          'chamber-send',
          'chamber-mic',
          'chamber-tutor-voice',
          'chamber-voice-status',
          'chamber-exit',
          'chamber-chat-log',
        ]) {
          nodes.set(id, makeNode(id));
        }

        await import('./public/js/drill-chamber.js');

        window.DrillChamber.show({
          conceptName: 'Concept',
          entryName: 'Entry',
          question: 'What must happen first?',
        });

        assert.equal(nodes.get('chamber-mic').hidden, true);
        assert.equal(nodes.get('chamber-tutor-voice').hidden, true);
        """
    )
    assert result.returncode == 0, result.stderr
