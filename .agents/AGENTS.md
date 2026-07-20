# Repository Agent Rules

## HWPX Image Embedding Export Rule
- **Context**: The `python-hwpx` library requires a monkey-patch to map embedded images correctly when exporting documents in HWPX format.
- **Constraint**: Do not rewrite or modify `patched_add_image` to map `binaryItemIDRef` to numeric IDs (e.g., `"0"`) or attempt to inject `<binItem>` elements into `Contents/header.xml`. 
- **Required Behavior**:
  1. The `binaryItemIDRef` in `Contents/section0.xml` must map directly to the `<opf:item>` element's `id` attribute (e.g., `"BIN0001"`) inside `Contents/content.hpf` (the manifest).
  2. The corresponding `<opf:item>` element inside `Contents/content.hpf` must have the attribute `isEmbeded="1"`.
  3. Perform this mutation on the manifest element retrieved via `self._package._manifest_element()` and persist it using `self._package._persist_manifest()`.
- **References**: Refer to [hwp_export/hwpx_image_export_patch.md](file:///c:/Pro1/2026상반기/테이블명세표/hwp_export/hwpx_image_export_patch.md) for the detailed specification and code snippet of the patch.
