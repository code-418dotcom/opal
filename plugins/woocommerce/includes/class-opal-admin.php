<?php
/**
 * Admin pages and menu.
 *
 * @package OpalAIPhotography
 */

defined( 'ABSPATH' ) || exit;

/**
 * Class Opal_Admin
 *
 * Registers the top-level "Opal AI" menu, renders the tabbed admin interface,
 * adds the admin bar balance widget, and adds a product list column.
 */
class Opal_Admin {

	/**
	 * API client.
	 *
	 * @var Opal_API_Client
	 */
	private $api_client;

	/**
	 * Settings instance.
	 *
	 * @var Opal_Settings
	 */
	private $settings;

	/**
	 * A/B tests instance.
	 *
	 * @var Opal_AB_Tests
	 */
	private $ab_tests;

	/**
	 * Constructor.
	 *
	 * @param Opal_API_Client $api_client API client.
	 * @param Opal_Settings   $settings   Settings.
	 * @param Opal_AB_Tests   $ab_tests   A/B tests.
	 */
	public function __construct( Opal_API_Client $api_client, Opal_Settings $settings, Opal_AB_Tests $ab_tests ) {
		$this->api_client = $api_client;
		$this->settings   = $settings;
		$this->ab_tests   = $ab_tests;

		add_action( 'admin_menu', array( $this, 'register_menu' ) );
		add_action( 'admin_bar_menu', array( $this, 'admin_bar_balance' ), 100 );
		add_filter( 'manage_edit-product_columns', array( $this, 'add_product_column' ) );
		add_action( 'manage_product_posts_custom_column', array( $this, 'render_product_column' ), 10, 2 );
	}

	/**
	 * Register the top-level admin menu.
	 */
	public function register_menu() {
		$icon_svg = 'data:image/svg+xml;base64,' . base64_encode(
			'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>'
		);

		add_menu_page(
			__( 'Opal AI Photography', 'opal-ai-photography' ),
			__( 'Opal AI', 'opal-ai-photography' ),
			'manage_woocommerce',
			'opal-ai',
			array( $this, 'render_admin_page' ),
			$icon_svg,
			56
		);
	}

	/**
	 * Render the tabbed admin page.
	 */
	public function render_admin_page() {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended
		$current_tab = isset( $_GET['tab'] ) ? sanitize_text_field( wp_unslash( $_GET['tab'] ) ) : 'dashboard';

		$tabs = array(
			'dashboard' => __( 'Dashboard', 'opal-ai-photography' ),
			'bulk'      => __( 'Bulk Process', 'opal-ai-photography' ),
			'ab-tests'  => __( 'A/B Tests', 'opal-ai-photography' ),
			'settings'  => __( 'Settings', 'opal-ai-photography' ),
		);

		?>
		<div class="wrap opal-admin-wrap">
			<h1><?php echo esc_html__( 'Opal AI Product Photography', 'opal-ai-photography' ); ?></h1>

			<nav class="nav-tab-wrapper">
				<?php foreach ( $tabs as $slug => $label ) : ?>
					<a href="<?php echo esc_url( admin_url( 'admin.php?page=opal-ai&tab=' . $slug ) ); ?>"
					   class="nav-tab <?php echo $slug === $current_tab ? 'nav-tab-active' : ''; ?>">
						<?php echo esc_html( $label ); ?>
					</a>
				<?php endforeach; ?>
			</nav>

			<div class="opal-tab-content" style="margin-top:20px;">
				<?php
				switch ( $current_tab ) {
					case 'bulk':
						$this->render_bulk_tab();
						break;
					case 'ab-tests':
						$this->render_ab_tests_tab();
						break;
					case 'settings':
						$this->settings->render_settings_tab();
						break;
					default:
						$this->render_dashboard_tab();
						break;
				}
				?>
			</div>
		</div>
		<?php
	}

	// -------------------------------------------------------------------------
	// Dashboard tab
	// -------------------------------------------------------------------------

	/**
	 * Render the dashboard tab.
	 */
	private function render_dashboard_tab() {
		$balance_data = $this->get_cached_balance();
		$balance      = is_wp_error( $balance_data ) ? null : ( $balance_data['token_balance'] ?? null );
		$recent_jobs  = $this->get_recent_jobs();
		$stats        = $this->get_quick_stats();

		?>
		<div class="opal-dashboard-grid" style="display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:20px;">
			<!-- Token Balance Card -->
			<div class="opal-card" style="background:#fff; border:1px solid #ccd0d4; padding:20px; border-radius:4px;">
				<h3 style="margin-top:0;"><?php echo esc_html__( 'Token Balance', 'opal-ai-photography' ); ?></h3>
				<?php if ( null !== $balance ) : ?>
					<p style="font-size:2em; font-weight:bold; color:#2271b1; margin:10px 0;">
						<?php echo esc_html( number_format_i18n( $balance ) ); ?>
					</p>
					<p class="description"><?php echo esc_html__( 'tokens remaining', 'opal-ai-photography' ); ?></p>
				<?php else : ?>
					<p style="color:#d63638;">
						<?php echo esc_html__( 'Could not retrieve balance. Check your API settings.', 'opal-ai-photography' ); ?>
					</p>
				<?php endif; ?>
			</div>

			<!-- Quick Stats Card -->
			<div class="opal-card" style="background:#fff; border:1px solid #ccd0d4; padding:20px; border-radius:4px;">
				<h3 style="margin-top:0;"><?php echo esc_html__( 'Quick Stats', 'opal-ai-photography' ); ?></h3>
				<table class="widefat striped" style="border:0;">
					<tr>
						<td><?php echo esc_html__( 'Products processed', 'opal-ai-photography' ); ?></td>
						<td><strong><?php echo esc_html( number_format_i18n( $stats['processed'] ) ); ?></strong></td>
					</tr>
					<tr>
						<td><?php echo esc_html__( 'Total products', 'opal-ai-photography' ); ?></td>
						<td><strong><?php echo esc_html( number_format_i18n( $stats['total'] ) ); ?></strong></td>
					</tr>
					<tr>
						<td><?php echo esc_html__( 'Active A/B tests', 'opal-ai-photography' ); ?></td>
						<td><strong><?php echo esc_html( number_format_i18n( $stats['ab_tests'] ) ); ?></strong></td>
					</tr>
				</table>
			</div>

			<!-- Recent Jobs Card -->
			<div class="opal-card" style="background:#fff; border:1px solid #ccd0d4; padding:20px; border-radius:4px; grid-column:1/-1;">
				<h3 style="margin-top:0;"><?php echo esc_html__( 'Recent Jobs', 'opal-ai-photography' ); ?></h3>
				<?php if ( empty( $recent_jobs ) ) : ?>
					<p><?php echo esc_html__( 'No recent processing jobs.', 'opal-ai-photography' ); ?></p>
				<?php else : ?>
					<table class="widefat striped">
						<thead>
							<tr>
								<th><?php echo esc_html__( 'Product', 'opal-ai-photography' ); ?></th>
								<th><?php echo esc_html__( 'Job ID', 'opal-ai-photography' ); ?></th>
								<th><?php echo esc_html__( 'Status', 'opal-ai-photography' ); ?></th>
								<th><?php echo esc_html__( 'Date', 'opal-ai-photography' ); ?></th>
							</tr>
						</thead>
						<tbody>
							<?php foreach ( $recent_jobs as $job ) : ?>
								<tr>
									<td>
										<?php
										if ( ! empty( $job['product_id'] ) ) {
											$product = wc_get_product( $job['product_id'] );
											echo $product ? esc_html( $product->get_name() ) : '#' . esc_html( $job['product_id'] );
										} else {
											echo '&mdash;';
										}
										?>
									</td>
									<td><code><?php echo esc_html( $job['job_id'] ?? '' ); ?></code></td>
									<td>
										<?php
										$status_label = $job['status'] ?? 'unknown';
										$status_class = 'pending' === $status_label ? 'warning' : ( 'completed' === $status_label ? 'success' : 'error' );
										printf(
											'<span class="opal-status opal-status--%s">%s</span>',
											esc_attr( $status_class ),
											esc_html( ucfirst( $status_label ) )
										);
										?>
									</td>
									<td><?php echo esc_html( $job['date'] ?? '' ); ?></td>
								</tr>
							<?php endforeach; ?>
						</tbody>
					</table>
				<?php endif; ?>
			</div>
		</div>
		<?php
	}

	// -------------------------------------------------------------------------
	// Bulk Process tab
	// -------------------------------------------------------------------------

	/**
	 * Render the bulk processing tab.
	 */
	private function render_bulk_tab() {
		$products = wc_get_products(
			array(
				'status' => 'publish',
				'limit'  => 200,
				'return' => 'objects',
			)
		);

		?>
		<div class="opal-bulk-wrap">
			<h2><?php echo esc_html__( 'Bulk Image Processing', 'opal-ai-photography' ); ?></h2>
			<p><?php echo esc_html__( 'Select products to enhance their images with AI.', 'opal-ai-photography' ); ?></p>

			<form id="opal-bulk-form">
				<?php wp_nonce_field( 'wp_rest', '_wpnonce' ); ?>

				<div style="margin-bottom:15px;">
					<label>
						<input type="checkbox" id="opal-select-all" />
						<?php echo esc_html__( 'Select All', 'opal-ai-photography' ); ?>
					</label>
				</div>

				<table class="widefat striped">
					<thead>
						<tr>
							<th style="width:30px;"><input type="checkbox" id="opal-select-all-top" /></th>
							<th><?php echo esc_html__( 'Product', 'opal-ai-photography' ); ?></th>
							<th><?php echo esc_html__( 'Images', 'opal-ai-photography' ); ?></th>
							<th><?php echo esc_html__( 'Status', 'opal-ai-photography' ); ?></th>
						</tr>
					</thead>
					<tbody>
						<?php foreach ( $products as $product ) :
							$image_count = count( $product->get_gallery_image_ids() ) + ( $product->get_image_id() ? 1 : 0 );
							$opal_jobs   = get_post_meta( $product->get_id(), '_opal_jobs', true );
							$status      = ! empty( $opal_jobs ) ? __( 'Processed', 'opal-ai-photography' ) : __( 'Not processed', 'opal-ai-photography' );
							?>
							<tr>
								<td><input type="checkbox" name="product_ids[]" value="<?php echo esc_attr( $product->get_id() ); ?>" /></td>
								<td><?php echo esc_html( $product->get_name() ); ?></td>
								<td><?php echo esc_html( $image_count ); ?></td>
								<td><?php echo esc_html( $status ); ?></td>
							</tr>
						<?php endforeach; ?>
					</tbody>
				</table>

				<div style="margin-top:20px;">
					<h3><?php echo esc_html__( 'Processing Options', 'opal-ai-photography' ); ?></h3>
					<label style="display:block;margin-bottom:8px;">
						<input type="checkbox" name="remove_background" value="1" <?php checked( get_option( 'opal_remove_bg', true ) ); ?> />
						<?php echo esc_html__( 'Remove Background', 'opal-ai-photography' ); ?>
					</label>
					<label style="display:block;margin-bottom:8px;">
						<input type="checkbox" name="generate_scene" value="1" <?php checked( get_option( 'opal_generate_scene', false ) ); ?> />
						<?php echo esc_html__( 'Generate Scene', 'opal-ai-photography' ); ?>
					</label>
					<label style="display:block;margin-bottom:8px;">
						<input type="checkbox" name="upscale" value="1" <?php checked( get_option( 'opal_upscale', true ) ); ?> />
						<?php echo esc_html__( 'Upscale', 'opal-ai-photography' ); ?>
					</label>
				</div>

				<div style="margin-top:15px;">
					<label for="opal-bulk-scene-prompt"><?php echo esc_html__( 'Scene Prompt (optional)', 'opal-ai-photography' ); ?></label><br/>
					<textarea id="opal-bulk-scene-prompt" name="scene_prompt" rows="2" class="large-text"><?php echo esc_textarea( Opal_Settings::get_default_scene_prompt() ); ?></textarea>
				</div>

				<p style="margin-top:20px;">
					<button type="button" id="opal-start-bulk" class="button button-primary button-hero">
						<?php echo esc_html__( 'Start Processing', 'opal-ai-photography' ); ?>
					</button>
				</p>

				<div id="opal-bulk-progress" style="display:none; margin-top:20px;">
					<h3><?php echo esc_html__( 'Progress', 'opal-ai-photography' ); ?></h3>
					<div class="opal-progress-bar" style="background:#e0e0e0; border-radius:4px; height:24px; overflow:hidden;">
						<div id="opal-progress-fill" style="background:#2271b1; height:100%; width:0%; transition:width 0.3s;"></div>
					</div>
					<p id="opal-progress-text"></p>
				</div>
			</form>
		</div>
		<?php
	}

	// -------------------------------------------------------------------------
	// A/B Tests tab
	// -------------------------------------------------------------------------

	/**
	 * Render the A/B tests tab.
	 */
	private function render_ab_tests_tab() {
		$this->ab_tests->render_admin_page();
	}

	// -------------------------------------------------------------------------
	// Admin bar balance
	// -------------------------------------------------------------------------

	/**
	 * Add token balance to the admin bar.
	 *
	 * @param WP_Admin_Bar $admin_bar The admin bar instance.
	 */
	public function admin_bar_balance( $admin_bar ) {
		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			return;
		}

		$balance_data = $this->get_cached_balance();
		if ( is_wp_error( $balance_data ) ) {
			return;
		}

		$balance = isset( $balance_data['token_balance'] ) ? absint( $balance_data['token_balance'] ) : 0;

		$admin_bar->add_node(
			array(
				'id'    => 'opal-balance',
				'title' => sprintf(
					/* translators: %s: token count */
					esc_html__( 'Opal: %s tokens', 'opal-ai-photography' ),
					number_format_i18n( $balance )
				),
				'href'  => admin_url( 'admin.php?page=opal-ai' ),
			)
		);
	}

	// -------------------------------------------------------------------------
	// Product list column
	// -------------------------------------------------------------------------

	/**
	 * Add the Opal status column to the products list.
	 *
	 * @param array $columns Existing columns.
	 * @return array Modified columns.
	 */
	public function add_product_column( $columns ) {
		$columns['opal_status'] = __( 'Opal AI', 'opal-ai-photography' );
		return $columns;
	}

	/**
	 * Render the Opal status column.
	 *
	 * @param string $column    Column slug.
	 * @param int    $post_id   Post ID.
	 */
	public function render_product_column( $column, $post_id ) {
		if ( 'opal_status' !== $column ) {
			return;
		}

		$last = get_post_meta( $post_id, '_opal_last_processed', true );
		if ( $last ) {
			printf(
				'<span class="dashicons dashicons-yes-alt" style="color:#00a32a;" title="%s"></span> %s',
				esc_attr(
					sprintf(
						/* translators: %s: date string */
						__( 'Processed on %s', 'opal-ai-photography' ),
						$last
					)
				),
				esc_html( human_time_diff( strtotime( $last ) ) . ' ' . __( 'ago', 'opal-ai-photography' ) )
			);
		} else {
			echo '<span class="dashicons dashicons-minus" style="color:#999;"></span>';
		}
	}

	// -------------------------------------------------------------------------
	// Helpers
	// -------------------------------------------------------------------------

	/**
	 * Get balance with 5-minute transient cache.
	 *
	 * @return array|WP_Error
	 */
	private function get_cached_balance() {
		$cached = get_transient( 'opal_token_balance' );
		if ( false !== $cached ) {
			return $cached;
		}

		$result = $this->api_client->get_balance();
		if ( ! is_wp_error( $result ) ) {
			set_transient( 'opal_token_balance', $result, 5 * MINUTE_IN_SECONDS );
		}

		return $result;
	}

	/**
	 * Get the 10 most recent Opal jobs from post meta.
	 *
	 * @return array
	 */
	private function get_recent_jobs() {
		global $wpdb;

		// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching
		$rows = $wpdb->get_results(
			$wpdb->prepare(
				"SELECT post_id, meta_value FROM {$wpdb->postmeta}
				 WHERE meta_key = %s
				 ORDER BY meta_id DESC LIMIT 10",
				'_opal_jobs'
			),
			ARRAY_A
		);

		$jobs = array();
		foreach ( $rows as $row ) {
			$meta = maybe_unserialize( $row['meta_value'] );
			if ( is_array( $meta ) ) {
				foreach ( array_reverse( $meta ) as $entry ) {
					$entry['product_id'] = absint( $row['post_id'] );
					$jobs[]              = $entry;
				}
			}
		}

		return array_slice( $jobs, 0, 10 );
	}

	/**
	 * Get quick stats for the dashboard.
	 *
	 * @return array {processed: int, total: int, ab_tests: int}
	 */
	private function get_quick_stats() {
		global $wpdb;

		// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching
		$processed = (int) $wpdb->get_var(
			$wpdb->prepare(
				"SELECT COUNT(DISTINCT post_id) FROM {$wpdb->postmeta} WHERE meta_key = %s",
				'_opal_last_processed'
			)
		);

		$total_products = (int) wp_count_posts( 'product' )->publish;
		$ab_count       = $this->ab_tests->count_active();

		return array(
			'processed' => $processed,
			'total'     => $total_products,
			'ab_tests'  => $ab_count,
		);
	}
}
