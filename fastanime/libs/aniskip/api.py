# fastanime/libs/aniskip/api.py

import logging
from typing import List, Literal, Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

ANISKIP_API_URL = "https://api.aniskip.com/v2/skip-times"


class SkipTime(BaseModel):
    """Represents a single skip interval (e.g., an opening or ending)."""

    interval: tuple[float, float]
    skip_type: Literal["op", "ed"] = Field(alias="skipType")
    skip_id: str = Field(alias="skipId")
    episode_length: float = Field(alias="episodeLength")


class SkipTimeResult(BaseModel):
    """Represents the full response from the Aniskip API for an episode."""

    found: bool
    results: List[SkipTime] = Field(default_factory=list)
    message: Optional[str] = None
    status_code: int = Field(alias="statusCode")


class AniSkip:
    """A client for fetching opening and ending skip times from the Aniskip API."""

    @classmethod
    def get_skip_times(
        cls,
        mal_id: int,
        episode_number: int,
        types: List[Literal["op", "ed"]] = ["op", "ed"],
    ) -> Optional[SkipTimeResult]:
        """
        Fetches skip times for a specific anime episode from Aniskip.

        Args:
            mal_id: The MyAnimeList ID of the anime.
            episode_number: The episode number.
            types: A list of types to fetch ('op' for opening, 'ed' for ending).

        Returns:
            A SkipTimeResult object if the request is successful, otherwise None.
        """
        if not mal_id or not episode_number:
            return None

        url = f"{ANISKIP_API_URL}/{mal_id}/{episode_number}"
        params = [("type", t) for t in types]

        try:
            with httpx.Client() as client:
                response = client.get(url, params=params, timeout=5)
                # Aniskip can return 404 for not found, which is a valid response.
                if response.status_code not in [200, 404]:
                    response.raise_for_status()

                return SkipTimeResult.model_validate(response.json())
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as e:
            logger.error(
                f"Aniskip API request failed for MAL ID {mal_id}, Ep {episode_number}: {e}"
            )
            return None
