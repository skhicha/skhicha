#!/usr/bin/env python3
"""
Auto-generates skhicha/skhicha/README.md by scanning all public repos:
- Detects languages, frameworks and libraries from each repo's language
  stats and dependency manifests (requirements.txt, package.json, pubspec.yaml,
  Dockerfile, pyproject.toml).
- Renders a colorful shields.io "tech I rely on" badge section.
- Builds a Featured Projects table from repo descriptions/topics (and
  ds-portfolio's subfolders, since that repo bundles multiple projects).
No personal/employer/college info is included anywhere in the output.
"""
import os, re, json, base64, sys
import urllib.request

USERNAME = "skhicha"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
API = "https://api.github.com"

def gh(path, token_required=False):
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json",
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})
    })
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        if token_required:
            raise
        return None

def gh_raw(owner, repo, path):
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{path}"
    req = urllib.request.Request(url, headers={
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})
    })
    try:
        with urllib.request.urlopen(req) as r:
            return r.read().decode(errors="ignore")
    except Exception:
        return None

# Badge definitions: keyword -> shields.io badge markdown
BADGES = {
    "python":      ("Python", "3776AB", "python", "white"),
    "java":        ("Java", "ED8B00", "openjdk", "white"),
    "c":           ("C", "00599C", "c", "white"),
    "dart":        ("Dart", "0175C2", "dart", "white"),
    "javascript":  ("JavaScript", "F7DF1E", "javascript", "black"),
    "typescript":  ("TypeScript", "3178C6", "typescript", "white"),
    "sql":         ("SQL", "4479A1", "postgresql", "white"),
    "html":        ("HTML5", "E34F26", "html5", "white"),
    "css":         ("CSS3", "1572B6", "css3", "white"),
    "pytorch":     ("PyTorch", "EE4C2C", "pytorch", "white"),
    "tensorflow":  ("TensorFlow", "FF6F00", "tensorflow", "white"),
    "transformers":("HuggingFace", "FFD21E", "huggingface", "black"),
    "langchain":   ("LangChain", "1C3C3C", "langchain", "white"),
    "scikit-learn":("Scikit--learn", "F7931E", "scikit-learn", "white"),
    "sklearn":     ("Scikit--learn", "F7931E", "scikit-learn", "white"),
    "openai":      ("OpenAI", "412991", "openai", "white"),
    "qdrant":      ("Qdrant", "DC244C", "qdrant", "white"),
    "redis":       ("Redis", "DC382D", "redis", "white"),
    "react":       ("React", "61DAFB", "react", "black"),
    "fastapi":     ("FastAPI", "009688", "fastapi", "white"),
    "flask":       ("Flask", "000000", "flask", "white"),
    "django":      ("Django", "092E20", "django", "white"),
    "flutter":     ("Flutter", "02569B", "flutter", "white"),
    "firebase":    ("Firebase", "FFCA28", "firebase", "black"),
    "postgres":    ("PostgreSQL", "4169E1", "postgresql", "white"),
    "docker":      ("Docker", "2496ED", "docker", "white"),
    "streamlit":   ("Streamlit", "FF4B4B", "streamlit", "white"),
    "ros":         ("ROS2", "22314E", "ros", "white"),
    "opencv":      ("OpenCV", "5C3EE8", "opencv", "white"),
    "pandas":      ("Pandas", "150458", "pandas", "white"),
    "numpy":       ("NumPy", "013243", "numpy", "white"),
    "node":        ("Node.js", "339933", "nodedotjs", "white"),
    "express":     ("Express", "000000", "express", "white"),
    "mongodb":     ("MongoDB", "47A248", "mongodb", "white"),
    "jest":        ("Jest", "C21325", "jest", "white"),
    "recharts":    ("Recharts", "22B5BF", "chartdotjs", "white"),
}

LANG_KEYWORDS = {
    "Python": "python", "Java": "java", "C": "c", "Dart": "dart",
    "JavaScript": "javascript", "TypeScript": "typescript",
    "HTML": "html", "CSS": "css", "CMake": None, "Jupyter Notebook": "python",
}

DEP_KEYWORDS = {
    # pip/requirements/pyproject
    "torch": "pytorch", "pytorch": "pytorch", "tensorflow": "tensorflow",
    "transformers": "transformers", "langchain": "langchain",
    "scikit-learn": "scikit-learn", "sklearn": "scikit-learn",
    "openai": "openai", "google-generativeai": "openai",
    "qdrant": "qdrant", "redis": "redis", "fastapi": "fastapi",
    "flask": "flask", "django": "django", "streamlit": "streamlit",
    "opencv-python": "opencv", "cv2": "opencv", "pandas": "pandas", "numpy": "numpy",
    "psycopg2": "postgres", "sqlalchemy": "postgres",
    # npm
    "react": "react", "recharts": "recharts", "express": "express",
    "mongoose": "mongodb", "jest": "jest",
    # pubspec
    "firebase_core": "firebase", "firebase_auth": "firebase",
    "cloud_firestore": "firebase", "flutter": "flutter",
}

def detect_from_text(text, found):
    if not text:
        return
    low = text.lower()
    for kw, badge_key in DEP_KEYWORDS.items():
        if kw in low:
            found.add(badge_key)

def scan_repo(repo):
    name = repo["name"]
    found = set()

    langs = gh(f"/repos/{USERNAME}/{name}/languages") or {}
    for lang in langs:
        key = LANG_KEYWORDS.get(lang)
        if key:
            found.add(key)

    for path in ["requirements.txt", "pyproject.toml", "package.json", "pubspec.yaml", "Dockerfile"]:
        content = gh_raw(USERNAME, name, path)
        detect_from_text(content, found)

    # ds-portfolio bundles multiple sub-projects; scan one level deeper
    if name == "ds-portfolio":
        contents = gh(f"/repos/{USERNAME}/{name}/contents/") or []
        for item in contents:
            if item.get("type") == "dir":
                for path in ["requirements.txt"]:
                    content = gh_raw(USERNAME, name, f"{item['name']}/{path}")
                    detect_from_text(content, found)

    # apps repo bundles multiple Flutter apps
    if name == "apps":
        contents = gh(f"/repos/{USERNAME}/{name}/contents/") or []
        for item in contents:
            if item.get("type") == "dir":
                content = gh_raw(USERNAME, name, f"{item['name']}/pubspec.yaml")
                detect_from_text(content, found)

    found.discard(None)
    return found

def extract_readme_description(owner, repo_name):
    """Pull a short description from the repo's own README: the first
    non-empty line that isn't a heading, badge/image line, or horizontal
    rule. Markdown formatting is stripped. Returns None if nothing usable
    is found."""
    content = gh_raw(owner, repo_name, "README.md")
    if not content:
        return None
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):          # heading
            continue
        if line.startswith(("<", "!", "[![", "---", "===")):  # badges/images/rules
            continue
        # strip basic markdown emphasis/links for a clean snippet
        clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        clean = re.sub(r"[*_`#]", "", clean).strip()
        if len(clean) < 10:                # too short to be a real description
            continue
        return (clean[:180] + "…") if len(clean) > 180 else clean
    return None

def synthesize_description(skills):
    """Last-resort fallback: build a plain description from detected tech
    when the repo has neither a GitHub description nor a usable README line."""
    if not skills:
        return "Code repository."
    labels = [BADGES[k][0].replace("--", "-") for k in sorted(skills) if k in BADGES]
    if not labels:
        return "Code repository."
    shown = labels[:4]
    rest = f" and {len(labels) - 4} more" if len(labels) > 4 else ""
    return f"Project using {', '.join(shown)}{rest}."

def render_badges(skill_keys):
    lines = []
    row = []
    for key in sorted(skill_keys):
        if key not in BADGES:
            continue
        label, color, logo, logocolor = BADGES[key]
        row.append(f'<img src="https://img.shields.io/badge/{label}-{color}?style=for-the-badge&logo={logo}&logoColor={logocolor}" />')
        if len(row) == 5:
            lines.append(" ".join(row))
            row = []
    if row:
        lines.append(" ".join(row))
    return "\n<br/>\n".join(lines)

def main():
    # /user/repos (authenticated) returns both public and private repos
    # the token's owner can see; falls back to public-only if no token is set.
    if TOKEN:
        repos = gh("/user/repos?per_page=100&affiliation=owner&visibility=all", token_required=True) or []
    else:
        repos = gh(f"/users/{USERNAME}/repos?per_page=100&type=public") or []
    repos = [r for r in repos if not r.get("fork")]

    all_skills = set()
    featured = []
    for r in repos:
        skills = scan_repo(r)
        all_skills |= skills  # private repos contribute to skill badges...
        if r["name"] != "skhicha" and not r.get("private"):
            desc = r.get("description")
            if not desc:
                desc = extract_readme_description(USERNAME, r["name"])
            if not desc:
                desc = synthesize_description(skills)
            featured.append({               # ...but only public repos are
                "name": r["name"],           # listed/linked in the public
                "description": desc,         # Projects table.
                "url": r["html_url"],
            })

    badges_md = render_badges(all_skills)
    featured_rows = "\n".join(
        f"| [{p['name']}]({p['url']}) | {p['description']} |" for p in featured
    )

    readme = f"""<h1 align="center">Hi there, I'm Shubham 👋</h1>

<p align="center">
<img src="https://komarev.com/ghpvc/?username={USERNAME}&style=flat-square&color=blueviolet" alt="Profile views" />
</p>

---

### 🛠️ When I build, I rely on

<p align="left">
{badges_md}
</p>

---

### 📂 Projects

| Repo | What it is |
|---|---|
{featured_rows}

---

### 📊 GitHub Stats

<p align="center">
<img src="https://github-readme-stats.vercel.app/api?username={USERNAME}&show_icons=true&theme=tokyonight&hide_border=true&count_private=true" height="165" />
<img src="https://github-readme-stats.vercel.app/api/top-langs/?username={USERNAME}&layout=compact&theme=tokyonight&hide_border=true" height="165" />
</p>

<p align="center"><sub>This README updates itself automatically — see <code>.github/workflows/update-readme.yml</code></sub></p>
"""
    return readme

if __name__ == "__main__":
    out = main()
    with open("README_generated.md", "w") as f:
        f.write(out)
    print(out)
