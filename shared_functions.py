from time import time
from statistics import median

def round_down(value, decimal_point):
    multiplier = 10 ** decimal_point
    return int(value * multiplier) / multiplier

def get_time(start_time, precision):
    end_time = time()
    print("Time Taken: " + str(round(end_time - start_time, precision)))

def test_runtime(repeat_num, precision, target):
    time_list = []
    for index in range(repeat_num):
        start_time = time()
        print(f"Loop {index}")
        target()
        end_time = time()
        result = round(end_time - start_time, precision)
        time_list.append(result)
        print(f"Time taken: {result}")
    median_time = median(time_list)
    print(f"Median time: {median_time}")

def rgb2hex(r,g,b):
    return f"#{r:02x}{g:02x}{b:02x}"