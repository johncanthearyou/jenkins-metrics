import pyodbc

def connect():
    return pyodbc.connect("Driver = {SQL Server};Server=localhost\\MSSQLSERVER01;Database=jenkins-metrics;Trusted_Connection=True;")

def verify_metrics():
    db_connection = connect()
    cursor = db_connection.cursor()
    cursor.execute("SELECT name, database_id, create_date FROM sys.databases;")
    row = cursor.fetchone()
    if row:
        print(row)

verify_metrics()