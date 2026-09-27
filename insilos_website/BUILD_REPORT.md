# Build Report — 19.0.2.0.0

## Scope

- 22 public page variants/routes.
- 6 solution detail pages.
- 4 industry detail pages.
- 3 resource articles.
- QWeb server-rendered content.
- 2 Owl public components.
- Demo request model, public form, backend workflow and email queue.
- Responsive Pexels media, local SVG product/architecture graphics.

## Static validation passed

- All XML files are well-formed.
- External XML IDs are unique.
- Manifest data/assets/images exist.
- Python files compile.
- JavaScript files pass `node --check`.
- WebP files can be opened and verified.
- Local media references resolve.
- No Pexels image hotlinks or C3 media links are present.
- SCSS delimiters are balanced.
- Solution → industry references are valid.

## Runtime validation required

The build environment does not include an Insilos 19 server. Before production, run:

```bash
./insilos-bin -d TEST_DATABASE -i insilos_website --test-enable --stop-after-init
```

Then execute the browser and go-live checklist in `QA_CHECKLIST.md`.
