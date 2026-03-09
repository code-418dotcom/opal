<?php
/**
 * Plugin Name: Opal AI Product Photography
 * Plugin URI: https://opal.app
 * Description: AI-powered product image enhancement for WooCommerce — background removal, studio scenes, upscaling, and A/B testing.
 * Version: 1.0.0
 * Requires at least: 6.4
 * Requires PHP: 8.0
 * WC requires at least: 8.0
 * WC tested up to: 9.5
 * Author: Opal
 * Author URI: https://opal.app
 * License: GPL v2 or later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain: opal-ai-photography
 * Domain Path: /languages
 *
 * @package OpalAIPhotography
 */

defined( 'ABSPATH' ) || exit;

define( 'OPAL_VERSION', '1.0.0' );
define( 'OPAL_PLUGIN_FILE', __FILE__ );
define( 'OPAL_PLUGIN_DIR', plugin_dir_path( __FILE__ ) );
define( 'OPAL_PLUGIN_URL', plugin_dir_url( __FILE__ ) );
define( 'OPAL_PLUGIN_BASENAME', plugin_basename( __FILE__ ) );

/**
 * Check if WooCommerce is active.
 *
 * @return bool
 */
function opal_is_woocommerce_active() {
	return in_array(
		'woocommerce/woocommerce.php',
		apply_filters( 'active_plugins', get_option( 'active_plugins', array() ) ),
		true
	);
}

/**
 * Show admin notice when WooCommerce is not active.
 */
function opal_woocommerce_missing_notice() {
	?>
	<div class="notice notice-error">
		<p>
			<?php
			printf(
				/* translators: %s: WooCommerce plugin name */
				esc_html__( 'Opal AI Product Photography requires %s to be installed and activated.', 'opal-ai-photography' ),
				'<strong>WooCommerce</strong>'
			);
			?>
		</p>
	</div>
	<?php
}

/**
 * Declare HPOS compatibility.
 */
add_action(
	'before_woocommerce_init',
	function () {
		if ( class_exists( '\Automattic\WooCommerce\Utilities\FeaturesUtil' ) ) {
			\Automattic\WooCommerce\Utilities\FeaturesUtil::declare_compatibility( 'custom_order_tables', __FILE__, true );
		}
	}
);

/**
 * Plugin activation hook.
 */
function opal_activate() {
	if ( ! opal_is_woocommerce_active() ) {
		deactivate_plugins( plugin_basename( __FILE__ ) );
		wp_die(
			esc_html__( 'Opal AI Product Photography requires WooCommerce to be installed and activated.', 'opal-ai-photography' ),
			'Plugin Activation Error',
			array( 'back_link' => true )
		);
	}

	require_once OPAL_PLUGIN_DIR . 'includes/class-opal-ab-tests.php';
	Opal_AB_Tests::create_tables();

	add_option( 'opal_activated', true );
}

/**
 * Plugin deactivation hook.
 */
function opal_deactivate() {
	// Clear all scheduled Action Scheduler actions.
	if ( function_exists( 'as_unschedule_all_actions' ) ) {
		as_unschedule_all_actions( 'opal_process_product' );
		as_unschedule_all_actions( 'opal_poll_job' );
	}

	// Clear transients.
	delete_transient( 'opal_token_balance' );
}

register_activation_hook( __FILE__, 'opal_activate' );
register_deactivation_hook( __FILE__, 'opal_deactivate' );

/**
 * Initialize the plugin after plugins are loaded.
 */
function opal_init() {
	if ( ! opal_is_woocommerce_active() ) {
		add_action( 'admin_notices', 'opal_woocommerce_missing_notice' );
		return;
	}

	// Load text domain.
	load_plugin_textdomain( 'opal-ai-photography', false, dirname( OPAL_PLUGIN_BASENAME ) . '/languages' );

	// Include class files.
	require_once OPAL_PLUGIN_DIR . 'includes/class-opal-api-client.php';
	require_once OPAL_PLUGIN_DIR . 'includes/class-opal-settings.php';
	require_once OPAL_PLUGIN_DIR . 'includes/class-opal-admin.php';
	require_once OPAL_PLUGIN_DIR . 'includes/class-opal-image-handler.php';
	require_once OPAL_PLUGIN_DIR . 'includes/class-opal-bulk-processor.php';
	require_once OPAL_PLUGIN_DIR . 'includes/class-opal-single-processor.php';
	require_once OPAL_PLUGIN_DIR . 'includes/class-opal-product-metabox.php';
	require_once OPAL_PLUGIN_DIR . 'includes/class-opal-ab-tests.php';
	require_once OPAL_PLUGIN_DIR . 'includes/class-opal-ab-tracking.php';
	require_once OPAL_PLUGIN_DIR . 'includes/class-opal-rest-controller.php';
	require_once OPAL_PLUGIN_DIR . 'includes/class-opal-plugin.php';

	// Boot the plugin.
	Opal_Plugin::instance();
}

add_action( 'plugins_loaded', 'opal_init', 20 );
