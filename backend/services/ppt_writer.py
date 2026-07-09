from pathlib import Path
from pptx import Presentation
from pptx.util import Inches


class PptWriter:
    def write_slide_plan_to_template(
            self,
            template_path: Path,
            slide_plan: str,
            result_path: Path
    ) -> Path:
        ppt = Presentation(str(template_path))

        if len(ppt.slides) == 0:
            blank_layout = ppt.slide_layouts[6]
            ppt.slides.add_slide(blank_layout)

        first_slide = ppt.slides[0]
        written = False

        for shape in first_slide.shapes:
            if shape.has_text_frame:
                shape.text = slide_plan
                written = True
                break

        if not written:
            textbox = first_slide.shapes.add_textbox(
                Inches(0.7),
                Inches(0.7),
                Inches(8),
                Inches(5)
            )
            textbox.text = slide_plan

        ppt.save(str(result_path))
        return result_path