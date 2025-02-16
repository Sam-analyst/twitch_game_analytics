import requests

def get_twitch_access_token(
    client_id : str,
    client_secret : str
) -> str:
    """
    Helper function to obtain an access token from Twitch.
    Access tokens expire after a certain number of days and
    there isn't a way to request one without an expiration date
    to my knowledge.

    Parameters:
    - client_id (str): twitch client id. This can be obtained by creating a twitch dev account
    - client_secret (str): twitch secret

    Returns:
    - new twitch access token (str)

    """

    url = "https://id.twitch.tv/oauth2/token"

    payload = {
        "client_id" : client_id,
        "client_secret" : client_secret,
        "grant_type" : "client_credentials"
    }

    response = requests.post(url, data=payload)

    access_token = response.json()["access_token"]

    print("here's your token:", access_token)

    return access_token