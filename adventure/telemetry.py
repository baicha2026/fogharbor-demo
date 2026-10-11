"""完整记录留在本局；长局复盘均匀取样并保留准确汇总，避免接口长度上限。"""

from copy import deepcopy


def _sample(rows: list[dict], limit: int) -> list[dict]:
    if len(rows) <= limit:
        return deepcopy(rows)
    # 保留首尾和均匀间隔，不把漫长探索只裁成末尾片段。
    return [deepcopy(rows[i * (len(rows) - 1) // (limit - 1)]) for i in range(limit)]


def review_payload(game: dict, mode: str = "demo") -> dict:
    limits = {"battle_log": 200, "path": 401, "hit_points": 400, "dps_samples": 200}
    payload = {key: _sample(game[key], limit) for key, limit in limits.items()}
    payload.update(
        result=game["result"],
        mode=mode,
        summary={
            "steps": sum(row["event"] != "arrival" for row in game["path"]) - 1,
            "battle_rounds": len(game["battle_log"]),
            "hit_count": len(game["hit_points"]),
            "vacuum_rounds": sum(bool(row.get("vacuum")) for row in game["dps_samples"]),
            "sampled": any(len(game[key]) > limit for key, limit in limits.items()),
        },
    )
    return payload
