# 0.4.6 portable package smoke

Run against the **built/extracted package**, not repository source scripts. The two approved revisions are nested beside the existing case `inputs` folder. The revision file allowlist is `portable-revision-files.json`; evaluation and archived development records must stay out of the plugin. The source-bound helpers are public in EasyViz 0.4.5, while these curated case assets enter 0.4.6.

Example invocations after extracting a 0.4.6 package and copying both case folders to a writable project:

```sh
python /path/to/project/vabistsevits-forest/revision-v0.4.6/plot.py --runtime /path/to/extracted/easyviz/skills/easyviz/scripts --out /path/to/project/forest-attempt-01
python /path/to/project/massier-integration-radar/revision-v0.4.6/plot.py --runtime /path/to/extracted/easyviz/skills/easyviz/scripts --out /path/to/project/radar-attempt-01
```

On a machine without Arial, adopt an installed family explicitly; this is a real specification change, recorded before drawing:

```sh
python /path/to/project/vabistsevits-forest/revision-v0.4.6/plot.py --runtime /path/to/extracted/easyviz/skills/easyviz/scripts --font "DejaVu Sans" --out /path/to/project/forest-portable-font
python /path/to/project/massier-integration-radar/revision-v0.4.6/plot.py --runtime /path/to/extracted/easyviz/skills/easyviz/scripts --font "DejaVu Sans" --out /path/to/project/radar-portable-font
```

Use a fresh attempt folder. Explicit `--overwrite` archives an existing attempt before new capture; it does not mint a receipt for old exports. Confirm `qa.json` has `status: pass`, `valid_outputs: true`, all real checks passed and `handoff.json.consumption.kind: captured-bytes-before-export`. The data/spec/script and all helper source versions must be current when opening the workbench. Font override outputs must preserve `supplied-spec.json`, consume their own `adopted-spec.json` and declare the original specification as an auxiliary input.

For independent source/PDF/SVG verification, place fresh outputs at the copied cases' `revision-v0.4.6/output` locations, then call the repository audit externally (do not ship the audit/evals folder in the plugin):

```sh
python /path/to/repository/evals/development-v0.4.6/reproduce-design/verify_revisions.py --forest-case /path/to/copied/vabistsevits-forest --radar-case /path/to/copied/massier-integration-radar --expected-font "DejaVu Sans" --out /path/to/project/package-reproduce-verification.json
```

This reader checks 48 forest estimates, 96 CI endpoints, supplied fill states, all 25 radar vertices, five closed traces, three zeros, actual embedded 8 pt fonts and physical full-canvas exports without importing either plotting script. Use `--expected-font Arial` for the default. Visual inspection remains separate; technical success is not an aesthetic or inference score.
