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
        content_inventory = self._build_content_inventory(content_slides)
        compact_library = self._compact_slide_library(slide_library)

        system_prompt = """
You are a native PowerPoint template-fill planner.

You do NOT rewrite text.
You do NOT summarize text.
You do NOT shorten text.
You do NOT add ellipsis.
You do NOT change meaning.
You only arrange existing content into existing PowerPoint template slots.

The user provides:
1. content_inventory:
   - immutable text blocks extracted from content.pptx
   - each block has content_id, role_hint, semantic_type, semantic_group, parent_content_id, text
   - text is the only source of truth

2. slide_library:
   - reusable PowerPoint template slides
   - each slide has existing text slots with slot_id, role, slot_level, group_id, group_order, parent_slot_id, usable_for

Your job:
- Choose the best source_slide for each content page.
- Assign existing content_ids to suitable slot_ids.
- Preserve content order.
- Preserve semantic relationships.
- Keep subordinate / explanatory / sequential content together when appropriate.
- Use visual hierarchy: parent_content_id should be placed under or near its parent content.
- Use slot group_id and parent_slot_id to keep related content visually together.
- Return ONLY valid JSON.
"""

        user_prompt = f"""
CONTENT INVENTORY.
These text blocks are immutable. You must not rewrite them.

{json.dumps(content_inventory, ensure_ascii=False, indent=2)}

SLIDE LIBRARY.

{json.dumps(compact_library, ensure_ascii=False, indent=2)}

Return JSON with this exact structure:

{{
  "schema": "slidebeautifier_native_fill_plan.strict.slot_hierarchy.v1",
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
      "placements": [
        {{
          "slot_id": "s01_sh2",
          "role": "title | subtitle | label | body",
          "content_ids": ["p0_title"]
        }}
      ]
    }}
  ]
}}

Hard rules:
- Do NOT output replacement text directly.
- Use content_ids only.
- Each content_id may be used at most once per page.
- Do not drop required content_ids.
- Do not invent content_ids.
- Do not change content text.
- Preserve the order of content_ids as much as possible.
- decorative_candidate and noise_candidate slots must not be used.
- title content should use title_candidate slots.
- subtitle or short summary content should use subtitle_candidate slots if available.
- label_candidate slots may be used only for short labels, keywords, numbers, or section tags.
- Do not put long body text into label_candidate slots.
- body/explanation/example/detail content should use body_candidate slots.
- Choose a source_slide that has enough suitable slots for the content.
- Similar content pages may use different source_slide templates.
- Avoid using the same source_slide repeatedly unless it is clearly the best fit.

Slot hierarchy rules:
- slot_level 0 is main title.
- slot_level 1 is subtitle, section heading, or short label.
- slot_level 2 is body content under a parent slot.
- If several slots share the same group_id, they belong to the same visual group.
- If a body slot has parent_slot_id, it should contain content that explains or belongs to that parent.
- Do not place unrelated content into the same group_id.
- Prefer using one visual group for one semantic group.
- If a segment has parent_content_id, place it in the same group_id as its parent when possible.
- Example/detail/result segments should be placed under or near their parent idea.

Content segmentation rules:
- content_inventory may contain sentence-level segments from the same original bullet.
- Segments sharing the same semantic_group belong to the same original bullet.
- If a segment has parent_content_id, it should be placed in the same visual group as its parent.
- Example/detail/result segments should be placed under or near their parent idea.
- Use label_candidate for the parent keyword only when the text is short.
- Use body_candidate for explanation/example/detail text.
"""

        raw = self._chat_json(system_prompt, user_prompt)
        parsed = self._parse_json(raw)

        return self._normalize_strict_plan(
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
        content_inventory = self._build_content_inventory(content_slides)
        compact_library = self._compact_slide_library(slide_library)

        system_prompt = """
You are a PowerPoint fill_plan repair engine.

You do NOT rewrite text.
You do NOT summarize text.
You do NOT shorten text.
You do NOT add ellipsis.
You only repair source_slide and slot_id assignment.

Your job:
- Fix slot errors.
- Reduce layout warnings by choosing better template slides or slots.
- Keep all original content unchanged.
- Use content_ids only.
- Return ONLY valid JSON.
"""

        user_prompt = f"""
CONTENT INVENTORY.
Immutable source text:

{json.dumps(content_inventory, ensure_ascii=False, indent=2)}

SLIDE LIBRARY:

{json.dumps(compact_library, ensure_ascii=False, indent=2)}

CURRENT FILL PLAN:

{json.dumps(fill_plan, ensure_ascii=False, indent=2)}

CHECK REPORT:

{json.dumps(check_report, ensure_ascii=False, indent=2)}

Return corrected JSON with this exact structure:

{{
  "schema": "slidebeautifier_native_fill_plan.strict.slot_hierarchy.v1",
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
      "placements": [
        {{
          "slot_id": "s01_sh2",
          "role": "title | subtitle | label | body",
          "content_ids": ["p0_title"]
        }}
      ]
    }}
  ]
}}

Repair rules:
- Do not output replacement text directly.
- Do not alter source text.
- Do not remove required content.
- If text is too long for a slot, choose a larger slot or a different source_slide.
- If one slide has many content blocks, choose a template with more body slots.
- If content is semantically connected, keep it together.
- If a template has many unused visible cards, choose a simpler source_slide.
- Do not use decorative_candidate or noise_candidate slots.
- Do not place long body content into label_candidate.
- Preserve page order.

Slot hierarchy rules:
- Use slot_level 0 for page title.
- Use slot_level 1 for subtitle / section heading / short label.
- Use slot_level 2 for body content.
- Keep semantically related content in the same group_id.
- Use parent_slot_id to understand which body slot belongs to which subtitle/section.
"""

        raw = self._chat_json(system_prompt, user_prompt)
        parsed = self._parse_json(raw)

        return self._normalize_strict_plan(
            plan=parsed,
            content_slides=content_slides,
            slide_library=slide_library
        )

    def generate_creative_fill_plan(
        self,
        content_slides: list[dict],
        slide_library: dict
    ) -> dict:
        compact_content = self._compact_content_slides(content_slides)
        compact_library = self._compact_slide_library(slide_library)

        system_prompt = """
You are a PowerPoint design-optimized content planner.

In this mode, you ARE allowed to rewrite, shorten, combine, and reorganize text
to make it fit better into the selected template.

But you must:
- Preserve the original meaning.
- Do not invent facts.
- Do not add unsupported information.
- Keep the key message of each slide.
- Make text concise and presentation-friendly.
- Choose suitable source_slide and slot_id values.
- Use slot hierarchy and visual group information.
- Return ONLY valid JSON.
"""

        user_prompt = f"""
CONTENT SLIDES:

{json.dumps(compact_content, ensure_ascii=False, indent=2)}

SLIDE LIBRARY:

{json.dumps(compact_library, ensure_ascii=False, indent=2)}

Return JSON with this exact structure:

{{
  "schema": "slidebeautifier_native_fill_plan.creative.slot_hierarchy.v1",
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
          "role": "title | subtitle | label | body",
          "text": "presentation-ready replacement text"
        }}
      ]
    }}
  ]
}}

Design rules:
- Each content slide must produce exactly one output slide.
- You may reuse source_slide, but avoid making every slide use the same template.
- Choose a template whose number of usable slots matches the content amount.
- If content has only 1-2 points, choose a simpler template.
- If content has 3-5 points, choose a multi-card or multi-body template.
- Avoid leaving many visible empty cards.
- Use title_candidate slots for titles.
- Use subtitle_candidate for short supporting statements.
- Use label_candidate only for very short labels, keywords, numbers, or section tags.
- Use body_candidate for explanations.
- Do not use decorative_candidate or noise_candidate slots.
- Keep text concise.
- Prefer short complete phrases over long paragraphs.
- Avoid ellipsis.
- Do not copy page numbers from the source.

Slot hierarchy rules:
- slot_level 0 is main title.
- slot_level 1 is subtitle, section heading, or short label.
- slot_level 2 is body content under a parent slot.
- If several slots share the same group_id, they belong to the same visual group.
- If a body slot has parent_slot_id, it should contain content that explains or belongs to that parent.
- Do not place unrelated content into the same group_id.
- Prefer using one visual group for one semantic group.
"""

        raw = self._chat_json(system_prompt, user_prompt)
        parsed = self._parse_json(raw)

        return self._normalize_creative_plan(
            plan=parsed,
            content_slides=content_slides,
            slide_library=slide_library
        )

    def repair_creative_fill_plan(
        self,
        content_slides: list[dict],
        slide_library: dict,
        fill_plan: dict,
        check_report: dict
    ) -> dict:
        compact_content = self._compact_content_slides(content_slides)
        compact_library = self._compact_slide_library(slide_library)

        system_prompt = """
You are a PowerPoint creative fill_plan repair engine.

You may rewrite, shorten, combine, and reorganize text to improve layout quality.

Your job:
- Fix slot errors.
- Reduce text overflow.
- Choose better source_slide if needed.
- Keep key meaning.
- Do not invent facts.
- Use slot hierarchy and visual group information.
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
  "schema": "slidebeautifier_native_fill_plan.creative.slot_hierarchy.v1",
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
          "role": "title | subtitle | label | body",
          "text": "presentation-ready replacement text"
        }}
      ]
    }}
  ]
}}

Repair rules:
- If text is too long, rewrite it into a shorter complete phrase.
- If a slot is too small, choose a larger slot or another source_slide.
- If there are many empty visible cards, choose a simpler source_slide.
- If every slide uses the same source_slide, diversify template choice.
- Do not use decorative_candidate or noise_candidate slots.
- Do not place body text into label_candidate.
- Preserve the key message of each content slide.
- Keep related content in the same group_id when possible.
"""

        raw = self._chat_json(system_prompt, user_prompt)
        parsed = self._parse_json(raw)

        return self._normalize_creative_plan(
            plan=parsed,
            content_slides=content_slides,
            slide_library=slide_library
        )

    def build_fallback_fill_plan(
        self,
        content_slides: list[dict],
        slide_library: dict,
        mode: str = "strict"
    ) -> dict:
        mode = str(mode or "strict").lower().strip()

        if mode not in ["strict", "creative"]:
            mode = "strict"

        slides = []

        for page_index, content_slide in enumerate(content_slides):
            if mode == "creative":
                slides.append(
                    self._fallback_creative_plan_slide(
                        page_index=page_index,
                        content_slide=content_slide,
                        slide_library=slide_library
                    )
                )
            else:
                slides.append(
                    self._fallback_strict_plan_slide(
                        page_index=page_index,
                        content_slide=content_slide,
                        slide_library=slide_library
                    )
                )

        return {
            "schema": f"slidebeautifier_native_fill_plan.{mode}.fallback.slot_hierarchy.v1",
            "status": "confirmed",
            "mode": mode,
            "slides": slides
        }

    def enforce_content_coverage(
        self,
        content_slides: list[dict],
        slide_library: dict,
        fill_plan: dict
    ) -> dict:
        if not isinstance(fill_plan, dict):
            fill_plan = {}

        original_plan_slides = fill_plan.get("slides", [])

        if not isinstance(original_plan_slides, list):
            original_plan_slides = []

        plan_by_page = {}

        for index, plan_slide in enumerate(original_plan_slides):
            if not isinstance(plan_slide, dict):
                continue

            try:
                page_index = int(plan_slide.get("page_index", index))
            except Exception:
                page_index = index

            plan_by_page[page_index] = plan_slide

        final_slides = []

        for page_index, content_slide in enumerate(content_slides):
            page_inventory = self._build_page_inventory(
                page_index=page_index,
                content_slide=content_slide
            )

            plan_slide = plan_by_page.get(page_index)

            if plan_slide is None:
                plan_slide = self._fallback_strict_plan_slide(
                    page_index=page_index,
                    content_slide=content_slide,
                    slide_library=slide_library
                )

            source_slide = self._safe_source_slide(
                ai_slide=plan_slide,
                page_index=page_index,
                content_slide=content_slide,
                slide_library=slide_library
            )

            valid_slots = self._valid_slots_for_source(
                slide_library=slide_library,
                source_slide=source_slide
            )

            if not valid_slots:
                valid_slots = self._valid_slots_for_source_relaxed(
                    slide_library=slide_library,
                    source_slide=source_slide
                )

            replacements = plan_slide.get("replacements", [])

            if not isinstance(replacements, list):
                replacements = []

            cleaned_replacements = []
            used_slot_ids = set()
            used_content_ids = set()

            for replacement in replacements:
                if not isinstance(replacement, dict):
                    continue

                slot_id = str(replacement.get("slot_id", "")).strip()

                if not slot_id:
                    continue

                if slot_id not in valid_slots:
                    continue

                if slot_id in used_slot_ids:
                    continue

                content_ids = replacement.get("content_ids", [])

                if isinstance(content_ids, str):
                    content_ids = [content_ids]

                if not isinstance(content_ids, list):
                    content_ids = []

                valid_content_ids = []

                for content_id in content_ids:
                    content_id = str(content_id).strip()

                    if not content_id:
                        continue

                    if content_id not in page_inventory:
                        continue

                    if content_id in used_content_ids:
                        continue

                    valid_content_ids.append(content_id)
                    used_content_ids.add(content_id)

                text = ""

                if valid_content_ids:
                    text = self._materialize_content_text(
                        content_ids=valid_content_ids,
                        page_inventory=page_inventory
                    )
                else:
                    text = str(replacement.get("text", "")).strip()

                if not text:
                    continue

                used_slot_ids.add(slot_id)

                cleaned_replacements.append(
                    {
                        "slot_id": slot_id,
                        "role": replacement.get(
                            "role",
                            self._infer_replacement_role(valid_slots.get(slot_id))
                        ),
                        "content_ids": valid_content_ids,
                        "text": text
                    }
                )

            missing_content_ids = [
                content_id
                for content_id, block in page_inventory.items()
                if block.get("required", True)
                and content_id not in used_content_ids
            ]

            if missing_content_ids:
                cleaned_replacements = self._append_missing_content(
                    replacements=cleaned_replacements,
                    missing_content_ids=missing_content_ids,
                    page_inventory=page_inventory,
                    valid_slots=valid_slots,
                    used_slot_ids=used_slot_ids
                )

            if not cleaned_replacements and page_inventory:
                cleaned_replacements = self._force_page_text_into_largest_slot(
                    page_inventory=page_inventory,
                    valid_slots=valid_slots
                )

            final_slides.append(
                {
                    "page_index": page_index,
                    "source_slide": source_slide,
                    "purpose": plan_slide.get("purpose", "content"),
                    "layout_rationale": plan_slide.get(
                        "layout_rationale",
                        {
                            "layout_pattern": "content coverage enforced",
                            "why_fit": "All original content is preserved before template fill.",
                            "risk": "Text may overflow if selected template has insufficient capacity."
                        }
                    ),
                    "replacements": cleaned_replacements
                }
            )

        return {
            "schema": "slidebeautifier_native_fill_plan.strict.coverage_enforced.slot_hierarchy.v1",
            "status": "confirmed",
            "mode": "strict",
            "slides": final_slides
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
            temperature=0.08,
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

    def _normalize_strict_plan(
        self,
        plan: Any,
        content_slides: list[dict],
        slide_library: dict
    ) -> dict:
        if not isinstance(plan, dict):
            raise ValueError("fill_plan must be a JSON object")

        inventory_by_page = self._content_inventory_by_page(content_slides)
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
                    self._fallback_strict_plan_slide(
                        page_index=page_index,
                        content_slide=content_slide,
                        slide_library=slide_library
                    )
                )
                continue

            normalized_slides.append(
                self._normalize_one_strict_slide(
                    page_index=page_index,
                    ai_slide=ai_slide,
                    content_slide=content_slide,
                    slide_library=slide_library,
                    page_inventory=inventory_by_page.get(page_index, {})
                )
            )

        return {
            "schema": "slidebeautifier_native_fill_plan.strict.slot_hierarchy.v1",
            "status": "confirmed",
            "mode": "strict",
            "slides": normalized_slides
        }

    def _normalize_one_strict_slide(
        self,
        page_index: int,
        ai_slide: dict,
        content_slide: dict,
        slide_library: dict,
        page_inventory: dict[str, dict]
    ) -> dict:
        source_slide = self._safe_source_slide(
            ai_slide=ai_slide,
            page_index=page_index,
            content_slide=content_slide,
            slide_library=slide_library
        )

        valid_slots = self._valid_slots_for_source(
            slide_library=slide_library,
            source_slide=source_slide
        )

        placements = ai_slide.get("placements")

        if placements is None:
            placements = ai_slide.get("replacements", [])

        if not isinstance(placements, list):
            placements = []

        used_slot_ids = set()
        used_content_ids = set()
        normalized_replacements = []

        for placement in placements:
            if not isinstance(placement, dict):
                continue

            slot_id = str(placement.get("slot_id", "")).strip()
            role = str(placement.get("role", "")).strip().lower()

            if role not in ["title", "subtitle", "label", "body"]:
                role = self._infer_replacement_role(valid_slots.get(slot_id))

            content_ids = placement.get("content_ids", [])

            if isinstance(content_ids, str):
                content_ids = [content_ids]

            if not isinstance(content_ids, list):
                content_ids = []

            content_ids = [
                str(content_id).strip()
                for content_id in content_ids
                if str(content_id).strip()
            ]

            if not slot_id:
                continue

            if slot_id not in valid_slots:
                continue

            if slot_id in used_slot_ids:
                continue

            slot = valid_slots.get(slot_id)

            if slot and slot.get("role") in ["decorative_candidate", "noise_candidate"]:
                continue

            valid_content_ids = []

            for content_id in content_ids:
                if content_id not in page_inventory:
                    continue

                if content_id in used_content_ids:
                    continue

                valid_content_ids.append(content_id)
                used_content_ids.add(content_id)

            if not valid_content_ids:
                continue

            text = self._materialize_content_text(
                content_ids=valid_content_ids,
                page_inventory=page_inventory
            )

            if not text:
                continue

            used_slot_ids.add(slot_id)

            normalized_replacements.append(
                {
                    "slot_id": slot_id,
                    "role": role,
                    "content_ids": valid_content_ids,
                    "text": text
                }
            )

        missing_content_ids = [
            content_id
            for content_id, block in page_inventory.items()
            if content_id not in used_content_ids
            and block.get("required", True)
        ]

        if missing_content_ids:
            normalized_replacements = self._append_missing_content(
                replacements=normalized_replacements,
                missing_content_ids=missing_content_ids,
                page_inventory=page_inventory,
                valid_slots=valid_slots,
                used_slot_ids=used_slot_ids
            )

        if not normalized_replacements:
            fallback = self._fallback_strict_plan_slide(
                page_index=page_index,
                content_slide=content_slide,
                slide_library=slide_library,
                forced_source_slide=source_slide
            )

            normalized_replacements = fallback.get("replacements", [])

        return {
            "page_index": page_index,
            "source_slide": source_slide,
            "purpose": str(ai_slide.get("purpose", "content")).strip() or "content",
            "layout_rationale": self._normalize_layout_rationale(ai_slide),
            "replacements": normalized_replacements
        }

    def _normalize_creative_plan(
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
                    self._fallback_creative_plan_slide(
                        page_index=page_index,
                        content_slide=content_slide,
                        slide_library=slide_library
                    )
                )
                continue

            normalized_slides.append(
                self._normalize_one_creative_slide(
                    page_index=page_index,
                    ai_slide=ai_slide,
                    content_slide=content_slide,
                    slide_library=slide_library
                )
            )

        return {
            "schema": "slidebeautifier_native_fill_plan.creative.slot_hierarchy.v1",
            "status": "confirmed",
            "mode": "creative",
            "slides": normalized_slides
        }

    def _normalize_one_creative_slide(
        self,
        page_index: int,
        ai_slide: dict,
        content_slide: dict,
        slide_library: dict
    ) -> dict:
        source_slide = self._safe_source_slide(
            ai_slide=ai_slide,
            page_index=page_index,
            content_slide=content_slide,
            slide_library=slide_library
        )

        valid_slots = self._valid_slots_for_source(
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
            role = str(replacement.get("role", "")).strip().lower()
            text = str(replacement.get("text", "")).strip()

            if role not in ["title", "subtitle", "label", "body"]:
                role = self._infer_replacement_role(valid_slots.get(slot_id))

            if not slot_id or not text:
                continue

            if slot_id not in valid_slots:
                continue

            if slot_id in used_slot_ids:
                continue

            slot = valid_slots.get(slot_id)

            if slot and slot.get("role") in ["decorative_candidate", "noise_candidate"]:
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
            fallback = self._fallback_creative_plan_slide(
                page_index=page_index,
                content_slide=content_slide,
                slide_library=slide_library,
                forced_source_slide=source_slide
            )

            replacements = fallback.get("replacements", [])

        return {
            "page_index": page_index,
            "source_slide": source_slide,
            "purpose": str(ai_slide.get("purpose", "content")).strip() or "content",
            "layout_rationale": self._normalize_layout_rationale(ai_slide),
            "replacements": replacements
        }

    def _fallback_strict_plan_slide(
        self,
        page_index: int,
        content_slide: dict,
        slide_library: dict,
        forced_source_slide: int | None = None
    ) -> dict:
        source_slide = forced_source_slide or self._choose_fallback_source_slide(
            page_index=page_index,
            content_slide=content_slide,
            slide_library=slide_library
        )

        library_slide = self._library_slides_by_index(slide_library).get(source_slide)

        if library_slide is None:
            raise ValueError("slide_library has no valid slides")

        page_inventory = self._build_page_inventory(
            page_index=page_index,
            content_slide=content_slide
        )

        slots = [
            slot for slot in library_slide.get("slots", [])
            if self._is_safe_slot(slot)
        ]

        title_slots = [slot for slot in slots if slot.get("role") == "title_candidate"]
        subtitle_slots = [slot for slot in slots if slot.get("role") == "subtitle_candidate"]
        label_slots = [slot for slot in slots if slot.get("role") == "label_candidate"]
        body_slots = [slot for slot in slots if slot.get("role") == "body_candidate"]

        replacements = []
        used_content_ids = set()

        title_block = page_inventory.get(f"p{page_index}_title")

        if title_block and title_slots:
            content_id = title_block["content_id"]
            used_content_ids.add(content_id)

            replacements.append(
                {
                    "slot_id": title_slots[0]["slot_id"],
                    "role": "title",
                    "content_ids": [content_id],
                    "text": title_block["text"]
                }
            )

        body_blocks = [
            block
            for content_id, block in page_inventory.items()
            if content_id not in used_content_ids
            and block.get("required", True)
        ]

        short_blocks = [
            block for block in body_blocks
            if len(block.get("text", "")) <= 18
        ]

        if short_blocks and label_slots:
            first_block = short_blocks[0]

            replacements.append(
                {
                    "slot_id": label_slots[0]["slot_id"],
                    "role": "label",
                    "content_ids": [first_block["content_id"]],
                    "text": first_block["text"]
                }
            )

            used_content_ids.add(first_block["content_id"])

        body_blocks = [
            block
            for block in body_blocks
            if block["content_id"] not in used_content_ids
        ]

        if body_blocks and subtitle_slots:
            first_block = body_blocks[0]

            if len(first_block.get("text", "")) <= 80:
                replacements.append(
                    {
                        "slot_id": subtitle_slots[0]["slot_id"],
                        "role": "subtitle",
                        "content_ids": [first_block["content_id"]],
                        "text": first_block["text"]
                    }
                )

                used_content_ids.add(first_block["content_id"])
                body_blocks = body_blocks[1:]

        if body_blocks and body_slots:
            groups = self._group_blocks_for_slots(
                blocks=body_blocks,
                slot_count=len(body_slots)
            )

            for slot, group in zip(body_slots, groups):
                if not group:
                    continue

                content_ids = [block["content_id"] for block in group]

                replacements.append(
                    {
                        "slot_id": slot["slot_id"],
                        "role": "body",
                        "content_ids": content_ids,
                        "text": "\n".join(block["text"] for block in group)
                    }
                )

                for content_id in content_ids:
                    used_content_ids.add(content_id)

        missing_ids = [
            content_id
            for content_id, block in page_inventory.items()
            if content_id not in used_content_ids
            and block.get("required", True)
        ]

        if missing_ids:
            replacements = self._append_missing_content(
                replacements=replacements,
                missing_content_ids=missing_ids,
                page_inventory=page_inventory,
                valid_slots={
                    slot["slot_id"]: slot
                    for slot in slots
                    if slot.get("slot_id")
                },
                used_slot_ids=set(r["slot_id"] for r in replacements)
            )

        return {
            "page_index": page_index,
            "source_slide": source_slide,
            "purpose": "content",
            "layout_rationale": {
                "layout_pattern": "fallback strict native fill",
                "why_fit": "Fallback preserves original content and uses available native slots.",
                "risk": "Visual quality may be lower than AI planning."
            },
            "replacements": replacements
        }

    def _fallback_creative_plan_slide(
        self,
        page_index: int,
        content_slide: dict,
        slide_library: dict,
        forced_source_slide: int | None = None
    ) -> dict:
        source_slide = forced_source_slide or self._choose_fallback_source_slide(
            page_index=page_index,
            content_slide=content_slide,
            slide_library=slide_library
        )

        library_slide = self._library_slides_by_index(slide_library).get(source_slide)

        if library_slide is None:
            raise ValueError("slide_library has no valid slides")

        slots = [
            slot for slot in library_slide.get("slots", [])
            if self._is_safe_slot(slot)
        ]

        title_slots = [slot for slot in slots if slot.get("role") == "title_candidate"]
        subtitle_slots = [slot for slot in slots if slot.get("role") == "subtitle_candidate"]
        label_slots = [slot for slot in slots if slot.get("role") == "label_candidate"]
        body_slots = [slot for slot in slots if slot.get("role") == "body_candidate"]

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
                    "role": "title",
                    "text": self._shorten_for_creative(title, 60)
                }
            )

        body_lines = bullets

        if body_lines and label_slots and len(body_lines[0]) <= 18:
            replacements.append(
                {
                    "slot_id": label_slots[0]["slot_id"],
                    "role": "label",
                    "text": self._shorten_for_creative(body_lines[0], 24)
                }
            )

            body_lines = body_lines[1:]

        if body_lines and subtitle_slots:
            replacements.append(
                {
                    "slot_id": subtitle_slots[0]["slot_id"],
                    "role": "subtitle",
                    "text": self._shorten_for_creative(body_lines[0], 80)
                }
            )

            body_lines = body_lines[1:]

        if body_lines and body_slots:
            groups = self._group_text_for_slots(
                lines=body_lines,
                slot_count=len(body_slots)
            )

            for slot, group in zip(body_slots, groups):
                if not group:
                    continue

                replacements.append(
                    {
                        "slot_id": slot["slot_id"],
                        "role": "body",
                        "text": "\n".join(
                            self._shorten_for_creative(line, 90)
                            for line in group
                        )
                    }
                )

        return {
            "page_index": page_index,
            "source_slide": source_slide,
            "purpose": "content",
            "layout_rationale": {
                "layout_pattern": "fallback creative native fill",
                "why_fit": "Fallback creates concise presentation text from source content.",
                "risk": "Text is shortened for layout."
            },
            "replacements": replacements
        }

    def _build_content_inventory(self, content_slides: list[dict]) -> dict:
        pages = []

        for page_index, slide in enumerate(content_slides):
            page_inventory = self._build_page_inventory(
                page_index=page_index,
                content_slide=slide
            )

            pages.append(
                {
                    "page_index": page_index,
                    "blocks": list(page_inventory.values())
                }
            )

        return {
            "schema": "slidebeautifier_content_inventory.segmented.v1",
            "rules": {
                "immutable_text": True,
                "no_rewrite": True,
                "no_summarize": True,
                "preserve_order": True
            },
            "pages": pages
        }

    def _content_inventory_by_page(
        self,
        content_slides: list[dict]
    ) -> dict[int, dict[str, dict]]:
        result = {}

        for page_index, slide in enumerate(content_slides):
            result[page_index] = self._build_page_inventory(
                page_index=page_index,
                content_slide=slide
            )

        return result

    def _build_page_inventory(
        self,
        page_index: int,
        content_slide: dict
    ) -> dict[str, dict]:
        result = {}

        title = str(content_slide.get("title", "")).strip()

        if title:
            content_id = f"p{page_index}_title"

            result[content_id] = {
                "content_id": content_id,
                "role_hint": "title",
                "semantic_type": "title",
                "semantic_group": "title",
                "parent_content_id": None,
                "order": 0,
                "text": title,
                "required": True
            }

        bullets = content_slide.get("bullets", [])

        if not isinstance(bullets, list):
            bullets = []

        order = 1
        previous_main_content_id = None

        for bullet_index, bullet in enumerate(bullets, start=1):
            raw_text = str(bullet).strip()

            if not raw_text:
                continue

            segments = self._split_text_into_semantic_segments(raw_text)
            bullet_group = f"p{page_index}_b{bullet_index}"

            for segment_index, segment in enumerate(segments, start=1):
                content_id = f"p{page_index}_b{bullet_index}_s{segment_index}"
                semantic_type = self._guess_content_role(segment)

                parent_content_id = None

                if segment_index > 1:
                    parent_content_id = f"p{page_index}_b{bullet_index}_s1"

                if semantic_type in ["example", "detail", "result"] and previous_main_content_id:
                    parent_content_id = previous_main_content_id

                result[content_id] = {
                    "content_id": content_id,
                    "role_hint": semantic_type,
                    "semantic_type": semantic_type,
                    "semantic_group": bullet_group,
                    "parent_content_id": parent_content_id,
                    "order": order,
                    "text": segment,
                    "required": True
                }

                if semantic_type not in ["example", "detail"]:
                    previous_main_content_id = content_id

                order += 1

        return result

    def _split_text_into_semantic_segments(
        self,
        text: str
    ) -> list[str]:
        text = str(text).strip()

        if not text:
            return []

        if len(text) <= 55:
            return [text]

        parts = re.split(r"(?<=[。！？!?；;])", text)

        parts = [
            part.strip()
            for part in parts
            if part and part.strip()
        ]

        if len(parts) <= 1 and len(text) > 80:
            parts = re.split(r"(?<=[，,])", text)

            parts = [
                part.strip()
                for part in parts
                if part and part.strip()
            ]

        if not parts:
            return [text]

        merged = []
        buffer = ""

        for part in parts:
            if not buffer:
                buffer = part
                continue

            if len(buffer) + len(part) <= 70:
                buffer += part
            else:
                merged.append(buffer)
                buffer = part

        if buffer:
            merged.append(buffer)

        return merged

    def _guess_content_role(self, text: str) -> str:
        clean = text.strip()

        if len(clean) <= 14 and not clean.endswith(("。", ".", "，", ",")):
            return "label"

        if any(marker in clean for marker in ["例如", "比如", "举例", "如：", "比如说"]):
            return "example"

        if any(marker in clean for marker in ["包括", "具体", "其中", "主要有", "分为"]):
            return "detail"

        if any(marker in clean for marker in ["因为", "由于", "原因", "导致"]):
            return "cause"

        if any(marker in clean for marker in ["所以", "因此", "从而", "结果"]):
            return "result"

        if any(marker in clean for marker in ["首先", "其次", "然后", "最后", "第一", "第二", "第三"]):
            return "sequence"

        if len(clean) <= 35:
            return "short_body"

        return "body"

    def _materialize_content_text(
        self,
        content_ids: list[str],
        page_inventory: dict[str, dict]
    ) -> str:
        blocks = []

        for content_id in content_ids:
            block = page_inventory.get(content_id)

            if not block:
                continue

            text = str(block.get("text", "")).strip()

            if text:
                blocks.append(
                    {
                        "order": block.get("order", 0),
                        "text": text
                    }
                )

        blocks = sorted(
            blocks,
            key=lambda item: item["order"]
        )

        return "\n".join(block["text"] for block in blocks)

    def _safe_source_slide(
        self,
        ai_slide: dict,
        page_index: int,
        content_slide: dict,
        slide_library: dict
    ) -> int:
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

        return source_slide

    def _normalize_layout_rationale(self, ai_slide: dict) -> dict:
        layout_rationale = ai_slide.get("layout_rationale", {})

        if not isinstance(layout_rationale, dict):
            layout_rationale = {}

        return {
            "layout_pattern": str(layout_rationale.get("layout_pattern", "")).strip(),
            "why_fit": str(layout_rationale.get("why_fit", "")).strip(),
            "risk": str(layout_rationale.get("risk", "")).strip()
        }

    def _append_missing_content(
        self,
        replacements: list[dict],
        missing_content_ids: list[str],
        page_inventory: dict[str, dict],
        valid_slots: dict[str, dict],
        used_slot_ids: set[str]
    ) -> list[dict]:
        if not missing_content_ids:
            return replacements

        available_slots = [
            slot
            for slot in valid_slots.values()
            if slot.get("slot_id") not in used_slot_ids
        ]

        body_slots = [
            slot for slot in available_slots
            if slot.get("role") == "body_candidate"
        ]

        subtitle_slots = [
            slot for slot in available_slots
            if slot.get("role") == "subtitle_candidate"
        ]

        label_slots = [
            slot for slot in available_slots
            if slot.get("role") == "label_candidate"
        ]

        groups = {}

        for content_id in missing_content_ids:
            block = page_inventory.get(content_id)

            if not block:
                continue

            group_id = block.get("semantic_group") or content_id
            groups.setdefault(group_id, []).append(block)

        sorted_groups = sorted(
            groups.values(),
            key=lambda blocks: min(block.get("order", 0) for block in blocks)
        )

        target_slots = body_slots + subtitle_slots + label_slots

        if target_slots:
            for slot, blocks in zip(target_slots, sorted_groups):
                blocks = sorted(
                    blocks,
                    key=lambda block: block.get("order", 0)
                )

                content_ids = [
                    block["content_id"]
                    for block in blocks
                ]

                text = "\n".join(
                    block["text"]
                    for block in blocks
                    if block.get("text")
                )

                if not text:
                    continue

                slot_id = slot["slot_id"]

                replacements.append(
                    {
                        "slot_id": slot_id,
                        "role": self._infer_replacement_role(slot),
                        "content_ids": content_ids,
                        "text": text
                    }
                )

                used_slot_ids.add(slot_id)

            remaining_groups = sorted_groups[len(target_slots):]

            if remaining_groups and replacements:
                target_index = len(replacements) - 1

                for index, replacement in enumerate(replacements):
                    if replacement.get("role") == "body":
                        target_index = index
                        break

                extra_texts = []
                extra_ids = []

                for blocks in remaining_groups:
                    blocks = sorted(
                        blocks,
                        key=lambda block: block.get("order", 0)
                    )

                    for block in blocks:
                        extra_ids.append(block["content_id"])
                        extra_texts.append(block["text"])

                if extra_texts:
                    old_text = replacements[target_index].get("text", "")

                    replacements[target_index]["text"] = "\n".join(
                        part for part in [
                            old_text,
                            "\n".join(extra_texts)
                        ]
                        if part
                    )

                    old_ids = replacements[target_index].get("content_ids", [])
                    replacements[target_index]["content_ids"] = old_ids + extra_ids

            return replacements

        if replacements:
            target_index = len(replacements) - 1

            for index, replacement in enumerate(replacements):
                if replacement.get("role") == "body":
                    target_index = index
                    break

            added_text = self._materialize_content_text(
                content_ids=missing_content_ids,
                page_inventory=page_inventory
            )

            old_text = replacements[target_index].get("text", "")

            replacements[target_index]["text"] = "\n".join(
                part for part in [old_text, added_text]
                if part
            )

            old_ids = replacements[target_index].get("content_ids", [])
            replacements[target_index]["content_ids"] = old_ids + missing_content_ids

        return replacements

    def _force_page_text_into_largest_slot(
        self,
        page_inventory: dict[str, dict],
        valid_slots: dict[str, dict]
    ) -> list[dict]:
        if not page_inventory or not valid_slots:
            return []

        candidate_slots = [
            slot
            for slot in valid_slots.values()
            if slot.get("role") == "body_candidate"
        ]

        if not candidate_slots:
            candidate_slots = [
                slot
                for slot in valid_slots.values()
                if slot.get("role") in [
                    "subtitle_candidate",
                    "title_candidate",
                    "label_candidate"
                ]
            ]

        if not candidate_slots:
            return []

        def slot_area(slot: dict) -> int:
            geometry = slot.get("geometry", {}) or {}
            width = int(geometry.get("width", 0) or 0)
            height = int(geometry.get("height", 0) or 0)

            return width * height

        best_slot = sorted(
            candidate_slots,
            key=slot_area,
            reverse=True
        )[0]

        content_ids = [
            content_id
            for content_id, block in sorted(
                page_inventory.items(),
                key=lambda item: item[1].get("order", 0)
            )
            if block.get("required", True)
        ]

        text = self._materialize_content_text(
            content_ids=content_ids,
            page_inventory=page_inventory
        )

        if not text:
            return []

        return [
            {
                "slot_id": best_slot["slot_id"],
                "role": self._infer_replacement_role(best_slot),
                "content_ids": content_ids,
                "text": text
            }
        ]

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

            safe_slots = [
                slot for slot in slide.get("slots", [])
                if self._is_safe_slot(slot)
            ]

            title_count = sum(
                1 for slot in safe_slots
                if slot.get("role") == "title_candidate"
            )

            subtitle_count = sum(
                1 for slot in safe_slots
                if slot.get("role") == "subtitle_candidate"
            )

            label_count = sum(
                1 for slot in safe_slots
                if slot.get("role") == "label_candidate"
            )

            body_slots = [
                slot for slot in safe_slots
                if slot.get("role") == "body_candidate"
            ]

            body_count = len(body_slots)

            total_capacity = sum(
                int(slot.get("capacity_chars", 0) or 0)
                for slot in body_slots
            )

            if title_count == 0:
                continue

            if body_count == 0 and bullet_count > 1:
                continue

            score = 0

            score += title_count * 4
            score += subtitle_count * 3
            score += label_count * 2
            score += body_count * 12
            score += min(total_capacity, 300) * 0.05

            if bullet_count >= 4 and body_count >= 2:
                score += 18

            if bullet_count >= 6 and body_count >= 3:
                score += 22

            if bullet_count <= 2 and body_count >= 3:
                score -= 12

            if bullet_count <= 1 and body_count >= 2:
                score -= 10

            if bullet_count >= 4 and body_count < 2:
                score -= 26

            if bullet_count >= 6 and body_count < 3:
                score -= 30

            if has_number and (body_count >= 1 or label_count >= 1):
                score += 6

            if has_compare and body_count >= 2:
                score += 8

            if has_process and (body_count >= 2 or label_count >= 2):
                score += 8

            if is_summary and body_count <= 2:
                score += 6

            score -= abs(source_slide - ((page_index % max(1, len(slides))) + 1)) * 0.15

            scored.append(
                {
                    "source_slide": source_slide,
                    "score": score,
                    "body_count": body_count,
                    "total_capacity": total_capacity
                }
            )

        scored = sorted(
            scored,
            key=lambda item: item["score"],
            reverse=True
        )

        if not scored:
            return int(slides[0].get("slide_index", 1))

        top_candidates = scored[:min(3, len(scored))]
        selected = top_candidates[page_index % len(top_candidates)]

        return selected["source_slide"]

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
                if not self._is_safe_slot(slot):
                    continue

                compact_slots.append(
                    {
                        "slot_id": slot.get("slot_id"),
                        "role": slot.get("role"),
                        "slot_level": slot.get("slot_level"),
                        "group_id": slot.get("group_id"),
                        "group_order": slot.get("group_order"),
                        "parent_slot_id": slot.get("parent_slot_id"),
                        "usable_for": slot.get("usable_for", []),
                        "geometry": slot.get("geometry", {}),
                        "font_size_pt": slot.get("font_size_pt"),
                        "paragraph_count": slot.get("paragraph_count"),
                        "capacity_chars": slot.get("capacity_chars"),
                        "old_text_length": len(str(slot.get("text", "")))
                    }
                )

            title_count = sum(
                1 for slot in compact_slots
                if slot.get("role") == "title_candidate"
            )

            subtitle_count = sum(
                1 for slot in compact_slots
                if slot.get("role") == "subtitle_candidate"
            )

            label_count = sum(
                1 for slot in compact_slots
                if slot.get("role") == "label_candidate"
            )

            body_count = sum(
                1 for slot in compact_slots
                if slot.get("role") == "body_candidate"
            )

            group_ids = sorted(
                {
                    slot.get("group_id")
                    for slot in compact_slots
                    if slot.get("group_id")
                }
            )

            compact_slides.append(
                {
                    "slide_index": slide.get("slide_index"),
                    "page_type": slide.get("page_type"),
                    "slot_count": len(compact_slots),
                    "title_count": title_count,
                    "subtitle_count": subtitle_count,
                    "label_count": label_count,
                    "body_count": body_count,
                    "group_ids": group_ids,
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
            if not self._is_safe_slot(slot):
                continue

            slot_id = slot.get("slot_id")

            if slot_id:
                result[str(slot_id)] = slot

        return result

    def _valid_slots_for_source_relaxed(
        self,
        slide_library: dict,
        source_slide: int
    ) -> dict[str, dict]:
        slide = self._library_slides_by_index(slide_library).get(source_slide)

        if slide is None:
            return {}

        result = {}

        for slot in slide.get("slots", []):
            role = slot.get("role")

            if role not in [
                "title_candidate",
                "subtitle_candidate",
                "label_candidate",
                "body_candidate"
            ]:
                continue

            if not slot.get("fillable", False):
                continue

            if bool(slot.get("is_vertical", False)):
                continue

            font_size = float(slot.get("font_size_pt") or 0)

            if font_size >= 54:
                continue

            slot_id = slot.get("slot_id")

            if slot_id:
                result[str(slot_id)] = slot

        return result

    def _is_safe_slot(
        self,
        slot: dict
    ) -> bool:
        role = slot.get("role")

        if role not in [
            "title_candidate",
            "subtitle_candidate",
            "body_candidate",
            "label_candidate"
        ]:
            return False

        if not slot.get("fillable", False):
            return False

        geometry = slot.get("geometry", {}) or {}

        width = int(geometry.get("width", 0) or 0)
        height = int(geometry.get("height", 0) or 0)
        capacity = int(slot.get("capacity_chars", 0) or 0)
        font_size = float(slot.get("font_size_pt") or 0)
        is_vertical = bool(slot.get("is_vertical", False))

        if is_vertical:
            return False

        if width <= 0 or height <= 0:
            return False

        if font_size >= 54:
            return False

        if width < 350000:
            return False

        if height < 90000:
            return False

        if role == "title_candidate":
            return width >= 900000 and height >= 120000

        if role == "subtitle_candidate":
            return width >= 700000 and height >= 100000 and capacity >= 6

        if role == "label_candidate":
            return width >= 350000 and height >= 90000 and capacity >= 3

        if role == "body_candidate":
            return width >= 700000 and height >= 160000 and capacity >= 8

        return False

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

    def _group_blocks_for_slots(
        self,
        blocks: list[dict],
        slot_count: int
    ) -> list[list[dict]]:
        if slot_count <= 0:
            return []

        if not blocks:
            return [[] for _ in range(slot_count)]

        slot_count = min(slot_count, len(blocks))
        chunk_size = math.ceil(len(blocks) / slot_count)

        groups = []

        for index in range(0, len(blocks), chunk_size):
            groups.append(blocks[index:index + chunk_size])

        return groups

    def _group_text_for_slots(
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

    def _shorten_for_creative(
        self,
        text: str,
        max_chars: int
    ) -> str:
        text = str(text).strip()

        if len(text) <= max_chars:
            return text

        cut_points = ["。", "，", "；", ";", ",", "."]
        candidate = text[:max_chars]

        best_cut = -1

        for mark in cut_points:
            pos = candidate.rfind(mark)

            if pos > best_cut:
                best_cut = pos

        if best_cut >= 8:
            return candidate[:best_cut + 1].strip()

        return candidate.strip()