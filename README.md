# OfficeBuddy Deployment Structure

OfficeBuddy is an AI-powered workplace email assistant built using Streamlit, Groq, and SMTP email delivery.

## Project Structure

```text
OfficeBuddy_Deployment/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
└── config/
    └── contacts.json
```

## Configuration

The working credentials are not stored directly inside `app.py`. They must be placed in an environment file.

1. Rename `.env.example` to `.env`.
2. Add the actual values for:
   - `SENDER_EMAIL`
   - `SENDER_APP_PASSWORD`
   - `GROQ_API_KEY`
3. Update `config/contacts.json` if recipient names, roles, or email addresses need to change.

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deployment Notes

For deployment, configure the same environment variables in the hosting platform instead of uploading the `.env` file.

Required environment variables:

```text
SENDER_EMAIL
SENDER_APP_PASSWORD
GROQ_API_KEY
SMTP_HOST
SMTP_PORT
CONTACTS_FILE
```

## Important Security Note

Never commit `.env` or real API keys to GitHub. Keep all credentials inside environment variables or platform secrets.
