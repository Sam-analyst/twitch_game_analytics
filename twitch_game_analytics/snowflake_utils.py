import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas


class SnowflakeConnection:
    def __init__(self, username, password, account, warehouse, database, schema):
        """Initialize the SnowflakeConnection object with necessary parameters"""
        self.username = username
        self.password = password
        self.account = account
        self.warehouse = warehouse
        self.database = database
        self.schema = schema
    
    def __enter__(self):
        """Establish a connection to Snowflake when entering the context"""
        self.conn = snowflake.connector.connect(
            user=self.username,
            password=self.password,
            account=self.account,
            warehouse=self.warehouse,
            database=self.database,
            schema=self.schema
        )

        return self.conn
    
    def __exit__(self, exc_type, exc_value, traceback):
        """Close the Snowflake connection when exiting the context"""
        self.conn.close()

class SnowflakeExecutor:
    def __init__(self, conn):
        """Initialize the SnowflakeExecutor with an active connection"""
        self.conn = conn
    
    def delete_table(self, table_name):
        sql = f"DROP TABLE IF EXISTS {table_name}"
        self.execute_sql(sql)
        print(f"sucessfully dropped {table_name}")

    def execute_sql(self, sql):
        """Execute a provided sql using the active connection"""
        with self.conn.cursor() as cursor:
            cursor.execute(sql)

    def write_pandas_df(self, df, table_name, **kwargs):
        """Method to insert pandas df into table name"""

        # upper case table name in case lower was provided
        table_name = table_name.upper()

        success, nchunks, nrows, _ = write_pandas(self.conn, df, table_name, **kwargs)
        if success:
            print(f"Sucessfully inserted {nrows} rows into {table_name}")
        else:
            raise Exception(f"Failed to insert data into {table_name}")
    
