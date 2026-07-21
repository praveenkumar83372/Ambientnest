"""
Chief Analytics Officer (CAO) Agent
Monitors YouTube channel metrics, evaluates past video performance,
and feeds data-driven strategic insights back to the CEO and shared memory.
"""

import os
import json
from googleapiclient.discovery import build
from channel_state import load_state, update_channel_metrics

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

class ChiefAnalyticsOfficer:
    def __init__(self):
        self.youtube = None
        if YOUTUBE_API_KEY:
            try:
                self.youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
            except Exception as e:
                print(f"⚠️ YouTube API client build error: {e}")

    def fetch_recent_channel_performance(self, channel_id=None, max_results=10):
        """
        Fetches view count, like count, and comment statistics for recent Shorts uploads.
        Falls back to local `channel_state.json` if YouTube API key is unconfigured or restricted.
        """
        print("\n📊 [CAO Agent] Fetching channel performance metrics...")
        state = load_state()

        if not self.youtube:
            print("⚠️ YOUTUBE_API_KEY unavailable. CAO using channel memory state.")
            return {
                "source": "channel_state_fallback",
                "metrics": state.get("metrics", {}),
                "top_performing_category": "Dark Psychology & Wealth Secrets",
                "recent_stats": state.get("history", [])[:5]
            }

        try:
            # Query recent uploads from channel
            search_kwargs = {
                "part": "snippet",
                "order": "date",
                "type": "video",
                "maxResults": max_results
            }
            if channel_id:
                search_kwargs["channelId"] = channel_id
            else:
                search_kwargs["forMine"] = True

            res = self.youtube.search().list(**search_kwargs).execute()
            video_ids = [item["id"]["videoId"] for item in res.get("items", []) if "videoId" in item.get("id", {})]

            if not video_ids:
                return {
                    "source": "youtube_api_empty",
                    "metrics": state.get("metrics", {}),
                    "recent_stats": []
                }

            # Retrieve statistics for video IDs
            stats_res = self.youtube.videos().list(
                part="statistics,snippet",
                id=",".join(video_ids)
            ).execute()

            performance_data = []
            total_views = 0

            for item in stats_res.get("items", []):
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})

                views = int(stats.get("viewCount", 0))
                likes = int(stats.get("likeCount", 0))
                comments = int(stats.get("commentCount", 0))
                title = snippet.get("title", "Untitled")

                total_views += views
                performance_data.append({
                    "title": title,
                    "views": views,
                    "likes": likes,
                    "comments": comments
                })

            # Sync views back to local state
            update_channel_metrics(state, revenue_usd=round(total_views * 0.003, 2))  # Est. $3 RPM average

            report = {
                "source": "youtube_api_live",
                "total_recent_views": total_views,
                "recent_stats": performance_data,
                "top_video": max(performance_data, key=lambda x: x["views"]) if performance_data else None
            }

            print(f"✅ Performance fetched successfully. Total recent views analyzed: {total_views}")
            return report

        except Exception as e:
            print(f"⚠️ YouTube API fetch warning: {e}. Falling back to internal state.")
            return {
                "source": "fallback_error",
                "error": str(e),
                "metrics": state.get("metrics", {}),
                "recent_stats": state.get("history", [])[:5]
            }

    def generate_ceo_briefing(self):
        """Generates a executive briefing summary to feed into CEO strategic prompts."""
        perf = self.fetch_recent_channel_performance()
        state = load_state()

        briefing = {
            "channel_target_progress": {
                "subscribers": state["metrics"].get("subscribers", 0),
                "total_videos": state["metrics"].get("total_videos_published", 0),
                "estimated_revenue_usd": state["metrics"].get("estimated_revenue_usd", 0.0),
                "target_goal_usd": state["metrics"].get("current_target_usd", 1000.0)
            },
            "recent_performance_summary": perf
        }
        return briefing


if __name__ == "__main__":
    cao = ChiefAnalyticsOfficer()
    briefing = cao.generate_ceo_briefing()
    print("CEO Strategic Briefing:")
    print(json.dumps(briefing, indent=2))