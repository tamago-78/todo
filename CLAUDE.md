# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Todo Progressive Web App (PWA) built with React 18 + TypeScript + Vite, using MUI (Material UI v5) for components and Emotion for styling. Todos are persisted client-side with localforage (IndexedDB). Comments in the codebase are written in Japanese.

## Commands

```bash
npm run dev        # Start Vite dev server
npm run build      # Type-check (tsc) then build for production
npm run preview    # Preview the production build
npm test           # Run tests with Vitest (watch mode; coverage is always collected)
npx vitest run     # Run tests once (no watch)
npx vitest run src/__tests__/isTodos.test.ts   # Run a single test file
npx eslint src --ext .ts,.tsx    # Lint (no npm script defined)
npx prettier --write src         # Format (no npm script defined)
```

## Gotchas

- The ESLint config file is named `.eslistrc.json` — note the typo (missing "n" in "eslint"). Modern ESLint does not auto-discover this filename, so pass it explicitly if needed: `npx eslint -c .eslistrc.json src --ext .ts,.tsx`. If you rename it to `.eslintrc.json`, keep its contents intact.
- Vitest is configured with `globals: true` (no need to import `describe`/`it`/`expect`; `tsconfig.json` includes `"types": ["vitest/globals"]`) and `environment: 'jsdom'`. Coverage (`@vitest/coverage-c8`, text reporter) is enabled on every test run.
- `vite.config.ts` sets `base: './'` (relative paths) so the build works when hosted under a subpath such as GitHub Pages. Do not change this to `/`.
- Prettier is configured with `singleQuote: true`; ESLint extends `prettier` to disable conflicting rules.

## Architecture

Single-page app with all state held in one component:

- `src/main.tsx` — entry point; renders `<App />` and registers the PWA service worker via `virtual:pwa-register`.
- `src/App.tsx` — owns ALL application state (`todos`, `filter`, input `text`, and open/closed flags for the drawer, dialogs, and QR modal) and passes state + handlers down as props. There is no state management library, router, or context; child components are purely presentational.
- Child components (one per file at `src/` root): `ToolBar` (app bar), `SideBar` (MUI Drawer with filter menu), `TodoItem` (todo list rendering + filtering), `FormDialog` (new-todo input), `AlertDialog` (confirm emptying trash), `ActionButton` (FAB), `QR` (QR code modal via react-qrcode-logo).
- `src/@types/*.d.ts` — ambient global type declarations. `Todo` and `Filter` (`'all' | 'checked' | 'unchecked' | 'removed'`) are globally available without imports; follow this pattern for new shared types.
- `src/lib/isTodos.ts` — runtime type guards used to validate data loaded from localforage.
- `src/__tests__/` — Vitest tests.

Key data-flow details:

- Todos are soft-deleted: `removed: true` marks a todo as trashed; `handleOnEmpty` in `App.tsx` permanently filters them out.
- Todo updates go through the single generic handler `handleOnTodo(obj, key, value)` in `App.tsx`, which deep-copies the array and mutates the matching todo's property — use it for toggling `checked`/`removed` and editing `value` rather than adding new handlers.
- Persistence: two `useEffect` hooks in `App.tsx` load from and save to the localforage key `todo-20200101`. Loaded data is validated with `isTodos` before being set.

## PWA

The manifest and icons are configured inline in `vite.config.ts` via `vite-plugin-pwa`; icon files live in `public/`. Changes to app name, theme color, or icons go in `vite.config.ts`, not a standalone manifest file.
