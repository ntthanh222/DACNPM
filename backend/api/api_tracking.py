"""
API Usage Tracking Middleware

Tracks usage of external APIs (VirusTotal, NIST NVD, Gemini, OpenAI)
with database persistence for admin monitoring and rate limit management.
"""
import logging
import json
from datetime import date, datetime
from typing import Optional, Dict, Any
from functools import wraps
from backend.database.connection import supabase_admin

logger = logging.getLogger(__name__)

# API configuration with daily limits
API_LIMITS = {
    'virustotal': {
        'daily_limit': 500,  # Free tier: 500 requests/day
        'description': 'VirusTotal API'
    },
    'nist_nvd': {
        'daily_limit': 50,  # NIST NVD API rate limit
        'description': 'NIST NVD API'
    },
    'gemini': {
        'daily_limit': 1500,  # Gemini API free tier
        'description': 'Google Gemini API'
    },
    'openai': {
        'daily_limit': 100,  # Placeholder for OpenAI if needed
        'description': 'OpenAI API'
    }
}


class APIUsageTracker:
    """Track API usage with database persistence"""

    @staticmethod
    def increment_usage(api_name: str, increment: int = 1) -> bool:
        """
        Increment API usage counter for today.

        Args:
            api_name: Name of the API (virustotal, nist_nvd, gemini, openai)
            increment: Number of requests to add (default: 1)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            today = date.today().isoformat()

            # Try to update existing record
            update_data = {
                'request_count': increment,  # This will be added to existing count
                'updated_at': datetime.now().isoformat()
            }

            # Use raw SQL to increment counter atomically
            # First, try to get existing record
            existing = supabase_admin.table('api_usage_tracking').select('*').eq('api_name', api_name).eq('date', today).execute()

            if existing.data:
                # Update existing record
                current_count = existing.data[0].get('request_count', 0)
                new_count = current_count + increment

                supabase_admin.table('api_usage_tracking').update({
                    'request_count': new_count,
                    'updated_at': datetime.now().isoformat()
                }).eq('api_name', api_name).eq('date', today).execute()
            else:
                # Create new record
                supabase_admin.table('api_usage_tracking').insert({
                    'api_name': api_name,
                    'date': today,
                    'request_count': increment,
                    'limit_cap': API_LIMITS.get(api_name, {}).get('daily_limit'),
                    'last_reset_at': datetime.now().isoformat(),
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }).execute()

            logger.debug(f"Incremented {api_name} usage by {increment}")
            return True

        except Exception as e:
            logger.error(f"Error incrementing API usage for {api_name}: {e}")
            return False

    @staticmethod
    def get_usage(api_name: str, days: int = 30) -> Dict[str, Any]:
        """
        Get API usage statistics for an API.

        Args:
            api_name: Name of the API
            days: Number of days to look back (default: 30)

        Returns:
            Dict with usage statistics
        """
        try:
            start_date = (date.today() - __import__('datetime').timedelta(days=days)).isoformat()

            response = supabase_admin.table('api_usage_tracking').select('*').eq('api_name', api_name).gte('date', start_date).order('date', desc=True).execute()

            total_requests = sum(record.get('request_count', 0) for record in response.data)

            return {
                'api_name': api_name,
                'total_requests': total_requests,
                'daily_records': response.data,
                'limit_cap': API_LIMITS.get(api_name, {}).get('daily_limit')
            }

        except Exception as e:
            logger.error(f"Error getting API usage for {api_name}: {e}")
            return {
                'api_name': api_name,
                'total_requests': 0,
                'daily_records': [],
                'error': str(e)
            }

    @staticmethod
    def check_rate_limit(api_name: str) -> tuple[bool, int]:
        """
        Check if API is within rate limits.

        Args:
            api_name: Name of the API

        Returns:
            tuple: (within_limit, remaining_requests)
        """
        try:
            today = date.today().isoformat()
            limit = API_LIMITS.get(api_name, {}).get('daily_limit', float('inf'))

            if limit == float('inf'):
                return True, float('inf')

            response = supabase_admin.table('api_usage_tracking').select('request_count').eq('api_name', api_name).eq('date', today).execute()

            if response.data:
                current_usage = response.data[0].get('request_count', 0)
            else:
                current_usage = 0

            remaining = max(0, limit - current_usage)
            within_limit = current_usage < limit

            return within_limit, remaining

        except Exception as e:
            logger.error(f"Error checking rate limit for {api_name}: {e}")
            # If we can't check, allow the request (fail open)
            return True, float('inf')

    @staticmethod
    def reset_daily_counters() -> int:
        """
        Reset daily API usage counters (called at midnight).

        Returns:
            int: Number of records reset
        """
        try:
            yesterday = (date.today() - __import__('datetime').timedelta(days=1)).isoformat()

            # Update records from yesterday to reset their counters
            response = supabase_admin.table('api_usage_tracking').select('id').lt('date', date.today().isoformat()).execute()

            reset_count = 0
            for record in response.data:
                supabase_admin.table('api_usage_tracking').update({
                    'request_count': 0,
                    'last_reset_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }).eq('id', record['id']).execute()
                reset_count += 1

            logger.info(f"Reset {reset_count} API usage counters")
            return reset_count

        except Exception as e:
            logger.error(f"Error resetting API counters: {e}")
            return 0


# Decorator for tracking API calls
def track_api_call(api_name: str):
    """
    Decorator to track API calls automatically.

    Usage:
        @track_api_call('virustotal')
        def call_virustotal(url):
            # API call implementation
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check rate limit before making call
            within_limit, remaining = APIUsageTracker.check_rate_limit(api_name)

            if not within_limit:
                logger.warning(f"Rate limit exceeded for {api_name}")
                raise Exception(f"Rate limit exceeded for {api_name}. Please try again tomorrow.")

            try:
                # Make the API call
                result = func(*args, **kwargs)

                # Track successful call
                APIUsageTracker.increment_usage(api_name)

                return result

            except Exception as e:
                # Still track the call even if it failed
                APIUsageTracker.increment_usage(api_name)
                raise e

        return wrapper
    return decorator


# Convenience functions for common APIs
def track_virustotal(func):
    """Track VirusTotal API calls"""
    return track_api_call('virustotal')(func)

def track_nist_nvd(func):
    """Track NIST NVD API calls"""
    return track_api_call('nist_nvd')(func)

def track_gemini(func):
    """Track Gemini API calls"""
    return track_api_call('gemini')(func)

def track_openai(func):
    """Track OpenAI API calls"""
    return track_api_call('openai')(func)


# ============================================================================
# Integration Examples
# ============================================================================

if __name__ == "__main__":
    # Example usage
    tracker = APIUsageTracker()

    # Track some API calls
    tracker.increment_usage('virustotal', 5)
    tracker.increment_usage('gemini', 2)

    # Check rate limits
    print("VirusTotal:", tracker.check_rate_limit('virustotal'))
    print("Gemini:", tracker.check_rate_limit('gemini'))

    # Get usage statistics
    print("VirusTotal Usage:", tracker.get_usage('virustotal', days=7))