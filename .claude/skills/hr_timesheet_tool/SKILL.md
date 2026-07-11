```markdown
# hr_timesheet_tool Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill covers the development patterns and conventions used in the `hr_timesheet_tool` TypeScript repository. The repository does not use a specific framework, focusing on plain TypeScript for building and maintaining a timesheet management tool. You'll learn about file naming, import/export styles, commit message conventions, and testing patterns to ensure consistency and maintainability.

## Coding Conventions

### File Naming
- Use **camelCase** for all file names.
  - Example: `timeEntryService.ts`, `userController.ts`

### Import Style
- Use **relative imports** for referencing modules within the codebase.
  - Example:
    ```typescript
    import { calculateHours } from './utils';
    ```

### Export Style
- Use **named exports** for all modules.
  - Example:
    ```typescript
    // In timeEntryService.ts
    export function submitTimesheet(data: TimesheetData) { ... }
    ```

### Commit Messages
- Follow the **Conventional Commits** standard.
- Use prefixes like `docs` for documentation changes.
  - Example:
    ```
    docs: update README with new setup instructions
    ```

## Workflows

### Documentation Update
**Trigger:** When updating or adding documentation files.
**Command:** `/update-docs`

1. Make your documentation changes (e.g., edit `README.md` or add new docs).
2. Stage and commit your changes using the `docs:` prefix in your commit message.
   - Example: `docs: add API usage section to README`
3. Push your changes to the repository.

## Testing Patterns

- Test files use the pattern `*.test.*` (e.g., `timeEntryService.test.ts`).
- The testing framework is not specified; follow the existing test file structure.
- Example test file:
  ```typescript
  import { calculateHours } from './utils';

  describe('calculateHours', () => {
    it('should return correct total hours', () => {
      expect(calculateHours([8, 8, 8])).toBe(24);
    });
  });
  ```

## Commands
| Command       | Purpose                                   |
|---------------|-------------------------------------------|
| /update-docs  | Start the documentation update workflow   |
```
