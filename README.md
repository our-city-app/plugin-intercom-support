# plugin-intercom-support
Plugin to bridge rogerthat multiuserchat to intercom multiuser chat

# Dependencies
- [GAE plugin framework](https://github.com/rogerthat-platform/gae-plugin-framework)
- Rogerthat plugin for GAE plugin framework(https://github.com/rogerthat-platform/plugin-rogerthat-api)

# Configuration:
```json
{
  "name": "intercom_support",
  "order": 1,
  "version": "master",
  "url": "https://github.com/rogerthat-platform/plugin-intercom-support.git",
  "configuration": {
    "rogerthat_api_key": "...",
    "intercom_api_access_key": "...",
    "intercom_webhook_hub_secret": "..."
  }
}
```

# Intercom webhook configuration
Point the webhook to your GAE application to the following resource: ```/plugins/intercom-support/intercom-webhook```
