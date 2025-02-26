#!/bin/bash

if [ -z "$1" ]; then
  echo "Usage: $0 proj_name"
  exit 1
fi

mkdir "$1"
ln -s ../ut "$1/ut"

# Create an empty Jupyter Notebook with one empty code cell
cat <<EOT >> "$1/playground.ipynb"
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": []
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": ".conda",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "name": "python",
   "version": "3.12.8"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
EOT

echo "'$1' created."