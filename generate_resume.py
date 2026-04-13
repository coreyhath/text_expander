import json
from fpdf import FPDF, XPos, YPos

_CHAR_MAP = {
    "\u2014": "-",   # em dash
    "\u2013": "-",   # en dash
    "\u2012": "-",   # figure dash
    "\u2010": "-",   # hyphen
    "\u2011": "-",   # non-breaking hyphen
    "\u2018": "'",   # left single quote
    "\u2019": "'",   # right single quote
    "\u201a": ",",   # single low quote
    "\u201b": "'",   # single high-reversed quote
    "\u201c": '"',   # left double quote
    "\u201d": '"',   # right double quote
    "\u201e": '"',   # double low quote
    "\u2026": "...", # ellipsis
    "\u00a0": " ",   # non-breaking space
    "\u2022": "-",   # bullet
    "\u2023": "-",   # triangular bullet
}

def _s(text: str) -> str:
    """Sanitize text to latin-1 safe characters for built-in PDF fonts."""
    for ch, rep in _CHAR_MAP.items():
        text = text.replace(ch, rep)
    return text.encode("latin-1", errors="replace").decode("latin-1")

class ResumePDF(FPDF):
    def __init__(self, data, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = data

    def write_header(self):
        # Name
        self.set_font("helvetica", "B", 24)
        name = self.data.get("name", "Name")
        self.cell(0, 10, _s(name), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        # Tailored title — shown below name for ATS keyword matching
        tailored_title = self.data.get("tailored_title", "")
        if tailored_title:
            self.set_font("helvetica", "I", 13)
            self.cell(0, 6, _s(tailored_title), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.set_font("helvetica", "", 10)

        contact_info = " | ".join(self.data.get("contact", []))
        if contact_info:
            self.cell(0, 5, _s(contact_info), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
            
        links = " | ".join(self.data.get("links", []))
        if links:
            self.cell(0, 5, _s(links), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.ln(2)

    def section_title(self, title):
        self.ln(4)
        self.set_font("helvetica", "B", 12)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 6, title.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        self.ln(1)

    def entry(self, title, subtitle, date, location, description):
        self.set_font("helvetica", "B", 11)
        self.cell(140, 6, _s(title), align="L")
        self.set_font("helvetica", "I", 10)
        self.cell(0, 6, _s(date), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")
        self.set_font("helvetica", "B", 10)
        self.cell(140, 6, _s(subtitle), align="L")
        self.set_font("helvetica", "I", 10)
        self.cell(0, 6, _s(location), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")
        self.set_font("helvetica", "", 10)
        for bullet in description:
            self.multi_cell(0, 4, _s(f"- {bullet}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

def generate_resume_pdf(data: dict, filepath: str):
    pdf = ResumePDF(data)
    pdf.set_margins(12, 12, 12)
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    
    pdf.write_header()
    
    # Summary Section
    if data.get("summary"):
        pdf.section_title("Summary")
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(0, 4, _s(data["summary"]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)

    # Skills Section
    if data.get("skills"):
        pdf.section_title("Skills")
        # Pre-compute max category width for uniform alignment
        pdf.set_font("helvetica", "B", 10)
        categories = []
        for skill in data["skills"]:
            cat = skill.get("category", "").strip().rstrip(":")
            categories.append(_s(cat + ":") if cat else "")
        max_cat_w = max((pdf.get_string_width(c) for c in categories), default=0) + 4
        for skill, category in zip(data["skills"], categories):
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(max_cat_w, 6, category)
            pdf.set_font("helvetica", "", 10)
            remaining_w = pdf.w - pdf.r_margin - pdf.get_x()
            pdf.multi_cell(remaining_w, 6, _s(skill.get("items", "")), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Experience Section
    if data.get("experience"):
        pdf.section_title("Experience")
        for exp in data["experience"]:
            pdf.entry(
                exp.get("title", ""),
                exp.get("company", ""),
                exp.get("date", ""),
                exp.get("location", ""),
                exp.get("description", [])
            )

    # Education Section
    if data.get("education"):
        pdf.section_title("Education")
        for edu in data["education"]:
            pdf.entry(
                edu.get("degree", ""),
                edu.get("institution", ""),
                edu.get("date", ""),
                edu.get("location", ""),
                []
            )

    pdf.output(filepath)

def create_resume():
    # Sample data for testing
    sample_data = {
        "name": "JOHN DOE",
        "contact": ["City, State", "(123) 456-7890", "email@example.com"],
        "links": ["://linkedin.com", "://github.com"],
        "summary": "Experienced Software Engineer with 5+ years of expertise in Python, Cloud Infrastructure, and AI. Proven track record of delivering scalable solutions.",
        "experience": [
            {
                "title": "Senior Software Engineer",
                "company": "Tech Solutions Inc.",
                "date": "Jan 2021 - Present",
                "description": [
                    "Led a team of 5 to rebuild the core API, improving latency by 40%.",
                    "Implemented CI/CD pipelines reducing deployment time by 50%."
                ]
            },
            {
                "title": "Software Developer",
                "company": "Data Systems Corp.",
                "date": "June 2018 - Dec 2020",
                "description": [
                    "Developed and maintained microservices using FastAPI and PostgreSQL.",
                    "Collaborated with UX teams to integrate front-end components."
                ]
            }
        ],
        "education": [
            {
                "degree": "B.S. in Computer Science",
                "institution": "State University",
                "date": "2014 - 2018",
                "details": ["Dean's List 2016-2018", "Minor in Applied Mathematics"]
            }
        ],
        "skills": [
            {"category": "Languages:", "items": "Python, SQL, JavaScript, C++"},
            {"category": "Tools:", "items": "Docker, AWS, Kubernetes, Git, Jenkins"}
        ]
    }
    generate_resume_pdf(sample_data, "resume.pdf")
    print("Resume generated: resume.pdf")

if __name__ == "__main__":
    create_resume()
