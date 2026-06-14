import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def parse_resume(file_path):
    if not file_path:
        return None
    ext = Path(file_path).suffix.lower() if file_path else ''
    try:
        if ext == '.pdf':
            return parse_pdf(file_path)
        elif ext in ('.docx', '.doc'):
            return parse_docx(file_path)
        elif ext == '.txt':
            return parse_txt(file_path)
        else:
            return parse_txt(file_path)
    except Exception as e:
        logger.error(f"Failed to parse resume {file_path}: {e}")
        return None

def parse_pdf(file_path):
    try:
        import PyPDF2
        text = []
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text.append(page.extract_text() or '')
        full_text = '\n'.join(text)
        return {'text': full_text, 'html': '', 'skills': [], 'experience': [], 'education': []}
    except ImportError:
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                full_text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
            return {'text': full_text, 'html': '', 'skills': [], 'experience': [], 'education': []}
        except ImportError:
            logger.warning("No PDF parser available")
            return None

def parse_docx(file_path):
    try:
        from docx import Document
        doc = Document(file_path)
        full_text = '\n'.join(p.text for p in doc.paragraphs)
        return {'text': full_text, 'html': '', 'skills': [], 'experience': [], 'education': []}
    except ImportError:
        logger.warning("python-docx not available")
        return None

def parse_txt(file_path):
    with open(file_path, 'r', errors='ignore') as f:
        full_text = f.read()
    return {'text': full_text, 'html': '', 'skills': [], 'experience': [], 'education': []}
