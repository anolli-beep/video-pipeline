# Video Pipeline: History, Finance and Politics channels

One repo makes the videos for all three of your channels, **in exactly the same way**:

1. **In the Claude chat:** Claude researches the topic, writes the script, and picks the pictures, cards and charts. You get one plan file (`.json`) per video. The plan says which channel it's for.
2. **On GitHub:** you upload the plan files. GitHub records the narration with that channel's ElevenLabs voice, fetches the Wikimedia images, animates the cards and charts in the channel's colours, and edits the video.
3. **You:** get a **"[Finance] Ready to upload"** (or [History], [Politics]) issue by email, check the video, and upload it to that channel in YouTube Studio.

| | History | Finance (UK) | Politics (US, nonpartisan) |
|---|---|---|---|
| Settings file | `config.yaml` + `channels/history.yaml` | `channels/finance.yaml` | `channels/politics.yaml` |
| Accent colour | red | green | teal (deliberately not party red or blue) |
| Visuals | mostly Wikimedia paintings, maps and photos | mostly animated cards and charts, plus photos | photos (Capitol, official portraits) plus cards and charts |
| Disclaimer in description | historians' debates | not financial advice, figures dated | nonpartisan, disputes attributed |
| Suggested publish times | 16:00, 19:30 UK | 07:30, 18:00 UK | 08:00, 17:00 US Eastern (13:00, 22:00 UK) |

No Google Cloud is needed, and no Anthropic API credits are used for the plan route.

---

## What it costs

| Service | Cost |
|---|---|
| **Claude** | Plans are written in your normal Claude chat. No API credits. |
| **ElevenLabs** | Each 10-minute video uses about 9,000 credits. One channel at 2 a day is about 540,000 a month, which is roughly the **Pro plan**. All three channels at 2 a day is about 1.6 million a month, which needs a bigger plan, so start slower (for example 1 a day per channel) and check current plan sizes at elevenlabs.io/pricing. `eleven_flash_v2_5` uses half the credits of `eleven_multilingual_v2`. |
| **GitHub** | **Free if the repository is Public.** |

---

## Part A: one-time setup (about 30 minutes)

### Step 1: ElevenLabs key and voices
1. Go to **elevenlabs.io** and choose a subscription (see costs above).
2. **Developers → API Keys → Create API Key**: switch on **Text to Speech** and **Voices: Read**. Copy the key.
3. **Voice Library**: filter to *Category: Narration* and *Language: English*. Pick one voice per channel (calm documentary for history, clear and friendly for finance, neutral for politics), preferring voices with a long notice period.
4. Click **+** to add each to My Voices. Then in **My Voices**, click **⋯ → Copy voice ID** for each. Keep them for step 3.

### Step 2: Put the code on GitHub
1. Sign in at **github.com**, then click **+** (top right) → **New repository**.
2. Name it `video-pipeline` and choose **Public**. Private also works, but its free storage (500 MB) fills up after a couple of videos. Your key stays secret either way.
3. Click **Create repository**, then click **uploading an existing file**.
4. Unzip the download and drag **everything inside the `video-pipeline` folder** onto the page, including the hidden `.github` folder. On a Mac, press **Cmd + Shift + .** in Finder to show hidden files; on Windows, go to **View → Show → Hidden items**.
5. Click **Commit changes**.
6. Check that you can see a `.github` folder in the file list. If not: **Actions → set up a workflow yourself**, name the file `render.yml`, paste in the contents of `.github/workflows/render.yml` from the download, and **Commit changes**.

### Step 3: Your channel settings
Edit each of these in the repo: click the file, then the **pencil icon** ✏️, change only the values in quotes, and **Commit changes**.
- `config.yaml` (history): `channel_name` and `elevenlabs_voice_id`
- `channels/finance.yaml`: `channel_name` and `elevenlabs_voice_id`
- `channels/politics.yaml`: `channel_name` and `elevenlabs_voice_id`

A channel you haven't set up yet just can't be used: its plans stop at the check step with a clear message, and nothing is spent.

### Step 4: Add your key to GitHub
In your repo: **Settings → Secrets and variables → Actions → New repository secret**. Name `ELEVENLABS_API_KEY`, paste the key from step 1, then **Add secret**.

### Step 5: Allow it to save its progress
**Settings → Actions → General**. Under **Workflow permissions**, choose **Read and write permissions**, then **Save**.

### Step 6: Get email alerts
On the repo's main page, click **Watch** (or **Unwatch**; top right, next to Fork and Star) → **All Activity**. Then check **profile picture → Settings → Notifications** has **Email** ticked under Watching.

### Step 7: First test run
1. Click the **Actions** tab. If asked, click **I understand my workflows, go ahead and enable them**.
2. Ask Claude for a plan (or use one you already have) and upload it to the `plans` folder: open `plans`, **Add file → Upload files**, drag the `.json` file in, **Commit changes**.
3. Wait about 20–30 minutes. A green tick under **Actions** means it worked. A red cross means it failed; click it to see the error and check the troubleshooting table below.
4. Go to the **Issues** tab and you'll find **"[History] Ready to upload: …"**. Follow Part B.

---

## Part B: uploading a video (about 10 minutes each)

### 1. Download
1. Open the **"Ready to upload"** email or issue and click the **Download** link at the bottom.
2. Scroll to the bottom of that page. Under **Artifacts**, click **video-…** to download the zip.
3. Unzip it. You'll have: `video.mp4`, `thumbnail.jpg`, `captions.srt`, `UPLOAD.txt`, `script.txt`, a `clips` folder with `CLIPS.txt` (and sometimes `pinned_comment.txt`).

⏱ Downloads are kept for **7 days**, so upload within a week.

### 2. Check it (the important part)
- Open the issue and read **"Worth a look before you upload"**. If the issue title starts with **⚠️**, read `script.txt` properly first.
- Watch the video, or at least skim through it: check that the images match what's being said and the voice sounds right.
- Not happy? Just don't upload it. Close the issue and a new video comes at the next run.

### 3. Upload to the right channel
1. Go to **studio.youtube.com**.
2. **Make sure you're on the right channel:** the issue title and the top of `UPLOAD.txt` say which one ([History], [Finance] or [Politics]). Click your profile picture (top right) → **Switch account** → choose that channel.
3. Click **Create** (top right) → **Upload videos** → **Select files** → choose `video.mp4`.

### 4. Fill in the details (copy from `UPLOAD.txt`)
- **Title:** paste the title.
- **Description:** paste everything under DESCRIPTION.
- **Thumbnail:** click **Upload file** and choose `thumbnail.jpg`. If it's greyed out, see Part C.
- **Audience:** **No, it's not made for kids**.
- Click **Show more**:
  - **Altered content:** **Yes**, because the narration is AI.
  - **Tags:** paste the tags.
  - **Category:** the one in `UPLOAD.txt` (Education, or News & Politics for the politics channel).
- Click **Next**.

### 5. Add the subtitles
1. On **Video elements**, click **Add** next to Subtitles.
2. Choose **Upload file → With timing → Continue**, pick `captions.srt`, then click **Done**.
3. Optional: **End screen → Add** to promote your latest video.
4. Click **Next**, wait for **Checks** to finish (look out for copyright claims), then click **Next**.

### 6. Schedule it
1. On **Visibility**, choose **Schedule**.
2. Set the date and time to the **SUGGESTED PUBLISH TIME** in `UPLOAD.txt`.
3. Click **Schedule**.

### 7. Finish
- If there was a `pinned_comment.txt`: once the video is live, post its text as a comment, then click **⋮ → Pin**.
- Close the GitHub issue (the **Close issue** button) so your inbox shows only videos still to upload.

---

## Making videos (the normal routine)

1. **In Claude, ask:** *"Make 3 history video plans"*, *"Make 2 finance video plans"* or *"Make 2 politics video plans"* (up to 5 at a time, any mix of channels, or name the topics). Claude researches each one, writes the script, picks the visuals and short clips, and gives you one `.json` file per video.
2. **Upload them:** in your repo, open the **plans** folder, click **Add file → Upload files**, drag all the `.json` files in, and click **Commit changes**.
3. **Wait about 20–30 minutes.** The **Render videos from plans** workflow starts on its own and makes all the videos at the same time. You get one **"Ready to upload"** issue per video, labelled with its channel.
4. **Upload them** as in Part B, and post the short clips (next section).

Finished plans move to `plans/done/`. If a video fails, its plan stays in `plans/` and you can retry it with **Actions → Render videos from plans → Run workflow**.

## Short clips for Shorts, Reels, TikTok, Facebook and Snapchat

Every video also comes with **3 vertical clips** (1080×1920, under 60 seconds) in the download's `clips` folder. Each clip is a run of whole scenes, so it starts and ends on a complete thought. It has a hook title at the top, the video in the middle, big captions underneath (most people watch shorts with the sound off) and your channel name at the bottom.

`CLIPS.txt` has a title, caption and hashtags for each clip, plus a posting checklist. The same file works on every app:

| App | Where | Notes |
|---|---|---|
| **YouTube Shorts** | Same channel as the main video | Set **Related video** to the full video so viewers can tap through. |
| **TikTok** | One account per channel | Turn on **AI-generated content** (More options), because the voice is AI. |
| **Instagram Reels** | One account per channel | Turn on the **AI info** label if offered. Linking to a Facebook Page lets Reels share there too. |
| **Facebook Reels** | Facebook Page per channel | Same caption as Instagram. |
| **Snapchat Spotlight** | Snapchat public profile | 60 seconds maximum, which these clips meet. |

Tips:
- Post one clip a day per app rather than all three at once.
- Each app pays creators differently and has its own eligibility rules (followers, views, sometimes minimum video length), which change often. Check each app's current creator programme before relying on it for income. Shorts also work as free adverts for the full videos, which earn more per view.
- Settings in `config.yaml`: `clips_per_video`, `clip_max_seconds` and `make_clips: false` to switch clips off.
- When I write a plan, I choose clips that make sense on their own and write a hook for each. Plans without clips get them picked automatically from the chapter openings.

## Adding the other channels (finance and politics)

If you set up only history at first, add the others whenever you're ready:

1. **YouTube:** create the channel (profile picture → **Settings → Add or manage your channels → Create a channel**). All channels can sit under one Google account; you switch between them in Studio.
2. **Voice:** add a voice for it in ElevenLabs and copy its voice ID.
3. **Settings:** fill in `channel_name` and `elevenlabs_voice_id` in `channels/finance.yaml` or `channels/politics.yaml` (pencil ✏️, then **Commit changes**).
4. **Ask Claude** for plans for that channel and upload them as usual. The same ElevenLabs key works for every channel.

## Part C: optional extras
- **Custom thumbnails greyed out?** Verify each channel in YouTube Studio: **Settings → Channel → Feature eligibility → Verify phone number**.
- **Background music:** in the `assets` folder, **Add file → Upload files**, and upload royalty-free tracks named exactly `music.mp3` (history), `music-finance.mp3` and `music-politics.mp3` (the YouTube Audio Library is free).
- **Change the publish times:** edit `publish_times` in `config.yaml` (history) or the channel's file in `channels`. Tell Claude too, so new plans use them.
- **Pause everything:** **Actions → Render videos from plans → ⋯ → Disable workflow**. Turn it back on the same way.

---

## Troubleshooting

| What you see | What to do |
|---|---|
| Red cross, error mentions **ElevenLabs** 401/402 | Check the `ELEVENLABS_API_KEY` secret, its permissions (Part A step 1) and your credits. |
| Red cross, error mentions **config.yaml** | A quote mark or space got changed. Compare your file with Part A step 3. |
| Red cross at **"Move finished plans"** | Part A step 5 wasn't saved. Set Read and write permissions. |
| "None of the plan's images could be found" | Ask Claude to swap the images in that plan, then upload it again. |
| No email arrived | Part A step 6, and check your spam folder for github.com emails. |
| No Artifacts at the bottom of the run | More than 7 days have passed, or the run failed. |
| Red cross at **Check the plan**, "has problems" | The plan file has a mistake (listed in the log). Nothing was spent. Paste the message into Claude for a fixed plan. |
| "set channel_name first" or "set elevenlabs_voice_id first" | That channel's file in `channels` still has a `REPLACE_WITH_...` value. See "Adding the other channels". |

## Keeping the channel healthy
YouTube judges the whole channel, and it penalises channels that look mass-produced. What protects you is the check in Part B step 2, and not publishing videos you're not happy with. If views are low after a month, **post fewer, better videos, not more.**

## What's in the folder
- `config.yaml`: shared settings, plus the history channel's name and voice
- `channels/`: one file per channel (name, voice, colour, disclaimer, publish times)
- `pipeline/graphics.py`: the animated cards and charts
- `pipeline/clips.py`: the vertical short clips
- `assets/fonts/`: the fonts used on cards, charts and thumbnails (free, OFL licence)
- `pipeline/images.py`: image search and checks
- `pipeline/render.py`: the automatic video editing
- `plans/`: where you upload plans; finished ones move to `plans/done/`
- `pipeline/writer.py`, `state/`, `archive/`: left over from the older automatic (API) version; not used
