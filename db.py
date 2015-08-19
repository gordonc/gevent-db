import gevent.socket
from gevent import queue

# avoid socket monkey patching
import imp
fp, pathname, description = imp.find_module('socket')
try:
    socket_ = imp.load_module('socket_', fp, pathname, description)
finally:
    if fp:
        fp.close()

import threading
import logging

class DBPool():
    def __init__(self,modulename,poolsize,connectparams):
        self.conns = [DBConnection_(socket_.socketpair()) for x in xrange(poolsize)]
        self.threads = [threading.Thread(target=self.worker, args=(self.conns[x],)) for x in xrange(poolsize)]
        self.queue = queue.Queue(poolsize)
        for i in xrange(poolsize):
            self.threads[i].daemon = True
            self.threads[i].start()
            self.conns[i].connect(modulename,connectparams)
            self.queue.put(self.conns[i])

    def worker(self,conn):
        while True:
            conn.pipe[1].recv(1)
            try:
                function = conn.state.function
                args = conn.state.args
                conn.state.ret = function(*args)
                conn.state.status = 0
            except Exception as inst:
                conn.state.error = inst
                conn.state.status = -1
            finally:
                conn.pipe[1].send('\0')

    def get(self):
        return DBConnection(self,self.queue.get())

class DBConnection_():
    class State():
        pass

    def __init__(self,pipe):
        self.pipe = pipe
        self.state = self.State()

    def connect(self,modulename,connectparams):
        self.conn = self.apply(__import__(modulename).connect,connectparams)

    def __del__():
        self.conn.close()

    def apply(self,function,*args):
        logging.info(args)
        
        self.state.function = function
        self.state.args = args
        gevent.socket.wait_write(self.pipe[0].fileno())
        self.pipe[0].send('\0')
        gevent.socket.wait_read(self.pipe[0].fileno())
        self.pipe[0].recv(1)
        if self.state.status != 0:
            raise self.state.error
        return self.state.ret

class DBConnection():
    def __init__(self,pool,conn_):
        self.pool = pool
        self.conn_ = conn_

    def apply(self,function,*args):
        return self.conn_.apply(function,*args)

    def __del__(self):
        self.pool.queue.put(self.conn_)

    def cursor(self):
        return DBCursor(self,self.conn_.apply(self.conn_.conn.cursor))

class DBCursor():
    def __init__(self,conn,cursor):
        self.conn = conn
        self.cursor = cursor

    def __iter__(self,*args):
        return self.conn.apply(self.cursor.__iter__,*args)

    def execute(self,*args):
        return self.conn.apply(self.cursor.execute,*args)

    def executemany(self,*args):
        return self.conn.apply(self.cursor.executemany,*args)

    def next(self,*args):
        return self.conn.apply(self.cursor.next,*args)

    def fetchone(self,*args):
        return self.conn.apply(self.cursor.fetchone,*args)

    def fetchall(self,*args):
        return self.conn.apply(self.cursor.fetchall,*args)

    def fetchmany(self,*args):
        return self.conn.apply(self.cursor.fetchmany,*args)

    @property
    def description(self):
        return self.cursor.description

import unittest
import time

class TestDBPool(unittest.TestCase):
    def percentile(self,timings,percent):
        idx = int((len(timings)-1) * percent)
        return timings[idx]

    def test_benchmark(self):
        requests = 1000
        concurrency = 10 
        sql = 'SELECT 1'
        
        timings = []
        def timer(pool,sql):
            conn = pool.get()
            t0 = time.time()
            cursor = conn.cursor()
            cursor.execute(sql)
            timings.append(time.time()-t0)
        
        pool = DBPool('sqlite3',concurrency,':memory:')
        
        greenlets = []
        for i in xrange(requests):
            greenlets.append(gevent.spawn(timer,pool,sql))
        
        for g in greenlets:
            g.join()

        print '66%% %f' % self.percentile(timings,0.66)
        print '90%% %f' % self.percentile(timings,0.90)
        print '99%% %f' % self.percentile(timings,0.99)
        print '99.9%% %f' % self.percentile(timings,0.999)
        print '100%% %f' % self.percentile(timings,1.00)

if __name__ == '__main__':
    unittest.main()

