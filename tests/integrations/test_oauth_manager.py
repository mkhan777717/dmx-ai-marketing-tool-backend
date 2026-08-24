from app.integrations.oauth.manager import OAuthManager


def test_pkce_verifier_generation():
    verifier = OAuthManager._generate_pkce_verifier()
    assert isinstance(verifier, str)
    assert len(verifier) >= 43


def test_s256_challenge_generation():
    verifier = "this_is_a_test_verifier_for_pkce_challenge_generation"
    challenge = OAuthManager._generate_pkce_challenge(verifier)
    assert isinstance(challenge, str)
    assert "=" not in challenge  # base64url encoding should not have padding
    # Known hash for this verifier
    # sha256("this_is_a_test_verifier_for_pkce_challenge_generation") -> ...
    assert challenge != verifier
    assert challenge == "rE6EaNJncZiunpu8cY8FuKqP9WYxwSJF2jGg-z0AZqg"


def test_url_contains_code_challenge_for_pkce_provider():
    workspace_id = "test-ws-id"
    provider = "twitter"
    state = OAuthManager.generate_state(workspace_id, provider)

    url = OAuthManager.get_authorization_url(
        provider=provider,
        state=state,
        redirect_uri="http://localhost/callback",
        client_id="testclient",
    )

    assert "code_challenge=" in url
    assert "code_challenge_method=S256" in url
    assert "state=" in url

    # Cleanup state
    OAuthManager.validate_state(state)


def test_stored_oauth_state_contains_code_verifier():
    workspace_id = "test-ws-id"
    provider = "x"
    state = OAuthManager.generate_state(workspace_id, provider)

    state_data = OAuthManager._states.get(state)
    assert state_data is not None
    assert "code_verifier" in state_data
    assert isinstance(state_data["code_verifier"], str)

    # Cleanup state
    OAuthManager.validate_state(state)


def test_callback_retrieves_verifier_and_state_is_single_use():
    workspace_id = "test-ws-id"
    provider = "twitter"
    state = OAuthManager.generate_state(workspace_id, provider)

    state_data_before = OAuthManager._states.get(state)
    assert state_data_before is not None

    state_data = OAuthManager.validate_state(state)
    assert state_data is not None
    assert state_data["workspace_id"] == workspace_id
    assert state_data["provider"] == provider
    assert state_data["code_verifier"] is not None

    # State should be removed
    assert OAuthManager.validate_state(state) is None


def test_existing_non_pkce_provider_flow_still_works_without_verifier():
    workspace_id = "test-ws-id"
    provider = "slack"
    state = OAuthManager.generate_state(workspace_id, provider)

    state_data = OAuthManager._states.get(state)
    assert state_data is not None
    assert state_data.get("code_verifier") is None

    url = OAuthManager.get_authorization_url(
        provider=provider,
        state=state,
        redirect_uri="http://localhost/callback",
        client_id="testclient",
    )
    assert "code_challenge=" not in url

    validated = OAuthManager.validate_state(state)
    assert validated is not None
    assert validated["code_verifier"] is None


def test_missing_invalid_state_fails_normally():
    assert OAuthManager.validate_state("invalid_state_123") is None


def test_google_oauth_url():
    workspace_id = "test-ws-id"
    provider = "google"
    state = OAuthManager.generate_state(workspace_id, provider)

    url = OAuthManager.get_authorization_url(
        provider=provider,
        state=state,
        redirect_uri="http://localhost/callback",
        client_id="testclient",
    )

    assert "accounts.google.com/o/oauth2/v2/auth" in url
    assert "business.manage" in url
    assert "access_type=offline" in url
    assert "prompt=consent" in url
    assert f"state={state}" in url

    # Cleanup
    OAuthManager.validate_state(state)


def test_facebook_oauth_url():
    workspace_id = "test-ws-id"
    provider = "facebook"
    state = OAuthManager.generate_state(workspace_id, provider)

    url = OAuthManager.get_authorization_url(
        provider=provider,
        state=state,
        redirect_uri="http://localhost/callback",
        client_id="fb_client_123",
    )

    assert "www.facebook.com/v26.0/dialog/oauth" in url
    assert "client_id=fb_client_123" in url
    assert "pages_show_list" in url
    assert "pages_manage_posts" in url
    assert "publish_video" not in url
    assert f"state={state}" in url

    # Cleanup
    OAuthManager.validate_state(state)


def test_instagram_oauth_url():
    workspace_id = "test-ws-id"
    provider = "instagram"
    state = OAuthManager.generate_state(workspace_id, provider)

    url = OAuthManager.get_authorization_url(
        provider=provider,
        state=state,
        redirect_uri="http://localhost/callback",
        client_id="ig_client_123",
    )

    assert "www.facebook.com/v26.0/dialog/oauth" in url
    assert "client_id=ig_client_123" in url
    assert "instagram_basic" in url
    assert "instagram_content_publish" in url
    assert "pages_show_list" in url
    assert "publish_video" not in url
    assert f"state={state}" in url

    # Cleanup
    OAuthManager.validate_state(state)
