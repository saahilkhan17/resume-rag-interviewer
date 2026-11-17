import pytest
from pathlib import Path
from app.services import resume_parser

@pytest.fixture
def sample_resume_bytes(sample_resume_bytes):
    # Already provided fixture returns bytes of sample_resume.txt
    return sample_resume_bytes

def test_parse_resume_text_extracts_skills_and_domains(sample_resume_bytes):
    text = sample_resume_bytes.decode('utf-8')
    result = resume_parser.parse_resume_text(text)
    # Expect certain skills present
    for skill in ['python', 'fastapi', 'postgresql', 'machine learning']:
        assert skill in result['skills']
    # Technologies subset should include same
    for tech in ['fastapi', 'postgresql']:
        assert tech in result['technologies']
    # Domains include machine learning and backend development
    assert 'machine learning' in result['domains']
    assert 'backend development' in result['domains']

def test_parse_resume_text_empty_returns_defaults():
    res = resume_parser.parse_resume_text("")
    assert res['skills'] == []
    assert res['technologies'] == []
    assert res['domains'] == []
    assert res['years_experience_hint'] is None

def test_years_experience_parsing():
    txt = "I have 3 years experience in software development."
    res = resume_parser.parse_resume_text(txt)
    assert res['years_experience_hint'] == 3

def test_parse_resume_file_pdf(tmp_path):
    # Create minimal PDF containing text "Python FastAPI developer"
    from io import BytesIO
    from pypdf import PdfWriter
    pdf_bytes = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    # Add text via annotation? Simplify: use pypdf to write simple content stream
    # Instead, create a PDF with a single page of simple text using reportlab if available.
    # To avoid extra deps, we embed a pre-generated PDF binary (simple) that contains the text.
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources 6 0 R /Contents 4 0 R >> endobj\n"
        b"4 0 obj << /Length 55 >> stream\n"
        b"BT /F1 12 Tf 10 190 Td (Python FastAPI developer) Tj ET\n"
        b"endstream endobj\n"
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"6 0 obj << /Type /Resources /Font << /F1 5 0 R >> >> endobj\n"
        b"xref\n0 7\n0000000000 65535 f \n0000000010 00000 n \n0000000065 00000 n \n0000000118 00000 n \n0000000220 00000 n \n0000000365 00000 n \n0000000455 00000 n \ntrailer << /Size 7 /Root 1 0 R >>\nstartxref\n527\n%%EOF"
    )
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(pdf_content)
    data = pdf_path.read_bytes()
    parsed = resume_parser.parse_resume_file(data, str(pdf_path))
    # Should extract skills python and fastapi from text
    assert 'python' in parsed['skills']
    assert 'fastapi' in parsed['skills']

def test_parse_resume_file_unsupported_extension():
    data = b"binary"
    with pytest.raises(ValueError):
        resume_parser.parse_resume_file(data, "file.exe")

def test_extract_text_from_md():
    md_bytes = b"# Title\nSome markdown content"
    txt = resume_parser.extract_text_from_bytes(md_bytes, "doc.md")
    assert "Title" in txt
    assert "markdown" in txt
