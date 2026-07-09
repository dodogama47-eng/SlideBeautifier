import json
import os
import re
import math
from typing import Any

from openai import OpenAI


class AIDesignPlanner:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError("OPENAI_API_KEY not found")

        self.client = OpenAI(api_key=api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    def generate_fill_plan(
        self,
        content_slides: list[dict],
        slide_library: dict
    ) -> dict:
        compact_content = self._compact_content_slides(content_slides)
        compact_library = self._compact_slide_library(slide_library)

        system_prompt = """
You are a native PowerPoint template-fill planner.

You receive:
1. content_slides: the true content source.
2. slide_library: reusable PowerPoint template slides.

Your output is not a design drawing.
Your output is a fill_plan that selects template slides and replaces existing text slots.

Critical rules:
- Do not invent facts.
- Do not copy old template wording.
- Do not create x/y coordinates.
- Do not create new text boxes.
- Use only existing slot_id values from the selected source_slide.
- Preserve the same number and order of content slides.
- Match content function to slot role.
- title content should use title_candidate slots.
- body explanation should use body_candidate slots.
- short labels should use label_candidate slots.
- decorative_candidate slots should not be used for body content.
- Return ONLY valid JSON.
"""

        user_prompt = f"""
CONTENT SLIDES:

{json.dumps(compact_content, ensure_ascii=False, indent=2)}

SLIDE LIBRARY:

{json.dumps(compact_library, ensure_ascii=False, indent=2)}

Return JSON with this exact structure:

{{
  "schema": "slidebeautifier_native_fill_plan.v1",
  "status": "confirmed",
  "slides": [
    {{
      "page_index": 0,
      "source_slide": 1,
      "purpose": "cover | chapter | content | comparison | data | process | ending",
      "layout_rationale": {{
        "layout_pattern": "string",
        "why_fit": "string",
        "risk": "string"
      }},
      "replacements": [
        {{
          "slot_id": "s01_sh2",
          "text": "replacement text"
        }}
      ]
    }}
  ]
}}

Planning rules:
- page_index is 0-based index of content slide.
- source_slide is 1-based slide_index from slide_library.
- Each content slide must produce exactly one output slide.
- You may reuse the same source_slide many times.
- Do not blindly follow template slide order.
- Use a source slide whose slot structure fits the content.
- Use title_candidate for title.
- Use body_candidate for paragraph/bullet explanation.
- Use label_candidate only for short words or short phrases.
- Keep text shorter than slot capacity_chars.
- For body text, use short lines separated by newlines.
- Do not include page numbers like 1/11, 2/11.
"""

        raw = self._chat_json(system_prompt, user_prompt)
        parsed = self._parse_json(raw)

        return self._normalize_fill_plan(
            plan=parsed,
            content_slides=content_slides,
            slide_library=slide_library
        )

    def build_fallback_fill_plan(
        self,
        content_slides: list[dict],
        slide_library: dict
    ) -> dict:
        slides = []

        for index, content_slide in enumerate(content_slides):
            slides.append(
                self._fallback_plan_slide(
                    page_index=index,
                    content_slide=content_slide,
                    slide_library=slide_library
                )
            )

        return {
            "schema": "slidebeautifier_native_fill_plan.v1",
            "status": "confirmed",
            "slides": slides
        }

    def _chat_json(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.15,
            response_format={
                "type": "json_object"
            }
        )

        return response.choices[0].message.content or ""

    def _parse_json(self, raw: str) -> Any:
        cleaned = raw.strip()

        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```json", "", cleaned, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r"^```", "", cleaned).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)

            if match:
                return json.loads(match.group(0))

            raise ValueError(f"AI did not return valid JSON: {raw}")

    def _normalize_fill_plan(
        self,
        plan: Any,
        content_slides: list[dict],
        slide_library: dict
    ) -> dict:
        if not isinstance(plan, dict):
            raise ValueError("fill_plan must be a JSON object")

        ai_slides = plan.get("slides", [])

        if not isinstance(ai_slides, list):
            ai_slides = []

        ai_by_page_index = {}

        for index, item in enumerate(ai_slides):
            if not isinstance(item, dict):
                continue

            try:
                page_index = int(item.get("page_index", index))
            except Exception:
                page_index = index

            ai_by_page_index[page_index] = item

        normalized_slides = []

        for page_index, content_slide in enumerate(content_slides):
            ai_slide = ai_by_page_index.get(page_index)

            if ai_slide is None:
                normalized_slides.append(
                    self._fallback_plan_slide(
                        page_index=page_index,
                        content_slide=content_slide,
                        slide_library=slide_library
                    )
                )
                continue

            normalized_slides.append(
                self._normalize_one_plan_slide(
                    page_index=page_index,
                    ai_slide=ai_slide,
                    content_slide=content_slide,
                    slide_library=slide_library
                )
            )

        return {
            "schema": "slidebeautifier_native_fill_plan.v1",
            "status": "confirmed",
            "slides": normalized_slides
        }

    def _normalize_one_plan_slide(
        self,
        page_index: int,
        ai_slide: dict,
        content_slide: dict,
        slide_library: dict
    ) -> dict:
        library_slides = self._library_slides_by_index(slide_library)

        try:
            source_slide = int(ai_slide.get("source_slide", 1))
        except Exception:
            source_slide = 1

        if source_slide not in library_slides:
            source_slide = self._choose_fallback_source_slide(
                page_index=page_index,
                content_slide=content_slide,
                slide_library=slide_library
            )

        valid_slot_ids = self._valid_slot_ids_for_source(
            slide_library=slide_library,
            source_slide=source_slide
        )

        raw_replacements = ai_slide.get("replacements", [])

        if not isinstance(raw_replacements, list):
            raw_replacements = []

        replacements = []
        used_slot_ids = set()

        for replacement in raw_replacements:
            if not isinstance(replacement, dict):
                continue

            slot_id = str(replacement.get("slot_id", "")).strip()
            text = str(replacement.get("text", "")).strip()

            if not slot_id or not text:
                continue

            if slot_id not in valid_slot_ids:
                continue

            if slot_id in used_slot_ids:
                continue

            used_slot_ids.add(slot_id)

            replacements.append(
                {
                    "slot_id": slot_id,
                    "text": text
                }
            )

        if not replacements:
            fallback = self._fallback_plan_slide(
                page_index=page_index,
                content_slide=content_slide,
                slide_library=slide_library,
                forced_source_slide=source_slide
            )

            replacements = fallback.get("replacements", [])

        layout_rationale = ai_slide.get("layout_rationale", {})

        if not isinstance(layout_rationale, dict):
            layout_rationale = {}

        return {
            "source_slide": source_slide,
            "purpose": str(ai_slide.get("purpose", "content")).strip() or "content",
            "layout_rationale": {
                "layout_pattern": str(layout_rationale.get("layout_pattern", "")).strip(),
                "why_fit": str(layout_rationale.get("why_fit", "")).strip(),
                "risk": str(layout_rationale.get("risk", "")).strip()
            },
            "replacements": replacements
        }

    def _fallback_plan_slide(
        self,
        page_index: int,
        content_slide: dict,
        slide_library: dict,
        forced_source_slide: int | None = None
    ) -> dict:
        if forced_source_slide is None:
            source_slide = self._choose_fallback_source_slide(
                page_index=page_index,
                content_slide=content_slide,
                slide_library=slide_library
            )
        else:
            source_slide = forced_source_slide

        library_slide = self._library_slides_by_index(slide_library).get(source_slide)

        if library_slide is None:
            raise ValueError("slide_library has no valid slides")

        slots = library_slide.get("slots", [])

        title_slots = [
            slot for slot in slots
            if slot.get("role") == "title_candidate"
        ]

        body_slots = [
            slot for slot in slots
            if slot.get("role") == "body_candidate"
        ]

        label_slots = [
            slot for slot in slots
            if slot.get("role") == "label_candidate"
        ]

        title = str(content_slide.get("title", f"Slide {page_index + 1}")).strip()
        bullets = content_slide.get("bullets", [])

        if not isinstance(bullets, list):
            bullets = []

        bullets = [
            str(item).strip()
            for item in bullets
            if item and str(item).strip()
        ]

        replacements = []

        if title and title_slots:
            replacements.append(
                {
                    "slot_id": title_slots[0]["slot_id"],
                    "text": self._shorten(title, title_slots[0].get("capacity_chars", 60))
                }
            )

        available_body_slots = body_slots or label_slots

        if bullets and available_body_slots:
            groups = self._split_lines_for_slots(
                lines=bullets,
                slot_count=len(available_body_slots)
            )

            for slot, group in zip(available_body_slots, groups):
                if not group:
                    continue

                capacity = slot.get("capacity_chars", 80)
                replacements.append(
                    {
                        "slot_id": slot["slot_id"],
                        "text": "\n".join(
                            self._shorten(line, max(20, capacity // max(1, len(group))))
                            for line in group
                        )
                    }
                )

        return {
            "source_slide": source_slide,
            "purpose": "content",
            "layout_rationale": {
                "layout_pattern": "fallback native slot fill",
                "why_fit": "Selected a source slide with available title/body slots.",
                "risk": "Fallback may be less accurate than AI plan."
            },
            "replacements": replacements
        }

    def _choose_fallback_source_slide(
        self,
        page_index: int,
        content_slide: dict,
        slide_library: dict
    ) -> int:
        slides = slide_library.get("slides", [])

        if not slides:
            raise ValueError("slide_library has no slides")

        raw_text = str(content_slide.get("raw_text", "")).lower()

        if page_index == 0:
            preferred = ["cover_candidate", "chapter_candidate", "content_candidate"]
        elif any(word in raw_text for word in ["summary", "conclusion", "总结", "结论"]):
            preferred = ["ending_candidate", "chapter_candidate", "content_candidate"]
        else:
            preferred = ["content_candidate", "chapter_candidate", "cover_candidate"]

        for page_type in preferred:
            candidates = [
                slide for slide in slides
                if slide.get("page_type") == page_type and slide.get("slots")
            ]

            if candidates:
                best = sorted(
                    candidates,
                    key=lambda slide: self._slide_fill_score(slide),
                    reverse=True
                )[0]

                return int(best.get("slide_index", 1))

        return int(slides[min(page_index, len(slides) - 1)].get("slide_index", 1))

    def _slide_fill_score(
        self,
        slide: dict
    ) -> int:
        score = 0

        for slot in slide.get("slots", []):
            role = slot.get("role")

            if role == "title_candidate":
                score += 3
            elif role == "body_candidate":
                score += 5
            elif role == "label_candidate":
                score += 1

        return score

    def _compact_content_slides(
        self,
        slides: list[dict]
    ) -> list[dict]:
        compact = []

        for slide in slides:
            bullets = slide.get("bullets", [])

            if not isinstance(bullets, list):
                bullets = []

            compact.append(
                {
                    "page_index": slide.get("page_index"),
                    "title": slide.get("title", ""),
                    "bullets": bullets[:12],
                    "raw_text": str(slide.get("raw_text", ""))[:2200],
                    "image_count": slide.get("image_count", 0),
                    "table_count": slide.get("table_count", 0)
                }
            )

        return compact

    def _compact_slide_library(
        self,
        slide_library: dict
    ) -> dict:
        compact_slides = []

        for slide in slide_library.get("slides", []):
            compact_slots = []

            for slot in slide.get("slots", []):
                if slot.get("role") == "decorative_candidate":
                    continue

                compact_slots.append(
                    {
                        "slot_id": slot.get("slot_id"),
                        "role": slot.get("role"),
                        "geometry": slot.get("geometry", {}),
                        "font_size_pt": slot.get("font_size_pt"),
                        "paragraph_count": slot.get("paragraph_count"),
                        "capacity_chars": slot.get("capacity_chars"),
                        "old_text_length": len(str(slot.get("text", "")))
                    }
                )

            compact_slides.append(
                {
                    "slide_index": slide.get("slide_index"),
                    "page_type": slide.get("page_type"),
                    "slot_count": len(compact_slots),
                    "slots": compact_slots
                }
            )

        return {
            "schema": slide_library.get("schema"),
            "slide_count": slide_library.get("slide_count"),
            "slides": compact_slides
        }

    def _library_slides_by_index(
        self,
        slide_library: dict
    ) -> dict[int, dict]:
        result = {}

        for slide in slide_library.get("slides", []):
            try:
                result[int(slide.get("slide_index"))] = slide
            except Exception:
                pass

        return result

    def _valid_slot_ids_for_source(
        self,
        slide_library: dict,
        source_slide: int
    ) -> set[str]:
        slide = self._library_slides_by_index(slide_library).get(source_slide)

        if slide is None:
            return set()

        result = set()

        for slot in slide.get("slots", []):
            if slot.get("role") == "decorative_candidate":
                continue

            slot_id = slot.get("slot_id")

            if slot_id:
                result.add(str(slot_id))

        return result

    def _split_lines_for_slots(
        self,
        lines: list[str],
        slot_count: int
    ) -> list[list[str]]:
        if slot_count <= 0:
            return []

        if not lines:
            return [[] for _ in range(slot_count)]

        slot_count = min(slot_count, len(lines))
        chunk_size = math.ceil(len(lines) / slot_count)

        groups = []

        for index in range(0, len(lines), chunk_size):
            groups.append(lines[index:index + chunk_size])

        return groups

    def _shorten(
        self,
        text: str,
        max_chars: int
    ) -> str:
        text = str(text).strip()

        if len(text) <= max_chars:
            return text

        return text[:max_chars - 1].rstrip() + "…"