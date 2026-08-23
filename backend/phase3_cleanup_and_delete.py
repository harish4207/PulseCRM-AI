from app.database.database import SessionLocal
from app.models.hcp import HCP
from app.models.interaction import Interaction
from app.models.user import User

# This script will: find HCPs created by tests (hospital='Test Hospital' and email like 'tempdoc%'), delete any interactions created by test users for those HCPs, then attempt to delete the HCP.

db = SessionLocal()
try:
    # find temporary HCPs
    hcps = db.query(HCP).filter(HCP.hospital == 'Test Hospital').all()
    print('found hcps:', [h.id for h in hcps])
    for h in hcps:
        # find interactions for this HCP created by test users
        interactions = db.query(Interaction).join(User, Interaction.user_id == User.id).filter(Interaction.hcp_id == h.id).filter(User.email.like('phase3_test_%') | User.email.like('integ_test_%')).all()
        print(f'hcp {h.id} interactions to delete:', [i.id for i in interactions])
        for i in interactions:
            db.delete(i)
        db.commit()
        # now attempt to delete hcp via service
        from app.services.hcp_service import HCPService
        res = HCPService.delete_hcp(db, h.id)
        print('delete result for hcp', h.id, res)
finally:
    db.close()
