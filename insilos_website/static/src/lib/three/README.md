# Sovereign Three.js Engine for Insilos Enterprise

## Overview
This directory contains the production-grade sovereign Three.js offline bundle for Insilos Enterprise Odoo 20 (`insilos_website`).

- **Version**: Three.js Revision 180 (`0.180.0`)
- **Included Controls**: `OrbitControls`
- **Bundle File**: `three.min.js` (703.9 KB minified IIFE)
- **Reference Module**: `OrbitControls.js`
- **Zero CDN Guarantee**: 100% self-contained, air-gapped, zero external network requests.
- **License**: MIT License (Ricardo Cabello / mrdoob and Three.js authors)

## Global Exposure
The bundle automatically exports:
- `window.THREE`
- `window.THREE.OrbitControls`
- `window.OrbitControls`

## Deterministic Build Command
Built locally using `npx esbuild 0.28.2`:
```bash
npx esbuild entry.js --bundle --minify --format=iife --global-name=InsilosThreeBundle --outfile=three.min.js
```
No external CDN links (`cdnjs`, `jsdelivr`, `unpkg`) are permitted.
