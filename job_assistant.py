"""
job_assistant.py — Human-sounding job application text generator.

Multi-pass LLM pipeline that produces cover letters, resumes, and Q&A answers
that read like a real person wrote them, not a chatbot.

Usage as a module:
    from job_assistant import generate_cover_letter, generate_resume_json, answer_question

Usage standalone:
    python job_assistant.py cover_letter --resume resume.txt --jd job.txt
    python job_assistant.py answer --resume resume.txt --jd job.txt --question "Why do you want this role?"
    python job_assistant.py resume --resume resume.txt --jd job.txt
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

__all__ = [
    "VoiceProfile",
    "DEFAULT_VOICE",
    "generate_cover_letter",
    "generate_resume_json",
    "answer_question",
    "audit_text",
    "extract_facts",
]

# ---------------------------------------------------------------------------
# Phase 1: AI-Tell Blacklists
# ---------------------------------------------------------------------------

AI_TELL_WORDS: list[str] = [
    "delve", "tapestry", "nuanced", "nuance", "meticulous", "commendable",
    "bustling", "leverage", "foster", "facilitate", "paramount", "pivotal",
    "straightforward", "groundbreaking", "multifaceted", "embark", "realm",
    "landscape", "beacon", "hallmark", "testament", "certainly", "absolutely",
    "indeed", "moreover", "furthermore", "nevertheless", "henceforth",
    "aforementioned", "utilize", "utilization", "synergy", "synergize",
    "holistic", "robust", "cutting-edge", "spearheaded", "orchestrated",
    "revolutionized", "transformative", "innovative", "unparalleled",
    "underscore", "underscores", "encompasses", "invaluable",
]

AI_TELL_PHRASES: list[str] = [
    "I am writing to express my interest",
    "I am excited about the opportunity",
    "I am thrilled to apply",
    "with a passion for",
    "I believe my background",
    "aligns perfectly with",
    "make me an ideal candidate",
    "I look forward to hearing from you at your earliest convenience",
    "thank you for your time and consideration",
    "I would be a great fit",
    "in today's fast-paced",
    "in today's rapidly evolving",
    "it is worth noting",
    "it is imperative",
    "it goes without saying",
    "in essence",
    "in summary",
    "in conclusion",
    "I am confident that",
    "I am eager to",
    "unique combination of",
    "well-positioned to",
    "a strong foundation in",
    "my skill set",
    "poised to contribute",
    "dynamic environment",
    "proven track record",
    "results-driven",
    "detail-oriented",
    "team player",
    "go-to person",
    "wear many hats",
    "hit the ground running",
    "think outside the box",
    "move the needle",
    "deep dive",
    "circle back",
    "at the end of the day",
    "bring to the table",
]

# Rules injected into cover letter and Q&A prompts to disrupt AI-typical structure.
STRUCTURAL_RULES = """\
STRUCTURAL RULES — follow these exactly:
- Use contractions everywhere: I'm, I've, I'll, didn't, doesn't, won't, can't, it's.
- Vary sentence length aggressively. Mix very short sentences (under 6 words) with longer ones. Real writing is bursty.
- NEVER write 4 equal-length paragraphs. Break the pattern: a short 1-sentence paragraph is fine. An asymmetric layout is human.
- Embed skills into narrative. Show, don't list. Wrong: "I am proficient in Python, React, and AWS." Right: "I built the ingestion pipeline in Python, then moved the frontend to React when we outgrew jQuery."
- Include at least one specific challenge or tension that was overcome — not everything was perfect.
- Every paragraph must contain at least one specific: a number, a proper noun (company, tool, person, project), or a concrete outcome.
- Do NOT parrot the job description back. Reference it indirectly through your own experience.
- Do NOT praise the company with generic adjectives. If you mention the company, reference something concrete (a product, a blog post, a recent event).
- Do NOT use bullet points unless explicitly asked.
- One em-dash or parenthetical aside is fine. More than two looks AI-generated.
- Do NOT end every sentence on a positive note. Neutral statements are human.
- Avoid tricolon patterns (listing exactly 3 things in a row, e.g. "X, Y, and Z") more than once.\
"""

# Rules for resume generation — ATS-optimized, professional, not conversational.
RESUME_STRUCTURAL_RULES = """\
RESUME WRITING RULES — follow these exactly:
- Summary: 2-3 sentences, professional tone, NO contractions, NO first-person pronouns ("I", "my", "me"). Write as a noun phrase or role descriptor (e.g. "Senior backend engineer with 10+ years..."). ATS-friendly — include key terms from the JD naturally.
- Experience bullets: Start each with a strong, varied action verb. Rotate from: Built, Designed, Migrated, Reduced, Automated, Led, Implemented, Deployed, Refactored, Scaled, Integrated, Introduced, Established, Cut, Shipped. Never start two consecutive bullets with the same verb.
- NO contractions. NO first-person "I". Resumes use implied first person (verb-first bullets).
- Quantify every achievement where data exists: percentages, time saved, user counts, team sizes, request volumes.
- DYNAMIC BULLET COUNT based on tenure at each role. Use today's date to calculate duration for any role marked "Present". Target bullet counts: under 12 months -> 2-3 bullets; 1-2 years -> 3-4 bullets; 2-4 years -> 4-6 bullets; 4+ years -> 6-8 bullets. Do NOT assign the same bullet count to all roles.
- Mix bullet formats for variety: some lead with the tool/tech ("Kafka-based event pipeline..."), some with the outcome ("Cut API latency 35% by..."), some with context ("As the team scaled past 100K users...").
- Every bullet must earn its place — no filler. If a bullet doesn't contain a specific technology, outcome, or scale metric, cut it.
- Avoid: "responsible for", "helped with", "worked on", "assisted in". Replace with active verbs and outcomes.\
"""

# ---------------------------------------------------------------------------
# Phase 2: Voice Profile
# ---------------------------------------------------------------------------


@dataclass
class VoiceProfile:
    """Captures a person's writing voice for injection into prompts."""

    name: str = "default"
    tone: str = "direct, conversational, professional but not corporate"
    quirks: str = "uses dashes occasionally, favors short sentences, sometimes drops into very casual phrasing"
    writing_samples: list[str] = field(default_factory=list)


DEFAULT_VOICE = VoiceProfile()


def extract_voice_traits(samples: list[str]) -> str:
    """Build a voice-description string from writing samples for prompt injection."""
    if not samples:
        return ""
    joined = "\n---\n".join(samples[:5])  # cap at 5 samples
    return (
        "Here are samples of the candidate's own writing. "
        "Match this voice — the rhythm, word choice, directness, and personality. "
        "Do NOT copy the content, only the style.\n\n"
        f"{joined}\n"
    )


# ---------------------------------------------------------------------------
# Phase 3: Core Pipeline Functions
# ---------------------------------------------------------------------------


def _create_client(api_key: str):
    """Thin wrapper — same pattern as keyboard_expander.py."""
    from openai import OpenAI

    return OpenAI(api_key=api_key)


def _blacklist_block() -> str:
    """Format the blacklist for prompt injection."""
    words = ", ".join(AI_TELL_WORDS)
    phrases = "\n".join(f'  - "{p}"' for p in AI_TELL_PHRASES)
    return (
        f"NEVER use any of these words: {words}.\n"
        f"NEVER use any of these phrases:\n{phrases}\n"
    )


def _build_system_prompt(
    task: str,
    voice: VoiceProfile,
    extra_rules: str = "",
) -> str:
    """Assemble the full system prompt: blacklist + structure + voice + task."""
    # Resumes are ATS-driven — casual voice quirks hurt more than they help.
    if task == "resume":
        voice_block = ""
        structural_rules = RESUME_STRUCTURAL_RULES
    else:
        voice_block = f"VOICE: {voice.tone}. {voice.quirks}.\n"
        if voice.writing_samples:
            voice_block += extract_voice_traits(voice.writing_samples) + "\n"
        structural_rules = STRUCTURAL_RULES

    task_instructions = {
        "cover_letter": (
            "You are ghostwriting a cover letter for the candidate below. "
            "Write it in first person as if you ARE the candidate. "
            "This must read like a real human sat down and wrote it — not a template, not a chatbot. "
            "Open with something specific (an anecdote, a direct claim, a surprising statement) — "
            "NEVER with 'I am writing to...' or 'I am excited about...'. "
            "Close naturally — something like 'Happy to share more if this sounds like a fit' or "
            "'Let me know if you'd like to see code samples.' NOT 'I look forward to hearing from you.' "
            "Keep it under 350 words. No subject line. No bullet points."
        ),
        "resume": (
            "You are generating a professional, ATS-optimized resume for the candidate. "
            "The summary must be noun-phrase style — no first-person pronouns, no contractions. "
            "Experience bullets must be concrete, quantified, and keyword-rich for ATS scanning. "
            "Use varied action verbs — never start two consecutive bullets the same way. "
            "Assign more bullets to longer tenures and fewer to shorter ones using the dynamic bullet count rule. "
            "No conversational phrasing anywhere. No contractions. Output strict JSON matching the schema provided."
        ),
        "qa_answer": (
            "You are answering an application question on behalf of the candidate. "
            "Write in first person as if you ARE the candidate. "
            "Be direct and specific. Answer the actual question — don't pad with filler. "
            "Use the candidate's real experience. Keep it concise."
        ),
    }

    return (
        f"{task_instructions.get(task, '')}\n\n"
        f"{voice_block}"
        f"{_blacklist_block()}\n"
        f"{structural_rules}\n"
        f"{extra_rules}"
    ).strip()


def extract_facts(
    resume: str,
    job_description: str,
    client,
    model: str = "gpt-4o-mini",
) -> str:
    """
    Pass 1 — extract concrete facts from resume + JD.

    Returns structured bullet points: numbers, project names, tools,
    outcomes, and the overlap between the resume and the JD.
    No prose — just raw material for the writing pass.
    """
    prompt = (
        "I need you to extract facts for a job application. Do NOT write prose. "
        "Output ONLY a structured list of bullet points.\n\n"
        "From the RESUME, extract:\n"
        "- Specific numbers (years of experience, team sizes, percentages, dollar amounts)\n"
        "- Company names, project names, product names\n"
        "- Tools, languages, frameworks actually used (not just listed)\n"
        "- Concrete outcomes and accomplishments\n"
        "- Job titles and date ranges\n\n"
        "From the JOB DESCRIPTION, extract:\n"
        "- Required skills and qualifications\n"
        "- Key responsibilities\n"
        "- Company name and role title\n"
        "- Any specifics: team size, tech stack, product area\n\n"
        "Then produce a MATCH section:\n"
        "- Which resume facts directly address which JD requirements\n"
        "- Gaps: JD requirements not covered by the resume (be honest)\n\n"
        f"RESUME:\n{resume}\n\n"
        f"JOB DESCRIPTION:\n{job_description}"
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,  # low temp for factual extraction
    )
    return resp.choices[0].message.content or ""


def audit_text(text: str) -> list[str]:
    """
    Scan text for AI tells. Returns list of flagged words/phrases found.

    >>> audit_text("I am writing to express my interest in this role.")
    ['I am writing to express my interest']
    """
    flagged: list[str] = []

    for phrase in AI_TELL_PHRASES:
        if re.search(re.escape(phrase), text, re.IGNORECASE):
            flagged.append(phrase)

    for word in AI_TELL_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE):
            flagged.append(word)

    return flagged


def _rewrite_flagged(
    text: str,
    flagged: list[str],
    client,
    model: str,
    system_prompt: str,
    temperature: float = 0.95,
) -> str:
    """
    Targeted rewrite: replace sentences containing flagged AI tells.
    Keeps everything else intact to avoid full regeneration drift.
    """
    flagged_list = ", ".join(f'"{f}"' for f in flagged)
    prompt = (
        "The following text contains AI-sounding words/phrases that must be replaced. "
        f"Flagged items: {flagged_list}\n\n"
        "Rewrite ONLY the sentences that contain these flagged items. "
        "Keep every other sentence exactly as-is. "
        "Replace the flagged words with natural, human alternatives. "
        "Do NOT rewrite the entire text. Do NOT add new content. "
        "Output the full text with only the flagged sentences changed.\n\n"
        f"TEXT:\n{text}"
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
    )
    return resp.choices[0].message.content or text


def _run_pipeline(
    user_prompt: str,
    system_prompt: str,
    client,
    model: str,
    temperature: float,
    max_audit_passes: int,
) -> str:
    """Core generate-then-audit loop shared by all generators."""
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    text = resp.choices[0].message.content or ""

    # Audit loop
    for _ in range(max_audit_passes):
        flagged = audit_text(text)
        if not flagged:
            break
        text = _rewrite_flagged(text, flagged, client, model, system_prompt, temperature)

    return text.strip()


# ---------------------------------------------------------------------------
# Phase 4: Public API
# ---------------------------------------------------------------------------


def generate_cover_letter(
    resume: str,
    job_description: str,
    *,
    api_key: str | None = None,
    model: str = "gpt-4o-mini",
    voice: VoiceProfile | None = None,
    temperature: float = 0.95,
    max_audit_passes: int = 2,
    date_str: str | None = None,
) -> str:
    """
    Generate a human-sounding cover letter via the 3-pass pipeline.

    Returns plain text (no PDF generation — caller handles that).
    """
    api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY required")

    voice = voice or DEFAULT_VOICE
    client = _create_client(api_key)
    date_str = date_str or datetime.now().strftime("%B %d, %Y")

    # Pass 1: fact extraction
    facts = extract_facts(resume, job_description, client, model)

    # Pass 2 + 3: write + audit
    system_prompt = _build_system_prompt("cover_letter", voice)
    user_prompt = (
        f"Today's date: {date_str}\n\n"
        f"EXTRACTED FACTS (use these, don't invent new ones):\n{facts}\n\n"
        f"CANDIDATE'S RESUME:\n{resume}\n\n"
        f"JOB DESCRIPTION:\n{job_description}\n\n"
        "Write the cover letter now."
    )

    return _run_pipeline(user_prompt, system_prompt, client, model, temperature, max_audit_passes)


def generate_resume_json(
    resume: str,
    job_description: str,
    *,
    api_key: str | None = None,
    model: str = "gpt-4o-mini",
    voice: VoiceProfile | None = None,
    temperature: float = 0.9,
) -> dict[str, Any]:
    """
    Generate a tailored resume as a JSON dict matching the schema used by generate_resume.py.

    Schema:
    {
      "name": str,
      "contact": [str, ...],
      "links": [str, ...],
      "summary": str,
      "experience": [{"title", "company", "location", "date", "description": [str]}],
      "education": [{"degree", "institution", "location", "date", "details": [str]}],
      "skills": [{"category": str, "items": str}]
    }
    """
    api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY required")

    voice = voice or DEFAULT_VOICE
    client = _create_client(api_key)

    # Pass 1: fact extraction
    facts = extract_facts(resume, job_description, client, model)

    # Pass 2: JSON generation with humanized descriptions
    system_prompt = _build_system_prompt(
        "resume",
        voice,
        extra_rules=(
            "Output your response strictly as a JSON object matching this structure. "
            "DO NOT include markdown block characters like ```json or ```. Just raw JSON.\n\n"
            "{\n"
            '  "name": "Applicant Name",\n'
            '  "contact": ["City, State", "Phone", "Email"],\n'
            '  "links": ["LinkedIn", "GitHub", "Portfolio"],\n'
            '  "summary": "Brief professional summary.",\n'
            '  "experience": [\n'
            '    {"title": "Job Title", "company": "Company Name", "location": "City, State", '
            '"date": "Date Range", "description": ["Bullet point 1", "Bullet point 2"]}\n'
            '  ],\n'
            '  "education": [\n'
            '    {"degree": "Degree", "institution": "University Name", "location": "City, State", '
            '"date": "Date Range", "details": ["Detail 1"]}\n'
            '  ],\n'
            '  "skills": [\n'
            '    {"category": "Lang", "items": "Skill1, Skill2"}\n'
            '  ]\n'
            "}\n\n"
            "For 'category' in skills: use a single short word, max 12 chars. "
            "Examples: Lang, Frameworks, Tools, DB, Cloud, OS, DevOps, ML, Infra, QA, Mobile, Web, Security.\n"
        ),
    )

    today_str = datetime.now().strftime("%B %d, %Y")
    user_prompt = (
        f"TODAY'S DATE: {today_str} — use this to calculate tenure for any role marked 'Present' "
        f"when determining dynamic bullet count.\n\n"
        f"EXTRACTED FACTS:\n{facts}\n\n"
        f"CANDIDATE'S ORIGINAL RESUME:\n{resume}\n\n"
        f"TARGET JOB DESCRIPTION:\n{job_description}\n\n"
        "Generate the tailored resume JSON now."
    )

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"

    # Strip markdown fences if model ignores the instruction
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw.strip())

    data: dict[str, Any] = json.loads(raw)

    # Audit the prose fields and rewrite if needed
    prose_fields_to_audit = []
    if "summary" in data:
        prose_fields_to_audit.append(("summary", data["summary"]))
    for exp in data.get("experience", []):
        for i, bullet in enumerate(exp.get("description", [])):
            prose_fields_to_audit.append((f"exp_bullet", bullet))

    # Collect all prose into one block, audit once
    all_prose = "\n".join(v for _, v in prose_fields_to_audit)
    flagged = audit_text(all_prose)
    if flagged:
        audit_sys = _build_system_prompt("resume", voice)
        rewritten = _rewrite_flagged(all_prose, flagged, client, model, audit_sys)
        # Re-parse the rewritten bullets back. Since this is best-effort,
        # we replace the summary at minimum.
        lines = [l for l in rewritten.split("\n") if l.strip()]
        if lines and "summary" in data:
            data["summary"] = lines[0]

    return data


def answer_question(
    question: str,
    resume: str,
    job_description: str,
    *,
    api_key: str | None = None,
    model: str = "gpt-4o-mini",
    voice: VoiceProfile | None = None,
    temperature: float = 0.95,
    max_sentences: int = 3,
    max_audit_passes: int = 2,
) -> str:
    """
    Answer an application-form question in human voice.

    Returns a concise answer (default: up to 3 sentences).
    """
    api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY required")

    voice = voice or DEFAULT_VOICE
    client = _create_client(api_key)

    system_prompt = _build_system_prompt(
        "qa_answer",
        voice,
        extra_rules=f"Keep the answer to {max_sentences} sentences or fewer. Be direct.",
    )
    user_prompt = (
        f"CANDIDATE'S RESUME:\n{resume}\n\n"
        f"JOB DESCRIPTION:\n{job_description}\n\n"
        f"QUESTION: {question}\n\n"
        "Answer in the candidate's voice."
    )

    return _run_pipeline(user_prompt, system_prompt, client, model, temperature, max_audit_passes)


# ---------------------------------------------------------------------------
# Phase 5: CLI for standalone testing
# ---------------------------------------------------------------------------


def _read_file_arg(path: str) -> str:
    """Read a file path or return the string as-is if not a valid path."""
    expanded = os.path.expanduser(path)
    if os.path.isfile(expanded):
        with open(expanded, "r", encoding="utf-8") as f:
            return f.read()
    return path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Human-sounding job application text generator"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # Shared arguments
    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--resume", required=True, help="Path to resume text file or raw text")
        p.add_argument("--jd", required=True, help="Path to job description text file or raw text")
        p.add_argument("--api-key", default=None, help="OpenAI API key (or set OPENAI_API_KEY)")
        p.add_argument("--model", default="gpt-4o-mini")
        p.add_argument("--temperature", type=float, default=0.95)
        p.add_argument("--voice-samples", nargs="*", default=[], help="Paths to writing sample files")

    # cover_letter
    cl = sub.add_parser("cover_letter", help="Generate a cover letter")
    add_common(cl)

    # answer
    ans = sub.add_parser("answer", help="Answer an application question")
    add_common(ans)
    ans.add_argument("--question", required=True, help="The question to answer")
    ans.add_argument("--max-sentences", type=int, default=3)

    # resume
    res = sub.add_parser("resume", help="Generate a tailored resume JSON")
    add_common(res)

    # audit (utility)
    aud = sub.add_parser("audit", help="Audit text for AI tells")
    aud.add_argument("--text", required=True, help="Path to text file or raw text to audit")

    args = parser.parse_args()

    if args.command == "audit":
        text = _read_file_arg(args.text)
        flagged = audit_text(text)
        if flagged:
            print(f"FLAGGED ({len(flagged)} items):")
            for f in flagged:
                print(f"  - {f}")
        else:
            print("CLEAN — no AI tells detected.")
        return

    resume = _read_file_arg(args.resume)
    jd = _read_file_arg(args.jd)

    voice = DEFAULT_VOICE
    if args.voice_samples:
        samples = [_read_file_arg(s) for s in args.voice_samples]
        voice = VoiceProfile(writing_samples=samples)

    if args.command == "cover_letter":
        result = generate_cover_letter(
            resume, jd,
            api_key=args.api_key,
            model=args.model,
            temperature=args.temperature,
            voice=voice,
        )
        print(result)

    elif args.command == "answer":
        result = answer_question(
            args.question, resume, jd,
            api_key=args.api_key,
            model=args.model,
            temperature=args.temperature,
            voice=voice,
            max_sentences=args.max_sentences,
        )
        print(result)

    elif args.command == "resume":
        data = generate_resume_json(
            resume, jd,
            api_key=args.api_key,
            model=args.model,
            temperature=args.temperature,
            voice=voice,
        )
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
