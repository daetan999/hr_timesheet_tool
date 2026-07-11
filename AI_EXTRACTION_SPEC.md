ai extraction spec

# AI Extraction Spec

## Purpose

This file tells the AI how to read the company's physical time cards.

## Observed sample layout

The sample time cards show:
- Worker name handwritten at the top
- Month handwritten near the top
- A card number at top right
- Main table with days and in/out columns
- Some stamped times
- Some handwritten corrections
- Some red markings
- Some notes such as OFF, Leave, OT, and Chinese handwritten text

## Important layout rules

The top-right card number matters:
- Card "1" usually means first half of month
- Card "2" usually means second half of month

In the provided examples, card "2" shows days 16 to 31.

The columns are:
- D = day
- IN 1
- OUT 1
- IN 2
- OUT 2
- IN 3
- OUT 3
- R

The AI should read the rows from top to bottom.

## Extraction priorities

For each visible worker/card section, extract:
1. Worker name
2. Month if visible
3. Card number if visible
4. Daily rows
5. Start time
6. End time
7. Notes/codes
8. Review flags

## Conservative rules

If the AI is not sure, it must flag for review.

Do not guess:
- Worker names
- Handwritten codes
- Crossed-out times
- Red handwritten notes
- Chinese handwritten notes
- Split shifts
- Lunch in/out cases

## Review flag reasons

Use these review reasons:
- unclear_worker_name
- unknown_code
- unclear_time
- cancelled_or_overwritten
- multiple_time_segments
- possible_split_shift
- blank_day
- handwritten_note_unclear
- date_mapping_unclear
- strange_hours

## Review item image linking

Each AI extraction result should keep a reference to the uploaded file or image page that produced the issue.

Each issue should include:
- source_file_id or source_image_path
- worker name if known
- day/date if known
- issue type
- risk level: high, medium, or low
- extracted value
- suggested correction if any
- reason HR needs to review it

The app should use this source reference to display the original image on the review page.

## Output format

The AI should return structured JSON only.

Each extracted card should include:
- detected_worker_name
- suggested_worker_match
- worker_name_confidence
- card_number
- month_seen
- entries
- issues

Each entry should include:
- day
- date
- start_time
- end_time
- hours_worked
- notes
- requires_review
- review_reason
