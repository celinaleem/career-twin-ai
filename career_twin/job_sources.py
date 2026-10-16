"""External job sources used for live job recommendations."""
from html.parser import HTMLParser
from html import unescape
import hashlib
import json
import os
import re
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


class JobSourceError(RuntimeError):
    pass


class JobPageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.meta = []
        self.text = []
        self._tag_stack = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self._tag_stack.append(tag)
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            name = (attrs.get("name") or attrs.get("property") or "").lower()
            if name in {"description", "og:title", "og:description"} and attrs.get("content"):
                self.meta.append(attrs["content"])

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False
        if self._tag_stack:
            self._tag_stack.pop()

    def handle_data(self, data):
        cleaned = " ".join(data.split())
        if not cleaned:
            return
        if self._in_title:
            self.title += cleaned + " "
        elif not self._skip_depth:
            self.text.append(cleaned)


def _nested(mapping, *keys, default=""):
    value = mapping
    for key in keys:
        if not isinstance(value, dict):
            return default
        value = value.get(key)
    return value if value is not None else default


def _text(value):
    if isinstance(value, dict):
        return str(value.get("name") or "")
    return str(value or "")


def _clean_page_text(text):
    text = re.sub(r"\s+", " ", text).strip()
    noisy = {"로그인", "회원가입", "고객센터", "개인정보처리방침", "이용약관"}
    parts = [part.strip() for part in re.split(r"(?<=[.!?。])\s+|\s{2,}", text) if part.strip()]
    if len(parts) <= 1:
        parts = [part.strip() for part in text.split(" ") if part.strip()]
    kept = []
    for part in parts:
        if part in noisy or len(part) < 2:
            continue
        kept.append(part)
    return " ".join(kept)[:12000]


def _fetch_html(url):
    request = Request(url, headers={
        "User-Agent": "Mozilla/5.0 CareerTwinAI/1.0",
        "Accept": "text/html,application/xhtml+xml",
    })
    try:
        with urlopen(request, timeout=12) as response:
            content_type = response.headers.get("content-type", "")
            if "html" not in content_type:
                raise JobSourceError("HTML 페이지가 아닙니다.")
            return response.read(2_000_000).decode("utf-8", errors="replace")
    except JobSourceError:
        raise
    except Exception as exc:
        raise JobSourceError(f"웹페이지를 가져오지 못했습니다: {exc}") from exc


def fetch_job_page(url):
    """Fetch a public job posting page and extract plain text.

    This is a best-effort helper for user-provided URLs. It does not log in,
    bypass bot protection, or execute JavaScript, so dynamic pages may return
    sparse text.
    """
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        raise JobSourceError("공고 URL은 http:// 또는 https://로 시작해야 합니다.")
    html = _fetch_html(url)
    parser = JobPageParser()
    parser.feed(html)
    title = " ".join(parser.title.split()) or "사용자 입력 공고"
    meta = " ".join(parser.meta)
    body = _clean_page_text(" ".join(parser.text))
    text = "\n".join(part for part in [title, meta, body] if part)
    if len(text) < 80:
        raise JobSourceError("페이지에서 충분한 공고 본문을 찾지 못했습니다. 본문을 직접 복사해 입력해 주세요.")
    return {
        "id": "url:" + hashlib.sha256(url.encode()).hexdigest()[:16],
        "source": "URL 가져오기",
        "company": "",
        "title": title,
        "url": url,
        "location": "",
        "job_type": "",
        "experience": "",
        "education": "",
        "keywords": meta,
        "salary": "",
        "posting_date": "",
        "expiration_date": "",
        "active": "",
        "text": text,
    }


def _strip_html(fragment):
    fragment = re.sub(r"<(script|style|noscript|svg)[\s\S]*?</\1>", " ", fragment, flags=re.I)
    fragment = re.sub(r"<[^>]*(?:data-|class=|onclick=|href=)[^>]*>", " ", fragment, flags=re.I)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    text = " ".join(unescape(fragment).split())
    text = re.sub(r"\b(?:class|data-[\w-]+|onclick|href|src|style)=\"[^\"]*\"", " ", text)
    text = re.sub(r"\b(?:class|data-[\w-]+|onclick|href|src|style)='[^']*'", " ", text)
    text = re.sub(r"javascript:[^ ]+", " ", text, flags=re.I)
    text = re.sub(r"https?://\s*\+\s*document\.domain\s*\+\s*['\"][^ ]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _clean_jobkorea_card(text, title, company):
    blocked = [
        "선택된 조건 검색하기", "필터 검색결과", "즐겨찾기", "스크랩", "관심기업",
        "상세검색", "공고미리보기", "미리보기", "즉시지원", "홈페이지 지원",
        "잡코리아", "채용정보", "검색결과", "data-", "class=", "onclick", "document.domain",
    ]
    text = re.sub(r"\b[\w-]+=\"[^\"]*\"", " ", text)
    text = re.sub(r"\b[\w-]+='[^']*'", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    pieces = []
    for piece in re.split(r"\s{2,}|(?<=\))\s+|(?<=다)\s+", text):
        piece = piece.strip(" |·")
        if len(piece) < 3:
            continue
        if title and title in piece:
            piece = piece.replace(title, " ").strip(" |·")
        if company and company in piece:
            piece = piece.replace(company, " ").strip(" |·")
        if any(token in piece for token in blocked):
            continue
        if piece not in pieces:
            pieces.append(piece)
        if len(" ".join(pieces)) > 450:
            break
    summary = " ".join(pieces).strip()
    return summary[:500] or "공고 요약을 가져오지 못했습니다. 원문 공고에서 상세 내용을 확인하세요."


def _clean_job_title(title):
    title = re.sub(r"\s+", " ", title or "").strip(" |")
    title = re.sub(r"\s*-\s*잡코리아.*$", "", title)
    title = re.sub(r"^잡코리아\s*[:|-]?\s*", "", title)
    if title in {"잡코리아", "채용정보", "공고미리보기", "미리보기"}:
        return ""
    return title[:120]


def _summarize_detail_text(text, title=""):
    text = _strip_html(text)
    text = re.sub(r"\b[\w-]+=\"[^\"]*\"", " ", text)
    text = re.sub(r"\b[\w-]+='[^']*'", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    blocked = [
        "잡코리아", "로그인", "회원가입", "스크랩", "관심기업", "공유하기", "인쇄하기",
        "기업정보", "채용정보", "고객센터", "개인정보처리방침", "이용약관", "광고",
        "document.domain", "class=", "data-", "onclick",
    ]
    candidates = []
    for piece in re.split(r"(?<=[.!?。])\s+|\s{2,}|[|]", text):
        piece = piece.strip(" ·-")
        if len(piece) < 8:
            continue
        if title and title in piece:
            piece = piece.replace(title, " ").strip(" ·-")
        if any(token in piece for token in blocked):
            continue
        if re.search(r"(경력|신입|정규직|계약직|인턴|채용|모집|개발|데이터|AI|Python|분석|우대|자격|담당|업무|연봉|서울|경기|부산|대전|광주)", piece):
            if piece not in candidates:
                candidates.append(piece)
        if len(" ".join(candidates)) > 450:
            break
    return " ".join(candidates)[:500] or "공고 요약을 가져오지 못했습니다. 원문 공고에서 상세 내용을 확인하세요."


def _jobkorea_card_text(html, start, end):
    return _strip_html(html[start:end])


def search_jobkorea_jobs(keywords, count=20):
    """Search JobKorea listing pages and parse visible posting cards.

    This is a best-effort crawler for public search-result HTML. It does not log
    in, bypass bot protection, or execute JavaScript.
    """
    keywords = keywords.strip()
    if not keywords:
        raise JobSourceError("검색 키워드를 입력하세요.")
    params = urlencode({"stext": keywords})
    search_url = "https://www.jobkorea.co.kr/recruit/joblist?" + params
    html = _fetch_html(search_url)

    anchors = []
    for match in re.finditer(r'<a[^>]+href="([^"]*/Recruit/GI_Read/[^"]+)"[^>]*>([\s\S]*?)</a>', html, re.I):
        url = urljoin("https://www.jobkorea.co.kr", unescape(match.group(1)))
        title = _clean_job_title(_strip_html(match.group(2)))
        if len(title) < 3 or "스크랩" in title or "AD" == title:
            continue
        anchors.append((match.start(), url, title))

    rows, seen = [], set()
    for i, (start, url, title) in enumerate(anchors):
        if url in seen:
            continue
        seen.add(url)
        next_start = anchors[i + 1][0] if i + 1 < len(anchors) else min(len(html), start + 5000)
        card = _jobkorea_card_text(html, max(0, start - 1200), next_start)
        company = ""
        summary = ""
        try:
            detail = fetch_job_page(url)
            detail_title = _clean_job_title(detail.get("title") or "")
            if detail_title and not re.search(r"^(잡코리아|채용정보|공고미리보기)", detail_title):
                title = detail_title
            summary = _summarize_detail_text(detail.get("text", ""), title)
            company = detail.get("company", "")
        except JobSourceError:
            pass
        company_match = re.search(r"([\w가-힣㈜주식회사\.\-&· ]{2,40})\s+(?:관심기업|외국계|대기업|중견기업|중소기업|벤처|강소기업)", card)
        if not company and company_match:
            company = company_match.group(1).strip()
        if not summary:
            summary = _clean_jobkorea_card(card, title, company)
        if summary.startswith('">') or summary in {"AD", "광고"}:
            continue
        text = "\n".join(part for part in [company, title, summary] if part)
        rows.append({
            "id": "jobkorea:" + hashlib.sha256(url.encode()).hexdigest()[:16],
            "source": "잡코리아",
            "company": company,
            "title": title,
            "url": url,
            "location": "",
            "job_type": "",
            "experience": "",
            "education": "",
            "keywords": summary,
            "salary": "",
            "posting_date": "",
            "expiration_date": "",
            "active": "",
            "text": text[:4000],
        })
        if len(rows) >= max(1, min(int(count), 50)):
            break

    if not rows:
        raise JobSourceError("잡코리아 검색 결과에서 공고 목록을 찾지 못했습니다. 차단되었거나 페이지 구조가 바뀌었을 수 있습니다.")
    return rows


def _job_text(job):
    position = job.get("position") if isinstance(job.get("position"), dict) else {}
    parts = [
        _nested(job, "company", "detail", "name"),
        _text(position.get("title")),
        _text(position.get("industry")),
        _text(position.get("location")),
        _text(position.get("job-type")),
        _text(position.get("experience-level")),
        _text(position.get("required-education-level")),
        _text(position.get("job-code")),
        _text(job.get("keyword")),
        _text(job.get("salary")),
    ]
    return "\n".join(part for part in parts if part)


def search_saramin_jobs(keywords, count=20, access_key=None):
    """Search Saramin's official job-search API.

    The API requires an access key issued by Saramin. Set SARAMIN_ACCESS_KEY in
    the environment or pass access_key explicitly.
    """
    access_key = access_key or os.getenv("SARAMIN_ACCESS_KEY", "")
    if not access_key:
        raise JobSourceError("사람인 API 키가 없습니다. SARAMIN_ACCESS_KEY 환경변수를 설정하세요.")
    keywords = keywords.strip()
    if not keywords:
        raise JobSourceError("검색 키워드를 입력하세요.")

    params = urlencode({
        "access-key": access_key,
        "keywords": keywords,
        "count": max(1, min(int(count), 50)),
        "start": 0,
        "sort": "pd",
        "fields": "posting-date expiration-date count",
    })
    request = Request(
        "https://oapi.saramin.co.kr/job-search?" + params,
        headers={"Accept": "application/json", "User-Agent": "CareerTwinAI/1.0"},
    )
    try:
        with urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise JobSourceError(f"사람인 공고를 불러오지 못했습니다: {exc}") from exc

    if "result" in payload:
        message = _nested(payload, "result", "message") or "사람인 API 오류"
        raise JobSourceError(message)

    jobs = _nested(payload, "jobs", "job", default=[])
    if isinstance(jobs, dict):
        jobs = [jobs]
    if not isinstance(jobs, list):
        return []

    rows = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        position = job.get("position") if isinstance(job.get("position"), dict) else {}
        company = _nested(job, "company", "detail", "name")
        title = _text(position.get("title"))
        rows.append({
            "id": "saramin:" + str(job.get("id", "")),
            "source": "사람인",
            "company": company,
            "title": title,
            "url": str(job.get("url") or ""),
            "location": _text(position.get("location")),
            "job_type": _text(position.get("job-type")),
            "experience": _text(position.get("experience-level")),
            "education": _text(position.get("required-education-level")),
            "keywords": _text(job.get("keyword")),
            "salary": _text(job.get("salary")),
            "posting_date": str(job.get("posting-date") or ""),
            "expiration_date": str(job.get("expiration-date") or ""),
            "active": str(job.get("active", "")),
            "text": _job_text(job),
        })
    return rows
