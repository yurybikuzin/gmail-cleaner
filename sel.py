#!/usr/bin/env python3
"""sel gmail messages
based on: https://developers.google.com/gmail/api/quickstart/python
"""
from __future__ import print_function
import os.path
import pathlib
import shutil
import pickle
import time
# import sys
import argparse
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# https://developers.google.com/gmail/api/auth/scopes
SCOPES = ['https://mail.google.com/']
# If modifying these scopes, delete the file token.pickle.

def messages_list(service, **opts):
    '''helper function'''
    results = service.users().messages().list(
        userId='me',
        maxResults=opts.get('bunch_size'),
        pageToken=opts.get('page_token'),
        includeSpamTrash=opts.get('include_spam_trash'),
        q=opts.get('query')
    ).execute()
    return results

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
        "select gmail messages by query" +
        ", optionally including spam/trash"
    )
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        'query',
        help='see https://support.google.com/mail/answer/7190?hl=en'
    )
    # https://stackoverflow.com/questions/15008758/parsing-boolean-values-with-argparse/15008806#15008806
    parser.add_argument(
        '--include-spam-trash',
        dest='include_spam_trash',
        action='store_true'
    )
    parser.add_argument(
        '--bunch-size',
        dest='bunch_size',
        type=int,
        default=500
    )
    parser.add_argument(
        '--data',
        dest='data',
        default='data'
    )
    parser.add_argument(
        '--overwrite',
        dest='overwrite',
        action='store_true'
    )
    parser.set_defaults(include_spam_trash=False, overwrite=False)
    args = parser.parse_args()

    data = args.data
    data_path = pathlib.Path.cwd() / data
    if data_path.exists():
        if not args.overwrite:
            raise Exception("data_path'{}' already exists. Use --overwrite".format(data_path))
        if not data_path.is_dir():
            raise Exception("data_path'{}' is not dir".format(data_path))
        shutil.rmtree(data_path)
    data_path.mkdir()
    sel(args, data_path)

def sel(args, data_path):
    '''sel'''
    print(
        "data_path: {}, query: '{}', bunch_size: {}, include_spam_trash: {}".format(
            data_path,
            args.query,
            args.bunch_size,
            args.include_spam_trash
        )
    )
    service = get_service()
    time_start = time.time()
    opts = {
        "query": args.query,
        "bunch_size": args.bunch_size,
        "include_spam_trash": args.include_spam_trash,
        "page_token": None,
        "total": 0,
        "bunch_num": 0
    }
    results = messages_list(
        service,
        **opts
    )
    messages = results.get('messages')
    if messages:
        opts["total"] += len(messages)
    opts["bunch_num"] = message_ids_to_pickle(messages, data_path, 0)
    opts["page_token"] = results.get('nextPageToken')

    ret = process_pages(service, data_path, time_start, opts)
    erase_last_output = ret.get("erase_last_output")
    opts["bunch_num"] = ret.get("bunch_num")
    opts["total"] = ret.get("total")

    with open(data_path / 'index.pickle', 'wb') as pickle_file:
        pickle.dump(opts, pickle_file)
    print(
        "{}bunches: {}, total: {}, elapsed: {}".format(
            erase_last_output,
            opts.get("bunch_num"),
            opts.get("total"),
            round(time.time() - time_start)
        )
    )

def process_pages(service, data_path, time_start, opts):
    '''process_pages'''
    erase_last_output = ''
    while opts.get("page_token") is not None:
        time_start_bunch = time.time()
        results = messages_list(
            service,
            **opts
        )
        messages = results.get('messages')
        opts["bunch_num"] = message_ids_to_pickle(
            messages,
            data_path,
            opts.get("bunch_num")
        )
        opts["total"] += len(messages)
        print(
            "{}bunch_num: {}, count: {}, took: {}, total: {}, elapsed: {}".format(
                erase_last_output,
                opts.get("bunch_num"),
                len(messages),
                round(time.time() - time_start_bunch, 1),
                opts.get("total"),
                round(time.time() - time_start)
            ),
            end="",
            flush=True
        )
        # https://stackoverflow.com/questions/5290994/remove-and-replace-printed-items/5291396#5291396
        erase_last_output = '\033[2K\033[1G'
        opts["page_token"] = results.get('nextPageToken')
    result = {
        "erase_last_output": erase_last_output,
        "bunch_num": opts.get("bunch_num"),
        "total": opts.get("total")
    }
    return result

def message_ids_to_pickle(messages, data_path, bunch_num):
    '''message_ids_to_pickle'''
    if not messages:
        return bunch_num
    ids = []
    for message in messages:
        ids.append(message['id'])
    with open(data_path / '{}.pickle'.format(bunch_num), 'wb') as pickle_file:
        pickle.dump(ids, pickle_file)
    return bunch_num + 1


if __name__ == '__main__':
    main()
