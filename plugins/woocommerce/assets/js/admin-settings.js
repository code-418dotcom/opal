/**
 * Opal AI Product Photography — Settings Page
 *
 * Handles "Test Connection" AJAX call, API key show/hide toggle,
 * and auto-save toggle animation.
 *
 * Depends on the `opalAdmin` localized object:
 *   - ajaxUrl: WordPress admin-ajax.php URL
 *   - nonce:   Admin AJAX nonce (opal_admin_nonce)
 *   - i18n:    Translated strings (testConnect, connected, connFailed)
 *
 * @package OpalAIPhotography
 */

(function () {
	'use strict';

	/* ======================================================================
	   Test Connection
	   ====================================================================== */

	/**
	 * Initialize the "Test Connection" button.
	 */
	function initTestConnection() {
		var btn = document.getElementById('opal-test-connection');
		var resultSpan = document.getElementById('opal-test-result');
		if (!btn) return;

		btn.addEventListener('click', function () {
			btn.disabled = true;
			btn.textContent = opalAdmin.i18n.testConnect || 'Testing connection...';

			if (resultSpan) {
				resultSpan.textContent = '';
				resultSpan.className = 'opal-connection-status testing';
				resultSpan.textContent = 'Testing...';
			}

			var formData = new FormData();
			formData.append('action', 'opal_test_connection');
			formData.append('nonce', opalAdmin.nonce);

			fetch(opalAdmin.ajaxUrl, {
				method: 'POST',
				body: formData,
				credentials: 'same-origin',
			})
				.then(function (res) { return res.json(); })
				.then(function (data) {
					if (data.success) {
						if (resultSpan) {
							resultSpan.className = 'opal-connection-status connected';
							resultSpan.textContent = data.data.message || (opalAdmin.i18n.connected || 'Connected!');
						}
						showToast(data.data.message || 'Connection successful!', 'success');
					} else {
						var msg = (data.data && data.data.message) || (opalAdmin.i18n.connFailed || 'Connection failed.');
						if (resultSpan) {
							resultSpan.className = 'opal-connection-status disconnected';
							resultSpan.textContent = msg;
						}
						showToast(msg, 'error');
					}
				})
				.catch(function () {
					if (resultSpan) {
						resultSpan.className = 'opal-connection-status disconnected';
						resultSpan.textContent = opalAdmin.i18n.connFailed || 'Connection failed.';
					}
					showToast('Network error during connection test.', 'error');
				})
				.finally(function () {
					btn.disabled = false;
					btn.textContent = 'Test Connection';
				});
		});
	}

	/* ======================================================================
	   API Key Visibility Toggle
	   ====================================================================== */

	/**
	 * Initialize the show/hide toggle for the API key field.
	 */
	function initApiKeyToggle() {
		var keyInput = document.querySelector('input[name="opal_api_key_encrypted"]');
		if (!keyInput) return;

		// Create the toggle button.
		var toggleBtn = document.createElement('button');
		toggleBtn.type = 'button';
		toggleBtn.className = 'button button-secondary';
		toggleBtn.textContent = 'Show';
		toggleBtn.style.marginLeft = '4px';
		toggleBtn.style.verticalAlign = 'middle';

		// Insert after the input but before the Test Connection button.
		var testBtn = document.getElementById('opal-test-connection');
		if (testBtn) {
			keyInput.parentNode.insertBefore(toggleBtn, testBtn);
		} else {
			keyInput.parentNode.insertBefore(toggleBtn, keyInput.nextSibling);
		}

		toggleBtn.addEventListener('click', function () {
			if (keyInput.type === 'password') {
				keyInput.type = 'text';
				toggleBtn.textContent = 'Hide';
			} else {
				keyInput.type = 'password';
				toggleBtn.textContent = 'Show';
			}
		});
	}

	/* ======================================================================
	   Auto-Save Toggle Animation
	   ====================================================================== */

	/**
	 * Add a subtle animation when checkbox toggles are changed,
	 * providing visual feedback that the change has been registered
	 * (actual save still requires the form submit button).
	 */
	function initToggleAnimation() {
		var checkboxes = document.querySelectorAll(
			'input[name="opal_auto_process"], ' +
			'input[name="opal_auto_replace"], ' +
			'input[name="opal_keep_originals"], ' +
			'input[name="opal_remove_bg"], ' +
			'input[name="opal_generate_scene"], ' +
			'input[name="opal_upscale"]'
		);

		checkboxes.forEach(function (cb) {
			cb.addEventListener('change', function () {
				var label = this.closest('label');
				if (!label) return;

				// Flash highlight.
				label.style.transition = 'background-color 0.3s ease';
				label.style.backgroundColor = 'rgba(99, 102, 241, 0.1)';
				label.style.borderRadius = '4px';
				label.style.padding = '2px 6px';

				setTimeout(function () {
					label.style.backgroundColor = 'transparent';
				}, 600);
			});
		});
	}

	/* ======================================================================
	   Toast Helper
	   ====================================================================== */

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

		var div = document.createElement('div');
		div.textContent = message;
		toast.appendChild(div);

		var dismiss = document.createElement('button');
		dismiss.className = 'opal-toast-dismiss';
		dismiss.type = 'button';
		dismiss.innerHTML = '&times;';
		toast.appendChild(dismiss);

		document.body.appendChild(toast);
		toast.offsetHeight; // eslint-disable-line no-unused-expressions
		toast.classList.add('visible');

		dismiss.addEventListener('click', function () {
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

	/* ======================================================================
	   Initialize
	   ====================================================================== */

	function init() {
		initTestConnection();
		initApiKeyToggle();
		initToggleAnimation();
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();
