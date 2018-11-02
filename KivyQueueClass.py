from queue import Queue

class KivyQueue(Queue):
    '''
    A Multithread safe class that calls a callback whenever an item is added
    to the queue. Instead of having to poll or wait, you could wait to get
    notified of additions.

    >>> def callabck():
    ...     print('Added')
    >>> q = KivyQueue(notify_func=callabck)
    >>> q.put('test', 55)
    Added
    >>> q.get()
    ('test', 55)

    :param notify_func: The function to call when adding to the queue
    '''

    notify_func = None

    def __init__(self, notify_func, **kwargs):
        Queue.__init__(self, **kwargs)
        self.notify_func = notify_func

    def put(self, key, val):
        '''
        Adds a (key, value) tuple to the queue and calls the callback function.
        '''
        Queue.put(self, (key, val), False)
        self.notify_func()

    def get(self):
        '''
        Returns the next items in the queue, if non-empty, otherwise a
        :py:attr:`Queue.Empty` exception is raised.
        '''
        return Queue.get(self, False)
