#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import requests

import numpy as np

import sqlite3


class DataBase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.database = None
        self.cursor = None

    def initialize(self, create: bool = False):
        self.database = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.database.cursor()

        if create:
            _cmd = f"CREATE TABLE submissions " \
                   f"(url text PRIMARY KEY, title text, keywords text, " \
                   f"rating_0_cnt int, rating_0_avg float, rating_0_std float, ratings_0 text," \
                   f"decision text, withdraw int )"
            self.cursor.execute(_cmd)

    def write_item_rating(
            self,
            suf: int,
            item_id: str,
            ratings: list,
            withdraw: int,
            decision: str,
            title: str,
            authors: list,
            keywords: list,
    ):
        if suf == 0:
            title = title.replace('\\', '').replace("\"", "'")
            authors = [a.replace('\\', '').replace("\"", "'") for a in authors]
            authors = ", ".join(authors)
            keywords = [k.replace('\\', '').replace("\"", "'") for k in keywords]
            keywords = ", ".join(keywords)

            num_rating = len(ratings)
            rating_avg = np.mean(ratings).item()
            rating_std = np.std(ratings).item()
            ratings = ', '.join(map(str, ratings))
            _cmd = f"INSERT INTO submissions " \
                   f"(url_id, s_{suf}_cnt, s_{suf}_avg, s_{suf}_std, s_{suf}_list, " \
                   f"withdraw, decision, title, authors, keywords) " \
                   f"VALUES (\"{item_id}\", {num_rating}, {rating_avg}, " \
                   f"{rating_std}, " \
                   f"\"{ratings}\", {withdraw}, \"{decision}\", " \
                   f"\"{title}\", \"{authors}\", \"{keywords}\" " \
                   f") "
        else:
            num_rating = len(ratings)
            rating_avg = np.mean(ratings).item()
            rating_std = np.std(ratings).item()
            ratings = ', '.join(map(str, ratings))
            _cmd = f"UPDATE submissions " \
                   f"SET " \
                   f"s_{suf}_cnt = {num_rating}, s_{suf}_avg = {rating_avg}, " \
                   f"s_{suf}_std = {rating_std}, " \
                   f"s_{suf}_list = \"{ratings}\", withdraw = {withdraw}, decision = \"{decision}\" " \
                   f"WHERE url_id = \"{item_id}\""
        print(_cmd)
        self.cursor.execute(_cmd)
        self.database.commit()

    def close(self):
        self.cursor.close()
        self.database.close()


def parse_item(i, suf, url, db_path):
    print(f"on {url} ...")
    item_id = url.split('id=')[-1]
    rqst_url = f"https://api.openreview.net/notes?forum={item_id}"
    rqst_data = requests.get(rqst_url)
    rqst_data = json.loads(rqst_data.text)

    # parse each note
    withdraw = 0
    # filter meta note
    meta_note = [d for d in rqst_data['notes'] if 'Paper' not in d['invitation']]
    # check withdrawn
    withdraw = 1 if 'Withdrawn_Submission' in meta_note[0]['invitation'] else 0

    # === decision ===
    decision = ''
    # only after final decision
    # if withdraw == 0:
    #     decision_note = [d for d in rqst_data['notes'] if 'Decision' in d['invitation']]
    #     decision = decision_note[0]['content']['decision']
    # else:
    #     decision = ''

    # meta data
    title = meta_note[0]['content']['title']
    authors = meta_note[0]['content']['authors']
    keywords = meta_note[0]['content']['keywords']

    # filter reviewer comments
    comment_notes = [d for d in rqst_data['notes'] \
                     if 'Official_Review' in d['invitation'] and 'recommendation' in d['content'].keys()]
    comment_notes = sorted(comment_notes, key=lambda d: d['number'])[::-1]
    ratings = [int(note['content']['recommendation'].split(':')[0]) for note in comment_notes]

    db = DataBase(db_path)
    db.initialize(create=False)
    db.write_item_rating(suf, item_id, ratings, withdraw, decision, title, authors, keywords)
    print(f"done: {i}")
    db.close()
