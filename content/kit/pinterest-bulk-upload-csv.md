---
title: "How to Bulk Upload Pins to Pinterest with a CSV (Step by Step)"
seo_title: "How to Bulk Upload Pins to Pinterest with a CSV"
description: "Bulk upload up to 200 Pinterest pins with one CSV file: the exact header line, a sample row, hosting your images and the upload steps."
keyword: "pinterest bulk upload csv"
category: pinterest
date: 2026-10-09
updated: 2026-10-09
tool: pinterest-csv-checker
feature: pins
start_here: true
---

Making pins one at a time is fine for three pins. For thirty it gets slow, and for a whole week of video promotion it eats an afternoon. Pinterest has a built-in bulk create feature that takes a CSV file and turns every row into a pin, with its own title, description, link, board and publish time. This guide walks through the whole process: what the file must contain, the exact header line, how to prepare your images, and how to upload and check the result.

## What you need before you start

Bulk upload has a few requirements. Sort these out first and the rest is mostly copy and paste.

- **A Pinterest business account.** It is free. You can convert a personal account or create a new one. Bulk create is not available on personal accounts.
- **Your boards, already created.** The CSV does not create boards. Every board name in the file must match an existing board exactly.
- **Your pin images, hosted online.** Pinterest fetches each image from a link, so the images need a public, direct URL. A file on your computer or a Google Drive sharing link will not work.
- **A spreadsheet tool** that can save as CSV: Google Sheets, Excel, LibreOffice or Numbers all work.

For the images themselves, use the standard 2:3 pin size of 1000×1500 pixels. Pinterest accepts other sizes, but tall 2:3 images are the format the feed is built around.

## The exact CSV header

The first line of your file must contain these column names, spelled exactly like this, in this order:

```
Title,Media URL,Pinterest board,Thumbnail,Description,Link,Publish date,Keywords
```

Here is what goes in each column:

| Column | What to put in it | Required? |
| --- | --- | --- |
| Title | The pin title, up to 100 characters | Yes |
| Media URL | Public direct link to the image (or video) | Yes |
| Pinterest board | Exact name of an existing board | Yes |
| Thumbnail | Cover image link, only for video pins | Video only |
| Description | Up to 500 characters | Recommended |
| Link | Where the pin sends people (your video, blog post or product page) | Recommended |
| Publish date | YYYY-MM-DDTHH:MM:SS, in the future | Optional |
| Keywords | A few comma-separated keywords | Optional |

For image pins, leave Thumbnail empty but keep the column. Removing a column shifts everything after it and the upload will fail or put text in the wrong place.

## A sample row

Here is one complete line under the header, for an image pin that promotes a YouTube video:

```
Title,Media URL,Pinterest board,Thumbnail,Description,Link,Publish date,Keywords
"7 Budget Meal Prep Ideas for Busy Weeks",https://yourname.github.io/pins/meal-prep-01.jpg,Budget Meal Prep,,"Seven simple meal prep ideas that keep the shopping list short. Watch the full video for the step-by-step method.",https://www.youtube.com/watch?v=VIDEO_ID,2026-10-20T18:00:00,"meal prep, budget meals, easy recipes"
```

A few details worth copying:

1. Wrap any field that contains a comma in double quotes. Titles, descriptions and keywords often do.
2. The empty Thumbnail is just two commas in a row: `,,`.
3. The publish date uses a capital T between the date and the time, with seconds.
4. The Media URL ends in the actual file name (`.jpg` or `.png`). That is what "direct link" means.

If you build the file in a spreadsheet, you do not need to type the quotes. Put each value in its own cell and the export adds quotes where needed.

## Step 1: Prepare and host your images

Name your image files clearly, for example `meal-prep-01.jpg`, `meal-prep-02.jpg`. Short, lowercase names without spaces make the URLs easy to build and less likely to break.

Next, upload the images somewhere that gives each file a public link. A simple free option is GitHub Pages, which serves files at addresses like `https://yourname.github.io/pins/meal-prep-01.jpg`. The full walkthrough is in [how to host Pinterest images with GitHub Pages](../host-pinterest-images-github-pages/).

Before you go further, paste one image URL into a private browser window. You should see only the image, with no login screen or preview page around it. If that works, Pinterest can fetch it too.

## Step 2: Fill in the spreadsheet

Open a new sheet and put the eight column names in row 1. Then add one row per pin:

1. **Title:** a clear, searchable phrase. Stay well under 100 characters so it reads well in the feed.
2. **Media URL:** the hosted link for that pin's image.
3. **Pinterest board:** copy the board name from Pinterest instead of retyping it, so spelling and capitals match.
4. **Thumbnail:** empty for image pins.
5. **Description:** one or two sentences that say what the person gets when they click, with your main keywords worked in naturally. Keep it under 500 characters.
6. **Link:** the destination. If you want to see Pinterest traffic in your analytics, add UTM parameters, for example `?utm_source=pinterest&utm_medium=social&utm_campaign=meal-prep`.
7. **Publish date:** spread pins out over days instead of publishing them all at once. Every date must be in the future when you upload.
8. **Keywords:** a short list of relevant terms, separated by commas.

You can include up to 200 pins in one CSV. If you have more, split them into several files.

The Faceless Creator Kit's Pin Factory can do this step for you: it renders the pin images in batch and exports the CSV with the header, UTM links and a posting schedule already filled in. Either way, the file format is the same.

## Step 3: Save as CSV and check it

Export the sheet as CSV (comma-separated values), with UTF-8 encoding if your app asks. In Google Sheets that is File → Download → Comma-separated values. In Excel, choose "CSV UTF-8" in the Save As dialog.

Then check the file before Pinterest does. Run it through the free [Pinterest CSV Checker](../../tools/pinterest-csv-checker/), which looks for the common problems: a wrong or misspelled header, titles or descriptions that are too long, publish dates in the past or in the wrong format, and Media URLs that do not look like direct image links.

A quick manual checklist if you prefer:

- Header line matches exactly, including capital letters and spaces
- No empty Title, Media URL or Pinterest board cells
- Every board name exists in your account
- No more than 200 rows of pins
- All publish dates are in the future

## Step 4: Upload the file to Pinterest

The menus move around from time to time, but at the time of writing the path looks like this:

1. Log in to your business account on a computer.
2. Click **Create** and choose **Create Pins in bulk**.
3. Upload your .csv file.
4. Wait while Pinterest processes it. Larger files take longer, and Pinterest usually shows a notification when the upload is done or when something failed.

Pins with a publish date appear as scheduled pins. Pins without one are published as soon as they are processed.

If something goes wrong, Pinterest reports which rows failed. The most common causes and their fixes are collected in [Pinterest bulk CSV errors and how to fix them](../pinterest-bulk-csv-errors/). Check Pinterest's help page for the current limits, since they can change.

## After the upload

Open a few of the new pins and check them in the feed: the image loads, the title is not cut off awkwardly, and the link goes to the right page with your UTM tags intact. Fix any single pin directly in Pinterest rather than re-uploading the whole file, or you may end up with duplicates.

Once the process works, it becomes a routine you can repeat every week: new images, a new sheet, one upload. If you are promoting YouTube videos this way, [Pinterest for YouTubers](../pinterest-for-youtubers/) covers how to plan pins around each video. Bulk upload saves time, but it makes no promise of views or sales on its own; useful pins that lead to useful content are still what matters.
