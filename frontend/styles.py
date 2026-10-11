CSS = """
<style>
:root { --ink: #243d34; --muted: #7c857b; --line: #dedfd4; --accent: #216052; }
html, body, [class*="css"], [data-testid="stApp"] {
    font-family: 'Noto Sans SC', 'Microsoft YaHei', sans-serif;
}
[data-testid="stAppViewContainer"] { background: #f5f4ef; }
.block-container { padding: 2.5rem 2.8rem 3rem; max-width: 1800px; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { opacity: .45; }
h1, h2, h3 { color: var(--ink); letter-spacing: -.03em; }
h2 { font-size: 1.2rem !important; font-weight: 600 !important; }
h3 { font-size: 1.05rem !important; }
p, label { line-height: 1.7; }
[data-testid="stCaptionContainer"] { color: var(--muted); }
[data-testid="stVerticalBlockBorderWrapper"] > div {
    border-radius: 14px !important; border-color: var(--line) !important;
}
[data-testid="stButton"] button, [data-testid="stDownloadButton"] button {
    border-radius: 8px; min-height: 2.75rem; font-weight: 500;
}
[data-testid="stButton"] button[kind="primary"] {
    background: var(--accent); border: 1px solid var(--accent);
}
[data-testid="stButton"] button[kind="secondary"] {
    background: #fafaf6; border: 1px solid #d6dbcf; color: var(--ink);
}
[data-testid="stButton"] button:hover { border-color: #216052; }
[data-testid="stMetricValue"] { font-size: 1.7rem; color: var(--ink); }
[data-testid="stMetricLabel"] { color: #768173; }
[data-testid="stExpander"] { background: #fafaf7; border-color: var(--line); }
div[data-baseweb="input"], div[data-baseweb="textarea"], div[data-baseweb="select"] > div {
    background: #eeeee6; border-radius: 8px;
}
hr { border-color: var(--line); margin: 1.4rem 0; }
.masthead { display: flex; justify-content: space-between; align-items: center;
    padding-bottom: 23px; margin-bottom: 28px; border-bottom: 1px solid var(--line); }
.wordmark { font-family: Georgia, serif; font-weight: 700; font-size: 30px;
    letter-spacing: -1px; color: #244e40; }
.wordmark span { font-family: sans-serif; font-size: 10px; letter-spacing: 3px;
    margin-left: 16px; color: #819178; font-weight: 500; }
.mastnote { font-size: 11px; color: #80907a; letter-spacing: 2px; }
.eyebrow { font-size: 10px; letter-spacing: 2px; color: #849075; margin-bottom: 9px; }
.hero-title { font-size: 32px; letter-spacing: -1px; color: #273f34;
    font-weight: 600; margin-bottom: 7px; }
.hero-subtitle { color: #7b8478; font-size: 13px; margin-bottom: 25px; }
.section-number { font-family: Georgia, serif; font-size: 12px; color: #8c987e;
    letter-spacing: 2px; margin-bottom: 5px; }
.section-title { font-size: 17px; font-weight: 600; color: #2c4136; margin-bottom: 4px; }
.section-note { color: #899080; font-size: 11px; margin-bottom: 20px; }
.status { display: inline-block; padding: 5px 12px; border-radius: 20px;
    background: #e5ebdf; color: #537348; font-size: 11px; letter-spacing: .4px; }
.empty-quest { border: 1px dashed #cfd5c5; border-radius: 12px; padding: 40px 25px;
    text-align: center; background: #f0f1e8; margin-top: 12px; }
.empty-symbol { font-family: Georgia, serif; font-size: 45px; color: #819d77;
    margin-bottom: 20px; }
.empty-quest strong { color: #355b48; font-weight: 500; font-size: 18px; }
.empty-quest p { color: #909582; font-size: 12px; margin-top: 10px; }
.legend { display: flex; gap: 16px; font-size: 10px; color: #7f887a; padding: 3px 0 14px; }
.legend i { display: inline-block; width: 7px; height: 7px; border-radius: 50%;
    margin-right: 4px; vertical-align: 1px; }
.footer { border-top: 1px solid var(--line); color: #959b8e; font-size: 10px;
    letter-spacing: 1px; margin-top: 30px; padding-top: 18px; }
@media (max-width: 850px) {
    .block-container { padding: 1.5rem 1rem; }
    .mastnote { display: none; }
    .hero-title { font-size: 26px; }
}
</style>
"""


def section(number: str, title: str, note: str) -> str:
    """Only called with trusted, static UI labels."""
    return (
        f'<div class="section-number">{number}</div>'
        f'<div class="section-title">{title}</div>'
        f'<div class="section-note">{note}</div>'
    )
