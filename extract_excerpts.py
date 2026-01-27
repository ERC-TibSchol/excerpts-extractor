"""
This script processes TEI XML files to extract excerpts and their metadata
"""

import argparse
import logging
import glob
import os
from datetime import datetime as dt

import pandas as pd
from lxml import etree
from tqdm import tqdm

ns = {"tei": "http://www.tei-c.org/ns/1.0"}


def compute_location_for_seg(seg):
    """Compute a human-readable location string for a <seg> element.

    The function finds a suitable starting <lb> (prefer text-before-lb heuristic,
    then first descendant <lb>, then the nearest preceding <lb>) and the last
    <lb> inside the segment to produce values like '1a1 - 1a3' or a single
    location value when both are equal.
    """
    lb = _first_lb_child_before_content(seg)

    # Detect whether there is any non-whitespace text before the first
    # internal <lb> inside this <seg>. If so, prefer the preceding <lb>
    # as the start location (even if the seg contains an internal <lb>).
    def has_text_before_internal_lb(elem):
        texts = []
        for node in elem.iter():
            if isinstance(node.tag, str) and node.tag.endswith("lb"):
                break
            if node.text:
                texts.append(node.text)
            if node.tail:
                texts.append(node.tail)
        return "".join(texts).strip() != ""

    text_before_internal_lb = has_text_before_internal_lb(seg)
    # If there is text before the first internal <lb> (including inline
    # content inside child elements), prefer the nearest preceding <lb> as
    # the start location. Also prefer preceding <lb> when the first
    # meaningful child is structural (milestone/pb/note) and
    # _first_lb_child_before_content returned a following <lb>.
    if text_before_internal_lb and lb is not None:
        previous_lbs = seg.xpath("preceding::tei:lb[1]", namespaces=ns)
        lb = previous_lbs[0] if previous_lbs else lb

    if lb is None:
        # If the segment starts with non-whitespace text, the starting location
        # is likely the nearest preceding <lb> (the line before the seg tag).
        # Also prefer the preceding <lb> when the first element child is a
        # structural marker (milestone/pb/note) because the line-break is
        # usually placed before the <seg> tag in such cases.
        # If there is any text before the first internal <lb>, prefer the
        # preceding <lb>.
        if text_before_internal_lb:
            previous_lbs = seg.xpath("preceding::tei:lb[1]", namespaces=ns)
            lb = previous_lbs[0] if previous_lbs else None
        else:
            first_lbs = seg.xpath(".//tei:lb[1]", namespaces=ns)
            if first_lbs:
                lb = first_lbs[0]
            else:
                previous_lbs = seg.xpath("preceding::tei:lb[1]", namespaces=ns)
                lb = previous_lbs[0] if previous_lbs else None

    lb_n = lb.attrib.get("n") if lb is not None else ""
    last_lb = seg.xpath('.//tei:lb[last()]', namespaces=ns)
    last_lb_n = last_lb[-1].attrib.get('n') if last_lb else ""

    if not last_lb_n and not lb_n:
        return ""
    if not lb_n:
        return last_lb_n
    if not last_lb_n:
        return lb_n
    if lb_n != last_lb_n:
        return f"{lb_n} - {last_lb_n}"
    return lb_n




def _first_lb_child_before_content(element):
    def text_before_first_lb(elem):
        texts = []
        for node in elem.iter():
            if isinstance(node.tag, str) and node.tag.endswith("lb"):
                break
            if node.text:
                texts.append(node.text)
            if node.tail:
                texts.append(node.tail)

        return "".join(texts).strip()

    if text_before_first_lb(element):
        # there is text before lb
        return None
    try:
        for elem in element:
            if isinstance(elem, etree._Comment) or isinstance(
                elem, etree._ProcessingInstruction
            ):
                continue
            elif elem.tag and (
                elem.tag.endswith("}pb")
                or elem.tag.endswith("}note")
                or elem.tag.endswith("}milestone")
            ):
                continue
            elif elem.tag.endswith("}lb"):
                return elem
            else:
                return None
    except Exception as e:
        logging.error("Error processing element: %s", elem.tag)
        logging.error(etree.tostring(elem))
        logging.error(repr(e))
        raise


def process_tei_files(tei_repo):
    excerpts = []

    for tei_filename in tqdm(tei_repo, total=len(tei_repo)):
        try:
            tree = etree.parse(tei_filename)
        except Exception:
            print("Failed to load ", tei_filename)
            continue

        tibschol_refs = tree.xpath('//tei:idno[@type="TibSchol"]/text()', namespaces=ns)
        zotero_refs = tree.xpath('//tei:idno[@type="Zotero"]/text()', namespaces=ns)
        seg_elements = tree.xpath('//tei:seg[@type="excerpt"]', namespaces=ns)

        for seg in seg_elements:
            lb_text = ""
            xml_id = seg.attrib.get("{http://www.w3.org/XML/1998/namespace}id")
            status = seg.attrib.get("status")
            # compute location using helper
            location = compute_location_for_seg(seg)

            if not location:
                logging.debug(
                    "No location for %s in file: %s",
                    xml_id,
                    os.path.basename(tei_filename),
                )

            seg_xml_minified = etree.tostring(
                seg,
                encoding="unicode",
                pretty_print=False,
                method="xml",
                with_tail=False,
            ).strip()
            excerpts.append(
                {
                    "source": os.path.basename(tei_filename),
                    "tibschol_refs": "\n".join(set(tibschol_refs)),
                    "zotero_refs": "\n".join(set(zotero_refs)),
                    "xml_id": xml_id,
                    "status": status,
                    "location": location,
                    "xml_content": f"<TEI xmlns='http://www.tei-c.org/ns/1.0'>{seg_xml_minified}</TEI>",
                }
            )

    df = pd.DataFrame(excerpts).fillna("")
    out_file = "data/excerpts.csv"
    df.to_csv(out_file, index=False)
    print(f"Excerpts written to {out_file}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process TEI XML files for excerpts.")
    parser.add_argument(
        "tei_repo_glob", help="Glob pattern for TEI XML files (e.g., '/path/to/*.xml')"
    )
    args = parser.parse_args()

    tei_repo = glob.glob(args.tei_repo_glob)
    process_tei_files(tei_repo)
