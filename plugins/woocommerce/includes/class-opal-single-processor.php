<?php
/**
 * Single product AJAX processing.
 *
 * @package OpalAIPhotography
 */

defined( 'ABSPATH' ) || exit;

/**
 * Class Opal_Single_Processor
 *
 * Handles AJAX-driven processing of a single product. The browser polls
 * for status via a separate AJAX endpoint.
 */
class Opal_Single_Processor {

	/**
	 * API client.
	 *
	 * @var Opal_API_Client
	 */
	private $api_client;

	/**
	 * Image handler.
	 *
	 * @var Opal_Image_Handler
	 */
	private $image_handler;

	/**
	 * Constructor.
	 *
	 * @param Opal_API_Client    $api_client    API client.
	 * @param Opal_Image_Handler $image_handler Image handler.
	 */
	public function __construct( Opal_API_Client $api_client, Opal_Image_Handler $image_handler ) {
		$this->api_client    = $api_client;
		$this->image_handler = $image_handler;

		add_action( 'wp_ajax_opal_process_product', array( $this, 'ajax_process_product' ) );
		add_action( 'wp_ajax_opal_poll_product', array( $this, 'ajax_poll_product' ) );
	}

	/**
	 * AJAX: Start processing a single product.
	 */
	public function ajax_process_product() {
		check_ajax_referer( 'opal_process_nonce', 'nonce' );

		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			wp_send_json_error( array( 'message' => __( 'Permission denied.', 'opal-ai-photography' ) ) );
		}

		$product_id = isset( $_POST['product_id'] ) ? absint( $_POST['product_id'] ) : 0;
		if ( ! $product_id ) {
			wp_send_json_error( array( 'message' => __( 'Invalid product ID.', 'opal-ai-photography' ) ) );
		}

		$product = wc_get_product( $product_id );
		if ( ! $product ) {
			wp_send_json_error( array( 'message' => __( 'Product not found.', 'opal-ai-photography' ) ) );
		}

		// Gather processing options from the request.
		$processing_options = array(
			'remove_background' => ! empty( $_POST['remove_background'] ),
			'generate_scene'    => ! empty( $_POST['generate_scene'] ),
			'upscale'           => ! empty( $_POST['upscale'] ),
		);

		$scene_prompt = isset( $_POST['scene_prompt'] ) ? sanitize_textarea_field( wp_unslash( $_POST['scene_prompt'] ) ) : '';

		// Collect images.
		$image_ids = array();
		$featured  = $product->get_image_id();
		if ( $featured ) {
			$image_ids[] = $featured;
		}
		$image_ids = array_merge( $image_ids, $product->get_gallery_image_ids() );

		if ( empty( $image_ids ) ) {
			wp_send_json_error( array( 'message' => __( 'Product has no images.', 'opal-ai-photography' ) ) );
		}

		// Build items array.
		$items     = array();
		$image_map = array();

		foreach ( $image_ids as $idx => $attach_id ) {
			$file_path = get_attached_file( $attach_id );
			if ( ! $file_path || ! file_exists( $file_path ) ) {
				continue;
			}
			$items[]           = array(
				'filename'     => basename( $file_path ),
				'scene_prompt' => $scene_prompt,
				'scene_count'  => 1,
			);
			$image_map[ $idx ] = array(
				'attach_id' => $attach_id,
				'file_path' => $file_path,
			);
		}

		if ( empty( $items ) ) {
			wp_send_json_error( array( 'message' => __( 'No valid image files found.', 'opal-ai-photography' ) ) );
		}

		// 1. Create job.
		$job_result = $this->api_client->create_job( $items, $processing_options );
		if ( is_wp_error( $job_result ) ) {
			wp_send_json_error( array( 'message' => $job_result->get_error_message() ) );
		}

		$job_id    = $job_result['job_id'];
		$job_items = $job_result['items'];

		// 2. Upload and complete each image.
		foreach ( $job_items as $idx => $ji ) {
			if ( ! isset( $image_map[ $idx ] ) ) {
				continue;
			}

			$upload = $this->api_client->upload_image( $image_map[ $idx ]['file_path'], $job_id, $ji['item_id'] );
			if ( is_wp_error( $upload ) ) {
				wp_send_json_error( array( 'message' => $upload->get_error_message() ) );
			}

			$complete = $this->api_client->complete_upload( $job_id, $ji['item_id'], $ji['filename'], $processing_options );
			if ( is_wp_error( $complete ) ) {
				wp_send_json_error( array( 'message' => $complete->get_error_message() ) );
			}
		}

		// Store the job mapping in a transient so the poll handler can access it.
		set_transient(
			'opal_single_job_' . $job_id,
			array(
				'product_id' => $product_id,
				'image_map'  => $image_map,
				'job_items'  => $job_items,
				'options'    => $processing_options,
			),
			HOUR_IN_SECONDS
		);

		wp_send_json_success(
			array(
				'job_id'  => $job_id,
				'status'  => 'processing',
				'message' => __( 'Job submitted. Polling for results...', 'opal-ai-photography' ),
			)
		);
	}

	/**
	 * AJAX: Poll the status of a single-product job.
	 */
	public function ajax_poll_product() {
		check_ajax_referer( 'opal_process_nonce', 'nonce' );

		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			wp_send_json_error( array( 'message' => __( 'Permission denied.', 'opal-ai-photography' ) ) );
		}

		$job_id = isset( $_POST['job_id'] ) ? sanitize_text_field( wp_unslash( $_POST['job_id'] ) ) : '';
		if ( empty( $job_id ) ) {
			wp_send_json_error( array( 'message' => __( 'Missing job ID.', 'opal-ai-photography' ) ) );
		}

		$job_result = $this->api_client->get_job( $job_id );
		if ( is_wp_error( $job_result ) ) {
			wp_send_json_error( array( 'message' => $job_result->get_error_message() ) );
		}

		$status = $job_result['status'] ?? 'unknown';

		if ( 'completed' === $status ) {
			$result = $this->handle_single_completed( $job_id, $job_result );
			if ( is_wp_error( $result ) ) {
				wp_send_json_error( array( 'message' => $result->get_error_message() ) );
			}
			wp_send_json_success(
				array(
					'status'  => 'completed',
					'message' => __( 'Processing complete! Images have been added to the media library.', 'opal-ai-photography' ),
					'images'  => $result,
				)
			);
		} elseif ( 'failed' === $status || 'error' === $status ) {
			wp_send_json_error(
				array(
					'status'  => 'failed',
					'message' => __( 'Processing failed on the server.', 'opal-ai-photography' ),
				)
			);
		} else {
			wp_send_json_success(
				array(
					'status'  => 'processing',
					'message' => __( 'Still processing...', 'opal-ai-photography' ),
				)
			);
		}
	}

	/**
	 * Handle a completed single-product job.
	 *
	 * @param string $job_id     Job ID.
	 * @param array  $job_result Full job response.
	 * @return array|WP_Error Array of processed image data, or WP_Error.
	 */
	private function handle_single_completed( $job_id, $job_result ) {
		$job_data = get_transient( 'opal_single_job_' . $job_id );
		if ( ! $job_data ) {
			return new \WP_Error( 'opal_no_job_data', __( 'Job mapping data not found.', 'opal-ai-photography' ) );
		}

		$product_id   = $job_data['product_id'];
		$items        = $job_result['items'] ?? array();
		$auto_replace = (bool) get_option( 'opal_auto_replace', false );
		$keep_orig    = (bool) get_option( 'opal_keep_originals', true );
		$processed    = array();

		foreach ( $items as $idx => $item ) {
			if ( 'completed' !== ( $item['status'] ?? '' ) ) {
				continue;
			}

			$dl_result = $this->api_client->get_download_url( $item['item_id'] );
			if ( is_wp_error( $dl_result ) ) {
				continue;
			}

			$download_url = $dl_result['download_url'] ?? '';
			if ( empty( $download_url ) ) {
				continue;
			}

			$filename  = 'opal-' . basename( $item['item_id'] ) . '.png';
			$attach_id = $this->image_handler->download_and_attach( $download_url, $product_id, $filename );

			if ( is_wp_error( $attach_id ) ) {
				continue;
			}

			$processed[] = array(
				'attachment_id' => $attach_id,
				'url'           => wp_get_attachment_url( $attach_id ),
			);

			if ( $auto_replace && 0 === $idx ) {
				$this->image_handler->replace_featured_image( $product_id, $attach_id, $keep_orig );
			} elseif ( $auto_replace ) {
				$this->image_handler->add_to_gallery( $product_id, $attach_id );
			}
		}

		// Update post meta.
		$existing = get_post_meta( $product_id, '_opal_jobs', true );
		if ( ! is_array( $existing ) ) {
			$existing = array();
		}
		$existing[] = array(
			'job_id' => $job_id,
			'status' => 'completed',
			'date'   => current_time( 'mysql' ),
		);
		update_post_meta( $product_id, '_opal_jobs', $existing );
		update_post_meta( $product_id, '_opal_last_processed', current_time( 'mysql' ) );
		update_post_meta( $product_id, '_opal_processed_images', $processed );

		delete_transient( 'opal_single_job_' . $job_id );

		return $processed;
	}

	/**
	 * Process a product programmatically (used by the REST controller).
	 *
	 * @param int   $product_id Product ID.
	 * @param array $options    {remove_background, generate_scene, upscale, scene_prompt}.
	 * @return array|WP_Error {job_id, status} on success, WP_Error on failure.
	 */
	public function process_product( $product_id, $options = array() ) {
		$product = wc_get_product( $product_id );
		if ( ! $product ) {
			return new \WP_Error( 'opal_product_not_found', __( 'Product not found.', 'opal-ai-photography' ) );
		}

		$image_ids = array();
		$featured  = $product->get_image_id();
		if ( $featured ) {
			$image_ids[] = $featured;
		}
		$image_ids = array_merge( $image_ids, $product->get_gallery_image_ids() );

		if ( empty( $image_ids ) ) {
			return new \WP_Error( 'opal_no_images', __( 'Product has no images.', 'opal-ai-photography' ) );
		}

		$processing_options = array(
			'remove_background' => $options['remove_background'] ?? true,
			'generate_scene'    => $options['generate_scene'] ?? false,
			'upscale'           => $options['upscale'] ?? true,
		);

		$scene_prompt = $options['scene_prompt'] ?? '';

		$items     = array();
		$image_map = array();

		foreach ( $image_ids as $idx => $attach_id ) {
			$file_path = get_attached_file( $attach_id );
			if ( ! $file_path || ! file_exists( $file_path ) ) {
				continue;
			}
			$items[]           = array(
				'filename'     => basename( $file_path ),
				'scene_prompt' => $scene_prompt,
				'scene_count'  => 1,
			);
			$image_map[ $idx ] = array(
				'attach_id' => $attach_id,
				'file_path' => $file_path,
			);
		}

		if ( empty( $items ) ) {
			return new \WP_Error( 'opal_no_valid_images', __( 'No valid image files.', 'opal-ai-photography' ) );
		}

		$job_result = $this->api_client->create_job( $items, $processing_options );
		if ( is_wp_error( $job_result ) ) {
			return $job_result;
		}

		$job_id    = $job_result['job_id'];
		$job_items = $job_result['items'];

		foreach ( $job_items as $idx => $ji ) {
			if ( ! isset( $image_map[ $idx ] ) ) {
				continue;
			}

			$upload = $this->api_client->upload_image( $image_map[ $idx ]['file_path'], $job_id, $ji['item_id'] );
			if ( is_wp_error( $upload ) ) {
				return $upload;
			}

			$complete = $this->api_client->complete_upload( $job_id, $ji['item_id'], $ji['filename'], $processing_options );
			if ( is_wp_error( $complete ) ) {
				return $complete;
			}
		}

		set_transient(
			'opal_single_job_' . $job_id,
			array(
				'product_id' => $product_id,
				'image_map'  => $image_map,
				'job_items'  => $job_items,
				'options'    => $processing_options,
			),
			HOUR_IN_SECONDS
		);

		return array(
			'job_id' => $job_id,
			'status' => 'processing',
		);
	}
}
