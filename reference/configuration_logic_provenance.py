"""Render reviewed assertions in the existing Configuration Logic evidence fields."""
import re
from urllib.parse import urlsplit

from django.core.management.base import CommandError

SOURCE_ID = re.compile(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+", re.ASCII)
EVIDENCE_HASH = re.compile(r"sha256:[0-9a-f]{64}", re.ASCII)


def readable_source_id(value):
    return isinstance(value, str) and SOURCE_ID.fullmatch(value) is not None


def source_descriptor(year, title, *, organization=None, url=None, reviewed=None):
    """Describe the document independently of its acquisition and verification."""
    if isinstance(reviewed, str) and reviewed.strip():
        return reviewed.strip()
    title = title or "Source description unavailable"
    manufacturer = organization or ""
    if manufacturer and not re.search(rf"\b{re.escape(manufacturer)}\b", title, re.IGNORECASE):
        match = re.match(r"^(20\d{2}(?:[–-]20\d{2})?)\s+", title)
        title = (f"{match[1]} {manufacturer} {title[match.end():]}" if match
                 else f"{manufacturer} {title}")
    if not re.search(r"\b20\d{2}\b", title):
        title = f"{year} {title}"
    if url and re.search(r"\.pdf(?:\.\d+)?/?$", urlsplit(url).path, re.IGNORECASE) and not title.endswith("PDF"):
        title += " PDF"
    return title


def register_source_alias(registry, alias, identity, descriptor):
    """Pin a readable alias to the publisher, title, locator and edition."""
    prior_identity, descriptors = registry.setdefault(alias, (identity, set()))
    if prior_identity != identity:
        raise CommandError(f"Conflicting Source References identity for Evidence ID {alias}.")
    if descriptor:
        descriptors.add(descriptor)


def consolidate_source_rows(rows, registry):
    """Emit one row per verified alias while retaining each year's evidence notes."""
    groups, ordered = {}, []
    for row in rows:
        alias = row[6]
        if alias not in registry:
            ordered.append(row)
        else:
            if alias not in groups:
                groups[alias] = []
                ordered.append(alias)
            groups[alias].append(row)
    result = []
    for item in ordered:
        if not isinstance(item, str):
            result.append(item)
            continue
        first, *other_rows = groups[item]
        if not other_rows:
            result.append(first)
            continue
        (organization, title, url, _), descriptors = registry[item]
        years = sorted({row[0] for row in groups[item]})
        scope = (f"{years[0]}–{years[-1]}" if len(years) > 1 and years == list(range(years[0], years[-1] + 1))
                 else ", ".join(map(str, years)))
        descriptor = source_descriptor(scope, title, organization=organization, url=url,
                                       reviewed=next(iter(descriptors)) if len(descriptors) == 1 else None)
        notes = dict.fromkeys(
            f"MY{year}{f' (reviewed {reviewed})' if reviewed else ''}: {note or ''}".rstrip()
            for year, _, _, _, reviewed, _, _, _, note in groups[item]
        )
        if len(descriptors) > 1:
            notes[f"Reviewed descriptors: {' / '.join(sorted(descriptors))}"] = None
        result.append((*first[:5], descriptor, item, first[7], " | ".join(notes)))
    return result


def provenance(citations, source_ids, *, lineage=None, gap=None):
    """Use declared assertion-to-source links and combine assertions sharing a locator."""
    grouped = {}
    if not isinstance(citations, (list, tuple)):
        citations = ()
        gap = gap or "Unusable manufacturer citation metadata"
    for citation in citations:
        try:
            label, source, locator = (citation[key].strip() for key in ("assertion", "source_id", "locator"))
            if (not label or not locator or not readable_source_id(source) or source not in source_ids
                    or any(";" in value or "\n" in value or "\r" in value for value in (label, locator))):
                raise ValueError
        except (KeyError, AttributeError, TypeError, ValueError):
            gap = gap or "Unresolved manufacturer citation"
            continue
        labels = grouped.setdefault((source, locator), {})
        labels[label] = None
    parts = [f"{'/'.join(labels)}: {source} {locator}" for (source, locator), labels in grouped.items()]
    if gap or not parts:
        parts.append(f"Evidence gap: {gap or 'Manufacturer assertion citations unavailable'}")
    if lineage:
        parts.append(f"Lineage: {lineage}")
    return "; ".join(parts)
