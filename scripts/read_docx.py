"""Read-only DOCX text extractor using only the Python standard library.

Reads paragraphs and tables from ``word/document.xml`` inside a .docx
container and prints their text content to stdout as UTF-8, in document
order. Does not modify the input file or any other file.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from collections.abc import Iterator
from xml.etree import ElementTree

_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _paragraph_text(paragraph: ElementTree.Element) -> str:
    return "".join(node.text or "" for node in paragraph.iter(f"{_W_NS}t"))


def _iter_blocks(body: ElementTree.Element) -> Iterator[str]:
    for child in body:
        if child.tag == f"{_W_NS}p":
            yield _paragraph_text(child)
        elif child.tag == f"{_W_NS}tbl":
            for row in child.iter(f"{_W_NS}tr"):
                cells = [
                    "".join(_paragraph_text(p) for p in cell.iter(f"{_W_NS}p"))
                    for cell in row.iter(f"{_W_NS}tc")
                ]
                yield "\t".join(cells)


def extract_text(docx_path: str) -> str:
    """Return the text content of ``docx_path`` in document order."""
    with (
        zipfile.ZipFile(docx_path) as archive,
        archive.open("word/document.xml") as xml_file,
    ):
        tree = ElementTree.parse(xml_file)
    body = tree.getroot().find(f"{_W_NS}body")
    if body is None:
        return ""
    return "\n".join(_iter_blocks(body))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Path to the .docx file to read")
    args = parser.parse_args(argv)

    text = extract_text(args.path)
    sys.stdout.buffer.write(text.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
