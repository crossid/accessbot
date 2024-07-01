# Setup Slack

Slack can be used as the messaging platform to communicate with the bot.
Workforce can request and approve access from the bot directly via Slack.

## Create slack app

Navigate to [https://api.slack.com/apps](https://api.slack.com/apps/)

- Click on _Create New App_ and choose _From an app manifest_.
- Select your workspace and click _Next_.
- Copy [manifest](./slack_manifest.yml) and replace every _<backend_domain>_ with the actual backend
  domain and paste it into the _yaml_ tab, click _next_ then _create_.
  Note: even if backend is not deployed yet, you can define a value such _integration.mydomain.io_ as slack
  does not perform any doamin validations.
