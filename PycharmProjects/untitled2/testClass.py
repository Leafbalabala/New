class New:
    count = 0

    def __init__(self, name):
        self.name = name
        New.count+=1


for i in range(1, 5):
    locals()['new' + str(i)] = New(i)

print(new4.name)
print(New.count)
