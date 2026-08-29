# DFU v2 deployment

## Components

- Patient portal: `/mobile.html`
- Doctor portal: `/doctor.html`
- API: FastAPI in `backend/main.py`
- Production database: PostgreSQL 16
- ORM and migrations: SQLAlchemy 2 + Alembic
- Images and optional videos: protected server directory `backend/uploads/`; PostgreSQL stores metadata, ownership and archive relationships

## Local development

1. Copy `.env.example` to `.env` and replace every placeholder secret.
2. Start PostgreSQL:

   ```powershell
   docker compose --env-file .env up -d postgres
   ```

3. Create a virtual environment and install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r backend\requirements.txt
   ```

4. Load environment variables and run the initial migration:

   ```powershell
   alembic upgrade head
   python backend\main.py
   ```

For temporary local interface testing only, omitting `DATABASE_URL` uses
`backend/dfu_v2.db`. Production must set a PostgreSQL `DATABASE_URL`.

## Doctor invitation

The first startup seeds one invitation using `DFU_INITIAL_DOCTOR_INVITE`.
The current requested temporary value is `ritanai`. The database stores a
bcrypt hash, never the plaintext invitation. Change or disable it after initial
doctor onboarding.

## Server staging rollout

1. Keep `/home/ubuntu/dfu` running on port 8003.
2. Upload this version to `/home/ubuntu/dfu-v2`.
3. Link the existing model rather than copying it:

   ```bash
   ln -s /home/ubuntu/dfu/best_model.pth /home/ubuntu/dfu-v2/best_model.pth
   ```

4. Create a new `.env` on the server and start PostgreSQL on localhost only.
5. Run `alembic upgrade head` from `/home/ubuntu/dfu-v2`.
6. Start v2 on `127.0.0.1:8004` with `DFU_PORT=8004`.
7. Add an Nginx staging route such as `/dfu-test/` and complete acceptance testing.
8. Back up PostgreSQL and the old source before switching production traffic.

## Required acceptance tests

- New patient registration opens profile onboarding.
- Existing patient skips onboarding and can edit the profile from the user icon.
- Doctor registration rejects an invalid invitation.
- Doctor workflow separates new-patient and existing-patient registration.
- New patients receive a unique `RT-P-...` patient code and every visit receives a unique `RT-E-...` encounter code.
- Existing-patient registration uses an exact 11-digit mobile number and never matches by age or sex.
- Phone, admission ID, age, sex and diabetes grade are required at final submission; name, residence and dietary habits are optional.
- Patient self-service onboarding uses the same phone/age/sex/diabetes-grade rules as the doctor workflow.
- Five confirmed photos are required. Both 15-second videos are optional and a zero-video encounter can be archived.
- Final submission shows a confirmation dialog and the completion screen identifies the submitting doctor.
- The doctor workbench lists draft and archived encounters and supports exact patient/admission/encounter lookup.
- A doctor-created result appears in the patient's encounter history.
- Doctors only see dashboard records they created.
- Anonymous successful analysis does not retain an image.
- Deleting a patient record removes both database metadata and the stored image.
- PostgreSQL backup and restore are tested before production cutover.

## Encounter migration

Migration `20260715_0003` adds stable patient codes, admission encounters and optional-video metadata. Existing analysis rows are preserved and each one is linked to a separate legacy encounter; legacy rows are not merged by demographic similarity.

Migration `20260715_0004` adds the unique patient mobile number, aligned patient profile fields and an encounter phone snapshot. Existing profiles are preserved and are prompted to complete the newly required fields on their next patient-side visit.
