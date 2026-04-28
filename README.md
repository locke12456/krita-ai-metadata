# Krita AI Metadata Export

**Version:** 0.20  
**License:** MIT

Krita AI Metadata Export is a Krita plugin for exporting generated artwork layers with structured metadata, PNG output, JSON sidecars, and optional batch manifests.

Version 0.20 adds a Krita 5 / Krita 6 compatible workflow and a standalone manual metadata export mode. Krita AI Diffusion can still be used for AI-generated prompt metadata, but the core grouping, preview, PNG export, JSON sidecar, and manifest workflow can also run without Krita AI Diffusion installed.

![Krita AI Metadata Export overview](images/overview-krita-ai-export.png)

## Highlights in 0.20

- Krita 5 / Krita 6 compatible plugin registration and docker support
- Manual metadata export mode that works without Krita AI Diffusion
- PNG export and JSON sidecar export from selected layers or export groups
- Metadata export groups with readable sequential keys such as `0001-chibi`
- Auto map workflow for selected generated layers
- Persistent mapping stored inside the `.kra` document
- Preview panel for resolved and unresolved export targets
- Batch `manifest.json` support
- Safer handling for moved layers, deleted old groups, and re-auto-mapping
- Fixes stale group records that could reuse an old seed after layer reorganization
- Manual mode no longer shows irrelevant Krita AI unavailable warnings

## What this plugin does

The plugin helps keep each exported image connected to its intended metadata after a Krita document has been edited, grouped, renamed, or prepared for publishing.

It is useful when you want to:

- Export selected generated layers as PNG files
- Keep matching JSON metadata next to every PNG
- Use stable filenames for batches
- Preserve generation parameters when Krita AI Diffusion metadata is available
- Export manually organized artwork even when Krita AI Diffusion is unavailable
- Verify output before writing files

## Requirements

### Required

- Krita with Python plugin support
- A writable output folder

### Optional

- Krita AI Diffusion

Krita AI Diffusion is only required for AI-derived prompt and generation metadata lookup. Manual grouping and basic PNG / JSON export remain available without it.

## Installation

1. Download or clone this repository.
2. Copy the plugin folder into Krita's Python plugin directory.
3. Restart Krita.
4. Enable the plugin from Krita's Python Plugin Manager.
5. Open the docker from Krita's docker menu.

## Basic Workflow

![Layout](images/layout.png)

### 1. Open the Metadata Export docker

The docker provides:

- Runtime mode label
- Current document state
- Layer selection controls
- Layer list and metadata sync state
- Manual group label input
- Output folder selection
- Export options
- Preview log
- Export result log

### 2. Choose AI-enabled mode or manual mode

When Krita AI Diffusion metadata is available, the plugin can resolve prompt metadata from stored snapshots or job history.

![AI metadata overview](images/overview-krita-ai-export.png)

When Krita AI Diffusion is unavailable, the plugin uses manual metadata export mode.

![Krita 6 manual mode export](images/overview-krita-6-manual-mode-export.png)

Manual mode keeps the export workflow available:

- Select layers or groups
- Create export groups
- Preview export targets
- Export PNG files
- Write JSON sidecars
- Write a manifest

Manual mode does not invent missing prompt, seed, sampler, or model data.

### 3. Filter and select layers

Use the layer list filters to narrow the visible targets:

- Synced / inherited
- Unsynced
- Visible
- Hidden
- Groups
- Layers

You can import the current Krita selection into the plugin selection and then choose which layers to map or export.

### 4. Enter a group label

Before mapping selected layers, enter a readable group label.

Example:

~~~text
chibi
~~~

The plugin creates export-friendly names:

~~~text
[0001] - chibi
0001-chibi.png
0001-chibi.json
~~~

For multiple selected layers, the plugin creates sequential export targets:

~~~text
0001-chibi.png
0002-chibi.png
0003-chibi.png
0004-chibi.png
~~~

The seed is stored in metadata when available, but it is not used as the group name or filename.

### 5. Auto map selected layers

Click **Auto map selected layers**.

![Auto map selected layers](images/auto-map.png)

Auto mapping creates metadata export groups and stores the mapping in the `.kra` document.

This allows metadata to be resolved later from the document snapshot, even if the layer has been reorganized.

Version 0.20 also fixes a stale-record case where moving a layer out, deleting the old group, and running auto map again could reuse the old group's seed.

### 6. Choose the output folder

If the document is saved, the output folder can follow the `.kra` location.

If the document is unsaved, the plugin can use a home export folder such as:

~~~text
~/krita_ai_metadata_export
~~~

You can also choose a folder manually with **Browse**.

### 7. Configure export options

Common options include:

- Export mode
- Overwrite existing files
- Allow unresolved export
- Write manifest
- Include invisible selected targets

PNG is the primary export format in this version.

### 8. Preview export

Click **Preview export** before writing files.

![Export preview](images/export-preview.png)

The preview helps verify:

- Target count
- Output paths
- Resolved / unresolved metadata state
- Warnings
- Whether the output key is correct

Example:

~~~text
Preview targets: 2; warnings: 0
- 0005-test: [Generated] ... (resolved) -> output/0005-test.png
- 0006-test: [Generated] ... (resolved) -> output/0006-test.png
~~~

### 9. Export PNG metadata

Click **Export selected PNG metadata**.

![Export result 1](images/export-result1.png)

For each exported target, the plugin writes:

~~~text
{name}.png
{name}.json
~~~

When manifest output is enabled, it also writes:

~~~text
manifest.json
~~~

![Export result 2](images/export-result2.png)

## Output Files

### PNG

The PNG is the exported visual image.

When metadata is available, the PNG can include embedded generation parameters.

### JSON sidecar

The JSON sidecar stores the structured export payload, including:

- Export key
- Group name
- Group ID
- Layer IDs
- Manual label
- Sync index
- Image index
- Seed when available
- Params snapshot when available
- A1111 parameters when available
- Runtime mode fields
- Warning list
- Child layer summary for group targets

### Manifest

The optional `manifest.json` provides a batch-level index of exported files.

## Metadata and Manual Mode

In AI-enabled mode, the plugin can use stored metadata snapshots and Krita AI Diffusion integration to write generation metadata.

In manual mode, prompt search and AI metadata lookup are disabled. Export still works, but the plugin will not fabricate missing prompt or seed data.

This keeps the output honest:

- Available metadata is preserved
- Missing metadata stays missing
- Manual exports remain usable
- PNG / JSON / manifest files can still be produced

## Civitai Create Post Verification

![Civitai create post](images/civitai-post.png)

Exported PNG files can be uploaded to Civitai's create post screen.

When generation metadata is available, Civitai can read the embedded PNG parameters and show prompt text, negative prompt, preview image, and generation settings such as seed, steps, sampler, and guidance.

This is useful for checking that the exported PNG still carries metadata in a format external tools can inspect.

## Recommended Use

- Use **Preview export** before exporting.
- Save the `.kra` document after auto mapping so metadata mapping persists.
- Use readable group labels for filenames.
- Use **Write manifest** for batch exports.
- Use **Allow unresolved export** only when exporting without complete metadata is intentional.

## License

This project is licensed under the MIT License.

## Links

- Krita: https://krita.org/
- Krita GitHub: https://github.com/KDE/krita
- Krita AI Diffusion: https://github.com/Acly/krita-ai-diffusion