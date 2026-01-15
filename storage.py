import json
import logging
import tempfile
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DB_FILE = Path("sent.json")


def load_sent():
    """
    Load the set of previously sent listing IDs.
    
    Returns:
        set: Set of listing IDs that have been sent
    """
    try:
        if DB_FILE.exists():
            content = DB_FILE.read_text(encoding='utf-8')
            data = json.loads(content)
            if not isinstance(data, list):
                logger.warning("sent.json contains invalid data, resetting to empty set")
                return set()
            return set(data)
        return set()
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse sent.json: {e}. Resetting to empty set.")
        # Backup corrupted file
        backup_path = DB_FILE.with_suffix('.json.bak')
        if DB_FILE.exists():
            DB_FILE.rename(backup_path)
            logger.info(f"Backed up corrupted file to {backup_path}")
        return set()
    except Exception as e:
        logger.error(f"Unexpected error loading sent.json: {e}")
        return set()


def save_sent(sent):
    """
    Save the set of sent listing IDs to disk using atomic write.
    
    Args:
        sent: Set of listing IDs to save
    """
    try:
        # Atomic write: write to temp file first, then rename
        temp_file = DB_FILE.with_suffix('.json.tmp')
        data = json.dumps(list(sent), indent=2, ensure_ascii=False)
        
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            dir=DB_FILE.parent,
            delete=False,
            suffix='.tmp'
        ) as f:
            temp_path = Path(f.name)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        
        # Atomic rename
        temp_path.replace(DB_FILE)
        logger.debug(f"Saved {len(sent)} sent listings to {DB_FILE}")
        
    except Exception as e:
        logger.error(f"Failed to save sent.json: {e}", exc_info=True)
        raise
