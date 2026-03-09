<?php
/**
 * Image download and media library insertion.
 *
 * @package OpalAIPhotography
 */

defined( 'ABSPATH' ) || exit;

/**
 * Class Opal_Image_Handler
 *
 * Downloads processed images from Opal SAS URLs and inserts them into the
 * WordPress media library attached to the originating product.
 */
class Opal_Image_Handler {

	/**
	 * Download an image from the Opal download URL and attach it to a product.
	 *
	 * @param string $download_url The Opal SAS download URL.
	 * @param int    $product_id   The WooCommerce product post ID.
	 * @param string $filename     The desired filename for the attachment.
	 * @return int|WP_Error The new attachment ID, or WP_Error on failure.
	 */
	public function download_and_attach( $download_url, $product_id, $filename ) {
		if ( empty( $download_url ) ) {
			return new \WP_Error( 'opal_empty_url', __( 'Download URL is empty.', 'opal-ai-photography' ) );
		}

		// Ensure the filename is safe.
		$filename = sanitize_file_name( $filename );
		if ( empty( $filename ) ) {
			$filename = 'opal-processed-' . wp_generate_password( 8, false ) . '.png';
		}

		// Download the file to a temporary location.
		$tmp_file = $this->download_to_temp( $download_url );
		if ( is_wp_error( $tmp_file ) ) {
			return $tmp_file;
		}

		// Determine the upload directory.
		$upload_dir = wp_upload_dir();
		if ( ! empty( $upload_dir['error'] ) ) {
			// phpcs:ignore WordPress.WP.AlternativeFunctions.unlink_unlink
			@unlink( $tmp_file );
			return new \WP_Error( 'opal_upload_dir_error', $upload_dir['error'] );
		}

		// Ensure we have a unique filename to avoid overwrites.
		$filename  = wp_unique_filename( $upload_dir['path'], $filename );
		$dest_file = trailingslashit( $upload_dir['path'] ) . $filename;

		// Move the temp file into the uploads directory.
		// phpcs:ignore WordPress.PHP.NoSilencedErrors.Discouraged
		$moved = @copy( $tmp_file, $dest_file );
		// phpcs:ignore WordPress.WP.AlternativeFunctions.unlink_unlink
		@unlink( $tmp_file );

		if ( ! $moved ) {
			return new \WP_Error(
				'opal_file_move_error',
				__( 'Could not move downloaded file to uploads directory.', 'opal-ai-photography' )
			);
		}

		// Set correct file permissions.
		$stat  = stat( dirname( $dest_file ) );
		$perms = $stat['mode'] & 0000666;
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_chmod
		@chmod( $dest_file, $perms );

		// Determine MIME type.
		$filetype = wp_check_filetype( $filename );
		$mime     = $filetype['type'] ?: 'image/png';

		// Create the attachment post.
		$attachment_data = array(
			'post_mime_type' => $mime,
			'post_title'     => preg_replace( '/\.[^.]+$/', '', $filename ),
			'post_content'   => '',
			'post_status'    => 'inherit',
		);

		$attach_id = wp_insert_attachment( $attachment_data, $dest_file, $product_id );

		if ( is_wp_error( $attach_id ) ) {
			// phpcs:ignore WordPress.WP.AlternativeFunctions.unlink_unlink
			@unlink( $dest_file );
			return $attach_id;
		}

		// Generate metadata (thumbnails, sizes, etc.).
		require_once ABSPATH . 'wp-admin/includes/image.php';
		$metadata = wp_generate_attachment_metadata( $attach_id, $dest_file );
		wp_update_attachment_metadata( $attach_id, $metadata );

		return $attach_id;
	}

	/**
	 * Download a remote file to a temporary path.
	 *
	 * @param string $url The URL to download.
	 * @return string|WP_Error Temporary file path, or WP_Error.
	 */
	private function download_to_temp( $url ) {
		$response = wp_remote_get(
			$url,
			array(
				'timeout'  => 120,
				'stream'   => true,
				'filename' => wp_tempnam( 'opal_' ),
			)
		);

		if ( is_wp_error( $response ) ) {
			return $response;
		}

		$code = wp_remote_retrieve_response_code( $response );
		if ( 200 !== $code ) {
			$tmp = $response['filename'] ?? '';
			if ( $tmp && file_exists( $tmp ) ) {
				// phpcs:ignore WordPress.WP.AlternativeFunctions.unlink_unlink
				@unlink( $tmp );
			}
			return new \WP_Error(
				'opal_download_error',
				sprintf(
					/* translators: %d: HTTP status code */
					__( 'Failed to download image (HTTP %d).', 'opal-ai-photography' ),
					$code
				)
			);
		}

		return $response['filename'];
	}

	/**
	 * Replace a product's featured image with a new attachment.
	 *
	 * @param int $product_id   The product post ID.
	 * @param int $attach_id    The new attachment ID.
	 * @param bool $keep_original Whether to keep the original as a gallery image.
	 */
	public function replace_featured_image( $product_id, $attach_id, $keep_original = true ) {
		$product = wc_get_product( $product_id );
		if ( ! $product ) {
			return;
		}

		$old_image_id = $product->get_image_id();

		// Set the new featured image.
		$product->set_image_id( $attach_id );

		// Optionally keep the original in the gallery.
		if ( $keep_original && $old_image_id ) {
			$gallery = $product->get_gallery_image_ids();
			if ( ! in_array( $old_image_id, $gallery, true ) ) {
				$gallery[] = $old_image_id;
				$product->set_gallery_image_ids( $gallery );
			}
		}

		$product->save();
	}

	/**
	 * Add an attachment to a product's gallery.
	 *
	 * @param int $product_id The product post ID.
	 * @param int $attach_id  The attachment ID to add.
	 */
	public function add_to_gallery( $product_id, $attach_id ) {
		$product = wc_get_product( $product_id );
		if ( ! $product ) {
			return;
		}

		$gallery = $product->get_gallery_image_ids();
		if ( ! in_array( $attach_id, $gallery, true ) ) {
			$gallery[] = $attach_id;
			$product->set_gallery_image_ids( $gallery );
			$product->save();
		}
	}
}
