# Bargain Hunters — Project Context

## What this is
A WhatsApp-based bargain hunting platform. Django + n8n MVP, expanding to 
include a React Native mobile app and Next.js website.

## Current stack
- Django backend (MVP)
- n8n for WhatsApp automation flows
- PostgreSQL database
- [add your other dependencies here]

## Target architecture
- Django REST API as single source of truth for all clients
- React Native (Expo) mobile app
- Next.js website + merchant portal
- Shared monorepo with packages/api-client (typed hooks shared across web + mobile)
- Celery + Redis for async tasks
- Django Channels for real-time deal updates
- n8n stays as WhatsApp/webhook glue, calls Django API only

## Key decisions already made
- JWT auth across all clients
- Versioned DRF endpoints
- n8n must not write to DB directly — always via Django API
- Monorepo structure: apps/django-api, apps/web, apps/mobile, packages/api-client

## Brand Guidelines

### Colors
Use these values consistently across web (Tailwind), mobile (theme.ts), and any future clients.

| Token | Hex | Usage |
|---|---|---|
| `brand-600` / `primary` | `#E54416` | Primary buttons, active states, CTAs |
| `brand-700` / `primaryDark` | `#C73D0F` | Hover/pressed states, dark accents |
| `brand-500` / `primaryMedium` | `#F97316` | Secondary highlights |
| `brand-100` / `primaryAccent` | `#FDEBD0` | Tinted backgrounds, badges |
| `brand-50` / `primaryLight` | `#FFF9F1` | Page/screen backgrounds |
| `surface` | `#FFFFFF` | Cards, modals, input backgrounds |
| `background` | `#F9FAFB` | App/page background |
| `textPrimary` | `#111827` | Headings and body copy |
| `textSecondary` | `#6B7280` | Labels, subtext |
| `textMuted` | `#9CA3AF` | Placeholders, disabled text |
| `border` | `#E5E7EB` | Dividers, card borders |

**Android native** — keep `colors.xml` in sync: `splashscreen_background`, `iconBackground`, `colorPrimary` = `#E54416`; `colorPrimaryDark` = `#C73D0F`.

### Typography
- **Web**: Tailwind default system-font stack; no custom font loaded yet.
- **Mobile**: System font stack (San Francisco on iOS, Roboto on Android).
- **Weights**: 400 regular · 600 semibold · 700 bold.
- **Future**: Plan to load **Inter** (or similar geometric sans) via `expo-font` + `@expo-google-fonts/inter` for consistent cross-platform look.

### Design Principles
- Backgrounds: `brand-50` (`#FFF9F1`) screen fill, white cards with subtle shadows.
- Primary actions: solid `brand-600` fill, white text, rounded corners (10–16 px).
- Secondary/outline actions: white fill, `brand-600` border and text.
- Status badges: use `brand-100` background + `brand-700` text.
- Keep the brand warm and energetic — orange-red conveys urgency and value (deals!).

## Current priorities
- [add what you're working on first]

## Git Commits
- On every major code change, commit the changes and push to master branch