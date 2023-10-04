class MouEbuchyiClass(list):
    pass

a = MouEbuchyiClass()
a.append(2)
b = {}
print(type(a).mro())
print(type(b).mro())
