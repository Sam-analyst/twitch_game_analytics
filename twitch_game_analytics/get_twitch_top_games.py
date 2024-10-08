import os
import time
from datetime import datetime, timezone

import pandas as pd
import requests

twitch_client_id = os.getenv("TWITCH_CLIENT_ID")
twitch_access_token = os.getenv("TWITCH_ACCESS_TOKEN")

# headers for all requests are the same
HEADERS = {
    "Client-ID": twitch_client_id,
    "Authorization": f"Bearer {twitch_access_token}"
}

# endpoints per https://dev.twitch.tv/docs/api/reference/
TWITCH_API_ENDPOINTS = {
    "top_games" : "https://api.twitch.tv/helix/games/top",
    "streams" : "https://api.twitch.tv/helix/streams"
}

# max attempts if api fails
MAX_API_ATTEMPTS = 3

def get_top_n_games_and_stats(
        limit : int = 1,
    ) -> pd.DataFrame:

    # first get top n game ids
    top_n_games_df = get_top_n_games(limit)

    # change it to a list
    game_ids_list = list(top_n_games_df["GAME_ID"].values)

    # for each game, pull approx current viewers + number of streamers
    dfs = []
    for game_id in game_ids_list:

        streamers = get_game_viewers(game_id)

        game_stats = (streamers
                      .groupby("game_id")
                      .agg(
                          {"viewer_count" : "sum",
                           "user_id" : "count"
                           }
                        )
                      .reset_index()
                      .rename(columns={"viewer_count" : "total_viewers",
                                       "user_id" : "num_streamers"}
                             )
                      )
        
        dfs.append(game_stats)
    
    df = pd.concat(dfs).reset_index(drop=True)

    # convert viewer_count float to int
    df["total_viewers"] = df["total_viewers"].astype(int)

    # adding in snapshot datetime
    snapshot_dt = datetime.now(timezone.utc)
    df["snapshot_datetime"] = snapshot_dt
    df["snapshot_dt"] = int(snapshot_dt.strftime("%Y%m%d")) # storing date as int in yyyymmdd format

    # uppercase all columns, which is needed to write to snowflake
    df.columns = df.columns.str.upper()

    return df

def get_top_n_games(
        limit : int = 1,
    ) -> pd.DataFrame:
    """
    Function to get the current top n games from twitch in terms of viewer count
    """

    params = {
        "first" : limit
    }

    response_json = get_twitch_data("top_games", params)

    df = pd.DataFrame(response_json["data"])

    # rename columns for consistency and clarity
    df.rename(columns={
        "id" : "game_id",
        "name" : "game_name"
    }, inplace=True)

    # uppercase all columns, which is needed to write to snowflake
    df.columns = df.columns.str.upper()

    return df
    
    
def get_game_viewers(
        twitch_game_id : str
    ) -> pd.DataFrame:
    """
    Function to obtain total viewer count for a game
    """

    params = {
        "game_id": twitch_game_id,
        "first" : 100 # requesting the max num of rows, which is 100
    }

    streams_df_list = []
    page_count = 1
    next_page = None
    max_pages = 1000

    # api pulls back only 100 streams at a time so need to loop thru pages as long
    # as we return a pagination - cursor value
    while page_count <= max_pages:

        params["after"] = next_page
        
        response_json = get_twitch_data("streams", params)

        df = pd.DataFrame(response_json["data"])

        streams_df_list.append(df)

        next_page = response_json["pagination"].get("cursor")

        if next_page is None:
            print(f"reached the end - pulled back {page_count} pages for game_id {twitch_game_id}")
            break

        page_count += 1
    
    # raise an error if we actually hit 1K pages
    if page_count == max_pages:
        raise Exception(f"Max page count hit - please investigate game id {twitch_game_id}")

    df = pd.concat(streams_df_list)

    # per twitchs docs, users can be duplicated across pages as we loop so gonna take avg to dedupe

    # first overwrite tags column to str so that we can group by it
    df["tags"] = df["tags"].astype(str)

    # group by everything except tags_ids, which is a deprecated column that returns empty list
    grouping_columns = [column for column in df.columns if column not in ["viewer_count", "tag_ids"]]

    df = df.groupby(grouping_columns)["viewer_count"].mean().reset_index()

    return df

def get_twitch_data(
        data_source : str,
        params : dict
    ):
    """
    Function that runs a get request call to a given twitch api endpoint
    """

    if data_source not in TWITCH_API_ENDPOINTS.keys():
        raise Exception(f"{data_source} is not a valid data source")

    for i in range(MAX_API_ATTEMPTS):

        response = requests.get(TWITCH_API_ENDPOINTS[data_source], headers=HEADERS, params=params)

        if response.status_code == 200:
            break
        
        # if api request comes back unsuccessful, sleep for 5 seconds
        time.sleep(5)

        # if we hit our max retrys then we'll want throw an error
        if i + 1 == MAX_API_ATTEMPTS:
            response.raise_for_status()
    
    return response.json()