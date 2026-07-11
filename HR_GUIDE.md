# Timesheet Tool — HR User Guide

Welcome. This tool helps you review worker timesheets and export a payroll-ready Excel file each month.

You do not need to install anything. Just open the link in your browser.

---

## What you need

- The tool URL (given to you by your manager)
- Worker timesheet files: photos, PDFs, or small Excel files
- About 30–60 minutes per month depending on the number of workers

---

## Monthly workflow — step by step

### Step 1 — Open the tool and start a new month

1. Open the URL in your browser (Chrome or Safari recommended)
2. Select the month and year for the timesheets you are processing
3. Click **Start New Month**
4. If you already started this month before, click the month name under **Continue Existing Month** instead

---

### Step 2 — Confirm your worker list

You will see a list of workers. This list is used to help the AI match names on timesheets.

- Add any workers who are not on the list
- Remove workers who are no longer active
- Click **Save Workers** when done

---

### Step 3 — Confirm SOP codes

SOP codes are the abbreviations your workers write on their time cards (e.g. OFF, AL, MC).

- The tool comes with a few codes already set up
- You can add more here if needed
- Click **Save** when done

---

### Step 4 — Upload timesheets

Click **Upload Timesheets** and select the files.

**Accepted file types:**
- Photos (JPG, PNG, HEIC) — photos of physical time cards
- PDF files — scanned cards or printed documents
- Excel files — if some workers submit small Excel timesheets

You can upload multiple files at once. If you accidentally upload the same file twice, the tool will detect it and skip it.

Click **Upload** and wait for the files to be processed. This takes a few seconds per file.

---

### Step 5 — Run AI extraction

Click **Run AI Extraction** to have the AI read all the uploaded files and pull out the timesheet data.

This may take 1–3 minutes depending on how many workers you have. You will see a progress bar.

When it finishes, you will see the extracted rows in the review table.

---

### Step 6 — Run AI second-pass (recommended)

Before manually reviewing rows, click **Run AI Second-Pass on All Needs Review**.

This asks the AI to double-check the uncertain rows. Some rows may be automatically resolved (you will still be able to see what the AI changed in the Reviewed tab).

This takes about 30–60 seconds.

---

### Step 7 — Review the remaining rows

Click **Start Reviews** to go through each row that still needs attention.

For each row you will see:
- The worker name, date, and extracted times
- The reason it needs attention (e.g. unclear time, unknown code)
- The original timesheet image on the right (zoom in to check)

**What to do:**
- If the AI is correct — click **Confirm** or **Mark Reviewed**
- If the AI is wrong — correct the time or notes, then click **Save**
- If you are unsure — you can skip and come back later
- If you reviewed a row but change your mind — click **Reopen** to edit it again

---

### Step 8 — Add unknown SOP codes (if needed)

If the AI detected a code it does not recognise (e.g. a new abbreviation your workers use), you will see a notice at the top of the review page.

To add it:
1. Type the **short code** in the Code box — for example: `OT` or `MC`

   > **Important:** type a short code only (e.g. `OT`, not `OT – overtime worked on public holiday`). The code box accepts up to 20 characters.

2. Type the **meaning** in the Meaning box — for example: `Overtime` or `Medical Certificate`
3. Tick the box to apply it to all matching rows in this session
4. Click **Add to SOP Presets**

The code will be saved for future months too.

---

### Step 9 — Export Excel

When all rows show as Reviewed (or Clean), click **Export Excel**.

If there are still unresolved rows, the tool will warn you and ask you to confirm. You can still export — the unresolved rows will be visible in the Excel file so payroll can see them.

The Excel file downloads automatically. Open it to check:
- **Summary sheet** — all workers, total hours, leave counts, attention flags
- **Per-worker sheets** — daily breakdown for each worker

---

## Frequently asked questions

**What if I close the browser halfway through?**
All your saved work is kept. When you reopen the URL and select the same month, everything will be exactly where you left it. Only the current unsaved row (the one you were editing) might need to be re-done.

**What if an AI batch is running and I close the browser?**
Rows that were already processed are saved. When you reopen, run the second-pass again and it will pick up the remaining rows.

**What if the AI got a time wrong?**
Correct it in the review modal and click Save. Your correction is recorded in the audit trail.

**What if a worker submitted an Excel file and I get an error?**
Ask the worker to export their sheet as a PDF and resubmit. Excel support is coming in a future update.

**What if I exported but realised I made a mistake?**
Go back to the review page, find the row, click Reopen, correct it, save, and export again.

**The tool is loading slowly — is that normal?**
The AI steps (extraction and second-pass) take 1–3 minutes for a full batch. Page loads should be fast. If the page itself is slow, try refreshing.

---

## Who to contact

If something is not working or you have questions about the tool, contact your manager.

Do not share the URL with anyone outside the HR team.
