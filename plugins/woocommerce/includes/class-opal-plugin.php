<?php
/**
 * Main plugin singleton class.
 *
 * @package OpalAIPhotography
 */

defined( 'ABSPATH' ) || exit;

/**
 * Class Opal_Plugin
 *
 * Central orchestrator — initializes all components and registers shared hooks.
 */
class Opal_Plugin {

	/**
	 * Singleton instance.
	 *
	 * @var Opal_Plugin|null
	 */
	private static $instance = null;

	/**
	 * API client instance.
	 *
	 * @var Opal_API_Client
	 */
	public $api_client;

	/**
	 * Settings instance.
	 *
	 * @var Opal_Settings
	 */
	public $settings;

	/**
	 * Admin instance.
	 *
	 * @var Opal_Admin
	 */
	public $admin;

	/**
	 * Image handler instance.
	 *
	 * @var Opal_Image_Handler
	 */
	public $image_handler;

	/**
	 * Bulk processor instance.
	 *
	 * @var Opal_Bulk_Processor
	 */
	public $bulk_processor;

	/**
	 * Single processor instance.
	 *
	 * @var Opal_Single_Processor
	 */
	public $single_processor;

	/**
	 * Product metabox instance.
	 *
	 * @var Opal_Product_Metabox
	 */
	public $product_metabox;

	/**
	 * A/B tests instance.
	 *
	 * @var Opal_AB_Tests
	 */
	public $ab_tests;

	/**
	 * A/B tracking instance.
	 *
	 * @var Opal_AB_Tracking
	 */
	public $ab_tracking;

	/**
	 * REST controller instance.
	 *
	 * @var Opal_REST_Controller
	 */
	public $rest_controller;

	/**
	 * Get the singleton instance.
	 *
	 * @return Opal_Plugin
	 */
	public static function instance() {
		if ( null === self::$instance ) {
			self::$instance = new self();
		}
		return self::$instance;
	}

	/**
	 * Private constructor — use instance().
	 */
	private function __construct() {
		$this->init_components();
		$this->register_hooks();
	}

	/**
	 * Initialize all component classes.
	 */
	private function init_components() {
		$this->api_client       = new Opal_API_Client();
		$this->settings         = new Opal_Settings();
		$this->image_handler    = new Opal_Image_Handler();
		$this->ab_tests         = new Opal_AB_Tests();
		$this->ab_tracking      = new Opal_AB_Tracking( $this->ab_tests );
		$this->bulk_processor   = new Opal_Bulk_Processor( $this->api_client, $this->image_handler );
		$this->single_processor = new Opal_Single_Processor( $this->api_client, $this->image_handler );
		$this->product_metabox  = new Opal_Product_Metabox();
		$this->admin            = new Opal_Admin( $this->api_client, $this->settings, $this->ab_tests );
		$this->rest_controller  = new Opal_REST_Controller(
			$this->api_client,
			$this->single_processor,
			$this->bulk_processor,
			$this->ab_tests,
			$this->ab_tracking
		);
	}

	/**
	 * Register WordPress hooks.
	 */
	private function register_hooks() {
		add_action( 'admin_enqueue_scripts', array( $this, 'enqueue_admin_assets' ) );
		add_action( 'rest_api_init', array( $this->rest_controller, 'register_routes' ) );

		// Check if just activated.
		if ( get_option( 'opal_activated' ) ) {
			delete_option( 'opal_activated' );
			add_action( 'admin_notices', array( $this, 'activation_notice' ) );
		}
	}

	/**
	 * Show a welcome notice after activation.
	 */
	public function activation_notice() {
		$settings_url = admin_url( 'admin.php?page=opal-ai&tab=settings' );
		?>
		<div class="notice notice-success is-dismissible">
			<p>
				<?php
				printf(
					/* translators: %s: Settings page URL */
					wp_kses(
						__( 'Opal AI Product Photography is active! <a href="%s">Configure your API key</a> to get started.', 'opal-ai-photography' ),
						array( 'a' => array( 'href' => array() ) )
					),
					esc_url( $settings_url )
				);
				?>
			</p>
		</div>
		<?php
	}

	/**
	 * Enqueue admin scripts and styles on Opal pages.
	 *
	 * @param string $hook_suffix The current admin page.
	 */
	public function enqueue_admin_assets( $hook_suffix ) {
		$opal_pages = array( 'toplevel_page_opal-ai', 'opal-ai_page_opal-ai' );
		$is_opal    = in_array( $hook_suffix, $opal_pages, true );
		$is_product = in_array( $hook_suffix, array( 'post.php', 'post-new.php' ), true );

		if ( ! $is_opal && ! $is_product ) {
			return;
		}

		wp_enqueue_style(
			'opal-admin',
			OPAL_PLUGIN_URL . 'assets/css/admin.css',
			array(),
			OPAL_VERSION
		);

		if ( $is_opal ) {
			wp_enqueue_script(
				'opal-admin',
				OPAL_PLUGIN_URL . 'assets/js/admin.js',
				array( 'jquery' ),
				OPAL_VERSION,
				true
			);

			wp_localize_script(
				'opal-admin',
				'opalAdmin',
				array(
					'ajaxUrl'  => admin_url( 'admin-ajax.php' ),
					'restUrl'  => rest_url( 'opal/v1/' ),
					'nonce'    => wp_create_nonce( 'opal_admin_nonce' ),
					'restNonce' => wp_create_nonce( 'wp_rest' ),
					'i18n'     => array(
						'processing'  => __( 'Processing...', 'opal-ai-photography' ),
						'complete'    => __( 'Complete', 'opal-ai-photography' ),
						'failed'      => __( 'Failed', 'opal-ai-photography' ),
						'confirm'     => __( 'Are you sure?', 'opal-ai-photography' ),
						'testConnect' => __( 'Testing connection...', 'opal-ai-photography' ),
						'connected'   => __( 'Connected successfully!', 'opal-ai-photography' ),
						'connFailed'  => __( 'Connection failed.', 'opal-ai-photography' ),
					),
				)
			);
		}

		if ( $is_product ) {
			$screen = get_current_screen();
			if ( $screen && 'product' === $screen->post_type ) {
				wp_enqueue_script(
					'opal-product-metabox',
					OPAL_PLUGIN_URL . 'assets/js/admin-product-metabox.js',
					array( 'jquery' ),
					OPAL_VERSION,
					true
				);

				wp_localize_script(
					'opal-product-metabox',
					'opalMetabox',
					array(
						'ajaxUrl' => admin_url( 'admin-ajax.php' ),
						'nonce'   => wp_create_nonce( 'opal_process_nonce' ),
						'i18n'    => array(
							'processing' => __( 'Processing...', 'opal-ai-photography' ),
							'polling'    => __( 'Waiting for results...', 'opal-ai-photography' ),
							'complete'   => __( 'Enhancement complete!', 'opal-ai-photography' ),
							'failed'     => __( 'Processing failed.', 'opal-ai-photography' ),
						),
					)
				);
			}
		}
	}

	/**
	 * Prevent cloning.
	 */
	private function __clone() {}

	/**
	 * Prevent unserialization.
	 */
	public function __wakeup() {
		throw new \Exception( 'Cannot unserialize singleton' );
	}
}
