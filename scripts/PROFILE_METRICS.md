# Automatic profile metrics

The `Refresh profile metrics` GitHub Actions workflow runs daily at 22:15 UTC
(09:15 Sydney during daylight saving, 08:15 during standard time), on updater
changes, and manually from Actions. Standard hosted runners are free in this
public repository. No ChatGPT task, paid scraper, proxy subscription, or login
cookie is required.

The homepage already reads `profile-metrics.json` from GitHub's raw endpoint,
so scheduled bot commits reach visitors without requiring a Pages rebuild.

- Google Scholar: reads the all-time Citations cell after verifying the profile name.
- LinkedIn: reads the owner's exact follower count from public structured data or
  the profile's top card. Suggested people, post likes, rounded counts, and
  connections are excluded. If the existing `LINKEDIN_ACCESS_TOKEN` secret is
  configured with `r_member_profileAnalytics`, the official API is tried first.
- Each source is independent. A blocked request, login page, CAPTCHA, malformed
  value, or missing metric retains its last verified count and date. A successful
  check refreshes its verification date even if the count is unchanged.
- The Actions summary reports which sources were verified. If both sources fail,
  the job fails rather than reporting a successful refresh. There is no attempt
  to bypass access controls or CAPTCHAs. The screenshot-confirmed LinkedIn
  baseline is 20,393 on 24 November 2026; the Scholar baseline remains 36.

## Limits

Free public-page access is best effort: LinkedIn and Scholar may block cloud
runners, so a daily check does not guarantee daily fresh values. LinkedIn's
approved API requires a member token with the analytics permission; tokens can
expire. Scholar has no supported public citation-count API. Do not substitute
OpenAlex or Semantic Scholar counts while labelling them Google Scholar.
GitHub can disable scheduled workflows after 60 days of repository inactivity;
re-enable the workflow from Actions if that happens.

## Checks

Run `python -m pip install beautifulsoup4==4.15.0`, then
`python -m unittest discover -s scripts -p 'test_*.py'`.
Run `python scripts/profile_metrics.py` for a live refresh. Source errors log
only the exception class, never response bodies or credentials.
