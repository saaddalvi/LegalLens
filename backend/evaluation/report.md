# LegalLens evaluation

## Overall (cases: Plain RAG: 36, CRAG: 36)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 96% | 92% |
| Answer accuracy | 86% | 94% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | 0% | 0% |

## english (cases: Plain RAG: 15, CRAG: 15)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 100% | 93% |
| Answer accuracy | 100% | 93% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | 0% | 0% |

## hindi (cases: Plain RAG: 5, CRAG: 5)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 80% | 80% |
| Answer accuracy | 100% | 100% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | 0% | 0% |

## repealed_code (cases: Plain RAG: 6, CRAG: 6)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | 100% | 100% |
| Answer accuracy | 100% | 100% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | 0% | 0% |

## out_of_scope (cases: Plain RAG: 5, CRAG: 5)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | n/a | n/a |
| Answer accuracy | 100% | 100% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | n/a | n/a |

## poor_retrieval (cases: Plain RAG: 5, CRAG: 5)

| Metric | Plain RAG | CRAG |
|---|---|---|
| Retrieval hit-rate | n/a | n/a |
| Answer accuracy | 0% | 80% |
| Citation validity (after blocking) | 100% | 100% |
| Hallucinated citations before blocking | 0% | 0% |

## Per case

| Case | Plain RAG | CRAG |
|---|---|---|
| en-const-arrest | correct, hit (corpus) | correct, hit (corpus) |
| en-const-speech | correct, hit (corpus) | correct, hit (corpus) |
| en-const-education | correct, hit (corpus) | correct, hit (corpus) |
| en-bns-murder | correct, hit (corpus) | correct, hit (corpus) |
| en-bns-theft | correct, hit (corpus) | correct, hit (corpus) |
| en-bnss-fir | correct, hit (corpus) | correct, hit (corpus) |
| en-bsa-electronic | correct, hit (corpus) | correct, hit (corpus) |
| en-cpa-complaint | correct, hit (corpus) | correct, hit (corpus) |
| en-mta-deposit | correct, hit (corpus) | correct, hit (corpus) |
| en-tpa-lease | correct, hit (corpus) | correct, hit (corpus) |
| en-wages-payment | correct, hit (corpus) | correct, hit (corpus) |
| en-wages-overtime | correct, hit (corpus) | correct, hit (corpus) |
| en-osh-hours | correct, hit (corpus) | correct, hit (corpus) |
| en-ss-gratuity | correct, hit (corpus) | correct, hit (corpus) |
| en-ir-strike | correct, hit (corpus) | wrong, miss (fallback) |
| hi-const-arrest | correct, hit (corpus) | correct, hit (corpus) |
| hi-mta-deposit | correct, miss (corpus) | correct, miss (corpus) |
| hi-cpa-complaint | correct, hit (corpus) | correct, hit (corpus) |
| hi-wages | correct, hit (corpus) | correct, hit (corpus) |
| hi-bns-murder | correct, hit (corpus) | correct, hit (corpus) |
| rep-ipc-302 | correct, hit (corpus) | correct, hit (corpus) |
| rep-ipc-420 | correct, hit (corpus) | correct, hit (corpus) |
| rep-ipc-498a | correct, hit (corpus) | correct, hit (corpus) |
| rep-crpc-154 | correct, hit (corpus) | correct, hit (corpus) |
| rep-crpc-41 | correct, hit (corpus) | correct, hit (corpus) |
| rep-iea-65b | correct, hit (corpus) | correct, hit (corpus) |
| oos-sue | correct (none) | correct (none) |
| oos-sign | correct (none) | correct (none) |
| oos-us-law | correct (none) | correct (none) |
| oos-recipe | correct (none) | correct (none) |
| oos-plead | correct (none) | correct (none) |
| poor-rti | wrong (corpus) | correct (fallback) |
| poor-drunk-driving | wrong (corpus) | wrong (corpus_and_fallback) |
| poor-divorce | wrong (corpus) | correct (fallback) |
| poor-dv | wrong (corpus) | correct (fallback) |
| poor-gst | wrong (corpus) | correct (fallback) |

## Contract evaluation

| Metric | Result |
|---|---|
| Flag recall | 25% |
| Flag precision | 33% |
| Hallucinated clause references (expected 0) | 0 of 54 checked |
| Follow-up accuracy | 83% |
| Follow-up accuracy: clause_supported | 100% |
| Follow-up accuracy: contract_silent | 100% |
| Follow-up accuracy: law | 50% |
| Follow-up accuracy: sign_refusal | 100% |
| Follow-up accuracy: hindi | 50% |

### rent-agreement: Rent agreement with a deposit over the Model Tenancy Act limit

- Expected flags: 4.1: Model Tenancy Act 11
- Found flags: 4.1: Model Tenancy Act 11; 4.2: Model Tenancy Act 11
- Expected flags found: 1 of 1; found flags that were expected: 1 of 2
- Hallucinated clause references: 0

| Follow-up | Query | Result |
|---|---|---|
| clause_supported | How much security deposit do I have to pay, and when do I get it back? | correct (answer, contract_and_corpus, 2 Clause refs) |
| contract_silent | Does this agreement let me keep a pet in the flat? | correct (answer, fallback, 0 Clause refs) |
| law | Is there a legal limit on the security deposit a landlord can take for a home? | correct (answer, corpus, 0 Clause refs) |
| sign_refusal | Should I sign this rent agreement? | correct (refusal, none, 0 Clause refs) |
| hindi | मुझे सिक्योरिटी डिपॉज़िट वापस कब मिलेगा? | correct (answer, contract_and_fallback, 1 Clause ref) |

### job-offer: Job offer with a post-employment non-compete

- Expected flags: 8.1: Indian Contract Act 27
- Found flags: 4.1: Occupational Safety, Health and Working Conditions Code 25
- Expected flags found: 0 of 1; found flags that were expected: 0 of 1
- Hallucinated clause references: 0

| Follow-up | Query | Result |
|---|---|---|
| clause_supported | How much notice do I have to give if I want to leave? | correct (answer, contract_corpus_and_fallback, 2 Clause refs) |
| contract_silent | Can I work from home under this offer? | correct (answer, corpus_and_fallback, 0 Clause refs) |
| law | Are non-compete clauses that apply after I leave a job enforceable in India? | wrong (answer, fallback, 0 Clause refs) |
| sign_refusal | Should I accept this job offer? | correct (refusal, none, 0 Clause refs) |
| hindi | नौकरी छोड़ने के बाद मुझ पर क्या पाबंदी रहेगी? | wrong (answer, contract_and_fallback, 2 Clause refs) |

### nda: NDA with a penalty clause and a restriction on other work

- Expected flags: 6.1: Indian Contract Act 74; 7.1: Indian Contract Act 27
- Found flags: none
- Expected flags found: 0 of 2; found flags that were expected: 0 of 0
- Hallucinated clause references: 0

| Follow-up | Query | Result |
|---|---|---|
| clause_supported | How long do my confidentiality obligations last? | correct (answer, contract_and_fallback, 1 Clause ref) |
| contract_silent | Who pays the legal costs if there is a dispute under this NDA? | error (GoogleRateLimitError) |
| law | Can a contract fix a penalty amount for breach whether or not any loss is suffered? | error (GoogleRateLimitError) |
| sign_refusal | Is it safe for me to sign this NDA? | correct (refusal, none, 0 Clause refs) |
| hindi | इस समझौते में गोपनीय जानकारी में क्या-क्या आता है? | error (GoogleRateLimitError) |

3 follow-ups failed after retries and are excluded from the metrics.

<!-- end contract evaluation -->
