import os

PROJECT_PARENT_DIRECTORY = "twitch_game_analytics"

def read_sql_file(folder, file_name):

    file_path = find_sql_file(folder, file_name)

    with open(file_path, "r") as file:
        sql = file.read()
    
    return sql

def find_sql_file(folder, file_name):
    current_directory = os.path.dirname(os.path.abspath(__file__))

    i = 0
    while i < 25: # putting a hardcoded stopper in just in case

        if os.path.basename(current_directory) == PROJECT_PARENT_DIRECTORY:
            parent_directory = os.path.dirname(current_directory)

            if os.path.basename(parent_directory) == PROJECT_PARENT_DIRECTORY:
                file_path = os.path.join(parent_directory, "sql", "games_dim", "create_temp_games_dim.sql")
                break
            
            else:
                file_path = os.path.join(PROJECT_PARENT_DIRECTORY, *["sql", "games_dim", "create_temp_games_dim.sql"])
                break
        
        else:
            current_directory = os.path.dirname(current_directory)
            i += 1
    
    return file_path
