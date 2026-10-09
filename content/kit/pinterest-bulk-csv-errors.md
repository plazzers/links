---
title: "Pinterest Bulk CSV Errors and How to Fix Them"
description: "The most common Pinterest bulk upload CSV errors, what causes each one and how to fix it, from header mistakes to broken image links."
keyword: "pinterest bulk upload csv error"
category: pinterest
date: 2026-10-09
updated: 2026-10-09
tool: pinterest-csv-checker
feature: pins
---

You built a CSV, uploaded it to Pinterest, and some or all of the pins did not appear. Bulk upload is strict about the file format, and a small slip in one column can fail a row or the whole file. The good news is that almost every failure comes from a short list of causes. This guide goes through them one by one in the same format: the error you see, what causes it, and how to fix it.

Pinterest's exact wording changes over time, so treat the error descriptions below as typical symptoms rather than exact messages.

## Before you debug: check the basics

Rule out these four things first. They cover a surprising share of problems.

1. **Business account.** Bulk create only works on a Pinterest business account (free to set up).
2. **File type.** The file must be a real .csv, not .xlsx or .numbers renamed to .csv.
3. **Row count.** Up to 200 pins per CSV. Split larger batches into several files.
4. **Header line.** The first line must be exactly:

```
Title,Media URL,Pinterest board,Thumbnail,Description,Link,Publish date,Keywords
```

The quickest way to check all of this at once is the free [Pinterest CSV Checker](../../tools/pinterest-csv-checker/), which reads your file in the browser and flags each problem by row. If you are starting from scratch, the full walkthrough is in [how to bulk upload pins with a CSV](../pinterest-bulk-upload-csv/).

## File and header errors

### The whole file is rejected or "invalid format"

- **Cause:** The header does not match. Common slips are `Board` instead of `Pinterest board`, `Image URL` instead of `Media URL`, `Publish Date` with a capital D, extra spaces, or a missing column such as Thumbnail.
- **Fix:** Replace your first line with the exact header above. Keep all eight columns, even ones you leave empty.

### Strange characters at the start of the first column

- **Cause:** Some apps add an invisible byte-order mark or save in a non-UTF-8 encoding, so the first header reads as something like `ï»¿Title`.
- **Fix:** Re-export as "CSV UTF-8" (Excel) or File → Download → Comma-separated values (Google Sheets). If the problem persists, paste the data into a fresh Google Sheet and download it from there.

### Columns are shifted or text lands in the wrong field

- **Cause:** A title, description or keyword list contains a comma but is not wrapped in double quotes, so the comma splits it into two columns. Line breaks inside a description can do the same.
- **Fix:** Wrap those fields in double quotes, or let your spreadsheet app export the CSV so it adds quotes automatically. Remove line breaks inside cells.

### The file uses semicolons instead of commas

- **Cause:** In some regions, Excel uses semicolons as the list separator when saving CSV.
- **Fix:** Open the file in a text editor to check. If you see semicolons, export again from Google Sheets, or change the separator setting in your system or Excel options.

## Image and Media URL errors

These are the most common row-level failures.

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Image could not be fetched | URL is not public | Test it in a private window; make the file or repository public |
| Link opens a preview page | URL is a share link, not a direct file | Use a link that ends in the file, such as `.jpg` or `.png` |
| Works for you, fails for Pinterest | Image sits behind a login | Host it somewhere that serves files without signing in |
| 404 on the image | Typo or wrong capitals in the file name | Copy the exact file name; URLs are often case-sensitive |

### "Media URL" fails on Google Drive or Dropbox links

- **Cause:** Sharing links from cloud storage usually open a viewer page, not the raw image. Pinterest needs the image file itself.
- **Fix:** Host your images on a service that gives each file a plain public URL. A free option is covered in [hosting Pinterest images with GitHub Pages](../host-pinterest-images-github-pages/).

### Images upload but look cropped or tiny

- **Cause:** The image is not in a pin-friendly ratio, or it is very small.
- **Fix:** Use 1000×1500 pixels (2:3). Keep file sizes reasonable so they load quickly.

## Board errors

### "Board not found" or the row is skipped

- **Cause:** The board does not exist yet, or the name differs from the real board name. Differences in capitals, a trailing space, an ampersand versus "and", or a curly apostrophe versus a straight one all count.
- **Fix:** Create the board first in Pinterest. Then copy its name from the board page and paste it into every row. If you use board sections, check Pinterest's help page for how sections are handled in bulk upload at the time of writing.

### Pins go to the wrong board

- **Cause:** A shifted column (see the comma problem above) pushes text from Media URL or Title into the board column.
- **Fix:** Fix the quoting, then check that each row has exactly eight fields.

## Title, description and keyword errors

### Text is cut off or the row fails on length

- **Cause:** Title over 100 characters or description over 500.
- **Fix:** Trim them. A shorter title often reads better in the feed anyway. Count characters in your spreadsheet with `=LEN(A2)` in a helper column, and delete the helper column before exporting.

### Missing title or description

- **Cause:** Empty cells, often from a formula that returned nothing or a row that was only partly filled in.
- **Fix:** Fill every Title, Media URL and Pinterest board cell. Delete fully empty rows at the bottom of the sheet, since some exports keep them as rows of commas.

### Keywords look wrong or are ignored

- **Cause:** Keywords are not quoted, so the commas between them split into new columns.
- **Fix:** Put the full keyword list in one cell, for example `"meal prep, budget meals, easy recipes"`.

## Publish date errors

### Pins publish right away instead of on schedule

- **Cause:** The Publish date column is empty, or the value was not recognized.
- **Fix:** Use the format `YYYY-MM-DDTHH:MM:SS`, for example `2026-10-20T18:00:00`, with a capital T.

### "Date must be in the future" or the row fails

- **Cause:** The date has already passed, often because the file was prepared days earlier, or because the time is earlier today.
- **Fix:** Move all dates forward. Leave a buffer of at least a few hours after the moment you upload.

### Dates change format when you open the CSV

- **Cause:** Spreadsheet apps convert date text into their own date format, then save it back as something like `10/20/2026 18:00`.
- **Fix:** Format the Publish date column as plain text before you paste the dates, or add the dates after the last time you open the file in a spreadsheet. Check the raw file in a text editor before uploading.

## Link and video pin errors

### Link column rejected

- **Cause:** The link is missing `https://`, contains spaces, or points to a site Pinterest blocks.
- **Fix:** Use full URLs that start with `https://`. Encode spaces as `%20` or remove them. If you add UTM parameters, check the link still opens correctly.

### Video pins fail

- **Cause:** The Thumbnail column is empty for a video, or it contains a link to something that is not an image.
- **Fix:** For video pins, add a direct image link in Thumbnail. For image pins, leave Thumbnail empty.

## A quick prevention routine

Most of these problems are easier to prevent than to fix after an upload. Before every batch:

1. Start from a saved template with the correct header.
2. Paste board names from Pinterest, never type them.
3. Open three random image URLs in a private window.
4. Check lengths and dates in the sheet.
5. Run the finished file through the [Pinterest CSV Checker](../../tools/pinterest-csv-checker/).

If you make pins in batches regularly, the Faceless Creator Kit's Pin Factory exports the CSV with the header, length checks and future publish dates already handled, which removes several of the errors above at the source. Whichever way you build the file, a clean CSV only gets the pins published; it makes no promise of views or clicks, so the pins themselves still need to be worth saving.
