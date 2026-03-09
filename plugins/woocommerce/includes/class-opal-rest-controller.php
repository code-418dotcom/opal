<?php
/**
 * WP REST API endpoints.
 *
 * @package OpalAIPhotography
 */

defined( 'ABSPATH' ) || exit;

/**
 * Class Opal_REST_Controller
 *
 * Registers REST routes under the opal/v1 namespace for product processing,
 * bulk operations, A/B testing, balance proxy, and view tracking.
 */
class Opal_REST_Controller {

	/**
	 * REST namespace.
	 *
	 * @var string
	 */
	const NAMESPACE = 'opal/v1';

	/**
	 * API client.
	 *
	 * @var Opal_API_Client
	 */
	private $api_client;

	/**
	 * Single processor.
	 *
	 * @var Opal_Single_Processor
	 */
	private $single_processor;

	/**
	 * Bulk processor.
	 *
	 * @var Opal_Bulk_Processor
	 */
	private $bulk_processor;

	/**
	 * A/B tests.
	 *
	 * @var Opal_AB_Tests
	 */
	private $ab_tests;

	/**
	 * A/B tracking.
	 *
	 * @var Opal_AB_Tracking
	 */
	private $ab_tracking;

	/**
	 * Constructor.
	 *
	 * @param Opal_API_Client       $api_client        API client.
	 * @param Opal_Single_Processor $single_processor  Single processor.
	 * @param Opal_Bulk_Processor   $bulk_processor    Bulk processor.
	 * @param Opal_AB_Tests         $ab_tests          A/B tests.
	 * @param Opal_AB_Tracking      $ab_tracking       A/B tracking.
	 */
	public function __construct(
		Opal_API_Client $api_client,
		Opal_Single_Processor $single_processor,
		Opal_Bulk_Processor $bulk_processor,
		Opal_AB_Tests $ab_tests,
		Opal_AB_Tracking $ab_tracking
	) {
		$this->api_client       = $api_client;
		$this->single_processor = $single_processor;
		$this->bulk_processor   = $bulk_processor;
		$this->ab_tests         = $ab_tests;
		$this->ab_tracking      = $ab_tracking;
	}

	/**
	 * Register all REST routes.
	 */
	public function register_routes() {
		// --- Processing ---
		register_rest_route(
			self::NAMESPACE,
			'/process-product',
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'process_product' ),
				'permission_callback' => array( $this, 'can_manage' ),
				'args'                => array(
					'product_id' => array(
						'required'          => true,
						'type'              => 'integer',
						'sanitize_callback' => 'absint',
					),
				),
			)
		);

		register_rest_route(
			self::NAMESPACE,
			'/bulk-process',
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'bulk_process' ),
				'permission_callback' => array( $this, 'can_manage' ),
				'args'                => array(
					'product_ids' => array(
						'required' => true,
						'type'     => 'array',
						'items'    => array( 'type' => 'integer' ),
					),
				),
			)
		);

		register_rest_route(
			self::NAMESPACE,
			'/batch/(?P<id>[a-zA-Z0-9-]+)/status',
			array(
				'methods'             => 'GET',
				'callback'            => array( $this, 'batch_status' ),
				'permission_callback' => array( $this, 'can_manage' ),
			)
		);

		// --- A/B Tests ---
		register_rest_route(
			self::NAMESPACE,
			'/ab-tests',
			array(
				array(
					'methods'             => 'POST',
					'callback'            => array( $this, 'create_ab_test' ),
					'permission_callback' => array( $this, 'can_manage' ),
					'args'                => array(
						'product_id'         => array( 'required' => true, 'type' => 'integer', 'sanitize_callback' => 'absint' ),
						'name'               => array( 'type' => 'string', 'sanitize_callback' => 'sanitize_text_field', 'default' => '' ),
						'variant_a_image_id' => array( 'required' => true, 'type' => 'integer', 'sanitize_callback' => 'absint' ),
						'variant_b_image_id' => array( 'required' => true, 'type' => 'integer', 'sanitize_callback' => 'absint' ),
					),
				),
				array(
					'methods'             => 'GET',
					'callback'            => array( $this, 'list_ab_tests' ),
					'permission_callback' => array( $this, 'can_manage' ),
				),
			)
		);

		register_rest_route(
			self::NAMESPACE,
			'/ab-tests/(?P<id>\d+)/start',
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'start_ab_test' ),
				'permission_callback' => array( $this, 'can_manage' ),
			)
		);

		register_rest_route(
			self::NAMESPACE,
			'/ab-tests/(?P<id>\d+)/conclude',
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'conclude_ab_test' ),
				'permission_callback' => array( $this, 'can_manage' ),
				'args'                => array(
					'winner' => array(
						'required'          => true,
						'type'              => 'string',
						'sanitize_callback' => 'sanitize_text_field',
					),
				),
			)
		);

		register_rest_route(
			self::NAMESPACE,
			'/ab-tests/(?P<id>\d+)/cancel',
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'cancel_ab_test' ),
				'permission_callback' => array( $this, 'can_manage' ),
			)
		);

		// --- Balance ---
		register_rest_route(
			self::NAMESPACE,
			'/balance',
			array(
				'methods'             => 'GET',
				'callback'            => array( $this, 'get_balance' ),
				'permission_callback' => array( $this, 'can_manage' ),
			)
		);

		// --- Tracking (public, nonce-verified) ---
		register_rest_route(
			self::NAMESPACE,
			'/track-view',
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'track_view' ),
				'permission_callback' => '__return_true',
				'args'                => array(
					'test_id'    => array( 'required' => true, 'type' => 'integer', 'sanitize_callback' => 'absint' ),
					'variant'    => array( 'required' => true, 'type' => 'string', 'sanitize_callback' => 'sanitize_text_field' ),
					'event_type' => array( 'type' => 'string', 'default' => 'view', 'sanitize_callback' => 'sanitize_text_field' ),
				),
			)
		);
	}

	// -------------------------------------------------------------------------
	// Permission callbacks
	// -------------------------------------------------------------------------

	/**
	 * Check if the current user can manage WooCommerce.
	 *
	 * @return bool
	 */
	public function can_manage() {
		return current_user_can( 'manage_woocommerce' );
	}

	// -------------------------------------------------------------------------
	// Processing endpoints
	// -------------------------------------------------------------------------

	/**
	 * POST /process-product — trigger single product processing.
	 *
	 * @param WP_REST_Request $request The request.
	 * @return WP_REST_Response|WP_Error
	 */
	public function process_product( $request ) {
		$product_id = $request->get_param( 'product_id' );

		$options = array(
			'remove_background' => (bool) $request->get_param( 'remove_background' ) ?? true,
			'generate_scene'    => (bool) $request->get_param( 'generate_scene' ) ?? false,
			'upscale'           => (bool) $request->get_param( 'upscale' ) ?? true,
			'scene_prompt'      => sanitize_textarea_field( $request->get_param( 'scene_prompt' ) ?? '' ),
		);

		$result = $this->single_processor->process_product( $product_id, $options );

		if ( is_wp_error( $result ) ) {
			return $result;
		}

		return rest_ensure_response( $result );
	}

	/**
	 * POST /bulk-process — start a bulk processing batch.
	 *
	 * @param WP_REST_Request $request The request.
	 * @return WP_REST_Response
	 */
	public function bulk_process( $request ) {
		$product_ids = array_map( 'absint', $request->get_param( 'product_ids' ) );

		$options = array(
			'remove_background' => (bool) $request->get_param( 'remove_background' ) ?? true,
			'generate_scene'    => (bool) $request->get_param( 'generate_scene' ) ?? false,
			'upscale'           => (bool) $request->get_param( 'upscale' ) ?? true,
			'scene_prompt'      => sanitize_textarea_field( $request->get_param( 'scene_prompt' ) ?? '' ),
		);

		$batch_id = $this->bulk_processor->start_batch( $product_ids, $options );

		return rest_ensure_response(
			array(
				'batch_id' => $batch_id,
				'status'   => 'running',
				'total'    => count( $product_ids ),
			)
		);
	}

	/**
	 * GET /batch/{id}/status — get batch progress.
	 *
	 * @param WP_REST_Request $request The request.
	 * @return WP_REST_Response|WP_Error
	 */
	public function batch_status( $request ) {
		$batch_id = sanitize_text_field( $request->get_param( 'id' ) );
		$status   = $this->bulk_processor->get_batch_status( $batch_id );

		if ( null === $status ) {
			return new \WP_Error(
				'opal_batch_not_found',
				__( 'Batch not found.', 'opal-ai-photography' ),
				array( 'status' => 404 )
			);
		}

		return rest_ensure_response( $status );
	}

	// -------------------------------------------------------------------------
	// A/B test endpoints
	// -------------------------------------------------------------------------

	/**
	 * POST /ab-tests — create a new test.
	 *
	 * @param WP_REST_Request $request The request.
	 * @return WP_REST_Response|WP_Error
	 */
	public function create_ab_test( $request ) {
		$data = array(
			'product_id'         => $request->get_param( 'product_id' ),
			'name'               => $request->get_param( 'name' ),
			'variant_a_image_id' => $request->get_param( 'variant_a_image_id' ),
			'variant_b_image_id' => $request->get_param( 'variant_b_image_id' ),
		);

		$result = $this->ab_tests->create_test( $data );
		if ( is_wp_error( $result ) ) {
			return $result;
		}

		$test = $this->ab_tests->get_test( $result );
		return rest_ensure_response( $test );
	}

	/**
	 * GET /ab-tests — list all tests.
	 *
	 * @param WP_REST_Request $request The request.
	 * @return WP_REST_Response
	 */
	public function list_ab_tests( $request ) {
		$status = $request->get_param( 'status' );
		$tests  = $this->ab_tests->list_tests( $status );
		return rest_ensure_response( $tests );
	}

	/**
	 * POST /ab-tests/{id}/start — start a test.
	 *
	 * @param WP_REST_Request $request The request.
	 * @return WP_REST_Response|WP_Error
	 */
	public function start_ab_test( $request ) {
		$test_id = absint( $request->get_param( 'id' ) );
		$result  = $this->ab_tests->start_test( $test_id );

		if ( is_wp_error( $result ) ) {
			return $result;
		}

		$test = $this->ab_tests->get_test( $test_id );
		return rest_ensure_response( $test );
	}

	/**
	 * POST /ab-tests/{id}/conclude — conclude with a winner.
	 *
	 * @param WP_REST_Request $request The request.
	 * @return WP_REST_Response|WP_Error
	 */
	public function conclude_ab_test( $request ) {
		$test_id = absint( $request->get_param( 'id' ) );
		$winner  = $request->get_param( 'winner' );
		$result  = $this->ab_tests->conclude_test( $test_id, $winner );

		if ( is_wp_error( $result ) ) {
			return $result;
		}

		$test = $this->ab_tests->get_test( $test_id );
		return rest_ensure_response( $test );
	}

	/**
	 * POST /ab-tests/{id}/cancel — cancel a test.
	 *
	 * @param WP_REST_Request $request The request.
	 * @return WP_REST_Response|WP_Error
	 */
	public function cancel_ab_test( $request ) {
		$test_id = absint( $request->get_param( 'id' ) );
		$result  = $this->ab_tests->cancel_test( $test_id );

		if ( is_wp_error( $result ) ) {
			return $result;
		}

		$test = $this->ab_tests->get_test( $test_id );
		return rest_ensure_response( $test );
	}

	// -------------------------------------------------------------------------
	// Balance
	// -------------------------------------------------------------------------

	/**
	 * GET /balance — proxy to the Opal API.
	 *
	 * @return WP_REST_Response|WP_Error
	 */
	public function get_balance() {
		$result = $this->api_client->get_balance();
		if ( is_wp_error( $result ) ) {
			return $result;
		}
		return rest_ensure_response( $result );
	}

	// -------------------------------------------------------------------------
	// Tracking (public)
	// -------------------------------------------------------------------------

	/**
	 * POST /track-view — record a view event (public, nonce-verified).
	 *
	 * @param WP_REST_Request $request The request.
	 * @return WP_REST_Response
	 */
	public function track_view( $request ) {
		$test_id    = $request->get_param( 'test_id' );
		$variant    = strtoupper( $request->get_param( 'variant' ) );
		$event_type = $request->get_param( 'event_type' );

		if ( ! in_array( $variant, array( 'A', 'B' ), true ) ) {
			return rest_ensure_response( array( 'ok' => false ) );
		}

		if ( ! in_array( $event_type, array( 'view', 'add_to_cart', 'conversion' ), true ) ) {
			$event_type = 'view';
		}

		$this->ab_tracking->record_view( $test_id, $variant );

		return rest_ensure_response( array( 'ok' => true ) );
	}
}
