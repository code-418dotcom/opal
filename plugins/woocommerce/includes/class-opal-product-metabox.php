<?php
/**
 * WooCommerce product editor meta box.
 *
 * @package OpalAIPhotography
 */

defined( 'ABSPATH' ) || exit;

/**
 * Class Opal_Product_Metabox
 *
 * Adds an "Opal AI" meta box to the WooCommerce product edit screen with
 * processing controls, status display, and before/after gallery.
 */
class Opal_Product_Metabox {

	/**
	 * Constructor.
	 */
	public function __construct() {
		add_action( 'add_meta_boxes', array( $this, 'register_metabox' ) );
	}

	/**
	 * Register the meta box on the product post type.
	 */
	public function register_metabox() {
		add_meta_box(
			'opal-ai-product',
			__( 'Opal AI Photography', 'opal-ai-photography' ),
			array( $this, 'render_metabox' ),
			'product',
			'side',
			'default'
		);
	}

	/**
	 * Render the meta box content.
	 *
	 * @param WP_Post $post The current post.
	 */
	public function render_metabox( $post ) {
		$product_id      = $post->ID;
		$last_processed  = get_post_meta( $product_id, '_opal_last_processed', true );
		$opal_jobs       = get_post_meta( $product_id, '_opal_jobs', true );
		$processed_imgs  = get_post_meta( $product_id, '_opal_processed_images', true );
		$default_options = Opal_Settings::get_default_processing_options();
		$default_prompt  = Opal_Settings::get_default_scene_prompt();

		?>
		<div id="opal-metabox-wrap">
			<!-- Status -->
			<div class="opal-metabox-section">
				<strong><?php echo esc_html__( 'Status:', 'opal-ai-photography' ); ?></strong>
				<?php if ( $last_processed ) : ?>
					<span style="color:#00a32a;">
						<?php
						printf(
							/* translators: %s: relative time */
							esc_html__( 'Processed %s ago', 'opal-ai-photography' ),
							esc_html( human_time_diff( strtotime( $last_processed ) ) )
						);
						?>
					</span>
				<?php else : ?>
					<span style="color:#999;"><?php echo esc_html__( 'Not processed', 'opal-ai-photography' ); ?></span>
				<?php endif; ?>
			</div>

			<hr />

			<!-- Processing Options -->
			<div class="opal-metabox-section">
				<p>
					<label>
						<input type="checkbox" id="opal-opt-remove-bg" <?php checked( $default_options['remove_background'] ); ?> />
						<?php echo esc_html__( 'Remove Background', 'opal-ai-photography' ); ?>
					</label>
				</p>
				<p>
					<label>
						<input type="checkbox" id="opal-opt-generate-scene" <?php checked( $default_options['generate_scene'] ); ?> />
						<?php echo esc_html__( 'Generate Scene', 'opal-ai-photography' ); ?>
					</label>
				</p>
				<p>
					<label>
						<input type="checkbox" id="opal-opt-upscale" <?php checked( $default_options['upscale'] ); ?> />
						<?php echo esc_html__( 'Upscale', 'opal-ai-photography' ); ?>
					</label>
				</p>
			</div>

			<!-- Scene Prompt -->
			<div class="opal-metabox-section">
				<p>
					<label for="opal-scene-prompt"><?php echo esc_html__( 'Scene Prompt:', 'opal-ai-photography' ); ?></label>
					<textarea id="opal-scene-prompt" class="widefat" rows="2" placeholder="<?php echo esc_attr__( 'e.g. Product on a marble countertop', 'opal-ai-photography' ); ?>"><?php echo esc_textarea( $default_prompt ); ?></textarea>
				</p>
			</div>

			<!-- Action Button -->
			<div class="opal-metabox-section">
				<button type="button" id="opal-enhance-btn" class="button button-primary" data-product-id="<?php echo esc_attr( $product_id ); ?>" style="width:100%;">
					<?php echo esc_html__( 'Enhance with Opal', 'opal-ai-photography' ); ?>
				</button>
				<div id="opal-processing-status" style="display:none; margin-top:10px;">
					<span class="spinner is-active" style="float:none; margin:0 5px 0 0;"></span>
					<span id="opal-status-text"><?php echo esc_html__( 'Processing...', 'opal-ai-photography' ); ?></span>
				</div>
			</div>

			<?php if ( ! empty( $processed_imgs ) && is_array( $processed_imgs ) ) : ?>
				<hr />
				<!-- Before/After Gallery -->
				<div class="opal-metabox-section">
					<strong><?php echo esc_html__( 'Processed Images:', 'opal-ai-photography' ); ?></strong>
					<div class="opal-image-gallery" style="margin-top:8px;">
						<?php foreach ( $processed_imgs as $img ) :
							$attach_id = $img['attachment_id'] ?? ( $img['url'] ?? 0 );
							if ( is_numeric( $attach_id ) && $attach_id > 0 ) :
								$thumb_url = wp_get_attachment_image_url( (int) $attach_id, 'thumbnail' );
								$full_url  = wp_get_attachment_url( (int) $attach_id );
								if ( $thumb_url ) :
									?>
									<div style="display:inline-block; margin:4px; position:relative;">
										<?php if ( ! empty( $img['original_id'] ) ) :
											$orig_thumb = wp_get_attachment_image_url( (int) $img['original_id'], 'thumbnail' );
											if ( $orig_thumb ) : ?>
												<img src="<?php echo esc_url( $orig_thumb ); ?>" alt="<?php echo esc_attr__( 'Original', 'opal-ai-photography' ); ?>" style="width:60px;height:60px;object-fit:cover;border:2px solid #ccc;border-radius:3px;" />
												<span style="margin:0 2px;">&rarr;</span>
											<?php endif; ?>
										<?php endif; ?>
										<a href="<?php echo esc_url( $full_url ); ?>" target="_blank">
											<img src="<?php echo esc_url( $thumb_url ); ?>" alt="<?php echo esc_attr__( 'Processed', 'opal-ai-photography' ); ?>" style="width:60px;height:60px;object-fit:cover;border:2px solid #2271b1;border-radius:3px;" />
										</a>
									</div>
								<?php
								endif;
							endif;
						endforeach; ?>
					</div>
				</div>
			<?php endif; ?>

			<?php if ( ! empty( $opal_jobs ) && is_array( $opal_jobs ) ) : ?>
				<hr />
				<!-- Job History -->
				<div class="opal-metabox-section">
					<strong><?php echo esc_html__( 'Job History:', 'opal-ai-photography' ); ?></strong>
					<ul style="margin:5px 0; font-size:12px;">
						<?php foreach ( array_reverse( array_slice( $opal_jobs, -5 ) ) as $job ) : ?>
							<li>
								<code style="font-size:11px;"><?php echo esc_html( substr( $job['job_id'] ?? '', 0, 8 ) ); ?></code>
								&mdash;
								<?php echo esc_html( ucfirst( $job['status'] ?? 'unknown' ) ); ?>
								<br/>
								<small><?php echo esc_html( $job['date'] ?? '' ); ?></small>
							</li>
						<?php endforeach; ?>
					</ul>
				</div>
			<?php endif; ?>
		</div>
		<?php
	}
}
