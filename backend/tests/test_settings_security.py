import os
import pytest
from pydantic import ValidationError
from backend.config.settings import Settings

def test_test_environment_prevents_production_supabase():
    # If environment is 'test', and supabase_url is the production one, it should fail
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            environment='test',
            supabase_url='https://aivvorhfsxjpfeqpcxxh.supabase.co',
            supabase_key='test',
            supabase_service_role_key='test'
        )
    assert "Test/QA environment must not connect to the production Supabase database." in str(exc_info.value)

def test_qa_environment_prevents_production_supabase():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            environment='qa',
            supabase_url='https://aivvorhfsxjpfeqpcxxh.supabase.co',
            supabase_key='test',
            supabase_service_role_key='test'
        )
    assert "Test/QA environment must not connect to the production Supabase database." in str(exc_info.value)

def test_production_environment_requires_secure_jwt():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            environment='production',
            jwt_secret='change-this-to-a-secure-random-key-in-production',
            supabase_url='https://example.supabase.co',
            supabase_key='test',
            supabase_service_role_key='test'
        )
    assert "Must set a secure JWT_SECRET in production" in str(exc_info.value)

def test_production_environment_requires_debug_false():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            environment='production',
            jwt_secret='secure-key-1234567890',
            api_debug=True,
            supabase_url='https://example.supabase.co',
            supabase_key='test',
            supabase_service_role_key='test'
        )
    assert "API_DEBUG must be false in production" in str(exc_info.value)
