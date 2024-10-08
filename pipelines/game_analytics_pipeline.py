import os

from twitch_game_analytics import (SnowflakeConnection, SnowflakeExecutor,
                                   get_top_n_games, get_top_n_games_and_stats,
                                   read_sql_file)


def twitch_game_analytics_pipeline():

    # obtaining snowflake creds
    snowflake_username = os.getenv("SNFLK_UNAME")
    snowflake_password = os.getenv("SNFLK_PWD")
    snowflake_account = os.getenv("SNFLK_ACCT")

    # setting additional snowflake settins
    warehouse = "COMPUTE_WH"
    database = "TWITCH_GAME_ANALYTICS"
    schema = "GAME_ANALYTICS"
    n_games = 20

    # obtaining our dfs from the twitch api
    top_n_games_df = get_top_n_games(n_games)
    top_n_game_stats_df = get_top_n_games_and_stats(n_games)

    # read in our sql queries
    create_temp_games_dim_sql = read_sql_file(
        folder="games_dim", file_name="create_temp_games_dim.sql"
    )
    upsert_games_dim = read_sql_file(
        folder="games_dim", file_name="upsert_games_dim.sql"
    )

    # create our snowflake connection object
    sf_conn = SnowflakeConnection(
        snowflake_username,
        snowflake_password,
        snowflake_account,
        warehouse,
        database,
        schema,
    )

    # run full pipeline
    with sf_conn as conn:

        sf = SnowflakeExecutor(conn)

        # games_dim pipeline

        # create temp table
        sf.execute_sql(create_temp_games_dim_sql)

        # save data to temp table
        sf.write_pandas_df(df=top_n_games_df, table_name="temp_games_dim")

        # perform upsert into games_dim
        sf.execute_sql(upsert_games_dim)

        # delete temp table
        sf.delete_table("temp_games_dim")

        # games_fct pipeline

        # all we need to do in here is write into the table, which is scary
        sf.write_pandas_df(
            df=top_n_game_stats_df,
            table_name="game_metrics_fct",
            use_logical_type=True
        )

    return None
