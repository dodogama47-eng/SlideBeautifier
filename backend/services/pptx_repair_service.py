from pathlib import Path
import os
import zipfile
import json
from xml.etree import ElementTree as ET


class PptxRepairService:


    def repair_pptx(
        self,
        pptx_path: Path,
        report_path: Path | None = None
    ) -> dict:
        pptx_path = Path(pptx_path)

        report = {
            "pptx_path": str(pptx_path),
            "status": "ok",
            "duplicate_entries_removed": 0,
            "content_type_duplicates_removed": 0,
            "warnings": []
        }

        if not pptx_path.exists():
            report["status"] = "failed"
            report["warnings"].append("PPTX file does not exist.")
            self._save_report(report_path, report)
            return report

        if pptx_path.stat().st_size == 0:
            report["status"] = "failed"
            report["warnings"].append("PPTX file is empty.")
            self._save_report(report_path, report)
            return report

        temp_path = pptx_path.with_suffix(".repair.tmp.pptx")

        try:
            with zipfile.ZipFile(pptx_path, "r") as zin:
                infos = [
                    info
                    for info in zin.infolist()
                    if not info.is_dir()
                ]

                last_index_by_name = {}

                for index, info in enumerate(infos):
                    last_index_by_name[info.filename] = index

                unique_infos = []

                for index, info in enumerate(infos):
                    if last_index_by_name.get(info.filename) == index:
                        unique_infos.append(info)
                    else:
                        report["duplicate_entries_removed"] += 1

                with zipfile.ZipFile(
                    temp_path,
                    "w",
                    compression=zipfile.ZIP_DEFLATED
                ) as zout:
                    for info in unique_infos:
                        data = zin.read(info.filename)

                        if info.filename == "[Content_Types].xml":
                            data, removed_count = self._repair_content_types(data)
                            report["content_type_duplicates_removed"] += removed_count

                        zout.writestr(info.filename, data)

            os.replace(temp_path, pptx_path)

            self._validate_basic_structure(
                pptx_path=pptx_path,
                report=report
            )

        except Exception as error:
            report["status"] = "failed"
            report["warnings"].append(str(error))

            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass

        self._save_report(report_path, report)
        return report

    def _repair_content_types(
        self,
        data: bytes
    ) -> tuple[bytes, int]:
        removed_count = 0

        try:
            root = ET.fromstring(data)
        except Exception:
            return data, removed_count

        seen_defaults = set()
        seen_overrides = set()

        for child in list(root):
            tag = self._strip_namespace(child.tag)

            if tag == "Default":
                key = child.attrib.get("Extension", "")

                if key in seen_defaults:
                    root.remove(child)
                    removed_count += 1
                else:
                    seen_defaults.add(key)

            elif tag == "Override":
                key = child.attrib.get("PartName", "")

                if key in seen_overrides:
                    root.remove(child)
                    removed_count += 1
                else:
                    seen_overrides.add(key)

        repaired = ET.tostring(
            root,
            encoding="utf-8",
            xml_declaration=True
        )

        return repaired, removed_count

    def _validate_basic_structure(
        self,
        pptx_path: Path,
        report: dict
    ) -> None:
        required_entries = [
            "[Content_Types].xml",
            "ppt/presentation.xml",
            "ppt/_rels/presentation.xml.rels"
        ]

        try:
            with zipfile.ZipFile(pptx_path, "r") as zf:
                names = set(zf.namelist())

                for entry in required_entries:
                    if entry not in names:
                        report["status"] = "failed"
                        report["warnings"].append(
                            f"Missing required entry: {entry}"
                        )

                duplicate_names = self._find_duplicate_names(zf)

                if duplicate_names:
                    report["status"] = "warning"
                    report["warnings"].append(
                        f"Still has duplicate entries: {duplicate_names[:10]}"
                    )

        except Exception as error:
            report["status"] = "failed"
            report["warnings"].append(
                f"Validation failed: {str(error)}"
            )

    def _find_duplicate_names(
        self,
        zf: zipfile.ZipFile
    ) -> list[str]:
        seen = set()
        duplicates = []

        for info in zf.infolist():
            if info.filename in seen:
                duplicates.append(info.filename)
            else:
                seen.add(info.filename)

        return duplicates

    def _strip_namespace(
        self,
        tag: str
    ) -> str:
        if "}" in tag:
            return tag.split("}", 1)[1]

        return tag

    def _save_report(
        self,
        report_path: Path | None,
        report: dict
    ) -> None:
        if report_path is None:
            return

        report_path = Path(report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, "w", encoding="utf-8") as file:
            json.dump(
                report,
                file,
                ensure_ascii=False,
                indent=2
            )