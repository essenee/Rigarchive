"""Synthetic regressions: session tolerance must not permit application drift."""
import copy
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.core import signing
from django.contrib.sessions.backends.db import SessionStore
from django.test import SimpleTestCase

from .baseline_guard import digest, fingerprints, verify_tables


class SessionBaselineGuardTests(SimpleTestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.time = self.now - timedelta(minutes=5)
        self.history = {}
        for n in (1, 2):
            url = f'/synthetic/{n}/'
            self.history[url] = {'manufacturer_name':'Synthetic','model_name':'Synthetic','generation_name':str(n),
                'generation_number':n,'year_span':'2021–present','url':url}
        self.data = {'synthetic_auth':'unchanged','recently_viewed_generations':[dict(self.history['/synthetic/1/'],image_url=None)]}
        row = self.session_row(self.data)
        self.pk = digest(['SYNTHETIC_ONLY_SESSION_KEY'])
        self.raw = {
            'django_session': {'columns':['session_key','session_data','expire_date'],'pk_columns':['session_key'],
                'rows':{('SYNTHETIC_ONLY_SESSION_KEY',):row}},
            'reference_test': {'columns':['id','value'],'pk_columns':['id'],'rows':{(1,):(1,'original')}}}
        self.baseline = {'tables':{k:fingerprints(v) for k,v in self.raw.items()},
            'verified_session_fingerprints':[{'PK_fingerprint':self.pk,'decoded_key_names':sorted(self.data),
                'decoded_non_history_digest':digest({'synthetic_auth':'unchanged'})}]}

    def session_row(self, data, *, expiry_delta=0):
        value = SessionStore().encode(data)
        signed = signing.b62_decode(value.rsplit(':',2)[1])
        expiry = datetime.fromtimestamp(signed+settings.SESSION_COOKIE_AGE+expiry_delta,timezone.utc).replace(tzinfo=None).isoformat(sep=' ')
        return ('SYNTHETIC_ONLY_SESSION_KEY',value,expiry)

    def check(self, raw):
        actual={k:fingerprints(v) for k,v in raw.items()}
        sessions={digest(list(pk)):row for pk,row in raw['django_session']['rows'].items()}
        return verify_tables(self.baseline,actual,session_rows=sessions,known_history=self.history,
            baseline_time=self.time,now=datetime.now(timezone.utc))

    def changed_session(self, data=None, **kwargs):
        raw=copy.deepcopy(self.raw)
        if data is None:
            data=copy.deepcopy(self.data)
            data['recently_viewed_generations'].append(dict(self.history['/synthetic/2/'],image_url=None))
        raw['django_session']['rows'][('SYNTHETIC_ONLY_SESSION_KEY',)]=self.session_row(data,**kwargs)
        return raw

    def test_unchanged_tables_pass(self):
        self.assertEqual(self.check(self.raw),[])

    def test_verified_browsing_change_passes(self):
        changes=self.check(self.changed_session())
        self.assertEqual(len(changes),1)
        self.assertTrue(changes[0]['authentication_values_unchanged'])

    def test_non_session_change_rejected(self):
        raw=copy.deepcopy(self.raw);raw['reference_test']['rows'][(1,)]=(1,'changed')
        with self.assertRaisesRegex(AssertionError,'Non-session application data changed'):
            self.check(raw)

    def test_signed_authentication_change_rejected(self):
        data=copy.deepcopy(self.data);data['synthetic_auth']='changed'
        with self.assertRaisesRegex(AssertionError,'authentication/non-history'):
            self.check(self.changed_session(data))

    def test_invalid_signature_rejected_without_signature_in_error(self):
        raw=self.changed_session();row=list(raw['django_session']['rows'][('SYNTHETIC_ONLY_SESSION_KEY',)])
        row[1]='invalid-synthetic-signature';raw['django_session']['rows'][('SYNTHETIC_ONLY_SESSION_KEY',)]=tuple(row)
        with self.assertRaisesRegex(AssertionError,'^Changed session signature is invalid$'):
            self.check(raw)

    def test_abnormal_expiry_rejected(self):
        with self.assertRaisesRegex(AssertionError,'expiry differs'):
            self.check(self.changed_session(expiry_delta=3600))

    def test_new_or_deleted_session_rejected_for_review(self):
        raw=copy.deepcopy(self.raw);raw['django_session']['rows'].clear()
        with self.assertRaisesRegex(AssertionError,'New/deleted session'):
            self.check(raw)

    def test_unknown_history_reference_rejected(self):
        data=copy.deepcopy(self.data);data['recently_viewed_generations'][0]['url']='/unknown/'
        with self.assertRaisesRegex(AssertionError,'unknown generation'):
            self.check(self.changed_session(data))
