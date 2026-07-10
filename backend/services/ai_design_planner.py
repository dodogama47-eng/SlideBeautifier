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
- subtitle content should use subtitle_candidate if available.
- body explanation should use body_candidate slots.
- short labels should use label_candidate slots only for short phrases.
- decorative_candidate slots must not be used.
- Do not use ellipsis such as "..." or "…".
- Return ONLY valid JSON.
"""

        user_prompt = f"""
CONTENT SLIDES:

{json.dumps(compact_content, ensure_ascii=False, indent=2)}

SLIDE LIBRARY:

{json.dumps(compact_library, ensure_ascii=False, indent=2)}

Return JSON with this exact structure:

{{
  "schema": "slidebeautifier_native_fill_plan.v2",
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
          "role": "title | subtitle | body | label",
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
- You may reuse the same source_slide, but do NOT use the same source_slide repeatedly unless it is clearly the best fit.
- Do not blindly follow template slide order.
- Choose a source slide whose slot structure fits the content.
- For each slide, compare all template pages and choose the best fit.
- Same content type can use different source_slide templates.
- Similar page types may still use different source_slide templates.
- Match the number of content blocks to the number of usable body slots.
- If content has only 1-2 body points, choose a simple template with fewer body slots.
- If content has 3-5 body points, choose a template with multiple body/card slots.
- Do not choose a template with many visible empty cards if there is not enough content to fill them.
- Prefer layouts where title, subtitle, and body are visually separated.
- Do not put subtitle and body into the same slot.
- Use title_candidate for title.
- Use subtitle_candidate for short secondary explanation.
- Use body_candidate for paragraph/bullet explanation.
- Use label_candidate only for short words or short phrases.
- Avoid using label_candidate for body sentences.
- Keep text shorter than capacity_chars.
- For body text, use short complete lines separated by newlines.
- Do not include page numbers like 1/11, 2/11.
- Do not put long Chinese sentences into label_candidate slots.
- Never output ellipsis such as "..." or "…".
"""

        raw = self._chat_json(system_prompt, user_prompt)
        parsed = self._parse_json(raw)

        return self._normalize_fill_plan(
            plan=parsed,
            content_slides=content_slides,
            slide_library=slide_library
        )

    def repair_fill_plan(
        self,
        content_slides: list[dict],
        slide_library: dict,
        fill_plan: dict,
        check_report: dict
    ) -> dict:
        compact_content = self._compact_content_slides(content_slides)
        compact_library = self._compact_slide_library(slide_library)

        system_prompt = """
You are a PowerPoint fill_plan repair engine.

You receive:
- content_slides
- slide_library
- current fill_plan
- check_report with warnings/errors

Your job:
Return a corrected fill_plan.

Repair rules:
- Fix all errors.
- Reduce all warnings as much as possible.
- You may change source_slide.
- You may change slot_id.
- You may shorten text while preserving meaning.
- You may split text across multiple body_candidate slots.
- Do not use decorative_candidate slots.
- Do not use label_candidate for long body content.
- Use only slot_id values from the selected source_slide.
- Do not invent new content.
- Do not output ellipsis such as "..." or "…".
- Return ONLY valid JSON.
"""

        user_prompt = f"""
CONTENT SLIDES:

{json.dumps(compact_content, ensure_ascii=False, indent=2)}

SLIDE LIBRARY:

{json.dumps(compact_library, ensure_ascii=False, indent=2)}

CURRENT FILL PLAN:

{json.dumps(fill_plan, ensure_ascii=False, indent=2)}

CHECK REPORT:

{json.dumps(check_report, ensure_ascii=False, indent=2)}

Return corrected JSON with this exact structure:

{{
  "schema": "slidebeautifier_native_fill_plan.v2",
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
          "role": "title | subtitle | body | label",
          "text": "replacement text"
        }}
      ]
    }}
  ]
}}

Repair strategy:
- If text exceeds capacity, shorten it as a complete sentence.
- If slot role is wrong, choose a better slot.
- If selected source_slide has poor slots, choose a different source_slide.
- If title/body are overlapping visually, use another template page with more body_candidate slots.
- If the selected template leaves many visible empty cards, choose a simpler source_slide.
- If many slides use the same source_slide, diversify template choice while keeping layout fit.
- If text is too long, rewrite it as a shorter complete sentence, not with ellipsis.
- Do not use "..." or "…".
- If a slide has only a few points, do not use a three-card template.
- Preserve all important factual points from content_slides.
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
            "schema": "slidebeautifier_native_fill_plan.v2",
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
            temperature=0.12,
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
            "schema": "slidebeautifier_native_fill_plan.v2",
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

        valid_slots = self._valid_slots_for_source(
            slide_library=slide_library,
            source_slide=source_slide
        )

        valid_slot_ids = set(valid_slots.keys())
        raw_replacements = ai_slide.get("replacements", [])

        if not isinstance(raw_replacements, list):
            raw_replacements = []

        replacements = []
        used_slot_ids = set()

        for replacement in raw_replacements:
            if not isinstance(replacement, dict):
                continue

            slot_id = str(replacement.get("slot_id", "")).strip()
            role = str(replacement.get("role", "")).strip().lower()
            text = str(replacement.get("text", "")).strip()

            if role not in ["title", "subtitle", "body", "label"]:
                role = self._infer_replacement_role(
                    slot=valid_slots.get(slot_id)
                )

            if not slot_id or not text:
                continue

            if slot_id not in valid_slot_ids:
                continue

            if slot_id in used_slot_ids:
                continue

            slot = valid_slots.get(slot_id)

            if slot and slot.get("role") == "decorative_candidate":
                continue

            used_slot_ids.add(slot_id)

            replacements.append(
                {
                    "slot_id": slot_id,
                    "role": role,
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
            "page_index": page_index,
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

        subtitle_slots = [
            slot for slot in slots
            if slot.get("role") == "subtitle_candidate"
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
            slot = title_slots[0]
            replacements.append(
                {
                    "slot_id": slot["slot_id"],
                    "role": "title",
                    "text": self._shorten(title, slot.get("capacity_chars", 50))
                }
            )

        body_lines = bullets

        if body_lines and subtitle_slots:
            slot = subtitle_slots[0]
            first_line = body_lines[0]
            replacements.append(
                {
                    "slot_id": slot["slot_id"],
                    "role": "subtitle",
                    "text": self._shorten(first_line, slot.get("capacity_chars", 40))
                }
            )
            body_lines = body_lines[1:]

        available_body_slots = body_slots or label_slots

        if body_lines and available_body_slots:
            groups = self._split_lines_for_slots(
                lines=body_lines,
                slot_count=len(available_body_slots)
            )

            for slot, group in zip(available_body_slots, groups):
                if not group:
                    continue

                capacity = slot.get("capacity_chars", 80)
                role = "body" if slot.get("role") == "body_candidate" else "label"

                replacements.append(
                    {
                        "slot_id": slot["slot_id"],
                        "role": role,
                        "text": "\n".join(
                            self._shorten(line, max(12, capacity // max(1, len(group))))
                            for line in group
                        )
                    }
                )

        return {
            "page_index": page_index,
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
        bullets = content_slide.get("bullets", [])

        if not isinstance(bullets, list):
            bullets = []

        bullet_count = len(bullets)
        has_number = any(char.isdigit() for char in raw_text)
        has_compare = any(word in raw_text for word in ["compare", "versus", "对比", "比较", "不同"])
        has_process = any(word in raw_text for word in ["step", "process", "流程", "步骤", "阶段"])
        is_summary = any(word in raw_text for word in ["summary", "conclusion", "总结", "结论"])

        scored = []

        for slide in slides:
            source_slide = int(slide.get("slide_index", 1))
            slots = slide.get("slots", [])

            title_count = len([s for s in slots if s.get("role") == "title_candidate"])
            subtitle_count = len([s for s in slots if s.get("role") == "subtitle_candidate"])
            body_count = len([s for s in slots if s.get("role") == "body_candidate"])
            label_count = len([s for s in slots if s.get("role") == "label_candidate"])

            score = 0

            if title_count:
                score += 4

            score += body_count * 8
            score += subtitle_count * 2
            score += label_count

            if bullet_count >= 4 and body_count >= 2:
                score += 12

            if bullet_count >= 6 and body_count >= 3:
                score += 16

            if bullet_count <= 2 and body_count >= 3:
                score -= 10

            if bullet_count <= 1 and body_count >= 2:
                score -= 8

            if has_number and body_count >= 2:
                score += 8

            if has_compare and body_count >= 2:
                score += 10

            if has_process and body_count >= 3:
                score += 10

            if is_summary and body_count <= 2:
                score += 8

            score -= abs(source_slide - ((page_index % max(1, len(slides))) + 1)) * 0.3

            scored.append(
                {
                    "source_slide": source_slide,
                    "score": score,
                    "body_count": body_count
                }
            )

        scored = sorted(
            scored,
            key=lambda item: item["score"],
            reverse=True
        )

        if not scored:
            return 1

        top_candidates = scored[:min(3, len(scored))]
        selected = top_candidates[page_index % len(top_candidates)]

        return selected["source_slide"]

    def _slide_fill_score(
        self,
        slide: dict,
        bullet_count: int = 0
    ) -> int:
        score = 0
        body_count = 0

        for slot in slide.get("slots", []):
            role = slot.get("role")

            if role == "title_candidate":
                score += 4
            elif role == "subtitle_candidate":
                score += 2
            elif role == "body_candidate":
                score += 7
                body_count += 1
            elif role == "label_candidate":
                score += 1

        if bullet_count >= 3 and body_count >= 2:
            score += 8

        if bullet_count >= 5 and body_count >= 3:
            score += 10

        return score

    def _compact_content_slides(self, slides: list[dict]) -> list[dict]:
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

    def _compact_slide_library(self, slide_library: dict) -> dict:
        compact_slides = []

        for slide in slide_library.get("slides", []):
            compact_slots = []

            for slot in slide.get("slots", []):
                role = slot.get("role")

                if role == "decorative_candidate":
                    continue

                compact_slots.append(
                    {
                        "slot_id": slot.get("slot_id"),
                        "role": role,
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

    def _library_slides_by_index(self, slide_library: dict) -> dict[int, dict]:
        result = {}

        for slide in slide_library.get("slides", []):
            try:
                result[int(slide.get("slide_index"))] = slide
            except Exception:
                pass

        return result

    def _valid_slots_for_source(
        self,
        slide_library: dict,
        source_slide: int
    ) -> dict[str, dict]:
        slide = self._library_slides_by_index(slide_library).get(source_slide)

        if slide is None:
            return {}

        result = {}

        for slot in slide.get("slots", []):
            if slot.get("role") == "decorative_candidate":
                continue

            slot_id = slot.get("slot_id")

            if slot_id:
                result[str(slot_id)] = slot

        return result

    def _infer_replacement_role(self, slot: dict | None) -> str:
        if not slot:
            return "body"

        role = slot.get("role")

        if role == "title_candidate":
            return "title"

        if role == "subtitle_candidate":
            return "subtitle"

        if role == "label_candidate":
            return "label"

        return "body"

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

        cut_points = ["。", "，", "；", ";", ",", "."]
        safe_limit = max(12, max_chars)

        candidate = text[:safe_limit]

        best_cut = -1

        for mark in cut_points:
            pos = candidate.rfind(mark)

            if pos > best_cut:
                best_cut = pos

        if best_cut >= 8:
            return candidate[:best_cut + 1].strip()

        return candidate.strip()