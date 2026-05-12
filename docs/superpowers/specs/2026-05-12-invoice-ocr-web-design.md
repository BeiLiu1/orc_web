# Invoice OCR Web System Design

## 1. Background

The current project is a local Python script that processes images from a `data/` folder and writes Excel files to `output/`. It is useful as a prototype, but it does not match the real finance workflow:

- Finance users work through a browser.
- Users upload invoice images marked by upstream staff with colored boxes.
- Areas with the same or visually similar box color belong to the same calculation group.
- Users need to review OCR details, manually correct amounts or taxes, and recalculate results.
- Users need history records and Excel export.
- Deployment should be simple on a public server.

This design replaces the script-first workflow with a small front-end/back-end web system deployed by Docker Compose.

## 2. First Version Scope

Included:

- Image upload only: `png`, `jpg`, `jpeg`.
- One or multiple image uploads per recognition task.
- Automatic colored-box detection.
- Dynamic color grouping, without hardcoded red/yellow/blue business meaning.
- OCR extraction for each detected colored-box region.
- Grouped result display in the browser.
- Manual editing of recognized amount and tax items.
- Manual addition and deletion of detail rows within a color group.
- Real-time recalculation after edits.
- History records stored in SQLite.
- Excel export with summary and detailed calculation sheets.
- Docker Compose deployment.

Excluded from first version:

- PDF upload and automatic page splitting.
- Login and complex permission management.
- Manual drawing or adjustment of boxes on the image.
- Filling results into an existing finance Excel template.
- Long-term original file storage.
- Multi-tenant or enterprise audit workflow.

## 3. Recommended Architecture

Use a front-end/back-end split with Docker Compose:

- `frontend`: Vue 3 + Vite application, served by Nginx after build.
- `backend`: Python FastAPI application.
- `ocr runtime`: Tesseract, OpenCV, and Python OCR dependencies installed inside the backend image.
- `database`: SQLite file mounted under `storage/`.
- `file storage`: local mounted folders for temporary uploads and generated exports.

Runtime request flow:

```text
Browser
  -> Nginx frontend
  -> /api reverse proxy
  -> FastAPI backend
  -> OCR pipeline / SQLite / export files
```

The server only needs Docker and Docker Compose. No manual Python, Node, OpenCV, or Tesseract installation should be required on the host.

## 4. Deployment Shape

Target structure:

```text
backend/
  app/
  Dockerfile
  requirements.txt
frontend/
  src/
  Dockerfile
  nginx.conf
deploy/
storage/
  db/
  uploads/
  exports/
docker-compose.yml
.env.example
```

Expected start command:

```bash
docker compose up -d --build
```

Important environment variables:

- `APP_PORT`: exposed web port.
- `STORAGE_DIR`: container storage root.
- `UPLOAD_RETENTION_DAYS`: uploaded image retention period.
- `EXPORT_RETENTION_DAYS`: generated Excel retention period.
- `MAX_UPLOAD_MB`: upload size limit.
- `ACCESS_TOKEN` or `BASIC_AUTH_PASSWORD`: optional simple access protection.

Because this is exposed on a public server, first version should at least support a simple access token or Nginx Basic Auth. It is not a full account system, but it avoids an unprotected public OCR endpoint.

## 5. Main User Flow

1. User opens the web page.
2. User uploads one or more invoice images.
3. Backend creates a recognition job and temporarily stores the uploaded images.
4. Backend detects colored boxes in each image.
5. Backend groups boxes by similar border color.
6. Backend OCRs each detected box region.
7. Backend parses recognized amount and tax values.
8. Frontend displays image preview, detected groups, details, and formulas.
9. User edits wrong or missing amount/tax values.
10. Frontend recalculates immediately and saves the corrected result.
11. User exports Excel.
12. User can reopen previous jobs from history.

## 6. Frontend Design

Pages:

- `Upload`: upload images and create a recognition task.
- `Job Detail`: review recognition result, edit details, recalculate, export.
- `History`: list previous jobs and open details.

Job detail layout:

- Left side: image preview.
- Right side: color group panels.
- Each group panel shows:
  - color swatch.
  - group name, such as `颜色组 1`.
  - calculated amount total.
  - calculated tax total.
  - formula text, such as `6.41 + 19.00 + 5.08`.
  - editable detail rows.

Editable detail row fields:

- source image/page name.
- raw OCR text.
- amount.
- tax.
- manual row flag.
- corrected flag.
- optional bounding-box coordinates for troubleshooting.

The first version does not require manual image annotation. Users can edit recognized detail rows, add missing detail rows to an existing color group, or delete wrong detail rows. Manually added rows do not have bounding-box coordinates.

## 7. Backend API

Suggested endpoints:

```text
POST   /api/jobs/upload
GET    /api/jobs
GET    /api/jobs/{job_id}
PUT    /api/jobs/{job_id}/items
POST   /api/jobs/{job_id}/export
GET    /api/exports/{export_id}/download
DELETE /api/jobs/{job_id}
```

Endpoint behavior:

- `POST /api/jobs/upload`: accepts image files, runs recognition, stores result.
- `GET /api/jobs`: returns history list.
- `GET /api/jobs/{job_id}`: returns full editable result.
- `PUT /api/jobs/{job_id}/items`: saves user-corrected details and recalculates group totals.
- `POST /api/jobs/{job_id}/export`: generates an Excel file from the latest saved result.
- `GET /api/exports/{export_id}/download`: downloads generated Excel.
- `DELETE /api/jobs/{job_id}`: deletes history result and any temporary files still present.

## 8. Data Model

Use SQLite for first version.

`jobs`:

- `id`
- `original_filenames`
- `status`
- `created_at`
- `updated_at`
- `amount_total`
- `tax_total`
- `error_message`

`image_files`:

- `id`
- `job_id`
- `original_name`
- `stored_path`
- `width`
- `height`
- `created_at`

`groups`:

- `id`
- `job_id`
- `group_index`
- `display_name`
- `color_hex`
- `amount_total`
- `tax_total`
- `formula_amount`
- `formula_tax`

`items`:

- `id`
- `job_id`
- `group_id`
- `image_file_id`
- `raw_text`
- `amount`
- `tax`
- `bbox_x`
- `bbox_y`
- `bbox_w`
- `bbox_h`
- `ocr_confidence`
- `is_manual`
- `is_corrected`

`exports`:

- `id`
- `job_id`
- `filename`
- `stored_path`
- `created_at`

## 9. OCR And Color Detection Pipeline

The first version should not reuse the current hardcoded `red/yellow/blue` result model. Instead:

1. Load image with OpenCV.
2. Detect colored rectangular outlines.
3. Merge fragmented contour segments into stable boxes.
4. Filter boxes by size, aspect ratio, and border-color density.
5. Extract the dominant border color for every box.
6. Cluster colors by distance in HSV or LAB color space.
7. Assign each box to a dynamic group.
8. Crop each box interior.
9. Run OCR using Tesseract.
10. Parse amount and tax pairs from OCR text.
11. Store raw text and parsed values together.

Parsing rules:

- Keep the current idea of recognizing decimal numbers.
- Detect VAT/tax lines where possible.
- Treat the rightmost decimal value in a charge line as amount.
- Treat the rightmost decimal value in a VAT/tax line as tax.
- Preserve raw OCR text even when parsing fails.
- If parsing fails, create an empty editable item instead of silently dropping the box.

The existing modules can inform the implementation, but the core result model and grouping logic should be rewritten.

## 10. Calculation Rules

For each color group:

```text
amount_total = sum(item.amount)
tax_total = sum(item.tax)
```

Overall totals:

```text
all_amount_total = sum(group.amount_total)
all_tax_total = sum(group.tax_total)
```

All values should be stored and displayed with two decimal places. Recalculation should happen both in the frontend for responsiveness and in the backend for saved/exported correctness.

Manual edits:

- Editing amount or tax marks the row as corrected.
- Adding a row marks it as manual.
- Deleting a row removes it from group and export calculations.
- Export always uses the latest saved result.

## 11. Excel Export

The generated Excel file should include two sheets.

`汇总` sheet:

- 颜色组
- 颜色值
- 含税金额合计
- 税费合计
- 含税金额计算式
- 税费计算式

`明细` sheet:

- 颜色组
- 序号
- 图片名
- 原始识别文本
- 含税金额
- 税费
- 是否人工新增
- 是否人工修改
- 框坐标

This export is intentionally not tied to a specific finance template in the first version.

## 12. Error Handling

Upload errors:

- unsupported file type.
- file too large.
- unreadable image.

Recognition errors:

- no colored box detected.
- OCR failed for one or more boxes.
- parser could not extract numbers.

The UI should show partial results whenever possible. A failed box or parsing failure should become an editable row instead of blocking the whole job.

## 13. Cleanup Policy

History result data remains in SQLite until the user deletes it.

Temporary files:

- uploaded images can be deleted after the configured retention period.
- generated Excel files can be deleted after the configured retention period.
- deleting a job should also delete related temporary files if they still exist.

If a historical job's original image has been cleaned, the result details should still be viewable, but image preview may show `文件已清理`.

## 14. Testing Strategy

Backend:

- parser unit tests.
- color clustering tests with sampled colors.
- calculation tests.
- API tests for upload, edit, history, and export.

OCR pipeline:

- fixture images for known invoice examples.
- expected group count and expected parsed amount/tax values.
- tolerant assertions for OCR where exact raw text may vary.

Frontend:

- calculation behavior tests.
- edit/save/export flow tests.
- visual sanity checks for image preview and group panels.

Deployment:

- `docker compose up -d --build` starts both services.
- frontend can reach backend through `/api`.
- export download works from a fresh container start with mounted storage.

## 15. Implementation Order

1. Restructure repository into `backend/` and `frontend/`.
2. Implement backend data models and SQLite persistence.
3. Implement image upload and job creation.
4. Rewrite OCR/color grouping pipeline.
5. Implement result editing and recalculation APIs.
6. Implement Excel export.
7. Build frontend upload, history, and job detail pages.
8. Add Dockerfiles and `docker-compose.yml`.
9. Add deployment documentation.
10. Validate with existing sample images and one manually marked invoice image.

## 16. Open Follow-up Items

These are explicitly deferred, not blockers for the first version:

- PDF upload and page splitting.
- Manual box drawing or correction.
- Mapping color groups into a fixed finance Excel template.
- User accounts and role-based permissions.
- Batch queue for large OCR workloads.
