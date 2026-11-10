# Spotify to YouTube Playlist Converter

A local web app that transfers your **Spotify Liked Songs** into a YouTube playlist. Built with **Python, FastAPI, SQLAlchemy, and SQLite**, it connects to the Spotify Web API and YouTube Data API v3 using OAuth 2.0.

The application includes a browser-based dashboard for authorizing accounts, importing liked songs, transferring tracks in batches, and checking transfer results.

## Features

- **Spotify integration:** Import liked songs, including track titles, artists, and Spotify IDs.
- **YouTube integration:** Search for corresponding videos and add them to a private YouTube playlist.
- **Batch transfers:** Choose how many songs to transfer in each run.
- **Local persistence:** Store track information, transfer statuses, and OAuth tokens in SQLite.
- **Playlist reuse:** Append to an existing playlist created by the app, or create a new one.
- **Status and error reporting:** See pending, matched, added, and failed counts through the dashboard.

> **Current scope:** This version imports **Liked Songs** from Spotify. It does not yet support choosing arbitrary Spotify playlists, and YouTube matching uses the first search result.

## Tech stack

| Component | Technology |
| --- | --- |
| Backend | Python, FastAPI |
| API calls | HTTPX, Spotify Web API, YouTube Data API v3 |
| Authentication | Spotify and Google OAuth 2.0 |
| Database | SQLite, SQLAlchemy |
| Frontend | HTML, CSS, JavaScript (embedded in `main.py`) |

## Prerequisites

- **Python 3.10 or newer**
- A **Spotify Developer** application with a client ID and client secret
- A **Google Cloud** project with **YouTube Data API v3** enabled
- A **Google OAuth 2.0 Web application** client with a client ID and client secret
- Spotify and Google/YouTube accounts you can sign into

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/justinmedina/spotify_to_youtube_playlist_converter.git
cd spotify_to_youtube_playlist_converter
```

### 2. Create a virtual environment

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows PowerShell:**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can skip activation and run `.\.venv\Scripts\python.exe` in place of `python` in the commands below.

### 3. Install dependencies

From the **repository root** (the folder containing `requirements.txt`):

```bash
python -m pip install -r requirements.txt
```

### 4. Configure Spotify and Google OAuth

Change into the application folder:

```bash
cd playlist_converter
```

Make a local `.env` file from the included example:

**macOS / Linux:**

```bash
cp .env.example .env
```

**Windows PowerShell:**

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set your real Spotify and Google client IDs and client secrets. Keep that file private.

**Spotify configuration**

1. Create an application in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Add this exact Redirect URI to the application's settings:
   `http://127.0.0.1:8000/auth/spotify/callback`
3. Copy the application's client ID and client secret into `.env`.

**Google / YouTube configuration**

1. Create or open a project in the [Google Cloud Console](https://console.cloud.google.com/).
2. Enable **YouTube Data API v3** for the project.
3. Configure the OAuth consent screen in **Google Auth Platform**. If the app is in testing mode, add the Google account you will use as a test user.
4. Create an OAuth 2.0 client of type **Web application**.
5. Add this exact **Authorized redirect URI**:
   `http://127.0.0.1:8000/auth/google/callback`
6. Copy the Google client ID and client secret into `.env`.

**Important:** Redirect URIs must match the configured values, including the port and path. For Spotify local development, use `127.0.0.1`, not `localhost`.

### 5. Run the app

From inside the **`playlist_converter`** folder:

```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Visit **http://127.0.0.1:8000** in your browser. The app automatically creates a local SQLite database named `songs.db` if one does not already exist.

## Using the converter

1. Click **Login Spotify** and authorize the app.
2. Click **Login Google** and authorize access to your YouTube account.
3. Under **Sync Spotify liked songs**, select the import limit and click **Sync liked songs**.
4. Under **Transfer to YouTube playlist**, enter the playlist title and choose a transfer batch size. Start with **5 to 10 songs**.
5. Click **Transfer**. By default, the app reuses its saved playlist if the title matches.
6. Use **Status counts** or **Show failed (last 10)** to inspect transfer results.

The dashboard also links to the FastAPI interactive API documentation at `/docs`.

## Useful endpoints

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/` | GET | Web dashboard |
| `/health` | GET | Server health check |
| `/docs` | GET | Interactive API documentation |
| `/auth/spotify/login` | GET | Start Spotify sign-in |
| `/auth/google/login` | GET | Start Google sign-in |
| `/spotify/sync_liked` | GET | Import Spotify liked songs into SQLite |
| `/transfer/youtube` | POST | Transfer pending songs to YouTube |
| `/tracks/status_counts` | GET | View song status counts |
| `/tracks/failed` | GET | View failed song transfers |

## Limitations and troubleshooting

- **YouTube API quotas:** Searching for videos and adding them to playlists consumes API quota. Use small batches and review errors if transfers stop. Changing the request delay does **not** reduce quota usage.
- **Song matching:** This version takes the first YouTube search result. It may choose a cover, live recording, or incorrect song.
- **Failures do not automatically retry:** Failed tracks are recorded as `failed` and are not selected in subsequent transfers without additional handling.
- **Creating another playlist:** The app tracks a song's transfer status globally. Songs previously marked `added` will not automatically transfer again into a new playlist.
- **OAuth redirect errors:** Double-check the exact redirect URI in the corresponding developer console and `.env` file.
- **Google authorization errors:** Check that YouTube Data API v3 is enabled and that your Google account is a test user when required.

## Security notes

This project is intended to run **locally**. It currently stores OAuth tokens in SQLite and does not implement OAuth `state` validation or access controls on its transfer endpoints. **Do not expose it publicly** without addressing those issues.

Never commit `.env`, `songs.db`, credentials, or OAuth tokens. The included `.gitignore` excludes local secrets and generated files. The `.env.example` file is safe to commit because it uses placeholders.

## Project structure

```text
spotify_to_youtube_playlist_converter/
├── README.md
├── requirements.txt
├── .gitignore
└── playlist_converter/
    ├── .env.example
    ├── .env                  # Local only, ignored by Git
    ├── songs.db             # Created locally, ignored by Git
    ├── main.py              # Dashboard and FastAPI app
    ├── routes.py            # Sync, transfer, and status endpoints
    ├── spotify_auth.py      # Spotify authorization
    ├── google_auth.py       # Google authorization
    ├── spotify_client.py    # Spotify API client
    ├── youtube_client.py    # YouTube API client
    ├── database.py          # SQLAlchemy database setup
    └── models.py            # Database models
```

## References

- [Spotify Web API](https://developer.spotify.com/documentation/web-api)
- [Spotify Redirect URI requirements](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri)
- [YouTube Data API v3](https://developers.google.com/youtube/v3)
- [FastAPI](https://fastapi.tiangolo.com/)
