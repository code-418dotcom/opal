/**
 * Opal AI Product Photography — Product Editor Metabox
 *
 * Handles the "Enhance with Opal" button in the WooCommerce product
 * editor sidebar: triggers processing, polls for completion, and
 * reloads the before/after gallery.
 *
 * Depends on the `opalMetabox` localized object:
 *   - ajaxUrl: WordPress admin-ajax.php URL
 *   - nonce:   Nonce (opal_process_nonce)
 *   - i18n:    Translated strings (processing, polling, complete, failed)
 *
 * Also reads `opalAdmin.restUrl` and `opalAdmin.restNonce` when available,
 * falling back to constructing the REST URL from ajaxUrl.
 *
 * @package OpalAIPhotography
 */

(function () {
	'use strict';

	/* ======================================================================
	   Configuration
	   ====================================================================== */

	/** Poll interval in milliseconds. */
	var POLL_INTERVAL = 5000;

	/** Maximum number of poll attempts before giving up. */
	var MAX_POLLS = 120; // 10 minutes at 5s intervals.

	/* ======================================================================
	   Helpers
	   ====================================================================== */

	/**
	 * Get the REST URL base.
	 * Prefer opalAdmin.restUrl; fall back to deriving from ajaxUrl.
	 *
	 * @returns {string}
	 */
	function getRestUrl() {
		if (typeof opalAdmin !== 'undefined' && opalAdmin.restUrl) {
			return opalAdmin.restUrl;
		}
		// Fallback: derive from ajaxUrl (…/wp-admin/admin-ajax.php → …/wp-json/opal/v1/).
		var ajaxUrl = opalMetabox.ajaxUrl || '';
		var base = ajaxUrl.replace('/wp-admin/admin-ajax.php', '/wp-json/opal/v1/');
		return base;
	}

	/**
	 * Get the REST nonce.
	 *
	 * @returns {string}
	 */
	function getRestNonce() {
		if (typeof opalAdmin !== 'undefined' && opalAdmin.restNonce) {
			return opalAdmin.restNonce;
		}
		return opalMetabox.nonce || '';
	}

	/**
	 * Make an authenticated REST request.
	 *
	 * @param {string} endpoint
	 * @param {Object} options
	 * @returns {Promise<Object>}
	 */
	function restFetch(endpoint, options) {
		options = options || {};
		var url = getRestUrl() + endpoint;
		var headers = Object.assign({
			'Content-Type': 'application/json',
			'X-WP-Nonce': getRestNonce(),
		}, options.headers || {});

		return fetch(url, Object.assign({}, options, { headers: headers }))
			.then(function (res) {
				if (!res.ok) {
					return res.json().then(function (err) {
						throw new Error(err.message || 'Request failed');
					});
				}
				return res.json();
			});
	}

	/* ======================================================================
	   Metabox Logic
	   ====================================================================== */

	/** @type {number|null} */
	var pollTimer = null;

	/** @type {number} */
	var pollCount = 0;

	/**
	 * Initialize the metabox functionality.
	 */
	function init() {
		var enhanceBtn = document.getElementById('opal-enhance-btn');
		if (!enhanceBtn) return;

		enhanceBtn.addEventListener('click', function () {
			startProcessing(enhanceBtn);
		});
	}

	/**
	 * Start processing for the current product.
	 *
	 * @param {HTMLButtonElement} btn - The enhance button.
	 */
	function startProcessing(btn) {
		var productId = parseInt(btn.getAttribute('data-product-id'), 10);
		if (!productId) return;

		// Gather options from the metabox checkboxes.
		var removeBg = document.getElementById('opal-opt-remove-bg');
		var genScene = document.getElementById('opal-opt-generate-scene');
		var upscale = document.getElementById('opal-opt-upscale');
		var scenePrompt = document.getElementById('opal-scene-prompt');

		var body = {
			product_id: productId,
			remove_background: removeBg ? removeBg.checked : true,
			generate_scene: genScene ? genScene.checked : false,
			upscale: upscale ? upscale.checked : true,
			scene_prompt: scenePrompt ? scenePrompt.value.trim() : '',
		};

		// Update UI: disable button, show spinner.
		btn.disabled = true;
		showStatus(opalMetabox.i18n.processing || 'Processing...');

		restFetch('process-product', {
			method: 'POST',
			body: JSON.stringify(body),
		})
			.then(function (data) {
				// The response should contain a job_id to poll.
				if (data.job_id) {
					showStatus(opalMetabox.i18n.polling || 'Waiting for results...');
					startPolling(data.job_id, productId, btn);
				} else {
					// If no job_id, assume synchronous completion.
					onComplete(btn);
				}
			})
			.catch(function (err) {
				onError(btn, err.message);
			});
	}

	/**
	 * Poll the batch status endpoint until the job is finished.
	 *
	 * @param {string}            jobId     - The Opal job ID.
	 * @param {number}            productId - The WC product ID.
	 * @param {HTMLButtonElement}  btn       - The enhance button.
	 */
	function startPolling(jobId, productId, btn) {
		pollCount = 0;

		if (pollTimer) clearInterval(pollTimer);

		pollTimer = setInterval(function () {
			pollCount++;

			if (pollCount > MAX_POLLS) {
				clearInterval(pollTimer);
				pollTimer = null;
				onError(btn, 'Processing timed out. Check the Opal dashboard for status.');
				return;
			}

			restFetch('batch/' + jobId + '/status')
				.then(function (data) {
					var status = data.status || '';

					if (status === 'completed') {
						clearInterval(pollTimer);
						pollTimer = null;
						onComplete(btn);
					} else if (status === 'failed') {
						clearInterval(pollTimer);
						pollTimer = null;
						onError(btn, 'Processing failed. Please try again.');
					}
					// Otherwise keep polling.
				})
				.catch(function () {
					// Network error during polling; keep retrying.
				});
		}, POLL_INTERVAL);
	}

	/**
	 * Handle successful processing completion.
	 *
	 * @param {HTMLButtonElement} btn
	 */
	function onComplete(btn) {
		showStatus(opalMetabox.i18n.complete || 'Enhancement complete!', 'success');
		btn.disabled = false;

		// Reload the metabox gallery after a short pause.
		setTimeout(function () {
			window.location.reload();
		}, 1500);
	}

	/**
	 * Handle a processing error.
	 *
	 * @param {HTMLButtonElement} btn
	 * @param {string}           message
	 */
	function onError(btn, message) {
		showStatus((opalMetabox.i18n.failed || 'Processing failed.') + ' ' + message, 'error');
		btn.disabled = false;
	}

	/**
	 * Show or update the processing status indicator.
	 *
	 * @param {string} text  - Status message.
	 * @param {string} type  - 'processing' (default), 'success', or 'error'.
	 */
	function showStatus(text, type) {
		type = type || 'processing';

		var statusWrap = document.getElementById('opal-processing-status');
		var statusText = document.getElementById('opal-status-text');
		var spinner = statusWrap ? statusWrap.querySelector('.spinner') : null;

		if (!statusWrap) return;

		statusWrap.style.display = 'block';
		if (statusText) statusText.textContent = text;

		if (spinner) {
			if (type === 'processing') {
				spinner.classList.add('is-active');
				spinner.style.display = '';
			} else {
				spinner.classList.remove('is-active');
				spinner.style.display = 'none';
			}
		}

		// Color feedback.
		if (statusText) {
			switch (type) {
				case 'success':
					statusText.style.color = '#00a32a';
					break;
				case 'error':
					statusText.style.color = '#d63638';
					break;
				default:
					statusText.style.color = '';
			}
		}
	}

	/* ======================================================================
	   Bootstrap
	   ====================================================================== */

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();
