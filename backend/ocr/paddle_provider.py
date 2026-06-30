from unittest import result

from paddleocr import PaddleOCR
from .base import OCRProvider

class PaddleOCRProvider(OCRProvider):

    def __init__(self):

        # self.ocr = PaddleOCR(
        #     use_angle_cls=True,
        #     lang="en"
        # )
        self.ocr = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            lang="en"
        )

    def extract(self, file_path):
        result = self.ocr.predict(file_path)
        texts = []
        for page in result:
            texts.extend(
                page["rec_texts"]
            )
        return "\n".join(texts)
