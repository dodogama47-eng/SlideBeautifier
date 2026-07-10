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
   - each block has content_id, role_hint, text
   - text is the only source of truth

2. slide_library:
   - reusable PowerPoint template slides
   - each slide has existing text slots with slot_id and role

Your job:
- Choose the best source_slide for each content page.
- Assign existing content_ids to suitable slot_ids.
- Preserve content order.
- Preserve semantic relationships.
- Keep subordinate / explanatory / sequential content together when appropriate.
- Do not turn hierarchical or sequential content into unrelated parallel bullets.
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
  "schema": "slidebeautifier_native_fill_plan.v3",
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
          "role": "title | subtitle | body | label",
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
- Do not drop important content_ids.
- Do not invent content_ids.
- Do not change content text.
- Do not split one content_id.
- Do not combine unrelated content.
- Preserve the order of content_ids as much as possible.
- title content should use title_candidate slots.
- subtitle content should use subtitle_candidate if available.
- body/explanation content should use body_candidate slots.
- label_candidate is only for very short independent labels.
- Do not place long explanatory text into label_candidate.
- decorative_candidate slots must not be used.
- Choose a source_slide that has enough suitable slots for the content.
- If content has few blocks, choose a simple template with fewer visible content areas.
- If content has many blocks, choose a template with more body_candidate slots.
- Similar content pages may use different source_slide templates.
- Avoid using the same source_slide repeatedly unless it is clearly the best fit.

Semantic rules:
- If one line explains the previous line, keep them in the same slot.
- If lines form a cause-effect chain, keep their order.
- If lines are steps, keep them sequential.
- If a bullet has sub-bullets, keep them together.
- Do not flatten hierarchy into unrelated parallel cards.
- Do not over-cut content into too many tiny fragments.
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
  "schema": "slidebeautifier_native_fill_plan.v3",
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
          "role": "title | subtitle | body | label",
          "content_ids": ["p0_title"]
        }}
      ]
    }}
  ]
}}

Repair rules:
- Do not output replacement text directly.
- Do not alter source text.
- Do not remove important content.
- If text is too long for a slot, choose a larger slot or a different source_slide.
- If one slide has too many content blocks, choose a template with more body slots.
- If content is semantically connected, keep it together.
- If a template has too many unused visible cards, choose a simpler template.
- Do not use decorative_candidate slots.
- Do not place body content into label_candidate.
- Preserve page order.
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

        for page_index, content_slide in enumerate(content_slides):
            slides.append(
                self._fallback_plan_slide(
                    page_index=page_index,
                    content_slide=content_slide,
                    slide_library=slide_library
                )
            )

        return {
            "schema": "slidebeautifier_native_fill_plan.v3",
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
            temperature=0.05,
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
                    slide_library=slide_library,
                    page_inventory=inventory_by_page.get(page_index, {})
                )
            )

        return {
            "schema": "slidebeautifier_native_fill_plan.v3",
            "status": "confirmed",
            "slides": normalized_slides
        }

    def _normalize_one_plan_slide(
        self,
        page_index: int,
        ai_slide: dict,
        content_slide: dict,
        slide_library: dict,
        page_inventory: dict[str, dict]
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

        placements = ai_slide.get("placements")

        # 兼容旧格式 replacements，但不信任 AI 的 text，只信 content_ids
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

            if role not in ["title", "subtitle", "body", "label"]:
                role = self._infer_replacement_role(
                    slot=valid_slots.get(slot_id)
                )

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

            if slot and slot.get("role") == "decorative_candidate":
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

        # 如果 AI 漏掉了内容，尝试把未使用内容追加进已有 body slot 或 fallback
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
            fallback = self._fallback_plan_slide(
                page_index=page_index,
                content_slide=content_slide,
                slide_library=slide_library,
                forced_source_slide=source_slide
            )

            normalized_replacements = fallback.get("replacements", [])

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
            "replacements": normalized_replacements
        }

    def _append_missing_content(
        self,
        replacements: list[dict],
        missing_content_ids: list[str],
        page_inventory: dict[str, dict],
        valid_slots: dict[str, dict],
        used_slot_ids: set[str]
    ) -> list[dict]:
        body_slots = [
            slot
            for slot in valid_slots.values()
            if slot.get("role") == "body_candidate"
            and slot.get("slot_id") not in used_slot_ids
        ]

        title_slots = [
            slot
            for slot in valid_slots.values()
            if slot.get("role") == "title_candidate"
            and slot.get("slot_id") not in used_slot_ids
        ]

        candidate_slots = body_slots or title_slots

        if candidate_slots:
            slot = candidate_slots[0]
            slot_id = slot["slot_id"]

            replacements.append(
                {
                    "slot_id": slot_id,
                    "role": "body",
                    "content_ids": missing_content_ids,
                    "text": self._materialize_content_text(
                        content_ids=missing_content_ids,
                        page_inventory=page_inventory
                    )
                }
            )

            return replacements

        # 没有空 slot，就追加到最后一个 body replacement，保证内容不丢
        if replacements:
            target_index = len(replacements) - 1

            for index, replacement in enumerate(replacements):
                if replacement.get("role") == "body":
                    target_index = index
                    break

            old_text = replacements[target_index].get("text", "")
            added_text = self._materialize_content_text(
                content_ids=missing_content_ids,
                page_inventory=page_inventory
            )

            replacements[target_index]["text"] = "\n".join(
                part for part in [old_text, added_text] if part
            )

            old_ids = replacements[target_index].get("content_ids", [])
            replacements[target_index]["content_ids"] = old_ids + missing_content_ids

        return replacements

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

        page_inventory = self._content_inventory_by_page([content_slide]).get(0)

        # 如果这是从原列表里的 page_index 进入，重新生成正确 id
        page_inventory = self._build_page_inventory(
            page_index=page_index,
            content_slide=content_slide
        )

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

        # 如果第一个 body 更像副标题，且模板有 subtitle slot，就放进去，但原文不改
        if body_blocks and subtitle_slots:
            first_block = body_blocks[0]
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

        available_body_slots = body_slots or label_slots

        if body_blocks and available_body_slots:
            groups = self._group_blocks_for_slots(
                blocks=body_blocks,
                slot_count=len(available_body_slots)
            )

            for slot, group in zip(available_body_slots, groups):
                if not group:
                    continue

                role = "body" if slot.get("role") == "body_candidate" else "label"
                content_ids = [block["content_id"] for block in group]

                replacements.append(
                    {
                        "slot_id": slot["slot_id"],
                        "role": role,
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
                "layout_pattern": "fallback immutable native slot fill",
                "why_fit": "Selected a source slide with available title/body slots.",
                "risk": "Fallback preserves all text but may be less visually optimized."
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

            score += body_count * 9
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

            score -= abs(source_slide - ((page_index % max(1, len(slides))) + 1)) * 0.25

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
            "schema": "slidebeautifier_content_inventory.v1",
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
                "order": 0,
                "text": title,
                "required": True
            }

        bullets = content_slide.get("bullets", [])

        if not isinstance(bullets, list):
            bullets = []

        order = 1

        for bullet_index, bullet in enumerate(bullets, start=1):
            text = str(bullet).strip()

            if not text:
                continue

            content_id = f"p{page_index}_b{bullet_index}"

            result[content_id] = {
                "content_id": content_id,
                "role_hint": self._guess_content_role(text),
                "order": order,
                "text": text,
                "required": True
            }

            order += 1

        return result

    def _guess_content_role(self, text: str) -> str:
        clean = text.strip()

        if len(clean) <= 18 and not clean.endswith(("。", ".", "，", ",")):
            return "label_or_subtitle"

        if any(marker in clean for marker in ["首先", "其次", "最后", "第一", "第二", "第三"]):
            return "sequence"

        if any(marker in clean for marker in ["因为", "所以", "导致", "因此", "由于"]):
            return "cause_effect"

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

        blocks = sorted(blocks, key=lambda item: item["order"])

        return "\n".join(block["text"] for block in blocks)

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