# twitch_game_analytics
A Python package to fetch live stream data from the Twitch API.

### Example Usage
Check out this [Jupyer notebook](https://github.com/Sam-analyst/twitch_game_analytics/blob/main/docs/example.ipynb) for a quick tutorial on how to pull Twitch data using this package.

### Installation
Install directly from GitHub
``` bash
pip install git+https://github.com/Sam-analyst/twitch_game_analytics.git
```

### Authentication Setup
1. Create a Twitch developer account if you don't have one already: [dev.twitch.tv](dev.twitch.tv)
2. Register a new application in the console
3. Once registered, create a new secret and copy your `Client ID` and `Client Secret`
4. Use the following helper [function](https://github.com/Sam-analyst/twitch_game_analytics/blob/88fa5a17f073c887f061ca4545ac61953ba1ec05/twitch_game_analytics/utils.py#L3) to request an access token.
``` python
from twitch_game_analytics.utils import get_twitch_access_token

token = get_twitch_access_token(client_id="your-client-id", client_secret="your-client-secret")
```
5. After retrieving your credentials, set the following environment variables:
``` bash
export TWITCH_CLIENT_ID="your-client-id"
export TWITCH_ACCESS_TOKEN="your-access-token"
```
The package automatically reads these from the environment for API authentication.
