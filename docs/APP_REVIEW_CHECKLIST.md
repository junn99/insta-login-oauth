# Meta App Review Checklist (Min-Pass)

Use this as a reviewer-reproducible pre-submit check.

## App Domains

- [ ] In Meta App Dashboard -> Settings -> Basic, set `App Domains` to include:
  - [ ] `your-app.streamlit.app`
  - [ ] (Optional) `localhost` for local testing

## Valid OAuth Redirect URIs

- [ ] In Meta App Dashboard -> Instagram -> API setup with Instagram login -> `Valid OAuth Redirect URIs`, add exact Streamlit callback URLs:
  - [ ] `https://your-app.streamlit.app/Login`
  - [ ] `http://localhost:8501/Login` (local test, if used)
- [ ] Ensure app env `OAUTH_REDIRECT_URI` matches one registered URI exactly (including `/Login`, scheme, and host).

## Privacy Policy URL

- [ ] Set **Privacy Policy URL** to: `https://your-app.streamlit.app/Privacy`
- [ ] URL is publicly accessible **without login**.

## Data Deletion Instructions URL

- [ ] Set **Data Deletion Instructions URL** to: `https://your-app.streamlit.app/Data_Deletion`
- [ ] URL is publicly accessible **without login**.

## Screencast Outline (Permission -> In-App Proof)

- [ ] `instagram_business_basic` -> `/Login` (OAuth grant) and `/Live_Insights` profile/basic account section.
- [ ] `instagram_business_manage_insights` -> `/Dashboard` metrics/charts/audience and `/Live_Insights` business insights + audience demographics sections.
- [ ] Keep one continuous 2-3 minute recording showing login, permission grant, each mapped section, then `/Privacy` and `/Data_Deletion`.
- [ ] Note: Audience demographics require 100+ followers. Include this in the submission notes if the test account has fewer followers.
