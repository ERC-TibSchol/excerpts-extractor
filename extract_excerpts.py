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
            lb = _first_lb_child_before_content(seg)
            if lb is None:
                previous_lbs = seg.xpath("preceding::tei:lb[1]", namespaces=ns)
                lb = previous_lbs[0] if previous_lbs else None
                lb_text = (
                    etree.tostring(
                        lb,
                        encoding="unicode",
                        pretty_print=False,
                        method="xml",
                        with_tail=False,
                    ).strip()
                    if lb is not None
                    else ""
                )

            lb_n = lb.attrib.get("n") if lb is not None else ""
            last_lb = seg.xpath(".//tei:lb[last()]", namespaces=ns)
            last_lb_n = last_lb[-1].attrib.get("n") if last_lb else ""

            if not last_lb_n and not lb_n:
                location = ""
            elif not lb_n:
                location = last_lb_n
            elif not last_lb_n:
                location = lb_n
            elif lb_n != last_lb_n:
                location = f"{lb_n} - {last_lb_n}"
            else:
                location = lb_n

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
                    "xml_content": f"<TEI xmlns='http://www.tei-c.org/ns/1.0'>{lb_text}{seg_xml_minified}</TEI>",
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
