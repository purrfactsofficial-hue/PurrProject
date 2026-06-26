# SPEC — `captions.json` Contract & Importer

**Status:** Draft 1.0
**Owners:** `/purrfacts-scenario` skill (writer) · PurrFacts platform `caption_importer.py` (reader)
**Purpose:** Define the single data contract that lets the scenario skill author all 12
publishing descriptions and the platform import them without either side knowing the other's
internals. If both sides conform to this document, import always succeeds.

---

## 1. Scope

This spec covers exactly one thing: the per-episode `captions.json` file — its location,
schema, validation, and how the platform ingests it. It does **not** cover script lines,
generation prompts, scheduling, or posting. Those are separate concerns.

```
/purrfacts-scenario  ──writes──▶  captions.json  ──reads──▶  caption_importer.py  ──▶  captions table
```

---

## 2. File location & naming

One file per **episode folder**:

```
<VIDEO_REPO_PATH>\<EpisodeFolder>\captions.json
e.g.  C:\Users\yborodulina\Downloads\Purr\Episode_Pizza\captions.json
```

- Filename is exactly `captions.json` (lowercase).
- Encoding: UTF-8 **without BOM**. Non-ASCII (Cyrillic, CJK) is expected and required.
- Exactly one per episode, covering all four languages.

---

## 3. Schema (human-readable)

```json
{
  "schema_version": "1.0",
  "episode": "Pizza",
  "episode_number": 8,
  "topic_tags": {
    "en": "#FoodFacts",
    "uk": "#ФактиПроЇжу",
    "zh": "#食物趣聞",
    "fr": "#FaitsCulinaires"
  },
  "languages": {
    "en": {
      "youtube":   { "title": "...", "description": "...", "hashtags": ["...", "#Shorts", "#PurrFacts"] },
      "tiktok":    { "caption": "...", "hashtags": ["...", "#PurrFacts"] },
      "instagram": { "caption": "...", "hashtags": ["...", "#PurrFacts"] }
    },
    "uk": { "youtube": {…}, "tiktok": {…}, "instagram": {…} },
    "zh": { "youtube": {…}, "tiktok": {…}, "instagram": {…} },
    "fr": { "youtube": {…}, "tiktok": {…}, "instagram": {…} }
  }
}
```

### Required keys
- Top level: `schema_version`, `episode`, `languages`. (`episode_number`, `topic_tags` optional but recommended.)
- `languages` MUST contain all four: `en`, `uk`, `zh`, `fr`.
- Each language MUST contain all three: `youtube`, `tiktok`, `instagram`.

### Per-platform fields

| Platform | Required fields | Notes |
|---|---|---|
| `youtube` | `title`, `description`, `hashtags` | `title` is distinct from `description` |
| `tiktok` | `caption`, `hashtags` | single line |
| `instagram` | `caption`, `hashtags` | 1–2 sentences |

### Field constraints

| Field | Type | Limit |
|---|---|---|
| `youtube.title` | string | 1–100 chars |
| `youtube.description` | string | 1–5000 chars |
| `tiktok.caption` | string | 1–150 chars (1 line) |
| `instagram.caption` | string | 1–2200 chars |
| `*.hashtags` | array of strings | each starts with `#`, no spaces inside |

---

## 4. Hashtag rules

| Platform | Count | Must include |
|---|---|---|
| `youtube` | 3–6 | `#Shorts` **and** `#PurrFacts` |
| `tiktok` | 1–5 | `#PurrFacts` |
| `instagram` | exactly 5 | `#PurrFacts` |

- `#PurrFacts` appears on **every** platform list — it's the branded series tag.
- Instagram is capped at 5 by the platform itself (Dec 2025 rule); 6+ is a hard error.
- Hashtags are stored as an array. The Phase 4 publisher decides placement (YouTube appends
  them to the description; TikTok/IG append to the caption). The skill does **not** inline
  hashtags into caption/description text.

---

## 5. Formal JSON Schema (importer validates against this)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["schema_version", "episode", "languages"],
  "properties": {
    "schema_version": { "type": "string", "const": "1.0" },
    "episode": { "type": "string", "minLength": 1 },
    "episode_number": { "type": "integer", "minimum": 0 },
    "topic_tags": {
      "type": "object",
      "properties": {
        "en": { "type": "string", "pattern": "^#" },
        "uk": { "type": "string", "pattern": "^#" },
        "zh": { "type": "string", "pattern": "^#" },
        "fr": { "type": "string", "pattern": "^#" }
      }
    },
    "languages": {
      "type": "object",
      "required": ["en", "uk", "zh", "fr"],
      "additionalProperties": false,
      "properties": {
        "en": { "$ref": "#/$defs/lang" },
        "uk": { "$ref": "#/$defs/lang" },
        "zh": { "$ref": "#/$defs/lang" },
        "fr": { "$ref": "#/$defs/lang" }
      }
    }
  },
  "$defs": {
    "hashtag": { "type": "string", "pattern": "^#\\S+$" },
    "lang": {
      "type": "object",
      "required": ["youtube", "tiktok", "instagram"],
      "properties": {
        "youtube": {
          "type": "object",
          "required": ["title", "description", "hashtags"],
          "properties": {
            "title": { "type": "string", "minLength": 1, "maxLength": 100 },
            "description": { "type": "string", "minLength": 1, "maxLength": 5000 },
            "hashtags": {
              "type": "array", "minItems": 3, "maxItems": 6,
              "items": { "$ref": "#/$defs/hashtag" },
              "allOf": [
                { "contains": { "const": "#Shorts" } },
                { "contains": { "const": "#PurrFacts" } }
              ]
            }
          }
        },
        "tiktok": {
          "type": "object",
          "required": ["caption", "hashtags"],
          "properties": {
            "caption": { "type": "string", "minLength": 1, "maxLength": 150 },
            "hashtags": {
              "type": "array", "minItems": 1, "maxItems": 5,
              "items": { "$ref": "#/$defs/hashtag" },
              "contains": { "const": "#PurrFacts" }
            }
          }
        },
        "instagram": {
          "type": "object",
          "required": ["caption", "hashtags"],
          "properties": {
            "caption": { "type": "string", "minLength": 1, "maxLength": 2200 },
            "hashtags": {
              "type": "array", "minItems": 5, "maxItems": 5,
              "items": { "$ref": "#/$defs/hashtag" },
              "contains": { "const": "#PurrFacts" }
            }
          }
        }
      }
    }
  }
}
```

The importer uses the `jsonschema` package against this exact schema. Keep this block and the
schema file (`backend/schemas/captions.schema.json`) byte-identical.

---

## 6. Validation severity

Two levels. **Errors block the import; warnings let it through but surface in the UI.**

| Condition | Severity | Message (interface voice) |
|---|---|---|
| File missing | error | "No captions.json in {folder}. Run /purrfacts-scenario for this episode, then Import." |
| Invalid JSON | error | "captions.json won't parse — line {n}: {detail}. Fix and re-import." |
| `schema_version` ≠ "1.0" (major) | error | "captions.json is version {v}; this platform reads 1.x. Update the skill or the platform." |
| Missing a language block | error | "captions.json is missing the `{lang}` block. Add it and re-import." |
| Missing a platform in a language | error | "`{lang}` has no `{platform}` block." |
| Instagram hashtags ≠ 5 | error | "`{lang}/instagram` has {n} hashtags; Instagram requires exactly 5." |
| `#PurrFacts` missing on a list | warning | "`{lang}/{platform}` is missing #PurrFacts — added on save?" |
| `#Shorts` missing on YouTube | warning | "`{lang}/youtube` is missing #Shorts." |
| Title > 100 chars | error | "`{lang}/youtube` title is {n} chars (max 100)." |
| Unknown top-level field | warning | ignored, logged |

Unknown fields are ignored (forward-compatible). Unknown **major** versions are rejected.

---

## 7. Importer behaviour (`caption_importer.py`)

### Signature
```
import_captions(episode_folder: str, video_links: dict[str,int], force: bool=False) -> ImportResult
```

### Steps
1. Locate `captions.json` in `episode_folder`. Missing → error result.
2. Parse JSON. Invalid → error result with line/column.
3. Validate against the JSON Schema (§5) + the severity table (§6).
   Any error-level finding → abort, return all findings (don't half-import).
4. For each `language × platform` (12 cells) → build a row:
   - `title`   = `youtube.title` for YouTube, else `null`
   - `caption` = `youtube.description` for YouTube, else `{platform}.caption`
   - `hashtags`= `" ".join(block.hashtags)`
   - `language`, `platform` set accordingly
   - `source`  = `"skill"`
   - `video_id`= resolved via `video_links[language]` (see §8)
5. **Upsert rule (protects manual edits):**
   - If no existing row → insert.
   - If existing row `source == "skill"` → overwrite.
   - If existing row `source == "manual"` → **skip** (keep the human edit), add to
     `skipped_manual`, unless `force=True`.
6. Return `ImportResult { imported, skipped_manual, warnings, errors }`.

### ImportResult shape (also the API response)
```json
{ "imported": 12, "skipped_manual": 0, "warnings": [], "errors": [] }
```

---

## 8. Language ↔ video-file linkage

Captions are per-language; each language has its own rendered `.mp4`. The importer needs to
attach each language block to the right `videos.id`.

**Convention (v1):** the language code appears in the filename, e.g.
`ep08_pizza_en.mp4`, `ep08_pizza_uk.mp4`, … The scanner records each as its own `videos`
row; `video_links = { "en": 41, "uk": 42, "zh": 43, "fr": 44 }`.

**Fallback:** if the episode is a single multi-language file, all 12 rows attach to that one
`video_id`. The importer accepts either; the caller supplies `video_links`.

---

## 9. API surface

| Method & path | Body | Returns |
|---|---|---|
| `POST /captions/import` | `{ "episode_folder": "...", "force": false }` | `ImportResult` |
| `GET /captions/{video_id}` | — | the saved grid for that video |
| `POST /captions/save` | `{ video_id, language, platform, title?, caption, hashtags }` | `{status:"saved"}`; sets `source="manual"` |

`/captions/save` is what the Episode-page editor calls per cell; it always stamps the row
`manual`, which then protects it from being clobbered on the next import (§7.5).

---

## 10. Writer responsibilities (`/purrfacts-scenario` skill)

When the skill finishes an episode it MUST, as its final step:
1. Assemble the object per §3 with `schema_version: "1.0"`.
2. Produce all 12 cells — no placeholders, no empty strings.
3. Apply the per-platform hashtag rules (§4) including `#PurrFacts` everywhere and `#Shorts`
   on every YouTube list.
4. Localize, don't translate — each language reads natively (per the brand's localization rule).
5. Write `captions.json` (UTF-8, no BOM) into the episode folder.
6. Echo the path so the operator knows where it landed.

A drift between this section and §3/§4 is the only thing that breaks import. They are one contract.

---

## 11. Versioning

- `schema_version` is `MAJOR.MINOR`. Importer accepts any `1.x`.
- Adding optional fields → bump MINOR; old importers ignore them.
- Renaming/removing fields or changing nesting → bump MAJOR; importer rejects mismatched MAJOR
  with the §6 message so the two sides never silently disagree.

---

## 12. Acceptance tests

- [ ] Valid Pizza `captions.json` (all 4 langs) → `imported: 12`, no errors
- [ ] Re-import same file → `imported: 12` again (skill rows overwrite cleanly)
- [ ] Edit `en/tiktok` via `/captions/save`, re-import → that cell `skipped_manual: 1`, stays edited
- [ ] Re-import with `force:true` → manual cell overwritten back to skill text
- [ ] Remove the `uk` block → error, zero rows written (atomic)
- [ ] Instagram list with 4 hashtags → error names `{lang}/instagram`
- [ ] YouTube list missing `#Shorts` → warning, import still succeeds
- [ ] BOM-prefixed or invalid UTF-8 → error with a clear fix instruction
- [ ] Unknown extra field `notes` → ignored, import succeeds

---

## 13. Worked example — `Episode_Pizza\captions.json`

Fact: the first Margherita pizza was coloured like the Italian flag.

```json
{
  "schema_version": "1.0",
  "episode": "Pizza",
  "episode_number": 8,
  "topic_tags": { "en": "#FoodFacts", "uk": "#ФактиПроЇжу", "zh": "#食物趣聞", "fr": "#FaitsCulinaires" },
  "languages": {
    "en": {
      "youtube": {
        "title": "Why Does Pizza Look Like a Flag? 🍕",
        "description": "Did you know the very first Margherita pizza was made to match the Italian flag — red tomato, white cheese, green basil? Purr Whisperich serves up a tasty slice of history. A new fact every day!",
        "hashtags": ["#KidsLearning", "#FunFacts", "#FoodFacts", "#KidsCartoon", "#Shorts", "#PurrFacts"]
      },
      "tiktok": {
        "caption": "Pizza was the first food to wear a flag 🍕🇮🇹",
        "hashtags": ["#KidsCartoon", "#FunFacts", "#FoodFacts", "#KidsLearning", "#PurrFacts"]
      },
      "instagram": {
        "caption": "Your kid will never look at pizza the same way 🍕 Purr reveals why the first Margherita matched the Italian flag.",
        "hashtags": ["#KidsAnimation", "#FunFacts", "#FoodFacts", "#LearnWithKids", "#PurrFacts"]
      }
    },
    "uk": {
      "youtube": {
        "title": "Чому піца схожа на прапор? 🍕",
        "description": "А ти знав, що першу піцу «Маргариту» зробили схожою на італійський прапор — червоний помідор, білий сир, зелений базилік? Пан Мурлик розповідає смачну історію. Нові факти щодня!",
        "hashtags": ["#НавчанняДляДітей", "#ЦікавіФакти", "#ФактиПроЇжу", "#МультикДляДітей", "#Shorts", "#PurrFacts"]
      },
      "tiktok": {
        "caption": "Піца — перша їжа, що «вдягнула» прапор 🍕🇮🇹",
        "hashtags": ["#МультикДляДітей", "#ЦікавіФакти", "#ФактиПроЇжу", "#НавчанняДляДітей", "#PurrFacts"]
      },
      "instagram": {
        "caption": "Твоя дитина більше ніколи не дивитиметься на піцу так само 🍕 Пан Мурлик пояснює, чому перша «Маргарита» була кольорів італійського прапора.",
        "hashtags": ["#МультфільмДляДітей", "#ЦікавіФакти", "#ФактиПроЇжу", "#ВчимосяГраючись", "#PurrFacts"]
      }
    },
    "zh": {
      "youtube": {
        "title": "為甚麼披薩像國旗？🍕",
        "description": "你知道嗎？第一個瑪格麗特披薩的顏色，正好配合意大利國旗——紅色番茄、白色起司、綠色羅勒！噗嚕貓同你講一個美味的小故事。每日一個新知識！",
        "hashtags": ["#兒童教育", "#冷知識", "#食物趣聞", "#卡通兒童", "#Shorts", "#PurrFacts"]
      },
      "tiktok": {
        "caption": "披薩是第一個「穿上國旗」的食物 🍕🇮🇹",
        "hashtags": ["#卡通兒童", "#冷知識", "#食物趣聞", "#兒童教育", "#PurrFacts"]
      },
      "instagram": {
        "caption": "看完這集，小朋友會用全新角度看披薩 🍕 噗嚕貓告訴你，第一個瑪格麗特披薩為何跟意大利國旗一樣。",
        "hashtags": ["#兒童動畫", "#冷知識", "#食物趣聞", "#親子學習", "#PurrFacts"]
      }
    },
    "fr": {
      "youtube": {
        "title": "Pourquoi la pizza ressemble à un drapeau ? 🍕",
        "description": "Savais-tu que la toute première pizza Margherita a été créée aux couleurs du drapeau italien — tomate rouge, mozzarella blanche, basilic vert ? Purr te raconte une savoureuse histoire. Un nouveau fait chaque jour !",
        "hashtags": ["#ApprendreEnSamusant", "#LeSaviezVous", "#FaitsCulinaires", "#DessinAnimé", "#Shorts", "#PurrFacts"]
      },
      "tiktok": {
        "caption": "La pizza, premier plat à porter un drapeau 🍕🇮🇹",
        "hashtags": ["#DessinAnimé", "#LeSaviezVous", "#FaitsCulinaires", "#ApprendrePourEnfants", "#PurrFacts"]
      },
      "instagram": {
        "caption": "Ton enfant ne regardera plus jamais une pizza pareil 🍕 Purr explique pourquoi la première Margherita avait les couleurs du drapeau italien.",
        "hashtags": ["#DessinAniméEnfant", "#LeSaviezVous", "#FaitsCulinaires", "#ApprendreEnFamille", "#PurrFacts"]
      }
    }
  }
}
```

---

## 14. Open decisions to confirm

1. **File granularity** — one `captions.json` per episode (assumed) vs one per language video.
   Affects §2 and §8 only.
2. **Chinese variant** — the `zh` block above uses Taiwan-leaning Mandarin terms (e.g. 起司).
   If the channel locks to HK Cantonese, the skill writes that variant instead; the contract
   is identical either way.
3. **Filename language code** — confirm the `_en/_uk/_zh/_fr` suffix convention (§8) matches
   how your renders are actually named, so the scanner can link them.

None of these change the schema — only how files are located and which Chinese is written.
