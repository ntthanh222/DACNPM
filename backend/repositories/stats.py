from typing import Dict, List
from collections import Counter
from backend.database.connection import supabase, supabase_admin


def get_vulnerability_distribution() -> Dict[str, int]:
    """
    Analyze chat history to extract vulnerability type distribution
    Based on intent classification and entity extraction from Rasa

    Returns dict with vulnerability types and counts:
    {
        "injection": 45,
        "cross_site_scripting": 32,
        "authentication": 28,
        "remote_code_execution": 19,
        "memory_corruption": 12,
        "csrf": 8,
        "other": 15
    }
    """
    # Define vulnerability-related intents
    vuln_intents = [
        'sql_injection', 'xss', 'csrf', 'rce',
        'authentication', 'authorization', 'injection',
        'buffer_overflow', 'memory_corruption', 'command_injection',
        'ldap_injection', 'session_management'
    ]

    # Get recent chat history with vulnerability-related intents
    try:
        # Use supabase_admin to bypass RLS restrictions for server-side statistics
        client = supabase_admin if supabase_admin else supabase
        if not client:
            return {
                "injection": 0, "cross_site_scripting": 0,
                "authentication": 0, "remote_code_execution": 0,
                "memory_corruption": 0, "csrf": 0, "other": 0, "total": 0,
                "message": "Database not configured. Supabase connection required."
            }
        response = client.table('chat_history').select('*')\
            .not_.is_('intent', 'null')\
            .order('created_at', desc=True)\
            .limit(1000)\
            .execute()

        chat_messages = response.data

        # Count occurrences of each vulnerability type
        vuln_distribution = Counter()

        for chat in chat_messages:
            intent = chat.get('intent', 'other')
            if intent in vuln_intents:
                vuln_distribution[intent] += 1

            # Also analyze entities for additional context
            entities = chat.get('entities', {})
            if isinstance(entities, dict):
                for entity_type in entities.keys():
                    if entity_type in vuln_intents:
                        vuln_distribution[entity_type] += 1
            elif isinstance(entities, list):
                for entity in entities:
                    entity_type = entity.get('entity')
                    if entity_type and entity_type in vuln_intents:
                        vuln_distribution[entity_type] += 1

        # Normalize to standard vulnerability categories
        normalized = normalize_vulnerability_categories(dict(vuln_distribution))

        # Add total count
        normalized['total'] = sum(normalized.values())

        return normalized

    except Exception as e:
        print(f"Error fetching vulnerability distribution: {e}")
        # Return empty state - no fake data
        return {
            "injection": 0,
            "cross_site_scripting": 0,
            "authentication": 0,
            "remote_code_execution": 0,
            "memory_corruption": 0,
            "csrf": 0,
            "other": 0,
            "total": 0,
            "message": "No vulnerability data available. Start chatting to generate statistics."
        }


def normalize_vulnerability_categories(raw_stats: Dict[str, int]) -> Dict[str, int]:
    """
    Group raw intent/entity counts into standard vulnerability categories

    Categories:
    - injection: sql_injection, command_injection, ldap_injection
    - cross_site_scripting: xss, cross_site_scripting
    - authentication: authentication, authorization, session_management
    - remote_code_execution: rce, remote_code_execution
    - memory_corruption: buffer_overflow, memory_corruption
    - csrf: csrf
    - other: all other categories
    """
    category_mapping = {
        'sql_injection': 'injection',
        'command_injection': 'injection',
        'ldap_injection': 'injection',
        'injection': 'injection',
        'xss': 'cross_site_scripting',
        'cross_site_scripting': 'cross_site_scripting',
        'authentication': 'authentication',
        'authorization': 'authentication',
        'session_management': 'authentication',
        'rce': 'remote_code_execution',
        'remote_code_execution': 'remote_code_execution',
        'buffer_overflow': 'memory_corruption',
        'memory_corruption': 'memory_corruption',
        'csrf': 'csrf'
    }

    normalized = {
        'injection': 0,
        'cross_site_scripting': 0,
        'authentication': 0,
        'remote_code_execution': 0,
        'memory_corruption': 0,
        'csrf': 0,
        'other': 0
    }

    for vuln_type, count in raw_stats.items():
        category = category_mapping.get(vuln_type, 'other')
        normalized[category] += count

    return normalized


def get_chat_statistics(limit: int = 1000, user_id: str = None) -> Dict:
    """
    Get aggregate chat statistics
    """
    try:
        # Use supabase_admin to bypass RLS restrictions for server-side statistics
        client = supabase_admin if supabase_admin else supabase
        if not client:
            return {
                "total_conversations": 0, "unique_intents": 0,
                "top_intents": [], "average_message_length": 0,
                "message": "Database not configured."
            }
        query = client.table('chat_history').select('*')
        if user_id:
            query = query.eq('user_id', str(user_id))
        response = query.order('created_at', desc=True).limit(limit).execute()

        messages = response.data

        # Calculate statistics
        total_conversations = len(messages)
        intents = [msg.get('intent') for msg in messages if msg.get('intent')]

        intent_distribution = Counter(intents)

        return {
            "total_conversations": total_conversations,
            "unique_intents": len(intent_distribution),
            "top_intents": intent_distribution.most_common(5),
            "average_message_length": sum(
                len(msg.get('user_message', '')) for msg in messages
            ) / total_conversations if total_conversations > 0 else 0
        }
    except Exception as e:
        print(f"Error fetching chat statistics: {e}")
        return {
            "total_conversations": 0,
            "unique_intents": 0,
            "top_intents": [],
            "average_message_length": 0,
            "message": "No chat history available. Start a conversation to see statistics."
        }


def get_system_health_stats() -> Dict:
    """
    Get system health metrics
    """
    import time
    from backend.database.connection import supabase_admin

    # Test database connectivity
    start_time = time.time()
    try:
        if not supabase_admin:
            return {
                "database_status": "not_configured",
                "database_latency_ms": None,
                "rasa_status": "unknown",
                "timestamp": time.time()
            }
        # Simple query to test database connection
        supabase_admin.table('users').select('id').limit(1).execute()
        db_latency = round((time.time() - start_time) * 1000, 2)
        db_status = "healthy"
    except Exception as e:
        print(f"Database health check failed: {e}")
        db_latency = None
        db_status = "error"

    return {
        "database_status": db_status,
        "database_latency_ms": db_latency,
        "rasa_status": "unknown",  # Would require actual ping implementation
        "timestamp": time.time()
    }
