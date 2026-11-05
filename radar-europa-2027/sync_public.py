"""Export an allowlisted production snapshot to a dedicated public checkout."""
import argparse
import subprocess
from pathlib import Path
from radar import ROOT, public_snapshot, read_json, write_json

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkout', required=True)
    args = parser.parse_args()
    checkout = Path(args.checkout).resolve()
    def git(*args):
        return subprocess.check_output(['git','-C',str(checkout),*args],text=True).strip()
    remote = git('remote','get-url','origin')
    if remote not in ('git@github.com:foxnove/youtube.git','https://github.com/foxnove/youtube.git'):
        raise ValueError('Unexpected public repository')
    if git('branch','--show-current') != 'radar-europa-2027':
        raise ValueError('Unexpected public branch')
    data = read_json(ROOT/'docs/data.json',{})
    if data.get('environment') != 'production':
        raise ValueError('Only production status can be published')
    write_json(checkout/'radar-europa-2027/data.json', public_snapshot(data,data.get('history',[])))
    git('config','user.name','github-actions[bot]')
    git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    git('add','--','radar-europa-2027/data.json')
    if subprocess.run(['git','-C',str(checkout),'diff','--cached','--quiet']).returncode:
        git('commit','-m','radar: atualizar estado e tarifas verificadas')
        git('push','origin','HEAD:radar-europa-2027')
    print('Allowlisted public data synchronized.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
