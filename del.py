#!/usr/bin/env python3
"""del gmail messages
based on: https://developers.google.com/gmail/api/quickstart/python
"""
from __future__ import print_function
import os.path
import pathlib
import pickle
import time
import argparse
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# https://developers.google.com/gmail/api/auth/scopes
SCOPES = ['https://mail.google.com/']
# If modifying these scopes, delete the file token.pickle.

def get_service():
    '''get_service'''
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('gmail', 'v1', credentials=creds)
    return service

def main():
    """main
    """
    description = (
        "description: " +
        "delete gmail messages previously selected by sel.py"
    )
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        '--data',
        dest='data',
        default='data'
    )
    args = parser.parse_args()

    data = args.data
    data_path = pathlib.Path.cwd() / data
    if not data_path.exists():
        raise Exception("data_path'{}' already exists. Use --overwrite".format(data_path))
    if not data_path.is_dir():
        raise Exception("data_path'{}' is not dir".format(data_path))
    with open(data_path / 'index.pickle', 'rb') as pickle_file:
        index = pickle.load(pickle_file)
    do_del(index, data_path)

def do_del(index, data_path):
    '''del'''
    print(
        (
            "total: {}, query: '{}', include_spam_trash: {}" +
            ", data_path: {}, bunch_num: {} , bunch_size: {}"
        ).format(
            index.get('total'),
            index.get('query'),
            index.get('include_spam_trash'),
            data_path,
            index.get('bunch_num'),
            index.get('bunch_size')
        )
    )
    ret = get_bunches_to_process(index, data_path)
    bunch_i_list = ret.get("bunch_i_list")
    to_be_deleted = ret.get("to_be_deleted")
    erase_last_output = ''
    time_start = time.time()
    deleted = 0
    if bunch_i_list:
        service = get_service()
        for i in bunch_i_list:
            with open(data_path / '{}.pickle'.format(i), 'rb') as pickle_file:
                ids = pickle.load(pickle_file)
            time_start_request = time.time()
            service.users().messages().batchDelete(
                userId='me',
                body={"ids": ids}
            ).execute()
            deleted += len(ids)
            (data_path / '{}.deleted'.format(i)).touch()
            time_elapsed = time.time() - time_start
            time_estimated = time_elapsed * to_be_deleted / deleted
            print(
                "{}deleted: {}/{}, took: {}, elapsed: {}, estimated: {}".format(
                    erase_last_output,
                    deleted,
                    to_be_deleted,
                    round(time.time() - time_start_request, 1),
                    round(time_elapsed),
                    round(time_estimated)
                ),
                end="",
                flush=True
            )
            erase_last_output = '\033[2K\033[1G'
    time_elapsed = time.time() - time_start
    print(
        "{}deleted: {}/{}, elapsed: {}".format(
            erase_last_output,
            deleted,
            index.get("total"),
            round(time_elapsed)
        )
    )

def get_bunches_to_process(index, data_path):
    '''get_bunches_to_process'''
    bunch_i_list = []
    to_be_deleted = 0
    bunch_num = index.get('bunch_num')
    bunch_size = index.get('bunch_size')
    for i in range(bunch_num):
        pickle_exists = (data_path / '{}.pickle'.format(i)).exists()
        deleted_exists = (data_path / '{}.deleted'.format(i)).exists()
        if pickle_exists and not deleted_exists:
            bunch_i_list.append(i)
            if i < bunch_num - 1:
                to_be_deleted += bunch_size
            else:
                to_be_deleted += index.get('total') % bunch_size
    result = {"bunch_i_list": bunch_i_list, "to_be_deleted": to_be_deleted}
    return result

if __name__ == '__main__':
    main()
