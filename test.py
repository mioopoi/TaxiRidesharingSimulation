from container import LinkedList


class Myclass:
    def __init__(self):
        self.a = 1
        self.b = 2
        self.c = 0

    def add(self):
        self.c = self.a + self.b

class B:
    def __init__(self):
        self.x = 0

    def do_sth(self, sth):
        """

        :param sth:
        :type sth: Myclass
        :return:
        """
        sth.add()

my_class = Myclass()
b = B()
b.do_sth(my_class)
print my_class.c

# your code goes here
x = set()
x.add(5)
x.add(6)
x.add(5)
x.add(2)
x.add(7)
x.add(1)
for i in x:
    print i
print (7 in x)
