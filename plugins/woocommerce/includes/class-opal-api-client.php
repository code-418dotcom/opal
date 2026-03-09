<?php
/**
 * Opal API client.
 *
 * @package OpalAIPhotography
 */

defined( 'ABSPATH' ) || exit;

/**
 * Class Opal_API_Client
 *
 * Communicates with the Opal REST API using WordPress HTTP functions.
 */
class Opal_API_Client {

	/**
	 * Default API base URL.
	 *
	 * @var string
	 */
	const DEFAULT_API_URL = 'https://opal-web-api-dev.victoriousmoss-91bcd75e.westeurope.azurecontainerapps.io';

	/**
	 * Get the configured API base URL.
	 *
	 * @return string
	 */
	private function get_api_url() {
		$url = get_option( 'opal_api_url', self::DEFAULT_API_URL );
		return untrailingslashit( $url );
	}

	/**
	 * Get the configured API key.
	 *
	 * @return string
	 */
	private function get_api_key() {
		$encrypted = get_option( 'opal_api_key_encrypted', '' );
		if ( empty( $encrypted ) ) {
			return '';
		}
		return $this->decrypt_api_key( $encrypted );
	}

	/**
	 * Encrypt an API key for storage.
	 *
	 * @param string $key The plain API key.
	 * @return string The encrypted key (base64-encoded).
	 */
	public function encrypt_api_key( $key ) {
		if ( empty( $key ) ) {
			return '';
		}
		$salt   = wp_salt( 'auth' );
		$iv     = substr( hash( 'sha256', $salt ), 0, 16 );
		$method = 'aes-256-cbc';
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_encode
		return base64_encode( openssl_encrypt( $key, $method, $salt, 0, $iv ) );
	}

	/**
	 * Decrypt a stored API key.
	 *
	 * @param string $encrypted The encrypted key (base64-encoded).
	 * @return string The plain API key.
	 */
	private function decrypt_api_key( $encrypted ) {
		$salt   = wp_salt( 'auth' );
		$iv     = substr( hash( 'sha256', $salt ), 0, 16 );
		$method = 'aes-256-cbc';
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode
		return openssl_decrypt( base64_decode( $encrypted ), $method, $salt, 0, $iv );
	}

	/**
	 * Build common request headers.
	 *
	 * @return array|WP_Error Headers array or WP_Error if no API key configured.
	 */
	private function get_headers() {
		$api_key = $this->get_api_key();
		if ( empty( $api_key ) ) {
			return new \WP_Error(
				'opal_no_api_key',
				__( 'Opal API key is not configured. Please set it in Opal AI settings.', 'opal-ai-photography' )
			);
		}

		return array(
			'X-API-Key'    => $api_key,
			'Content-Type' => 'application/json',
			'Accept'       => 'application/json',
		);
	}

	/**
	 * Perform a GET request to the Opal API.
	 *
	 * @param string $endpoint The API endpoint (e.g. "/v1/billing/balance").
	 * @return array|WP_Error Decoded JSON response or WP_Error.
	 */
	private function get( $endpoint ) {
		$headers = $this->get_headers();
		if ( is_wp_error( $headers ) ) {
			return $headers;
		}

		$url      = $this->get_api_url() . $endpoint;
		$response = wp_remote_get(
			$url,
			array(
				'headers' => $headers,
				'timeout' => 30,
			)
		);

		return $this->parse_response( $response );
	}

	/**
	 * Perform a POST request to the Opal API with JSON body.
	 *
	 * @param string $endpoint The API endpoint.
	 * @param array  $body     The request body (will be JSON-encoded).
	 * @return array|WP_Error Decoded JSON response or WP_Error.
	 */
	private function post( $endpoint, $body = array() ) {
		$headers = $this->get_headers();
		if ( is_wp_error( $headers ) ) {
			return $headers;
		}

		$url      = $this->get_api_url() . $endpoint;
		$response = wp_remote_post(
			$url,
			array(
				'headers' => $headers,
				'body'    => wp_json_encode( $body ),
				'timeout' => 60,
			)
		);

		return $this->parse_response( $response );
	}

	/**
	 * Perform a multipart POST request (for file uploads).
	 *
	 * @param string $endpoint  The API endpoint.
	 * @param string $file_path Absolute path to the file.
	 * @param array  $fields    Additional form fields.
	 * @return array|WP_Error Decoded JSON response or WP_Error.
	 */
	private function post_multipart( $endpoint, $file_path, $fields = array() ) {
		$api_key = $this->get_api_key();
		if ( empty( $api_key ) ) {
			return new \WP_Error(
				'opal_no_api_key',
				__( 'Opal API key is not configured.', 'opal-ai-photography' )
			);
		}

		$url      = $this->get_api_url() . $endpoint;
		$boundary = wp_generate_password( 24, false );
		$filename = basename( $file_path );

		// Build multipart body.
		$body = '';
		foreach ( $fields as $name => $value ) {
			$body .= "--{$boundary}\r\n";
			$body .= "Content-Disposition: form-data; name=\"{$name}\"\r\n\r\n";
			$body .= "{$value}\r\n";
		}

		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents
		$file_contents = file_get_contents( $file_path );
		if ( false === $file_contents ) {
			return new \WP_Error( 'opal_file_read_error', __( 'Could not read file for upload.', 'opal-ai-photography' ) );
		}

		$mime_type = wp_check_filetype( $filename )['type'] ?: 'application/octet-stream';
		$body     .= "--{$boundary}\r\n";
		$body     .= "Content-Disposition: form-data; name=\"file\"; filename=\"{$filename}\"\r\n";
		$body     .= "Content-Type: {$mime_type}\r\n\r\n";
		$body     .= $file_contents . "\r\n";
		$body     .= "--{$boundary}--\r\n";

		$response = wp_remote_post(
			$url,
			array(
				'headers' => array(
					'X-API-Key'    => $api_key,
					'Content-Type' => "multipart/form-data; boundary={$boundary}",
					'Accept'       => 'application/json',
				),
				'body'    => $body,
				'timeout' => 120,
			)
		);

		return $this->parse_response( $response );
	}

	/**
	 * Parse an HTTP response into an array or WP_Error.
	 *
	 * @param array|WP_Error $response The wp_remote_* response.
	 * @return array|WP_Error Decoded body or error.
	 */
	private function parse_response( $response ) {
		if ( is_wp_error( $response ) ) {
			return $response;
		}

		$code = wp_remote_retrieve_response_code( $response );
		$body = wp_remote_retrieve_body( $response );
		$data = json_decode( $body, true );

		if ( $code < 200 || $code >= 300 ) {
			$message = isset( $data['detail'] ) ? $data['detail'] : $body;
			return new \WP_Error(
				'opal_api_error',
				sprintf(
					/* translators: 1: HTTP status code 2: error message */
					__( 'Opal API error (%1$d): %2$s', 'opal-ai-photography' ),
					$code,
					$message
				),
				array(
					'status' => $code,
					'body'   => $data,
				)
			);
		}

		if ( null === $data ) {
			return new \WP_Error( 'opal_json_error', __( 'Invalid JSON response from Opal API.', 'opal-ai-photography' ) );
		}

		return $data;
	}

	/**
	 * Get the current token balance.
	 *
	 * @return array|WP_Error {token_balance: int}
	 */
	public function get_balance() {
		return $this->get( '/v1/billing/balance' );
	}

	/**
	 * Get available billing packages.
	 *
	 * @return array|WP_Error {packages: [...]}
	 */
	public function get_packages() {
		return $this->get( '/v1/billing/packages' );
	}

	/**
	 * Create a processing job.
	 *
	 * @param array $items             Array of {filename, scene_prompt, scene_count}.
	 * @param array $processing_options {remove_background, generate_scene, upscale}.
	 * @return array|WP_Error {job_id, items: [{item_id, filename}]}
	 */
	public function create_job( $items, $processing_options ) {
		return $this->post(
			'/v1/jobs',
			array(
				'items'              => $items,
				'processing_options' => $processing_options,
			)
		);
	}

	/**
	 * Upload an image for a job item.
	 *
	 * @param string $file_path Absolute path to the image file.
	 * @param string $job_id    The job ID.
	 * @param string $item_id   The item ID.
	 * @return array|WP_Error {ok, raw_blob_path}
	 */
	public function upload_image( $file_path, $job_id, $item_id ) {
		return $this->post_multipart(
			'/v1/uploads/direct',
			$file_path,
			array(
				'job_id'  => $job_id,
				'item_id' => $item_id,
			)
		);
	}

	/**
	 * Complete an upload to trigger processing.
	 *
	 * @param string $job_id             The job ID.
	 * @param string $item_id            The item ID.
	 * @param string $filename           The filename.
	 * @param array  $processing_options Processing options.
	 * @return array|WP_Error {ok}
	 */
	public function complete_upload( $job_id, $item_id, $filename, $processing_options ) {
		return $this->post(
			'/v1/uploads/complete',
			array(
				'job_id'             => $job_id,
				'item_id'            => $item_id,
				'filename'           => $filename,
				'processing_options' => $processing_options,
			)
		);
	}

	/**
	 * Get job status and results.
	 *
	 * @param string $job_id The job ID.
	 * @return array|WP_Error {job_id, status, items: [{item_id, status, output_blob_path}]}
	 */
	public function get_job( $job_id ) {
		return $this->get( '/v1/jobs/' . urlencode( $job_id ) );
	}

	/**
	 * Get a download URL for a processed item.
	 *
	 * @param string $item_id The item ID.
	 * @return array|WP_Error {download_url}
	 */
	public function get_download_url( $item_id ) {
		return $this->get( '/v1/downloads/' . urlencode( $item_id ) );
	}

	/**
	 * Test the API connection with current settings.
	 *
	 * @return array|WP_Error Balance data on success, WP_Error on failure.
	 */
	public function test_connection() {
		return $this->get_balance();
	}
}
