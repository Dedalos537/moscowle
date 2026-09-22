# User Model
The central entity of the system, acting as Patient, Therapist, or Admin.

## Key Attributes
- `role`: Determines permissions (`admin`, `supervisor`, `terapista`, `jugador`).
- `sede_id`: Links the user to a specific location.
- `assigned_therapist_id`: Links a patient to their therapist.

## Relationships
- **Many-to-Many**: Users can be linked to multiple therapists.
- **One-to-Many**: A therapist has many patients.

Links: [[Services.ToolsRegistry]], [[Models.Appointment]]
