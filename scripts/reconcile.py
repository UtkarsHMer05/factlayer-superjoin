from backend.factlayer import db
from backend.factlayer.alignment import reconcile

if __name__ == '__main__':
    db.init()
    for c in db.rows('SELECT id,name FROM collections'):
        print('Reconciling', c['name'], flush=True)
        reconcile(c['id'])
