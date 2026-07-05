from sqlalchemy.orm import Session

from app.models import Tag


def normalize_tag_name(tag_name: str) -> str:
    return tag_name.strip().casefold()


def normalize_tag_names(tag_names: list[str]) -> list[str]:
    normalized_names = []
    seen_names = set()

    for tag_name in tag_names:
        normalized_name = normalize_tag_name(tag_name)

        if normalized_name in seen_names:
            continue

        seen_names.add(normalized_name)
        normalized_names.append(normalized_name)

    return normalized_names


def get_or_create_tags(db: Session, tag_names: list[str]) -> list[Tag]:
    normalized_names = normalize_tag_names(tag_names)

    if not normalized_names:
        return []

    existing_tags = (
        db.query(Tag)
        .filter(Tag.name.in_(normalized_names))
        .order_by(Tag.name)
        .all()
    )
    existing_tags_by_name = {tag.name: tag for tag in existing_tags}
    new_tags = [
        Tag(name=tag_name)
        for tag_name in normalized_names
        if tag_name not in existing_tags_by_name
    ]

    db.add_all(new_tags)

    return sorted(
        [*existing_tags, *new_tags],
        key=lambda tag: tag.name,
    )
