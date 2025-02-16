import os
import time
import pandas as pd
import requests

# needs these credentials to access Twitch api
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_ACCESS_TOKEN = os.getenv("TWITCH_ACCESS_TOKEN")

# headers for all requests are the same
HEADERS = {
    "Client-ID": TWITCH_CLIENT_ID,
    "Authorization": f"Bearer {TWITCH_ACCESS_TOKEN}"
}

# endpoints per https://dev.twitch.tv/docs/api/reference/
TWITCH_API_ENDPOINTS = {
    "top_games" : "https://api.twitch.tv/helix/games/top",
    "streams" : "https://api.twitch.tv/helix/streams"
}

def get_twitch_games_and_streams(
    run_sample: bool = False
) -> dict:
    """
    Retrieves a dictionary of pandas DataFrames containing data on Twitch games and their
    corresponding live streams.

    This function first fetches the list of Twitch games using the `_get_Twitch_games` function, 
    then extracts a unique list of game IDs. It proceeds to fetch live stream data for these 
    games using the `_get_game_streams` function. The results are returned as a dictionary 
    containing two DataFrames: one for games and one for streams.

    Parameters:
    - run_sample: (bool, optional): Will run on one game if set to True. This should be used
    for development purposes only. Default is False.

    Returns:
    dict: A dictionary with the following keys:
        - "games_df" (pd.DataFrame): A DataFrame containing data on Twitch games.
        - "streams_df" (pd.DataFrame): A DataFrame containing live stream data for the games.

    Notes:
    - Results within these dataframes may contain duplicates. See _fetch_paginated_data
    for more details.
    - You must have two environmental variables set. One with the name TWITCH_CLIENT_ID
    containing your twitch client id and another TWITCH_ACCESS_TOKEN containing your
    twitch access token.
    """

    # check if the correct twitch authentication env variables have been set properly
    if TWITCH_CLIENT_ID is None or TWITCH_ACCESS_TOKEN is None:
        raise Exception("Twitch authentication env variables are returning as None")

    # getting the games df
    games_df = _get_twitch_games()

    # get unique list of game_ids
    game_ids = list(set(games_df["id"]))

    # select first game_id if run_sample set to true
    if run_sample is True:
        print("run_sample set to True. Pulling data for 1 game")
        game_ids = game_ids[:1]

    # get live streams for each game
    streams_df = _get_game_streams(game_ids)

    return {
        "games_df" : games_df,
        "streams_df" : streams_df
    }


def _get_game_streams(
    game_ids : list[str]
) -> pd.DataFrame:
    """
    Fetches all live streams for a list of game ids. Game ids are unique game ids
    created by Twitch. These can be pulled from the _get_Twitch_game function.

    Parameters:
    - game_ids (list[str]): A list of game ids for which stream data is to be fetched.

    Returns:
    pd.DataFrame: A pandas DataFrame containing all the live streams for the game.
    Each row in the returned DataFrame will represent a current live stream.
    
    Notes:
    - Duplicate data can be returned since we have to loop through pages. See
    _fetch_paginated_data for more details.
    """

    # need to loop through each game id provided and then combine the results into one df
    game_streams_df = []
    for game_id in game_ids:

        params = {
            "game_id" : game_id,
            "first" : 100 # this is the max rows you can call from the api
        }

        streams = _fetch_paginated_data(
            data_source="streams",
            headers=HEADERS,
            params=params
        )

        game_streams_df.append(streams)
    
    return pd.concat(game_streams_df)


def _get_twitch_games() -> pd.DataFrame:
    """
    Function to get all currently streamed games from Twitch.

    This function is needed to obtain the currently streamed game_ids
    from Twitch, which is needed to get the streams data.

    Notes
    - Duplicate data can be returned since we have to loop through pages. See
      _fetch_paginated_data for more details
    - Results will be returned from high to low in terms of game viewers
    """
    
    params = {
        "first" : 100 # this is the max rows you can call from the api
    }

    return _fetch_paginated_data(
        data_source="top_games",
        headers=HEADERS,
        params=params
    )

def _fetch_paginated_data(
    data_source : str,
    headers : dict,
    params : dict,
) -> pd.DataFrame:
    """
    According to Twitch's API docs, the max number of records that can be returned from a single call is 100.
    However, in many instances, we need more than 100 records. To address this, they recommend running a loop
    call the API multiple times and then combining the results. They also state that if a pagination
    value is returned within the json response, it indicates there's more data to obtain and that we can
    use the pagination value in the next api call to get the rest of the results.

    Some callouts with this methodology.
    - Since we're looping thru live data, duplicates will occur
    - Some records may be missed if a record was on the next page, but by the time we get to the next page
    it moves up. This is more concerning than the first bullet

    Per Twitch's recommendation, this function makes multiple API calls to a given end point, combines
    the results, and returns it as a pandas DataFrame.

    Parameters:
    - data_source (str): The API endpoint or data source to fetch data from.
    - headers (dict): The HTTP headers to include with the request, typically containing authentication tokens.
    - params (dict): The parameters for the API request, including any pagination or filtering parameters.

    Returns:
    - pd.DataFrame: A pandas DataFrame containing the concatenated results from all pages.

    Raises:
    - Exception: If the maximum page limit (1000) is reached before the end of the data, indicating a potential issue.
    """

    # instantiating our starting variables
    df_list = [] # empty list to append each page to
    page_count = 1 # arbitrary starting point for our page, which we define as 1
    max_pages = 1000 # the max number of pages - defining an upper limit out of infinite loop fear
    next_page = None # begin with next_page as None for our first call to Twitch

    while page_count <= max_pages:

        params["after"] = next_page
        
        response_json = _call_twitch_api(
            data_source=data_source,
            headers=headers,
            params=params
        )

        df = pd.DataFrame(response_json["data"])

        df_list.append(df)

        # the respone json will have a cursor value under pagination if there are more pages
        next_page = response_json["pagination"].get("cursor")

        # if there isn't a cursor value, then we've reached the end - no more pages :) so we can break the loop
        if next_page is None:
            print(f"reached the end - pulled back {page_count} pages")
            break

        page_count += 1
    
    # raise an error if we actually hit 1K pages
    if page_count == max_pages:
        raise Exception("Max page count hit - please investigate")

    return pd.concat(df_list)

def _call_twitch_api(
        data_source : str,
        headers : dict,
        params : dict,
        max_attempts : int = 3
) -> dict:
    """
    Makes a GET request to a specified Twitch API endpoint.

    This function checks if the provided `data_source` is a valid endpoint in the `Twitch_API_ENDPOINTS` 
    dictionary, then attempts to make a GET request to that endpoint with the given `headers` and `params`. 
    If the request fails (non-200 status code), it will retry up to the specified `max_attempts` 
    with a 5-second delay between each retry. If the request is still unsuccessful after all retries, 
    an exception is raised.

    Parameters:
    - data_source (str): The key for the desired Twitch API endpoint in `Twitch_API_ENDPOINTS`.
    - headers (dict): The HTTP headers to send with the GET request.
    - params (dict): The query parameters to include in the GET request.
    - max_attempts (int, optional): The maximum number of attempts to make if the request fails. Default is 3.

    Raises:
    - Exception: If `data_source` is not a valid key in `Twitch_API_ENDPOINTS`.
    - HTTPError: If the request fails after the maximum number of attempts.

    Returns:
    - dict: The JSON response from the API call, parsed into a Python dictionary.
    """

    if data_source not in TWITCH_API_ENDPOINTS.keys():
        raise Exception(f"{data_source} is not a valid data source")

    for i in range(max_attempts):

        response = requests.get(TWITCH_API_ENDPOINTS[data_source], headers=headers, params=params)

        # if we get a successful response end the loop
        if response.status_code == 200:
            break
        
        # if api request comes back unsuccessful, sleep for 5 seconds
        time.sleep(5)

        # if we hit our max retrys then we'll want throw an error
        if i + 1 == max_attempts:
            response.raise_for_status()
    
    return response.json()