import json
from fpdf import FPDF, XPos, YPos

class ResumePDF(FPDF):
    def __init__(self, data, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = data

    def write_header(self):
        # Name and Contact Info
        self.set_font("helvetica", "B", 24)
        name = self.data.get("name", "Name")
        self.cell(0, 10, name, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.set_font("helvetica", "", 10)
        
        contact_info = " | ".join(self.data.get("contact", []))
        if contact_info:
            self.cell(0, 5, contact_info, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
            
        links = " | ".join(self.data.get("links", []))
        if links:
            self.cell(0, 5, links, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.ln(10)

    def section_title(self, title):
        self.set_font("helvetica", "B", 12)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 8, title.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True)
        self.ln(2)

    def entry(self, title, subtitle, date, description):
        self.set_font("helvetica", "B", 11)
        self.cell(140, 6, title, align="L")
        self.set_font("helvetica", "I", 10)
        self.cell(0, 6, date, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")
        self.set_font("helvetica", "B", 10)
        self.cell(0, 6, subtitle, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("helvetica", "", 10)
        for bullet in description:
            # handle bullets properly and replace special characters
            bullet = bullet.replace("\u2013", "-").replace("\u2014", "-")
            self.multi_cell(0, 5, f"- {bullet}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(4)

def generate_resume_pdf(data: dict, filepath: str):
    pdf = ResumePDF(data)
    pdf.set_margins(25, 25, 25)
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()
    
    pdf.write_header()
    
    # Summary Section
    if data.get("summary"):
        pdf.section_title("Summary")
        pdf.set_font("helvetica", "", 10)
        summary = data["summary"].replace("\u2013", "-").replace("\u2014", "-")
        pdf.multi_cell(0, 5, summary, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(4)

    # Skills Section
    if data.get("skills"):
        pdf.section_title("Skills")
        # Pre-compute max category width for uniform alignment
        pdf.set_font("helvetica", "B", 10)
        categories = []
        for skill in data["skills"]:
            cat = skill.get("category", "").strip().rstrip(":")
            categories.append(cat + ":" if cat else "")
        max_cat_w = max((pdf.get_string_width(c) for c in categories), default=0) + 4
        for skill, category in zip(data["skills"], categories):
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(max_cat_w, 6, category)
            pdf.set_font("helvetica", "", 10)
            remaining_w = pdf.w - pdf.r_margin - pdf.get_x()
            pdf.multi_cell(remaining_w, 6, skill.get("items", ""), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Experience Section
    if data.get("experience"):
        pdf.section_title("Experience")
        for exp in data["experience"]:
            pdf.entry(
                exp.get("title", ""),
                exp.get("company", ""),
                exp.get("date", ""),
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
