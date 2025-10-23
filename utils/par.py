# Distinguish b/t return and yeild

# return are used in regular function and yeild are used in function generator

# 1. return
# def add(a,b):
#     return a+b

# print(add(10,20))



# 2. yield
def count_to_up(n):
    i = 0
    while i < n:
        yield i 
        i = i+1


for num in count_to_up(5):
    print(num)
