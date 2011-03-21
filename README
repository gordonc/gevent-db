A gevent cooperative database pool using socketpair as bidirectional pipes with regular python threads
gevent-db uses pipes to trigger events between the gevent main thread and database connection threads

gevent-db supports python database specification v2.0 libraries, defaulting to pyodbc:
http://code.google.com/p/pyodbc/

DBPool initializes a connection pool with given odbc connection string and pool size

pool = db.DBPool('DSN=test',10)

DBPool.get retrieves a connection from the pool, and blocks if no connections are available
The connection destructor releases the connection back to the pool when the connection goes out of scope

conn = pool.get()

see examples in db.py testcases

