"""Small cross-library checks that do not need network access or model downloads."""

import tempfile
import unittest
from pathlib import Path

from career_twin.ingest import extract, render_page
from career_twin.retrieval import search


class IntegrationTests(unittest.TestCase):
    def test_pdf_text_and_page_rendering(self):
        import fitz

        document = fitz.open()
        document.new_page().insert_text((72, 72), "PDF evidence")
        content = document.tobytes()
        document.close()

        chunks, warnings = extract("paper.pdf", content)
        self.assertEqual(warnings, [])
        self.assertIn("PDF evidence", chunks[0]["text"])
        self.assertEqual(chunks[0]["page"], 1)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "paper.pdf"
            path.write_bytes(content)
            self.assertTrue(render_page(path, 1).startswith(b"\x89PNG\r\n\x1a\n"))

    def test_faiss_search_with_embeddings(self):
        class FakeEmbeddings:
            def embed(self, texts):
                return [[1.0, 0.0] if "Python" in text else [0.0, 1.0]
                        for text in texts]

        records = [
            {"id": "python", "name": "Project", "text": "Python search"},
            {"id": "sql", "name": "Project", "text": "SQL reports"},
        ]
        hits = search("Python", records, ai=FakeEmbeddings())
        self.assertEqual(hits[0]["id"], "python")
        self.assertEqual(hits[0]["search_method"], "BM25 + FAISS / RRF")


if __name__ == "__main__":
    unittest.main()
