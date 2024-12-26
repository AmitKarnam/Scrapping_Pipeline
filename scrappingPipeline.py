from typing import Callable, List


# Higeher order function that takes a scrapping fuction as input and returns the same output as the parameter function
def Scrap(url: str, func: Callable[[str], List]) -> List:
    documentation = func(url)
    return documentation
