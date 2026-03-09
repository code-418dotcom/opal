<?php
/**
 * Frontend A/B test tracking.
 *
 * @package OpalAIPhotography
 */

defined( 'ABSPATH' ) || exit;

/**
 * Class Opal_AB_Tracking
 *
 * Handles cookie-based variant assignment, featured image swapping via
 * WooCommerce filters, and event tracking (views, add-to-cart, conversions).
 */
class Opal_AB_Tracking {

	/**
	 * Cookie lifetime in seconds (30 days).
	 *
	 * @var int
	 */
	const COOKIE_LIFETIME = 30 * DAY_IN_SECONDS;

	/**
	 * A/B tests instance.
	 *
	 * @var Opal_AB_Tests
	 */
	private $ab_tests;

	/**
	 * Cached running tests keyed by product_id.
	 *
	 * @var array|null
	 */
	private $running_tests = null;

	/**
	 * Constructor.
	 *
	 * @param Opal_AB_Tests $ab_tests A/B tests instance.
	 */
	public function __construct( Opal_AB_Tests $ab_tests ) {
		$this->ab_tests = $ab_tests;

		// Only run on the frontend.
		if ( is_admin() ) {
			return;
		}

		add_filter( 'woocommerce_product_get_image_id', array( $this, 'swap_featured_image' ), 10, 2 );
		add_action( 'wp_footer', array( $this, 'tracking_pixel' ) );
		add_action( 'woocommerce_add_to_cart', array( $this, 'track_add_to_cart' ), 10, 6 );
		add_action( 'woocommerce_thankyou', array( $this, 'track_conversion' ) );
	}

	/**
	 * Load running tests into the cache.
	 */
	private function load_running_tests() {
		if ( null !== $this->running_tests ) {
			return;
		}

		$this->running_tests = array();
		$tests = $this->ab_tests->list_tests( Opal_AB_Tests::STATUS_RUNNING, 100 );

		foreach ( $tests as $test ) {
			$pid = absint( $test['product_id'] );
			$this->running_tests[ $pid ] = $test;
		}
	}

	/**
	 * Get or assign a variant for a product.
	 *
	 * @param int $product_id The product ID.
	 * @return string 'A' or 'B'.
	 */
	private function get_variant( $product_id ) {
		$cookie_name = 'opal_ab_' . $product_id;

		if ( isset( $_COOKIE[ $cookie_name ] ) ) {
			$variant = sanitize_text_field( wp_unslash( $_COOKIE[ $cookie_name ] ) );
			if ( in_array( $variant, array( 'A', 'B' ), true ) ) {
				return $variant;
			}
		}

		// Random assignment: 50/50.
		$variant = ( wp_rand( 0, 1 ) === 0 ) ? 'A' : 'B';

		// Set the cookie (will be sent with the response).
		if ( ! headers_sent() ) {
			setcookie(
				$cookie_name,
				$variant,
				array(
					'expires'  => time() + self::COOKIE_LIFETIME,
					'path'     => COOKIEPATH,
					'domain'   => COOKIE_DOMAIN,
					'secure'   => is_ssl(),
					'httponly' => false,
					'samesite' => 'Lax',
				)
			);
		}

		// Also set in the superglobal for the current request.
		$_COOKIE[ $cookie_name ] = $variant;

		return $variant;
	}

	/**
	 * WooCommerce filter: swap the featured image based on variant assignment.
	 *
	 * @param int        $image_id The original image ID.
	 * @param WC_Product $product  The product instance.
	 * @return int The (possibly swapped) image ID.
	 */
	public function swap_featured_image( $image_id, $product ) {
		$this->load_running_tests();

		$product_id = $product->get_id();
		if ( ! isset( $this->running_tests[ $product_id ] ) ) {
			return $image_id;
		}

		$test    = $this->running_tests[ $product_id ];
		$variant = $this->get_variant( $product_id );

		if ( 'A' === $variant ) {
			return absint( $test['variant_a_image_id'] );
		}

		return absint( $test['variant_b_image_id'] );
	}

	/**
	 * Output the tracking pixel JavaScript in the footer.
	 *
	 * Records view events for products on the current page that have running tests.
	 */
	public function tracking_pixel() {
		$this->load_running_tests();

		if ( empty( $this->running_tests ) ) {
			return;
		}

		// Determine which products are visible on the current page.
		$track_products = array();

		if ( is_product() ) {
			global $product;
			if ( $product && isset( $this->running_tests[ $product->get_id() ] ) ) {
				$test    = $this->running_tests[ $product->get_id() ];
				$variant = $this->get_variant( $product->get_id() );
				$track_products[] = array(
					'test_id' => absint( $test['id'] ),
					'variant' => $variant,
				);
			}
		}

		if ( empty( $track_products ) ) {
			return;
		}

		$rest_url = rest_url( 'opal/v1/track-view' );
		$nonce    = wp_create_nonce( 'wp_rest' );

		?>
		<script>
		(function() {
			var tracked = <?php echo wp_json_encode( $track_products ); ?>;
			if (!tracked.length) return;

			tracked.forEach(function(item) {
				var xhr = new XMLHttpRequest();
				xhr.open('POST', <?php echo wp_json_encode( $rest_url ); ?>);
				xhr.setRequestHeader('Content-Type', 'application/json');
				xhr.setRequestHeader('X-WP-Nonce', <?php echo wp_json_encode( $nonce ); ?>);
				xhr.send(JSON.stringify({
					test_id: item.test_id,
					variant: item.variant,
					event_type: 'view'
				}));
			});
		})();
		</script>
		<?php
	}

	/**
	 * Track add-to-cart events.
	 *
	 * @param string $cart_item_key  Cart item key.
	 * @param int    $product_id     Product ID.
	 * @param int    $quantity       Quantity.
	 * @param int    $variation_id   Variation ID.
	 * @param array  $variation      Variation attributes.
	 * @param array  $cart_item_data Cart item data.
	 */
	public function track_add_to_cart( $cart_item_key, $product_id, $quantity, $variation_id, $variation, $cart_item_data ) {
		$this->load_running_tests();

		if ( ! isset( $this->running_tests[ $product_id ] ) ) {
			return;
		}

		$test    = $this->running_tests[ $product_id ];
		$variant = $this->get_variant( $product_id );

		$this->ab_tests->record_metric( absint( $test['id'] ), $variant, 'add_to_cart' );
	}

	/**
	 * Track conversion events on the thank-you page.
	 *
	 * @param int $order_id The order ID.
	 */
	public function track_conversion( $order_id ) {
		$this->load_running_tests();

		if ( empty( $this->running_tests ) ) {
			return;
		}

		$order = wc_get_order( $order_id );
		if ( ! $order ) {
			return;
		}

		// Avoid double-counting.
		if ( $order->get_meta( '_opal_ab_tracked' ) ) {
			return;
		}

		foreach ( $order->get_items() as $item ) {
			$product_id = $item->get_product_id();
			if ( ! isset( $this->running_tests[ $product_id ] ) ) {
				continue;
			}

			$test    = $this->running_tests[ $product_id ];
			$variant = $this->get_variant( $product_id );
			$revenue = (float) $item->get_total();

			$this->ab_tests->record_metric( absint( $test['id'] ), $variant, 'conversion', $revenue );
		}

		$order->update_meta_data( '_opal_ab_tracked', '1' );
		$order->save();
	}

	/**
	 * Record a view event (used by the REST endpoint).
	 *
	 * @param int    $test_id Test ID.
	 * @param string $variant 'A' or 'B'.
	 */
	public function record_view( $test_id, $variant ) {
		$this->ab_tests->record_metric( absint( $test_id ), $variant, 'view' );
	}
}
