<?php
/**
 * Uninstall handler — runs when the plugin is deleted via the WordPress admin.
 *
 * @package OpalAIPhotography
 */

// Verify this is a legitimate uninstall request.
if ( ! defined( 'WP_UNINSTALL_PLUGIN' ) ) {
	exit;
}

global $wpdb;

// 1. Delete all opal_ options.
$options = array(
	'opal_api_url',
	'opal_api_key_encrypted',
	'opal_default_scene_prompt',
	'opal_remove_bg',
	'opal_generate_scene',
	'opal_upscale',
	'opal_auto_process',
	'opal_auto_replace',
	'opal_keep_originals',
	'opal_activated',
);

foreach ( $options as $option ) {
	delete_option( $option );
}

// 2. Drop custom tables.
$tables = array(
	$wpdb->prefix . 'opal_ab_tests',
	$wpdb->prefix . 'opal_ab_metrics',
);

foreach ( $tables as $table ) {
	// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching, WordPress.DB.DirectDatabaseQuery.SchemaChange
	$wpdb->query( "DROP TABLE IF EXISTS {$table}" ); // phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared
}

// 3. Delete transients.
// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching
$wpdb->query(
	$wpdb->prepare(
		"DELETE FROM {$wpdb->options} WHERE option_name LIKE %s OR option_name LIKE %s",
		'%_transient_opal_%',
		'%_transient_timeout_opal_%'
	)
);

// 4. Delete all Opal post meta from products.
$meta_keys = array(
	'_opal_jobs',
	'_opal_processed_images',
	'_opal_last_processed',
);

foreach ( $meta_keys as $meta_key ) {
	// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching
	$wpdb->delete(
		$wpdb->postmeta,
		array( 'meta_key' => $meta_key ),
		array( '%s' )
	);
}

// 5. Delete A/B tracking order meta.
// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching
$wpdb->delete(
	$wpdb->postmeta,
	array( 'meta_key' => '_opal_ab_tracked' ),
	array( '%s' )
);

// 6. Clean up any Action Scheduler actions.
// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching
$wpdb->query(
	$wpdb->prepare(
		"DELETE FROM {$wpdb->prefix}actionscheduler_actions WHERE hook LIKE %s",
		'opal_%'
	)
);
