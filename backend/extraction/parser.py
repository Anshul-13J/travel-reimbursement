from pathlib import Path
import traceback

from llm.models import structured_llm


class ReceiptParser:

    def __init__(self):
        self.prompt = (
            Path(
                "extraction/prompt.md"
            ).read_text()
        )

    def parse(
        self,
        receipt_text
    ):

        try:

            prompt = (
                self.prompt
                .format(
                    receipt=receipt_text
                )
            )
            result = (
                structured_llm
                .invoke(prompt)
            )
            return result.model_dump()

        except Exception as e:
            print(f"Error parsing receipt: {e}")
            traceback.print_exc()
            raise