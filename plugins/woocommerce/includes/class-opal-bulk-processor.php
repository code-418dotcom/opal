<?php
/**
 * Bulk processing with Action Scheduler.
 *
 * @package OpalAIPhotography
 */

defined( 'ABSPATH' ) || exit;

/**
 * Class Opal_Bulk_Processor
 *
 * Processes multiple products asynchronously via WooCommerce Action Scheduler.
 */
class Opal_Bulk_Processor {

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
	 * Maximum number of poll retries per job.
	 *
	 * @var int
	 */
	const MAX_POLL_RETRIES = 20;

	/**
	 * Poll interval in seconds.
	 *
	 * @var int
	 */
	const POLL_INTERVAL = 30;

	/**
	 * Constructor.
	 *
	 * @param Opal_API_Client    $api_client    API client.
	 * @param Opal_Image_Handler $image_handler Image handler.
	 */
	public function __construct( Opal_API_Client $api_client, Opal_Image_Handler $image_handler ) {
		$this->api_client    = $api_client;
		$this->image_handler = $image_handler;

		add_action( 'opal_process_product', array( $this, 'process_product_callback' ), 10, 3 );
		add_action( 'opal_poll_job', array( $this, 'poll_job_callback' ), 10, 4 );
	}

	/**
	 * Start a bulk processing batch.
	 *
	 * @param array $product_ids Product IDs to process.
	 * @param array $options     Processing options {remove_background, generate_scene, upscale, scene_prompt}.
	 * @return string The batch ID.
	 */
	public function start_batch( $product_ids, $options ) {
		$batch_id    = wp_generate_uuid4();
		$total       = count( $product_ids );
		$batch_state = array(
			'batch_id'   => $batch_id,
			'total'      => $total,
			'processed'  => 0,
			'failed'     => 0,
			'pending'    => $total,
			'status'     => 'running',
			'started_at' => current_time( 'mysql' ),
			'products'   => array(),
		);

		// Initialize per-product state.
		foreach ( $product_ids as $pid ) {
			$batch_state['products'][ $pid ] = array(
				'status' => 'pending',
				'job_id' => '',
				'error'  => '',
			);
		}

		set_transient( 'opal_batch_' . $batch_id, $batch_state, DAY_IN_SECONDS );

		// Schedule each product as an individual Action Scheduler action.
		$processing_options = array(
			'remove_background' => ! empty( $options['remove_background'] ),
			'generate_scene'    => ! empty( $options['generate_scene'] ),
			'upscale'           => ! empty( $options['upscale'] ),
		);

		$scene_prompt = isset( $options['scene_prompt'] ) ? sanitize_textarea_field( $options['scene_prompt'] ) : '';

		foreach ( $product_ids as $index => $pid ) {
			if ( function_exists( 'as_schedule_single_action' ) ) {
				as_schedule_single_action(
					time() + $index, // stagger by 1 second each
					'opal_process_product',
					array(
						'batch_id'           => $batch_id,
						'product_id'         => absint( $pid ),
						'options'            => array_merge( $processing_options, array( 'scene_prompt' => $scene_prompt ) ),
					),
					'opal'
				);
			}
		}

		return $batch_id;
	}

	/**
	 * Action Scheduler callback: process a single product.
	 *
	 * @param string $batch_id   The batch ID.
	 * @param int    $product_id The product ID.
	 * @param array  $options    Processing options.
	 */
	public function process_product_callback( $batch_id, $product_id, $options ) {
		$product = wc_get_product( $product_id );
		if ( ! $product ) {
			$this->update_product_status( $batch_id, $product_id, 'failed', '', __( 'Product not found.', 'opal-ai-photography' ) );
			return;
		}

		// Collect image attachment IDs.
		$image_ids = array();
		$featured  = $product->get_image_id();
		if ( $featured ) {
			$image_ids[] = $featured;
		}
		$gallery = $product->get_gallery_image_ids();
		$image_ids = array_merge( $image_ids, $gallery );

		if ( empty( $image_ids ) ) {
			$this->update_product_status( $batch_id, $product_id, 'failed', '', __( 'No images found.', 'opal-ai-photography' ) );
			return;
		}

		// Build job items.
		$items       = array();
		$image_map   = array(); // index => attachment_id for later mapping.
		$scene_prompt = $options['scene_prompt'] ?? '';

		foreach ( $image_ids as $idx => $attach_id ) {
			$file_path = get_attached_file( $attach_id );
			if ( ! $file_path || ! file_exists( $file_path ) ) {
				continue;
			}
			$items[]              = array(
				'filename'     => basename( $file_path ),
				'scene_prompt' => $scene_prompt,
				'scene_count'  => 1,
			);
			$image_map[ $idx ]    = array(
				'attach_id' => $attach_id,
				'file_path' => $file_path,
			);
		}

		if ( empty( $items ) ) {
			$this->update_product_status( $batch_id, $product_id, 'failed', '', __( 'No valid image files found.', 'opal-ai-photography' ) );
			return;
		}

		$processing_options = array(
			'remove_background' => ! empty( $options['remove_background'] ),
			'generate_scene'    => ! empty( $options['generate_scene'] ),
			'upscale'           => ! empty( $options['upscale'] ),
		);

		// 1. Create job.
		$job_result = $this->api_client->create_job( $items, $processing_options );
		if ( is_wp_error( $job_result ) ) {
			$this->update_product_status( $batch_id, $product_id, 'failed', '', $job_result->get_error_message() );
			return;
		}

		$job_id    = $job_result['job_id'];
		$job_items = $job_result['items'];

		// 2. Upload each image.
		foreach ( $job_items as $idx => $ji ) {
			if ( ! isset( $image_map[ $idx ] ) ) {
				continue;
			}
			$upload_result = $this->api_client->upload_image(
				$image_map[ $idx ]['file_path'],
				$job_id,
				$ji['item_id']
			);

			if ( is_wp_error( $upload_result ) ) {
				$this->update_product_status( $batch_id, $product_id, 'failed', $job_id, $upload_result->get_error_message() );
				return;
			}

			// 3. Complete upload.
			$complete_result = $this->api_client->complete_upload(
				$job_id,
				$ji['item_id'],
				$ji['filename'],
				$processing_options
			);

			if ( is_wp_error( $complete_result ) ) {
				$this->update_product_status( $batch_id, $product_id, 'failed', $job_id, $complete_result->get_error_message() );
				return;
			}
		}

		// Store the image mapping for the poll callback.
		set_transient(
			'opal_job_map_' . $job_id,
			array(
				'product_id' => $product_id,
				'image_map'  => $image_map,
				'job_items'  => $job_items,
			),
			DAY_IN_SECONDS
		);

		$this->update_product_status( $batch_id, $product_id, 'processing', $job_id );

		// 4. Schedule poll.
		if ( function_exists( 'as_schedule_single_action' ) ) {
			as_schedule_single_action(
				time() + self::POLL_INTERVAL,
				'opal_poll_job',
				array(
					'batch_id'   => $batch_id,
					'product_id' => $product_id,
					'job_id'     => $job_id,
					'retry'      => 0,
				),
				'opal'
			);
		}
	}

	/**
	 * Action Scheduler callback: poll a job for completion.
	 *
	 * @param string $batch_id   The batch ID.
	 * @param int    $product_id The product ID.
	 * @param string $job_id     The Opal job ID.
	 * @param int    $retry      Current retry count.
	 */
	public function poll_job_callback( $batch_id, $product_id, $job_id, $retry ) {
		$job_result = $this->api_client->get_job( $job_id );

		if ( is_wp_error( $job_result ) ) {
			if ( $retry < self::MAX_POLL_RETRIES ) {
				$this->schedule_retry( $batch_id, $product_id, $job_id, $retry );
			} else {
				$this->update_product_status( $batch_id, $product_id, 'failed', $job_id, $job_result->get_error_message() );
			}
			return;
		}

		$status = $job_result['status'] ?? 'unknown';

		if ( 'completed' === $status ) {
			$this->handle_completed_job( $batch_id, $product_id, $job_id, $job_result );
		} elseif ( 'failed' === $status || 'error' === $status ) {
			$this->update_product_status( $batch_id, $product_id, 'failed', $job_id, __( 'Job failed on the Opal server.', 'opal-ai-photography' ) );
		} elseif ( $retry < self::MAX_POLL_RETRIES ) {
			$this->schedule_retry( $batch_id, $product_id, $job_id, $retry );
		} else {
			$this->update_product_status( $batch_id, $product_id, 'failed', $job_id, __( 'Job timed out after maximum retries.', 'opal-ai-photography' ) );
		}
	}

	/**
	 * Handle a completed job — download results and optionally replace images.
	 *
	 * @param string $batch_id   The batch ID.
	 * @param int    $product_id The product ID.
	 * @param string $job_id     The job ID.
	 * @param array  $job_result The full job response.
	 */
	private function handle_completed_job( $batch_id, $product_id, $job_id, $job_result ) {
		$job_map = get_transient( 'opal_job_map_' . $job_id );
		$items   = $job_result['items'] ?? array();

		$processed_images = array();
		$auto_replace     = (bool) get_option( 'opal_auto_replace', false );
		$keep_originals   = (bool) get_option( 'opal_keep_originals', true );

		foreach ( $items as $idx => $item ) {
			if ( 'completed' !== ( $item['status'] ?? '' ) ) {
				continue;
			}

			// Get the download URL.
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

			$processed_images[] = array(
				'item_id'       => $item['item_id'],
				'attachment_id' => $attach_id,
				'original_id'   => isset( $job_map['image_map'][ $idx ]['attach_id'] )
					? $job_map['image_map'][ $idx ]['attach_id']
					: 0,
			);

			// Auto-replace featured image (first image).
			if ( $auto_replace && 0 === $idx ) {
				$this->image_handler->replace_featured_image( $product_id, $attach_id, $keep_originals );
			} elseif ( $auto_replace ) {
				$this->image_handler->add_to_gallery( $product_id, $attach_id );
			}
		}

		// Store processed images in post meta.
		$existing_jobs = get_post_meta( $product_id, '_opal_jobs', true );
		if ( ! is_array( $existing_jobs ) ) {
			$existing_jobs = array();
		}
		$existing_jobs[] = array(
			'job_id'           => $job_id,
			'status'           => 'completed',
			'date'             => current_time( 'mysql' ),
			'processed_images' => $processed_images,
		);
		update_post_meta( $product_id, '_opal_jobs', $existing_jobs );
		update_post_meta( $product_id, '_opal_last_processed', current_time( 'mysql' ) );

		if ( ! empty( $processed_images ) ) {
			update_post_meta( $product_id, '_opal_processed_images', $processed_images );
		}

		// Cleanup transient.
		delete_transient( 'opal_job_map_' . $job_id );

		$this->update_product_status( $batch_id, $product_id, 'completed', $job_id );
	}

	/**
	 * Schedule a poll retry.
	 *
	 * @param string $batch_id   Batch ID.
	 * @param int    $product_id Product ID.
	 * @param string $job_id     Job ID.
	 * @param int    $retry      Current retry count.
	 */
	private function schedule_retry( $batch_id, $product_id, $job_id, $retry ) {
		if ( function_exists( 'as_schedule_single_action' ) ) {
			as_schedule_single_action(
				time() + self::POLL_INTERVAL,
				'opal_poll_job',
				array(
					'batch_id'   => $batch_id,
					'product_id' => $product_id,
					'job_id'     => $job_id,
					'retry'      => $retry + 1,
				),
				'opal'
			);
		}
	}

	/**
	 * Update the batch transient with a product's new status.
	 *
	 * @param string $batch_id   The batch ID.
	 * @param int    $product_id The product ID.
	 * @param string $status     New status (processing|completed|failed).
	 * @param string $job_id     The Opal job ID.
	 * @param string $error      Error message if failed.
	 */
	private function update_product_status( $batch_id, $product_id, $status, $job_id = '', $error = '' ) {
		$batch = get_transient( 'opal_batch_' . $batch_id );
		if ( ! is_array( $batch ) ) {
			return;
		}

		$prev_status = $batch['products'][ $product_id ]['status'] ?? 'pending';

		$batch['products'][ $product_id ] = array(
			'status' => $status,
			'job_id' => $job_id,
			'error'  => $error,
		);

		// Update counters.
		if ( 'completed' === $status && 'completed' !== $prev_status ) {
			$batch['processed']++;
			if ( 'pending' === $prev_status ) {
				$batch['pending']--;
			}
		} elseif ( 'failed' === $status && 'failed' !== $prev_status ) {
			$batch['failed']++;
			if ( 'pending' === $prev_status ) {
				$batch['pending']--;
			}
		}

		// Check if batch is done.
		if ( $batch['processed'] + $batch['failed'] >= $batch['total'] ) {
			$batch['status']      = 'completed';
			$batch['finished_at'] = current_time( 'mysql' );
		}

		set_transient( 'opal_batch_' . $batch_id, $batch, DAY_IN_SECONDS );
	}

	/**
	 * Get the current status of a batch.
	 *
	 * @param string $batch_id The batch ID.
	 * @return array|null The batch state, or null if not found.
	 */
	public function get_batch_status( $batch_id ) {
		$batch = get_transient( 'opal_batch_' . sanitize_text_field( $batch_id ) );
		return is_array( $batch ) ? $batch : null;
	}
}
