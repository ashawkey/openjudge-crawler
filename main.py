import grab
import urllib.parse
import json
import time
import os

import gensim
from nltk.tokenize import word_tokenize

from config import *

DEBUG = False
VERBOSE = True
DUPTHRESH = 0.5

join = urllib.parse.urljoin

contest = '2020hw7'
workspace = 'output'
tempdir = 'tmp'

sleep_time = 0
root = 'http://mathicpython.openjudge.cn/'

g = grab.Grab()

# auth

g.go('http://openjudge.cn/api/auth/login/', post={'email': email, 'password': password})

resp = json.loads(g.doc.body)
if resp['result'] != 'SUCCESS':
    print(f'[ERROR] login: {resp}')

# crawl

g.go(join(root, contest))

problems = g.doc("//td[@class='problem-id']/a/@href")

# {'user': [p1, p2, ...], ...}, p = [type, source]
results = {}

for problem_id, problem in enumerate(problems):
    print(f'[INFO] crawl problem {problem_id}')
    url_stat = join(root, join(problem.text(), 'statistics'))

    page = 1
    while True:
        print(f'[INFO] start page {page}')
        g.go(join(url_stat, f'?page={page}'))
        has_next_page = len(g.doc("//a[@class='nextprev'][@rel='next']"))

        users = g.doc("//tr/td[@class='submit-user']/a")
        entries = g.doc("//tr/td[@class='result']/a")

        for user, entry in zip(users, entries):

            user = user.text()

            if not user in results:
                results[user] = {}
            
            # if accepted, record the first accepted answer
            # else, record the last answer
            if not problem_id in results[user] or results[user][problem_id][0] != 'Accepted':
                url_solution = join(root, entry.attr('href'))
                result_type = entry.text()

                time.sleep(sleep_time)
                g.go(url_solution)
                source = g.doc("//pre")[0].html()[14:-14]
                
                results[user][problem_id] = [result_type, source]

                if VERBOSE: 
                    print(f'[INFO] add user: {user} type: {result_type} problem: {problem_id}')
        
        print(f'[INFO] crawled page {page} with {len(entries)} entries')

        if DEBUG: break

        if not has_next_page:
            break
        else:    
            page += 1
    
    if DEBUG: break

# check for duplicates
users = list(results.keys())
users.sort()

for problem_id in range(len(problems)):
    # build dictionary
    docs = []
    for user in users:
        if problem_id in results[user]:
            docs.append([word.lower() for word in word_tokenize(results[user][problem_id][1])])
    dictionary = gensim.corpora.Dictionary(docs)
    bows = [dictionary.doc2bow(doc) for doc in docs]
    tfidf = gensim.models.TfidfModel(bows)
    sims = gensim.similarities.Similarity(tempdir + os.sep, tfidf[bows], num_features=len(dictionary))
    # check duplicates
    for user in users:
        if problem_id in results[user]:
            result_type, source = results[user][problem_id]
            query_doc = [word.lower() for word in word_tokenize(source)]
            query_bow = dictionary.doc2bow(query_doc)
            query_tfidf = tfidf[query_bow]

            for similarity, user2 in zip(sims[query_tfidf], users):
                if user2 == user: continue
                if similarity > DUPTHRESH:
                    if VERBOSE:
                        print(f'[INFO] problem {problem_id}: {user} <-- {similarity:.3f} --> {user2}')
                    result_type += f'\n### [DUP] {user2}: similarity = {similarity:.3f}'
                    results[user][problem_id][0] = result_type

    
# write md files

os.makedirs(workspace, exist_ok=True)

filename = os.path.join(workspace, contest + '.md')

with open(filename, 'w') as f:
    for user in users:
        f.write(f'### {user}\n')
        for problem_id in range(len(problems)):
            if problem_id in results[user]:
                result_type, source = results[user][problem_id]
                f.write('```python\n')
                f.write('### ' + result_type + '\n')
                f.write(source + '\n')
                f.write('```\n')
            else:
                f.write(f'No submission for {problem_id}\n')

