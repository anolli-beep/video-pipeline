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

## Stick-figure scenes (all channels)

A shot can also be a short animated stick-figure scene in the channel's flat style:

```json
{"stick": {"scene": "point", "label": "11.40pm, 14 April 1912", "who": {"preset": "lookout", "name": "Frederick Fleet"}, "bubble": "!"}}
{"stick": {"scene": "talk", "who": "captain", "other": {"preset": "gentleman", "hat": "none", "name": "Thomas Andrews"}, "bubbles": ["?", "!"]}}
{"stick": {"scene": "ship", "label": "11.40pm", "night": true, "iceberg": true}}
{"stick": {"scene": "deposit", "box": "ISA", "pop": "+ tax-free"}}
```

- Scenes: walk, march, think, worried, celebrate, point, shrug, cross_river, deposit, coins_jar,
  crowd_shocked, dig, read, talk, ship, lifeboat, radio.
- `label`: short heading at the top. `bubble` / `bubbles`: text in speech bubbles. `others`: a list of
  characters for crowds, marches and lifeboats. `ship` also takes `night`, `iceberg` and `funnels`;
  `lifeboat` takes `night`, `count` and `face`; `radio` shows its `bubble` as the message sent.
- `who` (and `other`): a ready-made character, or one with changes, e.g.
  `{"preset": "king", "colour": "#24457a", "facial": "beard", "name": "Henry VIII"}`. Leave `who` out to
  show the channel's own guide character. Crowd members get small random differences so none are identical.
- Characters: roman_general, roman_soldier, senator, emperor, king, queen, sultan, knight, monk, baker,
  diarist, merchant, sailor, worker, saver, student, parent, retiree, banker, official, captain, officer,
  lookout, wireless_op, gentleman, lady, steward, child, soldier, pilot, scientist.
- Look options: `hat` (none, laurel, crown, helmet, helmet_closed, turban, cap, tophat, tricorn, baker,
  peaked, widehat, headphones, tin_helmet, flying_cap), `hair` (short, long, long_curly, curly, bun,
  tonsure, bald, none), `hair_colour`, `facial` (beard, moustache), `glasses`, `outfit` (cape, robe,
  toga, tabard, tie, apron, scarf, jacket, coat, dress), `build` (slim, normal, stout), `height`,
  `colour`, `shield`, `name`.
- Pictures that stay up longer than `max_shot_seconds` (6 by default) are split into close-ups, so
  the screen changes about every 5 seconds even when a scene has few shots.

## Short clips (optional)

```json
"clips": [{"scenes": [4, 6], "hook": "The river that started a civil war",
           "caption": "One small river, one huge decision.", "hashtags": ["romanhistory", "juliuscaesar"]}]
```

- `scenes`: first and last scene numbers (counting from 1). Keep each clip around 45-55 seconds
  of narration (about 110-135 words). If it runs over 59 seconds, scenes are dropped from the end.
- Without `clips`, up to 3 are picked from the chapter openings.

## Pronunciations (optional)

```json
"pronunciations": {"Rumelihisarı": "Roo-meh-lee-hee-sar-uh"}
```

Respellings for this video only, on top of `pronunciations.yaml`. Captions keep the normal spelling.
