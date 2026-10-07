# INNORIA & INSILOS ENTERPRISE ASSETS LIBRARY

Canonical repository and media catalog of brand logos, symbols, and partner marks for **ZenCode Enterprise** and **INSILOS Autonomous Enterprise Platform**.

All assets are indexed both on the static filesystem and inside the Odoo Database Assets & Media Library (`ir.attachment` with `public=True`).

---

## 1. ZenCode Enterprise Brand Assets (`/assets_library/zencode/`)

### Vector Formats (SVG)
- **Horizontal Mint Logo**: `zencode-logo-horizontal-mint.svg` (Primary brand logo for dark backgrounds)
- **Horizontal Dark Logo**: `zencode-logo-horizontal-dark.svg` (For light backgrounds)
- **Horizontal White Logo**: `zencode-logo-horizontal-white.svg` (Monochrome white)
- **Horizontal Black Logo**: `zencode-logo-horizontal-black.svg` (Monochrome black)
- **Stacked Mint Logo**: `zencode-logo-stacked-mint.svg`
- **Stacked Dark Logo**: `zencode-logo-stacked-dark.svg`
- **Stacked White Logo**: `zencode-logo-stacked-white.svg`
- **Stacked Black Logo**: `zencode-logo-stacked-black.svg`
- **Symbol Mint Mark**: `zencode-symbol-mint.svg` (Official sovereign 'Z' sparkle icon `#42E6C3`)
- **Symbol Dark Mark**: `zencode-symbol-dark.svg`
- **Symbol White Mark**: `zencode-symbol-white.svg`
- **Symbol Black Mark**: `zencode-symbol-black.svg`
- **Favicon**: `favicon.svg`

### Raster Formats (High-Resolution PNG)
- `zencode-logo-horizontal-mint.png`
- `zencode-logo-horizontal-dark.png`
- `zencode-logo-horizontal-white.png`
- `zencode-logo-stacked-mint.png`
- `zencode-symbol-mint.png`
- `zencode-symbol-dark.png`
- `zencode-symbol-white.png`
- `zencode-app-icon-512.png`
- `zencode-app-icon-1024.png`
- Favicon suite: `favicon-16.png`, `favicon-32.png`, `favicon-48.png`, `favicon-96.png`, `favicon-192.png`, `favicon-512.png`, `apple-touch-icon.png`

---

## 2. INSILOS Autonomous Enterprise Platform Assets (`/assets_library/insilos/`)

### Vector Formats (SVG)
- **Horizontal Dark Canvas Logo**: `insilos_logo_dark.svg` (White typography with gold/orange silos `#070B14` high contrast)
- **Horizontal Light Canvas Logo**: `insilos_logo.svg` / `h-logo-light.svg` (Dark typography `#004455` for light backgrounds)
- **Brand Icon**: `insilos_brand_icon.svg` / `insilos-icon.svg` (Multi-tiered autonomous silo towers)
- **Brand Mark**: `insilos_mark.svg` & `insilos_mark_dark.svg`
- **Vertical Stacked Logo Light**: `v_logo_light.svg`
- **Vertical Stacked Logo Dark**: `v_logo_dark.svg`
- **Social Share Banner**: `social_share.svg`

### Raster Formats (High-Resolution PNG)
- `insilos_logo_dark.png`
- `v_logo_light.png`
- `v_logo_dark.png`
- `insilos-icon-192x192.png`
- `insilos-icon-512x512.png`
- `insilos-icon-ios.png`
- `social_share.png`

---

## 3. Enterprise Ecosystem Partners (`/assets_library/clients/`)
- `client_a_gray.png`: Tổng Công Ty Tân Cảng Sài Gòn (SNP)
- `client_b_gray.png`: Tập Đoàn Thép Hòa Phát Dung Quất
- `client_d_gray.png`: Cơ Khí Chế Tạo Máy V-LIFT

---

## 4. Odoo Media Library Integration (`ir.attachment`)
All 57 assets are synchronized into PostgreSQL `ir_attachment` with:
- `public = true`
- `type = 'url'`
- `res_model = 'ir.ui.view'`
- `url = /insilos_website/static/src/img/assets_library/...`

To re-index anytime across local and Kubernetes environments:
```bash
python3 tools/sync_logos_to_assets_library.py local
python3 tools/sync_logos_to_assets_library.py prod_pod
```
