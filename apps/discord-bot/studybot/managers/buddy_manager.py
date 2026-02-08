"""バディマッチング ビジネスロジック"""

import logging

from studybot.repositories.buddy_repository import BuddyRepository

logger = logging.getLogger(__name__)

COMPATIBILITY_WEIGHTS = {
    "subject_overlap": 0.4,
    "timezone_compat": 0.2,
    "pattern_similarity": 0.2,
    "style_compat": 0.2,
}


class BuddyManager:
    """バディマッチングの管理"""

    def __init__(self, db_pool) -> None:
        self.repository = BuddyRepository(db_pool)

    async def get_or_create_profile(self, user_id: int, username: str) -> dict | None:
        await self.repository.ensure_user(user_id, username)
        return await self.repository.get_profile(user_id)

    async def update_profile(
        self,
        user_id: int,
        username: str,
        subjects: list[str],
        preferred_times: list[str],
        study_style: str,
    ) -> None:
        await self.repository.ensure_user(user_id, username)
        await self.repository.upsert_profile(user_id, subjects, preferred_times, study_style)

    async def find_buddy(
        self, user_id: int, username: str, guild_id: int, subject: str | None = None
    ) -> dict:
        await self.repository.ensure_user(user_id, username)
        my_profile = await self.repository.get_profile(user_id)
        if not my_profile:
            await self.repository.upsert_profile(
                user_id,
                [subject] if subject else [],
                [],
                "focused",
            )
            my_profile = await self.repository.get_profile(user_id)

        candidates = await self.repository.find_compatible(user_id, guild_id, subject)
        if not candidates:
            return {"error": "互換性のあるバディが見つかりませんでした"}

        scored = []
        for c in candidates:
            score = self._calculate_compatibility(my_profile, c)
            scored.append((c, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        best_candidate, best_score = scored[0]

        match_id = await self.repository.create_match(
            user_id,
            best_candidate["user_id"],
            guild_id,
            subject,
            best_score,
        )

        return {
            "match_id": match_id,
            "partner_id": best_candidate["user_id"],
            "partner_name": best_candidate["username"],
            "subject": subject,
            "compatibility_score": round(best_score, 2),
        }

    def _calculate_compatibility(self, profile_a: dict, profile_b: dict) -> float:
        w = COMPATIBILITY_WEIGHTS
        score = 0.0

        # Subject overlap (Jaccard similarity)
        subjects_a = set(profile_a.get("subjects", []) or [])
        subjects_b = set(profile_b.get("subjects", []) or [])
        if subjects_a or subjects_b:
            intersection = len(subjects_a & subjects_b)
            union = len(subjects_a | subjects_b)
            score += (intersection / union if union > 0 else 0) * w["subject_overlap"]
        else:
            score += 0.5 * w["subject_overlap"]

        # Time compatibility
        times_a = set(profile_a.get("preferred_times", []) or [])
        times_b = set(profile_b.get("preferred_times", []) or [])
        if times_a and times_b:
            overlap = len(times_a & times_b)
            total = len(times_a | times_b)
            score += (overlap / total if total > 0 else 0) * w["timezone_compat"]
        else:
            score += 0.5 * w["timezone_compat"]

        # Pattern similarity (simplified)
        score += 0.5 * w["pattern_similarity"]

        # Style compatibility
        style_a = profile_a.get("study_style", "focused")
        style_b = profile_b.get("study_style", "focused")
        style_score = 1.0 if style_a == style_b else 0.5
        score += style_score * w["style_compat"]

        return score

    async def get_active_matches(self, user_id: int) -> list[dict]:
        return await self.repository.get_active_matches(user_id)

    async def get_match_history(self, user_id: int, limit: int = 20) -> list[dict]:
        return await self.repository.get_match_history(user_id, limit)

    async def end_match(self, match_id: int) -> None:
        await self.repository.end_match(match_id)

    async def check_concurrent_session(self, user_id: int) -> bool:
        """バディが同時にセッション中かチェック"""
        return await self.repository.has_active_buddy_session(user_id)
