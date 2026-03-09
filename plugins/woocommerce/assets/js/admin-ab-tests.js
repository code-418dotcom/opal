/**
 * Opal AI Product Photography — A/B Test Management Page
 *
 * Handles test list display, create form with WP media uploader,
 * start/conclude/cancel actions, and results view with significance.
 *
 * Depends on the `opalAdmin` localized object:
 *   - restUrl:   WP REST base URL (e.g. /wp-json/opal/v1/)
 *   - restNonce: REST nonce for X-WP-Nonce header
 *   - i18n:      Translated strings
 *
 * @package OpalAIPhotography
 */

(function () {
	'use strict';

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
	function restFetch(endpoint, options) {
		options = options || {};
		var url = opalAdmin.restUrl + endpoint;
		var headers = Object.assign({
			'Content-Type': 'application/json',
			'X-WP-Nonce': opalAdmin.restNonce,
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

	/**
	 * Show a toast notification.
	 *
	 * @param {string} message
	 * @param {string} type - 'success', 'error', or 'info'.
	 */
	function showToast(message, type) {
		type = type || 'info';
		var existing = document.querySelectorAll('.opal-toast');
		existing.forEach(function (el) { el.remove(); });

		var toast = document.createElement('div');
		toast.className = 'opal-toast opal-toast-' + type;
		toast.innerHTML =
			'<span>' + escapeHtml(message) + '</span>' +
			'<button class="opal-toast-dismiss" type="button">&times;</button>';

		document.body.appendChild(toast);
		toast.offsetHeight; // eslint-disable-line no-unused-expressions
		toast.classList.add('visible');

		toast.querySelector('.opal-toast-dismiss').addEventListener('click', function () {
			toast.classList.remove('visible');
			setTimeout(function () { toast.remove(); }, 300);
		});

		setTimeout(function () {
			if (toast.parentNode) {
				toast.classList.remove('visible');
				setTimeout(function () { toast.remove(); }, 300);
			}
		}, 6000);
	}

	/**
	 * Escape HTML entities.
	 *
	 * @param {string} str
	 * @returns {string}
	 */
	function escapeHtml(str) {
		var div = document.createElement('div');
		div.textContent = str;
		return div.innerHTML;
	}

	/* ======================================================================
	   WP Media Uploader Integration
	   ====================================================================== */

	/**
	 * Open the WordPress media uploader and resolve with the selected
	 * attachment ID and URL.
	 *
	 * @param {string} title  - Modal title.
	 * @param {string} button - Button label.
	 * @returns {Promise<{id: number, url: string}>}
	 */
	function openMediaUploader(title, button) {
		return new Promise(function (resolve, reject) {
			// wp.media is available when wp-media-utils is enqueued.
			if (typeof wp === 'undefined' || typeof wp.media === 'undefined') {
				reject(new Error('WordPress media library is not available.'));
				return;
			}

			var frame = wp.media({
				title: title,
				button: { text: button },
				multiple: false,
				library: { type: 'image' },
			});

			frame.on('select', function () {
				var attachment = frame.state().get('selection').first().toJSON();
				resolve({ id: attachment.id, url: attachment.sizes && attachment.sizes.thumbnail
					? attachment.sizes.thumbnail.url
					: attachment.url });
			});

			frame.on('close', function () {
				// User closed without selecting; just do nothing.
			});

			frame.open();
		});
	}

	/* ======================================================================
	   Create Test Form
	   ====================================================================== */

	/**
	 * Initialize the create A/B test form handlers.
	 */
	function initCreateForm() {
		var form = document.getElementById('opal-create-ab-test');
		if (!form) return;

		var createBtn = document.getElementById('opal-create-test-btn');
		var variantAInput = document.getElementById('opal-ab-variant-a');
		var variantBInput = document.getElementById('opal-ab-variant-b');

		// Add "Select Image" buttons next to variant ID fields.
		addMediaButton(variantAInput, 'Select Variant A Image');
		addMediaButton(variantBInput, 'Select Variant B Image');

		if (createBtn) {
			createBtn.addEventListener('click', function () {
				submitCreateTest(form, createBtn);
			});
		}
	}

	/**
	 * Add a "Select Image" button after an input field that opens the
	 * WP media uploader.
	 *
	 * @param {HTMLInputElement} input       - The image ID input.
	 * @param {string}          buttonLabel  - Button text.
	 */
	function addMediaButton(input, buttonLabel) {
		if (!input) return;

		var btn = document.createElement('button');
		btn.type = 'button';
		btn.className = 'button button-secondary';
		btn.textContent = buttonLabel;
		btn.style.marginLeft = '8px';
		btn.style.verticalAlign = 'middle';

		// Preview image element.
		var preview = document.createElement('img');
		preview.style.display = 'none';
		preview.style.width = '60px';
		preview.style.height = '60px';
		preview.style.objectFit = 'cover';
		preview.style.borderRadius = '4px';
		preview.style.marginLeft = '8px';
		preview.style.verticalAlign = 'middle';

		input.parentNode.insertBefore(btn, input.nextSibling);
		input.parentNode.insertBefore(preview, btn.nextSibling);

		btn.addEventListener('click', function () {
			openMediaUploader(buttonLabel, 'Use this image')
				.then(function (attachment) {
					input.value = attachment.id;
					preview.src = attachment.url;
					preview.style.display = 'inline-block';
				})
				.catch(function () {
					// Silently ignore if media library unavailable.
				});
		});
	}

	/**
	 * Submit the create test form via REST API.
	 *
	 * @param {HTMLFormElement}  form
	 * @param {HTMLButtonElement} btn
	 */
	function submitCreateTest(form, btn) {
		var productSelect = document.getElementById('opal-ab-product');
		var nameInput = document.getElementById('opal-ab-name');
		var variantAInput = document.getElementById('opal-ab-variant-a');
		var variantBInput = document.getElementById('opal-ab-variant-b');

		var productId = productSelect ? parseInt(productSelect.value, 10) : 0;
		var name = nameInput ? nameInput.value.trim() : '';
		var variantA = variantAInput ? parseInt(variantAInput.value, 10) : 0;
		var variantB = variantBInput ? parseInt(variantBInput.value, 10) : 0;

		// Validation.
		if (!productId) {
			showToast('Please select a product.', 'error');
			return;
		}
		if (!variantA || !variantB) {
			showToast('Both variant image IDs are required.', 'error');
			return;
		}

		btn.disabled = true;
		btn.textContent = 'Creating...';

		restFetch('ab-tests', {
			method: 'POST',
			body: JSON.stringify({
				product_id: productId,
				name: name,
				variant_a_image_id: variantA,
				variant_b_image_id: variantB,
			}),
		})
			.then(function (test) {
				showToast('A/B test created successfully!', 'success');
				// Redirect back to the tests list after a short delay.
				setTimeout(function () {
					var listUrl = window.location.href.replace(/&opal_action=create/, '');
					window.location.href = listUrl;
				}, 1000);
			})
			.catch(function (err) {
				showToast('Failed to create test: ' + err.message, 'error');
				btn.disabled = false;
				btn.textContent = 'Create Test';
			});
	}

	/* ======================================================================
	   Action Buttons (Start / Conclude / Cancel)
	   ====================================================================== */

	/**
	 * Initialize action button handlers on the detail page.
	 */
	function initActionButtons() {
		var actionBtns = document.querySelectorAll('.opal-ab-action');
		if (!actionBtns.length) return;

		actionBtns.forEach(function (btn) {
			btn.addEventListener('click', function () {
				var action = this.getAttribute('data-action');
				var testId = this.getAttribute('data-test-id');
				var winner = this.getAttribute('data-winner') || null;

				handleAction(action, testId, winner, this);
			});
		});
	}

	/**
	 * Execute a test action (start, conclude, cancel).
	 *
	 * @param {string}            action - 'start', 'conclude', or 'cancel'.
	 * @param {string}            testId - The test ID.
	 * @param {string|null}       winner - 'A' or 'B' (for conclude).
	 * @param {HTMLButtonElement}  btn    - The clicked button.
	 */
	function handleAction(action, testId, winner, btn) {
		var confirmMsg = opalAdmin.i18n.confirm || 'Are you sure?';

		if (action === 'conclude') {
			confirmMsg = 'Declare Variant ' + winner + ' the winner? The winning image will be set as the product\'s featured image.';
		} else if (action === 'cancel') {
			confirmMsg = 'Cancel this test? The original product image will be restored.';
		} else if (action === 'start') {
			confirmMsg = 'Start this A/B test? Product images will be swapped for visitors.';
		}

		if (!window.confirm(confirmMsg)) return;

		btn.disabled = true;
		var originalText = btn.textContent;
		btn.textContent = 'Working...';

		var endpoint, body;

		if (action === 'start') {
			endpoint = 'ab-tests/' + testId + '/start';
			body = null;
		} else if (action === 'conclude') {
			endpoint = 'ab-tests/' + testId + '/conclude';
			body = JSON.stringify({ winner: winner });
		} else {
			// Cancel is not implemented as a REST route in the current backend,
			// but we handle it for forward compatibility.
			endpoint = 'ab-tests/' + testId + '/cancel';
			body = null;
		}

		restFetch(endpoint, {
			method: 'POST',
			body: body,
		})
			.then(function () {
				showToast('Test ' + action + ' successful!', 'success');
				setTimeout(function () { window.location.reload(); }, 1000);
			})
			.catch(function (err) {
				showToast('Action failed: ' + err.message, 'error');
				btn.disabled = false;
				btn.textContent = originalText;
			});
	}

	/* ======================================================================
	   Initialize
	   ====================================================================== */

	function init() {
		initCreateForm();
		initActionButtons();
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();
