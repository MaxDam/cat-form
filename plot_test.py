from cat.mad_hatter.decorators import hook, tool
import numpy as np 
import matplotlib.pyplot as plt
from datetime import datetime
from cat.utils import get_static_url, get_static_path
import os


@tool(return_direct=True)
def get_plot_intent2(input, cat):
    '''get plot'''
    values = np.random.randint(1, 10, 5)
    fig, ax = plt.subplots()
    indici = np.arange(len(values))
    ax.bar(indici, values, color='blue')
    ax.set_xlabel('Index')
    ax.set_ylabel('Value')
    ax.set_title('Random Graph')
    delete_previous_files_by_prefix("plot-")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"plot-{timestamp}.svg"
    fig.savefig(f'{get_static_path()}/{filename}')
    return f"<img style='width:400px' src='{get_static_url()}/{filename}'>"


@tool(return_direct=True)
def get_image(input, cat):
    '''get image'''
    return "<img style='width:400px' src='https://maxdam.github.io/cat-pizza-challenge/img/thumb.jpg'>"


# delete previous files
def delete_previous_files_by_prefix(prefix):
    folder = get_static_path()
    files = os.listdir(folder)
    for file in files:
        if file.startswith(prefix):
            file_path = os.path.join(folder, file)
            os.remove(file_path)
