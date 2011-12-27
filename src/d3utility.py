from multiprocessing import Manager

class largequeue(object):
    ''' An extended queue, used to bypass the size restrictions of a normal multiprocessing.Queue
    '''

    manager = Manager()
    lock = manager.Lock()
    queues = manager.list()
    maxqueuesize = 0
    
    def __init__(self, maxqueuesize = 400):
        self.maxqueuesize = maxqueuesize
        self.queues.append(self.manager.Queue())
        
    def put(self, obj):
        self.lock.acquire()
        if self.queues[-1].qsize() >= self.maxqueuesize:
            print 'New Queue'
            self.queues.append(self.manager.Queue())
            
        self.queues[-1].put(obj)
        
        self.lock.release()
        
    def get(self):
        self.lock.acquire()
        
        if self.queues[0].empty() and len(self.queues) > 1:
            self.queues = self.queues[1:]
            
        rval = self.queues[0].get()
        
        self.lock.release()
        
        return rval
    
    def qsize(self):
        self.lock.acquire()
        
        rval = 0
        
        for queue in self.queues:
            print queue.qsize()
            rval += queue.qsize()
        
        self.lock.release()
        
        return rval
    
    def empty(self):
        self.lock.acquire()
        rval = True
        
        for queue in self.queues:
            if not queue.empty():
                rval = False
                break
            
        self.lock.release()
        return rval
        