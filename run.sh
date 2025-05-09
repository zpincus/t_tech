#!/bin/bash

if ! python -c "import natsort; import pandas; import seaborn; import scipy" &> /dev/null; then
    echo "Installing required packages..."
    pip install natsort pandas seaborn scipy
fi

# use script_dir in case someone runs this script from a different directory;
# use double quotes to allow for spaces in the path
script_dir=$(dirname "$0")
python "${script_dir}/cell_count.py" < "${script_dir}/cell-count.csv"