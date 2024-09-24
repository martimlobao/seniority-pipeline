"""Dataclasses for job postings and processed job postings."""

from hashlib import sha256

from pydantic import BaseModel


class JobPosting(BaseModel):
    """Dataclass representing a raw job posting record."""

    url: str
    company: str
    title: str
    location: str
    scraped_on: int

    def __hash__(self) -> int:
        """Generates a hash based on the job posting fields.

        Note that this hash remains constant for the processed job posting.

        Returns:
            int: Hash value of the job posting.
        """
        # use only these fields for hashing so that the hash does not change
        # when we add seniority
        return hash((self.url, self.company, self.title, self.location, self.scraped_on))

    @property
    def cache_key(self) -> str:
        """Generates a Redis cache key based on the company and title."""
        return sha256(f"{self.company}\t{self.title}".encode()).hexdigest()

    @property
    def uuid(self) -> int:
        """Generates a unique identifier for each company and title.

        Uses the last 4 bytes of the cache key to create a signed 32-bit
        integer.
        """
        # use last 4 bytes of sha256 hash as UUID
        int_value: int = int(self.cache_key[:8], 16)

        # convert to a signed 32-bit integer using bitwise operations
        int32: int = int_value & 0xFFFFFFFF  # Ensure 32-bit
        return (int32 ^ 0x80000000) - 0x80000000


class ProcessedJobPosting(JobPosting):
    """Dataclass representing a job posting record with seniority data."""

    seniority: int
