/**
 * Opal AI Product Photography — Frontend A/B Test Tracking
 *
 * Fires a non-blocking view tracking call on product pages that have
 * an active A/B test. Uses the Beacon API for reliability; falls back
 * to fetch() if Beacon is unavailable.
 *
 * This script expects data attributes on the body or a container element:
 *   data-opal-test-id   — The A/B test ID
 *   data-opal-variant   — The assigned variant ('A' or 'B')
 *
 * It also reads from the inline `opalTracking` global (if set by PHP):
 *   opalTracking.restUrl   — REST endpoint URL
 *   opalTracking.nonce     — WP REST nonce
 *   opalTracking.tests     — Array of {test_id, variant}
 *
 * Only fires once per page load (debounced via a module-level flag).
 *
 * @package OpalAIPhotography
 */

(function () {
	'use strict';

	/** Prevent duplicate firing on the same page load. */
	var hasFired = false;

	/**
	 * Send a tracking event.
	 *
	 * @param {string} url       - Full REST endpoint URL.
	 * @param {Object} payload   - JSON body.
	 * @param {string} nonce     - WP REST nonce.
	 */
	function sendTrack(url, payload, nonce) {
		var body = JSON.stringify(payload);

		// Prefer Beacon API for non-blocking, page-unload-safe delivery.
		if (navigator.sendBeacon) {
			var blob = new Blob([body], { type: 'application/json' });
			// Note: Beacon does not support custom headers, so we append
			// the nonce as a query parameter as a fallback for verification.
			var beaconUrl = url + (url.indexOf('?') === -1 ? '?' : '&') + '_wpnonce=' + encodeURIComponent(nonce);
			var sent = navigator.sendBeacon(beaconUrl, blob);
			if (sent) return;
		}

		// Fallback: fetch with keepalive.
		try {
			fetch(url, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-WP-Nonce': nonce,
				},
				body: body,
				keepalive: true,
				credentials: 'same-origin',
			}).catch(function () {
				// Silently ignore tracking failures.
			});
		} catch (e) {
			// Ignore.
		}
	}

	/**
	 * Collect tracking data and fire view events.
	 */
	function trackViews() {
		if (hasFired) return;
		hasFired = true;

		var tests = [];
		var restUrl = '';
		var nonce = '';

		// Source 1: global opalTracking object (set by PHP inline script).
		if (typeof opalTracking !== 'undefined' && opalTracking.tests) {
			tests = opalTracking.tests;
			restUrl = opalTracking.restUrl || '';
			nonce = opalTracking.nonce || '';
		}

		// Source 2: data attributes on elements with [data-opal-test-id].
		if (!tests.length) {
			var elements = document.querySelectorAll('[data-opal-test-id]');
			elements.forEach(function (el) {
				var testId = parseInt(el.getAttribute('data-opal-test-id'), 10);
				var variant = (el.getAttribute('data-opal-variant') || '').toUpperCase();
				if (testId && (variant === 'A' || variant === 'B')) {
					tests.push({ test_id: testId, variant: variant });
				}
			});

			// Try to find the REST URL from a meta tag or known patterns.
			var linkTag = document.querySelector('link[rel="https://api.w.org/"]');
			if (linkTag) {
				restUrl = linkTag.getAttribute('href') + 'opal/v1/track-view';
			}
		}

		if (!tests.length || !restUrl) return;

		// Fire one tracking call per test.
		tests.forEach(function (item) {
			sendTrack(restUrl, {
				test_id: item.test_id,
				variant: item.variant,
				event_type: 'view',
			}, nonce);
		});
	}

	/* ======================================================================
	   Bootstrap — fire as early as possible without blocking rendering.
	   ====================================================================== */

	if (document.readyState === 'complete' || document.readyState === 'interactive') {
		// DOM already ready; schedule on next microtask to avoid blocking.
		setTimeout(trackViews, 0);
	} else {
		document.addEventListener('DOMContentLoaded', trackViews);
	}
})();
