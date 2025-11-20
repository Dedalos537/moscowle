import pymysql

def get_db_connection():
    # Load environment variables from .env file
    from dotenv import load_dotenv
    import os

    load_dotenv(dotenv_path='.env')

    db_host = os.getenv('DB_HOST')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_name = os.getenv('DB_NAME')

    # Establish a database connection
    connection = pymysql.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_name,
        cursorclass=pymysql.cursors.DictCursor
    )

    return connection


