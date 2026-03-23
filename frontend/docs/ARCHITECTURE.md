# Frontend Architecture

## Design Goals
- Keep frontend fully isolated under `frontend/`
- Keep business features modular by domain
- Align with cookie-auth backend security model (no localStorage token persistence)

## Security Model
- API requests use `credentials: include`
- CSRF header (`X-CSRF-Token`) is injected from `csrf_token` cookie for mutating methods
- Access/refresh cookies remain HttpOnly and are never manually read by frontend code

## Modules
- `src/app/AuthContext.tsx`
  - Hydrates current user via `/users/me`
  - Exposes `reload()` and `logout()` to pages/components
- `src/lib/api.ts`
  - Single request wrapper
  - Normalized error handling
  - API operations grouped by domain (auth/user/admin)
- `src/features/*`
  - `auth`: entry/login
  - `user`: personal security/session controls
  - `admin`: observability + governance controls

## Routing Strategy
- Public route: `/login`
- Authenticated routes: `/`, `/sessions`, `/security`
- Admin-only routes: `/admin/events`, `/admin/config`
- Route guard enforces auth and admin role branch

## Container Strategy
- `Dockerfile.dev`: hot-reload development container
- `Dockerfile`: production static bundle served with Nginx
- `docker-compose.yml`: both modes under one frontend-local compose file

