"""Compile the project's PO catalogs using only Python's standard library.

Run from any directory. No GNU gettext installation is needed on Windows.
The readable PO is authoritative; commit its matching MO when committing later.
"""
import argparse
import ast
from pathlib import Path
import re
import struct


def compile_catalog(path):
    messages = {}
    entry = {}
    current = None

    def flush():
        if "msgid" not in entry:
            return
        key = entry["msgid"]
        if "msgctxt" in entry:
            key = entry["msgctxt"] + "\x04" + key
        if "msgid_plural" in entry:
            key += "\x00" + entry["msgid_plural"]
            indexes = sorted(int(k[7:-1]) for k in entry if k.startswith("msgstr["))
            if indexes != list(range(len(indexes))) or not indexes:
                raise ValueError("Incomplete plural translation")
            value = "\x00".join(entry[f"msgstr[{i}]"] for i in indexes)
        else:
            value = entry.get("msgstr", "")
        if not value:
            raise ValueError("Empty translation: " + key)
        if key in messages:
            raise ValueError("Duplicate translation: " + key)
        messages[key.encode("utf-8")] = value.encode("utf-8")

    for line in path.read_text(encoding="utf-8").splitlines() + [""]:
        if not line.strip():
            flush()
            entry, current = {}, None
        elif line.startswith("#"):
            if line.startswith("#,") and "fuzzy" in [flag.strip() for flag in line[2:].split(",")]:
                raise ValueError("Resolve fuzzy translations before compiling")
        elif line.startswith('"'):
            if current is None:
                raise ValueError("Unexpected continued string")
            entry[current] += ast.literal_eval(line)
        else:
            match = re.fullmatch(r'(msgctxt|msgid_plural|msgid|msgstr(?:\[\d+\])?)\s+(".*")', line)
            if not match:
                raise ValueError("Unsupported PO syntax: " + line)
            current, literal = match.groups()
            entry[current] = ast.literal_eval(literal)
    items = sorted(messages.items())
    count = len(items)
    id_start = 28 + count * 16
    ids = b"".join(key + b"\0" for key, _ in items)
    value_start = id_start + len(ids)
    values = b"".join(value + b"\0" for _, value in items)
    id_table, value_table = [], []
    for key, value in items:
        id_table.extend([len(key), id_start])
        value_table.extend([len(value), value_start])
        id_start += len(key) + 1
        value_start += len(value) + 1
    return (struct.pack("<7I", 0x950412DE, 0, count, 28, 28 + count * 8, 0, 0)
            + struct.pack(f"<{count * 2}I", *id_table)
            + struct.pack(f"<{count * 2}I", *value_table) + ids + values)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify compiled catalogs without changing files.")
    args = parser.parse_args()
    for path in sorted((Path(__file__).resolve().parents[1] / "locale").glob("*/LC_MESSAGES/*.po")):
        data = compile_catalog(path)
        target = path.with_suffix(".mo")
        if args.check:
            if not target.exists() or target.read_bytes() != data:
                raise SystemExit(f"Recompile translations: {path}")
        else:
            target.write_bytes(data)
        print(f"{'Checked' if args.check else 'Compiled'} {path.parent.parent.name}/{path.stem}")


if __name__ == "__main__":
    main()
