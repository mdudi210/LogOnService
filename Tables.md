+-------------------+
| User |
+-------------------+
| id (UUID) (PK) |
| email |
| username |
| role |
| is_active |
| is_verified |
| created_at |
| updated_at |
| deleted_at |
+-------------------+
|
| 1
|
| 1
+------------------------+
| UserCredential |
+------------------------+
| id (UUID) (PK) |
| user_id (FK) |
| password_hash |
| hash_algorithm |
| password_changed_at |
| created_at |
+------------------------+

        |
        | 1
        |
        | *

+-------------------+
| UserDevice |
+-------------------+
| id (UUID) (PK) |
| user_id (FK) |
| device_name |
| device_fingerprint |
| user_agent_hash |
| ip_address |
| is_trusted |
| created_at |
| last_used_at |
+-------------------+

        |
        | 1
        |
        | *

+-------------------+
| Session |
+-------------------+
| id (UUID) (PK) |
| user_id (FK) |
| device_id |
| session_started_at |
| session_expires_at |
| is_revoked |
| revoked_at |
+-------------------+

        |
        | 1
        |
        | *

+-------------------+
| UserMFA |
+-------------------+
| id (UUID) (PK) |
| user_id (FK) |
| mfa_type |
| secret_encrypted |
| is_enabled |
| created_at |
+-------------------+

        |
        | 1
        |
        | *

+-------------------+
| OAuthAccount |
+-------------------+
| id (UUID) (PK) |
| user_id (FK) |
| provider |
| provider_user_id |
| access_token_encrypted |
| refresh_token_encrypted |
| linked_at |
+-------------------+

        |
        | 1
        |
        | *

+-------------------+
| AuditLog |
+-------------------+
| id (UUID) (PK) |
| user_id (FK) |
| event_type |
| ip_address |
| metadata (JSONB) |
| created_at |
+-------------------+
