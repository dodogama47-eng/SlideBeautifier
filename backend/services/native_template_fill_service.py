from pathlib import Path
from copy import deepcopy
import json
import re
import unicodedata
import zipfile
from xml.etree import ElementTree as ET


P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"

NS = {
    "p": P_NS,
    "a": A_NS,
    "r": R_NS,
    "rel": REL_NS,
    "ct": CT_NS,
}

SLIDE_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"


def qn(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


class NativeTemplateFillService:
    """
    SlideBeautifier Native Template Fill Engine.

    自己重写，不复制第三方包。

    思路：
    1. analyze_reference(): 把 reference.pptx 分析成 slide_library
    2. AI 生成 fill_plan: source_slide + replacements(slot_id, text, role)
    3. check_fill_plan(): 检查 slot、role、容量、文本长度
    4. apply_fill_plan(): 克隆原 slide XML，替换原文本框内容

    重点：
    - 不新建 textbox
    - 不靠坐标乱放
    - 直接替换原 PowerPoint shape 里的文字
    - 继承原字体、字号、颜色、位置、图层
    """

    def analyze_reference(
        self,
        reference_path: Path,
        output_json_path: Path | None = None
    ) -> dict:
        reference_path = Path(reference_path)

        with zipfile.ZipFile(reference_path, "r") as zf:
            entries = {
                item.filename: zf.read(item.filename)
                for item in zf.infolist()
                if not item.is_dir()
            }

        presentation_root = ET.fromstring(entries["ppt/presentation.xml"])
        rels_root = ET.fromstring(entries["ppt/_rels/presentation.xml.rels"])

        slide_refs = self._parse_slide_refs(
            presentation_root=presentation_root,
            rels_root=rels_root
        )

        slides = []

        for slide_number, slide_part in slide_refs:
            slide_xml = entries[slide_part]
            slide_root = ET.fromstring(slide_xml)

            slots = self._analyze_slide_slots(
                slide_root=slide_root,
                slide_number=slide_number
            )

            slide_text = "\n".join(
                slot.get("text", "")
                for slot in slots
                if slot.get("text")
            )

            slides.append(
                {
                    "slide_index": slide_number,
                    "part_name": slide_part,
                    "page_type": self._classify_page_type(
                        index=slide_number,
                        total=len(slide_refs),
                        text=slide_text,
                        slots=slots
                    ),
                    "text_summary": slide_text[:500],
                    "slots": slots,
                    "slot_count": len(slots)
                }
            )

        library = {
            "schema": "slidebeautifier_native_template_library.v2",
            "source_pptx": str(reference_path),
            "slide_count": len(slides),
            "slides": slides
        }

        if output_json_path is not None:
            self._write_json(output_json_path, library)

        return library

    def save_fill_plan(
        self,
        fill_plan: dict,
        output_json_path: Path
    ) -> None:
        self._write_json(output_json_path, fill_plan)

    def apply_fill_plan(
        self,
        reference_path: Path,
        fill_plan: dict,
        result_path: Path,
        slide_library: dict | None = None
    ) -> None:
        reference_path = Path(reference_path)
        result_path = Path(result_path)
        result_path.parent.mkdir(parents=True, exist_ok=True)

        if slide_library is None:
            slide_library = self.analyze_reference(reference_path)

        with zipfile.ZipFile(reference_path, "r") as zf:
            entries = {
                item.filename: zf.read(item.filename)
                for item in zf.infolist()
                if not item.is_dir()
            }

        presentation_root = ET.fromstring(entries["ppt/presentation.xml"])
        rels_root = ET.fromstring(entries["ppt/_rels/presentation.xml.rels"])
        content_types_root = ET.fromstring(entries["[Content_Types].xml"])

        source_slide_refs = dict(
            self._parse_slide_refs(
                presentation_root=presentation_root,
                rels_root=rels_root
            )
        )

        self._clear_presentation_slide_list(
            presentation_root=presentation_root,
            rels_root=rels_root
        )

        max_slide_number = self._max_existing_slide_number(entries)
        next_slide_number = max_slide_number + 1
        next_slide_id = self._max_existing_slide_id(presentation_root) + 1
        next_rid_number = self._max_existing_rid_number(rels_root) + 1

        output_slides = fill_plan.get("slides", [])

        if not isinstance(output_slides, list) or not output_slides:
            raise ValueError("fill_plan.slides must be a non-empty list")

        for output_index, plan_slide in enumerate(output_slides):
            source_slide = self._safe_int(plan_slide.get("source_slide"), default=1)

            if source_slide not in source_slide_refs:
                source_slide = 1

            source_slide_part = source_slide_refs[source_slide]
            source_rels_part = self._slide_rels_part(source_slide_part)

            new_slide_number = next_slide_number + output_index
            new_slide_part = f"ppt/slides/slide{new_slide_number}.xml"
            new_rels_part = f"ppt/slides/_rels/slide{new_slide_number}.xml.rels"
            new_rid = f"rId{next_rid_number + output_index}"

            slide_root = ET.fromstring(entries[source_slide_part])

            self._clear_replaceable_text(
                slide_root=slide_root,
                source_slide=source_slide,
                slide_library=slide_library
            )

            replacements = plan_slide.get("replacements", [])

            if not isinstance(replacements, list):
                replacements = []

            self._apply_replacements_to_slide(
                slide_root=slide_root,
                source_slide=source_slide,
                replacements=replacements
            )

            entries[new_slide_part] = self._xml_bytes(slide_root)

            if source_rels_part in entries:
                entries[new_rels_part] = entries[source_rels_part]
            else:
                entries[new_rels_part] = self._empty_rels_xml()

            self._add_slide_to_presentation(
                presentation_root=presentation_root,
                rels_root=rels_root,
                slide_id=next_slide_id + output_index,
                rel_id=new_rid,
                slide_target=f"slides/slide{new_slide_number}.xml"
            )

            self._ensure_slide_content_type(
                content_types_root=content_types_root,
                slide_part=f"/{new_slide_part}"
            )

        entries["ppt/presentation.xml"] = self._xml_bytes(presentation_root)
        entries["ppt/_rels/presentation.xml.rels"] = self._xml_bytes(rels_root)
        entries["[Content_Types].xml"] = self._xml_bytes(content_types_root)

        with zipfile.ZipFile(result_path, "w", compression=zipfile.ZIP_DEFLATED) as out:
            for name, data in entries.items():
                out.writestr(name, data)

    def check_fill_plan(
        self,
        slide_library: dict,
        fill_plan: dict,
        output_json_path: Path | None = None
    ) -> dict:
        warnings = []
        errors = []

        slides_by_index = {
            int(slide.get("slide_index")): slide
            for slide in slide_library.get("slides", [])
            if slide.get("slide_index") is not None
        }

        for output_index, plan_slide in enumerate(fill_plan.get("slides", []), start=1):
            source_slide = self._safe_int(plan_slide.get("source_slide"), default=None)

            if source_slide is None:
                errors.append(
                    {
                        "output_slide": output_index,
                        "message": "source_slide missing or invalid"
                    }
                )
                continue

            library_slide = slides_by_index.get(source_slide)

            if library_slide is None:
                errors.append(
                    {
                        "output_slide": output_index,
                        "source_slide": source_slide,
                        "message": "source_slide not found in slide_library"
                    }
                )
                continue

            slots_by_id = {
                slot["slot_id"]: slot
                for slot in library_slide.get("slots", [])
                if slot.get("slot_id")
            }

            used_slot_ids = set()

            replacements = plan_slide.get("replacements", [])

            if not isinstance(replacements, list):
                errors.append(
                    {
                        "output_slide": output_index,
                        "source_slide": source_slide,
                        "message": "replacements must be a list"
                    }
                )
                continue

            for replacement_index, replacement in enumerate(replacements, start=1):
                slot_id = replacement.get("slot_id")
                text = str(replacement.get("text", "")).strip()
                replacement_role = str(replacement.get("role", "")).strip()

                if not slot_id:
                    errors.append(
                        {
                            "output_slide": output_index,
                            "replacement": replacement_index,
                            "message": "slot_id missing"
                        }
                    )
                    continue

                if slot_id in used_slot_ids:
                    errors.append(
                        {
                            "output_slide": output_index,
                            "slot_id": slot_id,
                            "message": "duplicate replacement for same slot_id"
                        }
                    )
                    continue

                used_slot_ids.add(slot_id)

                slot = slots_by_id.get(slot_id)

                if slot is None:
                    errors.append(
                        {
                            "output_slide": output_index,
                            "source_slide": source_slide,
                            "slot_id": slot_id,
                            "message": "slot_id not found on selected source_slide"
                        }
                    )
                    continue

                if not text:
                    warnings.append(
                        {
                            "output_slide": output_index,
                            "source_slide": source_slide,
                            "slot_id": slot_id,
                            "message": "empty replacement text"
                        }
                    )
                    continue

                slot_role = slot.get("role")
                capacity = int(slot.get("capacity_chars", 80))
                visual_width = self._visual_width(text)

                if slot_role in ["decorative_candidate", "noise_candidate"]:
                    errors.append(
                        {
                            "output_slide": output_index,
                            "source_slide": source_slide,
                            "slot_id": slot_id,
                            "slot_role": slot_role,
                            "message": "replacement uses decorative/noise slot"
                        }
                    )
                    continue

                if replacement_role == "title" and slot_role not in ["title_candidate", "body_candidate"]:
                    warnings.append(
                        {
                            "output_slide": output_index,
                            "source_slide": source_slide,
                            "slot_id": slot_id,
                            "slot_role": slot_role,
                            "replacement_role": replacement_role,
                            "message": "title text is not placed in a title/body slot"
                        }
                    )

                if replacement_role in ["body", "card", "step"] and slot_role == "label_candidate":
                    warnings.append(
                        {
                            "output_slide": output_index,
                            "source_slide": source_slide,
                            "slot_id": slot_id,
                            "slot_role": slot_role,
                            "replacement_role": replacement_role,
                            "message": "body/card text placed in label slot"
                        }
                    )

                if slot_role == "label_candidate" and visual_width > max(12, capacity * 0.8):
                    warnings.append(
                        {
                            "output_slide": output_index,
                            "source_slide": source_slide,
                            "slot_id": slot_id,
                            "slot_role": slot_role,
                            "visual_width": visual_width,
                            "capacity_chars": capacity,
                            "message": "label slot text too long"
                        }
                    )

                if visual_width > capacity * 1.15:
                    warnings.append(
                        {
                            "output_slide": output_index,
                            "source_slide": source_slide,
                            "slot_id": slot_id,
                            "slot_role": slot_role,
                            "visual_width": visual_width,
                            "capacity_chars": capacity,
                            "message": "text exceeds estimated slot capacity"
                        }
                    )

                line_count = len([line for line in text.splitlines() if line.strip()])
                original_paragraph_count = int(slot.get("paragraph_count", 1) or 1)

                if line_count > max(original_paragraph_count + 2, 4):
                    warnings.append(
                        {
                            "output_slide": output_index,
                            "source_slide": source_slide,
                            "slot_id": slot_id,
                            "slot_role": slot_role,
                            "line_count": line_count,
                            "original_paragraph_count": original_paragraph_count,
                            "message": "too many lines for original slot"
                        }
                    )

            body_slots = [
                slot for slot in library_slide.get("slots", [])
                if slot.get("role") == "body_candidate"
            ]

            if len(replacements) >= 3 and len(body_slots) == 0:
                warnings.append(
                    {
                        "output_slide": output_index,
                        "source_slide": source_slide,
                        "message": "selected template has many replacements but no body_candidate slots"
                    }
                )

        report = {
            "summary": {
                "ok": max(0, len(fill_plan.get("slides", [])) - len(errors)),
                "warn": len(warnings),
                "error": len(errors)
            },
            "warnings": warnings,
            "errors": errors
        }

        if output_json_path is not None:
            self._write_json(output_json_path, report)

        return report

    def needs_repair(self, check_report: dict) -> bool:
        summary = check_report.get("summary", {})
        return int(summary.get("warn", 0)) > 0 or int(summary.get("error", 0)) > 0

    def _parse_slide_refs(
        self,
        presentation_root: ET.Element,
        rels_root: ET.Element
    ) -> list[tuple[int, str]]:
        rel_map = {}

        for rel in rels_root.findall(qn(REL_NS, "Relationship")):
            rel_id = rel.attrib.get("Id")
            rel_type = rel.attrib.get("Type")
            target = rel.attrib.get("Target", "")

            if rel_type == SLIDE_REL_TYPE and rel_id:
                rel_map[rel_id] = self._normalize_slide_target(target)

        result = []

        sld_id_list = presentation_root.find("p:sldIdLst", NS)

        if sld_id_list is None:
            return result

        for index, sld_id in enumerate(sld_id_list.findall("p:sldId", NS), start=1):
            rel_id = sld_id.attrib.get(qn(R_NS, "id"))
            slide_part = rel_map.get(rel_id)

            if slide_part:
                result.append((index, slide_part))

        return result

    def _normalize_slide_target(self, target: str) -> str:
        target = target.replace("\\", "/")

        if target.startswith("/"):
            target = target[1:]

        if target.startswith("ppt/"):
            return target

        if target.startswith("slides/"):
            return f"ppt/{target}"

        return f"ppt/{target}"

    def _analyze_slide_slots(
        self,
        slide_root: ET.Element,
        slide_number: int
    ) -> list[dict]:
        slots = []

        for order, shape in enumerate(slide_root.findall(".//p:sp", NS), start=1):
            tx_body = shape.find("p:txBody", NS)

            if tx_body is None:
                continue

            shape_id, shape_name = self._shape_identity(shape, order)
            text = self._shape_text(shape)
            geometry = self._shape_geometry(shape)
            font_size = self._font_size(shape)
            paragraph_count = len(self._paragraph_texts(shape))
            is_vertical = self._is_vertical_text(shape, geometry)

            role = self._guess_slot_role(
                order=order,
                shape_name=shape_name,
                text=text,
                geometry=geometry,
                font_size=font_size,
                paragraph_count=paragraph_count,
                is_vertical=is_vertical
            )

            if role == "noise_candidate":
                continue

            slots.append(
                {
                    "slot_id": f"s{slide_number:02d}_sh{shape_id}",
                    "shape_id": shape_id,
                    "shape_name": shape_name,
                    "role": role,
                    "text": text,
                    "paragraph_count": paragraph_count,
                    "geometry": geometry,
                    "font_size_pt": font_size,
                    "capacity_chars": self._estimate_capacity(
                        role=role,
                        geometry=geometry,
                        font_size=font_size,
                        paragraph_count=paragraph_count
                    ),
                    "is_vertical": is_vertical
                }
            )

        return slots

    def _shape_identity(
        self,
        shape: ET.Element,
        fallback_id: int
    ) -> tuple[int, str]:
        c_nv_pr = shape.find(".//p:cNvPr", NS)

        if c_nv_pr is None:
            return fallback_id, ""

        raw_id = c_nv_pr.attrib.get("id")
        name = c_nv_pr.attrib.get("name", "")

        try:
            shape_id = int(raw_id)
        except Exception:
            shape_id = fallback_id

        return shape_id, name

    def _shape_text(self, shape: ET.Element) -> str:
        lines = []

        for paragraph in shape.findall(".//a:p", NS):
            texts = []

            for text_node in paragraph.findall(".//a:t", NS):
                if text_node.text:
                    texts.append(text_node.text)

            line = "".join(texts).strip()

            if line:
                lines.append(line)

        return "\n".join(lines)

    def _paragraph_texts(self, shape: ET.Element) -> list[str]:
        result = []

        for paragraph in shape.findall(".//a:p", NS):
            texts = []

            for text_node in paragraph.findall(".//a:t", NS):
                if text_node.text:
                    texts.append(text_node.text)

            result.append("".join(texts).strip())

        return result

    def _shape_geometry(self, shape: ET.Element) -> dict:
        xfrm = shape.find(".//p:spPr/a:xfrm", NS)

        if xfrm is None:
            return {
                "x": 0,
                "y": 0,
                "width": 0,
                "height": 0
            }

        off = xfrm.find("a:off", NS)
        ext = xfrm.find("a:ext", NS)

        return {
            "x": self._safe_int(off.attrib.get("x"), 0) if off is not None else 0,
            "y": self._safe_int(off.attrib.get("y"), 0) if off is not None else 0,
            "width": self._safe_int(ext.attrib.get("cx"), 0) if ext is not None else 0,
            "height": self._safe_int(ext.attrib.get("cy"), 0) if ext is not None else 0
        }

    def _font_size(self, shape: ET.Element) -> float | None:
        sizes = []

        for node in shape.findall(".//a:rPr", NS) + shape.findall(".//a:defRPr", NS):
            raw_size = node.attrib.get("sz")

            if not raw_size:
                continue

            try:
                sizes.append(int(raw_size) / 100)
            except Exception:
                pass

        if not sizes:
            return None

        return max(sizes)

    def _is_vertical_text(
        self,
        shape: ET.Element,
        geometry: dict
    ) -> bool:
        body_pr = shape.find(".//a:bodyPr", NS)

        if body_pr is not None:
            vert = body_pr.attrib.get("vert", "")

            if vert:
                return True

        width = geometry.get("width", 0)
        height = geometry.get("height", 0)

        if width > 0 and height / width >= 2.2:
            return True

        return False

    def _guess_slot_role(
        self,
        order: int,
        shape_name: str,
        text: str,
        geometry: dict,
        font_size: float | None,
        paragraph_count: int,
        is_vertical: bool
    ) -> str:
        normalized_name = shape_name.lower()
        normalized_text = text.strip().lower()

        if self._is_noise_text(normalized_text):
            return "noise_candidate"

        if is_vertical:
            return "decorative_candidate"

        if "title" in normalized_name or "标题" in normalized_name:
            return "title_candidate"

        if "subtitle" in normalized_name or "副标题" in normalized_name:
            return "subtitle_candidate"

        x = geometry.get("x", 0)
        y = geometry.get("y", 0)
        width = geometry.get("width", 0)
        height = geometry.get("height", 0)

        area = width * height

        if order == 1 and len(text) <= 100:
            return "title_candidate"

        if font_size and font_size >= 26 and len(text) <= 120:
            return "title_candidate"

        if y < 1300000 and len(text) <= 120:
            return "title_candidate"

        if y < 2300000 and len(text) <= 140 and area < 2500000000000:
            return "subtitle_candidate"

        if paragraph_count >= 3 or len(text) >= 80:
            return "body_candidate"

        if width >= 2600000 and height >= 700000:
            return "body_candidate"

        if len(text) <= 40:
            return "label_candidate"

        return "body_candidate"

    def _is_noise_text(self, text: str) -> bool:
        if not text:
            return False

        if re.fullmatch(r"\d+\s*/\s*\d+", text):
            return True

        if re.fullmatch(r"[•\-\s]*\d+\s*/\s*\d+", text):
            return True

        if text in ["•", "-", "—", "_"]:
            return True

        return False

    def _estimate_capacity(
        self,
        role: str,
        geometry: dict,
        font_size: float | None,
        paragraph_count: int
    ) -> int:
        width = geometry.get("width", 0)
        height = geometry.get("height", 0)

        if font_size is None or font_size <= 0:
            if role == "title_candidate":
                font_size = 28
            elif role == "subtitle_candidate":
                font_size = 18
            elif role == "body_candidate":
                font_size = 16
            else:
                font_size = 14

        if width <= 0 or height <= 0:
            return 60

        line_height = font_size * 12700 * 1.25
        max_lines = max(1, int(height / max(line_height, 1)))
        chars_per_line = max(4, int(width / max(font_size * 7000, 1)))

        capacity = chars_per_line * max_lines

        if role == "title_candidate":
            capacity = int(capacity * 0.70)
        elif role == "subtitle_candidate":
            capacity = int(capacity * 0.75)
        elif role == "label_candidate":
            capacity = int(capacity * 0.50)

        return max(8, min(capacity, 300))

    def _classify_page_type(
        self,
        index: int,
        total: int,
        text: str,
        slots: list[dict]
    ) -> str:
        normalized = text.lower()

        if index == 1:
            return "cover_candidate"

        if index == total:
            return "ending_candidate"

        if any(word in normalized for word in ["agenda", "contents", "outline", "目录"]):
            return "toc_candidate"

        if any(word in normalized for word in ["thank", "thanks", "谢谢", "感谢"]):
            return "ending_candidate"

        body_count = len([slot for slot in slots if slot.get("role") == "body_candidate"])

        if body_count >= 2:
            return "content_candidate"

        if len(slots) <= 2 and len(text) <= 120:
            return "chapter_candidate"

        return "content_candidate"

    def _clear_replaceable_text(
        self,
        slide_root: ET.Element,
        source_slide: int,
        slide_library: dict
    ) -> None:
        slots_by_shape_id = {}

        for slide in slide_library.get("slides", []):
            if int(slide.get("slide_index", 0)) != source_slide:
                continue

            for slot in slide.get("slots", []):
                shape_id = self._safe_int(slot.get("shape_id"), default=-1)
                slots_by_shape_id[shape_id] = slot

        for order, shape in enumerate(slide_root.findall(".//p:sp", NS), start=1):
            shape_id, _shape_name = self._shape_identity(shape, order)
            slot = slots_by_shape_id.get(shape_id)

            if slot is None:
                continue

            role = slot.get("role")

            if role in ["decorative_candidate", "noise_candidate"]:
                continue

            self._set_shape_text(shape, "")

    def _apply_replacements_to_slide(
        self,
        slide_root: ET.Element,
        source_slide: int,
        replacements: list[dict]
    ) -> None:
        shapes_by_slot_id = {}

        for order, shape in enumerate(slide_root.findall(".//p:sp", NS), start=1):
            shape_id, _shape_name = self._shape_identity(shape, order)
            slot_id = f"s{source_slide:02d}_sh{shape_id}"
            shapes_by_slot_id[slot_id] = shape

        for replacement in replacements:
            slot_id = str(replacement.get("slot_id", "")).strip()
            text = str(replacement.get("text", "")).strip()

            if not slot_id or slot_id not in shapes_by_slot_id:
                continue

            self._set_shape_text(shapes_by_slot_id[slot_id], text)

    def _set_shape_text(
        self,
        shape: ET.Element,
        text: str
    ) -> None:
        tx_body = shape.find("p:txBody", NS)

        if tx_body is None:
            return

        lines = text.splitlines()

        if not lines:
            lines = [""]

        paragraphs = tx_body.findall("a:p", NS)

        if not paragraphs:
            paragraph = ET.SubElement(tx_body, qn(A_NS, "p"))
            paragraphs = [paragraph]

        first_paragraph_template = deepcopy(paragraphs[0])

        for paragraph in paragraphs:
            self._set_paragraph_text(paragraph, "")

        for index, line in enumerate(lines):
            if index < len(paragraphs):
                paragraph = paragraphs[index]
            else:
                paragraph = deepcopy(first_paragraph_template)
                tx_body.append(paragraph)

            self._set_paragraph_text(paragraph, line)

    def _set_paragraph_text(
        self,
        paragraph: ET.Element,
        text: str
    ) -> None:
        text_nodes = paragraph.findall(".//a:t", NS)

        if not text_nodes:
            run = paragraph.find("a:r", NS)

            if run is None:
                run = ET.SubElement(paragraph, qn(A_NS, "r"))

            text_node = run.find("a:t", NS)

            if text_node is None:
                text_node = ET.SubElement(run, qn(A_NS, "t"))

            text_nodes = [text_node]

        text_nodes[0].text = text

        for extra_node in text_nodes[1:]:
            extra_node.text = ""

    def _clear_presentation_slide_list(
        self,
        presentation_root: ET.Element,
        rels_root: ET.Element
    ) -> None:
        sld_id_list = presentation_root.find("p:sldIdLst", NS)

        if sld_id_list is None:
            sld_id_list = ET.SubElement(presentation_root, qn(P_NS, "sldIdLst"))

        for child in list(sld_id_list):
            sld_id_list.remove(child)

        for rel in list(rels_root.findall(qn(REL_NS, "Relationship"))):
            if rel.attrib.get("Type") == SLIDE_REL_TYPE:
                rels_root.remove(rel)

    def _add_slide_to_presentation(
        self,
        presentation_root: ET.Element,
        rels_root: ET.Element,
        slide_id: int,
        rel_id: str,
        slide_target: str
    ) -> None:
        sld_id_list = presentation_root.find("p:sldIdLst", NS)

        if sld_id_list is None:
            sld_id_list = ET.SubElement(presentation_root, qn(P_NS, "sldIdLst"))

        ET.SubElement(
            sld_id_list,
            qn(P_NS, "sldId"),
            {
                "id": str(slide_id),
                qn(R_NS, "id"): rel_id
            }
        )

        ET.SubElement(
            rels_root,
            qn(REL_NS, "Relationship"),
            {
                "Id": rel_id,
                "Type": SLIDE_REL_TYPE,
                "Target": slide_target
            }
        )

    def _ensure_slide_content_type(
        self,
        content_types_root: ET.Element,
        slide_part: str
    ) -> None:
        for child in content_types_root:
            if child.attrib.get("PartName") == slide_part:
                return

        ET.SubElement(
            content_types_root,
            qn(CT_NS, "Override"),
            {
                "PartName": slide_part,
                "ContentType": "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"
            }
        )

    def _max_existing_slide_number(self, entries: dict[str, bytes]) -> int:
        result = 0

        for name in entries.keys():
            match = re.fullmatch(r"ppt/slides/slide(\d+)\.xml", name)

            if match:
                result = max(result, int(match.group(1)))

        return result

    def _max_existing_slide_id(self, presentation_root: ET.Element) -> int:
        result = 255

        for node in presentation_root.findall(".//p:sldId", NS):
            try:
                result = max(result, int(node.attrib.get("id", 0)))
            except Exception:
                pass

        return result

    def _max_existing_rid_number(self, rels_root: ET.Element) -> int:
        result = 0

        for rel in rels_root.findall(qn(REL_NS, "Relationship")):
            rel_id = rel.attrib.get("Id", "")
            match = re.fullmatch(r"rId(\d+)", rel_id)

            if match:
                result = max(result, int(match.group(1)))

        return result

    def _slide_rels_part(self, slide_part: str) -> str:
        path = Path(slide_part)
        return f"{path.parent}/_rels/{path.name}.rels".replace("\\", "/")

    def _empty_rels_xml(self) -> bytes:
        root = ET.Element(qn(REL_NS, "Relationships"))
        return self._xml_bytes(root)

    def _xml_bytes(self, root: ET.Element) -> bytes:
        return ET.tostring(
            root,
            encoding="utf-8",
            xml_declaration=True
        )

    def _write_json(self, path: Path, data: dict) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2
            )

    def _visual_width(self, text: str) -> float:
        width = 0.0

        for char in "".join(text.split()):
            east_asian_width = unicodedata.east_asian_width(char)

            if east_asian_width in {"F", "W"}:
                width += 2.0
            elif east_asian_width == "A":
                width += 1.5
            else:
                width += 1.0

        return width

    def _safe_int(self, value, default=None):
        try:
            return int(value)
        except Exception:
            return default