# Data Model Notes

## Organizational Model

- Single company
- Multiple departments
- Project belongs to department
- Backend user is scoped by department (except super admin)

## Identity Model

- `customer.phone` is global unique and acts as natural-person id
- No separate participant user account is created

## Group Model

- No dedicated group field
- A project's member list is the draw scope (project list equals group)

## Draw State Transition

- `DrawBatch.status`: `PENDING -> CONFIRMED` or `PENDING -> VOID`
- `DrawWinner.status`: `PENDING -> CONFIRMED` or `PENDING -> VOID`

## Data Mutation Guarantees

- Preview draw does not consume prize quota permanently until confirmed
- Confirm draw updates winner status and increments `prize.used_count` atomically
- Void draw keeps records with reason for audit, without consuming quota

## Cross-Project Interaction

`exclusion_rule` supports:
- source project + optional source prize
- target project + optional target prize
- mode: exclude source winners from target candidate pool

