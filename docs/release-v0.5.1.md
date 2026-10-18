EasyViz 0.5.1 adds portable figure projects and a standalone workbench for reviewing figures with the original Agent.

### Editable figure projects

- **Both tracks:** use SVG as the default graphic export, with PDF, PNG and TIFF available on request at the adopted physical dimensions. Keep plotting code, settings, source provenance and separate captions with the result.
- **Editable projects:** a single `.ev` project bundles the current mapped SVG, code/settings and declared inputs. Imports validate the project before opening it, without executing its code.

### Standalone workbench and Agent editing

Open the project library, import `.ev` files and choose a figure without starting from a selected attempt. Add numbered comments, rename figures, compare attempts, and accept or restore reviewed versions. The compact inspector gives each annotation its own plain-text instruction.

The normal loop is **Save drafts → ask the original Agent chat to apply the comments → compare the fresh result**. Optional MCP submission sends edits to the connected original Agent while it is active and waiting. The page shows progress, cancellation and individual outcomes; submitting does not start an idle chat.

### Request handling and export checks

- Repair cancelled submission waits, duplicate batch completion and unfinished jobs that could block later edits.
- Preserve adopted export formats, figure names and request ownership across fresh attempts and restoration. Improve open-bar selection and annotation badge placement.
- Exclude temporary request locks and local service state from portable packages.
- **850 tests passed**, and extracted-package redraws and workbench interactions were checked. SVG selection retains genuine mapped identities; grouped collections and raster layers keep their existing granularity.

[Install or update](https://github.com/idealstarry/EasyViz/blob/main/INSTALL.md) · [Changelog](https://github.com/idealstarry/EasyViz/blob/main/CHANGELOG.md) · [QA record](https://github.com/idealstarry/EasyViz/blob/v0.5.1/evals/release-qa/v0.5.1/README.md)

Give your local Agent the repository link and ask it to follow `INSTALL.md`, or use the attached portable plugin ZIP.
