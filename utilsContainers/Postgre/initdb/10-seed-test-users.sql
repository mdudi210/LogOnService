-- Idempotent seed data for local testing
-- Admin login: admin@logonservices.local / Admin@12345
-- User login: user@logonservices.local / User@12345

INSERT INTO users (
    id, email, username, role, is_active, is_verified, created_at, updated_at
)
VALUES
    ('11111111-1111-1111-1111-111111111111', 'admin@logonservices.local', 'admin_test', 'admin', TRUE, TRUE, NOW(), NOW()),
    ('22222222-2222-2222-2222-222222222222', 'user@logonservices.local', 'user_test', 'user', TRUE, TRUE, NOW(), NOW())
ON CONFLICT (email) DO UPDATE SET
    username = EXCLUDED.username,
    role = EXCLUDED.role,
    is_active = EXCLUDED.is_active,
    is_verified = EXCLUDED.is_verified,
    updated_at = NOW();

INSERT INTO user_credentials (
    id, user_id, password_hash, password_salt, hash_algorithm, password_changed_at, created_at
)
VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111', '$argon2id$v=19$m=65536,t=3,p=4$Jouttv0zMXNItHi7AEuVQA$CliUAgtKWMedBLmr0ZFYdNfboS4JHpbb1ID886PwJ3w', 'Vibv9uyw7JXlfA0UKZM6Qxdcz2e4oPo0', 'argon2id', NOW(), NOW()),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '22222222-2222-2222-2222-222222222222', '$argon2id$v=19$m=65536,t=3,p=4$h3iLDU0Ftcix/45FAN0e+Q$XjAdYl1S/Hhy21K8/cEpZLvsUPuDpmA6j7meBvb6h8M', 'G1tKN3MBIfg5097W0YuoAFnSKgnjaMbZ', 'argon2id', NOW(), NOW())
ON CONFLICT (user_id) DO UPDATE SET
    password_hash = EXCLUDED.password_hash,
    password_salt = EXCLUDED.password_salt,
    hash_algorithm = EXCLUDED.hash_algorithm,
    password_changed_at = NOW();
