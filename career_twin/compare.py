"""이력서의 표현과 공고 문장을 대조한다. 검색 결과를 역량 판정으로 취급하지 않는다."""
import re

from .retrieval import search, source_label


_COMMON_ENGLISH = {"and", "the", "for", "with", "from", "job", "role", "team", "year", "years"}
_UNPROVEN = re.compile(r"(?:하지\s*않|한\s*적\s*없|경험\s*없|예정|계획|학습\s*중|공부\s*중|미경험)")


def english_keywords(text):
    """비교 가능한 영문 기술 표기만 추린다. 기술 역량의 증명은 아니다."""
    found = re.findall(r"(?<![A-Za-z0-9])[A-Za-z][A-Za-z0-9.+#-]{1,}(?![A-Za-z0-9])", text)
    return list({word.lower(): word for word in found if word.lower() not in _COMMON_ENGLISH}.values())


def evidence_sentences(chunks):
    """서로 다른 경험과 계획이 한 검색 청크에 섞이지 않도록 문장 단위로 나눈다."""
    records = []
    for chunk in chunks:
        for index, sentence in enumerate(re.split(r"(?<=[.!?])\s+|[\r\n]+", chunk["text"])):
            sentence = sentence.strip()
            if sentence:
                records.append({**chunk, "id": f"{chunk['id']}:sentence:{index}", "text": sentence})
    return records


def compare_resume(requirements, chunks):
    """요구사항별 관련 원문과 문서에 없는 영문 기술 표기를 반환한다."""
    if any(chunk.get("kind") != "personal" for chunk in chunks):
        raise ValueError("이력서 비교에는 개인 문서만 사용할 수 있습니다.")
    resume_text = "\n".join(chunk["text"] for chunk in chunks)
    resume_lower = resume_text.lower()
    sentences = evidence_sentences(chunks)
    rows = []
    for requirement in requirements:
        query = str(requirement.get("text") or "").strip()
        if not query or re.match(r"^(?:원문\s*URL\s*:|https?://)", query, re.IGNORECASE):
            continue
        keywords = english_keywords(query)
        hits = search(query, sentences, k=5)
        hit = next((item for item in hits if not keywords or any(re.search(
            rf"(?<![A-Za-z0-9]){re.escape(word)}(?![A-Za-z0-9])", item["text"], re.IGNORECASE)
            for word in keywords)), None)
        quote = hit["text"].strip() if hit else ""
        unproven = bool(_UNPROVEN.search(quote))
        rows.append({
            "requirement": query,
            "category": requirement.get("category", "업무"),
            "resume_quote": quote,
            "source": source_label(hit) if hit else "",
            "signal": "경험 확인 필요" if unproven else "관련 표현 발견" if hit else "관련 표현 미발견",
            "suggestion": (
                "이 문장은 미수행·학습 예정 표현을 포함합니다. 실제 수행 경험이 있다면 별도 근거를 적고, 없다면 경험으로 바꾸지 마세요."
                if unproven else
                "실제로 수행한 역할과 결과를 더 구체적으로 적고, 공고의 용어는 사실과 일치할 때만 사용하세요."
                if hit else
                "관련 경험이 있다면 수행 내용과 결과를 이력서에 추가하세요. 경험이 없다면 새로 만들어 적지 마세요."
            ),
        })
    keywords = english_keywords("\n".join(row["requirement"] for row in rows))
    missing = [word for word in keywords if not re.search(
        rf"(?<![A-Za-z0-9]){re.escape(word)}(?![A-Za-z0-9])", resume_lower, re.IGNORECASE)]
    return {"rows": rows, "missing_keywords": missing}
