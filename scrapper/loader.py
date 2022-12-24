import logging
import asyncio
from core.database import Database

logging.basicConfig(
    level='INFO',
    format="%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

db = Database(asyncio.get_event_loop())
