AXIOM COMMERCIAL APPRAISAL — PLATFORM
======================================
One folder. One script. All your assignment documents.


FOLDER STRUCTURE
----------------
axiom_platform/
  axiom.py          ← the one script you run
  fill_engine.py    ← document fill engine (don't modify)
  config.json       ← template registry (edit to add new templates)
  README.txt        ← this file

  templates/        ← READ-ONLY source files, never touch these
    engagement_letter_template.docx
    doc_request_template.docx
    invoice_template.docx
    appraisal_template_styled.docx
    workbook.xlsx

  assignments/      ← auto-created, one subfolder per assignment
    DEMO-001_Northstar_Example_Holdings/
      workbook.xlsx           ← your calc workbook for this job
      2026-001_variables.json ← exported from Intake tab
      outputs/
        2026-001_engagement_letter.docx
        2026-001_doc_request.docx
        2026-001_appraisal_report.docx
        2026-001_invoice.docx


REQUIREMENTS
------------
Python 3.9+  (already installed)
python-docx  → pip install python-docx
openpyxl     → pip install openpyxl


COMMANDS
--------
Open a terminal, navigate to the axiom_platform folder, then:

  python axiom.py new DEMO-001 "Northstar Example Holdings"
      Creates the assignment folder and copies the workbook in.

  python axiom.py engage 2026-001
      Generates engagement letter + document request + invoice.
      Run this after filling out the Intake tab and exporting JSON.

  python axiom.py deliver 2026-001
      Generates a final appraisal report only when validation passes.
      Run this after all calc tabs are complete.

  python axiom.py deliver 2026-001 --draft
      Generates an explicitly incomplete DRAFT report without changing
      the assignment's delivery stage.

  python axiom.py validate 2026-001
      Checks delivery readiness without changing assignment files or state.

  python axiom.py contract
      Checks workbook and template keys against the versioned field registry.

  python axiom.py list
      Shows all assignments and their current stage.

  python axiom.py status 2026-001
      Shows details for one assignment.


WORKFLOW
--------
1. New engagement call comes in
   → python axiom.py new 2026-001 "Client Name"

2. Open assignments/2026-001_.../workbook.xlsx
   → Fill out the Intake tab
   → Click Export JSON button

3. Send engagement documents
   → python axiom.py engage 2026-001
   → Outputs appear in assignments/2026-001_.../outputs/
   → Review before manually sending engagement_letter.docx,
     doc_request.docx, and invoice.docx

4. Do the appraisal work
   → Fill calc tabs in workbook.xlsx as you go
   → Excel auto-computes the Outputs tab

5. Validate
   → python axiom.py validate 2026-001
   → Resolve all required fields and document blocks

6. Deliver
   → python axiom.py deliver 2026-001
   → Review the generated appraisal_report.docx before delivery


REPORT MEDIA
------------

New assignments include a standard assets folder. Add report images using
these names before final delivery (JPG and PNG are supported):

  assets/maps/regional.jpg
  assets/maps/aerial.jpg
  assets/maps/parcel.jpg
  assets/maps/sca-sale-location.jpg
  assets/maps/land-sale-location.jpg
  assets/maps/lease-comp-location.jpg
  assets/building-sketch.jpg

Place multiple subject and lease-comparable photos in:

  assets/photos/subject/
  assets/photos/lease-comps/

Run `python axiom.py validate <file_no>` to see exactly which required media
is still missing. Draft delivery leaves missing media markers visible.


COMPARABLE SALE PAGES (COMP SHEET)
-----------------------------------
The appraisal report template supports auto-generated comp pages.

1. In the appraisal_template_styled.docx, place the single placeholder:

      [[COMP_SHEETS_BLOCK]]

   on its own paragraph at the point where comp pages should appear
   (typically at the start of the Sales Comparison Approach section).

2. Fill in the comp_data sheet in workbook.xlsx:
   - Row 1 is the header (do not edit)
   - Each row 2+ is one comparable sale
   - Column A (COMP_NO):      e.g. "Sale No. 1"
   - Columns B–Z, AA–AI:     all comp fields (see row 1 headers for labels)
   - Rows without a value in column A are skipped

3. When you run:
      python axiom.py deliver <file_no>

   The platform will automatically:
   - Fill all [[KEY]] placeholders in the report as usual
   - Expand [[COMP_SHEETS_BLOCK]] into N fully-formatted comp pages
   - Add a page break between each comp

The comp block template (templates/comp_block_template.docx) is the
single-comp master — edit it to change the layout for all comps.


ADDING A NEW TEMPLATE
---------------------
1. Drop the new .docx template into the templates/ folder
2. Open config.json
3. Add an entry under the appropriate stage ("engage" or "deliver"):
     {
       "template": "your_template.docx",
       "output":   "your_output.docx"
     }
4. Add any new placeholders to schemas/field_registry.v1.json and increment
   its schema version under the rules in docs/FIELD_REGISTRY.md.
5. Run: python axiom.py contract


ADDING A NEW STAGE
------------------
Open config.json and add a new entry under "stages" following the
same pattern as "engage" and "deliver". Then add the corresponding
command handler in axiom.py (copy cmd_engage as a starting point).
