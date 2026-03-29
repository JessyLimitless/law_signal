#!/usr/bin/env python3
"""
상법 Signal 전자책 빌드 스크립트
MD 파일들을 읽어 단일 HTML 전자책으로 변환
"""

import re
import markdown
from pathlib import Path

# ─── 설정 ───
BASE_DIR = Path(__file__).parent
MD_FILES = [
    "sangbeop_1-1_v2.md",
    "sangbeop_1-2_1-3_1-4_FINAL.md",
    "sangbeop_2-1_2-2_2-3_2-4_FINAL.md",
    "sangbeop_3-1_3-2_3-3_3-4_FINAL.md",
    "sangbeop_4-1_4-2_4-3_FINAL.md",
    "sangbeop_5-1_5-2_FINAL.md",
]
OUTPUT = BASE_DIR / "index.html"

CHAPTERS = {
    1: {"en": "Logic & Governance", "ko": "이사의 의무와 경영판단의 쟁점", "icon": "01"},
    2: {"en": "Memory & Capital", "ko": "자본 거래와 주주권의 충돌", "icon": "02"},
    3: {"en": "Security & Structure", "ko": "M&A와 지배구조 개편의 법적 이슈", "icon": "03"},
    4: {"en": "Commit & Log", "ko": "상업등기와 지배구조 품질", "icon": "04"},
    5: {"en": "Signal Integration", "ko": "두 책을 하나로", "icon": "05"},
}


# ─── 마크다운 → HTML 변환 ───
def convert_md(text: str) -> str:
    """마크다운을 HTML로 변환하고 커스텀 컴포넌트를 적용"""
    html = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "nl2br"],
        output_format="html5",
    )
    return html


def extract_sections(md_text: str) -> list[dict]:
    """마크다운 텍스트를 섹션 단위로 분리"""
    lines = md_text.split("\n")
    sections = []
    current = None
    buffer = []

    for line in lines:
        # H1 또는 H2 — 새 섹션 시작
        m_h1 = re.match(r"^#\s+(.+)$", line)
        m_h2 = re.match(r"^##\s+(.+)$", line)

        if m_h1 or m_h2:
            if current:
                current["body"] = "\n".join(buffer)
                sections.append(current)
            title = (m_h1 or m_h2).group(1).strip()
            level = 1 if m_h1 else 2
            current = {"title": title, "level": level, "body": ""}
            buffer = []
        else:
            buffer.append(line)

    if current:
        current["body"] = "\n".join(buffer)
        sections.append(current)

    return sections


def classify_section(title: str) -> dict:
    """섹션 제목으로 유형 분류"""
    info = {"type": "content", "id": "", "label": "", "display_title": title}

    # 챕터 오프너
    if "챕터 오프너" in title or "오프너" in title:
        info["type"] = "opener"
        m = re.search(r'[—–-]\s*"(.+)"', title)
        info["label"] = m.group(1) if m else title
        return info

    # 섹션 번호 매칭 (1.1, 2.3, 5.5 등)
    m = re.match(r"(\d+\.\d+)\s+(.+?)(?::\s*(.+))?$", title)
    if m:
        info["type"] = "section"
        info["id"] = f"sec-{m.group(1).replace('.', '-')}"
        info["label"] = m.group(1)
        info["display_title"] = m.group(2).strip()
        if m.group(3):
            info["subtitle"] = m.group(3).strip()
        return info

    # 장 제목 (제1장, 제2장 등)
    m = re.match(r"제(\d+)장", title)
    if m:
        info["type"] = "part"
        ch = int(m.group(1))
        info["chapter"] = ch
        info["id"] = f"part-{ch}"
        return info

    # 에필로그
    if "에필로그" in title:
        info["type"] = "section"
        info["id"] = "sec-5-5"
        info["label"] = "5.5"
        info["display_title"] = title
        return info

    return info


def process_body_html(html: str) -> str:
    """변환된 HTML에 커스텀 스타일 클래스 적용"""

    # 판례 포인트 블록 감지 및 래핑
    html = re.sub(
        r"<blockquote>\s*<p><strong>📋?\s*판례\s*포인트([^<]*)</strong>",
        r'<blockquote class="case-law-box"><p><strong>판례 포인트\1</strong>',
        html,
    )
    # 판례 포인트 (📋 없는 변형)
    html = re.sub(
        r"<blockquote>\s*<p><strong>판례\s*포인트([^<]*)</strong>",
        r'<blockquote class="case-law-box"><p><strong>판례 포인트\1</strong>',
        html,
    )

    # 교훈 블록
    html = re.sub(
        r"<blockquote>\s*<p>([^<]*(?:확인하라|경계하라|추적하라|검토하라|계산하라|재검토|의심하라|주시하라)[^<]*)</p>",
        r'<blockquote class="lesson-box"><p>\1</p>',
        html,
    )

    # 일반 인용문 (이탤릭 닫는 문장 — 격언류)
    html = re.sub(
        r"<blockquote>\s*<p><em>\"(.+?)\"</em></p>\s*</blockquote>",
        r'<div class="epigraph"><p>"\1"</p></div>',
        html,
    )
    html = re.sub(
        r"<blockquote>\s*<p><em>\u201c(.+?)\u201d</em></p>\s*</blockquote>",
        r'<div class="epigraph"><p>"\1"</p></div>',
        html,
    )

    # 코드 블록 → DART 박스 또는 체크리스트
    html = re.sub(
        r'<pre><code>(\s*(?:Step\s*\d|DART|\[주요사항|사업보고서|연결\s*재무|자사주|공시가|이\s*두\s*책|DART\s*공시|DART\s*vs|자동\s*탐지|□).+?)</code></pre>',
        r'<div class="dart-box"><pre>\1</pre></div>',
        html,
        flags=re.DOTALL,
    )

    # 코드 블록 내 체크리스트 변환
    html = re.sub(
        r'<pre><code>(\s*(?:이사회\s*연간|특수관계자|현행|개정|판정|배당금|FCF|최대\s*희석률|이사회\s*품질).+?)</code></pre>',
        r'<div class="checklist-box"><pre>\1</pre></div>',
        html,
        flags=re.DOTALL,
    )

    # 남은 코드블록 → 일반 dart-box
    html = re.sub(
        r"<pre><code>(.+?)</code></pre>",
        r'<div class="dart-box"><pre>\1</pre></div>',
        html,
        flags=re.DOTALL,
    )

    # 테이블 래핑
    html = re.sub(
        r"(<table>)",
        r'<div class="table-wrap">\1',
        html,
    )
    html = re.sub(
        r"(</table>)",
        r"\1</div>",
        html,
    )

    # H3 서브섹션 분류
    # ① 법적 쟁점
    html = re.sub(
        r"<h3>([①②③④⑤⑥][\s\-]*(?:법적\s*쟁점|왜\s).*?)</h3>",
        r'<h3 class="sub-legal">\1</h3>',
        html,
    )
    # ② 법률의 구조
    html = re.sub(
        r"<h3>([①②③④⑤⑥][\s\-]*법률의\s*구조.*?)</h3>",
        r'<h3 class="sub-structure">\1</h3>',
        html,
    )
    # ③ 케이스 스터디
    html = re.sub(
        r"<h3>(.*?📋.*?케이스.*?)</h3>",
        r'<h3 class="sub-case">\1</h3>',
        html,
    )
    html = re.sub(
        r"<h3>(.*?비교\s*케이스.*?)</h3>",
        r'<h3 class="sub-case">\1</h3>',
        html,
    )
    # ④ 시그널 대조표
    html = re.sub(
        r"<h3>(.*?시그널\s*대조표.*?)</h3>",
        r'<h3 class="sub-signal">\1</h3>',
        html,
    )
    html = re.sub(
        r"<h3>(.*?응모\s*판단.*?)</h3>",
        r'<h3 class="sub-signal">\1</h3>',
        html,
    )
    # ⑤ DART 실전 박스
    html = re.sub(
        r"<h3>(.*?DART.*?)</h3>",
        r'<h3 class="sub-dart">\1</h3>',
        html,
    )
    # 내재가치 체크리스트
    html = re.sub(
        r"<h3>(.*?체크리스트.*?)</h3>",
        r'<h3 class="sub-checklist">\1</h3>',
        html,
    )
    # 심화
    html = re.sub(
        r"<h3>(.*?심화.*?)</h3>",
        r'<h3 class="sub-deep">\1</h3>',
        html,
    )

    # 숫자 기반 서브섹션 (챕터 2 스타일: ### 1 법적 쟁점)
    html = re.sub(
        r"<h3>(\d[\s\-]*법적\s*쟁점.*?)</h3>",
        r'<h3 class="sub-legal">\1</h3>',
        html,
    )
    html = re.sub(
        r"<h3>(\d[\s\-]*법률의\s*구조.*?)</h3>",
        r'<h3 class="sub-structure">\1</h3>',
        html,
    )
    html = re.sub(
        r"<h3>(\d[\-\s]*[AB]?\s*케이스.*?)</h3>",
        r'<h3 class="sub-case">\1</h3>',
        html,
    )
    html = re.sub(
        r"<h3>(\d[\s\-]*투자자\s*시그널.*?)</h3>",
        r'<h3 class="sub-signal">\1</h3>',
        html,
    )
    html = re.sub(
        r"<h3>(\d[\s\-]*DART.*?)</h3>",
        r'<h3 class="sub-dart">\1</h3>',
        html,
    )

    # H4 케이스 내 서브 (발단, 전개, 위기, 결말, 교훈, 역설)
    for kw in ["발단", "전개", "위기", "결말", "교훈", "역설"]:
        html = re.sub(
            rf"<h4><strong>({kw}.*?)</strong></h4>",
            rf'<h4 class="case-phase phase-{kw}"><strong>\1</strong></h4>',
            html,
        )
        html = re.sub(
            rf"<p><strong>({kw}\s*[—–\-].*?)</strong></p>",
            rf'<p class="case-phase phase-{kw}"><strong>\1</strong></p>',
            html,
        )

    # 면책 조항 제거 (여러 변형 포함)
    html = re.sub(
        r"<p><em>DART Insight.*?</em>(?:<br\s*/?>.*?)?</p>",
        "",
        html,
        flags=re.DOTALL,
    )
    html = re.sub(
        r"<p><em>©.*?</em>(?:<br\s*/?>.*?)?</p>",
        "",
        html,
        flags=re.DOTALL,
    )
    html = re.sub(
        r"<em>DART Insight[^<]*</em>",
        "",
        html,
    )
    html = re.sub(
        r"<em>©\s*20\d{2}[^<]*</em>",
        "",
        html,
    )
    # "다음 섹션" 링크 제거
    html = re.sub(
        r"<p><em>다음\s*(?:섹션|장).*?</em></p>",
        "",
        html,
    )

    # <h2>---</h2> 마크다운 잔재 제거
    html = re.sub(r"<h2>-{2,}</h2>", "", html)

    # blockquote 밖에 있는 판례 포인트 <p><strong> 패턴을 blockquote로 래핑
    # (일부 MD에서 blockquote 안이 아닌 일반 paragraph로 판례 포인트가 나오는 경우)
    html = re.sub(
        r"(?<!case-law-box\">)<p><strong>(📋?\s*판례\s*포인트[^<]*)</strong></p>\s*"
        r"(<p>(?:(?!<h[23]|<blockquote|<div).)*?</p>\s*)*",
        lambda m: '<blockquote class="case-law-box">' + m.group(0) + '</blockquote>',
        html,
    )

    # 단독 키워드 발단/전개/위기/결말/교훈/역설 (em dash 없는 변형)
    for kw in ["발단", "전개", "위기", "결말", "교훈", "역설"]:
        html = re.sub(
            rf"<p><strong>({kw})</strong></p>",
            rf'<p class="case-phase phase-{kw}"><strong>\1</strong></p>',
            html,
        )

    # 연속 hr 정리
    html = re.sub(r"(<hr\s*/?>[\s\n]*){2,}", "<hr/>", html)

    return html


# ─── TOC 빌드 ───
def build_toc(all_sections: list[dict]) -> str:
    """사이드바 TOC HTML 생성"""
    toc = []
    current_part = 0

    for sec in all_sections:
        info = sec.get("info", {})
        if info["type"] == "part":
            ch = info.get("chapter", 0)
            if ch != current_part:
                if current_part > 0:
                    toc.append("</ul></li>")
                current_part = ch
                ci = CHAPTERS.get(ch, {})
                toc.append(
                    f'<li class="toc-part"><a href="#{info["id"]}">'
                    f'<span class="toc-part-num">{ci.get("icon", str(ch))}</span>'
                    f'<span class="toc-part-label">{ci.get("en", "")}</span></a>'
                    f'<ul class="toc-sections">'
                )
        elif info["type"] == "section":
            sid = info["id"]
            label = info.get("label", "")
            title = info.get("display_title", "")
            toc.append(
                f'<li><a href="#{sid}">'
                f'<span class="toc-sec-num">{label}</span>'
                f'<span class="toc-sec-title">{title}</span></a></li>'
            )

    if current_part > 0:
        toc.append("</ul></li>")

    return "\n".join(toc)


# ─── 콘텐츠 HTML 빌드 ───
def build_content(all_sections: list[dict]) -> str:
    """메인 콘텐츠 영역 HTML 생성"""
    parts = []
    current_chapter = 0

    for sec in all_sections:
        info = sec.get("info", {})
        body_html = sec.get("html", "")

        if info["type"] == "part":
            ch = info.get("chapter", 0)
            if ch != current_chapter:
                if current_chapter > 0:
                    parts.append("</div>")  # close prev chapter
                current_chapter = ch
                ci = CHAPTERS.get(ch, {})
                parts.append(
                    f'<div class="chapter-group" id="{info["id"]}">'
                    f'<div class="part-header">'
                    f'<span class="part-badge">PART {ci["icon"]}</span>'
                    f'<h1 class="part-title">{ci["en"]}</h1>'
                    f'<p class="part-subtitle">{ci["ko"]}</p>'
                    f"</div>"
                )

        elif info["type"] == "opener":
            parts.append(
                f'<div class="chapter-opener">'
                f'<div class="opener-icon">&#x1F3AC;</div>'
                f'<h2 class="opener-title">챕터 오프너 &mdash; &ldquo;{info["label"]}&rdquo;</h2>'
                f'<div class="opener-body">{body_html}</div>'
                f"</div>"
            )

        elif info["type"] == "section":
            subtitle_html = ""
            if "subtitle" in info:
                subtitle_html = (
                    f'<p class="section-subtitle">{info["subtitle"]}</p>'
                )
            parts.append(
                f'<section class="chapter-section" id="{info["id"]}">'
                f'<div class="section-header">'
                f'<span class="section-label">{info.get("label", "")}</span>'
                f'<h2 class="section-title">{info.get("display_title", "")}</h2>'
                f"{subtitle_html}"
                f"</div>"
                f'<div class="section-content">{body_html}</div>'
                f"</section>"
            )

        else:
            # 기타 콘텐츠
            if body_html.strip():
                parts.append(f'<div class="misc-content">{body_html}</div>')

    if current_chapter > 0:
        parts.append("</div>")

    return "\n".join(parts)


# ─── HTML 템플릿 ───
def get_template() -> str:
    return r"""<!DOCTYPE html>
<html lang="ko" data-theme="light" data-fs="default">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>상법 Signal — 기업 지배구조의 소스코드를 읽는 기술</title>
<meta name="description" content="숫자 너머의 구조를 읽는 법. 법적 리스크를 투자 시그널로 전환하는 25개 섹션의 실전 가이드."/>
<meta property="og:title" content="상법 Signal — 기업 지배구조의 소스코드를 읽는 기술"/>
<meta property="og:description" content="숫자를 읽는 사람은 많다. 구조를 읽는 사람은 적다. 그래서 구조에 알파가 있다."/>
<meta property="og:image" content="og-image.png"/>
<meta property="og:type" content="book"/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:title" content="상법 Signal"/>
<meta name="twitter:image" content="og-image.png"/>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;700;900&family=Pretendard:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
/* ══════════════════════════════════════
   CSS CUSTOM PROPERTIES
   ══════════════════════════════════════ */
:root {
  --sidebar-w: 272px;
  --max-content: 840px;
  --progress-h: 3px;

  /* Light */
  --bg: #f8f9fc;
  --fg: #1e293b;
  --fg-muted: #64748b;
  --card: #ffffff;
  --border: #e8ecf4;
  --accent: #e8556d;
  --accent2: #ff7a8e;
  --accent-light: rgba(232,85,109,.07);
  --accent-light2: rgba(232,85,109,.13);
  --cover-bg: linear-gradient(135deg,#1e293b 0%,#334155 50%,#1e293b 100%);
  --cover-accent: #ff7a8e;
  --shadow: 0 4px 24px rgba(99,102,241,.06), 0 1px 3px rgba(0,0,0,.04);
  --shadow-hover: 0 8px 32px rgba(99,102,241,.10), 0 2px 6px rgba(0,0,0,.06);
  --code-bg: #f1f5f9;
  --sidebar-bg: #ffffff;
  --sidebar-border: #e8ecf4;
  --dart-bg: #f0fdf4;
  --dart-border: #22c55e;
  --case-bg: #fefce8;
  --case-border: #eab308;
  --law-bg: #eff6ff;
  --law-border: #3b82f6;
  --lesson-bg: #fdf4ff;
  --lesson-border: #a855f7;
  --part-bg: linear-gradient(135deg,#1e293b 0%,#334155 60%,#475569 100%);
}
[data-theme="dark"] {
  --bg: #0f172a;
  --fg: #e2e8f0;
  --fg-muted: #94a3b8;
  --card: #1e293b;
  --border: #334155;
  --accent: #ff7a8e;
  --accent2: #fca5b4;
  --accent-light: rgba(255,122,142,.10);
  --accent-light2: rgba(255,122,142,.18);
  --shadow: 0 4px 24px rgba(0,0,0,.3);
  --shadow-hover: 0 8px 32px rgba(0,0,0,.4);
  --code-bg: #1e293b;
  --sidebar-bg: #0f172a;
  --sidebar-border: #1e293b;
  --dart-bg: rgba(34,197,94,.08);
  --dart-border: #22c55e;
  --case-bg: rgba(234,179,8,.08);
  --case-border: #eab308;
  --law-bg: rgba(59,130,246,.08);
  --law-border: #3b82f6;
  --lesson-bg: rgba(168,85,247,.08);
  --lesson-border: #a855f7;
  --part-bg: linear-gradient(135deg,#0f172a 0%,#1e293b 60%,#334155 100%);
}

/* Font size presets */
[data-fs="small"]  { font-size: 14px; }
[data-fs="default"]{ font-size: 16px; }
[data-fs="large"]  { font-size: 18px; }

/* ══════════════════════════════════════
   RESET & BASE
   ══════════════════════════════════════ */
*,*::before,*::after { box-sizing:border-box; margin:0; padding:0; }
html { scroll-behavior:smooth; }
body {
  font-family: 'Noto Serif KR', serif;
  color: var(--fg);
  background: var(--bg);
  line-height: 1.9;
  word-break: keep-all;
  letter-spacing: -0.01em;
  overflow-wrap: break-word;
  -webkit-font-smoothing: antialiased;
}

/* ══════════════════════════════════════
   PROGRESS BAR
   ══════════════════════════════════════ */
#progress {
  position: fixed; top:0; left:0; z-index:9999;
  height: var(--progress-h);
  width: 0%;
  background: linear-gradient(90deg, var(--accent), var(--accent2), var(--cover-accent));
  transition: width .15s linear;
}

/* ══════════════════════════════════════
   SIDEBAR
   ══════════════════════════════════════ */
.sidebar {
  position: fixed; top:0; left:0; bottom:0;
  width: var(--sidebar-w);
  background: var(--sidebar-bg);
  border-right: 1px solid var(--sidebar-border);
  z-index: 1000;
  display: flex; flex-direction: column;
  transition: transform .3s ease;
  overflow: hidden;
}
.sidebar-header {
  padding: 28px 24px 20px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.sidebar-logo {
  font-family: 'Pretendard', sans-serif;
  font-weight: 700; font-size: 1.1rem;
  color: var(--accent);
  letter-spacing: -.02em;
}
.sidebar-logo small {
  display: block; font-weight: 400; font-size: .72rem;
  color: var(--fg-muted); margin-top: 2px; letter-spacing: 0;
}
.sidebar-nav {
  flex: 1; overflow-y: auto; padding: 16px 0;
  scrollbar-width: thin;
  scrollbar-color: rgba(100,116,139,.2) transparent;
}
.sidebar-nav::-webkit-scrollbar { width: 3px; }
.sidebar-nav::-webkit-scrollbar-thumb { background: rgba(100,116,139,.2); border-radius: 3px; }
.sidebar-nav ul { list-style: none; }
.sidebar-nav .toc-part {
  margin-top: 8px;
}
.sidebar-nav .toc-part > a {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 24px;
  font-family: 'Pretendard', sans-serif;
  font-weight: 700; font-size: .78rem;
  color: var(--fg-muted);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: .06em;
  transition: color .2s;
}
.sidebar-nav .toc-part > a:hover { color: var(--accent); }
.toc-part-num {
  display: inline-flex; align-items: center; justify-content: center;
  width: 24px; height: 24px;
  background: var(--accent-light);
  color: var(--accent);
  border-radius: 6px;
  font-size: .7rem; font-weight: 700;
}
.toc-sections { padding-left: 0; }
.toc-sections li a {
  display: flex; align-items: baseline; gap: 8px;
  padding: 6px 24px 6px 58px;
  font-family: 'Pretendard', sans-serif;
  font-size: .82rem; font-weight: 400;
  color: var(--fg-muted);
  text-decoration: none;
  border-left: 2px solid transparent;
  transition: all .2s;
}
.toc-sections li a:hover {
  color: var(--fg);
  background: var(--accent-light);
}
.toc-sections li a.active {
  color: var(--accent);
  border-left-color: var(--accent);
  background: var(--accent-light);
  font-weight: 600;
}
.toc-sec-num {
  font-weight: 600; min-width: 28px;
  color: var(--accent);
  font-size: .78rem;
}
.sidebar-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--border);
  font-family: 'Pretendard', sans-serif;
  font-size: .68rem;
  color: var(--fg-muted);
  flex-shrink: 0;
}

/* ══════════════════════════════════════
   MAIN
   ══════════════════════════════════════ */
.main {
  margin-left: var(--sidebar-w);
  min-height: 100vh;
}

/* ══════════════════════════════════════
   COVER / HERO
   ══════════════════════════════════════ */
.cover {
  background: #0c1222;
  padding: clamp(100px,14vw,180px) 32px clamp(80px,10vw,140px);
  text-align: center;
  position: relative;
  overflow: hidden;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
/* SVG 그리드 패턴 */
.cover::before {
  content:''; position:absolute; inset:0;
  background-image:
    linear-gradient(rgba(232,85,109,.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(232,85,109,.06) 1px, transparent 1px);
  background-size: 60px 60px;
  mask-image: radial-gradient(ellipse 80% 70% at 50% 50%, black 30%, transparent 70%);
  -webkit-mask-image: radial-gradient(ellipse 80% 70% at 50% 50%, black 30%, transparent 70%);
  animation: grid-drift 20s linear infinite;
}
@keyframes grid-drift {
  0% { transform: translate(0,0); }
  100% { transform: translate(60px,60px); }
}
/* 글로우 오브 */
.cover::after {
  content:''; position:absolute; inset:0;
  background:
    radial-gradient(ellipse 600px 600px at 25% 30%, rgba(232,85,109,.18) 0%, transparent 70%),
    radial-gradient(ellipse 500px 500px at 75% 65%, rgba(99,102,241,.12) 0%, transparent 70%),
    radial-gradient(ellipse 400px 300px at 50% 80%, rgba(255,122,142,.08) 0%, transparent 60%);
  pointer-events:none;
}
/* 떠다니는 노드 */
.cover-nodes {
  position:absolute; inset:0; pointer-events:none; z-index:0;
}
.cover-node {
  position:absolute;
  width: var(--size);
  height: var(--size);
  border-radius:50%;
  border: 1px solid rgba(232,85,109,.2);
  animation: float var(--dur) ease-in-out infinite alternate;
}
.cover-node::after {
  content:''; position:absolute;
  top:50%; left:50%;
  width:4px; height:4px;
  margin:-2px 0 0 -2px;
  background: var(--accent);
  border-radius:50%;
  box-shadow: 0 0 8px rgba(232,85,109,.5);
}
@keyframes float {
  0% { transform: translateY(0) scale(1); opacity:.4; }
  100% { transform: translateY(var(--drift)) scale(1.1); opacity:.7; }
}
/* 연결선 SVG */
.cover-lines {
  position:absolute; inset:0; pointer-events:none; z-index:0;
  opacity:.15;
}
.cover-inner {
  position:relative; z-index:2;
  max-width:720px; margin:0 auto;
}
.cover-badge {
  display: inline-block;
  font-family: 'Pretendard', sans-serif;
  font-size: .68rem; font-weight: 600;
  letter-spacing: .14em; text-transform: uppercase;
  color: var(--accent2);
  border: 1px solid rgba(255,122,142,.3);
  padding: 7px 22px;
  border-radius: 24px;
  margin-bottom: 36px;
  backdrop-filter: blur(4px);
  background: rgba(255,122,142,.06);
}
.cover-divider {
  width:48px; height:2px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  margin: 0 auto 32px;
}
.cover h1 {
  font-size: clamp(2.6rem,6vw,4.2rem);
  font-weight: 900;
  color: #fff;
  line-height: 1.15;
  margin-bottom: 12px;
  letter-spacing: -.04em;
}
.cover h1 em {
  font-style:normal;
  background: linear-gradient(135deg, var(--accent2), #c084fc);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.cover-hangul-sub {
  font-family: 'Noto Serif KR', serif;
  font-size: clamp(1rem,2vw,1.35rem);
  font-weight: 400;
  color: rgba(255,255,255,.5);
  margin-bottom: 28px;
  letter-spacing: .02em;
}
.cover-subtitle {
  font-family: 'Pretendard', sans-serif;
  font-size: clamp(.85rem,1.5vw,1rem);
  color: rgba(255,255,255,.45);
  line-height: 1.8;
  max-width: 520px; margin: 0 auto 40px;
}
.cover-stats {
  display: inline-flex; gap: 32px;
  font-family: 'Pretendard', sans-serif;
  margin-bottom: 36px;
}
.cover-stat {
  text-align:center;
}
.cover-stat-num {
  display:block;
  font-size: 1.8rem; font-weight: 900;
  color: var(--accent2);
  line-height:1;
}
.cover-stat-label {
  display:block;
  font-size: .68rem; font-weight: 500;
  color: rgba(255,255,255,.35);
  margin-top:6px;
  text-transform: uppercase;
  letter-spacing: .08em;
}
.cover-meta {
  font-family: 'Pretendard', sans-serif;
  font-size: .72rem;
  color: rgba(255,255,255,.25);
  letter-spacing: .04em;
}
.cover-scroll-hint {
  position:absolute;
  bottom: 32px; left:50%;
  transform: translateX(-50%);
  z-index:2;
  display:flex; flex-direction:column; align-items:center;
  gap:6px;
  color: rgba(255,255,255,.25);
  font-family: 'Pretendard', sans-serif;
  font-size: .65rem;
  letter-spacing: .1em;
  animation: hint-pulse 2s ease-in-out infinite;
}
.cover-scroll-hint svg { width:16px; height:16px; stroke:rgba(255,255,255,.3); }
@keyframes hint-pulse { 0%,100%{opacity:.3;transform:translateX(-50%) translateY(0)} 50%{opacity:.6;transform:translateX(-50%) translateY(4px)} }

/* ══════════════════════════════════════
   PART HEADER
   ══════════════════════════════════════ */
.part-header {
  background: var(--part-bg);
  padding: clamp(48px,8vw,80px) 32px;
  text-align: center;
  position: relative;
  overflow: hidden;
}
.part-header::before {
  content:''; position:absolute; inset:0;
  background: radial-gradient(ellipse at 50% 50%, rgba(232,85,109,.12) 0%, transparent 60%);
}
.part-badge {
  position: relative; z-index:1;
  display: inline-block;
  font-family: 'Pretendard', sans-serif;
  font-size: .68rem; font-weight: 700;
  letter-spacing: .15em;
  color: var(--accent2);
  margin-bottom: 16px;
}
.part-title {
  position: relative; z-index:1;
  font-size: clamp(1.6rem,3.5vw,2.4rem);
  color: #fff; font-weight: 900;
  margin-bottom: 10px;
  letter-spacing: -.02em;
}
.part-subtitle {
  position: relative; z-index:1;
  font-size: clamp(.88rem,1.5vw,1.05rem);
  color: rgba(255,255,255,.55);
}

/* ══════════════════════════════════════
   CHAPTER OPENER
   ══════════════════════════════════════ */
.chapter-opener {
  max-width: var(--max-content);
  margin: 0 auto;
  padding: 48px 32px;
}
.opener-icon { font-size: 2rem; margin-bottom: 12px; }
.opener-title {
  font-size: 1.4rem; font-weight: 700;
  color: var(--accent);
  margin-bottom: 20px;
  letter-spacing: -.01em;
}
.opener-body {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 32px;
  box-shadow: var(--shadow);
}
.opener-body p { margin-bottom: 1em; }
.opener-body p:last-child { margin-bottom:0; }

/* ══════════════════════════════════════
   SECTION CARD
   ══════════════════════════════════════ */
.chapter-section {
  max-width: var(--max-content);
  margin: 32px auto;
  padding: 0 32px;
}
.section-header {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px 12px 0 0;
  padding: 28px 36px 22px;
  border-bottom: 2px solid var(--accent);
}
.section-label {
  font-family: 'Pretendard', sans-serif;
  font-size: .72rem; font-weight: 700;
  color: var(--accent);
  letter-spacing: .05em;
  text-transform: uppercase;
}
.section-title {
  font-size: clamp(1.2rem,2.5vw,1.6rem);
  font-weight: 700;
  color: var(--fg);
  margin-top: 4px;
  letter-spacing: -.02em;
}
.section-subtitle {
  font-size: .9rem;
  font-style: italic;
  color: var(--fg-muted);
  margin-top: 6px;
}
.section-content {
  background: var(--card);
  border: 1px solid var(--border);
  border-top: none;
  border-radius: 0 0 12px 12px;
  padding: 36px;
  box-shadow: var(--shadow);
}

/* ══════════════════════════════════════
   TYPOGRAPHY IN CONTENT
   ══════════════════════════════════════ */
.section-content p,
.opener-body p {
  margin-bottom: 1em;
  text-align: left;
}
.opener-body p:first-of-type::first-letter {
  float: left;
  font-size: 3.2em;
  color: var(--accent);
  line-height: 0.8;
  padding-right: 8px;
  font-weight: 700;
}
.section-content p + p { text-indent: 0; }
.section-content p em {
  font-size: .93em;
  color: var(--fg-muted);
}
.section-content h3 {
  font-size: 1.15rem;
  font-weight: 700;
  margin: 2.2em 0 .8em;
  padding-left: 14px;
  border-left: 3px solid var(--accent);
  color: var(--fg);
}
.section-content h3:first-child { margin-top: .5em; }
.section-content h3.sub-legal { border-left-color: #3b82f6; }
.section-content h3.sub-structure { border-left-color: #8b5cf6; }
.section-content h3.sub-case { border-left-color: #eab308; }
.section-content h3.sub-signal { border-left-color: #22c55e; }
.section-content h3.sub-dart { border-left-color: #06b6d4; }
.section-content h3.sub-checklist { border-left-color: var(--accent); }
.section-content h3.sub-deep { border-left-color: #f97316; }

.section-content h4 {
  font-size: 1rem; font-weight: 700;
  margin: 1.6em 0 .6em;
  color: var(--fg);
}

.section-content strong { color: var(--fg); letter-spacing: 0.01em; }
.section-content em { color: var(--fg-muted); }

.section-content a {
  color: var(--accent);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.section-content code {
  font-family: 'Pretendard', monospace;
  background: var(--code-bg);
  color: var(--accent);
  padding: 2px 7px;
  border-radius: 4px;
  font-size: .88em;
}

.section-content ul, .section-content ol {
  padding-left: 1.5em;
  margin-bottom: 1em;
}
.section-content li { margin-bottom: .4em; }

.section-content hr {
  border: none;
  border-top: 1px solid var(--border);
  margin: 2em 0;
}

/* ══════════════════════════════════════
   CASE STUDY PHASE TAGS
   ══════════════════════════════════════ */
.case-phase strong::before {
  font-family: 'Pretendard', sans-serif;
  font-size: .65rem; font-weight: 700;
  padding: 2px 8px; border-radius: 4px;
  margin-right: 8px; vertical-align: middle;
  letter-spacing: .04em;
}
.phase-발단 strong::before { content:'발단'; background:#dbeafe; color:#2563eb; }
.phase-전개 strong::before { content:'전개'; background:#fef3c7; color:#d97706; }
.phase-위기 strong::before { content:'위기'; background:#fee2e2; color:#dc2626; }
.phase-결말 strong::before { content:'결말'; background:#f3e8ff; color:#7c3aed; }
.phase-교훈 strong::before { content:'교훈'; background:#dcfce7; color:#16a34a; }
.phase-역설 strong::before { content:'역설'; background:#fce7f3; color:#db2777; }

/* ══════════════════════════════════════
   BLOCKQUOTE VARIANTS
   ══════════════════════════════════════ */
.section-content blockquote {
  border-left: 4px solid var(--border);
  padding: 14px 20px;
  margin: 1.2em 0;
  background: var(--accent-light);
  border-radius: 0 8px 8px 0;
  font-size: .94em;
}
blockquote.case-law-box {
  background: var(--law-bg);
  border-left-color: var(--law-border);
}
blockquote.lesson-box {
  background: var(--lesson-bg);
  border-left-color: var(--lesson-border);
}
.epigraph {
  text-align: center;
  padding: 32px 20px;
  margin: 2em 0;
  font-style: italic;
  color: var(--fg-muted);
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  font-size: 1.02em;
}

/* ══════════════════════════════════════
   DART BOX / CHECKLIST
   ══════════════════════════════════════ */
.dart-box {
  background: var(--dart-bg);
  border: 1px solid var(--dart-border);
  border-radius: 10px;
  padding: 20px 24px;
  margin: 1.4em 0;
  position: relative;
}
.dart-box::before {
  content: 'DART';
  position: absolute; top: -10px; left: 16px;
  font-family: 'Pretendard', sans-serif;
  font-size: .62rem; font-weight: 700;
  color: #fff; background: var(--dart-border);
  padding: 2px 10px; border-radius: 4px;
  letter-spacing: .08em;
}
.dart-box pre, .checklist-box pre {
  font-family: 'Pretendard', monospace;
  font-size: .84rem;
  line-height: 1.7;
  white-space: pre-wrap;
  color: var(--fg);
  background: transparent;
  margin: 0; padding: 0;
}
.checklist-box {
  background: var(--accent-light);
  border: 1px solid var(--accent);
  border-radius: 10px;
  padding: 20px 24px;
  margin: 1.4em 0;
}

/* ══════════════════════════════════════
   TABLES
   ══════════════════════════════════════ */
.table-wrap {
  overflow-x: auto;
  margin: 1.4em 0;
  border-radius: 10px;
  border: 1px solid var(--border);
}
.section-content table {
  width: 100%;
  border-collapse: collapse;
  font-size: .88rem;
  font-family: 'Pretendard', sans-serif;
}
.section-content thead th {
  background: var(--accent-light2);
  color: var(--fg);
  font-weight: 600;
  padding: 10px 14px;
  text-align: left;
  border-bottom: 2px solid var(--accent);
  position: sticky; top: 0;
  white-space: nowrap;
}
.section-content tbody td {
  padding: 9px 14px;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}
.section-content tbody tr:nth-child(even) td {
  background: rgba(232,85,109,.02);
}
.section-content tbody tr:hover td {
  background: var(--accent-light);
}

/* ══════════════════════════════════════
   FLOATING BUTTONS
   ══════════════════════════════════════ */
.fab-group {
  position: fixed; bottom: 28px; right: 28px;
  display: flex; flex-direction: column; gap: 10px;
  z-index: 999;
}
.fab {
  width: 44px; height: 44px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--fg-muted);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  box-shadow: var(--shadow);
  transition: all .2s;
  font-size: 1.1rem;
  backdrop-filter: blur(8px);
}
.fab:hover {
  transform: scale(1.1);
  box-shadow: var(--shadow-hover);
  color: var(--accent);
}
#btn-top { opacity:0; pointer-events:none; transition: opacity .3s; }
#btn-top.show { opacity:1; pointer-events:auto; }

/* ══════════════════════════════════════
   HAMBURGER (mobile)
   ══════════════════════════════════════ */
.hamburger {
  display: none;
  position: fixed; top: 14px; left: 14px; z-index: 1100;
  width: 40px; height: 40px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--card);
  cursor: pointer;
  align-items: center; justify-content: center;
  box-shadow: var(--shadow);
}
.hamburger svg { width:20px; height:20px; stroke:var(--fg); }
.overlay {
  display: none;
  position: fixed; inset:0; z-index: 999;
  background: rgba(0,0,0,.4);
  backdrop-filter: blur(2px);
}
.overlay.show { display:block; }

/* ══════════════════════════════════════
   SECTION ANIMATION
   ══════════════════════════════════════ */
.chapter-section,
.chapter-opener,
.prologue-section,
.epilogue-section,
.appendix-section {
  opacity: 0;
  transform: translateY(24px);
  transition: opacity .5s ease, transform .5s ease;
}
.chapter-section.visible,
.chapter-opener.visible,
.prologue-section.visible,
.epilogue-section.visible,
.appendix-section.visible {
  opacity: 1;
  transform: translateY(0);
}

/* ══════════════════════════════════════
   PROLOGUE / EPILOGUE
   ══════════════════════════════════════ */
.prologue-section,
.epilogue-section {
  max-width: var(--max-content);
  margin: 0 auto;
  padding: 0 32px;
}
.prologue-header,
.epilogue-header {
  text-align: center;
  padding: 56px 0 24px;
}
.prologue-badge,
.epilogue-badge {
  display: inline-block;
  font-family: 'Pretendard', sans-serif;
  font-size: .68rem; font-weight: 700;
  letter-spacing: .15em;
  color: var(--accent);
  border: 1px solid var(--accent);
  padding: 5px 20px;
  border-radius: 20px;
}
.prologue-body,
.epilogue-body {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 40px 36px;
  box-shadow: var(--shadow);
  margin-bottom: 48px;
}
.prologue-body p,
.epilogue-body p {
  margin-bottom: 1em;
  text-align: left;
}
.prologue-body p:last-child,
.epilogue-body p:last-child { margin-bottom: 0; }
.prologue-body h1,
.epilogue-body h1 {
  font-size: 1.6rem; font-weight: 700;
  color: var(--accent);
  margin-bottom: 24px;
  text-align: center;
}
.prologue-body h2,
.epilogue-body h2 {
  font-size: 1.15rem; font-weight: 700;
  color: var(--fg);
  margin: 2em 0 .8em;
  padding-left: 14px;
  border-left: 4px solid var(--accent);
}
.prologue-body h3,
.epilogue-body h3 {
  font-size: 1.05rem; font-weight: 700;
  color: var(--fg);
  margin: 1.6em 0 .6em;
}
.prologue-body blockquote,
.epilogue-body blockquote {
  border-left: 4px solid var(--accent);
  padding: 14px 20px;
  margin: 1.2em 0;
  background: var(--accent-light);
  border-radius: 0 8px 8px 0;
  font-size: .94em;
}
.prologue-body hr,
.epilogue-body hr {
  border: none;
  border-top: 1px solid var(--border);
  margin: 2em 0;
}
.prologue-body p:first-of-type::first-letter,
.epilogue-body p:first-of-type::first-letter {
  float: left;
  font-size: 3.2em;
  line-height: 0.8;
  padding-right: 8px;
  padding-top: 4px;
  color: var(--accent);
  font-weight: 700;
}
.appendix-section {
  max-width: var(--max-content);
  margin: 0 auto;
  padding: 0 32px;
}
.appendix-header {
  text-align: center;
  padding: 56px 0 24px;
}
.appendix-badge {
  display: inline-block;
  font-family: 'Pretendard', sans-serif;
  font-size: .68rem; font-weight: 700;
  letter-spacing: .15em;
  color: var(--fg-muted);
  border: 1px solid var(--fg-muted);
  padding: 5px 20px;
  border-radius: 20px;
}
.appendix-body {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 40px 36px;
  box-shadow: var(--shadow);
  margin-bottom: 48px;
}
.appendix-body p { margin-bottom: 1em; text-align: left; }
.appendix-body p:last-child { margin-bottom: 0; }
.appendix-body h1 {
  font-size: 1.6rem; font-weight: 700;
  color: var(--fg); margin-bottom: 24px; text-align: center;
}
.appendix-body h2 {
  font-size: 1.15rem; font-weight: 700;
  color: var(--fg); margin: 2.5em 0 .8em;
  padding-left: 14px; border-left: 4px solid var(--fg-muted);
}
.appendix-body h3 {
  font-size: 1rem; font-weight: 700;
  color: var(--fg); margin: 1.6em 0 .6em;
}
.appendix-body hr { border: none; border-top: 1px solid var(--border); margin: 2em 0; }
.toc-special a {
  display: block;
  padding: 8px 24px;
  font-family: 'Pretendard', sans-serif;
  font-size: .82rem; font-weight: 600;
  color: var(--accent);
  text-decoration: none;
  transition: all .2s;
}
.toc-special a:hover {
  background: var(--accent-light);
}

/* ══════════════════════════════════════
   COLOPHON (판권 페이지)
   ══════════════════════════════════════ */
.colophon {
  max-width: 560px;
  margin: 80px auto 0;
  padding: 0 32px 64px;
  text-align: center;
}
.colophon-title-area {
  padding: 48px 0 32px;
}
.colophon-book-title {
  font-family: 'Noto Serif KR', serif;
  font-size: clamp(1.6rem, 3vw, 2.2rem);
  font-weight: 900;
  color: var(--fg);
  letter-spacing: -.03em;
  line-height: 1.3;
}
.colophon-book-title em {
  font-style: normal;
  color: var(--accent);
}
.colophon-book-sub {
  font-family: 'Pretendard', sans-serif;
  font-size: .82rem;
  color: var(--fg-muted);
  margin-top: 8px;
  letter-spacing: .04em;
}
.colophon-divider {
  width: 60px;
  height: 2px;
  background: var(--accent);
  margin: 0 auto 32px;
}
.colophon-info {
  font-family: 'Pretendard', sans-serif;
  font-size: .88rem;
  color: var(--fg);
  line-height: 2.2;
  text-align: left;
  display: inline-block;
}
.colophon-info strong {
  display: inline-block;
  width: 72px;
  color: var(--fg-muted);
  font-weight: 600;
  letter-spacing: .02em;
}
.colophon-price {
  margin: 32px auto;
  padding: 14px 32px;
  display: inline-block;
  border: 1.5px solid var(--accent);
  border-radius: 8px;
  font-family: 'Pretendard', sans-serif;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--accent);
  letter-spacing: .02em;
}
.colophon-copyright {
  margin-top: 32px;
  font-family: 'Pretendard', sans-serif;
  font-size: .75rem;
  color: var(--fg-muted);
  line-height: 1.8;
}
.colophon-copyright p { margin: 4px 0; }
.colophon-publisher {
  margin-top: 40px;
  padding-top: 24px;
  border-top: 1px solid var(--border);
}
.colophon-publisher-name {
  font-family: 'Pretendard', sans-serif;
  font-size: .9rem;
  font-weight: 700;
  color: var(--fg);
  letter-spacing: .06em;
}
.colophon-publisher-info {
  font-family: 'Pretendard', sans-serif;
  font-size: .72rem;
  color: var(--fg-muted);
  margin-top: 8px;
  line-height: 1.7;
}
@media print {
  .colophon { page-break-before: always; }
}

/* ══════════════════════════════════════
   FOOTER
   ══════════════════════════════════════ */
.site-footer {
  max-width: var(--max-content);
  margin: 0 auto;
  padding: 48px 32px 64px;
  text-align: center;
  font-family: 'Pretendard', sans-serif;
  font-size: .78rem;
  color: var(--fg-muted);
  border-top: 1px solid var(--border);
}

/* ══════════════════════════════════════
   RESPONSIVE
   ══════════════════════════════════════ */
@media (max-width: 900px) {
  .sidebar { transform: translateX(-100%); }
  .sidebar.open { transform: translateX(0); }
  .main { margin-left: 0; }
  .hamburger { display: flex; }
  .chapter-section,
  .chapter-opener { padding-left: 16px; padding-right: 16px; }
  .section-header { padding: 22px 20px 18px; }
  .section-content { padding: 24px 20px; }
  .opener-body { padding: 24px 20px; }
  .cover { padding: 80px 20px; min-height: auto; }
  .cover-stats { gap: 20px; }
  .cover-stat-num { font-size: 1.4rem; }
  .cover-node { display:none; }
  .cover-lines { display:none; }
  .cover-scroll-hint { bottom: 20px; }
  .part-header { padding: 48px 20px; }
  /* 프롤로그/에필로그/부록 모바일 */
  .prologue-section,
  .epilogue-section,
  .appendix-section { padding: 0 16px; }
  .prologue-body,
  .epilogue-body,
  .appendix-body { padding: 24px 20px; }
  /* 판권 모바일 */
  .colophon { padding: 0 16px 48px; margin-top: 48px; }
  .colophon-title-area { padding: 36px 0 24px; }
  .colophon-book-title { font-size: 1.4rem; }
  .colophon-info { font-size: .82rem; }
  .colophon-info strong { width: 64px; font-size: .78rem; }
  .colophon-price { font-size: .95rem; padding: 12px 24px; }
  /* 테이블 모바일 가로스크롤 */
  .table-wrap { -webkit-overflow-scrolling: touch; }
  .table-wrap table { min-width: 480px; }
  /* DART 박스 모바일 */
  .dart-box { padding: 16px 16px; }
  .dart-box pre { font-size: .78rem; }
  /* FAB 위치 조정 */
  .fab-group { bottom: 16px; right: 16px; }
  .fab { width: 40px; height: 40px; font-size: 1rem; }
  /* 드롭캡 모바일 축소 */
  .opener-body p:first-of-type::first-letter,
  .prologue-body p:first-of-type::first-letter,
  .epilogue-body p:first-of-type::first-letter { font-size: 2.4em; }
}

/* ══════════════════════════════════════
   PRINT
   ══════════════════════════════════════ */
@media print {
  .sidebar, .fab-group, .hamburger, .overlay, #progress { display:none!important; }
  .main { margin-left:0!important; }
  .chapter-section, .chapter-opener { opacity:1!important; transform:none!important; }
  .part-header { background:#1e293b!important; -webkit-print-color-adjust:exact; print-color-adjust:exact; }
  .cover { background:#1e293b!important; -webkit-print-color-adjust:exact; print-color-adjust:exact; }
}
</style>
</head>
<body>

<!-- Progress -->
<div id="progress"></div>

<!-- Hamburger -->
<button class="hamburger" id="hamburger" aria-label="메뉴 열기">
  <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round">
    <line x1="3" y1="6" x2="21" y2="6"/>
    <line x1="3" y1="12" x2="21" y2="12"/>
    <line x1="3" y1="18" x2="21" y2="18"/>
  </svg>
</button>
<div class="overlay" id="overlay"></div>

<!-- Sidebar -->
<nav class="sidebar" id="sidebar">
  <div class="sidebar-header">
    <div class="sidebar-logo">
      상법 Signal
      <small>기업 지배구조의 소스코드를 읽는 기술</small>
    </div>
  </div>
  <div class="sidebar-nav">
    <ul id="toc">
      {{TOC}}
    </ul>
  </div>
  <div class="sidebar-footer">
    &copy; 2026 상법 Signal &middot; DART Insight
  </div>
</nav>

<!-- Main -->
<main class="main">
  <!-- Cover -->
  <div class="cover" id="cover">
    <!-- 떠다니는 노드 -->
    <div class="cover-nodes">
      <div class="cover-node" style="top:12%;left:8%;--size:80px;--dur:6s;--drift:-18px"></div>
      <div class="cover-node" style="top:25%;left:78%;--size:60px;--dur:8s;--drift:14px"></div>
      <div class="cover-node" style="top:55%;left:15%;--size:50px;--dur:7s;--drift:-12px"></div>
      <div class="cover-node" style="top:70%;left:85%;--size:70px;--dur:9s;--drift:16px"></div>
      <div class="cover-node" style="top:40%;left:92%;--size:40px;--dur:5s;--drift:-10px"></div>
      <div class="cover-node" style="top:85%;left:45%;--size:55px;--dur:7.5s;--drift:12px"></div>
      <div class="cover-node" style="top:8%;left:55%;--size:45px;--dur:6.5s;--drift:-15px"></div>
      <div class="cover-node" style="top:60%;left:50%;--size:35px;--dur:5.5s;--drift:8px"></div>
    </div>
    <!-- 연결선 -->
    <svg class="cover-lines" viewBox="0 0 1000 800" preserveAspectRatio="none">
      <line x1="80" y1="96" x2="780" y2="200" stroke="#e8556d" stroke-width=".5"/>
      <line x1="150" y1="440" x2="850" y2="560" stroke="#e8556d" stroke-width=".5"/>
      <line x1="780" y1="200" x2="920" y2="320" stroke="#6366f1" stroke-width=".5"/>
      <line x1="80" y1="96" x2="150" y2="440" stroke="#6366f1" stroke-width=".5"/>
      <line x1="550" y1="64" x2="850" y2="560" stroke="#e8556d" stroke-width=".3"/>
      <line x1="500" y1="480" x2="920" y2="320" stroke="#6366f1" stroke-width=".3"/>
    </svg>
    <!-- 콘텐츠 -->
    <div class="cover-inner">
      <span class="cover-badge">DART Insight Series</span>
      <h1>상법 <em>Signal</em></h1>
      <p class="cover-hangul-sub">기업 지배구조의 소스코드를 읽는 기술</p>
      <div class="cover-divider"></div>
      <p class="cover-subtitle">
        숫자 너머의 구조를 읽는 법<br/>
        법적 리스크를 투자 시그널로 전환하는 실전 가이드
      </p>
      <div class="cover-stats">
        <div class="cover-stat"><span class="cover-stat-num">5</span><span class="cover-stat-label">Chapters</span></div>
        <div class="cover-stat"><span class="cover-stat-num">25</span><span class="cover-stat-label">Sections</span></div>
        <div class="cover-stat"><span class="cover-stat-num">42+</span><span class="cover-stat-label">Cases</span></div>
      </div>
      <p class="cover-meta">DART Insight &middot; 소셜브레인</p>
    </div>
    <!-- 스크롤 힌트 -->
    <div class="cover-scroll-hint">
      SCROLL
      <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round"><path d="M12 5v14M19 12l-7 7-7-7"/></svg>
    </div>
  </div>

  <!-- Content -->
  {{CONTENT}}

  <!-- 저작권 -->
  <div class="colophon" id="colophon">
    <div class="colophon-copyright">
      <p>&copy; 2026 주식회사 뮤즈에아이이. All Rights Reserved.</p>
      <p>출판사 등록번호 251002023000251</p>
    </div>
  </div>

  <!-- Footer -->
  <footer class="site-footer">
    <p>상법 Signal &mdash; 기업 지배구조의 소스코드를 읽는 기술</p>
    <p style="margin-top:6px;">&copy; 2026 주식회사 뮤즈에아이이</p>
  </footer>
</main>

<!-- FABs -->
<div class="fab-group">
  <button class="fab" id="btn-font" aria-label="글자 크기" title="글자 크기">가</button>
  <button class="fab" id="btn-theme" aria-label="테마 전환" title="테마 전환">&#x1F313;</button>
  <button class="fab" id="btn-top" aria-label="맨 위로" title="맨 위로">&uarr;</button>
</div>

<script>
(function(){
  /* ── Scroll progress ── */
  const progress = document.getElementById('progress');
  const btnTop = document.getElementById('btn-top');
  function onScroll(){
    const h = document.documentElement.scrollHeight - window.innerHeight;
    const pct = h > 0 ? (window.scrollY / h) * 100 : 0;
    progress.style.width = pct + '%';
    btnTop.classList.toggle('show', window.scrollY > 400);
  }
  window.addEventListener('scroll', onScroll, {passive:true});

  /* ── Back to top ── */
  btnTop.addEventListener('click', ()=> window.scrollTo({top:0, behavior:'smooth'}));

  /* ── Theme toggle ── */
  const html = document.documentElement;
  const btnTheme = document.getElementById('btn-theme');
  const saved = localStorage.getItem('theme');
  if(saved) html.dataset.theme = saved;
  btnTheme.addEventListener('click', ()=>{
    const next = html.dataset.theme === 'dark' ? 'light' : 'dark';
    html.dataset.theme = next;
    localStorage.setItem('theme', next);
  });

  /* ── Font size ── */
  const sizes = ['small','default','large'];
  const btnFont = document.getElementById('btn-font');
  let fsIdx = sizes.indexOf(html.dataset.fs || 'default');
  btnFont.addEventListener('click', ()=>{
    fsIdx = (fsIdx + 1) % sizes.length;
    html.dataset.fs = sizes[fsIdx];
    localStorage.setItem('fs', sizes[fsIdx]);
  });
  const savedFs = localStorage.getItem('fs');
  if(savedFs && sizes.includes(savedFs)){ html.dataset.fs = savedFs; fsIdx = sizes.indexOf(savedFs); }

  /* ── Hamburger ── */
  const sidebar = document.getElementById('sidebar');
  const hamburger = document.getElementById('hamburger');
  const overlay = document.getElementById('overlay');
  function closeSidebar(){ sidebar.classList.remove('open'); overlay.classList.remove('show'); }
  hamburger.addEventListener('click', ()=>{ sidebar.classList.toggle('open'); overlay.classList.toggle('show'); });
  overlay.addEventListener('click', closeSidebar);

  /* ── TOC active tracking ── */
  const tocLinks = document.querySelectorAll('#toc a');
  const sections = [];
  tocLinks.forEach(a => {
    const id = a.getAttribute('href')?.slice(1);
    const el = id && document.getElementById(id);
    if(el) sections.push({el, a});
  });
  function updateActive(){
    let current = null;
    for(const s of sections){
      if(s.el.getBoundingClientRect().top <= 120) current = s;
    }
    tocLinks.forEach(a => a.classList.remove('active'));
    if(current) current.a.classList.add('active');
  }
  window.addEventListener('scroll', updateActive, {passive:true});

  /* ── Close sidebar on link click (mobile) ── */
  tocLinks.forEach(a => a.addEventListener('click', ()=>{
    if(window.innerWidth <= 900) closeSidebar();
  }));

  /* ── Fade-in animation ── */
  const observer = new IntersectionObserver((entries)=>{
    entries.forEach(e => { if(e.isIntersecting) e.target.classList.add('visible'); });
  }, {threshold: 0.05});
  document.querySelectorAll('.chapter-section, .chapter-opener, .prologue-section, .epilogue-section, .appendix-section').forEach(el => observer.observe(el));

  /* ── Init ── */
  onScroll();
  updateActive();
})();
</script>
</body>
</html>"""


# ─── 메인 ───
def main():
    print("[BUILD] sangbeop Signal e-book build start...")

    all_sections = []
    for fname in MD_FILES:
        fpath = BASE_DIR / fname
        print(f"  읽는 중: {fname}")
        md_text = fpath.read_text(encoding="utf-8")
        sections = extract_sections(md_text)
        for sec in sections:
            info = classify_section(sec["title"])
            sec["info"] = info
            sec["html"] = process_body_html(convert_md(sec["body"]))
        all_sections.extend(sections)

    print(f"  총 {len(all_sections)}개 섹션 처리 완료")

    toc_html = build_toc(all_sections)
    content_html = build_content(all_sections)

    # 프롤로그 / 에필로그 삽입
    prologue_html = ""
    epilogue_html = ""
    pro_path = BASE_DIR / "prologue.md"
    epi_path = BASE_DIR / "epilogue.md"
    if pro_path.exists():
        pro_md = pro_path.read_text(encoding="utf-8")
        pro_body = process_body_html(convert_md(pro_md))
        prologue_html = (
            '<div class="prologue-section" id="prologue">'
            '<div class="prologue-header">'
            '<span class="prologue-badge">PROLOGUE</span>'
            '</div>'
            f'<div class="prologue-body">{pro_body}</div>'
            '</div>'
        )
    if epi_path.exists():
        epi_md = epi_path.read_text(encoding="utf-8")
        epi_body = process_body_html(convert_md(epi_md))
        epilogue_html = (
            '<div class="epilogue-section" id="epilogue">'
            '<div class="epilogue-header">'
            '<span class="epilogue-badge">EPILOGUE</span>'
            '</div>'
            f'<div class="epilogue-body">{epi_body}</div>'
            '</div>'
        )

    # 부록 삽입
    appendix_html = ""
    app_path = BASE_DIR / "appendix.md"
    if app_path.exists():
        app_md = app_path.read_text(encoding="utf-8")
        app_body = process_body_html(convert_md(app_md))
        appendix_html = (
            '<div class="appendix-section" id="appendix">'
            '<div class="appendix-header">'
            '<span class="appendix-badge">APPENDIX</span>'
            '</div>'
            f'<div class="appendix-body">{app_body}</div>'
            '</div>'
        )

    # TOC에 프롤로그/에필로그/부록 추가
    toc_prefix = '<li class="toc-special"><a href="#prologue">프롤로그</a></li>\n' if prologue_html else ""
    toc_suffix = ""
    if epilogue_html:
        toc_suffix += '<li class="toc-special"><a href="#epilogue">에필로그</a></li>\n'
    if appendix_html:
        toc_suffix += '<li class="toc-special"><a href="#appendix">부록</a></li>\n'
    toc_html = toc_prefix + toc_html + toc_suffix

    content_html = prologue_html + content_html + epilogue_html + appendix_html

    template = get_template()

    final_html = template.replace("{{TOC}}", toc_html).replace(
        "{{CONTENT}}", content_html
    )

    OUTPUT.write_text(final_html, encoding="utf-8")
    size_kb = OUTPUT.stat().st_size / 1024
    print(f"\n[DONE] Build complete: {OUTPUT}")
    print(f"   파일 크기: {size_kb:.0f} KB")


if __name__ == "__main__":
    main()
