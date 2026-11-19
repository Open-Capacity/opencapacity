"""Examples and exchanges for opencapacity-1.0.yaml.

Run: python3 tools/examples.py
Rewrites the part of the YAML after the marker line with the examples and exchanges
defined here. All values are fictional.
"""
import copy, hashlib, hmac, json, pathlib, re

BASE = 'https://provider.example/capacity/v1'
FR = {'level': 'METRO', 'code': 'FR'}
AM = {'level': 'METRO', 'code': 'AM'}
LD = {'level': 'METRO', 'code': 'LD'}
CLOUD = {'name': 'Example Cloud', 'asn': 64500, 'type': 'CLOUD'}
NET = {'name': 'Example Network', 'asn': 64501, 'type': 'NETWORK'}
LIQ = {'feature': 'LIQUID_COOLING', 'required': True}
CAGE = {'feature': 'PRIVATE_CAGE', 'required': False}


def feat(name, support, required):
    return {'feature': name, 'support': support, 'required': required}


def answer(aid, at, results, reference=None):
    order = ['AVAILABLE', 'POSSIBLE', 'UNAVAILABLE', 'NOT_DISCLOSED']
    a = {'answerId': aid}
    if reference:
        a['reference'] = reference
    a.update({'generatedAt': at, 'validUntil': at.replace('T', 'T')[:8] + '%02d' % (int(at[8:10]) + 1) + at[10:],
              'grade': min((r['grade'] for r in results), key=order.index), 'results': results})
    return a


def problem(slug, title, status, code, detail, errors=None):
    p = {'type': 'https://opencapacity.example/problems/' + slug, 'title': title, 'status': status, 'code': code, 'detail': detail}
    if errors:
        p['errors'] = errors
    return p


EX = {}


def ex(name, summary, value):
    assert name not in EX, name
    EX[name] = {'summary': summary, 'value': value}
    return value


# ---------------------------------------------------------------- discovery
ex('CapabilitiesCoreOnly', 'A provider that implements queries only, answers at facility level, and returns bands', {
    'specVersion': '1.0.0',
    'provider': {'name': 'Example Colocation', 'url': 'https://provider.example'},
    'conformance': ['CORE'],
    'authentication': {'tokenUrl': 'https://provider.example/oauth2/token'},
    'locationLevels': ['COUNTRY', 'METRO', 'CAMPUS', 'FACILITY'],
    'areaLocations': False,
    'finestAnswerLevel': 'FACILITY',
    'features': ['LIQUID_COOLING', 'DIRECT_TO_CHIP_COOLING', 'IMMERSION_COOLING', 'PRIVATE_CAGE', 'PRIVATE_SUITE'],
    'defaultPowerFactor': 0.9,
    'disclosure': {'timing': 'ALWAYS', 'density': 'ALWAYS', 'cabinets': 'ALWAYS', 'power': 'CASE_BY_CASE',
                   'interconnection': 'CASE_BY_CASE', 'reasons': 'ALWAYS'},
    'limits': {'maxLocationsPerRequirement': 5, 'answerValiditySeconds': 3600},
})
ex('LocationsPage', 'One page of locations with a cursor for the next page', {
    'data': [
        {'level': 'METRO', 'code': 'FR', 'name': 'Frankfurt', 'standardCode': 'DEFRA', 'parent': {'level': 'COUNTRY', 'code': 'DE'}},
        {'level': 'CAMPUS', 'code': 'FR-CAMPUS-1', 'name': 'Frankfurt East Campus', 'parent': FR},
        {'level': 'FACILITY', 'code': 'FR-A', 'name': 'Frankfurt A', 'parent': {'level': 'CAMPUS', 'code': 'FR-CAMPUS-1'}},
        {'level': 'FACILITY', 'code': 'FR-B', 'name': 'Frankfurt B', 'parent': {'level': 'CAMPUS', 'code': 'FR-CAMPUS-1'}},
        {'level': 'METRO', 'code': 'AM', 'name': 'Amsterdam', 'standardCode': 'NLAMS', 'parent': {'level': 'COUNTRY', 'code': 'NL'}},
    ],
    'pagination': {'limit': 5, 'next': 'bG9jLTAwMDY'},
})

# ---------------------------------------------------------------- queries
ex('QueryPowerCabinetsDensity', 'Total power with a cabinet count and a density range, as circuit capacity in kVA', {
    'reference': 'example-query-2',
    'requirement': {
        'locations': [FR],
        'demand': {'power': {'value': 600, 'unit': 'KVA'}, 'powerBasis': 'CIRCUIT_CAPACITY', 'powerFactor': 0.95,
                   'cabinets': {'count': 30}, 'density': {'min': 10, 'target': 20, 'max': 40, 'unit': 'KVA'}},
        'timeframe': {'neededForService': '2027-Q1', 'termMonths': 36},
    }})
ex('AnswerPowerCabinetsDensity', 'An answer with a power band and a cabinet band', answer('ans-0101', '2026-11-18T10:05:00Z', [{
    'location': FR, 'grade': 'AVAILABLE',
    'timing': {'status': 'IN_SERVICE', 'availableForSale': 'NOW', 'availableForService': '2027-01'},
    'density': {'min': 5, 'max': 40, 'unit': 'KVA'}, 'cabinets': {'min': 30}, 'power': {'min': 600, 'unit': 'KVA'},
    'supportedFeatures': []}], 'example-query-2'))

ex('QueryFacility', 'A question about one facility', {
    'requirement': {'locations': [{'level': 'FACILITY', 'code': 'FR-A'}],
                    'demand': {'cabinets': {'count': 12}, 'density': {'target': 15, 'unit': 'KW'}},
                    'timeframe': {'neededForService': '2027-03'},
                    'desiredFeatures': [LIQ]}})
ex('AnswerCoarserThanRequested', 'The provider answers for the metro and says which location was requested', answer('ans-0102', '2026-11-18T10:06:00Z', [{
    'location': FR, 'requested': {'level': 'FACILITY', 'code': 'FR-A'}, 'grade': 'AVAILABLE',
    'supportedFeatures': [feat('LIQUID_COOLING', 'AVAILABLE', True)]}]))

ex('QueryArea', 'Everything within 400 km of a point', {
    'requirement': {'locations': [{'level': 'AREA', 'center': {'latitude': 50.11, 'longitude': 8.68}, 'radiusKm': 400}],
                    'demand': {'power': {'value': 2, 'unit': 'MW'}},
                    'timeframe': {'neededForService': '2027'}}})
AREA = {'level': 'AREA', 'center': {'latitude': 50.11, 'longitude': 8.68}, 'radiusKm': 400}
ex('AnswerArea', 'One result for each named location the provider reports inside the area', answer('ans-0103', '2026-11-18T10:07:00Z', [
    {'location': FR, 'requested': AREA, 'grade': 'POSSIBLE', 'timing': {'status': 'PLANNED', 'availableForService': '2027-Q4'},
     'supportedFeatures': [], 'reasons': ['TIMING']},
    {'location': AM, 'requested': AREA, 'grade': 'AVAILABLE', 'timing': {'status': 'PLANNED', 'availableForService': '2027-Q2'},
     'supportedFeatures': []}]))

ex('QueryNotServed', 'Two metros, one of which the provider does not serve', {
    'requirement': {'locations': [FR, {'level': 'METRO', 'code': 'USNYC', 'scheme': 'STANDARD'}],
                    'demand': {'cabinets': {'count': 4}, 'density': {'max': 8, 'unit': 'KVA'}}}})
ex('AnswerNotServed', 'UNAVAILABLE with reason LOCATION_NOT_SERVED for the metro the provider does not serve', answer('ans-0104', '2026-11-18T10:08:00Z', [
    {'location': FR, 'grade': 'AVAILABLE', 'timing': {'status': 'IN_SERVICE', 'availableForSale': 'NOW', 'availableForService': 'NOW'},
     'supportedFeatures': []},
    {'location': {'level': 'METRO', 'code': 'USNYC', 'scheme': 'STANDARD'}, 'grade': 'UNAVAILABLE',
     'supportedFeatures': [], 'reasons': ['LOCATION_NOT_SERVED']}]))

ex('QueryPartialFit', '60 adjacent cabinets, of which at least 40 are worth an answer', {
    'requirement': {'locations': [LD],
                    'demand': {'cabinets': {'count': 60, 'minimum': 40}, 'density': {'target': 12, 'max': 20, 'unit': 'KW'},
                               'spaceType': 'CAGE', 'contiguous': True},
                    'timeframe': {'neededForService': '2027-Q2'},
                    'desiredFeatures': [CAGE]}})
ex('AnswerPartialFit', 'POSSIBLE with a cabinet band below the requested count and the reason', answer('ans-0105', '2026-11-18T10:09:00Z', [{
    'location': LD, 'grade': 'POSSIBLE', 'timing': {'status': 'IN_SERVICE', 'availableForService': '2027-Q2'},
    'density': {'max': 20, 'unit': 'KW'}, 'cabinets': {'min': 40, 'max': 50},
    'supportedFeatures': [feat('PRIVATE_CAGE', 'AVAILABLE', False)], 'reasons': ['SPACE']}]))

ex('QueryInterconnectionLatency', 'Two parties in the metro, one with a latency limit', {
    'requirement': {'locations': [FR],
                    'demand': {'cabinets': {'count': 8}, 'density': {'target': 10, 'unit': 'KW'}},
                    'timeframe': {'neededForService': '2027-06'},
                    'interconnection': [
                        {'party': CLOUD, 'within': 'METRO', 'maxRoundTripMs': 2, 'required': True},
                        {'party': NET, 'within': 'FACILITY', 'required': False}]}})
ex('AnswerInterconnectionLatency', 'A latency band for one party and NOT_DISCLOSED for the other', answer('ans-0106', '2026-11-18T10:10:00Z', [{
    'location': FR, 'grade': 'AVAILABLE', 'supportedFeatures': [],
    'interconnection': [
        {'party': CLOUD, 'within': 'METRO', 'presence': 'AVAILABLE', 'required': True, 'roundTripMs': {'min': 0.4, 'max': 1.2}},
        {'party': NET, 'within': 'FACILITY', 'presence': 'NOT_DISCLOSED', 'required': False}]}]))

ex('QueryRamp', '20 MW that ramps over 18 months, with a sale date and a service date', {
    'requirement': {'locations': [{'level': 'COUNTRY', 'code': 'DE'}],
                    'demand': {'power': {'value': 20, 'unit': 'MW'}, 'spaceType': 'HALL'},
                    'timeframe': {'neededForSale': '2027-Q1', 'neededForService': '2028-Q1', 'latestAcceptable': '2028-06', 'termMonths': 120,
                                  'ramp': [{'by': '2028-Q1', 'percent': 25}, {'by': '2028-Q4', 'percent': 60}, {'by': '2029-06', 'percent': 100}]},
                    'desiredFeatures': [{'feature': 'DIRECT_TO_CHIP_COOLING', 'required': True}],
                    'offering': 'WHOLESALE'}})
ex('AnswerRampPlanned', 'Planned capacity with a sale date to the month and a service date to the year', answer('ans-0107', '2026-11-18T10:11:00Z', [{
    'location': FR, 'requested': {'level': 'COUNTRY', 'code': 'DE'}, 'grade': 'POSSIBLE',
    'timing': {'status': 'PLANNED', 'availableForSale': '2027-03', 'availableForService': '2028'},
    'supportedFeatures': [{'feature': 'DIRECT_TO_CHIP_COOLING', 'support': 'AVAILABLE', 'required': True, 'availableForService': '2028'}],
    'reasons': ['TIMING', 'REVIEW_REQUIRED'], 'nextStepUrl': 'https://provider.example/contact'}]))

ex('QueryImmediate', 'No timeframe, which states an immediate need', {
    'requirement': {'locations': [AM], 'demand': {'cabinets': {'count': 2}, 'density': {'max': 6, 'unit': 'KVA'}}}})
ex('AnswerAvailableNow', 'In service, for sale now and usable now', answer('ans-0108', '2026-11-18T10:12:00Z', [{
    'location': AM, 'grade': 'AVAILABLE', 'timing': {'status': 'IN_SERVICE', 'availableForSale': 'NOW', 'availableForService': 'NOW'},
    'density': {'max': 10, 'unit': 'KVA'}, 'cabinets': {'min': 2}, 'supportedFeatures': []}]))

ex('QueryRedundancyPowerFeed', 'Redundancy, a DC power feed, and a commercial offering as hard constraints', {
    'requirement': {'locations': [FR, AM],
                    'demand': {'cabinets': {'count': 16}, 'density': {'target': 30, 'unit': 'KW'}},
                    'timeframe': {'neededForService': '2027-09'},
                    'redundancy': {'power': 'TWO_N', 'cooling': 'N_PLUS_1'},
                    'powerFeed': {'current': 'DC', 'voltage': 400},
                    'offering': 'RETAIL_COLOCATION'}})
ex('AnswerRedundancyUnavailable', 'UNAVAILABLE in one metro with the reasons, and POSSIBLE in the other', answer('ans-0109', '2026-11-18T10:13:00Z', [
    {'location': FR, 'grade': 'UNAVAILABLE', 'supportedFeatures': [], 'reasons': ['REDUNDANCY', 'POWER_FEED']},
    {'location': AM, 'grade': 'POSSIBLE', 'timing': {'status': 'PLANNED', 'availableForService': 'NOT_DISCLOSED'},
     'supportedFeatures': [], 'reasons': ['POWER_FEED', 'REVIEW_REQUIRED']}]))

ex('AnswerPowerOnly', 'A region answered as a whole and an area answered with one named location', answer('ans-0110', '2026-11-18T10:14:00Z', [
    {'location': {'level': 'REGION', 'code': 'EMEA'}, 'grade': 'POSSIBLE',
     'supportedFeatures': [feat('DIRECT_TO_CHIP_COOLING', 'POSSIBLE', True)], 'reasons': ['REVIEW_REQUIRED']},
    {'location': FR, 'requested': {'level': 'AREA', 'center': {'latitude': 50.11, 'longitude': 8.68}, 'radiusKm': 50}, 'grade': 'POSSIBLE',
     'timing': {'status': 'PLANNED', 'availableForService': '2028'},
     'supportedFeatures': [feat('DIRECT_TO_CHIP_COOLING', 'AVAILABLE', True)], 'reasons': ['TIMING']}]))

ex('QueryInconsistentDemand', 'Total power that 40 cabinets cannot hold at the density max', {
    'requirement': {'locations': [FR],
                    'demand': {'power': {'value': 5, 'unit': 'MW'}, 'cabinets': {'count': 40},
                               'density': {'max': 100, 'unit': 'KVA'}}}})
ex('QueryTooManyLocations', '14 countries sent to a provider that accepts 10 locations', {
    'requirement': {'locations': [{'level': 'COUNTRY', 'code': c} for c in
                                  'DE NL GB FR IE ES IT SE CH AT BE DK PL PT'.split()],
                    'demand': {'power': {'value': 1, 'unit': 'MW'}}}})

ex('ProblemUnsupportedLocationLevel', 'An area sent to a provider that does not accept areas',
   problem('unsupported-location-level', 'Location level is not supported', 422, 'UNSUPPORTED_LOCATION_LEVEL',
           'This provider does not accept a point and a radius as a location.',
           [{'pointer': '/requirement/locations/0', 'detail': 'Use a REGION, COUNTRY, METRO, CAMPUS, or FACILITY location.'}]))
ex('ProblemTooManyLocations', 'More locations than the provider accepts in one requirement',
   problem('too-many-locations', 'Too many locations', 422, 'TOO_MANY_LOCATIONS',
           'A requirement can name at most 10 locations. This one names 14.',
           [{'pointer': '/requirement/locations', 'detail': 'Send 10 locations or fewer.'}]))
ex('ProblemQuotaExceeded', 'The query quota for the period is used up',
   problem('quota-exceeded', 'Query quota exceeded', 429, 'QUOTA_EXCEEDED',
           'The daily query quota for this client is used up. Retry after the time in the Retry-After header.'))

# ---------------------------------------------------------------- signals
SIG_REQ = {
    'reference': 'example-signal-1', 'confidence': 'PLANNED',
    'confidentiality': {'sharing': 'NONE', 'contactPermitted': True},
    'contact': {'name': 'Network Operations', 'email': 'noc@example.com'},
    'requirement': {'locations': [FR],
                    'demand': {'power': {'value': 800, 'unit': 'KVA'}, 'cabinets': {'count': 40}, 'density': {'target': 20, 'unit': 'KVA'}},
                    'timeframe': {'neededForService': '2027-06-01'},
                    'desiredFeatures': [LIQ]}}


def signal(req, state, revision, updated, **extra):
    s = copy.deepcopy(req)
    s.update({'signalId': 'sig-0001', 'state': state, 'revision': revision, 'createdAt': '2026-11-18T10:00:00Z',
              'updatedAt': updated, 'expiresAt': '2027-11-18T10:00:00Z'})
    s.update(extra)
    return s


ex('SignalCreated', 'The stored signal: state RECEIVED, revision 1', signal(SIG_REQ, 'RECEIVED', 1, '2026-11-18T10:00:00Z'))
ex('SignalAcknowledged', 'After the provider took the signal into planning, with its current answer',
   signal(SIG_REQ, 'ACKNOWLEDGED', 1, '2026-11-19T09:30:00Z', answer=answer('ans-0201', '2026-11-19T09:30:00Z', [{
       'location': FR, 'grade': 'POSSIBLE', 'timing': {'status': 'PLANNED', 'availableForService': '2027-Q3'},
       'supportedFeatures': [feat('LIQUID_COOLING', 'AVAILABLE', True)], 'reasons': ['TIMING']}])))
SIG_AMEND = copy.deepcopy(SIG_REQ)
SIG_AMEND['confidence'] = 'FUNDED'
SIG_AMEND['requirement']['demand'] = {'power': {'value': 1200, 'unit': 'KVA'}, 'cabinets': {'count': 60}, 'density': {'target': 20, 'unit': 'KVA'}}
SIG_AMEND['requirement']['timeframe'] = {'neededForService': '2027-Q3'}
ex('SignalAmendRequest', 'The whole signal with a larger demand, a later date, and a firmer confidence', SIG_AMEND)
ex('SignalAmended', 'Revision 2, back in state RECEIVED', signal(SIG_AMEND, 'RECEIVED', 2, '2026-11-25T14:00:00Z'))
ex('ProblemPreconditionFailed', 'An amend sent with the ETag of an older revision',
   problem('precondition-failed', 'The resource has changed', 412, 'PRECONDITION_FAILED',
           'The If-Match value does not match the current version. Read the signal again and repeat the amend.'))
ex('SignalWithdrawn', 'State WITHDRAWN: no longer an active need, still readable', signal(SIG_AMEND, 'WITHDRAWN', 2, '2026-12-10T08:00:00Z'))
ex('SignalReactivated', 'An amend of a withdrawn signal: revision 3, state RECEIVED', signal(SIG_AMEND, 'RECEIVED', 3, '2026-12-15T11:00:00Z'))
SIG_CLOSED = signal(SIG_AMEND, 'CLOSED', 3, '2027-02-01T16:00:00Z', closeReason='FULFILLED')
ex('SignalClosed', 'A signal the provider closed, with the reason', SIG_CLOSED)
ex('ProblemStateConflict', 'An amend of a signal in state CLOSED',
   problem('state-conflict', 'The signal cannot be changed in its current state', 409, 'STATE_CONFLICT',
           'The signal is CLOSED. Create a new signal.'))
ex('ProblemNotFound', 'A read of a signal that was deleted',
   problem('not-found', 'Not found', 404, 'NOT_FOUND', 'No signal with this identifier exists.'))
SIG_AGG = {
    'reference': 'example-signal-2', 'confidence': 'FUNDED',
    'confidentiality': {'sharing': 'AGGREGATED', 'contactPermitted': False},
    'expiresAt': '2027-06-30T00:00:00Z',
    'requirement': {'locations': [{'level': 'REGION', 'code': 'EMEA'}],
                    'demand': {'power': {'value': 12, 'unit': 'MW'}},
                    'timeframe': {'neededForService': '2028'},
                    'desiredFeatures': [{'feature': 'DIRECT_TO_CHIP_COOLING', 'required': True}]}}
ex('SignalAggregatedRequest', 'A funded need that can be counted in anonymous totals, with no contact', SIG_AGG)
SIG2 = copy.deepcopy(SIG_AGG)
SIG2.update({'signalId': 'sig-0002', 'state': 'RECEIVED', 'revision': 1, 'createdAt': '2026-11-20T12:00:00Z', 'updatedAt': '2026-11-20T12:00:00Z'})
ex('SignalAggregatedCreated', 'The stored signal with the expiry the customer set', SIG2)
ex('SignalsPage', 'A page with two signals', {
    'data': [signal(SIG_AMEND, 'ACKNOWLEDGED', 2, '2026-11-26T09:00:00Z'), SIG2],
    'pagination': {'limit': 50}})

# ---------------------------------------------------------------- subscriptions
SUB_REQ = {
    'name': 'Frankfurt liquid cooling', 'notifyOn': 'ANY_CHANGE',
    'requirement': {'locations': [FR],
                    'demand': {'cabinets': {'count': 20}, 'density': {'target': 40, 'unit': 'KW'}},
                    'timeframe': {'neededForService': '2027-Q4'},
                    'desiredFeatures': [LIQ]},
    'delivery': {'type': 'WEBHOOK', 'url': 'https://customer.example/hooks/capacity'}}
SECRET = 'whsec_example_0123456789abcdef'


def subscription(req, sid, state, updated, last=None, secret=None, created='2026-11-18T11:00:00Z'):
    s = copy.deepcopy(req)
    if secret:
        s['delivery']['signingSecret'] = secret
    s.update({'subscriptionId': sid, 'state': state, 'createdAt': created, 'updatedAt': updated})
    if last is not None:
        s['lastSequence'] = last
    return s


def event(n, etype, time, sub, data):
    d = {'subscriptionId': sub, 'sequence': n}
    d.update(data)
    return {'specversion': '1.0', 'id': 'evt-%s-%06d' % (sub, n), 'source': BASE, 'type': 'org.opencapacity.' + etype,
            'subject': sub, 'time': time, 'datacontenttype': 'application/json', 'data': d}


ex('SubscriptionWebhookRequirementRequest', 'Follow a requirement, report any change, deliver to a webhook', SUB_REQ)
ex('SubscriptionPendingVerification', 'The new subscription with its signing secret, waiting for verification',
   subscription(SUB_REQ, 'sub-0002', 'PENDING_VERIFICATION', '2026-11-18T11:00:00Z', secret=SECRET))
EV_VERIFY = ex('EventVerification', 'The verification event sent to a new webhook endpoint',
               event(1, 'subscription.verification', '2026-11-18T11:00:01Z', 'sub-0002', {'challenge': 'c7f3a1d09b2e4f58'}))


def sub_answer(aid, at, grade, timing, liquid):
    r = {'location': FR, 'grade': grade, 'timing': timing, 'supportedFeatures': [feat('LIQUID_COOLING', liquid, True)]}
    if grade != 'AVAILABLE':
        r['reasons'] = ['TIMING']
    return answer(aid, at, [r])


ex('EventAnswerInitial', 'The first answer event after activation',
   event(2, 'answer.updated', '2026-11-18T11:00:05Z', 'sub-0002', {'reason': 'INITIAL', 'answer': sub_answer(
       'ans-0301', '2026-11-18T11:00:05Z', 'POSSIBLE', {'status': 'PLANNED', 'availableForService': '2028-Q1'}, 'POSSIBLE')}))
ex('EventAnswerDetailChange', 'The service date moved earlier and the grade did not change',
   event(3, 'answer.updated', '2026-12-04T09:20:00Z', 'sub-0002', {'reason': 'DETAIL_CHANGE', 'answer': sub_answer(
       'ans-0318', '2026-12-04T09:20:00Z', 'POSSIBLE', {'status': 'PLANNED', 'availableForService': '2027-Q4'}, 'AVAILABLE')}))
ex('EventAnswerRefresh', 'The previous answer expired and nothing else changed',
   event(4, 'answer.updated', '2026-12-05T09:20:00Z', 'sub-0002', {'reason': 'REFRESH', 'answer': sub_answer(
       'ans-0325', '2026-12-05T09:20:00Z', 'POSSIBLE', {'status': 'PLANNED', 'availableForService': '2027-Q4'}, 'AVAILABLE')}))
EV_GRADE = ex('EventAnswerGradeChange', 'The grade changed from POSSIBLE to AVAILABLE',
              event(5, 'answer.updated', '2026-12-12T15:45:00Z', 'sub-0002', {'reason': 'GRADE_CHANGE', 'answer': sub_answer(
                  'ans-0340', '2026-12-12T15:45:00Z', 'AVAILABLE', {'status': 'PLANNED', 'availableForSale': 'NOW', 'availableForService': '2027-Q4'}, 'AVAILABLE')}))
ex('EventSignalWithdrawn', 'Sent to a subscription that follows a signal, when the customer withdraws the signal',
   event(18, 'signal.updated', '2026-12-10T08:00:01Z', 'sub-0001', {'signalId': 'sig-0001', 'signalState': 'WITHDRAWN'}))
ex('EventSubscriptionSuspended', 'The provider stopped delivery after repeated failures',
   event(6, 'subscription.updated', '2026-12-20T03:10:00Z', 'sub-0002', {'subscriptionState': 'SUSPENDED'}))
SUB_PAUSE = copy.deepcopy(SUB_REQ)
SUB_PAUSE['paused'] = True
ex('SubscriptionPauseRequest', 'The whole subscription with paused set to true', SUB_PAUSE)
ex('SubscriptionPaused', 'State PAUSED: no events are delivered', subscription(SUB_PAUSE, 'sub-0002', 'PAUSED', '2026-12-13T10:00:00Z', last=5))
SUB_URL = copy.deepcopy(SUB_REQ)
SUB_URL['delivery']['url'] = 'https://customer.example/hooks/capacity-v2'
ex('SubscriptionUrlChangeRequest', 'The whole subscription with a new webhook URL', SUB_URL)
ex('SubscriptionReverification', 'A changed URL returns the subscription to PENDING_VERIFICATION',
   subscription(SUB_URL, 'sub-0002', 'PENDING_VERIFICATION', '2026-12-21T09:00:00Z', last=6))

SUB_PULL = {'name': 'Amsterdam small footprint', 'notifyOn': 'GRADE_CHANGE',
            'requirement': {'locations': [AM], 'demand': {'cabinets': {'count': 6}, 'density': {'max': 10, 'unit': 'KVA'}},
                            'timeframe': {'neededForService': '2027-02'}},
            'delivery': {'type': 'PULL'}}
ex('SubscriptionPullRequest', 'Follow a requirement and read the events yourself', SUB_PULL)
ex('SubscriptionPullActive', 'A PULL subscription is ACTIVE at once',
   subscription(SUB_PULL, 'sub-0003', 'ACTIVE', '2026-11-18T12:00:00Z', last=1, created='2026-11-18T12:00:00Z'))


def pull_answer(aid, at, grade):
    r = {'location': AM, 'grade': grade, 'supportedFeatures': []}
    if grade != 'AVAILABLE':
        r['reasons'] = ['SPACE']
    return answer(aid, at, [r])


PULL_EVENTS = [
    event(1, 'answer.updated', '2026-11-18T12:00:02Z', 'sub-0003', {'reason': 'INITIAL', 'answer': pull_answer('ans-0401', '2026-11-18T12:00:02Z', 'UNAVAILABLE')}),
    event(2, 'answer.updated', '2026-11-27T07:30:00Z', 'sub-0003', {'reason': 'GRADE_CHANGE', 'answer': pull_answer('ans-0422', '2026-11-27T07:30:00Z', 'POSSIBLE')}),
    event(3, 'answer.updated', '2026-12-03T13:10:00Z', 'sub-0003', {'reason': 'GRADE_CHANGE', 'answer': pull_answer('ans-0437', '2026-12-03T13:10:00Z', 'AVAILABLE')}),
]
ex('EventsPage', 'Two events and a cursor', {'data': PULL_EVENTS[:2], 'pagination': {'limit': 2, 'next': 'ZXZ0LTAwMDM'}})


# ---------------------------------------------------------------- exchanges
def compact(v):
    return json.dumps(v, separators=(',', ':'))


def sse(events):
    return ''.join('id: %d\nevent: %s\ndata: %s\n\n' % (e['data']['sequence'], e['type'], compact(e)) for e in events)


SIG_T = 1797090300
SIG_BODY = compact(EV_GRADE)
SIG_HEX = hmac.new(SECRET.encode(), ('%d.%s' % (SIG_T, SIG_BODY)).encode(), hashlib.sha256).hexdigest()
SIGNATURE = 't=%d,v1=%s' % (SIG_T, SIG_HEX)
AUTH = {'Authorization': 'Bearer ACCESS_TOKEN'}
JSON_H = {'Authorization': 'Bearer ACCESS_TOKEN', 'Content-Type': 'application/json'}


def step(title, op, method, path, status, req=None, res=None, req_headers=None, res_headers=None, **extra):
    s = {'title': title, 'operationId': op, 'request': {'method': method, 'path': path}, 'response': {'status': status}}
    if req_headers:
        s['request']['headers'] = req_headers
    if req:
        s['request']['example'] = req
    if res_headers:
        s['response']['headers'] = res_headers
    if res:
        s['response']['example'] = res
    for k, v in extra.items():
        a, b = k.split('_', 1)
        s[a][b] = v
    return s


def q(title, req, res, status=200, res_headers=None):
    return step(title, 'queryCapacity', 'POST', '/queries', status, req, res, JSON_H, res_headers)


def hook(title, example, signature='t=<unix seconds>,v1=<hex>', **extra):
    return step(title, 'receiveCapacityEvent', 'POST', 'https://customer.example/hooks/capacity', 200, example, None,
                {'Content-Type': 'application/cloudevents+json', 'OpenCapacity-Signature': signature}, **extra)


EXCHANGES = [
    {'id': 'discover', 'title': 'Discover what a provider supports', 'steps': [
        step('Read the capabilities', 'getCapabilities', 'GET', '/capabilities', 200, None, 'Capabilities'),
        step('Read the capabilities of a provider that implements queries only', 'getCapabilities', 'GET', '/capabilities', 200, None, 'CapabilitiesCoreOnly'),
        step('List locations', 'listLocations', 'GET', '/locations?limit=5', 200, None, 'LocationsPage', AUTH),
    ]},
    {'id': 'query', 'title': 'Query capacity', 'steps': [
        q('Cabinets and a density range', 'QueryCabinetsAndDensity', 'AnswerBanded'),
        q('The same query answered with grades only', 'QueryCabinetsAndDensity', 'AnswerGradeOnly'),
        q('Power alone, in a region or an area', 'QueryPowerOnly', 'AnswerPowerOnly'),
        q('Total power, cabinets, and density together', 'QueryPowerCabinetsDensity', 'AnswerPowerCabinetsDensity'),
        q('A facility question answered at metro level', 'QueryFacility', 'AnswerCoarserThanRequested'),
        q('An area answered with named locations', 'QueryArea', 'AnswerArea'),
        q('A metro the provider does not serve', 'QueryNotServed', 'AnswerNotServed'),
        q('A partial fit', 'QueryPartialFit', 'AnswerPartialFit'),
        q('Interconnection parties and latency', 'QueryInterconnectionLatency', 'AnswerInterconnectionLatency'),
        q('A ramp with a sale date and a service date', 'QueryRamp', 'AnswerRampPlanned'),
        q('An immediate need', 'QueryImmediate', 'AnswerAvailableNow'),
        q('Redundancy and power feed constraints', 'QueryRedundancyPowerFeed', 'AnswerRedundancyUnavailable'),
    ]},
    {'id': 'query-errors', 'title': 'Query errors', 'steps': [
        q('Total power that does not fit the cabinets and density', 'QueryInconsistentDemand', 'ProblemInconsistentDemand', 422),
        q('An area sent to a provider that does not accept areas', 'QueryArea', 'ProblemUnsupportedLocationLevel', 422),
        q('Too many locations', 'QueryTooManyLocations', 'ProblemTooManyLocations', 422),
        q('Query quota used up', 'QueryImmediate', 'ProblemQuotaExceeded', 429, {'Retry-After': '3600'}),
    ]},
    {'id': 'signal-lifecycle', 'title': 'Register, amend, withdraw, and delete a signal', 'steps': [
        step('Register a signal', 'createSignal', 'POST', '/signals', 201, 'SignalRequest', 'SignalCreated',
             dict(JSON_H, **{'Idempotency-Key': '7d3f2a9c-1b6e-4f0a-9c55-0e2d8a41b7f3'}),
             {'Location': '/capacity/v1/signals/sig-0001', 'ETag': '"sig-0001-1"'}),
        step('Read the signal after the provider acknowledged it', 'getSignal', 'GET', '/signals/sig-0001', 200, None, 'SignalAcknowledged',
             AUTH, {'ETag': '"sig-0001-1"'}),
        step('Amend the signal', 'replaceSignal', 'PUT', '/signals/sig-0001', 200, 'SignalAmendRequest', 'SignalAmended',
             dict(JSON_H, **{'If-Match': '"sig-0001-1"'}), {'ETag': '"sig-0001-2"'}),
        step('Amend with a stale ETag', 'replaceSignal', 'PUT', '/signals/sig-0001', 412, 'SignalAmendRequest', 'ProblemPreconditionFailed',
             dict(JSON_H, **{'If-Match': '"sig-0001-1"'})),
        step('Withdraw the signal', 'withdrawSignal', 'POST', '/signals/sig-0001/withdraw', 200, None, 'SignalWithdrawn',
             AUTH, {'ETag': '"sig-0001-3"'}),
        step('Amend the withdrawn signal to make it active again', 'replaceSignal', 'PUT', '/signals/sig-0001', 200, 'SignalAmendRequest', 'SignalReactivated',
             dict(JSON_H, **{'If-Match': '"sig-0001-3"'}), {'ETag': '"sig-0001-4"'}),
        step('Delete the signal', 'deleteSignal', 'DELETE', '/signals/sig-0001', 204, None, None, AUTH),
        step('Read the deleted signal', 'getSignal', 'GET', '/signals/sig-0001', 404, None, 'ProblemNotFound', AUTH),
    ]},
    {'id': 'signal-other', 'title': 'Other signal exchanges', 'steps': [
        step('Register a signal that can be counted in anonymous totals', 'createSignal', 'POST', '/signals', 201, 'SignalAggregatedRequest', 'SignalAggregatedCreated',
             dict(JSON_H, **{'Idempotency-Key': 'b41c7e02-55aa-4d1f-8e3b-6f9d2c7a1e90'}),
             {'Location': '/capacity/v1/signals/sig-0002', 'ETag': '"sig-0002-1"'}),
        step('List signals', 'listSignals', 'GET', '/signals', 200, None, 'SignalsPage', AUTH),
        step('Read a signal the provider closed', 'getSignal', 'GET', '/signals/sig-0001', 200, None, 'SignalClosed', AUTH, {'ETag': '"sig-0001-5"'}),
        step('Amend a closed signal', 'replaceSignal', 'PUT', '/signals/sig-0001', 409, 'SignalAmendRequest', 'ProblemStateConflict',
             dict(JSON_H, **{'If-Match': '"sig-0001-5"'})),
    ]},
    {'id': 'subscribe-webhook', 'title': 'Subscribe with webhook delivery', 'steps': [
        step('Create the subscription', 'createSubscription', 'POST', '/subscriptions', 201, 'SubscriptionWebhookRequirementRequest', 'SubscriptionPendingVerification',
             dict(JSON_H, **{'Idempotency-Key': '2f8e6b1d-90c4-4a7e-b3d2-5c1a9e7f0d46'}), {'ETag': '"sub-0002-1"'}),
        hook('Receive the verification event and echo the challenge', 'EventVerification', response_body={'challenge': 'c7f3a1d09b2e4f58'}),
        hook('Receive the first answer', 'EventAnswerInitial'),
        hook('Receive a change of detail', 'EventAnswerDetailChange'),
        hook('Receive a refresh', 'EventAnswerRefresh'),
        hook('Receive a grade change and verify its signature', 'EventAnswerGradeChange', SIGNATURE, request_rawBody=SIG_BODY,
             request_signature={'signingSecret': SECRET, 'timestamp': SIG_T, 'signedString': '%d.<raw body>' % SIG_T,
                                'algorithm': 'HMAC-SHA256, hex', 'value': SIG_HEX}),
        step('Pause the subscription', 'replaceSubscription', 'PUT', '/subscriptions/sub-0002', 200, 'SubscriptionPauseRequest', 'SubscriptionPaused',
             dict(JSON_H, **{'If-Match': '"sub-0002-2"'}), {'ETag': '"sub-0002-3"'}),
        hook('Receive notice that the provider suspended delivery', 'EventSubscriptionSuspended'),
        step('Change the webhook URL', 'replaceSubscription', 'PUT', '/subscriptions/sub-0002', 200, 'SubscriptionUrlChangeRequest', 'SubscriptionReverification',
             dict(JSON_H, **{'If-Match': '"sub-0002-4"'}), {'ETag': '"sub-0002-5"'}),
        step('Delete the subscription', 'deleteSubscription', 'DELETE', '/subscriptions/sub-0002', 204, None, None, AUTH),
    ]},
    {'id': 'subscribe-signal', 'title': 'Follow a signal', 'steps': [
        step('Create a subscription that follows a signal', 'createSubscription', 'POST', '/subscriptions', 201, 'SubscriptionWebhook', None, JSON_H),
        hook('Receive a grade change for the signal', 'EventAnswerUpdated'),
        hook('Receive notice that the signal was withdrawn', 'EventSignalWithdrawn'),
    ]},
    {'id': 'subscribe-pull', 'title': 'Subscribe and read or stream the events', 'steps': [
        step('Create the subscription', 'createSubscription', 'POST', '/subscriptions', 201, 'SubscriptionPullRequest', 'SubscriptionPullActive',
             JSON_H, {'ETag': '"sub-0003-1"'}),
        step('Read events as a page', 'listSubscriptionEvents', 'GET', '/subscriptions/sub-0003/events?limit=2', 200, None, 'EventsPage',
             dict(AUTH, Accept='application/json')),
        step('Stream events', 'listSubscriptionEvents', 'GET', '/subscriptions/sub-0003/events', 200, None, None,
             dict(AUTH, Accept='text/event-stream'), {'Content-Type': 'text/event-stream'}, response_text=sse(PULL_EVENTS[:2])),
        step('Reconnect after the stream dropped', 'listSubscriptionEvents', 'GET', '/subscriptions/sub-0003/events', 200, None, None,
             dict(AUTH, **{'Accept': 'text/event-stream', 'Last-Event-ID': '2'}), {'Content-Type': 'text/event-stream'}, response_text=sse(PULL_EVENTS[2:])),
    ]},
]

# ---------------------------------------------------------------- emit
PLAIN = re.compile(r'^[A-Za-z][A-Za-z0-9_.-]*$')
RESERVED = {'yes', 'no', 'true', 'false', 'null', 'on', 'off', 'y', 'n'}


def scalar(v):
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return repr(v)
    if PLAIN.match(v) and v.lower() not in RESERVED:
        return v
    return "'" + v.replace("'", "''") + "'"


def emit(v, ind, out):
    pad = ' ' * ind
    if isinstance(v, dict):
        for k, x in v.items():
            if isinstance(x, str) and '\n' in x:
                out.append('%s%s: |' % (pad, scalar(k)))
                out.extend((pad + '  ' + line).rstrip() for line in x.rstrip('\n').split('\n'))
            elif isinstance(x, (dict, list)) and x:
                out.append('%s%s:' % (pad, scalar(k)))
                emit(x, ind + 2, out)
            elif isinstance(x, (dict, list)):
                out.append('%s%s: %s' % (pad, scalar(k), '{}' if isinstance(x, dict) else '[]'))
            else:
                out.append('%s%s: %s' % (pad, scalar(k), scalar(x)))
    else:
        for x in v:
            if isinstance(x, (dict, list)) and x:
                sub = []
                emit(x, ind + 2, sub)
                out.append(pad + '- ' + sub[0].lstrip())
                out.extend(sub[1:])
            else:
                out.append('%s- %s' % (pad, scalar(x) if not isinstance(x, (dict, list)) else '[]'))


MARK = '    # Examples below this line are generated by tools/examples.py.\n'
NOTE = '''# x-exchanges lists complete request and response exchanges in the order of real use. Each step
# names an operation, the request line and headers, and the examples in components/examples that
# are its request body and its response body. Paths are relative to the server URL.
'''

if __name__ == '__main__':
    spec = pathlib.Path(__file__).resolve().parent.parent / 'opencapacity-1.0.yaml'
    text = spec.read_text()
    head = text.split(MARK)[0]
    out = []
    emit(EX, 4, out)
    ex_out = []
    emit(EXCHANGES, 2, ex_out)
    spec.write_text(head + MARK + '\n'.join(out) + '\n' + NOTE + 'x-exchanges:\n' + '\n'.join(ex_out) + '\n')
    print(len(EX), 'generated examples;', len(EXCHANGES), 'exchanges;', sum(len(e['steps']) for e in EXCHANGES), 'steps')
    print('signature', SIGNATURE)
