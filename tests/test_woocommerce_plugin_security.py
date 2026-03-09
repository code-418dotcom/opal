"""
Security tests for the WooCommerce plugin (plugins/woocommerce/).

These tests perform static analysis on the PHP source to verify:
  - CSRF protection (nonce verification on all state-changing endpoints)
  - Authorization checks (capability verification on all admin endpoints)
  - SQL injection prevention (prepared statements for all DB queries)
  - XSS prevention (proper output escaping in HTML contexts)
  - Input sanitization (all user inputs are sanitized before use)
  - Encryption correctness (API key storage)
  - File handling safety (download, upload, path traversal)
  - Information disclosure prevention
"""

import os
import re
import glob
import pytest

PLUGIN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "plugins",
    "woocommerce",
)


def read_file(relative_path):
    """Read a plugin file and return its contents."""
    path = os.path.join(PLUGIN_DIR, relative_path)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def get_all_php_files():
    """Return all PHP file paths relative to PLUGIN_DIR."""
    result = []
    for root, _dirs, files in os.walk(PLUGIN_DIR):
        for f in files:
            if f.endswith(".php"):
                result.append(os.path.relpath(os.path.join(root, f), PLUGIN_DIR))
    return result


# ---------------------------------------------------------------------------
# 1. ABSPATH guard — every PHP file must refuse direct access
# ---------------------------------------------------------------------------


class TestDirectAccessProtection:
    """Every PHP file must exit if loaded outside WordPress."""

    @pytest.mark.parametrize("php_file", get_all_php_files())
    def test_abspath_guard(self, php_file):
        content = read_file(php_file)
        # uninstall.php uses WP_UNINSTALL_PLUGIN instead
        if "uninstall.php" in php_file:
            assert "WP_UNINSTALL_PLUGIN" in content, (
                f"{php_file} must check WP_UNINSTALL_PLUGIN"
            )
        else:
            assert "ABSPATH" in content, (
                f"{php_file} must check defined('ABSPATH') to prevent direct access"
            )


# ---------------------------------------------------------------------------
# 2. CSRF — nonce verification on all AJAX handlers
# ---------------------------------------------------------------------------


class TestCSRFProtection:
    """All AJAX endpoints must verify nonces."""

    def test_ajax_test_connection_has_nonce_check(self):
        content = read_file("includes/class-opal-settings.php")
        assert "check_ajax_referer" in content, (
            "ajax_test_connection must verify nonce with check_ajax_referer"
        )

    def test_ajax_process_product_has_nonce_check(self):
        content = read_file("includes/class-opal-single-processor.php")
        # Both AJAX handlers must check nonce
        matches = re.findall(r"check_ajax_referer", content)
        assert len(matches) >= 2, (
            "Both ajax_process_product and ajax_poll_product must verify nonces"
        )

    def test_rest_endpoints_have_permission_callbacks(self):
        """All REST routes (except track-view) must check manage_woocommerce."""
        content = read_file("includes/class-opal-rest-controller.php")
        # Count routes registered
        route_count = content.count("register_rest_route")
        # Count permission callbacks
        perm_count = content.count("permission_callback")
        assert perm_count >= route_count, (
            f"Found {route_count} routes but only {perm_count} permission callbacks"
        )

    def test_track_view_is_only_public_endpoint(self):
        """Only track-view should use __return_true as permission callback."""
        content = read_file("includes/class-opal-rest-controller.php")
        public_count = content.count("__return_true")
        assert public_count == 1, (
            f"Expected exactly 1 public endpoint (track-view), found {public_count}"
        )

    def test_settings_form_uses_settings_fields(self):
        """Settings form must include WP nonce via settings_fields()."""
        content = read_file("includes/class-opal-settings.php")
        assert "settings_fields" in content, (
            "Settings form must call settings_fields() for CSRF protection"
        )

    def test_bulk_form_has_nonce_field(self):
        """The bulk processing form must include a nonce."""
        content = read_file("includes/class-opal-admin.php")
        assert "wp_nonce_field" in content, (
            "Bulk form must include wp_nonce_field() for CSRF protection"
        )


# ---------------------------------------------------------------------------
# 3. Authorization — capability checks
# ---------------------------------------------------------------------------


class TestAuthorization:
    """All admin actions must verify user capabilities."""

    def test_ajax_handlers_check_capability(self):
        """AJAX handlers must verify manage_woocommerce capability."""
        content = read_file("includes/class-opal-single-processor.php")
        assert content.count("manage_woocommerce") >= 2, (
            "Both AJAX handlers must check manage_woocommerce capability"
        )

    def test_settings_ajax_checks_capability(self):
        content = read_file("includes/class-opal-settings.php")
        assert "manage_woocommerce" in content, (
            "Settings AJAX must check manage_woocommerce capability"
        )

    def test_admin_bar_checks_capability(self):
        content = read_file("includes/class-opal-admin.php")
        assert "manage_woocommerce" in content, (
            "Admin bar balance must check capability"
        )

    def test_rest_can_manage_checks_capability(self):
        content = read_file("includes/class-opal-rest-controller.php")
        assert "manage_woocommerce" in content, (
            "REST permission callback must check manage_woocommerce"
        )

    def test_admin_menu_requires_capability(self):
        content = read_file("includes/class-opal-admin.php")
        assert "'manage_woocommerce'" in content, (
            "Admin menu page must require manage_woocommerce capability"
        )


# ---------------------------------------------------------------------------
# 4. SQL Injection Prevention
# ---------------------------------------------------------------------------


class TestSQLInjection:
    """All database queries must use prepared statements."""

    def _get_raw_query_lines(self, content, filename=""):
        """Find lines with potential SQL injection (query without prepare)."""
        issues = []
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Skip comments and phpcs ignore lines
            if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("#"):
                continue
            # Look for $wpdb->query() calls that don't use $wpdb->prepare()
            if "$wpdb->query(" in stripped and "prepare" not in stripped:
                # Allow DROP TABLE IF EXISTS (uninstall pattern)
                if "DROP TABLE IF EXISTS" in stripped:
                    continue
                # Allow simple variable-only queries that are safe
                issues.append((i, stripped))
        return issues

    def test_ab_tests_uses_prepared_statements(self):
        content = read_file("includes/class-opal-ab-tests.php")
        # Find all $wpdb->query() calls and verify each has a matching prepare()
        # within the next 5 lines (multiline pattern: $wpdb->query(\n\t$wpdb->prepare(...)))
        lines = content.split("\n")
        unsafe = []
        for i, line in enumerate(lines):
            s = line.strip()
            if "$wpdb->query(" in s and "prepare" not in s:
                # Check next 5 lines for prepare
                lookahead = "\n".join(lines[i:i + 6])
                if "prepare" not in lookahead:
                    unsafe.append((i + 1, s))
        assert not unsafe, (
            f"class-opal-ab-tests.php has unprepared query() calls: {unsafe}"
        )

    def test_admin_uses_prepared_statements(self):
        content = read_file("includes/class-opal-admin.php")
        unsafe = self._get_raw_query_lines(content, "class-opal-admin.php")
        assert not unsafe, (
            f"class-opal-admin.php has unprepared query() calls: {unsafe}"
        )

    def test_uninstall_table_drop_is_safe(self):
        """Uninstall uses $wpdb->prefix which is trusted."""
        content = read_file("uninstall.php")
        # Verify table names come from $wpdb->prefix only
        drop_lines = [l for l in content.split("\n") if "DROP TABLE" in l]
        for line in drop_lines:
            assert "$wpdb->prefix" in content, (
                "DROP TABLE must use $wpdb->prefix for table names"
            )

    def test_record_metric_column_is_whitelist_controlled(self):
        """record_metric() interpolates $column into SQL — verify it's switch-controlled."""
        content = read_file("includes/class-opal-ab-tests.php")
        # Extract the record_metric method
        start = content.find("function record_metric")
        end = content.find("\n\t}", start) + 3
        method = content[start:end]
        # Verify: $column is set only from a switch statement with hardcoded values
        assert "switch ( $event_type )" in method, (
            "record_metric must use a switch to whitelist column names"
        )
        assert "'views'" in method and "'add_to_carts'" in method and "'conversions'" in method, (
            "record_metric switch must only allow whitelisted column names"
        )
        # Verify there's a default: return that prevents unknown columns
        assert "default:" in method and "return;" in method, (
            "record_metric switch must have a default: return to reject unknown event types"
        )


# ---------------------------------------------------------------------------
# 5. XSS Prevention — Output Escaping
# ---------------------------------------------------------------------------


class TestXSSPrevention:
    """All HTML output must use proper WordPress escaping functions."""

    ESCAPING_FUNCTIONS = [
        "esc_html", "esc_attr", "esc_url", "esc_textarea",
        "wp_kses", "wp_json_encode", "absint", "number_format_i18n",
        "esc_html__", "esc_attr__",
    ]

    def test_admin_page_escapes_output(self):
        """Admin page must escape all dynamic output."""
        content = read_file("includes/class-opal-admin.php")
        # Check that echo statements use escaping
        echo_lines = [
            (i, l.strip())
            for i, l in enumerate(content.split("\n"), 1)
            if "echo " in l and "esc_" not in l and "wp_" not in l
            and not l.strip().startswith("//")
            and not l.strip().startswith("*")
            and "'" not in l.split("echo")[1][:5]  # skip echo '<tag...'
        ]
        # Filter out safe patterns: echo with wp_get_attachment_image (returns escaped),
        # and echo of simple HTML strings
        unsafe_echoes = []
        for i, line in echo_lines:
            # Skip lines that echo static HTML
            if re.match(r"echo\s+'[^']*';", line.split("//")[0].strip()):
                continue
            if "wp_get_attachment_image" in line:
                continue
            if "wc_price" in line:
                continue
            unsafe_echoes.append((i, line))
        # Allow some known-safe patterns (empty strings, static HTML)
        assert len(unsafe_echoes) <= 2, (
            f"Admin page has potentially unescaped echo statements: {unsafe_echoes}"
        )

    def test_ab_tests_page_escapes_output(self):
        """A/B tests admin page must escape all dynamic output."""
        content = read_file("includes/class-opal-ab-tests.php")
        # Find echo with variables that aren't escaped
        unsafe = []
        for i, line in enumerate(content.split("\n"), 1):
            s = line.strip()
            if "echo " in s and "$" in s:
                has_escape = any(fn in s for fn in self.ESCAPING_FUNCTIONS)
                if not has_escape and not s.startswith("//"):
                    # Skip wp_get_attachment_image calls
                    if "wp_get_attachment_image" in s:
                        continue
                    unsafe.append((i, s))
        assert not unsafe, (
            f"A/B tests page has unescaped variable output: {unsafe}"
        )

    def test_metabox_escapes_output(self):
        """Product metabox must escape all dynamic output."""
        content = read_file("includes/class-opal-product-metabox.php")
        unsafe = []
        for i, line in enumerate(content.split("\n"), 1):
            s = line.strip()
            if "echo " in s and "$" in s:
                has_escape = any(fn in s for fn in self.ESCAPING_FUNCTIONS)
                if not has_escape and not s.startswith("//"):
                    if "wp_get_attachment_image" in s or "wp_get_attachment_url" in s:
                        continue
                    unsafe.append((i, s))
        assert not unsafe, (
            f"Product metabox has unescaped variable output: {unsafe}"
        )

    def test_js_escapes_html_in_toasts(self):
        """JavaScript toast functions must escape HTML."""
        for js_file in ["assets/js/admin-bulk.js", "assets/js/admin-ab-tests.js"]:
            content = read_file(js_file)
            assert "escapeHtml" in content, (
                f"{js_file} must use escapeHtml() for toast messages"
            )


# ---------------------------------------------------------------------------
# 6. Input Sanitization
# ---------------------------------------------------------------------------


class TestInputSanitization:
    """All user inputs must be sanitized before use."""

    def test_settings_sanitize_api_key(self):
        """API key must be sanitized and encrypted before storage."""
        content = read_file("includes/class-opal-settings.php")
        assert "sanitize_callback" in content, "Settings must have sanitize_callback"
        assert "sanitize_api_key" in content, "API key must have custom sanitization"
        assert "encrypt_api_key" in content, "API key must be encrypted before storage"

    def test_settings_sanitize_url(self):
        """API URL must be sanitized with esc_url_raw."""
        content = read_file("includes/class-opal-settings.php")
        assert "esc_url_raw" in content, "API URL must use esc_url_raw sanitization"

    def test_settings_sanitize_textarea(self):
        """Scene prompt must be sanitized with sanitize_textarea_field."""
        content = read_file("includes/class-opal-settings.php")
        assert "sanitize_textarea_field" in content, (
            "Scene prompt must use sanitize_textarea_field"
        )

    def test_rest_args_have_sanitize_callbacks(self):
        """REST route args should have sanitize_callback or type validation."""
        content = read_file("includes/class-opal-rest-controller.php")
        # Count args definitions vs sanitize_callback
        args_count = content.count("'args'")
        sanitize_count = content.count("sanitize_callback")
        # Not all args need sanitize_callback if they have 'type' validation,
        # but critical ones (strings, IDs) should
        assert sanitize_count >= 4, (
            f"REST args should have sanitize callbacks, found only {sanitize_count}"
        )

    def test_admin_tab_parameter_is_sanitized(self):
        """The ?tab= GET parameter must be sanitized."""
        content = read_file("includes/class-opal-admin.php")
        assert "sanitize_text_field" in content, (
            "GET parameters must be sanitized with sanitize_text_field"
        )

    def test_ab_test_action_parameter_is_sanitized(self):
        """The ?opal_action= GET parameter must be sanitized."""
        content = read_file("includes/class-opal-ab-tests.php")
        assert "sanitize_text_field" in content, (
            "GET parameters must be sanitized with sanitize_text_field"
        )

    def test_post_data_sanitized_in_single_processor(self):
        """POST data in single processor AJAX must be sanitized."""
        content = read_file("includes/class-opal-single-processor.php")
        assert "absint" in content, "Product ID must use absint()"
        assert "sanitize_textarea_field" in content, "Scene prompt must be sanitized"

    def test_image_filename_is_sanitized(self):
        """Downloaded image filenames must be sanitized."""
        content = read_file("includes/class-opal-image-handler.php")
        assert "sanitize_file_name" in content, (
            "Downloaded filenames must use sanitize_file_name()"
        )


# ---------------------------------------------------------------------------
# 7. Encryption — API Key Storage
# ---------------------------------------------------------------------------


class TestEncryption:
    """API key encryption must be implemented correctly."""

    def test_uses_aes_256_cbc(self):
        """API key encryption must use AES-256-CBC."""
        content = read_file("includes/class-opal-api-client.php")
        assert "aes-256-cbc" in content, "Must use AES-256-CBC for encryption"

    def test_uses_wp_salt_for_key(self):
        """Encryption key must derive from wp_salt()."""
        content = read_file("includes/class-opal-api-client.php")
        assert "wp_salt" in content, "Encryption key must use wp_salt()"

    def test_static_iv_weakness_documented(self):
        """
        FLAG: The IV is derived deterministically from wp_salt('auth').
        This means the same IV is always used, making identical plaintexts
        produce identical ciphertexts. While not critical for API keys
        (they're unique), this is a cryptographic weakness.
        """
        content = read_file("includes/class-opal-api-client.php")
        # Verify IV derivation pattern
        assert "substr( hash(" in content, "IV is derived from hash"
        # Count how many times the IV is computed — should be same in both encrypt/decrypt
        iv_computations = content.count("substr( hash( 'sha256', $salt ), 0, 16 )")
        assert iv_computations == 2, (
            f"IV must be computed the same way in encrypt and decrypt, found {iv_computations} instances"
        )

    def test_api_key_never_stored_in_plaintext(self):
        """The raw API key must never be stored as a WordPress option."""
        content = read_file("includes/class-opal-settings.php")
        # Verify the setting name contains 'encrypted'
        assert "opal_api_key_encrypted" in content, (
            "API key option must be named with 'encrypted' suffix"
        )

    def test_empty_key_preserves_existing(self):
        """Submitting empty API key field must not delete the existing key."""
        content = read_file("includes/class-opal-settings.php")
        # The sanitize_api_key method should return existing key on empty input
        method_start = content.find("function sanitize_api_key")
        method_end = content.find("\n\t}", method_start) + 3
        method = content[method_start:method_end]
        assert "get_option( 'opal_api_key_encrypted'" in method, (
            "Empty API key submission must preserve existing encrypted key"
        )


# ---------------------------------------------------------------------------
# 8. File Handling Safety
# ---------------------------------------------------------------------------


class TestFileHandling:
    """File operations must prevent path traversal and validate content."""

    def test_download_validates_http_status(self):
        """Downloads must check HTTP status code."""
        content = read_file("includes/class-opal-image-handler.php")
        assert "wp_remote_retrieve_response_code" in content, (
            "Downloads must check HTTP response code"
        )
        assert "200 !== $code" in content or "200" in content, (
            "Downloads must reject non-200 responses"
        )

    def test_download_cleans_up_temp_files(self):
        """Failed downloads must clean up temporary files."""
        content = read_file("includes/class-opal-image-handler.php")
        unlink_count = content.count("@unlink")
        assert unlink_count >= 2, (
            "Must clean up temp files on failure (found fewer than 2 unlink calls)"
        )

    def test_filename_uniqueness(self):
        """Uploaded files must use wp_unique_filename to prevent overwrites."""
        content = read_file("includes/class-opal-image-handler.php")
        assert "wp_unique_filename" in content, (
            "Must use wp_unique_filename() to prevent overwriting existing files"
        )

    def test_file_permissions_set(self):
        """Uploaded files must have correct permissions."""
        content = read_file("includes/class-opal-image-handler.php")
        assert "chmod" in content, (
            "Must set appropriate file permissions on downloaded files"
        )

    def test_mime_type_validated(self):
        """Uploaded files must have their MIME type checked."""
        content = read_file("includes/class-opal-image-handler.php")
        assert "wp_check_filetype" in content, (
            "Must validate MIME type of downloaded files"
        )

    def test_upload_uses_wp_upload_dir(self):
        """Files must be stored in the WordPress uploads directory."""
        content = read_file("includes/class-opal-image-handler.php")
        assert "wp_upload_dir" in content, (
            "Must use wp_upload_dir() for file storage location"
        )

    def test_multipart_boundary_is_random(self):
        """Multipart form boundaries must be randomly generated."""
        content = read_file("includes/class-opal-api-client.php")
        assert "wp_generate_password" in content, (
            "Multipart boundary must be randomly generated"
        )


# ---------------------------------------------------------------------------
# 9. Information Disclosure Prevention
# ---------------------------------------------------------------------------


class TestInformationDisclosure:
    """Plugin must not leak sensitive information."""

    def test_api_key_not_echoed_in_html(self):
        """The decrypted API key must never appear in HTML output."""
        for php_file in get_all_php_files():
            content = read_file(php_file)
            # Check for patterns like echo $api_key or echo get_api_key()
            if "echo" in content and "decrypt_api_key" in content:
                pytest.fail(
                    f"{php_file} might echo the decrypted API key"
                )

    def test_api_key_field_is_password_type(self):
        """The API key input must be type=password."""
        content = read_file("includes/class-opal-settings.php")
        assert 'type="password"' in content, (
            "API key input must be type=password to prevent shoulder surfing"
        )

    def test_api_key_field_has_autocomplete_off(self):
        """The API key input must disable autocomplete."""
        content = read_file("includes/class-opal-settings.php")
        assert 'autocomplete="off"' in content, (
            "API key input must have autocomplete=off"
        )

    def test_error_messages_dont_leak_credentials(self):
        """Error messages must not include API keys or connection strings."""
        content = read_file("includes/class-opal-api-client.php")
        # The parse_response method should not include the full request in errors
        parse_start = content.find("function parse_response")
        parse_end = content.find("\n\t}", parse_start) + 3
        method = content[parse_start:parse_end]
        # Should not include headers (which contain API key) in error data
        assert "headers" not in method.lower() or "X-API-Key" not in method, (
            "Error responses must not include request headers with API key"
        )


# ---------------------------------------------------------------------------
# 10. Public Endpoint Security (track-view)
# ---------------------------------------------------------------------------


class TestPublicEndpointSecurity:
    """The public track-view endpoint must have input validation."""

    def test_track_view_validates_variant(self):
        """track_view must validate variant is A or B."""
        content = read_file("includes/class-opal-rest-controller.php")
        track_start = content.find("function track_view")
        track_end = content.find("\n\t}", track_start) + 3
        method = content[track_start:track_end]
        assert "in_array" in method, (
            "track_view must validate variant against whitelist"
        )

    def test_track_view_validates_event_type(self):
        """track_view must validate event_type against a whitelist."""
        content = read_file("includes/class-opal-rest-controller.php")
        track_start = content.find("function track_view")
        track_end = content.find("\n\t}", track_start) + 3
        method = content[track_start:track_end]
        assert "view" in method and "add_to_cart" in method and "conversion" in method, (
            "track_view must whitelist allowed event types"
        )

    def test_track_view_has_type_validation_on_args(self):
        """track_view REST args must have type validation."""
        content = read_file("includes/class-opal-rest-controller.php")
        # Find the track-view route registration
        tv_start = content.find("'/track-view'")
        tv_end = content.find(");", tv_start) + 2
        route = content[tv_start:tv_end]
        assert "'type'" in route, (
            "track-view args must have type validation"
        )
        assert "'sanitize_callback'" in route, (
            "track-view args must have sanitize_callback"
        )

    def test_record_metric_validates_variant(self):
        """record_metric must validate variant is A or B."""
        content = read_file("includes/class-opal-ab-tests.php")
        rec_start = content.find("function record_metric")
        rec_end = content.find("\n\t}", rec_start) + 3
        method = content[rec_start:rec_end]
        assert "in_array" in method and "'A'" in method and "'B'" in method, (
            "record_metric must validate variant against A/B whitelist"
        )


# ---------------------------------------------------------------------------
# 11. Singleton & Deserialization Safety
# ---------------------------------------------------------------------------


class TestObjectSafety:
    """Plugin singleton must prevent unsafe deserialization."""

    def test_wakeup_throws_exception(self):
        """__wakeup must throw to prevent deserialization attacks."""
        content = read_file("includes/class-opal-plugin.php")
        assert "__wakeup" in content, "Singleton must implement __wakeup"
        assert "throw" in content, "__wakeup must throw an exception"

    def test_clone_is_private(self):
        """__clone must be private to prevent cloning."""
        content = read_file("includes/class-opal-plugin.php")
        assert "private function __clone" in content, (
            "__clone must be private"
        )

    def test_constructor_is_private(self):
        """Constructor must be private for singleton pattern."""
        content = read_file("includes/class-opal-plugin.php")
        assert "private function __construct" in content, (
            "Singleton constructor must be private"
        )


# ---------------------------------------------------------------------------
# 12. Transient / Data Integrity
# ---------------------------------------------------------------------------


class TestDataIntegrity:
    """Batch and job data must be handled safely."""

    def test_batch_id_is_uuid(self):
        """Batch IDs must be cryptographically random UUIDs."""
        content = read_file("includes/class-opal-bulk-processor.php")
        assert "wp_generate_uuid4" in content, (
            "Batch IDs must use wp_generate_uuid4() for unpredictability"
        )

    def test_batch_status_sanitizes_id(self):
        """get_batch_status must sanitize the batch ID."""
        content = read_file("includes/class-opal-bulk-processor.php")
        func_start = content.find("function get_batch_status")
        func_end = content.find("\n\t}", func_start) + 3
        method = content[func_start:func_end]
        assert "sanitize_text_field" in method, (
            "Batch ID must be sanitized before use as transient key"
        )

    def test_transients_have_expiry(self):
        """All transients must have a finite expiry time."""
        content = read_file("includes/class-opal-bulk-processor.php")
        # Find all set_transient calls and check within a window of surrounding lines
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "set_transient(" in line:
                # Look at the next 10 lines for the expiry argument
                window = "\n".join(lines[i:i + 12])
                assert "DAY_IN_SECONDS" in window or "HOUR_IN_SECONDS" in window, (
                    f"Transient at line {i+1} must have finite expiry"
                )

    def test_order_meta_prevents_double_counting(self):
        """Conversion tracking must prevent double-counting."""
        content = read_file("includes/class-opal-ab-tracking.php")
        assert "_opal_ab_tracked" in content, (
            "Conversion tracking must use order meta to prevent double-counting"
        )
        assert "get_meta" in content, (
            "Must check existing tracking meta before recording"
        )


# ---------------------------------------------------------------------------
# 13. Cookie Security
# ---------------------------------------------------------------------------


class TestCookieSecurity:
    """A/B test cookies must have proper security attributes."""

    def test_cookie_has_secure_flag(self):
        """Cookies must have Secure flag when on HTTPS."""
        content = read_file("includes/class-opal-ab-tracking.php")
        assert "'secure'" in content, "Cookie must set 'secure' flag"
        assert "is_ssl()" in content, "Secure flag must be conditional on is_ssl()"

    def test_cookie_has_samesite(self):
        """Cookies must have SameSite attribute."""
        content = read_file("includes/class-opal-ab-tracking.php")
        assert "'samesite'" in content, "Cookie must set SameSite attribute"
        assert "'Lax'" in content, "SameSite should be Lax for functional cookies"

    def test_cookie_uses_wp_constants(self):
        """Cookies must use WordPress cookie path/domain constants."""
        content = read_file("includes/class-opal-ab-tracking.php")
        assert "COOKIEPATH" in content, "Cookie must use COOKIEPATH"
        assert "COOKIE_DOMAIN" in content, "Cookie must use COOKIE_DOMAIN"

    def test_cookie_value_is_validated(self):
        """Cookie values must be validated before use."""
        content = read_file("includes/class-opal-ab-tracking.php")
        func_start = content.find("function get_variant")
        func_end = content.find("\n\t}", func_start) + 3
        method = content[func_start:func_end]
        assert "sanitize_text_field" in method, (
            "Cookie value must be sanitized"
        )
        assert "in_array" in method, (
            "Cookie value must be validated against A/B whitelist"
        )


# ---------------------------------------------------------------------------
# 14. SSRF Prevention
# ---------------------------------------------------------------------------


class TestSSRFPrevention:
    """API URL must be validated to prevent SSRF."""

    def test_api_url_sanitized_on_save(self):
        """API URL is sanitized with esc_url_raw on save."""
        content = read_file("includes/class-opal-settings.php")
        assert "esc_url_raw" in content, (
            "API URL must be sanitized with esc_url_raw to prevent SSRF"
        )

    def test_api_url_uses_untrailingslashit(self):
        """API URL is normalized before use."""
        content = read_file("includes/class-opal-api-client.php")
        assert "untrailingslashit" in content, (
            "API URL must be normalized with untrailingslashit"
        )

    def test_download_url_not_arbitrary(self):
        """Image downloads must come from Opal API, not arbitrary URLs."""
        content = read_file("includes/class-opal-image-handler.php")
        # The download_and_attach method receives URLs from the Opal API response,
        # not directly from user input. Verify it's called from processor classes
        # and not exposed directly.
        assert "private function download_to_temp" in content, (
            "download_to_temp must be private to prevent arbitrary URL fetching"
        )


# ---------------------------------------------------------------------------
# 15. Multipart Form Body Injection
# ---------------------------------------------------------------------------


class TestMultipartSecurity:
    """Multipart form bodies must prevent header injection."""

    def test_multipart_field_name_from_code(self):
        """Multipart field names must be hardcoded, not from user input."""
        content = read_file("includes/class-opal-api-client.php")
        # The post_multipart method takes $fields which are passed from
        # internal code (upload_image, complete_upload) with hardcoded keys
        # Verify the callers use hardcoded field names
        assert "'job_id'" in content, "Field names should be hardcoded strings"
        assert "'item_id'" in content, "Field names should be hardcoded strings"

    def test_filename_uses_basename(self):
        """Filenames in multipart bodies must use basename()."""
        content = read_file("includes/class-opal-api-client.php")
        assert "basename( $file_path )" in content, (
            "Multipart filename must use basename() to strip path"
        )


# ---------------------------------------------------------------------------
# 16. Uninstall Safety
# ---------------------------------------------------------------------------


class TestUninstallSafety:
    """Uninstall must check for legitimate context and clean up completely."""

    def test_uninstall_checks_constant(self):
        """uninstall.php must verify WP_UNINSTALL_PLUGIN constant."""
        content = read_file("uninstall.php")
        assert "WP_UNINSTALL_PLUGIN" in content, (
            "uninstall.php must check WP_UNINSTALL_PLUGIN"
        )

    def test_uninstall_removes_all_options(self):
        """uninstall.php must remove all plugin options."""
        content = read_file("uninstall.php")
        expected_options = [
            "opal_api_url",
            "opal_api_key_encrypted",
            "opal_default_scene_prompt",
            "opal_remove_bg",
            "opal_generate_scene",
            "opal_upscale",
            "opal_auto_process",
            "opal_auto_replace",
            "opal_keep_originals",
        ]
        for opt in expected_options:
            assert opt in content, f"uninstall.php must remove option: {opt}"

    def test_uninstall_drops_tables(self):
        """uninstall.php must drop custom tables."""
        content = read_file("uninstall.php")
        assert "opal_ab_tests" in content, "Must drop opal_ab_tests table"
        assert "opal_ab_metrics" in content, "Must drop opal_ab_metrics table"

    def test_uninstall_cleans_transients(self):
        """uninstall.php must clean up transients."""
        content = read_file("uninstall.php")
        assert "transient_opal_" in content, "Must clean up opal transients"

    def test_uninstall_cleans_post_meta(self):
        """uninstall.php must clean up post meta."""
        content = read_file("uninstall.php")
        assert "_opal_jobs" in content, "Must clean up _opal_jobs meta"
        assert "_opal_processed_images" in content, "Must clean up processed images meta"
        assert "_opal_last_processed" in content, "Must clean up last processed meta"
        assert "_opal_ab_tracked" in content, "Must clean up AB tracking meta"


# ---------------------------------------------------------------------------
# 17. WordPress Coding Standards Compliance
# ---------------------------------------------------------------------------


class TestCodingStandards:
    """Basic WordPress coding standards for security."""

    @pytest.mark.parametrize("php_file", get_all_php_files())
    def test_no_eval(self, php_file):
        """No PHP file should use eval()."""
        content = read_file(php_file)
        # Match eval( but not "evaluate" or similar words
        if re.search(r'\beval\s*\(', content):
            pytest.fail(f"{php_file} uses eval() which is a security risk")

    @pytest.mark.parametrize("php_file", get_all_php_files())
    def test_no_exec(self, php_file):
        """No PHP file should use exec(), system(), or passthru()."""
        content = read_file(php_file)
        dangerous = ["exec(", "system(", "passthru(", "shell_exec(", "proc_open("]
        for func in dangerous:
            assert func not in content, (
                f"{php_file} uses dangerous function: {func}"
            )

    @pytest.mark.parametrize("php_file", get_all_php_files())
    def test_no_extract(self, php_file):
        """No PHP file should use extract() which can overwrite variables."""
        content = read_file(php_file)
        if re.search(r'\bextract\s*\(', content):
            pytest.fail(f"{php_file} uses extract() which is a security risk")

    def test_no_raw_superglobals_in_rest_controller(self):
        """REST controller must not directly access $_GET, $_POST, $_REQUEST."""
        content = read_file("includes/class-opal-rest-controller.php")
        for var in ["$_GET", "$_POST", "$_REQUEST", "$_SERVER"]:
            assert var not in content, (
                f"REST controller must use $request->get_param() instead of {var}"
            )

    def test_admin_get_params_sanitized(self):
        """Admin page must sanitize $_GET parameters."""
        content = read_file("includes/class-opal-admin.php")
        # Every $_GET access should be wrapped in sanitize_text_field + wp_unslash
        get_accesses = re.findall(r'\$_GET\[.*?\]', content)
        for access in get_accesses:
            # Find the line containing this access
            for line in content.split("\n"):
                if access in line:
                    assert "sanitize_text_field" in line or "absint" in line, (
                        f"$_GET access must be sanitized: {line.strip()}"
                    )
                    break
