project brief

# Timesheet Analysis Tool - Project Brief

## Goal

Build a local web app that helps HR/accounting convert physical worker time card photos and PDFs into a clean Excel timesheet workbook.

The app must run locally on a user's computer.

## Core problem

The company currently uses physical time cards. Workers stamp or write their start/end times on monthly time cards. HR/accounting currently checks photos manually and transfers the data into Excel.

This app should reduce manual work by using AI to extract the timesheet data, then asking HR to confirm uncertain fields before generating the final Excel file.

## Target user

HR/accounting staff. The user may be non-technical.

## Main workflow

1. HR opens the local web app.
2. HR selects the month and year for the timesheets.
3. HR confirms the worker list.
4. HR confirms or updates SOP codes and abbreviation meanings.
5. HR enters monthly notes or special cases.
6. HR uploads all timesheet images/PDFs.
7. The app extracts timesheet data using AI.
8. The app shows uncertain items for HR review.
9. HR confirms/corrects unclear names, times, codes, blank days, and split shifts.
10. The app exports a clean Excel workbook.

## Input files

Supported files:
- JPG
- JPEG
- PNG
- HEIC
- PDF

Filenames are random and must not be used to identify workers.

One worker may have:
- One image
- Two images
- Front/back images
- Half a time card in one image
- Multiple workers partially visible in one image
- PDF generated from Excel instead of a physical photo

## Time card layout

The physical time card layout is mostly standardized.

The top area contains:
- Worker name
- Month
- Card number

The card number at top right is important:
- "1" usually means first half of the month
- "2" usually means second half of the month

For card number "2", rows usually represent days 16 to 31.

The main table columns are:
- D
- IN 1
- OUT 1
- IN 2
- OUT 2
- IN 3
- OUT 3
- R

Each day usually has one start time and one end time, but rare cases may include split shifts, lunch in/out, or movement between shops.

## Date handling

HR selects the month and year at the start.

The app should create the correct number of days for that month.

If the time card shows card number "2", it should generally map rows to the second half of the month.

If date mapping is unclear, flag for HR review instead of guessing.

## Worker masterlist

The app should save worker data locally.

Each worker has:
- Name
- Worker type: Full-time or Part-time

Worker type is for reporting and validation context only. It does not change hours calculation in version 1.

## SOP codes

The app should save SOP/abbreviation codes locally.

Examples:
- AL = Annual Leave
- MC = Medical Certificate
- BL = Baby Leave
- OFF = Off Day
- OT = Overtime

HR can add or edit codes.

If the AI detects an unknown code, the app should ask HR what it means and offer to save it for future months.

## Monthly notes

Before upload, HR can enter notes for the month.

Examples:
- Serene is off for half the month.
- John may have split shop entries.
- Some cards may include lunch in/out.

AI should use this context when extracting and flagging issues.

## AI extraction behavior

Use an AI vision model for extraction.

The AI must extract:
- Worker name
- Month/card side if visible
- Day/date
- Start time
- End time
- Hours worked
- Notes/code
- Whether the entry requires HR review
- Reason for review

The AI must flag:
- Unclear worker name
- Unknown abbreviation
- Unclear time
- Cancelled or overwritten row
- Multiple time segments
- Lunch in/out or split shift
- Missing start/end time
- Strange working hours
- Blank days that may require explanation
- Any handwritten note that is not clear

The AI must not silently guess uncertain items.

## Hours calculation

For version 1:
- Hours worked = end time - start time
- No lunch deduction
- No overtime calculation
- No payroll calculation
- If time is unclear, flag for review

Hours should display as:
- 9h 35m

## Review workflow

Before Excel export, the app must show uncertain items to HR.

Examples:
- AI detected name "Kinn", suggested match "Kim". Confirm?
- AI found unknown code "BL". What does it mean?
- AI found many blank days. Should they be OFF, AL, blank, or something else?
- AI found possible split shift. Please confirm final start/end/notes.

HR corrections should be applied before export.

## Review image preview requirement

When the AI flags an issue for HR review, the app must show the relevant original uploaded timesheet image beside the issue.

The HR user should not need to manually search through uploaded photos to verify an issue.

Each review item should show:
- Worker name if known
- Suggested worker match if applicable
- Risk level: High, Medium, or Low
- Issue reason
- AI extracted value
- Date/day if known
- Original image preview
- HR correction/confirmation field

For version 1, the final Excel does not need to embed the original images. The Excel should include written attention notes and the Summary worksheet should indicate which workers require attention.

## Excel output

Generate one Excel workbook.

File name format:
Timesheet_Report_<Month>_<Year>.xlsx

Each worker gets one worksheet named after the worker.

Each worker worksheet has columns:
- Date
- Start Time
- End Time
- Hours Worked
- Notes

At the bottom of each worker worksheet:
- Total Hours Worked
- Notes Summary
- Attention / Review Items

Notes Summary example:
AL: 4
MC: 2
BL: 1
OFF: 6

Also create a final worksheet called Summary.

Summary worksheet columns:
- Worker
- Worker Type
- Total Hours
- Count of each note code
- Other Notes
- Requires Attention

## Formatting

Use simple Excel formatting:
- Header row bold
- Leave/note rows highlighted yellow
- Requires attention rows highlighted orange
- Unresolved rows highlighted red
- Auto-adjust column widths if practical

## Tech stack

Use:
- Python
- FastAPI
- Jinja2
- pandas
- openpyxl
- OpenAI API for AI vision extraction
- Local JSON files for worker/SOP storage

Do not use:
- React
- Database for version 1
- Login system
- Cloud hosting
- Complex frontend framework

## Code structure

Use this structure:

app.py
services/ai_extractor.py
services/excel_exporter.py
services/file_processor.py
services/config_store.py
templates/
static/
config/
uploads/
outputs/

Keep app.py focused on routes and page flow.

Do not put all logic into app.py.

## Local run command

The app should run with:

uvicorn app:app --reload

Then the user opens:

http://127.0.0.1:8000

## Handover goal

The final project should be easy to send to another person.

They should be able to:
1. Install Python
2. Add their OpenAI API key
3. Run pip install -r requirements.txt
4. Start the app locally
5. Use it in their browser
