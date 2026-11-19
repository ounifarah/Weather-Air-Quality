import logging

from extract import extract
from load import load
from transform import clean

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)

CITIES = {
    "Tunis": (36.8065, 10.1815),
    "Sfax": (34.7406, 10.7603),
    "Sousse": (35.8256, 10.6369),
    "Bizerte": (37.2744, 9.8739),
    "Gabes": (33.8815, 10.0982),
}


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

    if failed:
        raise RuntimeError(f"Pipeline failed for: {', '.join(failed)}")


if __name__ == "__main__":
    run_etl()