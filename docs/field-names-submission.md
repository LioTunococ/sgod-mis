# Submission Model Fields

## Foreign Keys
- **school** – which school submitted this
- **form_template** – which form this is for
- **period** – which period (e.g., 2025-Q1)

## Lifecycle Fields
- **status** (choices: draft, submitted, returned, noted)
- **submitted_at**, **submitted_by**
- **returned_at**, **returned_by**, **returned_remarks**
- **noted_at**, **noted_by**, **noted_remarks**

## Payload Fields
- **data** (JSON) – answers keyed by field name
- **attachments** (ManyToMany or separate table)

## Metadata
- **created_at**, **updated_at**
- **last_modified_by**
