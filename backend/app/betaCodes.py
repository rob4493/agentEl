"""Operator-only CLI. Never expose code administration as HTTP routes."""
import argparse
from datetime import datetime,timedelta,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
from .betaSecurity import readCodes


def updateCodes(filename,action,identity,days=14):
    path=Path(filename)
    path.parent.mkdir(parents=True,exist_ok=True)
    lock=path.with_name(path.name+'.lock')
    descriptor=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    # Serialize the complete read-modify-replace transaction; never let two
    # operator commands lose another reviewer's revocation or newly issued ID.
    try:return modifyCodes(filename,action,identity,days)
    finally:
        os.close(descriptor);lock.unlink()


def modifyCodes(filename,action,identity,days=14):
    if not re.fullmatch(r'[A-Za-z0-9_-]{3,48}',identity):raise ValueError('Use a unique 3–48 character code ID')
    path=Path(filename)
    data=readCodes(path) if path.exists() else {'version':1,'codes':[]}
    entry=next((entry for entry in data['codes'] if entry['codeId']==identity),None)
    plaintext=None
    if action=='create':
        if entry:raise ValueError('ID already exists; choose a new ID, including after revocation')
        if not 1<=days<=90:raise ValueError('Expiry must be 1–90 days')
        if len(data['codes'])>=128:raise ValueError('Code store full')
        plaintext=identity+'.'+secrets.token_urlsafe(32)
        data['codes'].append({'codeId':identity,'tokenHash':hashlib.sha256(plaintext.encode()).hexdigest(),
            'enabled':True,'expiresAt':(datetime.now(timezone.utc)+timedelta(days=days)).isoformat()})
    elif action=='revoke':
        if not entry:raise ValueError('Unknown ID')
        entry['enabled']=False
    else:raise ValueError('Unknown action')
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.tmp')
    # Restrictive Unix mode; Windows operators must also set directory ACLs.
    descriptor=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(descriptor,'w',encoding='utf-8') as handle:json.dump(data,handle,indent=2)
        os.replace(temporary,path)
    except BaseException:
        if temporary.exists():temporary.unlink()
        raise
    return plaintext


def main():
    parser=argparse.ArgumentParser(description='Create/revoke high-entropy private-beta codes; hashes stay in a private local file.')
    parser.add_argument('action',choices=['create','revoke'])
    parser.add_argument('--file',required=True)
    parser.add_argument('--id',required=True)
    parser.add_argument('--days',type=int,default=14)
    args=parser.parse_args()
    try:
        code=updateCodes(args.file,args.action,args.id,args.days)
    except (ValueError,OSError):parser.exit(1,'Code update failed; check private configuration and arguments. No credential was printed.\n')
    if code:print(code)  # Deliberate one-time operator output; never server logging.
    else:print('Access revoked for the selected ID. Existing admitted inference is not cancelled.')


if __name__=='__main__':main()
