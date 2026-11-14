from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def unfold_lines(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    unfolded = []
    for line in text.split("\n"):
        if line[:1] in (" ", "\t") and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    return unfolded


def split_cards(lines):
    cards = []
    current = None
    for line in lines:
        token = line.strip().upper()
        if token == "BEGIN:VCARD":
            current = []
        elif token == "END:VCARD":
            if current is not None:
                cards.append((True, current))
                current = None
        elif current is not None and line.strip():
            current.append(line)
    if current is not None:
        cards.append((False, current))
    return cards


def parse_property(line):
    head, _, value = line.partition(":")
    name = head.split(";", 1)[0].strip().upper()
    return name, value


def rev_datetime(rev):
    if not rev:
        return None
    raw = rev.strip()
    try:
        body = raw[:-1] if raw.endswith("Z") else raw
        parsed = datetime.fromisoformat(body)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        pass
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S", "%Y%m%d"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def build_contact(lines):
    contact = {}
    for line in lines:
        name, value = parse_property(line)
        if name == "EMAIL" and "email" not in contact:
            contact["email"] = value.strip().lower()
        elif name == "FN" and "fn" not in contact:
            contact["fn"] = value
        elif name == "TEL" and "tel" not in contact:
            contact["tel"] = value
        elif name == "REV" and "rev" not in contact:
            contact["rev"] = value
    return contact


def is_newer(incoming, existing):
    incoming_rev = rev_datetime(incoming.get("rev"))
    existing_rev = rev_datetime(existing.get("rev"))
    if incoming_rev is None:
        return False
    if existing_rev is None:
        return True
    return incoming_rev > existing_rev


def run_ingest(args):
    cards_dir = Path(args.cards)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    merged = {}
    quarantined = []

    for path in sorted(cards_dir.rglob("*.vcf")):
        text = path.read_text(encoding="utf-8", errors="replace")
        source = str(path.relative_to(cards_dir))
        for complete, card_lines in split_cards(unfold_lines(text)):
            if not complete:
                quarantined.append({"source": source, "reason": "truncated"})
                continue
            contact = build_contact(card_lines)
            email = contact.get("email")
            if not email:
                continue
            if email not in merged or is_newer(contact, merged[email]):
                merged[email] = contact

    contacts = []
    for email in sorted(merged):
        record = {"email": email, "fn": merged[email].get("fn", "")}
        if "tel" in merged[email]:
            record["tel"] = merged[email]["tel"]
        if "rev" in merged[email]:
            record["rev"] = merged[email]["rev"]
        contacts.append(record)

    with (out_dir / "contacts.jsonl").open("w", encoding="utf-8") as handle:
        for record in contacts:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    with (out_dir / "quarantine.jsonl").open("w", encoding="utf-8") as handle:
        for record in quarantined:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    report = {
        "contact_count": len(contacts),
        "quarantine_count": len(quarantined),
    }
    (out_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"ingested {len(contacts)} contacts, {len(quarantined)} quarantined")
    return 0
