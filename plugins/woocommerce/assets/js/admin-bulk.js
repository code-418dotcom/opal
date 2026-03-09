/**
 * Opal AI Product Photography — Bulk Processing Page
 *
 * Handles product grid display, selection, category filtering,
 * bulk processing triggers, and progress polling.
 *
 * Depends on the `opalAdmin` localized object:
 *   - restUrl:   WP REST base URL (e.g. /wp-json/opal/v1/)
 *   - restNonce: REST nonce for X-WP-Nonce header
 *   - nonce:     Admin AJAX nonce
 *   - i18n:      Translated strings
 *
 * @package OpalAIPhotography
 */

(function () {
	'use strict';

	/* ======================================================================
	   State
	   ====================================================================== */

	let selectedIds = new Set();
	let currentBatchId = null;
	let pollTimer = null;

	/* ======================================================================
	   DOM References
	   ====================================================================== */

	const selectAllCheckbox = document.getElementById('opal-select-all');
	const selectAllTop = document.getElementById('opal-select-all-top');
	const startBtn = document.getElementById('opal-start-bulk');
	const progressWrap = document.getElementById('opal-bulk-progress');
	const progressFill = document.getElementById('opal-progress-fill');
	const progressText = document.getElementById('opal-progress-text');

	/* ======================================================================
	   Helpers
	   ====================================================================== */

	/**
	 * Make an authenticated REST request.
	 *
	 * @param {string} endpoint - Relative to opalAdmin.restUrl.
	 * @param {Object} options  - fetch() options.
	 * @returns {Promise<Object>}
	 */
	function restFetch(endpoint, options = {}) {
		const url = opalAdmin.restUrl + endpoint;
		const headers = Object.assign({
			'Content-Type': 'application/json',
			'X-WP-Nonce': opalAdmin.restNonce,
		}, options.headers || {});

		return fetch(url, Object.assign({}, options, { headers }))
			.then(function (res) {
				if (!res.ok) {
					return res.json().then(function (err) {
						throw new Error(err.message || 'Request failed');
					});
				}
				return res.json();
			});
	}

	/**
	 * Show a toast notification.
	 *
	 * @param {string} message - The message text.
	 * @param {string} type    - 'success', 'error', or 'info'.
	 */
	function showToast(message, type) {
		type = type || 'info';

		// Remove any existing toasts.
		var existing = document.querySelectorAll('.opal-toast');
		existing.forEach(function (el) { el.remove(); });

		var toast = document.createElement('div');
		toast.className = 'opal-toast opal-toast-' + type;
		toast.innerHTML =
			'<span>' + escapeHtml(message) + '</span>' +
			'<button class="opal-toast-dismiss" type="button">&times;</button>';

		document.body.appendChild(toast);

		// Trigger reflow then show.
		toast.offsetHeight; // eslint-disable-line no-unused-expressions
		toast.classList.add('visible');

		toast.querySelector('.opal-toast-dismiss').addEventListener('click', function () {
			toast.classList.remove('visible');
			setTimeout(function () { toast.remove(); }, 300);
		});

		// Auto-dismiss after 6 seconds.
		setTimeout(function () {
			if (toast.parentNode) {
				toast.classList.remove('visible');
				setTimeout(function () { toast.remove(); }, 300);
			}
		}, 6000);
	}

	/**
	 * Escape HTML entities in a string.
	 *
	 * @param {string} str
	 * @returns {string}
	 */
	function escapeHtml(str) {
		var div = document.createElement('div');
		div.textContent = str;
		return div.innerHTML;
	}

	/**
	 * Update the selection count display.
	 */
	function updateSelectionCount() {
		var countEl = document.querySelector('.opal-bulk-count');
		if (countEl) {
			countEl.textContent = selectedIds.size + ' selected';
		}

		if (startBtn) {
			startBtn.disabled = selectedIds.size === 0;
		}
	}

	/* ======================================================================
	   Product Selection
	   ====================================================================== */

	/**
	 * Initialize all product row checkboxes.
	 */
	function initProductCheckboxes() {
		var checkboxes = document.querySelectorAll('input[name="product_ids[]"]');

		checkboxes.forEach(function (cb) {
			cb.addEventListener('change', function () {
				var productId = parseInt(this.value, 10);
				var row = this.closest('tr') || this.closest('.opal-product-item');

				if (this.checked) {
					selectedIds.add(productId);
					if (row) row.classList.add('selected');
				} else {
					selectedIds.delete(productId);
					if (row) row.classList.remove('selected');
				}

				updateSelectionCount();
				syncSelectAll();
			});
		});
	}

	/**
	 * Sync the "select all" checkboxes with individual checkbox state.
	 */
	function syncSelectAll() {
		var checkboxes = document.querySelectorAll('input[name="product_ids[]"]');
		var allChecked = checkboxes.length > 0 &&
			Array.from(checkboxes).every(function (cb) { return cb.checked; });

		if (selectAllCheckbox) selectAllCheckbox.checked = allChecked;
		if (selectAllTop) selectAllTop.checked = allChecked;
	}

	/**
	 * Handle "Select All" toggle.
	 *
	 * @param {boolean} checked - Whether to select or deselect all.
	 */
	function toggleAll(checked) {
		var checkboxes = document.querySelectorAll('input[name="product_ids[]"]');

		checkboxes.forEach(function (cb) {
			cb.checked = checked;
			var productId = parseInt(cb.value, 10);
			var row = cb.closest('tr') || cb.closest('.opal-product-item');

			if (checked) {
				selectedIds.add(productId);
				if (row) row.classList.add('selected');
			} else {
				selectedIds.delete(productId);
				if (row) row.classList.remove('selected');
			}
		});

		updateSelectionCount();
	}

	/* ======================================================================
	   Category Filter
	   ====================================================================== */

	/**
	 * Initialize category filter dropdown (if present).
	 */
	function initCategoryFilter() {
		var filterSelect = document.getElementById('opal-category-filter');
		if (!filterSelect) return;

		filterSelect.addEventListener('change', function () {
			var category = this.value;
			var rows = document.querySelectorAll('[data-category]');

			rows.forEach(function (row) {
				if (!category || row.getAttribute('data-category') === category) {
					row.style.display = '';
				} else {
					row.style.display = 'none';
				}
			});
		});
	}

	/* ======================================================================
	   Bulk Processing
	   ====================================================================== */

	/**
	 * Gather processing options from the form.
	 *
	 * @returns {Object}
	 */
	function getProcessingOptions() {
		var removeBg = document.querySelector('input[name="remove_background"]');
		var genScene = document.querySelector('input[name="generate_scene"]');
		var upscale = document.querySelector('input[name="upscale"]');
		var scenePrompt = document.getElementById('opal-bulk-scene-prompt');

		return {
			remove_background: removeBg ? removeBg.checked : true,
			generate_scene: genScene ? genScene.checked : false,
			upscale: upscale ? upscale.checked : true,
			scene_prompt: scenePrompt ? scenePrompt.value.trim() : '',
		};
	}

	/**
	 * Start bulk processing for selected products.
	 */
	function startBulkProcess() {
		if (selectedIds.size === 0) {
			showToast('Please select at least one product.', 'error');
			return;
		}

		var productIds = Array.from(selectedIds);
		var options = getProcessingOptions();

		// Disable the button and show progress area.
		if (startBtn) {
			startBtn.disabled = true;
			startBtn.textContent = opalAdmin.i18n.processing || 'Processing...';
		}

		if (progressWrap) {
			progressWrap.style.display = 'block';
		}
		updateProgress(0, productIds.length, 'Starting...');

		var body = Object.assign({ product_ids: productIds }, options);

		restFetch('bulk-process', {
			method: 'POST',
			body: JSON.stringify(body),
		})
			.then(function (data) {
				currentBatchId = data.batch_id;
				showToast('Batch started (' + productIds.length + ' products).', 'info');
				startPolling();
			})
			.catch(function (err) {
				showToast('Failed to start batch: ' + err.message, 'error');
				resetBulkUI();
			});
	}

	/**
	 * Poll the batch status endpoint every 5 seconds.
	 */
	function startPolling() {
		if (pollTimer) clearInterval(pollTimer);

		pollTimer = setInterval(function () {
			if (!currentBatchId) {
				clearInterval(pollTimer);
				return;
			}

			restFetch('batch/' + currentBatchId + '/status')
				.then(function (data) {
					var completed = data.completed || 0;
					var failed = data.failed || 0;
					var total = data.total || 1;
					var done = completed + failed;
					var status = data.status || 'running';

					updateProgress(done, total, buildStatusText(completed, failed, total));
					updatePerProductStatuses(data.products || []);

					if (status === 'completed' || status === 'failed' || done >= total) {
						clearInterval(pollTimer);
						pollTimer = null;
						currentBatchId = null;

						if (failed === 0) {
							showToast('All ' + completed + ' products processed successfully!', 'success');
						} else {
							showToast(completed + ' completed, ' + failed + ' failed.', 'error');
						}

						resetBulkUI();
					}
				})
				.catch(function (err) {
					// Network error during polling; keep trying.
					console.warn('Opal: poll error', err.message);
				});
		}, 5000);
	}

	/**
	 * Build a status text string from progress values.
	 *
	 * @param {number} completed
	 * @param {number} failed
	 * @param {number} total
	 * @returns {string}
	 */
	function buildStatusText(completed, failed, total) {
		var parts = [completed + ' / ' + total + ' completed'];
		if (failed > 0) {
			parts.push(failed + ' failed');
		}
		return parts.join(' — ');
	}

	/**
	 * Update the visual progress bar and text.
	 *
	 * @param {number} done  - Number of completed items.
	 * @param {number} total - Total items.
	 * @param {string} text  - Status text.
	 */
	function updateProgress(done, total, text) {
		var pct = total > 0 ? Math.round((done / total) * 100) : 0;

		if (progressFill) {
			progressFill.style.width = pct + '%';
		}
		if (progressText) {
			progressText.textContent = text;
		}
	}

	/**
	 * Update per-product status indicators in the table (if the batch
	 * response includes per-product data).
	 *
	 * @param {Array} products - Array of {product_id, status}.
	 */
	function updatePerProductStatuses(products) {
		if (!products || !products.length) return;

		products.forEach(function (item) {
			var cb = document.querySelector('input[name="product_ids[]"][value="' + item.product_id + '"]');
			if (!cb) return;

			var row = cb.closest('tr');
			if (!row) return;

			// Find the status cell (last td).
			var cells = row.querySelectorAll('td');
			var statusCell = cells[cells.length - 1];
			if (statusCell && item.status) {
				statusCell.textContent = item.status.charAt(0).toUpperCase() + item.status.slice(1);
			}
		});
	}

	/**
	 * Reset the bulk processing UI to its initial state.
	 */
	function resetBulkUI() {
		if (startBtn) {
			startBtn.disabled = false;
			startBtn.textContent = 'Start Processing';
		}
	}

	/* ======================================================================
	   Initialize
	   ====================================================================== */

	function init() {
		// Bail if we are not on the bulk tab.
		if (!document.getElementById('opal-bulk-form')) return;

		initProductCheckboxes();
		initCategoryFilter();
		updateSelectionCount();

		// Select All checkboxes.
		if (selectAllCheckbox) {
			selectAllCheckbox.addEventListener('change', function () {
				toggleAll(this.checked);
				if (selectAllTop) selectAllTop.checked = this.checked;
			});
		}

		if (selectAllTop) {
			selectAllTop.addEventListener('change', function () {
				toggleAll(this.checked);
				if (selectAllCheckbox) selectAllCheckbox.checked = this.checked;
			});
		}

		// Start button.
		if (startBtn) {
			startBtn.addEventListener('click', startBulkProcess);
		}
	}

	// Run on DOMContentLoaded.
	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();
