import test from 'node:test';
import assert from 'node:assert/strict';

const capturedEvents = [];

globalThis.window = {
    location: { search: '' },
    posthog: {
        capture(...args) {
            capturedEvents.push(args);
        }
    }
};

const { capture } = await import('../static/js/analytics/analytics.js');

test('only explicit controlled verification pages suppress analytics', () => {
    const cases = [
        {
            search: '?verification=controlled',
            event: 'controlled_verification',
            captured: false
        },
        {
            search: '',
            event: 'direct_visit',
            captured: true
        },
        {
            search: '?source=guide_reaction',
            event: 'guide_visit',
            captured: true
        },
        {
            search: '?source=student_invite',
            event: 'student_invite',
            captured: true
        },
        {
            search: '?verification=controlled&source=student_invite',
            event: 'student_invite_with_verification_flag',
            captured: true
        },
        {
            search: '?verification=unexpected',
            event: 'unrecognized_verification_value',
            captured: true
        }
    ];

    for (const scenario of cases) {
        const countBeforeCapture = capturedEvents.length;
        window.location.search = scenario.search;

        capture(scenario.event, { entry_source: 'bounded_test_value' });

        assert.equal(
            capturedEvents.length,
            countBeforeCapture + Number(scenario.captured),
            scenario.event
        );
    }

    assert.deepEqual(
        capturedEvents.map(([event]) => event),
        cases.filter(({ captured }) => captured).map(({ event }) => event)
    );
    assert.ok(
        capturedEvents.every(([, properties]) => (
            Object.keys(properties).length === 1 &&
            properties.entry_source === 'bounded_test_value'
        ))
    );
});
