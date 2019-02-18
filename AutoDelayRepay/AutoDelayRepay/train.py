
# TODO implement a train oject. It should now when it was due in an how delayed it was.
# maybe just store data. How do you make it store more than one day of data?
class Train(object):
    """
    A train data structure that stores relevent information about a train journey.

    """

    def __init__(self, dept_time, arrival_time, dept_station, arrival_station):
        self.dept_time = dept_time
        self.arrival_time = arrival_time
        self.dept_station = dept_station
        self.arrival_station = arrival_station

    def departure_time(self):
        return self.dept_time

    def arrival_time(self):
        pass

        




class TrainList(object):
    """
    A linked list type data structures that links me to the next train after this one.

    Train 1:    Dept - Arr
        Train 2:    Dept - CNCL
            Train 3:    Dept - Arr

    This will help solve the problem of when a train is canceled and I need to find the next one.
    """
    def __init__(self, head=None):
        self.head = head or Train()

    def add(self):
        '''
        Add a train to the list.

        :return:
        '''

    def next(self):
        '''
        The next train in the list

        :return:
        '''
        pass

    def current(self):
        '''
        The current train in the list. Basically pop()

        :return:
        '''