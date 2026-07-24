"""Terminal receipt totals preserved when a later case stage fails."""

from __future__ import annotations


def summarize_failed_session_receipts(runs) -> dict[str, int]:
    receipts = [item.result.get("final_receipt") for item in runs
                if item.result.get("final_receipt")]
    return {
        "session_final_receipts": len(receipts),
        "session_verified_receipts": sum(item.get("status") == "VERIFIED" for item in receipts),
        "session_failed_receipts": sum(item.get("status") == "FAILED" for item in receipts),
        "session_retracted_receipts": sum(item.get("status") == "RETRACTED" for item in receipts),
    }
