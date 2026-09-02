# Meta Developer API Testing Configuration

To perform real end-to-end testing with the Facebook and Instagram integrations, you must configure a Meta App in the Meta Developer Dashboard. No credentials are included in this repository.

## 1. Meta App Configuration
1. Go to [Meta for Developers](https://developers.facebook.com/).
2. Create a new App and select the **Business** app type.
3. Once created, navigate to **App Settings > Basic** to retrieve your `App ID` and `App Secret`.
4. Inject these into your backend environment as:
   - `FACEBOOK_CLIENT_ID`
   - `FACEBOOK_CLIENT_SECRET`

## 2. OAuth Redirect URI
1. In the Meta App Dashboard, add the **Facebook Login for Business** product.
2. Under **Facebook Login > Settings**, find the "Valid OAuth Redirect URIs" field.
3. Add your backend callback URL (e.g., `http://localhost:8000/api/v1/integrations/oauth/callback` or your production equivalent).

## 3. Required Permissions
During OAuth, the backend requests the following scopes. These work immediately for users added as "Testers" in your app, but require App Review for public use:

**Facebook Permissions:**
- `pages_show_list`
- `pages_read_engagement`
- `pages_manage_posts`

**Instagram Permissions:**
- `instagram_basic`
- `instagram_content_publish`
- `pages_show_list`
- `pages_read_engagement`

## 4. Test Assets Required
To successfully test the entire sync and publishing lifecycle, you need real test assets:
1. **Facebook Page**: Create a test Facebook Page. Your Meta Developer account must have Admin ("Full Control") access to this page.
2. **Instagram Account**: Create an Instagram account and switch it to a **Professional** or **Creator** account.
3. **Link Accounts**: Inside the Facebook Page settings (or Instagram app), link the Facebook Page to the Instagram Professional account.

## 5. Developer / Tester Roles
1. In the Meta App Dashboard, go to **App Roles > Roles**.
2. Add the personal Facebook account you are using to authenticate as a **Developer** or **Tester**.
3. *Note:* If your app is in "Development" mode, only users explicitly listed in App Roles can successfully complete the OAuth flow and grant permissions.

Once configured, the `/api/v1/integrations/oauth/authorize?provider=facebook` and `provider=instagram` endpoints will successfully redirect to the Meta authorization dialog and return a functional long-lived access token.
