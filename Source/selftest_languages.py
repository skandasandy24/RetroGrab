"""Check the three Spotify language examples against live YouTube metadata."""
import sys

import yt_dlp

import spotify
from common import js_runtimes


CASES = (
    (
        {"title": "Not Ramaiya Vastavaiya (TAMIL)", "artists": ["Anirudh Ravichander", "Sreerama Chandra"],
         "duration": 203},
        {"tamil": "Pl9Ddheyr5M", "hindi": "4OXJvm4JBsU", "telugu": "RYErWwKbJHU"},
    ),
    (
        {"title": 'Veezha Veera (From "O.M: Operation Mole")', "artists": ["Sai Abhyankkar", "Tippu"],
         "duration": 236},
        {"original": "wkz07LzGpcY", "hindi": "YCwR9Egv8X4", "telugu": "ebrQN6zFBzU"},
    ),
    ({"title": "Ncs", "artists": ["NoCopyrightSounds"], "duration": 194}, {}),
)


def main():
    def log(message):
        print(message, file=sys.stderr)

    opts = {"quiet": True, "extract_flat": "in_playlist", "skip_download": True,
            "js_runtimes": js_runtimes()}
    passed = True
    print("| Spotify track | Versions | Asks? |")
    print("|---|---|---|")
    with yt_dlp.YoutubeDL(opts) as searcher:
        for track, expected in CASES:
            candidates = spotify.gather(searcher, track, log)
            versions = spotify.language_versions(searcher, track, candidates, log)
            ids = {key: entry["id"] for key, entry in versions.items()}
            preferred = spotify.spotify_version(track)
            labels = []
            for key, video_id in ids.items():
                label = f"{key}={video_id}"
                if key == preferred:
                    label += " (Spotify's)"
                labels.append(label)
            print(f"| {track['title']} | {', '.join(labels) or 'none'} | {'Yes' if len(ids) >= 2 else 'No'} |")
            if list(ids.items()) != list(expected.items()):
                log(f"Unexpected versions for {track['title']}. Expected {expected}.")
                passed = False
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
