import psycopg2
from psycopg2 import Error


def test_postgres_connection():
    try:
        # Connection parameters - update these with your database details
        connection = psycopg2.connect(
            host="194-36-88-187.cloud-xip.com",
            database="postgres",  # default database
            user="root",
            password="KAM2024kam2024",
            port="5432",  # default PostgreSQL port
        )

        # Create a cursor object
        cursor = connection.cursor()

        # Print PostgreSQL details
        print("PostgreSQL server information:")
        print(connection.get_dsn_parameters())

        # Execute a test query
        cursor.execute("SELECT version();")

        # Fetch result
        db_version = cursor.fetchone()
        print("PostgreSQL database version:")
        print(db_version)

    except (Exception, Error) as error:
        print("Error while connecting to PostgreSQL:", error)

    finally:
        if "connection" in locals():
            if cursor:
                cursor.close()
            if connection:
                connection.close()
            print("PostgreSQL connection is closed")


if __name__ == "__main__":
    test_postgres_connection()
