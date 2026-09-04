"""Loads SEED_ENTITIES into the canonical_entities table. Run once before the bulk
crawl so entity resolution has its full seed list available from the first record."""
import asyncio
import sys

sys.path.insert(0, ".")

from src.entity_resolution.seed_entities import SEED_ENTITIES
from src.storage.database import SessionLocal, init_db
from src.storage.models import CanonicalEntity


async def main():
    await init_db()
    async with SessionLocal() as session:
        for canonical_name in SEED_ENTITIES:
            session.add(CanonicalEntity(canonical_name=canonical_name, entity_type="ORG"))
        await session.commit()
    print(f"Seeded {len(SEED_ENTITIES)} canonical entities.")


if __name__ == "__main__":
    asyncio.run(main())
