#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A script that installs docker
import subprocess

import requests

url = 'https://get.docker.com'
response = requests.get(url)

response.raise_for_status()

subprocess.run(response.text, shell=True, check=True)
