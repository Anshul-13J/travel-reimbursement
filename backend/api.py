import os
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ocr.factory import get_ocr
from extraction.parser import (
    ReceiptParser
)

# Configurations

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(
    exist_ok=True,
    parents=True
)

# App

app = FastAPI(
    title="Travel Reimbursement API",
    description="API for travel reimbursement OCR",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helpers and init

ocr_provider = get_ocr()
parser = ReceiptParser()

# Endpoints

@app.get("/")
def root():

    return {
        "status": "running",
        "service": "travel-reimbursement-api"
    }


@app.get("/health")
def health():

    return {
        "healthy": True,
    }


@app.post("/ocr")
async def extract_receipt(
    file: UploadFile = File(...)
):

    try:
        #save file for processing
        extension = (
            Path(file.filename)
            .suffix
        )
        unique_name = (
            f"{uuid.uuid4()}"
            f"{extension}"
        )
        file_path = (
            UPLOAD_DIR
            / unique_name
        )
        contents = (
            await file.read()
        )
        with open(
            file_path,
            "wb"
        ) as f:
            f.write(
                contents
            )
        # -------------------------
        # OCR
        # -------------------------
        raw_text = (
            ocr_provider
            .extract(
                str(file_path)
            )
        )
        parsed = parser.parse(
            raw_text
        )
        return {
            "receipt_id":
                str(uuid.uuid4()),
            "receipt_name":
                file.filename,
            "raw_text":
                raw_text,
            **parsed
        }

    except Exception as e:
        print(f"Error processing receipt: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    
    finally:
        try:
            if (
                file_path
                and file_path.exists()
            ):
                file_path.unlink()
        except Exception as cleanup_error:

            print(
                "Failed to delete "
                f"{file_path}: "
                f"{cleanup_error}"
            )