# Gemini CLI - Next Session TODO

This file outlines the remaining tasks to complete the user's request.

### Completed Modifications Summary:

1.  **Data Structure**: `IPersonConfig` in `src/types/storeType.ts` has been updated to use `phone` instead of `department`, `identity`, and `avatar`.
2.  **Excel Import Logic**:
    *   The import process in `src/views/Config/Person/PersonAll/useViewModel.ts` is now incremental.
    *   The web worker at `src/views/Config/Person/PersonAll/importExcel.worker.ts` correctly parses the new Excel structure (`ID`, `姓名`, `电话`).
3.  **Display Logic**:
    *   The main lottery 3D card display now shows a masked phone number.
    *   The personnel management table columns are updated.
4.  **i18n Keys**: All relevant locale files (`data.ts`, `table.ts`, `error.ts`) have been updated.
5.  **Single Person Form**: The `SinglePerson.vue` component has been updated to use a `phone` input.

### Remaining Tasks for Next Session:

1.  **Fix `addOnePerson` Reset Logic**:
    *   **File**: `src/views/Config/Person/PersonAll/useViewModel.ts`
    *   **Task**: In the `addOnePerson` function, the line `singlePersonData.value = {} as IBasePersonConfig` incorrectly resets the form data. It should be changed to `singlePersonData.value = { uid: '', name: '', phone: '' }` to correctly clear the form for the next entry.

2.  **Global Code Audit**:
    *   **Task**: Perform a project-wide search for the obsolete keys: `department`, `identity`, and `avatar`.
    *   **Goal**: Ensure no residual logic is relying on these old keys. Remove any remaining references if found.

3.  **Full Feature Validation**:
    *   **Task**: After completing the code changes, run the application and perform end-to-end testing.
    *   **Checklist**:
        *   Verify that the incremental Excel import works as expected (adds new users, skips existing ones).
        *   Confirm that phone numbers are correctly masked on the lottery 3D cards.
        *   Confirm that phone numbers are correctly masked in the personnel management table.
        *   Test the "Add Single Person" functionality to ensure it works with the new data structure.
        *   Ensure the application runs without any console errors related to the changes.
