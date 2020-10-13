import grab
import urllib.parse
import json
import time

from config import *

DEBUG = False

join = urllib.parse.urljoin

contest = '2020hw2'
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

results = {}

for problem_id, problem in enumerate(problems):
    print(f'[INFO] crawl problem {problem_id}')
    problem_stat = join(root, join(problem.text(), 'statistics'))

    page = 1
    while True:
        print(f'[INFO] start page {page}')
        g.go(join(problem_stat, f'?page={page}'))
        has_next_page = len(g.doc("//a[@class='nextprev'][@rel='next']"))

        ACs = g.doc("//a[@class='result-right']/@href")
        users = g.doc("//a[@class='result-right']/preceding::a[1]")

        for user, AC in zip(users, ACs):

            user = user.text()

            if not user in results:
                results[user] = {}
                
            if not problem_id + 1 in results[user]:
                solution = join(root, AC.text())
                g.go(solution)
                source = g.doc("//pre")[0].html()[14:-14]
                
                results[user][problem_id + 1] = source
                print(f'[INFO] add {user} {problem_id + 1}')
        
        print(f'[INFO] crawled page {page} with {len(ACs)} ACs')

        if DEBUG: break

        if not has_next_page:
            break
        else:    
            page += 1
    
    if DEBUG: break
    
# write md files

filename = contest + '.md'

with open(filename, 'w') as f:

    users = list(results.keys())
    users.sort()

    for user in users:
        f.write(f'### {user}\n')
        for problem_id in range(len(problems)):
            if problem_id + 1 in results[user]:
                source = results[user][problem_id + 1]
                f.write('```python\n')
                f.write(source + '\n')
                f.write('```\n')
            else:
                f.write(f'No submission for {problem_id+1}\n')




        
    




