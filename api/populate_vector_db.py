import asyncio
import os
import sys
import time
from pathlib import Path
from loguru import logger
from tqdm.asyncio import tqdm

# Adjust imports based on whether we're running inside Docker or locally
if os.path.exists('/app'):
    # We're inside Docker container
    from app.services.ocr_service import OCRService
    from app.services.vector_service import VectorService
    from app.core.config import settings
    
    # In Docker, the project root is /app
    project_root = Path('/app')
else:
    # We're running locally
    # This allows running the script from the project root
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))
    
    from api.app.services.ocr_service import OCRService
    from api.app.services.vector_service import VectorService
    from api.app.core.config import settings

# --- Constants ---
# Use the original archive/docs-sm path
DATA_DIR = project_root / "archive" / "docs-sm"
BATCH_SIZE = 32
DELETE_EXISTING_INDEX = True
MAX_RETRIES = 10
RETRY_DELAY = 5

async def wait_for_marqo(vector_service, max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY):
    """Wait for Marqo to be available with retries"""
    logger.info(f"Waiting for Marqo to be available at {settings.MARQO_URL}...")
    
    for attempt in range(1, max_retries + 1):
        try:
            # Try to connect and check if index exists
            if await vector_service._ensure_index_exists_async():
                logger.success(f"Successfully connected to Marqo on attempt {attempt}")
                return True
            else:
                logger.warning(f"Attempt {attempt}/{max_retries}: Marqo connection succeeded but index creation failed")
        except Exception as e:
            logger.warning(f"Attempt {attempt}/{max_retries}: Failed to connect to Marqo: {str(e)}")
        
        if attempt < max_retries:
            wait_time = retry_delay * (2 ** (attempt - 1))  # Exponential backoff
            wait_time = min(wait_time, 60)  # Cap at 60 seconds
            logger.info(f"Retrying in {wait_time} seconds...")
            await asyncio.sleep(wait_time)
        else:
            logger.error("Failed to connect to Marqo after all retries")
            return False
    
    return False

async def populate_database():
    """
    Scans the data directory, processes each document using OCR,
    and populates the Marqo vector database.
    """
    logger.info("--- Starting Vector Database Population ---")
    logger.info(f"Source data directory: {DATA_DIR}")
    logger.info(f"Vector DB URL: {settings.MARQO_URL}")
    logger.info(f"Vector DB Index: {settings.MARQO_INDEX_NAME}")

    if not DATA_DIR.is_dir():
        logger.error(f"Data directory not found: {DATA_DIR}")
        logger.error("Please ensure the 'archive/docs-sm' directory exists and is populated.")
        return

    # --- Initialize Services ---
    ocr_service = OCRService()
    vector_service = VectorService()
    
    # Wait for Marqo to be available
    if not await wait_for_marqo(vector_service):
        logger.error("Cannot proceed with population as Marqo is not available")
        return

    # --- Clear Existing Index (Optional) ---
    if DELETE_EXISTING_INDEX:
        try:
            logger.warning(f"Attempting to delete existing index '{settings.MARQO_INDEX_NAME}'...")
            await vector_service.delete_index()
            # Re-initialize the service to ensure the index is re-created on demand
            vector_service = VectorService()
            logger.success("Index deleted and services re-initialized.")
        except Exception as e:
            logger.warning(f"Could not delete index (it might not exist yet). Error: {e}")

    # --- Gather Files ---
    logger.info("Scanning for document files...")
    all_files = list(DATA_DIR.glob("**/*.*"))
    image_files = [
        f for f in all_files if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}
    ]
    logger.info(f"Found {len(image_files)} total image files to process.")

    # --- Process and Index Files ---
    documents_to_add = []
    total_processed = 0
    total_failed = 0

    # Using tqdm.as_completed for progress bar on async tasks
    tasks = [process_file(file, ocr_service) for file in image_files]
    
    for future in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Processing Documents"):
        try:
            doc = await future
            if doc:
                documents_to_add.append(doc)
                if len(documents_to_add) >= BATCH_SIZE:
                    await index_batch(vector_service, documents_to_add)
                    total_processed += len(documents_to_add)
                    documents_to_add = []
            else:
                total_failed += 1
        except Exception as e:
            logger.error(f"Error in main processing loop: {e}")
            total_failed += 1

    # Index any remaining documents
    if documents_to_add:
        await index_batch(vector_service, documents_to_add)
        total_processed += len(documents_to_add)

    # --- Final Summary ---
    logger.success("--- Vector Database Population Completed ---")
    logger.info(f"Total documents successfully indexed: {total_processed}")
    logger.info(f"Total documents failed to process: {total_failed}")


async def process_file(image_path: Path, ocr_service: OCRService) -> dict | None:
    """
    Reads a file, extracts text using OCR, and returns a document dictionary.
    """
    try:
        document_type = image_path.parent.name
        with open(image_path, "rb") as f:
            file_content = f.read()

        text = await ocr_service.extract_text_from_file(file_content, image_path.name)

        if text and text.strip():
            clean_text = ocr_service.preprocess_text(text)
            return {
                # Use a sanitized and unique filename for the _id
                "_id": f"{document_type}_{image_path.name}".replace(" ", "_").replace("/", "_"),
                "text": clean_text,
                "document_type": document_type,
                "filename": image_path.name,
                "metadata": {"source_path": str(image_path)},
            }
        else:
            logger.warning(f"No text extracted from {image_path.name}, skipping.")
            return None
    except Exception as e:
        logger.error(f"Failed to process file {image_path.name}: {e}")
        return None

async def index_batch(vector_service: VectorService, batch: list):
    """
    Indexes a batch of documents into the vector database.
    """
    try:
        logger.debug(f"Indexing batch of {len(batch)} documents...")
        # Note: We are now passing the '_id' field directly in the document.
        # This requires the VectorService to be adjusted to use it.
        # If not adjusted, Marqo will generate its own IDs.
        await vector_service.add_documents(batch)
        logger.info(f"Successfully indexed batch of {len(batch)} documents.")
    except Exception as e:
        logger.error(f"Failed to index batch: {e}")
        # Optionally, re-raise or handle failed batches
        raise

if __name__ == "__main__":
    # Configure logging for the script
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}")
    
    try:
        asyncio.run(populate_database())
    except KeyboardInterrupt:
        logger.warning("--- Population process interrupted by user. ---")
    except Exception as e:
        logger.error(f"An unexpected error occurred during the population process: {e}")
