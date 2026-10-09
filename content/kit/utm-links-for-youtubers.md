---
title: "UTM Links for YouTubers: Track Which Videos Send Visitors"
seo_title: "UTM Links for YouTubers: Track What Works"
description: "How to add UTM tags to the links in your YouTube descriptions and pins, with a simple naming system, so you can see which video or pin sent each visitor."
keyword: "utm links for youtube"
category: selling
date: 2026-10-09
updated: 2026-10-09
tool: title-scorer
feature: planner
---

If you link to your own site, a free download or a product from your videos, you'll eventually want to know which video sent people there. YouTube Studio shows how many people watched; it doesn't show what they did after they left. UTM tags fill that gap. They're short labels you add to the end of a link, and most analytics tools read them to tell you where each visitor came from.

This guide explains what UTM tags are, a simple naming system for YouTube and Pinterest, and how to read the results without getting lost in data.

## What a UTM link looks like

A UTM link is a normal link with a few extra parameters at the end:

```
https://example.com/checklist/?utm_source=youtube&utm_medium=description&utm_campaign=repot-snake-plant
```

The page is the same; the extra part just labels the visit. There are five standard tags:

| Tag | What it means | Example |
|---|---|---|
| `utm_source` | Where the visitor came from | `youtube`, `pinterest` |
| `utm_medium` | The type of link | `description`, `pinned-comment`, `pin` |
| `utm_campaign` | What you're promoting or which piece of content | the video's slug, like `repot-snake-plant` |
| `utm_content` | Optional: which link, if there are several | `top-link`, `links-list` |
| `utm_term` | Optional: mostly for paid search keywords | usually not needed |

For most creators, the first three are enough.

## A simple naming system

UTM tags only help if you use them the same way every time. Pick a system and write it down:

- **Always lowercase.** Some analytics tools treat `YouTube` and `youtube` as different sources.
- **Use hyphens, not spaces.** `repot-snake-plant`, not `repot snake plant`.
- **Source = the platform.** `youtube`, `pinterest`, `newsletter`.
- **Medium = where the link sits.** `description`, `pinned-comment`, `pin`, `email`.
- **Campaign = the video or pin slug.** A short, unique name for each piece of content. If your videos have working titles in a planner, reuse a short version of those.

This repo's own pins use the same idea: `utm_source=pinterest&utm_medium=pin&utm_campaign=<pin-slug>`. It's simple, consistent and easy to filter.

## Where to use UTM links

Add tags to links that go to **your own** pages, where you can see the analytics:

- The main link in your video description (see the [YouTube description guide](../youtube-description-template/) for where it belongs)
- Links in pinned comments
- The link field of each Pinterest pin
- Links in your emails to subscribers

Don't add UTM tags to links within your own site, from one page to another. That can overwrite the original source of the visit and make your reports less accurate.

Links to other people's sites don't need your tags; you won't see their analytics anyway.

## Where you'll see the results

UTM tags are only useful if something reads them. Common options:

- **Website analytics.** Tools like Google Analytics, and many privacy-focused alternatives, report visits by source, medium and campaign.
- **Store or email platforms.** Some show referral sources or UTM data for each sale or sign-up. Check what yours reports before relying on it.
- **Pinterest analytics** shows outbound clicks per pin, which you can compare with the visits your own analytics records for each pin's campaign tag.

If your platform doesn't report UTM tags at all, they still don't hurt, and you'll have them in place if you add analytics later.

## Making UTM links without mistakes

Typing tags by hand leads to typos. A few ways to avoid that:

- **Keep a spreadsheet** with columns for page, source, medium and campaign, and a formula that joins them into a link.
- **Use a link builder.** Several free campaign URL builders exist, including one from Google, that build the link from a form.
- **Use `?` for the first tag and `&` for the rest.** If the page link already has a `?`, start your tags with `&` instead.
- **Test every link** in a private browser window. It should open the right page, with the tags visible in the address bar.

Long links look messy in descriptions. You can shorten them with a link shortener, but check that the shortener keeps the tags when it redirects, and remember that viewers can't see where a short link goes. A clear label next to the link helps.

## Reading the results without overthinking

Once a month, or as part of a weekly review, look at visits and sign-ups grouped by campaign:

1. **Which videos send visitors at all?** Often it's a small number of videos. That's normal and useful to know.
2. **Which links get used?** If the pinned-comment link never gets clicks but the description link does, focus there.
3. **Which pins send visitors?** Compare campaigns tagged `pinterest` to see which pin topics and headlines lead to your site.

Then make one small change based on what you see, for example moving the main link higher in the description of your next video. The [weekly content review](../weekly-content-review/) explains how to change one thing at a time so you can tell what helped.

Keep expectations realistic. UTM data shows where visits came from; it can't tell you why. Small numbers can swing a lot from week to week, so look for patterns over several weeks before drawing conclusions.

## Privacy and honesty

UTM tags describe the link, not the person. They don't identify individual viewers, and they don't need to. If your site uses analytics, make sure your privacy policy says so, and follow the rules that apply where you and your visitors are. This isn't legal advice; your analytics or store provider usually has guidance for its own product.

## Quick checklist

- Use `utm_source`, `utm_medium` and `utm_campaign` on links to your own pages
- Lowercase, hyphens, the same system every time
- Campaign = the video or pin slug
- No UTM tags on links within your own site
- Test every link before publishing
- Review by campaign monthly, and change one thing at a time

If you're also improving the titles of the videos that carry these links, the free [YouTube Title Scorer](../../tools/title-scorer/) checks drafts for length, a strong start and your keyword. Pins have their own checks in the free [Pinterest CSV Checker](../../tools/pinterest-csv-checker/), including link format.
