# Plans folder

Upload plan files (`something.json`) written in the Claude chat here. Each upload starts the
**Render videos from plans** workflow, which makes one video per plan at the same time (up to 5),
then moves finished plans into `plans/done/`. A plan that fails stays here so you can retry it
(Actions → Render videos from plans → Run workflow).

## Plan format

```json
{
  "channel": "history",
  "title": "The Day Constantinople Fell",
  "alt_titles": ["...", "..."],
  "thumbnail_text": "THE LAST DAY",
  "description_summary": "Two or three sentences for the top of the description.",
  "tags": ["fall of constantinople", "byzantine empire"],
  "lane": "Big events & empires",
  "publish_at": "2026-10-01T16:00:00+01:00",
  "sources": [{"title": "Britannica: Fall of Constantinople", "url": "https://..."}],
  "unverified": [{"claim": "...", "reason": "only one source"}],
  "scenes": [
    {
      "chapter": "Introduction",
      "narration": "On the night of 28 May 1453, ...",
      "shots": [
        {"file": "File:Le siège de Constantinople (1453) by Jean Le Tavernier after 1455.jpg",
         "caption": "The siege, illuminated manuscript, c. 1455"},
        {"query": "Theodosian Walls Istanbul", "caption": "The Theodosian Walls today"}
      ]
    },
    {"chapter": null, "narration": "...", "shots": [ ... ]}
  ]
}
```

- `channel`: `history`, `finance` or `politics`. It picks the voice, colours, disclaimer and the
  issue label. Plans without it are treated as history.
- `chapter`: a short title on the first scene of each chapter, `null` on the rest.
- Each shot uses `file` (an exact Wikimedia Commons file name) or `query` (a specific Commons
  search), or both (`query` is the fallback if the file can't be used).
- Only public domain, CC0 and CC BY images are used; the rest are skipped automatically.
- `publish_at` is optional (UK time with offset).

## Cards and charts (all channels)

A shot can also be an animated card or chart, drawn in the channel's colour:

```json
{"card": {"style": "title", "kicker": "THE BASICS", "text": "What is an ISA?"}}
{"card": {"style": "stat", "value": "£20,000", "label": "ISA allowance each tax year", "note": "2026/27 · GOV.UK"}}
{"card": {"style": "list", "title": "Four kinds of ISA", "items": ["Cash ISA", "Stocks and shares ISA"]}}
{"card": {"style": "quote", "text": "...", "by": "James Madison, Federalist No. 51, 1788"}}
{"card": {"style": "compare", "left": {"title": "Supporters say", "items": ["..."]},
                              "right": {"title": "Critics say", "items": ["..."]}}}
{"chart": {"type": "bar", "title": "Bank of England base rate, end of year", "labels": ["2022", "2023"],
           "values": [3.5, 5.25], "suffix": "%", "source": "Bank of England", "highlight": 1}}
{"chart": {"type": "line", "title": "...", "labels": ["..."], "values": [1, 2], "prefix": "$", "suffix": "tn"}}
```

- Optional `thumbnail_file` (top level): the Commons file to use for the thumbnail. Otherwise the first
  photo is used, or the first card if the video has no photos.
- Every plan is checked before anything is spent (`python main.py check plans/x.json`).

## Short clips (optional)

```json
"clips": [{"scenes": [4, 6], "hook": "The river that started a civil war",
           "caption": "One small river, one huge decision.", "hashtags": ["romanhistory", "juliuscaesar"]}]
```

- `scenes`: first and last scene numbers (counting from 1). Keep each clip around 45-55 seconds
  of narration (about 110-135 words). If it runs over 59 seconds, scenes are dropped from the end.
- Without `clips`, up to 3 are picked from the chapter openings.
