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


def test_learner_state_and_due_desk_browser_contracts(
    clean_page: Page, base_url: str, captured: dict
) -> None:
    """Exercise Linear Desk due surfaces + learner-state sync under V8 coverage."""
    _enter_app_shell_as_guest(clean_page, base_url)

    result = clean_page.evaluate(
        """async () => {
          const assert = (cond, msg) => { if (!cond) throw new Error(msg); };
          const sync = await import('/js/learner-state-sync.js?v=3');
          const due = await import('/js/due-for-spaced.js?v=7');
          const auth = await import('/js/auth.js?v=5');

          // defaultStorage catch when localStorage access throws
          const lsDesc = Object.getOwnPropertyDescriptor(window, 'localStorage');
          Object.defineProperty(window, 'localStorage', {
            configurable: true,
            get() { throw new Error('storage-denied'); },
          });
          try {
            const denied = sync.readLocalLearnerState();
            assert(Array.isArray(denied.concepts) && denied.concepts.length === 0, 'denied storage');
          } finally {
            Object.defineProperty(window, 'localStorage', lsDesc);
          }

          // Storage helpers + parseJson catch + conceptRecency zero + collectLocalTrainingMap branches
          const mem = new Map();
          const storage = {
            getItem(key) { return mem.has(key) ? mem.get(key) : null; },
            setItem(key, value) { mem.set(key, String(value)); },
            removeItem(key) { mem.delete(key); },
            key(i) { return [...mem.keys()][i] || null; },
            get length() { return mem.size; },
          };
          storage.setItem('learnops_concepts', '{not-json');
          assert(sync.readLocalLearnerState(storage).concepts.length === 0, 'bad json concepts');
          storage.setItem('learnops_concepts', JSON.stringify([{
            id: 'c1',
            name: 'Thermostat',
            // no date fields → conceptRecency returns 0
          }]));
          storage.setItem('socratink:training:v1:c1', JSON.stringify({
            concept_id: 'c1',
            schema_version: 1,
            grounding: 'ungrounded',
            node_records: {
              sensor: {
                attempts: [{
                  id: 'a1',
                  at: '2026-07-07T00:00:00.000Z',
                  user_text: 'strong',
                  classification: 'strong',
                  gaps: [],
                  grader_version: 'test',
                }],
                repairs: [{ id: 'r1', at: '2026-07-07T00:05:00.000Z' }],
                study_revealed_at: '2026-07-07T00:10:00.000Z',
              },
            },
          }));

          assert(Object.keys(sync.collectLocalTrainingMap(null)).length === 0, 'null storage map');
          assert(Object.keys(sync.collectLocalTrainingMap({})).length === 0, 'empty object map');
          assert(
            Object.keys(sync.collectLocalTrainingMap({ getItem() { return null; } })).length === 0,
            'getItem-only storage falls through',
          );

          const local = sync.readLocalLearnerState(storage);
          assert(local.concepts.length === 1, 'read local concepts');
          assert(local.training.c1, 'read local training');

          const remote = {
            concepts: [{
              id: 'c1',
              name: 'Remote',
              updated_at: '2026-07-07T12:00:00.000Z',
            }, { id: 'c2', name: 'Only remote' }],
            training: {
              c1: {
                concept_id: 'c1',
                schema_version: 1,
                grounding: 'ungrounded',
                node_records: {
                  sensor: {
                    attempts: [{
                      id: 'a-remote',
                      at: '2026-07-06T00:00:00.000Z',
                      user_text: 'remote',
                      classification: 'partial',
                      gaps: [],
                      grader_version: 'test',
                    }],
                    repairs: [],
                    study_revealed_at: '2026-07-06T00:10:00.000Z',
                  },
                },
              },
            },
          };
          // Local has no dates; remote has updated_at → remote wins on recency 0 vs finite
          const merged = sync.mergeLearnerState(local, remote);
          assert(merged.concepts.length === 2, 'merge concepts');
          assert(merged.training.c1.node_records.sensor.attempts.length === 2, 'union attempts');
          sync.writeLocalLearnerState(merged, storage);

          let putCount = 0;
          const fetchImpl = async (url, opts = {}) => {
            if (opts.method === 'GET' || !opts.method) {
              return {
                status: 404,
                ok: false,
                async json() { return {}; },
              };
            }
            putCount += 1;
            return { status: 200, ok: true, async json() { return { status: 'ok' }; } };
          };
          const guest = await sync.hydrateAndSyncLearnerState({
            storage,
            fetchImpl,
            isIdentified: false,
          });
          assert(guest.synced === false, 'guest hydrate skipped');
          const hydrated = await sync.hydrateAndSyncLearnerState({
            storage,
            fetchImpl,
            isIdentified: true,
          });
          assert(hydrated.synced === true, 'identified hydrate');
          assert(putCount === 1, 'hydrate put once');

          // GET 200 path + PUT/GET failure throws
          const remoteOk = await sync.fetchRemoteLearnerState({
            fetchImpl: async () => ({
              status: 200,
              ok: true,
              async json() { return remote; },
            }),
          });
          assert(remoteOk.concepts.length === 2, 'get 200 body');
          let getFailed = false;
          try {
            await sync.fetchRemoteLearnerState({
              fetchImpl: async () => ({ status: 500, ok: false, async json() { return {}; } }),
            });
          } catch (err) {
            getFailed = String(err.message).includes('learner-state-get-failed:500');
          }
          assert(getFailed, 'get non-ok throws');
          let putFailed = false;
          try {
            await sync.putRemoteLearnerState(merged, {
              fetchImpl: async () => ({ status: 503, ok: false, async json() { return {}; } }),
            });
          } catch (err) {
            putFailed = String(err.message).includes('learner-state-put-failed:503');
          }
          assert(putFailed, 'put non-ok throws');

          const pushed = await sync.pushLocalLearnerState({
            storage,
            fetchImpl,
            isIdentified: true,
          });
          assert(pushed.pushed === true, 'push local');
          const skippedPush = await sync.pushLocalLearnerState({
            storage,
            fetchImpl,
            isIdentified: false,
          });
          assert(skippedPush.pushed === false, 'guest push skipped');

          // Due surfaces: route IDs + labelForNode fallbacks
          assert(
            JSON.stringify(due.collectDrillableNodeIds({
              metadata: { id: 'core' },
              backbone: [{ id: 'bb1' }],
              clusters: [{ id: 'cl1', subnodes: [{ id: 'sn1', learner_scaffold: { task_label: 'S' } }] }],
            })) === JSON.stringify(['sn1']),
            'cluster scaffold wins',
          );
          assert(due.renderReadyFilterHtml({ count: 0 }) === '', 'filter hidden at zero');
          const filterHtml = due.renderReadyFilterHtml({ count: 1, active: true });
          assert(filterHtml.includes('Due'), 'Due label');
          assert(filterHtml.includes('is-active'), 'active filter');
          assert(
            due.collectDrillableNodeIds({ metadata: { label: 'Only core' }, backbone: [], clusters: [] })
              .join(',') === 'core-thesis',
            'empty graph falls back to core-thesis',
          );
          assert(
            due.labelForNode({ metadata: { label: 'Thesis label' }, backbone: [], clusters: [] }, 'core-thesis')
              === 'Thesis label',
            'core-thesis label from metadata.label',
          );
          assert(
            due.labelForNode({ metadata: { name: 'Thesis name' }, backbone: [], clusters: [] }, 'core-thesis')
              === 'Thesis name',
            'core-thesis label from metadata.name',
          );
          assert(
            due.labelForNode({ metadata: {}, backbone: [], clusters: [] }, 'core-thesis') === 'Core thesis',
            'core-thesis default label',
          );
          assert(due.labelForNode({ backbone: [], clusters: [] }, 'unknown-node') === 'unknown-node', 'unknown id');
          assert(
            due.listDueForSpaced({
              concepts: [{ id: 'bad', graphData: '{not-json' }],
              trainingByConceptId: {},
            }).length === 0,
            'parseGraphData catch',
          );
          const selection = due.renderDueSelectionHtml([{
            concept_id: 'c1',
            node_id: 'sensor',
            node_label: 'Sensor reading',
            last_attempt_at: '2026-07-07T00:00:00.000Z',
          }]);
          assert(selection.includes('data-node-id="sensor"'), 'selection node id');
          assert(selection.includes('Up next from memory'), 'selection kicker');
          assert(due.renderDueSelectionHtml([]) === '', 'empty selection');

          // Seed desk with due training and exercise UI handlers.
          const now = Date.now();
          const eighteenHoursAgo = new Date(now - 19 * 60 * 60 * 1000).toISOString();
          localStorage.setItem('learnops_concepts', JSON.stringify([{
            id: 'due-c1',
            name: 'Due Session',
            state: 'solidified',
            createdAt: now,
            graphData: JSON.stringify({
              metadata: { id: 'core', label: 'Feedback loop' },
              backbone: [
                { id: 'sensor', label: 'Sensor reading' },
                { id: 'actuator', label: 'Actuator' },
              ],
              clusters: [],
            }),
          }, {
            id: 'fresh-c2',
            name: 'Fresh Session',
            state: 'growing',
            createdAt: now,
            graphData: JSON.stringify({
              metadata: { id: 'core', label: 'Fresh model' },
              backbone: [{ id: 'fresh-node', label: 'Fresh node' }],
              clusters: [],
            }),
          }]));
          localStorage.setItem('learnops_active', 'due-c1');
          localStorage.setItem('socratink:training:v1:due-c1', JSON.stringify({
            concept_id: 'due-c1',
            schema_version: 1,
            grounding: 'ungrounded',
            node_records: {
              sensor: {
                attempts: [{
                  id: 'a-due',
                  at: eighteenHoursAgo,
                  user_text: 'strong spaced',
                  classification: 'strong',
                  gaps: [],
                  grader_version: 'test',
                }],
                repairs: [],
                study_revealed_at: eighteenHoursAgo,
              },
            },
          }));
          window.App.showDashboard();
          return { ok: true, authReady: typeof auth.invalidateAuthSession === 'function' };
        }"""
    )
    assert result["ok"] is True

    expect(clean_page.locator("#desk-ready-filter")).to_be_visible()
    expect(clean_page.locator("#grid-container .tile-group.is-due .concept-pin-due-ring")).to_be_attached()
    clean_page.locator("#desk-ready-filter").click()
    expect(clean_page.locator("#desk-ready-filter")).to_have_attribute("aria-pressed", "true")
    expect(clean_page.locator("#grid-container")).to_have_class(re.compile(r"is-ready-filtered"))

    clean_page.evaluate(
        """() => {
          document.documentElement.dataset.theme = 'dark';
          document.body.dataset.theme = 'dark';
          document.body.classList.add('night');
        }"""
    )
    filtered_occupied = clean_page.locator(
        "#grid-container .tile-group.is-filtered-out:not(.empty)"
    )
    expect(filtered_occupied).to_have_count(1)
    expect(filtered_occupied).to_have_css("filter", "grayscale(0.45)")
    expect(filtered_occupied).to_have_css("opacity", "0.16")

    clean_page.emulate_media(reduced_motion="reduce")
    expect(
        clean_page.locator("#grid-container .tile-group.is-due .concept-pin-due-ring")
    ).to_have_css("animation-name", "none")

    # Filtered empty tiles must no-op selectTile.
    clean_page.evaluate("window.App.selectTile(8)")
    expect(clean_page.locator("#desk-due-selection-host .desk-due-selection__action")).to_be_visible()
    clean_page.locator("#desk-due-selection-host .desk-due-selection__action").click()
    expect(clean_page.locator("#map-view")).to_be_visible()
    expect(clean_page.locator("#map-content h2").first).to_contain_text("Sensor reading")

    # Return to desk, then clear concepts without renderGrid so iso syncTile
    # removes the due-ring from a still-populated pin.
    clean_page.evaluate(
        """() => {
          window.App.showDashboard();
        }"""
    )
    expect(clean_page.locator("#desk-ready-filter")).to_be_visible()
    clean_page.evaluate(
        """() => {
          localStorage.setItem('learnops_concepts', JSON.stringify([]));
          localStorage.removeItem('learnops_active');
          // Same-tab storage events do not fire; focus triggers iso refresh.
          window.dispatchEvent(new Event('focus'));
        }"""
    )
    expect(clean_page.locator("#grid-container .concept-pin-due-ring")).to_have_count(0)

    # App sync wrappers: guest, identified success, identified error.
    # Also hit saveConcepts / trainingStore hooks / deleteConcept due-refresh paths.
    clean_page.evaluate(
        """async () => {
          const auth = await import('/js/auth.js?v=5');
          await window.App.syncLearnerStateIfIdentified();
          await window.App.pushLearnerStateIfIdentified();

          const originalFetch = window.fetch;
          auth.invalidateAuthSession();
          window.fetch = async (url, opts = {}) => {
            const href = String(url);
            if (href.includes('/api/me')) {
              return {
                ok: true,
                status: 200,
                async json() {
                  return {
                    auth_enabled: true,
                    authenticated: true,
                    guest_mode: false,
                    user: { id: 'user-1', email: 'a@b.c' },
                  };
                },
              };
            }
            if (href.includes('/api/learner-state')) {
              if ((opts.method || 'GET') === 'PUT') {
                return { ok: true, status: 200, async json() { return { status: 'ok' }; } };
              }
              return {
                ok: true,
                status: 200,
                async json() {
                  return { schema_version: 1, concepts: [], training: {}, updated_at: new Date().toISOString() };
                },
              };
            }
            return originalFetch(url, opts);
          };
          try {
            const synced = await window.App.syncLearnerStateIfIdentified();
            if (!synced) throw new Error('expected identified sync');
            await window.App.pushLearnerStateIfIdentified();

            // Keep the identified fetch mock while exercising saveConcepts /
            // scheduleLearnerStatePush so the debounced PUT does not 401.
            const conceptId = 'hook-c1';
            localStorage.setItem('learnops_concepts', JSON.stringify([{
              id: conceptId,
              name: 'Hook Session',
              state: 'solidified',
              createdAt: Date.now(),
              graphData: JSON.stringify({
                metadata: { id: 'core', label: 'Core' },
                backbone: [{ id: 'sensor', label: 'Sensor' }],
                clusters: [],
              }),
            }]));
            localStorage.setItem('learnops_active', conceptId);
            window.App.showDashboard();
            await window.App.seedLocalQaConcept();

            const originalConfirm = window.confirm;
            window.confirm = () => true;
            try {
              window.App.deleteConcept(conceptId);
              localStorage.setItem('learnops_concepts', JSON.stringify([{
                id: 'hook-c2',
                name: 'Second',
                state: 'primed',
                createdAt: Date.now(),
                graphData: JSON.stringify({ metadata: { label: 'X' }, backbone: [], clusters: [] }),
              }]));
              localStorage.setItem('learnops_active', 'hook-c2');
              window.App.showDashboard();
              window.App.deleteConcept('hook-c2');
            } finally {
              window.confirm = originalConfirm;
            }
            await new Promise((r) => setTimeout(r, 900));
          } finally {
            window.fetch = originalFetch;
            auth.invalidateAuthSession();
          }

          auth.invalidateAuthSession();
          window.fetch = async (url) => {
            if (String(url).includes('/api/me')) {
              return {
                ok: true,
                status: 200,
                async json() {
                  return {
                    auth_enabled: true,
                    authenticated: true,
                    guest_mode: false,
                    user: { id: 'user-1', email: 'a@b.c' },
                  };
                },
              };
            }
            throw new Error('forced-sync-failure');
          };
          try {
            await window.App.syncLearnerStateIfIdentified();
            await window.App.pushLearnerStateIfIdentified();
          } finally {
            window.fetch = originalFetch;
            auth.invalidateAuthSession();
          }
        }"""
    )

    clean_page.evaluate(
        """() => {
          localStorage.setItem('learnops_concepts', JSON.stringify([]));
          localStorage.removeItem('learnops_active');
          window.App.showDashboard();
        }"""
    )
    expect(clean_page.locator("#desk-title")).to_be_attached()

    assert captured["console_errors"] == []
