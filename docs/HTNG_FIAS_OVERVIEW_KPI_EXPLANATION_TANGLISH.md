Integration Overview DashboardOvvoru KPI card-um simple-aa — Team-ku explain panna (Tanglish)FOUNDATION IMPLEMENTED — VENDOR VALIDATION PENDINGHMS · HTNG &amp; FIAS Integration · Overview pagePrepared: 20 November 2026 · Audience: project owner + teamBased on the actual code in the ACX-Platform repository (feature/htng-fias-on-develop)Indha document-la irukura numbers ellam DEMO / TEST data (synthetic). Idhu real hotel traffic illa. Ippo endha vendor-um connect aagala.

# Indha Document Enna?

Neenga team kitta "Overview page-la indha card enna solludhu?" nu explain pannanum-na, indha
document use pannalaam. Technical code details-a kammi pannittu, **ovvoru card-um enna
artham, eppadi count aagudhu, ippo yen indha number / status kaattudhu, team kitta eppadi
sollalaam** — idha mattum simple-aa kuduthirukom.

Ovvoru card-kum indha format follow pannirukom:

| Heading | Enna solludhu |
|---|---|
| **Idhu enna?** | card-oda simple artham |
| **Eppadi count aagudhu?** | endha messages-a count pannudhu |
| **Udharanam** | oru chinna kanakku (example) |
| **Ippo demo-la** | demo screen-la enna number, yen |
| **Team kitta sollunga** | neenga apdiye solla oru ready line |
| **Gavanam!** | thappa purinjukka koodaadha vishayam |

Technical-aa full details vendum-na: `docs/HTNG_FIAS_COMPLETE_DASHBOARD_CODE_LEVEL_EXPLANATION.pdf`.

## Table of Contents

- Chapter 1 – Integration-na Enna? (Oru Nimisham Story)
- Chapter 2 – Dashboard-la 5 Pages
- Chapter 3 – Overview Page: Yen Vachirukom?
- Chapter 4 – Integration Status Cards (Mela Irukura 3 Cards)
- Chapter 5 – Message Activity: 6 KPI Cards
- Chapter 6 – Cards-a Add Pannalaamaa? (Romba Mukkiyam)
- Chapter 7 – HTNG Health, FIAS Health Panels Matrum Recent Activity
- Chapter 8 – Time Matrum Refresh
- Chapter 9 – Status Words: Oru Chinna Dictionary
- Chapter 10 – Team Kekkura Common Kelvigal (FAQ)
- Chapter 11 – Team-ku 5 Nimisham Explain Script
- Chapter 12 – Oru Page Cheat Sheet
- Appendix – Technical Reference (Kettaa Mattum)

# Chapter 1 – Integration-na Enna? (Oru Nimisham Story)

Ovvoru hotel-um already oru **PMS** (Property Management System) vendor software use
pannuvaanga. Guest check-in, check-out, room move ellam andha PMS-la dhaan first nadakkum.

Namma **HMS** software-ku indha vishayam automatic-aa therinjaa dhaan room ready pannradhu,
housekeeping, devices ellam correct-aa handle panna mudiyum. Staff thirumba type panna
vendaam.

Adhukaaga PMS → HMS-ku messages varra oru "door" (integration) build pannirukom. Indha door
rendu type-la irukkalaam:

| Type | Simple-aa | Ippo status |
|---|---|---|
| **HTNG** | web service — PMS namma server-ku HTTP-la message anuppum | code ready, aana switch OFF; vendor documents varala |
| **FIAS** | TCP link — oru continuous connection, records anuppum | code ready, aana link start pannala; vendor documents varala |

Rendu-um yen? **Vendor yaarunu innum decide aagala (HF-03)**, avanga endha protocol
use pannuvaanganu-um theriyaadhu (HF-04). Adhanaala rendukkum ready-aa oru common system
build pannirukom.

> **Figure: Oru message-oda payanam (simple view)** (diagram rendered in the PDF)

**Mukkiyamaana vishayam:** ippo endha vendor-um connect aagala. Dashboard-la therira numbers
ellam namma test / demo data. Adhai "live hotel traffic" nu team kitta solla koodaadhu.

# Chapter 2 – Dashboard-la 5 Pages

| Page | Oru line-la | Yaaru use pannuvaanga |
|---|---|---|
| **Overview** | HTNG, FIAS rendu-oda health + message counts, oru screen-la | manager, project owner, ops lead |
| **HTNG Monitoring** | HTNG mattum detail-aa | integration / support team |
| **FIAS Monitoring** | FIAS mattum detail-aa (same layout) | integration / support team |
| **Message Logs** | messages search panna (protocol, status, hotel, date filter) | support team |
| **Failed Messages / DLQ** | fail aana messages paarkka — **read-only**, edhuvum maatha mudiyaadhu | support team |

Indha pages paarkka user-ku **Facility Management "read" permission** vendum. Illana
"Access denied" varum. Ovvoru user-um **avanga hotels-oda data mattum** dhaan paarppaanga.

# Chapter 3 – Overview Page: Yen Vachirukom?

Overview page oru **"health check" screen**. Manager oru paarvai paarthaa indha 3 kelvikku
badhil kidaikkanum:

1. HTNG, FIAS ready-aa? Connection eppadi irukku?
2. Evlo messages vandhirukku, evlo pending, evlo fail aachu?
3. Latest-aa enna nadandhudhu, latest-aa enna fail aachu?

> **Figure: Overview page-la enna enna section irukku (mela irundhu keezha)** (diagram rendered in the PDF)

Page-la mela **"Your facilities only · updated 20 Nov 2026, 11:07 am"** maadhiri oru line
irukkum. Adhu **server indha data-va eppo ready pannuchu** nu solludhu — page last refresh
time maadhiri. Page **ovvoru 60 second-kkum automatic-aa refresh** aagum; **Refresh** button
press panna udane refresh aagum.

# Chapter 4 – Integration Status Cards (Mela Irukura 3 Cards)

## 4.1 HTNG card

Indha card-la 3 vishayam irukku:

### (a) Production readiness: "Not ready"

- **Idhu enna?** HTNG real hotel-la use panna ready-aa illaya nu oru final verdict.
- **Eppadi decide aagudhu?** Oru checklist maadhiri. Edhaavadhu oru item pending-aa irundhaalum
  "Not ready". Ippo pending items: vendor validation, business approvals, DBA approval, test
  results publish aagala, integration switch OFF, live HMS update gate closed.
- **Team kitta sollunga:** *"Idhu technical failure illa. Approvals-um vendor documents-um
  varra varaikkum idhu 'Not ready' dhaan kaattum — idhu expected."*
- **Gavanam!** Idhu connection status illa; idhu **readiness / approvals status**.

### (b) Connection: "Disabled"

- **Idhu enna?** HTNG door (web service endpoint) **switch ON-aa OFF-aa** nu solludhu.
- **Yen "Disabled"?** Rendu settings (`INTEGRATION_ENABLED`, `INTEGRATION_HTNG_INBOUND_ENABLED`)
  default-aa OFF. Safety-kaaga naama ON pannala.
- **Eppo maarum?** Switch ON pannaa "Enabled" (or vendor schema illaatha naala "Enabled ·
  awaiting vendor spec") nu maarum.
- **Team kitta sollunga:** *"HTNG door-a naama deliberately close pannirukom. Network problem
  illa, configuration switch OFF."*
- **Gavanam!** Idhu network test illa. Vendor kooda connection irukaa nu idhu check pannaadhu.

### (c) Processing: "Backlog stalled"

- **Idhu enna?** Mudiyaadha (unfinished) messages-la **oldest message 15 nimishathukku mela
  wait pannudhaa** nu paarkkum. Aamaam-na "Backlog stalled".
- **Ella status-um:**

| Status | Artham |
|---|---|
| Idle · no backlog | pending message edhuvum illa |
| Processing backlog | pending irukku, aana 15 min-kulla |
| **Backlog stalled** | oldest pending message 15 min-ku mela wait pannudhu |
| Unavailable | database-la integration tables illa, check panna mudiyala |

- **Yen ippo "stalled"?** Demo-la messages process panra **worker program run aagala**
  (integration switch OFF). Adhanaala pending messages appadiye irukku, age koodite pogudhu
  (HTNG oldest ≈ 17 mani neram).
- **Team kitta sollunga:** *"Worker ippo run aagala, adhanaala pending messages move aagala.
  System crash illa."*
- **Gavanam!** "Awaiting retry" messages-um (next try future-la schedule aanadhu) indha
  calculation-la count aagum. So "stalled" nu vandhaa udane "crash" nu nenaikka koodaadhu.

## 4.2 FIAS card

| Item | Ippo | Simple artham |
|---|---|---|
| Production readiness | **Not ready** | HTNG maadhiriye — approvals + vendor documents pending |
| Connection | **Not observable** | FIAS TCP link **endha process-layum start pannala**. Adhanaala dashboard-ku link state theriyaadhu. Idhu "connected"-um illa, "disconnected"-um illa — **"theriyaadhu"** |
| Processing | **Backlog stalled** | same reason — worker run aagala (FIAS oldest ≈ 28 mani neram) |

- **Team kitta sollunga:** *"FIAS-ku code ready, test-la work aagudhu. Aana real link start
  panna vendor-oda FIAS manual-um link rules-um vendum. Adhanaala 'Not observable'."*
- **Gavanam!** "Not observable" ≠ "Down". Grey / dashed badge — failure colour illa.

## 4.3 Vendor validation card: "Vendor validation pending"

- **Idhu enna?** Vendor-oda official specification vachu, vendor test environment-la namma
  integration verify pannoma nu solludhu.
- **Yen pending?** Vendor documents edhuvum varala:
  - HTNG: schema / profile (HF-07), security (HF-08)
  - FIAS: manual + records (HF-11), link rules (HF-06), property code case (HF-05)
- **Idhu live-aa check aagudhaa?** Illa. Code-la irukura **approval list** paarthu decide
  aagudhu. Namma synthetic tests pass aanaalum idhu maaraadhu.
- **Team kitta sollunga:** *"Namma tests ellam pass. Aana adhu vendor certification illa.
  Vendor documents vandha appuram dhaan validation start aagum."*

# Chapter 5 – Message Activity: 6 KPI Cards

Mudhalla 3 rules — idhu purinjaa ella card-um easy:

1. **Time limit illa.** Indha cards "inniku" or "indha week" count illa. Database-la
   **ippo store aagi irukura ella messages**-um count aagum. (Old messages-a delete panra
   retention setting ippo OFF.)
2. **Unga hotels mattum.** Login panna user-oda facilities-oda messages mattum.
3. **HTNG + FIAS serthu.** Ovvoru card-um rendu protocol-um add panni kaattum.

Database-la paarkka mudiyalana (tables illa), card-la **"Unavailable"** varum — **0 varaadhu**.
0 vandhaa "check pannom, onnum illa" nu artham.

Demo numbers (synthetic data): **Inbound 42 · Outbound 3 · Pending 13 · Failed 5 ·
Awaiting retry 5 · DLQ 5.**

## 5.1 INBOUND — "Received from vendors"

- **Idhu enna?** Vendor PMS-la irundhu vandhu, namma system accept panni store panna
  **ella incoming messages**-oda total. Endha status-la irundhaalum count aagum.
- **Eppadi count aagudhu?** Incoming messages table-la ella rows-um count → HTNG + FIAS add.
- **Udharanam:** HTNG 12 processed + 3 pending + 2 failed = 17; FIAS 5 processed + 1 retry = 6
  → **Inbound = 23**.
- **Ippo demo-la:** HTNG 24 + FIAS 18 = **42**.
- **Count-la varaadhavai:**
  - duplicate message (same message thirumba vandhaa) — pudhu row create aagaadhu;
  - reject aana messages (wrong password, unknown hotel, bad format) — store-e aagaadhu.
- **Team kitta sollunga:** *"Ippo varaikkum namma accept panni store panna incoming messages
  total 42. Idhu daily count illa."*
- **Gavanam!** Message Logs page default-aa **last 7 days** mattum kaattum — adhanaala andha
  page-la 38 nu varum, ingu 42. Rendum correct dhaan.

## 5.2 OUTBOUND — "Queued or sent to vendors"

- **Idhu enna?** Namma HMS-la irundhu vendor-ku **thirumba anuppa ready pannina messages**
  (reply / update) total. Endha status-la irundhaalum count.
- **Eppadi count aagudhu?** Outgoing (outbox) messages table-la ella rows, HTNG + FIAS.
- **Udharanam:** 4 waiting + 2 sent → **Outbound = 6**.
- **Ippo demo-la:** HTNG 2 + FIAS 1 = **3**, moonum **waiting (queued)**.
- **Yen anuppala?** Outgoing messages anuppura part (outbox relay) **start pannala**, vendor
  address-um illa (HF-24). Adhanaala "sent" ippo 0.
- **Team kitta sollunga:** *"3 reply messages ready-aa queue-la irukku. Vendor endpoint
  configure aagura varaikkum avanga poga maattaanga."*
- **Gavanam!** Card label "Queued or sent" — ippo ellam "queued" dhaan.

## 5.3 PENDING — "Waiting to be processed"

- **Idhu enna?** Innum **mudiyaadha** incoming messages.
- **Eppadi count aagudhu?** Indha 3 status-um serthu:

| Status | Artham |
|---|---|
| Pending | store aachu, worker innum edukkala |
| Processing | worker ippo process pannudhu |
| Awaiting retry | onetime fail aachu (temporary problem), thirumba try panna wait pannudhu |

- **Udharanam:** 3 pending + 1 processing + 2 awaiting retry → **Pending = 6**.
- **Ippo demo-la:** HTNG 8 + FIAS 5 = **13** (adhula 5 awaiting retry, 3 processing).
- **Team kitta sollunga:** *"13 messages innum complete aagala. Adhula 5 retry-ku wait
  pannudhu. Worker run aagaadhadhaala idhu kuraiyaadhu."*
- **Gavanam!** Outgoing pending messages indha card-la illa — incoming mattum.
  Card-la "Waiting to be processed" nu irundhaalum, processing-la irukuradhum retry-ku
  wait panradhum kooda idhula irukku.

## 5.4 FAILED — "Inbound, moved to the DLQ"

- **Idhu enna?** System **"mudiyaadhu"** nu give up panna incoming messages. Idhu ellam
  **DLQ (Dead Letter Queue)**-la poyidum. Oru aal paarthu dhaan fix pannanum.
- **Eppo oru message Failed aagum?**
  - **Permanent problem** (wrong data, HMS rule reject, approval illa) → **first try-laye**
    failed;
  - **Temporary problem** (HMS busy, timeout) → automatic retry. **5 attempts** mudinjum
    sari aagalana failed.
- **Udharanam:** 2 failed + 4 awaiting retry → **Failed = 2** (retry-la irukuradhu count illa).
- **Ippo demo-la:** HTNG 3 + FIAS 2 = **5**. Reason: "Rejected by HMS business rule"
  (Permanent).
- **Team kitta sollunga:** *"5 messages permanent-aa fail aagi DLQ-la irukku. Support team
  Failed Messages page-la paarthu reason check pannalaam."*
- **Gavanam!** Fail aagi retry-la success aana message ingu count aagaadhu — adhu processed.
  Failed message thaanaa sari aagaadhu; authorised person "redrive" pannanum (adhu indha
  dashboard-la illa, read-only).

## 5.5 AWAITING RETRY — "Scheduled for another attempt"

- **Idhu enna?** **Temporary problem**-naala fail aagi, **thirumba automatic-aa try panna
  schedule aana** incoming messages.
- **Retry eppo?** Wait time double aagite pogum: 5 sec → 10 → 20 → 40 … maximum 15 nimisham
  (real service-la random "jitter" serkkuradhaala wait konjam kammiyaavum irukkalaam).
  Total 5 attempts.
- **Udharanam:** HTNG 2 + FIAS 1 → **Awaiting retry = 3**.
- **Ippo demo-la:** HTNG 3 + FIAS 2 = **5**.
- **Team kitta sollunga:** *"5 messages temporary problem-naala wait pannudhu; system
  thaanaave thirumba try pannum."*
- **Gavanam!** Indha 5 messages **Pending card-layum already count aagirukku**. Rendaiyum add
  panna koodaadhu.

## 5.6 DLQ — "Inbound and outbound"

- **Idhu enna?** Dead Letter Queue-la irukura **ella** messages — incoming failed +
  outgoing failed.
- **Eppadi count aagudhu?** Failed (incoming) + outgoing failed.
- **Udharanam:** 2 incoming failed + 1 outgoing failed → **DLQ = 3**, Failed = 2.
- **Ippo demo-la:** 5 + 0 = **5** (outgoing failed illa, adhanaala Failed = DLQ).
- **Team kitta sollunga:** *"DLQ-la mottham 5 messages. Ellam incoming dhaan."*
- **Gavanam!** Failed-um DLQ-um add panna koodaadhu — Failed already DLQ-kulla irukku.

# Chapter 6 – Cards-a Add Pannalaamaa? (Romba Mukkiyam)

Team-la yaaraavadhu "Pending + Failed + Awaiting retry + DLQ add pannaa total varum" nu
nenaikkalaam. **Adhu thappu.**

> **Figure: KPI numbers eppadi ondrodu ondru connect aagudhu (demo data)** (diagram rendered in the PDF)

| Card A | Card B | Same message rendu-layum varumaa? |
|---|---|---|
| Pending | Awaiting retry | **Aamaam** — retry messages Pending-kulla irukku |
| Failed | DLQ | **Aamaam** — Failed ellam DLQ-kulla irukku |
| Inbound | Pending / Failed / Awaiting retry | **Aamaam** — ellame Inbound-oda part |
| Pending | Failed | Illa |
| Awaiting retry | Failed | Illa |
| Inbound | Outbound | Illa (vera vera table) |

**Correct-aana kanakku:**

```text
Inbound = Processed + Pending + Failed
   42   =    24     +   13    +   5
```

Processed (24) Overview-la card-aa illa; HTNG / FIAS pages-la "Processed" card-la irukku.

# Chapter 7 – HTNG Health, FIAS Health Panels Matrum Recent Activity

## 7.1 Health panels

Overview-la keezha HTNG-ku oru panel, FIAS-ku oru panel. Mela partha same numbers-a
**protocol-wise pirichu** kaattum.

| Row | Artham | Demo HTNG | Demo FIAS |
|---|---|---|---|
| Connection | switch / link status (Chapter 4) | Disabled | Not observable |
| Authentication | vendor login setup irukaa (enabled sender + hotel mapping) | Configured | Configured |
| Processing | backlog status | Backlog stalled | Backlog stalled |
| Vendor validation | vendor verify pannaangalaa | Pending | Pending |
| Last successful processing | kadaisiyaa success aana incoming message time | demo time | demo time |
| Inbound / Outbound | indha protocol mattum | 24 / 2 | 18 / 1 |
| Pending / Awaiting retry | indha protocol mattum | 8 / 3 | 5 / 2 |
| Failed (DLQ) | incoming failed + outgoing failed | 3 | 2 |
| Latest failure | kadaisiyaa fail aana message-oda reason + time | Rejected by HMS business rule · Permanent | same |

Keezha **"HTNG monitoring"**, **"HTNG message logs"** buttons — click panna andha page-ku
pogum (filter already set aagi).

## 7.2 Recent messages / Latest failures

- **Recent messages:** last 7 days-la vandha **latest 5 incoming messages** (HTNG + FIAS).
  Ovvoru row-la: protocol, message type (Check-in / Check-out), hotel, status, received time.
- Mela **"Last successful processing"** — incoming success **or** outgoing sent, edhu latest-oo
  adhoda time.
- **Latest failures:** DLQ-la irukura **latest 5 failed messages** — reason, hotel, time.
- "All messages", "Failed messages" buttons → full pages.

# Chapter 8 – Time Matrum Refresh

| Kelvi | Badhil |
|---|---|
| Message-la irukura time enna? | namma system message-a **accept panna time**. Vendor kudutha time illa |
| Endha timezone? | database-la UTC; screen-la **unga browser / computer timezone**-ku convert aagum (India-na IST) |
| Format? | "20 Nov, 05:43 am" maadhiri — seconds illa; current year-na year kaattaadhu. Mouse vachaa full date + year |
| Refresh panna time maarumaa? | **Maaraadhu.** Message time fixed |
| Refresh panna enna maarum? | "updated …" time maarum; pudhu message vandhaa counts maarum; backlog age koodum |
| Auto refresh? | Overview 60 second-kku oru thadavai (tab open-aa irukkum podhu). Refresh button udane |
| Message Logs / DLQ table auto refresh aagumaa? | Illa — filter maathunaa or page reload pannaa dhaan |

**Udharanam (worker run aanaa):** 4:43-ku message varudhu → Inbound +1, Pending +1. Worker
process panni success aanaa → Pending −1, Processed +1, "Last successful processing" = 4:43.
Adutha refresh-la (60 sec-kulla) screen-la theriyum. **Ippo worker run aagaadhadhaala**
message Pending-laye irukkum, 15 nimisham kazhichu "Backlog stalled" varum.

# Chapter 9 – Status Words: Oru Chinna Dictionary

| Screen-la | Simple artham | Colour |
|---|---|---|
| **Not ready** | production-ku ready illa (approvals / vendor pending) | red |
| **Disabled** | switch OFF (deliberate) | grey |
| **Enabled** | switch ON | green |
| **Not observable** | dashboard-ku theriyaadhu — down illa, unknown | grey dashed |
| **Unavailable** | data edukka mudiyala (database tables illa / error) | grey dashed |
| **Not currently observable** | indha number-a dashboard-aal paarkka mudiyaadhu | grey text |
| **Backlog stalled** | oldest unfinished message 15 min-ku mela wait | red |
| **Idle · no backlog** | pending edhuvum illa | green |
| **Pending** (badge) | approval / validation innum varala | amber |
| **Vendor validation pending** | vendor verify pannala | amber |
| **Configured** | vendor login + hotel mapping setup irukku | green |
| **Processed** | message success-aa mudinjadhu | green |
| **Awaiting retry** | thirumba try panna wait | amber |
| **Failed** | give up — DLQ | red |
| **Test only / Blocked** | vendor spec illa, adapter run aagaadhu | amber / red |

# Chapter 10 – Team Kekkura Common Kelvigal (FAQ)

**K: Dashboard-la numbers irukke, vendor connect aagiduchaa?**
Illa. Idhu demo / test data. Endha vendor-um connect aagala.

**K: "Backlog stalled" — system crash aagiducha?**
Illa. Worker program ippo run aagala (switch OFF). Pending messages appadiye irukku.

**K: FIAS "Not observable" — FIAS down-aa?**
Illa. FIAS link start-e pannala, adhanaala status theriyaadhu. Down nu solla mudiyaadhu.

**K: HTNG "Disabled" — network problem-aa?**
Illa. Safety-kaaga switch OFF pannirukom.

**K: Pending 13, Awaiting retry 5 — total 18 pending-aa?**
Illa. 5 already 13-kulla irukku. Pending = 13 dhaan.

**K: Failed 5, DLQ 5 — total 10 failed-aa?**
Illa. Same 5 messages dhaan.

**K: Inbound 42, Message Logs-la 38 — yen difference?**
Overview-la time limit illa; Message Logs default last 7 days. 4 messages 12 days old.

**K: Failed message-a dashboard-la irundhu thirumba run pannalaamaa?**
Illa. Dashboard read-only. Redrive panna write permission + reason vendum, adhu backend API
mattum (audit record aagum).

**K: Number 0 vandhaa enna artham? "Unavailable" vandhaa?**
0 = check pannom, onnum illa. Unavailable = check panna mudiyala. Rendum vera vera.

**K: Eppo production-ku pogum?**
Vendor name (HF-03), vendor documents (HF-07/08 or HF-11/06/05), DBA approval (HF-39),
business approvals — ivai vandha appuram, vendor validation pannittu dhaan.

# Chapter 11 – Team-ku 5 Nimisham Explain Script

> **1. Purpose:** "Hotels-la PMS-la nadakura check-in, check-out ellam HMS-ku automatic-aa
> varanum. Adhukkaana integration door dhaan HTNG / FIAS. Indha Overview page andha door-oda
> health screen."
>
> **2. Mela 3 cards:** "HTNG, FIAS rendum 'Not ready' — approvals, vendor documents pending.
> HTNG 'Disabled' — naama switch OFF pannirukom. FIAS 'Not observable' — link start pannala,
> adhanaala theriyaadhu. Vendor validation pending."
>
> **3. 6 KPI cards:** "Inbound = vandha messages total. Outbound = vendor-ku anuppa ready-aana
> replies. Pending = innum mudiyaadhadhu (retry-ku wait panradhum serthu). Failed = give up
> panna incoming messages. Awaiting retry = temporary problem, thirumba try pannum. DLQ = ella
> failed messages, incoming + outgoing."
>
> **4. Add pannaadheenga:** "Awaiting retry Pending-kulla irukku, Failed DLQ-kulla irukku.
> Correct kanakku: Inbound = Processed + Pending + Failed — 42 = 24 + 13 + 5."
>
> **5. Ippo nilamai:** "Ellam demo data. Foundation ready, tests pass. Vendor documents, DBA
> approval, business approvals vandha appuram dhaan live. Status: Foundation implemented —
> vendor validation pending."

# Chapter 12 – Oru Page Cheat Sheet

| Card | Oru line artham | Count-la enna | Demo | Add pannalaamaa? |
|---|---|---|---|---|
| INBOUND | vandha ella incoming messages | ella status-um | 42 | — (idhu total) |
| OUTBOUND | vendor-ku anuppa ready-aana messages | ella outgoing status | 3 | Inbound kooda illa |
| PENDING | innum mudiyaadhadhu | pending + processing + awaiting retry | 13 | Awaiting retry kooda **koodaadhu** |
| FAILED | give up panna incoming | DLQ-la irukura incoming | 5 | DLQ kooda **koodaadhu** |
| AWAITING RETRY | temporary fail, thirumba try | retry-ku wait | 5 | Pending-kulla already irukku |
| DLQ | ella failed (in + out) | incoming failed + outgoing failed | 5 | Failed-a include pannudhu |

**Nyaabagam vachukkunga:** time limit illa · unga hotels mattum · "Unavailable" ≠ 0 ·
"Not observable" ≠ down · demo data ≠ vendor traffic.

# Appendix – Technical Reference (Kettaa Mattum)

Team-la developer yaaraavadhu "idhu code-la enga irukku?" nu kettaa:

| Card / Item | Backend field (API: GET /api/v1/integrations/observability/overview) |
|---|---|
| Inbound | `protocols.htng.messages.inbound.total` + `protocols.fias.messages.inbound.total` |
| Outbound | `protocols.*.messages.outbound.total` (HTNG + FIAS) |
| Pending | `overview.messages.pending` (PENDING + PROCESSING + RETRY_WAIT) |
| Failed | `overview.messages.failed_dead_letter` |
| Awaiting retry | `protocols.*.messages.inbound.retry_wait` (HTNG + FIAS) |
| DLQ | `overview.messages.failed_dead_letter` + `overview.messages.outbound_dead_letter` |
| Status cards | `overview.htng_status` / `overview.fias_status`, `overview.readiness_classification` |

Code: `backend/app/integrations/observability.py`, `backend/app/integrations/processing/activity.py`,
`frontend/src/features/integrations/views/OverviewView.tsx`. Full technical explanation:
`docs/HTNG_FIAS_COMPLETE_DASHBOARD_CODE_LEVEL_EXPLANATION.pdf`.
