# PRIVACY: RAM-only. Zero disk I/O.
import io
import gc
import pathlib


def read_file_context(filepath: pathlib.Path, max_chars: int = 1500) -> str:
    try:
        suffix = filepath.suffix.lower()

        if suffix in [".txt", ".md"]:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(max_chars)

        elif suffix == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(str(filepath))
                text_parts = []
                chars_read = 0
                for page in reader.pages:
                    extracted_text = page.extract_text()
                    if extracted_text:
                        extract = str(extracted_text)
                        text_parts.append(extract)
                        chars_read += len(extract)
                    if chars_read >= max_chars:
                        break
                result = "".join(text_parts)
                return result[:int(max_chars)] # type: ignore
            except Exception:
                return f"File found: {filepath.name} (couldn't read content)"

        elif suffix in [".docx", ".doc"]:
            try:
                import docx
                doc = docx.Document(str(filepath))
                text_parts = []
                for para in doc.paragraphs:
                    if para.text:
                        text_parts.append(para.text)
                result = "\n".join(text_parts)
                return result[:int(max_chars)] # type: ignore
            except Exception:
                return f"File found: {filepath.name} (couldn't read content)"

        elif suffix in [".csv", ".xlsx"]:
            return f"Spreadsheet found: {filepath.name} — open it to see contents"

        else:
            return f"File found: {filepath.name}"

    except Exception:
        return f"File found: {filepath.name} (couldn't read content)"

    finally:
        gc.collect()
    return ""
