#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# A script that updates oioioi from a Github release
import sys
import os
import requests
import json
import tarfile
import shutil
from packaging import version

API_REPOS = 'https://api.github.com/repos/'
REPO = 'sio2project/oioioi'
ASSET_PREFIX = 'oioioi_easy_installer'
ASSET_EXT = 'tar.gz'
HEADERS = {'Accept': 'application/vnd.github.v3+json'}


def get_target_version():
    url = API_REPOS + REPO + '/releases/latest'
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()['tag_name']


def download_tgz(tag_name, asset_name, output_name):
    def get_asset_download_url():
        url = API_REPOS + REPO + '/releases/tags/' + tag_name
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()

        assets = response.json()['assets']
        for asset in assets:
            if asset['label'] == asset_name:
                return asset['browser_download_url']

    download_url = get_asset_download_url()
    if download_url is None:
        raise RuntimeError("selected version doesn't contain the easy-installer")

    response = requests.get(download_url, headers=HEADERS)
    response.raise_for_status()
    with open(output_name, 'wb') as f:
        f.write(response.content)


def main():
    if len(sys.argv) != 4:
        print('Usage: {} deployment_directory current_version target_version'.format(sys.argv[0]))
        sys.exit(2)

    deployment_directory = sys.argv[1]
    current_version = sys.argv[2]
    target_version = sys.argv[3]
    if not target_version:
        target_version = get_target_version()

    if version.parse(current_version) >= version.parse(target_version):
        sys.exit(3)

    asset_name = ASSET_PREFIX + '_' + target_version + '.' + ASSET_EXT
    # asset_path = os.path.join(os.getcwd(), asset_name)
    download_tgz(target_version, asset_name, asset_name)
    with tarfile.open(asset_name, 'r') as t:
        asset_folder = t.getnames()[0]
        t.extractall()

    shutil.copytree(asset_folder, '.', dirs_exist_ok=True)
    os.remove(asset_name)
    shutil.rmtree(asset_folder)


if __name__ == "__main__":
    main()
