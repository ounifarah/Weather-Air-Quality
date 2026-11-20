import logging

from cities import CITIES
from extract import extract_all
from load import load
from transform import clean

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


def run_etl() -> None:
    """Fetch all cities in one go, then clean and load each city."""
    results = extract_all(CITIES)

    failed = []
    for city, (weather, air) in results.items():
        try:
            rows = load(clean(weather, air, city))
            LOGGER.info("%s: saved %s rows", city, rows)
        except Exception:
            LOGGER.exception("%s failed", city)
            failed.append(city)

    LOGGER.info("Done: %s of %s cities succeeded", len(CITIES) - len(failed), len(CITIES))
    if failed:
        raise RuntimeError(f"Pipeline failed for: {', '.join(failed)}")


if __name__ == "__main__":
    run_etl()