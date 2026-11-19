import logging
import time

from cities import CITIES
from extract import extract
from load import load
from transform import clean

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


def run_etl() -> None:
    """Extract, clean, and load data for every configured city."""
    failed = []
    for city, (latitude, longitude) in CITIES.items():
        try:
            weather, air = extract(city, latitude, longitude)
            rows = load(clean(weather, air, city))
            LOGGER.info("%s: saved %s rows", city, rows)
        except Exception:
            LOGGER.exception("%s failed", city)
            failed.append(city)
        time.sleep(0.5)  # be polite to the free API

    LOGGER.info("Done: %s of %s cities succeeded", len(CITIES) - len(failed), len(CITIES))
    if failed:
        raise RuntimeError(f"Pipeline failed for: {', '.join(failed)}")


if __name__ == "__main__":
    run_etl()