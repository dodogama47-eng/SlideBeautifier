from pathlib import Path
from pptx import Presentation


class PptReader:
    def extract_all_text(self, pptx_path: Path) -> str:
        ppt = Presentation(str(pptx_path))
        result = []

        for index, slide in enumerate(ppt.slides, start=1):
            texts = []

            for shape in slide.shapes:
                if shape.has_text_frame:
                    text = shape.text.strip()
                    if text:
                        texts.append(text)

            if texts:
                result.append(f"Slide {index}:\n" + "\n".join(texts))

        return "\n\n".join(result)