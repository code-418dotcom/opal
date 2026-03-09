<?php
/**
 * Settings management.
 *
 * @package OpalAIPhotography
 */

defined( 'ABSPATH' ) || exit;

/**
 * Class Opal_Settings
 *
 * Registers WordPress settings, renders the settings tab, and handles the
 * Test Connection AJAX endpoint.
 */
class Opal_Settings {

	/**
	 * Constructor.
	 */
	public function __construct() {
		add_action( 'admin_init', array( $this, 'register_settings' ) );
		add_action( 'wp_ajax_opal_test_connection', array( $this, 'ajax_test_connection' ) );
	}

	/**
	 * Register all settings with the WordPress Settings API.
	 */
	public function register_settings() {
		// Section: API.
		add_settings_section(
			'opal_api_section',
			__( 'API Configuration', 'opal-ai-photography' ),
			array( $this, 'render_api_section' ),
			'opal-settings'
		);

		register_setting( 'opal-settings', 'opal_api_url', array(
			'type'              => 'string',
			'sanitize_callback' => 'esc_url_raw',
			'default'           => Opal_API_Client::DEFAULT_API_URL,
		) );

		add_settings_field( 'opal_api_url', __( 'API URL', 'opal-ai-photography' ), array( $this, 'render_api_url_field' ), 'opal-settings', 'opal_api_section' );

		register_setting( 'opal-settings', 'opal_api_key_encrypted', array(
			'type'              => 'string',
			'sanitize_callback' => array( $this, 'sanitize_api_key' ),
		) );

		add_settings_field( 'opal_api_key', __( 'API Key', 'opal-ai-photography' ), array( $this, 'render_api_key_field' ), 'opal-settings', 'opal_api_section' );

		// Section: Processing defaults.
		add_settings_section(
			'opal_processing_section',
			__( 'Processing Defaults', 'opal-ai-photography' ),
			array( $this, 'render_processing_section' ),
			'opal-settings'
		);

		register_setting( 'opal-settings', 'opal_default_scene_prompt', array(
			'type'              => 'string',
			'sanitize_callback' => 'sanitize_textarea_field',
			'default'           => '',
		) );

		add_settings_field( 'opal_default_scene_prompt', __( 'Default Scene Prompt', 'opal-ai-photography' ), array( $this, 'render_scene_prompt_field' ), 'opal-settings', 'opal_processing_section' );

		register_setting( 'opal-settings', 'opal_remove_bg', array(
			'type'    => 'boolean',
			'default' => true,
		) );

		add_settings_field( 'opal_remove_bg', __( 'Remove Background', 'opal-ai-photography' ), array( $this, 'render_remove_bg_field' ), 'opal-settings', 'opal_processing_section' );

		register_setting( 'opal-settings', 'opal_generate_scene', array(
			'type'    => 'boolean',
			'default' => false,
		) );

		add_settings_field( 'opal_generate_scene', __( 'Generate Scene', 'opal-ai-photography' ), array( $this, 'render_generate_scene_field' ), 'opal-settings', 'opal_processing_section' );

		register_setting( 'opal-settings', 'opal_upscale', array(
			'type'    => 'boolean',
			'default' => true,
		) );

		add_settings_field( 'opal_upscale', __( 'Upscale', 'opal-ai-photography' ), array( $this, 'render_upscale_field' ), 'opal-settings', 'opal_processing_section' );

		// Section: Automation.
		add_settings_section(
			'opal_automation_section',
			__( 'Automation', 'opal-ai-photography' ),
			array( $this, 'render_automation_section' ),
			'opal-settings'
		);

		register_setting( 'opal-settings', 'opal_auto_process', array(
			'type'    => 'boolean',
			'default' => false,
		) );

		add_settings_field( 'opal_auto_process', __( 'Auto-Process New Products', 'opal-ai-photography' ), array( $this, 'render_auto_process_field' ), 'opal-settings', 'opal_automation_section' );

		register_setting( 'opal-settings', 'opal_auto_replace', array(
			'type'    => 'boolean',
			'default' => false,
		) );

		add_settings_field( 'opal_auto_replace', __( 'Auto-Replace Images', 'opal-ai-photography' ), array( $this, 'render_auto_replace_field' ), 'opal-settings', 'opal_automation_section' );

		register_setting( 'opal-settings', 'opal_keep_originals', array(
			'type'    => 'boolean',
			'default' => true,
		) );

		add_settings_field( 'opal_keep_originals', __( 'Keep Originals', 'opal-ai-photography' ), array( $this, 'render_keep_originals_field' ), 'opal-settings', 'opal_automation_section' );
	}

	// -------------------------------------------------------------------------
	// Section descriptions
	// -------------------------------------------------------------------------

	/**
	 * Render API section description.
	 */
	public function render_api_section() {
		echo '<p>' . esc_html__( 'Enter your Opal API credentials. You can find your API key in the Opal dashboard.', 'opal-ai-photography' ) . '</p>';
	}

	/**
	 * Render processing section description.
	 */
	public function render_processing_section() {
		echo '<p>' . esc_html__( 'Configure default processing options applied to new jobs.', 'opal-ai-photography' ) . '</p>';
	}

	/**
	 * Render automation section description.
	 */
	public function render_automation_section() {
		echo '<p>' . esc_html__( 'Control automatic image processing behaviour.', 'opal-ai-photography' ) . '</p>';
	}

	// -------------------------------------------------------------------------
	// Field renderers
	// -------------------------------------------------------------------------

	/**
	 * Render the API URL field.
	 */
	public function render_api_url_field() {
		$value = get_option( 'opal_api_url', Opal_API_Client::DEFAULT_API_URL );
		printf(
			'<input type="url" name="opal_api_url" value="%s" class="regular-text" />',
			esc_attr( $value )
		);
		echo '<p class="description">' . esc_html__( 'The base URL for the Opal API.', 'opal-ai-photography' ) . '</p>';
	}

	/**
	 * Render the API key field.
	 */
	public function render_api_key_field() {
		$has_key = ! empty( get_option( 'opal_api_key_encrypted', '' ) );
		$placeholder = $has_key
			? __( 'Key saved — enter a new key to replace it', 'opal-ai-photography' )
			: __( 'Enter your API key', 'opal-ai-photography' );

		printf(
			'<input type="password" name="opal_api_key_encrypted" value="" placeholder="%s" class="regular-text" autocomplete="off" />',
			esc_attr( $placeholder )
		);

		echo '&nbsp;<button type="button" id="opal-test-connection" class="button button-secondary">'
			. esc_html__( 'Test Connection', 'opal-ai-photography' )
			. '</button>';
		echo '<span id="opal-test-result" style="margin-left:10px;"></span>';
		echo '<p class="description">' . esc_html__( 'Your Opal API key. Stored encrypted.', 'opal-ai-photography' ) . '</p>';
	}

	/**
	 * Render the scene prompt field.
	 */
	public function render_scene_prompt_field() {
		$value = get_option( 'opal_default_scene_prompt', '' );
		printf(
			'<textarea name="opal_default_scene_prompt" rows="3" class="large-text">%s</textarea>',
			esc_textarea( $value )
		);
		echo '<p class="description">' . esc_html__( 'Default scene description used for AI scene generation (e.g. "Product on a marble countertop in soft studio lighting").', 'opal-ai-photography' ) . '</p>';
	}

	/**
	 * Render the Remove Background checkbox.
	 */
	public function render_remove_bg_field() {
		$this->render_checkbox( 'opal_remove_bg', __( 'Remove product backgrounds by default', 'opal-ai-photography' ) );
	}

	/**
	 * Render the Generate Scene checkbox.
	 */
	public function render_generate_scene_field() {
		$this->render_checkbox( 'opal_generate_scene', __( 'Generate AI studio scenes by default', 'opal-ai-photography' ) );
	}

	/**
	 * Render the Upscale checkbox.
	 */
	public function render_upscale_field() {
		$this->render_checkbox( 'opal_upscale', __( 'Upscale images to high resolution by default', 'opal-ai-photography' ) );
	}

	/**
	 * Render the Auto-Process checkbox.
	 */
	public function render_auto_process_field() {
		$this->render_checkbox( 'opal_auto_process', __( 'Automatically process images when a new product is published', 'opal-ai-photography' ) );
	}

	/**
	 * Render the Auto-Replace checkbox.
	 */
	public function render_auto_replace_field() {
		$this->render_checkbox( 'opal_auto_replace', __( 'Automatically replace product images with processed versions', 'opal-ai-photography' ) );
	}

	/**
	 * Render the Keep Originals checkbox.
	 */
	public function render_keep_originals_field() {
		$this->render_checkbox( 'opal_keep_originals', __( 'Keep original images in the media library after replacement', 'opal-ai-photography' ) );
	}

	/**
	 * Helper to render a checkbox field.
	 *
	 * @param string $option_name The option name.
	 * @param string $label       The label text.
	 */
	private function render_checkbox( $option_name, $label ) {
		$checked = get_option( $option_name, false );
		printf(
			'<label><input type="checkbox" name="%s" value="1" %s /> %s</label>',
			esc_attr( $option_name ),
			checked( $checked, true, false ),
			esc_html( $label )
		);
	}

	// -------------------------------------------------------------------------
	// Sanitization
	// -------------------------------------------------------------------------

	/**
	 * Sanitize and encrypt the API key before storage.
	 *
	 * If the submitted value is empty, keep the existing key.
	 *
	 * @param string $value The submitted value.
	 * @return string The encrypted API key.
	 */
	public function sanitize_api_key( $value ) {
		$value = sanitize_text_field( $value );
		if ( empty( $value ) ) {
			// Keep existing key if nothing was submitted.
			return get_option( 'opal_api_key_encrypted', '' );
		}

		$client = new Opal_API_Client();
		return $client->encrypt_api_key( $value );
	}

	// -------------------------------------------------------------------------
	// Settings tab renderer (called by Opal_Admin)
	// -------------------------------------------------------------------------

	/**
	 * Render the full settings tab content.
	 */
	public function render_settings_tab() {
		?>
		<form method="post" action="options.php">
			<?php
			settings_fields( 'opal-settings' );
			do_settings_sections( 'opal-settings' );
			submit_button( __( 'Save Settings', 'opal-ai-photography' ) );
			?>
		</form>
		<?php
	}

	// -------------------------------------------------------------------------
	// AJAX: Test Connection
	// -------------------------------------------------------------------------

	/**
	 * Handle the Test Connection AJAX request.
	 */
	public function ajax_test_connection() {
		check_ajax_referer( 'opal_admin_nonce', 'nonce' );

		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			wp_send_json_error( array( 'message' => __( 'Permission denied.', 'opal-ai-photography' ) ) );
		}

		$client = new Opal_API_Client();
		$result = $client->test_connection();

		if ( is_wp_error( $result ) ) {
			wp_send_json_error( array( 'message' => $result->get_error_message() ) );
		}

		$balance = isset( $result['token_balance'] ) ? absint( $result['token_balance'] ) : 0;
		wp_send_json_success(
			array(
				/* translators: %d: token balance */
				'message' => sprintf( __( 'Connected! Token balance: %d', 'opal-ai-photography' ), $balance ),
			)
		);
	}

	// -------------------------------------------------------------------------
	// Helpers for reading processing options
	// -------------------------------------------------------------------------

	/**
	 * Get the default processing options from settings.
	 *
	 * @return array {remove_background: bool, generate_scene: bool, upscale: bool}
	 */
	public static function get_default_processing_options() {
		return array(
			'remove_background' => (bool) get_option( 'opal_remove_bg', true ),
			'generate_scene'    => (bool) get_option( 'opal_generate_scene', false ),
			'upscale'           => (bool) get_option( 'opal_upscale', true ),
		);
	}

	/**
	 * Get the default scene prompt.
	 *
	 * @return string
	 */
	public static function get_default_scene_prompt() {
		return get_option( 'opal_default_scene_prompt', '' );
	}
}
