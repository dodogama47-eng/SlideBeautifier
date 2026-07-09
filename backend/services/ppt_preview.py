from pathlib import Path
import comtypes.client


class PptPreviewService:
    def render_pptx_to_images(
        self,
        pptx_path: Path,
        output_dir: Path
    ) -> list[Path]:
        pptx_path = Path(pptx_path).resolve()
        output_dir = Path(output_dir).resolve()

        output_dir.mkdir(parents=True, exist_ok=True)

        for old_file in output_dir.glob("*.png"):
            old_file.unlink()

        powerpoint = None
        presentation = None

        try:
            powerpoint = comtypes.client.CreateObject("PowerPoint.Application")
            powerpoint.Visible = 1

            presentation = powerpoint.Presentations.Open(
                str(pptx_path),
                WithWindow=False
            )

            image_paths = []

            for index in range(1, presentation.Slides.Count + 1):
                image_path = output_dir / f"page_{index}.png"

                presentation.Slides(index).Export(
                    str(image_path),
                    "PNG",
                    1600,
                    900
                )

                image_paths.append(image_path)

            return image_paths

        finally:
            if presentation is not None:
                presentation.Close()

            if powerpoint is not None:
                powerpoint.Quit()