#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys

if len(sys.argv) != 2:
    print('Usage: {} attribute'.format(sys.argv[0]))
    sys.exit(2)

with open('MANIFEST.json') as f:
    manifest = json.load(f)
    print(manifest[sys.argv[1]])
