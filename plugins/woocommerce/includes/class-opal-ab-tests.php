<?php
/**
 * A/B testing management.
 *
 * @package OpalAIPhotography
 */

defined( 'ABSPATH' ) || exit;

/**
 * Class Opal_AB_Tests
 *
 * Local A/B testing engine with custom WordPress tables, CRUD, significance
 * computation, and admin page rendering.
 */
class Opal_AB_Tests {

	/**
	 * Test statuses.
	 */
	const STATUS_DRAFT     = 'draft';
	const STATUS_RUNNING   = 'running';
	const STATUS_CONCLUDED = 'concluded';
	const STATUS_CANCELLED = 'cancelled';

	// -------------------------------------------------------------------------
	// Table creation (called on activation)
	// -------------------------------------------------------------------------

	/**
	 * Create the custom database tables.
	 */
	public static function create_tables() {
		global $wpdb;
		$charset = $wpdb->get_charset_collate();

		$tests_table   = $wpdb->prefix . 'opal_ab_tests';
		$metrics_table = $wpdb->prefix . 'opal_ab_metrics';

		$sql = "CREATE TABLE IF NOT EXISTS {$tests_table} (
			id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
			product_id BIGINT UNSIGNED NOT NULL,
			name VARCHAR(255) NOT NULL DEFAULT '',
			status VARCHAR(20) NOT NULL DEFAULT 'draft',
			variant_a_image_id BIGINT UNSIGNED NOT NULL DEFAULT 0,
			variant_b_image_id BIGINT UNSIGNED NOT NULL DEFAULT 0,
			original_image_id BIGINT UNSIGNED NOT NULL DEFAULT 0,
			winner VARCHAR(10) DEFAULT NULL,
			started_at DATETIME DEFAULT NULL,
			concluded_at DATETIME DEFAULT NULL,
			created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			PRIMARY KEY (id),
			KEY idx_product (product_id),
			KEY idx_status (status)
		) {$charset};

		CREATE TABLE IF NOT EXISTS {$metrics_table} (
			id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
			test_id BIGINT UNSIGNED NOT NULL,
			variant CHAR(1) NOT NULL,
			views INT UNSIGNED NOT NULL DEFAULT 0,
			add_to_carts INT UNSIGNED NOT NULL DEFAULT 0,
			conversions INT UNSIGNED NOT NULL DEFAULT 0,
			revenue DECIMAL(12,2) NOT NULL DEFAULT 0.00,
			updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
			PRIMARY KEY (id),
			UNIQUE KEY idx_test_variant (test_id, variant)
		) {$charset};";

		require_once ABSPATH . 'wp-admin/includes/upgrade.php';
		dbDelta( $sql );
	}

	// -------------------------------------------------------------------------
	// CRUD
	// -------------------------------------------------------------------------

	/**
	 * Create a new A/B test.
	 *
	 * @param array $data {product_id, name, variant_a_image_id, variant_b_image_id}.
	 * @return int|WP_Error The test ID, or WP_Error.
	 */
	public function create_test( $data ) {
		global $wpdb;

		$product_id = absint( $data['product_id'] ?? 0 );
		if ( ! $product_id ) {
			return new \WP_Error( 'opal_invalid_product', __( 'A valid product ID is required.', 'opal-ai-photography' ) );
		}

		$product = wc_get_product( $product_id );
		if ( ! $product ) {
			return new \WP_Error( 'opal_product_not_found', __( 'Product not found.', 'opal-ai-photography' ) );
		}

		$name       = sanitize_text_field( $data['name'] ?? '' );
		$variant_a  = absint( $data['variant_a_image_id'] ?? 0 );
		$variant_b  = absint( $data['variant_b_image_id'] ?? 0 );
		$original   = $product->get_image_id();

		if ( ! $variant_a || ! $variant_b ) {
			return new \WP_Error( 'opal_missing_variants', __( 'Both variant image IDs are required.', 'opal-ai-photography' ) );
		}

		$table = $wpdb->prefix . 'opal_ab_tests';

		// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery
		$inserted = $wpdb->insert(
			$table,
			array(
				'product_id'         => $product_id,
				'name'               => $name,
				'status'             => self::STATUS_DRAFT,
				'variant_a_image_id' => $variant_a,
				'variant_b_image_id' => $variant_b,
				'original_image_id'  => $original ? $original : 0,
				'created_at'         => current_time( 'mysql' ),
			),
			array( '%d', '%s', '%s', '%d', '%d', '%d', '%s' )
		);

		if ( false === $inserted ) {
			return new \WP_Error( 'opal_db_error', __( 'Failed to create test.', 'opal-ai-photography' ) );
		}

		$test_id = (int) $wpdb->insert_id;

		// Initialize metrics rows.
		$metrics_table = $wpdb->prefix . 'opal_ab_metrics';
		foreach ( array( 'A', 'B' ) as $variant ) {
			// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery
			$wpdb->insert(
				$metrics_table,
				array(
					'test_id' => $test_id,
					'variant' => $variant,
				),
				array( '%d', '%s' )
			);
		}

		return $test_id;
	}

	/**
	 * Get a single test by ID.
	 *
	 * @param int $test_id The test ID.
	 * @return array|null Test data with metrics, or null.
	 */
	public function get_test( $test_id ) {
		global $wpdb;
		$table = $wpdb->prefix . 'opal_ab_tests';

		// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching
		$test = $wpdb->get_row(
			$wpdb->prepare( "SELECT * FROM {$table} WHERE id = %d", absint( $test_id ) ),
			ARRAY_A
		);

		if ( ! $test ) {
			return null;
		}

		$test['metrics'] = $this->get_metrics( $test_id );
		$test['significance'] = $this->compute_significance( $test_id );

		return $test;
	}

	/**
	 * List all tests, optionally filtered by status.
	 *
	 * @param string|null $status Filter by status, or null for all.
	 * @param int         $limit  Maximum results.
	 * @param int         $offset Offset for pagination.
	 * @return array
	 */
	public function list_tests( $status = null, $limit = 50, $offset = 0 ) {
		global $wpdb;
		$table = $wpdb->prefix . 'opal_ab_tests';

		if ( $status ) {
			// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching
			$tests = $wpdb->get_results(
				$wpdb->prepare(
					"SELECT * FROM {$table} WHERE status = %s ORDER BY created_at DESC LIMIT %d OFFSET %d",
					sanitize_text_field( $status ),
					absint( $limit ),
					absint( $offset )
				),
				ARRAY_A
			);
		} else {
			// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching
			$tests = $wpdb->get_results(
				$wpdb->prepare(
					"SELECT * FROM {$table} ORDER BY created_at DESC LIMIT %d OFFSET %d",
					absint( $limit ),
					absint( $offset )
				),
				ARRAY_A
			);
		}

		foreach ( $tests as &$test ) {
			$test['metrics'] = $this->get_metrics( (int) $test['id'] );
		}

		return $tests;
	}

	/**
	 * Count active (running) tests.
	 *
	 * @return int
	 */
	public function count_active() {
		global $wpdb;
		$table = $wpdb->prefix . 'opal_ab_tests';

		// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching
		return (int) $wpdb->get_var(
			$wpdb->prepare( "SELECT COUNT(*) FROM {$table} WHERE status = %s", self::STATUS_RUNNING )
		);
	}

	/**
	 * Start a test (set status to running).
	 *
	 * @param int $test_id Test ID.
	 * @return bool|WP_Error
	 */
	public function start_test( $test_id ) {
		global $wpdb;
		$test = $this->get_test( $test_id );
		if ( ! $test ) {
			return new \WP_Error( 'opal_test_not_found', __( 'Test not found.', 'opal-ai-photography' ) );
		}
		if ( self::STATUS_DRAFT !== $test['status'] ) {
			return new \WP_Error( 'opal_invalid_status', __( 'Only draft tests can be started.', 'opal-ai-photography' ) );
		}

		$table = $wpdb->prefix . 'opal_ab_tests';
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery
		$wpdb->update(
			$table,
			array(
				'status'     => self::STATUS_RUNNING,
				'started_at' => current_time( 'mysql' ),
			),
			array( 'id' => absint( $test_id ) ),
			array( '%s', '%s' ),
			array( '%d' )
		);

		return true;
	}

	/**
	 * Conclude a test with a winner.
	 *
	 * @param int    $test_id Test ID.
	 * @param string $winner  'A' or 'B'.
	 * @return bool|WP_Error
	 */
	public function conclude_test( $test_id, $winner ) {
		global $wpdb;

		$winner = strtoupper( sanitize_text_field( $winner ) );
		if ( ! in_array( $winner, array( 'A', 'B' ), true ) ) {
			return new \WP_Error( 'opal_invalid_winner', __( 'Winner must be A or B.', 'opal-ai-photography' ) );
		}

		$test = $this->get_test( $test_id );
		if ( ! $test ) {
			return new \WP_Error( 'opal_test_not_found', __( 'Test not found.', 'opal-ai-photography' ) );
		}
		if ( self::STATUS_RUNNING !== $test['status'] ) {
			return new \WP_Error( 'opal_invalid_status', __( 'Only running tests can be concluded.', 'opal-ai-photography' ) );
		}

		$table = $wpdb->prefix . 'opal_ab_tests';
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery
		$wpdb->update(
			$table,
			array(
				'status'       => self::STATUS_CONCLUDED,
				'winner'       => $winner,
				'concluded_at' => current_time( 'mysql' ),
			),
			array( 'id' => absint( $test_id ) ),
			array( '%s', '%s', '%s' ),
			array( '%d' )
		);

		// Apply the winning image as the product's featured image.
		$winning_image = 'A' === $winner
			? absint( $test['variant_a_image_id'] )
			: absint( $test['variant_b_image_id'] );

		$product = wc_get_product( absint( $test['product_id'] ) );
		if ( $product && $winning_image ) {
			$product->set_image_id( $winning_image );
			$product->save();
		}

		return true;
	}

	/**
	 * Cancel a test.
	 *
	 * @param int $test_id Test ID.
	 * @return bool|WP_Error
	 */
	public function cancel_test( $test_id ) {
		global $wpdb;

		$test = $this->get_test( $test_id );
		if ( ! $test ) {
			return new \WP_Error( 'opal_test_not_found', __( 'Test not found.', 'opal-ai-photography' ) );
		}

		if ( in_array( $test['status'], array( self::STATUS_CONCLUDED, self::STATUS_CANCELLED ), true ) ) {
			return new \WP_Error( 'opal_invalid_status', __( 'This test is already finished.', 'opal-ai-photography' ) );
		}

		$table = $wpdb->prefix . 'opal_ab_tests';
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery
		$wpdb->update(
			$table,
			array( 'status' => self::STATUS_CANCELLED ),
			array( 'id' => absint( $test_id ) ),
			array( '%s' ),
			array( '%d' )
		);

		// Restore original image.
		if ( ! empty( $test['original_image_id'] ) ) {
			$product = wc_get_product( absint( $test['product_id'] ) );
			if ( $product ) {
				$product->set_image_id( absint( $test['original_image_id'] ) );
				$product->save();
			}
		}

		return true;
	}

	// -------------------------------------------------------------------------
	// Metrics
	// -------------------------------------------------------------------------

	/**
	 * Get metrics for a test.
	 *
	 * @param int $test_id Test ID.
	 * @return array Keyed by variant (A, B).
	 */
	public function get_metrics( $test_id ) {
		global $wpdb;
		$table = $wpdb->prefix . 'opal_ab_metrics';

		// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching
		$rows = $wpdb->get_results(
			$wpdb->prepare( "SELECT * FROM {$table} WHERE test_id = %d", absint( $test_id ) ),
			ARRAY_A
		);

		$metrics = array();
		foreach ( $rows as $row ) {
			$metrics[ $row['variant'] ] = array(
				'views'        => (int) $row['views'],
				'add_to_carts' => (int) $row['add_to_carts'],
				'conversions'  => (int) $row['conversions'],
				'revenue'      => (float) $row['revenue'],
			);
		}

		return $metrics;
	}

	/**
	 * Record a metric event for a test variant.
	 *
	 * @param int    $test_id    Test ID.
	 * @param string $variant    'A' or 'B'.
	 * @param string $event_type 'view', 'add_to_cart', or 'conversion'.
	 * @param float  $revenue    Optional revenue for conversion events.
	 */
	public function record_metric( $test_id, $variant, $event_type, $revenue = 0.0 ) {
		global $wpdb;
		$table   = $wpdb->prefix . 'opal_ab_metrics';
		$variant = strtoupper( sanitize_text_field( $variant ) );

		if ( ! in_array( $variant, array( 'A', 'B' ), true ) ) {
			return;
		}

		$column = '';
		switch ( $event_type ) {
			case 'view':
				$column = 'views';
				break;
			case 'add_to_cart':
				$column = 'add_to_carts';
				break;
			case 'conversion':
				$column = 'conversions';
				break;
			default:
				return;
		}

		// Atomic increment.
		if ( 'conversion' === $event_type && $revenue > 0 ) {
			// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching
			$wpdb->query(
				$wpdb->prepare(
					"UPDATE {$table} SET {$column} = {$column} + 1, revenue = revenue + %f WHERE test_id = %d AND variant = %s",
					floatval( $revenue ),
					absint( $test_id ),
					$variant
				)
			);
		} else {
			// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching
			$wpdb->query(
				$wpdb->prepare(
					"UPDATE {$table} SET {$column} = {$column} + 1 WHERE test_id = %d AND variant = %s",
					absint( $test_id ),
					$variant
				)
			);
		}
	}

	// -------------------------------------------------------------------------
	// Significance computation (Z-test)
	// -------------------------------------------------------------------------

	/**
	 * Compute statistical significance for a test.
	 *
	 * @param int $test_id Test ID.
	 * @return array|null {z_score, p_value, significant, lift_percent, conversion_rate_a, conversion_rate_b}
	 */
	public function compute_significance( $test_id ) {
		$metrics = $this->get_metrics( $test_id );
		if ( empty( $metrics['A'] ) || empty( $metrics['B'] ) ) {
			return null;
		}

		$views_a       = $metrics['A']['views'];
		$views_b       = $metrics['B']['views'];
		$conversions_a = $metrics['A']['conversions'];
		$conversions_b = $metrics['B']['conversions'];

		if ( $views_a < 1 || $views_b < 1 ) {
			return null;
		}

		$rate_a = $conversions_a / $views_a;
		$rate_b = $conversions_b / $views_b;

		// Pooled proportion.
		$total_conversions = $conversions_a + $conversions_b;
		$total_views       = $views_a + $views_b;

		if ( $total_views < 1 ) {
			return null;
		}

		$pooled = $total_conversions / $total_views;

		// Standard error.
		$se_denom = $pooled * ( 1 - $pooled );
		if ( $se_denom <= 0 ) {
			return array(
				'z_score'            => 0.0,
				'p_value'            => 1.0,
				'significant'        => false,
				'lift_percent'       => 0.0,
				'conversion_rate_a'  => $rate_a,
				'conversion_rate_b'  => $rate_b,
			);
		}

		$se = sqrt( $se_denom * ( ( 1 / $views_a ) + ( 1 / $views_b ) ) );

		if ( $se <= 0 ) {
			return array(
				'z_score'            => 0.0,
				'p_value'            => 1.0,
				'significant'        => false,
				'lift_percent'       => 0.0,
				'conversion_rate_a'  => $rate_a,
				'conversion_rate_b'  => $rate_b,
			);
		}

		$z_score = ( $rate_b - $rate_a ) / $se;

		// Two-tailed p-value approximation using the error function.
		$p_value = 2.0 * ( 1.0 - $this->normal_cdf( abs( $z_score ) ) );

		$lift = ( $rate_a > 0 ) ? ( ( $rate_b - $rate_a ) / $rate_a ) * 100.0 : 0.0;

		return array(
			'z_score'           => round( $z_score, 4 ),
			'p_value'           => round( $p_value, 6 ),
			'significant'       => $p_value < 0.05,
			'lift_percent'      => round( $lift, 2 ),
			'conversion_rate_a' => round( $rate_a, 6 ),
			'conversion_rate_b' => round( $rate_b, 6 ),
		);
	}

	/**
	 * Normal CDF approximation (Abramowitz & Stegun).
	 *
	 * @param float $x The value.
	 * @return float
	 */
	private function normal_cdf( $x ) {
		$a1 = 0.254829592;
		$a2 = -0.284496736;
		$a3 = 1.421413741;
		$a4 = -1.453152027;
		$a5 = 1.061405429;
		$p  = 0.3275911;

		$sign = ( $x < 0 ) ? -1 : 1;
		$x    = abs( $x ) / sqrt( 2 );

		$t   = 1.0 / ( 1.0 + $p * $x );
		$y   = 1.0 - ( ( ( ( ( $a5 * $t + $a4 ) * $t ) + $a3 ) * $t + $a2 ) * $t + $a1 ) * $t * exp( -$x * $x );

		return 0.5 * ( 1.0 + $sign * $y );
	}

	// -------------------------------------------------------------------------
	// Admin page rendering
	// -------------------------------------------------------------------------

	/**
	 * Render the A/B tests admin page content.
	 */
	public function render_admin_page() {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended
		$action = isset( $_GET['opal_action'] ) ? sanitize_text_field( wp_unslash( $_GET['opal_action'] ) ) : 'list';
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended
		$test_id = isset( $_GET['test_id'] ) ? absint( $_GET['test_id'] ) : 0;

		switch ( $action ) {
			case 'view':
				if ( $test_id ) {
					$this->render_test_detail( $test_id );
				}
				break;
			case 'create':
				$this->render_create_form();
				break;
			default:
				$this->render_test_list();
				break;
		}
	}

	/**
	 * Render the test list.
	 */
	private function render_test_list() {
		$tests = $this->list_tests();
		$create_url = admin_url( 'admin.php?page=opal-ai&tab=ab-tests&opal_action=create' );

		?>
		<h2>
			<?php echo esc_html__( 'A/B Image Tests', 'opal-ai-photography' ); ?>
			<a href="<?php echo esc_url( $create_url ); ?>" class="page-title-action"><?php echo esc_html__( 'Create New Test', 'opal-ai-photography' ); ?></a>
		</h2>

		<?php if ( empty( $tests ) ) : ?>
			<p><?php echo esc_html__( 'No A/B tests yet. Create one to start comparing product images.', 'opal-ai-photography' ); ?></p>
		<?php else : ?>
			<table class="widefat striped">
				<thead>
					<tr>
						<th><?php echo esc_html__( 'Name', 'opal-ai-photography' ); ?></th>
						<th><?php echo esc_html__( 'Product', 'opal-ai-photography' ); ?></th>
						<th><?php echo esc_html__( 'Status', 'opal-ai-photography' ); ?></th>
						<th><?php echo esc_html__( 'Views (A / B)', 'opal-ai-photography' ); ?></th>
						<th><?php echo esc_html__( 'Conversions (A / B)', 'opal-ai-photography' ); ?></th>
						<th><?php echo esc_html__( 'Winner', 'opal-ai-photography' ); ?></th>
						<th><?php echo esc_html__( 'Created', 'opal-ai-photography' ); ?></th>
						<th></th>
					</tr>
				</thead>
				<tbody>
					<?php foreach ( $tests as $test ) :
						$product = wc_get_product( $test['product_id'] );
						$m       = $test['metrics'] ?? array();
						$views_a = $m['A']['views'] ?? 0;
						$views_b = $m['B']['views'] ?? 0;
						$conv_a  = $m['A']['conversions'] ?? 0;
						$conv_b  = $m['B']['conversions'] ?? 0;
						$detail_url = admin_url( 'admin.php?page=opal-ai&tab=ab-tests&opal_action=view&test_id=' . $test['id'] );
						?>
						<tr>
							<td><a href="<?php echo esc_url( $detail_url ); ?>"><?php echo esc_html( $test['name'] ?: '#' . $test['id'] ); ?></a></td>
							<td><?php echo $product ? esc_html( $product->get_name() ) : '#' . esc_html( $test['product_id'] ); ?></td>
							<td><?php echo esc_html( ucfirst( $test['status'] ) ); ?></td>
							<td><?php echo esc_html( $views_a . ' / ' . $views_b ); ?></td>
							<td><?php echo esc_html( $conv_a . ' / ' . $conv_b ); ?></td>
							<td><?php echo $test['winner'] ? esc_html( 'Variant ' . $test['winner'] ) : '&mdash;'; ?></td>
							<td><?php echo esc_html( $test['created_at'] ); ?></td>
							<td><a href="<?php echo esc_url( $detail_url ); ?>" class="button button-small"><?php echo esc_html__( 'View', 'opal-ai-photography' ); ?></a></td>
						</tr>
					<?php endforeach; ?>
				</tbody>
			</table>
		<?php endif;
	}

	/**
	 * Render the create test form.
	 */
	private function render_create_form() {
		$products = wc_get_products( array(
			'status' => 'publish',
			'limit'  => 200,
			'return' => 'objects',
		) );

		?>
		<h2><?php echo esc_html__( 'Create A/B Test', 'opal-ai-photography' ); ?></h2>
		<form id="opal-create-ab-test">
			<?php wp_nonce_field( 'wp_rest', '_wpnonce' ); ?>
			<table class="form-table">
				<tr>
					<th><label for="opal-ab-name"><?php echo esc_html__( 'Test Name', 'opal-ai-photography' ); ?></label></th>
					<td><input type="text" id="opal-ab-name" name="name" class="regular-text" /></td>
				</tr>
				<tr>
					<th><label for="opal-ab-product"><?php echo esc_html__( 'Product', 'opal-ai-photography' ); ?></label></th>
					<td>
						<select id="opal-ab-product" name="product_id">
							<option value=""><?php echo esc_html__( 'Select a product', 'opal-ai-photography' ); ?></option>
							<?php foreach ( $products as $product ) : ?>
								<option value="<?php echo esc_attr( $product->get_id() ); ?>">
									<?php echo esc_html( $product->get_name() ); ?>
								</option>
							<?php endforeach; ?>
						</select>
					</td>
				</tr>
				<tr>
					<th><label for="opal-ab-variant-a"><?php echo esc_html__( 'Variant A Image ID', 'opal-ai-photography' ); ?></label></th>
					<td>
						<input type="number" id="opal-ab-variant-a" name="variant_a_image_id" class="small-text" />
						<p class="description"><?php echo esc_html__( 'WordPress media library attachment ID for variant A.', 'opal-ai-photography' ); ?></p>
					</td>
				</tr>
				<tr>
					<th><label for="opal-ab-variant-b"><?php echo esc_html__( 'Variant B Image ID', 'opal-ai-photography' ); ?></label></th>
					<td>
						<input type="number" id="opal-ab-variant-b" name="variant_b_image_id" class="small-text" />
						<p class="description"><?php echo esc_html__( 'WordPress media library attachment ID for variant B.', 'opal-ai-photography' ); ?></p>
					</td>
				</tr>
			</table>
			<p>
				<button type="button" id="opal-create-test-btn" class="button button-primary"><?php echo esc_html__( 'Create Test', 'opal-ai-photography' ); ?></button>
			</p>
		</form>
		<?php
	}

	/**
	 * Render the detail view for a single test.
	 *
	 * @param int $test_id Test ID.
	 */
	private function render_test_detail( $test_id ) {
		$test = $this->get_test( $test_id );
		if ( ! $test ) {
			echo '<p>' . esc_html__( 'Test not found.', 'opal-ai-photography' ) . '</p>';
			return;
		}

		$product = wc_get_product( $test['product_id'] );
		$m       = $test['metrics'] ?? array();
		$sig     = $test['significance'];
		$back    = admin_url( 'admin.php?page=opal-ai&tab=ab-tests' );

		?>
		<p><a href="<?php echo esc_url( $back ); ?>">&larr; <?php echo esc_html__( 'Back to list', 'opal-ai-photography' ); ?></a></p>

		<h2><?php echo esc_html( $test['name'] ?: __( 'A/B Test', 'opal-ai-photography' ) . ' #' . $test['id'] ); ?></h2>

		<div style="display:grid; grid-template-columns:1fr 1fr; gap:20px; max-width:800px;">
			<!-- Variant A -->
			<div style="background:#fff; border:1px solid #ccd0d4; padding:15px; border-radius:4px; text-align:center;">
				<h3><?php echo esc_html__( 'Variant A', 'opal-ai-photography' ); ?></h3>
				<?php echo wp_get_attachment_image( absint( $test['variant_a_image_id'] ), 'medium', false, array( 'style' => 'max-width:100%;height:auto;' ) ); ?>
				<table class="widefat" style="margin-top:10px;">
					<tr><td><?php echo esc_html__( 'Views', 'opal-ai-photography' ); ?></td><td><strong><?php echo esc_html( $m['A']['views'] ?? 0 ); ?></strong></td></tr>
					<tr><td><?php echo esc_html__( 'Add to Carts', 'opal-ai-photography' ); ?></td><td><strong><?php echo esc_html( $m['A']['add_to_carts'] ?? 0 ); ?></strong></td></tr>
					<tr><td><?php echo esc_html__( 'Conversions', 'opal-ai-photography' ); ?></td><td><strong><?php echo esc_html( $m['A']['conversions'] ?? 0 ); ?></strong></td></tr>
					<tr><td><?php echo esc_html__( 'Revenue', 'opal-ai-photography' ); ?></td><td><strong><?php echo esc_html( wc_price( $m['A']['revenue'] ?? 0 ) ); ?></strong></td></tr>
				</table>
			</div>

			<!-- Variant B -->
			<div style="background:#fff; border:1px solid #ccd0d4; padding:15px; border-radius:4px; text-align:center;">
				<h3><?php echo esc_html__( 'Variant B', 'opal-ai-photography' ); ?></h3>
				<?php echo wp_get_attachment_image( absint( $test['variant_b_image_id'] ), 'medium', false, array( 'style' => 'max-width:100%;height:auto;' ) ); ?>
				<table class="widefat" style="margin-top:10px;">
					<tr><td><?php echo esc_html__( 'Views', 'opal-ai-photography' ); ?></td><td><strong><?php echo esc_html( $m['B']['views'] ?? 0 ); ?></strong></td></tr>
					<tr><td><?php echo esc_html__( 'Add to Carts', 'opal-ai-photography' ); ?></td><td><strong><?php echo esc_html( $m['B']['add_to_carts'] ?? 0 ); ?></strong></td></tr>
					<tr><td><?php echo esc_html__( 'Conversions', 'opal-ai-photography' ); ?></td><td><strong><?php echo esc_html( $m['B']['conversions'] ?? 0 ); ?></strong></td></tr>
					<tr><td><?php echo esc_html__( 'Revenue', 'opal-ai-photography' ); ?></td><td><strong><?php echo esc_html( wc_price( $m['B']['revenue'] ?? 0 ) ); ?></strong></td></tr>
				</table>
			</div>
		</div>

		<!-- Significance -->
		<?php if ( $sig ) : ?>
			<div style="background:#fff; border:1px solid #ccd0d4; padding:15px; border-radius:4px; margin-top:20px; max-width:800px;">
				<h3><?php echo esc_html__( 'Statistical Significance', 'opal-ai-photography' ); ?></h3>
				<table class="widefat">
					<tr>
						<td><?php echo esc_html__( 'Z-Score', 'opal-ai-photography' ); ?></td>
						<td><strong><?php echo esc_html( $sig['z_score'] ); ?></strong></td>
					</tr>
					<tr>
						<td><?php echo esc_html__( 'P-Value', 'opal-ai-photography' ); ?></td>
						<td><strong><?php echo esc_html( $sig['p_value'] ); ?></strong></td>
					</tr>
					<tr>
						<td><?php echo esc_html__( 'Significant (p < 0.05)', 'opal-ai-photography' ); ?></td>
						<td>
							<strong style="color:<?php echo esc_attr( $sig['significant'] ? '#00a32a' : '#d63638' ); ?>;">
								<?php echo $sig['significant'] ? esc_html__( 'Yes', 'opal-ai-photography' ) : esc_html__( 'No', 'opal-ai-photography' ); ?>
							</strong>
						</td>
					</tr>
					<tr>
						<td><?php echo esc_html__( 'Lift (B vs A)', 'opal-ai-photography' ); ?></td>
						<td><strong><?php echo esc_html( $sig['lift_percent'] . '%' ); ?></strong></td>
					</tr>
				</table>
			</div>
		<?php endif; ?>

		<!-- Actions -->
		<?php if ( self::STATUS_DRAFT === $test['status'] || self::STATUS_RUNNING === $test['status'] ) : ?>
			<div style="margin-top:20px;">
				<?php if ( self::STATUS_DRAFT === $test['status'] ) : ?>
					<button type="button" class="button button-primary opal-ab-action" data-action="start" data-test-id="<?php echo esc_attr( $test['id'] ); ?>">
						<?php echo esc_html__( 'Start Test', 'opal-ai-photography' ); ?>
					</button>
				<?php endif; ?>

				<?php if ( self::STATUS_RUNNING === $test['status'] ) : ?>
					<button type="button" class="button button-primary opal-ab-action" data-action="conclude" data-test-id="<?php echo esc_attr( $test['id'] ); ?>" data-winner="A">
						<?php echo esc_html__( 'Declare A Winner', 'opal-ai-photography' ); ?>
					</button>
					<button type="button" class="button button-primary opal-ab-action" data-action="conclude" data-test-id="<?php echo esc_attr( $test['id'] ); ?>" data-winner="B">
						<?php echo esc_html__( 'Declare B Winner', 'opal-ai-photography' ); ?>
					</button>
				<?php endif; ?>

				<button type="button" class="button opal-ab-action" data-action="cancel" data-test-id="<?php echo esc_attr( $test['id'] ); ?>">
					<?php echo esc_html__( 'Cancel Test', 'opal-ai-photography' ); ?>
				</button>
			</div>
		<?php endif; ?>

		<?php if ( self::STATUS_CONCLUDED === $test['status'] ) : ?>
			<div style="margin-top:20px; padding:15px; background:#d4edda; border:1px solid #c3e6cb; border-radius:4px; max-width:800px;">
				<strong>
					<?php
					printf(
						/* translators: %s: winning variant letter */
						esc_html__( 'Winner: Variant %s', 'opal-ai-photography' ),
						esc_html( $test['winner'] )
					);
					?>
				</strong>
				&mdash;
				<?php
				printf(
					/* translators: %s: date */
					esc_html__( 'Concluded on %s', 'opal-ai-photography' ),
					esc_html( $test['concluded_at'] )
				);
				?>
			</div>
		<?php endif; ?>

		<div style="margin-top:20px;">
			<p>
				<strong><?php echo esc_html__( 'Product:', 'opal-ai-photography' ); ?></strong>
				<?php echo $product ? esc_html( $product->get_name() ) : '#' . esc_html( $test['product_id'] ); ?>
			</p>
			<p>
				<strong><?php echo esc_html__( 'Status:', 'opal-ai-photography' ); ?></strong>
				<?php echo esc_html( ucfirst( $test['status'] ) ); ?>
			</p>
			<p>
				<strong><?php echo esc_html__( 'Created:', 'opal-ai-photography' ); ?></strong>
				<?php echo esc_html( $test['created_at'] ); ?>
			</p>
		</div>
		<?php
	}
}
