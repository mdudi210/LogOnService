-- Idempotent seed data for local testing
-- Admin login: admin@test.local / Admin@12345
-- User login: user@test.local / User@12345

INSERT INTO users (
    id, email, username, role, is_active, is_verified, created_at, updated_at
)
VALUES
    ('11111111-1111-1111-1111-111111111111', 'admin@test.local', 'admin_test', 'admin', TRUE, TRUE, NOW(), NOW()),
    ('22222222-2222-2222-2222-222222222222', 'user@test.local', 'user_test', 'user', TRUE, TRUE, NOW(), NOW())
ON CONFLICT (email) DO UPDATE SET
    username = EXCLUDED.username,
    role = EXCLUDED.role,
    is_active = EXCLUDED.is_active,
    is_verified = EXCLUDED.is_verified,
    updated_at = NOW();

INSERT INTO user_credentials (
    id, user_id, password_hash, hash_algorithm, password_changed_at, created_at
)
VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111', '$argon2id$v=19$m=65536,t=3,p=4$PsVqaLYSNmCOefs/SaaAMA$K1i6c2Gf09jh62kT+CeB+2bu2K+Kf7eNTvTx7Ig7iXk', 'argon2id', NOW(), NOW()),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '22222222-2222-2222-2222-222222222222', '$argon2id$v=19$m=65536,t=3,p=4$D8xCSSv983jhidCMwMybWQ$tjCaj91zFSP5taYja0SLDcCkuClehvJnXL1cD6rSlcQ', 'argon2id', NOW(), NOW())
ON CONFLICT (user_id) DO UPDATE SET
    password_hash = EXCLUDED.password_hash,
    hash_algorithm = EXCLUDED.hash_algorithm,
    password_changed_at = NOW();
