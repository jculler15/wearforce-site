# The Wearforce — eBay connector

This pulls your live eBay listings into the website automatically.

## When your eBay developer account is approved

1. Log in at https://developer.ebay.com and open your app's keys page
   (often called "Application Keys" or "Keysets"). Use the **Production**
   keys, not Sandbox.

2. You are looking for two values:
   - **App ID (Client ID)**
   - **Cert ID (Client Secret)**

3. Copy this file's template to a real config and paste your keys in:
   - Duplicate `config.example.json` and name the copy `config.json`
   - Paste the App ID into `clientId` and the Cert ID into `clientSecret`
   - `sellerUsername` is already set to `thewearforce`

   (You can also just hand the two keys to Claude and it will fill this in.)

4. Run it:

   ```
   python3 "/Volumes/CullerMedia/The Wearforce/scripts/fetch_ebay.py"
   ```

   It writes your real products into `site/data/products.json`, and the
   website shows them.

## Keep your keys private

`config.json` holds your secret key. Do not post it publicly or commit it
anywhere shared. It stays on your computer (and later, on the website host).

## Later: make it automatic

Once it runs cleanly, we schedule it (every 15–30 minutes) so the site keeps
itself in sync with no effort from you. That happens as part of putting the
site online (Phase 3).
