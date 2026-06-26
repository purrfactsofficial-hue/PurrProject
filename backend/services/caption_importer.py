import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
from sqlalchemy.orm import Session

from database import Caption

_SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "captions.schema.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))

_LANGS = ["en", "uk", "zh", "fr"]
_PLATFORMS = ["youtube", "tiktok", "instagram"]


@dataclass
class ImportResult:
    imported: int = 0
    skipped_manual: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def import_captions(
    episode_folder: str,
    video_id: int,
    db: Session,
    force: bool = False,
) -> ImportResult:
    result = ImportResult()
    folder = Path(episode_folder)
    captions_file = folder / "captions.json"

    if not captions_file.exists():
        result.errors.append(
            f"No captions.json in {folder.name}. "
            "Run /purrfacts-scenario for this episode, then Import."
        )
        return result

    raw = captions_file.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        result.errors.append(
            "captions.json has a UTF-8 BOM. Save the file as UTF-8 without BOM and re-import."
        )
        return result

    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        result.errors.append(
            f"captions.json won't parse — line {exc.lineno}: {exc.msg}. Fix and re-import."
        )
        return result

    try:
        jsonschema.validate(data, _SCHEMA)
    except jsonschema.ValidationError as exc:
        path = "/".join(str(p) for p in exc.absolute_path)
        result.errors.append(_schema_error_message(exc, path, data))
        return result
    except jsonschema.SchemaError as exc:
        result.errors.append(f"Internal schema error: {exc.message}")
        return result

    custom_errors = _custom_checks(data)
    if custom_errors:
        result.errors.extend(custom_errors)
        return result

    result.warnings.extend(_custom_warnings(data))

    rows_to_write = _build_rows(data, video_id)
    _upsert_rows(rows_to_write, db, result, force)
    db.commit()
    return result


def _schema_error_message(exc: jsonschema.ValidationError, path: str, data: dict) -> str:
    schema_version = data.get("schema_version", "")
    if "schema_version" in exc.absolute_path or exc.validator == "const":
        return (
            f"captions.json is version {schema_version}; "
            "this platform reads 1.x. Update the skill or the platform."
        )
    if path:
        return f"`{path}`: {exc.message}"
    return exc.message


def _custom_checks(data: dict) -> list[str]:
    errors = []
    langs = data.get("languages", {})
    for lang in _LANGS:
        if lang not in langs:
            errors.append(
                f"captions.json is missing the `{lang}` block. Add it and re-import."
            )
            continue
        for platform in _PLATFORMS:
            if platform not in langs[lang]:
                errors.append(f"`{lang}` has no `{platform}` block.")
                continue
            block = langs[lang][platform]
            if platform == "instagram":
                count = len(block.get("hashtags", []))
                if count != 5:
                    errors.append(
                        f"`{lang}/instagram` has {count} hashtags; Instagram requires exactly 5."
                    )
            if platform == "youtube":
                title = block.get("title", "")
                if len(title) > 100:
                    errors.append(
                        f"`{lang}/youtube` title is {len(title)} chars (max 100)."
                    )
    return errors


def _custom_warnings(data: dict) -> list[str]:
    warnings = []
    langs = data.get("languages", {})
    for lang in _LANGS:
        for platform in _PLATFORMS:
            block = langs.get(lang, {}).get(platform, {})
            hashtags = block.get("hashtags", [])
            if "#PurrFacts" not in hashtags:
                warnings.append(f"`{lang}/{platform}` is missing #PurrFacts.")
            if platform == "youtube" and "#Shorts" not in hashtags:
                warnings.append(f"`{lang}/youtube` is missing #Shorts.")
    return warnings


def _build_rows(data: dict, video_id: int) -> list[dict]:
    rows = []
    for lang in _LANGS:
        lang_block = data["languages"][lang]
        for platform in _PLATFORMS:
            block = lang_block[platform]
            if platform == "youtube":
                title = block["title"]
                caption = block["description"]
            else:
                title = None
                caption = block["caption"]
            hashtags = " ".join(block["hashtags"])
            rows.append({
                "video_id": video_id,
                "language": lang,
                "platform": platform,
                "title": title,
                "caption": caption,
                "hashtags": hashtags,
            })
    return rows


def _upsert_rows(rows: list[dict], db: Session, result: ImportResult, force: bool) -> None:
    now = datetime.now(timezone.utc)
    for r in rows:
        existing = (
            db.query(Caption)
            .filter_by(video_id=r["video_id"], language=r["language"], platform=r["platform"])
            .first()
        )
        if existing is None:
            db.add(Caption(
                video_id=r["video_id"],
                language=r["language"],
                platform=r["platform"],
                title=r["title"],
                caption=r["caption"],
                hashtags=r["hashtags"],
                source="skill",
                updated_at=now,
            ))
            result.imported += 1
        elif existing.source == "manual" and not force:
            result.skipped_manual += 1
        else:
            existing.title = r["title"]
            existing.caption = r["caption"]
            existing.hashtags = r["hashtags"]
            existing.source = "skill"
            existing.updated_at = now
            result.imported += 1
