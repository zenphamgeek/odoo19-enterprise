# Insilos Theme Genesis (`insilos_theme_genesis`)

Enterprise design system and dual-theme SCSS architecture for Insilos Enterprise 20, implementing IBM Carbon Design System 11 and SAP Fiori Horizon ergonomics.

## Key Modules & Stylesheets

| File | Bundle | Purpose |
| :--- | :--- | :--- |
| [`static/src/scss/insilos_modern_tokens.scss`](file:///home/zen/O20/enterprise/insilos_theme_genesis/static/src/scss/insilos_modern_tokens.scss) | `web.assets_backend` | Root Light Mode design tokens (`--insilos-bg-*`, `--insilos-text-*`, `--insilos-border-*`) |
| [`static/src/scss/insilos_modern_tokens.dark.scss`](file:///home/zen/O20/enterprise/insilos_theme_genesis/static/src/scss/insilos_modern_tokens.dark.scss) | `web.assets_web_dark` | Root Dark Mode design tokens and `--bs-body-color` overrides |
| [`static/src/scss/insilos_systray_restructure.scss`](file:///home/zen/O20/enterprise/insilos_theme_genesis/static/src/scss/insilos_systray_restructure.scss) | `web.assets_backend` | 48px ShellBar, single launcher icon guard, flexbox overflow containment |
| [`static/src/scss/insilos_form_restructure.scss`](file:///home/zen/O20/enterprise/insilos_theme_genesis/static/src/scss/insilos_form_restructure.scss) | `web.assets_backend` | 100% full-width `.o_form_sheet`, 48px action baseline, Carbon tabs |
| [`static/src/scss/insilos_webclient_general.dark.scss`](file:///home/zen/O20/enterprise/insilos_theme_genesis/static/src/scss/insilos_webclient_general.dark.scss) | `web.assets_web_dark` | Dark Mode component overrides (zero bare white surfaces, dark launcher logo toggle) |

## Quick Verification

```bash
# 1. Counter-Code Security Scanner (must return 0 detections)
python3 scripts/counter_code_scanner.py --path . --scope enterprise/insilos_theme_genesis addons/web enterprise/web_studio --max-allowed-detections 0

# 2. Dual-Theme Playwright E2E Audit (Light & Dark modes)
node tools/audit_crm_dual_theme.js
```

## Full Architecture Documentation
See [`docs/SOVEREIGN_DUAL_THEME_AND_FORM_ARCHITECTURE.md`](file:///home/zen/O20/docs/SOVEREIGN_DUAL_THEME_AND_FORM_ARCHITECTURE.md).
