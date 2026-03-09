=== Opal AI Product Photography ===
Contributors: opaloptics
Tags: woocommerce, product photography, ai, background removal, image enhancement
Requires at least: 6.4
Tested up to: 6.7
Requires PHP: 8.0
WC requires at least: 8.0
WC tested up to: 9.5
Stable tag: 1.0.0
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

AI-powered product image enhancement for WooCommerce. Remove backgrounds, generate studio scenes, upscale images, and A/B test product photos — all from your WordPress dashboard.

== Description ==

**Opal AI Product Photography** transforms your WooCommerce product images into professional, studio-quality photos using artificial intelligence.

Stop spending thousands on product photography. Opal enhances your existing images with:

= Background Removal =
Automatically remove cluttered backgrounds and replace them with clean, white studio backdrops. Powered by BiRefNet for industry-leading 256-level alpha mattes.

= AI Scene Generation =
Place your products in realistic studio scenes, lifestyle settings, or custom environments. Describe the scene you want and Opal generates it with FLUX AI.

= Smart Upscaling =
Enlarge product images up to 4x without quality loss. Perfect for zoom-ready, high-resolution product galleries.

= Bulk Catalog Processing =
Process your entire product catalog in one click. Select products, choose your settings, and let Opal enhance every image automatically.

= A/B Image Testing =
Test which product images convert better. Create split tests between original and AI-enhanced images, track views and conversions, and get statistically significant results — all natively in WooCommerce.

= Key Features =

* One-click image enhancement from the product editor
* Bulk processing for entire catalogs
* Background removal with transparent or white output
* AI-generated studio scenes with custom prompts
* Image upscaling up to 4x resolution
* Built-in A/B testing with statistical significance
* Cookie-based visitor segmentation for fair tests
* Automatic conversion tracking (views, add-to-cart, purchases)
* Token-based usage — pay only for what you process
* Token balance displayed in the admin bar
* WooCommerce HPOS compatible
* Processing history per product

== Installation ==

1. Upload the `opal-ai-photography` folder to `/wp-content/plugins/`.
2. Activate the plugin through the 'Plugins' menu in WordPress.
3. Navigate to **Opal AI** in the admin menu.
4. Go to the **Settings** tab and enter your Opal API key.
5. Click **Test Connection** to verify everything is working.
6. Start enhancing images from the **Bulk Process** tab or individual product editors.

= Getting an API Key =

1. Visit [opaloptics.com](https://opaloptics.com) and create an account.
2. Navigate to your dashboard and generate an API key.
3. Copy the key and paste it into the plugin settings.

= Requirements =

* WordPress 6.4 or later
* WooCommerce 8.0 or later
* PHP 8.0 or later
* An active Opal API account with token balance

== Frequently Asked Questions ==

= How does pricing work? =

Opal uses a token-based system. Each image processing operation costs tokens. You can purchase token packages from the Opal dashboard. Your current balance is always visible in the WordPress admin bar.

= What happens to my original images? =

By default, original images are preserved in your WordPress media library. Enhanced images are added alongside them. You can control this behavior in Settings > Keep Originals.

= Can I process my entire catalog at once? =

Yes. Go to Opal AI > Bulk Process, select the products you want to enhance, choose your processing options, and click Start Processing. Progress is tracked in real time.

= How does A/B testing work? =

Create a test by selecting a product and two image variants (e.g., original vs. AI-enhanced). When you start the test, visitors are randomly shown one variant via a cookie. The plugin tracks views, add-to-cart events, and purchases for each variant. Once you have enough data, the plugin calculates statistical significance so you can confidently pick the winner.

= Does this work with WooCommerce HPOS? =

Yes. The plugin declares full compatibility with WooCommerce High-Performance Order Storage (custom order tables).

= What image formats are supported? =

JPEG, PNG, and WebP. Processed images are returned as high-quality PNG files.

= Is my API key stored securely? =

Yes. API keys are encrypted before being stored in the WordPress database. They are never exposed in plain text.

= Can I auto-process new products? =

Yes. Enable "Auto-Process New Products" in the Settings tab. When you publish a new product, its images will be automatically enhanced using your default processing options.

== Screenshots ==

1. Dashboard — Token balance, quick stats, and recent processing jobs.
2. Bulk Processing — Select products and process entire catalogs at once.
3. Product Editor — One-click enhancement from the product sidebar.
4. A/B Testing — Compare image variants with real conversion data.
5. A/B Test Results — Statistical significance, lift percentage, and variant comparison.
6. Settings — API configuration, processing defaults, and automation options.

== Changelog ==

= 1.0.0 =
* Initial release.
* Background removal with BiRefNet AI.
* AI scene generation with custom prompts.
* Smart image upscaling.
* Bulk catalog processing with real-time progress.
* A/B image testing with statistical significance.
* Cookie-based variant assignment.
* Conversion tracking (views, add-to-cart, purchases).
* Product editor metabox with before/after gallery.
* Admin bar token balance display.
* WooCommerce HPOS compatibility.
* Encrypted API key storage.

== Upgrade Notice ==

= 1.0.0 =
Initial release. Install, configure your API key, and start enhancing your product images.

== External Services ==

This plugin communicates with the **Opal API** (`https://opaloptics.com`) to process product images. When you use the plugin, the following data is sent to the Opal service:

* Product images (uploaded for processing)
* Processing options (background removal, scene prompts, upscaling preferences)
* Your API key (for authentication)

No personal customer data, order information, or other WooCommerce data is transmitted.

**Service Terms:**

* [Opal Terms of Service](https://opaloptics.com/terms)
* [Opal Privacy Policy](https://opaloptics.com/privacy)

By using this plugin, you agree to the Opal Terms of Service and Privacy Policy.
